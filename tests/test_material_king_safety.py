"""駒得と玉周辺安全度の不変重み付き合成を確認する。"""

import unittest
from dataclasses import FrozenInstanceError

from kaname_shogi.king_safety import king_safety_balance
from kaname_shogi.material_king_safety import (
    KingSafetyWeights,
    evaluate_material_king_safety,
)
from kaname_shogi.model import (
    BasicPieceType,
    Board,
    Piece,
    PieceType,
    Position,
    Side,
    Square,
)
from kaname_shogi.move import BoardMove, DropMove
from kaname_shogi.movegen import is_checkmate, legal_moves, position_after_move

_HAND_TYPES = (
    BasicPieceType.ROOK,
    BasicPieceType.BISHOP,
    BasicPieceType.GOLD,
    BasicPieceType.SILVER,
    BasicPieceType.KNIGHT,
    BasicPieceType.LANCE,
    BasicPieceType.PAWN,
)


def _position(*pieces, side_to_move: Side = Side.SENTE) -> Position:
    """独立した固定配置から局面を作る。"""
    board = Board()
    for piece_type, side, square in pieces:
        board.set_piece(square, Piece(piece_type, side))
    return Position(board, side_to_move)


def _design_a() -> Position:
    """先手玉５五・後手王９一・後手歩５三の設計Aを作る。"""
    return _position(
        (PieceType.KING, Side.SENTE, Square(5, 5)),
        (PieceType.KING, Side.GOTE, Square(9, 1)),
        (PieceType.PAWN, Side.GOTE, Square(5, 3)),
    )


def _design_b() -> Position:
    """先手玉５五・後手王９一・後手歩５二の設計Bを作る。"""
    return _position(
        (PieceType.KING, Side.SENTE, Square(5, 5)),
        (PieceType.KING, Side.GOTE, Square(9, 1)),
        (PieceType.PAWN, Side.GOTE, Square(5, 2)),
    )


def _position_contents(position: Position):
    """盤面・手番・双方の持ち駒を固定順の値にする。"""
    board = tuple(
        position.board.piece_at(Square(file, rank))
        for file in range(1, 10)
        for rank in range(1, 10)
    )
    sente_hand = tuple(position.sente_hand.count(piece) for piece in _HAND_TYPES)
    gote_hand = tuple(position.gote_hand.count(piece) for piece in _HAND_TYPES)
    return board, position.side_to_move, sente_hand, gote_hand


def _move_case() -> Position:
    """成り・竜取り・歩打ちを比較する共通開始局面を作る。"""
    position = _position(
        (PieceType.KING, Side.SENTE, Square(9, 9)),
        (PieceType.ROOK, Side.SENTE, Square(8, 8)),
        (PieceType.PAWN, Side.SENTE, Square(5, 4)),
        (PieceType.KING, Side.GOTE, Square(1, 1)),
        (PieceType.DRAGON, Side.GOTE, Square(8, 7)),
    )
    position.sente_hand.add(BasicPieceType.PAWN)
    return position


class MaterialKingSafetyTests(unittest.TestCase):
    def test_combines_material_and_safety(self):
        """設計値を指定視点で合成し、局面を読み取りのまま保つ。

        駒得だけへの固定、項目の符号反転、評価中の盤面・手番・持ち駒の変更を検出する。
        """
        a = _design_a()
        b = _design_b()
        concentrated = _position(
            (PieceType.KING, Side.SENTE, Square(5, 5)),
            (PieceType.KING, Side.GOTE, Square(9, 1)),
            (PieceType.PAWN, Side.GOTE, Square(5, 3)),
            (PieceType.PAWN, Side.GOTE, Square(4, 3)),
            (PieceType.KNIGHT, Side.GOTE, Square(6, 2)),
        )
        before = tuple(
            _position_contents(position) for position in (a, b, concentrated)
        )

        cases = (
            ("A_sente", a, Side.SENTE, -11),
            ("A_gote", a, Side.GOTE, 11),
            ("B_sente", b, Side.SENTE, -10),
            ("B_gote", b, Side.GOTE, 10),
            ("concentrated", concentrated, Side.SENTE, -82),
        )
        for name, position, perspective, expected in cases:
            with self.subTest(case=name):
                self.assertEqual(
                    evaluate_material_king_safety(position, perspective), expected
                )
        with self.subTest(case="position_unchanged"):
            self.assertEqual(
                tuple(
                    _position_contents(position) for position in (a, b, concentrated)
                ),
                before,
            )

    def test_accepts_named_weights_without_changing_defaults(self):
        """名前付き係数を使い、一度の設定で既定値を変えない。

        係数の直書き、safety=0の拒否、設定のモジュール既定値への漏れを検出する。
        """
        position = _design_a()

        cases = (
            (
                "named_weights",
                KingSafetyWeights(material=2, safety=3),
                -5,
            ),
            (
                "zero_safety_weight",
                KingSafetyWeights(material=2, safety=0),
                -2,
            ),
        )
        for name, weights, expected in cases:
            with self.subTest(case=name):
                self.assertEqual(
                    evaluate_material_king_safety(
                        position, Side.SENTE, weights=weights
                    ),
                    expected,
                )
        with self.subTest(case="default_unchanged"):
            self.assertEqual(evaluate_material_king_safety(position, Side.SENTE), -11)

    def test_validates_immutable_weights(self):
        """係数の型・範囲を検証し、生成後の変更を拒む。

        0の駒得係数、負の安全度係数、bool・floatを整数として受ける誤りを検出する。
        """
        with self.subTest(case="default_values"):
            self.assertEqual(
                KingSafetyWeights(), KingSafetyWeights(material=10, safety=1)
            )

        invalid_weights = (
            ({"material": 0}, "駒得重みは1以上の整数にしてください"),
            ({"material": -1}, "駒得重みは1以上の整数にしてください"),
            ({"material": True}, "駒得重みは1以上の整数にしてください"),
            ({"material": 1.5}, "駒得重みは1以上の整数にしてください"),
            ({"safety": -1}, "安全度重みは0以上の整数にしてください"),
            ({"safety": True}, "安全度重みは0以上の整数にしてください"),
            ({"safety": 1.5}, "安全度重みは0以上の整数にしてください"),
        )
        for values, message in invalid_weights:
            with (
                self.subTest(values=values),
                self.assertRaisesRegex(ValueError, message),
            ):
                KingSafetyWeights(**values)

        weights = KingSafetyWeights()
        with self.subTest(case="frozen"):
            with self.assertRaises(FrozenInstanceError):
                weights.material = 20

    def test_validates_kings_even_with_zero_safety_weight(self):
        """安全度係数を0にしても両玉の個数前提を検証する。

        駒得だけへ暗黙に切り替わる経路と、玉の欠落・重複を見逃す誤りを検出する。
        """
        missing_both = Position(Board(), Side.SENTE)
        missing_gote = _position((PieceType.KING, Side.SENTE, Square(9, 9)))
        duplicate_sente = _position(
            (PieceType.KING, Side.SENTE, Square(9, 9)),
            (PieceType.KING, Side.SENTE, Square(8, 9)),
            (PieceType.KING, Side.GOTE, Square(1, 1)),
        )
        duplicate_gote = _position(
            (PieceType.KING, Side.SENTE, Square(9, 9)),
            (PieceType.KING, Side.GOTE, Square(1, 1)),
            (PieceType.KING, Side.GOTE, Square(2, 1)),
        )

        for name, position in (
            ("missing_both", missing_both),
            ("missing_gote", missing_gote),
            ("duplicate_sente", duplicate_sente),
            ("duplicate_gote", duplicate_gote),
        ):
            with (
                self.subTest(case=name),
                self.assertRaisesRegex(
                    ValueError, "先手・後手の玉はそれぞれ1枚必要です"
                ),
            ):
                evaluate_material_king_safety(
                    position,
                    Side.SENTE,
                    weights=KingSafetyWeights(safety=0),
                )

    def test_values_promotion_capture_and_drop(self):
        """成り・竜取り・駒打ち後を開始側の視点で採点する。

        適用後手番への視点切替、成駒や取った駒の扱い、枝間の局面共有を検出する。
        """
        position = _move_case()
        before = _position_contents(position)
        branches = (
            (BoardMove(Square(5, 4), Square(5, 3), True), 108),
            (BoardMove(Square(8, 8), Square(8, 7), False), 320),
            (DropMove(BasicPieceType.PAWN, Square(7, 6)), -2),
        )

        for move, expected in branches:
            with self.subTest(move=move):
                self.assertIn(move, legal_moves(position))
                after = position_after_move(position, move)
                self.assertEqual(after.side_to_move, Side.GOTE)
                self.assertFalse(is_checkmate(after))
                self.assertEqual(
                    evaluate_material_king_safety(after, Side.SENTE), expected
                )
                self.assertEqual(_position_contents(position), before)
        with self.subTest(case="initial_position"):
            self.assertEqual(evaluate_material_king_safety(position, Side.SENTE), -2)

    def test_hand_changes_material_but_not_safety(self):
        """持ち駒を加えると駒得だけが変わり、安全度差は保たれる。

        持ち駒を安全度へ混ぜる誤り、手駒の駒得を落とす誤りを検出する。
        """
        base = _design_a()
        with_pawn = base.copy()
        with_pawn.sente_hand.add(BasicPieceType.PAWN)
        with_rook = base.copy()
        with_rook.sente_hand.add(BasicPieceType.ROOK)

        for name, position in (
            ("base", base),
            ("with_pawn", with_pawn),
            ("with_rook", with_rook),
        ):
            with self.subTest(safety_case=name):
                self.assertEqual(king_safety_balance(position, Side.SENTE), -1)

        for name, position, expected in (
            ("base", base, -11),
            ("with_pawn", with_pawn, -1),
            ("with_rook", with_rook, 139),
        ):
            with self.subTest(material_case=name):
                self.assertEqual(
                    evaluate_material_king_safety(position, Side.SENTE), expected
                )


if __name__ == "__main__":
    unittest.main()
