"""同じ開始局面で深さを増やし、完了記録を順に渡す。"""

from collections.abc import Iterator

from . import alpha_beta
from .contracts import SearchOperations
from .result import IterationResult


def search[N, M](
    node: N, max_depth: int, operations: SearchOperations[N, M]
) -> Iterator[IterationResult[M]]:
    """開始局面を深さ1から上限まで探索し、完了記録のイテレーターを返す。

    max_depthはboolを除く1以上の整数で、呼出し時に検査し不正ならValueError。
    実探索は結果の取得時だけ行い、局面を変更しない操作セットを前提とする。
    前回最善手は根の順序だけに使い、結果の評価は各深さで求め直す。
    手なしなら一件で終了。例外は伝播し、未完了記録は渡さない。
    累計は完了反復だけ。渡した記録と結果を変更せず最新の参照を切り替える。
    """
    if type(max_depth) is not int or max_depth < 1:
        raise ValueError("上限の深さは1以上の整数で指定してください")

    def iterations():
        total = 0
        preferred = None
        for depth in range(1, max_depth + 1):
            result = alpha_beta.search(
                node, depth, operations, preferred_move=preferred
            )
            preferred = result.move
            total += result.visited_nodes
            # Python固有のジェネレーターが深さ間のローカル状態を保持する。
            # 他言語へ移す場合は深さ・前回手・累計を明示保持するIterator等で
            # 同じ「完了結果を一件ずつ渡す」役割を実現する。
            yield IterationResult(depth, result, total)
            if result.move is None:
                return

    return iterations()
