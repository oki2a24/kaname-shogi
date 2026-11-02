"""被攻撃駒の価値比較に使う独立した7開始局面を検査する。"""

import json
import unittest
from pathlib import Path

from undefended_piece_value_comparison_support import (
    POSITION_EXPECTATIONS,
    POSITION_SET_ID,
)

from kaname_shogi.comparison_io import load_positions
from kaname_shogi.evaluation import material_balance, piece_reference_value
from kaname_shogi.material_piece_threat import (
    PieceThreatWeights,
    evaluate_material_piece_threat,
)
from kaname_shogi.material_piece_threat_value import (
    PieceThreatValueWeights,
    evaluate_material_piece_threat_value,
)
from kaname_shogi.model import Side, Square
from kaname_shogi.movegen import (
    is_piece_attacking_square,
    is_square_attacked,
    legal_moves,
)
from kaname_shogi.supported_piece_threat import (
    supported_lower_value_threat_balance,
    supported_lower_value_threat_count,
)
from kaname_shogi.undefended_piece import (
    attacked_undefended_piece_balance,
    attacked_undefended_piece_count,
)
from kaname_shogi.undefended_piece_value import (
    attacked_undefended_piece_value,
    attacked_undefended_piece_value_balance,
)

_ROOT = Path(__file__).resolve().parents[1]
_POSITIONS_PATH = _ROOT / "data/comparison/undefended-piece-value-positions-v1.json"
_HISTORICAL_POSITION_PATHS = (
    _ROOT / "data/comparison/undefended-piece-positions-v1.json",
    _ROOT / "data/comparison/supported-piece-threat-pilot-positions-v1.json",
    _ROOT / "data/comparison/supported-piece-threat-confirmation-positions-v1.json",
    _ROOT / "data/comparison/c2-king-safety-positions-v1.json",
)


class UndefendedPieceValueComparisonPositionTests(unittest.TestCase):
    def test_positions_match_hand_calculated_components(self):
        """新規7局面の合法手順・対象駒・M/U/価値/Vを手計算値へ固定する。

        同じ盤面の重複、手順・手番の取り違え、駒種価値や差の符号の誤り、U対象と
        V対象の混同を検出する。期待値は製品評価の出力から生成しない。
        """
        self.assertTrue(
            _POSITIONS_PATH.is_file(), "被攻撃駒価値比較の新規7局面JSONが未作成です"
        )
        positions = load_positions(_POSITIONS_PATH)
        payload = json.loads(_POSITIONS_PATH.read_bytes())
        self.assertEqual(len(positions), 7)
        self.assertEqual(payload["id"], POSITION_SET_ID)
        self.assertEqual(
            tuple(position.position_id for position in positions),
            tuple(POSITION_EXPECTATIONS),
        )
        self.assertEqual(
            tuple(position.setup_moves for position in positions),
            tuple(
                expected["setup_moves"] for expected in POSITION_EXPECTATIONS.values()
            ),
        )
        sfen_values = tuple(position.start_sfen for position in positions)
        self.assertEqual(len(set(sfen_values)), len(sfen_values))

        for position in positions:
            expected = POSITION_EXPECTATIONS[position.position_id]
            current = position.start_position
            with self.subTest(position=position.position_id):
                self.assertIs(current.side_to_move, expected["side_to_move"])
                self.assertTrue(legal_moves(current), "開始局面は終局してはいけません")
                self.assertEqual(
                    material_balance(current, Side.SENTE), expected["material"]
                )
                self.assertEqual(
                    attacked_undefended_piece_balance(current, Side.SENTE),
                    expected["u_balance"],
                )
                self.assertEqual(
                    (
                        attacked_undefended_piece_count(current, Side.SENTE),
                        attacked_undefended_piece_count(current, Side.GOTE),
                    ),
                    expected["u_counts"],
                )
                self.assertEqual(
                    attacked_undefended_piece_value_balance(current, Side.SENTE),
                    expected["value_balance"],
                )
                self.assertEqual(
                    (
                        attacked_undefended_piece_value(current, Side.SENTE),
                        attacked_undefended_piece_value(current, Side.GOTE),
                    ),
                    expected["value_sums"],
                )
                self.assertEqual(
                    supported_lower_value_threat_balance(current, Side.SENTE),
                    expected["v_balance"],
                )
                self.assertEqual(
                    (
                        supported_lower_value_threat_count(current, Side.SENTE),
                        supported_lower_value_threat_count(current, Side.GOTE),
                    ),
                    expected["v_counts"],
                )
                self.assertEqual(
                    evaluate_material_piece_threat(
                        current,
                        Side.SENTE,
                        weights=PieceThreatWeights(
                            material=10, undefended=1, supported_threat=1
                        ),
                    ),
                    expected["old_score"],
                )
                self.assertEqual(
                    evaluate_material_piece_threat_value(
                        current,
                        Side.SENTE,
                        weights=PieceThreatValueWeights(
                            material=10,
                            undefended_value=1,
                            supported_threat=1,
                        ),
                    ),
                    expected["new_score"],
                )
                self.assertEqual(
                    evaluate_material_piece_threat(current, Side.GOTE),
                    -expected["old_score"],
                )
                self.assertEqual(
                    evaluate_material_piece_threat_value(current, Side.GOTE),
                    -expected["new_score"],
                )
                self._assert_targets(current, expected)

        reversal = POSITION_EXPECTATIONS["value-rank-reversal"]
        self.assertLess(reversal["u_balance"] * reversal["value_balance"], 0)

    def test_positions_do_not_reuse_historical_comparison_starts(self):
        """新規比較開始局面が過去のU/V/C2比較開始局面と重複しない。

        旧U初期局面を無対象対照として再利用すると独立した標本という前提が崩れる。
        """
        historical_starts = {
            position.start_sfen: f"{path.name}:{position.position_id}"
            for path in _HISTORICAL_POSITION_PATHS
            for position in load_positions(path)
        }
        overlaps = [
            (position.position_id, historical_starts[position.start_sfen])
            for position in load_positions(_POSITIONS_PATH)
            if position.start_sfen in historical_starts
        ]
        self.assertEqual(overlaps, [], "過去の比較開始局面を再利用しています")

    def _assert_targets(self, position, expected):
        """手計算で固定したU対象・V対象とその支え・低価値攻撃元を照合する。"""
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

        for side, (file, rank), kind, supporters, attackers in expected["v_targets"]:
            target = Square(file, rank)
            piece = board.piece_at(target)
            self.assertIsNotNone(piece)
            self.assertIs(piece.side, side)
            self.assertIs(piece.piece_type, kind)
            target_value = piece_reference_value(kind)
            self._assert_attack_sources(board, target, side, supporters)
            opponent = Side.GOTE if side is Side.SENTE else Side.SENTE
            self._assert_attack_sources(board, target, opponent, attackers)
            for _, _, attacker_kind in attackers:
                self.assertLess(piece_reference_value(attacker_kind), target_value)

    def _assert_attack_sources(self, board, target, side, sources):
        """指定側の全ての期待攻撃元が対象マスへ利いていることを確認する。"""
        for source_side, (file, rank), kind in sources:
            self.assertIs(source_side, side)
            source = Square(file, rank)
            piece = board.piece_at(source)
            self.assertIsNotNone(piece)
            self.assertIs(piece.side, side)
            self.assertIs(piece.piece_type, kind)
            self.assertTrue(is_piece_attacking_square(board, source, target))
