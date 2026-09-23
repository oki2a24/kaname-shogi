"""駒の移動先候補を求め、移動・駒取りを局面へ適用する。

movegenはmove generation（指し手生成）の略。現段階では歩・金・銀・桂・香・飛車・角と成駒6種の移動先、
空いている到着マスへの盤面移動、相手駒を取って指した側の持ち駒へ加える局面への移動適用、持ち駒を
空マスへ打つ局面への適用を扱う。成功時だけ手番を交代する。王手を検出し、自玉を相手の利きに残す
移動・駒打ちを拒否する。全駒の専用関数を
作る方針はまだ決めず、次の駒を学ぶ際に共有できる処理を検討する。

契約と判断の背景：docs/design/02-pawn-move-candidates.md、
docs/learning/06-pawn-move-candidates.md、docs/design/03-gold-move-candidates.md、
docs/design/04-silver-move-candidates.md、docs/design/05-lance-move-candidates.md、
docs/design/06-rook-move-candidates.md、docs/design/07-bishop-move-candidates.md、
docs/learning/18-knight-move-candidates.md、docs/knowledge/15-knight-move-candidates.md、
docs/design/08-knight-move-candidates.md、docs/design/13-capture-and-hands.md、
docs/design/14-hand-drops.md。
"""

from typing import Callable, Optional

from .model import (BasicPieceType, Board, Piece, PieceType, Position, Side,
                    Square)


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
        PieceType.PRO_PAWN: pro_pawn_move_candidates,
        PieceType.PRO_LANCE: pro_lance_move_candidates,
        PieceType.PRO_KNIGHT: pro_knight_move_candidates,
        PieceType.PRO_SILVER: pro_silver_move_candidates,
        PieceType.HORSE: horse_move_candidates,
        PieceType.DRAGON: dragon_move_candidates,
    }
    return candidate_functions[piece.piece_type](board, source)


def _opponent_side(side: Side) -> Side:
    """sideと反対の先後を返す非公開の値操作。"""
    return Side.GOTE if side == Side.SENTE else Side.SENTE


def _find_king_square(board: Board, side: Side) -> Optional[Square]:
    """指定側の玉のマスを探し、なければNoneを返す非公開の読み取り操作。"""
    for file in range(1, 10):
        for rank in range(1, 10):
            square = Square(file, rank)
            if board.piece_at(square) == Piece(PieceType.KING, side):
                return square
    return None


def is_in_check(board: Board, side: Side) -> bool:
    """指定側の玉が相手の駒の移動候補に入っているかを返す。

    引数:
        board: 王手を調べる盤面。盤面は変更しない。
        side: 玉を調べる先手・後手。

    戻り値:
        指定側の玉が盤上にあり、相手側のいずれかの駒の既存候補に含まれれば
        True。玉がない部分局面、またはどの相手駒からも攻撃されていない場合は
        False。

    玉の位置と相手側の全駒を盤から読み、既存の駒種別候補生成を再利用する。
    候補生成と同じく、相手駒のマスは候補に含め、長距離駒の遮蔽や桂馬の飛び越しも
    その規則に従う。判定だけを行い、盤面・手番・持ち駒は変更しない。玉がない
    部分局面をFalseとするのは、候補生成を個別に確認する既存テストとの互換性のため。
    """
    king_square = _find_king_square(board, side)
    if king_square is None:
        return False

    opponent = _opponent_side(side)
    for file in range(1, 10):
        for rank in range(1, 10):
            source = Square(file, rank)
            piece = board.piece_at(source)
            if piece is None or piece.side != opponent:
                continue
            if king_square in _move_candidates_for_piece(board, source):
                return True
    return False


def _is_enemy_camp(side: Side, rank: int) -> bool:
    """rank段がsideから見た相手陣（1〜3段または7〜9段）ならTrueを返す。"""
    return rank <= 3 if side == Side.SENTE else rank >= 7


def _promoted_piece_type(piece_type: PieceType) -> PieceType:
    """成れる基本駒種を盤上の成駒種へ変換する。"""
    promoted = {
        PieceType.PAWN: PieceType.PRO_PAWN,
        PieceType.LANCE: PieceType.PRO_LANCE,
        PieceType.KNIGHT: PieceType.PRO_KNIGHT,
        PieceType.SILVER: PieceType.PRO_SILVER,
        PieceType.BISHOP: PieceType.HORSE,
        PieceType.ROOK: PieceType.DRAGON,
    }
    try:
        return promoted[piece_type]
    except KeyError as error:
        raise ValueError("指定した駒種は成れません") from error


def _can_promote(piece: Piece, source: Square, destination: Square) -> bool:
    """駒と移動元・移動先から、成りを選択できるか判定する。"""
    if piece.is_promoted or piece.piece_type in (PieceType.KING, PieceType.GOLD):
        return False
    return (_is_enemy_camp(piece.side, source.rank)
            or _is_enemy_camp(piece.side, destination.rank))


def _must_promote(piece: Piece, destination: Square) -> bool:
    """歩・香・桂が到達先で不成にできないか判定する。"""
    last_rank = 1 if piece.side == Side.SENTE else 9
    if piece.piece_type in (PieceType.PAWN, PieceType.LANCE):
        return destination.rank == last_rank
    if piece.piece_type == PieceType.KNIGHT:
        second_last_rank = 2 if piece.side == Side.SENTE else 8
        return destination.rank in (last_rank, second_last_rank)
    return False


def _apply_move_unchecked(position: Position, source: Square,
                          destination: Square, *, promote: bool = False) -> None:
    """自玉の安全確認を除く移動規則を局面へ適用する非公開操作。

    引数:
        position: 変更対象の盤面と手番を持つ可変の局面。
        source: 移動元の筋・段を表すSquare。
        destination: 移動先の筋・段を表すSquare。
        promote: 成りを選択するならTrue。省略時は不成として扱う。

    戻り値:
        なし（None）。成功時だけposition.boardとposition.side_to_moveを変更する。
        駒取りの成功時は、指した側の持ち駒も変更する。

    例外:
        ValueError: 出発駒の所有者と手番が一致しない場合、到着マスが出発駒の
            移動先候補に含まれない場合、相手の玉を取ろうとした場合、または
            成れない駒への成り指定、成りが必要な局面での不成指定、move_pieceが拒否する
            空の出発マス、同一マスの場合。失敗時は盤面、
            手番、先手・後手の持ち駒を変更しない。

    出発駒の所有者と局面の手番を照合し、既存の移動先候補に到着マスが含まれる
    ときだけ局面を変更する。成りは移動元または移動先が相手陣にある場合だけ
    選択でき、歩・香・桂が行き所を失う場合は強制される。成駒は成駒自身の候補を
    用いて移動し、移動後も成駒のまま保持する。到着マスが空なら盤面移動をmove_pieceへ委譲する。
    相手駒なら、出発駒を到着マスへ移し、取られた駒種を指した側の持ち駒へ1枚
    加える。これにより、手番を知らないBoardの配置責務と、対局を一手進める
    Positionの局面責務を分ける。玉は持ち駒にならないため取れない。成功後だけ
    手番を交代する。自玉が相手の利きに残るかは呼び出し側で確認する。
    """
    piece = position.board.piece_at(source)
    if piece is not None and piece.side != position.side_to_move:
        raise ValueError("手番と出発駒の所有者が一致しません")
    if (piece is not None
            and destination not in _move_candidates_for_piece(position.board, source)):
        raise ValueError("到着マスは出発駒の移動先候補に含まれません")
    if piece is not None:
        if promote and not _can_promote(piece, source, destination):
            raise ValueError("この移動では成れません")
        if not promote and _must_promote(piece, destination):
            raise ValueError("この移動では成りが必要です")

    moving_piece = (Piece(_promoted_piece_type(piece.piece_type), piece.side)
                    if piece is not None and promote else piece)

    if piece is None:
        move_piece(position.board, source, destination)
    else:
        target_piece = position.board.piece_at(destination)
        if target_piece is None:
            if moving_piece is piece:
                move_piece(position.board, source, destination)
            else:
                position.board.set_piece(source, None)
                position.board.set_piece(destination, moving_piece)
        else:
            if target_piece.piece_type == PieceType.KING:
                raise ValueError("玉は取れません")
            hand = (position.sente_hand if position.side_to_move == Side.SENTE
                    else position.gote_hand)
            hand.add(target_piece.base_piece_type)
            position.board.set_piece(source, None)
            position.board.set_piece(destination, moving_piece)
    if position.side_to_move == Side.SENTE:
        position.side_to_move = Side.GOTE
    else:
        position.side_to_move = Side.SENTE


def _apply_if_king_safe(position: Position,
                        apply_unchecked: Callable[[Position], None]) -> None:
    """複製局面で試し指しし、自玉が安全なら本物へ同じ操作を適用する。"""
    side = position.side_to_move
    trial = position.copy()
    apply_unchecked(trial)
    if is_in_check(trial.board, side):
        raise ValueError("自玉が王手になる手は指せません")
    apply_unchecked(position)


def apply_move(position: Position, source: Square, destination: Square,
               *, promote: bool = False) -> None:
    """候補内の移動を試し指しし、自玉が安全な場合だけ局面へ適用する。

    引数:
        position: 変更対象の盤面・手番・持ち駒を持つ可変の局面。
        source: 移動元の筋・段を表すSquare。
        destination: 移動先の筋・段を表すSquare。
        promote: 成りを選択するならTrue。省略時は不成として扱う。

    戻り値:
        なし（None）。成功時だけpositionの盤面・持ち駒・手番を変更する。

    例外:
        ValueError: 既存の移動規則に反する場合、または試し指し後に自玉が
            相手の利きに残る場合。失敗時は本物の局面を変更しない。

    既存の成り、駒取り、手番交代などの検証は `_apply_move_unchecked` と同じである。
    成り、駒取り、手番交代などの既存検証に成功した後、独立した複製局面で
    試し指しを行う。指した側の玉が相手の利きに残る場合は `ValueError` とし、
    本物の盤面・持ち駒・手番を変更しない。相手玉への王手は許可するが、
    詰みと打ち歩詰めは検証しない。
    """
    _apply_if_king_safe(
        position,
        lambda trial: _apply_move_unchecked(
            trial, source, destination, promote=promote))


def _has_unpromoted_pawn_on_file(board: Board, side: Side, file: int) -> bool:
    """sideの未成の歩がfile筋にあればTrueを返し、盤面を変更しない。

    引数:
        board: 調べる盤面。内容は変更しない。
        side: 歩の所有者として調べる先手・後手。
        file: 調べる筋。公開操作ではないため、apply_dropからSquare.fileを渡す。

    戻り値:
        指定筋の1段から9段に、指定側の未成の歩が1枚でもあればTrue。なければ
        False。

    PieceType.PAWNだけを未成の歩として扱い、PieceType.PRO_PAWN（と金）は二歩の
    対象から除外する。持ち駒の基本駒種とは異なり、盤上の成り状態を判定する。
    """
    for rank in range(1, 10):
        piece = board.piece_at(Square(file, rank))
        if piece == Piece(PieceType.PAWN, side):
            return True
    return False


def _has_no_legal_destination(piece_type: BasicPieceType, side: Side,
                              rank: int) -> bool:
    """piece_typeをsideがrank段へ打ったとき行き所がなければTrueを返す。

    引数:
        piece_type: 打つ基本駒種を表すデータ。
        side: 打つ先手・後手を表す値。
        rank: 打ち先の段を表す1〜9の整数。公開操作ではないため、apply_dropから
            Square.rankを渡す。

    戻り値:
        歩・香・桂を打った直後に一度も進めない段ならTrue、それ以外ならFalse。

    盤面・持ち駒・手番は変更しない。盤面を読まない判定にすることで、二歩の筋を
    走査する判定と責務を分ける。
    """
    last_rank = 1 if side == Side.SENTE else 9
    if piece_type in (BasicPieceType.PAWN, BasicPieceType.LANCE):
        return rank == last_rank
    if piece_type == BasicPieceType.KNIGHT:
        second_last_rank = 2 if side == Side.SENTE else 8
        return rank in (last_rank, second_last_rank)
    return False


def _apply_drop_unchecked(position: Position, piece_type: BasicPieceType,
                          destination: Square) -> None:
    """自玉の安全確認を除く駒打ち規則を局面へ適用する非公開操作。

    引数:
        position: 変更対象の盤面、手番、双方の持ち駒を持つ可変の局面。
        piece_type: 打つ玉以外の基本駒種を表すデータ。
        destination: 打ち先の筋・段を表すSquare。

    戻り値:
        なし（None）。成功時は手番側の持ち駒を1枚減らし、その側のPieceを
        destinationへ置き、手番を交代する。

    例外:
        ValueError: 玉を指定した場合、手番側が指定駒種を持たない場合、
            destinationが占有されている場合、持ち歩を打つ同じ筋に手番側の
            未成の歩がある場合、または歩・香・桂を行き所のない段へ打つ場合。
            失敗時は盤面、手番、先手・後手の持ち駒を変更しない。

        駒打ちは盤上の出発マスと移動先候補を持たないため、盤上移動のapply_moveと
        分ける。歩を打つときは二歩を検証する。歩・香・桂は行き所のない段への
        打ちも検証する。自玉が相手の利きに残るかは呼び出し側で確認する。
    """
    if piece_type == BasicPieceType.KING:
        raise ValueError("玉は打てません")
    if position.board.piece_at(destination) is not None:
        raise ValueError("到着マスは空にしてください")
    if (piece_type == BasicPieceType.PAWN
            and _has_unpromoted_pawn_on_file(position.board,
                                             position.side_to_move,
                                             destination.file)):
        raise ValueError("同じ筋に歩があるため二歩です")
    if _has_no_legal_destination(piece_type, position.side_to_move,
                                 destination.rank):
        raise ValueError("行き所のない段へは打てません")

    hand = (position.sente_hand if position.side_to_move == Side.SENTE
            else position.gote_hand)
    hand.remove(piece_type)
    position.board.set_piece(
        destination,
        Piece(PieceType[piece_type.name], position.side_to_move))
    if position.side_to_move == Side.SENTE:
        position.side_to_move = Side.GOTE
    else:
        position.side_to_move = Side.SENTE


def _apply_drop(position: Position, piece_type: BasicPieceType,
                destination: Square, *, check_uchi_fuzume: bool) -> None:
    """駒打ちを適用し、必要なら打ち歩詰めを拒否する非公開操作。"""
    side = position.side_to_move
    trial = position.copy()
    _apply_drop_unchecked(trial, piece_type, destination)
    if is_in_check(trial.board, side):
        raise ValueError("自玉が王手になる手は指せません")
    if (check_uchi_fuzume and piece_type == BasicPieceType.PAWN
            and _is_checkmate(trial, check_uchi_fuzume=False)):
        raise ValueError("打ち歩詰めはできません")
    _apply_drop_unchecked(position, piece_type, destination)


def apply_drop(position: Position, piece_type: BasicPieceType,
               destination: Square) -> None:
    """持ち駒を試し打ちし、自玉が安全な場合だけ局面へ適用する。

    引数:
        position: 変更対象の盤面・手番・持ち駒を持つ可変の局面。
        piece_type: 打つ玉以外の基本駒種を表すデータ。
        destination: 打ち先の筋・段を表すSquare。

    戻り値:
        なし（None）。成功時だけ指定側の持ち駒、盤面、手番を変更する。

    例外:
        ValueError: 玉、持ち駒不足、占有マス、二歩、行き所のない段、または
            試し打ち後に自玉が相手の利きに残る場合。失敗時は本物の局面を変更しない。

    既存の玉・占有・持ち駒・二歩・行き所のない駒の検証を行った後、独立した
    複製局面で試し打ちする。打った側の玉が相手の利きに残る場合、または持ち歩で
    相手玉へ解除不能な王手をかける場合は `ValueError` とし、本物の盤面・持ち駒・
    手番を変更しない。打ち歩詰めの確認中は非公開操作で再帰を一段止める。
    """
    _apply_drop(position, piece_type, destination, check_uchi_fuzume=True)


def _has_legal_move(position: Position, *, check_uchi_fuzume: bool) -> bool:
    """指定方針で、手番側に合法手があるかを返す非公開操作。"""
    for file in range(1, 10):
        for rank in range(1, 10):
            source = Square(file, rank)
            piece = position.board.piece_at(source)
            if piece is None or piece.side != position.side_to_move:
                continue
            for destination in _move_candidates_for_piece(position.board, source):
                for promote in (False, True):
                    try:
                        apply_move(position.copy(), source, destination,
                                   promote=promote)
                    except ValueError:
                        continue
                    return True

    for piece_type in BasicPieceType:
        if piece_type == BasicPieceType.KING:
            continue
        for file in range(1, 10):
            for rank in range(1, 10):
                try:
                    _apply_drop(position.copy(), piece_type,
                                Square(file, rank),
                                check_uchi_fuzume=check_uchi_fuzume)
                except ValueError:
                    continue
                return True
    return False


def has_legal_move(position: Position) -> bool:
    """手番側に現在実装済みの規則で指せる手が一つでもあるかを返す。

    引数:
        position: 調べる盤面、手番、先後の持ち駒を持つ局面。

    戻り値:
        手番側の盤上移動または駒打ちを一つでも適用できるならTrue。全候補が
        既存規則で拒否されるならFalse。

    副作用:
        positionの盤面、手番、双方の持ち駒を変更しない。

    手番側の全駒の既存候補を調べ、不成と成りの両方を複製局面へ試し指しする。
    さらに玉以外の全持ち駒種と全81マスを複製局面へ試し打ちする。既存の
    apply_moveとapply_dropに、成り、二歩、行き所のない駒、自玉の安全、打ち歩詰めの
    検証を委ねることで、詰み判定用に同じ規則を重複実装しない。
    """
    return _has_legal_move(position, check_uchi_fuzume=True)


def _is_checkmate(position: Position, *, check_uchi_fuzume: bool) -> bool:
    """指定方針で、手番側が詰みかを返す非公開操作。"""
    side = position.side_to_move
    if _find_king_square(position.board, side) is None:
        return False
    return (is_in_check(position.board, side)
            and not _has_legal_move(position,
                                    check_uchi_fuzume=check_uchi_fuzume))


def is_checkmate(position: Position) -> bool:
    """手番側が王手を受け、合法手がなければ詰みかを返す。

    引数:
        position: 調べる盤面、手番、先後の持ち駒を持つ局面。

    戻り値:
        手番側の玉が盤上にあり王手を受け、現在実装済みの規則で防ぐ手が
        一つもないときTrue。それ以外はFalse。

    副作用:
        positionの盤面、手番、双方の持ち駒を変更しない。

    詰みは防ぎようのない王手なので、王手でない局面を合法手なしだけで詰みには
    しない。玉がない部分局面も、既存のis_in_checkと同じく詰みではないFalseと
    する。終局規則のうち投了、千日手、持将棋、入玉、反則勝敗、打ち歩詰めは
    この操作の対象外である。
    """
    return _is_checkmate(position, check_uchi_fuzume=True)


def is_game_over(position: Position) -> bool:
    """今回の範囲で、詰みによって対局が終局かを返す。

    引数:
        position: 調べる盤面、手番、先後の持ち駒を持つ局面。

    戻り値:
        今回唯一扱う終局である詰みならTrue、それ以外ならFalse。

    副作用:
        positionの盤面、手番、双方の持ち駒を変更しない。

    終局という判定を詰みから分けることで、将来に投了や千日手などを扱う場所を
    明確にする。今回の終局範囲は詰みだけなので、is_checkmateの結果を返す。
    """
    return is_checkmate(position)


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


def _gold_like_move_candidates(board: Board, source: Square) -> list[Square]:
    """金と同じ6方向を、駒種検証済みの成駒について調べる非公開操作。"""
    piece = board.piece_at(source)
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


def _promoted_minor_candidates(board: Board, source: Square,
                               piece_type: PieceType,
                               name: str) -> list[Square]:
    """指定した金相当の成駒だけを受け付け、候補を返す非公開操作。"""
    piece = board.piece_at(source)
    if piece is None or piece.piece_type != piece_type:
        raise ValueError(f"出発マスには{name}を指定してください")
    return _gold_like_move_candidates(board, source)


def pro_pawn_move_candidates(board: Board, source: Square) -> list[Square]:
    """と金（PRO_PAWN）の金と同じ移動先候補を返す。"""
    return _promoted_minor_candidates(board, source, PieceType.PRO_PAWN, "と金")


def pro_lance_move_candidates(board: Board, source: Square) -> list[Square]:
    """成香（PRO_LANCE）の金と同じ移動先候補を返す。"""
    return _promoted_minor_candidates(board, source, PieceType.PRO_LANCE, "成香")


def pro_knight_move_candidates(board: Board, source: Square) -> list[Square]:
    """成桂（PRO_KNIGHT）の金と同じ移動先候補を返す。"""
    return _promoted_minor_candidates(board, source, PieceType.PRO_KNIGHT, "成桂")


def pro_silver_move_candidates(board: Board, source: Square) -> list[Square]:
    """成銀（PRO_SILVER）の金と同じ移動先候補を返す。"""
    return _promoted_minor_candidates(board, source, PieceType.PRO_SILVER, "成銀")


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


def horse_move_candidates(board: Board, source: Square) -> list[Square]:
    """馬（HORSE）の角の長距離と縦横1マスの候補を返す。"""
    piece = board.piece_at(source)
    if piece is None or piece.piece_type != PieceType.HORSE:
        raise ValueError("出発マスには馬を指定してください")
    forward = -1 if piece.side == Side.SENTE else 1
    directions = ((-1, forward), (1, forward), (-1, -forward),
                  (1, -forward))
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
    for file_step, rank_step in ((0, forward), (-1, 0),
                                 (0, -forward), (1, 0)):
        next_file, next_rank = source.file + file_step, source.rank + rank_step
        if not (1 <= next_file <= 9 and 1 <= next_rank <= 9):
            continue
        target = Square(next_file, next_rank)
        occupant = board.piece_at(target)
        if occupant is None or occupant.side != piece.side:
            candidates.append(target)
    return candidates


def dragon_move_candidates(board: Board, source: Square) -> list[Square]:
    """竜（DRAGON）の飛車の長距離と斜め1マスの候補を返す。"""
    piece = board.piece_at(source)
    if piece is None or piece.piece_type != PieceType.DRAGON:
        raise ValueError("出発マスには竜を指定してください")
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
    for file_step, rank_step in ((-1, forward), (1, forward),
                                 (-1, -forward), (1, -forward)):
        next_file, next_rank = source.file + file_step, source.rank + rank_step
        if not (1 <= next_file <= 9 and 1 <= next_rank <= 9):
            continue
        target = Square(next_file, next_rank)
        occupant = board.piece_at(target)
        if occupant is None or occupant.side != piece.side:
            candidates.append(target)
    return candidates
