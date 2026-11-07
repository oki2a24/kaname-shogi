"""既存の将棋ルールと、局面非依存の探索を接続する。"""

from dataclasses import replace

from ..evaluation import material_balance
from ..model import Position, Side
from ..move import Move
from ..movegen import (
    first_legal_move_controlled,
    is_in_check,
    legal_moves,
    legal_moves_controlled,
    position_after_move,
    position_after_move_controlled,
)
from ..search_control import SearchControl, SearchSignal
from .contracts import (
    AdvancedNode,
    ControlledSearchOperations,
    NodeInspection,
    PreparedRoot,
    SearchOperations,
)
from .diagnostics import SearchCounters
from .quiescence import search as quiescence_search
from .result import QuiescenceLimit, Score, SearchInterrupted


def make_operations(perspective: Side) -> SearchOperations[Position, Move]:
    """開始側perspectiveに視点を固定した将棋用操作セットを返す。

    局面は引数として受け取り、元局面を変更しない。合法手生成と王手確認は
    既存規則へ委譲し、非終端の合法手を再利用する。履歴による終局は扱わない。
    各操作の例外は伝播し、探索時間制御や入出力を行わない。
    """

    def evaluate(position: Position) -> Score:
        return _evaluate(position, perspective)

    def inspect(position: Position) -> NodeInspection[Move]:
        moves = legal_moves(position)
        return _inspection(position, moves, perspective)

    return SearchOperations(inspect, position_after_move, evaluate)


def _evaluate(position: Position, perspective: Side) -> Score:
    """旧・制御付き操作に共通の開始側固定の静的評価。"""
    return 0, material_balance(position, perspective)


def _inspection(
    position: Position, moves: tuple[Move, ...], perspective: Side
) -> NodeInspection[Move]:
    """生成済みの手から開始側の役割と終端値を共通に決める。"""
    maximizing = position.side_to_move == perspective
    if moves:
        return NodeInspection(moves, maximizing, None)
    score = (
        (-1 if maximizing else 1, 0)
        if is_in_check(position.board, position.side_to_move)
        else _evaluate(position, perspective)
    )
    return NodeInspection((), maximizing, score)


def _interrupted(control: SearchControl) -> SearchInterrupted:
    """将棋処理の未完了を保持し、後から来た抑制を優先する。"""
    reason = (
        SearchSignal.SUPPRESS
        if control.check() is SearchSignal.SUPPRESS
        else SearchSignal.STOP
    )
    return SearchInterrupted(reason)


def make_controlled_operations(
    perspective: Side,
    *,
    counters: SearchCounters | None = None,
) -> ControlledSearchOperations[Position, Move]:
    """開始側視点の将棋用制御付き操作セットを作る操作。

    引数:
        perspective: 静的評価を固定する開始側。
        counters: 通常のinspect入口を数える任意データ。Noneなら記録しない。

    戻り値:
        同じSearchControlで準備・合法手調査・遷移を行う操作セット。

    副作用:
        操作セットの構築ではなし。使用時は任意計数だけを更新し、局面は変更しない。
    前提条件・設計理由:
        初回準備だけ通常停止を保護し、調査・遷移では目標を適用しない。
        予備手準備と合法手生成内部の試し局面は通常ノードとして数えず、
        実際にinspect操作へ入った回数だけを記録する。時計原点や予算を作らず、
        既存規則の完了／中断を別型へ変換し、故障はそのまま伝播する。
    """

    def prepare(
        position: Position, control: SearchControl
    ) -> PreparedRoot[Move] | SearchInterrupted:
        result = first_legal_move_controlled(
            position, control=control, protect_first_legal=True
        )
        if not result.completed:
            return _interrupted(control)
        return PreparedRoot(result.moves[0] if result.moves else None)

    def inspect(
        position: Position, control: SearchControl
    ) -> NodeInspection[Move] | SearchInterrupted:
        if counters is not None:
            counters.normal_nodes += 1
        result = legal_moves_controlled(
            position, control=control, include_target=False, protect_first_legal=False
        )
        if not result.completed:
            return _interrupted(control)
        return _inspection(position, result.moves, perspective)

    def advance(
        position: Position, move: Move, control: SearchControl
    ) -> AdvancedNode[Position] | SearchInterrupted:
        result = position_after_move_controlled(position, move, control=control)
        if not result.completed:
            return _interrupted(control)
        return AdvancedNode(result.position)

    return ControlledSearchOperations(
        prepare,
        inspect,
        advance,
        lambda position: _evaluate(position, perspective),
    )


def make_quiescence_operations(
    perspective: Side,
    additional_depth: int,
    *,
    counters: SearchCounters | None = None,
) -> ControlledSearchOperations[Position, Move]:
    """指定深さの静止探索を通常探索の末端へ接続した操作セットを返す。

    引数:
        perspective: 評価の開始側。通常探索と末端探索で視点を固定する。
        additional_depth: 末端から追加する手数。boolを除く0以上の整数。
        counters: 通常調査と静止探索呼出しを分けて記録する任意データ。

    戻り値:
        既存の合法手・遷移・駒得評価へ委譲し、深さ0で静止探索を行う操作セット。

    副作用:
        操作セットの構築では局面・制御・時計を変更しない。実行時は渡された
        SearchControlに従い、入力局面を直接変更しない。
    前提条件:
        追加深さ0は境界ケースとして許可する。王手なしは静的評価を返し、王手中は
        合法回避を一手として数える。対局・時計予算は呼出し元が用意する。
    """
    if type(additional_depth) is not int or additional_depth < 0:
        raise ValueError("追加深さは0以上の整数で指定してください")

    operations = make_controlled_operations(perspective, counters=counters)
    quiescence_operations = make_controlled_operations(perspective)

    def search_leaf(
        position: Position,
        inspected: NodeInspection[Move],
        lower: Score | None,
        upper: Score | None,
        control: SearchControl,
    ) -> Score | SearchInterrupted | QuiescenceLimit:
        return quiescence_search(
            position,
            inspected,
            additional_depth,
            lower,
            upper,
            control,
            quiescence_operations,
            counters=counters,
        )

    return replace(operations, search_leaf=search_leaf)
