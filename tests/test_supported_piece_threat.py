"""支えのある駒を狙う低価値駒を枚数と先後差で評価する。"""

import unittest
from unittest.mock import patch

from supported_piece_threat_support import (
    both_sides_case,
    both_sides_case_pieces,
    design_case,
    design_case_pieces,
)
from undefended_piece_support import position, rotate_and_swap, snapshot

from kaname_shogi import supported_piece_threat
from kaname_shogi.model import BasicPieceType, PieceType, Side, Square


class SupportedPieceThreatTests(unittest.TestCase):
    def _count(self, current, side):
        """指定側の対象枚数を公開操作へ渡す。"""
        count = getattr(
            supported_piece_threat, "supported_lower_value_threat_count", None
        )
        self.assertTrue(callable(count), "対象枚数を数える操作が必要")
        return count(current, side)

    def _balance(self, current, perspective):
        """視点側から見た対象枚数の差を公開操作へ渡す。"""
        balance = getattr(
            supported_piece_threat, "supported_lower_value_threat_balance", None
        )
        self.assertTrue(callable(balance), "対象枚数の差を返す操作が必要")
        return balance(current, perspective)

    def test_design_case_counts(self):
        """承認済みA・B・Cと先後反転で対象側の枚数を保つ。

        AとBの支え条件、Cの非攻撃、片側固定を独立した手計算値で確認する。
        反転配置の期待値は製品関数の出力から作らない。
        """
        for name, expected_sente in (("A", 1), ("B", 0), ("C", 0)):
            with self.subTest(case=name):
                current = design_case(name)
                self.assertEqual(self._count(current, Side.SENTE), expected_sente)
                self.assertEqual(self._count(current, Side.GOTE), 0)

                mirrored = position(*rotate_and_swap(design_case_pieces(name)))
                self.assertEqual(self._count(mirrored, Side.GOTE), expected_sente)
                self.assertEqual(self._count(mirrored, Side.SENTE), 0)

    def test_design_case_balances(self):
        """A・B・Cの先後差と視点反転を手計算値で確認する。

        自陣から相手陣を引く符号の逆転、片側固定、先後反転での非対称を検出する。
        """
        for name, expected_sente in (("A", -1), ("B", 0), ("C", 0)):
            with self.subTest(case=name):
                current = design_case(name)
                self.assertEqual(self._balance(current, Side.SENTE), expected_sente)
                self.assertEqual(self._balance(current, Side.GOTE), -expected_sente)

                mirrored = position(*rotate_and_swap(design_case_pieces(name)))
                self.assertEqual(self._balance(mirrored, Side.GOTE), expected_sente)
                self.assertEqual(self._balance(mirrored, Side.SENTE), -expected_sente)

    def test_both_sides_count_and_nonzero_balance(self):
        """両側に対象があるD局面の枚数と先後反転を確認する。

        一方だけの走査や先手固定、差の符号逆転を検出する。期待値は配置から手計算し、
        もう一方の局面は駒配置を独立に180度回転・先後交換して作る。
        """
        current = both_sides_case()
        self.assertEqual(self._count(current, Side.SENTE), 2)
        self.assertEqual(self._count(current, Side.GOTE), 1)
        self.assertEqual(self._balance(current, Side.SENTE), -1)
        self.assertEqual(self._balance(current, Side.GOTE), 1)

        mirrored = position(*rotate_and_swap(both_sides_case_pieces()))
        self.assertEqual(self._count(mirrored, Side.SENTE), 1)
        self.assertEqual(self._count(mirrored, Side.GOTE), 2)
        self.assertEqual(self._balance(mirrored, Side.SENTE), 1)
        self.assertEqual(self._balance(mirrored, Side.GOTE), -1)

    def test_strict_value_boundary(self):
        """同価値・低価値・高価値の境界で厳密な大小を使う。

        同価値を含める誤りと高価値を含める逆転を、角13に対する別配置で検出する。
        """
        cases = (
            (PieceType.BISHOP, Square(3, 3), 0),
            (PieceType.SILVER, Square(4, 4), 1),
            (PieceType.ROOK, Square(5, 1), 0),
        )
        for attacker_type, attacker_square, expected in cases:
            with self.subTest(attacker=attacker_type):
                current = position(
                    (PieceType.BISHOP, Side.SENTE, Square(5, 5)),
                    (PieceType.GOLD, Side.SENTE, Square(4, 6)),
                    (attacker_type, Side.GOTE, attacker_square),
                )
                self.assertEqual(self._count(current, Side.SENTE), expected)

    def test_promoted_values_and_motion(self):
        """成駒の現在価値と現在の移動を脅威条件に使う。

        成駒を基本駒価値へ戻す誤りと、馬・竜の追加利きを見落とす誤りを区別する。
        """
        cases = (
            (PieceType.BISHOP, PieceType.PRO_PAWN, Square(4, 4), 1),
            (PieceType.GOLD, PieceType.PRO_PAWN, Square(4, 4), 0),
            (PieceType.HORSE, PieceType.ROOK, Square(5, 1), 0),
            (PieceType.DRAGON, PieceType.HORSE, Square(4, 5), 1),
        )
        for target_type, attacker_type, attacker_square, expected in cases:
            with self.subTest(target=target_type, attacker=attacker_type):
                current = position(
                    (target_type, Side.SENTE, Square(5, 5)),
                    (PieceType.GOLD, Side.SENTE, Square(4, 6)),
                    (attacker_type, Side.GOTE, attacker_square),
                )
                self.assertEqual(self._count(current, Side.SENTE), expected)

    def test_all_nonking_targets(self):
        """全13種類の非玉駒を対象として走査する。

        対象駒種の限定や成駒の走査漏れを検出する。最安の歩は同価値の歩に狙われても
        条件を満たさない。
        """
        expected_by_type = {
            PieceType.PAWN: 0,
            PieceType.LANCE: 1,
            PieceType.KNIGHT: 1,
            PieceType.SILVER: 1,
            PieceType.GOLD: 1,
            PieceType.BISHOP: 1,
            PieceType.ROOK: 1,
            PieceType.PRO_PAWN: 1,
            PieceType.PRO_LANCE: 1,
            PieceType.PRO_KNIGHT: 1,
            PieceType.PRO_SILVER: 1,
            PieceType.HORSE: 1,
            PieceType.DRAGON: 1,
        }
        for target_type, expected in expected_by_type.items():
            with self.subTest(target=target_type):
                current = position(
                    (target_type, Side.SENTE, Square(5, 5)),
                    (PieceType.GOLD, Side.SENTE, Square(4, 6)),
                    (PieceType.PAWN, Side.GOTE, Square(5, 4)),
                )
                self.assertEqual(self._count(current, Side.SENTE), expected)

    def test_all_nonking_attackers(self):
        """全13種類の非玉駒を攻撃元候補として走査する。

        攻撃元の駒種を限定する誤りを検出し、同価値の竜だけを除外する。動き形状の全般は
        既存移動生成テストでも補完する。
        """
        attacker_squares = {
            PieceType.PAWN: Square(5, 4),
            PieceType.LANCE: Square(5, 1),
            PieceType.KNIGHT: Square(4, 3),
            PieceType.SILVER: Square(4, 4),
            PieceType.GOLD: Square(4, 4),
            PieceType.BISHOP: Square(3, 3),
            PieceType.ROOK: Square(5, 2),
            PieceType.PRO_PAWN: Square(4, 4),
            PieceType.PRO_LANCE: Square(4, 4),
            PieceType.PRO_KNIGHT: Square(4, 4),
            PieceType.PRO_SILVER: Square(4, 4),
            PieceType.HORSE: Square(4, 5),
            PieceType.DRAGON: Square(4, 4),
        }
        for attacker_type, attacker_square in attacker_squares.items():
            expected = 0 if attacker_type == PieceType.DRAGON else 1
            with self.subTest(attacker=attacker_type):
                current = position(
                    (PieceType.DRAGON, Side.SENTE, Square(5, 5)),
                    (PieceType.GOLD, Side.SENTE, Square(4, 6)),
                    (attacker_type, Side.GOTE, attacker_square),
                )
                self.assertEqual(self._count(current, Side.SENTE), expected)

    def test_multiple_and_mixed_attackers(self):
        """価値の高い攻撃元の後にある安い攻撃元も見つけ、対象を一度だけ数える。

        盤面走査の先頭の高価値駒で探索を止める誤りと、安い攻撃元ごとの重複加算を検出
        する。独立に回転・先後交換した配置でも対象側の枚数を保つ。
        """
        pieces = (
            (PieceType.BISHOP, Side.SENTE, Square(5, 5)),
            (PieceType.GOLD, Side.SENTE, Square(4, 6)),
            (PieceType.ROOK, Side.GOTE, Square(1, 5)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
            (PieceType.SILVER, Side.GOTE, Square(6, 4)),
        )
        current = position(*pieces)
        self.assertEqual(self._count(current, Side.SENTE), 1)

        mirrored = position(*rotate_and_swap(pieces))
        self.assertEqual(self._count(mirrored, Side.GOTE), 1)

    def test_king_roles(self):
        """玉は対象・低価値攻撃元から除き、味方の支えとして使う。

        玉を価値0の攻撃元として含める誤りと、対象の玉を枚数へ加える誤りを検出する。
        """
        king_supports = position(
            (PieceType.BISHOP, Side.SENTE, Square(5, 5)),
            (PieceType.KING, Side.SENTE, Square(4, 6)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        )
        king_as_attacker = position(
            (PieceType.BISHOP, Side.SENTE, Square(5, 5)),
            (PieceType.KING, Side.SENTE, Square(4, 6)),
            (PieceType.KING, Side.GOTE, Square(5, 4)),
        )
        king_as_target = position(
            (PieceType.KING, Side.SENTE, Square(5, 5)),
            (PieceType.GOLD, Side.SENTE, Square(4, 6)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        )
        self.assertEqual(self._count(king_supports, Side.SENTE), 1)
        self.assertEqual(self._count(king_as_attacker, Side.SENTE), 0)
        self.assertEqual(self._count(king_as_target, Side.SENTE), 0)

    def test_shield_and_pin(self):
        """遮蔽物は利きを止め、ピンされた攻撃・支えは幾何学的に含める。

        長距離駒の遮蔽を無視する誤りと、ピン駒を合法手の利きだけで除外する誤りを検出
        する。
        """
        shielded = position(
            (PieceType.DRAGON, Side.SENTE, Square(5, 5)),
            (PieceType.GOLD, Side.SENTE, Square(4, 6)),
            (PieceType.LANCE, Side.GOTE, Square(5, 1)),
            (PieceType.PAWN, Side.GOTE, Square(5, 3)),
        )
        pawn_attacks = position(
            (PieceType.DRAGON, Side.SENTE, Square(5, 5)),
            (PieceType.GOLD, Side.SENTE, Square(4, 6)),
            (PieceType.LANCE, Side.GOTE, Square(5, 1)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        )
        pinned_attacker = position(
            (PieceType.ROOK, Side.SENTE, Square(5, 9)),
            (PieceType.KING, Side.GOTE, Square(5, 1)),
            (PieceType.SILVER, Side.GOTE, Square(5, 2)),
            (PieceType.BISHOP, Side.SENTE, Square(4, 3)),
            (PieceType.GOLD, Side.SENTE, Square(3, 4)),
        )
        pinned_defender = position(
            (PieceType.KING, Side.SENTE, Square(4, 9)),
            (PieceType.SILVER, Side.SENTE, Square(4, 8)),
            (PieceType.BISHOP, Side.SENTE, Square(5, 7)),
            (PieceType.ROOK, Side.GOTE, Square(4, 1)),
            (PieceType.PAWN, Side.GOTE, Square(5, 6)),
        )
        self.assertEqual(self._count(shielded, Side.SENTE), 0)
        self.assertEqual(self._count(pawn_attacks, Side.SENTE), 1)
        self.assertEqual(self._count(pinned_attacker, Side.SENTE), 1)
        self.assertEqual(self._count(pinned_defender, Side.SENTE), 1)

    def test_empty_hands_turn_and_no_mutation(self):
        """空盤・持ち駒・手番に依存せず、計算中も局面を変更しない。

        盤上駒だけで数える契約と、読み取り評価が盤面・手番・持ち駒を変えないことを
        snapshotで検出する。
        """
        empty = position()
        self.assertEqual(self._count(empty, Side.SENTE), 0)
        self.assertEqual(self._count(empty, Side.GOTE), 0)
        self.assertEqual(self._balance(empty, Side.SENTE), 0)
        self.assertEqual(self._balance(empty, Side.GOTE), 0)

        current = design_case("A")
        current.side_to_move = Side.GOTE
        current.sente_hand.add(BasicPieceType.ROOK)
        current.gote_hand.add(BasicPieceType.BISHOP)
        before = snapshot(current)
        self.assertEqual(self._count(current, Side.SENTE), 1)
        self.assertEqual(self._count(current, Side.GOTE), 0)
        self.assertEqual(self._balance(current, Side.SENTE), -1)
        self.assertEqual(self._balance(current, Side.GOTE), 1)
        self.assertEqual(snapshot(current), before)

    def test_helper_rejects_unknown_design_case(self):
        """固定局面ヘルパーは未知の名前をエラーとして扱う。"""
        with self.assertRaisesRegex(ValueError, "未知の設計局面"):
            design_case("unknown")

    def test_dependency_error_propagates(self):
        """利き照会の例外を脅威集計で隠さず呼び出し元へ伝える。"""
        current = design_case("A")
        with patch.object(
            supported_piece_threat,
            "is_piece_attacking_square",
            side_effect=RuntimeError("利き照会"),
        ):
            with self.assertRaisesRegex(RuntimeError, "利き照会"):
                self._count(current, Side.SENTE)

        with patch.object(
            supported_piece_threat,
            "piece_reference_value",
            side_effect=RuntimeError("参考価値"),
        ):
            with self.assertRaisesRegex(RuntimeError, "参考価値"):
                self._count(current, Side.SENTE)


if __name__ == "__main__":
    unittest.main()
