"""評価操作を差し替えられる一手選択を提供する。"""

import random
from collections.abc import Callable

from .model import Position, Side
from .move import Move
from .movegen import (
    _find_king_square,
    _is_checkmate_for_known_king,
    position_after_move,
)


def choose_one_ply_move(
    position: Position,
    moves: tuple[Move, ...],
    rng: random.Random,
    *,
    evaluate: Callable[[Position, Side], int],
) -> Move | None:
    """指定側視点の評価と一手詰み優先で候補から一手を選ぶ。

    引数:
        position: 合法手の元になった局面。手番を評価視点として固定する。
        moves: positionの合法手を表すタプル。空でもよい。
        rng: 同点候補から一手だけを選ぶ呼出側の乱数生成器。
        evaluate: 適用後の局面と開始側を受け、通常評価の整数を返す読み取り操作。

    戻り値:
        movesが空ならNone。それ以外は、相手を即詰みにする候補を通常点より優先し、
        残る場合はevaluateの値が最大の候補から選んだ一手。

    副作用:
        positionとmovesを変更しない。rngが選択時に一度進み、evaluateが呼ばれる。
        評価例外、未知の手型、不合法手の例外を捕捉せず伝える。

    前提条件:
        movesはpositionの合法手タプル、evaluateは整数を返す読み取り専用操作、
        rngはchoiceを持つ乱数生成器である。

    候補ごとに既存の複製適用を使い、開始側視点を保持して通常点を比較する。
    相手玉の位置は候補手で動かないため選択開始時に一度だけ探し、候補後はそのマス
    への直接利きを調べる。位置が不一致なら公開詰み判定へ戻す。一手詰みだけは
    `(1, 0)`、通常手は `(0, 評価点)` として順序を分けるため、通常評価がどれほど
    大きくても詰みを上回らない。最大点の候補を元の順で集めて抽選を一度だけ行う。
    特定の評価関数をimportせず、別の通常評価へ交換できる。
    """
    if not moves:
        return None

    perspective = position.side_to_move
    opponent = Side.GOTE if perspective == Side.SENTE else Side.SENTE
    opponent_king_square = _find_king_square(position.board, opponent)
    scored_moves: list[tuple[Move, tuple[int, int]]] = []
    for move in moves:
        after = position_after_move(position, move)
        if opponent_king_square is not None and _is_checkmate_for_known_king(
            after, opponent_king_square
        ):
            score = (1, 0)
        else:
            score = (0, evaluate(after, perspective))
        scored_moves.append((move, score))

    best_score = max(score for _, score in scored_moves)
    best_moves = tuple(move for move, score in scored_moves if score == best_score)
    return rng.choice(best_moves)
