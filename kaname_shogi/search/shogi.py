"""既存の将棋ルールと、局面非依存の探索を接続する。"""

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
from .result import Score, SearchInterrupted


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
) -> ControlledSearchOperations[Position, Move]:
    """開始側視点の将棋用制御付き操作セットを作る操作。

    perspectiveは評価の開始側。各操作は同じSearchControlを明示して受ける。
    初回準備だけ通常停止を保護し、調査・遷移では目標を適用しない。
    元盤面・持駒を変更せず、既存規則の完了／中断を別型へ変換する。
    時計原点や予算を作らず、故障はそのまま伝播する。
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
