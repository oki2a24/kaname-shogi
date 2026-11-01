"""支えのない被攻撃駒の価値合計と視点差を検査する。"""

import unittest
from unittest.mock import patch

from undefended_piece_value_support import (
    design_case,
    design_case_pieces,
    position,
    rotate_and_swap,
    snapshot,
)

from kaname_shogi import undefended_piece_value as value_module
from kaname_shogi.model import BasicPieceType, PieceType, Side, Square


class UndefendedPieceValueTests(unittest.TestCase):
    def _value(self, current, side):
        """指定側の価値合計を公開操作へ渡す。"""
        return value_module.attacked_undefended_piece_value(current, side)

    def _balance(self, current, side):
        """指定視点の価値合計差を公開操作へ渡す。"""
        return value_module.attacked_undefended_piece_value_balance(current, side)

    def test_design_values_and_balances(self):
        """対象駒の価値を一度加え、先後視点の差を返す。

        枚数だけを返す誤り、対象価値の符号逆転、手番固定を検出する。
        """
        self.assertEqual(self._value(design_case("A"), Side.SENTE), 15)
        self.assertEqual(self._value(design_case("B"), Side.SENTE), 1)
        self.assertEqual(self._value(design_case("C"), Side.SENTE), 0)
        self.assertEqual(self._balance(design_case("A"), Side.SENTE), -15)
        self.assertEqual(self._balance(design_case("A"), Side.GOTE), 15)

    def test_both_sides_nonzero_and_rotated(self):
        """両側の値を集計し、配置反転後も対応側の差を保つ。

        後手側の集計漏れ、先後固定、価値合計差の符号逆転を検出する。
        """
        current = design_case("E")
        self.assertEqual(self._value(current, Side.SENTE), 15)
        self.assertEqual(self._value(current, Side.GOTE), 8)
        self.assertEqual(self._balance(current, Side.SENTE), -7)
        self.assertEqual(self._balance(current, Side.GOTE), 7)

        rotated = position(*rotate_and_swap(design_case_pieces("E")))
        self.assertEqual(self._value(rotated, Side.GOTE), 15)
        self.assertEqual(self._value(rotated, Side.SENTE), 8)
        self.assertEqual(self._balance(rotated, Side.GOTE), -7)
        self.assertEqual(self._balance(rotated, Side.SENTE), 7)

    def test_sums_multiple_undefended_targets_per_side(self):
        """同じ側の複数対象をすべて合計して差へ反映する。

        最後の対象だけを返す集計、片側の複数対象だけを落とす誤りを検出する。
        """
        pieces = (
            (PieceType.KING, Side.SENTE, Square(9, 9)),
            (PieceType.SILVER, Side.SENTE, Square(3, 7)),
            (PieceType.ROOK, Side.SENTE, Square(5, 5)),
            (PieceType.KING, Side.GOTE, Square(1, 1)),
            (PieceType.PAWN, Side.GOTE, Square(3, 6)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        )
        current = position(*pieces)
        before = snapshot(current)

        self.assertEqual(self._value(current, Side.SENTE), 23)
        self.assertEqual(self._value(current, Side.GOTE), 2)
        self.assertEqual(self._balance(current, Side.SENTE), -21)
        self.assertEqual(snapshot(current), before)

        rotated = position(*rotate_and_swap(pieces), side_to_move=Side.GOTE)
        self.assertEqual(self._value(rotated, Side.GOTE), 23)
        self.assertEqual(self._value(rotated, Side.SENTE), 2)
        self.assertEqual(self._balance(rotated, Side.GOTE), -21)

    def test_each_current_piece_value_and_king_exclusion(self):
        """13種の現在価値を数え、玉を危険度の対象から除く。

        全駒種の価値対応、成駒を未成価値へ戻す誤り、玉の架空価値を検出する。
        """
        expected_values = (
            (PieceType.ROOK, 15),
            (PieceType.BISHOP, 13),
            (PieceType.GOLD, 9),
            (PieceType.SILVER, 8),
            (PieceType.KNIGHT, 6),
            (PieceType.LANCE, 5),
            (PieceType.PAWN, 1),
            (PieceType.PRO_PAWN, 12),
            (PieceType.PRO_LANCE, 10),
            (PieceType.PRO_KNIGHT, 10),
            (PieceType.PRO_SILVER, 9),
            (PieceType.HORSE, 15),
            (PieceType.DRAGON, 17),
        )
        for piece_type, expected in expected_values:
            with self.subTest(piece_type=piece_type):
                current = position(
                    (piece_type, Side.SENTE, Square(4, 5)),
                    (PieceType.KNIGHT, Side.GOTE, Square(5, 3)),
                )
                self.assertEqual(self._value(current, Side.SENTE), expected)
                rotated = position(
                    *rotate_and_swap(
                        (
                            (piece_type, Side.SENTE, Square(4, 5)),
                            (PieceType.KNIGHT, Side.GOTE, Square(5, 3)),
                        )
                    )
                )
                self.assertEqual(self._value(rotated, Side.GOTE), expected)

        king_position = position(
            (PieceType.KING, Side.SENTE, Square(4, 5)),
            (PieceType.KNIGHT, Side.GOTE, Square(5, 3)),
        )
        with patch.object(
            value_module,
            "piece_reference_value",
            wraps=value_module.piece_reference_value,
        ) as reference:
            self.assertEqual(self._value(king_position, Side.SENTE), 0)
        reference.assert_not_called()

    def test_attack_support_and_multiple_attackers(self):
        """攻撃元を一枚追加しても対象価値は一度だけ数える。

        攻撃元ごとの重複加算、支えの見落とし、対象条件の先後固定を検出する。
        """
        pieces = design_case_pieces("A")
        with_second_attacker = position(
            *pieces,
            (PieceType.SILVER, Side.GOTE, Square(4, 4)),
        )
        self.assertEqual(self._value(with_second_attacker, Side.SENTE), 15)

        without_attack = position(
            *(
                (piece_type, side, Square(5, 2) if square == Square(5, 3) else square)
                for piece_type, side, square in pieces
            )
        )
        self.assertEqual(self._value(without_attack, Side.SENTE), 0)

        supported = position(*design_case_pieces("C"))
        self.assertEqual(self._value(supported, Side.SENTE), 0)
        reflected = position(
            *rotate_and_swap(
                (
                    *pieces,
                    (PieceType.SILVER, Side.GOTE, Square(4, 4)),
                )
            )
        )
        self.assertEqual(self._value(reflected, Side.GOTE), 15)

    def test_king_attack_support_shield_and_pin(self):
        """玉は攻撃と支えへ含み、遮蔽・ピンは現在の利きに従う。

        玉役割の除外過剰、遮蔽を通す誤り、ピン駒の利きを除く誤りを検出する。
        """
        king_attacks = position(
            (PieceType.ROOK, Side.SENTE, Square(4, 5)),
            (PieceType.KING, Side.GOTE, Square(4, 4)),
        )
        self.assertEqual(self._value(king_attacks, Side.SENTE), 15)

        king_supports = position(
            (PieceType.ROOK, Side.SENTE, Square(4, 5)),
            (PieceType.KING, Side.SENTE, Square(3, 6)),
            (PieceType.KNIGHT, Side.GOTE, Square(5, 3)),
        )
        self.assertEqual(self._value(king_supports, Side.SENTE), 0)

        open_file = position(
            (PieceType.BISHOP, Side.SENTE, Square(4, 5)),
            (PieceType.ROOK, Side.GOTE, Square(4, 1)),
        )
        blocked_file = position(
            (PieceType.BISHOP, Side.SENTE, Square(4, 5)),
            (PieceType.ROOK, Side.GOTE, Square(4, 1)),
            (PieceType.PAWN, Side.GOTE, Square(4, 3)),
        )
        self.assertEqual(self._value(open_file, Side.SENTE), 13)
        self.assertEqual(self._value(blocked_file, Side.SENTE), 0)

        pinned_attacker = position(
            (PieceType.ROOK, Side.SENTE, Square(4, 5)),
            (PieceType.ROOK, Side.SENTE, Square(5, 9)),
            (PieceType.KNIGHT, Side.GOTE, Square(5, 3)),
            (PieceType.KING, Side.GOTE, Square(5, 1)),
        )
        self.assertEqual(self._value(pinned_attacker, Side.SENTE), 15)

    def test_empty_turn_hands_no_mutation_and_errors(self):
        """空局面は0で、手番・持ち駒は無視し入力と例外を保つ。

        空入力の誤計数、持ち駒の盤上扱い、手番依存、局面変更、例外握りつぶしを検出する。
        """
        empty = position()
        self.assertEqual(self._value(empty, Side.SENTE), 0)
        only_king = position((PieceType.KING, Side.GOTE, Square(5, 5)))
        self.assertEqual(self._value(only_king, Side.GOTE), 0)

        current = design_case("A")
        before = snapshot(current)
        self.assertEqual(self._value(current, Side.SENTE), 15)
        self.assertEqual(snapshot(current), before)
        current.side_to_move = Side.GOTE
        current.sente_hand.add(BasicPieceType.ROOK)
        current.gote_hand.add(BasicPieceType.PAWN)
        before = snapshot(current)
        self.assertEqual(self._value(current, Side.SENTE), 15)
        self.assertEqual(self._value(current, Side.GOTE), 0)
        self.assertEqual(snapshot(current), before)

        with patch.object(
            value_module, "is_square_attacked", side_effect=RuntimeError("利き故障")
        ):
            with self.assertRaisesRegex(RuntimeError, "利き故障"):
                self._value(design_case("A"), Side.SENTE)
        with patch.object(
            value_module, "piece_reference_value", side_effect=RuntimeError("価値故障")
        ):
            with self.assertRaisesRegex(RuntimeError, "価値故障"):
                self._value(design_case("A"), Side.SENTE)
