"""指し手入力の解析と、標準入出力による対局進行を扱う。"""

from dataclasses import dataclass
from typing import Callable, Union

from .display import render_position
from .model import BasicPieceType, Position, Side, Square, create_initial_position
from .movegen import apply_drop, apply_move, is_game_over


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


def _apply_command(position: Position,
                   command: Union[_MoveCommand, _DropCommand]) -> None:
    """解析済みの指示を対応する既存の局面操作へ一度だけ渡す。"""
    if isinstance(command, _MoveCommand):
        apply_move(position, command.source, command.destination,
                    promote=command.promote)
        return
    apply_drop(position, command.piece_type, command.destination)


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
             output_fn: Callable[[str], None] = print) -> None:
    """初期局面から入力を受け、合法手または投了まで対局を進める。

    引数:
        input_fn: 入力文字列を一つ返す操作。テストでは端末のinputを差し替える。
        output_fn: 表示文字列を一つ受け取る操作。テストではprintを差し替える。

    戻り値:
        なし（None）。詰み、投了、EOF、Ctrl-Cのいずれかで終了する。

    副作用:
        初期局面を作り、局面表示と入力案内をoutput_fnへ渡す。合法な入力だけが
        Positionを変更し、形式・合法性エラーでは同じ手番で再入力する。`resign` は
        入力時点の手番を投了側として表示し、局面を変更せずに終了する。

    前提条件:
        詰みは入力前に優先して確認する。EOF/Ctrl-Cは投了や勝敗に変換しない。
        標準のinputとprintを差し替え可能にすることで、端末以外でも同じ進行を検証する。
    """
    position = create_initial_position()
    output_fn(render_position(position))
    while True:
        if is_game_over(position):
            output_fn(_checkmate_message(position.side_to_move))
            return

        output_fn("指し手を入力してください（例: move 7 7 7 6）:")
        try:
            command = parse_command(input_fn())
            if isinstance(command, _ResignCommand):
                output_fn(_resignation_message(position.side_to_move))
                return
            _apply_command(position, command)
        except (EOFError, KeyboardInterrupt):
            output_fn("入力を終了しました。")
            return
        except ValueError as error:
            output_fn("エラー：" + str(error))
            continue
        output_fn(render_position(position))
