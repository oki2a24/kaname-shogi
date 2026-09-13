"""筋段の取り違え、不正座標、盤面の共有を検出する。"""

from dataclasses import FrozenInstanceError
import unittest

from kaname_shogi.model import Board, Piece, PieceType, Side, Square
from kaname_shogi.model import create_initial_position


class SquareTests(unittest.TestCase):
    def test_known_squares_have_expected_indices(self):
        for file, rank, expected in [(1, 1, 0), (1, 9, 8), (9, 1, 72),
                                     (9, 9, 80), (7, 6, 59)]:
            with self.subTest(file=file, rank=rank):
                self.assertEqual(Square(file, rank).to_index(), expected)

    def test_all_squares_cover_81_indices(self):
        indices = [Square(file, rank).to_index()
                   for file in range(1, 10) for rank in range(1, 10)]
        self.assertEqual(sorted(indices), list(range(81)))

    def test_invalid_coordinates_are_rejected(self):
        for value in [0, 10, -1, 1.0, "1", None, True, False]:
            for file, rank in [(value, 1), (1, value)]:
                with self.subTest(file=file, rank=rank):
                    with self.assertRaises(ValueError):
                        Square(file, rank)

    def test_square_cannot_change_after_creation(self):
        square = Square(7, 6)
        for name in ["file", "rank"]:
            with self.subTest(name=name):
                with self.assertRaises(FrozenInstanceError):
                    setattr(square, name, 1)


class BoardTests(unittest.TestCase):
    def test_new_board_is_empty(self):
        board = Board()
        for file in range(1, 10):
            for rank in range(1, 10):
                self.assertIsNone(board.piece_at(Square(file, rank)))

    def test_setting_a_piece_changes_only_its_square(self):
        board = Board()
        square = Square(7, 6)
        piece = Piece(PieceType.PAWN, Side.SENTE)
        board.set_piece(square, piece)
        for file in range(1, 10):
            for rank in range(1, 10):
                current = Square(file, rank)
                expected = piece if current == square else None
                self.assertEqual(board.piece_at(current), expected)

    def test_setting_none_clears_a_square(self):
        board = Board()
        square = Square(9, 9)
        board.set_piece(square, Piece(PieceType.LANCE, Side.SENTE))
        board.set_piece(square, None)
        self.assertIsNone(board.piece_at(square))

    def test_boards_do_not_share_cells(self):
        first, second = Board(), Board()
        square = Square(7, 6)
        first.set_piece(square, Piece(PieceType.PAWN, Side.SENTE))
        self.assertIsNone(second.piece_at(square))

    def test_piece_cannot_change_after_placement(self):
        piece = Piece(PieceType.PAWN, Side.SENTE)
        board = Board()
        board.set_piece(Square(7, 6), piece)
        for name, value in [("piece_type", PieceType.ROOK), ("side", Side.GOTE)]:
            with self.subTest(name=name):
                with self.assertRaises(FrozenInstanceError):
                    setattr(piece, name, value)
        self.assertEqual(board.piece_at(Square(7, 6)),
                         Piece(PieceType.PAWN, Side.SENTE))


class InitialPositionTests(unittest.TestCase):
    def test_all_81_squares_match_initial_setup(self):
        # 生成処理と独立した期待表。一〜九段、各行は９筋〜１筋。
        # テスト内だけの略号であり、SFENの読み込み処理ではない。
        rows = (
            "lnsgkgsnl", ".r.....b.", "ppppppppp",
            ".........", ".........", ".........",
            "PPPPPPPPP", ".B.....R.", "LNSGKGSNL",
        )
        kinds = dict(k=PieceType.KING, r=PieceType.ROOK, b=PieceType.BISHOP,
                     g=PieceType.GOLD, s=PieceType.SILVER, n=PieceType.KNIGHT,
                     l=PieceType.LANCE, p=PieceType.PAWN)
        position = create_initial_position()
        for rank, row in enumerate(rows, start=1):
            for file, symbol in zip(range(9, 0, -1), row):
                expected = None
                if symbol != ".":
                    side = Side.SENTE if symbol.isupper() else Side.GOTE
                    expected = Piece(kinds[symbol.lower()], side)
                with self.subTest(file=file, rank=rank):
                    self.assertEqual(position.board.piece_at(Square(file, rank)),
                                     expected)

    def test_piece_counts_and_first_turn(self):
        position = create_initial_position()
        pieces = [position.board.piece_at(Square(file, rank))
                  for file in range(1, 10) for rank in range(1, 10)]
        self.assertEqual(sum(piece is not None for piece in pieces), 40)
        for side in Side:
            owned = [piece for piece in pieces
                     if piece is not None and piece.side == side]
            self.assertEqual(len(owned), 20)
            self.assertEqual(sum(p.piece_type == PieceType.PAWN for p in owned), 9)
            self.assertEqual(sum(p.piece_type == PieceType.KING for p in owned), 1)
        self.assertEqual(position.side_to_move, Side.SENTE)

    def test_initial_positions_are_independent(self):
        first, second = create_initial_position(), create_initial_position()
        first.board.set_piece(Square(7, 7), None)
        first.side_to_move = Side.GOTE
        self.assertEqual(second.board.piece_at(Square(7, 7)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(second.side_to_move, Side.SENTE)
