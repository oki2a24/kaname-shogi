"""筋段の取り違え、不正座標、盤面の共有を検出する。"""

from dataclasses import FrozenInstanceError
import unittest

from kaname_shogi.model import Board, Piece, PieceType, Side, Square
from kaname_shogi.model import create_initial_position


class SquareTests(unittest.TestCase):
    def test_known_squares_have_expected_indices(self):
        """四隅と７六が、決めたマス番号に対応する。

        筋段の逆転や開始位置のずれを、手計算した添字で検出する。
        """
        for file, rank, expected in [(1, 1, 0), (1, 9, 8), (9, 1, 72),
                                     (9, 9, 80), (7, 6, 59)]:
            with self.subTest(file=file, rank=rank):
                self.assertEqual(Square(file, rank).to_index(), expected)

    def test_all_squares_cover_81_indices(self):
        """81マスが0〜80の添字を重複なく覆う。

        特定の座標だけが重なる誤りや、保存範囲を外れる変換を検出する。
        """
        indices = [Square(file, rank).to_index()
                   for file in range(1, 10) for rank in range(1, 10)]
        self.assertEqual(sorted(indices), list(range(81)))

    def test_invalid_coordinates_are_rejected(self):
        """範囲外・非整数・真偽値の筋段を拒否する。

        筋と段を個別に検証する。1.0やTrueも整数の座標として通さない。
        """
        for value in [0, 10, -1, 1.0, "1", None, True, False]:
            for file, rank in [(value, 1), (1, value)]:
                with self.subTest(file=file, rank=rank):
                    with self.assertRaises(ValueError):
                        Square(file, rank)

    def test_square_cannot_change_after_creation(self):
        """生成した座標の筋と段は後から変更できない。

        参照先が意図せず変わらないというSquareの契約を確認する。
        """
        square = Square(7, 6)
        for name in ["file", "rank"]:
            with self.subTest(name=name):
                with self.assertRaises(FrozenInstanceError):
                    setattr(square, name, 1)


class BoardTests(unittest.TestCase):
    def test_new_board_is_empty(self):
        """新しい盤面は全81マスが空である。

        空盤と初期配置を区別し、端のマスも含めて確認する。
        """
        board = Board()
        for file in range(1, 10):
            for rank in range(1, 10):
                self.assertIsNone(board.piece_at(Square(file, rank)))

    def test_setting_a_piece_changes_only_its_square(self):
        """７六への配置は他の80マスを変更しない。

        添字の衝突や広い範囲への誤代入を、全マスの参照結果で検出する。
        """
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
        """Noneを設定すると指定マスが空になる。

        配置済みの駒を消せる契約を確認する。駒取りのルール検証ではない。
        """
        board = Board()
        square = Square(9, 9)
        board.set_piece(square, Piece(PieceType.LANCE, Side.SENTE))
        board.set_piece(square, None)
        self.assertIsNone(board.piece_at(square))

    def test_boards_do_not_share_cells(self):
        """一方の盤に駒を置いても別の盤は変わらない。

        内部リストをクラス変数などで誤って共有した場合を検出する。
        """
        first, second = Board(), Board()
        square = Square(7, 6)
        first.set_piece(square, Piece(PieceType.PAWN, Side.SENTE))
        self.assertIsNone(second.piece_at(square))

    def test_piece_cannot_change_after_placement(self):
        """配置した駒の駒種と所有者は後から変更できない。

        盤が保持する駒の値を、呼び出し側の参照から変更できないことを確認する。
        """
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
        """初期配置の全81マスが独立した期待表と一致する。

        駒数だけでは分からない飛角の逆配置や、空マスへの誤配置を検出する。
        """
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
        """初期局面は各側20枚・歩9枚・玉1枚で先手番である。

        全マス比較に加え、学習した枚数と開始時の手番を明示的に確認する。
        """
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
        """初期局面を変更しても別の初期局面に影響しない。

        生成関数による盤面や局面の使い回しを、盤と手番の変更で検出する。
        """
        first, second = create_initial_position(), create_initial_position()
        first.board.set_piece(Square(7, 7), None)
        first.side_to_move = Side.GOTE
        self.assertEqual(second.board.piece_at(Square(7, 7)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(second.side_to_move, Side.SENTE)
