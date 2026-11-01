"""駒得・価値合計差・支えあり低価値脅威の合成を検査する。"""

import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import patch

from undefended_piece_value_support import (
    design_case,
    design_case_pieces,
    position,
    rotate_and_swap,
    snapshot,
)

from kaname_shogi import material_piece_threat, material_piece_threat_value
from kaname_shogi.model import Side


class MaterialPieceThreatValueTests(unittest.TestCase):
    def _evaluate_new(self, current, side, *, weights=None):
        """今回の通常評価操作を公開入口へ渡す。"""
        evaluate = getattr(
            material_piece_threat_value, "evaluate_material_piece_threat_value", None
        )
        self.assertTrue(callable(evaluate), "価値合計差を使う合成評価が必要")
        if weights is None:
            return evaluate(current, side)
        return evaluate(current, side, weights=weights)

    def test_default_design_scores_and_old_policy_unchanged(self):
        """従来Uの枚数差と今回の価値合計差が別の値になる。

        既存方式の変更、旧Uの二重加算、Vの欠落、先手固定を検出する。
        """
        expected_old = {"A": 99, "B": 99, "C": 179, "D": 308, "E": 20}
        expected_new = {"A": 85, "B": 99, "C": 179, "D": 294, "E": 13}
        for name in expected_old:
            with self.subTest(case=name):
                current = design_case(name)
                self.assertEqual(
                    material_piece_threat.evaluate_material_piece_threat(
                        current, Side.SENTE
                    ),
                    expected_old[name],
                )
                self.assertEqual(
                    self._evaluate_new(current, Side.SENTE), expected_new[name]
                )
                self.assertEqual(
                    self._evaluate_new(current, Side.GOTE), -expected_new[name]
                )

                rotated = position(*rotate_and_swap(design_case_pieces(name)))
                self.assertEqual(
                    self._evaluate_new(rotated, Side.GOTE), expected_new[name]
                )

    def test_custom_and_zero_weights(self):
        """名前付き係数を独立に適用し、各項の差を保つ。

        項の位置取り違え、重み無視、既存Uを再加算する誤りを検出する。
        """
        weights_type = getattr(
            material_piece_threat_value, "PieceThreatValueWeights", None
        )
        self.assertTrue(callable(weights_type), "名前付き合成重みが必要")
        current = design_case("D")
        self.assertEqual(self._evaluate_new(current, Side.SENTE), 294)
        self.assertEqual(self._evaluate_new(current, Side.GOTE), -294)
        self.assertEqual(
            self._evaluate_new(
                current,
                Side.SENTE,
                weights=weights_type(
                    material=3, undefended_value=2, supported_threat=4
                ),
            ),
            59,
        )
        self.assertEqual(
            self._evaluate_new(
                current, Side.SENTE, weights=weights_type(undefended_value=0)
            ),
            309,
        )
        self.assertEqual(
            self._evaluate_new(
                current, Side.SENTE, weights=weights_type(supported_threat=0)
            ),
            295,
        )

    def test_weights_strict_ranges_and_frozen(self):
        """合成重みを許容整数範囲へ制限し、作成後の変更を拒む。

        負値・bool・floatの受理と設定データの事後変更を検出する。
        """
        weights_type = getattr(
            material_piece_threat_value, "PieceThreatValueWeights", None
        )
        self.assertTrue(callable(weights_type), "名前付き合成重みが必要")
        self.assertEqual(weights_type(), weights_type(10, 1, 1))
        self.assertEqual(
            weights_type(1, 0, 0),
            weights_type(material=1, undefended_value=0, supported_threat=0),
        )

        invalid = (
            ({"material": 0}, "駒得重みは1以上の整数にしてください"),
            ({"material": -1}, "駒得重みは1以上の整数にしてください"),
            ({"material": True}, "駒得重みは1以上の整数にしてください"),
            ({"material": False}, "駒得重みは1以上の整数にしてください"),
            ({"material": 1.0}, "駒得重みは1以上の整数にしてください"),
            ({"undefended_value": -1}, "対象価値差重みは0以上の整数にしてください"),
            ({"undefended_value": True}, "対象価値差重みは0以上の整数にしてください"),
            ({"undefended_value": False}, "対象価値差重みは0以上の整数にしてください"),
            ({"undefended_value": 1.0}, "対象価値差重みは0以上の整数にしてください"),
            ({"supported_threat": -1}, "支えあり脅威重みは0以上の整数にしてください"),
            ({"supported_threat": True}, "支えあり脅威重みは0以上の整数にしてください"),
            (
                {"supported_threat": False},
                "支えあり脅威重みは0以上の整数にしてください",
            ),
            ({"supported_threat": 1.0}, "支えあり脅威重みは0以上の整数にしてください"),
        )
        for values, message in invalid:
            with self.subTest(values=values):
                with self.assertRaisesRegex(ValueError, message):
                    weights_type(**values)

        weights = weights_type()
        with self.assertRaises(FrozenInstanceError):
            weights.material = 20

    def test_calls_dependencies_once_even_at_zero_and_propagates(self):
        """三評価を一度ずつ使い、0係数の例外も伝えて局面を保つ。

        項の重複・脱落、0係数時の計算省略、例外握りつぶしを検出する。
        """
        weights_type = getattr(
            material_piece_threat_value, "PieceThreatValueWeights", None
        )
        self.assertTrue(callable(weights_type), "名前付き合成重みが必要")
        current = design_case("D")
        before = snapshot(current)
        with (
            patch.object(
                material_piece_threat_value, "material_balance", return_value=7
            ) as material,
            patch.object(
                material_piece_threat_value,
                "attacked_undefended_piece_value_balance",
                return_value=-3,
            ) as undefended,
            patch.object(
                material_piece_threat_value,
                "supported_lower_value_threat_balance",
                return_value=-2,
            ) as supported,
            patch.object(
                material_piece_threat,
                "attacked_undefended_piece_balance",
                side_effect=AssertionError("旧Uを加算してはいけない"),
            ) as old_undefended,
        ):
            self.assertEqual(
                self._evaluate_new(
                    current,
                    Side.SENTE,
                    weights=weights_type(
                        material=3, undefended_value=2, supported_threat=4
                    ),
                ),
                7,
            )
            self.assertEqual(
                self._evaluate_new(
                    current,
                    Side.SENTE,
                    weights=weights_type(
                        material=1, undefended_value=0, supported_threat=0
                    ),
                ),
                7,
            )
        self.assertEqual(material.call_count, 2)
        self.assertEqual(undefended.call_count, 2)
        self.assertEqual(supported.call_count, 2)
        old_undefended.assert_not_called()
        self.assertEqual(snapshot(current), before)

        for dependency in (
            "material_balance",
            "attacked_undefended_piece_value_balance",
            "supported_lower_value_threat_balance",
        ):
            with self.subTest(dependency=dependency):
                current = design_case("A")
                before = snapshot(current)
                with patch.object(
                    material_piece_threat_value,
                    dependency,
                    side_effect=RuntimeError("評価依存故障"),
                ) as failing:
                    with self.assertRaisesRegex(RuntimeError, "評価依存故障"):
                        self._evaluate_new(
                            current,
                            Side.GOTE,
                            weights=weights_type(
                                material=1,
                                undefended_value=0,
                                supported_threat=0,
                            ),
                        )
                failing.assert_called_once_with(current, Side.GOTE)
                self.assertEqual(snapshot(current), before)
