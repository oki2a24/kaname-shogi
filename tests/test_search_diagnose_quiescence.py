"""静止探索の小局面診断コマンドの契約を確認する。"""

import contextlib
import io
import unittest
from dataclasses import FrozenInstanceError
from fractions import Fraction
from unittest.mock import patch, sentinel

from kaname_shogi.model import Side
from kaname_shogi.search import diagnose_quiescence, run_controlled_iterative
from kaname_shogi.search.diagnose_quiescence import (
    DiagnosticResult,
    IterationDiagnostic,
    _format_result,
    _make_parser,
    _prepare_inputs,
    _run_search,
)
from kaname_shogi.search.result import (
    ControlledCompletion,
    ControlledSearchResult,
    IterationResult,
    QuiescenceLimit,
    SearchInterrupted,
    SearchResult,
)
from kaname_shogi.search_control import SearchSignal
from kaname_shogi.sfen import parse_sfen
from kaname_shogi.time_management import (
    SearchBudget,
    TimeManagementConfig,
    calculate_search_budget,
)
from kaname_shogi.usi_move import parse_usi_move

KINGS = "8k/9/9/9/9/9/9/9/K8 b - 1"
CAPTURES = "k8/9/9/9/2g1p4/9/9/9/2R1R3K b - 1"
CONFIG = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 2000)


def arguments(
    *, sfen=KINGS, variant="baseline", remaining_ms="600000", byoyomi_ms="30000"
):
    return [
        "--sfen",
        sfen,
        "--variant",
        variant,
        "--remaining-ms",
        remaining_ms,
        "--byoyomi-ms",
        byoyomi_ms,
    ]


def completed_result(move=None, depth=1, visited_nodes=3, score=(0, 2)):
    if move is None:
        move = parse_usi_move("9i9h")
    search_result = SearchResult(score, move, visited_nodes, None)
    return IterationResult(depth, search_result, visited_nodes)


def diagnostic_for(
    completion,
    *,
    move=None,
    last_completed=None,
    iterations=(),
    elapsed_ns=1_234_567,
    total_normal_nodes=8,
    total_quiescence_calls=10,
):
    return DiagnosticResult(
        ControlledSearchResult(completion, move, last_completed),
        elapsed_ns,
        tuple(iterations),
        total_normal_nodes,
        total_quiescence_calls,
    )


class DiagnoseQuiescenceTests(unittest.TestCase):
    def test_parser_requires_each_argument_and_restricts_variant(self):
        """SFEN・方式・二つの時計値を必須とし、方式を三候補に限定する。

        無指定の既定値と未知方式の探索開始を検出する。
        """
        supplied = arguments()
        parsed = _make_parser().parse_args(supplied)
        self.assertEqual(
            (
                parsed.sfen,
                parsed.variant,
                parsed.remaining_ms,
                parsed.byoyomi_ms,
            ),
            (KINGS, "baseline", 600000, 30000),
        )
        for missing in range(0, len(supplied), 2):
            with self.subTest(missing=supplied[missing]):
                argv = supplied[:missing] + supplied[missing + 2 :]
                with contextlib.redirect_stderr(io.StringIO()) as error_output:
                    with self.assertRaises(SystemExit) as raised:
                        _make_parser().parse_args(argv)
                self.assertEqual(raised.exception.code, 2)
                self.assertIn(supplied[missing], error_output.getvalue())

        with contextlib.redirect_stderr(io.StringIO()) as error_output:
            with self.assertRaises(SystemExit) as raised:
                _make_parser().parse_args(arguments(variant="q8"))
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("q8", error_output.getvalue())

    def test_prepare_inputs_delegates_sfen_and_budget_and_keeps_side(self):
        """有効な入力から開始側局面と公開予算計算の値を返す。

        時計予算の独自再実装や、SFENの手番を固定する誤りを検出する。
        """
        for sfen, side in (
            (KINGS, Side.SENTE),
            (KINGS.replace(" b ", " w "), Side.GOTE),
        ):
            with self.subTest(side=side):
                with (
                    patch.object(
                        diagnose_quiescence.comparison,
                        "parse_position",
                        wraps=diagnose_quiescence.comparison.parse_position,
                    ) as parse_position,
                    patch.object(
                        diagnose_quiescence,
                        "calculate_search_budget",
                        wraps=calculate_search_budget,
                    ) as calculate,
                ):
                    position, budget = _prepare_inputs(
                        sfen, "q2", 600000, 30000, CONFIG
                    )

                self.assertIs(position.side_to_move, side)
                self.assertEqual(budget, calculate_search_budget(600000, 30000, CONFIG))
                parse_position.assert_called_once_with(sfen)
                calculate.assert_called_once_with(600000, 30000, CONFIG)

    def test_prepare_inputs_rejects_bad_variant_sfen_and_bool_or_negative_clocks(self):
        """未知方式・不正SFEN・bool・負の時計値を入力エラーにする。

        boolを整数時計として通すことや、入力段階で不正値を予算化する誤りを検出する。
        """
        invalid_inputs = (
            ("invalid SFEN", "baseline", 0, 0),
            (KINGS, "unknown", 0, 0),
            (KINGS, True, 0, 0),
            (KINGS, "baseline", -1, 0),
            (KINGS, "baseline", 0, -1),
            (KINGS, "baseline", True, 0),
            (KINGS, "baseline", 0, False),
        )
        for values in invalid_inputs:
            with self.subTest(values=values), self.assertRaises(ValueError):
                _prepare_inputs(*values, CONFIG)

    def test_parser_main_maps_invalid_arguments_to_exit_two(self):
        """引数解析の失敗を2として返し、設定読込・探索を行わない。

        argparseのSystemExit漏出や入力不正からの探索開始を検出する。
        """
        with (
            contextlib.redirect_stderr(io.StringIO()) as error_output,
            patch.object(diagnose_quiescence, "load_time_management_config") as load,
            patch.object(diagnose_quiescence, "_run_search") as search,
        ):
            code = diagnose_quiescence.main(arguments(variant="bad"))

        self.assertEqual(code, 2)
        self.assertIn("bad", error_output.getvalue())
        load.assert_not_called()
        search.assert_not_called()

    def test_main_help_returns_zero_without_loading_config_or_searching(self):
        """ヘルプは0で返し、設定や局面を処理しない。

        ヘルプ表示後に設定故障や探索を誤って起こす経路を検出する。
        """
        with (
            contextlib.redirect_stdout(io.StringIO()) as output,
            contextlib.redirect_stderr(io.StringIO()) as error_output,
            patch.object(diagnose_quiescence, "load_time_management_config") as load,
            patch.object(diagnose_quiescence, "_run_search") as search,
        ):
            code = diagnose_quiescence.main(["--help"])

        self.assertEqual(code, 0)
        self.assertIn("--variant", output.getvalue())
        self.assertEqual(error_output.getvalue(), "")
        load.assert_not_called()
        search.assert_not_called()

    def test_config_failure_is_reported_to_stderr_with_nonzero_exit(self):
        """時計設定の読込故障を入力不正と区別し、標準エラーへ出す。

        設定障害の黙殺、成功扱い、stdoutへの混入を検出する。
        """
        for error in (OSError("設定ファイルを開けない"), ValueError("設定値が不正")):
            with self.subTest(error=error):
                with (
                    contextlib.redirect_stdout(io.StringIO()) as output,
                    contextlib.redirect_stderr(io.StringIO()) as error_output,
                    patch.object(
                        diagnose_quiescence,
                        "load_time_management_config",
                        side_effect=error,
                    ),
                ):
                    code = diagnose_quiescence.main(arguments())

                self.assertNotEqual(code, 0)
                self.assertIn(str(error), error_output.getvalue())
                self.assertEqual(output.getvalue(), "")

    def test_input_failure_returns_two_but_search_value_error_propagates(self):
        """SFEN・時計入力は2、探索内部のValueErrorはそのまま呼出し側へ返す。

        探索故障まで入力エラーとして握りつぶす広すぎる例外境界を検出する。
        """
        for argv in (
            arguments(remaining_ms="-1"),
            arguments(sfen="invalid SFEN"),
        ):
            with self.subTest(argv=argv):
                with (
                    contextlib.redirect_stderr(io.StringIO()) as error_output,
                    patch.object(
                        diagnose_quiescence,
                        "load_time_management_config",
                        return_value=CONFIG,
                    ),
                ):
                    code = diagnose_quiescence.main(argv)
                self.assertEqual(code, 2)
                self.assertIn("入力エラー", error_output.getvalue())

        failure = ValueError("探索内部の契約違反")
        with (
            patch.object(
                diagnose_quiescence, "load_time_management_config", return_value=CONFIG
            ),
            patch.object(diagnose_quiescence, "_run_search", side_effect=failure),
            self.assertRaises(ValueError) as caught,
        ):
            diagnose_quiescence.main(arguments())
        self.assertIs(caught.exception, failure)

    def test_run_search_selects_each_factory_once_and_passes_fixed_depth(self):
        """基準・追加2手・追加4手の操作を一度選び、固定通常深さ4で探索する。

        方式の取り違え、候補追加深さの誤設定、複数回探索を検出する。
        """
        position = parse_sfen(KINGS).position
        budget = SearchBudget(31, 47)
        expected_result = ControlledSearchResult(
            ControlledCompletion.NO_LEGAL_MOVE, None, None
        )
        for variant, additional_depth in (
            ("baseline", None),
            ("q2", 2),
            ("q4", 4),
        ):
            with self.subTest(variant=variant):
                events = []
                clock_values = iter((100, 200))

                def clock(events=events, clock_values=clock_values):
                    events.append("clock")
                    return next(clock_values)

                def make_base(perspective, *, counters, events=events):
                    events.append(("baseline", perspective, counters))
                    return sentinel.operations

                def make_quiet(perspective, depth, *, counters, events=events):
                    events.append(("quiet", perspective, depth, counters))
                    return sentinel.operations

                def search(
                    node,
                    depth,
                    operations,
                    control,
                    *,
                    on_iteration,
                    events=events,
                    expected_result=expected_result,
                ):
                    events.append(("search", node, depth, operations, control))
                    return expected_result

                with (
                    patch.object(
                        diagnose_quiescence.shogi,
                        "make_controlled_operations",
                        side_effect=make_base,
                    ) as make_base_mock,
                    patch.object(
                        diagnose_quiescence.shogi,
                        "make_quiescence_operations",
                        side_effect=make_quiet,
                    ) as make_quiet_mock,
                    patch.object(
                        diagnose_quiescence.iterative_deepening,
                        "search_controlled",
                        side_effect=search,
                    ) as search_mock,
                ):
                    diagnostic = _run_search(position, variant, budget, now_ns=clock)

                factory_calls = [
                    event for event in events if event[0] in ("quiet", "baseline")
                ]
                self.assertEqual(len(factory_calls), 1)
                self.assertEqual(events.count("clock"), 2)
                self.assertLess(events.index(factory_calls[0]), events.index("clock"))
                self.assertLess(
                    events.index("clock"),
                    next(
                        index
                        for index, event in enumerate(events)
                        if event[0] == "search"
                    ),
                )
                self.assertEqual(diagnostic.result, expected_result)
                self.assertEqual(diagnostic.elapsed_ns, 100)
                if additional_depth is None:
                    self.assertEqual(factory_calls[0][0:2], ("baseline", Side.SENTE))
                    make_base_mock.assert_called_once()
                    make_quiet_mock.assert_not_called()
                else:
                    self.assertEqual(
                        factory_calls[0][0:3], ("quiet", Side.SENTE, additional_depth)
                    )
                    make_quiet_mock.assert_called_once()
                    make_base_mock.assert_not_called()
                search_event = next(event for event in events if event[0] == "search")
                self.assertEqual(search_event[2], 4)
                self.assertIs(search_event[3], sentinel.operations)
                self.assertEqual(search_mock.call_count, 1)

    def test_run_search_records_per_iteration_deltas_and_total_counters(self):
        """反復ごとの差分と、未完了反復を含む全計数を保持する。

        累計を反復値として表示する誤り、未完了分を総計から落とす誤りを検出する。
        """
        position = parse_sfen(KINGS).position
        move = parse_usi_move("9i9h")
        first = completed_result(move, depth=1, visited_nodes=3)
        last = first
        expected = ControlledSearchResult(
            ControlledCompletion.QUIESCENCE_LIMIT, move, last
        )
        observed_counts = []
        clock_values = iter((1_000_000, 1_100_000))
        counters_seen = []

        def make_quiet(perspective, depth, *, counters):
            self.assertEqual((perspective, depth), (Side.SENTE, 4))
            counters_seen.append(counters)
            return sentinel.operations

        def search(node, depth, operations, control, *, on_iteration):
            self.assertEqual(
                (node, depth, operations), (position, 4, sentinel.operations)
            )
            counters = counters_seen[0]
            counters.normal_nodes = 3
            counters.quiescence_calls = 4
            on_iteration(1, first)
            counters.normal_nodes = 8
            counters.quiescence_calls = 10
            on_iteration(2, QuiescenceLimit())
            observed_counts.extend((counters.normal_nodes, counters.quiescence_calls))
            return expected

        with (
            patch.object(
                diagnose_quiescence.shogi,
                "make_quiescence_operations",
                side_effect=make_quiet,
            ) as factory,
            patch.object(
                diagnose_quiescence.iterative_deepening,
                "search_controlled",
                side_effect=search,
            ) as search_mock,
        ):
            result = _run_search(
                position,
                "q4",
                SearchBudget(500, 800),
                now_ns=lambda: next(clock_values),
            )

        factory.assert_called_once()
        search_mock.assert_called_once()
        self.assertEqual(result.elapsed_ns, 100_000)
        self.assertEqual(
            [
                (item.depth, item.normal_nodes, item.quiescence_calls)
                for item in result.iterations
            ],
            [(1, 3, 4), (2, 5, 6)],
        )
        self.assertEqual(result.iterations[0].result, first)
        self.assertIsInstance(result.iterations[1].result, QuiescenceLimit)
        self.assertEqual(
            (result.total_normal_nodes, result.total_quiescence_calls), (8, 10)
        )
        self.assertEqual(observed_counts, [8, 10])

    def test_baseline_result_matches_existing_controlled_runner(self):
        """基準診断は既存の時間制御探索と同じ結果・手を返す。

        診断専用経路だけで通常探索の結果を変える誤りを検出する。
        """
        position = parse_sfen(KINGS).position
        budget = SearchBudget(600000, 600000)
        actual = _run_search(position, "baseline", budget, now_ns=lambda: 0).result
        expected = run_controlled_iterative._run_search(position, 4, budget)
        self.assertEqual(actual, expected)

    def test_format_reports_all_fields_counters_and_non_loss_quiescence_limit(self):
        """方式・予算・時間・終了・手・反復/全計数を日本語で表示する。

        追加上限未完了を時間切れ負けと誤記し、計数や完了深さを省く誤りを検出する。
        """
        position = parse_sfen(CAPTURES).position
        budget = SearchBudget(21, 28)
        move = parse_usi_move("3i3e")
        completed = completed_result(move, depth=2, visited_nodes=5)
        cases = (
            (
                ControlledCompletion.QUIESCENCE_LIMIT,
                move,
                completed,
                "QUIESCENCE_LIMIT",
                "最後に完了した通常深さ",
                (
                    IterationDiagnostic(1, completed_result(move, depth=1), 3, 2),
                    IterationDiagnostic(2, completed, 5, 6),
                    IterationDiagnostic(3, QuiescenceLimit(), 7, 8),
                ),
            ),
            (
                ControlledCompletion.QUIESCENCE_LIMIT,
                parse_usi_move("3i3h"),
                None,
                "QUIESCENCE_LIMIT",
                "合法予備手",
                (IterationDiagnostic(1, QuiescenceLimit(), 2, 3),),
            ),
            (
                ControlledCompletion.STOPPED,
                parse_usi_move("3i3h"),
                None,
                "STOPPED",
                "合法予備手",
                (IterationDiagnostic(1, SearchInterrupted(SearchSignal.STOP), 2, 3),),
            ),
            (
                ControlledCompletion.SUPPRESSED,
                None,
                completed,
                "SUPPRESSED",
                "該当なし",
                (IterationDiagnostic(2, completed, 5, 6),),
            ),
            (
                ControlledCompletion.NO_LEGAL_MOVE,
                None,
                None,
                "NO_LEGAL_MOVE",
                "該当なし",
                (),
            ),
        )
        for completion, selected, last, state_label, origin_label, iterations in cases:
            with self.subTest(completion=completion, origin=origin_label):
                diagnostic = diagnostic_for(
                    completion,
                    move=selected,
                    last_completed=last,
                    iterations=iterations,
                )
                output = _format_result(CAPTURES, position, "q4", budget, diagnostic)
                for field in (
                    "方式:",
                    "目標期間(ms): 21",
                    "上限期間(ms): 28",
                    "消費時間(ms): 1.235",
                    f"終了状態: {state_label}",
                    "選択手:",
                    f"手の由来: {origin_label}",
                    "完了した通常深さ:",
                    "各反復の通常調査回数:",
                    "各反復の静止探索呼出し回数:",
                    "全体の通常調査回数: 8",
                    "全体の静止探索呼出し回数: 10",
                ):
                    self.assertIn(field, output)
                self.assertNotIn("時間切れ負け", output)
                if iterations:
                    last_iteration = iterations[-1]
                    self.assertIn(f"反復{last_iteration.depth}:", output)
                    self.assertIn(f"通常調査回数={last_iteration.normal_nodes}", output)
                    self.assertIn(
                        f"静止探索呼出し回数={last_iteration.quiescence_calls}",
                        output,
                    )
                else:
                    self.assertIn("各反復の通常調査回数:\n  なし", output)
                    self.assertIn("各反復の静止探索呼出し回数:\n  なし", output)
                if last is None:
                    self.assertIn("完了記録: なし", output)
                else:
                    self.assertIn("完了記録: あり", output)
                    self.assertIn("最終完了深さの評価: ＋2", output)

    def test_format_keeps_interrupted_iteration_and_completed_depth_separate(self):
        """通常停止の反復を未完了として示し、最後の完成深さと混同しない。

        SearchInterruptedを完了記録として数える誤表示を検出する。
        """
        position = parse_sfen(KINGS).position
        move = parse_usi_move("9i9h")
        completed = completed_result(move, depth=1)
        result = diagnostic_for(
            ControlledCompletion.STOPPED,
            move=move,
            last_completed=completed,
            iterations=(
                IterationDiagnostic(1, completed, 3, 2),
                IterationDiagnostic(2, SearchInterrupted(SearchSignal.STOP), 4, 5),
            ),
        )
        output = _format_result(KINGS, position, "q2", SearchBudget(0, 0), result)
        self.assertIn("完了した通常深さ: 1", output)
        self.assertIn("反復2: 停止で未完了", output)
        self.assertIn("反復2: 停止で未完了・通常調査回数=4", output)
        self.assertIn("反復2: 静止探索呼出し回数=5", output)

    def test_main_uses_loaded_config_runs_once_and_prints_success(self):
        """設定読込・予算・探索を一度ずつ行い、正常時に一件を標準出力する。

        手番側時計の誤用、時計設定の再読込、stdout欠落やエラー混在を検出する。
        """
        expected_position = parse_sfen(KINGS).position
        expected_budget = calculate_search_budget(600000, 30000, CONFIG)
        move = parse_usi_move("9i9h")
        completed = completed_result(move, depth=4)
        diagnostic = diagnostic_for(
            ControlledCompletion.COMPLETE,
            move=move,
            last_completed=completed,
            iterations=(IterationDiagnostic(4, completed, 3, 2),),
        )
        with (
            contextlib.redirect_stdout(io.StringIO()) as output,
            contextlib.redirect_stderr(io.StringIO()) as error_output,
            patch.object(
                diagnose_quiescence,
                "load_time_management_config",
                return_value=CONFIG,
            ) as load,
            patch.object(
                diagnose_quiescence,
                "_prepare_inputs",
                return_value=(expected_position, expected_budget),
            ) as prepare,
            patch.object(
                diagnose_quiescence, "_run_search", return_value=diagnostic
            ) as search,
        ):
            code = diagnose_quiescence.main(arguments(variant="q4"))

        self.assertEqual(code, 0)
        self.assertEqual(error_output.getvalue(), "")
        self.assertIn("方式: q4", output.getvalue())
        self.assertIn("終了状態: COMPLETE", output.getvalue())
        self.assertEqual(output.getvalue().count("選択手:"), 1)
        load.assert_called_once_with()
        prepare.assert_called_once_with(KINGS, "q4", 600000, 30000, CONFIG)
        search.assert_called_once_with(expected_position, "q4", expected_budget)

    def test_main_keyboard_interrupt_returns_130_without_partial_stdout(self):
        """探索中のCtrl+Cを130として報告し、部分結果を標準出力へ出さない。

        中断を成功扱いすることや未完了結果を再実行・表示する誤りを検出する。
        """
        with (
            contextlib.redirect_stdout(io.StringIO()) as output,
            contextlib.redirect_stderr(io.StringIO()) as error_output,
            patch.object(
                diagnose_quiescence,
                "load_time_management_config",
                return_value=CONFIG,
            ),
            patch.object(
                diagnose_quiescence, "_run_search", side_effect=KeyboardInterrupt
            ) as search,
        ):
            code = diagnose_quiescence.main(arguments())

        self.assertEqual(code, 130)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("Ctrl+C", error_output.getvalue())
        search.assert_called_once()

    def test_diagnostic_dataclasses_are_frozen(self):
        """診断結果と反復スナップショットを変更不可として保持する。

        呼出し後に累計・反復差分を書き換える誤りを検出する。
        """
        move = parse_usi_move("9i9h")
        completed = completed_result(move)
        diagnostic = diagnostic_for(
            ControlledCompletion.COMPLETE,
            move=move,
            last_completed=completed,
            iterations=(IterationDiagnostic(1, completed, 3, 4),),
        )
        with self.assertRaises(FrozenInstanceError):
            diagnostic.elapsed_ns = 0
        with self.assertRaises(FrozenInstanceError):
            diagnostic.iterations[0].normal_nodes = 0


if __name__ == "__main__":
    unittest.main()
