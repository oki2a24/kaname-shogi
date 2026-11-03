"""支えのない被攻撃駒の価値合計を計算する。"""

from .evaluation import piece_reference_value
from .model import PieceType, Position, Side
from .movegen import _BOARD_SQUARES, is_square_attacked


def _opponent_side(side: Side) -> Side:
    """指定側と反対の先後を返す。"""
    return Side.GOTE if side == Side.SENTE else Side.SENTE


def _value_for_side(position: Position, side: Side) -> int:
    """指定側の支えのない被攻撃非玉駒の参考価値を合計する。"""
    opponent = _opponent_side(side)
    total = 0
    for square in _BOARD_SQUARES:
        piece = position.board.piece_at(square)
        if piece is None or piece.side != side or piece.piece_type == PieceType.KING:
            continue
        attacked = is_square_attacked(position.board, square, opponent)
        supported = is_square_attacked(position.board, square, side)
        if attacked and not supported:
            total += piece_reference_value(piece.piece_type)
    return total


def attacked_undefended_piece_value(position: Position, side: Side) -> int:
    """指定側の支えのない被攻撃非玉駒の参考価値合計を返す。

    引数:
        position: 評価する盤面・手番・持ち駒を持つ局面。変更しない。
        side: 対象を集計する先手または後手。

    戻り値:
        相手の現在の盤上利きがあり、指定側の盤上駒から支えられていない対象駒の
        参考価値合計。対象一枚は攻撃元の数によらず一度だけ加える。

    副作用:
        なし。盤面・手番・持ち駒を読み取るだけ。

    前提条件・例外:
        有効なPosition、Side、Pieceを受け付ける。玉は対象から除外するが、玉の
        利きは攻撃・支えに含む。持ち駒と手番は対象判定に使わない。駒価値・利きの
        依存操作が送出した例外をそのまま伝える。

    既存のU（支えのない被攻撃駒の枚数差）を置き換える評価要素であり、同じ
    対象条件を保って参考価値を使う。盤上の価値表と現在の利き定義を再利用する。
    """
    return _value_for_side(position, side)


def attacked_undefended_piece_value_balance(
    position: Position, perspective: Side
) -> int:
    """指定視点に有利な支えのない被攻撃駒の価値合計差を返す。

    引数:
        position: 評価する局面。盤面・手番・持ち駒は変更しない。
        perspective: 差を正として見る先手または後手。

    戻り値:
        相手側の価値合計から視点側の価値合計を引いた整数。正は視点側の危険が
        相手より小さいことを表す。

    副作用:
        なし。

    前提条件・例外:
        `attacked_undefended_piece_value` の条件と例外を引き継ぐ。

    各側の集計は単独の読み取り操作へ委譲し、M（駒得）やV（支えあり低価値駒
    脅威）の符号と同じく、視点側に有利な差を正に統一する。
    """
    opponent = _opponent_side(perspective)
    return attacked_undefended_piece_value(position, opponent) - (
        attacked_undefended_piece_value(position, perspective)
    )
