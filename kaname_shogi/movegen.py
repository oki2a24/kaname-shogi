"""駒の移動先候補を求め、空マスへの移動を盤面へ適用する。

movegenはmove generation（指し手生成）の略。現段階では歩・金・銀・桂・香・飛車・角の移動先、
空いている到着マスへの盤面移動、成功時だけ手番を交代する局面への移動適用を扱う。合法手の確定は
行わない。全駒の専用関数を作る方針はまだ決めず、次の駒を学ぶ際に共有できる処理を検討する。

契約と判断の背景：docs/design/02-pawn-move-candidates.md、
docs/learning/06-pawn-move-candidates.md、docs/design/03-gold-move-candidates.md、
docs/design/04-silver-move-candidates.md、docs/design/05-lance-move-candidates.md、
docs/design/06-rook-move-candidates.md、docs/design/07-bishop-move-candidates.md、
docs/learning/18-knight-move-candidates.md、docs/knowledge/15-knight-move-candidates.md、
docs/design/08-knight-move-candidates.md。
"""

from .model import Board, PieceType, Position, Side, Square


def move_piece(board: Board, source: Square, destination: Square) -> None:
    """空いている到着マスへ駒を移し、渡された盤面を変更する。

    引数:
        board: 変更対象の盤面。
        source: 移動元の筋・段を表すSquare。
        destination: 移動先の筋・段を表すSquare。

    戻り値:
        なし（None）。成功時はboardの配置を変更する。

    例外:
        ValueError: 出発マスが空、到着マスに駒がある、または同じマスを
            出発・到着に指定した場合。不正時は盤面を変更しない。

    移動方向や候補生成結果は検証しない。候補生成と盤面変更を別の責務に
    するため、今回はBoard単位の可変操作として設計している。検証をすべて
    先に行い、成功後に出発マスを空にして到着マスへ同じPieceを置く。
    駒取り、手番更新、成り、王手、合法手判定は扱わない。
    """
    if source == destination:
        raise ValueError("出発マスと到着マスは別にしてください")

    piece = board.piece_at(source)
    if piece is None:
        raise ValueError("出発マスに駒がありません")
    if board.piece_at(destination) is not None:
        raise ValueError("到着マスは空にしてください")

    board.set_piece(source, None)
    board.set_piece(destination, piece)


def _move_candidates_for_piece(board: Board, source: Square) -> list[Square]:
    """sourceの駒種に対応する既存の移動先候補を返す非公開の操作。"""
    piece = board.piece_at(source)
    if piece is None:
        raise ValueError("出発マスに駒がありません")
    candidate_functions = {
        PieceType.KING: king_move_candidates,
        PieceType.ROOK: rook_move_candidates,
        PieceType.BISHOP: bishop_move_candidates,
        PieceType.GOLD: gold_move_candidates,
        PieceType.SILVER: silver_move_candidates,
        PieceType.KNIGHT: knight_move_candidates,
        PieceType.LANCE: lance_move_candidates,
        PieceType.PAWN: pawn_move_candidates,
    }
    return candidate_functions[piece.piece_type](board, source)


def apply_move(position: Position, source: Square, destination: Square) -> None:
    """候補に含まれる到着マスへの移動・駒取り・手番交代を局面へ適用する。

    引数:
        position: 変更対象の盤面と手番を持つ可変の局面。
        source: 移動元の筋・段を表すSquare。
        destination: 移動先の筋・段を表すSquare。

    戻り値:
        なし（None）。成功時だけposition.boardとposition.side_to_moveを変更する。

    例外:
        ValueError: 出発駒の所有者と手番が一致しない場合、到着マスが出発駒の
            移動先候補に含まれない場合、相手の玉を取ろうとした場合、または
            move_pieceが拒否する空の出発マス、同一マスの場合。失敗時は盤面、
            手番、先手・後手の持ち駒を変更しない。

    出発駒の所有者と局面の手番を照合し、既存の移動先候補に到着マスが含まれる
    ときだけ局面を変更する。到着マスが空なら盤面移動をmove_pieceへ委譲する。
    相手駒なら、出発駒を到着マスへ移し、取られた駒種を指した側の持ち駒へ1枚
    加える。これにより、手番を知らないBoardの配置責務と、対局を一手進める
    Positionの局面責務を分ける。玉は持ち駒にならないため取れない。成功後だけ
    手番を交代する。持ち駒を盤へ打つ操作、成り、王手、合法手は検証しない。
    """
    piece = position.board.piece_at(source)
    if piece is not None and piece.side != position.side_to_move:
        raise ValueError("手番と出発駒の所有者が一致しません")
    if (piece is not None
            and destination not in _move_candidates_for_piece(position.board, source)):
        raise ValueError("到着マスは出発駒の移動先候補に含まれません")

    if piece is None:
        move_piece(position.board, source, destination)
    else:
        target_piece = position.board.piece_at(destination)
        if target_piece is None:
            move_piece(position.board, source, destination)
        else:
            if target_piece.piece_type == PieceType.KING:
                raise ValueError("玉は取れません")
            hand = (position.sente_hand if position.side_to_move == Side.SENTE
                    else position.gote_hand)
            hand.add(target_piece.piece_type)
            position.board.set_piece(source, None)
            position.board.set_piece(destination, piece)
    if position.side_to_move == Side.SENTE:
        position.side_to_move = Side.GOTE
    else:
        position.side_to_move = Side.SENTE


def king_move_candidates(board: Board, source: Square) -> list[Square]:
    """出発マスの玉について、周囲8方向の移動先候補を返す。

    `PieceType.KING`は玉（王）を表す駒種のデータであり、
    `king_move_candidates`は候補を求める操作である。玉は先後によらず
    同じ8方向へ1マス進む。盤外と自駒のマスを除き、空マスと相手駒の
    マスを固定順で返す。盤面を変更せず、王手や合法手判定は扱わない。

    引数:
        board: 調べる盤面。
        source: 玉（KING）がある出発マス。

    戻り値:
        上、右上、右、右下、下、左下、左、左上の順の新しいリスト。

    例外:
        ValueError: 出発マスが空、または玉以外の場合。
    """
    piece = board.piece_at(source)
    if piece is None or piece.piece_type != PieceType.KING:
        raise ValueError("出発マスには玉を指定してください")
    offsets = ((0, -1), (-1, -1), (-1, 0), (-1, 1),
               (0, 1), (1, 1), (1, 0), (1, -1))
    candidates = []
    for file_delta, rank_delta in offsets:
        target_file = source.file + file_delta
        target_rank = source.rank + rank_delta
        if not (1 <= target_file <= 9 and 1 <= target_rank <= 9):
            continue
        target = Square(target_file, target_rank)
        occupant = board.piece_at(target)
        if occupant is not None and occupant.side == piece.side:
            continue
        candidates.append(target)
    return candidates


def knight_move_candidates(board: Board, source: Square) -> list[Square]:
    """出発マスの桂馬について、移動先候補を返す。

    `PieceType.KNIGHT`は桂馬を表す駒種のデータであり、
    `knight_move_candidates`はその駒の移動先候補を求める操作である。

    引数:
        board: 調べる盤面。盤面の駒は正しいPieceTypeとSideを持つこと。
        source: 桂馬（KNIGHT）がある出発マス。検証済みのSquareを渡す。

    戻り値:
        右前（筋−1）・左前（筋＋1）の順に、盤内で到達できるマスを並べた
        新しいリスト。先手は段−2、後手は段＋2へ進む。盤外のマスと自駒の
        あるマスは含めず、相手駒のあるマスは含める。途中のマスは調べず、
        桂馬の飛び越しを妨げない。候補がなければ空リストを返す。

    例外:
        ValueError: 出発マスが空、または桂馬以外の場合。
        呼び出しの誤りを通常の候補なしと区別する。

    出発駒のPiece.sideから先後を読み、Position.side_to_moveは参照しないため、
    手番に関係なく先後どちらの桂馬も調べられる。候補計算は盤面を変更せず、
    相手駒も取り除かない。戻り値は呼び出しごとに独立したリストである。
    成桂・成り・行き所のない桂の合法性、駒取り、実際の移動、王手、合法手の
    確定、持ち駒は扱わない。候補順は再現性と読みやすさのためで、指し手の
    優先順位ではない。
    """
    piece = board.piece_at(source)
    if piece is None or piece.piece_type != PieceType.KNIGHT:
        raise ValueError("出発マスには桂馬を指定してください")
    forward = -2 if piece.side == Side.SENTE else 2
    candidates = []
    for file_delta in (-1, 1):
        target_file = source.file + file_delta
        target_rank = source.rank + forward
        if not (1 <= target_file <= 9 and 1 <= target_rank <= 9):
            continue
        target = Square(target_file, target_rank)
        occupant = board.piece_at(target)
        if occupant is not None and occupant.side == piece.side:
            continue
        candidates.append(target)
    return candidates


def bishop_move_candidates(board: Board, source: Square) -> list[Square]:
    """出発マスの角について、斜め4方向の移動先候補を返す。

    引数:
        board: 調べる盤面。駒は正しいPieceTypeとSideを持つこと。
        source: 角（BISHOP）がある出発マス。検証済みのSquareを渡す。

    戻り値:
        右前・左前・右後ろ・左後ろの順に、各方向の近いマスから並べた
        新しいリスト。空マスと最初の相手駒のマスを含み、自駒のマスと
        その先は含めない。候補なしは空リスト。

    例外:
        ValueError: 出発マスが空、または角以外の場合。
        呼び出しの誤りを通常の候補なしと区別する。

    先後は出発マスのPiece.sideから読み、右は筋−1、左は筋＋1とする。
    前は先手なら段−1、後手なら段＋1であり、後ろはその反対である。
    方向ごとに同じ走査を行い、盤外または駒に当たった方向だけを終了する。
    順序は再現性と読みやすさのためで、指し手の優先順位ではない。

    盤面を変更せず、相手駒も取り除かない。手番を持つPositionを受け取らず、
    どちらの角も調べられる。成り・馬・王手は扱わず、合法手の確定ではない。
    飛車との処理共有は、斜め方向の走査を学ぶ今回の範囲では先取りしない。
    """
    piece = board.piece_at(source)
    if piece is None or piece.piece_type != PieceType.BISHOP:
        raise ValueError("出発マスには角を指定してください")

    forward = -1 if piece.side == Side.SENTE else 1
    directions = ((-1, forward), (1, forward), (-1, -forward), (1, -forward))
    candidates = []
    for file_step, rank_step in directions:
        next_file = source.file + file_step
        next_rank = source.rank + rank_step
        while 1 <= next_file <= 9 and 1 <= next_rank <= 9:
            target = Square(next_file, next_rank)
            occupant = board.piece_at(target)
            if occupant is not None and occupant.side == piece.side:
                break
            candidates.append(target)
            if occupant is not None:
                break
            next_file += file_step
            next_rank += rank_step
    return candidates


def rook_move_candidates(board: Board, source: Square) -> list[Square]:
    """出発マスの飛車について、縦横4方向の移動先候補を返す。

    引数:
        board: 調べる盤面。駒は正しいPieceTypeとSideを持つこと。
        source: 飛車（ROOK）がある出発マス。検証済みのSquareを渡す。

    戻り値:
        右・左・前・後ろの順に、各方向の近いマスから並べた新しいリスト。
        空マスと最初の相手駒のマスを含み、自駒のマスとその先は含めない。
        候補なしは空リスト。

    例外:
        ValueError: 出発マスが空、または飛車以外の場合。
        呼び出しの誤りを通常の候補なしと区別する。

    先後は出発マスのPiece.sideから読み、右は筋−1、左は筋＋1とする。
    前は先手なら段−1、後手なら段＋1であり、後ろはその反対である。
    方向ごとに同じ走査を行い、盤外または駒に当たった方向だけを終了する。
    順序は再現性と読みやすさのためで、指し手の優先順位ではない。

    盤面を変更せず、相手駒も取り除かない。手番を持つPositionを受け取らず、
    どちらの飛車も調べられる。成り・王手は扱わず、合法手の確定ではない。
    香との処理共有は、4方向の走査を学ぶ今回の範囲では先取りしない。
    """
    piece = board.piece_at(source)
    if piece is None or piece.piece_type != PieceType.ROOK:
        raise ValueError("出発マスには飛車を指定してください")

    forward = -1 if piece.side == Side.SENTE else 1
    directions = ((-1, 0), (1, 0), (0, forward), (0, -forward))
    candidates = []
    for file_step, rank_step in directions:
        next_file = source.file + file_step
        next_rank = source.rank + rank_step
        while 1 <= next_file <= 9 and 1 <= next_rank <= 9:
            target = Square(next_file, next_rank)
            occupant = board.piece_at(target)
            if occupant is not None and occupant.side == piece.side:
                break
            candidates.append(target)
            if occupant is not None:
                break
            next_file += file_step
            next_rank += rank_step
    return candidates


def lance_move_candidates(board: Board, source: Square) -> list[Square]:
    """出発マスの香について、前方の移動先候補を0〜8個のリストで返す。

    引数:
        board: 調べる盤面。駒は正しいPieceTypeとSideを持つこと。
        source: 香（LANCE）がある出発マス。検証済みのSquareを渡す。

    戻り値:
        同じ筋の前方にあるSquareを、出発点に近い順に並べた新しいリスト。
        自駒の手前または最初の相手駒のマスまでを含む。候補なしは空リスト。
        順序は再現性と読みやすさのためで、強さの優先順位ではない。

    例外:
        ValueError: 出発マスが空、または香以外の場合。
        呼び出しの誤りを通常の候補なしと区別する。

    所有者は盤上のPiece.sideから読み、先手は段−1、後手は段＋1で調べる。
    筋は変えず、段が盤内であることを確かめてからSquareを作る。
    自駒も相手駒も飛び越せないため、駒に当たった時点で繰り返しを止める。
    香の一方向の停止条件を直接読めるよう、飛・角との共有は先取りしない。

    盤面を変更せず、相手駒も取り除かない。手番を持つPositionを受け取らず、
    どちらの香も調べられる。成香・成り・王手は扱わず、合法手の確定ではない。
    最奥段も候補に含み得るが不成を合法と認める意味ではなく、相手の玉の
    マスも含み得るが玉取りを合法と認める意味ではない。
    """
    piece = board.piece_at(source)
    if piece is None or piece.piece_type != PieceType.LANCE:
        raise ValueError("出発マスには香を指定してください")
    forward = -1 if piece.side == Side.SENTE else 1
    candidates = []
    next_rank = source.rank + forward
    while 1 <= next_rank <= 9:
        target = Square(source.file, next_rank)
        occupant = board.piece_at(target)
        if occupant is not None and occupant.side == piece.side:
            break
        candidates.append(target)
        if occupant is not None:
            break
        next_rank += forward
    return candidates


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
