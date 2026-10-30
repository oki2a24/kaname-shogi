"""相手に攻められ味方の支えがない駒の集計を確認する。"""

import unittest
from unittest.mock import patch

from undefended_piece_support import (
    both_nonzero_case,
    design_case,
    position,
    rotate_and_swap,
    snapshot,
)

from kaname_shogi import undefended_piece
from kaname_shogi.model import BasicPieceType, PieceType, Side, Square
from kaname_shogi.movegen import is_square_attacked
from kaname_shogi.undefended_piece import (
    attacked_undefended_piece_balance,
    attacked_undefended_piece_count,
)


class UndefendedPieceTests(unittest.TestCase):
    def test_counts_four_attack_defense_combinations(self):
        """攻撃と支えの四条件から対象枚数と差を計算する。

        攻撃・支えのAND条件、支えの見落とし、攻撃のない駒の誤計上を検出する。
        期待値は承認済みの手書き配置から独立に定める。
        """
        for name, expected_count, expected_balance in (
            ("A", 1, -1),
            ("B", 0, 0),
            ("C", 0, 0),
            ("D", 0, 0),
        ):
            position_for_case = design_case(name)
            with self.subTest(case=name):
                self.assertEqual(
                    attacked_undefended_piece_count(position_for_case, Side.SENTE),
                    expected_count,
                )
                self.assertEqual(
                    attacked_undefended_piece_count(position_for_case, Side.GOTE), 0
                )
                self.assertEqual(
                    attacked_undefended_piece_balance(position_for_case, Side.SENTE),
                    expected_balance,
                )
                self.assertEqual(
                    attacked_undefended_piece_balance(position_for_case, Side.GOTE),
                    -expected_balance,
                )

    def test_counts_multiple_attackers_and_defenders_once(self):
        """複数の攻撃元は一枚として数え、支え一枚でも対象から外す。

        攻撃元ごとの重複加算と、支え一枚を無視して攻撃駒を数える誤りを検出する。
        追加した角と追加の支え駒自身も攻撃対象なら別に数えることを確認する。
        """
        attacked_by_two = position(
            (PieceType.KING, Side.SENTE, Square(9, 9)),
            (PieceType.KNIGHT, Side.SENTE, Square(5, 5)),
            (PieceType.GOLD, Side.SENTE, Square(4, 7)),
            (PieceType.KING, Side.GOTE, Square(1, 1)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
            (PieceType.BISHOP, Side.GOTE, Square(7, 3)),
            (PieceType.ROOK, Side.SENTE, Square(7, 9)),
        )
        defended_by_two = position(
            (PieceType.KING, Side.SENTE, Square(9, 9)),
            (PieceType.KNIGHT, Side.SENTE, Square(5, 5)),
            (PieceType.GOLD, Side.SENTE, Square(4, 6)),
            (PieceType.GOLD, Side.SENTE, Square(6, 6)),
            (PieceType.KING, Side.GOTE, Square(1, 1)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        )
        attacked_support_piece = position(
            (PieceType.KING, Side.SENTE, Square(9, 9)),
            (PieceType.KNIGHT, Side.SENTE, Square(5, 5)),
            (PieceType.GOLD, Side.SENTE, Square(4, 6)),
            (PieceType.GOLD, Side.SENTE, Square(6, 6)),
            (PieceType.KING, Side.GOTE, Square(1, 1)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
            (PieceType.PAWN, Side.GOTE, Square(6, 5)),
        )
        self.assertEqual(
            attacked_undefended_piece_count(attacked_by_two, Side.SENTE), 1
        )
        self.assertEqual(attacked_undefended_piece_count(attacked_by_two, Side.GOTE), 1)
        self.assertEqual(
            attacked_undefended_piece_count(defended_by_two, Side.SENTE), 0
        )
        self.assertEqual(
            attacked_undefended_piece_count(attacked_support_piece, Side.SENTE), 1
        )
        self.assertEqual(
            attacked_undefended_piece_count(attacked_support_piece, Side.GOTE), 1
        )

    def test_handles_both_sides_and_rotated_perspectives(self):
        """両側に対象がある局面と先後反転で差の符号を保つ。

        一方の側だけを走査する誤り、差の符号逆転、先手固定の誤りを検出する。
        期待値は固定局面の手計算値であり、評価関数から生成しない。
        """
        pieces = both_nonzero_case()
        cases = (
            (position(*pieces), 2, 1, -1, 1),
            (position(*rotate_and_swap(pieces)), 1, 2, 1, -1),
        )
        for current, sente_count, gote_count, sente_balance, gote_balance in cases:
            with self.subTest(position=current):
                self.assertEqual(
                    attacked_undefended_piece_count(current, Side.SENTE), sente_count
                )
                self.assertEqual(
                    attacked_undefended_piece_count(current, Side.GOTE), gote_count
                )
                self.assertEqual(
                    attacked_undefended_piece_balance(current, Side.SENTE),
                    sente_balance,
                )
                self.assertEqual(
                    attacked_undefended_piece_balance(current, Side.GOTE), gote_balance
                )

    def test_includes_every_non_king_target_type(self):
        """成駒を含む全13種類の非玉駒を対象にする。

        駒種を一部だけ走査する誤りや、成駒を対象から除外する誤りを検出する。
        駒種名と日本語名を各ケースに表示し、対象の抜けを識別できるようにする。
        """
        japanese_names = {
            PieceType.ROOK: "飛車",
            PieceType.BISHOP: "角行",
            PieceType.GOLD: "金将",
            PieceType.SILVER: "銀将",
            PieceType.KNIGHT: "桂馬",
            PieceType.LANCE: "香車",
            PieceType.PAWN: "歩兵",
            PieceType.PRO_PAWN: "と金",
            PieceType.PRO_LANCE: "成香",
            PieceType.PRO_KNIGHT: "成桂",
            PieceType.PRO_SILVER: "成銀",
            PieceType.HORSE: "馬",
            PieceType.DRAGON: "竜",
        }
        for piece_type, japanese_name in japanese_names.items():
            current = position(
                (piece_type, Side.SENTE, Square(5, 5)),
                (PieceType.PAWN, Side.GOTE, Square(5, 4)),
            )
            with self.subTest(piece=f"{piece_type.name}（{japanese_name}）"):
                self.assertEqual(
                    attacked_undefended_piece_count(current, Side.SENTE), 1
                )

    def test_promoted_support_uses_current_movement(self):
        """と金・馬・竜が成った後の移動で対象を支える。

        成駒を未成駒の動きで扱うと、追加された金移動・馬の直交一歩・竜の斜め一歩を
        支えとして見落とす誤りを検出する。
        """
        cases = (
            (PieceType.PRO_PAWN, Square(4, 6), 0),
            (PieceType.PAWN, Square(4, 6), 1),
            (PieceType.HORSE, Square(4, 5), 0),
            (PieceType.BISHOP, Square(4, 5), 1),
            (PieceType.DRAGON, Square(4, 4), 0),
            (PieceType.ROOK, Square(4, 4), 1),
        )
        for support_type, support_square, expected_count in cases:
            current = position(
                (PieceType.KNIGHT, Side.SENTE, Square(5, 5)),
                (support_type, Side.SENTE, support_square),
                (PieceType.PAWN, Side.GOTE, Square(5, 4)),
            )
            with self.subTest(support=support_type):
                self.assertEqual(
                    attacked_undefended_piece_count(current, Side.SENTE),
                    expected_count,
                )

    def test_excludes_king_as_target_but_uses_king_attacks(self):
        """玉を対象外にしながら攻撃元と支え役には含める。

        玉自身を対象枚数へ含める誤りと、玉の利きを攻撃・支えから外す誤りを検出する。
        """
        attacked_king = position(
            (PieceType.KING, Side.SENTE, Square(5, 5)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        )
        king_attacks_target = position(
            (PieceType.KNIGHT, Side.SENTE, Square(5, 5)),
            (PieceType.KING, Side.GOTE, Square(5, 4)),
        )
        king_supports_target = position(
            (PieceType.KNIGHT, Side.SENTE, Square(5, 5)),
            (PieceType.KING, Side.SENTE, Square(4, 6)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        )
        self.assertEqual(attacked_undefended_piece_count(attacked_king, Side.SENTE), 0)
        self.assertEqual(
            attacked_undefended_piece_count(king_attacks_target, Side.SENTE), 1
        )
        self.assertEqual(
            attacked_undefended_piece_count(king_supports_target, Side.SENTE), 0
        )

    def test_counts_pinned_attacker_and_pinned_defender(self):
        """ピンされた攻撃駒と支え駒も現在の利きとして数える。

        合法手にない利きを除外して攻撃・支えを判定する誤りを検出する。
        """
        pinned_attacker = position(
            (PieceType.KING, Side.SENTE, Square(1, 9)),
            (PieceType.ROOK, Side.SENTE, Square(5, 9)),
            (PieceType.KNIGHT, Side.SENTE, Square(4, 4)),
            (PieceType.KING, Side.GOTE, Square(5, 1)),
            (PieceType.GOLD, Side.GOTE, Square(5, 3)),
        )
        pinned_defender = position(
            (PieceType.KING, Side.SENTE, Square(5, 9)),
            (PieceType.GOLD, Side.SENTE, Square(5, 7)),
            (PieceType.KNIGHT, Side.SENTE, Square(4, 6)),
            (PieceType.KING, Side.GOTE, Square(1, 1)),
            (PieceType.ROOK, Side.GOTE, Square(5, 1)),
            (PieceType.PAWN, Side.GOTE, Square(4, 5)),
        )
        self.assertEqual(
            attacked_undefended_piece_count(pinned_attacker, Side.SENTE), 1
        )
        self.assertEqual(attacked_undefended_piece_count(pinned_attacker, Side.GOTE), 1)
        self.assertEqual(
            attacked_undefended_piece_count(pinned_defender, Side.SENTE), 1
        )
        self.assertEqual(attacked_undefended_piece_count(pinned_defender, Side.GOTE), 0)

    def test_sliding_blocker_preserves_support_boundary(self):
        """長距離の支えは遮蔽駒の手前で止まる。

        飛車の支えを遮蔽物の向こうへ通す誤りや、遮蔽駒自身を誤って攻撃扱いする誤りを
        検出する。
        """
        open_ray = position(
            (PieceType.KNIGHT, Side.SENTE, Square(5, 5)),
            (PieceType.ROOK, Side.SENTE, Square(5, 8)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        )
        blocked_ray = position(
            (PieceType.KNIGHT, Side.SENTE, Square(5, 5)),
            (PieceType.KNIGHT, Side.SENTE, Square(5, 7)),
            (PieceType.ROOK, Side.SENTE, Square(5, 8)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        )
        self.assertEqual(attacked_undefended_piece_count(open_ray, Side.SENTE), 0)
        self.assertEqual(attacked_undefended_piece_count(blocked_ray, Side.SENTE), 1)
        self.assertFalse(is_square_attacked(blocked_ray.board, Square(5, 7), Side.GOTE))

    def test_turn_hands_empty_and_immutability(self):
        """手番と持ち駒を無視し空盤・玉だけでも状態を変えない。

        手番・持ち駒をC/Uへ混ぜる誤り、不要な玉必須検査、呼出し中の盤面変更を検出する。
        """
        for side_to_move in Side:
            current = design_case("A")
            current.side_to_move = side_to_move
            current.sente_hand.add(BasicPieceType.PAWN)
            current.gote_hand.add(BasicPieceType.PAWN)
            before = snapshot(current)
            self.assertEqual(attacked_undefended_piece_count(current, Side.SENTE), 1)
            self.assertEqual(attacked_undefended_piece_count(current, Side.GOTE), 0)
            self.assertEqual(attacked_undefended_piece_balance(current, Side.SENTE), -1)
            self.assertEqual(snapshot(current), before)

        empty = position()
        kings_only = position(
            (PieceType.KING, Side.SENTE, Square(9, 9)),
            (PieceType.KING, Side.GOTE, Square(1, 1)),
        )
        for current in (empty, kings_only):
            self.assertEqual(attacked_undefended_piece_count(current, Side.SENTE), 0)
            self.assertEqual(attacked_undefended_piece_count(current, Side.GOTE), 0)
            self.assertEqual(attacked_undefended_piece_balance(current, Side.SENTE), 0)

    def test_propagates_attack_probe_errors(self):
        """利き照会の例外を伝え、呼出し前の局面を保つ。

        例外を0件へ握りつぶす誤りと、失敗した照会中に局面を変更する誤りを検出する。
        """
        current = design_case("A")
        before = snapshot(current)
        with patch.object(
            undefended_piece,
            "is_square_attacked",
            side_effect=RuntimeError("利き照会失敗"),
        ):
            with self.assertRaisesRegex(RuntimeError, "利き照会失敗"):
                attacked_undefended_piece_count(current, Side.SENTE)
        self.assertEqual(snapshot(current), before)


if __name__ == "__main__":
    unittest.main()
