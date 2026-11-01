"""支えのない被攻撃駒の価値を独立局面で検査する固定配置。"""

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
    """指定した筋・段に駒を置く新しい局面を返す。"""
    board = Board()
    for piece_type, side, square in pieces:
        board.set_piece(square, Piece(piece_type, side))
    return Position(board, side_to_move)


def design_case(name: str) -> Position:
    """設計A〜Eの駒配置を手計算用に組み立てる。"""
    cases = {
        "A": (
            (PieceType.ROOK, Side.SENTE, Square(4, 5)),
            (PieceType.PAWN, Side.SENTE, Square(1, 8)),
            (PieceType.KNIGHT, Side.GOTE, Square(5, 3)),
        ),
        "B": (
            (PieceType.PAWN, Side.SENTE, Square(4, 5)),
            (PieceType.ROOK, Side.SENTE, Square(1, 8)),
            (PieceType.KNIGHT, Side.GOTE, Square(5, 3)),
        ),
        "C": (
            (PieceType.ROOK, Side.SENTE, Square(4, 5)),
            (PieceType.PAWN, Side.SENTE, Square(1, 8)),
            (PieceType.SILVER, Side.SENTE, Square(3, 6)),
            (PieceType.KNIGHT, Side.GOTE, Square(5, 3)),
        ),
        "D": (
            (PieceType.ROOK, Side.SENTE, Square(4, 5)),
            (PieceType.PAWN, Side.SENTE, Square(1, 8)),
            (PieceType.BISHOP, Side.SENTE, Square(8, 5)),
            (PieceType.GOLD, Side.SENTE, Square(7, 6)),
            (PieceType.KNIGHT, Side.GOTE, Square(5, 3)),
            (PieceType.PAWN, Side.GOTE, Square(8, 4)),
        ),
        "E": (
            (PieceType.ROOK, Side.SENTE, Square(4, 5)),
            (PieceType.PAWN, Side.SENTE, Square(8, 5)),
            (PieceType.KNIGHT, Side.GOTE, Square(5, 3)),
            (PieceType.SILVER, Side.GOTE, Square(8, 4)),
        ),
    }
    try:
        return position(*cases[name])
    except KeyError as error:
        raise ValueError(f"未知の設計局面です: {name}") from error


def design_case_pieces(name: str) -> tuple[PieceSpec, ...]:
    """設計局面の手書き駒配置を返す。"""
    current = design_case(name)
    return tuple(
        (piece.piece_type, piece.side, Square(file, rank))
        for file in range(1, 10)
        for rank in range(1, 10)
        if (piece := current.board.piece_at(Square(file, rank))) is not None
    )


def rotate_and_swap(pieces: Iterable[PieceSpec]) -> tuple[PieceSpec, ...]:
    """配置を180度回転し、先後を交換したタプルを返す。"""
    rotated = []
    for piece_type, side, square in pieces:
        other = Side.GOTE if side is Side.SENTE else Side.SENTE
        rotated.append((piece_type, other, Square(10 - square.file, 10 - square.rank)))
    return tuple(rotated)


def snapshot(position_: Position) -> tuple[object, ...]:
    """盤面、手番、両側の持ち駒を読み取り専用で記録する。"""
    board = tuple(
        position_.board.piece_at(Square(file, rank))
        for file in range(1, 10)
        for rank in range(1, 10)
    )
    hands = tuple(
        tuple(
            hand.count(piece_type)
            for piece_type in BasicPieceType
            if piece_type is not BasicPieceType.KING
        )
        for hand in (position_.sente_hand, position_.gote_hand)
    )
    return board, position_.side_to_move, hands
