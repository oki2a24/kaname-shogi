"""指定した盤上駒の幾何学的な利きを確認する。"""

import unittest
from unittest.mock import patch

from undefended_piece_support import position, rotate_and_swap, snapshot

from kaname_shogi import movegen
from kaname_shogi.model import PieceType, Side, Square


class PieceAttackTests(unittest.TestCase):
    def _attack(self, current, source, target):
        """指定した駒の利き照会を公開操作へ渡す。"""
        attack = getattr(movegen, "is_piece_attacking_square", None)
        self.assertTrue(callable(attack), "指定駒の利き照会操作が必要")
        return attack(current.board, source, target)

    def test_source_target_occupancy_and_blockers(self):
        """味方占有・相手占有・空マスと遮蔽を区別する。"""
        source = Square(5, 9)
        target = Square(5, 5)
        for target_piece_side in (Side.SENTE, Side.GOTE):
            with self.subTest(target_piece_side=target_piece_side):
                current = position(
                    (PieceType.ROOK, Side.SENTE, source),
                    (PieceType.GOLD, target_piece_side, target),
                )
                before = snapshot(current)
                self.assertTrue(self._attack(current, source, target))
                self.assertEqual(snapshot(current), before)

        gote_source = Square(5, 1)
        gote_target = Square(5, 5)
        gote_occupied = position(
            (PieceType.ROOK, Side.GOTE, gote_source),
            (PieceType.GOLD, Side.GOTE, gote_target),
        )
        before = snapshot(gote_occupied)
        self.assertTrue(self._attack(gote_occupied, gote_source, gote_target))
        self.assertEqual(snapshot(gote_occupied), before)

        empty_target = position((PieceType.ROOK, Side.SENTE, source))
        before = snapshot(empty_target)
        self.assertTrue(self._attack(empty_target, source, target))
        self.assertFalse(self._attack(empty_target, source, source))
        self.assertFalse(self._attack(empty_target, Square(2, 2), target))
        self.assertEqual(snapshot(empty_target), before)

        blocked = position(
            (PieceType.ROOK, Side.SENTE, source),
            (PieceType.PAWN, Side.SENTE, Square(5, 7)),
        )
        self.assertFalse(self._attack(blocked, source, target))
        opponent_blocked = position(
            (PieceType.ROOK, Side.SENTE, source),
            (PieceType.PAWN, Side.GOTE, Square(5, 7)),
        )
        self.assertFalse(self._attack(opponent_blocked, source, target))

    def test_king_and_promoted_piece_geometry(self):
        """玉・馬・竜の移動候補を利きとして共有する。"""
        cases = (
            (PieceType.KING, Square(5, 5), Square(4, 4), Square(3, 3)),
            (PieceType.HORSE, Square(5, 5), Square(5, 4), Square(5, 3)),
            (PieceType.DRAGON, Square(5, 5), Square(4, 4), Square(3, 3)),
        )
        for piece_type, source, target, beyond in cases:
            with self.subTest(piece_type=piece_type):
                pieces = ((piece_type, Side.SENTE, source),)
                current = position(*pieces)
                self.assertTrue(self._attack(current, source, target))
                self.assertFalse(self._attack(current, source, beyond))

                mirror = rotate_and_swap(pieces)
                mirrored_position = position(*mirror)
                mirrored_source = Square(10 - source.file, 10 - source.rank)
                mirrored_target = Square(10 - target.file, 10 - target.rank)
                mirrored_beyond = Square(10 - beyond.file, 10 - beyond.rank)
                self.assertTrue(
                    self._attack(mirrored_position, mirrored_source, mirrored_target)
                )
                self.assertFalse(
                    self._attack(mirrored_position, mirrored_source, mirrored_beyond)
                )

        sente_pawn_source = Square(5, 5)
        sente_pawn_target = Square(5, 4)
        sente_pawn = position((PieceType.PAWN, Side.SENTE, sente_pawn_source))
        self.assertTrue(self._attack(sente_pawn, sente_pawn_source, sente_pawn_target))
        gote_pawn_source = Square(5, 5)
        gote_pawn_target = Square(5, 6)
        gote_pawn = position((PieceType.PAWN, Side.GOTE, gote_pawn_source))
        self.assertTrue(self._attack(gote_pawn, gote_pawn_source, gote_pawn_target))

    def test_pinned_source_keeps_geometric_attack(self):
        """ピンされた銀の候補マスも既存の利きと同じく数える。"""
        current = position(
            (PieceType.KING, Side.SENTE, Square(5, 9)),
            (PieceType.SILVER, Side.SENTE, Square(5, 8)),
            (PieceType.ROOK, Side.GOTE, Square(5, 1)),
        )
        self.assertTrue(self._attack(current, Square(5, 8), Square(4, 7)))

    def test_candidate_error_propagates(self):
        """委譲先の候補生成エラーを隠さず呼び出し元へ伝える。"""
        current = position((PieceType.ROOK, Side.SENTE, Square(5, 9)))
        with patch.object(
            movegen, "_move_candidates_for_piece", side_effect=RuntimeError("候補生成")
        ):
            with self.assertRaisesRegex(RuntimeError, "候補生成"):
                self._attack(current, Square(5, 9), Square(5, 8))


if __name__ == "__main__":
    unittest.main()
