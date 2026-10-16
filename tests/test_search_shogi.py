"""共通探索と既存の将棋ルールをつなぐ契約を確認する。"""

import unittest
from unittest.mock import patch

from kaname_shogi.model import (
    BasicPieceType,
    Board,
    Piece,
    PieceType,
    Position,
    Side,
    Square,
)
from kaname_shogi.search import alpha_beta, minimax, shogi
from kaname_shogi.sfen import format_sfen, parse_sfen
from kaname_shogi.usi_move import parse_usi_move

KINGS = "8k/9/9/9/9/9/9/9/K8 b - 1"
RECAPTURE = "8k/9/4g4/4p4/4RS3/9/9/9/K8 b - 1"
ESCAPE = "8k/9/4gs3/9/4R4/9/9/9/K8 b - 1"
MATE = "3pkp3/3p1p3/4RG3/9/9/9/9/9/K8 b - 1"


class ShogiSearchTests(unittest.TestCase):
    def test_kings_only_matches_and_counts_depth_two(self):
        """玉だけの局面で評価0と全候補同点、二手の訪問13/9を確認する。

        根計数の欠落と、全幅側で候補を省く誤りを検出する。
        """
        p = parse_sfen(KINGS).position
        ops = shogi.make_operations(Side.SENTE)
        expected = tuple(map(parse_usi_move, ("9i9h", "9i8h", "9i8i")))
        for depth in (2, 3, 4):
            f, a = minimax.search(p, depth, ops), alpha_beta.search(p, depth, ops)
            self.assertEqual((f.score, a.score), ((0, 0), (0, 0)))
            self.assertEqual((f.move, a.move), (expected[0], expected[0]))
            self.assertEqual(f.root_scores, tuple((m, (0, 0)) for m in expected))
            self.assertGreater(a.visited_nodes, 0)
            self.assertLessEqual(a.visited_nodes, f.visited_nodes)
            if depth == 2:
                self.assertEqual((f.visited_nodes, a.visited_nodes), (13, 9))

    def test_gote_perspective_and_material_sign(self):
        """後手視点で符号と最大・最小の役割を反転する。

        先手固定と0点だけの検証のすり抜けを検出する。
        """
        p = parse_sfen(RECAPTURE).position
        sente, gote = (
            shogi.make_operations(Side.SENTE),
            shogi.make_operations(Side.GOTE),
        )
        self.assertEqual((sente.evaluate(p), gote.evaluate(p)), ((0, 13), (0, -13)))
        self.assertTrue(sente.inspect(p).maximizing)
        self.assertFalse(gote.inspect(p).maximizing)
        p2 = gote.advance(p, parse_usi_move("5e5d"))
        self.assertTrue(gote.inspect(p2).maximizing)
        p = parse_sfen(KINGS.replace(" b ", " w ")).position
        for search in (minimax.search, alpha_beta.search):
            r = search(p, 2, gote)
            self.assertEqual((r.score, r.move), ((0, 0), parse_usi_move("1a1b")))

    def test_material_lines_and_source_independence(self):
        """教材の各合法な手を適用して局所評価と元局面不変を確認する。

        手順の取り違えと枝間の可変局面共有を検出する。
        """
        ops = shogi.make_operations(Side.SENTE)
        for sfen, line, scores in (
            (RECAPTURE, ("5e5d", "5c5d", "4e5d"), (15, -15, 3)),
            (ESCAPE, ("9i9h", "5c5d", "5e5f", "5d5e"), (-2, -2, -2, -2)),
            (ESCAPE, ("9i9h", "5c5d", "5e5d", "4c5d"), (-2, -2, 16, -14)),
        ):
            sf = parse_sfen(sfen)
            p = sf.position
            for token, score in zip(line, scores, strict=True):
                move = parse_usi_move(token)
                self.assertIn(move, ops.inspect(p).moves)
                p = ops.advance(p, move)
                self.assertEqual(ops.evaluate(p), (0, score))
            self.assertEqual(format_sfen(sf), sfen)

    def test_rotated_recapture_keeps_starting_side_scores(self):
        """先後を交換し180度回した教材でも開始側の局所値を保つ。

        後手開始でだけ座標や視点を誤る接続を検出する。
        """
        original = parse_sfen(RECAPTURE).position
        board = Board()
        for file in range(1, 10):
            for rank in range(1, 10):
                piece = original.board.piece_at(Square(file, rank))
                if piece:
                    side = Side.GOTE if piece.side == Side.SENTE else Side.SENTE
                    board.set_piece(
                        Square(10 - file, 10 - rank), Piece(piece.piece_type, side)
                    )
        p = Position(board, Side.GOTE)
        ops = shogi.make_operations(Side.GOTE)
        self.assertEqual(ops.evaluate(p), (0, 13))
        for token, score in zip(("5e5f", "5g5f", "6e5f"), (15, -15, 3), strict=True):
            move = parse_usi_move(token)
            self.assertIn(move, ops.inspect(p).moves)
            p = ops.advance(p, move)
            self.assertEqual(ops.evaluate(p), (0, score))

    def test_mate_at_root_and_horizon(self):
        """末端・開始時とも詰みを通常の駒得より優先する。

        詰みを20点へ落とす誤りと勝敗視点反転を検出する。
        """
        p = parse_sfen(MATE).position
        ops = shogi.make_operations(Side.SENTE)
        after = ops.advance(p, parse_usi_move("5c5b"))
        self.assertEqual(ops.inspect(after).terminal_score, (1, 0))
        self.assertEqual(
            shogi.make_operations(Side.GOTE).inspect(after).terminal_score, (-1, 0)
        )
        for search in (minimax.search, alpha_beta.search):
            self.assertEqual(search(p, 1, ops).score, (1, 0))
            self.assertEqual(search(p, 2, ops).score, (1, 0))
            for depth in (2, 3, 4):
                r = search(after, depth, shogi.make_operations(Side.GOTE))
                self.assertEqual((r.score, r.move, r.visited_nodes), ((-1, 0), None, 1))

    def test_no_moves_without_check_and_inspection_reuse(self):
        """手なしで王手でなければ通常点とし、調査の合法手を再利用する。

        合法手二重生成と手なし即負けを検出する。
        """
        ops = shogi.make_operations(Side.SENTE)
        empty = parse_sfen("9/9/9/9/9/9/9/9/9 b - 1").position
        for search in (minimax.search, alpha_beta.search):
            r = search(empty, 2, ops)
            self.assertEqual((r.score, r.move, r.visited_nodes), ((0, 0), None, 1))
        with (
            patch.object(shogi, "legal_moves", wraps=shogi.legal_moves) as generate,
            patch.object(shogi, "is_in_check", wraps=shogi.is_in_check) as check,
        ):
            ops.inspect(parse_sfen(KINGS).position)
            self.assertEqual(generate.call_count, 1)
            check.assert_not_called()
        with (
            patch.object(shogi, "legal_moves", wraps=shogi.legal_moves) as generate,
            patch.object(shogi, "is_in_check", wraps=shogi.is_in_check) as check,
        ):
            self.assertEqual(ops.inspect(empty).terminal_score, (0, 0))
            self.assertEqual(generate.call_count, 1)
            check.assert_called_once()

    def test_promotes_and_drops_without_mutating_source(self):
        """接続操作で成り・打ちを既存規則へ渡し、持駒を分離する。

        打ちを盤上移動と誤る・成りを落とす誤りを検出する。
        """
        ops = shogi.make_operations(Side.SENTE)
        for sfen, token, score in (
            ("8k/9/9/7P1/9/9/9/9/K8 b - 1", "2d2c+", 12),
            ("8k/9/9/9/9/9/9/9/K8 b P 1", "P*5e", 1),
        ):
            sf = parse_sfen(sfen)
            move = parse_usi_move(token)
            self.assertIn(move, ops.inspect(sf.position).moves)
            after = ops.advance(sf.position, move)
            self.assertEqual(ops.evaluate(after), (0, score))
            self.assertEqual(after.side_to_move, Side.GOTE)
            self.assertEqual(format_sfen(sf), sfen)
            if token.endswith("+"):
                self.assertEqual(
                    after.board.piece_at(Square(2, 3)).piece_type, PieceType.PRO_PAWN
                )
            else:
                self.assertEqual(after.sente_hand.count(BasicPieceType.PAWN), 0)
                self.assertEqual(
                    after.board.piece_at(Square(5, 5)),
                    Piece(PieceType.PAWN, Side.SENTE),
                )
