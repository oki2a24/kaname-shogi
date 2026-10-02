"""USI局面コマンドを既存の局面履歴と合法手適用へつなぐ。"""

from .game_record import GameRecord
from .model import Position, create_initial_position
from .move import BoardMove, DropMove
from .usi_move import parse_usi_move


def parse_usi_position(command: str) -> Position:
    """USI平手局面コマンドを合法適用し、最後の局面を返す。

    引数:
        command: `position startpos moves` と1手以上のUSI指し手からなる全文。

    戻り値:
        平手初期局面へ全指し手を合法適用した、独立した現在局面。
        指し手の履歴自体は返さない。

    副作用:
        なし。新しいGameRecord内だけで局面を再生し、入力コマンドや他の局面を
        変更しない。

    前提条件:
        対応形式は `position startpos moves <move1> ... <moveN>` のみであり、
        `moves` と1手以上を必要とする。各一手表記はparse_usi_moveの対応形式に従う。

    文法解析を一手表記変換や将棋の合法手規則と混ぜず、既存のGameRecordへ
    一手ずつ委譲することで、USI境界に局面適用規則を重複実装しない。

    例外:
        ValueError: 対応外・不正なコマンド、不正な一手表記、または不合法手の場合。
            一手に起因する場合は、問題の手数とトークンをメッセージに含む。
    """
    tokens = command.split()
    if (
        len(tokens) < 4
        or tokens[0] != "position"
        or tokens[1] != "startpos"
        or tokens[2] != "moves"
    ):
        raise ValueError(
            "USI局面コマンドはposition startpos movesと1手以上で指定してください"
        )

    record = GameRecord(create_initial_position())
    for move_number, token in enumerate(tokens[3:], start=1):
        try:
            move = parse_usi_move(token)
            if isinstance(move, BoardMove):
                record.apply_move(
                    move.source,
                    move.destination,
                    promote=move.promote,
                )
            elif isinstance(move, DropMove):
                record.apply_drop(move.piece_type, move.destination)
            else:
                raise ValueError("USIの一手表記がMove値に変換されません")
        except ValueError as error:
            raise ValueError(
                f"第{move_number}手 ({token}) の解析または局面適用に失敗しました: {error}"
            ) from error

    return record.current_position
