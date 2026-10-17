"""局面操作から独立した、指定深さ探索の共有本体。"""

from .contracts import SearchOperations
from .result import Score, SearchResult


def search[N, M](
    node: N,
    depth: int,
    operations: SearchOperations[N, M],
    *,
    pruning: bool,
    preferred_move: M | None = None,
) -> SearchResult[M]:
    """操作セットで深さ優先探索し、根の値・手・訪問数を返す内部操作。

    depthはboolを除く0以上の整数。不正な深さはValueError。
    各訪問で局面調査を一度行い、終端評価を深さ打切りより優先する。
    操作の非破壊契約を前提とし、例外を隠さない。計数は実行ごとに独立。
    pruning=Trueでは未設定境界をNoneで表し、上下限が交差したら省略する。
    内部の返却値は境界の場合があるが、無境界で開始した根の値は確定する。
    同値で先行最善手を上書きせず、境界値を候補の確定値として公開しない。
    preferred_moveは根だけで先頭へ移す。根の調査後、子へ進む前に照合し、
    不在なら深さ0・終端でもValueError。Noneは指定なし専用。
    """
    if type(depth) is not int or depth < 0:
        raise ValueError("深さは0以上の整数で指定してください")
    visits = 0
    root_scores: list[tuple[M, Score]] = []

    def visit(
        current: N,
        remaining: int,
        lower: Score | None = None,
        upper: Score | None = None,
        *,
        root: bool = False,
    ) -> tuple[Score, M | None]:
        nonlocal visits
        visits += 1
        inspected = operations.inspect(current)
        moves = inspected.moves
        if root and preferred_move is not None:
            if preferred_move not in moves:
                raise ValueError("優先手は開始局面の合法手から指定してください")
            moves = (preferred_move,) + tuple(m for m in moves if m != preferred_move)
        if inspected.terminal_score is not None:
            return inspected.terminal_score, None
        if remaining == 0:
            return operations.evaluate(current), None
        best: Score | None = None
        selected: M | None = None
        for move in moves:
            value, _ = visit(
                operations.advance(current, move), remaining - 1, lower, upper
            )
            if root and not pruning:
                root_scores.append((move, value))
            if best is None or (value > best if inspected.maximizing else value < best):
                best, selected = value, move
            if pruning:
                if inspected.maximizing:
                    lower = best if lower is None else max(lower, best)
                else:
                    upper = best if upper is None else min(upper, best)
                if lower is not None and upper is not None and lower >= upper:
                    break
        assert best is not None, "非終端の局面調査は一つ以上の手を返す必要があります"
        return best, selected

    score, move = visit(node, depth, root=True)
    return SearchResult(score, move, visits, None if pruning else tuple(root_scores))
