"""駒得と玉周辺安全度を名前付き重みで合成する。"""

from dataclasses import dataclass

from .evaluation import material_balance
from .king_safety import king_safety_balance
from .model import Position, Side


@dataclass(frozen=True)
class KingSafetyWeights:
    """駒得・安全度それぞれの合成係数を表す変更不可の設定データ。

    引数:
        material: 駒得差へ掛ける1以上の整数。既定値は10。
        safety: 玉周辺安全度差へ掛ける0以上の整数。既定値は1。

    例外:
        ValueError: 係数が許容範囲の整数でない場合。boolやfloatは整数として扱わない。

    戻り値:
        生成された設定データ。dataclassのフィールド代入はできない。

    評価ごとの意図しない設定漏れを防ぐため値を固定し、評価項目を名前で指定する。
    駒得係数は正に保ち、安全度係数のみ0へ設定して比較から除ける。
    """

    material: int = 10
    safety: int = 1

    def __post_init__(self) -> None:
        """生成時に係数の型と許容範囲を検証する。"""
        if type(self.material) is not int or self.material < 1:
            raise ValueError("駒得重みは1以上の整数にしてください")
        if type(self.safety) is not int or self.safety < 0:
            raise ValueError("安全度重みは0以上の整数にしてください")


_DEFAULT_KING_SAFETY_WEIGHTS = KingSafetyWeights()


def evaluate_material_king_safety(
    position: Position,
    perspective: Side,
    *,
    weights: KingSafetyWeights = _DEFAULT_KING_SAFETY_WEIGHTS,
) -> int:
    """指定側から見た駒得と玉周辺安全度の重み付き通常評価を返す。

    引数:
        position: 評価する盤面・手番・双方の持ち駒を持つ局面。変更しない。
        perspective: 正の値を有利とする先手または後手。
        weights: 名前付きの駒得・安全度係数。省略時は(10, 1)。

    戻り値:
        `weights.material * material_balance(position, perspective) +`
        `weights.safety * king_safety_balance(position, perspective)` の整数。

    例外:
        ValueError: 安全度係数が0でも、先手・後手の玉が各一枚でない場合。

    副作用:
        なし。局面や持ち駒を変更せず、探索・乱数・詰み判定も行わない。

    駒得と玉周辺安全度の正本へそれぞれ委譲し、設定可能な係数で合成する。
    安全度係数が0でも関数を呼び、評価入力の玉前提を一貫して検査する。
    詰みを区別する一手選択は別の責務とする。
    """
    material = material_balance(position, perspective)
    safety = king_safety_balance(position, perspective)
    return weights.material * material + weights.safety * safety
