"""将棋用の制御付き操作契約と非破壊性を確認する。"""

import unittest
from contextlib import contextmanager
from unittest.mock import patch

from test_search_movegen import snapshot, uchi
from test_search_shogi import KINGS, MATE, RECAPTURE

from kaname_shogi import movegen as mg
from kaname_shogi.model import Side, Square
from kaname_shogi.search import shogi
from kaname_shogi.search.contracts import AdvancedNode, NodeInspection, PreparedRoot
from kaname_shogi.search.result import SearchInterrupted
from kaname_shogi.search_control import SearchControl, SearchSignal
from kaname_shogi.sfen import parse_sfen
from kaname_shogi.time_management import SearchBudget
from kaname_shogi.usi_move import parse_usi_move


@contextmanager
def pawn_defense_stop(side, dest, control, suppress):
    """根を対象歩打ちへ絞り、実際の防御調査で停止する教材境界。"""
    apply, drop, defense = (
        mg.apply_move,
        mg._apply_drop_controlled,
        mg._has_legal_move_controlled,
    )

    def root_move(*args, **kwargs):
        if args[0].side_to_move == side:
            raise ValueError("教材では根の盤上手を除く")
        return apply(*args, **kwargs)

    def root_drop(*args, **kwargs):
        if args[0].side_to_move == side and args[2] != dest:
            raise ValueError("教材では対象の歩打ちだけ")
        return drop(*args, **kwargs)

    def stop_inside(*args, **kwargs):
        control.request_stop(suppress_response=suppress)
        return defense(*args, **kwargs)

    with (
        patch.object(mg, "apply_move", side_effect=root_move),
        patch.object(mg, "_apply_drop_controlled", side_effect=root_drop),
        patch.object(mg, "_has_legal_move_controlled", side_effect=stop_inside),
    ):
        yield


class ControlledShogiTests(unittest.TestCase):
    def test_prepare_protects_only_first_legal_acquisition(self):
        """準備は通常停止を保護し、後続調査は保護しない。

        0予算を手なしへ変換する誤りと保護の再開を検出する。
        """
        p = parse_sfen(KINGS).position
        ops = shogi.make_controlled_operations(Side.SENTE)
        for budget in (None, SearchBudget(0, 0)):
            c = SearchControl(budget, 0, now_ns=lambda: 0)
            c.request_stop()
            self.assertEqual(ops.prepare(p, c), PreparedRoot(parse_usi_move("9i9h")))
            self.assertEqual(ops.inspect(p, c), SearchInterrupted(SearchSignal.STOP))
        c = SearchControl(None, 0)
        empty = parse_sfen("9/9/9/9/9/9/9/9/9 b - 1").position
        self.assertEqual(ops.prepare(empty, c), PreparedRoot(None))
        c.request_stop(suppress_response=True)
        self.assertEqual(ops.prepare(p, c), SearchInterrupted(SearchSignal.SUPPRESS))

    def test_incomplete_generation_and_application_keep_reason(self):
        """未完了一覧や適用は空・成功へ変換せず、中断理由を保持する。

        再確認CONTINUEでの中断消失と、後からの抑制喪失を検出する。
        """
        p = parse_sfen(KINGS).position
        move = parse_usi_move("9i9h")
        ops = shogi.make_controlled_operations(Side.SENTE)
        for suppress in (False, True):
            c = SearchControl(None, 0)
            if suppress:
                c.request_stop(suppress_response=True)
            want = SearchInterrupted(
                SearchSignal.SUPPRESS if suppress else SearchSignal.STOP
            )
            for moves in ((), (move,)):
                with patch.object(
                    shogi,
                    "legal_moves_controlled",
                    return_value=mg.LegalMovesResult(False, moves),
                ):
                    self.assertEqual(ops.inspect(p, c), want)
            with patch.object(
                shogi,
                "position_after_move_controlled",
                return_value=mg.MoveApplicationResult(False, None),
            ):
                self.assertEqual(ops.advance(p, move, c), want)

    def test_controlled_shogi_preserves_scores_and_positions(self):
        """開始側視点・成り・打ち・詰みを既存規則へつなぎ独立局面を作る。

        視点固定ミス、持駒共有、原局面の変更を検出する。
        """
        for side in Side:
            p = parse_sfen(
                KINGS.replace(" b ", " w ") if side == Side.GOTE else KINGS
            ).position
            ops = shogi.make_controlled_operations(side)
            self.assertEqual(ops.evaluate(p), (0, 0))
            self.assertTrue(ops.inspect(p, SearchControl(None, 0)).maximizing)
        p = parse_sfen(RECAPTURE).position
        self.assertEqual(
            shogi.make_controlled_operations(Side.SENTE).evaluate(p), (0, 13)
        )
        self.assertEqual(
            shogi.make_controlled_operations(Side.GOTE).evaluate(p), (0, -13)
        )
        for sfen, line, scores in (
            (RECAPTURE, ("5e5d", "5c5d", "4e5d"), (15, -15, 3)),
            ("8k/9/9/7P1/9/9/9/9/K8 b - 1", ("2d2c+",), (12,)),
            ("8k/9/9/9/9/9/9/9/K8 b P 1", ("P*5e",), (1,)),
        ):
            p = parse_sfen(sfen).position
            before = snapshot(p)
            ops = shogi.make_controlled_operations(Side.SENTE)
            current = p
            for token, score in zip(line, scores, strict=True):
                move = parse_usi_move(token)
                inspection = ops.inspect(current, SearchControl(None, 0))
                self.assertIsInstance(inspection, NodeInspection)
                self.assertIn(move, inspection.moves)
                advanced = ops.advance(current, move, SearchControl(None, 0))
                self.assertIsInstance(advanced, AdvancedNode)
                self.assertIsNot(advanced.node, current)
                current = advanced.node
                self.assertEqual(ops.evaluate(current), (0, score))
            self.assertEqual(snapshot(p), before)
            move = parse_usi_move(line[0])
            one = ops.advance(p, move, SearchControl(None, 0)).node
            two = ops.advance(p, move, SearchControl(None, 0)).node
            two_before = snapshot(two)
            one.board.set_piece(Square(9, 9), None)
            one.sente_hand.add(mg.BasicPieceType.PAWN)
            one.gote_hand.add(mg.BasicPieceType.PAWN)
            self.assertEqual(snapshot(two), two_before)
            self.assertEqual(snapshot(p), before)
        ops = shogi.make_controlled_operations(Side.SENTE)
        after = ops.advance(
            parse_sfen(MATE).position, parse_usi_move("5c5b"), SearchControl(None, 0)
        ).node
        for side, score in ((Side.SENTE, (1, 0)), (Side.GOTE, (-1, 0))):
            self.assertEqual(
                shogi.make_controlled_operations(side)
                .inspect(after, SearchControl(None, 0))
                .terminal_score,
                score,
            )

    def test_public_pawn_defense_interruption_reaches_adapter(self):
        """実際の歩打ち防御調査の中断を接続部で保持する。

        初回準備だけの保護と抑制優先を先後と各操作で確認する。
        """
        for side in Side:
            for operation in ("prepare", "inspect", "advance"):
                for suppress in (False, True):
                    p, dest = uchi(side)
                    p.board.set_piece(
                        Square(4, 3) if side == Side.SENTE else Square(6, 7), None
                    )
                    before = snapshot(p)
                    c = SearchControl(None, 0)
                    ops = shogi.make_controlled_operations(side)
                    with pawn_defense_stop(side, dest, c, suppress):
                        r = (
                            ops.advance(p, mg.DropMove(mg.BasicPieceType.PAWN, dest), c)
                            if operation == "advance"
                            else getattr(ops, operation)(p, c)
                        )
                    if operation == "prepare" and not suppress:
                        self.assertEqual(
                            r, PreparedRoot(mg.DropMove(mg.BasicPieceType.PAWN, dest))
                        )
                    else:
                        self.assertEqual(
                            r,
                            SearchInterrupted(
                                SearchSignal.SUPPRESS if suppress else SearchSignal.STOP
                            ),
                        )
                    self.assertEqual(snapshot(p), before)

    def test_adapter_passes_same_control_and_faults(self):
        """全操作へ同じ制御を渡し、依存操作の故障を隠さない。

        別制御の隠れた生成と、例外の正常中断化を検出する。
        """
        p = parse_sfen(KINGS).position
        move = parse_usi_move("9i9h")
        c = SearchControl(None, 0)
        ops = shogi.make_controlled_operations(Side.SENTE)
        for name, op, args in (
            ("first_legal_move_controlled", ops.prepare, (p, c)),
            ("legal_moves_controlled", ops.inspect, (p, c)),
            ("position_after_move_controlled", ops.advance, (p, move, c)),
        ):
            original = getattr(shogi, name)

            def observed(*args, original=original, **kwargs):
                self.assertIs(kwargs["control"], c)
                return original(*args, **kwargs)

            with patch.object(shogi, name, side_effect=observed):
                op(*args)
            fault = RuntimeError(name)
            with (
                patch.object(shogi, name, side_effect=fault),
                self.assertRaises(RuntimeError) as caught,
            ):
                op(*args)
            self.assertIs(caught.exception, fault)
        fault = RuntimeError("評価")
        with (
            patch.object(shogi, "material_balance", side_effect=fault),
            self.assertRaises(RuntimeError) as caught,
        ):
            ops.evaluate(p)
        self.assertIs(caught.exception, fault)
