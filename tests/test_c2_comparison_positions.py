"""C2専用局面の合法再生と手計算した玉周辺の危険を確認する。"""

import unittest
from pathlib import Path

from kaname_shogi.comparison_io import load_positions
from kaname_shogi.evaluation import material_balance
from kaname_shogi.king_safety import king_danger_count, king_safety_balance
from kaname_shogi.model import Piece, PieceType, Side, Square


class KingSafetyComparisonPositionsTests(unittest.TestCase):
    def test_positions_preserve_independent_king_danger_examples(self):
        """C2局面を合法再生し、玉配置と危険マス数の期待値を保つ。

        序盤は後手角が７七と８八へ利くので先手玉周辺D=2。角交換後は
        両玉周辺D=0。歩打ち後は後手飛車が８七、後手歩が８八へ利きD=2。
        変更した局面を同じ条件として扱う誤りを検出する。
        """
        path = (
            Path(__file__).resolve().parents[1]
            / "data/comparison/c2-king-safety-positions-v1.json"
        )
        try:
            positions = load_positions(path)
        except (OSError, ValueError) as error:
            self.fail(f"C2局面を合法再生できません: {error}")

        expected = (
            ("initial", 0, Side.SENTE, Square(5, 9), Square(5, 1), 0, 0),
            ("bishop-line-danger", 5, Side.GOTE, Square(7, 8), Square(6, 2), 2, 0),
            (
                "bishop-exchange-development",
                20,
                Side.SENTE,
                Square(7, 8),
                Square(7, 2),
                0,
                0,
            ),
            ("pawn-pressure", 30, Side.SENTE, Square(7, 8), Square(7, 2), 2, 0),
        )
        self.assertEqual(len(positions), len(expected))
        for index, row in enumerate(expected):
            position = positions[index]
            name, plies, turn, sente_king, gote_king, sente_danger, gote_danger = row
            with self.subTest(position=name):
                current = position.start_position
                self.assertEqual(position.position_id, name)
                self.assertEqual(len(position.setup_moves), plies)
                self.assertIs(current.side_to_move, turn)
                self.assertEqual(
                    current.board.piece_at(sente_king),
                    Piece(PieceType.KING, Side.SENTE),
                )
                self.assertEqual(
                    current.board.piece_at(gote_king), Piece(PieceType.KING, Side.GOTE)
                )
                self.assertEqual(king_danger_count(current, Side.SENTE), sente_danger)
                self.assertEqual(king_danger_count(current, Side.GOTE), gote_danger)
                self.assertEqual(
                    king_safety_balance(current, Side.SENTE), gote_danger - sente_danger
                )
                self.assertEqual(material_balance(current, Side.SENTE), 0)
