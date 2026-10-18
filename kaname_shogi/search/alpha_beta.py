"""αβ枝刈り付きの指定深さ探索の入口。"""

from ..search_control import SearchControl
from . import core
from .contracts import ControlledSearchOperations, SearchOperations
from .result import SearchInterrupted, SearchResult


def search[N, M](
    node: N,
    depth: int,
    operations: SearchOperations[N, M],
    *,
    preferred_move: M | None = None,
) -> SearchResult[M]:
    """局面を指定深さまでαβ探索し、確定した根の値と最初の最善手を返す。

    depthは0以上の整数。入力を変更せず操作の例外を伝える。
    訪問は開始局面を含み、候補ごとの境界値を確定値として公開しない。
    preferred_moveは根の合法手に限り、その手だけを先頭へ移す。
    Noneは指定なし。不在なら子を探索せずValueError。子の手順序は変えない。
    """
    return core.search(
        node, depth, operations, pruning=True, preferred_move=preferred_move
    )


def search_controlled[N, M](
    node: N,
    depth: int,
    operations: ControlledSearchOperations[N, M],
    control: SearchControl,
    *,
    preferred_move: M | None = None,
) -> SearchResult[M] | SearchInterrupted:
    """指定深さのαβ完了結果または中断を返す同期操作。

    depthはbool以外の0以上。優先手は根の調査完了後に照合する。
    同一制御で上限・通常停止・抑制だけを確認し、目標と予備手保護は使わない。
    操作の非破壊契約を前提とし、故障をそのまま伝える。準備と反復は行わない。
    """
    return core.search_controlled(
        node, depth, operations, control, pruning=True, preferred_move=preferred_move
    )
