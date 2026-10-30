"""未守備駒評価の比較policyが同じ一手選択に接続されることを確認する。"""

import random
import unittest
from pathlib import Path
from unittest.mock import patch

from kaname_shogi import (
    comparison_result_io,
    game_search,
    material_undefended_piece,
    one_ply_selection,
)
from kaname_shogi.comparison import ComparisonConfig
from kaname_shogi.material_undefended_piece import UndefendedPieceWeights
from kaname_shogi.model import Side, Square
from kaname_shogi.move import BoardMove
from kaname_shogi.movegen import (
    MoveSelectionPolicy,
    is_checkmate,
    legal_moves,
    position_after_move,
)
from tests.undefended_piece_support import (
    design_case,
    mate_case,
    position,
    rotate_and_swap,
    snapshot,
)


class UndefendedPiecePolicyTests(unittest.TestCase):
    @staticmethod
    def _policy(name):
        """追加policyがあれば返し、未接続なら意図したassertionで失敗する。"""
        return MoveSelectionPolicy.__members__.get(name)

    @staticmethod
    def _design_a_for(perspective):
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
    def _support_moves(perspective):
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

    def test_unselected_undefended_policies_do_not_change_legacy_summary_order(self):
        """未選択の連携policyを旧比較のsummary計時へ混入しない。

        enum列挙値を無条件で計時欄へ出し、既存成果物の再集計を壊す誤りを検出する。
        """
        config = ComparisonConfig(
            baseline=MoveSelectionPolicy.MATERIAL,
            candidate=MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY,
            positions=(),
            pairs_per_position=1,
            seed=20261030,
            max_plies=1,
            output_dir=Path("unused-output"),
            positions_path=Path("unused-positions.json"),
            positions_json=b"{}",
        )

        self.assertEqual(
            comparison_result_io._summary_policy_order(config),
            (
                MoveSelectionPolicy.RANDOM,
                MoveSelectionPolicy.MATERIAL,
                MoveSelectionPolicy.TWO_PLY_MATERIAL,
                MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH,
                MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA,
                MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY,
            ),
        )

    def test_policy_uses_exact_undefended_weights_for_both_sides(self):
        """先手・後手双方でpolicyが10/0と10/1の固定評価を選択器へ渡す。

        重みの逆転・同一化、片側だけの符号誤り、一手選択器を迂回する誤りを検出する。
        """
        policy_cases = (
            ("MATERIAL_UNDEFENDED_PIECE_MATERIAL_ONLY", 0, (140, 140), None),
            ("MATERIAL_UNDEFENDED_PIECE", 1, (140, 139), "supported"),
        )
        evaluate_material_undefended_piece = (
            material_undefended_piece.evaluate_material_undefended_piece
        )
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                current = self._design_a_for(perspective)
                supported, unsupported = self._support_moves(perspective)
                moves = (supported, unsupported)
                for name, weight, expected_scores, unique_best in policy_cases:
                    with self.subTest(policy=name):
                        policy = self._policy(name)
                        self.assertIsNotNone(policy, f"比較policy {name} が未接続です")
                        score_calls = []

                        def record_evaluation(
                            after, side, *, weights, calls=score_calls
                        ):
                            score = evaluate_material_undefended_piece(
                                after, side, weights=weights
                            )
                            calls.append((weights, score))
                            return score

                        rng = random.Random(20261030)
                        with patch.object(
                            material_undefended_piece,
                            "evaluate_material_undefended_piece",
                            side_effect=record_evaluation,
                        ):
                            with patch.object(
                                one_ply_selection,
                                "choose_one_ply_move",
                                wraps=one_ply_selection.choose_one_ply_move,
                            ) as selector:
                                with patch.object(
                                    rng, "choice", wraps=rng.choice
                                ) as choice:
                                    selected = game_search.choose_move(
                                        current, moves, policy, rng
                                    )

                        selector.assert_called_once()
                        expected_weights = UndefendedPieceWeights(
                            material=10, undefended=weight
                        )
                        self.assertEqual(
                            score_calls,
                            [
                                (expected_weights, expected_scores[0]),
                                (expected_weights, expected_scores[1]),
                            ],
                        )
                        expected_tied_moves = (
                            moves if unique_best is None else (supported,)
                        )
                        choice.assert_called_once_with(expected_tied_moves)
                        self.assertIn(selected, expected_tied_moves)

    def test_candidate_prefers_supported_piece_for_both_sides_and_orders(self):
        """先後と候補順を反転しても候補policyは支えを作る手を選ぶ。

        固定した候補位置だけを優先する誤りと、評価視点の符号反転漏れを検出する。
        """
        name = "MATERIAL_UNDEFENDED_PIECE"
        policy = self._policy(name)
        self.assertIsNotNone(policy, f"比較policy {name} が未接続です")
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                current = self._design_a_for(perspective)
                supported, unsupported = self._support_moves(perspective)
                self.assertIn(supported, legal_moves(current))
                self.assertIn(unsupported, legal_moves(current))
                for moves in ((supported, unsupported), (unsupported, supported)):
                    with self.subTest(moves=moves):
                        selected = game_search.choose_move(
                            current, moves, policy, random.Random(20261030)
                        )
                        self.assertEqual(selected, supported)

    def test_both_policies_prioritize_one_ply_mate(self):
        """両policyが巨大な通常評価より一手詰みを優先する。

        先後・候補順での優先順位逆転と、詰み局面を通常評価へ渡す誤りを検出する。
        """
        policy_cases = (
            ("MATERIAL_UNDEFENDED_PIECE_MATERIAL_ONLY", 0),
            ("MATERIAL_UNDEFENDED_PIECE", 1),
        )
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                current, mate, normal = mate_case(perspective)
                self.assertIn(mate, legal_moves(current))
                self.assertIn(normal, legal_moves(current))
                self.assertTrue(is_checkmate(position_after_move(current, mate)))
                self.assertFalse(is_checkmate(position_after_move(current, normal)))
                before = snapshot(current)
                for name, weight in policy_cases:
                    policy = self._policy(name)
                    self.assertIsNotNone(policy, f"比較policy {name} が未接続です")
                    for moves in ((mate, normal), (normal, mate)):
                        with self.subTest(policy=name, moves=moves):
                            rng = random.Random(20261030)
                            with patch.object(
                                material_undefended_piece,
                                "evaluate_material_undefended_piece",
                                return_value=10**30,
                            ) as evaluate:
                                with patch.object(
                                    rng, "choice", wraps=rng.choice
                                ) as choice:
                                    selected = game_search.choose_move(
                                        current, moves, policy, rng
                                    )

                            self.assertEqual(selected, mate)
                            evaluate.assert_called_once()
                            evaluated_position, evaluated_side = evaluate.call_args.args
                            self.assertEqual(evaluated_side, perspective)
                            self.assertEqual(
                                snapshot(evaluated_position),
                                snapshot(position_after_move(current, normal)),
                            )
                            self.assertEqual(
                                evaluate.call_args.kwargs["weights"].undefended,
                                weight,
                            )
                            choice.assert_called_once_with((mate,))
                            self.assertEqual(snapshot(current), before)


if __name__ == "__main__":
    unittest.main()
