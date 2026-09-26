"""指し手入力の解析と、標準入出力による対局進行を扱う。"""

import random
from dataclasses import dataclass
from typing import Callable, Optional, Union

from .display import render_position
from .game_record import GameRecord
from .move import BoardMove, DropMove, Move
from .model import BasicPieceType, Side, Square, create_initial_position
from .movegen import choose_weak_move, is_game_over, legal_moves


FORMAT_ERROR = "入力形式が正しくありません。"


@dataclass(frozen=True)
class _MoveCommand:
    """盤上移動の入力を、合法性判定前の値として保持する。"""

    source: Square
    destination: Square
    promote: bool


@dataclass(frozen=True)
class _DropCommand:
    """駒打ちの入力を、合法性判定前の値として保持する。"""

    piece_type: BasicPieceType
    destination: Square


@dataclass(frozen=True)
class _ResignCommand:
    """投了の入力を、局面を変更しない終局指示として保持する。"""


_PIECE_NAMES = {
    BasicPieceType.PAWN: "歩",
    BasicPieceType.LANCE: "香",
    BasicPieceType.KNIGHT: "桂",
    BasicPieceType.SILVER: "銀",
    BasicPieceType.GOLD: "金",
    BasicPieceType.BISHOP: "角",
    BasicPieceType.ROOK: "飛",
}


def parse_command(text: str) -> Union[_MoveCommand, _DropCommand,
                                        _ResignCommand]:
    """入力文字列を盤上移動または駒打ちの指示へ変換する。

    引数:
        text: `move`、`drop`、または `resign` のCLI入力。区切りは半角・全角空白、
            筋段は半角・全角数字を受け付ける。

    戻り値:
        盤上移動なら元・先のSquareと成り指定を持つ内部値、駒打ちなら基本駒種と
        打ち先を持つ内部値、投了なら局面を変更しない投了指示。

    例外:
        ValueError: 操作語、引数、成り記号、駒名、または座標が入力形式に合わない場合。

    副作用:
        局面を変更しない。候補内か、手番に合うか、二歩かなどの合法性はここで判定せず、
        既存のapply_move / apply_dropへ委譲する。文字列を局面処理から分離するための操作である。
    """
    parts = text.split()
    if parts == ["resign"]:
        return _ResignCommand()
    if parts[:1] == ["move"] and len(parts) in (5, 6):
        if len(parts) == 6 and parts[5] != "+":
            raise ValueError(FORMAT_ERROR)
        try:
            return _MoveCommand(
                Square(int(parts[1]), int(parts[2])),
                Square(int(parts[3]), int(parts[4])),
                len(parts) == 6,
            )
        except ValueError as error:
            raise ValueError(FORMAT_ERROR) from error

    piece_types = {
        "歩": BasicPieceType.PAWN,
        "香": BasicPieceType.LANCE,
        "桂": BasicPieceType.KNIGHT,
        "銀": BasicPieceType.SILVER,
        "金": BasicPieceType.GOLD,
        "角": BasicPieceType.BISHOP,
        "飛": BasicPieceType.ROOK,
    }
    if parts[:1] == ["drop"] and len(parts) == 4:
        try:
            return _DropCommand(
                piece_types[parts[1]],
                Square(int(parts[2]), int(parts[3])),
            )
        except (KeyError, ValueError) as error:
            raise ValueError(FORMAT_ERROR) from error

    raise ValueError(FORMAT_ERROR)


def _apply_command(record: GameRecord,
                   command: Union[_MoveCommand, _DropCommand]) -> None:
    """解析済みの指示を対局記録の操作へ一度だけ渡す。

    引数:
        record: 開始局面と成功手の履歴を保持する対局記録。
        command: 形式解析済みの盤上移動または駒打ちのデータ。

    戻り値:
        なし（None）。合法な指示ならrecordの現在局面と履歴が更新される。

    副作用:
        `GameRecord`へ委譲し、合法性エラー時は記録を変更しない。入力イベントの
        解析と履歴更新を分離し、成功した指し手だけを棋譜へ残すための操作である。
    """
    if isinstance(command, _MoveCommand):
        record.apply_move(command.source, command.destination,
                          promote=command.promote)
        return
    record.apply_drop(command.piece_type, command.destination)


def _is_human_turn(side: Side) -> bool:
    """今回の対局設定で、指定手番を人間が担当するか返す。"""
    return side == Side.SENTE


def _apply_selected_move(record: GameRecord, move: Move) -> None:
    """合法手データを既存のGameRecord操作へ変換して適用する。"""
    if isinstance(move, BoardMove):
        record.apply_move(move.source, move.destination,
                          promote=move.promote)
        return
    if isinstance(move, DropMove):
        record.apply_drop(move.piece_type, move.destination)
        return
    raise TypeError("未知の合法手データです")


def _format_selected_move(move: Move) -> str:
    """コンピュータの合法手を既存CLI形式の文字列へ変換する。"""
    if isinstance(move, BoardMove):
        suffix = " +" if move.promote else ""
        return (f"move {move.source.file} {move.source.rank} "
                f"{move.destination.file} {move.destination.rank}{suffix}")
    if isinstance(move, DropMove):
        return (f"drop {_PIECE_NAMES[move.piece_type]} "
                f"{move.destination.file} {move.destination.rank}")
    raise TypeError("未知の合法手データです")


def _run_computer_turn(record: GameRecord, rng: random.Random,
                       output_fn: Callable[[str], None]) -> bool:
    """後手の合法手を一つ選んで適用し、成功したかを返す。

    合法手が空の場合は選択不能を勝敗や投了へ変換せず、専用メッセージを表示して
    Falseを返す。選択された手は適用前に表示し、成功後の局面を表示する。
    """
    moves = legal_moves(record.current_position)
    selected = choose_weak_move(moves, rng)
    if selected is None:
        output_fn("コンピュータの合法手がありません。")
        return False
    side_name = ("先手" if record.current_position.side_to_move == Side.SENTE
                 else "後手")
    output_fn(side_name + "の指し手: " + _format_selected_move(selected))
    _apply_selected_move(record, selected)
    output_fn(render_position(record.current_position))
    return True


def _resignation_message(side_to_move: Side) -> str:
    """投了した手番側と、その相手の勝者表示を作る。"""
    loser_name = "先手" if side_to_move == Side.SENTE else "後手"
    winner_name = "後手" if side_to_move == Side.SENTE else "先手"
    return f"{loser_name}が投了しました。{winner_name}の勝ちです。"


def _checkmate_message(side_to_move: Side) -> str:
    """詰まされた手番から勝者表示を作る。"""
    winner = Side.GOTE if side_to_move == Side.SENTE else Side.SENTE
    winner_name = "先手" if winner == Side.SENTE else "後手"
    return f"詰みです。{winner_name}の勝ちです。"


def run_game(*, input_fn: Callable[[], str] = input,
             output_fn: Callable[[str], None] = print,
             rng: Optional[random.Random] = None) -> GameRecord:
    """初期局面から、人間先手とコンピュータ後手の対局を進める。

    引数:
        input_fn: 人間の入力文字列を一つ返す操作。テストでは端末のinputを差し替える。
        output_fn: 盤面・案内・自動手の表示文字列を一つ受け取る操作。
        rng: コンピュータ手の選択に使う乱数生成器。省略時は対局開始時に一個だけ
            生成し、その対局の全自動手で使う。テストでは固定種を注入できる。

    戻り値:
        詰み、投了、EOF、Ctrl-C、またはコンピュータの合法手空一覧で終了した時点の
        `GameRecord`。人間・コンピュータ双方の成功したmove / dropだけを履歴に含め、
        終了イベントは履歴に含めない。

    副作用:
        初期局面から記録を作り、局面表示、入力案内、自動手の表示をoutput_fnへ渡す。
        合法な入力と自動手だけが記録の現在局面と履歴を変更し、形式・合法性エラーでは
        人間の同じ手番で再入力する。`resign` は人間先手の投了として表示し、局面を
        変更せず終了する。

    前提条件:
        各手番の行動前に詰みを優先して確認する。EOF/Ctrl-Cと合法手空一覧は投了や勝敗に
        変換しない。先手を人間、後手をコンピュータとする担当境界を分け、将来の担当切替
        をこの進行層へ閉じ込める。標準のinputとprintは差し替え可能である。
    """
    if rng is None:
        rng = random.Random()
    record = GameRecord(create_initial_position())
    output_fn(render_position(record.current_position))
    while True:
        position = record.current_position
        if is_game_over(position):
            output_fn(_checkmate_message(position.side_to_move))
            return record

        if not _is_human_turn(position.side_to_move):
            if not _run_computer_turn(record, rng, output_fn):
                return record
            continue

        output_fn("指し手を入力してください（例: move 7 7 7 6）:")
        try:
            command = parse_command(input_fn())
            if isinstance(command, _ResignCommand):
                output_fn(_resignation_message(position.side_to_move))
                return record
            _apply_command(record, command)
        except (EOFError, KeyboardInterrupt):
            output_fn("入力を終了しました。")
            return record
        except ValueError as error:
            output_fn("エラー：" + str(error))
            continue
        output_fn(render_position(record.current_position))
