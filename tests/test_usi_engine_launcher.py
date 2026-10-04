"""ShogiHome用USIエンジン起動ファイルの実プロセス境界を確認する。"""

import os
from pathlib import Path
import subprocess
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = PROJECT_ROOT / "kaname-shogi-usi"


class UsiEngineLauncherTests(unittest.TestCase):
    def test_launcher_starts_usi_engine(self):
        """実行ファイルを直接起動するとUSI初期化へ応答する。

        ShogiHomeに登録する実行ファイルから標準入出力で既存エンジンを起動できることを確認し、
        起動不能やUSI初期応答の欠落を検出する。
        """
        self.assertTrue(LAUNCHER.is_file(), "USIエンジンの実行ファイルがありません")
        self.assertTrue(os.access(LAUNCHER, os.X_OK), "USIエンジンの実行権限がありません")

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
            "usiok\n",
        )
        self.assertEqual(result.stderr, "")

    def test_launcher_propagates_usi_engine_error_status(self):
        """不正なUSI入力時の異常終了コードを呼び出し側へ伝える。

        mainの戻り値を破棄し、エラーを成功終了として報告する誤りを検出する。
        """
        self.assertTrue(LAUNCHER.is_file(), "USIエンジンの実行ファイルがありません")
        self.assertTrue(os.access(LAUNCHER, os.X_OK), "USIエンジンの実行権限がありません")

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
