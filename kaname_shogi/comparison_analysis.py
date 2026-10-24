"""比較結果を二局一組で集計し、得点区間を計算する。"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from .comparison import GameEndReason
from .movegen import MoveSelectionPolicy

_WINNING_REASONS = {
    GameEndReason.CHECKMATE,
    GameEndReason.NO_LEGAL_MOVE,
    GameEndReason.PERPETUAL_CHECK_LOSS,
}
_PURPOSES = {"pilot", "confirmation"}
CONFIDENCE_LEVEL = 0.95
_DECISION_BOUNDARY = 0.5
_HOEFFDING_LOG_TERM = math.log(40)


@dataclass(frozen=True)
class PairScore:
    """一組の候補方式得点の下限・上限平均を表す。

    引数:
        lower: 二局の候補得点下限の正確な平均。
        upper: 二局の候補得点上限の正確な平均。

    戻り値:
        0以上1以下で順序が正しい区間を保持する変更不可データ。

    例外:
        ValueError: Fraction以外、範囲外、またはlowerがupperを超える場合。

    副作用:
        なし。

    前提条件:
        端点は候補方式視点の値であり、浮動小数へ丸める前の正確な分数を保持する。
    """

    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        if not isinstance(self.lower, Fraction) or not isinstance(self.upper, Fraction):
            raise ValueError("組得点はFractionで指定してください")
        if not Fraction(0) <= self.lower <= self.upper <= Fraction(1):
            raise ValueError("組得点区間は0以上1以下で順序どおりにしてください")


@dataclass(frozen=True)
class ScoreAnalysis:
    """得点平均・区間・判定を保持する分析結果。

    引数:
        pairs: 集計対象となった先後交換の組数。
        lower_mean/upper_mean: 各組平均の下限・上限を組間平均した正確なFraction。
        radius: 95% Hoeffding半径。
        lower/upper: [0,1]へ切り詰めた得点率区間。
        decision: pilotの参考表示、またはconfirmationの三値判定。

    戻り値:
        集計数、丸め前平均、区間、判定を保持する変更不可データ。

    副作用:
        なし。

    前提条件:
        作成側は全組を一度だけ含め、局面別や中間時点の反復判定と混同しない。
    """

    pairs: int
    lower_mean: Fraction
    upper_mean: Fraction
    radius: float
    lower: float
    upper: float
    decision: str


def game_score_bounds(
    reason: GameEndReason,
    winner_policy: MoveSelectionPolicy | None,
    candidate: MoveSelectionPolicy,
) -> tuple[Fraction, Fraction]:
    """一局の候補方式得点上下限を返す。

    引数:
        reason: 比較対局の排他的終局理由。
        winner_policy: 勝者が定まる場合の方式。それ以外はNone。
        candidate: 一局の得点を計算する候補方式。

    戻り値:
        候補勝ちは(1, 1)、候補負けは(0, 0)、通常千日手は(1/2, 1/2)、
        上限または双方連続王手の未裁定は(0, 1)。

    例外:
        ValueError: 不明な終局、勝者と終局理由の不一致、中断または故障の場合。

    副作用:
        なし。与えられた終局情報だけを使う。

    前提条件:
        winner_policyは棋譜終局情報から確定した勝者方式で、先後ではなく方式視点へ
        勝敗を写した値である。
    """
    if not isinstance(reason, GameEndReason):
        raise ValueError("比較の終局理由が不明です")
    if not isinstance(candidate, MoveSelectionPolicy):
        raise ValueError("候補方式が不明です")
    if winner_policy is not None and not isinstance(winner_policy, MoveSelectionPolicy):
        raise ValueError("勝者方式が不明です")

    if reason in _WINNING_REASONS:
        if winner_policy is None:
            raise ValueError("勝敗が決まる終局には勝者方式が必要です")
        score = Fraction(1) if winner_policy is candidate else Fraction(0)
        return score, score
    if winner_policy is not None:
        raise ValueError("勝敗が決まらない終局に勝者方式を指定できません")
    if reason is GameEndReason.REPETITION:
        return Fraction(1, 2), Fraction(1, 2)
    if reason in {
        GameEndReason.PLY_LIMIT,
        GameEndReason.UNRESOLVED_DOUBLE_PERPETUAL_CHECK,
    }:
        return Fraction(0), Fraction(1)
    if reason in {GameEndReason.INTERRUPTED, GameEndReason.ERROR}:
        raise ValueError("中断・故障した対局は得点へ含められません")
    raise ValueError("比較の終局理由が未対応です")


def make_pair_score(
    bounds: tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction]],
) -> PairScore:
    """先後交換二局の得点上下限を正確なFraction平均へまとめる。

    引数:
        bounds: 先後交換二局それぞれの候補得点上下限。

    戻り値:
        二局を同じ重みで平均したPairScore。

    例外:
        ValueError: 二局でない、またはいずれかの端点が型・範囲契約外の場合。

    副作用:
        なし。整数比演算のみ行い、浮動小数丸めをしない。

    前提条件:
        二局は同一組の先後交換試合で、各局の下限・上限は候補方式視点である。
    """
    if type(bounds) is not tuple or len(bounds) != 2:
        raise ValueError("一組は先後交換する二局の得点区間で指定してください")
    validated: list[PairScore] = []
    for game_bounds in bounds:
        if type(game_bounds) is not tuple or len(game_bounds) != 2:
            raise ValueError("一局の得点区間は下限と上限の二値で指定してください")
        validated.append(PairScore(*game_bounds))
    return PairScore(
        (validated[0].lower + validated[1].lower) / 2,
        (validated[0].upper + validated[1].upper) / 2,
    )


def analyze_scores(pairs: Sequence[PairScore], *, purpose: str) -> ScoreAnalysis:
    """組ごとの上下限からHoeffding区間と目的別判定を計算する。

    引数:
        pairs: 組単位の候補得点上下限。組間を独立抽出とみなす。
        purpose: 予備比較`pilot`または事前固定の確認比較`confirmation`。

    戻り値:
        標本組数、Fractionの平均上下限、95%半径、丸め前の区間端点と判定。

    例外:
        ValueError: 空標本、不正purpose、PairScore以外を含む場合。

    副作用:
        なし。平方根を取るまで平均得点をFractionで正確に保つ。

    前提条件:
        各PairScoreは先後交換二局の平均であり、区間は0〜1。組内二局の独立性は仮定
        せず、組間独立抽出の仮定の下で固定比較一回のHoeffding区間を計算する。
    """
    _validate_purpose(purpose)
    if not isinstance(pairs, Sequence) or isinstance(pairs, (str, bytes)):
        raise ValueError("得点は組ごとの列で指定してください")
    if not pairs:
        raise ValueError("区間計算には1組以上が必要です")
    if any(not isinstance(pair, PairScore) for pair in pairs):
        raise ValueError("得点列はPairScoreだけで構成してください")

    pair_count = len(pairs)
    lower_mean = sum((pair.lower for pair in pairs), Fraction(0)) / pair_count
    upper_mean = sum((pair.upper for pair in pairs), Fraction(0)) / pair_count
    radius = math.sqrt(_HOEFFDING_LOG_TERM / (2 * pair_count))
    lower = max(0.0, float(lower_mean) - radius)
    upper = min(1.0, float(upper_mean) + radius)
    return ScoreAnalysis(
        pairs=pair_count,
        lower_mean=lower_mean,
        upper_mean=upper_mean,
        radius=radius,
        lower=lower,
        upper=upper,
        decision=decide_interval(lower, upper, purpose=purpose),
    )


def decide_interval(lower: float, upper: float, *, purpose: str) -> str:
    """確認比較の区間端点から改善・悪化・判断不能を返す。

    引数:
        lower: 候補方式得点率区間の下端。
        upper: 候補方式得点率区間の上端。
        purpose: 予備比較`pilot`または確認比較`confirmation`。

    戻り値:
        pilotは`exploratory`。confirmationは境界を厳密に超えたときだけ`improved`または
        `worsened`、それ以外は`inconclusive`。

    例外:
        ValueError: 不正purpose、bool/非数値、非有限、0〜1外または逆転区間の場合。

    副作用:
        なし。

    前提条件:
        入力区間は未丸めの比較値であり、50%との端点一致は判断不能にする。
    """
    _validate_purpose(purpose)
    if type(lower) not in {int, float} or type(upper) not in {int, float}:
        raise ValueError("区間端点は数値で指定してください")
    try:
        lower_value = float(lower)
        upper_value = float(upper)
    except OverflowError as error:
        raise ValueError("区間端点は有限の0〜1数値で指定してください") from error
    if (
        not math.isfinite(lower_value)
        or not math.isfinite(upper_value)
        or not 0.0 <= lower_value <= upper_value <= 1.0
    ):
        raise ValueError("区間端点は有限の0〜1範囲で順序どおりにしてください")
    if purpose == "pilot":
        return "exploratory"
    if lower_value > _DECISION_BOUNDARY:
        return "improved"
    if upper_value < _DECISION_BOUNDARY:
        return "worsened"
    return "inconclusive"


def reference_pair_count() -> int:
    """合意した期待値55%で検出力80%の十分条件を満たす参考組数を返す。

    引数:
        なし。信頼水準95%、境界50%、期待平均55%、目標検出力80%を固定して使う。

    戻り値:
        導出した厳密不等式の右辺を満たす最小整数組数。

    副作用:
        なし。対数・平方根の数値演算だけを行う。

    前提条件:
        未決着なしのHoeffding十分条件から得た参考値で、実際の必要最小組数や
        未決着を含む実験の検出力保証とは扱わない。
    """
    numerator = (math.sqrt(math.log(40)) + math.sqrt(math.log(5))) ** 2
    return math.floor(numerator / (2 * 0.05**2)) + 1


def _validate_purpose(purpose: str) -> None:
    """分析目的を登録済みのpilot/confirmationに限定する。"""
    if not isinstance(purpose, str) or purpose not in _PURPOSES:
        raise ValueError("比較目的はpilotまたはconfirmationで指定してください")
