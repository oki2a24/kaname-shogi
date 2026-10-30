"""駒得と支えのない狙われた駒の差を名前付き重みで合成する。"""

from dataclasses import dataclass

from .evaluation import material_balance
from .model import Position, Side
from .undefended_piece import attacked_undefended_piece_balance


@dataclass(frozen=True)
class UndefendedPieceWeights:
    """駒得・対象差それぞれの合成係数を表す変更不可の設定データ。

    引数:
        material: 駒得差へ掛ける1以上の整数。既定値は10。
        undefended: 攻撃され支えのない駒の差へ掛ける0以上の整数。既定値は1。

    例外:
        ValueError: 係数が許容範囲の整数でない場合。boolやfloatは整数として扱わない。

    戻り値:
        生成された設定データ。dataclassのフィールド代入はできない。

    評価ごとの意図しない設定漏れを防ぐため値を固定し、評価項目を名前で指定する。
    駒得係数は正に保ち、対象差係数のみ0へ設定できる。0でも対象差の入力条件を
    一貫して検証できるよう、評価操作はUの計算を省略しない。
    """

    material: int = 10
    undefended: int = 1

    def __post_init__(self) -> None:
        """生成時に係数の型と許容範囲を検証する。"""
        if type(self.material) is not int or self.material < 1:
            raise ValueError("駒得重みは1以上の整数にしてください")
        if type(self.undefended) is not int or self.undefended < 0:
            raise ValueError("対象差重みは0以上の整数にしてください")


_DEFAULT_UNDEFENDED_PIECE_WEIGHTS = UndefendedPieceWeights()


def evaluate_material_undefended_piece(
    position: Position,
    perspective: Side,
    *,
    weights: UndefendedPieceWeights = _DEFAULT_UNDEFENDED_PIECE_WEIGHTS,
) -> int:
    """指定側から見た駒得と対象差の重み付き通常評価を返す。

    引数:
        position: 評価する盤面・手番・双方の持ち駒を持つ局面。変更しない。
        perspective: 正の値を有利とする先手または後手。
        weights: 名前付きの駒得・対象差係数。省略時は(10, 1)。

    戻り値:
        `weights.material * material_balance(position, perspective) +`
        `weights.undefended * attacked_undefended_piece_balance(position, perspective)`
        の整数。

    副作用:
        なし。局面や持ち駒を変更せず、探索・乱数・詰み判定も行わない。

    前提条件:
        有効なPositionと先手・後手の視点を受け付ける。玉なしの部分局面も評価できる。
        対象差係数が0でもU計算を行い、入力条件と依存先の例外伝播を保つ。

    駒得と対象差の正本へそれぞれ委譲し、名前付き係数で結果を合成する。通常評価値
    と一手詰みの優先順位は別の一手選択器が扱い、この関数は詰みを表す値を作らない。
    """
    material = material_balance(position, perspective)
    undefended = attacked_undefended_piece_balance(position, perspective)
    return weights.material * material + weights.undefended * undefended
