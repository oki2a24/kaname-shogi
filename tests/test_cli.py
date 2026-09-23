"""CLIの指し手解析と対局進行を検証する。"""

import unittest

from kaname_shogi import cli
from kaname_shogi.model import BasicPieceType, Square


class CommandParsingTests(unittest.TestCase):
    def test_parses_move_and_drop_with_halfwidth_or_fullwidth_input(self):
        """半角・全角の座標と空白を、移動・駒打ちの指示へ変換する。"""
        move = cli.parse_command("move　７　７　７　６")
        promoted = cli.parse_command("move 2 2 2 1 +")
        drop = cli.parse_command("drop　歩　５　５")

        self.assertEqual((move.source, move.destination, move.promote),
                         (Square(7, 7), Square(7, 6), False))
        self.assertEqual((promoted.source, promoted.destination,
                          promoted.promote),
                         (Square(2, 2), Square(2, 1), True))
        self.assertEqual((drop.piece_type, drop.destination),
                         (BasicPieceType.PAWN, Square(5, 5)))

    def test_rejects_invalid_command_format(self):
        """未知の操作語・記号・引数・座標を入力形式エラーとして拒否する。"""
        invalid_commands = (
            "",
            "ｍｏｖｅ 7 7 7 6",
            "move 7 7 7 6 ＋",
            "move 7 7 7",
            "move 7 7 7 6 extra",
            "drop 王 5 5",
            "drop 歩 10 5",
        )

        for command in invalid_commands:
            with self.subTest(command=command):
                with self.assertRaisesRegex(ValueError,
                                             "入力形式が正しくありません。"):
                    cli.parse_command(command)
