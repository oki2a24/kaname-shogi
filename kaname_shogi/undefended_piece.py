"""相手の利きがあり味方の支えがない盤上駒を読み取る。"""

from .model import PieceType, Position, Side, Square
from .movegen import is_square_attacked


def _opponent_side(side: Side) -> Side:
    """指定側と反対の先後を返す。"""
    return Side.GOTE if side == Side.SENTE else Side.SENTE


def _count_for_side(position: Position, side: Side) -> int:
    """指定側の攻撃され支えのない盤上非玉駒を走査して数える。"""
    opponent = _opponent_side(side)
    count = 0
    for file in range(1, 10):
        for rank in range(1, 10):
            square = Square(file, rank)
            piece = position.board.piece_at(square)
            if (
                piece is None
                or piece.side != side
                or piece.piece_type == PieceType.KING
            ):
                continue
            is_attacked = is_square_attacked(position.board, square, opponent)
            is_supported = is_square_attacked(position.board, square, side)
            if is_attacked and not is_supported:
                count += 1
    return count


def attacked_undefended_piece_count(position: Position, side: Side) -> int:
    """指定側の攻撃され支えのない盤上非玉駒の枚数を返す。

    引数:
        position: 評価する盤面・手番・持ち駒を持つ局面。玉なし部分局面も受け付ける。
        side: 枚数を数える先手または後手。

    戻り値:
        相手の利きがあり、指定側の利きがない盤上非玉駒の枚数。

    副作用:
        盤面・手番・持ち駒を変更しない。

    前提条件:
        有効なBoard・Piece・Sideを持つPositionを受け付ける。合法な駒取り可能性は
        判定せず、現在の利きと遮蔽だけを用いる。玉は対象外だが攻撃・支えに含める。
        利きは既存の公開操作へ委譲するため、ピンされた駒も攻撃元・支え役になる。
    """
    return _count_for_side(position, side)


def attacked_undefended_piece_balance(position: Position, perspective: Side) -> int:
    """指定側に有利な攻撃され支えのない駒の差を返す。

    引数:
        position: 評価する盤面・手番・持ち駒を持つ局面。玉なし部分局面も受け付ける。
        perspective: 得点を正として見る先手または後手。

    戻り値:
        相手側の対象枚数から指定側の対象枚数を引いた整数。相手側の対象が多いほど
        正となる。

    副作用:
        盤面・手番・持ち駒を変更しない。

    前提条件:
        有効なBoard・Piece・Sideを持つPositionを受け付ける。攻撃と支えは公開利き
        操作の定義に従い、手番・持ち駒・合法性に依存させない。この操作はCの差Uを
        集計するだけで、評価重みや駒得との合成は別の操作に任せる。
    """
    opponent = _opponent_side(perspective)
    return _count_for_side(position, opponent) - _count_for_side(position, perspective)
