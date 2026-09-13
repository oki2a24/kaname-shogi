"""盤面を変更せず、駒の移動先候補を求める。

movegenはmove generation（指し手生成）の略。現段階では歩の移動先のみを
扱い、指し手の適用や合法手の確定は行わない。全駒の専用関数を作る方針は
まだ決めず、次の駒を学ぶ際に共有できる処理を検討する。

契約と判断の背景：docs/design/02-pawn-move-candidates.md、
docs/learning/06-pawn-move-candidates.md。
"""

from .model import Board, PieceType, Side, Square


def pawn_move_candidates(board: Board, source: Square) -> list[Square]:
    """出発マスの歩について、移動先候補を0個または1個のリストで返す。

    引数:
        board: 調べる盤面。正しいPieceTypeとSideを持つ駒が配置されていること。
        source: 歩がある出発マス。検証済みのSquareを渡す。

    戻り値:
        一歩前が盤外または自駒のマスなら新しい空リスト。
        空マスまたは相手駒のマスなら、そのSquareだけを含む新しいリスト。

    例外:
        ValueError: 出発マスが空、または歩（PAWN）以外の場合。
        これは呼び出しの誤りであり、通常の「候補なし」と区別する。

    先後は出発マスのPiece.sideから読む。別引数にして盤上の所有者と
    食い違わせない。手番を持つPositionは受け取らず、どちらの歩も調べられる。
    先手は段−1、後手は段＋1で筋は不変。盤外は計算の通常の結果として
    Square生成前に除外し、Squareの例外を捕捉して候補なしにはしない。

    盤面は変更しない。相手駒があっても取り除かない。成り・王手・手番の
    制約は未検証なので、候補は合法手の確定ではない。相手の玉のマスも
    同じ占有条件で扱うが、玉取りを合法と認める意味ではない。
    """
    piece = board.piece_at(source)
    if piece is None or piece.piece_type != PieceType.PAWN:
        raise ValueError("出発マスには歩を指定してください")

    next_rank = source.rank + (-1 if piece.side == Side.SENTE else 1)
    if not 1 <= next_rank <= 9:
        return []

    target = Square(source.file, next_rank)
    occupant = board.piece_at(target)
    if occupant is not None and occupant.side == piece.side:
        return []
    return [target]
