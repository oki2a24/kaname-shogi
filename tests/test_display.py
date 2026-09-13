"""表示の筋段・所有者の逆転とCLIの出力漏れを検出する。"""

from pathlib import Path
import subprocess
import sys
import unittest

from kaname_shogi.display import render_position
from kaname_shogi.model import Side, create_initial_position


EXPECTED = """手番：先手
+：先手、-：後手

    9   8   7   6   5   4   3   2   1
一 -香 -桂 -銀 -金 -玉 -金 -銀 -桂 -香
二  ・ -飛  ・  ・  ・  ・  ・ -角  ・
三 -歩 -歩 -歩 -歩 -歩 -歩 -歩 -歩 -歩
四  ・  ・  ・  ・  ・  ・  ・  ・  ・
五  ・  ・  ・  ・  ・  ・  ・  ・  ・
六  ・  ・  ・  ・  ・  ・  ・  ・  ・
七 +歩 +歩 +歩 +歩 +歩 +歩 +歩 +歩 +歩
八  ・ +角  ・  ・  ・  ・  ・ +飛  ・
九 +香 +桂 +銀 +金 +王 +金 +銀 +桂 +香"""


class DisplayTests(unittest.TestCase):
    def test_initial_position_matches_full_display(self):
        """初期配置を先手視点で筋段・所有者付きで表示する。

        固定した全文を使い、保存順の流用や飛角・王玉の表示違いを検出する。
        """
        self.assertEqual(render_position(create_initial_position()), EXPECTED)

    def test_turn_label_follows_position(self):
        """後手番の局面には「手番：後手」と表示する。

        先手の表示への固定化を検出し、手番以外の表示が変わらないことも確認する。
        """
        position = create_initial_position()
        position.side_to_move = Side.GOTE
        self.assertEqual(render_position(position),
                         EXPECTED.replace("手番：先手", "手番：後手", 1))

    def test_cli_prints_initial_position_and_exits(self):
        """CLIは初期配置を出力し、エラーなく終了する。

        実プロセスで起動し、入口の接続・末尾改行・不要なエラー出力を確認する。
        """
        result = subprocess.run(
            [sys.executable, "-m", "kaname_shogi"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, EXPECTED + "\n")
        self.assertEqual(result.stderr, "")
