"""局面操作から独立した、指定深さ探索の共有本体。"""

from .contracts import SearchOperations
from .result import Score, SearchResult


def search[N, M](
    node: N,
    depth: int,
    operations: SearchOperations[N, M],
    *,
    pruning: bool,
) -> SearchResult[M]:
    """操作セットで深さ優先探索し、根の値・手・訪問数を返す内部操作。

    depthはboolを除く0以上の整数。不正な深さはValueError。
    各訪問で局面調査を一度行い、終端評価を深さ打切りより優先する。
    操作の非破壊契約を前提とし、例外を隠さない。計数は実行ごとに独立。
    """
    if type(depth) is not int or depth < 0:
        raise ValueError("深さは0以上の整数で指定してください")
    visits = 0
    root_scores: list[tuple[M, Score]] = []

    def visit(current: N, remaining: int, *, root: bool = False):
        nonlocal visits
        visits += 1
        inspected = operations.inspect(current)
        if inspected.terminal_score is not None:
            return inspected.terminal_score, None
        if remaining == 0:
            return operations.evaluate(current), None
        best: Score | None = None
        selected: M | None = None
        for move in inspected.moves:
            value, _ = visit(operations.advance(current, move), remaining - 1)
            if root:
                root_scores.append((move, value))
            if best is None or (value > best if inspected.maximizing else value < best):
                best, selected = value, move
        assert best is not None, "非終端の局面調査は一つ以上の手を返す必要があります"
        return best, selected

    score, move = visit(node, depth, root=True)
    return SearchResult(score, move, visits, tuple(root_scores))
