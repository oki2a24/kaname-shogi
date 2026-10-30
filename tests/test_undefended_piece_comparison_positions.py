"""固定した連携評価比較局面の独立C/U期待値を確認する。"""

import unittest
from pathlib import Path

from kaname_shogi.comparison_io import load_positions
from kaname_shogi.model import Side
from kaname_shogi.undefended_piece import (
    attacked_undefended_piece_balance,
    attacked_undefended_piece_count,
)


class UndefendedPieceComparisonPositionTests(unittest.TestCase):
    def test_positions_match_hand_calculated_undefended_counts(self):
        """5局面の合法手順・手番・C値とU値を設計表に照合する。

        局面の取り違え、支えの数え漏れ、先後のU符号逆転、重複開始局面を検出する。
        期待C/U値は評価関数の出力から作らず設計表の個別計算で固定する。
        """
        positions_path = (
            Path(__file__).parents[1]
            / "data/comparison/undefended-piece-positions-v1.json"
        )
        self.assertTrue(positions_path.is_file(), "連携評価比較の5局面JSONが未作成です")
        positions = load_positions(positions_path)

        expected = (
            ("initial", (), Side.SENTE, 0, 0, 0),
            (
                "two-unsupported-pawns",
                ("7g7f", "3c3d", "7f7e", "7c7d"),
                Side.SENTE,
                1,
                1,
                0,
            ),
            (
                "both-pawns-supported",
                (
                    "7g7f",
                    "3c3d",
                    "7f7e",
                    "7c7d",
                    "6i7h",
                    "6a7b",
                    "7h7g",
                    "7b7c",
                    "7g7f",
                ),
                Side.GOTE,
                0,
                0,
                0,
            ),
            (
                "sente-threatened",
                ("7g7f", "3c3d", "7f7e", "7c7d", "2g2f", "6a7b", "2f2e", "7b7c"),
                Side.SENTE,
                1,
                0,
                -1,
            ),
            (
                "gote-threatened",
                ("7g7f", "3c3d", "3g3f", "3d3e", "4i3h", "4c4d", "3h3g", "9c9d"),
                Side.SENTE,
                0,
                1,
                1,
            ),
        )
        self.assertEqual(len(positions), len(expected))
        self.assertEqual(
            tuple(
                (
                    position.position_id,
                    position.setup_moves,
                    position.start_position.side_to_move,
                )
                for position in positions
            ),
            tuple((row[0], row[1], row[2]) for row in expected),
        )
        self.assertEqual(len({position.start_sfen for position in positions}), 5)

        for index, position in enumerate(positions):
            _, _, _, sente_count, gote_count, sente_balance = expected[index]
            with self.subTest(position=position.position_id):
                self.assertEqual(
                    attacked_undefended_piece_count(
                        position.start_position, Side.SENTE
                    ),
                    sente_count,
                )
                self.assertEqual(
                    attacked_undefended_piece_count(position.start_position, Side.GOTE),
                    gote_count,
                )
                self.assertEqual(
                    attacked_undefended_piece_balance(
                        position.start_position, Side.SENTE
                    ),
                    sente_balance,
                )
                self.assertEqual(
                    attacked_undefended_piece_balance(
                        position.start_position, Side.GOTE
                    ),
                    -sente_balance,
                )


if __name__ == "__main__":
    unittest.main()
