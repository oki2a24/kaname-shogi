"""駒得・支えのない被攻撃駒の価値・支えあり脅威を合成する。"""

from dataclasses import dataclass

from .evaluation import material_balance
from .model import Position, Side
from .supported_piece_threat import supported_lower_value_threat_balance
from .undefended_piece_value import attacked_undefended_piece_value_balance


@dataclass(frozen=True)
class PieceThreatValueWeights:
    """駒得・被攻撃価値・支えあり脅威の合成係数を保持する設定データ。

    引数:
        material: M（駒得）へ掛ける1以上の整数。既定値10。
        undefended_value: 支えのない被攻撃駒の価値合計差へ掛ける0以上の整数。
            既定値1。
        supported_threat: V（支えあり低価値駒脅威）へ掛ける0以上の整数。
            既定値1。

    例外:
        ValueError: 係数が範囲内の厳密な整数でない場合。boolとfloatも拒否する。

    戻り値:
        変更不能な名前付き係数データ。

    係数を名前で指定して、異なる評価項目の位置を取り違えないようにする。駒得の
    正の尺度は維持し、二つの追加項目はそれぞれ0へ設定できる。
    """

    material: int = 10
    undefended_value: int = 1
    supported_threat: int = 1

    def __post_init__(self) -> None:
        """係数の型と許容範囲を作成時に確認する。"""
        if type(self.material) is not int or self.material < 1:
            raise ValueError("駒得重みは1以上の整数にしてください")
        if type(self.undefended_value) is not int or self.undefended_value < 0:
            raise ValueError("対象価値差重みは0以上の整数にしてください")
        if type(self.supported_threat) is not int or self.supported_threat < 0:
            raise ValueError("支えあり脅威重みは0以上の整数にしてください")


_DEFAULT_PIECE_THREAT_VALUE_WEIGHTS = PieceThreatValueWeights()


def evaluate_material_piece_threat_value(
    position: Position,
    perspective: Side,
    *,
    weights: PieceThreatValueWeights = _DEFAULT_PIECE_THREAT_VALUE_WEIGHTS,
) -> int:
    """指定視点のM（駒得）・被攻撃価値・V（支えあり脅威）を合成する。

    引数:
        position: 評価する局面。盤面・手番・持ち駒は変更しない。
        perspective: 正の点を有利とみなす先手または後手。
        weights: 名前付き合成係数。既定値は(10, 1, 1)。

    戻り値:
        駒得・支えのない被攻撃駒の価値合計差・Vの重み付き合計である整数。

    副作用:
        なし。局面を読むだけで、探索・乱数・詰み判定を行わない。

    前提条件・例外:
        有効なPosition、Side、重みを受け付ける。係数が0でも三評価を計算し、依存先の
        例外をそのまま伝える。詰みの勝敗はこの点数へ符号化しない。

    既存U（支えのない被攻撃駒の枚数差）は加えず、今回の価値合計差で置き換える。
    既存のM・Vと価値合計差を一回ずつ計算し、名前付き係数で合成する。
    """
    material = material_balance(position, perspective)
    return _evaluate_material_piece_threat_value_with_material(
        position, perspective, material, weights=weights
    )


def _evaluate_material_piece_threat_value_with_material(
    position: Position,
    perspective: Side,
    material: int,
    *,
    weights: PieceThreatValueWeights = _DEFAULT_PIECE_THREAT_VALUE_WEIGHTS,
) -> int:
    """既知のMと既存価値合計/Vから、価値+V通常評価点を返す非公開操作。

    比較policyの一手選択が合法手差分から得たMを渡し、候補ごとの全盤面走査を
    繰り返さずに済むようにする。公開評価器は従来どおりMを一度全盤面計算して委譲する。
    """
    undefended_value = attacked_undefended_piece_value_balance(position, perspective)
    supported_threat = supported_lower_value_threat_balance(position, perspective)
    return (
        weights.material * material
        + weights.undefended_value * undefended_value
        + weights.supported_threat * supported_threat
    )
