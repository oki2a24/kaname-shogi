"""盤上の未成飛車について、移動先候補数の差を数える。"""

from .model import PieceType, Position, Side, Square
from .movegen import rook_move_candidates


def rook_mobility_balance(position: Position, perspective: Side) -> int:
    """指定側から見た盤上の未成飛車の移動先候補数差を返す。

    引数:
        position: 読み取り対象の盤面・手番・持ち駒を持つ局面。
        perspective: 評価の視点となる先手または後手。

    戻り値:
        視点側の未成飛車ごとの候補数合計から、相手側の合計を引いた整数。
        相手駒のマスは数え、味方駒のマスと盤外は数えない。

    副作用:
        なし。盤面、手番、双方の持ち駒を変更しない。

    前提条件:
        position内のPieceが有効な駒種と所属を表し、perspectiveはSideである。

    駒得評価と分けて交換できる読み取り部品にするため、候補生成だけを
    movegenへ委ねる。合法手、自玉の安全、相手の利き、成りの別候補は扱わず、
    盤上のPieceType.ROOKごとに既存の候補マスを数える。駒ごとの候補を合算し、
    同じマスへ届く複数の飛車もそれぞれの寄与として残す。
    """
    opponent = Side.GOTE if perspective == Side.SENTE else Side.SENTE
    totals = {perspective: 0, opponent: 0}

    for file in range(1, 10):
        for rank in range(1, 10):
            source = Square(file, rank)
            piece = position.board.piece_at(source)
            if piece is None or piece.piece_type != PieceType.ROOK:
                continue
            totals[piece.side] += len(rook_move_candidates(position.board, source))

    return totals[perspective] - totals[opponent]
