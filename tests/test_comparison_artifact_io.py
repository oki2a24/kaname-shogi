"""比較実験のJSON成果物に使う厳密な共通入出力を確認する。"""

import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    artifact_io_module = importlib.import_module("kaname_shogi.comparison_artifact_io")
except ModuleNotFoundError as error:
    if error.name != "kaname_shogi.comparison_artifact_io":
        raise
    artifact_io_module = None

decode_object = getattr(artifact_io_module, "decode_object", None)
write_new_json = getattr(artifact_io_module, "write_new_json", None)


class ComparisonArtifactIoTests(unittest.TestCase):
    def _require_implementation(self):
        """共通JSON入出力の未実装を振る舞い不足として示す。"""
        self.assertIsNotNone(decode_object, "厳密なJSON読込が未実装です")
        self.assertIsNotNone(write_new_json, "新規限定JSON保存が未実装です")

    def test_decode_object_accepts_finite_json_object(self):
        """有限値を含むUTF-8 JSONオブジェクトを辞書へ変換する。

        配列や数値をオブジェクトと取り違えず、通常の有限値を拒否する誤りを検出する。
        """
        self._require_implementation()

        payload = decode_object(
            '{"outer":{"items":[1,true,null]},"name":"将棋"}'.encode(),
            context="試験",
        )

        self.assertEqual(payload, {"outer": {"items": [1, True, None]}, "name": "将棋"})

    def test_decode_object_rejects_duplicate_keys_in_every_object(self):
        """トップ・入れ子両方の同名キーをJSONとして拒否する。

        json.loadsの後勝ちで重複値を隠し、異なる条件を読み込む誤りを検出する。
        """
        self._require_implementation()
        for raw in (
            b'{"name":1,"name":2}',
            b'{"outer":{"name":1,"name":2}}',
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    decode_object(raw, context="試験")

    def test_decode_object_rejects_non_object_non_utf8_and_non_finite_values(self):
        """トップ配列・不正UTF-8・NaNと正負Infinityを拒否する。

        JSON拡張値や誤ったトップ階層を有効な成果物として受け入れる誤りを検出する。
        """
        self._require_implementation()
        invalid_values = (
            b"[]",
            b"\xff",
            b'{"value":NaN}',
            b'{"value":Infinity}',
            b'{"value":-Infinity}',
            b'{"outer":{"value":NaN}}',
            b'{"outer":{"value":1e999}}',
        )
        for raw in invalid_values:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    decode_object(raw, context="試験")

    def test_write_new_json_creates_once_and_never_overwrites(self):
        """JSONを新規保存し、既存ファイル・ディレクトリ・親欠落を保護する。

        保存先の上書きや、存在しない親の暗黙生成を行う誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "result.json"
            payload = {"format": "fixture-v1", "value": "将棋"}

            write_new_json(target, payload)

            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), payload)
            with self.assertRaises(FileExistsError):
                write_new_json(target, {"changed": True})
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), payload)
            with self.assertRaises((FileExistsError, IsADirectoryError, OSError)):
                write_new_json(Path(directory), payload)
            with self.assertRaises(FileNotFoundError):
                write_new_json(Path(directory) / "missing" / "result.json", payload)

    def test_write_new_json_serializes_before_creating_the_output(self):
        """JSON化不能な値は出力ファイルを作る前に拒否する。

        部分的な成果物が正規の一覧に見える状態で残る誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "invalid.json"

            with self.assertRaises((TypeError, ValueError)):
                write_new_json(target, {"value": object()})

            self.assertFalse(target.exists())

    def test_write_new_json_removes_owned_partial_file_and_reports_cleanup_failure(
        self,
    ):
        """書込失敗時は作成した途中ファイルを除去し、除去故障も診断する。

        既存ファイルを消さず、保存途中の空・部分ファイルを成果物として残す誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "partial.json"
            original_open = Path.open

            class FailingWriter:
                """作成済み保存先への書込を故障させる。"""

                def __enter__(self):
                    return self

                def __exit__(self, exception_type, exception, traceback):
                    del exception_type, exception, traceback
                    return False

                def write(self, raw):
                    del raw
                    raise OSError("書込失敗")

            def create_then_fail(path, mode="r", *args, **kwargs):
                if Path(path) == target and mode == "xb":
                    with original_open(path, mode):
                        pass
                    return FailingWriter()
                return original_open(path, mode, *args, **kwargs)

            with patch.object(Path, "open", create_then_fail):
                with self.assertRaisesRegex(OSError, "書込失敗"):
                    write_new_json(target, {"value": 1})
            self.assertFalse(target.exists())

            with patch.object(Path, "open", create_then_fail):
                with patch.object(Path, "unlink", side_effect=OSError("除去失敗")):
                    with self.assertRaisesRegex(OSError, "除去失敗"):
                        write_new_json(target, {"value": 1})
            self.assertTrue(target.exists())
            target.unlink()
