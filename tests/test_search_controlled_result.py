"""制御付き探索の中断と、最終結果の不整合を確認する。"""

import unittest

from kaname_shogi.search.result import SearchInterrupted
from kaname_shogi.search_control import SearchSignal


class ControlledResultTests(unittest.TestCase):
    def test_interruption_accepts_only_stop_or_suppress(self):
        """中断は通常停止と抑制だけを理由にする。

        継続・不正な値を中断へ混ぜる検証欠落を検出する。
        """
        for reason in (SearchSignal.STOP, SearchSignal.SUPPRESS):
            self.assertEqual(SearchInterrupted(reason).reason, reason)
        for reason in (SearchSignal.CONTINUE, None, "STOP"):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                SearchInterrupted(reason)

    def test_four_completion_states_and_invalid_combinations(self):
        """四状態ごとの手と記録の組合せを構築時に検査する。

        未確定投了、完了記録と異なる手、抑制時の手の漏出を検出する。
        """
        from kaname_shogi.search.result import (
            ControlledCompletion as C,
        )
        from kaname_shogi.search.result import (
            ControlledSearchResult as R,
        )
        from kaname_shogi.search.result import (
            IterationResult,
            SearchResult,
        )

        record = IterationResult(2, SearchResult((0, 1), "B", 7, None), 10)
        empty = IterationResult(1, SearchResult((0, 0), None, 1, None), 1)
        for state, move, last in (
            (C.COMPLETE, "B", record),
            (C.NO_LEGAL_MOVE, None, None),
            (C.STOPPED, "A", None),
            (C.STOPPED, "B", record),
            (C.SUPPRESSED, None, None),
            (C.SUPPRESSED, None, record),
        ):
            value = R(state, move, last)
            self.assertEqual((value.completion, value.move), (state, move))
            self.assertIs(value.last_completed, last)
        for state, move, last in (
            (C.COMPLETE, "A", record),
            (C.COMPLETE, "B", None),
            (C.COMPLETE, None, empty),
            (C.STOPPED, None, None),
            (C.STOPPED, "A", record),
            (C.NO_LEGAL_MOVE, "A", None),
            (C.NO_LEGAL_MOVE, None, record),
            (C.SUPPRESSED, "B", record),
            ("STOPPED", "A", None),
            (C.SUPPRESSED, None, object()),
        ):
            with self.subTest(state=state, move=move), self.assertRaises(ValueError):
                R(state, move, last)

    def test_interruption_has_no_evaluation_and_is_frozen(self):
        """中断値を評価へ混ぜる欄と後から理由を書き換える経路を設けない。

        仮の評価・手・訪問数を持たせる設計変更を検出する。
        """
        from dataclasses import FrozenInstanceError

        value = SearchInterrupted(SearchSignal.STOP)
        for field in ("score", "move", "visited_nodes", "evaluate"):
            self.assertFalse(hasattr(value, field))
        with self.assertRaises(FrozenInstanceError):
            value.reason = SearchSignal.SUPPRESS

    def test_success_wrappers_and_operations_are_immutable(self):
        """準備・正常遷移・操作セットと終了結果を後から上書きしない。

        過去記録や操作を探索間で書き換える誤りを検出する。
        """
        from dataclasses import FrozenInstanceError

        from kaname_shogi.search.contracts import (
            AdvancedNode,
            ControlledSearchOperations,
            PreparedRoot,
        )
        from kaname_shogi.search.result import (
            ControlledCompletion,
            ControlledSearchResult,
        )

        node = object()
        prepared = PreparedRoot("A")
        advanced = AdvancedNode(node)
        ops = ControlledSearchOperations(None, None, None, None)
        result = ControlledSearchResult(ControlledCompletion.STOPPED, "A", None)
        self.assertIsNone(PreparedRoot(None).move)
        self.assertEqual(prepared.move, "A")
        self.assertIs(advanced.node, node)
        for obj, field in (
            (prepared, "move"),
            (advanced, "node"),
            (ops, "inspect"),
            (result, "move"),
        ):
            with self.assertRaises(FrozenInstanceError):
                setattr(obj, field, None)
