"""歩・金・銀・桂馬・香・飛車・角の向き・占有・盤外と、盤面不変の契約を検証する。"""

import unittest

from kaname_shogi import movegen
from kaname_shogi.model import Board, Piece, PieceType, Position, Side, Square
from kaname_shogi.movegen import (
    bishop_move_candidates, gold_move_candidates, lance_move_candidates,
    king_move_candidates, knight_move_candidates, pawn_move_candidates,
    rook_move_candidates,
    silver_move_candidates,
)


class MovePieceTests(unittest.TestCase):
    def _move_piece(self, board, source, destination):
        """移動適用関数を取得し、未実装をテスト失敗として扱う。"""
        self.assertTrue(hasattr(movegen, "move_piece"),
                        "move_piece がまだ実装されていません")
        return movegen.move_piece(board, source, destination)

    def test_moves_piece_to_empty_destination(self):
        """空いている到着マスへ駒を移し、出発マスを空にする。

        出発マスと到着マスの更新漏れや、移動するPieceの取り違えを検出する。
        """
        board = Board()
        source, destination = Square(5, 5), Square(5, 4)
        piece = Piece(PieceType.PAWN, Side.SENTE)
        board.set_piece(source, piece)

        result = self._move_piece(board, source, destination)

        self.assertIsNone(result)
        self.assertIsNone(board.piece_at(source))
        self.assertEqual(board.piece_at(destination), piece)

    def test_rejects_empty_source_without_changing_board(self):
        """空の出発マスを拒否し、盤面を変更しない。

        空の出発点を移動成功として扱う誤りと、失敗後の部分変更を検出する。
        """
        board = Board()
        destination = Square(5, 4)
        before = [board.piece_at(Square(file, rank))
                  for file in range(1, 10) for rank in range(1, 10)]

        with self.assertRaises(ValueError):
            self._move_piece(board, Square(5, 5), destination)

        after = [board.piece_at(Square(file, rank))
                 for file in range(1, 10) for rank in range(1, 10)]
        self.assertEqual(after, before)

    def test_rejects_occupied_destination_without_changing_board(self):
        """駒のある到着マスを拒否し、盤面を変更しない。

        今回は駒取りを扱わないため、到着駒を上書きする誤りを検出する。
        """
        board = Board()
        source, destination = Square(5, 5), Square(5, 4)
        moving_piece = Piece(PieceType.PAWN, Side.SENTE)
        destination_piece = Piece(PieceType.GOLD, Side.GOTE)
        board.set_piece(source, moving_piece)
        board.set_piece(destination, destination_piece)
        before = [board.piece_at(Square(file, rank))
                  for file in range(1, 10) for rank in range(1, 10)]

        with self.assertRaises(ValueError):
            self._move_piece(board, source, destination)

        after = [board.piece_at(Square(file, rank))
                 for file in range(1, 10) for rank in range(1, 10)]
        self.assertEqual(after, before)

    def test_rejects_same_source_and_destination_without_changing_board(self):
        """出発マスと到着マスが同じ場合を拒否し、盤面を変更しない。

        同じマスを空にしてから駒を戻す実装や、無意味な成功扱いを検出する。
        """
        board = Board()
        source = Square(5, 5)
        piece = Piece(PieceType.KING, Side.SENTE)
        board.set_piece(source, piece)
        before = [board.piece_at(Square(file, rank))
                  for file in range(1, 10) for rank in range(1, 10)]

        with self.assertRaises(ValueError):
            self._move_piece(board, source, source)

        after = [board.piece_at(Square(file, rank))
                 for file in range(1, 10) for rank in range(1, 10)]
        self.assertEqual(after, before)


class ApplyMoveTests(unittest.TestCase):
    def _apply_move(self, position, source, destination):
        """局面への移動適用関数を取得し、未実装をテスト失敗として扱う。"""
        self.assertTrue(hasattr(movegen, "apply_move"),
                        "apply_move がまだ実装されていません")
        return movegen.apply_move(position, source, destination)

    def test_moves_piece_and_switches_turn_after_success(self):
        """成功した移動は盤面を更新し、先手・後手の手番を交代する。

        盤面移動だけで手番を残す誤りと、交代方向を逆にする誤りを検出する。
        """
        for initial_turn, expected_turn in [
            (Side.SENTE, Side.GOTE),
            (Side.GOTE, Side.SENTE),
        ]:
            board = Board()
            source = Square(5, 5)
            destination = (Square(5, 4) if initial_turn == Side.SENTE
                           else Square(5, 6))
            piece = Piece(PieceType.PAWN, initial_turn)
            board.set_piece(source, piece)
            position = Position(board, initial_turn)
            with self.subTest(initial_turn=initial_turn):
                self.assertIsNone(self._apply_move(position, source, destination))
                self.assertIsNone(position.board.piece_at(source))
                self.assertEqual(position.board.piece_at(destination), piece)
                self.assertEqual(position.side_to_move, expected_turn)

    def test_moves_each_piece_to_an_empty_candidate_and_switches_turn(self):
        """各駒種は候補内の空マスへ移動し、成功後に手番を交代する。

        駒種から候補関数を選び忘れる誤りや、候補照合後に手番を交代しない誤りを検出する。
        """
        cases = [
            (PieceType.KING, Square(5, 4)),
            (PieceType.ROOK, Square(4, 5)),
            (PieceType.BISHOP, Square(4, 4)),
            (PieceType.GOLD, Square(5, 4)),
            (PieceType.SILVER, Square(5, 4)),
            (PieceType.KNIGHT, Square(4, 3)),
            (PieceType.LANCE, Square(5, 4)),
            (PieceType.PAWN, Square(5, 4)),
        ]
        for piece_type, destination in cases:
            board = Board()
            source = Square(5, 5)
            piece = Piece(piece_type, Side.SENTE)
            board.set_piece(source, piece)
            position = Position(board, Side.SENTE)
            with self.subTest(piece_type=piece_type):
                self.assertIsNone(self._apply_move(position, source, destination))
                self.assertIsNone(board.piece_at(source))
                self.assertEqual(board.piece_at(destination), piece)
                self.assertEqual(position.side_to_move, Side.GOTE)

    def test_rejects_empty_destination_outside_piece_candidates_without_changing_position(self):
        """候補外の空マスを拒否し、盤面と手番を変更しない。

        空いているだけの任意のマスへ動かしてしまう誤りを、先後の歩の反対向きで検出する。
        """
        source = Square(5, 5)
        squares = [Square(file, rank) for file in range(1, 10)
                   for rank in range(1, 10)]
        for side, destination in [(Side.SENTE, Square(5, 6)),
                                  (Side.GOTE, Square(5, 4))]:
            board = Board()
            board.set_piece(source, Piece(PieceType.PAWN, side))
            position = Position(board, side)
            before = [board.piece_at(square) for square in squares]
            with self.subTest(side=side):
                with self.assertRaises(ValueError):
                    self._apply_move(position, source, destination)
                self.assertEqual([board.piece_at(square) for square in squares], before)
                self.assertEqual(position.side_to_move, side)

    def test_rejects_invalid_move_without_changing_board_or_turn(self):
        """不正な移動は盤面と手番のどちらも変更しない。

        盤面変更後に失敗する処理や、例外時にも手番だけ交代する誤りを検出する。
        """
        cases = [
            ("empty_source", Square(5, 5), Square(5, 4), ()),
            ("occupied_destination", Square(5, 5), Square(5, 4),
             ((Square(5, 5), Piece(PieceType.PAWN, Side.SENTE)),
              (Square(5, 4), Piece(PieceType.GOLD, Side.GOTE)))),
            ("same_square", Square(5, 5), Square(5, 5),
             ((Square(5, 5), Piece(PieceType.PAWN, Side.SENTE)),)),
        ]
        for name, source, destination, placements in cases:
            board = Board()
            for square, piece in placements:
                board.set_piece(square, piece)
            position = Position(board, Side.SENTE)
            before_board = [board.piece_at(Square(file, rank))
                            for file in range(1, 10) for rank in range(1, 10)]
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    self._apply_move(position, source, destination)
                after_board = [board.piece_at(Square(file, rank))
                               for file in range(1, 10) for rank in range(1, 10)]
                self.assertEqual(after_board, before_board)
                self.assertEqual(position.side_to_move, Side.SENTE)

    def test_rejects_piece_owned_by_the_other_side_without_changing_position(self):
        """手番と所有者が異なる駒を拒否し、局面を変更しない。

        後手の駒を先手番で、先手の駒を後手番で動かしてしまう二手指しと、
        例外時の盤面または手番の部分変更を検出する。
        """
        source, destination = Square(5, 5), Square(5, 4)
        for turn, piece_side in [(Side.SENTE, Side.GOTE),
                                 (Side.GOTE, Side.SENTE)]:
            board = Board()
            piece = Piece(PieceType.PAWN, piece_side)
            board.set_piece(source, piece)
            position = Position(board, turn)
            before_board = [board.piece_at(Square(file, rank))
                            for file in range(1, 10) for rank in range(1, 10)]
            with self.subTest(turn=turn, piece_side=piece_side):
                with self.assertRaises(ValueError):
                    self._apply_move(position, source, destination)
                after_board = [board.piece_at(Square(file, rank))
                               for file in range(1, 10) for rank in range(1, 10)]
                self.assertEqual(after_board, before_board)
                self.assertEqual(position.side_to_move, turn)


class KingMoveCandidatesTests(unittest.TestCase):
    def test_empty_source_is_rejected(self):
        """空の出発マスを玉候補の計算対象として受け付けない。

        候補なしと呼び出しの誤りを区別するValueErrorの契約を確認する。
        """
        with self.assertRaises(ValueError):
            king_move_candidates(Board(), Square(5, 5))

    def test_non_king_source_is_rejected(self):
        """玉以外の駒種を玉候補の出発点として受け付けない。

        駒種の検証漏れにより他の駒を玉として扱う誤りを検出する。
        """
        for side in Side:
            for kind in PieceType:
                if kind == PieceType.KING:
                    continue
                board = Board()
                source = Square(5, 5)
                board.set_piece(source, Piece(kind, side))
                with self.subTest(side=side, kind=kind):
                    with self.assertRaises(ValueError):
                        king_move_candidates(board, source)

    def test_open_board_returns_eight_directions_in_order(self):
        """５五の玉は先後によらず周囲8方向を固定順に返す。

        玉に前方の反転を適用する誤りと方向順の誤りを検出する。
        """
        expected = [Square(5, 4), Square(4, 4), Square(4, 5), Square(4, 6),
                    Square(5, 6), Square(6, 6), Square(6, 5), Square(6, 4)]
        for side in Side:
            board = Board()
            source = Square(5, 5)
            board.set_piece(source, Piece(PieceType.KING, side))
            with self.subTest(side=side):
                self.assertEqual(king_move_candidates(board, source), expected)

    def test_corner_excludes_off_board_destinations(self):
        """１一の玉は盤内の３マスだけを候補にする。

        盤端で盤外のSquareを候補に含める誤りを検出する。
        """
        board = Board()
        source = Square(1, 1)
        board.set_piece(source, Piece(PieceType.KING, Side.SENTE))
        self.assertEqual(king_move_candidates(board, source),
                         [Square(1, 2), Square(2, 2), Square(2, 1)])

    def test_own_destination_is_excluded_and_opponent_is_included(self):
        """自駒の到着先を除外し、相手駒の到着先を候補に含める。

        到着先の所有者判定を逆にする誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 4), Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(4, 4), Piece(PieceType.PAWN, Side.GOTE))
        self.assertEqual(king_move_candidates(board, source),
                         [Square(4, 4), Square(4, 5), Square(4, 6),
                          Square(5, 6), Square(6, 6), Square(6, 5),
                          Square(6, 4)])

    def test_candidate_generation_preserves_board_and_turn(self):
        """候補計算は盤面と局面の手番を変更しない。

        実際の移動や駒取りを候補生成へ混入する誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(4, 4), Piece(PieceType.PAWN, Side.GOTE))
        position = Position(board, Side.SENTE)
        before = [board.piece_at(Square(file, rank))
                  for file in range(1, 10) for rank in range(1, 10)]
        for turn in Side:
            position.side_to_move = turn
            king_move_candidates(position.board, source)
            self.assertEqual(position.side_to_move, turn)
        after = [board.piece_at(Square(file, rank))
                 for file in range(1, 10) for rank in range(1, 10)]
        self.assertEqual(after, before)

    def test_results_are_independent_lists(self):
        """呼び出しごとに玉の候補リストを独立して返す。

        呼び出し側による戻り値の変更が別の結果へ波及する誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.KING, Side.SENTE))
        expected = king_move_candidates(board, source)
        result = king_move_candidates(board, source)
        result.clear()
        self.assertEqual(king_move_candidates(board, source), expected)


class KnightMoveCandidatesTests(unittest.TestCase):
    def test_empty_source_is_rejected(self):
        """空の出発マスを桂馬候補の計算対象として受け付けない。

        候補なしと呼び出しの誤りを区別するValueErrorの契約を確認する。
        """
        with self.assertRaises(ValueError):
            knight_move_candidates(Board(), Square(5, 5))

    def test_non_knight_source_is_rejected(self):
        """桂馬以外の駒種を桂馬候補の出発点として受け付けない。

        駒種の検証漏れにより、他の駒を桂馬の動きとして扱う誤りを検出する。
        """
        for side in Side:
            for kind in PieceType:
                if kind == PieceType.KNIGHT:
                    continue
                with self.subTest(side=side, kind=kind):
                    board = Board()
                    board.set_piece(Square(5, 5), Piece(kind, side))
                    with self.assertRaises(ValueError):
                        knight_move_candidates(board, Square(5, 5))

    def test_open_board_returns_right_front_then_left_front(self):
        """５五の桂馬は右前、左前の順に候補を返す。

        先後の段方向、筋の増減、固定順の誤りを検出する。
        """
        for side, expected in [
            (Side.SENTE, [Square(4, 3), Square(6, 3)]),
            (Side.GOTE, [Square(4, 7), Square(6, 7)]),
        ]:
            with self.subTest(side=side):
                board = Board()
                source = Square(5, 5)
                board.set_piece(source, Piece(PieceType.KNIGHT, side))
                self.assertEqual(knight_move_candidates(board, source), expected)

    def test_intermediate_pieces_do_not_block_candidates(self):
        """途中のマスに駒があっても桂馬は到着先を候補にする。

        途中のマスを走査して候補を誤って止める実装を検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.KNIGHT, Side.SENTE))
        board.set_piece(Square(4, 4), Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(6, 4), Piece(PieceType.PAWN, Side.GOTE))
        self.assertEqual(knight_move_candidates(board, source),
                         [Square(4, 3), Square(6, 3)])

    def test_own_destination_is_excluded(self):
        """桂馬の到着先にある自駒のマスを候補から除外する。

        到着先の所有者を確認せず、自駒のマスを候補に含める誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.KNIGHT, Side.SENTE))
        board.set_piece(Square(4, 3), Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(knight_move_candidates(board, source), [Square(6, 3)])

    def test_opponent_destination_is_included(self):
        """桂馬の到着先にある相手駒のマスを候補に含める。

        相手駒のマスまで除外する誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.KNIGHT, Side.SENTE))
        board.set_piece(Square(6, 3), Piece(PieceType.PAWN, Side.GOTE))
        self.assertEqual(knight_move_candidates(board, source),
                         [Square(4, 3), Square(6, 3)])

    def test_edges_exclude_off_board_candidates_for_both_sides(self):
        """先後の桂馬は盤外の到着先を候補から除外する。

        筋と段の境界を確認せずSquareを作る誤りを、盤端の先後両方で検出する。
        """
        cases = [
            (Side.SENTE, Square(1, 2), []),
            (Side.SENTE, Square(9, 2), []),
            (Side.SENTE, Square(1, 3), [Square(2, 1)]),
            (Side.SENTE, Square(9, 3), [Square(8, 1)]),
            (Side.GOTE, Square(1, 8), []),
            (Side.GOTE, Square(9, 8), []),
            (Side.GOTE, Square(1, 7), [Square(2, 9)]),
            (Side.GOTE, Square(9, 7), [Square(8, 9)]),
        ]
        for side, source, expected in cases:
            with self.subTest(side=side, source=source):
                board = Board()
                board.set_piece(source, Piece(PieceType.KNIGHT, side))
                self.assertEqual(knight_move_candidates(board, source), expected)

    def test_candidate_generation_preserves_all_squares(self):
        """候補計算の前後で盤上の全81マスを変更しない。

        桂馬を動かしたり、相手駒を取ったりする処理の混入を検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.KNIGHT, Side.SENTE))
        board.set_piece(Square(4, 3), Piece(PieceType.PAWN, Side.GOTE))
        squares = [Square(file, rank) for file in range(1, 10)
                   for rank in range(1, 10)]
        before = [board.piece_at(square) for square in squares]
        knight_move_candidates(board, source)
        self.assertEqual([board.piece_at(square) for square in squares], before)

    def test_turn_does_not_restrict_candidates_or_change(self):
        """局面の手番によらず桂馬の所有者で候補を計算し、手番も変更しない。

        Position.side_to_moveを候補生成の制限や更新に誤用する実装を検出する。
        """
        board = Board()
        sente_source, gote_source = Square(5, 5), Square(1, 7)
        board.set_piece(sente_source, Piece(PieceType.KNIGHT, Side.SENTE))
        board.set_piece(gote_source, Piece(PieceType.KNIGHT, Side.GOTE))
        position = Position(board, Side.SENTE)
        expected = {
            Side.SENTE: [Square(4, 3), Square(6, 3)],
            Side.GOTE: [Square(2, 9)],
        }
        for turn in Side:
            with self.subTest(turn=turn):
                position.side_to_move = turn
                self.assertEqual(knight_move_candidates(position.board, sente_source),
                                 expected[Side.SENTE])
                self.assertEqual(knight_move_candidates(position.board, gote_source),
                                 expected[Side.GOTE])
                self.assertEqual(position.side_to_move, turn)

    def test_results_are_independent_lists(self):
        """呼び出しごとに桂馬の候補リストを独立して返す。

        呼び出し側による戻り値の変更が、別の呼び出し結果へ波及する誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.KNIGHT, Side.SENTE))
        expected = knight_move_candidates(board, source)
        result = knight_move_candidates(board, source)
        result.clear()
        self.assertEqual(knight_move_candidates(board, source), expected)


class BishopMoveCandidatesTests(unittest.TestCase):
    def test_empty_source_is_rejected(self):
        """空の出発マスを角候補の計算対象として受け付けない。

        候補なしと呼び出しの誤りを区別するValueErrorの契約を確認する。
        """
        with self.assertRaises(ValueError):
            bishop_move_candidates(Board(), Square(5, 5))

    def test_non_bishop_source_is_rejected(self):
        """角以外の駒種を角候補の出発点として受け付けない。

        駒種の検証漏れにより、他の駒を角の動きとして扱う誤りを検出する。
        """
        for side in Side:
            for kind in PieceType:
                if kind == PieceType.BISHOP:
                    continue
                with self.subTest(side=side, kind=kind):
                    board = Board()
                    board.set_piece(Square(5, 5), Piece(kind, side))
                    with self.assertRaises(ValueError):
                        bishop_move_candidates(board, Square(5, 5))

    def test_open_board_returns_four_diagonal_directions_in_order(self):
        """５五の角は右前・左前・右後ろ・左後ろの順に候補を返す。

        筋と段の同時増減、先後の前後、方向順、走査距離の誤りを検出する。
        """
        for side, expected in [
            (Side.SENTE, (
                [Square(file, rank) for file, rank in [(4, 4), (3, 3), (2, 2), (1, 1)]]
                + [Square(file, rank) for file, rank in [(6, 4), (7, 3), (8, 2), (9, 1)]]
                + [Square(file, rank) for file, rank in [(4, 6), (3, 7), (2, 8), (1, 9)]]
                + [Square(file, rank) for file, rank in [(6, 6), (7, 7), (8, 8), (9, 9)]]
            )),
            (Side.GOTE, (
                [Square(file, rank) for file, rank in [(4, 6), (3, 7), (2, 8), (1, 9)]]
                + [Square(file, rank) for file, rank in [(6, 6), (7, 7), (8, 8), (9, 9)]]
                + [Square(file, rank) for file, rank in [(4, 4), (3, 3), (2, 2), (1, 1)]]
                + [Square(file, rank) for file, rank in [(6, 4), (7, 3), (8, 2), (9, 1)]]
            )),
        ]:
            with self.subTest(side=side):
                board = Board()
                board.set_piece(Square(5, 5), Piece(PieceType.BISHOP, side))
                self.assertEqual(bishop_move_candidates(board, Square(5, 5)), expected)

    def test_own_piece_stops_each_direction_before_its_square(self):
        """4方向それぞれで自駒の手前までを候補にし、自駒の先へ進まない。

        自駒を候補に含めたり、別方向まで走査を止めたりする誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.BISHOP, Side.SENTE))
        blockers = [Square(4, 4), Square(7, 3), Square(3, 7), Square(7, 7)]
        for blocker in blockers:
            board.set_piece(blocker, Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(bishop_move_candidates(board, source),
                         [Square(6, 4), Square(4, 6), Square(6, 6)])

    def test_opponent_piece_is_last_destination_in_each_direction(self):
        """4方向それぞれで最初の相手駒を最後の候補に含め、その先へ進まない。

        相手駒を除外したり、相手駒を飛び越して奥まで返したりする誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.BISHOP, Side.SENTE))
        blockers = [Square(3, 3), Square(7, 3), Square(3, 7), Square(7, 7)]
        for blocker in blockers:
            board.set_piece(blocker, Piece(PieceType.PAWN, Side.GOTE))
        self.assertEqual(bishop_move_candidates(board, source),
                         [Square(4, 4), Square(3, 3),
                          Square(6, 4), Square(7, 3),
                          Square(4, 6), Square(3, 7),
                          Square(6, 6), Square(7, 7)])

    def test_blocked_direction_does_not_stop_other_directions(self):
        """1方向が自駒で塞がっても、残り3方向を候補計算する。

        全体を途中で終了する誤りと、斜め方向の増減を取り違える誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.BISHOP, Side.SENTE))
        board.set_piece(Square(4, 4), Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(bishop_move_candidates(board, source),
                         [Square(6, 4), Square(7, 3), Square(8, 2), Square(9, 1),
                          Square(4, 6), Square(3, 7), Square(2, 8), Square(1, 9),
                          Square(6, 6), Square(7, 7), Square(8, 8), Square(9, 9)])

    def test_edges_stop_at_board_boundary_for_both_sides(self):
        """四隅の角は盤外を除き、固定した斜め方向順で候補を返す。

        筋・段の境界判定の欠落、座標の誤り、方向順の入れ替えを検出する。
        """
        cases = [
            (Square(1, 1), [Square(2, 2), Square(3, 3), Square(4, 4),
                           Square(5, 5), Square(6, 6), Square(7, 7),
                           Square(8, 8), Square(9, 9)]),
            (Square(9, 1), [Square(8, 2), Square(7, 3), Square(6, 4),
                           Square(5, 5), Square(4, 6), Square(3, 7),
                           Square(2, 8), Square(1, 9)]),
            (Square(1, 9), [Square(2, 8), Square(3, 7), Square(4, 6),
                           Square(5, 5), Square(6, 4), Square(7, 3),
                           Square(8, 2), Square(9, 1)]),
            (Square(9, 9), [Square(8, 8), Square(7, 7), Square(6, 6),
                           Square(5, 5), Square(4, 4), Square(3, 3),
                           Square(2, 2), Square(1, 1)]),
        ]
        for side in Side:
            for source, expected in cases:
                with self.subTest(side=side, source=source):
                    board = Board()
                    board.set_piece(source, Piece(PieceType.BISHOP, side))
                    self.assertEqual(bishop_move_candidates(board, source), expected)

    def test_candidate_generation_preserves_all_squares(self):
        """候補計算の前後で盤上の全81マスを変更しない。

        角を動かす、相手駒を取る、通過した駒を消す処理の混入を検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.BISHOP, Side.SENTE))
        board.set_piece(Square(4, 4), Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(7, 3), Piece(PieceType.PAWN, Side.GOTE))
        squares = [Square(file, rank) for file in range(1, 10)
                   for rank in range(1, 10)]
        before = [board.piece_at(square) for square in squares]
        bishop_move_candidates(board, source)
        self.assertEqual([board.piece_at(square) for square in squares], before)

    def test_results_are_independent_lists(self):
        """呼び出しごとに候補リストを独立して返す。

        呼び出し側による戻り値の変更が、別の呼び出し結果へ波及する誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.BISHOP, Side.SENTE))
        expected = bishop_move_candidates(board, source)
        result = bishop_move_candidates(board, source)
        result.append(Square(1, 1))
        self.assertEqual(bishop_move_candidates(board, source), expected)

    def test_turn_does_not_restrict_candidates_or_change(self):
        """手番によらず出発駒の所有者で候補を計算し、手番を変更しない。

        Positionの手番を候補生成の制限に誤用する実装を、先後の角で検出する。
        """
        board = Board()
        sente_source, gote_source = Square(5, 5), Square(1, 1)
        board.set_piece(sente_source, Piece(PieceType.BISHOP, Side.SENTE))
        board.set_piece(gote_source, Piece(PieceType.BISHOP, Side.GOTE))
        position = Position(board, Side.SENTE)
        sente_expected = bishop_move_candidates(board, sente_source)
        gote_expected = bishop_move_candidates(board, gote_source)
        for turn in Side:
            with self.subTest(turn=turn):
                position.side_to_move = turn
                self.assertEqual(bishop_move_candidates(position.board, sente_source),
                                 sente_expected)
                self.assertEqual(bishop_move_candidates(position.board, gote_source),
                                 gote_expected)
                self.assertEqual(position.side_to_move, turn)


class RookMoveCandidatesTests(unittest.TestCase):
    def test_empty_source_is_rejected(self):
        """空の出発マスを飛車候補の計算対象として受け付けない。

        候補なしと呼び出しの誤りを区別するValueErrorの契約を確認する。
        """
        with self.assertRaises(ValueError):
            rook_move_candidates(Board(), Square(5, 5))

    def test_non_rook_source_is_rejected(self):
        """飛車以外の駒種を飛車候補の出発点として受け付けない。

        駒種の検証漏れにより、他の駒を飛車の動きとして扱う誤りを検出する。
        """
        for side in Side:
            for kind in PieceType:
                if kind == PieceType.ROOK:
                    continue
                with self.subTest(side=side, kind=kind):
                    board = Board()
                    board.set_piece(Square(5, 5), Piece(kind, side))
                    with self.assertRaises(ValueError):
                        rook_move_candidates(board, Square(5, 5))

    def test_open_board_returns_four_directions_in_order(self):
        """５五の飛車は右・左・前・後ろの各方向を近い順に返す。

        筋の増減、先後の前方、方向順、走査距離の誤りを開いた盤面で検出する。
        """
        for side, vertical in [
            (Side.SENTE, [(5, 4), (5, 3), (5, 2), (5, 1),
                          (5, 6), (5, 7), (5, 8), (5, 9)]),
            (Side.GOTE, [(5, 6), (5, 7), (5, 8), (5, 9),
                         (5, 4), (5, 3), (5, 2), (5, 1)]),
        ]:
            with self.subTest(side=side):
                board = Board()
                source = Square(5, 5)
                board.set_piece(source, Piece(PieceType.ROOK, side))
                expected = ([Square(file, 5) for file in [4, 3, 2, 1]]
                            + [Square(file, 5) for file in [6, 7, 8, 9]]
                            + [Square(file, rank) for file, rank in vertical])
                self.assertEqual(rook_move_candidates(board, source), expected)

    def test_own_piece_stops_each_direction_before_its_square(self):
        """4方向それぞれで自駒の手前までを候補にし、自駒の先へ進まない。

        自駒を候補に含めたり、別方向まで走査を止めたりする誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.ROOK, Side.SENTE))
        blockers = [Square(4, 5), Square(7, 5), Square(5, 3), Square(5, 7)]
        for blocker in blockers:
            board.set_piece(blocker, Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(rook_move_candidates(board, source),
                         [Square(6, 5), Square(5, 4), Square(5, 6)])

    def test_opponent_piece_is_last_destination_in_each_direction(self):
        """4方向それぞれで最初の相手駒を候補に含め、その先へ進まない。

        相手駒を除外したり、相手駒を飛び越して奥まで返したりする誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.ROOK, Side.SENTE))
        blockers = [Square(3, 5), Square(7, 5), Square(5, 3), Square(5, 7)]
        for blocker in blockers:
            board.set_piece(blocker, Piece(PieceType.PAWN, Side.GOTE))
        self.assertEqual(rook_move_candidates(board, source),
                         [Square(4, 5), Square(3, 5),
                          Square(6, 5), Square(7, 5),
                          Square(5, 4), Square(5, 3),
                          Square(5, 6), Square(5, 7)])

    def test_blocked_direction_does_not_stop_other_directions(self):
        """1方向が自駒で塞がっても、残り3方向を候補計算する。

        全体を途中で終了する誤りと、右方向の筋減少を取り違える誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.ROOK, Side.SENTE))
        board.set_piece(Square(4, 5), Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(rook_move_candidates(board, source),
                         [Square(file, 5) for file in [6, 7, 8, 9]]
                         + [Square(5, rank) for rank in [4, 3, 2, 1]]
                         + [Square(5, rank) for rank in [6, 7, 8, 9]])

    def test_edges_stop_at_board_boundary_for_both_sides(self):
        """四隅の飛車は盤外を除き、右・左・前・後ろの順で候補を返す。

        筋・段の境界判定の欠落、座標の誤り、方向順の入れ替えを検出する。
        """
        cases = [
            (Square(1, 1),
             [Square(file, 1) for file in range(2, 10)]
             + [Square(1, rank) for rank in range(2, 10)]),
            (Square(9, 1),
             [Square(file, 1) for file in range(8, 0, -1)]
             + [Square(9, rank) for rank in range(2, 10)]),
            (Square(1, 9),
             [Square(file, 9) for file in range(2, 10)]
             + [Square(1, rank) for rank in range(8, 0, -1)]),
            (Square(9, 9),
             [Square(file, 9) for file in range(8, 0, -1)]
             + [Square(9, rank) for rank in range(8, 0, -1)]),
        ]
        for side in Side:
            for source, expected in cases:
                with self.subTest(side=side, source=source):
                    board = Board()
                    board.set_piece(source, Piece(PieceType.ROOK, side))
                    self.assertEqual(rook_move_candidates(board, source), expected)

    def test_candidate_generation_preserves_all_squares(self):
        """候補計算の前後で盤上の全81マスを変更しない。

        飛車を動かす、相手駒を取る、通過した駒を消す処理の混入を検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.ROOK, Side.SENTE))
        board.set_piece(Square(4, 5), Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(7, 5), Piece(PieceType.PAWN, Side.GOTE))
        squares = [Square(file, rank) for file in range(1, 10)
                   for rank in range(1, 10)]
        before = [board.piece_at(square) for square in squares]
        rook_move_candidates(board, source)
        self.assertEqual([board.piece_at(square) for square in squares], before)

    def test_results_are_independent_lists(self):
        """呼び出しごとに候補リストを独立して返す。

        呼び出し側による戻り値の変更が、別の呼び出し結果へ波及する誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.ROOK, Side.SENTE))
        expected = rook_move_candidates(board, source)
        result = rook_move_candidates(board, source)
        result.append(Square(1, 1))
        self.assertEqual(rook_move_candidates(board, source), expected)

    def test_turn_does_not_restrict_candidates_or_change(self):
        """手番によらず出発駒の所有者で候補を計算し、手番を変更しない。

        Positionの手番を候補生成の制限に誤用する実装を、先後の飛車で検出する。
        """
        board = Board()
        sente_source, gote_source = Square(5, 5), Square(1, 1)
        board.set_piece(sente_source, Piece(PieceType.ROOK, Side.SENTE))
        board.set_piece(gote_source, Piece(PieceType.ROOK, Side.GOTE))
        position = Position(board, Side.SENTE)
        sente_expected = rook_move_candidates(board, sente_source)
        gote_expected = rook_move_candidates(board, gote_source)
        for turn in Side:
            with self.subTest(turn=turn):
                position.side_to_move = turn
                self.assertEqual(rook_move_candidates(position.board, sente_source),
                                 sente_expected)
                self.assertEqual(rook_move_candidates(position.board, gote_source),
                                 gote_expected)
                self.assertEqual(position.side_to_move, turn)


class LanceMoveCandidatesTests(unittest.TestCase):
    def test_edge_files_and_ranks_limit_destinations(self):
        """端の筋でも同じ筋を進み、最奥段を含めて盤外で止まる。

        最大8候補、最奥段からの候補なし、境界直前の1候補を確認する。
        成る前の香を最奥段に置くケースは境界確認用で、合法局面の例ではない。
        """
        for file in (1, 9):
            for side, source_rank, expected_ranks in [
                (Side.SENTE, 9, [8, 7, 6, 5, 4, 3, 2, 1]),
                (Side.GOTE, 1, [2, 3, 4, 5, 6, 7, 8, 9]),
                (Side.SENTE, 1, []),
                (Side.GOTE, 9, []),
                (Side.SENTE, 2, [1]),
                (Side.GOTE, 8, [9]),
            ]:
                with self.subTest(file=file, side=side, source_rank=source_rank):
                    board = Board()
                    source = Square(file, source_rank)
                    board.set_piece(source, Piece(PieceType.LANCE, side))
                    self.assertEqual(lance_move_candidates(board, source),
                                     [Square(file, rank) for rank in expected_ranks])

    def test_first_piece_blocks_later_pieces(self):
        """前方に複数の駒があっても最初の駒で候補を打ち切る。

        手前の駒を飛び越し、奥の駒まで候補を追加してしまう誤りを検出する。
        """
        for side, opponent, near_rank, far_rank, empty_ranks in [
            (Side.SENTE, Side.GOTE, 3, 1, [4]),
            (Side.GOTE, Side.SENTE, 7, 9, [6]),
        ]:
            for near_owner in (side, opponent):
                for far_owner in (side, opponent):
                    with self.subTest(side=side, near_owner=near_owner, far_owner=far_owner):
                        board = Board()
                        board.set_piece(Square(5, 5), Piece(PieceType.LANCE, side))
                        board.set_piece(Square(5, near_rank), Piece(PieceType.GOLD, near_owner))
                        board.set_piece(Square(5, far_rank), Piece(PieceType.SILVER, far_owner))
                        expected = [Square(5, rank) for rank in empty_ranks]
                        if near_owner == opponent:
                            expected.append(Square(5, near_rank))
                        self.assertEqual(lance_move_candidates(board, Square(5, 5)), expected)

    def test_pieces_outside_forward_file_do_not_block(self):
        """横・斜め・後ろの駒は香の前方の候補を妨げない。

        他の筋や後方の占有まで停止条件に使う誤りを検出する。
        """
        for side, rear_rank, expected_ranks in [
            (Side.SENTE, 6, [4, 3, 2, 1]),
            (Side.GOTE, 4, [6, 7, 8, 9]),
        ]:
            with self.subTest(side=side):
                board = Board()
                board.set_piece(Square(5, 5), Piece(PieceType.LANCE, side))
                for file, rank in [(4, 4), (4, 5), (4, 6),
                                   (6, 4), (6, 5), (6, 6), (5, rear_rank)]:
                    board.set_piece(Square(file, rank), Piece(PieceType.GOLD, side))
                self.assertEqual(lance_move_candidates(board, Square(5, 5)),
                                 [Square(5, rank) for rank in expected_ranks])

    def test_results_are_independent_lists(self):
        """候補あり・自駒・盤外のいずれも独立した候補リストを返す。

        呼び出し側が結果を書き換えたときに、他の呼び出しへ影響する共有を検出する。
        """
        for state, source, expected in [
            ("open", Square(5, 3), [Square(5, 2), Square(5, 1)]),
            ("own", Square(5, 3), []),
            ("outside", Square(5, 1), []),
        ]:
            with self.subTest(state=state):
                board = Board()
                board.set_piece(source, Piece(PieceType.LANCE, Side.SENTE))
                if state == "own":
                    board.set_piece(Square(5, 2), Piece(PieceType.PAWN, Side.SENTE))
                result = lance_move_candidates(board, source)
                another_result = lance_move_candidates(board, source)
                self.assertEqual(result, expected)
                result.append(Square(9, 9))
                self.assertEqual(another_result, expected)
                self.assertEqual(lance_move_candidates(board, source), expected)

    def test_candidate_generation_preserves_all_squares(self):
        """候補あり・自駒・相手駒・盤外の全経路で全81マスを変更しない。

        経路の駒を消す、香を動かす、相手駒を取るなどの盤面更新の混入を検出する。
        """
        squares = [Square(file, rank) for file in range(1, 10) for rank in range(1, 10)]
        for side, opponent, blocked_rank, edge in [
            (Side.SENTE, Side.GOTE, 3, 1),
            (Side.GOTE, Side.SENTE, 7, 9),
        ]:
            for state in ("open", "own", "opponent", "outside"):
                with self.subTest(side=side, state=state):
                    board = Board()
                    source = Square(5, edge if state == "outside" else 5)
                    board.set_piece(source, Piece(PieceType.LANCE, side))
                    if state in ("own", "opponent"):
                        owner = side if state == "own" else opponent
                        board.set_piece(Square(5, blocked_rank), Piece(PieceType.PAWN, owner))
                    board.set_piece(Square(2, 2), Piece(PieceType.KING, opponent))
                    before = [board.piece_at(square) for square in squares]
                    lance_move_candidates(board, source)
                    self.assertEqual([board.piece_at(square) for square in squares], before)

    def test_turn_does_not_restrict_candidates_or_change(self):
        """手番によらず先後の香を調べられ、手番も変えない。

        駒の所有者と手番の混同を、先後の香がある同じ盤面で検出する。
        """
        board = Board()
        board.set_piece(Square(1, 3), Piece(PieceType.LANCE, Side.SENTE))
        board.set_piece(Square(9, 7), Piece(PieceType.LANCE, Side.GOTE))
        position = Position(board, Side.SENTE)
        for turn in Side:
            with self.subTest(turn=turn):
                position.side_to_move = turn
                self.assertEqual(lance_move_candidates(position.board, Square(1, 3)),
                                 [Square(1, 2), Square(1, 1)])
                self.assertEqual(lance_move_candidates(position.board, Square(9, 7)),
                                 [Square(9, 8), Square(9, 9)])
                self.assertEqual(position.side_to_move, turn)

    def test_opponent_piece_is_last_destination(self):
        """相手駒のマスを最後の候補に含め、その先へは進めない。

        相手駒の過剰除外と飛び越しを、先後と直前・途中・最奥段で検出する。
        """
        for side, opponent, blocked_rank, expected_ranks in [
            (Side.SENTE, Side.GOTE, 4, [4]),
            (Side.SENTE, Side.GOTE, 3, [4, 3]),
            (Side.SENTE, Side.GOTE, 1, [4, 3, 2, 1]),
            (Side.GOTE, Side.SENTE, 6, [6]),
            (Side.GOTE, Side.SENTE, 7, [6, 7]),
            (Side.GOTE, Side.SENTE, 9, [6, 7, 8, 9]),
        ]:
            with self.subTest(side=side, blocked_rank=blocked_rank):
                board = Board()
                board.set_piece(Square(5, 5), Piece(PieceType.LANCE, side))
                board.set_piece(Square(5, blocked_rank), Piece(PieceType.PAWN, opponent))
                self.assertEqual(lance_move_candidates(board, Square(5, 5)),
                                 [Square(5, rank) for rank in expected_ranks])

    def test_own_piece_stops_before_its_square(self):
        """自駒の手前までを候補にし、自駒もその先も含めない。

        自駒だけを除いてその先へ進む誤りを、先後と直前・途中・最奥段で検出する。
        """
        for side, blocked_rank, expected_ranks in [
            (Side.SENTE, 4, []),
            (Side.SENTE, 3, [4]),
            (Side.SENTE, 1, [4, 3, 2]),
            (Side.GOTE, 6, []),
            (Side.GOTE, 7, [6]),
            (Side.GOTE, 9, [6, 7, 8]),
        ]:
            with self.subTest(side=side, blocked_rank=blocked_rank):
                board = Board()
                board.set_piece(Square(5, 5), Piece(PieceType.LANCE, side))
                board.set_piece(Square(5, blocked_rank), Piece(PieceType.PAWN, side))
                self.assertEqual(lance_move_candidates(board, Square(5, 5)),
                                 [Square(5, rank) for rank in expected_ranks])

    def test_gote_destinations_are_nearest_first(self):
        """後手の香は段が増える向きへ近い順に進める。

        先手の向きを後手にも適用する誤りと、九段を除きすぎる誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.LANCE, Side.GOTE))
        self.assertEqual(lance_move_candidates(board, Square(5, 5)),
                         [Square(5, 6), Square(5, 7), Square(5, 8), Square(5, 9)])

    def test_sente_destinations_are_nearest_first(self):
        """先手の香は同じ筋の前方を近い順に候補として返す。

        歩と同じ1マスへの制限、筋の変更、後退や候補順の逆転を検出する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.LANCE, Side.SENTE))
        self.assertEqual(lance_move_candidates(board, Square(5, 5)),
                         [Square(5, 4), Square(5, 3), Square(5, 2), Square(5, 1)])

    def test_non_lance_source_is_rejected(self):
        """香以外の駒種を先後どちらでも拒否する。

        歩や銀などを香の動きとして扱う駒種確認の欠落を検出する。
        """
        for side in Side:
            for kind in PieceType:
                if kind == PieceType.LANCE:
                    continue
                with self.subTest(side=side, kind=kind):
                    board = Board()
                    board.set_piece(Square(5, 5), Piece(kind, side))
                    with self.assertRaises(ValueError):
                        lance_move_candidates(board, Square(5, 5))

    def test_empty_source_is_rejected(self):
        """空の出発マスは呼び出しの誤りとして拒否する。

        存在しない香を通常の候補なしとして扱う検証漏れを検出する。
        """
        with self.assertRaises(ValueError):
            lance_move_candidates(Board(), Square(5, 5))


class SilverMoveCandidatesTests(unittest.TestCase):
    def test_destination_occupancy_and_board_preservation(self):
        """銀の全方向で自駒と相手駒を区別し、全81マスを変更しない。

        斜め後ろの占有判定漏れ、相手駒の過剰除外、移動や駒取りの混入を検出する。
        """
        squares = [Square(f, r) for f in range(1, 10) for r in range(1, 10)]
        for side, opponent, coordinates in [
            (Side.SENTE, Side.GOTE, [(5, 4), (6, 4), (4, 4), (6, 6), (4, 6)]),
            (Side.GOTE, Side.SENTE, [(5, 6), (6, 6), (4, 6), (6, 4), (4, 4)]),
        ]:
            destinations = [Square(f, r) for f, r in coordinates]
            for target in destinations:
                for owner in [None, side, opponent]:
                    with self.subTest(side=side, target=target, owner=owner):
                        board = Board()
                        board.set_piece(Square(5, 5), Piece(PieceType.SILVER, side))
                        if owner is not None:
                            board.set_piece(target, Piece(PieceType.PAWN, owner))
                        before = [board.piece_at(square) for square in squares]
                        expected = [sq for sq in destinations if owner != side or sq != target]
                        self.assertEqual(silver_move_candidates(board, Square(5, 5)), expected)
                        self.assertEqual([board.piece_at(square) for square in squares], before)

    def test_all_destinations_blocked_returns_fresh_empty_list(self):
        """銀の全方向が自駒なら毎回独立した空リストを返す。

        候補なしの誤表現と、戻り値の共有による次回計算への影響を検出する。
        """
        for side in Side:
            with self.subTest(side=side):
                board = Board()
                for f, r in [(5, 5), (5, 4), (6, 4), (4, 4),
                             (5, 6), (6, 6), (4, 6)]:
                    board.set_piece(Square(f, r), Piece(PieceType.SILVER, side))
                result = silver_move_candidates(board, Square(5, 5))
                self.assertEqual(result, [])
                result.append(Square(1, 1))
                self.assertEqual(silver_move_candidates(board, Square(5, 5)), [])

    def test_inside_edges_remain_destinations(self):
        """最端の筋・段も盤内なら銀の候補に含める。

        境界の判定範囲を狭めすぎる誤りを、固定の期待値で検出する。
        """
        for side, source, coordinates in [
            (Side.SENTE, Square(2, 2), [(2, 1), (3, 1), (1, 1), (3, 3), (1, 3)]),
            (Side.GOTE, Square(8, 8), [(8, 9), (9, 9), (7, 9), (9, 7), (7, 7)]),
        ]:
            with self.subTest(side=side):
                board = Board()
                board.set_piece(source, Piece(PieceType.SILVER, side))
                self.assertEqual(silver_move_candidates(board, source),
                                 [Square(f, r) for f, r in coordinates])

    def test_turn_does_not_restrict_candidates_or_change(self):
        """手番によらず先後の銀を調べられ、盤外除外でも盤面・手番を変えない。

        所有者と手番の混同や、候補計算への局面更新の混入を検出する。
        """
        board = Board()
        board.set_piece(Square(1, 1), Piece(PieceType.SILVER, Side.SENTE))
        board.set_piece(Square(9, 9), Piece(PieceType.SILVER, Side.GOTE))
        position = Position(board, Side.SENTE)
        squares = [Square(f, r) for f in range(1, 10) for r in range(1, 10)]
        before = [board.piece_at(square) for square in squares]
        for turn in Side:
            with self.subTest(turn=turn):
                position.side_to_move = turn
                self.assertEqual(silver_move_candidates(board, Square(1, 1)), [Square(2, 2)])
                self.assertEqual(silver_move_candidates(board, Square(9, 9)), [Square(8, 8)])
                self.assertEqual(position.side_to_move, turn)
                self.assertEqual([board.piece_at(square) for square in squares], before)

    def test_own_piece_is_excluded_without_losing_other_candidates(self):
        """自駒のある方向だけを除き、残る候補を順序どおり返す。

        自駒の除外漏れと、途中で候補計算全体を終了する誤りを検出する。
        """
        for side, blocked, coordinates in [
            (Side.SENTE, Square(5, 4), [(6, 4), (4, 4), (6, 6), (4, 6)]),
            (Side.GOTE, Square(5, 6), [(6, 6), (4, 6), (6, 4), (4, 4)]),
        ]:
            with self.subTest(side=side):
                board = Board()
                board.set_piece(Square(5, 5), Piece(PieceType.SILVER, side))
                board.set_piece(blocked, Piece(PieceType.PAWN, side))
                self.assertEqual(silver_move_candidates(board, Square(5, 5)),
                                 [Square(f, r) for f, r in coordinates])

    def test_corners_exclude_only_outside_destinations(self):
        """四隅の銀は盤外だけを除外し、盤内の候補を順に返す。

        筋・段の境界確認の欠落と、金の横・真後ろの混入を検出する。
        """
        for side, source, coordinates in [
            (Side.SENTE, Square(1, 1), [(2, 2)]),
            (Side.SENTE, Square(9, 1), [(8, 2)]),
            (Side.SENTE, Square(1, 9), [(1, 8), (2, 8)]),
            (Side.SENTE, Square(9, 9), [(9, 8), (8, 8)]),
            (Side.GOTE, Square(1, 1), [(1, 2), (2, 2)]),
            (Side.GOTE, Square(9, 1), [(9, 2), (8, 2)]),
            (Side.GOTE, Square(1, 9), [(2, 8)]),
            (Side.GOTE, Square(9, 9), [(8, 8)]),
        ]:
            with self.subTest(side=side, source=source):
                board = Board()
                board.set_piece(source, Piece(PieceType.SILVER, side))
                try:
                    candidates = silver_move_candidates(board, source)
                except ValueError as error:
                    self.fail(f"盤外は通常の候補除外として扱う必要がある: {error}")
                self.assertEqual(candidates, [Square(f, r) for f, r in coordinates])

    def test_five_destinations_follow_owner_in_order(self):
        """先後の銀の5候補を固定順で返し、横と真後ろを含めない。

        向きの逆転や金の方向表の流用を、手で確認した期待値で検出する。
        """
        for side, coordinates in [
            (Side.SENTE, [(5, 4), (6, 4), (4, 4), (6, 6), (4, 6)]),
            (Side.GOTE, [(5, 6), (6, 6), (4, 6), (6, 4), (4, 4)]),
        ]:
            with self.subTest(side=side):
                board = Board()
                board.set_piece(Square(5, 5), Piece(PieceType.SILVER, side))
                self.assertEqual(silver_move_candidates(board, Square(5, 5)),
                                 [Square(f, r) for f, r in coordinates])

    def test_non_silver_source_is_rejected(self):
        """銀以外の駒種を先後どちらでも拒否する。

        金などを銀の動きとして扱う駒種確認の欠落を検出する。
        """
        for side in Side:
            for kind in PieceType:
                if kind == PieceType.SILVER:
                    continue
                with self.subTest(side=side, kind=kind):
                    board = Board()
                    board.set_piece(Square(5, 5), Piece(kind, side))
                    with self.assertRaises(ValueError):
                        silver_move_candidates(board, Square(5, 5))

    def test_empty_source_is_rejected(self):
        """空の出発マスは呼び出しの誤りとして拒否する。

        存在しない銀を通常の候補なしとして隠す誤りを検出する。
        """
        with self.assertRaises(ValueError):
            silver_move_candidates(Board(), Square(5, 5))


class GoldMoveCandidatesTests(unittest.TestCase):
    def test_destination_occupancy_and_board_preservation(self):
        """各方向の自駒・相手駒を区別し、全81マスを変更しない。

        横や後ろだけの判定漏れ、相手駒の過剰除外、駒取りの混入を検出する。
        """
        squares = [Square(f, r) for f in range(1, 10) for r in range(1, 10)]
        for side, opponent, coordinates in [
            (Side.SENTE, Side.GOTE, [(5, 4), (6, 4), (4, 4), (6, 5), (4, 5), (5, 6)]),
            (Side.GOTE, Side.SENTE, [(5, 6), (6, 6), (4, 6), (6, 5), (4, 5), (5, 4)]),
        ]:
            destinations = [Square(f, r) for f, r in coordinates]
            for target in destinations:
                for owner in [None, side, opponent]:
                    with self.subTest(side=side, target=target, owner=owner):
                        board = Board()
                        board.set_piece(Square(5, 5), Piece(PieceType.GOLD, side))
                        if owner is not None:
                            board.set_piece(target, Piece(PieceType.PAWN, owner))
                        before = [board.piece_at(square) for square in squares]
                        expected = [sq for sq in destinations if owner != side or sq != target]
                        self.assertEqual(gold_move_candidates(board, Square(5, 5)), expected)
                        self.assertEqual([board.piece_at(square) for square in squares], before)

    def test_all_destinations_blocked_returns_fresh_empty_list(self):
        """全方向が自駒なら毎回独立した空リストを返す。

        候補なしの誤表現と、戻り値の共有による次回計算への汚染を検出する。
        """
        for side in Side:
            with self.subTest(side=side):
                board = Board()
                for f, r in [(5, 5), (5, 4), (6, 4), (4, 4), (6, 5),
                             (4, 5), (5, 6), (6, 6), (4, 6)]:
                    board.set_piece(Square(f, r), Piece(PieceType.GOLD, side))
                result = gold_move_candidates(board, Square(5, 5))
                self.assertEqual(result, [])
                result.append(Square(1, 1))
                self.assertEqual(gold_move_candidates(board, Square(5, 5)), [])

    def test_inside_edges_remain_destinations(self):
        """最端の一段・九段・1筋・9筋を移動先から除きすぎない。

        盤外判定を狭く設定する境界の誤りを固定した期待値で検出する。
        """
        for side, source, coordinates in [
            (Side.SENTE, Square(2, 2), [(2, 1), (3, 1), (1, 1), (3, 2), (1, 2), (2, 3)]),
            (Side.GOTE, Square(8, 8), [(8, 9), (9, 9), (7, 9), (9, 8), (7, 8), (8, 7)]),
        ]:
            with self.subTest(side=side):
                board = Board()
                board.set_piece(source, Piece(PieceType.GOLD, side))
                self.assertEqual(gold_move_candidates(board, source),
                                 [Square(f, r) for f, r in coordinates])

    def test_turn_does_not_restrict_candidates_or_change(self):
        """同じ盤の手番を変えても両側の金の候補は同じで手番も変えない。

        所有者と手番の混同を、先後を含む同じ盤面で検出する。
        """
        board = Board()
        board.set_piece(Square(1, 1), Piece(PieceType.GOLD, Side.SENTE))
        board.set_piece(Square(9, 9), Piece(PieceType.GOLD, Side.GOTE))
        position = Position(board, Side.SENTE)
        squares = [Square(f, r) for f in range(1, 10) for r in range(1, 10)]
        before = [board.piece_at(square) for square in squares]
        for turn in Side:
            position.side_to_move = turn
            self.assertEqual(gold_move_candidates(position.board, Square(1, 1)),
                             [Square(2, 1), Square(1, 2)])
            self.assertEqual(gold_move_candidates(position.board, Square(9, 9)),
                             [Square(8, 9), Square(9, 8)])
            self.assertEqual(position.side_to_move, turn)
            self.assertEqual([board.piece_at(square) for square in squares], before)

    def test_own_piece_is_excluded_without_losing_other_candidates(self):
        """自駒のいる候補だけを除き、残る候補の順序を保つ。

        除外漏れと、一つの自駒で探索を打ち切る誤りを先後両側で検出する。
        """
        for side, blocked, coordinates in [
            (Side.SENTE, Square(5, 4), [(6, 4), (4, 4), (6, 5), (4, 5), (5, 6)]),
            (Side.GOTE, Square(5, 6), [(6, 6), (4, 6), (6, 5), (4, 5), (5, 4)]),
        ]:
            with self.subTest(side=side):
                board = Board()
                board.set_piece(Square(5, 5), Piece(PieceType.GOLD, side))
                board.set_piece(blocked, Piece(PieceType.PAWN, side))
                self.assertEqual(gold_move_candidates(board, Square(5, 5)),
                                 [Square(f, r) for f, r in coordinates])

    def test_corners_exclude_only_outside_destinations(self):
        """四隅で盤外だけを除外し、残る候補を順序どおり返す。

        筋・段どちらの境界確認の欠落も検出し、例外を通常結果にしない。
        """
        for side, source, coordinates in [
            (Side.SENTE, Square(1, 1), [(2, 1), (1, 2)]),
            (Side.SENTE, Square(9, 1), [(8, 1), (9, 2)]),
            (Side.SENTE, Square(1, 9), [(1, 8), (2, 8), (2, 9)]),
            (Side.SENTE, Square(9, 9), [(9, 8), (8, 8), (8, 9)]),
            (Side.GOTE, Square(1, 1), [(1, 2), (2, 2), (2, 1)]),
            (Side.GOTE, Square(9, 1), [(9, 2), (8, 2), (8, 1)]),
            (Side.GOTE, Square(1, 9), [(2, 9), (1, 8)]),
            (Side.GOTE, Square(9, 9), [(8, 9), (9, 8)]),
        ]:
            with self.subTest(side=side, source=source):
                board = Board()
                board.set_piece(source, Piece(PieceType.GOLD, side))
                try:
                    candidates = gold_move_candidates(board, source)
                except ValueError as error:
                    self.fail(f"盤の端の金は通常の候補を返す必要がある: {error}")
                self.assertEqual(candidates, [Square(f, r) for f, r in coordinates])

    def test_six_destinations_follow_owner_in_order(self):
        """先後の金の6候補を決めた順序で返し、斜め後ろを含めない。

        向きの逆転、方向の欠落・重複、余計な方向を固定した期待値で検出する。
        """
        for side, coordinates in [
            (Side.SENTE, [(5, 4), (6, 4), (4, 4), (6, 5), (4, 5), (5, 6)]),
            (Side.GOTE, [(5, 6), (6, 6), (4, 6), (6, 5), (4, 5), (5, 4)]),
        ]:
            with self.subTest(side=side):
                board = Board()
                source = Square(5, 5)
                board.set_piece(source, Piece(PieceType.GOLD, side))
                self.assertEqual(gold_move_candidates(board, source),
                                 [Square(f, r) for f, r in coordinates])

    def test_non_gold_source_is_rejected(self):
        """金以外の全駒種を先後どちらでも拒否する。

        歩などを金として動かせてしまう駒種確認の欠落を検出する。
        """
        for side in Side:
            for kind in PieceType:
                if kind == PieceType.GOLD:
                    continue
                with self.subTest(side=side, kind=kind):
                    board = Board()
                    board.set_piece(Square(5, 5), Piece(kind, side))
                    with self.assertRaises(ValueError):
                        gold_move_candidates(board, Square(5, 5))

    def test_empty_source_is_rejected(self):
        """空の出発マスを呼び出しの誤りとして拒否する。

        存在しない金を候補なしとして黙って扱う誤りを検出する。
        """
        with self.assertRaises(ValueError):
            gold_move_candidates(Board(), Square(5, 5))


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
