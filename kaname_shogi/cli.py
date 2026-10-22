"""指し手入力の解析と、標準入出力による対局進行を扱う。"""

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from . import game_search
from .cli_clock import CliClock, CliClockSettings
from .cli_session import CliSession
from .display import render_position
from .game_record import GameRecord
from .model import BasicPieceType, Side, Square, create_initial_position
from .move import BoardMove, DropMove, Move
from .movegen import MoveSelectionPolicy, SearchCompletion, is_game_over
from .repetition import RepetitionOutcome, RepetitionOutcomeKind, RepetitionTracker
from .search_control import SearchControl
from .time_management import (
    TimeManagementConfig,
    calculate_search_budget,
    load_time_management_config,
)

__all__ = (
    "GameMode",
    "choose_game_mode",
    "choose_move_selection_policy",
    "choose_clock_settings",
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

_HELP_TEXT = "\n".join(
    (
        "move <出発筋> <出発段> <到着筋> <到着段> [+] — 盤上の駒を動かします。+で成ります。",
        "drop <歩|香|桂|銀|金|角|飛> <筋> <段> — 持ち駒を打ちます。",
        "resign — 投了して対局を終了します。",
        "save <path> — 棋譜を保存します。保存成功後は同じ手番を続けます。",
        "load <path> — 棋譜を読み込みます。読込成功後はその局面から再開します。",
        "筋・段には全角数字も使えます。パスは空白を含まない一語です。",
    )
)


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
        return self == GameMode.HUMAN_VS_HUMAN or (
            self == GameMode.HUMAN_VS_COMPUTER and side == Side.SENTE
        )


def choose_game_mode(
    *, input_fn: Callable[[], str] = input, output_fn: Callable[[str], None] = print
) -> GameMode:
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
        output_fn(
            "対局形式を選んでください（1: 人間対人間、"
            "2: 人間対コンピュータ、3: コンピュータ対コンピュータ）:"
        )
        try:
            return modes[input_fn().strip()]
        except KeyError:
            output_fn("エラー：対局形式を1〜3で選んでください。")


def choose_move_selection_policy(
    input_fn: Callable[[], str] = input, output_fn: Callable[[str], None] = print
) -> MoveSelectionPolicy:
    """コンピュータの一手選択方針を対局開始前に選ぶ。

    引数:
        input_fn: 方針番号または空入力を一つ返す入力操作。
        output_fn: 選択肢と入力エラーを表示する操作。

    戻り値:
        1なら既存一様ランダムのRANDOM、2なら一手後の駒得比較のMATERIAL、
        3なら二手駒得のTWO_PLY_MATERIAL、4なら全幅四手のFOUR_PLY_FULL_WIDTH、
        5ならαβ四手のFOUR_PLY_ALPHA_BETA。
        空入力はRANDOMを返す。不正入力では返さず再入力する。

    副作用:
        局面、棋譜、乱数を変更せず、メニューとエラーだけを表示する。

    難易度を強さの保証ではなく一手選択方針として示す。現行の一様ランダムを
    既定値として保ち、五方式の選択を対局進行から分離する。新二方式も一局中に固定し、
    各コンピュータ手で深さ1から4まで再探索する。時計は対局管理層が持ち、各手を
    共通探索の制御へ渡す。
    """
    policies = {
        "1": MoveSelectionPolicy.RANDOM,
        "2": MoveSelectionPolicy.MATERIAL,
        "3": MoveSelectionPolicy.TWO_PLY_MATERIAL,
        "4": MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH,
        "5": MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA,
    }
    while True:
        output_fn(
            "一手選択方針を選んでください（1: ランダム、2: 一手駒得、"
            "3: 二手先読み（駒得）、4: 全幅読み（最大4手）、"
            "5: αβ枝刈り（最大4手）、空入力: ランダム）:"
        )
        choice = input_fn().strip()
        if choice == "":
            return MoveSelectionPolicy.RANDOM
        try:
            return policies[choice]
        except KeyError:
            output_fn("エラー：一手選択方針を1〜5で選んでください。")


def choose_clock_settings(
    *,
    input_fn: Callable[[], str] = input,
    output_fn: Callable[[str], None] = print,
) -> CliClockSettings:
    """コンピュータ対局の持ち時間と秒読みを入力して時計設定を返す。

    引数:
        input_fn: 分・秒の入力を一つずつ返す操作。EOFとCtrl-Cは呼出し側へ伝える。
        output_fn: 二欄の案内と入力エラーを表示する操作。

    戻り値:
        分を初期持ち時間ms、秒を秒読みmsへ変換したCliClockSettings。

    副作用:
        二欄を表示し、入力が不正または0と0の組合せなら両欄を再入力する。
        局面、時計、時間予算設定やファイルは変更しない。

    例外:
        EOFError、KeyboardInterrupt: 入力操作から呼出し側へそのまま伝える。

    空入力の10分・30秒は性能から決めた値ではなく、承認済み設計の利用者向け
    初期値である。半角の十進整数だけを受理し、USI入力の符号付き整数表記と分ける。
    """
    while True:
        output_fn("コンピュータの持ち時間（分、空入力10）:")
        initial_minutes_text = input_fn().strip()
        output_fn("秒読み（秒、空入力30）:")
        byoyomi_seconds_text = input_fn().strip()

        try:
            if initial_minutes_text == "":
                initial_minutes = 10
            elif all(character in "0123456789" for character in initial_minutes_text):
                initial_minutes = int(initial_minutes_text)
            else:
                raise ValueError("持ち時間は半角の非負整数で入力してください")

            if byoyomi_seconds_text == "":
                byoyomi_seconds = 30
            elif all(character in "0123456789" for character in byoyomi_seconds_text):
                byoyomi_seconds = int(byoyomi_seconds_text)
            else:
                raise ValueError("秒読みは半角の非負整数で入力してください")

            return CliClockSettings(
                initial_minutes * 60_000,
                byoyomi_seconds * 1_000,
            )
        except ValueError as error:
            output_fn("エラー：" + str(error))


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
Command = (
    MoveCommand | DropCommand | ResignCommand | SaveCommand | LoadCommand | HelpCommand
)


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
_PIECE_TYPES_BY_NAME = {name: piece_type for piece_type, name in _DROP_PIECE_SPECS}


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


def _apply_command(record: GameRecord, command: MoveCommand | DropCommand) -> None:
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
        record.apply_move(command.source, command.destination, promote=command.promote)
        return
    record.apply_drop(command.piece_type, command.destination)


def _apply_selected_move(record: GameRecord, move: Move) -> None:
    """合法手データを既存のGameRecord操作へ変換して適用する。"""
    if isinstance(move, BoardMove):
        record.apply_move(move.source, move.destination, promote=move.promote)
        return
    if isinstance(move, DropMove):
        record.apply_drop(move.piece_type, move.destination)
        return
    raise TypeError("未知の合法手データです")


def _format_selected_move(move: Move) -> str:
    """コンピュータの合法手を既存CLI形式の文字列へ変換する。"""
    if isinstance(move, BoardMove):
        suffix = " +" if move.promote else ""
        return (
            f"move {move.source.file} {move.source.rank} "
            f"{move.destination.file} {move.destination.rank}{suffix}"
        )
    if isinstance(move, DropMove):
        return (
            f"drop {_PIECE_NAMES[move.piece_type]} "
            f"{move.destination.file} {move.destination.rank}"
        )
    raise TypeError("未知の合法手データです")


def _run_computer_turn(
    record: GameRecord,
    repetition_tracker: RepetitionTracker,
    rng: random.Random,
    output_fn: Callable[[str], None],
    move_selection_policy: MoveSelectionPolicy,
    clock: CliClock,
    time_config: TimeManagementConfig,
    now_ns: Callable[[], int],
) -> tuple[CliClock, bool]:
    """共通の制御付き探索から一手を得て、対局時計と成功手を更新する。

    引数:
        record: 現在局面と成功手の履歴を保持する対局記録。
        repetition_tracker: 成功した実着手だけを判定する一局の履歴追跡器。
        rng: 五方式で共有する対局単位の乱数生成器。
        output_fn: 思考開始・結果・盤面を受け取る表示操作。
        move_selection_policy: 一局で固定する五方式の一手選択方針。
        clock: 開始時の残り時間を含む現在のCLI時計。
        time_config: 予算計算に使う対局中固定の時間設定。
        now_ns: 探索開始・返却時点を同じ単調時計で読む操作。

    戻り値:
        更新した時計と続行可否。局面・履歴は時間内に合法手を返した場合だけ進む。

    例外:
        ValueError: 時計の経過が不正、または探索結果が契約に合わない場合。
        探索・時計・表示・棋譜操作からの他の例外はそのまま呼出し側へ伝える。

    副作用:
        対局時計の返却後時間を更新し、時間内に手があれば一度だけ棋譜へ適用して
        表示する。時計の時間切れは探索予算の上限とは独立に、開始時時計と秒読みで
        判定する。抑制結果は手や勝敗へ変換しない。

    コンピュータ手に限って計時し、探索前の詰み確認や全合法手生成をせず、USIと
    同じ `game_search.search_move`、公開予算計算、SearchControlの停止契約を使う。
    """
    side = record.current_position.side_to_move
    side_name = "先手" if side is Side.SENTE else "後手"
    output_fn(side_name + "のコンピュータが思考中です。")
    started_ns = now_ns()
    budget = calculate_search_budget(
        clock.remaining_ns(side) // 1_000_000,
        clock.settings.byoyomi_ms,
        time_config,
    )
    control = SearchControl(budget, started_ns, now_ns=now_ns)
    search_position = record.current_position
    result = game_search.search_move(
        search_position, move_selection_policy, rng, control
    )
    elapsed_ns = now_ns() - started_ns
    updated_clock = clock.after_turn(side, elapsed_ns)

    if result.completion is SearchCompletion.SUPPRESSED:
        output_fn("探索結果が抑制されたため対局を終了しました。")
        return updated_clock, False
    if clock.is_expired(side, elapsed_ns):
        _output_clock_summary(output_fn, side, elapsed_ns, updated_clock)
        winner_name = "後手" if side is Side.SENTE else "先手"
        output_fn(f"{side_name}が時間切れです。{winner_name}の勝ちです。")
        return updated_clock, False
    if result.completion not in (
        SearchCompletion.COMPLETE,
        SearchCompletion.INTERRUPTED,
    ):
        raise ValueError("探索結果の終了状態が不正です")
    completion_name = (
        "完了" if result.completion is SearchCompletion.COMPLETE else "通常停止"
    )
    output_fn("探索状態: " + completion_name)
    _output_clock_summary(output_fn, side, elapsed_ns, updated_clock)
    if result.move is None:
        if result.completion is SearchCompletion.INTERRUPTED:
            raise ValueError("通常停止の探索結果に合法手がありません")
        output_fn(_resignation_message(side))
        return updated_clock, False

    output_fn(side_name + "の指し手: " + _format_selected_move(result.move))
    _apply_selected_move(record, result.move)
    position = record.current_position
    output_fn(render_position(position))
    outcome = repetition_tracker.add_position(position)
    should_continue = not _display_repetition_outcome(outcome, output_fn)
    return updated_clock, should_continue


def _display_repetition_outcome(
    outcome: RepetitionOutcome, output_fn: Callable[[str], None]
) -> bool:
    """千日手判定を表示し、現在の一局を終了する結果ならTrueを返す。"""
    if outcome.kind is RepetitionOutcomeKind.CONTINUE:
        return False
    if outcome.kind is RepetitionOutcomeKind.FOURFOLD_CONTINUE:
        output_fn("同一局面が4回現れました。対局を続けます。")
        return False
    if outcome.kind is RepetitionOutcomeKind.REPETITION:
        output_fn(
            "同一局面が打開後に再出現したため、千日手が成立しました。対局を終了します。"
        )
        return True
    if outcome.kind is RepetitionOutcomeKind.PERPETUAL_CHECK_LOSS:
        loser = outcome.losing_side
        if loser is None:
            raise ValueError("連続王手負けの結果に敗者がありません")
        loser_name = "先手" if loser is Side.SENTE else "後手"
        winner_name = "後手" if loser is Side.SENTE else "先手"
        output_fn(
            f"連続王手の千日手です。{loser_name}の負けです。{winner_name}の勝ちです。"
        )
        return True
    if outcome.kind is RepetitionOutcomeKind.UNRESOLVED_DOUBLE_PERPETUAL_CHECK:
        output_fn("双方が連続王手に該当する局面です。勝者を判定せず対局を停止します。")
        return True
    raise ValueError("千日手判定の結果が不正です")


def _resignation_message(side_to_move: Side) -> str:
    """投了した手番側と、その相手の勝者表示を作る。"""
    loser_name = "先手" if side_to_move == Side.SENTE else "後手"
    winner_name = "後手" if side_to_move == Side.SENTE else "先手"
    return f"{loser_name}が投了しました。{winner_name}の勝ちです。"


def _format_milliseconds_as_seconds(milliseconds: int) -> str:
    """整数msを秒と小数第3位へ切り分ける。"""
    seconds, fractional_ms = divmod(milliseconds, 1_000)
    if fractional_ms == 0:
        return f"{seconds}秒"
    return f"{seconds}.{fractional_ms:03d}秒"


def _format_elapsed_milliseconds(milliseconds: int) -> str:
    """消費時間の整数msを小数第3位まで表示する。"""
    seconds, fractional_ms = divmod(milliseconds, 1_000)
    return f"{seconds}.{fractional_ms:03d}秒"


def _format_clock_time(remaining_ns: int) -> str:
    """残りnsを切り捨てmsとしてMM:SS.mmm形式へ変換する。"""
    total_milliseconds = remaining_ns // 1_000_000
    total_seconds, milliseconds = divmod(total_milliseconds, 1_000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def _output_clock_summary(
    output_fn: Callable[[str], None],
    side: Side,
    elapsed_ns: int,
    updated_clock: CliClock,
) -> None:
    """一手の消費時間と返却後の残り時間を表示する。"""
    side_name = "先手" if side is Side.SENTE else "後手"
    elapsed_milliseconds = elapsed_ns // 1_000_000
    output_fn("消費時間: " + _format_elapsed_milliseconds(elapsed_milliseconds))
    output_fn(
        f"{side_name}の残り持ち時間: "
        f"{_format_clock_time(updated_clock.remaining_ns(side))}"
        f"（秒読み{_format_milliseconds_as_seconds(updated_clock.settings.byoyomi_ms)}）"
    )


def _checkmate_message(side_to_move: Side) -> str:
    """詰まされた手番から勝者表示を作る。"""
    winner = Side.GOTE if side_to_move == Side.SENTE else Side.SENTE
    winner_name = "先手" if winner == Side.SENTE else "後手"
    return f"詰みです。{winner_name}の勝ちです。"


def run_game(
    *,
    input_fn: Callable[[], str] = input,
    output_fn: Callable[[str], None] = print,
    rng: random.Random | None = None,
    mode: GameMode = GameMode.HUMAN_VS_COMPUTER,
    move_selection_policy: MoveSelectionPolicy = MoveSelectionPolicy.RANDOM,
    clock_settings: CliClockSettings | None = None,
    time_config: TimeManagementConfig | None = None,
    now_ns: Callable[[], int] = time.monotonic_ns,
) -> GameRecord:
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
        clock_settings: コンピュータ参加対局の初期持ち時間・秒読み。省略時は10分・30秒。
            人間対人間では時計を作らない。
        time_config: コンピュータ探索の予算設定。省略時は対局開始時に一度だけ読む。
            人間対人間では読み込まない。
        now_ns: コンピュータ手の開始・返却時刻を読む同じ単調時計。テストで注入できる。

    戻り値:
        詰み、投了、時間切れ、応答抑制、千日手、EOFまたはCtrl-Cで終了した時点の`GameRecord`。
        人間・コンピュータ双方の成功したmove / dropだけを履歴に含め、終了イベントは
        履歴に含めない。

    副作用:
        初期局面から記録を作り、局面表示、入力案内、自動手の表示をoutput_fnへ渡す。
        コンピュータ参加対局は時計を作り、未注入なら時間設定を一度だけ読み込む。
        合法な入力と自動手だけが記録の現在局面と履歴を変更し、形式・合法性・保存・
        読込エラーでは人間の同じ手番で再入力する。`save` は記録と現在時計を一つの
        ファイルへ保存し、`load` は棋譜・任意の時計・全指し手から再構成した千日手履歴を
        検証してからまとめて置き換え、局面を表示する。終局後の手を含む保存棋譜は拒否して
        現在状態を保ち、終局位置で終わる棋譜は結果表示後に終了する。時計なし旧v1を
        コンピュータ対局で読む場合は起動初期値から時計を作り、そのことを案内する。
        `resign` は人間担当側の投了として表示し、局面を変更せず終了する。通常の同一
        局面4回目は指し継ぎ案内を表示して続行し、打開後の再出現・連続王手負け・
        双方連続王手の未裁定結果は表示して現在の一局を終了する。人間対人間
        では両側、人間対コンピュータでは先手だけが入力し、コンピュータ対コンピュータ
        では両側が自動手を指す。

    前提条件:
        人間手番の行動前に詰みを確認する。コンピュータ手は共通の制御付き探索へ渡し、
        完了手なしは投了、返却後の対局時計超過は時間切れ負けとして扱う。抑制結果と
        EOF/Ctrl-Cを勝敗へ変換しない。人間の入力時間は差し引かない。先後交代は局面規則、
        入力・自動手の担当はmodeという境界を分ける。
        `load` 成功後は読込局面の `side_to_move` と `mode` に従って、次の人間入力または
        コンピュータ手へ進む。標準のinputとprintは差し替え可能である。
    """
    if rng is None:
        rng = random.Random()
    clock = None
    if mode is not GameMode.HUMAN_VS_HUMAN:
        if clock_settings is None:
            clock_settings = CliClockSettings(600_000, 30_000)
        if time_config is None:
            time_config = load_time_management_config()
        clock = CliClock.start(clock_settings)
    record = GameRecord(create_initial_position())
    repetition_tracker = RepetitionTracker(record.current_position)
    output_fn(render_position(record.current_position))
    try:
        while True:
            position = record.current_position
            if mode.is_human_turn(position.side_to_move):
                if is_game_over(position):
                    output_fn(_checkmate_message(position.side_to_move))
                    return record
            else:
                if clock is None or time_config is None:
                    raise ValueError("コンピュータ対局の時計設定がありません")
                clock, should_continue = _run_computer_turn(
                    record,
                    repetition_tracker,
                    rng,
                    output_fn,
                    move_selection_policy,
                    clock,
                    time_config,
                    now_ns,
                )
                if not should_continue:
                    return record
                continue

            output_fn("指し手を入力してください（例: move 7 7 7 6）:")
            try:
                command = parse_command(input_fn())
                if isinstance(command, HelpCommand):
                    output_fn(_HELP_TEXT)
                    continue
                if isinstance(command, SaveCommand):
                    CliSession(record, clock).save(command.path)
                    output_fn("棋譜を保存しました。")
                    continue
                if isinstance(command, LoadCommand):
                    session = CliSession.load(command.path)
                    candidate_record = session.record
                    candidate_repetition_tracker = RepetitionTracker.from_positions(
                        candidate_record.iter_positions()
                    )
                    if session.clock is None:
                        if mode is GameMode.HUMAN_VS_HUMAN:
                            candidate_clock = None
                        else:
                            if clock_settings is None:
                                raise ValueError(
                                    "コンピュータ対局の初期時計設定がありません"
                                )
                            candidate_clock = CliClock.start(clock_settings)
                    else:
                        candidate_clock = session.clock
                    record, repetition_tracker, clock = (
                        candidate_record,
                        candidate_repetition_tracker,
                        candidate_clock,
                    )
                    if session.clock is None and clock is not None:
                        output_fn(
                            "時計情報がないため、対局開始時に選んだ初期値を使用しました。"
                        )
                    output_fn("棋譜を読み込みました。")
                    output_fn(render_position(record.current_position))
                    if _display_repetition_outcome(
                        repetition_tracker.current_outcome, output_fn
                    ):
                        return record
                    continue
                if isinstance(command, ResignCommand):
                    output_fn(_resignation_message(position.side_to_move))
                    return record
                _apply_command(record, command)
            except (ValueError, OSError) as error:
                output_fn("エラー：" + str(error))
                continue
            position = record.current_position
            output_fn(render_position(position))
            outcome = repetition_tracker.add_position(position)
            if _display_repetition_outcome(outcome, output_fn):
                return record
    except EOFError, KeyboardInterrupt:
        output_fn("入力を終了しました。")
        return record
