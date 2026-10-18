"""制御付き指定深さ探索の値・停止境界・中断伝播を確認する。"""

import unittest
from dataclasses import replace

from search_tree_support import TreeNode, controlled_operations, two_level

from kaname_shogi.search import alpha_beta
from kaname_shogi.search.result import SearchInterrupted, SearchResult
from kaname_shogi.search_control import SearchControl, SearchSignal
from kaname_shogi.time_management import SearchBudget


class CheckpointControl(SearchControl):
    """特定の確認点だけで停止し、冗長な上位確認による見逃しを防ぐ教材。"""

    def __init__(self, stop_at):
        super().__init__(None, 0, now_ns=lambda: 0)
        self.stop_at = stop_at
        self.calls = 0

    def check(self, **kwargs):
        self.calls += 1
        return (
            SearchSignal.STOP if self.calls == self.stop_at else SearchSignal.CONTINUE
        )


class ControlledAlphaBetaTests(unittest.TestCase):
    def test_controlled_search_matches_hand_calculated_tree(self):
        """最大・最小側の枝刈りと同点規則を独立値で確認する。

        全枝読み、同点上書き、訪問数や境界値の公開を検出する。
        """
        for root, depth, want in (
            (two_level([3, 5], [-2, 10]), 2, ((0, 3), "A", 6)),
            (two_level([2, 4], [5, 10], maximizing=False), 2, ((0, 4), "A", 6)),
            (two_level([3, 5], [3, -2]), 2, ((0, 3), "A", 6)),
            (TreeNode("end", terminal_score=(-1, 0)), 0, ((-1, 0), None, 1)),
            (two_level([1], [2]), 0, ((0, 0), None, 1)),
        ):
            r = alpha_beta.search_controlled(
                root, depth, controlled_operations(), SearchControl(None, 0)
            )
            self.assertIsInstance(r, SearchResult)
            self.assertEqual((r.score, r.move, r.visited_nodes), want)
            self.assertIsNone(r.root_scores)

    def test_inspect_advance_and_recursive_interrupt_propagate(self):
        """各段の中断値を同一のまま伝え、後続候補を調べない。

        空一覧化、適用成功化、子中断後の比較・候補継続を検出する。
        """
        for maximizing in (True, False):
            root = TreeNode(
                "root",
                maximizing=maximizing,
                children=tuple(
                    (m, TreeNode(m, children=(("child", TreeNode(m + "0", (0, 2))),)))
                    for m in "ABC"
                ),
            )
            for phase in ("inspect", "advance"):
                for slot in "ABC":
                    for reason in (SearchSignal.STOP, SearchSignal.SUPPRESS):
                        base = controlled_operations()
                        interrupted = SearchInterrupted(reason)
                        seen = []
                        c = SearchControl(None, 0)

                        def inspect(
                            node,
                            seen=seen,
                            interrupted=interrupted,
                            phase=phase,
                            slot=slot,
                            base=base,
                            c=c,
                        ):
                            seen.append(("inspect", node.label))
                            return (
                                interrupted
                                if phase == "inspect" and node.label == slot + "0"
                                else base.inspect(node, c)
                            )

                        def advance(
                            node,
                            move,
                            seen=seen,
                            interrupted=interrupted,
                            phase=phase,
                            slot=slot,
                            base=base,
                            c=c,
                        ):
                            seen.append(("advance", node.label, move))
                            return (
                                interrupted
                                if phase == "advance" and node.label == slot
                                else base.advance(node, move, c)
                            )

                        ops = replace(
                            base,
                            inspect=lambda node, control: inspect(node),
                            advance=lambda node, move, control: advance(node, move),
                        )
                        r = alpha_beta.search_controlled(root, 2, ops, c)
                        self.assertIs(r, interrupted)
                        self.assertEqual(
                            seen[-1],
                            ("inspect", slot + "0")
                            if phase == "inspect"
                            else ("advance", slot, "child"),
                        )

    def test_stop_at_each_operation_boundary(self):
        """確認点単独の停止で後続操作を開始せず中断する。

        調査前後・適用前後・評価前後・復帰後・根最終確認の欠落を検出する。
        """
        root = TreeNode("root", children=(("A", TreeNode("A", (0, 7))),))
        for depth, checkpoints in ((0, range(1, 6)), (1, range(1, 9))):
            for checkpoint in checkpoints:
                seen = []
                c = CheckpointControl(checkpoint)
                r = alpha_beta.search_controlled(
                    root, depth, controlled_operations(seen), c
                )
                self.assertEqual(
                    r, SearchInterrupted(SearchSignal.STOP), (depth, checkpoint)
                )
                self.assertLessEqual(c.calls, checkpoint)
                if checkpoint == 1:
                    self.assertEqual(seen, [])
                if depth == 1 and checkpoint in (3, 4, 5):
                    self.assertEqual(seen, ["root"])

    def test_target_is_ignored_but_maximum_stops_inside_depth(self):
        """進行中は目標を無視し上限の一致から中断する。

        include_target誤指定と>=を>へ変える誤りを検出する。
        """
        root = TreeNode("root", children=(("A", TreeNode("A", (0, 7))),))
        for now, stops in (
            (10_000_000, False),
            (19_999_999, False),
            (20_000_000, True),
            (20_000_001, True),
        ):
            clock = [0]
            c = SearchControl(
                SearchBudget(10, 20), 0, now_ns=lambda clock=clock: clock[0]
            )
            base = controlled_operations()

            def advance(node, move, control, clock=clock, now=now, base=base):
                clock[0] = now
                return base.advance(node, move, control)

            r = alpha_beta.search_controlled(root, 1, replace(base, advance=advance), c)
            if stops:
                self.assertEqual(r, SearchInterrupted(SearchSignal.STOP))
            else:
                self.assertIsInstance(r, SearchResult)
                self.assertEqual((r.score, r.move), ((0, 7), "A"))

    def test_preferred_move_validation_waits_for_completed_inspection(self):
        """調査中断時は優先手不在を未確定とし、完了後だけ拒否する。

        中断の空一覧を優先手の誤りへ変える誤りを検出する。
        """
        interrupted = SearchInterrupted(SearchSignal.STOP)
        base = controlled_operations()
        for root in (two_level([1], [2]), TreeNode("end", terminal_score=(-1, 0))):
            for depth in (0, 2):
                c = SearchControl(None, 0)
                with self.assertRaises(ValueError):
                    alpha_beta.search_controlled(
                        root, depth, base, c, preferred_move="missing"
                    )
                r = alpha_beta.search_controlled(
                    root,
                    depth,
                    replace(base, inspect=lambda node, control: interrupted),
                    c,
                    preferred_move="missing",
                )
                self.assertIs(r, interrupted)
        r = alpha_beta.search_controlled(
            two_level([3, 5], [3, 4]),
            2,
            base,
            SearchControl(None, 0),
            preferred_move="B",
        )
        self.assertEqual(r.move, "B")

    def test_depth_validation_precedes_operations(self):
        """不正な深さは操作開始前に拒否し、0は許可する。

        bool許容・検証遅延を検出する。
        """
        for bad in (-1, True, 1.5, None):
            seen = []
            with self.assertRaises(ValueError):
                alpha_beta.search_controlled(
                    TreeNode("end"),
                    bad,
                    controlled_operations(seen),
                    SearchControl(None, 0),
                )
            self.assertEqual(seen, [])

    def test_faults_are_not_converted_to_interruption(self):
        """操作や時計の故障は同じ例外として呼出し元へ伝える。

        広いexceptで予備手や中断に隠す誤りを検出する。
        """
        root = TreeNode("root", children=(("A", TreeNode("A")),))
        for phase in ("inspect", "advance", "evaluate", "clock"):
            for kind in (RuntimeError, ValueError, KeyboardInterrupt):
                fault = kind("故障")

                def broken(*args, fault=fault):
                    raise fault

                ops = controlled_operations()
                c = SearchControl(
                    None, 0, now_ns=broken if phase == "clock" else lambda: 0
                )
                if phase != "clock":
                    ops = replace(ops, **{phase: broken})
                with self.assertRaises(kind) as caught:
                    alpha_beta.search_controlled(
                        root, 0 if phase == "evaluate" else 1, ops, c
                    )
                self.assertIs(caught.exception, fault)

    def test_real_stop_after_inspection_application_and_evaluation(self):
        """実制御への停止要求を操作の復帰後に検出する。

        確認点ダブルに加え通常停止・抑制の単調な要求経路と後続未実行を確認する。
        """

        def run_case(phase, suppress):
            root = TreeNode(
                "root",
                children=(
                    ("A", TreeNode("A", (0, 7), children=(("next", TreeNode("end")),))),
                ),
            )
            c = SearchControl(None, 0)
            base = controlled_operations()
            seen = []

            def inspected(node, control):
                seen.append(("inspect", node.label))
                value = base.inspect(node, control)
                if phase == "inspect":
                    c.request_stop(suppress_response=suppress)
                return value

            def advanced(node, move, control):
                seen.append(("advance", node.label))
                value = base.advance(node, move, control)
                if phase == "advance":
                    c.request_stop(suppress_response=suppress)
                return value

            def evaluated(node):
                seen.append(("evaluate", node.label))
                value = base.evaluate(node)
                c.request_stop(suppress_response=suppress)
                return value

            r = alpha_beta.search_controlled(
                root,
                1,
                replace(base, inspect=inspected, advance=advanced, evaluate=evaluated),
                c,
            )
            self.assertEqual(
                r,
                SearchInterrupted(
                    SearchSignal.SUPPRESS if suppress else SearchSignal.STOP
                ),
            )
            expected = [("inspect", "root")]
            if phase != "inspect":
                expected.append(("advance", "root"))
            if phase == "evaluate":
                expected.extend([("inspect", "A"), ("evaluate", "A")])
            self.assertEqual(seen, expected)

        for phase in ("inspect", "advance", "evaluate"):
            for suppress in (False, True):
                with self.subTest(phase=phase, suppress=suppress):
                    run_case(phase, suppress)
