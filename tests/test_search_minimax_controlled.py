"""制御付き全幅探索の完了値と停止シグナル伝播を確認する。"""

import unittest
from dataclasses import replace
from unittest.mock import Mock

from search_tree_support import controlled_operations, two_level

from kaname_shogi.search import minimax
from kaname_shogi.search.result import SearchInterrupted, SearchResult
from kaname_shogi.search_control import SearchControl, SearchSignal


class ControlledMinimaxTests(unittest.TestCase):
    def test_completed_result_is_full_width(self):
        """制御付き入口がprepareを使わず全幅の完了値を返す。

        αβ接続・合法予備手準備・根候補値の欠落を検出する。
        """
        seen = []
        base = controlled_operations(seen)
        prepare = Mock(side_effect=AssertionError("指定深さ探索では準備しない"))
        search_controlled = getattr(minimax, "search_controlled", None)
        self.assertTrue(callable(search_controlled), "制御付き全幅入口が必要です")
        result = search_controlled(
            two_level([3, 5], [-2, 10]),
            2,
            replace(base, prepare=prepare),
            SearchControl(None, 0, now_ns=lambda: 0),
        )
        self.assertIsInstance(result, SearchResult)
        self.assertEqual(
            (result.score, result.move, result.visited_nodes), ((0, 3), "A", 7)
        )
        self.assertEqual(result.root_scores, (("A", (0, 3)), ("B", (0, -2))))
        self.assertEqual(seen, ["root", "A", "A0", "A1", "B", "B0", "B1"])
        prepare.assert_not_called()

    def test_preferred_move_reorders_only_the_controlled_root(self):
        """制御付き全幅でも優先手を根だけに適用する。

        引数欠落、子への優先手伝播、候補枝の省略を検出する。
        """
        seen = []
        base = controlled_operations(seen)
        search_controlled = getattr(minimax, "search_controlled", None)
        self.assertTrue(callable(search_controlled), "制御付き全幅入口が必要です")
        result = search_controlled(
            two_level([3, 5], [-2, 10]),
            2,
            base,
            SearchControl(None, 0, now_ns=lambda: 0),
            preferred_move="B",
        )
        self.assertIsInstance(result, SearchResult)
        self.assertEqual(
            (result.score, result.move, result.visited_nodes), ((0, 3), "A", 7)
        )
        self.assertEqual(result.root_scores, (("B", (0, -2)), ("A", (0, 3))))
        self.assertEqual(seen, ["root", "B", "B0", "B1", "A", "A0", "A1"])

    def test_stop_and_suppression_do_not_publish_partial_scores(self):
        """操作途中の通常停止・抑制は未完了値を返さず伝播する。

        部分スコアの公開、停止後の子調査、抑制の通常停止化を検出する。
        """
        for signal in (SearchSignal.STOP, SearchSignal.SUPPRESS):
            with self.subTest(signal=signal):
                seen = []
                base = controlled_operations(seen)
                control = SearchControl(None, 0, now_ns=lambda: 0)

                def advance(node, move, active_control, base=base, requested=signal):
                    result = base.advance(node, move, active_control)
                    active_control.request_stop(
                        suppress_response=requested is SearchSignal.SUPPRESS
                    )
                    return result

                search_controlled = getattr(minimax, "search_controlled", None)
                self.assertTrue(
                    callable(search_controlled), "制御付き全幅入口が必要です"
                )
                result = search_controlled(
                    two_level([3, 5], [-2, 10]),
                    2,
                    replace(base, advance=advance),
                    control,
                )
                self.assertEqual(result, SearchInterrupted(signal))
                self.assertNotIsInstance(result, SearchResult)
                self.assertEqual(seen, ["root"])

    def test_invalid_depth_fails_before_preparation(self):
        """不正な深さは操作開始前に拒否する。

        bool許容や検査より先の準備副作用を検出する。
        """
        base = controlled_operations()
        prepare = Mock(side_effect=AssertionError("不正入力で準備しない"))
        search_controlled = getattr(minimax, "search_controlled", None)
        self.assertTrue(callable(search_controlled), "制御付き全幅入口が必要です")
        for depth in (-1, True, 1.5):
            with self.subTest(depth=depth), self.assertRaises(ValueError):
                search_controlled(
                    two_level([3], [4]),
                    depth,
                    replace(base, prepare=prepare),
                    SearchControl(None, 0, now_ns=lambda: 0),
                )
        prepare.assert_not_called()
