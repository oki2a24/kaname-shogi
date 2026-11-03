"""支えがある駒への低価値駒の利きを集計する。"""

from collections.abc import Iterator

from .evaluation import piece_reference_value
from .model import Piece, PieceType, Position, Side, Square
from .movegen import (
    _BOARD_SQUARES,
    _KNIGHT_SOURCE_OFFSETS,
    _RAY_DIRECTIONS,
    is_piece_attacking_square,
)


def _opponent_side(side: Side) -> Side:
    """指定側と反対の先後を返す。"""
    return Side.GOTE if side == Side.SENTE else Side.SENTE


def _target_source_candidates(
    pieces_by_index: dict[int, Piece], target: Square
) -> Iterator[tuple[Square, Piece]]:
    """初回盤面scanからtargetへ利きうるray先頭駒と桂sourceを返す。

    `pieces_by_index`は現在のBoardを一度全走査して作った局所データである。
    遠い盤面や履歴と共有せず、候補位置の占有確認でBoardを再読しない。
    """
    for file_step, rank_step in _RAY_DIRECTIONS:
        file = target.file + file_step
        rank = target.rank + rank_step
        while 1 <= file <= 9 and 1 <= rank <= 9:
            index = (file - 1) * 9 + rank - 1
            source = _BOARD_SQUARES[index]
            piece = pieces_by_index.get(index)
            if piece is not None:
                yield source, piece
                break
            file += file_step
            rank += rank_step

    for file_step, rank_step in _KNIGHT_SOURCE_OFFSETS:
        file = target.file + file_step
        rank = target.rank + rank_step
        if not (1 <= file <= 9 and 1 <= rank <= 9):
            continue
        index = (file - 1) * 9 + rank - 1
        source = _BOARD_SQUARES[index]
        piece = pieces_by_index.get(index)
        if piece is not None:
            yield source, piece


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

    targetを攻撃できる駒は、8方向rayの最初の駒か桂sourceに限られる。対象ごとに
    全占有駒を支え・攻撃の二度の候補として走査せず、この候補sourceを一巡で調べる。
    """
    board = position.board
    opponent = _opponent_side(side)
    occupied_squares = []
    pieces_by_index = {}
    for square in _BOARD_SQUARES:
        piece = board.piece_at(square)
        if piece is not None:
            occupied_squares.append((square, piece))
            pieces_by_index[square.to_index()] = piece
    count = 0

    for target, target_piece in occupied_squares:
        if target_piece.side != side or target_piece.piece_type == PieceType.KING:
            continue

        target_value = piece_reference_value(target_piece.piece_type)
        is_supported = False
        has_lower_attacker = False
        for source, source_piece in _target_source_candidates(pieces_by_index, target):
            if source_piece.side == side and not is_supported:
                is_supported = is_piece_attacking_square(board, source, target)
            elif (
                source_piece.side == opponent
                and source_piece.piece_type != PieceType.KING
                and not has_lower_attacker
                and piece_reference_value(source_piece.piece_type) < target_value
            ):
                has_lower_attacker = is_piece_attacking_square(board, source, target)
            if is_supported and has_lower_attacker:
                count += 1
                break

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
