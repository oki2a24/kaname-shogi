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
from kaname_shogi.move import BoardMove

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


def mate_case(perspective: Side) -> tuple[Position, BoardMove, BoardMove]:
    """詰み・通常手の合法な候補を含む固定局面を返す。

    引数:
        perspective: 先手なら先手例、後手ならその180度回転・先後反転例を選ぶ。

    戻り値:
        (局面, 一手詰みの飛車移動, 通常の飛車移動)。

    副作用:
        なし。新しいテスト用局面を作る。

    両例で二候補の合法性と詰み判定を各テストから確認し、既存選択器の詰み優先が
    開始側・候補順に依存しないことを固定配置で調べる。
    """
    pieces: tuple[PieceSpec, ...] = (
        (PieceType.KING, Side.SENTE, Square(9, 9)),
        (PieceType.ROOK, Side.SENTE, Square(5, 3)),
        (PieceType.GOLD, Side.SENTE, Square(4, 3)),
        (PieceType.KING, Side.GOTE, Square(5, 1)),
        (PieceType.PAWN, Side.GOTE, Square(4, 1)),
        (PieceType.PAWN, Side.GOTE, Square(6, 1)),
        (PieceType.PAWN, Side.GOTE, Square(4, 2)),
        (PieceType.PAWN, Side.GOTE, Square(6, 2)),
    )
    if perspective == Side.GOTE:
        pieces = rotate_and_swap(pieces)

    current = position(*pieces, side_to_move=perspective)
    if perspective == Side.SENTE:
        mate = BoardMove(Square(5, 3), Square(5, 2), False)
        normal = BoardMove(Square(5, 3), Square(6, 3), False)
    else:
        mate = BoardMove(Square(5, 7), Square(5, 8), False)
        normal = BoardMove(Square(5, 7), Square(4, 7), False)
    return current, mate, normal


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
