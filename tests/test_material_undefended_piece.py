"""駒得と支えのない狙われた駒の差を合成する評価を確認する。"""

import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import patch

from undefended_piece_support import (
    both_nonzero_case,
    design_case,
    position,
    snapshot,
)

from kaname_shogi import material_undefended_piece
from kaname_shogi.material_undefended_piece import (
    UndefendedPieceWeights,
    evaluate_material_undefended_piece,
)
from kaname_shogi.model import BasicPieceType, PieceType, Side, Square


class MaterialUndefendedPieceTests(unittest.TestCase):
    def test_combines_independent_expected_values(self):
        """独立に手計算した駒得と対象枚数差を両視点で合成する。

        Uの符号・係数違い、片側だけの式、駒得だけを返す実装を検出する。
        """
        cases = (
            ("A", design_case("A"), 139),
            ("B", design_case("B"), 140),
            ("C", design_case("C"), 140),
            ("both_sides", position(*both_nonzero_case()), 139),
        )
        for name, current, expected_sente in cases:
            with self.subTest(case=name, perspective=Side.SENTE):
                self.assertEqual(
                    evaluate_material_undefended_piece(current, Side.SENTE),
                    expected_sente,
                )
            with self.subTest(case=name, perspective=Side.GOTE):
                self.assertEqual(
                    evaluate_material_undefended_piece(current, Side.GOTE),
                    -expected_sente,
                )

    def test_validates_frozen_named_weights(self):
        """名前付き重みの境界を検証し設定データを凍結する。

        boolやfloatを整数として受ける誤り、係数の境界違反、既定値の変更を検出する。
        """
        self.assertEqual(
            UndefendedPieceWeights(),
            UndefendedPieceWeights(material=10, undefended=1),
        )
        self.assertEqual(UndefendedPieceWeights(material=1).material, 1)
        self.assertEqual(UndefendedPieceWeights(undefended=0).undefended, 0)

        invalid_weights = (
            ("material_zero", {"material": 0}),
            ("material_negative", {"material": -1}),
            ("material_bool", {"material": True}),
            ("material_float", {"material": 1.5}),
            ("undefended_negative", {"undefended": -1}),
            ("undefended_bool", {"undefended": True}),
            ("undefended_float", {"undefended": 1.5}),
        )
        for name, values in invalid_weights:
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    UndefendedPieceWeights(**values)

        weights = UndefendedPieceWeights()
        with self.assertRaises(FrozenInstanceError):
            weights.material = 20

    def test_custom_weights_and_zero_use_same_path(self):
        """別重みと0重みを適用し、0でもUの計算を呼ぶ。

        係数の直書き、設定の既定値への漏れ、0重みだけUを省略する誤りを検出する。
        """
        current = design_case("A")
        self.assertEqual(
            evaluate_material_undefended_piece(
                current,
                Side.SENTE,
                weights=UndefendedPieceWeights(material=2, undefended=3),
            ),
            25,
        )

        with patch.object(
            material_undefended_piece,
            "attacked_undefended_piece_balance",
            wraps=material_undefended_piece.attacked_undefended_piece_balance,
        ) as balance:
            self.assertEqual(
                evaluate_material_undefended_piece(
                    current,
                    Side.SENTE,
                    weights=UndefendedPieceWeights(material=2, undefended=0),
                ),
                28,
            )
            balance.assert_called_once_with(current, Side.SENTE)

        self.assertEqual(evaluate_material_undefended_piece(current, Side.SENTE), 139)

    def test_hand_turn_and_missing_kings(self):
        """玉なし局面を受け付け、持ち歩はMだけに反映し手番を無視する。

        玉必須化、持ち駒のU混入、手番依存、評価中の局面変更を検出する。
        """
        current = position(
            (PieceType.KNIGHT, Side.SENTE, Square(5, 5)),
            (PieceType.GOLD, Side.SENTE, Square(4, 7)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        )
        before = snapshot(current)
        self.assertEqual(evaluate_material_undefended_piece(current, Side.SENTE), 139)
        self.assertEqual(snapshot(current), before)

        current.sente_hand.add(BasicPieceType.PAWN)
        with_hand = snapshot(current)
        self.assertEqual(evaluate_material_undefended_piece(current, Side.SENTE), 149)
        self.assertEqual(snapshot(current), with_hand)

        current.side_to_move = Side.GOTE
        with_other_turn = snapshot(current)
        self.assertEqual(evaluate_material_undefended_piece(current, Side.SENTE), 149)
        self.assertEqual(snapshot(current), with_other_turn)

    def test_propagates_balance_errors_without_mutation(self):
        """U計算の例外を通常重み・0重みの両方で伝え局面を保つ。

        依存先の故障を隠す誤りと、評価処理による盤面・手番・持ち駒の変更を検出する。
        """
        current = design_case("A")
        for weights in (
            UndefendedPieceWeights(),
            UndefendedPieceWeights(undefended=0),
        ):
            before = snapshot(current)
            with self.subTest(weights=weights):
                with patch.object(
                    material_undefended_piece,
                    "attacked_undefended_piece_balance",
                    side_effect=RuntimeError("対象差の計算失敗"),
                ):
                    with self.assertRaisesRegex(RuntimeError, "対象差の計算失敗"):
                        evaluate_material_undefended_piece(
                            current, Side.SENTE, weights=weights
                        )
                self.assertEqual(snapshot(current), before)


if __name__ == "__main__":
    unittest.main()
