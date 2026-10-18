"""時間制御付き反復コマンドの引数境界を確認する。"""

import contextlib
import io
import unittest

from kaname_shogi.model import Side
from kaname_shogi.search.run_controlled_iterative import _make_parser, _prepare_inputs
from kaname_shogi.time_management import SearchBudget


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
