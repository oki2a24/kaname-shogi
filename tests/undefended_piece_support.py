"""支えのない狙われた駒のテスト用固定局面を組み立てる。"""

from collections.abc import Iterable

from kaname_shogi.model import (
    BasicPieceType,
    Board,
    Piece,
    PieceType,
    Position,
    Side,
    Square,
)

PieceSpec = tuple[PieceType, Side, Square]


def position(*pieces: PieceSpec, side_to_move: Side = Side.SENTE) -> Position:
    """筋・段で指定した駒を置くテスト用局面を返す。"""
    board = Board()
    for piece_type, side, square in pieces:
        board.set_piece(square, Piece(piece_type, side))
    return Position(board, side_to_move)


def design_case(name: str) -> Position:
    """承認済み設計のA〜D局面を手書き配置で返す。"""
    common = (
        (PieceType.KING, Side.SENTE, Square(9, 9)),  # 先手玉
        (PieceType.KNIGHT, Side.SENTE, Square(5, 5)),  # 先手桂
        (PieceType.KING, Side.GOTE, Square(1, 1)),  # 後手王
    )
    cases = {
        "A": common
        + (
            (PieceType.GOLD, Side.SENTE, Square(4, 7)),  # 先手金
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),  # 後手歩
        ),
        "B": common
        + (
            (PieceType.GOLD, Side.SENTE, Square(4, 6)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        ),
        "C": common
        + (
            (PieceType.GOLD, Side.SENTE, Square(4, 7)),
            (PieceType.PAWN, Side.GOTE, Square(5, 3)),
        ),
        "D": common
        + (
            (PieceType.GOLD, Side.SENTE, Square(4, 6)),
            (PieceType.PAWN, Side.GOTE, Square(5, 3)),
        ),
    }
    try:
        return position(*cases[name])
    except KeyError as error:
        raise ValueError(f"未知の設計局面です: {name}") from error


def both_nonzero_case() -> tuple[PieceSpec, ...]:
    """両側の対象枚数が0でない固定局面の駒配置を返す。"""
    return (
        (PieceType.KING, Side.SENTE, Square(9, 9)),  # 先手玉
        (PieceType.KNIGHT, Side.SENTE, Square(5, 5)),  # 先手桂
        (PieceType.KNIGHT, Side.SENTE, Square(3, 5)),  # 先手桂
        (PieceType.GOLD, Side.SENTE, Square(4, 7)),  # 先手金
        (PieceType.PAWN, Side.SENTE, Square(7, 5)),  # 先手歩
        (PieceType.KING, Side.GOTE, Square(1, 1)),  # 後手王
        (PieceType.PAWN, Side.GOTE, Square(5, 4)),  # 後手歩
        (PieceType.PAWN, Side.GOTE, Square(3, 4)),  # 後手歩
        (PieceType.KNIGHT, Side.GOTE, Square(7, 4)),  # 後手桂
    )


def rotate_and_swap(pieces: Iterable[PieceSpec]) -> tuple[PieceSpec, ...]:
    """全駒を180度回転し、先後を交換した配置を返す。"""
    rotated = []
    for piece_type, side, square in pieces:
        opposite = Side.GOTE if side == Side.SENTE else Side.SENTE
        rotated.append(
            (piece_type, opposite, Square(10 - square.file, 10 - square.rank))
        )
    return tuple(rotated)


def snapshot(position: Position) -> tuple[object, ...]:
    """81マス・手番・両側の玉以外の持ち駒枚数を読み取り専用で記録する。"""
    board = tuple(
        position.board.piece_at(Square(file, rank))
        for file in range(1, 10)
        for rank in range(1, 10)
    )
    hands = tuple(
        tuple(
            hand.count(piece_type)
            for piece_type in BasicPieceType
            if piece_type != BasicPieceType.KING
        )
        for hand in (position.sente_hand, position.gote_hand)
    )
    return board, position.side_to_move, hands
