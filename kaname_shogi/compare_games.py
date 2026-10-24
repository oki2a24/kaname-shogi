"""比較対局を実行する専用コマンドライン入口を提供する。"""

from __future__ import annotations

import hashlib
import signal
import sys
import time
from collections.abc import Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from multiprocessing import get_context
from pathlib import Path

from .comparison import (
    BatchStatus,
    ComparisonConfig,
    ComparisonPosition,
    GameEndReason,
    GameResult,
    ScheduledGame,
    make_schedule,
    run_game,
    summarize,
)
from .comparison_io import (
    _json_bytes,
    _make_parser,
    atomic_write_json,
    conditions_payload,
    game_payload,
    load_config,
    summary_payload,
)
from .comparison_resume import load_resume_state, run_lock
from .game_record import GameRecord


def main(argv: Sequence[str] | None = None) -> int:
    """比較条件を検証し、逐次または並列対局と局別保存を実行する。

    引数:
        argv: CLI引数列。Noneならプロセスのコマンドラインを使う。

    戻り値:
        全局成功・保存成功は0、故障・保存失敗は1、入力不正は2、Ctrl-Cは130。

    副作用:
        help以外では全入力を先に検証し、通常実行では新規出力先を作成してconditions.jsonを
        一度保存する。再開では既存条件・局JSONを照合してから未完了局を実行する。各確定局JSONの後に
        summary.jsonを原子的に更新する。標準出力と標準エラーへ短い日本語表示を行う。

    前提条件:
        通常CLI・USIの入口や設定は変更しない。workers=1は予定順に逐次実行し、
        複数workerはspawn process poolを使う。--resumeは同じ条件とソース指紋を要求し、
        完了局を保持して欠落・中断・故障局だけを開始局面から再実行する。通常千日手の再戦、
        自動再試行、棋力の統計判定を行わない。
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if any(argument in {"-h", "--help"} for argument in arguments):
        parser = _make_parser(add_help=True)
        parser.prog = "python -m kaname_shogi.compare_games"
        parser.description = "既存の一手選択方式を指定局面で記述比較します。"
        parser.print_help()
        return 0

    try:
        config = load_config(arguments)
    except (OSError, ValueError) as error:
        print(f"入力エラー: {error}", file=sys.stderr)
        return 2

    try:
        schedule = make_schedule(config)
        source_root = Path(__file__).resolve().parents[1]
        conditions = (
            None
            if config.resume
            else conditions_payload(config, schedule, source_root=source_root)
        )
    except Exception as error:
        print(
            f"条件JSONを作成できません: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1

    if not config.resume:
        try:
            config.output_dir.mkdir()
        except OSError as error:
            print(f"出力先を作成できません: {error}", file=sys.stderr)
            return 1

    try:
        with run_lock(config.output_dir):
            started_at_ns = time.monotonic_ns()
            if config.resume:
                state = load_resume_state(config, source_root=source_root)
                conditions_hash = state.conditions_sha256
                initial_results = state.completed_results
                started_at_ns -= state.elapsed_ns
            else:
                assert conditions is not None
                conditions_hash = hashlib.sha256(_json_bytes(conditions)).hexdigest()
                try:
                    atomic_write_json(config.output_dir / "conditions.json", conditions)
                except KeyboardInterrupt:
                    return _finish_interrupted_before_games(
                        config, schedule, started_at_ns
                    )
                except Exception as error:
                    print(
                        f"条件JSONを保存できません: {type(error).__name__}: {error}",
                        file=sys.stderr,
                    )
                    return 1
                initial_results = ()
            return _run_scheduled_games(
                config,
                schedule,
                conditions_hash=conditions_hash,
                started_at_ns=started_at_ns,
                initial_results=initial_results,
            )
    except (OSError, ValueError) as error:
        print(f"入力エラー: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("比較を中断しました。", file=sys.stderr)
        return 130
    except Exception as error:
        print(
            f"比較を実行できません: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1


def _run_scheduled_games(
    config: ComparisonConfig,
    schedule: Sequence[ScheduledGame],
    *,
    conditions_hash: str,
    started_at_ns: int,
    initial_results: Sequence[GameResult],
) -> int:
    """検証済みの保存局を含め、未完了予定だけを逐次または並列実行する。"""
    positions_by_id = {position.position_id: position for position in config.positions}
    initial_by_id = {result.schedule.game_id: result for result in initial_results}
    results = [
        initial_by_id[game.game_id]
        for game in schedule
        if game.game_id in initial_by_id
    ]
    if len(results) == len(schedule):
        try:
            _save_summary(
                config, schedule, results, BatchStatus.COMPLETE, started_at_ns
            )
        except KeyboardInterrupt:
            return _save_interrupted_summary(config, schedule, results, started_at_ns)
        except Exception as error:
            print(
                f"summary.jsonを保存できません: {type(error).__name__}: {error}",
                file=sys.stderr,
            )
            return 1
        _print_completion(config, schedule, results)
        return 0

    if config.workers > 1:
        return _run_parallel_games(
            config,
            schedule,
            positions_by_id,
            conditions_hash=conditions_hash,
            started_at_ns=started_at_ns,
            initial_results=results,
        )

    completed_ids = {result.schedule.game_id for result in results}
    try:
        for game in schedule:
            if game.game_id in completed_ids:
                continue
            position = positions_by_id[game.position_id]
            try:
                game_result = run_game(game, position, config)
            except KeyboardInterrupt:
                game_result = _empty_result(game, position, GameEndReason.INTERRUPTED)
            except Exception as error:
                game_result = _empty_result(
                    game,
                    position,
                    GameEndReason.ERROR,
                    error=f"{type(error).__name__}: {error}",
                )

            game_path = config.output_dir / f"{game.game_id}.json"
            interrupted_during_payload = False
            try:
                payload = game_payload(
                    game_result,
                    config,
                    conditions_sha256=conditions_hash,
                )
            except KeyboardInterrupt:
                interrupted_during_payload = True
                try:
                    payload = game_payload(
                        game_result,
                        config,
                        conditions_sha256=conditions_hash,
                    )
                except KeyboardInterrupt:
                    return _save_interrupted_summary(
                        config, schedule, results, started_at_ns
                    )
                except Exception as error:
                    print(
                        f"局JSONを作成できません ({game.game_id}): "
                        f"{type(error).__name__}: {error}",
                        file=sys.stderr,
                    )
                    return 1

            try:
                atomic_write_json(game_path, payload)
            except KeyboardInterrupt:
                if not _payload_matches_saved_file(game_path, payload):
                    try:
                        atomic_write_json(game_path, payload)
                    except KeyboardInterrupt:
                        if not _payload_matches_saved_file(game_path, payload):
                            return _save_interrupted_summary(
                                config, schedule, results, started_at_ns
                            )
                    except Exception as error:
                        print(
                            f"局JSONを保存できません ({game.game_id}): "
                            f"{type(error).__name__}: {error}",
                            file=sys.stderr,
                        )
                        return 1
                if _payload_matches_saved_file(game_path, payload):
                    results.append(game_result)
                return _save_interrupted_summary(
                    config, schedule, results, started_at_ns
                )
            except Exception as error:
                print(
                    f"局JSONを保存できません ({game.game_id}): "
                    f"{type(error).__name__}: {error}",
                    file=sys.stderr,
                )
                return 1

            results.append(game_result)
            if interrupted_during_payload:
                return _save_interrupted_summary(
                    config, schedule, results, started_at_ns
                )
            status = _status_after_game(game_result, len(results), len(schedule))
            try:
                _save_summary(config, schedule, results, status, started_at_ns)
            except KeyboardInterrupt:
                return _save_interrupted_summary(
                    config, schedule, results, started_at_ns
                )
            except Exception as error:
                print(
                    f"summary.jsonを保存できません: {type(error).__name__}: {error}",
                    file=sys.stderr,
                )
                return 1

            if game_result.reason is GameEndReason.ERROR:
                print(
                    f"対局 {game.game_id} が故障終了しました: {game_result.error}",
                    file=sys.stderr,
                )
                _print_scope_notes(sys.stderr)
                return 1
            if game_result.reason is GameEndReason.INTERRUPTED:
                print(f"対局 {game.game_id} の途中で中断しました。", file=sys.stderr)
                _print_scope_notes(sys.stderr)
                return 130
    except KeyboardInterrupt:
        return _save_interrupted_summary(config, schedule, results, started_at_ns)

    _print_completion(config, schedule, results)
    return 0


def _empty_result(
    schedule: ScheduledGame,
    position: ComparisonPosition,
    reason: GameEndReason,
    *,
    error: str | None = None,
) -> GameResult:
    """一局操作が例外で結果を返せなかった場合の空棋譜結果を作る。"""
    return GameResult(
        schedule=schedule,
        start_sfen=position.start_sfen,
        initial_move_number=position.initial_move_number,
        record=GameRecord(position.start_position),
        reason=reason,
        winner_side=None,
        winner_policy=None,
        plies=0,
        move_times_ns=(),
        unfinished_calculation_ns=None,
        error=error,
    )


def _payload_matches_saved_file(path: Path, payload: dict[str, object]) -> bool:
    """原子的に保存されたJSONが今回のpayloadと一致するか返す。"""
    try:
        return Path(path).read_bytes() == _json_bytes(payload)
    except OSError:
        return False


def _run_game_worker(
    schedule: ScheduledGame,
    position: ComparisonPosition,
    config: ComparisonConfig,
) -> GameResult:
    """spawn子プロセスで一局を実行し、pickle可能な結果だけを返す。"""
    return run_game(schedule, position, config)


def _ignore_worker_sigint() -> None:
    """spawn workerは端末SIGINTを無視し、親が中断後に局結果を回収できるようにする。"""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _run_parallel_games(
    config: ComparisonConfig,
    schedule: Sequence[ScheduledGame],
    positions_by_id: dict[str, ComparisonPosition],
    *,
    conditions_hash: str,
    started_at_ns: int,
    initial_results: Sequence[GameResult] = (),
) -> int:
    """spawn process poolで対局し、条件・結果ファイルを親だけが保存する。"""
    results_by_id = {result.schedule.game_id: result for result in initial_results}
    status = BatchStatus.RUNNING
    parent_interrupted = False
    persistence_error: str | None = None
    with ProcessPoolExecutor(
        max_workers=config.workers,
        mp_context=get_context("spawn"),
        initializer=_ignore_worker_sigint,
    ) as executor:
        pending = {}
        next_schedule_index = 0
        submission_stopped = False

        def submit_next() -> bool:
            nonlocal next_schedule_index, submission_stopped
            if submission_stopped:
                return False
            while (
                next_schedule_index < len(schedule)
                and schedule[next_schedule_index].game_id in results_by_id
            ):
                next_schedule_index += 1
            if next_schedule_index >= len(schedule):
                return False
            game = schedule[next_schedule_index]
            deferred_interrupt = None

            def defer_sigint(signum, frame):
                nonlocal deferred_interrupt
                deferred_interrupt = (signum, frame)

            previous_sigint_handler = signal.signal(signal.SIGINT, defer_sigint)
            try:
                try:
                    future = executor.submit(
                        _run_game_worker,
                        game,
                        positions_by_id[game.position_id],
                        config,
                    )
                except KeyboardInterrupt:
                    raise
                except Exception as error:
                    # submitがFutureを返せない局も予定単位でERRORとして回収する。
                    future = Future()
                    future.set_exception(error)
                    submission_stopped = True

                # SIGINTを一時保留し、投入済みFutureを必ず親の対応表へ登録してから
                # 中断処理へ移る。そうしないと局結果を回収できず未開始件数がずれる。
                pending[future] = game
                next_schedule_index += 1
            finally:
                signal.signal(signal.SIGINT, previous_sigint_handler)

            if deferred_interrupt is not None:
                if previous_sigint_handler == signal.SIG_IGN:
                    return True
                if callable(previous_sigint_handler):
                    previous_sigint_handler(*deferred_interrupt)
                else:
                    raise KeyboardInterrupt
            return True

        def stop_after_parent_interrupt() -> None:
            """親割込み後は未開始を取消し、結果回収だけを続ける。"""
            nonlocal parent_interrupted, status
            parent_interrupted = True
            if status is BatchStatus.RUNNING:
                status = BatchStatus.INTERRUPTED
            for pending_future in tuple(pending):
                if pending_future.cancel():
                    pending.pop(pending_future)

        def _process_completed_future(future: Future[GameResult]) -> None:
            nonlocal persistence_error, status
            game = pending[future]
            position = positions_by_id[game.position_id]

            if persistence_error is not None:
                try:
                    future.result()
                except BaseException:
                    pass
                pending.pop(future, None)
                return

            try:
                game_result = future.result()
            except KeyboardInterrupt as interrupt:
                try:
                    worker_exception = future.exception()
                except KeyboardInterrupt:
                    raise
                if worker_exception is not interrupt:
                    raise
                game_result = _empty_result(game, position, GameEndReason.INTERRUPTED)
            except Exception as error:
                game_result = _empty_result(
                    game,
                    position,
                    GameEndReason.ERROR,
                    error=f"{type(error).__name__}: {error}",
                )

            game_path = config.output_dir / f"{game.game_id}.json"
            payload = game_payload(
                game_result,
                config,
                conditions_sha256=conditions_hash,
            )
            try:
                atomic_write_json(game_path, payload)
            except KeyboardInterrupt:
                stop_after_parent_interrupt()
                if not _payload_matches_saved_file(game_path, payload):
                    try:
                        atomic_write_json(game_path, payload)
                    except KeyboardInterrupt as retry_error:
                        if not _payload_matches_saved_file(game_path, payload):
                            persistence_error = (
                                "局JSON保存中に再度割り込まれました "
                                f"({game.game_id}): "
                                f"{type(retry_error).__name__}: {retry_error}"
                            )
                            status = BatchStatus.ERROR
                    except Exception as retry_error:
                        persistence_error = (
                            f"局JSONを保存できません ({game.game_id}): "
                            f"{type(retry_error).__name__}: {retry_error}"
                        )
                        status = BatchStatus.ERROR
                if persistence_error is None and not _payload_matches_saved_file(
                    game_path, payload
                ):
                    persistence_error = f"局JSONを確認できません ({game.game_id})"
                    status = BatchStatus.ERROR
            except Exception as error:
                persistence_error = (
                    f"局JSONを保存できません ({game.game_id}): "
                    f"{type(error).__name__}: {error}"
                )
                status = BatchStatus.ERROR

            if persistence_error is not None:
                for pending_future in tuple(pending):
                    if pending_future.cancel():
                        pending.pop(pending_future)
                pending.pop(future, None)
                return

            results_by_id[game.game_id] = game_result
            if game_result.reason is GameEndReason.ERROR:
                status = BatchStatus.ERROR
            elif (
                game_result.reason is GameEndReason.INTERRUPTED
                and status is BatchStatus.RUNNING
            ):
                status = BatchStatus.INTERRUPTED
            elif len(results_by_id) == len(schedule) and status is BatchStatus.RUNNING:
                status = BatchStatus.COMPLETE

            if status in {BatchStatus.ERROR, BatchStatus.INTERRUPTED}:
                for pending_future in tuple(pending):
                    if pending_future.cancel():
                        pending.pop(pending_future)

            pending.pop(future, None)
            if parent_interrupted:
                return
            results = [
                results_by_id[item.game_id]
                for item in schedule
                if item.game_id in results_by_id
            ]
            try:
                _save_summary(
                    config,
                    schedule,
                    results,
                    status,
                    started_at_ns,
                    in_flight_games=len(pending),
                )
            except KeyboardInterrupt:
                stop_after_parent_interrupt()
            except Exception as error:
                persistence_error = (
                    f"summary.jsonを保存できません: {type(error).__name__}: {error}"
                )
                status = BatchStatus.ERROR
                for pending_future in tuple(pending):
                    if pending_future.cancel():
                        pending.pop(pending_future)

        try:
            while len(pending) < config.workers and submit_next():
                pass
        except KeyboardInterrupt:
            stop_after_parent_interrupt()

        while pending:
            try:
                completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            except KeyboardInterrupt:
                stop_after_parent_interrupt()
                continue

            for future in completed:
                try:
                    _process_completed_future(future)
                except KeyboardInterrupt:
                    stop_after_parent_interrupt()

            if status is BatchStatus.RUNNING and not parent_interrupted:
                try:
                    while len(pending) < config.workers and submit_next():
                        pass
                except KeyboardInterrupt:
                    stop_after_parent_interrupt()

    if parent_interrupted and persistence_error is None:
        results = [
            results_by_id[item.game_id]
            for item in schedule
            if item.game_id in results_by_id
        ]
        try:
            _save_summary(
                config,
                schedule,
                results,
                status,
                started_at_ns,
                in_flight_games=0,
            )
        except Exception as error:
            persistence_error = (
                f"summary.jsonを保存できません: {type(error).__name__}: {error}"
            )

    if persistence_error is not None:
        print(persistence_error, file=sys.stderr)
        _print_scope_notes(sys.stderr)
        return 1

    results = [
        results_by_id[item.game_id]
        for item in schedule
        if item.game_id in results_by_id
    ]
    error_result = next(
        (result for result in results if result.reason is GameEndReason.ERROR), None
    )
    if error_result is not None:
        print(
            f"対局 {error_result.schedule.game_id} が故障終了しました: "
            f"{error_result.error}",
            file=sys.stderr,
        )
        _print_scope_notes(sys.stderr)
        return 1
    interrupted_result = next(
        (result for result in results if result.reason is GameEndReason.INTERRUPTED),
        None,
    )
    if interrupted_result is not None:
        print(
            f"対局 {interrupted_result.schedule.game_id} の途中で中断しました。",
            file=sys.stderr,
        )
        _print_scope_notes(sys.stderr)
        return 130
    if parent_interrupted:
        print("比較を中断しました。実行中の局は回収して保存しました。", file=sys.stderr)
        _print_scope_notes(sys.stderr)
        return 130
    _print_completion(config, schedule, results)
    return 0


def _status_after_game(
    result: GameResult,
    saved_games: int,
    planned_games: int,
) -> BatchStatus:
    """保存済み局と終局理由から次のsummary状態を返す。"""
    if result.reason is GameEndReason.ERROR:
        return BatchStatus.ERROR
    if result.reason is GameEndReason.INTERRUPTED:
        return BatchStatus.INTERRUPTED
    if saved_games == planned_games:
        return BatchStatus.COMPLETE
    return BatchStatus.RUNNING


def _save_summary(
    config: ComparisonConfig,
    schedule: Sequence[ScheduledGame],
    results: Sequence[GameResult],
    status: BatchStatus,
    started_at_ns: int,
    *,
    in_flight_games: int = 0,
) -> None:
    """保存済み局結果から最新summaryを原子的に作る。"""
    elapsed_ns = max(0, time.monotonic_ns() - started_at_ns)
    summary = summarize(
        config,
        results,
        batch_status=status,
        unstarted_games=len(schedule) - len(results) - in_flight_games,
        in_flight_games=in_flight_games,
        elapsed_ns=elapsed_ns,
    )
    if config.resume:
        summary["elapsed_lower_bound"] = True
        if config.workers == 1:
            summary["in_flight_games"] = 0
    atomic_write_json(
        config.output_dir / "summary.json",
        summary_payload(summary),
    )


def _save_interrupted_summary(
    config: ComparisonConfig,
    schedule: Sequence[ScheduledGame],
    results: Sequence[GameResult],
    started_at_ns: int,
) -> int:
    """確定済み局だけの中断summaryを保存し130を返す。"""
    try:
        _save_summary(
            config,
            schedule,
            results,
            BatchStatus.INTERRUPTED,
            started_at_ns,
        )
    except Exception as error:
        print(
            f"中断summaryを保存できません: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1
    print("比較を中断しました。確定済みの局だけを保存しました。", file=sys.stderr)
    _print_scope_notes(sys.stderr)
    return 130


def _finish_interrupted_before_games(
    config: ComparisonConfig,
    schedule: Sequence[ScheduledGame],
    started_at_ns: int,
) -> int:
    """条件保存直後の割込み状態を、開始局なしで記録する。"""
    return _save_interrupted_summary(config, schedule, (), started_at_ns)


def _print_completion(
    config: ComparisonConfig,
    schedule: Sequence[ScheduledGame],
    results: Sequence[GameResult],
) -> None:
    """完了件数と比較の証拠範囲を短く表示する。"""
    counts = {reason.value: 0 for reason in GameEndReason}
    for result in results:
        counts[result.reason.value] += 1
    print(f"比較完了: {len(results)}/{len(schedule)}局")
    print(
        "結果: "
        f"詰み {counts[GameEndReason.CHECKMATE.value]}、"
        f"合法手なし {counts[GameEndReason.NO_LEGAL_MOVE.value]}、"
        f"連続王手負け {counts[GameEndReason.PERPETUAL_CHECK_LOSS.value]}、"
        f"通常千日手 {counts[GameEndReason.REPETITION.value]}、"
        "双方連続王手の未裁定 "
        f"{counts[GameEndReason.UNRESOLVED_DOUBLE_PERPETUAL_CHECK.value]}、"
        f"手数上限 {counts[GameEndReason.PLY_LIMIT.value]}局"
    )
    print(f"方式は固定深さ・時計制御なしです（上限 {config.max_plies} 手）。")
    print("千日手出現は一局内の判定で、独立した複数対局として数えません。")
    print("通常千日手でも自動再戦しません。")
    _print_scope_notes(sys.stdout)
    print(f"結果ファイル: {config.output_dir}")


def _print_scope_notes(stream) -> None:
    """統計的な棋力結論を出していない旨を指定出力先へ表示する。"""
    print("統計的な強さ判定は未実施です。", file=stream)


if __name__ == "__main__":
    raise SystemExit(main())
