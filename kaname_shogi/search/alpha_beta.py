"""αβ枝刈り付きの指定深さ探索の入口。"""

from . import core
from .contracts import SearchOperations
from .result import SearchResult


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
