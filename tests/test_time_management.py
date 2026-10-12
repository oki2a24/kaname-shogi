"""時間設定と整数msの予算計算の契約を確認する。"""

import unittest
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory

from kaname_shogi import time_management as tm

VALID = '{"allocation_turns":20,"maximum_multiplier":2,"byoyomi_target_ratio":0.75,"response_margin_ms":2000}'


class TimeManagementTests(unittest.TestCase):
    def load_text(self, text):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(text, encoding="utf-8")
            return tm.load_time_management_config(path)

    def test_loads_provisional_config(self):
        """四設定を正確な不変データとして読む。

        読込結果の欠落、倍率・割合の取り違え、既定値へのすり替えを検出する。
        """
        config = self.load_text(VALID)
        self.assertIsNotNone(config)
        self.assertEqual(config.allocation_turns, 20)
        self.assertEqual(config.maximum_multiplier, Fraction(2))
        self.assertEqual(config.byoyomi_target_ratio, Fraction(3, 4))
        self.assertEqual(config.response_margin_ms, 2000)

    def test_rejects_invalid_config_values(self):
        """型と許容範囲に反する設定を拒否する。

        boolの数値扱い、境界の包含間違い、係数文字列の暗黙変換を検出する。
        """
        import json

        cases = {
            "allocation_turns": [0, -1, 1.0, True, False, "20", None, [], {}],
            "maximum_multiplier": [1, 0, -1, True, False, "2", None, [], {}],
            "byoyomi_target_ratio": [0, 1, -1, True, False, "0.75", None, [], {}],
            "response_margin_ms": [-1, 0.0, True, False, "2000", None, [], {}],
        }
        for key, values in cases.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    payload = json.loads(VALID)
                    payload[key] = value
                    with self.assertRaises(ValueError):
                        self.load_text(json.dumps(payload))

    def test_rejects_invalid_direct_config(self):
        """直接構築でも設定の型と範囲を強制する。

        読込経路だけで検査し計算側へ不正な設定が流れる誤りを検出する。
        """
        valid = [20, Fraction(2), Fraction(3, 4), 2000]
        for index, invalid in enumerate(
            [
                [0, -1, True, 1.0],
                [Fraction(1), 2, 2.0],
                [Fraction(0), Fraction(1), 0.75],
                [-1, True, 0.0],
            ]
        ):
            for value in invalid:
                with self.subTest(index=index, value=value):
                    fields = valid.copy()
                    fields[index] = value
                    with self.assertRaises(ValueError):
                        tm.TimeManagementConfig(*fields)

    def test_rejects_invalid_json_structure(self):
        """未知・欠落・重複やJSON外の構文を拒否する。

        辞書化で重複を失うこと、四項目以外を受け入れることを検出する。
        """
        import json

        cases = [
            "[]",
            "null",
            "true",
            "2",
            '"text"',
            VALID + "{}",
            VALID + ",",
            "//comment\n" + VALID,
        ]
        for key in json.loads(VALID):
            payload = json.loads(VALID)
            del payload[key]
            cases.append(json.dumps(payload))
            value = json.loads(VALID)[key]
            cases.append(VALID[:-1] + ',"' + key + '":' + json.dumps(value) + "}")
        cases.append(VALID[:-1] + ',"extra":1}')
        cases.append(VALID[:-1] + ",}")
        for constant in ("NaN", "Infinity", "-Infinity"):
            cases.append(
                VALID.replace(
                    '"maximum_multiplier":2', '"maximum_multiplier":' + constant
                )
            )
        for text in cases:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    self.load_text(text)

    def test_accepts_config_boundaries(self):
        """境界近傍と巨大有限係数を十進表記通りに読む。

        floatによる1への丸め、巨大値の無限大化、独自上限を検出する。
        """
        config = self.load_text(
            '{"allocation_turns":1,"maximum_multiplier":1.0000000000000000001,"byoyomi_target_ratio":0.0000000000000000001,"response_margin_ms":0}'
        )
        self.assertEqual(
            config.maximum_multiplier,
            Fraction(10000000000000000001, 10000000000000000000),
        )
        self.assertEqual(config.byoyomi_target_ratio, Fraction(1, 10000000000000000000))
        self.assertEqual((config.allocation_turns, config.response_margin_ms), (1, 0))
        config = self.load_text(
            VALID.replace(":2,", ":1e400,").replace(":0.75,", ":0.9999999999999999999,")
        )
        self.assertEqual(config.maximum_multiplier, Fraction(10**400))
        self.assertEqual(
            config.byoyomi_target_ratio,
            Fraction(9999999999999999999, 10000000000000000000),
        )

    def test_default_path_is_independent_of_cwd(self):
        """別作業ディレクトリからもGit管理設定を読む。

        cwd相対の設定参照、ファイル不在時の無断代替を検出する。
        """
        import os

        previous = Path.cwd()
        try:
            with TemporaryDirectory() as directory:
                os.chdir(directory)
                try:
                    config = tm.load_time_management_config()
                except OSError as error:
                    self.fail(f"既定設定を読めない: {error}")
                self.assertEqual(
                    config,
                    tm.TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 2000),
                )
        finally:
            os.chdir(previous)

    def test_reloads_explicit_file_without_mutating_old_config(self):
        """明示ファイルの更新は次回読込だけに反映する。

        隠れたキャッシュと過去設定への変更伝播を検出する。
        """
        from dataclasses import FrozenInstanceError

        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(VALID, encoding="utf-8")
            original = tm.load_time_management_config(path)
            path.write_text(VALID.replace(":20,", ":7,"), encoding="utf-8")
            updated = tm.load_time_management_config(path)
            self.assertEqual(updated.allocation_turns, 7)
            self.assertEqual(original.allocation_turns, 20)
            with self.assertRaises(FrozenInstanceError):
                original.allocation_turns = 7

    def test_reports_config_read_errors(self):
        """読込不能と不正文字コードをパス付き例外にする。

        読込失敗の隠蔽と診断からの対象パス欠落を検出する。
        """
        from unittest.mock import patch

        with TemporaryDirectory() as directory:
            for path in (Path(directory), Path(directory) / "missing.json"):
                with self.subTest(path=path), self.assertRaises(OSError) as caught:
                    tm.load_time_management_config(path)
                self.assertIn(str(path), str(caught.exception))
            path = Path(directory) / "invalid.json"
            path.write_bytes(b"\xff")
            with self.assertRaises(ValueError) as caught:
                tm.load_time_management_config(path)
            self.assertIn(str(path), str(caught.exception))
            with patch.object(Path, "open", side_effect=OSError("読取故障")):
                with self.assertRaises(OSError) as caught:
                    tm.load_time_management_config(path)
            self.assertIn(str(path), str(caught.exception))
            self.assertIn("読取故障", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            self.load_text(VALID.replace(":20,", ":0,"))
        self.assertIn("allocation_turns", str(caught.exception))

    def test_calculates_budget_examples(self):
        """手計算した期間と上限を整数msで返す。

        分岐・切捨て順序・上限制限・float丸め・巨大値の誤計算を検出する。
        """
        default = tm.TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 2000)
        cases = [
            (default, 600000, 30000, 30000, 60000),
            (default, 60000, 30000, 3000, 6000),
            (default, 10000, 30000, 500, 1000),
            (default, 1, 30000, 0, 0),
            (default, 0, 30000, 21000, 28000),
            (default, 0, 1999, 0, 0),
            (default, 0, 2000, 0, 0),
            (default, 0, 2001, 0, 1),
            (default, 0, 0, 0, 0),
            (default, 100, 0, 0, 0),
            (default, 100, 1903, 3, 3),
            (
                tm.TimeManagementConfig(3, Fraction(3, 2), Fraction(3, 4), 0),
                11,
                0,
                3,
                4,
            ),
            (
                tm.TimeManagementConfig(1, Fraction(2), Fraction(29, 100), 0),
                0,
                100,
                29,
                100,
            ),
            (
                tm.TimeManagementConfig(1, Fraction(10**400), Fraction(3, 4), 0),
                10,
                0,
                10,
                10,
            ),
            (
                tm.TimeManagementConfig(1, Fraction(2), Fraction(3, 4), 0),
                10**400,
                0,
                10**400,
                10**400,
            ),
        ]
        for config, remaining, byoyomi, target, maximum in cases:
            with self.subTest(remaining=remaining, byoyomi=byoyomi, config=config):
                try:
                    result = tm.calculate_search_budget(remaining, byoyomi, config)
                except ValueError:
                    self.fail("正常入力で予算計算が例外になった")
                self.assertIsNotNone(result)
                self.assertEqual(
                    (result.target_ms, result.maximum_ms), (target, maximum)
                )
                self.assertIs(type(result.target_ms), int)
                self.assertIs(type(result.maximum_ms), int)

    def test_rejects_invalid_clock_values(self):
        """非負整数以外の時計入力をValueErrorで拒否する。

        bool・小数の暗黙利用と負時間の0扱いを検出する。
        """
        config = tm.load_time_management_config()
        for index in (0, 1):
            for value in (-1, True, 1.0, "1", None):
                clocks = [100, 100]
                clocks[index] = value
                with (
                    self.subTest(index=index, value=value),
                    self.assertRaises(ValueError),
                ):
                    tm.calculate_search_budget(*clocks, config)

    def test_rejects_invalid_budget_data(self):
        """不正な予算データを直接構築でも拒否する。

        負予算・目標上限逆転・整数以外の値の流出を検出する。
        """
        for fields in [
            (-1, 0),
            (0, -1),
            (2, 1),
            (True, 1),
            (0, True),
            (0.0, 1),
            (0, 1.0),
        ]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                tm.SearchBudget(*fields)

    def test_keeps_allocation_turns_fixed(self):
        """反復計算でも固定分母と設定を変えない。

        手番カウンタを内部に持ち配分を増やす誤りを検出する。
        """
        from dataclasses import FrozenInstanceError

        config = tm.load_time_management_config()
        for _ in range(3):
            result = tm.calculate_search_budget(60000, 30000, config)
            self.assertEqual((result.target_ms, result.maximum_ms), (3000, 6000))
            self.assertEqual(config.allocation_turns, 20)
        with self.assertRaises(FrozenInstanceError):
            result.target_ms = 1
