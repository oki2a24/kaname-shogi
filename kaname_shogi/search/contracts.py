"""局面の種類に依存しない探索操作の契約。"""

from collections.abc import Callable
from dataclasses import dataclass

from .result import Score


@dataclass(frozen=True)
class NodeInspection[M]:
    """順序付き手・最大側か否か・終端評価を表す調査結果データ。

    継続時は手がありterminal_scoreはNone。終端時は手が空で評価がある。
    終端評価は静的評価より優先される。局面や手を変更しない。
    """

    moves: tuple[M, ...]
    maximizing: bool
    terminal_score: Score | None


@dataclass(frozen=True)
class SearchOperations[N, M]:
    """局面調査・独立した次局面作成・静的評価の操作を束ねるデータ。

    inspectは副作用なく同じ手順序を返す。advanceは元局面と他枝を変えず、
    evaluateは探索を行わない。各操作の例外は探索からそのまま伝える。
    """

    inspect: Callable[[N], NodeInspection[M]]
    advance: Callable[[N, M], N]
    evaluate: Callable[[N], Score]
