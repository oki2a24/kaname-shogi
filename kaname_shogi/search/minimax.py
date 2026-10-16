"""枝刈りなしの全幅探索の入口。"""

from . import core
from .contracts import SearchOperations
from .result import SearchResult


def search[N, M](
    node: N, depth: int, operations: SearchOperations[N, M]
) -> SearchResult[M]:
    """局面nodeをdepth手まで全幅で調べ、確定評価と最初の最善手を返す。

    depthは0以上の整数。元局面は変更せず、操作セットの例外を伝える。
    結果には根候補全ての確定値と、開始局面を含む訪問回数も保持する。
    """
    return core.search(node, depth, operations, pruning=False)
