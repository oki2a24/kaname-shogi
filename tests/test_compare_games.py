"""比較対局専用CLIの入出力・終了境界を確認する。"""

import contextlib
import dataclasses
import hashlib
import importlib
import io
import json
import signal
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import Future, ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from multiprocessing import get_context
from pathlib import Path
from unittest.mock import patch

from kaname_shogi.comparison import GameEndReason, GameResult, MoveTiming
from kaname_shogi.game_record import GameRecord
from kaname_shogi.usi_move import parse_usi_move

try:
    compare_games_module = importlib.import_module("kaname_shogi.compare_games")
except ModuleNotFoundError as error:
    if error.name != "kaname_shogi.compare_games":
        raise
    compare_games_module = None

main = getattr(compare_games_module, "main", None)


def _worker_sigint_is_ignored():
    """spawn worker内のSIGINT dispositionをbooleanで返す。"""
    return signal.getsignal(signal.SIGINT) == signal.SIG_IGN


class CompareGamesCliTests(unittest.TestCase):
    def _require_implementation(self):
        """CLI入口がない場合に振る舞い不足として失敗させる。"""
        self.assertIsNotNone(main, "比較CLI入口が未実装です")

    def setUp(self):
        self._require_implementation()

    @staticmethod
    def _positions_file(directory):
        """一局面だけを持つ有効な局面セットを書き出す。"""
        path = Path(directory) / "positions.json"
        path.write_text(
            json.dumps(
                {
                    "format": "kaname-shogi-comparison-positions-v1",
                    "id": "cli-fixture",
                    "positions": [
                        {"id": "initial", "setup_moves": [], "rationale": "初期局面"}
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _args(positions_path, output_dir, **overrides):
        """CLIに必要な条件引数を組み立てる。"""
        values = {
            "--baseline": "material",
            "--candidate": "random",
            "--positions": str(positions_path),
            "--pairs-per-position": "1",
            "--seed": "17",
            "--max-plies": "2",
            "--output-dir": str(output_dir),
        }
        values.update(overrides)
        return [item for pair in values.items() for item in pair]

    @staticmethod
    def _seed_list_file(directory, positions_path):
        """このCLI fixture専用の手書き一組乱数種一覧を保存する。"""
        payload = {
            "format": "kaname-shogi-comparison-seeds-v1",
            "purpose": "pilot",
            "positions_sha256": hashlib.sha256(positions_path.read_bytes()).hexdigest(),
            "position_ids": ["initial"],
            "pairs_per_position": 1,
            "source": "os",
            "bits": 128,
            "pairs": [
                {
                    "position_id": "initial",
                    "repetition_index": 0,
                    "baseline_seed": 11,
                    "candidate_seed": 12,
                }
            ],
        }
        path = Path(directory) / "seed-list.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    @staticmethod
    def _result(schedule, position, config, reason, *, tokens=(), error=None):
        """予定に合う棋譜・計時を持つ小さい結果を作る。"""
        record = GameRecord(position.start_position)
        move_times = []
        for ply, token in enumerate(tokens, start=1):
            current = record.current_position
            side = current.side_to_move
            policy = (
                config.baseline if side is schedule.baseline_side else config.candidate
            )
            move = parse_usi_move(token)
            record.apply_move(move.source, move.destination, promote=move.promote)
            move_times.append(MoveTiming(ply, side, policy, move, 25))
        return GameResult(
            schedule=schedule,
            start_sfen=position.start_sfen,
            initial_move_number=position.initial_move_number,
            record=record,
            reason=reason,
            winner_side=None,
            winner_policy=None,
            plies=len(record.moves),
            move_times_ns=tuple(move_times),
            unfinished_calculation_ns=100
            if reason
            in {
                GameEndReason.INTERRUPTED,
                GameEndReason.ERROR,
            }
            else None,
            error=error,
        )

    def _capture(self, argv, *, atomic_writer=None, runner=None):
        """stdout/stderrを回収しながらCLIを実行する。"""
        stdout = io.StringIO()
        stderr = io.StringIO()
        patches = []
        if atomic_writer is not None:
            patches.append(
                patch.object(compare_games_module, "atomic_write_json", atomic_writer)
            )
        if runner is not None:
            patches.append(patch.object(compare_games_module, "run_game", runner))
        with contextlib.ExitStack() as stack:
            for item in patches:
                stack.enter_context(item)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = main(argv)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def _run_controlled_parallel(
        self,
        positions,
        output_dir,
        *,
        pairs_per_position,
        workers,
        completion_priority=None,
        runner=None,
        interrupt_first_wait=False,
        interrupt_submit_number=None,
        interrupt_during_submit_number=None,
        submit_exception_number=None,
        running_game_ids=(),
        interrupt_writer_name=None,
        writer_failure_name=None,
    ):
        """Future完了順を同期的に制御する偽executorでCLIを実行する。"""
        instances = []
        entries = {}
        completion_order = []
        worker_writes = []
        writer_calls = []
        summary_writes = []
        in_worker = False
        wait_calls = 0
        submit_calls = 0
        interrupted_writer_names = set()
        real_writer = compare_games_module.atomic_write_json

        class ControlledExecutor:
            def __init__(self, *, max_workers, mp_context, initializer=None):
                self.max_workers = max_workers
                self.mp_context = mp_context
                self.initializer = initializer
                self.max_pending = 0
                self.exited = False
                instances.append(self)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                self.exited = True
                return False

            def submit(self, function, *args):
                nonlocal submit_calls
                submit_calls += 1
                if submit_calls == interrupt_submit_number:
                    raise KeyboardInterrupt
                if submit_calls == submit_exception_number:
                    raise BrokenProcessPool("injected submit failure")
                future = Future()
                entries[future] = (function, args)
                if args[0].game_id in running_game_ids:
                    future.set_running_or_notify_cancel()
                self.max_pending = max(
                    self.max_pending,
                    sum(not item.done() for item in entries),
                )
                if submit_calls == interrupt_during_submit_number:
                    signal.raise_signal(signal.SIGINT)
                return future

        def controlled_wait(futures, return_when):
            nonlocal in_worker, wait_calls
            if interrupt_first_wait and wait_calls == 0:
                wait_calls += 1
                raise KeyboardInterrupt
            wait_calls += 1
            already_completed = [future for future in futures if future.done()]
            if already_completed:
                future = already_completed[0]
                return {future}, set(futures) - {future}
            pending = [future for future in futures if not future.done()]

            def rank(future):
                game_id = entries[future][1][0].game_id
                if completion_priority and game_id in completion_priority:
                    return completion_priority[game_id]
                return 1000 + int(game_id[-6:])

            future = min(pending, key=rank)
            function, args = entries[future]
            in_worker = True
            try:
                try:
                    result = function(*args)
                except BaseException as error:
                    future.set_exception(error)
                else:
                    future.set_result(result)
            finally:
                in_worker = False
            completion_order.append(args[0].game_id)
            return {future}, set(futures) - {future}

        def finish_by_limit(schedule, position, config):
            return self._result(schedule, position, config, GameEndReason.PLY_LIMIT)

        def recording_writer(path, payload):
            name = Path(path).name
            writer_calls.append(name)
            if name == "summary.json":
                summary_writes.append(dict(payload))
            if in_worker:
                worker_writes.append(name)
            if name == interrupt_writer_name and name not in interrupted_writer_names:
                interrupted_writer_names.add(name)
                raise KeyboardInterrupt
            if name == writer_failure_name:
                raise OSError(f"{name} write failed")
            real_writer(path, payload)

        args = self._args(
            positions,
            output_dir,
            **{
                "--pairs-per-position": str(pairs_per_position),
                "--workers": str(workers),
            },
        )
        with (
            patch.object(
                compare_games_module,
                "ProcessPoolExecutor",
                ControlledExecutor,
                create=True,
            ),
            patch.object(compare_games_module, "wait", controlled_wait, create=True),
        ):
            exit_code, stdout, stderr = self._capture(
                args,
                atomic_writer=recording_writer,
                runner=runner or finish_by_limit,
            )
        instances[0].worker_writes = worker_writes
        instances[0].writer_calls = writer_calls
        instances[0].summary_writes = summary_writes
        instances[0].submit_calls = submit_calls
        instances[0].stdout = stdout
        return exit_code, stderr, instances[0], completion_order, worker_writes

    def test_help_needs_no_experiment_inputs(self):
        """helpは局面・出力先なしで表示し、実験入力を読まない。"""
        self._require_implementation()
        with patch.object(compare_games_module, "load_config") as load_config:
            exit_code, stdout, stderr = self._capture(["--help"])

        self.assertEqual(exit_code, 0)
        self.assertIn("--baseline", stdout)
        self.assertIn("--positions", stdout)
        self.assertEqual(stderr, "")
        load_config.assert_not_called()

    def test_invalid_arguments_do_not_create_output_or_start_games(self):
        """未知引数・既存パス・壊れたリンクを入力エラー2で拒否する。

        Path.existsがリンク先不在の既存出力を見落とし、mkdir失敗を実行エラー1へ
        誤分類する不具合を検出する。拒否後もリンクを保ち、対局を開始しない。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "not-created"
            with patch.object(compare_games_module, "run_game") as runner:
                exit_code, _, stderr = self._capture(
                    self._args(positions, output_dir) + ["--unknown", "x"]
                )

            self.assertEqual(exit_code, 2)
            self.assertIn("入力エラー", stderr)
            self.assertFalse(output_dir.exists())
            runner.assert_not_called()

            output_dir.mkdir()
            with patch.object(compare_games_module, "run_game") as runner:
                existing_exit, _, _ = self._capture(self._args(positions, output_dir))
            self.assertEqual(existing_exit, 2)
            runner.assert_not_called()

            dangling_output = Path(directory) / "dangling-output"
            dangling_output.symlink_to(Path(directory) / "missing-target")
            with patch.object(compare_games_module, "run_game") as runner:
                dangling_exit, _, dangling_stderr = self._capture(
                    self._args(positions, dangling_output)
                )
            self.assertEqual(dangling_exit, 2)
            self.assertIn("入力エラー", dangling_stderr)
            self.assertTrue(dangling_output.is_symlink())
            runner.assert_not_called()

    def test_worker_count_accepts_one_through_four_and_rejects_other_values(self):
        """ワーカー数を1〜4に制限し、不正値では出力や対局を開始しない。

        上限を越えるプロセス数、ゼロ・負数、整数でない入力を受理したり、値の検証前に
        出力先を作成・対局開始する誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            for workers in range(1, 5):
                output_dir = Path(directory) / f"valid-{workers}"
                try:
                    config = compare_games_module.load_config(
                        self._args(
                            positions,
                            output_dir,
                            **{"--workers": str(workers)},
                        )
                    )
                except ValueError as error:
                    self.fail(f"ワーカー数{workers}を受理できません: {error}")
                self.assertEqual(config.workers, workers)
                self.assertFalse(output_dir.exists())

            for value in ("0", "5", "-1", "not-an-integer"):
                with self.subTest(workers=value):
                    output_dir = Path(directory) / f"invalid-{value}"
                    args = self._args(
                        positions,
                        output_dir,
                        **{"--workers": value},
                    )
                    with patch.object(compare_games_module, "run_game") as runner:
                        exit_code, _, stderr = self._capture(args)

                    self.assertEqual(exit_code, 2)
                    self.assertIn("入力エラー", stderr)
                    self.assertFalse(output_dir.exists())
                    runner.assert_not_called()

    def test_parallel_results_keep_schedule_identity_when_completion_order_reverses(
        self,
    ):
        """完了順が逆転しても棋譜・方式別種を予定IDへ結び付ける。

        Futureの回収順を予定順と誤認し、別局のID・先後・乱数種で結果ファイルを保存する
        誤りを決定的な完了順で検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "parallel-results"
            exit_code, stderr, executor, completion_order, worker_writes = (
                self._run_controlled_parallel(
                    positions,
                    output_dir,
                    pairs_per_position=2,
                    workers=2,
                    completion_priority={
                        "game-000002": 0,
                        "game-000001": 1,
                        "game-000004": 2,
                        "game-000003": 3,
                    },
                )
            )

            self.assertEqual(exit_code, 0, stderr)
            self.assertEqual(executor.max_workers, 2)
            self.assertEqual(executor.mp_context.get_start_method(), "spawn")
            self.assertEqual(worker_writes, [])
            self.assertEqual(
                completion_order,
                ["game-000002", "game-000001", "game-000004", "game-000003"],
            )
            conditions = json.loads((output_dir / "conditions.json").read_bytes())
            self.assertEqual(conditions["execution"]["workers"], 2)
            for planned in conditions["schedule"]:
                saved = json.loads(
                    (output_dir / f"{planned['game_id']}.json").read_bytes()
                )
                self.assertEqual(saved["game_id"], planned["game_id"])
                self.assertEqual(
                    (saved["baseline_seed"], saved["candidate_seed"]),
                    (planned["baseline_seed"], planned["candidate_seed"]),
                )

    def test_parallel_scheduler_bounds_uncollected_futures_by_worker_count(self):
        """未回収Futureを最大ワーカー数までに制限する。

        予定全局を先に投入して、キューとFutureだけを無制限に保持する誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "bounded-results"

            exit_code, stderr, executor, _, _ = self._run_controlled_parallel(
                positions,
                output_dir,
                pairs_per_position=3,
                workers=2,
            )

        self.assertEqual(exit_code, 0, stderr)
        self.assertEqual(executor.max_pending, 2)

    def test_parallel_executor_initializes_workers_to_ignore_sigint(self):
        """並列executorへworkerのSIGINT無視初期化関数を渡す。

        端末Ctrl-Cがworkerまで届いて実行中局を部分終了させる接続漏れを検出する。
        初期化関数の中身はspawn実プロセスの専用テストで別に確認する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "worker-sigint-initializer-results"

            exit_code, stderr, executor, _, _ = self._run_controlled_parallel(
                positions,
                output_dir,
                pairs_per_position=1,
                workers=2,
            )

        self.assertEqual(exit_code, 0, stderr)
        self.assertTrue(callable(executor.initializer))
        self.assertEqual(executor.initializer.__name__, "_ignore_worker_sigint")

    def test_spawn_worker_initializer_ignores_sigint_in_child(self):
        """spawnした子プロセス内でSIGINTを無視するhandlerが設定される。

        親だけのhandler変更では端末のprocess group SIGINTから実行中局を守れないため、
        ProcessPool initializerが子のsignal dispositionを変えることを確認する。
        """
        self._require_implementation()

        with ProcessPoolExecutor(
            max_workers=1,
            mp_context=get_context("spawn"),
            initializer=compare_games_module._ignore_worker_sigint,
        ) as executor:
            ignores_sigint = executor.submit(_worker_sigint_is_ignored).result(
                timeout=20
            )

        self.assertTrue(ignores_sigint)

    def test_parallel_scheduler_leaves_all_artifact_writes_in_parent(self):
        """並列workerはファイルを書かず親が局JSONとsummaryを保存する。

        複数workerから同じ条件・summaryを書いて競合させたり、局保存を抜かす誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "parent-writes-results"

            exit_code, stderr, executor, _, _ = self._run_controlled_parallel(
                positions,
                output_dir,
                pairs_per_position=2,
                workers=2,
            )

        self.assertEqual(exit_code, 0, stderr)
        self.assertEqual(executor.worker_writes, [])
        self.assertEqual(
            executor.writer_calls,
            [
                "conditions.json",
                "game-000001.json",
                "summary.json",
                "game-000002.json",
                "summary.json",
                "game-000003.json",
                "summary.json",
                "game-000004.json",
                "summary.json",
            ],
        )

    def test_parallel_error_cancels_unstarted_work_and_stops_submissions(self):
        """ERROR結果後は未開始Futureを取消し、新しい局を投入しない。

        故障後に予定を追加実行したり、取消し成功futureを投入中として残してsummary件数を
        誤る動作を検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "error-results"

            def fail_first_game(schedule, position, config):
                if schedule.game_id == "game-000001":
                    return self._result(
                        schedule,
                        position,
                        config,
                        GameEndReason.ERROR,
                        error="fixture worker failure",
                    )
                return self._result(schedule, position, config, GameEndReason.PLY_LIMIT)

            exit_code, stderr, executor, _, _ = self._run_controlled_parallel(
                positions,
                output_dir,
                pairs_per_position=2,
                workers=2,
                runner=fail_first_game,
            )

            summary = json.loads((output_dir / "summary.json").read_bytes())
            saved_games = sorted(path.name for path in output_dir.glob("game-*.json"))

        self.assertEqual(exit_code, 1)
        self.assertIn("故障終了", stderr)
        self.assertEqual(executor.max_pending, 2)
        self.assertEqual(saved_games, ["game-000001.json"])
        self.assertEqual(summary["status"], "error")
        self.assertEqual(summary["started_games"], 1)
        self.assertEqual(summary["ended_games"], 1)
        self.assertEqual(summary["in_flight_games"], 0)
        self.assertEqual(summary["unstarted_games"], 3)

    def test_parallel_future_exception_is_saved_as_error_result(self):
        """worker Future例外をERROR局として保存し終了コード1にする。

        子プロセスの例外をCLIから漏らしたり、完了バッチを成功と表示する誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "future-error-results"

            def raise_first_game(schedule, position, config):
                if schedule.game_id == "game-000001":
                    raise RuntimeError("fixture future failure")
                return self._result(schedule, position, config, GameEndReason.PLY_LIMIT)

            try:
                exit_code, stderr, executor, _, _ = self._run_controlled_parallel(
                    positions,
                    output_dir,
                    pairs_per_position=2,
                    workers=2,
                    runner=raise_first_game,
                )
            except Exception as error:
                self.fail(f"worker例外をERROR局にできません: {error}")

            saved = json.loads((output_dir / "game-000001.json").read_bytes())

        self.assertEqual(exit_code, 1)
        self.assertIn("故障終了", stderr)
        self.assertEqual(saved["reason"], "error")
        self.assertIn("RuntimeError: fixture future failure", saved["error"])

    def test_parallel_worker_interruption_cancels_unstarted_work(self):
        """worker内INTERRUPTED後は未開始局を取消し130で終了する。

        worker中断をERRORや成功へ変換したり、取消し可能なFutureを実行済みに数える誤りを
        検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "worker-interrupted-results"

            def interrupt_first_game(schedule, position, config):
                if schedule.game_id == "game-000001":
                    return self._result(
                        schedule, position, config, GameEndReason.INTERRUPTED
                    )
                return self._result(schedule, position, config, GameEndReason.PLY_LIMIT)

            exit_code, stderr, _, _, _ = self._run_controlled_parallel(
                positions,
                output_dir,
                pairs_per_position=2,
                workers=2,
                runner=interrupt_first_game,
            )
            summary = json.loads((output_dir / "summary.json").read_bytes())
            saved_games = sorted(path.name for path in output_dir.glob("game-*.json"))

        self.assertEqual(exit_code, 130)
        self.assertIn("中断", stderr)
        self.assertEqual(saved_games, ["game-000001.json"])
        self.assertEqual(summary["status"], "interrupted")
        self.assertEqual(summary["started_games"], 1)
        self.assertEqual(summary["ended_games"], 1)
        self.assertEqual(summary["in_flight_games"], 0)
        self.assertEqual(summary["unstarted_games"], 3)

    def test_parent_keyboard_interrupt_drains_running_future_and_saves_summary(self):
        """親Ctrl-C後は実行中局を回収し、中断summaryを保存して130で終わる。

        親割込みを例外で漏らしたり、結果を回収せずにworkerを待ちっぱなしにする誤りを
        検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "parent-interrupted-results"

            try:
                exit_code, stderr, executor, _, _ = self._run_controlled_parallel(
                    positions,
                    output_dir,
                    pairs_per_position=2,
                    workers=2,
                    interrupt_first_wait=True,
                    running_game_ids={"game-000001"},
                )
            except KeyboardInterrupt as error:
                self.fail(f"親Ctrl-Cを中断summaryへ変換できません: {error}")

            summary = json.loads((output_dir / "summary.json").read_bytes())
            saved_games = sorted(path.name for path in output_dir.glob("game-*.json"))

        self.assertEqual(exit_code, 130)
        self.assertIn("中断", stderr)
        self.assertEqual(saved_games, ["game-000001.json"])
        self.assertEqual(summary["status"], "interrupted")
        self.assertEqual(summary["started_games"], 1)
        self.assertEqual(summary["ended_games"], 1)
        self.assertEqual(summary["in_flight_games"], 0)
        self.assertEqual(summary["unstarted_games"], 3)
        self.assertEqual(
            {
                key: executor.summary_writes[0][key]
                for key in (
                    "status",
                    "started_games",
                    "ended_games",
                    "in_flight_games",
                    "unstarted_games",
                )
            },
            {
                "status": "interrupted",
                "started_games": 1,
                "ended_games": 0,
                "in_flight_games": 1,
                "unstarted_games": 3,
            },
        )

    def test_parent_keyboard_interrupt_during_initial_submission_saves_summary(self):
        """初回Future投入中の親Ctrl-Cを中断summaryへ記録する。

        waitへ入る前のKeyboardInterruptがexecutor外へ漏れ、conditionsだけを残す誤りを
        検出する。投入されなかった全局は未開始として独立件数に反映する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "submit-interrupted-results"

            try:
                exit_code, stderr, executor, _, _ = self._run_controlled_parallel(
                    positions,
                    output_dir,
                    pairs_per_position=2,
                    workers=2,
                    interrupt_submit_number=1,
                )
            except KeyboardInterrupt as error:
                self.fail(f"初回投入時の親Ctrl-CがCLI外へ漏れました: {error}")

            summary = json.loads((output_dir / "summary.json").read_bytes())
            saved_games = list(output_dir.glob("game-*.json"))

        self.assertEqual(exit_code, 130)
        self.assertIn("中断", stderr)
        self.assertTrue(executor.exited)
        self.assertEqual(saved_games, [])
        self.assertEqual(summary["status"], "interrupted")
        self.assertEqual(summary["planned_games"], 4)
        self.assertEqual(summary["started_games"], 0)
        self.assertEqual(summary["ended_games"], 0)
        self.assertEqual(summary["in_flight_games"], 0)
        self.assertEqual(summary["unstarted_games"], 4)

    def test_parent_sigint_after_submit_side_effect_tracks_and_drains_future(self):
        """submit後・Future登録前のSIGINTでも投入済み局を追跡して保存する。

        submitの副作用後にFutureをpendingへ登録する前に割り込まれ、局結果を失って
        summary上で未開始へ誤算入する境界を検出する。二件目の投入で、先行Futureも
        残る状況を含める。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "submit-side-effect-interrupted-results"
            original_sigint_handler = signal.getsignal(signal.SIGINT)

            exit_code, stderr, executor, _, _ = self._run_controlled_parallel(
                positions,
                output_dir,
                pairs_per_position=2,
                workers=2,
                interrupt_during_submit_number=2,
                running_game_ids={"game-000001", "game-000002"},
            )

            summary = json.loads((output_dir / "summary.json").read_bytes())
            saved_games = sorted(path.name for path in output_dir.glob("game-*.json"))

        self.assertEqual(exit_code, 130)
        self.assertIn("中断", stderr)
        self.assertTrue(executor.exited)
        self.assertIs(signal.getsignal(signal.SIGINT), original_sigint_handler)
        self.assertEqual(saved_games, ["game-000001.json", "game-000002.json"])
        self.assertEqual(summary["status"], "interrupted")
        self.assertEqual(summary["started_games"], 2)
        self.assertEqual(summary["ended_games"], 2)
        self.assertEqual(summary["in_flight_games"], 0)
        self.assertEqual(summary["unstarted_games"], 2)

    def test_parallel_submit_failure_is_saved_as_error_and_stops_submissions(self):
        """ProcessPoolExecutor.submit失敗を局のERROR結果へ記録し後続投入を止める。

        submitがFutureを返す前にBrokenProcessPoolを送出した際、例外をCLI外へ漏らす、
        成功扱いする、または後続予定まで投入する誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "submit-failed-results"

            try:
                exit_code, stderr, executor, _, _ = self._run_controlled_parallel(
                    positions,
                    output_dir,
                    pairs_per_position=2,
                    workers=2,
                    submit_exception_number=2,
                    running_game_ids={"game-000001"},
                )
            except Exception as error:
                self.fail(f"submit失敗をERROR結果に変換できません: {error!r}")

            summary = json.loads((output_dir / "summary.json").read_bytes())
            failed_game = json.loads((output_dir / "game-000002.json").read_bytes())

        self.assertEqual(exit_code, 1)
        self.assertIn("BrokenProcessPool", stderr)
        self.assertTrue(executor.exited)
        self.assertEqual(executor.max_pending, 1)
        self.assertEqual(executor.submit_calls, 2)
        self.assertEqual(failed_game["reason"], "error")
        self.assertIn("injected submit failure", failed_game["error"])
        self.assertEqual(summary["status"], "error")
        self.assertEqual(summary["started_games"], 2)
        self.assertEqual(summary["ended_games"], 2)
        self.assertEqual(summary["in_flight_games"], 0)
        self.assertEqual(summary["unstarted_games"], 2)

    def test_parallel_game_and_summary_save_failures_reap_workers_without_success(self):
        """並列成果物保存失敗は後続投入を止め、worker回収後に1で返る。

        保存失敗後に成功を表示したり、executorを回収せず終了する誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            for failed_name in ("game-000001.json", "summary.json"):
                with self.subTest(failed_name=failed_name):
                    output_dir = (
                        Path(directory) / f"parallel-save-failure-{failed_name}"
                    )
                    exit_code, stderr, executor, completion_order, _ = (
                        self._run_controlled_parallel(
                            positions,
                            output_dir,
                            pairs_per_position=2,
                            workers=2,
                            writer_failure_name=failed_name,
                            running_game_ids={"game-000002"},
                        )
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(executor.stdout, "")
                    self.assertIn(failed_name, stderr)
                    self.assertTrue(executor.exited)
                    self.assertEqual(executor.max_pending, 2)
                    self.assertEqual(completion_order, ["game-000001", "game-000002"])
                    self.assertFalse((output_dir / "game-000002.json").exists())

    def test_parent_keyboard_interrupt_during_parallel_game_save_preserves_game(self):
        """局JSON保存中の親Ctrl-Cでも確定した局を保存して他局を回収する。

        保存中の割込みが完了済みFutureを失わせ、局別JSONと中断summaryの双方を欠く
        誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "game-save-interrupted-results"

            try:
                exit_code, stderr, executor, _, _ = self._run_controlled_parallel(
                    positions,
                    output_dir,
                    pairs_per_position=2,
                    workers=2,
                    interrupt_writer_name="game-000001.json",
                    running_game_ids={"game-000002"},
                )
            except KeyboardInterrupt as error:
                self.fail(f"局JSON保存中の親Ctrl-CがCLI外へ漏れました: {error}")

            summary = json.loads((output_dir / "summary.json").read_bytes())
            saved_games = sorted(path.name for path in output_dir.glob("game-*.json"))
            first_game = json.loads((output_dir / "game-000001.json").read_bytes())

        self.assertEqual(exit_code, 130)
        self.assertIn("中断", stderr)
        self.assertTrue(executor.exited)
        self.assertEqual(saved_games, ["game-000001.json", "game-000002.json"])
        self.assertEqual(first_game["reason"], "ply_limit")
        self.assertEqual(summary["status"], "interrupted")
        self.assertEqual(summary["started_games"], 2)
        self.assertEqual(summary["ended_games"], 2)
        self.assertEqual(summary["in_flight_games"], 0)
        self.assertEqual(summary["unstarted_games"], 2)

    def test_parent_keyboard_interrupt_during_parallel_summary_save_finishes_summary(
        self,
    ):
        """summary保存中の親Ctrl-C後にworkerを回収し最終summaryを残す。

        局JSON保存後のsummary書込割込みがCLI外へ漏れ、完了局の集計を失う誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            output_dir = Path(directory) / "summary-save-interrupted-results"

            try:
                exit_code, stderr, executor, _, _ = self._run_controlled_parallel(
                    positions,
                    output_dir,
                    pairs_per_position=2,
                    workers=2,
                    interrupt_writer_name="summary.json",
                    running_game_ids={"game-000002"},
                )
            except KeyboardInterrupt as error:
                self.fail(f"summary保存中の親Ctrl-CがCLI外へ漏れました: {error}")

            summary = json.loads((output_dir / "summary.json").read_bytes())
            saved_games = sorted(path.name for path in output_dir.glob("game-*.json"))

        self.assertEqual(exit_code, 130)
        self.assertIn("中断", stderr)
        self.assertTrue(executor.exited)
        self.assertEqual(saved_games, ["game-000001.json", "game-000002.json"])
        self.assertEqual(summary["status"], "interrupted")
        self.assertEqual(summary["started_games"], 2)
        self.assertEqual(summary["ended_games"], 2)
        self.assertEqual(summary["in_flight_games"], 0)
        self.assertEqual(summary["unstarted_games"], 2)

    def test_seed_and_seed_list_must_be_selected_exclusively_before_games(self):
        """種方式の両指定・未指定を出力作成と対局前に拒否する。"""
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            seed_list = self._seed_list_file(directory, positions)
            for index, include_seed in enumerate((True, False)):
                with self.subTest(include_seed=include_seed):
                    output_dir = Path(directory) / f"invalid-seed-mode-{index}"
                    args = self._args(
                        positions,
                        output_dir,
                        **{
                            "--candidate": "material-rook-mobility",
                            "--seed-list": str(seed_list),
                        },
                    )
                    if not include_seed:
                        args.remove("--seed")
                        args.remove("17")
                        args.remove("--seed-list")
                        args.remove(str(seed_list))
                    with patch.object(compare_games_module, "run_game") as runner:
                        exit_code, _, stderr = self._capture(args)

                    self.assertEqual(exit_code, 2)
                    self.assertIn("入力エラー", stderr)
                    self.assertFalse(output_dir.exists())
                    runner.assert_not_called()

    def test_incomplete_seed_list_rejects_the_batch_before_output_or_games(self):
        """最後の組が欠ける一覧を全対局開始前に拒否する。"""
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions = self._positions_file(directory)
            seed_list = self._seed_list_file(directory, positions)
            payload = json.loads(seed_list.read_text(encoding="utf-8"))
            payload["pairs"] = []
            seed_list.write_text(json.dumps(payload), encoding="utf-8")
            output_dir = Path(directory) / "invalid-incomplete-list"
            args = self._args(
                positions,
                output_dir,
                **{
                    "--candidate": "material-rook-mobility",
                    "--seed-list": str(seed_list),
                },
            )
            args.remove("--seed")
            args.remove("17")

            with patch.object(compare_games_module, "run_game") as runner:
                exit_code, _, stderr = self._capture(args)

            self.assertEqual(exit_code, 2)
            self.assertIn("入力エラー", stderr)
            self.assertFalse(output_dir.exists())
            runner.assert_not_called()

    def test_real_process_runs_b1_from_seed_list_and_rejects_reuse_of_output(self):
        """実CLIがB1の一覧予定を保存し、既存結果先への再実行を拒否する。

        実プロセスの引数接続・conditions v2・二局一組の種・棋譜・summary保存を検査し、
        同じ保存先を再利用して前実験を上書きする誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._positions_file(directory)
            seed_list_path = self._seed_list_file(directory, positions_path)
            output_dir = Path(directory) / "results"
            args = self._args(
                positions_path,
                output_dir,
                **{
                    "--candidate": "material-rook-mobility",
                    "--seed-list": str(seed_list_path),
                },
            )
            args.remove("--seed")
            args.remove("17")
            command = [sys.executable, "-m", "kaname_shogi.compare_games", *args]
            source_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                command,
                cwd=source_root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            conditions_bytes = (output_dir / "conditions.json").read_bytes()
            conditions = json.loads(conditions_bytes)
            self.assertEqual(
                conditions["format"], "kaname-shogi-comparison-conditions-v2"
            )
            self.assertIsNone(conditions["seed"])
            self.assertEqual(
                conditions["policy_parameters"]["candidate"],
                {"material": 10, "mobility": 1, "mate_priority": True},
            )
            self.assertEqual(
                conditions["randomization"]["seed_list_sha256"],
                hashlib.sha256(seed_list_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                [
                    (game["baseline_seed"], game["candidate_seed"])
                    for game in conditions["schedule"]
                ],
                [(11, 12), (11, 12)],
            )
            conditions_hash = hashlib.sha256(conditions_bytes).hexdigest()
            for game_number in (1, 2):
                game = json.loads(
                    (output_dir / f"game-{game_number:06d}.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(game["candidate"], "material-rook-mobility")
                self.assertEqual(game["conditions_sha256"], conditions_hash)
                self.assertEqual(
                    (game["baseline_seed"], game["candidate_seed"]), (11, 12)
                )
            summary = json.loads((output_dir / "summary.json").read_text())
            self.assertEqual(summary["status"], "complete")
            self.assertEqual(summary["started_games"], 2)
            saved_conditions = (output_dir / "conditions.json").read_bytes()

            repeated = subprocess.run(
                command,
                cwd=source_root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            self.assertEqual(repeated.returncode, 2)
            self.assertIn("入力エラー", repeated.stderr)
            self.assertEqual(
                (output_dir / "conditions.json").read_bytes(), saved_conditions
            )

    def test_success_saves_conditions_games_then_each_updated_summary(self):
        """条件を先に保存し、各局JSONの後にsummaryを更新して最後に完了する。"""
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._positions_file(directory)
            output_dir = Path(directory) / "results"
            saved = []
            real_writer = compare_games_module.atomic_write_json

            def recording_writer(path, payload):
                saved.append((Path(path).name, payload.copy()))
                real_writer(path, payload)

            def finish_by_limit(schedule, position, config):
                return self._result(schedule, position, config, GameEndReason.PLY_LIMIT)

            exit_code, stdout, stderr = self._capture(
                self._args(positions_path, output_dir),
                atomic_writer=recording_writer,
                runner=finish_by_limit,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr, "")
            self.assertEqual(
                [name for name, _ in saved],
                [
                    "conditions.json",
                    "game-000001.json",
                    "summary.json",
                    "game-000002.json",
                    "summary.json",
                ],
            )
            self.assertEqual(saved[2][1]["status"], "running")
            self.assertEqual(saved[2][1]["started_games"], 1)
            self.assertEqual(saved[2][1]["unstarted_games"], 1)
            self.assertEqual(saved[4][1]["status"], "complete")
            self.assertEqual(saved[4][1]["started_games"], 2)

            conditions_bytes = (output_dir / "conditions.json").read_bytes()
            conditions_hash = hashlib.sha256(conditions_bytes).hexdigest()
            for game_number in (1, 2):
                payload = json.loads(
                    (output_dir / f"game-{game_number:06d}.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(payload["conditions_sha256"], conditions_hash)
            self.assertEqual(
                json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))[
                    "status"
                ],
                "complete",
            )
            self.assertIn("統計的な強さ判定は未実施", stdout)
            self.assertIn("時計制御なし", stdout)
            self.assertIn("再戦しません", stdout)

    def test_b1_candidate_runs_and_is_recorded_by_the_comparison_cli(self):
        """比較CLIからB1を選び、条件・実際の手計時・集計へ記録する。

        CLI名だけの登録で選択器へ渡らない、またはB1の実行を既存五方式として保存する
        接続不良を、二局の実対局における独立した方式名で検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._positions_file(directory)
            output_dir = Path(directory) / "b1-results"
            argv = self._args(
                positions_path,
                output_dir,
                **{
                    "--candidate": "material-rook-mobility",
                    "--max-plies": "2",
                },
            )

            exit_code, _, stderr = self._capture(argv)

            self.assertEqual(exit_code, 0, stderr)
            conditions = json.loads(
                (output_dir / "conditions.json").read_text(encoding="utf-8")
            )
            game = json.loads(
                (output_dir / "game-000001.json").read_text(encoding="utf-8")
            )
            summary = json.loads(
                (output_dir / "summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(conditions["candidate"], "material-rook-mobility")
            self.assertEqual(
                [timing["policy"] for timing in game["move_times"]],
                ["material", "material-rook-mobility"],
            )
            self.assertIn("material-rook-mobility", summary["move_time_by_policy"])

    def test_repetition_is_recorded_once_without_automatic_rematch(self):
        """通常千日手を一局の結果として一度記録し、自動再戦しない。"""
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._positions_file(directory)
            output_dir = Path(directory) / "results"
            calls = []

            def end_by_repetition(schedule, position, config):
                calls.append(schedule.game_id)
                return self._result(
                    schedule, position, config, GameEndReason.REPETITION
                )

            exit_code, _, _ = self._capture(
                self._args(positions_path, output_dir), runner=end_by_repetition
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(calls, ["game-000001", "game-000002"])
            summary = json.loads((output_dir / "summary.json").read_text())
            self.assertEqual(summary["results"]["repetition"], 2)
            self.assertEqual(summary["results"]["unresolved_double_perpetual_check"], 0)

    def test_game_error_is_saved_then_stops_remaining_schedule(self):
        """対局故障は局・summaryへ保存した後、後続局を開始せず1で終える。"""
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._positions_file(directory)
            output_dir = Path(directory) / "results"
            calls = []

            def fail_game(schedule, position, config):
                calls.append(schedule.game_id)
                return self._result(
                    schedule,
                    position,
                    config,
                    GameEndReason.ERROR,
                    error="search failed",
                )

            exit_code, stdout, stderr = self._capture(
                self._args(positions_path, output_dir), runner=fail_game
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout, "")
            self.assertIn("search failed", stderr)
            self.assertEqual(calls, ["game-000001"])
            self.assertTrue((output_dir / "game-000001.json").exists())
            self.assertFalse((output_dir / "game-000002.json").exists())
            summary = json.loads((output_dir / "summary.json").read_text())
            self.assertEqual(summary["status"], "error")
            self.assertEqual(summary["results"]["error"], 1)
            self.assertEqual(summary["unstarted_games"], 1)

    def test_runner_exception_becomes_saved_error_and_stops_later_games(self):
        """一局操作の予期しない例外を診断付き故障結果として保存する。"""
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._positions_file(directory)
            output_dir = Path(directory) / "results"
            calls = []

            def raise_from_game(schedule, position, config):
                calls.append(schedule.game_id)
                raise RuntimeError("engine crash")

            exit_code, stdout, stderr = self._capture(
                self._args(positions_path, output_dir), runner=raise_from_game
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout, "")
            self.assertIn("RuntimeError: engine crash", stderr)
            self.assertEqual(calls, ["game-000001"])
            game = json.loads(
                (output_dir / "game-000001.json").read_text(encoding="utf-8")
            )
            self.assertEqual(game["reason"], "error")
            self.assertEqual(game["error"], "RuntimeError: engine crash")

    def test_keyboard_interrupt_before_first_game_writes_empty_interrupted_summary(
        self,
    ):
        """条件保存直後の割込みは開始局0・未実行全局のsummaryを保存する。"""
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._positions_file(directory)
            output_dir = Path(directory) / "results"
            real_writer = compare_games_module.atomic_write_json
            writes = []

            def interrupt_after_conditions(path, payload):
                real_writer(path, payload)
                writes.append(Path(path).name)
                if Path(path).name == "conditions.json":
                    raise KeyboardInterrupt

            with patch.object(compare_games_module, "run_game") as runner:
                exit_code, _, stderr = self._capture(
                    self._args(positions_path, output_dir),
                    atomic_writer=interrupt_after_conditions,
                )

            self.assertEqual(exit_code, 130)
            self.assertIn("中断", stderr)
            self.assertEqual(writes, ["conditions.json", "summary.json"])
            runner.assert_not_called()
            summary = json.loads((output_dir / "summary.json").read_text())
            self.assertEqual(summary["status"], "interrupted")
            self.assertEqual(summary["started_games"], 0)
            self.assertEqual(summary["unstarted_games"], 2)

    def test_keyboard_interrupt_during_game_persists_confirmed_partial_record(self):
        """一局進行中の割込み結果は確定手を保存し、終了コード130にする。"""
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._positions_file(directory)
            output_dir = Path(directory) / "results"

            def interrupt_game(schedule, position, config):
                return self._result(
                    schedule,
                    position,
                    config,
                    GameEndReason.INTERRUPTED,
                    tokens=("7g7f",),
                )

            exit_code, _, stderr = self._capture(
                self._args(positions_path, output_dir), runner=interrupt_game
            )

            self.assertEqual(exit_code, 130)
            self.assertIn("中断", stderr)
            game = json.loads(
                (output_dir / "game-000001.json").read_text(encoding="utf-8")
            )
            self.assertEqual(game["reason"], "interrupted")
            self.assertEqual(game["plies"], 1)
            self.assertEqual(len(game["record"]["moves"]), 1)
            summary = json.loads((output_dir / "summary.json").read_text())
            self.assertEqual(summary["status"], "interrupted")
            self.assertEqual(summary["results"]["interrupted"], 1)
            self.assertEqual(summary["unstarted_games"], 1)

    def test_keyboard_interrupt_between_games_stops_with_partial_pair(self):
        """一局終了後の次局開始時に割り込まれたら後続局なしで中断記録する。"""
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._positions_file(directory)
            output_dir = Path(directory) / "results"
            calls = []

            def interrupt_second(schedule, position, config):
                calls.append(schedule.game_id)
                if len(calls) == 2:
                    raise KeyboardInterrupt
                return self._result(schedule, position, config, GameEndReason.PLY_LIMIT)

            exit_code, _, stderr = self._capture(
                self._args(positions_path, output_dir), runner=interrupt_second
            )

            self.assertEqual(exit_code, 130)
            self.assertIn("中断", stderr)
            self.assertEqual(calls, ["game-000001", "game-000002"])
            summary = json.loads((output_dir / "summary.json").read_text())
            self.assertEqual(summary["status"], "interrupted")
            self.assertEqual(summary["results"]["ply_limit"], 1)
            self.assertEqual(summary["results"]["interrupted"], 1)
            self.assertEqual(summary["completed_pairs"], 0)
            self.assertEqual(summary["partial_pairs"], 1)
            self.assertEqual(summary["unstarted_games"], 0)

    def test_keyboard_interrupt_while_loading_next_game_saves_partial_summary(self):
        """次局データ取得時の割込みも局間中断として保存する。"""
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._positions_file(directory)
            output_dir = Path(directory) / "results"
            calls = []
            original_make_schedule = compare_games_module.make_schedule

            class InterruptingPositionId(str):
                def __hash__(self):
                    raise KeyboardInterrupt

            def interrupt_on_second_position(config):
                games = list(original_make_schedule(config))
                games[1] = dataclasses.replace(
                    games[1],
                    position_id=InterruptingPositionId(games[1].position_id),
                )
                return tuple(games)

            def finish_by_limit(schedule, position, config):
                calls.append(schedule.game_id)
                return self._result(schedule, position, config, GameEndReason.PLY_LIMIT)

            try:
                with patch.object(
                    compare_games_module,
                    "make_schedule",
                    side_effect=interrupt_on_second_position,
                ):
                    exit_code, _, stderr = self._capture(
                        self._args(positions_path, output_dir), runner=finish_by_limit
                    )
            except KeyboardInterrupt:
                self.fail("次局データ取得時の割込みがCLI外へ漏れました")

            self.assertEqual(exit_code, 130)
            self.assertIn("中断", stderr)
            self.assertEqual(calls, ["game-000001"])
            self.assertTrue((output_dir / "game-000001.json").exists())
            self.assertFalse((output_dir / "game-000002.json").exists())
            summary = json.loads((output_dir / "summary.json").read_text())
            self.assertEqual(summary["status"], "interrupted")
            self.assertEqual(summary["results"]["ply_limit"], 1)
            self.assertEqual(summary["unstarted_games"], 1)

    def test_game_save_and_summary_save_failures_return_one_without_success_text(self):
        """局またはsummaryの保存失敗を成功表示せず1で返す。"""
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._positions_file(directory)
            for failed_name in ("game-000001.json", "summary.json"):
                with self.subTest(failed_name=failed_name):
                    output_dir = Path(directory) / f"results-{failed_name}"
                    real_writer = compare_games_module.atomic_write_json

                    def failing_writer(
                        path,
                        payload,
                        failed_name=failed_name,
                        real_writer=real_writer,
                    ):
                        if Path(path).name == failed_name:
                            raise OSError(f"{failed_name} write failed")
                        real_writer(path, payload)

                    exit_code, stdout, stderr = self._capture(
                        self._args(positions_path, output_dir),
                        atomic_writer=failing_writer,
                        runner=lambda schedule, position, config: self._result(
                            schedule, position, config, GameEndReason.PLY_LIMIT
                        ),
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(stdout, "")
                    self.assertIn(failed_name, stderr)
                    if failed_name == "summary.json":
                        self.assertTrue((output_dir / "game-000001.json").exists())
                        self.assertFalse((output_dir / "summary.json").exists())
                    else:
                        self.assertFalse((output_dir / failed_name).exists())
                        self.assertFalse((output_dir / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
