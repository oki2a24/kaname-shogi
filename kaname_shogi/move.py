"""局面を変更しない、将棋の一手を表す値を定義する。

このモジュールは合法手生成・棋譜保存・将来のUSI変換の共通データ境界である。
一手の値を実際に局面へ適用する操作は、`movegen.apply_move` と
`movegen.apply_drop` が担当する。
"""

from dataclasses import dataclass
from typing import Union

from .model import BasicPieceType, Square


@dataclass(frozen=True)
class BoardMove:
    """盤上移動を表す変更不可の一手データ。

    引数:
        source: 出発マスを表す値。
        destination: 到着マスを表す値。
        promote: 移動時に成るかを表す値。

    戻り値:
        盤面を変更せず、指し手の内容を保持する値。

    副作用:
        生成後の属性を変更しない。局面を直接変更しない。

    `RecordedMove` は棋譜の履歴データであり、この型は合法手や将来の外部形式
    変換にも使う中立な指し手データである。用途の依存方向を分けるために独立した
    型とする。
    """

    source: Square
    destination: Square
    promote: bool


@dataclass(frozen=True)
class DropMove:
    """持ち駒を打つ操作の内容を表す変更不可の一手データ。

    引数:
        piece_type: 打つ基本駒種を表す値。玉は持ち駒にならない。
        destination: 打ち先のマスを表す値。

    戻り値:
        盤面を変更せず、駒打ちの内容を保持する値。

    副作用:
        生成後の属性を変更しない。局面を直接変更しない。

    駒打ちは盤上移動と異なるデータを必要とするため、`BoardMove` と別の型に
    する。ただし両方を `Move` として一つの合法手一覧で扱えるようにする。
    """

    piece_type: BasicPieceType
    destination: Square


Move = Union[BoardMove, DropMove]
"""合法手一覧に含められる盤上移動または駒打ちの型。"""
