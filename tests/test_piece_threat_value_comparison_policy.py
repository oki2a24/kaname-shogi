"""比較専用の駒価値方式を既存の一手選択器へ渡す契約を検査する。"""

import random
import unittest
from unittest.mock import patch

from undefended_piece_support import mate_case, position, rotate_and_swap, snapshot

from kaname_shogi import game_search
from kaname_shogi.material_piece_threat import (
    PieceThreatWeights,
    evaluate_material_piece_threat,
)
from kaname_shogi.material_piece_threat_value import (
    PieceThreatValueWeights,
    evaluate_material_piece_threat_value,
)
from kaname_shogi.model import PieceType, Side, Square
from kaname_shogi.move import BoardMove
from kaname_shogi.movegen import is_checkmate, legal_moves, position_after_move
from kaname_shogi.one_ply_selection import choose_one_ply_move
from kaname_shogi.search_control import SearchControl
from kaname_shogi.sfen import parse_sfen


def rook_support_case(perspective: Side):
    """飛車を金で支える手と支えない手を持つ局面を返す。"""
    pieces = (
        (PieceType.KING, Side.SENTE, Square(9, 9)),
        (PieceType.ROOK, Side.SENTE, Square(5, 5)),
        (PieceType.GOLD, Side.SENTE, Square(4, 7)),
        (PieceType.KING, Side.GOTE, Square(1, 1)),
        (PieceType.PAWN, Side.GOTE, Square(5, 4)),
    )
    if perspective is Side.GOTE:
        pieces = rotate_and_swap(pieces)

    current = position(*pieces, side_to_move=perspective)
    if perspective is Side.SENTE:
        supported = BoardMove(Square(4, 7), Square(4, 6), False)
        unsupported = BoardMove(Square(4, 7), Square(3, 7), False)
    else:
        supported = BoardMove(Square(6, 3), Square(6, 4), False)
        unsupported = BoardMove(Square(6, 3), Square(7, 3), False)
    return current, supported, unsupported


class PieceThreatValueComparisonPolicyTests(unittest.TestCase):
    def _policy(self, name: str):
        """比較専用policyがない場合もassertionで不足を示す。"""
        policy = getattr(game_search.movegen.MoveSelectionPolicy, name, None)
        self.assertIsNotNone(policy, f"{name}方針を追加してください")
        return policy

    def test_value_policy_uses_exact_evaluator_and_weights(self):
        """旧U方式と価値合計方式が異なる評価器・重みを使う。

        旧U evaluatorへの誤接続、新方式の旧undefended keyへの混同、重みの変更を検出する。
        """
        policy_cases = (
            (
                "MATERIAL_PIECE_THREAT_V1",
                evaluate_material_piece_threat,
                PieceThreatWeights(material=10, undefended=1, supported_threat=1),
            ),
            (
                "MATERIAL_PIECE_THREAT_VALUE_V1",
                evaluate_material_piece_threat_value,
                PieceThreatValueWeights(
                    material=10, undefended_value=1, supported_threat=1
                ),
            ),
        )
        for side in (Side.SENTE, Side.GOTE):
            current, supported, unsupported = rook_support_case(side)
            moves = (supported, unsupported)
            self.assertTrue(all(move in legal_moves(current) for move in moves))
            for name, evaluator_function, expected_weights in policy_cases:
                with self.subTest(side=side, policy=name):
                    policy = self._policy(name)
                    with patch(
                        "kaname_shogi.one_ply_selection.choose_one_ply_move",
                        wraps=choose_one_ply_move,
                    ) as chooser:
                        game_search.choose_move(
                            current, moves, policy, random.Random(20261102)
                        )
                    chooser.assert_called_once()
                    evaluator = chooser.call_args.kwargs["evaluate"]
                    self.assertIs(evaluator.func, evaluator_function)
                    self.assertEqual(evaluator.keywords["weights"], expected_weights)

    def test_value_policy_changes_choice_only_for_value_difference(self):
        """旧方式は同点、新方式は飛車を支える候補を選ぶ。

        旧Uとの置換、先後・候補順の不変性、固定された独立得点を検出する。
        """
        old_weights = PieceThreatWeights(material=10, undefended=1, supported_threat=1)
        new_weights = PieceThreatValueWeights(
            material=10, undefended_value=1, supported_threat=1
        )
        for side in (Side.SENTE, Side.GOTE):
            with self.subTest(side=side):
                current, supported, unsupported = rook_support_case(side)
                supported_after = position_after_move(current, supported)
                unsupported_after = position_after_move(current, unsupported)
                self.assertFalse(is_checkmate(supported_after))
                self.assertFalse(is_checkmate(unsupported_after))
                self.assertEqual(
                    evaluate_material_piece_threat(
                        supported_after, side, weights=old_weights
                    ),
                    230,
                )
                self.assertEqual(
                    evaluate_material_piece_threat(
                        unsupported_after, side, weights=old_weights
                    ),
                    230,
                )
                self.assertEqual(
                    evaluate_material_piece_threat_value(
                        supported_after, side, weights=new_weights
                    ),
                    230,
                )
                self.assertEqual(
                    evaluate_material_piece_threat_value(
                        unsupported_after, side, weights=new_weights
                    ),
                    216,
                )

                before = snapshot(current)
                for moves in ((supported, unsupported), (unsupported, supported)):
                    old_move = game_search.choose_move(
                        current,
                        moves,
                        self._policy("MATERIAL_PIECE_THREAT_V1"),
                        random.Random(20261102),
                    )
                    self.assertIn(old_move, moves)
                    selected = game_search.choose_move(
                        current,
                        moves,
                        self._policy("MATERIAL_PIECE_THREAT_VALUE_V1"),
                        random.Random(20261102),
                    )
                    self.assertEqual(selected, supported)
                self.assertEqual(snapshot(current), before)

    def test_value_policy_prioritizes_one_ply_mate(self):
        """新方式は巨大な通常点より先後両方の一手詰みを優先する。

        通常点を勝敗点として扱う誤りと先後・候補順による詰み優先の崩れを検出する。
        """
        policy = self._policy("MATERIAL_PIECE_THREAT_VALUE_V1")
        for side in (Side.SENTE, Side.GOTE):
            current, mate_move, normal_move = mate_case(side)
            candidates = legal_moves(current)
            self.assertIn(mate_move, candidates)
            self.assertIn(normal_move, candidates)
            self.assertTrue(is_checkmate(position_after_move(current, mate_move)))
            self.assertFalse(is_checkmate(position_after_move(current, normal_move)))
            normal_snapshot = snapshot(position_after_move(current, normal_move))

            def favor_non_mate(
                after, perspective, *, weights, expected_snapshot=normal_snapshot
            ):
                """通常評価で非詰み手を詰み手より極端に高くする。"""
                del perspective, weights
                return 10**30 if snapshot(after) == expected_snapshot else -(10**30)

            for moves in ((mate_move, normal_move), (normal_move, mate_move)):
                with self.subTest(side=side, moves=moves):
                    with patch(
                        "kaname_shogi.material_piece_threat_value.evaluate_material_piece_threat_value",
                        side_effect=favor_non_mate,
                    ) as evaluator:
                        selected = game_search.choose_move(
                            current, moves, policy, random.Random(20261102)
                        )
                    self.assertEqual(selected, mate_move)
                    evaluator.assert_called_once()

    def test_value_policy_is_not_exposed_to_controlled_search(self):
        """比較用価値方式を通常の時計付き探索から拒否する。

        比較用policyが通常CLI・USIの制御付き方式一覧へ誤登録されるのを検出する。
        """
        policy = self._policy("MATERIAL_PIECE_THREAT_VALUE_V1")
        start = parse_sfen("8k/9/9/9/9/9/9/9/K8 b - 1").position
        with self.assertRaisesRegex(ValueError, "未知の一手選択方針"):
            game_search.search_move(
                start, policy, random.Random(20261102), SearchControl(None, 0)
            )


if __name__ == "__main__":
    unittest.main()
