"""制御付き反復の予備手・完了記録・期限と返却境界を確認する。"""

import inspect
import unittest
from dataclasses import FrozenInstanceError, replace
from unittest.mock import patch

from search_tree_support import TreeNode, controlled_operations, depth_tree, two_level
from test_search_shogi import KINGS, MATE, RECAPTURE

from kaname_shogi import movegen as mg
from kaname_shogi.model import Side
from kaname_shogi.search import alpha_beta, shogi
from kaname_shogi.search import iterative_deepening as iterative
from kaname_shogi.search.contracts import PreparedRoot
from kaname_shogi.search.result import ControlledCompletion as C
from kaname_shogi.search.result import ControlledSearchResult, SearchInterrupted
from kaname_shogi.search_control import SearchControl, SearchSignal
from kaname_shogi.sfen import format_sfen, parse_sfen
from kaname_shogi.time_management import SearchBudget


def changing_tree():
    """深さ1 A=5、深さ2 B=1、深さ3 A=9の独立した数値木。"""
    root = two_level([1, -2], [2, 1])
    return replace(
        root,
        children=tuple(
            (
                move,
                replace(
                    branch,
                    score=(0, 5 if move == "A" else 3),
                    children=tuple(
                        (
                            m,
                            replace(
                                leaf,
                                children=(
                                    (
                                        "end",
                                        TreeNode(
                                            leaf.label + "end",
                                            (0, 9 if move == "A" else 0),
                                        ),
                                    ),
                                ),
                            ),
                        )
                        for m, leaf in branch.children
                    ),
                ),
            )
            for move, branch in root.children
        ),
    )


class FinalCheckControl(SearchControl):
    """特定の反復の根最終確認だけで停止する制御ダブル。"""

    def __init__(self, depth, *, suppress=False):
        super().__init__(None, 0, now_ns=lambda: 0)
        self.depth = depth
        self.current_depth = 0
        self.suppress = suppress

    def check(self, **kwargs):
        caller = inspect.currentframe().f_back.f_back
        if self.current_depth == self.depth and caller.f_code.co_name == "_search":
            self.request_stop(suppress_response=self.suppress)
        return super().check(**kwargs)


class ControlledIterativeTests(unittest.TestCase):
    def assert_record(self, r, state, move, depth, score, total):
        """結果と完了記録を独立リテラルの一組として比較する。"""
        self.assertEqual((r.completion, r.move), (state, move))
        self.assertIsNotNone(r.last_completed)
        last = r.last_completed
        self.assertEqual(
            (last.depth, last.result.score, last.total_visited_nodes),
            (depth, score, total),
        )

    def test_zero_budget_and_initial_stop_return_fallback(self):
        """初回完了前の通常停止は予備手を返し、深さ1を始めない。

        0予算の無視・架空完了記録・未確保の投了を検出する。
        """
        for zero in (False, True):
            c = SearchControl(SearchBudget(0, 0) if zero else None, 0, now_ns=lambda: 0)
            if not zero:
                c.request_stop()
            base = controlled_operations()
            prepared = []
            seen = []

            def prepare(node, control, prepared=prepared, base=base):
                prepared.append(node)
                return base.prepare(node, control)

            r = iterative.search_controlled(
                changing_tree(),
                3,
                replace(
                    base,
                    prepare=prepare,
                    inspect=lambda n, c, seen=seen: seen.append(n),
                ),
                c,
            )
            self.assertEqual(r, ControlledSearchResult(C.STOPPED, "A", None))
            self.assertEqual(len(prepared), 1)
            self.assertEqual(seen, [])
        r = iterative.search_controlled(
            changing_tree(), 2, controlled_operations(), SearchControl(None, 0)
        )
        self.assert_record(r, C.COMPLETE, "B", 2, (0, 1), 10)

    def test_no_legal_move_has_no_iteration_record(self):
        """準備の手なし確定と抑制中断は異なる終了状態になる。

        旧入口と同じ深さ1記録の捏造や、抑制を投了にする誤りを検出する。
        """
        base = controlled_operations()
        for suppress in (False, True):
            ops = replace(
                base,
                prepare=lambda n, c, suppress=suppress: (
                    SearchInterrupted(SearchSignal.SUPPRESS)
                    if suppress
                    else PreparedRoot(None)
                ),
            )
            r = iterative.search_controlled(
                TreeNode("end"), 4, ops, SearchControl(None, 0)
            )
            self.assertEqual(
                r,
                ControlledSearchResult(
                    C.SUPPRESSED if suppress else C.NO_LEGAL_MOVE, None, None
                ),
            )

    def test_rejects_invalid_depth_before_prepare(self):
        """上限の不正値を準備より前に拒否する。

        bool許容と実行後の遅い検査を検出する。
        """
        for bad in (0, -1, True, False, 1.5, None):
            seen = []
            ops = replace(
                controlled_operations(), prepare=lambda n, c, seen=seen: seen.append(n)
            )
            with self.assertRaises(ValueError):
                iterative.search_controlled(
                    changing_tree(), bad, ops, SearchControl(None, 0)
                )
            self.assertEqual(seen, [])

    def test_preparation_stop_is_contract_error(self):
        """準備で通常停止や整合しない根結果を返す操作セットを拒否する。

        予備手も手なし確定もない状態の正常終了化を検出する。
        """
        ops = replace(
            controlled_operations(),
            prepare=lambda n, c: SearchInterrupted(SearchSignal.STOP),
        )
        with self.assertRaises(ValueError):
            iterative.search_controlled(changing_tree(), 2, ops, SearchControl(None, 0))
        ops = replace(controlled_operations(), prepare=lambda n, c: PreparedRoot("A"))
        with self.assertRaises(ValueError):
            iterative.search_controlled(TreeNode("end"), 1, ops, SearchControl(None, 0))

    def test_incomplete_deeper_search_keeps_latest_record(self):
        """深さ3の暫定Aで深さ2の完了B・評価1・累計10を上書きしない。

        浅い高評価固定、中断反復の採用、未完了訪問の加算を検出する。
        """
        for suppress in (False, True):
            for early in (False, True):
                c = FinalCheckControl(3, suppress=suppress)
                base = controlled_operations()

                def inspect_node(
                    node, control, c=c, early=early, suppress=suppress, base=base
                ):
                    if node.label == "root":
                        c.current_depth += 1
                    if early and c.current_depth == 3 and node.label == "A0end":
                        c.request_stop(suppress_response=suppress)
                    return base.inspect(node, control)

                r = iterative.search_controlled(
                    changing_tree(), 3, replace(base, inspect=inspect_node), c
                )
                self.assert_record(
                    r,
                    C.SUPPRESSED if suppress else C.STOPPED,
                    None if suppress else "B",
                    2,
                    (0, 1),
                    10,
                )
                self.assertEqual(r.last_completed.result.move, "B")
        r = iterative.search_controlled(
            changing_tree(), 3, controlled_operations(), SearchControl(None, 0)
        )
        self.assertEqual(
            (r.completion, r.move, r.last_completed.result.score),
            (C.COMPLETE, "A", (0, 9)),
        )

    def test_target_stops_next_depth_without_discarding_current(self):
        """同一原点の目標は次の深さだけを止め、上限は進行中も止める。

        深さごとの原点再作成と期限一致の停止漏れを検出する。
        """
        origin = 1_000_000_000
        for elapsed, expected_depth, state in (
            (9_999_999, 3, C.COMPLETE),
            (10_000_000, 2, C.STOPPED),
            (10_000_001, 2, C.STOPPED),
            (19_999_999, 2, C.STOPPED),
            (20_000_000, 1, C.STOPPED),
            (20_000_001, 1, C.STOPPED),
        ):
            clock = [origin]
            c = SearchControl(
                SearchBudget(10, 20), origin, now_ns=lambda clock=clock: clock[0]
            )
            base = controlled_operations()
            roots = []

            def inspect_node(
                node, control, c=c, roots=roots, clock=clock, elapsed=elapsed, base=base
            ):
                self.assertIs(control, c)
                if node.label == "root":
                    roots.append(node)
                if len(roots) == 2 and node.label == "A":
                    clock[0] = origin + elapsed
                return base.inspect(node, control)

            r = iterative.search_controlled(
                changing_tree(), 3, replace(base, inspect=inspect_node), c
            )
            self.assertEqual(r.completion, state)
            self.assertIsNotNone(r.last_completed)
            self.assertEqual(r.last_completed.depth, expected_depth)
            self.assertEqual(len(roots), expected_depth if expected_depth != 1 else 2)

    def test_protection_does_not_restart_and_control_is_reused(self):
        """深さ2からの停止で保護を再開せず、同じ制御を各操作へ渡す。

        最終結果だけで隠れる保護誤指定を候補適用禁止でも検出する。
        """
        p = parse_sfen(KINGS).position
        c = SearchControl(None, 0)
        base = shogi.make_controlled_operations(Side.SENTE)
        roots = []
        original = shogi.legal_moves_controlled
        applied = []
        apply = mg.apply_move

        def inspect_node(node, control):
            self.assertIs(control, c)
            if node is p:
                roots.append(node)
                if len(roots) == 2:
                    c.request_stop()
            return base.inspect(node, control)

        def generation(*args, **kwargs):
            self.assertIs(kwargs["control"], c)
            self.assertFalse(kwargs["protect_first_legal"])
            return original(*args, **kwargs)

        def observe_apply(*args, **kwargs):
            if len(roots) == 2:
                applied.append(args)
            return apply(*args, **kwargs)

        def prepare(node, control):
            self.assertIs(control, c)
            return base.prepare(node, control)

        def advance(node, move, control):
            self.assertIs(control, c)
            return base.advance(node, move, control)

        with (
            patch.object(shogi, "legal_moves_controlled", side_effect=generation),
            patch.object(mg, "apply_move", side_effect=observe_apply),
        ):
            r = iterative.search_controlled(
                p,
                3,
                replace(base, prepare=prepare, inspect=inspect_node, advance=advance),
                c,
            )
        self.assert_record(r, C.STOPPED, r.move, 1, (0, 0), 4)
        self.assertEqual(applied, [])

    def test_final_boundary_distinguishes_stop_and_suppression(self):
        """根の確定前の停止と確定後の停止・返却前抑制を区別する。

        完了の取消し、最終抑制漏れ、抑制時の記録消失を検出する。
        """
        for suppress in (False, True):
            for limit in (1, 2):
                c = SearchControl(None, 0)
                real = alpha_beta.search_controlled

                def completed(*args, real=real, c=c, suppress=suppress, **kwargs):
                    result = real(*args, **kwargs)
                    c.request_stop(suppress_response=suppress)
                    return result

                with patch.object(
                    alpha_beta, "search_controlled", side_effect=completed
                ):
                    r = iterative.search_controlled(
                        changing_tree(), limit, controlled_operations(), c
                    )
                state = (
                    C.SUPPRESSED
                    if suppress
                    else C.COMPLETE
                    if limit == 1
                    else C.STOPPED
                )
                self.assert_record(r, state, None if suppress else "A", 1, (0, 5), 3)
        c = FinalCheckControl(1)
        base = controlled_operations()

        def inspect_node(node, control):
            if node.label == "root":
                c.current_depth += 1
            return base.inspect(node, control)

        r = iterative.search_controlled(
            changing_tree(), 1, replace(base, inspect=inspect_node), c
        )
        self.assertEqual(r, ControlledSearchResult(C.STOPPED, "A", None))

        # 完了データ構築後、外側の返却確認だけで抑制する。
        class ReturnControl(SearchControl):
            def check(self, **kwargs):
                if inspect.currentframe().f_back.f_code.co_name == "finish":
                    self.request_stop(suppress_response=True)
                return super().check(**kwargs)

        for root in (changing_tree(), TreeNode("end")):
            r = iterative.search_controlled(
                root, 1, controlled_operations(), ReturnControl(None, 0)
            )
            self.assertEqual((r.completion, r.move), (C.SUPPRESSED, None))
            self.assertEqual(r.last_completed is None, not root.children)

    def test_searches_do_not_share_control_fallback_or_records(self):
        """別探索と入れ子探索が制御・予備手・累計を共有しない。

        モジュール共有状態による結果混在や過去記録の書換えを検出する。
        """
        other = TreeNode("second", children=(("X", TreeNode("X", (0, -3))),))
        nested = []
        base = controlled_operations()
        c = SearchControl(None, 0)

        def prepare(node, control):
            nested.append(
                iterative.search_controlled(
                    other, 1, controlled_operations(), SearchControl(None, 0)
                )
            )
            return base.prepare(node, control)

        r = iterative.search_controlled(
            changing_tree(), 2, replace(base, prepare=prepare), c
        )
        self.assert_record(r, C.COMPLETE, "B", 2, (0, 1), 10)
        self.assert_record(nested[0], C.COMPLETE, "X", 1, (0, -3), 2)
        with self.assertRaises(FrozenInstanceError):
            r.last_completed.depth = 9
        c.request_stop()
        stopped = iterative.search_controlled(other, 2, controlled_operations(), c)
        self.assertEqual(stopped, ControlledSearchResult(C.STOPPED, "X", None))
        again = iterative.search_controlled(
            other, 1, controlled_operations(), SearchControl(None, 0)
        )
        self.assertIsNot(again.last_completed, nested[0].last_completed)

    def test_faults_after_completed_depth_remain_faults(self):
        """完了記録があっても後続操作の故障を保持手で隠さない。

        広いexceptによる正常停止化を各操作と時計で検出する。
        """

        def run_case(phase):
            roots = []
            fault = RuntimeError(phase)

            def now():
                if phase == "clock" and len(roots) == 3:
                    raise fault
                return 0

            c = SearchControl(None, 0, now_ns=now)
            base = controlled_operations()

            def inspect_node(node, control):
                if node.label == "root":
                    roots.append(node)
                if phase == "inspect" and len(roots) == 3:
                    raise fault
                return base.inspect(node, control)

            def prepare(node, control):
                if phase == "prepare":
                    raise fault
                return base.prepare(node, control)

            def advance(node, move, control):
                if phase == "advance" and len(roots) == 3:
                    raise fault
                return base.advance(node, move, control)

            def evaluate(node):
                if phase == "evaluate" and len(roots) == 3:
                    raise fault
                return base.evaluate(node)

            ops = replace(
                base,
                prepare=prepare,
                inspect=inspect_node,
                advance=advance,
                evaluate=evaluate,
            )
            with self.assertRaises(RuntimeError) as caught:
                iterative.search_controlled(depth_tree(), 3, ops, c)
            self.assertIs(caught.exception, fault)

        for phase in ("prepare", "inspect", "advance", "evaluate", "clock"):
            with self.subTest(phase=phase):
                run_case(phase)

    def test_controlled_shogi_and_legacy_stream_regressions(self):
        """実将棋の先後・各種の手と終端を旧入口と同じ結果へつなぐ。

        準備の訪問加算・視点違い・元局面変更を検出する。
        """
        for sfen in (
            KINGS,
            KINGS.replace(" b ", " w "),
            RECAPTURE,
            MATE,
            "8k/9/9/7P1/9/9/9/9/K8 b - 1",
            "8k/9/9/9/9/9/9/9/K8 b P 1",
            "9/9/9/9/9/9/9/9/9 b - 1",
        ):
            sf = parse_sfen(sfen)
            side = sf.position.side_to_move
            old = list(iterative.search(sf.position, 2, shogi.make_operations(side)))
            r = iterative.search_controlled(
                sf.position,
                2,
                shogi.make_controlled_operations(side),
                SearchControl(None, 0),
            )
            if old[-1].result.move is None:
                self.assertEqual(r, ControlledSearchResult(C.NO_LEGAL_MOVE, None, None))
            else:
                self.assertEqual(r.completion, C.COMPLETE)
                self.assertEqual(r.last_completed, old[-1])
            self.assertEqual(format_sfen(sf), sfen)
        r = iterative.search_controlled(
            parse_sfen(KINGS).position,
            2,
            shogi.make_controlled_operations(Side.SENTE),
            SearchControl(None, 0),
        )
        self.assert_record(r, C.COMPLETE, r.move, 2, (0, 0), 13)
