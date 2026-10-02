"""USI局面コマンドの解析と合法手順の再生を検証する。"""

import unittest

from kaname_shogi.model import (BasicPieceType, Piece, PieceType, Position,
                                Side, Square)
from kaname_shogi.usi_position import parse_usi_position


class UsiPositionTests(unittest.TestCase):
    def test_replays_multiple_ordinary_moves_from_startpos(self):
        """複数の通常手を平手初期局面から順番に再生する。

        最後の一手だけを初期局面へ適用する誤りや、手順数に応じた手番の
        更新漏れを検出する。
        """
        position = parse_usi_position(
            "position startpos moves 7g7f 3c3d 2g2f"
        )

        self.assertIsInstance(position, Position)
        self.assertEqual(position.board.piece_at(Square(7, 6)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(position.board.piece_at(Square(3, 4)),
                         Piece(PieceType.PAWN, Side.GOTE))
        self.assertEqual(position.board.piece_at(Square(2, 6)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(position.side_to_move, Side.GOTE)

    def test_replays_promoting_move_from_startpos(self):
        """成りを含む手順をと金の局面として再現する。

        一手変換で得たpromote指定を局面適用時に落とし、歩のまま残す誤りを
        検出する。
        """
        position = parse_usi_position(
            "position startpos moves 7g7f 3c3d 7f7e 3d3e "
            "7e7d 3e3f 7d7c+"
        )

        self.assertEqual(position.board.piece_at(Square(7, 3)),
                         Piece(PieceType.PRO_PAWN, Side.SENTE))
        self.assertEqual(position.side_to_move, Side.GOTE)

    def test_replays_captured_pawn_drop_from_startpos(self):
        """捕獲で得た歩を次の手番で打つ手順を再現する。

        捕獲した駒の持ち駒化、持ち歩の消費、打ち駒の所有者や手番の
        取り違えを検出する。
        """
        position = parse_usi_position(
            "position startpos moves 1g1f 1c1d 1f1e 1d1e "
            "1i1h 4c4d 1h1e 4d4e P*1d"
        )

        self.assertEqual(position.board.piece_at(Square(1, 4)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(position.board.piece_at(Square(1, 5)),
                         Piece(PieceType.LANCE, Side.SENTE))
        self.assertEqual(position.sente_hand.count(BasicPieceType.PAWN), 0)
        self.assertEqual(position.side_to_move, Side.GOTE)

    def test_rejects_position_without_moves(self):
        """手順を必須にし、初期局面だけのコマンドを拒否する。

        `moves` の欠落や空列を許し、仕様で対象外とした入力を受け入れる誤りを
        検出する。
        """
        for command in (
            "position startpos",
            "position startpos moves",
        ):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    parse_usi_position(command)

    def test_rejects_unsupported_or_malformed_position_commands(self):
        """対象外のSFENや位置コマンドの文法違反を拒否する。

        別のUSIコマンドや `startpos` 以外の局面形式を誤って解析し、開始局面を
        取り違えることを検出する。
        """
        commands = (
            "position sfen ... moves 7g7f",
            "go",
            "position other moves 7g7f",
            "position startpos extra moves 7g7f",
        )
        for command in commands:
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    parse_usi_position(command)

    def test_rejects_unparseable_move_token(self):
        """一手へ変換できないトークンを原因とともに拒否する。

        不正な手を無視して後続手を適用したり、問題箇所を呼び出し側が特定
        できない汎用エラーへ置き換えたりする誤りを検出する。
        """
        with self.assertRaises(ValueError) as context:
            parse_usi_position("position startpos moves 7g7")

        self.assertIn("7g7", str(context.exception))

    def test_rejects_illegal_move(self):
        """表記可能でも平手初期局面から不合法な一手を拒否する。

        USI表記の変換だけで合法性も満たしたと誤認し、二マス進む歩を局面へ
        適用することを検出する。
        """
        with self.assertRaises(ValueError) as context:
            parse_usi_position("position startpos moves 7g7e")

        self.assertIn("7g7e", str(context.exception))


if __name__ == "__main__":
    unittest.main()
