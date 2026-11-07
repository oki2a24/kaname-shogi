"""静止探索の追加末端と通常探索の完了境界を確認する。"""

import inspect
import unittest
from dataclasses import replace

from search_tree_support import TreeNode, controlled_operations

from kaname_shogi.search import alpha_beta, iterative_deepening, minimax
from kaname_shogi.search import result as search_result
from kaname_shogi.search.contracts import ControlledSearchOperations
from kaname_shogi.search.result import (
    ControlledCompletion,
    ControlledSearchResult,
    IterationResult,
    SearchInterrupted,
    SearchResult,
)
from kaname_shogi.search_control import SearchControl, SearchSignal


def leaf_hook_operations(operations, callback):
    """追加末端の有無を吸収し、実装前も探索結果のRedを確認する。"""
    if "search_leaf" not in inspect.signature(ControlledSearchOperations).parameters:
        return operations
    return replace(operations, search_leaf=callback)


def leaf_hook_tree():
    """Aは静止評価対象、Bは深さ0より前に終端と判定する木を作る。"""
    a = TreeNode(
        "A",
        (0, 1),
        children=(("continue", TreeNode("A-end", terminal_score=(0, 1))),),
    )
    b = TreeNode("B", (0, 2), terminal_score=(0, 2))
    return TreeNode("root", children=(("A", a), ("B", b)))


def iterative_limit_tree():
    """予備手A・深さ1最善手Bとなり、深さ2のA枝で未完了にできる木を作る。"""
    a1 = TreeNode(
        "A1",
        (0, 4),
        children=(("continue", TreeNode("A1-end", terminal_score=(0, 4))),),
    )
    b1 = TreeNode(
        "B1",
        (0, 1),
        children=(("continue", TreeNode("B1-end", terminal_score=(0, 1))),),
    )
    a = TreeNode("A", (0, 3), children=(("next", a1),))
    b = TreeNode("B", (0, 5), children=(("next", b1),))
    return TreeNode("root", children=(("A", a), ("B", b)))


def two_nonterminal_leaves():
    """各候補が深さ0で追加評価対象となる二枝木を作る。"""
    a = TreeNode(
        "A",
        (0, 1),
        children=(("continue", TreeNode("A-end", terminal_score=(0, 1))),),
    )
    b = TreeNode(
        "B",
        (0, 2),
        children=(("continue", TreeNode("B-end", terminal_score=(0, 2))),),
    )
    return TreeNode("root", children=(("A", a), ("B", b)))


class QuiescenceBoundaryTests(unittest.TestCase):
    def test_leaf_hook_changes_move_and_preserves_default_for_both_methods(self):
        """末端操作が静的値を置き換え、既定探索は従来の手を選ぶ。

        末端操作を無視する実装と、hookなしの既存経路まで変える実装を検出する。
        """
        for method in (alpha_beta, minimax):
            with self.subTest(method=method.__name__):
                tree = leaf_hook_tree()
                baseline = method.search_controlled(
                    tree,
                    1,
                    controlled_operations(),
                    SearchControl(None, 0, now_ns=lambda: 0),
                )
                calls = []

                def extend(
                    node,
                    inspected,
                    lower,
                    upper,
                    control,
                    calls=calls,
                ):
                    calls.append(node.label)
                    return (0, 4) if node.label == "A" else node.score

                extended = method.search_controlled(
                    tree,
                    1,
                    leaf_hook_operations(controlled_operations(), extend),
                    SearchControl(None, 0, now_ns=lambda: 0),
                )

                self.assertEqual((baseline.score, baseline.move), ((0, 2), "B"))
                self.assertEqual((extended.score, extended.move), ((0, 4), "A"))
                self.assertEqual(calls, ["A"])

    def test_terminal_nodes_skip_leaf_hook(self):
        """終端評価を追加末端へ渡さず、合法手のない局面を保つ。

        詰み等の終端値を静的評価や追加操作の返値で上書きする誤りを検出する。
        """
        calls = []

        def extend(node, inspected, lower, upper, control):
            calls.append(node.label)
            return (0, 99)

        result = alpha_beta.search_controlled(
            leaf_hook_tree(),
            1,
            leaf_hook_operations(controlled_operations(), extend),
            SearchControl(None, 0, now_ns=lambda: 0),
        )

        self.assertEqual((result.score, result.move), ((0, 99), "A"))
        self.assertEqual(calls, ["A"])

    def test_leaf_hook_receives_current_bounds_and_shared_control(self):
        """追加末端が現在の上下限と呼出し元の同一制御を受け取る。

        境界を初期化・反転する誤りと、追加制御を別生成する誤りを検出する。
        """
        for method in (alpha_beta, minimax):
            with self.subTest(method=method.__name__):
                control = SearchControl(None, 0, now_ns=lambda: 0)
                calls = []

                def extend(
                    node,
                    inspected,
                    lower,
                    upper,
                    active_control,
                    calls=calls,
                ):
                    calls.append((node.label, lower, upper, active_control))
                    return (0, 4) if node.label == "A" else (0, 2)

                result = method.search_controlled(
                    two_nonterminal_leaves(),
                    1,
                    leaf_hook_operations(controlled_operations(), extend),
                    control,
                )

                self.assertEqual((result.score, result.move), ((0, 4), "A"))
                self.assertEqual([call[0] for call in calls], ["A", "B"])
                self.assertTrue(all(call[3] is control for call in calls))
                if method is alpha_beta:
                    self.assertEqual(
                        [(call[1], call[2]) for call in calls],
                        [(None, None), ((0, 4), None)],
                    )
                else:
                    self.assertEqual(
                        [(call[1], call[2]) for call in calls],
                        [(None, None), (None, None)],
                    )

    def test_leaf_hook_receives_a_nonempty_upper_bound(self):
        """最小化中に確定した上限も追加末端へそのまま渡す。

        αβの上限を失い、静止探索側の枝刈りを誤らせる接続を検出する。
        """
        for method in (alpha_beta, minimax):
            with self.subTest(method=method.__name__):
                calls = []

                def extend(node, inspected, lower, upper, control, calls=calls):
                    calls.append((node.label, lower, upper))
                    return (0, 2) if node.label == "A" else (0, 4)

                tree = replace(two_nonterminal_leaves(), maximizing=False)
                result = method.search_controlled(
                    tree,
                    1,
                    leaf_hook_operations(controlled_operations(), extend),
                    SearchControl(None, 0, now_ns=lambda: 0),
                )

                self.assertEqual((result.score, result.move), ((0, 2), "A"))
                if method is alpha_beta:
                    self.assertEqual(
                        calls,
                        [("A", None, None), ("B", None, (0, 2))],
                    )
                else:
                    self.assertEqual(calls, [("A", None, None), ("B", None, None)])

    def test_leaf_hook_stop_or_suppression_is_not_scored(self):
        """末端操作の停止を評価へ変換せず同じ制御から優先して返す。

        末端操作中の停止要求を通常評価にし、後続枝まで調べる誤りを検出する。
        """
        for signal in (SearchSignal.STOP, SearchSignal.SUPPRESS):
            with self.subTest(signal=signal):
                control = SearchControl(None, 0, now_ns=lambda: 0)
                calls = []

                def extend(
                    node,
                    inspected,
                    lower,
                    upper,
                    active_control,
                    signal=signal,
                    calls=calls,
                ):
                    calls.append(node.label)
                    active_control.request_stop(
                        suppress_response=signal is SearchSignal.SUPPRESS
                    )
                    return (0, 99)

                result = alpha_beta.search_controlled(
                    two_nonterminal_leaves(),
                    1,
                    leaf_hook_operations(controlled_operations(), extend),
                    control,
                )

                self.assertEqual(result, SearchInterrupted(signal))
                self.assertEqual(calls, ["A"])

    def test_quiescence_limit_is_a_frozen_marker_without_a_score(self):
        """上限未完了に手や採点値を付けず、不変な結果にする。

        未完了を評価として比較・公開できる値にしてしまう誤りを検出する。
        """
        marker_type = getattr(search_result, "QuiescenceLimit", None)
        self.assertIsNotNone(marker_type, "未完了専用の型が必要です")
        if marker_type is None:
            return
        marker = marker_type()

        for field in ("score", "move", "visited_nodes", "reason"):
            self.assertFalse(hasattr(marker, field))
        with self.assertRaises(AttributeError):
            marker.unexpected = True

    def test_quiescence_completion_keeps_last_completed_or_reserve_move(self):
        """静止探索上限の終了状態が完了記録か予備手と整合する。

        未完了深さの手を採用する誤りと、最初の未完了時の合法手消失を検出する。
        """
        state = getattr(ControlledCompletion, "QUIESCENCE_LIMIT", None)
        self.assertIsNotNone(state, "追加上限の終了状態が必要です")
        if state is None:
            return
        last = IterationResult(1, SearchResult((0, 3), "A", 2, None), 2)

        limited = ControlledSearchResult(state, "A", last)
        self.assertEqual(
            (limited.completion, limited.move, limited.last_completed),
            (state, "A", last),
        )
        fallback = ControlledSearchResult(state, "B", None)
        self.assertEqual(
            (fallback.completion, fallback.move, fallback.last_completed),
            (state, "B", None),
        )
        with self.assertRaises(ValueError):
            ControlledSearchResult(state, "B", last)

    def test_quiescence_limit_propagates_through_both_fixed_depth_searchers(self):
        """上限未完了を評価・候補手に変換せず両再帰方式で返す。

        未完了を通常の静的値へ読み替えたり、片方の方式だけ継続したりする誤りを検出する。
        """
        marker_type = getattr(search_result, "QuiescenceLimit", None)
        self.assertIsNotNone(marker_type, "未完了専用の型が必要です")
        if marker_type is None:
            return
        marker = marker_type()
        tree = leaf_hook_tree()
        for method in (alpha_beta, minimax):
            with self.subTest(method=method.__name__):
                result = method.search_controlled(
                    tree,
                    1,
                    leaf_hook_operations(controlled_operations(), lambda *args: marker),
                    SearchControl(None, 0, now_ns=lambda: 0),
                )
                self.assertIs(result, marker)

    def test_incomplete_iteration_falls_back_and_reports_started_depths(self):
        """静止探索上限は旧完了手へ戻り、開始反復ごとに一度観測する。

        未完了手の採用、深さ誤記、最後の未完了反復の観測欠落を検出する。
        """
        marker_type = getattr(search_result, "QuiescenceLimit", None)
        state = getattr(ControlledCompletion, "QUIESCENCE_LIMIT", None)
        self.assertIsNotNone(marker_type, "未完了専用の型が必要です")
        self.assertIsNotNone(state, "追加上限の終了状態が必要です")
        if marker_type is None or state is None:
            return
        marker = marker_type()
        observed = []

        def extend(node, inspected, lower, upper, control):
            if node.label == "A1":
                return marker
            return node.score

        operations = leaf_hook_operations(controlled_operations(), extend)
        parameters = inspect.signature(iterative_deepening.search_controlled).parameters
        kwargs = {}
        if "on_iteration" in parameters:
            kwargs["on_iteration"] = lambda depth, result: observed.append(
                (depth, result)
            )
        control = SearchControl(None, 0, now_ns=lambda: 0)
        for pruning in (True, False):
            with self.subTest(pruning=pruning):
                observed.clear()
                result = iterative_deepening.search_controlled(
                    iterative_limit_tree(),
                    3,
                    operations,
                    control,
                    pruning=pruning,
                    **kwargs,
                )

                self.assertEqual(result.completion, state)
                self.assertEqual((result.move, result.last_completed.depth), ("B", 1))
                self.assertEqual(result.last_completed.result.score, (0, 5))
                self.assertEqual([depth for depth, _ in observed], [1, 2])
                self.assertIsInstance(observed[0][1], IterationResult)
                self.assertEqual(observed[0][1].result.move, "B")
                self.assertIs(observed[1][1], marker)
                self.assertEqual(
                    control.check(),
                    SearchSignal.CONTINUE,
                    "未完了上限は共有停止要求を書き換えません",
                )

    def test_first_incomplete_iteration_returns_prepared_reserve(self):
        """最初の反復が未完了なら合法予備手を返し、未完了記録を作らない。

        評価の捏造と、深さ0相当の未完了手なし応答を検出する。
        """
        marker_type = getattr(search_result, "QuiescenceLimit", None)
        state = getattr(ControlledCompletion, "QUIESCENCE_LIMIT", None)
        self.assertIsNotNone(marker_type, "未完了専用の型が必要です")
        self.assertIsNotNone(state, "追加上限の終了状態が必要です")
        if marker_type is None or state is None:
            return
        marker = marker_type()
        observed = []
        control = SearchControl(None, 0, now_ns=lambda: 0)

        result = iterative_deepening.search_controlled(
            leaf_hook_tree(),
            2,
            leaf_hook_operations(controlled_operations(), lambda *args: marker),
            control,
            on_iteration=lambda depth, item: observed.append((depth, item)),
        )

        self.assertEqual(
            (result.completion, result.move, result.last_completed), (state, "A", None)
        )
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0][0], 1)
        self.assertIs(observed[0][1], marker)
        self.assertEqual(control.check(), SearchSignal.CONTINUE)

    def test_suppression_at_quiescence_limit_overrides_fallback(self):
        """上限未完了と同時の抑制は応答手を隠し、完了記録を保つ。

        抑制より予備手・直前の完了手を優先する誤りを検出する。
        """
        marker_type = getattr(search_result, "QuiescenceLimit", None)
        state = getattr(ControlledCompletion, "QUIESCENCE_LIMIT", None)
        self.assertIsNotNone(marker_type, "未完了専用の型が必要です")
        self.assertIsNotNone(state, "追加上限の終了状態が必要です")
        if marker_type is None or state is None:
            return
        marker = marker_type()
        control = SearchControl(None, 0, now_ns=lambda: 0)

        def extend(node, inspected, lower, upper, active_control):
            if node.label == "A1":
                return marker
            return node.score

        def observe(depth, item):
            if depth == 2 and item is marker:
                control.request_stop(suppress_response=True)

        result = iterative_deepening.search_controlled(
            iterative_limit_tree(),
            3,
            leaf_hook_operations(controlled_operations(), extend),
            control,
            on_iteration=observe,
        )

        self.assertEqual(result.completion, ControlledCompletion.SUPPRESSED)
        self.assertIsNone(result.move)
        self.assertEqual(result.last_completed.depth, 1)
        self.assertEqual(result.last_completed.result.move, "B")
        self.assertEqual(control.check(), SearchSignal.SUPPRESS)

    def test_iteration_observer_exists_and_propagates_callback_errors(self):
        """反復観測の例外を探索停止や未完了へ変換せず伝播する。

        観測失敗を黙って飲み込み、診断記録を欠落させる誤りを検出する。
        """
        parameters = inspect.signature(iterative_deepening.search_controlled).parameters
        self.assertIn("on_iteration", parameters, "反復結果の観測入口が必要です")
        failure = RuntimeError("観測に失敗")

        def broken(depth, result):
            raise failure

        with self.assertRaises(RuntimeError) as caught:
            iterative_deepening.search_controlled(
                leaf_hook_tree(),
                1,
                controlled_operations(),
                SearchControl(None, 0, now_ns=lambda: 0),
                on_iteration=broken,
            )
        self.assertIs(caught.exception, failure)

    def test_stop_before_depth_does_not_create_observer_record(self):
        """反復開始前の停止では観測用の架空記録を作らない。

        開始していない深さの表示と合法予備手の消失を検出する。
        """
        parameters = inspect.signature(iterative_deepening.search_controlled).parameters
        self.assertIn("on_iteration", parameters, "反復結果の観測入口が必要です")
        observed = []
        control = SearchControl(None, 0, now_ns=lambda: 0)
        control.request_stop()

        result = iterative_deepening.search_controlled(
            leaf_hook_tree(),
            2,
            controlled_operations(),
            control,
            on_iteration=lambda depth, record: observed.append((depth, record)),
        )

        self.assertEqual(result.completion, ControlledCompletion.STOPPED)
        self.assertEqual(result.move, "A")
        self.assertEqual(observed, [])

    def test_iteration_observer_reports_an_interrupted_started_depth(self):
        """開始後に通常停止した反復も理由つきで一度だけ観測する。

        中断した探索仕事の欠落と、開始前停止を二重記録する誤りを検出する。
        """
        parameters = inspect.signature(iterative_deepening.search_controlled).parameters
        self.assertIn("on_iteration", parameters, "反復結果の観測入口が必要です")
        control = SearchControl(None, 0, now_ns=lambda: 0)
        base = controlled_operations()
        observed = []

        def stop_after_first_child(node, move, active_control):
            advanced = base.advance(node, move, active_control)
            if node.label == "root":
                active_control.request_stop()
            return advanced

        result = iterative_deepening.search_controlled(
            leaf_hook_tree(),
            2,
            replace(base, advance=stop_after_first_child),
            control,
            on_iteration=lambda depth, item: observed.append((depth, item)),
        )

        self.assertEqual(result.completion, ControlledCompletion.STOPPED)
        self.assertEqual(result.move, "A")
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0][0], 1)
        self.assertEqual(observed[0][1], SearchInterrupted(SearchSignal.STOP))
