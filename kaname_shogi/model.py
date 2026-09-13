"""筋・段で扱う駒と盤面。表示形式から独立したデータを保持する。"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class Side(Enum):
    SENTE = auto()
    GOTE = auto()


class PieceType(Enum):
    KING = auto()
    ROOK = auto()
    BISHOP = auto()
    GOLD = auto()
    SILVER = auto()
    KNIGHT = auto()
    LANCE = auto()
    PAWN = auto()


@dataclass(frozen=True)
class Square:
    file: int
    rank: int

    def __post_init__(self) -> None:
        # boolはintの一種だが、将棋の座標としては受け付けない。
        if any(type(value) is not int or not 1 <= value <= 9
               for value in (self.file, self.rank)):
            raise ValueError("筋・段は1〜9の整数で指定してください")

    def to_index(self) -> int:
        """１一、１二、…、１九、２一、…、９九を0〜80に対応付ける。"""
        return (self.file - 1) * 9 + (self.rank - 1)


@dataclass(frozen=True)
class Piece:
    piece_type: PieceType
    side: Side


class Board:
    def __init__(self) -> None:
        self._cells: list[Optional[Piece]] = [None] * 81

    def piece_at(self, square: Square) -> Optional[Piece]:
        return self._cells[square.to_index()]

    def set_piece(self, square: Square, piece: Optional[Piece]) -> None:
        """指定マスを設定する。指し手の合法性を判定する操作ではない。"""
        self._cells[square.to_index()] = piece


@dataclass
class Position:
    board: Board
    side_to_move: Side


def create_initial_position() -> Position:
    """平手の初期配置を、新しい盤面に作る。"""
    board = Board()
    back_rank = (
        PieceType.LANCE, PieceType.KNIGHT, PieceType.SILVER,
        PieceType.GOLD, PieceType.KING, PieceType.GOLD,
        PieceType.SILVER, PieceType.KNIGHT, PieceType.LANCE,
    )
    for side, home_rank, pawn_rank in [(Side.SENTE, 9, 7), (Side.GOTE, 1, 3)]:
        for file, piece_type in enumerate(back_rank, start=1):
            board.set_piece(Square(file, home_rank), Piece(piece_type, side))
            board.set_piece(Square(file, pawn_rank), Piece(PieceType.PAWN, side))

    # 飛角は先後で筋が異なるため、学習済みの筋・段を明記する。
    board.set_piece(Square(8, 8), Piece(PieceType.BISHOP, Side.SENTE))
    board.set_piece(Square(2, 8), Piece(PieceType.ROOK, Side.SENTE))
    board.set_piece(Square(8, 2), Piece(PieceType.ROOK, Side.GOTE))
    board.set_piece(Square(2, 2), Piece(PieceType.BISHOP, Side.GOTE))
    return Position(board, Side.SENTE)
