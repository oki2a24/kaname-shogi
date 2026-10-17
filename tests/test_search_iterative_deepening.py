"""反復の完了記録・深さ間再利用・遅延取得を確認する。"""

import unittest
from dataclasses import FrozenInstanceError, replace
from unittest.mock import patch

from search_tree_support import TreeNode, depth_tree, operations, two_level

from kaname_shogi.search import alpha_beta, iterative_deepening, minimax, shogi
from kaname_shogi.search.comparison import results_match
from kaname_shogi.search.contracts import SearchOperations
from kaname_shogi.sfen import format_sfen, parse_sfen


def changing_tree():
    """浅いA=5/B=3、深いA=−2/B=1を持つ独立数値木。"""
    root = two_level([1, -2], [2, 1])
    return replace(
        root,
        children=(
            ("A", replace(root.children[0][1], score=(0, 5))),
            ("B", replace(root.children[1][1], score=(0, 3))),
        ),
    )


class IterativeDeepeningTests(unittest.TestCase):
    def test_completed_depth_changes_best_and_accumulates(self):
        """浅い高評価を保持せず深い完了結果と累計へ更新する。

        反復省略・浅い評価の流用・今回分だけの累計を検出する。
        """
        records = list(iterative_deepening.search(changing_tree(), 2, operations()))
        self.assertEqual(
            [
                (
                    r.depth,
                    r.result.move,
                    r.result.score,
                    r.result.visited_nodes,
                    r.total_visited_nodes,
                )
                for r in records
            ],
            [(1, "A", (0, 5), 3, 3), (2, "B", (0, 1), 7, 10)],
        )

    def test_stream_is_lazy_and_validates_limit_immediately(self):
        """呼出し時に上限だけ検査し、要求された深さだけ探索する。

        遅い入力検査・先行全探索・boolの許容を検出する。
        """
        for bad in (0, -1, 1.5, True, False):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                iterative_deepening.search(changing_tree(), bad, operations())
        seen = []
        stream = iterative_deepening.search(changing_tree(), 2, operations(seen))
        self.assertEqual(seen, [])
        self.assertEqual(next(stream).depth, 1)
        self.assertEqual(seen, ["root", "A", "B"])
        self.assertEqual(next(stream).depth, 2)
        with self.assertRaises(StopIteration):
            next(stream)
        self.assertEqual(
            len(list(iterative_deepening.search(changing_tree(), 1, operations()))), 1
        )

    def test_previous_best_is_passed_to_next_depth(self):
        """前回完了の最善手を次の探索へ渡す。

        優先なし・浅い手への固定・二回前の流用を検出する。
        """
        real = alpha_beta.search
        calls = []

        def observed(node, depth, ops, *, preferred_move=None):
            calls.append((depth, preferred_move))
            return real(node, depth, ops, preferred_move=preferred_move)

        with patch.object(alpha_beta, "search", side_effect=observed):
            records = list(iterative_deepening.search(changing_tree(), 3, operations()))
        self.assertEqual(calls, [(1, None), (2, "A"), (3, "B")])
        self.assertEqual(records[-1].result.move, "B")

    def test_terminal_yields_once(self):
        """手なしは深さ1の評価を渡して終了する。

        同じ終端の不要な再探索と詰み・駒得の混同を検出する。
        """
        for score in ((-1, 0), (0, 3)):
            records = list(
                iterative_deepening.search(
                    TreeNode("end", terminal_score=score), 4, operations()
                )
            )
            self.assertEqual(len(records), 1)
            r = records[0]
            self.assertEqual(
                (
                    r.depth,
                    r.result.score,
                    r.result.move,
                    r.result.visited_nodes,
                    r.total_visited_nodes,
                ),
                (1, score, None, 1, 1),
            )

    def test_records_are_immutable_and_streams_independent(self):
        """過去記録を変更せず、二つの反復の状態を混ぜない。

        オブジェクト書換え・共有累計・前回最善手の共有・結果の不要な複製を検出する。
        """
        real = alpha_beta.search
        returned = []
        calls = []
        first_root = changing_tree()
        second_root = depth_tree()
        second_root = replace(
            second_root,
            children=(
                ("A", replace(second_root.children[0][1], score=(0, 0))),
                ("B", replace(second_root.children[1][1], score=(0, 1))),
            ),
        )

        def observed(*args, **kwargs):
            stream = "first" if args[0] is first_root else "second"
            calls.append((stream, args[1], kwargs["preferred_move"]))
            result = real(*args, **kwargs)
            returned.append(result)
            return result

        with patch.object(alpha_beta, "search", side_effect=observed):
            first = iterative_deepening.search(first_root, 2, operations())
            second = iterative_deepening.search(second_root, 2, operations())
            one = next(first)
            self.assertIs(one.result, returned[0])
            other = next(second)
            two = next(first)
            other_two = next(second)
        self.assertEqual(
            calls,
            [
                ("first", 1, None),
                ("second", 1, None),
                ("first", 2, "A"),
                ("second", 2, "B"),
            ],
        )
        self.assertEqual(
            (one.depth, one.result.move, one.total_visited_nodes), (1, "A", 3)
        )
        self.assertEqual(
            (two.depth, two.result.move, two.total_visited_nodes), (2, "B", 10)
        )
        self.assertEqual(
            (
                other.depth,
                other.result.move,
                other.total_visited_nodes,
                other_two.total_visited_nodes,
            ),
            (1, "B", 3, 8),
        )
        self.assertIsNot(one, two)
        self.assertIsNot(one.result, two.result)
        for obj, field, value in ((one, "depth", 99), (one.result, "move", "B")):
            with self.assertRaises(FrozenInstanceError):
                setattr(obj, field, value)

    def test_interruption_keeps_previous_record(self):
        """深い探索の故障でも取得済みの完了記録を変えない。

        未完了記録の公開・例外の隠蔽を検出する。
        """
        base = operations()
        for error in (KeyboardInterrupt, ValueError):
            roots = 0

            def inspect(node, error=error):
                nonlocal roots
                if node.label == "root":
                    roots += 1
                    if roots == 3:
                        raise error("探索中断")
                return base.inspect(node)

            stream = iterative_deepening.search(
                changing_tree(),
                3,
                SearchOperations(inspect, base.advance, base.evaluate),
            )
            one, two = next(stream), next(stream)
            with self.assertRaises(error):
                next(stream)
            self.assertEqual(
                (two.depth, two.result.move, two.total_visited_nodes), (2, "B", 10)
            )
            self.assertEqual(one.result.score, (0, 5))
            with self.assertRaises(StopIteration):
                next(stream)

    def test_ordering_can_reduce_or_increase_work(self):
        """浅い順序による今回分の削減と増加を独立な木で確認する。

        常に削減するとの仮定・前回手の無視・累計の過小表示を検出する。
        """
        for values, static, expected in (
            (([1, -2], [2, 1]), (3, 5), (7, 6, 9)),
            (([3, 5], [-2, 10]), (3, 5), (6, 7, 10)),
        ):
            root = two_level(*values)
            root = replace(
                root,
                children=tuple(
                    (move, replace(child, score=(0, score)))
                    for (move, child), score in zip(root.children, static, strict=True)
                ),
            )
            records = list(iterative_deepening.search(root, 2, operations()))
            standalone = alpha_beta.search(root, 2, operations())
            self.assertEqual(
                (
                    standalone.visited_nodes,
                    records[1].result.visited_nodes,
                    records[1].total_visited_nodes,
                ),
                expected,
            )
            self.assertEqual(
                records[1].result.score, minimax.search(root, 2, operations()).score
            )

    def test_shogi_cases_match_full_search_without_mutation(self):
        """将棋の先後・駒取り・成り・打ち・終端を反復入口へ接続する。

        根の局面変更・視点違い・将棋用操作の取り違えを検出する。
        """
        for sfen in (
            "8k/9/9/9/9/9/9/9/K8 b - 1",
            "8k/9/9/9/9/9/9/9/K8 w - 1",
            "8k/9/4g4/4p4/4RS3/9/9/9/K8 b - 1",
            "8k/9/9/9/3sr4/4P4/4G4/9/K8 w - 1",
            "8k/9/9/7P1/9/9/9/9/K8 b - 1",
            "8k/9/9/9/9/9/9/9/K8 b P 1",
            "3pkp3/3p1p3/4RG3/9/9/9/9/9/K8 b - 1",
            "9/9/9/9/9/9/9/9/9 b - 1",
        ):
            with self.subTest(sfen=sfen):
                sf = parse_sfen(sfen)
                ops = shogi.make_operations(sf.position.side_to_move)
                for record in iterative_deepening.search(sf.position, 2, ops):
                    full = minimax.search(sf.position, record.depth, ops)
                    self.assertTrue(results_match(full, record.result))
                    self.assertEqual(format_sfen(sf), sfen)
