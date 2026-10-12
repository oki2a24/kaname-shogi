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
