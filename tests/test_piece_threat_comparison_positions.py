"""二段階比較用の局面列と独立したM/U/V期待値を固定する。"""

import unittest
from pathlib import Path

from kaname_shogi.comparison_io import load_positions
from kaname_shogi.evaluation import material_balance
from kaname_shogi.model import BasicPieceType, PieceType, Side, Square
from kaname_shogi.movegen import is_piece_attacking_square, is_square_attacked
from kaname_shogi.supported_piece_threat import (
    supported_lower_value_threat_balance,
    supported_lower_value_threat_count,
)
from kaname_shogi.undefended_piece import (
    attacked_undefended_piece_balance,
    attacked_undefended_piece_count,
)

_ROOT = Path(__file__).resolve().parents[1]
_PILOT_PATH = _ROOT / "data/comparison/supported-piece-threat-pilot-positions-v1.json"
_CONFIRMATION_PATH = (
    _ROOT / "data/comparison/supported-piece-threat-confirmation-positions-v1.json"
)
_PILOT_MOVES = {
    "pilot-sente-bishop-pawn": (
        "7g7f",
        "5c5d",
        "4g4f",
        "3c3d",
        "4i4h",
        "4c4d",
        "4f4e",
        "6c6d",
        "4h4g",
        "8c8d",
        "4g4f",
        "8d8e",
        "8h5e",
    ),
    "pilot-gote-bishop-pawn": ("5g5f", "3c3d", "7g7f", "5c5d", "6g6f", "2b5e"),
    "pilot-sente-knight-pawn": (
        "7g7f",
        "7c7d",
        "7f7e",
        "7d7e",
        "6i6h",
        "7e7f",
        "8i7g",
    ),
    "pilot-undefended-bishop": ("7g7f", "5c5d", "7f7e", "3c3d", "8h5e"),
    "pilot-no-threat": ("7g7f", "3c3d", "2g2f", "8c8d"),
}
_CONFIRMATION_MOVES = {
    "confirmation-opening-side-pawns": (
        "2g2f",
        "8c8d",
        "7g7f",
        "3c3d",
        "6g6f",
        "4c4d",
    ),
    "confirmation-king-side-development": (
        "7g7f",
        "8c8d",
        "6g6f",
        "3c3d",
        "5g5f",
        "4c4d",
        "4g4f",
        "5c5d",
        "4i4h",
        "6c6d",
        "3i3h",
        "3a3b",
        "6i6h",
        "4a4b",
        "8g8f",
    ),
    "confirmation-bishop-exchange": (
        "7g7f",
        "3c3d",
        "8h2b+",
        "3a2b",
        "6g6f",
        "4c4d",
        "4g4f",
        "5c5d",
        "4i4h",
        "6c6d",
    ),
    "confirmation-rook-pawn-push": (
        "2g2f",
        "8c8d",
        "2f2e",
        "8d8e",
        "6g6f",
        "3c3d",
        "6i6h",
        "4c4d",
        "7g7f",
        "3a4b",
        "7f7e",
    ),
    "confirmation-central-development": (
        "5g5f",
        "5c5d",
        "6g6f",
        "4c4d",
        "4g4f",
        "6c6d",
        "4i4h",
        "6a6b",
        "3g3f",
        "3c3d",
        "6i6h",
        "2a3c",
    ),
    "confirmation-pawn-exchange": (
        "5g5f",
        "3c3d",
        "7g7f",
        "8c8d",
        "5f5e",
        "5c5d",
        "6g6f",
        "5d5e",
        "2g2f",
        "6c6d",
        "7i7h",
        "4c4d",
        "6i6h",
    ),
}
# 値は初期駒配置と手順から独立に手計算した。U/Vの符号は「後手側−先手側」。
_PILOT_EXPECTED = {
    "pilot-sente-bishop-pawn": {
        "muv": (0, 1, -1),
        "side_to_move": Side.GOTE,
        "u_counts": (0, 1),
        "v_counts": (1, 0),
        "u_targets": ((Side.GOTE, (6, 4), PieceType.PAWN),),
        "v_targets": (
            (
                Side.SENTE,
                (5, 5),
                PieceType.BISHOP,
                ((Side.GOTE, (5, 4), PieceType.PAWN),),
                ((Side.SENTE, (4, 6), PieceType.GOLD),),
            ),
        ),
    },
    "pilot-gote-bishop-pawn": {
        "muv": (0, 0, 1),
        "side_to_move": Side.SENTE,
        "u_counts": (0, 0),
        "v_counts": (0, 1),
        "u_targets": (),
        "v_targets": (
            (
                Side.GOTE,
                (5, 5),
                PieceType.BISHOP,
                ((Side.SENTE, (5, 6), PieceType.PAWN),),
                ((Side.GOTE, (5, 4), PieceType.PAWN),),
            ),
        ),
    },
    "pilot-sente-knight-pawn": {
        "muv": (-2, 0, -1),
        "side_to_move": Side.GOTE,
        "u_counts": (0, 0),
        "v_counts": (1, 0),
        "u_targets": (),
        "v_targets": (
            (
                Side.SENTE,
                (7, 7),
                PieceType.KNIGHT,
                ((Side.GOTE, (7, 6), PieceType.PAWN),),
                (
                    (Side.SENTE, (6, 8), PieceType.GOLD),
                    (Side.SENTE, (8, 8), PieceType.BISHOP),
                ),
            ),
        ),
    },
    "pilot-undefended-bishop": {
        "muv": (0, -1, 0),
        "side_to_move": Side.GOTE,
        "u_counts": (1, 0),
        "v_counts": (0, 0),
        "u_targets": ((Side.SENTE, (5, 5), PieceType.BISHOP),),
        "v_targets": (),
    },
    "pilot-no-threat": {
        "muv": (0, 0, 0),
        "side_to_move": Side.SENTE,
        "u_counts": (0, 0),
        "v_counts": (0, 0),
        "u_targets": (),
        "v_targets": (),
    },
}
_CONFIRMATION_EXPECTED = {
    "confirmation-opening-side-pawns": (0, 0, 0, Side.SENTE),
    "confirmation-king-side-development": (0, 0, 0, Side.GOTE),
    "confirmation-bishop-exchange": (0, 0, 0, Side.SENTE),
    "confirmation-rook-pawn-push": (0, 0, 0, Side.GOTE),
    "confirmation-central-development": (0, 0, 0, Side.SENTE),
    "confirmation-pawn-exchange": (-2, 0, 0, Side.GOTE),
}


def _state_key(position):
    """手数表記を除いた盤面・持ち駒・手番の状態キーを作る。"""
    board = tuple(
        (piece.side, piece.piece_type)
        if (piece := position.board.piece_at(Square(file, rank))) is not None
        else None
        for file in range(1, 10)
        for rank in range(1, 10)
    )
    hands = tuple(
        tuple(
            hand.count(kind)
            for kind in BasicPieceType
            if kind is not BasicPieceType.KING
        )
        for hand in (position.sente_hand, position.gote_hand)
    )
    return board, hands, position.side_to_move


class PieceThreatComparisonPositionTests(unittest.TestCase):
    def test_pilot_positions_match_hand_calculated_muv(self):
        """予備5局面の手順・手番・材料・U/V枚数と対象駒を固定する。

        V典型3役、Uのみの対照、無脅威対照を独立した配置値で確認し、
        先後差の符号、対象重複計上、対象・攻撃元・支え駒種の取り違えを検出する。
        """
        self.assertTrue(_PILOT_PATH.is_file(), "予備専用のV典型5局面が未作成です")
        positions = load_positions(_PILOT_PATH)
        self.assertEqual(tuple(p.position_id for p in positions), tuple(_PILOT_MOVES))
        self.assertEqual(
            tuple(p.setup_moves for p in positions), tuple(_PILOT_MOVES.values())
        )

        for position in positions:
            expected = _PILOT_EXPECTED[position.position_id]
            current = position.start_position
            with self.subTest(position=position.position_id):
                self.assertIs(current.side_to_move, expected["side_to_move"])
                m, u, v = expected["muv"]
                self.assertEqual(material_balance(current, Side.SENTE), m)
                self.assertEqual(
                    attacked_undefended_piece_balance(current, Side.SENTE), u
                )
                self.assertEqual(
                    supported_lower_value_threat_balance(current, Side.SENTE), v
                )
                self.assertEqual(
                    (
                        attacked_undefended_piece_count(current, Side.SENTE),
                        attacked_undefended_piece_count(current, Side.GOTE),
                    ),
                    expected["u_counts"],
                )
                self.assertEqual(
                    (
                        supported_lower_value_threat_count(current, Side.SENTE),
                        supported_lower_value_threat_count(current, Side.GOTE),
                    ),
                    expected["v_counts"],
                )
                self._assert_targets(current, expected)

    def test_confirmation_positions_are_distinct_and_cover_both_sides(self):
        """幅広い確認6局面を手番3/3で固定し予備・相互の重複を避ける。

        開局、駒組み、角交換、飛車先の歩、中央歩、歩交換の範囲を確認し、
        結果を見て局面を差し替える誤りや手番偏りを検出する。
        """
        self.assertTrue(_PILOT_PATH.is_file(), "予備専用のV典型5局面が未作成です")
        self.assertTrue(
            _CONFIRMATION_PATH.is_file(), "確認用の幅広い新規6局面が未作成です"
        )
        pilot = load_positions(_PILOT_PATH)
        confirmation = load_positions(_CONFIRMATION_PATH)
        self.assertEqual(
            tuple(p.position_id for p in confirmation), tuple(_CONFIRMATION_MOVES)
        )
        self.assertEqual(
            tuple(p.setup_moves for p in confirmation),
            tuple(_CONFIRMATION_MOVES.values()),
        )
        expected_sides = tuple(value[3] for value in _CONFIRMATION_EXPECTED.values())
        self.assertEqual(expected_sides.count(Side.SENTE), 3)
        self.assertEqual(expected_sides.count(Side.GOTE), 3)

        for position in confirmation:
            m, u, v, side = _CONFIRMATION_EXPECTED[position.position_id]
            current = position.start_position
            with self.subTest(position=position.position_id):
                self.assertIs(current.side_to_move, side)
                self.assertEqual(material_balance(current, Side.SENTE), m)
                self.assertEqual(
                    attacked_undefended_piece_balance(current, Side.SENTE), u
                )
                self.assertEqual(
                    supported_lower_value_threat_balance(current, Side.SENTE), v
                )

        pilot_keys = {_state_key(p.start_position) for p in pilot}
        confirmation_keys = [_state_key(p.start_position) for p in confirmation]
        self.assertEqual(len(set(confirmation_keys)), 6)
        self.assertFalse(pilot_keys.intersection(confirmation_keys))

    def _assert_targets(self, position, expected):
        """独立に固定したU対象とV対象の駒・利き・支えを確認する。"""
        board = position.board
        for side, (file, rank), kind in expected["u_targets"]:
            target = Square(file, rank)
            piece = board.piece_at(target)
            self.assertIsNotNone(piece)
            self.assertIs(piece.side, side)
            self.assertIs(piece.piece_type, kind)
            opponent = Side.GOTE if side is Side.SENTE else Side.SENTE
            self.assertTrue(is_square_attacked(board, target, opponent))
            self.assertFalse(is_square_attacked(board, target, side))

        for side, (file, rank), kind, attackers, supporters in expected["v_targets"]:
            target = Square(file, rank)
            piece = board.piece_at(target)
            self.assertIsNotNone(piece)
            self.assertIs(piece.side, side)
            self.assertIs(piece.piece_type, kind)
            for attacker_side, (af, ar), attacker_kind in attackers:
                source = Square(af, ar)
                attacker = board.piece_at(source)
                self.assertIsNotNone(attacker)
                self.assertIs(attacker.side, attacker_side)
                self.assertIs(attacker.piece_type, attacker_kind)
                self.assertTrue(is_piece_attacking_square(board, source, target))
            for supporter_side, (sf, sr), supporter_kind in supporters:
                source = Square(sf, sr)
                supporter = board.piece_at(source)
                self.assertIsNotNone(supporter)
                self.assertIs(supporter.side, supporter_side)
                self.assertIs(supporter.piece_type, supporter_kind)
                self.assertTrue(is_piece_attacking_square(board, source, target))


if __name__ == "__main__":
    unittest.main()
