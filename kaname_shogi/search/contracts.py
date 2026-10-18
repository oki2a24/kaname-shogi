"""局面の種類に依存しない探索操作の契約。"""

from collections.abc import Callable
from dataclasses import dataclass

from ..search_control import SearchControl
from .result import Score, SearchInterrupted


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


@dataclass(frozen=True)
class PreparedRoot[M]:
    """準備完了のデータ。moveは生成順の最初の合法手、Noneは手なし確定。

    入力を変更せず、手の合法性はprepare操作の前提とする。副作用はない。
    """

    move: M | None


@dataclass(frozen=True)
class AdvancedNode[N]:
    """正常適用した次局面のデータ。nodeは元局面・他枝から独立させる。

    入力自体の深い凍結はしない。独立性はadvance操作が担保する。副作用なし。
    """

    node: N


@dataclass(frozen=True)
class ControlledSearchOperations[N, M]:
    """準備・調査・遷移・評価の操作を束ねる不変データ。

    prepareは最初の手確保/手なし確定まで通常停止を保護し、抑制だけ中断する。
    inspect/advanceは目標を適用せず保護もしない。同一の制御を毎回明示して渡す。
    evaluateは開始側視点のScoreを返す。操作は元局面を変えず故障を例外で伝える。
    データ構築自体に副作用はない。Noneを手の値としては使わない。
    """

    prepare: Callable[[N, SearchControl], PreparedRoot[M] | SearchInterrupted]
    inspect: Callable[[N, SearchControl], NodeInspection[M] | SearchInterrupted]
    advance: Callable[[N, M, SearchControl], AdvancedNode[N] | SearchInterrupted]
    evaluate: Callable[[N], Score]
