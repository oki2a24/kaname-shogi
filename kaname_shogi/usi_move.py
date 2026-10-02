"""USI一手表記と既存の一手データを対応づける。"""

import re

from .model import BasicPieceType, Square
from .move import BoardMove, DropMove, Move


_BOARD_MOVE_PATTERN = re.compile(r"([1-9][a-i])([1-9][a-i])(\+?)")
_DROP_MOVE_PATTERN = re.compile(r"([A-Z])\*([1-9][a-i])")
_USI_PIECE_TYPES = {
    "P": BasicPieceType.PAWN,
    "L": BasicPieceType.LANCE,
    "N": BasicPieceType.KNIGHT,
    "S": BasicPieceType.SILVER,
    "G": BasicPieceType.GOLD,
    "B": BasicPieceType.BISHOP,
    "R": BasicPieceType.ROOK,
}
_USI_PIECE_SYMBOLS = {
    piece_type: symbol for symbol, piece_type in _USI_PIECE_TYPES.items()
}


def _parse_square(text: str) -> Square:
    """筋数字と段文字から盤上のSquare値を作る。"""
    return Square(int(text[0]), ord(text[1]) - ord("a") + 1)


def parse_usi_move(text: str) -> Move:
    """USIの一手トークンを局面非依存のMove値へ変換する。

    引数:
        text: 盤上移動・成り・駒打ちのいずれかを示すUSI一手トークン。

    戻り値:
        盤上移動ならBoardMove、駒打ちならDropMove。

    副作用:
        なし。局面、持ち駒、手番を参照・変更しない。

    前提条件:
        一手だけを空白なしで指定し、筋はASCII数字1〜9、段はASCII小文字a〜i
        で指定する。

    USI変換を中立なmove/model値型から分離し、文字列の文法と座標だけを
    対応づけるため、この関数では駒の動きや局面合法性を判定しない。

    例外:
        ValueError: textが対応する一手表記でない場合、または玉打ちの場合。
    """
    match = _BOARD_MOVE_PATTERN.fullmatch(text)
    if match is not None:
        return BoardMove(
            source=_parse_square(match.group(1)),
            destination=_parse_square(match.group(2)),
            promote=bool(match.group(3)),
        )

    match = _DROP_MOVE_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError("USIの指し手表記が不正です")

    piece_type = _USI_PIECE_TYPES.get(match.group(1))
    if piece_type is None:
        raise ValueError("USIの駒打ち表記が不正です")

    return DropMove(piece_type, _parse_square(match.group(2)))


def format_usi_move(move: Move) -> str:
    """局面非依存のMove値をUSI一手トークンへ変換する。

    引数:
        move: USIで表記できる盤上移動または玉以外の駒打ち。

    戻り値:
        通常移動・成りまたは駒打ちを示すUSI一手トークン。

    副作用:
        なし。局面、持ち駒、手番を参照・変更しない。

    前提条件:
        BoardMove / DropMoveの各フィールドが型契約を満たし、座標がSquareで
        ある。駒打ちの駒種は玉以外のBasicPieceTypeである。

    値型をUSI文字列へ依存させず、外部表記との対応をこのモジュールへ
    集約するため、ここでは局面合法性や持ち駒の有無を調べない。

    例外:
        ValueError: moveまたはそのフィールドがUSI表記に対応しない場合。
    """
    if isinstance(move, BoardMove):
        if (
            not isinstance(move.source, Square)
            or not isinstance(move.destination, Square)
            or type(move.promote) is not bool
        ):
            raise ValueError("BoardMoveの値がUSI表記に対応しません")

        suffix = "+" if move.promote else ""
        return (
            _format_square(move.source)
            + _format_square(move.destination)
            + suffix
        )

    if isinstance(move, DropMove):
        if (
            not isinstance(move.piece_type, BasicPieceType)
            or move.piece_type is BasicPieceType.KING
            or not isinstance(move.destination, Square)
        ):
            raise ValueError("DropMoveの値がUSI表記に対応しません")

        symbol = _USI_PIECE_SYMBOLS[move.piece_type]
        return f"{symbol}*{_format_square(move.destination)}"

    raise ValueError("USI表記に対応するMove値ではありません")


def _format_square(square: Square) -> str:
    """Square値を筋数字と段文字のUSI座標へ変換する。"""
    return f"{square.file}{chr(ord('a') + square.rank - 1)}"
