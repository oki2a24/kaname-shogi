"""枝刈りなしの全幅探索の入口。"""

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
    """局面nodeをdepth手まで全幅で調べ、確定評価と最初の最善手を返す。

    引数: nodeは開始局面、depthはboolを除く0以上の整数、operationsは非破壊な
    局面操作、preferred_moveは指定時に根の先頭へ移す合法手。子では並べ替えない。
    戻り値: 根の確定評価・最善手・訪問数・全根候補の確定値を持つSearchResult。
    副作用: nodeを変更しない。operationsを探索順に呼び、操作例外はそのまま伝える。
    前提・設計理由: 深さ0でもpreferred_moveを指定した場合は合法性を検査する。
    全幅として全候補の確定値を返すため、共有本体へ枝刈り無効を指定する。
    """
    return core.search(
        node, depth, operations, pruning=False, preferred_move=preferred_move
    )


def search_controlled[N, M](
    node: N,
    depth: int,
    operations: ControlledSearchOperations[N, M],
    control: SearchControl,
    *,
    preferred_move: M | None = None,
) -> SearchResult[M] | SearchInterrupted:
    """同じ共有本体で全幅指定深さ探索を行い、完了値か中断理由を返す。

    引数: nodeとdepthはsearchと同じ契約、operationsはprepareを含む制御付き操作、
    controlは呼出し元が所有する一回分の停止制御、preferred_moveは任意の合法な根の手。
    戻り値: 完了時はSearchResult、中断時は評価や途中候補を持たないSearchInterrupted。
    副作用: nodeを変更せず、operationsを呼ぶ。停止確認・時計確認はcontrolへ委譲し、
    操作例外を変換せず伝える。prepareは呼ばない。
    前提・設計理由: depthはboolを除く0以上の整数。全幅探索では根候補を刈らないため、
    結果に全根候補の確定値が必要である。
    """
    return core.search_controlled(
        node,
        depth,
        operations,
        control,
        pruning=False,
        preferred_move=preferred_move,
    )
