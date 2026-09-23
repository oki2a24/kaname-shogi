"""表示の筋段・所有者の逆転とCLIの出力漏れを検出する。"""

from pathlib import Path
import subprocess
import sys
import unittest

from kaname_shogi.display import render_position
from kaname_shogi.model import (Board, Piece, PieceType, Position, Side,
                                Square, create_initial_position)


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
    def test_renders_all_promoted_piece_names(self):
        """成駒6種を含む局面を、KeyErrorにせず名称付きで表示する。"""
        position = Position(Board(), Side.SENTE)
        promoted_pieces = (
            (Square(1, 1), PieceType.PRO_PAWN),
            (Square(2, 1), PieceType.PRO_LANCE),
            (Square(3, 1), PieceType.PRO_KNIGHT),
            (Square(4, 1), PieceType.PRO_SILVER),
            (Square(5, 1), PieceType.HORSE),
            (Square(6, 1), PieceType.DRAGON),
        )
        for square, piece_type in promoted_pieces:
            position.board.set_piece(square, Piece(piece_type, Side.SENTE))

        rendered = render_position(position)

        for name in ("と", "成香", "成桂", "成銀", "馬", "竜"):
            self.assertIn("+" + name, rendered)

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

    def test_cli_starts_game_and_exits_on_eof(self):
        """CLIは初期配置を表示し、EOFで終了メッセージを出して終了する。

        実プロセスで起動し、入口の接続・入力終了・不要なエラー出力を確認する。
        """
        result = subprocess.run(
            [sys.executable, "-m", "kaname_shogi"],
            cwd=Path(__file__).resolve().parents[1],
            input="", capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            EXPECTED + "\n"
            "指し手を入力してください（例: move 7 7 7 6）:\n"
            "入力を終了しました。\n",
        )
        self.assertEqual(result.stderr, "")
