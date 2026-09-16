"""盤面を変更せず、駒の移動先候補を求める。

movegenはmove generation（指し手生成）の略。現段階では歩・金・銀の移動先を
扱い、指し手の適用や合法手の確定は行わない。全駒の専用関数を作る方針は
まだ決めず、次の駒を学ぶ際に共有できる処理を検討する。

契約と判断の背景：docs/design/02-pawn-move-candidates.md、
docs/learning/06-pawn-move-candidates.md、docs/design/03-gold-move-candidates.md、
docs/design/04-silver-move-candidates.md。
"""

from .model import Board, PieceType, Side, Square


def silver_move_candidates(board: Board, source: Square) -> list[Square]:
    """出発マスの銀について、移動先候補を0〜5個のリストで返す。

    引数:
        board: 調べる盤面。駒は正しいPieceTypeとSideを持つこと。
        source: 銀（SILVER）がある出発マス。検証済みのSquareを渡す。

    戻り値:
        盤外と自駒のマスを除いた、移動先Squareの新しいリスト。
        候補なしは空リスト。前、前方の筋＋1、前方の筋−1、後方の筋＋1、
        後方の筋−1の順で返す。再現性のための順序で、強さの優先順位ではない。

    例外:
        ValueError: 出発マスが空、または銀以外の場合。
        呼び出しの誤りを通常の候補なしと区別する。

    先後は盤上のPiece.sideから読み、先手の前は段−1、後手は段＋1。
    筋・段が盤内かを確認してからSquareを作り、通常の盤外を例外にしない。
    金との方向の違いを読み比べられるよう、専用の短い関数と5方向の表を使う。

    盤面を変更せず、相手駒も取り除かない。手番を持つPositionを受け取らず、
    どちらの銀も調べられる。成銀・成り・王手は扱わず、合法手の確定ではない。
    相手の玉のマスも含み得るが、玉取りを合法とする意味ではない。
    """
    piece = board.piece_at(source)
    if piece is None or piece.piece_type != PieceType.SILVER:
        raise ValueError("出発マスには銀を指定してください")
    forward = -1 if piece.side == Side.SENTE else 1
    offsets = ((0, forward), (1, forward), (-1, forward),
               (1, -forward), (-1, -forward))
    candidates = []
    for df, dr in offsets:
        next_file, next_rank = source.file + df, source.rank + dr
        if not (1 <= next_file <= 9 and 1 <= next_rank <= 9):
            continue
        target = Square(next_file, next_rank)
        occupant = board.piece_at(target)
        if occupant is not None and occupant.side == piece.side:
            continue
        candidates.append(target)
    return candidates


def gold_move_candidates(board: Board, source: Square) -> list[Square]:
    """出発マスの金について、移動先候補を0〜6個のリストで返す。

    引数:
        board: 調べる盤面。駒は正しいPieceTypeとSideを持つこと。
        source: 金（GOLD）がある出発マス。検証済みのSquareを渡す。

    戻り値:
        盤外と自駒のマスを除いた、移動先Squareの新しいリスト。
        候補なしは空リスト。前、前方の筋＋1、前方の筋−1、横の筋＋1、
        横の筋−1、真後ろの順で返す。順序は指し手の優先順位ではない。

    例外:
        ValueError: 出発マスが空、または金以外の場合。
        呼び出しの誤りを通常の候補なしと区別する。

    先後は盤上のPiece.sideから読み、先手の前は段−1、後手は段＋1。
    筋・段を盤内と確認してからSquareを作り、通常の盤外に例外を使わない。
    6方向を増減の組で表し、同じ除外条件を順に適用する。

    盤面を変更せず、相手駒も取り除かない。手番を持つPositionを受け取らず、
    どちらの金も調べられる。王手などは検証せず、合法手の確定ではない。
    相手の玉のマスも含み得るが、玉取りを合法とする意味ではない。
    金以外の成り駒への対応や全駒の共通化は、必要になった段階で設計する。
    """
    piece = board.piece_at(source)
    if piece is None or piece.piece_type != PieceType.GOLD:
        raise ValueError("出発マスには金を指定してください")
    forward = -1 if piece.side == Side.SENTE else 1
    offsets = ((0, forward), (1, forward), (-1, forward),
               (1, 0), (-1, 0), (0, -forward))
    candidates = []
    for df, dr in offsets:
        next_file, next_rank = source.file + df, source.rank + dr
        if not (1 <= next_file <= 9 and 1 <= next_rank <= 9):
            continue
        target = Square(next_file, next_rank)
        occupant = board.piece_at(target)
        if occupant is not None and occupant.side == piece.side:
            continue
        candidates.append(target)
    return candidates


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
