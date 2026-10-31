"""M/U/V合成評価を既存一手選択器へ注入する契約を確認する。"""

import random
import unittest
from unittest.mock import Mock, patch

from supported_piece_threat_support import position
from undefended_piece_support import mate_case, rotate_and_swap, snapshot

from kaname_shogi.evaluation import material_balance
from kaname_shogi.material_piece_threat import (
    PieceThreatWeights,
    evaluate_material_piece_threat,
)
from kaname_shogi.model import PieceType, Position, Side, Square
from kaname_shogi.move import BoardMove
from kaname_shogi.movegen import is_checkmate, legal_moves, position_after_move
from kaname_shogi.one_ply_selection import choose_one_ply_move
from kaname_shogi.supported_piece_threat import supported_lower_value_threat_balance
from kaname_shogi.undefended_piece import attacked_undefended_piece_balance


def selection_case(perspective: Side) -> tuple[Position, BoardMove, BoardMove]:
    """支えを維持する手と対象角を逃がす手を持つ局面を返す。"""
    pieces = (
        (PieceType.KING, Side.SENTE, Square(9, 9)),
        (PieceType.BISHOP, Side.SENTE, Square(5, 5)),
        (PieceType.GOLD, Side.SENTE, Square(4, 6)),
        (PieceType.KING, Side.GOTE, Square(4, 3)),
        (PieceType.PAWN, Side.GOTE, Square(5, 4)),
    )
    if perspective == Side.GOTE:
        pieces = rotate_and_swap(pieces)
        escape = BoardMove(Square(5, 5), Square(4, 4), False)
        preserve = BoardMove(Square(6, 4), Square(6, 5), False)
    else:
        escape = BoardMove(Square(5, 5), Square(6, 6), False)
        preserve = BoardMove(Square(4, 6), Square(4, 5), False)
    return position(*pieces, side_to_move=perspective), escape, preserve


class PieceThreatSelectionTests(unittest.TestCase):
    def test_selects_escape_with_v_for_both_sides_and_orders(self):
        """先後双方でVのある枝から角を逃がす手を選ぶ。"""
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                current, escape, preserve = selection_case(perspective)
                candidates = (escape, preserve)
                legal = legal_moves(current)
                for move in candidates:
                    self.assertIn(move, legal)

                expected = ((escape, 0, 210), (preserve, -1, 209))
                for move, expected_v, expected_score in expected:
                    after = position_after_move(current, move)
                    self.assertFalse(is_checkmate(after))
                    self.assertEqual(material_balance(after, perspective), 21)
                    self.assertEqual(
                        attacked_undefended_piece_balance(after, perspective), 0
                    )
                    self.assertEqual(
                        supported_lower_value_threat_balance(after, perspective),
                        expected_v,
                    )
                    self.assertEqual(
                        evaluate_material_piece_threat(after, perspective),
                        expected_score,
                    )

                before = snapshot(current)
                for moves in (candidates, tuple(reversed(candidates))):
                    selected = choose_one_ply_move(
                        current,
                        moves,
                        random.Random(20261031),
                        evaluate=evaluate_material_piece_threat,
                    )
                    self.assertEqual(selected, escape)
                self.assertEqual(snapshot(current), before)

    def test_zero_v_keeps_both_candidates_tied(self):
        """V重み0は双方の候補を同点のまま元順の一回抽選へ渡す。"""
        weights = PieceThreatWeights(supported_threat=0)
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                current, escape, preserve = selection_case(perspective)
                candidates = (escape, preserve)
                before = snapshot(current)
                for moves in (candidates, tuple(reversed(candidates))):
                    for move in moves:
                        after = position_after_move(current, move)
                        self.assertEqual(
                            evaluate_material_piece_threat(
                                after, perspective, weights=weights
                            ),
                            210,
                        )

                    rng = random.Random(20261031)
                    with patch.object(rng, "choice", wraps=rng.choice) as choice:
                        selected = choose_one_ply_move(
                            current,
                            moves,
                            rng,
                            evaluate=lambda after, side: evaluate_material_piece_threat(
                                after, side, weights=weights
                            ),
                        )
                    self.assertIn(selected, moves)
                    choice.assert_called_once_with(moves)
                self.assertEqual(snapshot(current), before)

    def test_mate_priority_with_new_evaluator(self):
        """通常評価が極端に大きくても一手詰みを優先する。"""
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                current, mate, normal = mate_case(perspective)
                self.assertIn(mate, legal_moves(current))
                self.assertIn(normal, legal_moves(current))
                self.assertTrue(is_checkmate(position_after_move(current, mate)))
                self.assertFalse(is_checkmate(position_after_move(current, normal)))
                before = snapshot(current)

                for moves in ((mate, normal), (normal, mate)):
                    evaluator = Mock(
                        side_effect=lambda after, side: (
                            evaluate_material_piece_threat(after, side) + 10**30
                        )
                    )
                    rng = random.Random(20261031)
                    with patch.object(rng, "choice", wraps=rng.choice) as choice:
                        selected = choose_one_ply_move(
                            current, moves, rng, evaluate=evaluator
                        )

                    self.assertEqual(selected, mate)
                    evaluator.assert_called_once()
                    evaluated_position, evaluated_side = evaluator.call_args.args
                    self.assertEqual(evaluated_side, perspective)
                    self.assertEqual(
                        snapshot(evaluated_position),
                        snapshot(position_after_move(current, normal)),
                    )
                    choice.assert_called_once_with((mate,))
                    self.assertEqual(snapshot(current), before)


if __name__ == "__main__":
    unittest.main()
