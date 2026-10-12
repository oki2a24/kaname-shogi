"""USIプロトコルで一手を返すエンジン境界。"""

import random
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Callable, Optional

from .model import Position, Side
from .movegen import MoveSelectionPolicy, choose_move, legal_moves
from .time_management import (
    SearchBudget,
    TimeManagementConfig,
    calculate_search_budget,
    load_time_management_config,
)
from .usi_move import format_usi_move
from .usi_position import parse_usi_position

_USI_DIFFICULTY_VALUES = {
    "random": MoveSelectionPolicy.RANDOM,
    "material": MoveSelectionPolicy.MATERIAL,
    "twoplymaterial": MoveSelectionPolicy.TWO_PLY_MATERIAL,
}


@dataclass(frozen=True)
class _UsiClock:
    """解析操作だけが生成する、先後の残り時間と秒読みの非負整数msデータ。"""

    btime_ms: int
    wtime_ms: int
    byoyomi_ms: int


def _parse_go_clock(arguments: Sequence[str]) -> Optional[_UsiClock]:
    """goを除くトークン列から時計を読む。時計なしはNone、不正はValueError。"""
    unsupported = {
        "searchmoves",
        "depth",
        "nodes",
        "mate",
        "infinite",
        "ponder",
        "movetime",
    }
    for token in arguments:
        if token in unsupported:
            raise ValueError(f"未対応のgo引数です: {token}")
    values = {}
    index = 0
    while index < len(arguments):
        key = arguments[index]
        if key not in {"btime", "wtime", "byoyomi", "binc", "winc"}:
            index += 1
            continue
        if key in values:
            raise ValueError(f"時計項目が重複しています: {key}")
        if index + 1 == len(arguments):
            raise ValueError(f"時計値が欠落しています: {key}")
        text = arguments[index + 1]
        digits = text[1:] if text.startswith(("+", "-")) else text
        if not digits or any(character not in "0123456789" for character in digits):
            raise ValueError(f"時計値には十進整数msが必要です: {key}")
        try:
            value = int(text, 10)
        except ValueError as error:
            raise ValueError(
                f"時計値の整数変換に失敗しました: {key}: {error}"
            ) from error
        if value < 0:
            raise ValueError(f"時計値に負数は使えません: {key}")
        if key in {"binc", "winc"} and value > 0:
            raise ValueError(f"正の加算は未対応です: {key}")
        values[key] = value
        index += 2
    if not {"btime", "wtime", "byoyomi"}.intersection(values):
        return None
    for key in ("btime", "wtime"):
        if key not in values:
            raise ValueError(f"時計ありでは{key}が必須です")
    return _UsiClock(values["btime"], values["wtime"], values.get("byoyomi", 0))


def _prepare_search_budget(
    clock: Optional[_UsiClock], side_to_move: Side, config: TimeManagementConfig
) -> Optional[SearchBudget]:
    """現在手番の時計から期間を準備する。時計なしはNoneで、時刻取得はしない。"""
    if clock is None:
        return None
    remaining = clock.btime_ms if side_to_move == Side.SENTE else clock.wtime_ms
    return calculate_search_budget(remaining, clock.byoyomi_ms, config)


class _UsiEngineState:
    """最新のPositionまたは未設定を保持する、モジュール内の状態データ。"""

    def __init__(self) -> None:
        self._position: Optional[Position] = None

    def replace_position(self, position: Position) -> None:
        """現在局面を受け取ったPositionへ置き換える。複製はしない。"""
        self._position = position

    def clear_position(self) -> None:
        """現在局面を未設定へ戻す。手の選択に使う乱数器には触れない。"""
        self._position = None

    def require_position(self) -> Position:
        """現在局面を返し、未設定なら従来のgoエラーを送出する。"""
        if self._position is None:
            raise ValueError("goの前に有効なpositionを指定してください")
        return self._position


def run_usi_engine(
    input_fn: Callable[[], str],
    output_fn: Callable[[str], None],
    rng: Optional[random.Random] = None,
    *,
    time_config: Optional[TimeManagementConfig] = None,
) -> None:
    """注入された入出力関数でUSIコマンドを処理し、必要な応答を返す。

    引数:
        input_fn: 一回につき一行を返す入力関数。入力終了時はEOFErrorを送出する。
        output_fn: 改行を含まないUSI応答一行を受け取る出力関数。
        rng: 手を選ぶ乱数生成器。省略時はこの呼び出しの開始時に一つ作る。
        time_config: 検証済みの不変な時間設定。省略時は入力受付前に同梱JSONを
            一回読み、指定時は読まない。mainからは起動時の読込結果を注入する。

    戻り値:
        なし。quitまたは入力EOFでコマンド処理を終了する。

    副作用:
        USI応答をoutput_fnへ渡し、使用するrngの状態を進める。局面は関数内に
        作る非公開状態データに保持し、positionで置き換え、usinewgameで未設定に戻す。
        一手選択方針の設定も局面状態から分け、一回の実行中に保持する。最初のgoで
        その局の方針を固定し、usinewgame後の次局から新しい設定を適用する。
        乱数生成器は局面・設定状態から分け、一回の実行中に全goで共有する。
        時間設定も全go・usinewgameで同じ参照を保持する。省略時だけ設定ファイルを読む。

    前提条件:
        入力はUSIコマンド一行であり、positionは
        `position startpos moves <1手以上>`、`position sfen <SFEN>`、または
        `position sfen <SFEN> moves <1手以上>` 形式である。SFEN手数はUSI境界で
        読み取り、検索状態にはPositionだけを渡す。通常のgoは有限比較を完了して一手を返し、
        時計引数を検証し現在手番の時間予算を計算するが、期限判定・探索停止には
        まだ使わない。時計なしのNoneと明示0予算を区別し、0でも通常比較を完了する。
        乱数生成器は一回の実行内で全goに共有する。

    例外:
        ValueError: go時に局面が未設定、positionが既存パーサーに拒否された、または
            時計引数や省略時に読む設定が不正、または
            searchmoves / depth / nodes / mate / infinite / ponder / movetimeを含む場合。
        OSError: 省略時の設定読込が失敗した場合。診断の出力は呼出し元が担当する。
        EOFError: input_fnが入力終了を表すため送出した場合。この関数内では終了として扱う。

    局面再現、合法手列挙、方針別の一手選択、USI一手表記は既存の各責務へ委譲する。
    局面の寿命と手の選択設定・局内固定を別々に保ち、既存CLIや将棋規則を重ねて
    実装せず、USIコマンドと応答の境界に限定する。
    """
    config = time_config if time_config is not None else load_time_management_config()
    engine_rng = rng if rng is not None else random.Random()
    state = _UsiEngineState()
    configured_policy = MoveSelectionPolicy.RANDOM
    game_policy: Optional[MoveSelectionPolicy] = None

    while True:
        try:
            command = input_fn()
        except EOFError:
            return

        tokens = command.split()
        if not tokens:
            continue

        command_name = tokens[0]
        if command_name == "usi":
            output_fn("id name kaname-shogi")
            output_fn("id author kaname-shogi project")
            output_fn(
                "option name Difficulty type combo default Random "
                "var Random var Material var TwoPlyMaterial"
            )
            output_fn("usiok")
        elif command_name == "isready":
            output_fn("readyok")
        elif command_name == "setoption":
            if len(tokens) == 5 and tuple(
                token.casefold() for token in tokens[1:4]
            ) == ("name", "difficulty", "value"):
                value = tokens[4].casefold()
                if value in _USI_DIFFICULTY_VALUES:
                    configured_policy = _USI_DIFFICULTY_VALUES[value]
        elif command_name == "gameover":
            continue
        elif command_name == "usinewgame":
            state.clear_position()
            game_policy = None
        elif command_name == "position":
            state.replace_position(parse_usi_position(command).position)
        elif command_name == "go":
            clock = _parse_go_clock(tokens[1:])
            position = state.require_position()
            # 今回は期間計算まで。期限判定・探索停止への接続は後続で行う。
            _search_budget = _prepare_search_budget(
                clock, position.side_to_move, config
            )
            if game_policy is None:
                game_policy = configured_policy
            moves = legal_moves(position)
            move = choose_move(position, moves, game_policy, engine_rng)
            if move is None:
                output_fn("bestmove resign")
            else:
                output_fn(f"bestmove {format_usi_move(move)}")
        elif command_name == "quit":
            return


def main() -> int:
    """標準入出力をUSIコマンド処理へ接続する。

    引数:
        なし。標準入力・標準出力・標準エラーを使用する。

    戻り値:
        正常終了または入力EOFなら0。設定のValueError/OSError、USI局面・時計・
        未対応検索条件のValueErrorなら1。

    副作用:
        標準入力から一行ずつ読み、USI応答を改行付きで標準出力へ書いて各行を
        直ちにflushする。設定を入力受付前に一回読み、実行中固定する。
        設定読込とUSI入力の診断は標準エラーへ書き、設定故障なら入力を読まない。

    前提条件:
        テキスト標準ストリームが利用できる実行環境で呼び出す。

    入出力の仕方だけをこの入口に置き、コマンド状態と応答処理は
    `run_usi_engine` に委譲することで、関数テストと実プロセスの境界を分ける。
    設定読込のOSErrorだけを起動診断へ変換し、標準入出力の故障を設定不正と混同しない。
    """

    def input_line() -> str:
        line = sys.stdin.readline()
        if line == "":
            raise EOFError
        return line

    def output_line(response: str) -> None:
        sys.stdout.write(response + "\n")
        sys.stdout.flush()

    try:
        config = load_time_management_config()
    except (ValueError, OSError) as error:
        print(f"USIエンジンエラー: {error}", file=sys.stderr, flush=True)
        return 1

    try:
        run_usi_engine(input_line, output_line, time_config=config)
    except ValueError as error:
        print(f"USIエンジンエラー: {error}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
