"""時間制御付き反復コマンドの引数境界を確認する。"""

import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, sentinel

from kaname_shogi.model import Side
from kaname_shogi.search import run_controlled_iterative
from kaname_shogi.search.result import (
    ControlledCompletion,
    ControlledSearchResult,
    IterationResult,
    SearchResult,
)
from kaname_shogi.search.run_controlled_iterative import (
    _format_result,
    _make_parser,
    _prepare_inputs,
    _run_search,
)
from kaname_shogi.time_management import SearchBudget
from kaname_shogi.usi_move import parse_usi_move


class RunControlledIterativeTests(unittest.TestCase):
    def test_parser_requires_explicit_values(self):
        """四引数を必須にし、整数の値をそのまま解析する。

        深さや予算の暗黙既定値、小数の受理、文字列型の漏出を検出する。
        """
        supplied = [
            ("--sfen", "8k/9/9/9/9/9/9/9/K8 b - 1"),
            ("--max-depth", "4"),
            ("--target-ms", "31"),
            ("--maximum-ms", "47"),
        ]
        for missing in range(len(supplied)):
            with self.subTest(missing=supplied[missing][0]):
                args = [
                    value
                    for index, pair in enumerate(supplied)
                    if index != missing
                    for value in pair
                ]
                with contextlib.redirect_stderr(io.StringIO()) as error_output:
                    with self.assertRaises(SystemExit) as raised:
                        _make_parser().parse_args(args)
                self.assertEqual(raised.exception.code, 2)
                self.assertIn(supplied[missing][0], error_output.getvalue())

        parsed = _make_parser().parse_args(
            [value for pair in supplied for value in pair]
        )
        for actual, expected in (
            (parsed.sfen, supplied[0][1]),
            (parsed.max_depth, 4),
            (parsed.target_ms, 31),
            (parsed.maximum_ms, 47),
            (type(parsed.max_depth), int),
            (type(parsed.target_ms), int),
            (type(parsed.maximum_ms), int),
        ):
            with self.subTest(actual=actual, expected=expected):
                self.assertEqual(actual, expected)

        with contextlib.redirect_stderr(io.StringIO()) as error_output:
            with self.assertRaises(SystemExit) as raised:
                _make_parser().parse_args(
                    [
                        "--sfen",
                        supplied[0][1],
                        "--max-depth",
                        "2.5",
                        "--target-ms",
                        "31",
                        "--maximum-ms",
                        "47",
                    ]
                )
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--max-depth", error_output.getvalue())

    def test_parser_keeps_argparse_duplicate_and_abbreviation_rules(self):
        """重複値は最後を使い、一意な長い省略形を受け付ける。

        独自重複拒否やオプション省略形の誤った無効化を検出する。
        """
        parsed = _make_parser().parse_args(
            [
                "--sfen",
                "8k/9/9/9/9/9/9/9/K8 b - 1",
                "--max-depth",
                "2",
                "--max-depth",
                "4",
                "--target-ms",
                "31",
                "--maximum-ms",
                "47",
            ]
        )
        abbreviated = _make_parser().parse_args(
            [
                "--sfen",
                "8k/9/9/9/9/9/9/9/K8 b - 1",
                "--max-dep",
                "5",
                "--target-ms",
                "31",
                "--maximum-ms",
                "47",
            ]
        )
        for actual, expected in ((parsed.max_depth, 4), (abbreviated.max_depth, 5)):
            with self.subTest(actual=actual, expected=expected):
                self.assertEqual(actual, expected)

    def test_prepare_inputs_rejects_invalid_depth_budget_and_sfen(self):
        """深さ・予算・SFENを検査し、有効値を直接保持する。

        深さ0、予算境界の逆転、不正局面の通過や予算の再計算を検出する。
        """
        sente_sfen = "8k/9/9/9/9/9/9/9/K8 b - 1"
        gote_sfen = "8k/9/9/9/9/9/9/9/K8 w - 1"
        for values in (
            (sente_sfen, 0, 0, 0),
            (sente_sfen, 1, -1, 0),
            (sente_sfen, 1, 48, 47),
            ("invalid", 1, 0, 0),
        ):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    _prepare_inputs(*values)

        for sfen, side, target_ms, maximum_ms in (
            (sente_sfen, Side.SENTE, 0, 0),
            (gote_sfen, Side.GOTE, 31, 31),
            (sente_sfen, Side.SENTE, 31, 47),
        ):
            position, budget = _prepare_inputs(sfen, 4, target_ms, maximum_ms)
            with self.subTest(side=side):
                self.assertIs(getattr(position, "side_to_move", None), side)
            with self.subTest(budget=budget):
                self.assertEqual(
                    (budget.target_ms, budget.maximum_ms), (target_ms, maximum_ms)
                )
                self.assertEqual(budget, SearchBudget(target_ms, maximum_ms))

    def test_search_uses_direct_budget_and_one_control(self):
        """操作生成後に同じ時計原点と制御を一探索へ渡す。

        操作セット生成前の原点取得、原点/制御の再生成、予算値変更、複数探索を検出する。
        """
        position, budget = _prepare_inputs("8k/9/9/9/9/9/9/9/K8 b - 1", 4, 31, 47)
        events = []

        def make_operations(perspective):
            events.append("operations")
            return sentinel.operations

        def read_clock():
            events.append("clock")
            return 123456789

        def search_controlled(node, max_depth, operations, control):
            events.append("search")
            return sentinel.result

        with (
            patch.object(
                run_controlled_iterative.shogi,
                "make_controlled_operations",
                side_effect=make_operations,
            ) as make_operations_mock,
            patch.object(
                run_controlled_iterative.time,
                "monotonic_ns",
                side_effect=read_clock,
            ) as clock_mock,
            patch.object(
                run_controlled_iterative,
                "SearchControl",
                return_value=sentinel.control,
            ) as control_mock,
            patch.object(
                run_controlled_iterative.iterative_deepening,
                "search_controlled",
                side_effect=search_controlled,
            ) as search_mock,
        ):
            result = _run_search(position, 4, budget)

        self.assertEqual(events, ["operations", "clock", "search"])
        make_operations_mock.assert_called_once_with(Side.SENTE)
        clock_mock.assert_called_once_with()
        self.assertEqual(budget, SearchBudget(31, 47))
        control_mock.assert_called_once_with(budget, 123456789, now_ns=clock_mock)
        search_mock.assert_called_once_with(
            position, 4, sentinel.operations, sentinel.control
        )
        self.assertIs(result, sentinel.result)

    def test_search_uses_gote_as_perspective(self):
        """後手局面の開始側を制御操作の評価視点に使う。

        先手固定、予算/深さ/制御の欠落、探索結果の置換を検出する。
        """
        position, budget = _prepare_inputs("8k/9/9/9/9/9/9/9/K8 w - 1", 4, 31, 47)
        with (
            patch.object(
                run_controlled_iterative.shogi,
                "make_controlled_operations",
                return_value=sentinel.operations,
            ) as make_operations_mock,
            patch.object(
                run_controlled_iterative.time,
                "monotonic_ns",
                return_value=123456789,
            ) as clock_mock,
            patch.object(
                run_controlled_iterative,
                "SearchControl",
                return_value=sentinel.control,
            ) as control_mock,
            patch.object(
                run_controlled_iterative.iterative_deepening,
                "search_controlled",
                return_value=sentinel.result,
            ) as search_mock,
        ):
            result = _run_search(position, 4, budget)

        make_operations_mock.assert_called_once_with(Side.GOTE)
        clock_mock.assert_called_once_with()
        control_mock.assert_called_once_with(budget, 123456789, now_ns=clock_mock)
        search_mock.assert_called_once_with(
            position, 4, sentinel.operations, sentinel.control
        )
        self.assertIs(result, sentinel.result)

    def test_format_complete_and_no_legal_move(self):
        """完了記録を順に表示し、手なし状態に記録を作らない。

        指定深さとの混同、行順の崩れ、深さ/評価の捏造や投了断定を検出する。
        """
        sfen = "8k/9/9/9/9/9/9/9/K8 b - 1"
        position, budget = _prepare_inputs(sfen, 3, 31, 47)
        move = parse_usi_move("7g7f")
        complete = ControlledSearchResult(
            ControlledCompletion.COMPLETE,
            move,
            IterationResult(3, SearchResult((0, 2), move, 7, None), 12),
        )
        actual = _format_result(sfen, position, 3, budget, complete).splitlines()
        self.assertEqual(
            actual,
            [
                f"入力SFEN: {sfen}",
                "評価視点: 先手",
                "指定上限深さ: 3",
                "目標期間(ms): 31",
                "上限期間(ms): 47",
                "終了状態: COMPLETE（指定上限深さまで完了）",
                "選択手: 7g7f（7七→7六）",
                "手の由来: 完了結果",
                "完了記録: あり",
                "完了深さ: 3",
                "完了深さの評価: ＋2",
                "完了深さの訪問回数: 7",
                "反復累計（完了した深さまで）: 12",
            ],
        )

        no_legal_move = ControlledSearchResult(
            ControlledCompletion.NO_LEGAL_MOVE, None, None
        )
        actual = _format_result(sfen, position, 3, budget, no_legal_move).splitlines()
        self.assertEqual(
            actual,
            [
                f"入力SFEN: {sfen}",
                "評価視点: 先手",
                "指定上限深さ: 3",
                "目標期間(ms): 31",
                "上限期間(ms): 47",
                "終了状態: NO_LEGAL_MOVE（合法手なし）",
                "選択手: なし",
                "手の由来: 該当なし",
                "完了記録: なし（評価なし）",
            ],
        )
        self.assertNotIn("投了", "\n".join(actual))
        self.assertNotIn("詰み", "\n".join(actual))

    def test_format_stopped_with_and_without_record(self):
        """通常停止では予備手と最後の完了記録を分けて表示する。

        予備手へ評価を付ける誤り、指定深さの誤表示、未完了分の集計を検出する。
        """
        sfen = "8k/9/9/9/9/9/9/9/K8 b - 1"
        position, budget = _prepare_inputs(sfen, 3, 31, 47)
        move = parse_usi_move("7g7f")
        without_record = ControlledSearchResult(
            ControlledCompletion.STOPPED, move, None
        )
        self.assertEqual(
            _format_result(sfen, position, 3, budget, without_record).splitlines(),
            [
                f"入力SFEN: {sfen}",
                "評価視点: 先手",
                "指定上限深さ: 3",
                "目標期間(ms): 31",
                "上限期間(ms): 47",
                "終了状態: STOPPED（通常停止）",
                "選択手: 7g7f（7七→7六）",
                "手の由来: 合法予備手",
                "完了記録: なし（評価なし）",
            ],
        )

        with_record = ControlledSearchResult(
            ControlledCompletion.STOPPED,
            move,
            IterationResult(2, SearchResult((0, 1), move, 7, None), 10),
        )
        self.assertEqual(
            _format_result(sfen, position, 3, budget, with_record).splitlines(),
            [
                f"入力SFEN: {sfen}",
                "評価視点: 先手",
                "指定上限深さ: 3",
                "目標期間(ms): 31",
                "上限期間(ms): 47",
                "終了状態: STOPPED（通常停止）",
                "選択手: 7g7f（7七→7六）",
                "手の由来: 完了結果",
                "完了記録: あり",
                "完了深さ: 2",
                "完了深さの評価: ＋1",
                "完了深さの訪問回数: 7",
                "反復累計（完了した深さまで）: 10",
            ],
        )

    def test_format_suppressed_never_restores_move(self):
        """抑制時は記録の有無によらず選択手を表示しない。

        last_completedの手の復活、なしと記録ありの混同を検出する。
        """
        sfen = "8k/9/9/9/9/9/9/9/K8 b - 1"
        position, budget = _prepare_inputs(sfen, 3, 31, 47)
        move = parse_usi_move("7g7f")
        record = IterationResult(2, SearchResult((0, 1), move, 7, None), 10)
        for last_completed, record_lines in (
            (None, ["完了記録: なし（評価なし）"]),
            (
                record,
                [
                    "完了記録: あり",
                    "完了深さ: 2",
                    "完了深さの評価: ＋1",
                    "完了深さの訪問回数: 7",
                    "反復累計（完了した深さまで）: 10",
                ],
            ),
        ):
            result = ControlledSearchResult(
                ControlledCompletion.SUPPRESSED, None, last_completed
            )
            with self.subTest(recorded=last_completed is not None):
                actual = _format_result(sfen, position, 3, budget, result).splitlines()
                self.assertEqual(
                    actual[:8],
                    [
                        f"入力SFEN: {sfen}",
                        "評価視点: 先手",
                        "指定上限深さ: 3",
                        "目標期間(ms): 31",
                        "上限期間(ms): 47",
                        "終了状態: SUPPRESSED（応答抑制）",
                        "選択手: なし",
                        "手の由来: 該当なし",
                    ],
                )
                self.assertEqual(actual[8:], record_lines)
                self.assertNotIn("7g7f", "\n".join(actual))

    def test_format_uses_existing_move_and_score_formatters(self):
        """後手視点と既存の手/評価表記を実行条件・記録に出す。

        視点固定や独自・反転した手と正の評価表記を検出する。
        """
        sfen = "8k/9/9/9/9/9/9/9/K8 w - 1"
        position, budget = _prepare_inputs(sfen, 3, 31, 47)
        move = parse_usi_move("7g7f")
        result = ControlledSearchResult(
            ControlledCompletion.STOPPED,
            move,
            IterationResult(2, SearchResult((0, 1), move, 7, None), 10),
        )
        actual = _format_result(sfen, position, 3, budget, result).splitlines()
        self.assertEqual(
            actual,
            [
                f"入力SFEN: {sfen}",
                "評価視点: 後手",
                "指定上限深さ: 3",
                "目標期間(ms): 31",
                "上限期間(ms): 47",
                "終了状態: STOPPED（通常停止）",
                "選択手: 7g7f（7七→7六）",
                "手の由来: 完了結果",
                "完了記録: あり",
                "完了深さ: 2",
                "完了深さの評価: ＋1",
                "完了深さの訪問回数: 7",
                "反復累計（完了した深さまで）: 10",
            ],
        )

    def test_main_invalid_inputs_do_not_start_search(self):
        """入力不正・不足値・未知引数を終了値にして探索前で止める。

        入力ValueErrorの誤変換、未知引数の受理、argparse終了値の伝播、探索前の副作用を検出する。
        """
        valid_sfen = "8k/9/9/9/9/9/9/9/K8 b - 1"
        invalid_arguments = (
            [
                "--sfen",
                "invalid",
                "--max-depth",
                "1",
                "--target-ms",
                "0",
                "--maximum-ms",
                "0",
            ],
            [
                "--sfen",
                valid_sfen,
                "--max-depth",
                "0",
                "--target-ms",
                "0",
                "--maximum-ms",
                "0",
            ],
            [
                "--sfen",
                valid_sfen,
                "--max-depth",
                "1",
                "--target-ms",
                "48",
                "--maximum-ms",
                "47",
            ],
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with (
                    patch.object(
                        run_controlled_iterative.shogi,
                        "make_controlled_operations",
                    ) as operations_mock,
                    patch.object(
                        run_controlled_iterative.time, "monotonic_ns"
                    ) as clock_mock,
                    patch.object(
                        run_controlled_iterative.iterative_deepening,
                        "search_controlled",
                    ) as search_mock,
                    contextlib.redirect_stdout(io.StringIO()) as output,
                    contextlib.redirect_stderr(io.StringIO()) as error_output,
                ):
                    exit_code = run_controlled_iterative.main(arguments)

                self.assertEqual(exit_code, 2)
                self.assertEqual(output.getvalue(), "")
                self.assertIn("入力エラー:", error_output.getvalue())
                operations_mock.assert_not_called()
                clock_mock.assert_not_called()
                search_mock.assert_not_called()

        with (
            patch.object(
                run_controlled_iterative.shogi,
                "make_controlled_operations",
            ) as operations_mock,
            patch.object(run_controlled_iterative.time, "monotonic_ns") as clock_mock,
            patch.object(
                run_controlled_iterative.iterative_deepening, "search_controlled"
            ) as search_mock,
            contextlib.redirect_stdout(io.StringIO()) as output,
            contextlib.redirect_stderr(io.StringIO()) as error_output,
        ):
            exit_code = run_controlled_iterative.main(["--sfen", valid_sfen])

        self.assertEqual(exit_code, 2)
        self.assertIn("usage:", error_output.getvalue())
        self.assertNotIn("入力エラー:", error_output.getvalue())
        self.assertEqual(output.getvalue(), "")
        operations_mock.assert_not_called()
        clock_mock.assert_not_called()
        search_mock.assert_not_called()

        unknown_arguments = [
            "--sfen",
            valid_sfen,
            "--max-depth",
            "1",
            "--target-ms",
            "0",
            "--maximum-ms",
            "0",
            "--unknown",
        ]
        with (
            patch.object(
                run_controlled_iterative.shogi,
                "make_controlled_operations",
            ) as operations_mock,
            patch.object(run_controlled_iterative.time, "monotonic_ns") as clock_mock,
            patch.object(
                run_controlled_iterative.iterative_deepening, "search_controlled"
            ) as search_mock,
            contextlib.redirect_stdout(io.StringIO()) as output,
            contextlib.redirect_stderr(io.StringIO()) as error_output,
        ):
            clock_mock.return_value = 123456789
            search_mock.return_value = ControlledSearchResult(
                ControlledCompletion.NO_LEGAL_MOVE, None, None
            )
            exit_code = run_controlled_iterative.main(unknown_arguments)

        self.assertEqual(exit_code, 2)
        self.assertIn("usage:", error_output.getvalue())
        self.assertIn("unrecognized arguments: --unknown", error_output.getvalue())
        self.assertNotIn("入力エラー:", error_output.getvalue())
        self.assertEqual(output.getvalue(), "")
        operations_mock.assert_not_called()
        clock_mock.assert_not_called()
        search_mock.assert_not_called()

    def test_main_help_skips_clock_and_search(self):
        """ヘルプ要求を0で返し、時計と探索へ進まない。

        argparse終了を異常扱いする誤りやヘルプ後の探索開始を検出する。
        """
        with (
            patch.object(
                run_controlled_iterative.shogi,
                "make_controlled_operations",
            ) as operations_mock,
            patch.object(run_controlled_iterative.time, "monotonic_ns") as clock_mock,
            patch.object(
                run_controlled_iterative.iterative_deepening, "search_controlled"
            ) as search_mock,
            contextlib.redirect_stdout(io.StringIO()) as output,
            contextlib.redirect_stderr(io.StringIO()) as error_output,
        ):
            exit_code = run_controlled_iterative.main(["--help"])

        self.assertEqual(exit_code, 0)
        self.assertIn("usage:", output.getvalue())
        self.assertEqual(error_output.getvalue(), "")
        operations_mock.assert_not_called()
        clock_mock.assert_not_called()
        search_mock.assert_not_called()

    def test_internal_value_errors_propagate(self):
        """入力準備後のValueErrorを同じ例外のまま伝播する。

        操作・時計・探索・整形・出力の故障を入力誤り2へ誤変換するのを検出する。
        """
        arguments = [
            "--sfen",
            "8k/9/9/9/9/9/9/9/K8 b - 1",
            "--max-depth",
            "1",
            "--target-ms",
            "0",
            "--maximum-ms",
            "0",
        ]
        stopped = ControlledSearchResult(ControlledCompletion.NO_LEGAL_MOVE, None, None)

        for boundary in ("operations", "clock", "search", "format", "output"):
            with self.subTest(boundary=boundary):
                failure = ValueError(f"{boundary} failed")
                with contextlib.ExitStack() as stack:
                    if boundary == "operations":
                        stack.enter_context(
                            patch.object(
                                run_controlled_iterative.shogi,
                                "make_controlled_operations",
                                side_effect=failure,
                            )
                        )
                    elif boundary == "clock":
                        stack.enter_context(
                            patch.object(
                                run_controlled_iterative.shogi,
                                "make_controlled_operations",
                                return_value=sentinel.operations,
                            )
                        )
                        stack.enter_context(
                            patch.object(
                                run_controlled_iterative.time,
                                "monotonic_ns",
                                side_effect=failure,
                            )
                        )
                    elif boundary == "search":
                        stack.enter_context(
                            patch.object(
                                run_controlled_iterative.shogi,
                                "make_controlled_operations",
                                return_value=sentinel.operations,
                            )
                        )
                        stack.enter_context(
                            patch.object(
                                run_controlled_iterative.time,
                                "monotonic_ns",
                                return_value=123456789,
                            )
                        )
                        stack.enter_context(
                            patch.object(
                                run_controlled_iterative,
                                "SearchControl",
                                return_value=sentinel.control,
                            )
                        )
                        stack.enter_context(
                            patch.object(
                                run_controlled_iterative.iterative_deepening,
                                "search_controlled",
                                side_effect=failure,
                            )
                        )
                    elif boundary == "format":
                        stack.enter_context(
                            patch.object(
                                run_controlled_iterative,
                                "_run_search",
                                return_value=stopped,
                            )
                        )
                        stack.enter_context(
                            patch.object(
                                run_controlled_iterative,
                                "_format_result",
                                side_effect=failure,
                            )
                        )
                    else:
                        stack.enter_context(
                            patch.object(
                                run_controlled_iterative,
                                "_run_search",
                                return_value=stopped,
                            )
                        )
                        stack.enter_context(
                            patch.object(
                                run_controlled_iterative,
                                "_format_result",
                                return_value="rendered result",
                            )
                        )
                        print_mock = stack.enter_context(
                            patch("builtins.print", side_effect=[failure, None])
                        )
                    with (
                        contextlib.redirect_stdout(io.StringIO()),
                        contextlib.redirect_stderr(io.StringIO()),
                        self.assertRaises(ValueError) as raised,
                    ):
                        run_controlled_iterative.main(arguments)

                self.assertIs(raised.exception, failure)
                if boundary == "output":
                    print_mock.assert_called_once()

    def test_keyboard_interrupt_returns_130_without_result_recovery(self):
        """各段階の中断を130と診断へ変え、結果を再探索・再表示しない。

        捕捉範囲の欠落、通常結果の誤回収、内部段階の再実行を検出する。
        """
        arguments = [
            "--sfen",
            "8k/9/9/9/9/9/9/9/K8 b - 1",
            "--max-depth",
            "1",
            "--target-ms",
            "0",
            "--maximum-ms",
            "0",
        ]
        stopped = ControlledSearchResult(ControlledCompletion.NO_LEGAL_MOVE, None, None)
        diagnostic = "中断: Ctrl+C。結果表示は未完了です"

        class InterruptingOutput(io.StringIO):
            def __init__(self, interruption):
                super().__init__()
                self.interruption = interruption
                self.write_attempts = 0

            def write(self, value):
                self.write_attempts += 1
                if self.write_attempts == 1:
                    super().write("rendered")
                    raise self.interruption
                return super().write(value)

        for boundary in (
            "parse",
            "input",
            "operations",
            "clock",
            "search",
            "format",
            "output",
        ):
            with self.subTest(boundary=boundary):
                interruption = KeyboardInterrupt()
                with contextlib.ExitStack() as stack:
                    call_mocks = []
                    if boundary == "parse":
                        parser = Mock()
                        parser.parse_args.side_effect = interruption
                        call_mocks.append(parser.parse_args)
                        stack.enter_context(
                            patch.object(
                                run_controlled_iterative,
                                "_make_parser",
                                return_value=parser,
                            )
                        )
                    elif boundary == "input":
                        call_mocks.append(
                            stack.enter_context(
                                patch.object(
                                    run_controlled_iterative,
                                    "_prepare_inputs",
                                    side_effect=interruption,
                                )
                            )
                        )
                    elif boundary == "operations":
                        call_mocks.append(
                            stack.enter_context(
                                patch.object(
                                    run_controlled_iterative.shogi,
                                    "make_controlled_operations",
                                    side_effect=interruption,
                                )
                            )
                        )
                    elif boundary == "clock":
                        call_mocks.append(
                            stack.enter_context(
                                patch.object(
                                    run_controlled_iterative.shogi,
                                    "make_controlled_operations",
                                    return_value=sentinel.operations,
                                )
                            )
                        )
                        call_mocks.append(
                            stack.enter_context(
                                patch.object(
                                    run_controlled_iterative.time,
                                    "monotonic_ns",
                                    side_effect=interruption,
                                )
                            )
                        )
                    elif boundary == "search":
                        call_mocks.append(
                            stack.enter_context(
                                patch.object(
                                    run_controlled_iterative.shogi,
                                    "make_controlled_operations",
                                    return_value=sentinel.operations,
                                )
                            )
                        )
                        call_mocks.append(
                            stack.enter_context(
                                patch.object(
                                    run_controlled_iterative.time,
                                    "monotonic_ns",
                                    return_value=123456789,
                                )
                            )
                        )
                        call_mocks.append(
                            stack.enter_context(
                                patch.object(
                                    run_controlled_iterative,
                                    "SearchControl",
                                    return_value=sentinel.control,
                                )
                            )
                        )
                        call_mocks.append(
                            stack.enter_context(
                                patch.object(
                                    run_controlled_iterative.iterative_deepening,
                                    "search_controlled",
                                    side_effect=interruption,
                                )
                            )
                        )
                    elif boundary == "format":
                        call_mocks.append(
                            stack.enter_context(
                                patch.object(
                                    run_controlled_iterative,
                                    "_run_search",
                                    return_value=stopped,
                                )
                            )
                        )
                        call_mocks.append(
                            stack.enter_context(
                                patch.object(
                                    run_controlled_iterative,
                                    "_format_result",
                                    side_effect=interruption,
                                )
                            )
                        )
                    else:
                        call_mocks.append(
                            stack.enter_context(
                                patch.object(
                                    run_controlled_iterative,
                                    "_run_search",
                                    return_value=stopped,
                                )
                            )
                        )
                        call_mocks.append(
                            stack.enter_context(
                                patch.object(
                                    run_controlled_iterative,
                                    "_format_result",
                                    return_value="rendered result",
                                )
                            )
                        )

                    output = (
                        InterruptingOutput(interruption)
                        if boundary == "output"
                        else io.StringIO()
                    )
                    with (
                        contextlib.redirect_stdout(output),
                        contextlib.redirect_stderr(io.StringIO()) as error_output,
                    ):
                        exit_code = run_controlled_iterative.main(arguments)

                self.assertEqual(exit_code, 130)
                for call_mock in call_mocks:
                    call_mock.assert_called_once()
                self.assertEqual(
                    output.getvalue(), "rendered" if boundary == "output" else ""
                )
                if boundary == "output":
                    self.assertEqual(output.write_attempts, 1)
                self.assertEqual(error_output.getvalue(), f"{diagnostic}\n")

    def test_real_process_entrypoint(self):
        """モジュール入口のヘルプ・入力失敗・0ms停止を確認する。

        SystemExitの未接続、誤ったプロセス終了値、停止記録の捏造を検出する。
        """
        module = "kaname_shogi.search.run_controlled_iterative"
        repository_root = Path(__file__).resolve().parents[1]
        base_command = [sys.executable, "-m", module]
        cases = (
            (["--help"], 0, "usage:", ""),
            (
                [
                    "--sfen",
                    "invalid",
                    "--max-depth",
                    "1",
                    "--target-ms",
                    "0",
                    "--maximum-ms",
                    "0",
                ],
                2,
                "",
                "入力エラー:",
            ),
            (
                [
                    "--sfen",
                    "8k/9/9/9/9/9/9/9/K8 b - 1",
                    "--max-depth",
                    "1",
                    "--target-ms",
                    "0",
                    "--maximum-ms",
                    "0",
                ],
                0,
                "STOPPED（通常停止）",
                "",
            ),
        )

        for arguments, expected_code, expected_stdout, expected_stderr in cases:
            with self.subTest(arguments=arguments):
                completed = subprocess.run(
                    [*base_command, *arguments],
                    capture_output=True,
                    check=False,
                    cwd=repository_root,
                    text=True,
                )
                self.assertEqual(completed.returncode, expected_code)
                if expected_stdout:
                    self.assertIn(expected_stdout, completed.stdout)
                else:
                    self.assertEqual(completed.stdout, "")
                if expected_stderr:
                    self.assertIn(expected_stderr, completed.stderr)
                else:
                    self.assertEqual(completed.stderr, "")
                if arguments[-1] == "0" and arguments[0] == "--sfen":
                    if arguments[1] == "8k/9/9/9/9/9/9/9/K8 b - 1":
                        self.assertIn("完了記録: なし（評価なし）", completed.stdout)
