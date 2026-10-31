"""比較専用V0/V1の一手選択契約を確認する。"""

import random
import unittest
from pathlib import Path
from unittest.mock import patch

from supported_piece_threat_support import design_case_pieces, position
from undefended_piece_support import mate_case, rotate_and_swap, snapshot

from kaname_shogi import game_search
from kaname_shogi.comparison import (
    BatchStatus,
    ComparisonConfig,
    ComparisonPosition,
    summarize,
)
from kaname_shogi.material_piece_threat import (
    PieceThreatWeights,
    evaluate_material_piece_threat,
)
from kaname_shogi.model import PieceType, Side, Square
from kaname_shogi.move import BoardMove
from kaname_shogi.movegen import is_checkmate, legal_moves, position_after_move
from kaname_shogi.one_ply_selection import choose_one_ply_move
from kaname_shogi.sfen import parse_sfen


def selection_case(perspective: Side):
    """支えあり脅威が異なる二候補を持つV設計Aの先後別局面を返す。"""
    pieces = (
        (PieceType.KING, Side.SENTE, Square(9, 9)),
        *design_case_pieces("A"),
        (PieceType.KING, Side.GOTE, Square(4, 3)),
    )
    if perspective is Side.GOTE:
        pieces = rotate_and_swap(pieces)
        escape = BoardMove(Square(5, 5), Square(4, 4), False)
        preserve = BoardMove(Square(6, 4), Square(6, 5), False)
    else:
        escape = BoardMove(Square(5, 5), Square(6, 6), False)
        preserve = BoardMove(Square(4, 6), Square(4, 5), False)
    return position(*pieces, side_to_move=perspective), escape, preserve


class PieceThreatComparisonPolicyTests(unittest.TestCase):
    def _policy(self, name: str):
        """比較専用policyがない場合もassertionで不足を示す。"""
        policy = getattr(game_search.movegen.MoveSelectionPolicy, name, None)
        self.assertIsNotNone(policy, f"{name}方針を追加してください")
        return policy

    def test_v_comparison_policies_use_exact_weights(self):
        """先後両方でV0/V1が同じM/Uと指定V重みを使う。

        V0/V1の係数逆転、Uの脱落、別評価器への接続を検出する。
        """
        for side in (Side.SENTE, Side.GOTE):
            current, escape, preserve = selection_case(side)
            moves = (escape, preserve)
            self.assertTrue(all(move in legal_moves(current) for move in moves))
            for name, supported_weight in (
                ("MATERIAL_PIECE_THREAT_V0", 0),
                ("MATERIAL_PIECE_THREAT_V1", 1),
            ):
                policy = self._policy(name)
                with self.subTest(side=side, policy=name):
                    with patch(
                        "kaname_shogi.one_ply_selection.choose_one_ply_move",
                        wraps=choose_one_ply_move,
                    ) as chooser:
                        game_search.choose_move(
                            current, moves, policy, random.Random(20261031)
                        )
                    evaluator = chooser.call_args.kwargs["evaluate"]
                    self.assertIs(evaluator.func, evaluate_material_piece_threat)
                    self.assertEqual(
                        evaluator.keywords["weights"],
                        PieceThreatWeights(
                            material=10,
                            undefended=1,
                            supported_threat=supported_weight,
                        ),
                    )

    def test_v_weight_changes_choice_only_for_v_different_candidates(self):
        """M/Uが同じ候補ではV0が同点、V1だけが逃げ手を選ぶ。

        係数以外の選択差、先後依存、候補順依存を検出する。
        """
        v0 = PieceThreatWeights(material=10, undefended=1, supported_threat=0)
        v1 = PieceThreatWeights(material=10, undefended=1, supported_threat=1)
        for side in (Side.SENTE, Side.GOTE):
            with self.subTest(side=side):
                current, escape, preserve = selection_case(side)
                candidates = (escape, preserve)
                expected_v = ((escape, 0), (preserve, -1))
                for move, v_value in expected_v:
                    after = position_after_move(current, move)
                    self.assertEqual(
                        evaluate_material_piece_threat(after, side, weights=v0),
                        210,
                    )
                    self.assertEqual(
                        evaluate_material_piece_threat(after, side, weights=v1),
                        210 + v_value,
                    )

                before = snapshot(current)
                for moves in (candidates, tuple(reversed(candidates))):
                    rng = random.Random(20261031)
                    with patch.object(rng, "choice", wraps=rng.choice) as choice:
                        selected = game_search.choose_move(
                            current,
                            moves,
                            self._policy("MATERIAL_PIECE_THREAT_V0"),
                            rng,
                        )
                    self.assertIn(selected, moves)
                    choice.assert_called_once_with(moves)

                    selected = game_search.choose_move(
                        current,
                        moves,
                        self._policy("MATERIAL_PIECE_THREAT_V1"),
                        random.Random(20261031),
                    )
                    self.assertEqual(selected, escape)
                self.assertEqual(snapshot(current), before)

    def test_v_comparison_policies_prioritize_one_ply_mate(self):
        """両V方式は極端な通常点より先後両方の一手詰みを優先する。

        通常点を勝敗の代用にする誤りと、先後または候補順への依存を検出する。
        """
        for side in (Side.SENTE, Side.GOTE):
            current, mate, normal = mate_case(side)
            self.assertIn(mate, legal_moves(current))
            self.assertIn(normal, legal_moves(current))
            self.assertTrue(is_checkmate(position_after_move(current, mate)))
            self.assertFalse(is_checkmate(position_after_move(current, normal)))
            before = snapshot(current)
            normal_position = position_after_move(current, normal)
            normal_snapshot = snapshot(normal_position)

            def favor_non_mate(
                after, perspective, *, weights, normal_snapshot=normal_snapshot
            ):
                """通常評価で非詰み手を詰み手より極端に高くする。"""
                del perspective, weights
                return 10**30 if snapshot(after) == normal_snapshot else -(10**30)

            for name in (
                "MATERIAL_PIECE_THREAT_V0",
                "MATERIAL_PIECE_THREAT_V1",
            ):
                for moves in ((mate, normal), (normal, mate)):
                    with self.subTest(side=side, policy=name, moves=moves):
                        policy = self._policy(name)
                        with patch(
                            "kaname_shogi.material_piece_threat.evaluate_material_piece_threat",
                            side_effect=favor_non_mate,
                        ) as evaluator:
                            selected = game_search.choose_move(
                                current,
                                moves,
                                policy,
                                random.Random(20261031),
                            )
                        self.assertEqual(selected, mate)
                        evaluator.assert_called_once()
                        self.assertEqual(snapshot(current), before)

    def test_unselected_v_policies_keep_legacy_summary_timing_order(self):
        """旧方式のsummaryへ未選択V方式を追加しない。

        Enum追加後も選択されていない方式の計時列や旧summary順が変わる誤りを検出する。
        """
        self._policy("MATERIAL_PIECE_THREAT_V0")
        self._policy("MATERIAL_PIECE_THREAT_V1")
        start = parse_sfen("8k/9/9/9/9/9/9/9/K8 b - 1").position
        position_data = ComparisonPosition(
            position_id="initial",
            setup_moves=(),
            rationale="summaryの方式列を確認する。",
            start_position=start,
            start_sfen="8k/9/9/9/9/9/9/9/K8 b - 1",
            initial_move_number=1,
        )
        config = ComparisonConfig(
            baseline=game_search.movegen.MoveSelectionPolicy.MATERIAL,
            candidate=game_search.movegen.MoveSelectionPolicy.RANDOM,
            positions=(position_data,),
            pairs_per_position=1,
            seed=0,
            max_plies=1,
            output_dir=Path("unused-output"),
            positions_path=Path("unused-positions.json"),
            positions_json=b"{}",
        )
        summary = summarize(
            config,
            (),
            batch_status=BatchStatus.INTERRUPTED,
            unstarted_games=2,
            elapsed_ns=0,
        )
        self.assertEqual(
            tuple(summary["move_time_by_policy"]),
            (
                "random",
                "material",
                "two-ply-material",
                "full-width-4",
                "alpha-beta-4",
            ),
        )


if __name__ == "__main__":
    unittest.main()
