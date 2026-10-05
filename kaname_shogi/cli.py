"""指し手入力の解析と、標準入出力による対局進行を扱う。"""

import random
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Union

from .display import render_position
from .game_record import GameRecord
from .move import BoardMove, DropMove, Move
from .model import BasicPieceType, Side, Square, create_initial_position
from .movegen import (MoveSelectionPolicy, choose_move, is_game_over,
                      legal_moves)


__all__ = (
    "GameMode",
    "choose_game_mode",
    "choose_move_selection_policy",
    "MoveCommand",
    "DropCommand",
    "ResignCommand",
    "SaveCommand",
    "LoadCommand",
    "HelpCommand",
    "Command",
    "parse_command",
    "run_game",
)


FORMAT_ERROR = "入力形式が正しくありません。"

_HELP_TEXT = "\n".join((
    "move <出発筋> <出発段> <到着筋> <到着段> [+] — 盤上の駒を動かします。+で成ります。",
    "drop <歩|香|桂|銀|金|角|飛> <筋> <段> — 持ち駒を打ちます。",
    "resign — 投了して対局を終了します。",
    "save <path> — 棋譜を保存します。保存成功後は同じ手番を続けます。",
    "load <path> — 棋譜を読み込みます。読込成功後はその局面から再開します。",
    "筋・段には全角数字も使えます。パスは空白を含まない一語です。",
))


class GameMode(Enum):
    """CLIで対局形式を表し、先後の人間担当を照会するデータ。

    値は人間対人間、人間対コンピュータ、コンピュータ対コンピュータを表す。
    局面や手番を変更せず、現在の先後を人間が入力するかだけを進行層へ返す。
    将棋規則としての先後交代はPositionが担い、対局形式はそれを書き換えない。
    """

    HUMAN_VS_HUMAN = "human_vs_human"
    HUMAN_VS_COMPUTER = "human_vs_computer"
    COMPUTER_VS_COMPUTER = "computer_vs_computer"

    def is_human_turn(self, side: Side) -> bool:
        """sideの手番を人間が入力して担当するならTrueを返す。

        引数:
            side: 担当を調べる先手・後手を表すSide。

        戻り値:
            人間対人間では両側、人間対コンピュータでは先手だけがTrue。
            コンピュータ対コンピュータでは両側ともFalse。

        副作用:
            なし。局面・手番・乱数生成器を変更しない。

        先後が交互に指す規則と、人間・コンピュータの担当設定を分離するため、
        先後そのものではなく対局形式が担当を決める。
        """
        return (self == GameMode.HUMAN_VS_HUMAN
                or (self == GameMode.HUMAN_VS_COMPUTER
                    and side == Side.SENTE))


def choose_game_mode(*, input_fn: Callable[[], str] = input,
                     output_fn: Callable[[str], None] = print) -> GameMode:
    """CLI開始前に対局形式を選び、対応するGameModeを返す。

    引数:
        input_fn: 形式番号を一つ返す入力操作。EOFとCtrl-Cは呼び出し側へ伝える。
        output_fn: メニューと形式エラーを受け取る表示操作。

    戻り値:
        1・2・3に対応するGameMode。無効な入力では返さず、再入力する。

    副作用:
        局面、棋譜、乱数を変更しない。メニューと形式エラーだけを表示する。

    通常CLIとテストが同じ対局形式を選べるよう、文字列番号から進行設定の値へ
    変換する責務を、対局ループから分離する。
    """
    modes = {
        "1": GameMode.HUMAN_VS_HUMAN,
        "2": GameMode.HUMAN_VS_COMPUTER,
        "3": GameMode.COMPUTER_VS_COMPUTER,
    }
    while True:
        output_fn("対局形式を選んでください（1: 人間対人間、"
                  "2: 人間対コンピュータ、3: コンピュータ対コンピュータ）:")
        try:
            return modes[input_fn().strip()]
        except KeyError:
            output_fn("エラー：対局形式を1〜3で選んでください。")


def choose_move_selection_policy(
        input_fn: Callable[[], str] = input,
        output_fn: Callable[[str], None] = print) -> MoveSelectionPolicy:
    """コンピュータの一手選択方針を対局開始前に選ぶ。

    引数:
        input_fn: 方針番号または空入力を一つ返す入力操作。
        output_fn: 選択肢と入力エラーを表示する操作。

    戻り値:
        1なら既存一様ランダムのRANDOM、2なら一手後の駒得比較のMATERIAL。
        空入力はRANDOMを返す。不正入力では返さず再入力する。

    副作用:
        局面、棋譜、乱数を変更せず、メニューとエラーだけを表示する。

    難易度を強さの保証ではなく一手選択方針として示す。現行の一様ランダムを
    最弱の既定値として保ち、入力を対局進行から分離する。
    """
    policies = {
        "1": MoveSelectionPolicy.RANDOM,
        "2": MoveSelectionPolicy.MATERIAL,
    }
    while True:
        output_fn("一手選択方針を選んでください（1: 最弱（一様ランダム）、"
                  "2: 駒得を考える、空入力: 最弱）:")
        choice = input_fn().strip()
        if choice == "":
            return MoveSelectionPolicy.RANDOM
        try:
            return policies[choice]
        except KeyError:
            output_fn("エラー：一手選択方針を1〜2で選んでください。")


@dataclass(frozen=True)
class MoveCommand:
    """解析した盤上移動の指示を、合法性判定前の不変データとして保持する。

    引数:
        source: 出発マスを表すSquare。
        destination: 到着マスを表すSquare。
        promote: 成りを指定するかを表すbool。

    戻り値:
        なし。この型は値を表し、生成は解析済みのMoveCommandを得るために行う。

    副作用:
        なし。局面、手番、履歴、ファイルを変更しない。

    前提条件:
        座標と成り記号の入力形式はparse_commandが検査する。移動候補、手番、王手などの
        合法性は保持せず後段へ委譲し、解析と着手適用を分離する。
    """

    source: Square
    destination: Square
    promote: bool


@dataclass(frozen=True)
class DropCommand:
    """解析した駒打ちの指示を、合法性判定前の不変データとして保持する。

    引数:
        piece_type: 打つ基本駒種を表すBasicPieceType。
        destination: 打ち先のマスを表すSquare。

    戻り値:
        なし。この型は値を表し、生成は解析済みのDropCommandを得るために行う。

    副作用:
        なし。局面、手番、履歴、ファイルを変更しない。

    前提条件:
        駒名と座標の入力形式はparse_commandが検査する。持ち駒、二歩、行き所のない駒
        などの合法性は保持せず後段へ委譲し、解析と駒打ち適用を分離する。
    """

    piece_type: BasicPieceType
    destination: Square


@dataclass(frozen=True)
class ResignCommand:
    """解析した投了の指示を、局面を変更しない不変データとして保持する。

    引数・戻り値:
        なし。この型は属性を持たず、投了という解析済みの指示を表す。

    副作用:
        なし。局面、手番、履歴、ファイルを変更しない。

    前提条件:
        入力形式はparse_commandが検査する。勝者表示と対局終了はrun_gameが担い、解析と
        終局処理を分離する。
    """


@dataclass(frozen=True)
class SaveCommand:
    """解析した保存先を、ファイル操作前の不変データとして保持する。

    引数:
        path: 保存先を表す空白を含まない一語の文字列。

    戻り値:
        なし。この型は値を表し、生成は解析済みのSaveCommandを得るために行う。

    副作用:
        なし。局面、手番、履歴、ファイルを変更しない。

    前提条件:
        パスの語数はparse_commandが検査する。実際の保存とその失敗処理はrun_gameと
        GameRecordが担い、文字列解析とファイル操作を分離する。
    """

    path: str


@dataclass(frozen=True)
class LoadCommand:
    """解析した読込元を、ファイル操作前の不変データとして保持する。

    引数:
        path: 読込元を表す空白を含まない一語の文字列。

    戻り値:
        なし。この型は値を表し、生成は解析済みのLoadCommandを得るために行う。

    副作用:
        なし。局面、手番、履歴、ファイルを変更しない。

    前提条件:
        パスの語数はparse_commandが検査する。実際の読込とその失敗処理はrun_gameと
        GameRecordが担い、文字列解析とファイル操作を分離する。
    """

    path: str


# HelpCommandは解析済みのhelp指示を表す公開データ型である。
@dataclass(frozen=True)
class HelpCommand:
    """解析したヘルプ表示の指示を表す、不変で副作用のない値。

    引数・戻り値:
        なし。この型は属性を持たず、helpという指示の種類を表す。

    副作用:
        なし。局面・手番・棋譜を変更せず、実際の表示はrun_gameが担う。

    前提条件:
        入力形式はparse_commandが検査する。指示の値と表示操作を分けるため、
        この型の生成そのものはヘルプを表示しない。
    """


# Commandは解析済みの6種類の指示のいずれかを表す公開の型別名である。
Command = Union[MoveCommand, DropCommand, ResignCommand, SaveCommand,
                LoadCommand, HelpCommand]


# 駒打ちで入力・表示する基本駒の型と日本語名を、この順序で対応付ける。
_DROP_PIECE_SPECS = (
    (BasicPieceType.PAWN, "歩"),
    (BasicPieceType.LANCE, "香"),
    (BasicPieceType.KNIGHT, "桂"),
    (BasicPieceType.SILVER, "銀"),
    (BasicPieceType.GOLD, "金"),
    (BasicPieceType.BISHOP, "角"),
    (BasicPieceType.ROOK, "飛"),
)

_PIECE_NAMES = dict(_DROP_PIECE_SPECS)
_PIECE_TYPES_BY_NAME = {
    name: piece_type for piece_type, name in _DROP_PIECE_SPECS
}


def parse_command(text: str) -> Command:
    """入力文字列を対局または保存・読込の指示へ変換する。

    引数:
        text: `move`、`drop`、`resign`、`save`、`load`、または `help` のCLI入力。
            区切りは半角・全角空白、筋段は半角・全角数字を受け付ける。
            保存・読込のパスは空白を含まない一語として扱う。

    戻り値:
        盤上移動ならMoveCommand、駒打ちならDropCommand、投了ならResignCommand、
        保存ならSaveCommand、読込ならLoadCommand、ヘルプならHelpCommandのいずれかを
        表すCommand。各型は外部コードが型名と属性を利用できる公開データである。

    例外:
        ValueError: 操作語、引数、成り記号、駒名、または座標が入力形式に合わない場合。

    副作用:
        局面・ファイルを変更しない。候補内か、手番に合うか、二歩かなどの合法性は
        ここで判定せず、既存のapply_move / apply_dropへ委譲する。保存・読込も実行層へ
        渡すだけにして、文字列解析を局面・ファイル処理から分離する。
    """
    parts = text.split()
    if parts == ["resign"]:
        return ResignCommand()
    if parts == ["help"]:
        return HelpCommand()
    if parts[:1] == ["save"] and len(parts) == 2:
        return SaveCommand(parts[1])
    if parts[:1] == ["load"] and len(parts) == 2:
        return LoadCommand(parts[1])
    if parts[:1] == ["move"] and len(parts) in (5, 6):
        if len(parts) == 6 and parts[5] != "+":
            raise ValueError(FORMAT_ERROR)
        try:
            return MoveCommand(
                Square(int(parts[1]), int(parts[2])),
                Square(int(parts[3]), int(parts[4])),
                len(parts) == 6,
            )
        except ValueError as error:
            raise ValueError(FORMAT_ERROR) from error

    if parts[:1] == ["drop"] and len(parts) == 4:
        try:
            return DropCommand(
                _PIECE_TYPES_BY_NAME[parts[1]],
                Square(int(parts[2]), int(parts[3])),
            )
        except (KeyError, ValueError) as error:
            raise ValueError(FORMAT_ERROR) from error

    raise ValueError(FORMAT_ERROR)


def _apply_command(record: GameRecord,
                   command: Union[MoveCommand, DropCommand]) -> None:
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
    if isinstance(command, MoveCommand):
        record.apply_move(command.source, command.destination,
                          promote=command.promote)
        return
    record.apply_drop(command.piece_type, command.destination)


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
                       output_fn: Callable[[str], None],
                       move_selection_policy: MoveSelectionPolicy) -> bool:
    """コンピュータ担当側の合法手を一つ選んで適用し、成功したかを返す。

    合法手が空の場合は選択不能を勝敗や投了へ変換せず、専用メッセージを表示して
    Falseを返す。選択された手は適用前に表示し、成功後の局面を表示する。
    """
    moves = legal_moves(record.current_position)
    selected = choose_move(record.current_position, moves,
                           move_selection_policy, rng)
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
             rng: Optional[random.Random] = None,
             mode: GameMode = GameMode.HUMAN_VS_COMPUTER,
             move_selection_policy: MoveSelectionPolicy =
             MoveSelectionPolicy.RANDOM) -> GameRecord:
    """初期局面から、modeが決める担当で対局を進める。

    引数:
        input_fn: 人間の入力文字列を一つ返す操作。テストでは端末のinputを差し替える。
        output_fn: 盤面・案内・自動手の表示文字列を一つ受け取る操作。
        rng: コンピュータ手の選択に使う乱数生成器。省略時は対局開始時に一個だけ
            生成し、その対局の全自動手で使う。テストでは固定種を注入できる。
        mode: 人間・コンピュータの先後担当を表すGameMode。省略時は既存互換の
            人間先手・コンピュータ後手とする。
        move_selection_policy: コンピュータが一手を選ぶ方針。一局中固定する。省略時は
            現行と同じ一様ランダムのRANDOMとする。

    戻り値:
        詰み、投了、EOF、Ctrl-C、またはコンピュータの合法手空一覧で終了した時点の
        `GameRecord`。人間・コンピュータ双方の成功したmove / dropだけを履歴に含め、
        終了イベントは履歴に含めない。

    副作用:
        初期局面から記録を作り、局面表示、入力案内、自動手の表示をoutput_fnへ渡す。
        合法な入力と自動手だけが記録の現在局面と履歴を変更し、形式・合法性・保存・
        読込エラーでは人間の同じ手番で再入力する。`save` は記録を変更せず保存し、
        `load` は成功したときだけ記録を新しいものへ置き換えて局面を表示する。
        `resign` は人間担当側の投了として表示し、局面を変更せず終了する。人間対人間
        では両側、人間対コンピュータでは先手だけが入力し、コンピュータ対コンピュータ
        では両側が自動手を指す。

    前提条件:
        各手番の行動前に詰みを優先して確認する。EOF/Ctrl-Cと合法手空一覧は投了や勝敗に
        変換しない。先後交代は局面規則、入力・自動手の担当はmodeという境界を分ける。
        `load` 成功後は読込局面の `side_to_move` と `mode` に従って、次の人間入力または
        コンピュータ手へ進む。標準のinputとprintは差し替え可能である。
    """
    if rng is None:
        rng = random.Random()
    record = GameRecord(create_initial_position())
    output_fn(render_position(record.current_position))
    try:
        while True:
            position = record.current_position
            if is_game_over(position):
                output_fn(_checkmate_message(position.side_to_move))
                return record

            if not mode.is_human_turn(position.side_to_move):
                if not _run_computer_turn(record, rng, output_fn,
                                          move_selection_policy):
                    return record
                continue

            output_fn("指し手を入力してください（例: move 7 7 7 6）:")
            try:
                command = parse_command(input_fn())
                if isinstance(command, HelpCommand):
                    output_fn(_HELP_TEXT)
                    continue
                if isinstance(command, SaveCommand):
                    record.save(command.path)
                    output_fn("棋譜を保存しました。")
                    continue
                if isinstance(command, LoadCommand):
                    record = GameRecord.load(command.path)
                    output_fn("棋譜を読み込みました。")
                    output_fn(render_position(record.current_position))
                    continue
                if isinstance(command, ResignCommand):
                    output_fn(_resignation_message(position.side_to_move))
                    return record
                _apply_command(record, command)
            except (ValueError, OSError) as error:
                output_fn("エラー：" + str(error))
                continue
            output_fn(render_position(record.current_position))
    except (EOFError, KeyboardInterrupt):
        output_fn("入力を終了しました。")
        return record
