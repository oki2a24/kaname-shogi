"""玉周辺の危険マス数と指定側の安全度差を計算する。"""

from .model import PieceType, Position, Side, Square
from .movegen import is_square_attacked

_KING_NEIGHBOR_OFFSETS = (
    (-1, -1),
    (0, -1),
    (1, -1),
    (-1, 0),
    (1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
)


def _opponent_side(side: Side) -> Side:
    """sideと反対の先後を返す非公開の値操作。"""
    return Side.GOTE if side == Side.SENTE else Side.SENTE


def _find_king_squares(position: Position) -> dict[Side, Square]:
    """両側の玉を一度走査で見つけ、正確に一枚ずつであることを検証する。"""
    candidates: dict[Side, list[Square]] = {side: [] for side in Side}
    for file in range(1, 10):
        for rank in range(1, 10):
            square = Square(file, rank)
            piece = position.board.piece_at(square)
            if piece is not None and piece.piece_type == PieceType.KING:
                candidates[piece.side].append(square)

    if any(len(candidates[side]) != 1 for side in Side):
        raise ValueError("先手・後手の玉はそれぞれ1枚必要です")
    return {side: candidates[side][0] for side in Side}


def _count_attacked_neighbors(
    position: Position, king_square: Square, attacking_side: Side
) -> int:
    """玉の盤内隣接マスのうち、指定側から利かれる異なるマス数を返す。"""
    count = 0
    for file_delta, rank_delta in _KING_NEIGHBOR_OFFSETS:
        file = king_square.file + file_delta
        rank = king_square.rank + rank_delta
        if not 1 <= file <= 9 or not 1 <= rank <= 9:
            continue
        target = Square(file, rank)
        if is_square_attacked(position.board, target, attacking_side):
            count += 1
    return count


def king_danger_count(position: Position, side: Side) -> int:
    """指定側の玉周辺で、相手の利きがある異なるマス数を返す。

    引数:
        position: 両側の玉を含む局面。盤面や持ち駒は変更しない。
        side: 危険マス数を調べる先手・後手。

    戻り値:
        指定側の玉に隣接する盤内マスのうち、相手の盤上駒から利かれているマス数。
        空マス・味方占有・相手占有の各マスを含み、同じマスは一度だけ数える。

    例外:
        ValueError: 先手または後手の玉が欠けているか、同じ側に複数ある場合。

    玉の周囲は将来の着手を仮定せず、現在の盤面のまま調べる。利き照会は盤上の
    駒だけを使い、ピンされた駒の利きも含める。玉を取り除いた射線や持ち駒からの
    将来の駒打ちは数えない。両側の玉を一度の盤走査で検証してから、隣接する
    盤内マスだけをTask 1の公開利き照会へ渡す。
    """
    kings = _find_king_squares(position)
    return _count_attacked_neighbors(position, kings[side], _opponent_side(side))


def king_safety_balance(position: Position, perspective: Side) -> int:
    """指定側の玉周辺安全度を相手側との差で返す読み取り操作。

    引数:
        position: 両側の玉を含む局面。盤面、手番、持ち駒は変更しない。
        perspective: 正の値を有利とする先手・後手。

    戻り値:
        相手側の危険マス数から指定側の危険マス数を引いた整数。
        手番や持ち駒の将来利用には依存しない。

    例外:
        ValueError: 先手または後手の玉が欠けているか、同じ側に複数ある場合。

    安全度差S(P)=D(Q)-D(P)として、指定視点で正が有利になるようにする。
    両側の玉を一度の盤走査で検証し、同じ盤面の利き照会を再利用して差を作る。
    """
    kings = _find_king_squares(position)
    opponent = _opponent_side(perspective)
    perspective_danger = _count_attacked_neighbors(
        position, kings[perspective], opponent
    )
    opponent_danger = _count_attacked_neighbors(position, kings[opponent], perspective)
    return opponent_danger - perspective_danger
