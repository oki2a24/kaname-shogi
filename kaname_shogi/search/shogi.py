"""既存の将棋ルールと、局面非依存の探索を接続する。"""

from ..evaluation import material_balance
from ..model import Position, Side
from ..move import Move
from ..movegen import is_in_check, legal_moves, position_after_move
from .contracts import NodeInspection, SearchOperations
from .result import Score


def make_operations(perspective: Side) -> SearchOperations[Position, Move]:
    """開始側perspectiveに視点を固定した将棋用操作セットを返す。

    局面は引数として受け取り、元局面を変更しない。合法手生成と王手確認は
    既存規則へ委譲し、非終端の合法手を再利用する。履歴による終局は扱わない。
    各操作の例外は伝播し、探索時間制御や入出力を行わない。
    """

    def evaluate(position: Position) -> Score:
        return 0, material_balance(position, perspective)

    def inspect(position: Position) -> NodeInspection[Move]:
        moves = legal_moves(position)
        maximizing = position.side_to_move == perspective
        if moves:
            return NodeInspection(moves, maximizing, None)
        score = (
            (-1 if maximizing else 1, 0)
            if is_in_check(position.board, position.side_to_move)
            else evaluate(position)
        )
        return NodeInspection((), maximizing, score)

    return SearchOperations(inspect, position_after_move, evaluate)
