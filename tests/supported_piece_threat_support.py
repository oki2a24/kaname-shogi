"""支えがある駒への低価値駒の利きの固定局面を組み立てる。"""

from undefended_piece_support import position

from kaname_shogi.model import PieceType, Position, Side, Square

PieceSpec = tuple[PieceType, Side, Square]


def design_case_pieces(name: str) -> tuple[PieceSpec, ...]:
    """承認済み設計のA〜C局面を独立した駒配置で返す。"""
    cases = {
        "A": (
            (PieceType.BISHOP, Side.SENTE, Square(5, 5)),
            (PieceType.GOLD, Side.SENTE, Square(4, 6)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        ),
        "B": (
            (PieceType.BISHOP, Side.SENTE, Square(5, 5)),
            (PieceType.GOLD, Side.SENTE, Square(3, 6)),
            (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        ),
        "C": (
            (PieceType.BISHOP, Side.SENTE, Square(5, 5)),
            (PieceType.GOLD, Side.SENTE, Square(4, 6)),
            (PieceType.PAWN, Side.GOTE, Square(5, 3)),
        ),
    }
    try:
        return cases[name]
    except KeyError as error:
        raise ValueError(f"未知の設計局面です: {name}") from error


def design_case(name: str) -> Position:
    """承認済み設計のA〜C局面を返す。"""
    return position(*design_case_pieces(name))


def both_sides_case() -> Position:
    """両側の対象枚数が0でない、承認済みD局面を返す。"""
    return position(*both_sides_case_pieces())


def both_sides_case_pieces() -> tuple[PieceSpec, ...]:
    """承認済みD局面を先後反転用の駒配置として返す。"""
    return (
        (PieceType.BISHOP, Side.SENTE, Square(5, 5)),
        (PieceType.BISHOP, Side.SENTE, Square(3, 5)),
        (PieceType.GOLD, Side.SENTE, Square(4, 6)),
        (PieceType.PAWN, Side.SENTE, Square(8, 4)),
        (PieceType.PAWN, Side.GOTE, Square(5, 4)),
        (PieceType.PAWN, Side.GOTE, Square(3, 4)),
        (PieceType.ROOK, Side.GOTE, Square(8, 3)),
        (PieceType.GOLD, Side.GOTE, Square(7, 2)),
    )
