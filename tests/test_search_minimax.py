"""全幅探索の深さ、交互評価、終端と訪問を独立な数値木で確認する。"""

import unittest
from dataclasses import replace
from unittest.mock import Mock

from search_tree_support import TreeNode, depth_tree, operations, two_level

from kaname_shogi.search import minimax
from kaname_shogi.search.contracts import SearchOperations


class MinimaxTests(unittest.TestCase):
    def test_depth_changes_best_move(self):
        """二・三・四手で切る位置に応じてA/B/Aを選ぶ。

        深さのずれ、二手固定、途中の静的評価での終了を検出する。
        """
        for depth, score, move, visits in (
            (2, 1, "A", 5),
            (3, 2, "B", 7),
            (4, 3, "A", 9),
        ):
            with self.subTest(depth=depth):
                r = minimax.search(depth_tree(), depth, operations())
                self.assertEqual(
                    (r.score, r.move, r.visited_nodes), ((0, score), move, visits)
                )

    def test_minimizes_opponent_replies_and_retains_root_scores(self):
        """相手の最小値を比較し、根の確定値を順に残す。

        常時maxと候補の確定評価欠落を検出する。
        """
        seen = []
        r = minimax.search(two_level([3, 5], [4, 6]), 2, operations(seen))
        self.assertEqual((r.score, r.move, r.visited_nodes), ((0, 4), "B", 7))
        self.assertEqual(r.root_scores, (("A", (0, 3)), ("B", (0, 4))))
        self.assertEqual(seen, ["root", "A", "A0", "A1", "B", "B0", "B1"])

    def test_full_width_keeps_all_candidates(self):
        """全幅入口が両候補を最後まで調べて確定値を返す。

        αβへ誤接続して訪問数や後続根候補を欠く回帰を検出する。
        """
        seen = []
        result = minimax.search(two_level([3, 5], [-2, 10]), 2, operations(seen))
        self.assertEqual(
            (result.score, result.move, result.visited_nodes), ((0, 3), "A", 7)
        )
        self.assertEqual(result.root_scores, (("A", (0, 3)), ("B", (0, -2))))
        self.assertEqual(seen, ["root", "A", "A0", "A1", "B", "B0", "B1"])

    def test_preferred_move_only_reorders_root(self):
        """優先手は根だけを先頭へ移し、全候補の探索を保つ。

        優先手の無視、子への伝播、候補除外、真の最善手の取り違えを検出する。
        """
        root = two_level([3, 5], [-2, 10])
        seen = []
        result = minimax.search(root, 2, operations(seen), preferred_move="B")
        self.assertEqual(
            (result.score, result.move, result.visited_nodes), ((0, 3), "A", 7)
        )
        self.assertEqual(result.root_scores, (("B", (0, -2)), ("A", (0, 3))))
        self.assertEqual(seen, ["root", "B", "B0", "B1", "A", "A0", "A1"])

        tied = two_level([3, 5], [3, 4])
        self.assertEqual(
            minimax.search(tied, 2, operations(), preferred_move="B").move, "B"
        )

    def test_missing_preferred_move_fails_before_advancing(self):
        """開始局面にない優先手を子局面の作成前に拒否する。

        不正手の探索やadvance後の遅延検査を検出する。
        """
        seen = []
        advances = []
        base = operations(seen)
        invalid = SearchOperations(
            base.inspect,
            lambda node, move: advances.append(move),
            base.evaluate,
        )
        with self.assertRaises(ValueError):
            minimax.search(two_level([3], [4]), 2, invalid, preferred_move="missing")
        self.assertEqual(seen, ["root"])
        self.assertEqual(advances, [])

    def test_zero_depth_and_terminal_precedence(self):
        """終端は静的駒得より優先し、終端と深さ0では先へ進まない。

        末端での詰み無視と余分な訪問を検出する。
        """
        for depth in (0, 1, 2):
            for terminal in ((-1, 0), (1, 0)):
                with self.subTest(depth=depth, terminal=terminal):
                    node = TreeNode("end", (0, 1000000), terminal_score=terminal)
                    ops = operations()
                    advance, evaluate = (
                        Mock(side_effect=AssertionError("終端から進まない")),
                        Mock(side_effect=AssertionError("終端を静的評価しない")),
                    )
                    r = minimax.search(
                        node, depth, SearchOperations(ops.inspect, advance, evaluate)
                    )
                    self.assertEqual(
                        (r.score, r.move, r.visited_nodes, r.root_scores),
                        (terminal, None, 1, ()),
                    )
        root = replace(depth_tree(), score=(0, -7))
        r = minimax.search(root, 0, operations())
        self.assertEqual(
            (r.score, r.move, r.visited_nodes, r.root_scores), ((0, -7), None, 1, ())
        )

    def test_first_equal_best_and_invalid_depth(self):
        """同点は最初を選び、不正な深さを拒否する。

        同点で後続へ上書きする誤りとbool許容を検出する。
        """
        root = two_level([3, 5], [3, 4])
        self.assertEqual(minimax.search(root, 2, operations()).move, "A")
        root = replace(root, children=tuple(reversed(root.children)))
        self.assertEqual(minimax.search(root, 2, operations()).move, "B")
        for bad in (-1, True, 1.5):
            with self.subTest(depth=bad), self.assertRaises(ValueError):
                minimax.search(root, bad, operations())
