"""指し手入力の解析と、標準入出力による対局進行を扱う。"""

from dataclasses import dataclass
from typing import Union

from .model import BasicPieceType, Square


FORMAT_ERROR = "入力形式が正しくありません。"


@dataclass(frozen=True)
class _MoveCommand:
    """盤上移動の入力を、合法性判定前の値として保持する。"""

    source: Square
    destination: Square
    promote: bool


@dataclass(frozen=True)
class _DropCommand:
    """駒打ちの入力を、合法性判定前の値として保持する。"""

    piece_type: BasicPieceType
    destination: Square


def parse_command(text: str) -> Union[_MoveCommand, _DropCommand]:
    """入力文字列を盤上移動または駒打ちの指示へ変換する。

    引数:
        text: `move` または `drop` で始まるCLI入力。区切りは半角・全角空白、
            筋段は半角・全角数字を受け付ける。

    戻り値:
        盤上移動なら元・先のSquareと成り指定を持つ内部値、駒打ちなら基本駒種と
        打ち先を持つ内部値。

    例外:
        ValueError: 操作語、引数、成り記号、駒名、または座標が入力形式に合わない場合。

    副作用:
        局面を変更しない。候補内か、手番に合うか、二歩かなどの合法性はここで判定せず、
        既存のapply_move / apply_dropへ委譲する。文字列を局面処理から分離するための操作である。
    """
    parts = text.split()
    if parts[:1] == ["move"] and len(parts) in (5, 6):
        if len(parts) == 6 and parts[5] != "+":
            raise ValueError(FORMAT_ERROR)
        try:
            return _MoveCommand(
                Square(int(parts[1]), int(parts[2])),
                Square(int(parts[3]), int(parts[4])),
                len(parts) == 6,
            )
        except ValueError as error:
            raise ValueError(FORMAT_ERROR) from error

    piece_types = {
        "歩": BasicPieceType.PAWN,
        "香": BasicPieceType.LANCE,
        "桂": BasicPieceType.KNIGHT,
        "銀": BasicPieceType.SILVER,
        "金": BasicPieceType.GOLD,
        "角": BasicPieceType.BISHOP,
        "飛": BasicPieceType.ROOK,
    }
    if parts[:1] == ["drop"] and len(parts) == 4:
        try:
            return _DropCommand(
                piece_types[parts[1]],
                Square(int(parts[2]), int(parts[3])),
            )
        except (KeyError, ValueError) as error:
            raise ValueError(FORMAT_ERROR) from error

    raise ValueError(FORMAT_ERROR)
