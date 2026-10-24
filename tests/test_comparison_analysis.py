"""比較分析の一局得点・組集約・区間判定を確認する。"""

import unittest
from fractions import Fraction

from kaname_shogi.comparison import GameEndReason
from kaname_shogi.comparison_analysis import (
    PairScore,
    ScoreAnalysis,
    analyze_scores,
    decide_interval,
    game_score_bounds,
    make_pair_score,
    reference_pair_count,
)
from kaname_shogi.movegen import MoveSelectionPolicy


class GameScoreBoundsTests(unittest.TestCase):
    def test_wins_and_losses_are_scored_from_the_candidate_policy(self):
        """勝者方式に従って候補の勝ちを1、負けを0にする。

        先後側だけから勝敗を割り当てたり、基準方式の勝ちを候補の得点へ反転する
        誤りを検出する。
        """
        candidate = MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY
        baseline = MoveSelectionPolicy.MATERIAL
        for reason in (
            GameEndReason.CHECKMATE,
            GameEndReason.NO_LEGAL_MOVE,
            GameEndReason.PERPETUAL_CHECK_LOSS,
        ):
            with self.subTest(reason=reason, winner="candidate"):
                self.assertEqual(
                    game_score_bounds(reason, candidate, candidate),
                    (Fraction(1), Fraction(1)),
                )
            with self.subTest(reason=reason, winner="baseline"):
                self.assertEqual(
                    game_score_bounds(reason, baseline, candidate),
                    (Fraction(0), Fraction(0)),
                )

    def test_draw_and_unresolved_results_keep_their_distinct_bounds(self):
        """通常千日手は1/2、未決着と未裁定は0〜1にする。

        未裁定を確定引分けへ縮めたり、上限到達を候補負けへ固定する誤りを検出する。
        """
        candidate = MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY
        self.assertEqual(
            game_score_bounds(GameEndReason.REPETITION, None, candidate),
            (Fraction(1, 2), Fraction(1, 2)),
        )
        for reason in (
            GameEndReason.PLY_LIMIT,
            GameEndReason.UNRESOLVED_DOUBLE_PERPETUAL_CHECK,
        ):
            with self.subTest(reason=reason):
                self.assertEqual(
                    game_score_bounds(reason, None, candidate),
                    (Fraction(0), Fraction(1)),
                )

    def test_interrupted_error_and_winner_inconsistencies_are_rejected(self):
        """割込み・故障と終局に合わない勝者情報を集計前に拒否する。

        実行失敗を成績へ混ぜたり、引分・上限に架空の勝者を割り当てる誤りを検出する。
        """
        candidate = MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY
        for reason in (GameEndReason.INTERRUPTED, GameEndReason.ERROR):
            with self.subTest(reason=reason):
                with self.assertRaises(ValueError):
                    game_score_bounds(reason, None, candidate)
        with self.assertRaises(ValueError):
            game_score_bounds(GameEndReason.CHECKMATE, None, candidate)
        with self.assertRaises(ValueError):
            game_score_bounds(GameEndReason.REPETITION, candidate, candidate)


class PairScoreTests(unittest.TestCase):
    def test_two_game_bounds_are_averaged_as_exact_fractions(self):
        """勝ち＋千日手を3/4、上限＋負けを0〜1/2へ正確に集約する。

        float丸めや二局の合計を使い平均しない誤り、未知結果を0.5固定する誤りを検出する。
        """
        win_and_draw = make_pair_score(
            (
                (Fraction(1), Fraction(1)),
                (Fraction(1, 2), Fraction(1, 2)),
            )
        )
        unresolved_and_loss = make_pair_score(
            (
                (Fraction(0), Fraction(1)),
                (Fraction(0), Fraction(0)),
            )
        )
        self.assertEqual(win_and_draw, PairScore(Fraction(3, 4), Fraction(3, 4)))
        self.assertEqual(
            unresolved_and_loss,
            PairScore(Fraction(0), Fraction(1, 2)),
        )

    def test_pair_score_rejects_invalid_fraction_ranges_and_shape(self):
        """組得点の型・範囲・端点順・二局数を検証する。"""
        for bounds in (
            ((Fraction(-1), Fraction(0)), (Fraction(0), Fraction(1))),
            ((Fraction(3, 4), Fraction(1, 2)), (Fraction(0), Fraction(1))),
            ((0.0, Fraction(1)), (Fraction(0), Fraction(1))),
            ((Fraction(0), Fraction(1)),),
        ):
            with self.subTest(bounds=bounds):
                with self.assertRaises(ValueError):
                    make_pair_score(bounds)
        for lower, upper in (
            (Fraction(-1), Fraction(0)),
            (Fraction(3, 4), Fraction(1, 2)),
            (Fraction(0), 1.0),
            (Fraction(0), Fraction(2)),
        ):
            with self.subTest(lower=lower, upper=upper):
                with self.assertRaises(ValueError):
                    PairScore(lower, upper)


class ScoreAnalysisTests(unittest.TestCase):
    def test_hoeffding_radius_and_reference_count_match_fixed_values(self):
        """100組の半径と参考組数を独立した固定値へ照合する。"""
        scores = [PairScore(Fraction(1), Fraction(1))] * 100

        analysis = analyze_scores(scores, purpose="confirmation")

        self.assertIsInstance(analysis, ScoreAnalysis)
        self.assertEqual(analysis.pairs, 100)
        self.assertEqual(analysis.lower_mean, Fraction(1))
        self.assertEqual(analysis.upper_mean, Fraction(1))
        self.assertAlmostEqual(analysis.radius, 0.13581015157406195)
        self.assertAlmostEqual(analysis.lower, 0.8641898484259381)
        self.assertEqual(analysis.upper, 1.0)
        self.assertEqual(analysis.decision, "improved")
        self.assertEqual(reference_pair_count(), 2035)

        reference_analysis = analyze_scores(
            [PairScore(Fraction(0), Fraction(0))] * 2035,
            purpose="confirmation",
        )
        self.assertAlmostEqual(reference_analysis.radius, 0.030105789945364038)

    def test_pair_means_preserve_hand_calculated_bounds(self):
        """二組の平均下限3/8・上限5/8を製品計算と独立に確認する。"""
        pairs = (
            PairScore(Fraction(3, 4), Fraction(3, 4)),
            PairScore(Fraction(0), Fraction(1, 2)),
        )

        analysis = analyze_scores(pairs, purpose="confirmation")

        self.assertEqual(analysis.lower_mean, Fraction(3, 8))
        self.assertEqual(analysis.upper_mean, Fraction(5, 8))
        self.assertEqual(analysis.lower, 0.0)
        self.assertEqual(analysis.upper, 1.0)
        self.assertEqual(analysis.decision, "inconclusive")

    def test_one_pair_alone_cannot_support_improvement(self):
        """一組全勝でも広い95％区間が50％を含み改善支持にしない。"""
        analysis = analyze_scores(
            [PairScore(Fraction(1), Fraction(1))], purpose="confirmation"
        )

        self.assertEqual(analysis.pairs, 1)
        self.assertEqual(analysis.lower, 0.0)
        self.assertEqual(analysis.upper, 1.0)
        self.assertEqual(analysis.decision, "inconclusive")

    def test_interval_decision_respects_open_half_boundary_and_pilot(self):
        """50％一致は判断不能とし、pilotはどの幅でも正式判定しない。"""
        self.assertEqual(
            decide_interval(0.5, 0.7, purpose="confirmation"), "inconclusive"
        )
        self.assertEqual(
            decide_interval(0.3, 0.5, purpose="confirmation"), "inconclusive"
        )
        self.assertEqual(
            decide_interval(0.500001, 0.7, purpose="confirmation"), "improved"
        )
        self.assertEqual(
            decide_interval(0.3, 0.499999, purpose="confirmation"), "worsened"
        )
        self.assertEqual(decide_interval(0.6, 0.7, purpose="pilot"), "exploratory")
        self.assertEqual(
            analyze_scores(
                [PairScore(Fraction(1), Fraction(1))] * 100, purpose="pilot"
            ).decision,
            "exploratory",
        )

    def test_empty_input_bad_purpose_and_invalid_intervals_are_rejected(self):
        """標本数0・不正目的・逆転範囲・非有限値を拒否する。"""
        with self.assertRaises(ValueError):
            analyze_scores([], purpose="confirmation")
        with self.assertRaises(ValueError):
            analyze_scores([PairScore(Fraction(0), Fraction(1))], purpose="other")
        with self.assertRaises(ValueError):
            analyze_scores([(Fraction(0), Fraction(1))], purpose="pilot")
        for lower, upper in (
            (0.7, 0.6),
            (-0.1, 0.5),
            (0.0, 1.1),
            (float("nan"), 1.0),
            (0.0, float("inf")),
            (True, 1.0),
        ):
            with self.subTest(lower=lower, upper=upper):
                with self.assertRaises(ValueError):
                    decide_interval(lower, upper, purpose="confirmation")
        with self.assertRaises(ValueError):
            decide_interval(0.0, 1.0, purpose="other")


if __name__ == "__main__":
    unittest.main()
