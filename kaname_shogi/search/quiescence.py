"""将棋局面の静止探索を行う。"""

from ..model import Position
from ..move import BoardMove, Move
from ..movegen import is_in_check
from ..search_control import SearchControl, SearchSignal
from .contracts import ControlledSearchOperations, NodeInspection
from .diagnostics import SearchCounters
from .result import QuiescenceLimit, Score, SearchInterrupted


def search(
    position: Position,
    inspected: NodeInspection[Move],
    remaining: int,
    lower: Score | None,
    upper: Score | None,
    control: SearchControl,
    operations: ControlledSearchOperations[Position, Move],
    *,
    counters: SearchCounters | None = None,
) -> Score | SearchInterrupted | QuiescenceLimit:
    """調査済みの合法手を使い、静止局面まで捕獲または王手回避を読む。

    引数:
        position: 評価する局面。再帰の各枝は遷移操作で独立に作る。
        inspected: 現局面の合法手と終端評価。入口では通常探索が行った調査を再利用する。
        remaining: 現局面から追加できる最大手数。boolを除く0以上の整数。
        lower: 呼出し元から引き継ぐ開始側視点のα下限。未設定はNone。
        upper: 呼出し元から引き継ぐ開始側視点のβ上限。未設定はNone。
        control: 通常探索と共有する停止・抑制の制御。
        operations: 同じ評価視点を使う将棋用の制御付き局面操作。
        counters: 呼出し回数を記録する任意データ。Noneなら計数しない。

    戻り値:
        完了評価、通常停止・抑制、または王手中の追加上限未完了。

    副作用:
        局面を直接変更しない。時計・制御は渡された操作を通じて確認する。
    前提条件:
        inspectedはpositionに対する合法手調査結果で、operationsは同じ評価視点を
        使う。王手なしの上限0では静的評価、王手中の上限0では合法回避がなければ
        詰み、あれば未完了とするため、上限と終端を区別する。
    """
    if type(remaining) is not int or remaining < 0:
        raise ValueError("静止探索の追加深さは0以上の整数が必要です")
    if counters is not None:
        counters.quiescence_calls += 1
    if stopped := _interrupted(control):
        return stopped
    if inspected.terminal_score is not None:
        return inspected.terminal_score
    checked = is_in_check(position.board, position.side_to_move)
    if stopped := _interrupted(control):
        return stopped
    if checked and remaining == 0:
        return QuiescenceLimit()

    if checked:
        best: Score | None = None
        candidates = inspected.moves
    else:
        best = operations.evaluate(position)
        if stopped := _interrupted(control):
            return stopped
        if remaining == 0:
            return best
        if inspected.maximizing:
            if upper is not None and best >= upper:
                return best
            lower = best if lower is None else max(lower, best)
        else:
            if lower is not None and best <= lower:
                return best
            upper = best if upper is None else min(upper, best)
        capture_candidates = []
        for move in inspected.moves:
            if stopped := _interrupted(control):
                return stopped
            if not isinstance(move, BoardMove):
                continue
            captured = position.board.piece_at(move.destination)
            if captured is not None and captured.side is not position.side_to_move:
                capture_candidates.append(move)
        candidates = tuple(capture_candidates)
        if stopped := _interrupted(control):
            return stopped
        if not candidates:
            return best

    for move in candidates:
        if stopped := _interrupted(control):
            return stopped
        advanced = operations.advance(position, move, control)
        if stopped := _interrupted(control):
            return stopped
        if isinstance(advanced, SearchInterrupted):
            return advanced
        child_inspected = operations.inspect(advanced.node, control)
        if stopped := _interrupted(control):
            return stopped
        if isinstance(child_inspected, SearchInterrupted):
            return child_inspected
        child = search(
            advanced.node,
            child_inspected,
            remaining - 1,
            lower,
            upper,
            control,
            operations,
            counters=counters,
        )
        if isinstance(child, (SearchInterrupted, QuiescenceLimit)):
            return child
        if stopped := _interrupted(control):
            return stopped
        if best is None or (child > best if inspected.maximizing else child < best):
            best = child
        if inspected.maximizing:
            lower = best if lower is None else max(lower, best)
        else:
            upper = best if upper is None else min(upper, best)
        if lower is not None and upper is not None and lower >= upper:
            break

    if best is None:
        raise ValueError("王手局面の合法な回避手が必要です")
    return best


def _interrupted(control: SearchControl) -> SearchInterrupted | None:
    """同じ制御から停止・抑制を読み、抑制優先の理由にする。"""
    signal = control.check()
    return None if signal is SearchSignal.CONTINUE else SearchInterrupted(signal)
