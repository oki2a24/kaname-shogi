"""歩・金・銀・桂馬・香・飛車・角の向き・占有・盤外と、盤面不変の契約を検証する。"""

import unittest

from kaname_shogi import movegen
from kaname_shogi.model import (BasicPieceType, Board, Piece, PieceType,
                                Position, Side, Square)
from kaname_shogi.movegen import (
    bishop_move_candidates, gold_move_candidates, lance_move_candidates,
    king_move_candidates, knight_move_candidates, pawn_move_candidates,
    rook_move_candidates,
    silver_move_candidates,
)


class PromotedMinorMoveCandidateTests(unittest.TestCase):
    def test_promoted_minor_pieces_move_like_gold_for_sente_and_gote(self):
        """と金・成香・成桂・成銀は先後とも金と同じ6方向へ進める。

        成駒を未成駒の動きや同じ関数の未実装扱いにする誤りを検出する。
        """
        function_names = (
            ("pro_pawn_move_candidates", PieceType.PRO_PAWN),
            ("pro_lance_move_candidates", PieceType.PRO_LANCE),
            ("pro_knight_move_candidates", PieceType.PRO_KNIGHT),
            ("pro_silver_move_candidates", PieceType.PRO_SILVER),
        )
        source = Square(5, 5)
        for function_name, piece_type in function_names:
            self.assertTrue(hasattr(movegen, function_name),
                            function_name + " がまだ実装されていません")
            function = getattr(movegen, function_name)
            for side in Side:
                board = Board()
                board.set_piece(source, Piece(piece_type, side))
                forward = -1 if side == Side.SENTE else 1
                expected = [Square(5, 5 + forward),
                            Square(6, 5 + forward),
                            Square(4, 5 + forward),
                            Square(6, 5), Square(4, 5),
                            Square(5, 5 - forward)]
                with self.subTest(piece_type=piece_type, side=side):
                    self.assertEqual(function(board, source), expected)

    def test_promoted_minor_candidates_exclude_own_piece_and_include_opponent(self):
        """金相当の成駒は自駒を除き、相手駒のマスを候補に含める。

        候補生成で相手駒まで除外する誤りと、自駒を取れる扱いを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.PRO_PAWN, Side.SENTE))
        board.set_piece(Square(6, 5), Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(4, 5), Piece(PieceType.PAWN, Side.GOTE))

        self.assertTrue(hasattr(movegen, "pro_pawn_move_candidates"),
                        "pro_pawn_move_candidates がまだ実装されていません")
        result = movegen.pro_pawn_move_candidates(board, source)

        self.assertNotIn(Square(6, 5), result)
        self.assertIn(Square(4, 5), result)

    def test_promoted_minor_candidate_generation_does_not_change_board(self):
        """金相当の成駒候補生成は盤面を変更しない。

        候補計算中の駒移動や駒取りによる状態変更を検出する。
        """
        board = Board()
        source = Square(5, 5)
        piece = Piece(PieceType.PRO_SILVER, Side.GOTE)
        board.set_piece(source, piece)
        before = [board.piece_at(Square(file, rank))
                  for file in range(1, 10) for rank in range(1, 10)]

        self.assertTrue(hasattr(movegen, "pro_silver_move_candidates"),
                        "pro_silver_move_candidates がまだ実装されていません")
        movegen.pro_silver_move_candidates(board, source)

        after = [board.piece_at(Square(file, rank))
                 for file in range(1, 10) for rank in range(1, 10)]
        self.assertEqual(after, before)


class HorseMoveCandidateTests(unittest.TestCase):
    def test_horse_combines_bishop_moves_with_one_square_orthogonal_moves(self):
        """馬は角の長距離移動と縦横1マスを候補に含める。

        馬を角または玉のどちらか一方の動きだけにする誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.HORSE, Side.SENTE))

        self.assertTrue(hasattr(movegen, "horse_move_candidates"),
                        "horse_move_candidates がまだ実装されていません")
        result = movegen.horse_move_candidates(board, source)

        expected = ([Square(4, 4), Square(3, 3), Square(2, 2), Square(1, 1),
                     Square(6, 4), Square(7, 3), Square(8, 2), Square(9, 1),
                     Square(4, 6), Square(3, 7), Square(2, 8), Square(1, 9),
                     Square(6, 6), Square(7, 7), Square(8, 8), Square(9, 9)]
                    + [Square(5, 4), Square(4, 5), Square(5, 6),
                       Square(6, 5)])
        self.assertEqual(result, expected)

    def test_horse_respects_occupancy_and_preserves_board(self):
        """馬は長距離の駒を飛び越さず、自駒を除き相手駒を含める。

        追加1マスと角の長距離部分で占有規則を別々に誤る実装を検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.HORSE, Side.SENTE))
        board.set_piece(Square(4, 4), Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(6, 4), Piece(PieceType.PAWN, Side.GOTE))
        board.set_piece(Square(5, 4), Piece(PieceType.PAWN, Side.SENTE))
        before = [board.piece_at(Square(file, rank))
                  for file in range(1, 10) for rank in range(1, 10)]

        self.assertTrue(hasattr(movegen, "horse_move_candidates"),
                        "horse_move_candidates がまだ実装されていません")
        result = movegen.horse_move_candidates(board, source)

        self.assertNotIn(Square(4, 4), result)
        self.assertNotIn(Square(3, 3), result)
        self.assertIn(Square(6, 4), result)
        self.assertNotIn(Square(5, 4), result)
        self.assertEqual([board.piece_at(Square(file, rank))
                          for file in range(1, 10) for rank in range(1, 10)], before)


class DragonMoveCandidateTests(unittest.TestCase):
    def test_dragon_combines_rook_moves_with_one_square_diagonal_moves(self):
        """竜は飛車の長距離移動と斜め1マスを候補に含める。

        竜を飛車または玉のどちらか一方の動きだけにする誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.DRAGON, Side.SENTE))

        self.assertTrue(hasattr(movegen, "dragon_move_candidates"),
                        "dragon_move_candidates がまだ実装されていません")
        result = movegen.dragon_move_candidates(board, source)

        expected = ([Square(4, 5), Square(3, 5), Square(2, 5), Square(1, 5),
                     Square(6, 5), Square(7, 5), Square(8, 5), Square(9, 5),
                     Square(5, 4), Square(5, 3), Square(5, 2), Square(5, 1),
                     Square(5, 6), Square(5, 7), Square(5, 8), Square(5, 9)]
                    + [Square(4, 4), Square(6, 4), Square(4, 6),
                       Square(6, 6)])
        self.assertEqual(result, expected)

    def test_dragon_respects_occupancy_and_preserves_board(self):
        """竜は長距離の駒を飛び越さず、自駒を除き相手駒を含める。

        追加1マスと飛車の長距離部分で占有規則を別々に誤る実装を検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.DRAGON, Side.SENTE))
        board.set_piece(Square(4, 5), Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(6, 5), Piece(PieceType.PAWN, Side.GOTE))
        board.set_piece(Square(4, 4), Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(6, 4), Piece(PieceType.PAWN, Side.GOTE))
        before = [board.piece_at(Square(file, rank))
                  for file in range(1, 10) for rank in range(1, 10)]

        self.assertTrue(hasattr(movegen, "dragon_move_candidates"),
                        "dragon_move_candidates がまだ実装されていません")
        result = movegen.dragon_move_candidates(board, source)

        self.assertNotIn(Square(4, 5), result)
        self.assertNotIn(Square(3, 5), result)
        self.assertIn(Square(6, 5), result)
        self.assertNotIn(Square(4, 4), result)
        self.assertIn(Square(6, 4), result)
        self.assertEqual([board.piece_at(Square(file, rank))
                          for file in range(1, 10) for rank in range(1, 10)], before)


class CheckDetectionTests(unittest.TestCase):
    def test_detects_check_from_every_piece_type_for_both_sides(self):
        """全14駒種の利きによる王手を先後とも検出する。

        王手判定の駒種対応漏れ、先後の向きの逆転、成駒の候補表未接続を検出する。
        """
        cases = [
            (PieceType.KING, Square(5, 4), Square(5, 6)),
            (PieceType.ROOK, Square(5, 4), Square(5, 6)),
            (PieceType.BISHOP, Square(4, 4), Square(4, 6)),
            (PieceType.GOLD, Square(5, 4), Square(5, 6)),
            (PieceType.SILVER, Square(5, 4), Square(5, 6)),
            (PieceType.KNIGHT, Square(4, 3), Square(4, 7)),
            (PieceType.LANCE, Square(5, 4), Square(5, 6)),
            (PieceType.PAWN, Square(5, 4), Square(5, 6)),
            (PieceType.PRO_PAWN, Square(5, 4), Square(5, 6)),
            (PieceType.PRO_LANCE, Square(5, 4), Square(5, 6)),
            (PieceType.PRO_KNIGHT, Square(5, 4), Square(5, 6)),
            (PieceType.PRO_SILVER, Square(5, 4), Square(5, 6)),
            (PieceType.HORSE, Square(4, 4), Square(4, 6)),
            (PieceType.DRAGON, Square(5, 4), Square(5, 6)),
        ]
        source = Square(5, 5)
        for piece_type, sente_target, gote_target in cases:
            for attacker_side, target in ((Side.SENTE, sente_target),
                                          (Side.GOTE, gote_target)):
                defender_side = (Side.GOTE if attacker_side == Side.SENTE
                                 else Side.SENTE)
                board = Board()
                board.set_piece(source, Piece(piece_type, attacker_side))
                board.set_piece(target, Piece(PieceType.KING, defender_side))
                board.set_piece(Square(9, 9),
                                Piece(PieceType.KING, attacker_side))
                with self.subTest(piece_type=piece_type,
                                  attacker_side=attacker_side):
                    self.assertTrue(movegen.is_in_check(board, defender_side))
                    if piece_type == PieceType.KING:
                        self.assertTrue(movegen.is_in_check(board, attacker_side))
                    else:
                        self.assertFalse(movegen.is_in_check(board, attacker_side))

    def test_long_range_check_stops_at_own_or_opponent_blocker(self):
        """長距離駒は手前の駒で止まり、遮蔽された玉を王手としない。

        飛車・角・香・馬・竜の走査停止条件を王手判定から取り違える誤りを検出する。
        """
        cases = [
            (PieceType.ROOK, Square(5, 2), Square(5, 3), PieceType.BISHOP),
            (PieceType.BISHOP, Square(2, 2), Square(3, 3), PieceType.ROOK),
            (PieceType.LANCE, Square(5, 2), Square(5, 4), PieceType.BISHOP),
            (PieceType.HORSE, Square(2, 2), Square(3, 3), PieceType.ROOK),
            (PieceType.DRAGON, Square(5, 2), Square(5, 3), PieceType.BISHOP),
        ]
        source = Square(5, 5)
        for piece_type, king_square, blocker_square, blocker_piece_type in cases:
            for blocker_side in Side:
                board = Board()
                board.set_piece(source, Piece(piece_type, Side.SENTE))
                board.set_piece(king_square, Piece(PieceType.KING, Side.GOTE))
                board.set_piece(blocker_square,
                                Piece(blocker_piece_type, blocker_side))
                with self.subTest(piece_type=piece_type,
                                  blocker_side=blocker_side):
                    self.assertFalse(movegen.is_in_check(board, Side.GOTE))

    def test_knight_check_ignores_intermediate_occupancy(self):
        """桂馬の王手は途中の駒に遮られない。

        桂馬を長距離駒と同じ遮蔽規則で扱う誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.KNIGHT, Side.SENTE))
        board.set_piece(Square(4, 3), Piece(PieceType.KING, Side.GOTE))
        board.set_piece(Square(5, 4), Piece(PieceType.PAWN, Side.GOTE))
        board.set_piece(Square(4, 4), Piece(PieceType.PAWN, Side.SENTE))

        self.assertTrue(movegen.is_in_check(board, Side.GOTE))

    def test_adjacent_kings_are_mutually_in_check(self):
        """隣接した玉は互いの利きに入る。

        玉の候補を王手判定から除外する誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 4), Piece(PieceType.KING, Side.GOTE))

        self.assertTrue(movegen.is_in_check(board, Side.SENTE))
        self.assertTrue(movegen.is_in_check(board, Side.GOTE))

    def test_check_detection_returns_false_without_a_king(self):
        """指定側の玉がない部分局面は王手なしとして扱う。

        候補生成用の部分局面を既存の単体テストどおり利用できる契約を確認する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.ROOK, Side.GOTE))

        self.assertFalse(movegen.is_in_check(board, Side.SENTE))

    def test_check_detection_does_not_change_board(self):
        """王手判定は盤面を変更しない。

        王手・非王手・玉なしの各経路で、候補生成中に駒を動かしたり取ったりする
        実装を検出する。
        """
        cases = []

        checked = Board()
        checked.set_piece(Square(5, 5), Piece(PieceType.ROOK, Side.GOTE))
        checked.set_piece(Square(5, 2), Piece(PieceType.KING, Side.SENTE))
        cases.append(("checked", checked, Side.SENTE))

        not_checked = Board()
        not_checked.set_piece(Square(5, 5), Piece(PieceType.ROOK, Side.GOTE))
        not_checked.set_piece(Square(5, 3),
                              Piece(PieceType.BISHOP, Side.GOTE))
        not_checked.set_piece(Square(5, 2), Piece(PieceType.KING, Side.SENTE))
        cases.append(("not_checked", not_checked, Side.SENTE))

        no_king = Board()
        no_king.set_piece(Square(5, 5), Piece(PieceType.ROOK, Side.GOTE))
        cases.append(("no_king", no_king, Side.SENTE))

        for name, board, side in cases:
            before = [board.piece_at(Square(file, rank))
                      for file in range(1, 10) for rank in range(1, 10)]
            with self.subTest(case=name):
                movegen.is_in_check(board, side)
                after = [board.piece_at(Square(file, rank))
                         for file in range(1, 10) for rank in range(1, 10)]
                self.assertEqual(after, before)

    def test_multiple_attackers_and_fully_blocked_lines_have_stable_results(self):
        """複数の攻撃駒があっても、攻撃線の状態だけで王手を決める。

        盤の走査順に依存する早期終了や、遮蔽された線を数える誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 2), Piece(PieceType.KING, Side.GOTE))
        board.set_piece(Square(5, 5), Piece(PieceType.ROOK, Side.SENTE))
        board.set_piece(Square(2, 5), Piece(PieceType.BISHOP, Side.SENTE))
        self.assertTrue(movegen.is_in_check(board, Side.GOTE))

        board.set_piece(Square(5, 3), Piece(PieceType.BISHOP, Side.SENTE))
        board.set_piece(Square(3, 4), Piece(PieceType.PAWN, Side.SENTE))
        self.assertFalse(movegen.is_in_check(board, Side.GOTE))


class LegalMoveTests(unittest.TestCase):
    def _snapshot(self, position):
        """合法性確認前後を比べるため局面の配置・持ち駒・手番を読む。"""
        squares = [Square(file, rank)
                   for file in range(1, 10) for rank in range(1, 10)]
        piece_types = [piece_type for piece_type in BasicPieceType
                       if piece_type != BasicPieceType.KING]
        return (
            tuple(position.board.piece_at(square) for square in squares),
            tuple(position.sente_hand.count(piece_type)
                  for piece_type in piece_types),
            tuple(position.gote_hand.count(piece_type)
                  for piece_type in piece_types),
            position.side_to_move,
        )

    def test_rejects_move_that_leaves_own_king_in_check(self):
        """王手を受けている側の無関係な移動を拒否する。

        王手放置を成功させたり、失敗時に盤面・持ち駒・手番だけを部分変更したりする
        誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 5), Piece(PieceType.ROOK, Side.GOTE))
        board.set_piece(Square(4, 7), Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(9, 1), Piece(PieceType.KING, Side.GOTE))
        position = Position(board, Side.SENTE)
        before = self._snapshot(position)

        with self.assertRaisesRegex(ValueError, "王手"):
            movegen.apply_move(position, Square(4, 7), Square(4, 6))

        self.assertEqual(self._snapshot(position), before)

    def test_rejects_king_move_into_opponent_attack(self):
        """玉を相手の金の利きへ動かす手を拒否する。

        移動先候補に含まれるだけで安全とみなす誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 3), Piece(PieceType.GOLD, Side.GOTE))
        board.set_piece(Square(9, 1), Piece(PieceType.KING, Side.GOTE))
        position = Position(board, Side.SENTE)
        before = self._snapshot(position)

        with self.assertRaisesRegex(ValueError, "王手"):
            movegen.apply_move(position, Square(5, 5), Square(5, 4))

        self.assertEqual(self._snapshot(position), before)

    def test_rejects_move_that_unblocks_attack_on_own_king(self):
        """自玉との間を塞ぐ銀を動かして飛車の利きを通す手を拒否する。

        自玉以外の駒を動かして自ら王手を受ける反則を見逃す誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 3), Piece(PieceType.SILVER, Side.SENTE))
        board.set_piece(Square(5, 1), Piece(PieceType.ROOK, Side.GOTE))
        board.set_piece(Square(9, 1), Piece(PieceType.KING, Side.GOTE))
        position = Position(board, Side.SENTE)
        before = self._snapshot(position)

        with self.assertRaisesRegex(ValueError, "王手"):
            movegen.apply_move(position, Square(5, 3), Square(4, 4))

        self.assertEqual(self._snapshot(position), before)

    def test_allows_king_to_escape_from_check(self):
        """玉を相手飛車の利きから安全な隣接マスへ逃がせる。

        王手中は全ての玉移動を拒否する誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 1), Piece(PieceType.ROOK, Side.GOTE))
        board.set_piece(Square(9, 1), Piece(PieceType.KING, Side.GOTE))
        position = Position(board, Side.SENTE)

        self.assertIsNone(movegen.apply_move(
            position, Square(5, 5), Square(4, 5)))
        self.assertEqual(board.piece_at(Square(4, 5)),
                         Piece(PieceType.KING, Side.SENTE))
        self.assertEqual(position.side_to_move, Side.GOTE)

    def test_allows_king_to_capture_checking_piece(self):
        """玉が安全な王手駒を取って王手を防げる。

        相手駒を取る玉移動を一律に拒否する誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 4), Piece(PieceType.GOLD, Side.GOTE))
        board.set_piece(Square(9, 1), Piece(PieceType.KING, Side.GOTE))
        position = Position(board, Side.SENTE)

        self.assertIsNone(movegen.apply_move(
            position, Square(5, 5), Square(5, 4)))
        self.assertEqual(board.piece_at(Square(5, 4)),
                         Piece(PieceType.KING, Side.SENTE))
        self.assertEqual(position.sente_hand.count(BasicPieceType.GOLD), 1)

    def test_allows_drop_between_king_and_rook(self):
        """飛車の直線王手に対する合い駒の打ちを許可する。

        駒打ち後の王手判定を行わない誤りと、合い駒を一律に拒否する誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 1), Piece(PieceType.ROOK, Side.GOTE))
        board.set_piece(Square(9, 1), Piece(PieceType.KING, Side.GOTE))
        position = Position(board, Side.SENTE)
        position.sente_hand.add(BasicPieceType.GOLD)

        self.assertIsNone(movegen.apply_drop(
            position, BasicPieceType.GOLD, Square(5, 3)))
        self.assertEqual(board.piece_at(Square(5, 3)),
                         Piece(PieceType.GOLD, Side.SENTE))
        self.assertEqual(position.sente_hand.count(BasicPieceType.GOLD), 0)
        self.assertEqual(position.side_to_move, Side.GOTE)

    def test_rejects_drop_as_response_to_knight_check(self):
        """桂馬の王手に対する合い駒の打ちを拒否する。

        桂馬の飛び越しを合い駒で遮れると誤って扱う実装を検出する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(4, 3), Piece(PieceType.KNIGHT, Side.GOTE))
        board.set_piece(Square(9, 1), Piece(PieceType.KING, Side.GOTE))
        position = Position(board, Side.SENTE)
        position.sente_hand.add(BasicPieceType.GOLD)
        before = self._snapshot(position)

        with self.assertRaisesRegex(ValueError, "王手"):
            movegen.apply_drop(position, BasicPieceType.GOLD, Square(5, 4))

        self.assertEqual(self._snapshot(position), before)

    def test_rejects_drop_that_leaves_own_king_in_check(self):
        """王手を遮らない駒打ちを拒否する。

        駒打ちでは自玉の安全確認を省略する誤りと、持ち駒を先に減らす誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 1), Piece(PieceType.ROOK, Side.GOTE))
        board.set_piece(Square(9, 1), Piece(PieceType.KING, Side.GOTE))
        position = Position(board, Side.SENTE)
        position.sente_hand.add(BasicPieceType.GOLD)
        before = self._snapshot(position)

        with self.assertRaisesRegex(ValueError, "王手"):
            movegen.apply_drop(position, BasicPieceType.GOLD, Square(4, 4))

        self.assertEqual(self._snapshot(position), before)


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
    def _apply_move(self, position, source, destination, *, promote=False):
        """局面への移動適用関数を取得し、未実装をテスト失敗として扱う。"""
        self.assertTrue(hasattr(movegen, "apply_move"),
                        "apply_move がまだ実装されていません")
        try:
            if promote:
                return movegen.apply_move(position, source, destination,
                                          promote=True)
            return movegen.apply_move(position, source, destination)
        except (TypeError, KeyError) as error:
            raise AssertionError("成り指定または成駒の拒否が未実装です") from error

    def _hand_counts(self, position):
        """先後の玉以外の持ち駒枚数を、比較用の変更不可の値として返す。"""
        piece_types = [piece_type for piece_type in BasicPieceType
                       if piece_type != BasicPieceType.KING]
        return (
            tuple(position.sente_hand.count(piece_type)
                  for piece_type in piece_types),
            tuple(position.gote_hand.count(piece_type)
                  for piece_type in piece_types),
        )

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

    def test_captures_opponent_pawn_adds_hand_and_switches_turn(self):
        """候補内の相手歩を取り、指した側の持ち駒へ歩を1枚加える。

        取られた駒を盤上に残す、指した側ではない持ち駒へ加える、または手番を
        交代しない誤りを、先手・後手の両方で検出する。
        """
        cases = [
            (Side.SENTE, Square(5, 5), Square(5, 4), Side.GOTE),
            (Side.GOTE, Square(5, 5), Square(5, 6), Side.SENTE),
        ]
        for side, source, destination, expected_turn in cases:
            board = Board()
            board.set_piece(source, Piece(PieceType.PAWN, side))
            board.set_piece(destination, Piece(PieceType.PAWN, expected_turn))
            position = Position(board, side)
            with self.subTest(side=side):
                self.assertIsNone(self._apply_move(position, source, destination))
                self.assertIsNone(board.piece_at(source))
                self.assertEqual(board.piece_at(destination),
                                 Piece(PieceType.PAWN, side))
                hand = (position.sente_hand if side == Side.SENTE
                        else position.gote_hand)
                other_hand = (position.gote_hand if side == Side.SENTE
                              else position.sente_hand)
                self.assertEqual(hand.count(BasicPieceType.PAWN), 1)
                self.assertEqual(other_hand.count(BasicPieceType.PAWN), 0)
                self.assertEqual(position.side_to_move, expected_turn)

    def test_capturing_each_promoted_piece_restores_basic_hand_piece(self):
        """成駒を取ると、対応する基本駒種が持ち駒へ加わる。

        成駒をそのまま持ち駒として保存する誤りと、別の基本駒種へ戻す誤りを検出する。
        """
        cases = [
            (PieceType.PRO_PAWN, BasicPieceType.PAWN),
            (PieceType.PRO_LANCE, BasicPieceType.LANCE),
            (PieceType.PRO_KNIGHT, BasicPieceType.KNIGHT),
            (PieceType.PRO_SILVER, BasicPieceType.SILVER),
            (PieceType.HORSE, BasicPieceType.BISHOP),
            (PieceType.DRAGON, BasicPieceType.ROOK),
        ]
        for promoted_type, basic_type in cases:
            board = Board()
            source, destination = Square(5, 5), Square(5, 4)
            board.set_piece(source, Piece(PieceType.PAWN, Side.SENTE))
            board.set_piece(destination, Piece(promoted_type, Side.GOTE))
            position = Position(board, Side.SENTE)
            with self.subTest(promoted_type=promoted_type):
                self.assertIsNone(self._apply_move(position, source, destination))
                self.assertEqual(position.sente_hand.count(basic_type), 1)
                self.assertEqual(position.gote_hand.count(basic_type), 0)

    def test_rejects_capture_of_king_without_changing_position(self):
        """相手玉を取る移動を拒否し、局面のどの状態も変更しない。

        玉を通常の持ち駒として加える、盤面だけを変更する、または例外時に手番を
        交代する誤りを検出する。
        """
        board = Board()
        source, destination = Square(5, 5), Square(5, 4)
        board.set_piece(source, Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(destination, Piece(PieceType.KING, Side.GOTE))
        position = Position(board, Side.SENTE)
        squares = [Square(file, rank) for file in range(1, 10)
                   for rank in range(1, 10)]
        before_board = [board.piece_at(square) for square in squares]
        before_hands = self._hand_counts(position)

        with self.assertRaisesRegex(ValueError, "玉は取れません"):
            self._apply_move(position, source, destination)

        self.assertEqual([board.piece_at(square) for square in squares], before_board)
        self.assertEqual(position.side_to_move, Side.SENTE)
        self.assertEqual(self._hand_counts(position), before_hands)

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
            before_hands = self._hand_counts(position)
            with self.subTest(side=side):
                with self.assertRaises(ValueError):
                    self._apply_move(position, source, destination)
                self.assertEqual([board.piece_at(square) for square in squares], before)
                self.assertEqual(position.side_to_move, side)
                self.assertEqual(self._hand_counts(position), before_hands)

    def test_rejects_invalid_move_without_changing_board_or_turn(self):
        """不正な移動は盤面と手番のどちらも変更しない。

        盤面変更後に失敗する処理や、例外時にも手番だけ交代する誤りを検出する。
        """
        cases = [
            ("empty_source", Square(5, 5), Square(5, 4), ()),
            ("occupied_destination", Square(5, 5), Square(5, 4),
             ((Square(5, 5), Piece(PieceType.PAWN, Side.SENTE)),
              (Square(5, 4), Piece(PieceType.GOLD, Side.SENTE)))),
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
            before_hands = self._hand_counts(position)
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    self._apply_move(position, source, destination)
                after_board = [board.piece_at(Square(file, rank))
                               for file in range(1, 10) for rank in range(1, 10)]
                self.assertEqual(after_board, before_board)
                self.assertEqual(position.side_to_move, Side.SENTE)
                self.assertEqual(self._hand_counts(position), before_hands)

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
            before_hands = self._hand_counts(position)
            with self.subTest(turn=turn, piece_side=piece_side):
                with self.assertRaises(ValueError):
                    self._apply_move(position, source, destination)
                after_board = [board.piece_at(Square(file, rank))
                               for file in range(1, 10) for rank in range(1, 10)]
                self.assertEqual(after_board, before_board)
                self.assertEqual(position.side_to_move, turn)
                self.assertEqual(self._hand_counts(position), before_hands)

    def test_promotes_optional_piece_when_source_or_destination_is_enemy_camp(self):
        """未成の歩を敵陣へ成りとして動かし、成駒を置く。

        成り指定を無視して未成駒を置く誤りを、先後双方で検出する。
        """
        cases = (
            (Side.SENTE, Square(5, 4), Square(5, 3)),
            (Side.GOTE, Square(5, 6), Square(5, 7)),
        )
        for side, source, destination in cases:
            board = Board()
            board.set_piece(source, Piece(PieceType.PAWN, side))
            position = Position(board, side)
            with self.subTest(side=side):
                self.assertIsNone(self._apply_move(
                    position, source, destination, promote=True))
                self.assertEqual(board.piece_at(destination),
                                 Piece(PieceType.PRO_PAWN, side))

    def test_promotes_when_only_source_is_in_enemy_camp(self):
        """移動前だけが敵陣でも、成りを選べる。

        敵陣から出る移動で移動後だけを調べる誤りを検出する。
        """
        board = Board()
        source, destination = Square(5, 3), Square(4, 4)
        board.set_piece(source, Piece(PieceType.SILVER, Side.SENTE))
        position = Position(board, Side.SENTE)

        self.assertIsNone(self._apply_move(
            position, source, destination, promote=True))
        self.assertEqual(board.piece_at(destination),
                         Piece(PieceType.PRO_SILVER, Side.SENTE))

    def test_rejects_promotion_outside_enemy_camp_without_changing_position(self):
        """敵陣に関係しない成り指定を拒否し、局面を変更しない。

        任意の移動を成りとして適用する誤りを検出する。
        """
        board = Board()
        source, destination = Square(5, 5), Square(5, 4)
        board.set_piece(source, Piece(PieceType.PAWN, Side.SENTE))
        position = Position(board, Side.SENTE)
        before = [board.piece_at(Square(file, rank))
                  for file in range(1, 10) for rank in range(1, 10)]

        with self.assertRaises(ValueError):
            self._apply_move(position, source, destination, promote=True)

        self.assertEqual([board.piece_at(Square(file, rank))
                          for file in range(1, 10) for rank in range(1, 10)],
                         before)
        self.assertEqual(position.side_to_move, Side.SENTE)

    def test_rejects_gold_promotion_without_changing_position(self):
        """金の成り指定を拒否し、局面を変更しない。

        敵陣に入る駒はすべて成れると誤って扱う実装を検出する。
        """
        board = Board()
        source, destination = Square(5, 4), Square(5, 3)
        board.set_piece(source, Piece(PieceType.GOLD, Side.SENTE))
        position = Position(board, Side.SENTE)

        with self.assertRaises(ValueError):
            self._apply_move(position, source, destination, promote=True)
        self.assertEqual(board.piece_at(source), Piece(PieceType.GOLD, Side.SENTE))
        self.assertIsNone(board.piece_at(destination))
        self.assertEqual(position.side_to_move, Side.SENTE)

    def test_rejects_non_promotion_when_pawn_has_no_destination(self):
        """歩を最奥段へ不成で進める操作を拒否する。

        行き所のない駒を盤上に残す誤りを検出する。
        """
        board = Board()
        source, destination = Square(5, 2), Square(5, 1)
        board.set_piece(source, Piece(PieceType.PAWN, Side.SENTE))
        position = Position(board, Side.SENTE)

        with self.assertRaises(ValueError):
            self._apply_move(position, source, destination)
        self.assertEqual(board.piece_at(source), Piece(PieceType.PAWN, Side.SENTE))
        self.assertIsNone(board.piece_at(destination))
        self.assertEqual(position.side_to_move, Side.SENTE)

    def test_rejects_non_promotion_when_knight_has_no_destination(self):
        """桂を最奥段へ不成で進める操作を拒否する。

        桂の強制成りの境界を歩の規則だけで扱う誤りを検出する。
        """
        board = Board()
        source, destination = Square(5, 3), Square(4, 1)
        board.set_piece(source, Piece(PieceType.KNIGHT, Side.SENTE))
        position = Position(board, Side.SENTE)

        with self.assertRaises(ValueError):
            self._apply_move(position, source, destination)
        self.assertEqual(board.piece_at(source), Piece(PieceType.KNIGHT, Side.SENTE))
        self.assertIsNone(board.piece_at(destination))

    def test_forces_promotion_for_pawn_lance_and_knight(self):
        """歩・香・桂は行き所のない段への移動で成駒になる。

        不成を拒否するだけで成り駒を配置しない実装を、先後と駒種の境界で検出する。
        """
        cases = [
            (Side.SENTE, PieceType.PAWN, Square(5, 2), Square(5, 1),
             PieceType.PRO_PAWN),
            (Side.SENTE, PieceType.LANCE, Square(5, 2), Square(5, 1),
             PieceType.PRO_LANCE),
            (Side.SENTE, PieceType.KNIGHT, Square(5, 3), Square(4, 1),
             PieceType.PRO_KNIGHT),
            (Side.GOTE, PieceType.PAWN, Square(5, 8), Square(5, 9),
             PieceType.PRO_PAWN),
            (Side.GOTE, PieceType.LANCE, Square(5, 8), Square(5, 9),
             PieceType.PRO_LANCE),
            (Side.GOTE, PieceType.KNIGHT, Square(5, 7), Square(4, 9),
             PieceType.PRO_KNIGHT),
        ]
        for side, piece_type, source, destination, promoted_type in cases:
            board = Board()
            board.set_piece(source, Piece(piece_type, side))
            position = Position(board, side)
            with self.subTest(side=side, piece_type=piece_type):
                self.assertIsNone(self._apply_move(
                    position, source, destination, promote=True))
                self.assertEqual(board.piece_at(destination),
                                 Piece(promoted_type, side))

    def test_moves_each_promoted_piece_and_keeps_its_piece_type(self):
        """6種類の成駒は候補内へ移動し、成駒種を保ったまま手番を交代する。

        成駒を未成駒として扱う誤りと、成駒の移動を一律に拒否する誤りを検出する。
        """
        cases = [
            (PieceType.PRO_PAWN, Square(5, 4)),
            (PieceType.PRO_LANCE, Square(5, 4)),
            (PieceType.PRO_KNIGHT, Square(5, 4)),
            (PieceType.PRO_SILVER, Square(5, 4)),
            (PieceType.HORSE, Square(4, 4)),
            (PieceType.DRAGON, Square(4, 5)),
        ]
        for piece_type, destination in cases:
            for side in Side:
                side_destination = destination
                if piece_type == PieceType.PRO_PAWN or piece_type == PieceType.PRO_LANCE:
                    side_destination = Square(5, 5 + (-1 if side == Side.SENTE else 1))
                elif piece_type == PieceType.PRO_KNIGHT or piece_type == PieceType.PRO_SILVER:
                    side_destination = Square(5, 5 + (-1 if side == Side.SENTE else 1))
                elif piece_type == PieceType.HORSE:
                    side_destination = Square(4, 4 if side == Side.SENTE else 6)
                board = Board()
                source = Square(5, 5)
                piece = Piece(piece_type, side)
                board.set_piece(source, piece)
                position = Position(board, side)
                expected_turn = Side.GOTE if side == Side.SENTE else Side.SENTE
                with self.subTest(piece_type=piece_type, side=side):
                    self.assertIsNone(self._apply_move(
                        position, source, side_destination))
                    self.assertIsNone(board.piece_at(source))
                    self.assertEqual(board.piece_at(side_destination), piece)
                    self.assertEqual(position.side_to_move, expected_turn)

    def test_captures_with_promoted_piece_restores_captured_base_piece(self):
        """成駒で相手駒を取ると、取った駒を基本駒種で持ち駒に加える。

        成駒の移動だけ成功して駒取りや持ち駒復元を忘れる誤りを検出する。
        """
        board = Board()
        source, destination = Square(5, 5), Square(4, 4)
        board.set_piece(source, Piece(PieceType.HORSE, Side.SENTE))
        board.set_piece(destination, Piece(PieceType.DRAGON, Side.GOTE))
        position = Position(board, Side.SENTE)

        self.assertIsNone(self._apply_move(position, source, destination))

        self.assertEqual(board.piece_at(destination),
                         Piece(PieceType.HORSE, Side.SENTE))
        self.assertEqual(position.sente_hand.count(BasicPieceType.ROOK), 1)
        self.assertEqual(position.side_to_move, Side.GOTE)

    def test_rejects_promotion_flag_for_promoted_piece_without_changing_position(self):
        """成駒への成り指定を拒否し、局面を変更しない。

        成駒をもう一度成れる扱いにする誤りと、失敗時の部分変更を検出する。
        """
        board = Board()
        source, destination = Square(5, 5), Square(5, 4)
        piece = Piece(PieceType.PRO_PAWN, Side.SENTE)
        board.set_piece(source, piece)
        position = Position(board, Side.SENTE)

        with self.assertRaises(ValueError):
            self._apply_move(position, source, destination, promote=True)
        self.assertEqual(board.piece_at(source), piece)
        self.assertIsNone(board.piece_at(destination))
        self.assertEqual(position.side_to_move, Side.SENTE)


class ApplyDropTests(unittest.TestCase):
    def _apply_drop(self, position, piece_type, destination):
        """局面への駒打ち適用関数を取得し、未実装をテスト失敗として扱う。"""
        self.assertTrue(hasattr(movegen, "apply_drop"),
                        "apply_drop がまだ実装されていません")
        return movegen.apply_drop(position, piece_type, destination)

    def _hand_counts(self, position):
        """先後の玉以外の持ち駒枚数を、比較用の変更不可の値として返す。"""
        piece_types = [piece_type for piece_type in BasicPieceType
                       if piece_type != BasicPieceType.KING]
        return (
            tuple(position.sente_hand.count(piece_type)
                  for piece_type in piece_types),
            tuple(position.gote_hand.count(piece_type)
                  for piece_type in piece_types),
        )

    def _assert_position_unchanged(self, position, before_board, before_hands,
                                   before_turn):
        """盤面・双方の持ち駒・手番が、失敗前から変わらないことを確認する。"""
        squares = [Square(file, rank) for file in range(1, 10)
                   for rank in range(1, 10)]
        self.assertEqual([position.board.piece_at(square) for square in squares],
                         before_board)
        self.assertEqual(self._hand_counts(position), before_hands)
        self.assertEqual(position.side_to_move, before_turn)

    def test_drops_hand_pawn_to_empty_square_and_switches_turn(self):
        """手番側の持ち歩を空マスへ打ち、手番を交代する。

        先後の取り違え、盤上への配置漏れ、持ち駒の減算漏れ、手番の交代漏れを
        先手・後手の両方で検出する。
        """
        destination = Square(5, 5)
        cases = [(Side.SENTE, Side.GOTE), (Side.GOTE, Side.SENTE)]
        for side, expected_turn in cases:
            position = Position(Board(), side)
            hand = (position.sente_hand if side == Side.SENTE
                    else position.gote_hand)
            other_hand = (position.gote_hand if side == Side.SENTE
                          else position.sente_hand)
            hand.add(BasicPieceType.PAWN)
            with self.subTest(side=side):
                self.assertIsNone(self._apply_drop(position, BasicPieceType.PAWN,
                                                    destination))
                self.assertEqual(position.board.piece_at(destination),
                                 Piece(PieceType.PAWN, side))
                self.assertEqual(hand.count(BasicPieceType.PAWN), 0)
                self.assertEqual(other_hand.count(BasicPieceType.PAWN), 0)
                self.assertEqual(position.side_to_move, expected_turn)

    def test_rejects_unowned_piece_without_changing_position(self):
        """0枚の持ち駒を打つ操作を拒否し、局面を変更しない。

        持っていない駒を盤上へ置く誤り、負の枚数への減算、例外時の手番交代を
        検出する。
        """
        position = Position(Board(), Side.SENTE)
        squares = [Square(file, rank) for file in range(1, 10)
                   for rank in range(1, 10)]
        before_board = [position.board.piece_at(square) for square in squares]
        before_hands = self._hand_counts(position)

        with self.assertRaises(ValueError):
            self._apply_drop(position, BasicPieceType.PAWN, Square(5, 5))

        self._assert_position_unchanged(position, before_board, before_hands,
                                        Side.SENTE)

    def test_rejects_occupied_square_without_changing_position(self):
        """先手・後手の駒があるマスへの打ちを拒否し、局面を変更しない。

        到着駒を上書きする誤り、持ち駒を先に減らす誤り、例外時に手番を交代する
        誤りを、占有する側の両方で検出する。
        """
        destination = Square(5, 5)
        for occupying_side in Side:
            position = Position(Board(), Side.SENTE)
            position.sente_hand.add(BasicPieceType.PAWN)
            position.board.set_piece(destination,
                                     Piece(PieceType.SILVER, occupying_side))
            squares = [Square(file, rank) for file in range(1, 10)
                       for rank in range(1, 10)]
            before_board = [position.board.piece_at(square) for square in squares]
            before_hands = self._hand_counts(position)
            with self.subTest(occupying_side=occupying_side):
                with self.assertRaises(ValueError):
                    self._apply_drop(position, BasicPieceType.PAWN, destination)
                self._assert_position_unchanged(position, before_board,
                                                before_hands, Side.SENTE)

    def test_rejects_double_pawn_without_changing_position(self):
        """同じ筋に自分の歩がある持ち歩打ちを拒否し、局面を変更しない。

        持ち駒を先に減らすこと、例外時に手番を交代することを、先手・後手の両方で
        検出する。
        """
        for side, pawn_rank in ((Side.SENTE, 7), (Side.GOTE, 3)):
            position = Position(Board(), side)
            hand = (position.sente_hand if side == Side.SENTE
                    else position.gote_hand)
            hand.add(BasicPieceType.PAWN)
            position.board.set_piece(Square(5, pawn_rank),
                                     Piece(PieceType.PAWN, side))
            squares = [Square(file, rank) for file in range(1, 10)
                       for rank in range(1, 10)]
            before_board = [position.board.piece_at(square) for square in squares]
            before_hands = self._hand_counts(position)
            with self.subTest(side=side):
                with self.assertRaises(ValueError):
                    self._apply_drop(position, BasicPieceType.PAWN, Square(5, 5))
                self._assert_position_unchanged(position, before_board,
                                                before_hands, side)

    def test_allows_non_pawn_drop_on_file_with_own_pawn(self):
        """同じ筋に自分の歩があっても、銀の打ちは二歩として拒否しない。

        二歩の制限を歩以外の駒打ちへ誤って広げることを検出する。
        """
        position = Position(Board(), Side.SENTE)
        position.sente_hand.add(BasicPieceType.SILVER)
        position.board.set_piece(Square(5, 7),
                                 Piece(PieceType.PAWN, Side.SENTE))

        self.assertIsNone(self._apply_drop(position, BasicPieceType.SILVER,
                                           Square(5, 5)))
        self.assertEqual(position.board.piece_at(Square(5, 5)),
                         Piece(PieceType.SILVER, Side.SENTE))

    def test_allows_drop_on_file_with_own_promoted_pawn(self):
        """自分のと金がある筋でも、持ち歩を二歩として拒否しない。

        成駒を未成歩と誤認して二歩にする判定を検出する。
        """
        position = Position(Board(), Side.SENTE)
        position.sente_hand.add(BasicPieceType.PAWN)
        position.board.set_piece(Square(5, 7),
                                 Piece(PieceType.PRO_PAWN, Side.SENTE))

        self.assertIsNone(self._apply_drop(
            position, BasicPieceType.PAWN, Square(5, 5)))
        self.assertEqual(position.board.piece_at(Square(5, 5)),
                         Piece(PieceType.PAWN, Side.SENTE))

    def test_rejects_piece_with_no_legal_destination_without_changing_position(self):
        """行き所のない段への歩・香・桂打ちを拒否し、局面を変更しない。

        持ち駒を先に減らすこと、駒を盤上へ置くこと、例外時に手番を交代する
        誤りを、先後それぞれの禁止段で検出する。
        """
        cases = (
            (Side.SENTE, PieceType.PAWN, 1),
            (Side.SENTE, PieceType.LANCE, 1),
            (Side.SENTE, PieceType.KNIGHT, 1),
            (Side.SENTE, PieceType.KNIGHT, 2),
            (Side.GOTE, PieceType.PAWN, 9),
            (Side.GOTE, PieceType.LANCE, 9),
            (Side.GOTE, PieceType.KNIGHT, 8),
            (Side.GOTE, PieceType.KNIGHT, 9),
        )
        for side, piece_type, rank in cases:
            position = Position(Board(), side)
            hand = (position.sente_hand if side == Side.SENTE
                    else position.gote_hand)
            hand.add(BasicPieceType[piece_type.name])
            squares = [Square(file, board_rank) for file in range(1, 10)
                       for board_rank in range(1, 10)]
            before_board = [position.board.piece_at(square)
                            for square in squares]
            before_hands = self._hand_counts(position)
            with self.subTest(side=side, piece_type=piece_type, rank=rank):
                with self.assertRaises(ValueError):
                    self._apply_drop(position, piece_type, Square(5, rank))
                self._assert_position_unchanged(position, before_board,
                                                before_hands, side)

    def test_allows_piece_drop_just_before_no_legal_destination(self):
        """禁止段の一つ手前へ歩・香・桂を打てる。

        行き所のない駒の判定が必要以上に広がり、進める段への正しい駒打ちまで
        拒否する誤りを、先後それぞれで検出する。
        """
        cases = (
            (Side.SENTE, PieceType.PAWN, 2, Side.GOTE),
            (Side.SENTE, PieceType.LANCE, 2, Side.GOTE),
            (Side.SENTE, PieceType.KNIGHT, 3, Side.GOTE),
            (Side.GOTE, PieceType.PAWN, 8, Side.SENTE),
            (Side.GOTE, PieceType.LANCE, 8, Side.SENTE),
            (Side.GOTE, PieceType.KNIGHT, 7, Side.SENTE),
        )
        for side, piece_type, rank, expected_turn in cases:
            position = Position(Board(), side)
            hand = (position.sente_hand if side == Side.SENTE
                    else position.gote_hand)
            destination = Square(5, rank)
            basic_piece_type = BasicPieceType[piece_type.name]
            hand.add(basic_piece_type)
            with self.subTest(side=side, piece_type=piece_type, rank=rank):
                self.assertIsNone(self._apply_drop(position, basic_piece_type,
                                                    destination))
                self.assertEqual(position.board.piece_at(destination),
                                 Piece(piece_type, side))
                self.assertEqual(hand.count(BasicPieceType[piece_type.name]), 0)
                self.assertEqual(position.side_to_move, expected_turn)

    def test_rejects_king_without_changing_position(self):
        """玉を打つ操作を拒否し、局面を変更しない。

        玉を盤上へ置く誤りや、玉の指定で既存の持ち駒・手番まで変える誤りを
        検出する。
        """
        position = Position(Board(), Side.SENTE)
        position.sente_hand.add(BasicPieceType.PAWN)
        squares = [Square(file, rank) for file in range(1, 10)
                   for rank in range(1, 10)]
        before_board = [position.board.piece_at(square) for square in squares]
        before_hands = self._hand_counts(position)

        with self.assertRaises(ValueError):
            self._apply_drop(position, BasicPieceType.KING, Square(5, 5))

        self._assert_position_unchanged(position, before_board, before_hands,
                                        Side.SENTE)


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


class LegalMoveEnumerationTests(unittest.TestCase):
    def _snapshot(self, position):
        """合法手の有無を調べる前後で局面全体を比較する。"""
        squares = [Square(file, rank)
                   for file in range(1, 10) for rank in range(1, 10)]
        piece_types = [piece_type for piece_type in BasicPieceType
                       if piece_type != BasicPieceType.KING]
        return (
            tuple(position.board.piece_at(square) for square in squares),
            tuple(position.sente_hand.count(piece_type)
                  for piece_type in piece_types),
            tuple(position.gote_hand.count(piece_type)
                  for piece_type in piece_types),
            position.side_to_move,
        )

    def test_finds_legal_board_move_without_changing_position(self):
        """盤上の一手があれば合法手ありと判定し、局面を変更しない。

        盤上移動を走査しない、成功した試し指しを元の局面へ漏らす誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(9, 1), Piece(PieceType.KING, Side.GOTE))
        board.set_piece(Square(5, 5), Piece(PieceType.PAWN, Side.SENTE))
        position = Position(board, Side.SENTE)
        before = self._snapshot(position)

        self.assertTrue(hasattr(movegen, "has_legal_move"),
                        "has_legal_move がまだ実装されていません")
        self.assertTrue(movegen.has_legal_move(position))
        self.assertEqual(self._snapshot(position), before)

    def test_finds_legal_drop_without_changing_position(self):
        """持ち駒を打つ一手があれば合法手ありと判定し、局面を変更しない。

        盤上移動だけを調べて駒打ちを見落とす、試し打ちで持ち駒を減らす誤りを検出する。
        """
        board = Board()
        for file in range(1, 10):
            for rank in range(1, 10):
                if Square(file, rank) != Square(5, 9):
                    board.set_piece(Square(file, rank),
                                    Piece(PieceType.PAWN, Side.SENTE))
        position = Position(board, Side.SENTE)
        position.sente_hand.add(BasicPieceType.GOLD)
        before = self._snapshot(position)

        self.assertTrue(hasattr(movegen, "has_legal_move"),
                        "has_legal_move がまだ実装されていません")
        self.assertTrue(movegen.has_legal_move(position))
        self.assertEqual(self._snapshot(position), before)

    def test_returns_false_when_current_rules_reject_every_candidate(self):
        """全候補が自駒で塞がれた局面では合法手なしを返す。

        候補外や自駒への移動を成功扱いにする、候補の失敗を見落とす誤りを検出する。
        """
        board = Board()
        for file in range(1, 10):
            for rank in range(1, 10):
                board.set_piece(Square(file, rank),
                                Piece(PieceType.PAWN, Side.SENTE))
        position = Position(board, Side.SENTE)
        before = self._snapshot(position)

        self.assertTrue(hasattr(movegen, "has_legal_move"),
                        "has_legal_move がまだ実装されていません")
        self.assertFalse(movegen.has_legal_move(position))
        self.assertEqual(self._snapshot(position), before)
