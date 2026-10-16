"""αβの両側の枝刈り・同点境界・根の確定値を確認する。"""

import unittest
from dataclasses import replace

from search_tree_support import TreeNode, depth_tree, operations, two_level

from kaname_shogi.search import alpha_beta, minimax


class AlphaBetaTests(unittest.TestCase):
    def test_prunes_minimizing_branch(self):
        """相手の応手が根の基準以下なら残りを読まない。

        境界を子へ渡さない、刈った局面を訪問に数える誤りを検出する。
        """
        root = two_level([3, 5], [-2, 10])
        full = minimax.search(root, 2, operations())
        seen = []
        r = alpha_beta.search(root, 2, operations(seen))
        self.assertEqual((full.score, full.move, full.visited_nodes), ((0, 3), "A", 7))
        self.assertEqual((r.score, r.move, r.visited_nodes), ((0, 3), "A", 6))
        self.assertIsNone(r.root_scores)
        self.assertNotIn("B1", seen)

    def test_prunes_maximizing_branch(self):
        """最大側でも上限を超えた後の葉を調べない。

        最小側しか切らない、内部で境界を引き継がない誤りを検出する。
        """
        inner = two_level([2, 4], [5, 10], maximizing=False)
        for wrapped in (False, True):
            root = TreeNode("outer", children=(("only", inner),)) if wrapped else inner
            depth = 3 if wrapped else 2
            seen = []
            r = alpha_beta.search(root, depth, operations(seen))
            f = minimax.search(root, depth, operations())
            self.assertEqual(
                (r.score, r.move, r.visited_nodes),
                ((0, 4), "only" if wrapped else "A", 7 if wrapped else 6),
            )
            self.assertEqual(f.visited_nodes, 8 if wrapped else 7)
            self.assertNotIn("B1", seen)

    def test_equal_bound_does_not_replace_exact_best(self):
        """同点の上限値で、実際は劣る後続候補を選ばない。

        等号枝刈りの欠落と同点上書きを区別して検出する。
        """
        root = two_level([3, 5], [3, -2])
        r = alpha_beta.search(root, 2, operations())
        f = minimax.search(root, 2, operations())
        self.assertEqual((r.score, r.move, r.visited_nodes), ((0, 3), "A", 6))
        self.assertEqual(f.root_scores, (("A", (0, 3)), ("B", (0, -2))))

    def test_true_ties_and_no_cutoff(self):
        """真の同点は最初を選び、刈れない木も正しく読む。

        一律の省略、同点候補欠落を検出する。
        """
        root = two_level([3, 5], [3, 4])
        for first in ("A", "B"):
            self.assertEqual(alpha_beta.search(root, 2, operations()).move, first)
            root = replace(root, children=tuple(reversed(root.children)))
        r = alpha_beta.search(two_level([3, 5], [4, 6]), 2, operations())
        self.assertEqual((r.score, r.move, r.visited_nodes), ((0, 4), "B", 7))

    def test_shared_depth_and_terminal_contract(self):
        """αβ入口も深さと終端・入力検査の契約を守る。

        全幅だけに検査を置く誤りを検出する。
        """
        for depth, score, move, visits in (
            (2, 1, "A", 5),
            (3, 2, "B", 7),
            (4, 3, "A", 9),
        ):
            r = alpha_beta.search(depth_tree(), depth, operations())
            self.assertEqual(
                (r.score, r.move, r.visited_nodes), ((0, score), move, visits)
            )
        for depth in (0, 2):
            r = alpha_beta.search(
                TreeNode("loss", (0, 1000000), terminal_score=(-1, 0)),
                depth,
                operations(),
            )
            self.assertEqual(
                (r.score, r.move, r.visited_nodes, r.root_scores),
                ((-1, 0), None, 1, None),
            )
        for bad in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                alpha_beta.search(depth_tree(), bad, operations())
