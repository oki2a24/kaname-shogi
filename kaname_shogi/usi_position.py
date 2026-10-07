"""USI局面コマンドを既存の局面履歴と合法手適用へつなぐ。"""

from .game_record import GameRecord
from .model import create_initial_position
from .move import BoardMove, DropMove
from .sfen import SfenPosition, parse_sfen
from .usi_move import parse_usi_move


def parse_usi_position(command: str) -> SfenPosition:
    """USI局面コマンドを解析し、現在局面とSFEN手数を返す。

    引数:
        command: `position startpos moves ...`、`position sfen <SFEN>`、または
            `position sfen <SFEN> moves ...` 形式の全文。

    戻り値:
        現在局面と1始まりのSFEN手数を組にしたSfenPosition。SFENの手数は維持し、
        `moves` の指し手数だけ進める。`startpos` は手数1から始める。

    副作用:
        なし。新しいGameRecord内だけで局面を再生し、入力コマンドや他の局面を
        変更しない。

    前提条件:
        `startpos` は従来どおり `moves` と1手以上を必要とする。`sfen` はSFEN単独、
        または `moves` と1手以上を指定する。各一手表記はparse_usi_moveの対応形式に従う。

    文法解析を一手表記変換や将棋の合法手規則と混ぜず、既存のGameRecordへ
    一手ずつ委譲することで、USI境界に局面適用規則を重複実装しない。SFEN局面の
    読込は専用変換へ委譲し、Positionへ履歴や手数を追加しない。

    例外:
        ValueError: 対応外・不正なコマンド、不正な一手表記、または不合法手の場合。
            一手に起因する場合は、問題の手数とトークンをメッセージに含む。
    """
    tokens = command.split()
    if len(tokens) < 2 or tokens[0] != "position":
        raise ValueError("USI局面コマンドはpositionで始めてください")

    if tokens[1] == "startpos":
        if len(tokens) < 4 or tokens[2] != "moves":
            raise ValueError(
                "USI startpos局面はmovesと1手以上で指定してください"
            )
        initial_position = create_initial_position()
        base_move_number = 1
        move_tokens = tokens[3:]
    elif tokens[1] == "sfen":
        if len(tokens) < 5:
            raise ValueError("USI SFEN局面に盤面・手番・持ち駒が必要です")
        sfen_fields = tokens[2:5]
        next_index = 5
        if next_index < len(tokens) and tokens[next_index] != "moves":
            sfen_fields.append(tokens[next_index])
            next_index += 1
        sfen_position = parse_sfen(" ".join(sfen_fields))
        if next_index == len(tokens):
            return sfen_position
        if tokens[next_index] != "moves":
            raise ValueError("USI SFEN局面の後はmovesで指し手を指定してください")
        move_tokens = tokens[next_index + 1:]
        if not move_tokens:
            raise ValueError("USI SFEN局面のmovesには1手以上が必要です")
        initial_position = sfen_position.position
        base_move_number = sfen_position.move_number
    else:
        raise ValueError(f"未対応のUSI局面指定です: {tokens[1]}")

    record = GameRecord(initial_position)
    for move_index, token in enumerate(move_tokens, start=1):
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
                f"第{move_index}手 ({token}) の解析または局面適用に失敗しました: {error}"
            ) from error

    return SfenPosition(record.current_position,
                        base_move_number + len(move_tokens))
