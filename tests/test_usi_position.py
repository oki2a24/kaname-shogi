"""USI局面コマンドの解析と合法手順の再生を検証する。"""

import unittest

from kaname_shogi.model import (BasicPieceType, Piece, PieceType, Position,
                                Side, Square, create_initial_position)
from kaname_shogi.sfen import SfenPosition
from kaname_shogi.usi_position import parse_usi_position


class UsiPositionTests(unittest.TestCase):
    def test_replays_multiple_ordinary_moves_from_startpos(self):
        """複数の通常手を平手初期局面から順番に再生する。

        最後の一手だけを初期局面へ適用する誤りや、手順数に応じた手番の
        更新漏れを検出する。
        """
        result = parse_usi_position(
            "position startpos moves 7g7f 3c3d 2g2f"
        )
        position = result.position

        self.assertIsInstance(result, SfenPosition)
        self.assertIsInstance(position, Position)
        self.assertEqual(result.move_number, 4)
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
        result = parse_usi_position(
            "position startpos moves 7g7f 3c3d 7f7e 3d3e "
            "7e7d 3e3f 7d7c+"
        )
        position = result.position

        self.assertEqual(result.move_number, 8)
        self.assertEqual(position.board.piece_at(Square(7, 3)),
                         Piece(PieceType.PRO_PAWN, Side.SENTE))
        self.assertEqual(position.side_to_move, Side.GOTE)

    def test_replays_captured_pawn_drop_from_startpos(self):
        """捕獲で得た歩を次の手番で打つ手順を再現する。

        捕獲した駒の持ち駒化、持ち歩の消費、打ち駒の所有者や手番の
        取り違えを検出する。
        """
        result = parse_usi_position(
            "position startpos moves 1g1f 1c1d 1f1e 1d1e "
            "1i1h 4c4d 1h1e 4d4e P*1d"
        )
        position = result.position

        self.assertEqual(result.move_number, 10)
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

    def test_parses_sfen_without_moves(self):
        """SFENを指し手なしで受け取り、局面と元の手数を返す。

        SFEN単独指定を拒否したり、USI境界でSFEN手数を失う誤りを検出する。
        """
        result = parse_usi_position(
            "position sfen lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/"
            "1B5R1/LNSGKGSNL b - 17"
        )

        self.assertEqual(result.move_number, 17)
        expected = create_initial_position()
        self.assertEqual(result.position.side_to_move, expected.side_to_move)
        for file in range(1, 10):
            for rank in range(1, 10):
                square = Square(file, rank)
                with self.subTest(file=file, rank=rank):
                    self.assertEqual(result.position.board.piece_at(square),
                                     expected.board.piece_at(square))

    def test_replays_moves_from_sfen_and_advances_move_number(self):
        """SFEN局面から複数手を再生し、手数を指し手数だけ進める。

        初期局面へ差し替えたり、盤面と手数で異なる手順数を数える誤りを検出する。
        """
        result = parse_usi_position(
            "position sfen lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/"
            "1B5R1/LNSGKGSNL b - 17 moves 7g7f 3c3d"
        )

        self.assertEqual(result.move_number, 19)
        self.assertEqual(result.position.board.piece_at(Square(7, 6)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(result.position.board.piece_at(Square(3, 4)),
                         Piece(PieceType.PAWN, Side.GOTE))
        self.assertEqual(result.position.side_to_move, Side.SENTE)

    def test_replays_moves_from_sfen_without_move_number(self):
        """手数欄省略SFENの既定値1から指し手分だけ数える。

        省略時の既定値を0や未設定にしたり、盤面への適用と手数更新を分離する誤りを検出する。
        """
        result = parse_usi_position(
            "position sfen lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/"
            "1B5R1/LNSGKGSNL b - moves 7g7f"
        )

        self.assertEqual(result.move_number, 2)
        self.assertEqual(result.position.board.piece_at(Square(7, 6)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(result.position.side_to_move, Side.GOTE)

    def test_replays_drop_using_sfen_hand(self):
        """SFENの持ち歩をUSIの駒打ちに使い、持ち駒を消費する。

        SFEN起点でも既存の合法手適用を使い、着手後の手数を更新することを確認する。
        """
        result = parse_usi_position(
            "position sfen 4k4/9/9/9/9/9/9/9/4K4 b P 17 moves P*5e"
        )

        self.assertEqual(result.position.board.piece_at(Square(5, 5)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(result.position.sente_hand.count(BasicPieceType.PAWN), 0)
        self.assertEqual(result.position.side_to_move, Side.GOTE)
        self.assertEqual(result.move_number, 18)

    def test_rejects_sfen_with_empty_moves(self):
        """moves区切りがある場合は少なくとも1手を要求する。

        空の指し手列をSFEN単独指定と曖昧に扱い、USI入力の誤りを隠すことを検出する。
        """
        with self.assertRaises(ValueError):
            parse_usi_position(
                "position sfen lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/"
                "1B5R1/LNSGKGSNL b - 1 moves"
            )

    def test_rejects_unsupported_or_malformed_position_commands(self):
        """対象外のSFENや位置コマンドの文法違反を拒否する。

        別のUSIコマンドや `startpos` 以外の局面形式を誤って解析し、開始局面を
        取り違えることを検出する。
        """
        commands = (
            "position sfen 9/8 b - 1",
            "position sfen",
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
