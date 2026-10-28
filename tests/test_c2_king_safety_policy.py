"""比較用の玉周辺安全度付き一手方式の接続を確認する。"""

import random
import unittest
from unittest.mock import patch

from kaname_shogi import game_search
from kaname_shogi.material_king_safety import evaluate_material_king_safety
from kaname_shogi.model import Piece, PieceType, Side
from kaname_shogi.movegen import MoveSelectionPolicy, legal_moves
from tests.test_king_safety_selection import _king_danger_case, _mate_case


class RecordingChoice:
    """抽選に渡された候補を記録し、先頭の一手を返すテスト用操作。"""

    def __init__(self):
        self.candidates = None

    def choice(self, candidates):
        self.candidates = tuple(candidates)
        return candidates[0]


class KingSafetyComparisonPolicyTests(unittest.TestCase):
    def choose(self, name, position, moves, rng):
        """未接続の比較方式を振る舞いの失敗として報告する。"""
        policy = MoveSelectionPolicy.__members__.get(name)
        try:
            return game_search.choose_move(position, moves, policy, rng)
        except ValueError as error:
            self.fail(f"比較方式 {name} を使って選択できません: {error}")

    def test_candidate_prefers_safer_move_for_both_sides(self):
        """候補方式は先後双方で安全な玉移動を選ぶ。

        評価項の未接続と開始側の視点や符号の取り違えを検出する。
        """
        for side in (Side.SENTE, Side.GOTE):
            position, unsafe, safe = _king_danger_case(side)
            self.assertIn(unsafe, legal_moves(position))
            self.assertIn(safe, legal_moves(position))
            for moves in ((unsafe, safe), (safe, unsafe)):
                with self.subTest(side=side, moves=moves):
                    selected = self.choose(
                        "MATERIAL_KING_SAFETY", position, moves, random.Random(17)
                    )
                    self.assertEqual(selected, safe)

    def test_control_keeps_equal_material_moves_tied(self):
        """対照方式は駒得が同じ二候補を同点で抽選する。

        安全度重みを誤って有効にしたり候補の順序を失う誤りを検出する。
        """
        for side in (Side.SENTE, Side.GOTE):
            position, unsafe, safe = _king_danger_case(side)
            for moves in ((unsafe, safe), (safe, unsafe)):
                with self.subTest(side=side, moves=moves):
                    rng = RecordingChoice()
                    self.choose(
                        "MATERIAL_KING_SAFETY_MATERIAL_ONLY", position, moves, rng
                    )
                    self.assertEqual(rng.candidates, moves)

    def test_policy_uses_exact_weighted_scores_for_both_sides(self):
        """両方式の実評価値は手計算した重み付き期待値と一致する。

        選択結果の順位が同じでも、駒得10や安全度0・1を誤って渡す問題を検出する。
        """
        for side in (Side.SENTE, Side.GOTE):
            position, unsafe, safe = _king_danger_case(side)
            for name, expected in (
                ("MATERIAL_KING_SAFETY", [-11, -10]),
                ("MATERIAL_KING_SAFETY_MATERIAL_ONLY", [-10, -10]),
            ):
                with self.subTest(side=side, policy=name):
                    scores = []

                    def record_evaluation(
                        after, perspective, *, weights, recorded=scores
                    ):
                        score = evaluate_material_king_safety(
                            after, perspective, weights=weights
                        )
                        recorded.append(score)
                        return score

                    with patch(
                        "kaname_shogi.material_king_safety.evaluate_material_king_safety",
                        side_effect=record_evaluation,
                    ):
                        self.choose(name, position, (unsafe, safe), RecordingChoice())
                    self.assertEqual(scores, expected)

    def test_both_policies_prioritize_one_ply_mate(self):
        """両方式は先後双方で一手詰みを通常評価より優先する。

        一方だけ旧MATERIAL経路を使い詰みを見落とす誤りを検出する。
        """
        for side in (Side.SENTE, Side.GOTE):
            position, mate, normal = _mate_case(side)
            enemy = Side.GOTE if side is Side.SENTE else Side.SENTE
            position.board.set_piece(normal.destination, Piece(PieceType.ROOK, enemy))
            self.assertIn(mate, legal_moves(position))
            self.assertIn(normal, legal_moves(position))
            for name in ("MATERIAL_KING_SAFETY", "MATERIAL_KING_SAFETY_MATERIAL_ONLY"):
                for moves in ((normal, mate), (mate, normal)):
                    with self.subTest(side=side, policy=name, moves=moves):
                        rng = RecordingChoice()
                        selected = self.choose(name, position, moves, rng)
                        self.assertEqual(selected, mate)
                        self.assertEqual(rng.candidates, (mate,))
