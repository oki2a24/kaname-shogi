"""探索の評価と完了結果を表すデータ。"""

from dataclasses import dataclass
from enum import Enum, auto

from ..search_control import SearchSignal

# 勝敗区分を先に比較する評価データ。通常時だけ第二要素を比較する。
type Score = tuple[int, int]


@dataclass(frozen=True)
class SearchResult[M]:
    """確定した根の値・選択手・訪問回数のデータ。

    scoreは開始側視点、moveは手なし時None。visited_nodesは開始局面も含む。
    root_scoresは全幅側だけが保持する順序付き確定評価で、αβ側はNone。
    このデータ自身は局面を変更せず、未完了探索の結果を表さない。
    """

    score: Score
    move: M | None
    visited_nodes: int
    root_scores: tuple[tuple[M, Score], ...] | None


@dataclass(frozen=True)
class IterationResult[M]:
    """一つの深さの探索完了と、それまでの累計を保持するデータ。

    depthは完了した深さ、resultは今回の探索結果そのもの、
    total_visited_nodesは完了反復の訪問数の和。比較用や未完了分は含めない。
    フィールドは変更不可。任意の手型Mの中身まで凍結せず、呼出し側も
    手を変更しないことを前提とする。過去記録を最新の探索から独立させる。
    """

    depth: int
    result: SearchResult[M]
    total_visited_nodes: int


@dataclass(frozen=True)
class SearchInterrupted:
    """通常停止または抑制の理由だけを持つ、不変な中断データ。

    引数reasonはSTOP/SUPPRESSのみ。不正値はValueError、副作用はない。
    評価・手・訪問数を持たず、未完了値の採点利用を防ぐ。
    """

    reason: SearchSignal

    def __post_init__(self) -> None:
        if self.reason not in (SearchSignal.STOP, SearchSignal.SUPPRESS):
            raise ValueError("中断理由はSTOPまたはSUPPRESSが必要です")


class ControlledCompletion(Enum):
    """要求完了・手なし・通常停止・応答抑制の状態データ。"""

    COMPLETE = auto()
    NO_LEGAL_MOVE = auto()
    STOPPED = auto()
    SUPPRESSED = auto()


@dataclass(frozen=True)
class ControlledSearchResult[M]:
    """終了状態・応答候補・最後の完了記録を保持する不変データ。

    引数は四状態と手、IterationResultまたはNone。組合せ不正はValueError。
    COMPLETE/STOPPEDの手は記録があれば一致し、SUPPRESSEDの手は常にNone。
    副作用なし。合法性と要求深さの一致は探索側の前提であり、ここでは検査しない。
    """

    completion: ControlledCompletion
    move: M | None
    last_completed: IterationResult[M] | None

    def __post_init__(self) -> None:
        if not isinstance(self.completion, ControlledCompletion):
            raise ValueError("終了状態が不正です")
        last = self.last_completed
        if last is not None and not isinstance(last, IterationResult):
            raise ValueError("完了記録はIterationResultまたはNoneが必要です")
        if self.completion is ControlledCompletion.NO_LEGAL_MOVE:
            valid = self.move is None and last is None
        elif self.completion is ControlledCompletion.SUPPRESSED:
            valid = self.move is None
        else:
            valid = self.move is not None
            if self.completion is ControlledCompletion.COMPLETE:
                valid = valid and last is not None
            if last is not None:
                valid = valid and self.move == last.result.move
        if not valid:
            raise ValueError("終了状態と応答手・完了記録の組合せが不正です")
