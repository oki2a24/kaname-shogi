"""比較実験の再開条件・既存結果検証を確認する。"""

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from kaname_shogi import comparison as comparison_module
from kaname_shogi import comparison_io
from kaname_shogi.comparison import (
    ComparisonConfig,
    ComparisonPosition,
    GameEndReason,
    GameResult,
    MoveTiming,
    make_schedule,
)
from kaname_shogi.comparison_io import (
    atomic_write_json,
    conditions_payload,
    game_payload,
)
from kaname_shogi.game_record import GameRecord
from kaname_shogi.model import create_initial_position
from kaname_shogi.movegen import MoveSelectionPolicy
from kaname_shogi.usi_move import parse_usi_move

try:
    from kaname_shogi import comparison_resume as comparison_resume_module
except ModuleNotFoundError as error:
    if error.name != "kaname_shogi.comparison_resume":
        raise
    load_resume_state = None
    run_lock = None
else:
    load_resume_state = getattr(comparison_resume_module, "load_resume_state", None)
    run_lock = getattr(comparison_resume_module, "run_lock", None)


class ComparisonResumeConditionTests(unittest.TestCase):
    """保存条件の同一性契約を検証する。"""

    def _require_implementation(self):
        self.assertIsNotNone(load_resume_state, "比較再開の検証が未実装です")

    def test_run_lock_excludes_other_processes_and_releases_its_own_file(self):
        """同じ出力先の同時実行を拒否し正常終了後はロックを解放する。

        複数プロセスが同じ局を投入し結果を二重保存する誤りを検出する。
        """
        self.assertIsNotNone(run_lock, "比較実行ロックが未実装です")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with run_lock(root):
                lock_path = root / ".comparison.lock"
                self.assertTrue(lock_path.is_file())
                with self.assertRaisesRegex(ValueError, "使用中"):
                    with run_lock(root):
                        pass
            self.assertFalse((root / ".comparison.lock").exists())

    def test_run_lock_refuses_stale_lock_without_removing_it(self):
        """残存ロックを自動解除せず、確認を促して停止する。

        前プロセスがまだ動作中なのに古いと決め付けて二重実行する誤りを検出する。
        """
        self.assertIsNotNone(run_lock, "比較実行ロックが未実装です")
        with tempfile.TemporaryDirectory() as directory:
            lock_path = Path(directory) / ".comparison.lock"
            lock_path.write_text("stale", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "確認"):
                with run_lock(Path(directory)):
                    pass
            self.assertEqual(lock_path.read_text(encoding="utf-8"), "stale")

    def test_run_lock_releases_after_runtime_exception(self):
        """実行中の例外でも自プロセスのロックを解放する。

        例外後に通常の再開操作が永久にロックされたままになる誤りを検出する。
        """
        self.assertIsNotNone(run_lock, "比較実行ロックが未実装です")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "実行失敗"):
                with run_lock(root):
                    raise RuntimeError("実行失敗")
            self.assertFalse((root / ".comparison.lock").exists())

    def test_run_lock_removes_its_partial_file_when_initial_write_fails(self):
        """ロック初期書込みの途中失敗では自分が作った部分ファイルを除去する。

        トークンが完全一致しないだけで通常の書込み故障ロックを残す誤りを検出する。
        """
        self.assertIsNotNone(run_lock, "比較実行ロックが未実装です")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock_path = root / ".comparison.lock"
            real_fdopen = comparison_resume_module.os.fdopen

            class PartialLockFile:
                def __init__(self, descriptor):
                    self.file = real_fdopen(descriptor, "w", encoding="ascii")

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, traceback):
                    self.file.close()
                    return False

                def write(self, value):
                    self.file.write(value[:3])
                    raise OSError("注入したロック書込み失敗")

                def flush(self):
                    self.file.flush()

                def fileno(self):
                    return self.file.fileno()

            with (
                patch.object(
                    comparison_resume_module.os,
                    "fdopen",
                    side_effect=lambda descriptor, *args, **kwargs: PartialLockFile(
                        descriptor
                    ),
                ),
                self.assertRaisesRegex(OSError, "ロック書込み失敗"),
            ):
                with run_lock(root):
                    self.fail("初期ロック書込み失敗後に本体へ入ってはいけません")

            self.assertFalse(lock_path.exists())

    def _config(self, output_dir, *, pairs_per_position=1):
        position = ComparisonPosition(
            "initial",
            (),
            "平手初期局面",
            create_initial_position(),
            "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
            1,
        )
        return ComparisonConfig(
            baseline=MoveSelectionPolicy.MATERIAL,
            candidate=MoveSelectionPolicy.RANDOM,
            positions=(position,),
            pairs_per_position=pairs_per_position,
            seed=17,
            max_plies=1,
            output_dir=output_dir,
            positions_path=Path("positions.json"),
            positions_json=b'{"fixture": "positions"}',
            workers=2,
            resume=True,
        )

    def _saved_run(self, root):
        output_dir = root / "results"
        output_dir.mkdir()
        config = self._config(output_dir)
        payload = conditions_payload(
            config, make_schedule(config), source_root=Path(__file__).parents[1]
        )
        atomic_write_json(output_dir / "conditions.json", payload)
        return config, payload

    @staticmethod
    def _result(config, scheduled_game, *, incomplete=False):
        position = next(
            position
            for position in config.positions
            if position.position_id == scheduled_game.position_id
        )
        record = GameRecord(position.start_position)
        timings = ()
        if not incomplete:
            move = parse_usi_move("7g7f")
            side = record.current_position.side_to_move
            policy = (
                config.baseline
                if side is scheduled_game.baseline_side
                else config.candidate
            )
            record.apply_move(move.source, move.destination, promote=move.promote)
            timings = (MoveTiming(1, side, policy, move, 15),)
        return GameResult(
            schedule=scheduled_game,
            start_sfen=position.start_sfen,
            initial_move_number=position.initial_move_number,
            record=record,
            reason=(
                GameEndReason.INTERRUPTED if incomplete else GameEndReason.PLY_LIMIT
            ),
            winner_side=None,
            winner_policy=None,
            plies=len(record.moves),
            move_times_ns=timings,
            unfinished_calculation_ns=None,
            error=None,
        )

    def test_accepts_same_conditions_even_when_git_head_metadata_changes(self):
        """保存時と条件・ソースが同じならGit履歴メタデータの変化を許容する。

        文書コミットやdirty状態をコード変更と誤認して再開不能にする挙動を検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, _ = self._saved_run(root)
            conditions_path = config.output_dir / "conditions.json"
            original_conditions_bytes = conditions_path.read_bytes()

            with patch.object(
                comparison_io,
                "_git_metadata",
                return_value={
                    "head": "later-document-commit",
                    "dirty": True,
                    "diagnostic": None,
                },
            ):
                state = load_resume_state(config, source_root=Path(__file__).parents[1])

            self.assertEqual(
                state.conditions_sha256,
                __import__("hashlib").sha256(original_conditions_bytes).hexdigest(),
            )
            self.assertEqual(conditions_path.read_bytes(), original_conditions_bytes)
            self.assertEqual(state.completed_results, ())
            self.assertEqual(state.pending_schedule, make_schedule(config))

    def test_restores_completed_games_and_schedules_only_missing_or_interrupted(self):
        """完成2局を保持し、中断1局と欠落1局だけを再開対象にする。

        予定全局の再投入や、先頭からの作り直しで確定棋譜を上書きする誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "results"
            output.mkdir()
            config = self._config(output, pairs_per_position=2)
            schedule = make_schedule(config)
            conditions = conditions_payload(
                config, schedule, source_root=Path(__file__).parents[1]
            )
            atomic_write_json(output / "conditions.json", conditions)
            conditions_hash = hashlib.sha256(
                (output / "conditions.json").read_bytes()
            ).hexdigest()
            completed_ids = {schedule[0].game_id, schedule[2].game_id}
            original_bytes = {}
            for index in (0, 1, 2):
                result = self._result(config, schedule[index], incomplete=(index == 1))
                game_path = output / f"{schedule[index].game_id}.json"
                atomic_write_json(
                    game_path,
                    game_payload(result, config, conditions_sha256=conditions_hash),
                )
                if index in (0, 2):
                    original_bytes[game_path.name] = game_path.read_bytes()

            state = load_resume_state(config, source_root=Path(__file__).parents[1])

            self.assertEqual(
                {result.schedule.game_id for result in state.completed_results},
                completed_ids,
            )
            self.assertEqual(
                tuple(game.game_id for game in state.pending_schedule),
                (schedule[1].game_id, schedule[3].game_id),
            )
            self.assertEqual(
                {name: (output / name).read_bytes() for name in original_bytes},
                original_bytes,
            )

    def test_rejects_corrupt_and_unexpected_game_artifacts(self):
        """条件不一致の局JSONや予定外IDを再開対象へ混ぜない。

        不正な成果物を欠落局と同様に扱って捨てる誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, _ = self._saved_run(root)
            schedule = make_schedule(config)
            game_path = config.output_dir / f"{schedule[0].game_id}.json"
            conditions_hash = hashlib.sha256(
                (config.output_dir / "conditions.json").read_bytes()
            ).hexdigest()
            valid_payload = game_payload(
                self._result(config, schedule[0]),
                config,
                conditions_sha256=conditions_hash,
            )
            invalid_payloads = []
            wrong_hash = dict(valid_payload)
            wrong_hash["conditions_sha256"] = "0" * 64
            invalid_payloads.append(wrong_hash)
            illegal_move = json.loads(json.dumps(valid_payload))
            illegal_move["move_times"][0]["move"] = "9z9z"
            invalid_payloads.append(illegal_move)
            wrong_terminal = dict(valid_payload)
            wrong_terminal["reason"] = "repetition"
            invalid_payloads.append(wrong_terminal)
            for payload in invalid_payloads:
                with self.subTest(payload=payload):
                    atomic_write_json(game_path, payload)
                    with self.assertRaises(ValueError):
                        load_resume_state(config, source_root=Path(__file__).parents[1])
                    game_path.unlink()

            (config.output_dir / "game-unexpected.json").write_text(
                "{}", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "予定"):
                load_resume_state(config, source_root=Path(__file__).parents[1])

    def test_rebuilds_missing_or_old_summary_from_game_files(self):
        """summary欠落・古い値でも保存局から安全に再開時間を復元する。

        summaryがないため再開不能にする、または古い局件数を正本にする誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, _ = self._saved_run(root)
            state = load_resume_state(config, source_root=Path(__file__).parents[1])
            self.assertEqual(state.elapsed_ns, 0)

            atomic_write_json(config.output_dir / "summary.json", {"elapsed_ns": 23})
            state = load_resume_state(config, source_root=Path(__file__).parents[1])
            self.assertEqual(state.elapsed_ns, 23)
            self.assertEqual(state.completed_results, ())

    def test_retries_a_valid_error_result(self):
        """条件一致で記録された故障局だけを未完了として再実行する。

        ERROR結果を完成局として保持し、故障した比較を分析可能と誤認する挙動を検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "results"
            output.mkdir()
            config = self._config(output)
            schedule = make_schedule(config)
            conditions = conditions_payload(
                config, schedule, source_root=Path(__file__).parents[1]
            )
            atomic_write_json(output / "conditions.json", conditions)
            conditions_hash = hashlib.sha256(
                (output / "conditions.json").read_bytes()
            ).hexdigest()
            error_result = replace(
                self._result(config, schedule[0], incomplete=True),
                reason=GameEndReason.ERROR,
                error="注入した失敗",
            )
            atomic_write_json(
                output / f"{schedule[0].game_id}.json",
                game_payload(error_result, config, conditions_sha256=conditions_hash),
            )

            state = load_resume_state(config, source_root=Path(__file__).parents[1])

            self.assertEqual(state.completed_results, ())
            self.assertEqual(state.pending_schedule, schedule)

    def test_accepts_negative_unfinished_duration_from_clock_reversal_error(self):
        """時計逆行の故障局を診断付き未完了として再開対象にする。

        run_gameが異常な単調時計差を負の未確定時間として記録する契約を、readerが
        一律の負値拒否で再開不能にする誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, _ = self._saved_run(root)
            scheduled = make_schedule(config)[0]
            readings = iter((10, 0))
            with patch.object(
                comparison_module.game_search,
                "choose_move",
                return_value=parse_usi_move("7g7f"),
            ):
                result = comparison_module.run_game(
                    scheduled,
                    config.positions[0],
                    config,
                    clock_ns=lambda: next(readings),
                )
            self.assertEqual(result.reason, GameEndReason.ERROR)
            self.assertEqual(result.unfinished_calculation_ns, -10)

            conditions_hash = hashlib.sha256(
                (config.output_dir / "conditions.json").read_bytes()
            ).hexdigest()
            atomic_write_json(
                config.output_dir / f"{scheduled.game_id}.json",
                game_payload(result, config, conditions_sha256=conditions_hash),
            )

            state = load_resume_state(config, source_root=Path(__file__).parents[1])

        self.assertEqual(state.pending_schedule, make_schedule(config))

    def test_rejects_each_changed_experiment_condition_and_source(self):
        """方式・seed・局面・上限・worker・環境・コード差をそれぞれ拒否する。

        条件の一部だけを比較して異なる実験を同じ出力先へ混ぜる挙動を検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, _ = self._saved_run(root)
            changed_configs = (
                replace(config, candidate=MoveSelectionPolicy.TWO_PLY_MATERIAL),
                replace(config, seed=18),
                replace(config, positions_json=b'{"fixture": "changed"}'),
                replace(config, max_plies=13),
                replace(config, workers=3),
            )
            for changed in changed_configs:
                with self.subTest(changed=changed):
                    with self.assertRaisesRegex(ValueError, "条件"):
                        load_resume_state(
                            changed, source_root=Path(__file__).parents[1]
                        )

            with patch(
                "kaname_shogi.comparison_io.platform.platform",
                return_value="different-platform",
            ):
                with self.assertRaisesRegex(ValueError, "条件"):
                    load_resume_state(config, source_root=Path(__file__).parents[1])

            with patch(
                "kaname_shogi.comparison_io._source_sha256",
                return_value="0" * 64,
            ):
                with self.assertRaisesRegex(ValueError, "ソース"):
                    load_resume_state(config, source_root=Path(__file__).parents[1])
