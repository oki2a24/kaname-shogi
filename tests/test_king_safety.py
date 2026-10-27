"""玉の周辺にある異なる攻撃マス数と安全度差を検証する。"""

import unittest
from unittest.mock import patch

from kaname_shogi import king_safety
from kaname_shogi.model import (
    BasicPieceType,
    Board,
    Piece,
    PieceType,
    Position,
    Side,
    Square,
)

_HAND_TYPES = (
    BasicPieceType.ROOK,  # 飛車
    BasicPieceType.BISHOP,  # 角行
    BasicPieceType.GOLD,  # 金将
    BasicPieceType.SILVER,  # 銀将
    BasicPieceType.KNIGHT,  # 桂馬
    BasicPieceType.LANCE,  # 香車
    BasicPieceType.PAWN,  # 歩兵
)


def _position(*pieces, side_to_move: Side = Side.SENTE) -> Position:
    """固定した駒配置から持ち駒なしの局面を作るテスト用構築操作。"""
    board = Board()
    for piece_type, side, square in pieces:
        board.set_piece(square, Piece(piece_type, side))
    return Position(board, side_to_move)


def _standard_case() -> tuple[tuple[PieceType, Side, Square], ...]:
    """両側の危険数が非零で異なる固定局面を返す。"""
    return (
        (PieceType.KING, Side.SENTE, Square(5, 5)),
        (PieceType.PAWN, Side.SENTE, Square(8, 3)),
        (PieceType.KING, Side.GOTE, Square(9, 1)),
        (PieceType.PAWN, Side.GOTE, Square(5, 3)),
        (PieceType.PAWN, Side.GOTE, Square(4, 3)),
    )


def _rotate_and_swap(
    pieces: tuple[tuple[PieceType, Side, Square], ...],
) -> tuple[tuple[PieceType, Side, Square], ...]:
    """局面を180度回転し、各駒の所有者を入れ替えた配置を返す。"""
    rotated = []
    for piece_type, side, square in pieces:
        owner = Side.GOTE if side == Side.SENTE else Side.SENTE
        rotated.append((piece_type, owner, Square(10 - square.file, 10 - square.rank)))
    return tuple(rotated)


def _position_contents(position: Position):
    """盤面・手番・先後の持ち駒を固定順の値として返す。"""
    board = tuple(
        position.board.piece_at(Square(file, rank))
        for file in range(1, 10)
        for rank in range(1, 10)
    )
    sente_hand = tuple(position.sente_hand.count(piece) for piece in _HAND_TYPES)
    gote_hand = tuple(position.gote_hand.count(piece) for piece in _HAND_TYPES)
    return board, position.side_to_move, sente_hand, gote_hand


class _AlwaysAttacked:
    """全照会を攻撃ありとして記録するテスト用ダブル。"""

    def __init__(self):
        self.calls: list[tuple[Square, Side]] = []

    def __call__(self, _board: Board, target: Square, attacking_side: Side) -> bool:
        self.calls.append((target, attacking_side))
        return True


class KingSafetyTests(unittest.TestCase):
    def test_counts_static_cases_from_design(self):
        """設計の二局面から危険マス数と両視点の差を数える。

        Aの５四を一度数え、Bでは玉周辺外の攻撃を数えないことを確認する。
        """
        king_layout = (
            (PieceType.KING, Side.SENTE, Square(5, 5)),
            (PieceType.KING, Side.GOTE, Square(9, 1)),
        )
        case_b = _position(
            *king_layout,
            (PieceType.PAWN, Side.GOTE, Square(5, 2)),
        )
        self.assertEqual(king_safety.king_danger_count(case_b, Side.SENTE), 0)
        self.assertEqual(king_safety.king_danger_count(case_b, Side.GOTE), 0)
        self.assertEqual(king_safety.king_safety_balance(case_b, Side.SENTE), 0)
        self.assertEqual(king_safety.king_safety_balance(case_b, Side.GOTE), 0)

        case_a = _position(
            *king_layout,
            (PieceType.PAWN, Side.GOTE, Square(5, 3)),
        )
        self.assertEqual(king_safety.king_danger_count(case_a, Side.SENTE), 1)
        self.assertEqual(king_safety.king_danger_count(case_a, Side.GOTE), 0)
        self.assertEqual(king_safety.king_safety_balance(case_a, Side.SENTE), -1)
        self.assertEqual(king_safety.king_safety_balance(case_a, Side.GOTE), 1)

    def test_counts_distinct_attacked_squares(self):
        """同じ周辺マスへの複数の利きを一度だけ数える。

        攻撃駒の延べ数を危険マス数と取り違える実装を検出する。
        """
        position = _position(
            (PieceType.KING, Side.SENTE, Square(5, 5)),
            (PieceType.KING, Side.GOTE, Square(9, 1)),
            (PieceType.PAWN, Side.GOTE, Square(5, 3)),
            (PieceType.PAWN, Side.GOTE, Square(4, 3)),
            (PieceType.KNIGHT, Side.GOTE, Square(6, 2)),
        )
        self.assertEqual(king_safety.king_danger_count(position, Side.SENTE), 2)

    def test_counts_attacked_occupied_neighbor_squares(self):
        """味方・相手の駒が占める危険な隣接マスも数える。

        空マスだけを危険数へ加える誤りを、占有側を入れ替えて検出する。
        """
        for occupant_side in Side:
            position = _position(
                (PieceType.KING, Side.SENTE, Square(5, 5)),
                (PieceType.KING, Side.GOTE, Square(9, 1)),
                (PieceType.PAWN, Side.GOTE, Square(5, 3)),
                (PieceType.PAWN, occupant_side, Square(5, 4)),
            )
            before = _position_contents(position)
            with self.subTest(occupant_side=occupant_side):
                self.assertEqual(king_safety.king_danger_count(position, Side.SENTE), 1)
                self.assertEqual(king_safety.king_danger_count(position, Side.GOTE), 0)
                self.assertEqual(
                    king_safety.king_safety_balance(position, Side.SENTE), -1
                )
                self.assertEqual(
                    king_safety.king_safety_balance(position, Side.GOTE), 1
                )
                self.assertEqual(_position_contents(position), before)

    def test_subtracts_two_nonzero_unequal_dangers(self):
        """両側の危険数が異なる局面で相手差し引きを行う。

        一方の危険数だけを使う誤りと、差の引き算を逆にする誤りを検出する。
        """
        position = _position(*_standard_case())
        self.assertEqual(king_safety.king_danger_count(position, Side.SENTE), 2)
        self.assertEqual(king_safety.king_danger_count(position, Side.GOTE), 1)
        self.assertEqual(king_safety.king_safety_balance(position, Side.SENTE), -1)
        self.assertEqual(king_safety.king_safety_balance(position, Side.GOTE), 1)

    def test_rotates_owners_and_ignores_turn(self):
        """先後を交換した局面で視点符号が反転し、手番では変わらない。

        先後やside_to_moveへ固定した差分計算を検出する。
        """
        pieces = _standard_case()
        sente_to_move = _position(*pieces, side_to_move=Side.SENTE)
        gote_to_move = _position(*pieces, side_to_move=Side.GOTE)
        rotated = _position(
            *_rotate_and_swap(pieces),
            side_to_move=Side.GOTE,
        )

        self.assertEqual(king_safety.king_safety_balance(sente_to_move, Side.SENTE), -1)
        self.assertEqual(king_safety.king_safety_balance(gote_to_move, Side.SENTE), -1)
        self.assertEqual(king_safety.king_safety_balance(rotated, Side.SENTE), 1)
        self.assertEqual(king_safety.king_safety_balance(rotated, Side.GOTE), -1)

    def test_uses_only_on_board_adjacent_squares(self):
        """玉の盤内隣接マスだけを一度ずつ利き照会する。

        玉自身・盤外・距離2のマスを照会へ含める誤りを検出する。
        """
        cases = (
            (
                Square(5, 5),
                {
                    Square(4, 4),
                    Square(5, 4),
                    Square(6, 4),
                    Square(4, 5),
                    Square(6, 5),
                    Square(4, 6),
                    Square(5, 6),
                    Square(6, 6),
                },
            ),
            (
                Square(1, 5),
                {
                    Square(1, 4),
                    Square(2, 4),
                    Square(2, 5),
                    Square(1, 6),
                    Square(2, 6),
                },
            ),
            (
                Square(1, 1),
                {Square(1, 2), Square(2, 1), Square(2, 2)},
            ),
        )
        for king_square, expected_targets in cases:
            position = _position(
                (PieceType.KING, Side.SENTE, king_square),
                (PieceType.KING, Side.GOTE, Square(9, 9)),
            )
            attack_probe = _AlwaysAttacked()

            with patch.object(
                king_safety, "is_square_attacked", side_effect=attack_probe
            ):
                with self.subTest(king_square=king_square):
                    self.assertEqual(
                        king_safety.king_danger_count(position, Side.SENTE),
                        len(expected_targets),
                    )

            self.assertEqual(
                {target for target, _ in attack_probe.calls}, expected_targets
            )
            self.assertEqual(len(attack_probe.calls), len(expected_targets))
            self.assertEqual({side for _, side in attack_probe.calls}, {Side.GOTE})

    def test_excludes_king_square_itself(self):
        """玉自身への桂の利きを周辺危険数に加えない。

        桂が王手する玉のマスを隣接マスと同じに数える誤りを検出する。
        """
        position = _position(
            (PieceType.KING, Side.SENTE, Square(5, 5)),
            (PieceType.KING, Side.GOTE, Square(9, 1)),
            (PieceType.KNIGHT, Side.GOTE, Square(4, 3)),
        )
        self.assertEqual(king_safety.king_danger_count(position, Side.SENTE), 0)

    def test_includes_pinned_piece_attacks(self):
        """自玉を守るため動けない銀の利きを数える。

        合法手にできる利きだけを数えて静的な攻撃マスを落とす誤りを検出する。
        """
        position = _position(
            (PieceType.ROOK, Side.SENTE, Square(5, 9)),
            (PieceType.KING, Side.SENTE, Square(4, 5)),
            (PieceType.KING, Side.GOTE, Square(5, 1)),
            (PieceType.SILVER, Side.GOTE, Square(5, 3)),
        )
        self.assertEqual(king_safety.king_danger_count(position, Side.SENTE), 2)
        self.assertEqual(king_safety.king_danger_count(position, Side.GOTE), 0)
        self.assertEqual(king_safety.king_safety_balance(position, Side.SENTE), -2)

    def test_keeps_current_king_as_a_blocker(self):
        """現在の玉を遮蔽物として残したまま隣接利きを数える。

        玉を取り除いて飛車の背後まで利きとする誤りを検出する。
        """
        position = _position(
            (PieceType.KING, Side.SENTE, Square(5, 5)),
            (PieceType.KING, Side.GOTE, Square(9, 1)),
            (PieceType.ROOK, Side.GOTE, Square(5, 1)),
        )
        self.assertEqual(king_safety.king_danger_count(position, Side.SENTE), 1)

    def test_ignores_potential_hand_attacks(self):
        """持ち飛車・持ち桂馬が作る将来の利きを数えない。

        盤上の現在の利きと、将来の駒打ちによる利きを混同する誤りを検出する。
        """
        position = _position(
            (PieceType.KING, Side.SENTE, Square(5, 5)),
            (PieceType.KING, Side.GOTE, Square(9, 1)),
            (PieceType.PAWN, Side.GOTE, Square(5, 3)),
        )
        before = (
            king_safety.king_danger_count(position, Side.SENTE),
            king_safety.king_danger_count(position, Side.GOTE),
            king_safety.king_safety_balance(position, Side.SENTE),
        )
        position.sente_hand.add(BasicPieceType.ROOK)
        position.gote_hand.add(BasicPieceType.KNIGHT)

        self.assertEqual(before, (1, 0, -1))
        self.assertEqual(
            (
                king_safety.king_danger_count(position, Side.SENTE),
                king_safety.king_danger_count(position, Side.GOTE),
                king_safety.king_safety_balance(position, Side.SENTE),
            ),
            before,
        )

    def test_requires_exactly_one_king_per_side(self):
        """両側に玉が一枚ずつない局面を両公開操作で拒否する。

        玉欠落を安全度0と扱うことと、同側の複数玉を受け入れる誤りを検出する。
        """
        invalid_positions = (
            (),
            ((PieceType.KING, Side.SENTE, Square(5, 5)),),
            ((PieceType.KING, Side.GOTE, Square(9, 1)),),
            (
                (PieceType.KING, Side.SENTE, Square(5, 5)),
                (PieceType.KING, Side.SENTE, Square(4, 5)),
                (PieceType.KING, Side.GOTE, Square(9, 1)),
            ),
            (
                (PieceType.KING, Side.SENTE, Square(5, 5)),
                (PieceType.KING, Side.GOTE, Square(9, 1)),
                (PieceType.KING, Side.GOTE, Square(8, 1)),
            ),
        )
        message = "先手・後手の玉はそれぞれ1枚必要です"
        for pieces in invalid_positions:
            position = _position(*pieces)
            for side in Side:
                with self.subTest(pieces=pieces, operation="count", side=side):
                    with self.assertRaisesRegex(ValueError, message):
                        king_safety.king_danger_count(position, side)
                with self.subTest(pieces=pieces, operation="balance", side=side):
                    with self.assertRaisesRegex(ValueError, message):
                        king_safety.king_safety_balance(position, side)

    def test_preserves_full_position(self):
        """危険数と差の反復照会で局面全体を変更しない。

        盤面・手番・双方の持ち駒の読み取りや複製時の漏れを検出する。
        """
        position = _position(*_standard_case())
        position.sente_hand.add(BasicPieceType.ROOK)
        position.gote_hand.add(BasicPieceType.KNIGHT)
        before = _position_contents(position)

        for _ in range(2):
            for side in Side:
                king_safety.king_danger_count(position, side)
                king_safety.king_safety_balance(position, side)

        self.assertEqual(_position_contents(position), before)


if __name__ == "__main__":
    unittest.main()
