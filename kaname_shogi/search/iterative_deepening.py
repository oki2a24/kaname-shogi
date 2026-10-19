"""同じ開始局面の深さを増やし、完了記録または最終結果を返す。"""

from collections.abc import Callable, Iterator

from ..search_control import SearchControl, SearchSignal
from . import alpha_beta, minimax
from .contracts import ControlledSearchOperations, SearchOperations
from .result import (
    ControlledCompletion,
    ControlledSearchResult,
    IterationResult,
    SearchInterrupted,
    SearchResult,
)


def _validate_max_depth(max_depth: int) -> None:
    """上限の型・範囲を実行開始前に確認する。"""
    if type(max_depth) is not int or max_depth < 1:
        raise ValueError("上限の深さは1以上の整数で指定してください")


def _validate_pruning(pruning: bool) -> None:
    """方式選択がboolかを探索・準備の開始前に確認する。"""
    if type(pruning) is not bool:
        raise ValueError("pruningはboolで指定してください")


def _iterations[M](
    max_depth: int,
    search_depth: Callable[[int, M | None], SearchResult[M] | SearchInterrupted],
    before_depth: Callable[[], SearchInterrupted | None],
) -> Iterator[IterationResult[M] | SearchInterrupted]:
    """深さ・前回手・完了累計を所有する共通反復。準備や応答選択は行わない。"""
    total = 0
    preferred = None
    for depth in range(1, max_depth + 1):
        if stopped := before_depth():
            yield stopped
            return
        result = search_depth(depth, preferred)
        if isinstance(result, SearchInterrupted):
            yield result
            return
        preferred = result.move
        total += result.visited_nodes
        yield IterationResult(depth, result, total)
        if result.move is None:
            return


def search[N, M](
    node: N,
    max_depth: int,
    operations: SearchOperations[N, M],
    *,
    pruning: bool = True,
) -> Iterator[IterationResult[M]]:
    """開始局面を深さ1から上限まで探索し、完了記録のイテレーターを返す。

    引数: nodeは開始局面、max_depthはboolを除く1以上の上限、operationsは非破壊な
    局面操作、pruningはboolでTrueが既定のαβ、Falseが全幅探索を選ぶ。
    max_depthとpruningは呼出し時に検査し、不正なら探索前にValueError。
    戻り値: 深さごとの完了記録を順に返すイテレーター。実探索は記録取得時に行う。
    副作用: nodeは変更せずoperationsを探索順に呼ぶ。操作例外はそのまま伝播する。
    前提・設計理由: 反復・前回最善手・累計の扱いは両方式で共通化し、選択した
    指定深さ探索だけを切り替える。時間制御や応答期限は保証しない。
    前回最善手は根の順序だけに使い、結果の評価は各深さで求め直す。
    手なしなら一件で終了。例外は伝播し、未完了記録は渡さない。
    累計は完了反復だけ。渡した記録と結果を変更せず最新の参照を切り替える。
    """
    _validate_max_depth(max_depth)
    _validate_pruning(pruning)
    method = alpha_beta if pruning else minimax

    def records():
        # Pythonのジェネレーターが反復間の状態を保持する。
        # 他言語なら深さ・前回手・累計を持つIterator等で同じ契約を実現する。
        for record in _iterations(
            max_depth,
            lambda depth, preferred: method.search(
                node, depth, operations, preferred_move=preferred
            ),
            lambda: None,
        ):
            assert isinstance(record, IterationResult), "停止なしの反復は中断しません"
            yield record

    return records()


def search_controlled[N, M](
    node: N,
    max_depth: int,
    operations: ControlledSearchOperations[N, M],
    control: SearchControl,
    *,
    pruning: bool = True,
) -> ControlledSearchResult[M]:
    """予備手を一度準備し、制御付き反復探索の最終結果を一件返す同期操作。

    引数: nodeは開始局面、max_depthはboolを除く1以上の上限、operationsはprepareを
    含む非破壊な操作、controlは呼出し元が所有する一局分の停止制御、pruningはboolで
    Trueが既定のαβ、Falseが全幅探索を選ぶ。上限と方式は準備前に検査する。
    戻り値: 完了・停止・抑制・合法手なしの状態、選ばれた手、最新完了記録。
    副作用: 同じ開始局面とcontrolでoperationsを呼ぶ。操作例外はそのまま伝播する。
    前提・設計理由: operationsは元局面を変更せず、準備と再調査の合法手が一致する。
    反復・予備手・停止結果の組み立ては共通化し、指定深さ探索の方式だけを切り替える。
    目標で次の深さを始めず、上限・stop中断は最新完了手または予備手を返す。
    完了確定後の通常停止で記録を取り消さず、返却直前の抑制では手をなしにする。
    準備のSTOPや手あり準備後の根の手なしは契約違反としてValueError。
    送信や制御生成は行わず、故障はそのまま伝播する。時間内応答は保証しない。
    """
    _validate_max_depth(max_depth)
    _validate_pruning(pruning)
    method = alpha_beta if pruning else minimax
    last: IterationResult[M] | None = None

    def finish(
        completion: ControlledCompletion, move: M | None
    ) -> ControlledSearchResult[M]:
        if control.check() is SearchSignal.SUPPRESS:
            completion = ControlledCompletion.SUPPRESSED
        if completion is ControlledCompletion.SUPPRESSED:
            move = None
        return ControlledSearchResult(completion, move, last)

    prepared = operations.prepare(node, control)
    if isinstance(prepared, SearchInterrupted):
        if prepared.reason is not SearchSignal.SUPPRESS:
            raise ValueError(
                "準備は通常停止を保護して手を確保するか手なしを確定する必要があります"
            )
        return finish(ControlledCompletion.SUPPRESSED, None)
    if prepared.move is None:
        return finish(ControlledCompletion.NO_LEGAL_MOVE, None)

    def before_depth() -> SearchInterrupted | None:
        signal = control.check(include_target=True)
        return None if signal is SearchSignal.CONTINUE else SearchInterrupted(signal)

    completion = ControlledCompletion.COMPLETE
    move = prepared.move
    for record in _iterations(
        max_depth,
        lambda depth, preferred: method.search_controlled(
            node, depth, operations, control, preferred_move=preferred
        ),
        before_depth,
    ):
        if isinstance(record, SearchInterrupted):
            completion = (
                ControlledCompletion.SUPPRESSED
                if record.reason is SearchSignal.SUPPRESS
                else ControlledCompletion.STOPPED
            )
            break
        if record.result.move is None:
            raise ValueError("手あり準備後の根の完了結果には合法手が必要です")
        last = record
        move = record.result.move
    return finish(completion, move)
