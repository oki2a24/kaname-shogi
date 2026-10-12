"""USI時計の検証と自分側予算の準備を確認する。"""

import unittest
from fractions import Fraction
from unittest.mock import patch

from kaname_shogi import usi_engine
from kaname_shogi.model import Side
from kaname_shogi.time_management import SearchBudget, TimeManagementConfig


class UsiClockTests(unittest.TestCase):
    def parse(self, text):
        parser = getattr(usi_engine, "_parse_go_clock", None)
        self.assertIsNotNone(parser, "時計解析操作が必要です")
        try:
            return parser(text.split())
        except ValueError:
            raise
        except Exception as error:
            self.fail(f"時計解析の契約外例外: {type(error).__name__}: {error}")

    def test_parses_clock_and_omission(self):
        """時計を順序に依存せず読み、秒読み省略を0とする。

        未知語で解析を終える誤り、先後の代入逆転、秒読みの補完漏れを検出する。
        """
        for text, expected in (
            ("btime 600000 wtime 120000 byoyomi 30000", (600000, 120000, 30000)),
            (
                "mystery wtime 120000 extra btime 600000 byoyomi 30000",
                (600000, 120000, 30000),
            ),
            ("wtime 120000 btime 600000", (600000, 120000, 0)),
        ):
            with self.subTest(text=text):
                clock = self.parse(text)
                self.assertIsNotNone(clock)
                self.assertEqual(
                    (clock.btime_ms, clock.wtime_ms, clock.byoyomi_ms), expected
                )

    def test_distinguishes_missing_clock_from_zero(self):
        """時計なしと明示された両時計0を区別する。

        加算0だけを時計ありにしたり、明示0を未指定扱いする誤りを検出する。
        """
        for text in ("", "mystery", "binc 0", "winc 0", "binc 0 winc 0"):
            with self.subTest(text=text):
                self.assertIsNone(self.parse(text))
        clock = self.parse("btime 0 wtime 0")
        self.assertIsNotNone(clock)
        self.assertEqual((clock.btime_ms, clock.wtime_ms, clock.byoyomi_ms), (0, 0, 0))

    def test_rejects_invalid_known_fields(self):
        """既知五項目の不正値・重複・不足を項目付きで拒否する。

        相手側だけ未検査、重複の後勝ち、未知語による後続検査省略を検出する。
        """
        for key in ("btime", "wtime", "byoyomi", "binc", "winc"):
            for value, reason in (
                ("-1", "負"),
                ("1.0", "整数"),
                ("1e3", "整数"),
                ("true", "整数"),
                ("1_0", "整数"),
                ("１２", "整数"),
                ("١٢", "整数"),
                ("", "欠落"),
                ("btime", "整数"),
            ):
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ValueError) as caught:
                        self.parse(f"mystery {key} {value}")
                    self.assertIn(key, str(caught.exception))
                    self.assertIn(reason, str(caught.exception))
            with self.subTest(key=key, duplicate=True):
                with self.assertRaises(ValueError) as caught:
                    self.parse(f"{key} 0 extra {key} 0")
                self.assertIn(key, str(caught.exception))
                self.assertIn("重複", str(caught.exception))
        for text, missing in (
            ("btime 0", "wtime"),
            ("wtime 0", "btime"),
            ("byoyomi 0", "btime"),
        ):
            with self.subTest(text=text):
                with self.assertRaises(ValueError) as caught:
                    self.parse(text)
                self.assertIn(missing, str(caught.exception))
                self.assertIn("必須", str(caught.exception))

    def test_rejects_unsupported_go_parameters(self):
        """未対応条件と正の加算を無視せず拒否する。

        探索条件を黙って読み替える誤りと、加算の片側だけの検査を検出する。
        """
        for token in (
            "infinite",
            "ponder",
            "mate",
            "depth",
            "nodes",
            "searchmoves",
            "movetime",
        ):
            for suffix in ("", " 1"):
                with self.subTest(token=token, suffix=suffix):
                    with self.assertRaises(ValueError) as caught:
                        self.parse("mystery " + token + suffix)
                    self.assertIn(token, str(caught.exception))
                    self.assertIn("未対応", str(caught.exception))
        for key in ("binc", "winc"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError) as caught:
                    self.parse(f"{key} 1")
                self.assertIn(key, str(caught.exception))
                self.assertIn("未対応", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            self.parse("btime bad movetime 1")
        self.assertIn("movetime", str(caught.exception))
        self.assertIn("未対応", str(caught.exception))

    def test_accepts_integer_notation_and_large_values(self):
        """符号・先頭0と巨大整数を精度を失わず読む。

        独自上限、float化、正の符号や先頭0を拒否する誤りを検出する。
        """
        for text, expected in (
            ("+0", 0),
            ("00", 0),
            ("-0", 0),
            ("+120000", 120000),
            ("00120000", 120000),
            (str(10**400), 10**400),
        ):
            with self.subTest(text=text):
                clock = self.parse(f"btime {text} wtime {text}")
                self.assertEqual((clock.btime_ms, clock.wtime_ms), (expected, expected))

    def test_selects_budget_for_side_to_move(self):
        """現在手番の時計と注入設定から手計算した期間を返す。

        先手固定、相手側参照、0の未指定扱い、既定設定への置換を検出する。
        """
        prepare = getattr(usi_engine, "_prepare_search_budget", None)
        self.assertIsNotNone(prepare, "予算準備操作が必要です")
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 2000)
        custom = TimeManagementConfig(4, Fraction(3, 2), Fraction(1, 2), 0)
        cases = (
            (
                "btime 600000 wtime 120000 byoyomi 30000",
                Side.SENTE,
                config,
                SearchBudget(30000, 60000),
            ),
            (
                "btime 600000 wtime 120000 byoyomi 30000",
                Side.GOTE,
                config,
                SearchBudget(6000, 12000),
            ),
            ("btime 600000 wtime 0", Side.GOTE, config, SearchBudget(0, 0)),
            (
                "btime 600000 wtime 0 byoyomi 30000",
                Side.GOTE,
                config,
                SearchBudget(21000, 28000),
            ),
            ("btime 0 wtime 0", Side.SENTE, config, SearchBudget(0, 0)),
            (
                "btime 600000 wtime 120000 byoyomi 30000",
                Side.GOTE,
                custom,
                SearchBudget(30000, 45000),
            ),
        )
        for text, side, setting, expected in cases:
            with self.subTest(text=text, side=side, setting=setting):
                self.assertEqual(prepare(self.parse(text), side, setting), expected)
        with patch.object(usi_engine, "calculate_search_budget") as calculate:
            self.assertIsNone(prepare(None, Side.GOTE, config))
            calculate.assert_not_called()
