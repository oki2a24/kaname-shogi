"""盤上と持ち駒の駒得評価を共有する。"""

from .model import BasicPieceType, PieceType, Position, Side, Square
from .move import BoardMove, DropMove, Move

# 谷川浩司さんの参考値。成駒を含め、盤上にある駒種ごとの値を記録する。
# https://ocw.hokudai.ac.jp/wp-content/uploads/2016/01/IntelligentInformationProcessing-2005-Note-06.pdf
_TANIGAWA_PIECE_VALUES = {
    PieceType.PAWN: 1,  # 歩
    PieceType.PRO_PAWN: 12,  # と金
    PieceType.LANCE: 5,  # 香
    PieceType.PRO_LANCE: 10,  # 成香
    PieceType.KNIGHT: 6,  # 桂
    PieceType.PRO_KNIGHT: 10,  # 成桂
    PieceType.SILVER: 8,  # 銀
    PieceType.PRO_SILVER: 9,  # 成銀
    PieceType.GOLD: 9,  # 金
    PieceType.BISHOP: 13,  # 角
    PieceType.HORSE: 15,  # 馬
    PieceType.ROOK: 15,  # 飛
    PieceType.DRAGON: 17,  # 竜
}
_TANIGAWA_HAND_VALUES = {
    BasicPieceType.PAWN: 1,  # 歩
    BasicPieceType.LANCE: 5,  # 香
    BasicPieceType.KNIGHT: 6,  # 桂
    BasicPieceType.SILVER: 8,  # 銀
    BasicPieceType.GOLD: 9,  # 金
    BasicPieceType.BISHOP: 13,  # 角
    BasicPieceType.ROOK: 15,  # 飛
}


def piece_reference_value(piece_type: PieceType) -> int:
    """盤上駒の参考価値を既存の駒得評価と同じ表から返す。

    引数:
        piece_type: 価値を調べる有効な盤上駒種。成駒は成った後の駒種で渡す。

    戻り値:
        非玉駒の参考価値を表す整数。

    例外:
        ValueError: 玉には駒得評価用の参考価値を定義していない。

    副作用:
        なし。評価用の設定値を読み取るだけ。

    駒の価値を新しい表へ複製せず、駒得評価が使う正本へ委譲する。成駒の値を
    基本駒へ戻さず、玉に架空の値を与えないことで価値比較の意味を保つ。
    """
    if piece_type == PieceType.KING:
        raise ValueError("玉の参考価値は定義しません")
    return _TANIGAWA_PIECE_VALUES[piece_type]


def material_balance(position: Position, perspective: Side) -> int:
    """盤上と持ち駒の参考点を合算し、指定側から見た駒得差を返す。

    引数:
        position: 評価する盤面・手番・先後の持ち駒を持つ局面。変更しない。
        perspective: 得点を正として見る先手または後手。

    戻り値:
        指定側の非玉駒の合計から相手側の非玉駒の合計を引いた整数。盤上は成駒を
        その駒種の値で数え、持ち駒は基本駒種の値で数える。

    副作用:
        局面と持ち駒を変更しない。

    前提条件:
        Positionの盤面・持ち駒が表す現在状態を評価する。谷川浩司さんの参考値を
        教材用の局面比較に使う。これは通常対局の勝敗規則でも、持将棋・入玉時の
        規則上の点数計算でもない。
    """
    totals = {Side.SENTE: 0, Side.GOTE: 0}
    for file in range(1, 10):
        for rank in range(1, 10):
            piece = position.board.piece_at(Square(file, rank))
            if piece is not None:
                totals[piece.side] += _TANIGAWA_PIECE_VALUES.get(piece.piece_type, 0)

    for side, hand in (
        (Side.SENTE, position.sente_hand),
        (Side.GOTE, position.gote_hand),
    ):
        totals[side] += sum(
            hand.count(piece_type) * value
            for piece_type, value in _TANIGAWA_HAND_VALUES.items()
        )

    opponent = Side.GOTE if perspective == Side.SENTE else Side.SENTE
    return totals[perspective] - totals[opponent]


def _material_balance_after_move(
    before: Position,
    after: Position,
    move: Move,
    perspective: Side,
    base_balance: int,
) -> int:
    """合法一手で変化した駒価値だけを既存Mへ加えて返す非公開操作。

    引数:
        before: 合法手の元局面。
        after: 同じ合法手を独立した局面へ適用した後の状態。
        move: beforeに対して合法な盤上移動または駒打ち。
        perspective: Mを正側とする先手または後手。
        base_balance: `material_balance(before, perspective)` の値。

    戻り値:
        after全体を既存の`material_balance`で走査した値と同じ整数。

    副作用:
        before、after、moveを変更しない。

    前提条件:
        moveはbeforeの合法手であり、afterはその適用結果である。手番交代、持駒の
        更新、駒の成りと捕獲駒の基本駒種化は既存のmovegen操作が完了している。
        この前提下で、全81マスを再走査せず移動元/先・捕獲マスまたは打ち先だけを読む。
    """
    if isinstance(move, BoardMove):
        moved_before = before.board.piece_at(move.source)
        moved_after = after.board.piece_at(move.destination)
        captured = before.board.piece_at(move.destination)
        if moved_before is None or moved_after is None:
            raise ValueError("合法な盤上移動の適用前後に移動駒が必要です")

        old_sign = 1 if moved_before.side is perspective else -1
        new_sign = 1 if moved_after.side is perspective else -1
        delta = new_sign * _TANIGAWA_PIECE_VALUES.get(
            moved_after.piece_type, 0
        ) - old_sign * _TANIGAWA_PIECE_VALUES.get(moved_before.piece_type, 0)
        if captured is not None:
            captured_sign = 1 if captured.side is perspective else -1
            mover_sign = 1 if before.side_to_move is perspective else -1
            delta -= captured_sign * _TANIGAWA_PIECE_VALUES.get(captured.piece_type, 0)
            delta += mover_sign * _TANIGAWA_HAND_VALUES[captured.base_piece_type]
    elif isinstance(move, DropMove):
        placed = after.board.piece_at(move.destination)
        if placed is None:
            raise ValueError("合法な駒打ちの適用後に打ち駒が必要です")
        placed_sign = 1 if placed.side is perspective else -1
        mover_sign = 1 if before.side_to_move is perspective else -1
        delta = (
            placed_sign * _TANIGAWA_PIECE_VALUES.get(placed.piece_type, 0)
            - mover_sign * _TANIGAWA_HAND_VALUES[move.piece_type]
        )
    else:
        raise TypeError("未知の一手です")

    return base_balance + delta
