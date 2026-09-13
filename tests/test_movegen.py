"""歩の向き・占有・盤外と、候補計算が盤を変更しない契約を検証する。"""

import unittest

from kaname_shogi.model import Board, Piece, PieceType, Position, Side, Square
from kaname_shogi.movegen import pawn_move_candidates


class PawnMoveCandidatesTests(unittest.TestCase):
    def test_empty_destination_follows_piece_owner(self):
        """先手は段を減らし、後手は段を増やして同じ筋へ進む。

        期待する段を固定値で与え、方向の逆転を検出する。端の筋も確認する。
        """
        for side, rank, next_rank in [(Side.SENTE, 7, 6), (Side.GOTE, 3, 4)]:
            for file in [1, 7, 9]:
                with self.subTest(side=side, file=file):
                    board = Board()
                    source = Square(file, rank)
                    board.set_piece(source, Piece(PieceType.PAWN, side))
                    self.assertEqual(pawn_move_candidates(board, source),
                                     [Square(file, next_rank)])

    def test_outside_board_returns_no_candidates(self):
        """先手の一段目と後手の九段目からは例外を出さず候補なしにする。

        盤外のSquareを先に作ってしまう誤りを検出する。合法局面の例ではない。
        """
        for side, rank in [(Side.SENTE, 1), (Side.GOTE, 9)]:
            with self.subTest(side=side):
                board = Board()
                source = Square(7, rank)
                board.set_piece(source, Piece(PieceType.PAWN, side))
                self.assertEqual(pawn_move_candidates(board, source), [])

    def test_inside_edge_remains_a_destination(self):
        """盤内の最奥段は移動先として返す。

        範囲を狭くしすぎる誤りを検出する。成り情報や不成の合法性は扱わない。
        """
        for side, rank, next_rank in [(Side.SENTE, 2, 1), (Side.GOTE, 8, 9)]:
            with self.subTest(side=side):
                board = Board()
                source = Square(7, rank)
                board.set_piece(source, Piece(PieceType.PAWN, side))
                self.assertEqual(pawn_move_candidates(board, source),
                                 [Square(7, next_rank)])

    def test_own_piece_blocks_destination(self):
        """一歩前の自駒は先後どちらでも候補から除外する。

        所有者を固定して判定する誤りや、自駒へ重なる候補の生成を検出する。
        """
        for side, rank, next_rank in [(Side.SENTE, 7, 6), (Side.GOTE, 3, 4)]:
            with self.subTest(side=side):
                board = Board()
                source = Square(7, rank)
                board.set_piece(source, Piece(PieceType.PAWN, side))
                board.set_piece(Square(7, next_rank), Piece(PieceType.GOLD, side))
                self.assertEqual(pawn_move_candidates(board, source), [])

    def test_opponent_piece_allows_destination(self):
        """一歩前の相手駒のマスは先後どちらでも候補に含める。

        駒があるマスをすべて除外する誤りを検出する。駒取りの実行ではない。
        """
        for side, opponent, rank, next_rank in [
            (Side.SENTE, Side.GOTE, 7, 6), (Side.GOTE, Side.SENTE, 3, 4),
        ]:
            with self.subTest(side=side):
                board = Board()
                source, target = Square(7, rank), Square(7, next_rank)
                board.set_piece(source, Piece(PieceType.PAWN, side))
                board.set_piece(target, Piece(PieceType.GOLD, opponent))
                self.assertEqual(pawn_move_candidates(board, source), [target])

    def test_empty_source_is_rejected(self):
        """空の出発マスは候補なしではなく呼び出しの誤りとして拒否する。

        存在しない歩の候補を計算したり、呼び出しミスを黙って隠すことを防ぐ。
        """
        with self.assertRaises(ValueError):
            pawn_move_candidates(Board(), Square(7, 7))

    def test_non_pawn_source_is_rejected(self):
        """歩以外の駒を出発点に指定した場合は拒否する。

        全駒種を歩の動きとして扱う誤りを、先後と全ての歩以外の駒種で検出する。
        """
        for side in Side:
            for kind in PieceType:
                if kind == PieceType.PAWN:
                    continue
                with self.subTest(side=side, kind=kind):
                    board = Board()
                    board.set_piece(Square(7, 7), Piece(kind, side))
                    with self.assertRaises(ValueError):
                        pawn_move_candidates(board, Square(7, 7))

    def test_candidate_generation_preserves_all_squares(self):
        """候補あり・自駒・相手駒・盤外の全経路で盤面は変わらない。

        移動や駒取りを候補計算に混ぜる誤りを、全81マスの値の比較で検出する。
        """
        for side, opponent, rank, next_rank, edge in [
            (Side.SENTE, Side.GOTE, 7, 6, 1),
            (Side.GOTE, Side.SENTE, 3, 4, 9),
        ]:
            for state in ["empty", "own", "opponent", "outside"]:
                with self.subTest(side=side, state=state):
                    board = Board()
                    source = Square(7, edge if state == "outside" else rank)
                    board.set_piece(source, Piece(PieceType.PAWN, side))
                    if state in ["own", "opponent"]:
                        owner = side if state == "own" else opponent
                        board.set_piece(Square(7, next_rank), Piece(PieceType.GOLD, owner))
                    squares = [Square(f, r) for f in range(1, 10) for r in range(1, 10)]
                    before = [board.piece_at(square) for square in squares]
                    pawn_move_candidates(board, source)
                    self.assertEqual([board.piece_at(square) for square in squares], before)

    def test_turn_does_not_restrict_candidates_or_change(self):
        """候補は手番によらず歩の所有者で決まり、手番も変更しない。

        同じ盤面を持つ局面の手番だけを切り替え、先手番でも後手の歩を調べる。
        """
        board = Board()
        board.set_piece(Square(7, 7), Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(7, 3), Piece(PieceType.PAWN, Side.GOTE))
        position = Position(board, Side.SENTE)
        for turn in Side:
            with self.subTest(turn=turn):
                position.side_to_move = turn
                self.assertEqual(pawn_move_candidates(position.board, Square(7, 7)),
                                 [Square(7, 6)])
                self.assertEqual(pawn_move_candidates(position.board, Square(7, 3)),
                                 [Square(7, 4)])
                self.assertEqual(position.side_to_move, turn)
