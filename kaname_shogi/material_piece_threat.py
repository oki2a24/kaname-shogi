"""駒得・U・Vを名前付き重みで合成する。"""

from dataclasses import dataclass

from .evaluation import material_balance
from .model import Position, Side
from .supported_piece_threat import supported_lower_value_threat_balance
from .undefended_piece import attacked_undefended_piece_balance


@dataclass(frozen=True)
class PieceThreatWeights:
    """駒得・U・Vそれぞれの合成係数を保持する変更不可の設定データ。

    引数:
        material: 駒得差へ掛ける1以上の整数。既定値は10。
        undefended: Uの差へ掛ける0以上の整数。既定値は1。
        supported_threat: Vの差へ掛ける0以上の整数。既定値は1。

    戻り値:
        生成された重み設定。フィールドは生成後に変更できない。

    重みを位置でなく名前で指定することで、評価項目を入れ替えたときの係数取り違えを
    避ける。駒得の正の尺度を保ち、U/Vだけを個別に0へ設定できる。
    """

    material: int = 10
    undefended: int = 1
    supported_threat: int = 1

    def __post_init__(self) -> None:
        """生成時に係数の型と許容範囲を検証する。"""
        if type(self.material) is not int or self.material < 1:
            raise ValueError("駒得重みは1以上の整数にしてください")
        if type(self.undefended) is not int or self.undefended < 0:
            raise ValueError("対象差重みは0以上の整数にしてください")
        if type(self.supported_threat) is not int or self.supported_threat < 0:
            raise ValueError("支えあり脅威重みは0以上の整数にしてください")


_DEFAULT_PIECE_THREAT_WEIGHTS = PieceThreatWeights()


def evaluate_material_piece_threat(
    position: Position,
    perspective: Side,
    *,
    weights: PieceThreatWeights = _DEFAULT_PIECE_THREAT_WEIGHTS,
) -> int:
    """指定側から見たM/U/Vの重み付き通常評価を返す。

    引数:
        position: 評価する盤面・手番・双方の持ち駒を持つ局面。変更しない。
        perspective: 正の値を有利とする先手または後手。
        weights: 名前付きの駒得・U・V係数。既定値は(10, 1, 1)。

    戻り値:
        `weights.material * M + weights.undefended * U +`
        `weights.supported_threat * V` の整数。

    副作用:
        なし。局面を変更せず、探索・乱数・詰み判定も行わない。

    前提条件:
        有効なPositionと先手・後手の視点を受け付ける。U/Vの係数が0でも各評価項を
        計算し、依存操作の入力条件と例外伝播を保つ。詰みの勝敗はこの値へ符号化しない。

    M/U/Vの正本へ各一度委譲し、名前付き係数で通常点を合成する。詰み優先と一手選択は
    既存の差替式選択器へ任せ、他の選択方式を変更しない。
    """
    material = material_balance(position, perspective)
    undefended = attacked_undefended_piece_balance(position, perspective)
    supported_threat = supported_lower_value_threat_balance(position, perspective)
    return (
        weights.material * material
        + weights.undefended * undefended
        + weights.supported_threat * supported_threat
    )
