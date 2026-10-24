"""駒得と飛車可動性を合成した通常評価を提供する。"""

from dataclasses import dataclass

from .evaluation import material_balance
from .model import Position, Side
from .rook_mobility import rook_mobility_balance


@dataclass(frozen=True)
class RookMobilityWeights:
    """合成評価の係数を保持する、変更できない設定データ。

    引数:
        material: 駒得差の正の整数係数。既定値は10。
        mobility: 飛車可動性差の0以上の整数係数。既定値は1。

    生成後に属性を変更できない。値を一か所へ集め、評価式へ係数を重複して
    ハードコードしないようにする。設定ファイルや環境変数からは読み込まない。
    """

    material: int = 10
    mobility: int = 1

    def __post_init__(self) -> None:
        """係数の型と許容範囲を確認する。"""
        if type(self.material) is not int or self.material <= 0:
            raise ValueError("駒得係数は1以上の整数で指定してください")
        if type(self.mobility) is not int or self.mobility < 0:
            raise ValueError("可動性係数は0以上の整数で指定してください")


_DEFAULT_ROOK_MOBILITY_WEIGHTS = RookMobilityWeights()


def evaluate_material_rook_mobility(
    position: Position,
    perspective: Side,
    *,
    weights: RookMobilityWeights = _DEFAULT_ROOK_MOBILITY_WEIGHTS,
) -> int:
    """指定側から見た駒得と飛車可動性の重み付き通常評価を返す。

    引数:
        position: 読み取り対象の盤面・手番・双方の持ち駒を持つ局面。
        perspective: 正の値を有利とする先手または後手。
        weights: 名前付きの駒得・可動性係数。省略時は(10, 1)。

    戻り値:
        `weights.material * material_balance(position, perspective) +`
        `weights.mobility * rook_mobility_balance(position, perspective)` の整数。

    副作用:
        なし。局面を変更せず、探索・乱数・詰み判定も行わない。

    前提条件:
        positionとperspectiveは有効な局面・Sideで、weightsは生成済みの
        RookMobilityWeightsである。

    既存の駒得尺度を維持しながら、新しい評価要素を独立に差し替えられるよう、
    駒得と可動性の正本へそれぞれ委譲する。詰みを区別する一手選択は別の責務とする。
    """
    material = material_balance(position, perspective)
    mobility = rook_mobility_balance(position, perspective)
    return weights.material * material + weights.mobility * mobility
