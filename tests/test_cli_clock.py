"""CLI対局時計の設定・残り時間更新・切り捨てない時間切れを確認する。"""

import importlib
import unittest

from kaname_shogi.model import Side

try:
    cli_clock = importlib.import_module("kaname_shogi.cli_clock")
except ModuleNotFoundError:
    cli_clock = None


class CliClockTests(unittest.TestCase):
    def require_clock_api(self):
        """時計APIが未実装なら、import失敗ではなく不足契約として失敗する。"""
        self.assertIsNotNone(
            cli_clock,
            "CLI時計の設定・状態APIが未実装です（期待する振る舞いのテスト）",
        )
        return cli_clock

    def test_rejects_invalid_clock_values(self):
        """時計設定と残り時間は整数の範囲外を拒否する。

        boolの整数扱い、負値・小数の許容、残り時間の初期値超過を検出する。
        """
        module = self.require_clock_api()
        settings_type = module.CliClockSettings
        clock_type = module.CliClock

        for initial, byoyomi in (
            (True, 1),
            (-1, 1),
            (1.0, 1),
            ("1", 1),
            (0, 0),
            (0, False),
        ):
            with self.subTest(initial=initial, byoyomi=byoyomi):
                with self.assertRaises(ValueError):
                    settings_type(initial, byoyomi)

        valid = settings_type(5, 30)
        for sente, gote in (
            (True, 0),
            (-1, 0),
            (0.0, 0),
            (0, "0"),
            (5_000_001, 0),
            (0, 5_000_001),
        ):
            with self.subTest(sente=sente, gote=gote):
                with self.assertRaises(ValueError):
                    clock_type(valid, sente, gote)

        self.assertEqual(settings_type(0, 30).initial_time_ms, 0)
        self.assertEqual(
            clock_type(valid, 5_000_000, 0).sente_remaining_ns,
            5_000_000,
        )

    def test_updates_only_moving_side_without_carrying_byoyomi(self):
        """一手の消費は手番側だけから引き、次の秒読み値を維持する。

        秒読みの使い残しを持ち越す誤りと、相手側の時計を減らす誤りを検出する。
        """
        module = self.require_clock_api()
        settings = module.CliClockSettings(5_000, 30_000)
        clock = module.CliClock(settings, 5_000_000_000, 3_000_000_000)

        after = clock.after_turn(Side.SENTE, 20_000_000_000)

        self.assertEqual(after.sente_remaining_ns, 0)
        self.assertEqual(after.gote_remaining_ns, 3_000_000_000)
        self.assertEqual(after.settings.byoyomi_ms, 30_000)
        self.assertFalse(after.is_expired(Side.SENTE, 29_999_999_999))

        reversed_after = after.after_turn(Side.GOTE, 1_000_000_000)
        self.assertEqual(reversed_after.sente_remaining_ns, 0)
        self.assertEqual(reversed_after.gote_remaining_ns, 2_000_000_000)

    def test_preserves_submillisecond_remainders(self):
        """時計の残り値はmsへ丸めずnsの端数を保持する。

        手番ごとのms切り捨てで残り時間が失われる誤りを検出する。
        """
        module = self.require_clock_api()
        settings = module.CliClockSettings(2, 1)
        clock = module.CliClock(settings, 1_000_001, 1_000_001)

        after_one = clock.after_turn(Side.SENTE, 1)
        after_two = after_one.after_turn(Side.SENTE, 1)

        self.assertEqual(after_one.sente_remaining_ns, 1_000_000)
        self.assertEqual(after_two.sente_remaining_ns, 999_999)

    def test_expiry_includes_exact_nanosecond_boundary(self):
        """時間切れは持ち時間と秒読みの合計に達した時点で成立する。

        境界の等号を見落とす誤りと、秒読み0の期限を無制限にする誤りを検出する。
        """
        module = self.require_clock_api()
        settings = module.CliClockSettings(5_000, 30_000)
        clock = module.CliClock(settings, 5_000_000_000, 3_000_000_000)

        self.assertFalse(clock.is_expired(Side.SENTE, 34_999_999_999))
        self.assertTrue(clock.is_expired(Side.SENTE, 35_000_000_000))
        self.assertTrue(clock.is_expired(Side.SENTE, 35_000_000_001))

        zero_clock = module.CliClock(module.CliClockSettings(1, 0), 0, 0)
        self.assertTrue(zero_clock.is_expired(Side.SENTE, 0))

    def test_rejects_negative_elapsed_without_mutation(self):
        """逆行した経過値は拒否し、元の時計データを変えない。

        時計契約故障を時間切れ・残り時間増加へ読み替える誤りを検出する。
        """
        module = self.require_clock_api()
        clock = module.CliClock(module.CliClockSettings(5, 30), 5_000_000, 4_000_000)

        with self.assertRaises(ValueError):
            clock.after_turn(Side.SENTE, -1)
        with self.assertRaises(ValueError):
            clock.is_expired(Side.SENTE, -1)

        self.assertEqual(clock.sente_remaining_ns, 5_000_000)
        self.assertEqual(clock.gote_remaining_ns, 4_000_000)


if __name__ == "__main__":
    unittest.main()
