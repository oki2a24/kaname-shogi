"""駒得と飛車可動性の重み付き合成評価を確認する。"""

import unittest
from dataclasses import FrozenInstanceError

from kaname_shogi.material_rook_mobility import (
    RookMobilityWeights,
    evaluate_material_rook_mobility,
)
from kaname_shogi.model import BasicPieceType, Side, Square
from kaname_shogi.movegen import apply_drop, apply_move
from kaname_shogi.sfen import format_sfen, parse_sfen


class MaterialRookMobilityTests(unittest.TestCase):
    def test_combines_material_and_mobility(self):
        """駒得と可動性を指定側視点で合成する。

        駒得だけへ固定する誤り、項目の符号を反転する誤り、評価中の局面変更を検出する。
        """
        blocked = parse_sfen("8k/9/9/9/4R4/9/4P4/9/K8 b - 1")
        opened = parse_sfen("8k/9/9/9/4R4/9/5P3/9/K8 b - 1")
        before = (format_sfen(blocked), format_sfen(opened))

        self.assertEqual(
            evaluate_material_rook_mobility(
                blocked.position, blocked.position.side_to_move
            ),
            173,
        )
        self.assertEqual(
            evaluate_material_rook_mobility(
                opened.position, blocked.position.side_to_move
            ),
            176,
        )
        self.assertEqual(
            evaluate_material_rook_mobility(blocked.position, Side.GOTE),
            -173,
        )
        self.assertEqual(
            evaluate_material_rook_mobility(opened.position, Side.GOTE),
            -176,
        )
        self.assertEqual((format_sfen(blocked), format_sfen(opened)), before)

    def test_accepts_named_weights(self):
        """名前のある重みを使い、項目を0倍にできる。

        評価式へ係数を直書きする誤りや、一度の重み指定が既定値を変更する誤りを検出する。
        """
        position = parse_sfen("8k/9/9/9/4R4/9/4P4/9/K8 b - 1").position

        self.assertEqual(
            evaluate_material_rook_mobility(
                position,
                position.side_to_move,
                weights=RookMobilityWeights(material=2, mobility=3),
            ),
            71,
        )
        self.assertEqual(
            evaluate_material_rook_mobility(
                position,
                position.side_to_move,
                weights=RookMobilityWeights(material=2, mobility=0),
            ),
            32,
        )
        self.assertEqual(
            evaluate_material_rook_mobility(position, position.side_to_move), 173
        )

    def test_validates_immutable_weights(self):
        """重みの範囲を検証し、生成後の設定変更を拒む。

        負やboolの係数、駒得係数0、可変な既定設定を受け入れる誤りを検出する。
        """
        self.assertEqual(
            RookMobilityWeights(), RookMobilityWeights(material=10, mobility=1)
        )
        invalid_weights = (
            {"material": 0},
            {"material": -1},
            {"material": True},
            {"material": 1.5},
            {"mobility": -1},
            {"mobility": True},
            {"mobility": 1.5},
        )
        for values in invalid_weights:
            with self.subTest(values=values), self.assertRaises(ValueError):
                RookMobilityWeights(**values)

        weights = RookMobilityWeights()
        with self.assertRaises(FrozenInstanceError):
            weights.material = 20

    def test_values_promotion_and_hand_boundary(self):
        """成り・不成・持ち飛の盤上化後に現在の駒種と候補数を評価する。

        竜へ飛車の可動性を付ける誤り、打ち前の持ち駒に可動性を付ける誤りを検出する。
        """
        rook = parse_sfen("8k/9/9/9/4R4/9/9/9/K8 b - 1").position
        dragon = parse_sfen("8k/9/9/9/4+R4/9/9/9/K8 b - 1").position
        hand_rook = parse_sfen("8k/9/9/9/9/9/9/9/K8 b R 1").position
        promotion_position = parse_sfen("8k/9/9/4R4/9/9/9/9/K8 b - 1").position

        self.assertEqual(evaluate_material_rook_mobility(rook, rook.side_to_move), 166)
        self.assertEqual(
            evaluate_material_rook_mobility(dragon, dragon.side_to_move), 170
        )
        self.assertEqual(
            evaluate_material_rook_mobility(hand_rook, hand_rook.side_to_move), 150
        )
        for promote, expected in ((False, 166), (True, 170)):
            with self.subTest(promote=promote):
                after = promotion_position.copy()
                apply_move(after, Square(5, 4), Square(5, 3), promote=promote)
                self.assertEqual(
                    evaluate_material_rook_mobility(
                        after, promotion_position.side_to_move
                    ),
                    expected,
                )

        original_sfen = format_sfen(parse_sfen("8k/9/9/9/9/9/9/9/K8 b R 1"))
        hand_position = parse_sfen("8k/9/9/9/9/9/9/9/K8 b R 1")
        after_drop = hand_position.position.copy()
        apply_drop(after_drop, BasicPieceType.ROOK, Square(5, 5))
        self.assertEqual(
            evaluate_material_rook_mobility(
                hand_position.position, hand_position.position.side_to_move
            ),
            150,
        )
        self.assertEqual(
            evaluate_material_rook_mobility(
                after_drop, hand_position.position.side_to_move
            ),
            166,
        )
        self.assertEqual(format_sfen(hand_position), original_sfen)

    def test_scores_capture_after_demoting_piece(self):
        """取った竜は持ち飛へ変わり、盤上飛車の候補数だけを加える。

        竜の価値を持ち駒に残す誤りや、打ち・取り後に評価対象が更新されない誤りを検出する。
        """
        parsed = parse_sfen("8k/9/9/4+r4/4R4/9/9/9/K8 b - 1")
        after_capture = parsed.position.copy()

        apply_move(after_capture, Square(5, 5), Square(5, 4))

        self.assertEqual(
            evaluate_material_rook_mobility(
                after_capture, parsed.position.side_to_move
            ),
            316,
        )
        self.assertEqual(parsed.position.sente_hand.count(BasicPieceType.ROOK), 0)
        self.assertEqual(after_capture.sente_hand.count(BasicPieceType.ROOK), 1)


if __name__ == "__main__":
    unittest.main()
