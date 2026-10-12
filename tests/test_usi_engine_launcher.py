"""ShogiHome用USIエンジン起動ファイルの実プロセス境界を確認する。"""

import os
import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = PROJECT_ROOT / "kaname-shogi-usi"


class UsiEngineLauncherTests(unittest.TestCase):
    def test_launcher_advertises_difficulty_combo(self):
        """実行ファイルのusi応答でDifficulty comboをusiok前に通知する。

        ShogiHomeに登録する起動境界でoption応答が欠落したり、順序がずれる誤りを
        検出する。
        """
        self.assertTrue(LAUNCHER.is_file(), "USIエンジンの実行ファイルがありません")
        self.assertTrue(
            os.access(LAUNCHER, os.X_OK), "USIエンジンの実行権限がありません"
        )

        result = subprocess.run(
            [str(LAUNCHER)],
            cwd=PROJECT_ROOT,
            input="usi\nquit\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "id name kaname-shogi\n"
            "id author kaname-shogi project\n"
            "option name Difficulty type combo default Random var Random var Material var TwoPlyMaterial\n"
            "usiok\n",
        )
        self.assertEqual(result.stderr, "")

    def test_launcher_propagates_usi_engine_error_status(self):
        """不正なUSI入力時の異常終了コードを呼び出し側へ伝える。

        mainの戻り値を破棄し、エラーを成功終了として報告する誤りを検出する。
        """
        self.assertTrue(LAUNCHER.is_file(), "USIエンジンの実行ファイルがありません")
        self.assertTrue(
            os.access(LAUNCHER, os.X_OK), "USIエンジンの実行権限がありません"
        )

        result = subprocess.run(
            [str(LAUNCHER)],
            cwd=PROJECT_ROOT,
            input="position sfen invalid\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("USIエンジンエラー:", result.stderr)

    def test_launcher_loads_config_from_other_cwd(self):
        """別cwdからの起動でも同梱設定を読んでUSI応答する。

        設定をcwd相対で探す誤りを実入口で検出する。
        """
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            result = subprocess.run(
                [str(LAUNCHER)],
                cwd=directory,
                input="usi\nquit\n",
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "id name kaname-shogi",
                "id author kaname-shogi project",
                "option name Difficulty type combo default Random var Random var Material var TwoPlyMaterial",
                "usiok",
            ],
        )

    def test_launcher_rejects_bad_config_before_usi(self):
        """隔離した実入口で設定故障をUSI応答前に診断する。

        読込不能や不正JSONの無断代替、起動時応答の先行を検出する。
        """
        import shutil
        from tempfile import TemporaryDirectory

        for fault in ("missing", "syntax", "key", "encoding", "directory"):
            with self.subTest(fault=fault), TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copytree(
                    PROJECT_ROOT / "kaname_shogi",
                    root / "kaname_shogi",
                    ignore=shutil.ignore_patterns("__pycache__"),
                )
                launcher = root / "kaname-shogi-usi"
                shutil.copy2(LAUNCHER, launcher)
                (root / "config").mkdir()
                config = root / "config/time-management.json"
                if fault == "syntax":
                    config.write_text("{", encoding="utf-8")
                elif fault == "key":
                    config.write_text("{}", encoding="utf-8")
                elif fault == "encoding":
                    config.write_bytes(b"\xff")
                elif fault == "directory":
                    config.mkdir()
                result = subprocess.run(
                    [str(launcher)],
                    cwd=root,
                    input="usi\nquit\n",
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=5,
                    check=False,
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn("USIエンジンエラー:", result.stderr)
                self.assertIn(str(config), result.stderr)
                self.assertTrue(result.stderr.partition(str(config))[2].strip())
