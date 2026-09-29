"""CLI実行入口の実プロセス境界を限定的なスモークテストで確認する。"""

from pathlib import Path
import subprocess
import sys
import unittest


class CliEntrypointSmokeTests(unittest.TestCase):
    def test_cli_exits_from_game_mode_menu_on_eof(self):
        """CLIは対局形式メニューでEOFなら、対局を始めず終了する。

        実プロセスで起動し、入口のメニュー・入力終了・対局開始前に盤面を表示しない
        ことを確認する。
        """
        result = subprocess.run(
            [sys.executable, "-m", "kaname_shogi"],
            cwd=Path(__file__).resolve().parents[1],
            input="", capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "対局形式を選んでください（1: 人間対人間、2: 人間対コンピュータ、"
            "3: コンピュータ対コンピュータ）:\n"
            "入力を終了しました。\n",
        )
        self.assertEqual(result.stderr, "")
