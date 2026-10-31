"""駒得・U・Vの合成評価を独立した期待値で確認する。"""

import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import patch

from supported_piece_threat_support import both_sides_case, design_case
from undefended_piece_support import snapshot

from kaname_shogi import material_piece_threat
from kaname_shogi.model import Side


class MaterialPieceThreatTests(unittest.TestCase):
    def _evaluate(self, current, perspective, *, weights=None):
        """通常評価の操作を公開入口へ渡す。"""
        evaluate = getattr(
            material_piece_threat, "evaluate_material_piece_threat", None
        )
        self.assertTrue(callable(evaluate), "M/U/V合成評価の操作が必要")
        if weights is None:
            return evaluate(current, perspective)
        return evaluate(current, perspective, weights=weights)

    def test_default_design_scores(self):
        """承認済みA・B・Cの既定合成点と視点反転を確認する。

        Vの符号・Uの重複加算・駒得だけを返す実装・先手固定を検出する。
        """
        for name, expected in (("A", 209), ("B", 209), ("C", 210)):
            with self.subTest(case=name):
                current = design_case(name)
                before = snapshot(current)
                self.assertEqual(self._evaluate(current, Side.SENTE), expected)
                self.assertEqual(self._evaluate(current, Side.GOTE), -expected)
                self.assertEqual(snapshot(current), before)

    def test_zero_v_changes_only_v_term(self):
        """Vの係数だけを0にするとA/B/Cの仮合成点になる。

        重みを無視する誤りやUを二重加算する誤りを、同じ局面の既定点と比較して検出する。
        """
        weights_type = getattr(material_piece_threat, "PieceThreatWeights", None)
        self.assertTrue(callable(weights_type), "名前付き合成重みが必要")
        zero_v = weights_type(supported_threat=0)
        for name, expected in (("A", 210), ("B", 209), ("C", 210)):
            with self.subTest(case=name):
                current = design_case(name)
                self.assertEqual(
                    self._evaluate(current, Side.SENTE, weights=zero_v), expected
                )
                self.assertEqual(
                    self._evaluate(current, Side.GOTE, weights=zero_v), -expected
                )

    def test_all_terms_nonzero_and_custom_weights(self):
        """D局面でM・U・Vをすべて含め、別の名前付き係数も使う。

        項の欠落・重複・係数の取り違えと、先手固定の式を検出する。
        """
        weights_type = getattr(material_piece_threat, "PieceThreatWeights", None)
        self.assertTrue(callable(weights_type), "名前付き合成重みが必要")
        current = both_sides_case()
        before = snapshot(current)
        self.assertEqual(self._evaluate(current, Side.SENTE), 98)
        self.assertEqual(self._evaluate(current, Side.GOTE), -98)
        self.assertEqual(
            self._evaluate(
                current,
                Side.SENTE,
                weights=weights_type(material=3, undefended=2, supported_threat=4),
            ),
            24,
        )
        self.assertEqual(
            self._evaluate(
                current,
                Side.GOTE,
                weights=weights_type(material=3, undefended=2, supported_threat=4),
            ),
            -24,
        )
        self.assertEqual(snapshot(current), before)

    def test_weights_validate_integer_ranges_and_are_frozen(self):
        """名前付き重みは整数境界を守り、生成後に変更できない。

        boolやfloatの受理、負値・駒得0の受理、フィールドの代入を検出する。
        """
        weights_type = getattr(material_piece_threat, "PieceThreatWeights", None)
        self.assertTrue(callable(weights_type), "名前付き合成重みが必要")
        weights = weights_type()
        self.assertEqual(
            weights,
            weights_type(material=10, undefended=1, supported_threat=1),
        )
        self.assertEqual(
            weights_type(material=1, undefended=0, supported_threat=0),
            weights_type(1, 0, 0),
        )

        invalid = (
            ({"material": 0}, "駒得重みは1以上の整数にしてください"),
            ({"material": -1}, "駒得重みは1以上の整数にしてください"),
            ({"material": True}, "駒得重みは1以上の整数にしてください"),
            ({"material": 1.5}, "駒得重みは1以上の整数にしてください"),
            ({"undefended": -1}, "対象差重みは0以上の整数にしてください"),
            ({"undefended": True}, "対象差重みは0以上の整数にしてください"),
            ({"undefended": 1.5}, "対象差重みは0以上の整数にしてください"),
            (
                {"supported_threat": -1},
                "支えあり脅威重みは0以上の整数にしてください",
            ),
            (
                {"supported_threat": True},
                "支えあり脅威重みは0以上の整数にしてください",
            ),
            (
                {"supported_threat": 1.5},
                "支えあり脅威重みは0以上の整数にしてください",
            ),
        )
        for values, message in invalid:
            with self.subTest(values=values):
                with self.assertRaisesRegex(ValueError, message):
                    weights_type(**values)

        with self.assertRaises(FrozenInstanceError):
            weights.material = 20

    def test_dependency_calls_zero_weights_and_errors(self):
        """M・U・Vを各一度呼び、0係数でも例外を伝えて局面を保つ。

        係数0の項を省略する誤り、引数違い、依存先の例外を隠す誤りを検出する。
        """
        weights_type = getattr(material_piece_threat, "PieceThreatWeights", None)
        self.assertTrue(callable(weights_type), "名前付き合成重みが必要")
        current = design_case("A")
        before = snapshot(current)
        with (
            patch.object(
                material_piece_threat, "material_balance", return_value=7
            ) as material,
            patch.object(
                material_piece_threat,
                "attacked_undefended_piece_balance",
                return_value=-3,
            ) as undefended,
            patch.object(
                material_piece_threat,
                "supported_lower_value_threat_balance",
                return_value=2,
            ) as supported,
        ):
            self.assertEqual(
                self._evaluate(
                    current,
                    Side.SENTE,
                    weights=weights_type(material=1, undefended=0, supported_threat=0),
                ),
                7,
            )
        material.assert_called_once_with(current, Side.SENTE)
        undefended.assert_called_once_with(current, Side.SENTE)
        supported.assert_called_once_with(current, Side.SENTE)
        self.assertEqual(snapshot(current), before)

        for dependency, weights in (
            ("material_balance", weights_type()),
            (
                "attacked_undefended_piece_balance",
                weights_type(undefended=0),
            ),
            (
                "supported_lower_value_threat_balance",
                weights_type(supported_threat=0),
            ),
        ):
            with self.subTest(dependency=dependency):
                with patch.object(
                    material_piece_threat,
                    dependency,
                    side_effect=RuntimeError(dependency),
                ):
                    with self.assertRaisesRegex(RuntimeError, dependency):
                        self._evaluate(current, Side.SENTE, weights=weights)
                self.assertEqual(snapshot(current), before)


if __name__ == "__main__":
    unittest.main()
