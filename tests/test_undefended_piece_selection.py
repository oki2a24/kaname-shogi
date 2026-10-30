"""支えのない狙われた駒の評価を一手選択へ注入する契約を確認する。"""

import random
import unittest
from unittest.mock import Mock, patch

from undefended_piece_support import (
    design_case,
    mate_case,
    position,
    rotate_and_swap,
    snapshot,
)

from kaname_shogi.evaluation import material_balance
from kaname_shogi.material_undefended_piece import (
    UndefendedPieceWeights,
    evaluate_material_undefended_piece,
)
from kaname_shogi.model import Position, Side, Square
from kaname_shogi.move import BoardMove
from kaname_shogi.movegen import (
    is_checkmate,
    legal_moves,
    position_after_move,
)
from kaname_shogi.one_ply_selection import choose_one_ply_move
from kaname_shogi.undefended_piece import attacked_undefended_piece_balance


class UndefendedPieceSelectionTests(unittest.TestCase):
    @staticmethod
    def _design_a_for(perspective: Side) -> Position:
        """設計Aを先手視点または先後反転した後手視点で返す。"""
        original = design_case("A")
        pieces = tuple(
            (piece.piece_type, piece.side, Square(file, rank))
            for file in range(1, 10)
            for rank in range(1, 10)
            if (piece := original.board.piece_at(Square(file, rank))) is not None
        )
        if perspective == Side.GOTE:
            pieces = rotate_and_swap(pieces)
        return position(*pieces, side_to_move=perspective)

    @staticmethod
    def _support_moves(perspective: Side) -> tuple[BoardMove, BoardMove]:
        """支えを作る移動と支えから離れる移動を返す。"""
        if perspective == Side.SENTE:
            return (
                BoardMove(Square(4, 7), Square(4, 6), False),
                BoardMove(Square(4, 7), Square(3, 7), False),
            )
        return (
            BoardMove(Square(6, 3), Square(6, 4), False),
            BoardMove(Square(6, 3), Square(7, 3), False),
        )

    def test_selects_supported_piece_for_both_sides_and_orders(self):
        """先後双方で支えを作る手を選ぶ。

        評価値の符号・候補順への固定・新評価を選択器へ渡せない誤りを検出する。
        """
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                current = self._design_a_for(perspective)
                supported, unsupported = self._support_moves(perspective)
                candidates = (supported, unsupported)
                legal = legal_moves(current)
                for move in candidates:
                    self.assertIn(move, legal)

                expected = ((supported, 0, 140), (unsupported, -1, 139))
                for move, expected_undefended, expected_score in expected:
                    with self.subTest(perspective=perspective, move=move):
                        after = position_after_move(current, move)
                        self.assertFalse(is_checkmate(after))
                        self.assertEqual(material_balance(after, perspective), 14)
                        self.assertEqual(
                            attacked_undefended_piece_balance(after, perspective),
                            expected_undefended,
                        )
                        self.assertEqual(
                            evaluate_material_undefended_piece(after, perspective),
                            expected_score,
                        )

                for moves in (candidates, tuple(reversed(candidates))):
                    selected = choose_one_ply_move(
                        current,
                        moves,
                        random.Random(20261030),
                        evaluate=evaluate_material_undefended_piece,
                    )
                    self.assertEqual(selected, supported)

    def test_material_and_zero_weight_keep_both_candidates_tied(self):
        """駒得だけと対象差重み0は元候補を一度の同点抽選へ渡す。

        新評価の暗黙接続、重み0でもUを無視しない誤り、抽選候補の欠落を検出する。
        """
        zero_undefended = UndefendedPieceWeights(undefended=0)
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                current = self._design_a_for(perspective)
                supported, unsupported = self._support_moves(perspective)
                candidates = (supported, unsupported)
                for move in candidates:
                    after = position_after_move(current, move)
                    self.assertEqual(material_balance(after, perspective), 14)
                    self.assertEqual(
                        evaluate_material_undefended_piece(
                            after, perspective, weights=zero_undefended
                        ),
                        140,
                    )

                for moves in (candidates, tuple(reversed(candidates))):
                    for evaluator in (
                        material_balance,
                        lambda after, side: evaluate_material_undefended_piece(
                            after, side, weights=zero_undefended
                        ),
                    ):
                        with self.subTest(moves=moves, evaluator=evaluator):
                            rng = random.Random(20261030)
                            with patch.object(
                                rng, "choice", wraps=rng.choice
                            ) as choice:
                                selected = choose_one_ply_move(
                                    current, moves, rng, evaluate=evaluator
                                )
                            self.assertIn(selected, moves)
                            choice.assert_called_once_with(moves)

    def test_mate_priority_survives_undefended_piece_evaluation(self):
        """巨大な通常評価より一手詰みを優先する。

        先後・候補順で詰み優先が崩れる誤り、詰み手の評価、局面共有を検出する。
        """
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
                            evaluate_material_undefended_piece(after, side) + 10**30
                        )
                    )
                    rng = random.Random(20261030)
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
