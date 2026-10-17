"""探索の評価と完了結果を表すデータ。"""

from dataclasses import dataclass

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
