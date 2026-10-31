"""共有評価と複製適用の公開契約を確認する。"""

import importlib.util
import unittest

from kaname_shogi import evaluation, movegen
from kaname_shogi.model import BasicPieceType, PieceType, Side, Square
from kaname_shogi.sfen import format_sfen, parse_sfen
from kaname_shogi.usi_move import parse_usi_move


class EvaluationTests(unittest.TestCase):
    def test_piece_reference_values_match_current_table(self):
        """盤上駒の全参考価値を駒得評価と共有する。

        価値表の複製、成駒を基本駒価値へ戻す誤り、飛と角の区別漏れを検出する。
        """
        value = getattr(evaluation, "piece_reference_value", None)
        self.assertTrue(callable(value), "盤上駒の参考価値操作が必要")
        expected = (
            (PieceType.PAWN, 1),
            (PieceType.PRO_PAWN, 12),
            (PieceType.LANCE, 5),
            (PieceType.PRO_LANCE, 10),
            (PieceType.KNIGHT, 6),
            (PieceType.PRO_KNIGHT, 10),
            (PieceType.SILVER, 8),
            (PieceType.PRO_SILVER, 9),
            (PieceType.GOLD, 9),
            (PieceType.BISHOP, 13),
            (PieceType.HORSE, 15),
            (PieceType.ROOK, 15),
            (PieceType.DRAGON, 17),
        )
        for piece_type, points in expected:
            with self.subTest(piece_type=piece_type):
                self.assertEqual(value(piece_type), points)

    def test_king_has_no_piece_reference_value(self):
        """玉には交換価値として使う参考値を設けない。

        玉を最安の0点として危険な攻撃元に扱う実装を検出する。
        """
        value = getattr(evaluation, "piece_reference_value", None)
        self.assertTrue(callable(value), "盤上駒の参考価値操作が必要")
        with self.assertRaisesRegex(ValueError, "玉の参考価値は定義しません"):
            value(PieceType.KING)

    def test_material_balance_keeps_perspective_and_compatibility(self):
        """共有評価は開始側の符号と既存入口の値を保つ。

        別の駒価値表や先手固定の採点を検出する。
        """
        self.assertIsNotNone(importlib.util.find_spec("kaname_shogi.evaluation"))
        from kaname_shogi.evaluation import material_balance

        p = parse_sfen("8k/9/4g4/4p4/4RS3/9/9/9/K8 b - 1").position
        self.assertEqual(material_balance(p, Side.SENTE), 13)
        self.assertEqual(material_balance(p, Side.GOTE), -13)
        self.assertEqual(movegen.material_balance(p, Side.SENTE), 13)

    def test_position_after_move_preserves_source_and_hands(self):
        """公開適用は歩取りを独立した局面へ適用する。

        元局面や別枝の盤面・持駒の共有、例外の隠蔽を検出する。
        """
        advance = getattr(movegen, "position_after_move", None)
        self.assertTrue(callable(advance), "複製適用の公開操作が必要")
        sf = parse_sfen("8k/9/4g4/4p4/4RS3/9/9/9/K8 b - 1")
        before = format_sfen(sf)
        a = advance(sf.position, parse_usi_move("5e5d"))
        b = advance(sf.position, parse_usi_move("5e5f"))
        self.assertEqual(movegen.material_balance(a, Side.SENTE), 15)
        self.assertEqual(a.sente_hand.count(BasicPieceType.PAWN), 1)
        a.board.set_piece(Square(5, 4), None)
        a.sente_hand.add_many(BasicPieceType.PAWN, 1)
        self.assertEqual(b.sente_hand.count(BasicPieceType.PAWN), 0)
        self.assertEqual(format_sfen(sf), before)
        with self.assertRaises(TypeError):
            advance(sf.position, object())
        with self.assertRaises(ValueError):
            advance(sf.position, parse_usi_move("9i1a"))
