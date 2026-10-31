"""支えがある駒への低価値駒の利きを集計する。"""

from .evaluation import piece_reference_value
from .model import PieceType, Position, Side, Square
from .movegen import is_piece_attacking_square


def _opponent_side(side: Side) -> Side:
    """指定側と反対の先後を返す。"""
    return Side.GOTE if side == Side.SENTE else Side.SENTE


def supported_lower_value_threat_count(position: Position, side: Side) -> int:
    """指定側の支えがある駒へ低価値駒が利く対象の枚数を返す。

    引数:
        position: 評価する盤面・手番・持ち駒を持つ局面。玉なし部分局面も受け付ける。
        side: 枚数を数える先手または後手。

    戻り値:
        味方駒に支えられ、現在価値が低い相手の盤上非玉駒に利かれている、指定側の
        盤上非玉駒の枚数。対象一枚は攻撃元が複数でも一度だけ数える。

    副作用:
        盤面・手番・持ち駒を変更しない。

    前提条件:
        有効なBoard・Piece・Sideを持つPositionを受け付ける。合法な駒取り・玉安全・
        手番・持ち駒は判定せず、現在の幾何学的な利きだけを用いる。玉は対象と低価値
        攻撃元から除くが、味方の支えには含める。価値と利きは既存の公開操作へ委譲し、
        その例外を隠さない。
    """
    board = position.board
    opponent = _opponent_side(side)
    occupied_squares = []
    for file in range(1, 10):
        for rank in range(1, 10):
            square = Square(file, rank)
            piece = board.piece_at(square)
            if piece is not None:
                occupied_squares.append((square, piece))
    count = 0

    for target, target_piece in occupied_squares:
        if target_piece.side != side or target_piece.piece_type == PieceType.KING:
            continue

        target_value = piece_reference_value(target_piece.piece_type)
        is_supported = any(
            source_piece.side == side
            and is_piece_attacking_square(board, source, target)
            for source, source_piece in occupied_squares
        )
        if not is_supported:
            continue

        has_lower_attacker = any(
            source_piece.side == opponent
            and source_piece.piece_type != PieceType.KING
            and piece_reference_value(source_piece.piece_type) < target_value
            and is_piece_attacking_square(board, source, target)
            for source, source_piece in occupied_squares
        )
        if has_lower_attacker:
            count += 1

    return count


def supported_lower_value_threat_balance(position: Position, perspective: Side) -> int:
    """指定視点側に有利な支えあり低価値駒脅威の枚数差を返す。

    引数:
        position: 評価する盤面・手番・持ち駒を持つ局面。玉なし部分局面も受け付ける。
        perspective: 得点を正として見る先手または後手。

    戻り値:
        相手側の対象枚数から視点側の対象枚数を引いた整数。相手側の対象が多いほど
        正となる。

    副作用:
        盤面・手番・持ち駒を変更しない。

    前提条件:
        有効なBoard・Piece・Sideを持つPositionを受け付ける。両側の枚数は公開の
        `supported_lower_value_threat_count`へ委譲し、その例外を隠さない。この操作はV
        の差だけを返し、重み付けや他の評価項との合成は別の操作に任せる。
    """
    opponent = _opponent_side(perspective)
    return supported_lower_value_threat_count(
        position, opponent
    ) - supported_lower_value_threat_count(position, perspective)
