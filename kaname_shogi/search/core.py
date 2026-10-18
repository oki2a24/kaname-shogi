"""局面操作から独立した、指定深さ探索の共有本体。"""

from ..search_control import SearchControl, SearchSignal
from .contracts import (
    AdvancedNode,
    ControlledSearchOperations,
    PreparedRoot,
    SearchOperations,
)
from .result import Score, SearchInterrupted, SearchResult


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
    adapted = ControlledSearchOperations(
        lambda current, control: PreparedRoot(None),
        lambda current, control: operations.inspect(current),
        lambda current, move, control: AdvancedNode(operations.advance(current, move)),
        operations.evaluate,
    )
    result = _search(
        node, depth, adapted, None, pruning=pruning, preferred_move=preferred_move
    )
    assert isinstance(result, SearchResult), "停止なしの探索は中断しません"
    return result


def search_controlled[N, M](
    node: N,
    depth: int,
    operations: ControlledSearchOperations[N, M],
    control: SearchControl,
    *,
    pruning: bool,
    preferred_move: M | None = None,
) -> SearchResult[M] | SearchInterrupted:
    """同じ再帰本体で制御付き指定深さ探索を行う内部操作。

    深さはboolを除く0以上、制御は呼出し元の一回分。目標・初手保護を適用しない。
    完了した根の値だけを公開し、中断に評価を付けず返す。元局面を変更せず故障を伝播。
    """
    return _search(
        node, depth, operations, control, pruning=pruning, preferred_move=preferred_move
    )


def _search[N, M](
    node: N,
    depth: int,
    operations: ControlledSearchOperations[N, M],
    control: SearchControl | None,
    *,
    pruning: bool,
    preferred_move: M | None = None,
) -> SearchResult[M] | SearchInterrupted:
    """停止なし／制御付きを共有する唯一の再帰・採点・枝刈り本体。"""
    if type(depth) is not int or depth < 0:
        raise ValueError("深さは0以上の整数で指定してください")
    visits = 0
    root_scores: list[tuple[M, Score]] = []

    def interrupted() -> SearchInterrupted | None:
        if control is None:
            return None
        signal = control.check()
        return None if signal is SearchSignal.CONTINUE else SearchInterrupted(signal)

    def visit(
        current: N,
        remaining: int,
        lower: Score | None = None,
        upper: Score | None = None,
        *,
        root: bool = False,
    ) -> tuple[Score, M | None] | SearchInterrupted:
        nonlocal visits
        visits += 1
        if stopped := interrupted():
            return stopped
        inspected = operations.inspect(current, control)
        if isinstance(inspected, SearchInterrupted):
            return inspected
        if stopped := interrupted():
            return stopped
        moves = inspected.moves
        if root and preferred_move is not None:
            if preferred_move not in moves:
                raise ValueError("優先手は開始局面の合法手から指定してください")
            moves = (preferred_move,) + tuple(m for m in moves if m != preferred_move)
        if inspected.terminal_score is not None:
            return inspected.terminal_score, None
        if remaining == 0:
            if stopped := interrupted():
                return stopped
            score = operations.evaluate(current)
            if stopped := interrupted():
                return stopped
            return score, None
        best: Score | None = None
        selected: M | None = None
        for move in moves:
            if stopped := interrupted():
                return stopped
            advanced = operations.advance(current, move, control)
            if isinstance(advanced, SearchInterrupted):
                return advanced
            if stopped := interrupted():
                return stopped
            child = visit(advanced.node, remaining - 1, lower, upper)
            if isinstance(child, SearchInterrupted):
                return child
            if stopped := interrupted():
                return stopped
            value, _ = child
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

    result = visit(node, depth, root=True)
    if isinstance(result, SearchInterrupted):
        return result
    if stopped := interrupted():
        return stopped
    score, move = result
    return SearchResult(score, move, visits, None if pruning else tuple(root_scores))
