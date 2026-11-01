"""新しい価値合計評価を既存の一手選択器へ渡す契約を検査する。"""

import random
import unittest
from unittest.mock import Mock, patch

from undefended_piece_support import mate_case, position, rotate_and_swap, snapshot

from kaname_shogi.material_piece_threat import evaluate_material_piece_threat
from kaname_shogi.material_piece_threat_value import (
    PieceThreatValueWeights,
    evaluate_material_piece_threat_value,
)
from kaname_shogi.model import PieceType, Side, Square
from kaname_shogi.move import BoardMove
from kaname_shogi.movegen import is_checkmate, legal_moves, position_after_move
from kaname_shogi.one_ply_selection import choose_one_ply_move


class UndefendedPieceValueSelectionTests(unittest.TestCase):
    @staticmethod
    def _rook_support_case(perspective: Side):
        """飛車を金で支える手と支えない手を持つ局面を返す。"""
        pieces = (
            (PieceType.KING, Side.SENTE, Square(9, 9)),
            (PieceType.ROOK, Side.SENTE, Square(5, 5)),
            (PieceType.GOLD, Side.SENTE, Square(4, 7)),
            (PieceType.KING, Side.GOTE, Square(1, 1)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        )
        if perspective == Side.GOTE:
            pieces = rotate_and_swap(pieces)

        current = position(*pieces, side_to_move=perspective)
        if perspective == Side.SENTE:
            supported = BoardMove(Square(4, 7), Square(4, 6), False)
            unsupported = BoardMove(Square(4, 7), Square(3, 7), False)
        else:
            supported = BoardMove(Square(6, 3), Square(6, 4), False)
            unsupported = BoardMove(Square(6, 3), Square(7, 3), False)
        return current, supported, unsupported

    def test_prefers_support_for_rook_both_sides_and_orders(self):
        """飛車を支える金の移動を先後や候補順によらず選ぶ。

        支えで価値合計差とVの役割が変わること、開始側視点、候補順固定を検出する。
        """
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                current, supported, unsupported = self._rook_support_case(perspective)
                original_before = snapshot(current)
                candidates = legal_moves(current)
                self.assertIn(supported, candidates)
                self.assertIn(unsupported, candidates)

                supported_after = position_after_move(current, supported)
                unsupported_after = position_after_move(current, unsupported)
                self.assertFalse(is_checkmate(supported_after))
                self.assertFalse(is_checkmate(unsupported_after))
                self.assertEqual(snapshot(current), original_before)
                self.assertNotEqual(snapshot(supported_after), snapshot(current))
                self.assertNotEqual(snapshot(unsupported_after), snapshot(current))
                self.assertNotEqual(
                    snapshot(supported_after), snapshot(unsupported_after)
                )

                self.assertEqual(
                    evaluate_material_piece_threat(supported_after, perspective), 230
                )
                self.assertEqual(
                    evaluate_material_piece_threat(unsupported_after, perspective), 230
                )
                self.assertEqual(
                    evaluate_material_piece_threat_value(supported_after, perspective),
                    230,
                )
                self.assertEqual(
                    evaluate_material_piece_threat_value(
                        unsupported_after, perspective
                    ),
                    216,
                )

                for moves in ((supported, unsupported), (unsupported, supported)):
                    selected = choose_one_ply_move(
                        current,
                        moves,
                        random.Random(20261102),
                        evaluate=evaluate_material_piece_threat_value,
                    )
                    self.assertEqual(selected, supported)

    def test_zero_terms_tie_and_empty_candidates(self):
        """追加項を0にした同点は一度抽選し、空候補は評価しない。

        元順序を崩した抽選、空候補への評価、価値項だけ0にしたときのV無視を検出する。
        """
        current, supported, unsupported = self._rook_support_case(Side.SENTE)
        zero_extra_terms = PieceThreatValueWeights(
            undefended_value=0, supported_threat=0
        )
        evaluator = Mock(
            side_effect=lambda after, side: evaluate_material_piece_threat_value(
                after, side, weights=zero_extra_terms
            )
        )
        rng = random.Random(20261102)
        moves = (supported, unsupported)
        with patch.object(rng, "choice", wraps=rng.choice) as choice:
            selected = choose_one_ply_move(current, moves, rng, evaluate=evaluator)

        self.assertIn(selected, moves)
        self.assertEqual(evaluator.call_count, 2)
        for call, move in zip(evaluator.call_args_list, moves, strict=True):
            evaluated_position, perspective = call.args
            self.assertEqual(perspective, Side.SENTE)
            self.assertEqual(
                snapshot(evaluated_position),
                snapshot(position_after_move(current, move)),
            )
        choice.assert_called_once_with(moves)
        self.assertEqual(
            evaluate_material_piece_threat_value(
                position_after_move(current, supported),
                Side.SENTE,
                weights=zero_extra_terms,
            ),
            230,
        )
        self.assertEqual(
            evaluate_material_piece_threat_value(
                position_after_move(current, unsupported),
                Side.SENTE,
                weights=zero_extra_terms,
            ),
            230,
        )

        value_term_zero = PieceThreatValueWeights(undefended_value=0)
        self.assertEqual(
            evaluate_material_piece_threat_value(
                position_after_move(current, supported),
                Side.SENTE,
                weights=value_term_zero,
            ),
            229,
        )
        self.assertEqual(
            evaluate_material_piece_threat_value(
                position_after_move(current, unsupported),
                Side.SENTE,
                weights=value_term_zero,
            ),
            230,
        )

        empty_evaluator = Mock()
        empty_rng = random.Random(20261102)
        with patch.object(empty_rng, "choice", wraps=empty_rng.choice) as empty_choice:
            self.assertIsNone(
                choose_one_ply_move(current, (), empty_rng, evaluate=empty_evaluator)
            )
        empty_evaluator.assert_not_called()
        empty_choice.assert_not_called()

    def test_mate_priority_with_new_evaluator(self):
        """巨大な通常点より一手詰みを優先し、詰み枝を採点しない。

        先後・候補順による詰み優先の崩れと、詰み手への評価呼出しを検出する。
        """
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                current, mate, normal = mate_case(perspective)
                candidates = legal_moves(current)
                self.assertIn(mate, candidates)
                self.assertIn(normal, candidates)
                mate_after = position_after_move(current, mate)
                normal_after = position_after_move(current, normal)
                self.assertTrue(is_checkmate(mate_after))
                self.assertFalse(is_checkmate(normal_after))

                for moves in ((mate, normal), (normal, mate)):
                    evaluator = Mock(
                        side_effect=lambda after, side: (
                            evaluate_material_piece_threat_value(after, side) + 10**30
                        )
                    )
                    rng = random.Random(20261102)
                    with patch.object(rng, "choice", wraps=rng.choice) as choice:
                        selected = choose_one_ply_move(
                            current, moves, rng, evaluate=evaluator
                        )

                    self.assertEqual(selected, mate)
                    evaluator.assert_called_once()
                    evaluated_position, evaluated_perspective = evaluator.call_args.args
                    self.assertEqual(evaluated_perspective, perspective)
                    self.assertEqual(
                        snapshot(evaluated_position), snapshot(normal_after)
                    )
                    choice.assert_called_once_with((mate,))

    def test_evaluator_exception_leaves_source_unchanged(self):
        """新評価の依存例外を伝え、選択元の局面を変更しない。

        評価例外の握りつぶしと候補適用による元局面の破壊を検出する。
        """
        current, supported, unsupported = self._rook_support_case(Side.SENTE)
        before = snapshot(current)
        rng = random.Random(20261102)
        with patch(
            "kaname_shogi.material_piece_threat_value.material_balance",
            side_effect=RuntimeError("駒得評価故障"),
        ) as material:
            with self.assertRaisesRegex(RuntimeError, "駒得評価故障"):
                choose_one_ply_move(
                    current,
                    (supported, unsupported),
                    rng,
                    evaluate=evaluate_material_piece_threat_value,
                )

        material.assert_called_once()
        self.assertEqual(snapshot(current), before)


if __name__ == "__main__":
    unittest.main()
