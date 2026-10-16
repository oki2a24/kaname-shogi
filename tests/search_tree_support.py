"""独立期待値を持つ数値木。探索は製品の本体だけを使う。"""

from dataclasses import dataclass

from kaname_shogi.search.contracts import NodeInspection, SearchOperations
from kaname_shogi.search.result import Score


@dataclass(frozen=True)
class TreeNode:
    """局面ラベル・静的値・手番・子を保持する確認用データ。"""

    label: str
    score: Score = (0, 0)
    maximizing: bool = True
    children: tuple[tuple[str, TreeNode], ...] = ()
    terminal_score: Score | None = None


def operations(seen=None):
    """節点の情報を返すだけの操作セットを作り、任意の訪問履歴へ追記する。"""

    def inspect(node):
        if seen is not None:
            seen.append(node.label)
        terminal = node.terminal_score
        if not node.children and terminal is None:
            terminal = node.score
        return NodeInspection(
            tuple(m for m, _ in node.children), node.maximizing, terminal
        )

    return SearchOperations(
        inspect,
        lambda node, move: dict(node.children)[move],
        lambda node: node.score,
    )


def two_level(a, b, *, maximizing=True):
    """二枝の木を作る。期待する探索値は呼出し側のリテラルで与える。"""

    def branch(label, values):
        return TreeNode(
            label,
            maximizing=not maximizing,
            children=tuple(
                (str(i), TreeNode(f"{label}{i}", (0, value)))
                for i, value in enumerate(values)
            ),
        )

    return TreeNode(
        "root",
        maximizing=maximizing,
        children=(("A", branch("A", a)), ("B", branch("B", b))),
    )


def depth_tree():
    """深さ2/3/4でA/B/Aを選ぶ、独立値を置いた木を作る。"""

    def branch(label, scores):
        end = TreeNode(label + "3", (0, scores[2]))
        middle = TreeNode(label + "2", (0, scores[1]), False, (("next", end),))
        first = TreeNode(label + "1", (0, scores[0]), True, (("next", middle),))
        return TreeNode(label, maximizing=False, children=(("next", first),))

    return TreeNode(
        "root",
        children=(("A", branch("A", (1, -4, 3))), ("B", branch("B", (0, 2, -1)))),
    )
