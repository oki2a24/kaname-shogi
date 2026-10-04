"""USIプロトコルで一手を返すエンジン境界。"""

import sys
import random
from typing import Callable, Optional

from .model import Position
from .movegen import choose_weak_move, legal_moves
from .usi_move import format_usi_move
from .usi_position import parse_usi_position


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
) -> None:
    """注入された入出力関数でUSIコマンドを処理し、必要な応答を返す。

    引数:
        input_fn: 一回につき一行を返す入力関数。入力終了時はEOFErrorを送出する。
        output_fn: 改行を含まないUSI応答一行を受け取る出力関数。
        rng: 手を選ぶ乱数生成器。省略時はこの呼び出しの開始時に一つ作る。

    戻り値:
        なし。quitまたは入力EOFでコマンド処理を終了する。

    副作用:
        USI応答をoutput_fnへ渡し、使用するrngの状態を進める。局面は関数内に
        作る非公開状態データに保持し、positionで置き換え、usinewgameで未設定に戻す。
        乱数生成器は局面状態から分け、一回の実行中に全goで共有する。

    前提条件:
        入力はUSIコマンド一行であり、positionは既存パーサーが扱う
        `position startpos moves <1手以上>` 形式である。通常のgoは直ちに一手を
        返し、時計値を使わない。乱数生成器は一回の実行内で全goに共有する。

    例外:
        ValueError: go時に局面が未設定、positionが既存パーサーに拒否された、または
            searchmoves / depth / nodes / mate / infinite / ponderを含む場合。
        EOFError: input_fnが入力終了を表すため送出した場合。この関数内では終了として扱う。

    局面再現、合法手列挙、弱い一手選択、USI一手表記は既存の各責務へ委譲する。
    局面の寿命と手の選択方法を別々に保ち、既存CLIや将棋規則を重ねて実装せず、
    USIコマンドと応答の境界に限定する。
    """
    engine_rng = rng if rng is not None else random.Random()
    state = _UsiEngineState()
    unsupported_go_tokens = {
        "searchmoves", "depth", "nodes", "mate", "infinite", "ponder"
    }

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
            output_fn("usiok")
        elif command_name == "isready":
            output_fn("readyok")
        elif command_name == "setoption" or command_name == "gameover":
            continue
        elif command_name == "usinewgame":
            state.clear_position()
        elif command_name == "position":
            state.replace_position(parse_usi_position(command))
        elif command_name == "go":
            unsupported = next(
                (token for token in tokens[1:] if token in unsupported_go_tokens),
                None,
            )
            if unsupported is not None:
                raise ValueError(f"未対応のgo引数です: {unsupported}")

            position = state.require_position()
            moves = legal_moves(position)
            move = choose_weak_move(moves, engine_rng)
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
        正常終了または入力EOFなら0、USI局面や未対応検索条件のValueErrorなら1。

    副作用:
        標準入力から一行ずつ読み、USI応答を改行付きで標準出力へ書いて各行を
        直ちにflushする。ValueErrorの説明だけを標準エラーへ書く。

    前提条件:
        テキスト標準ストリームが利用できる実行環境で呼び出す。

    入出力の仕方だけをこの入口に置き、コマンド状態と応答処理は
    `run_usi_engine` に委譲することで、関数テストと実プロセスの境界を分ける。
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
        run_usi_engine(input_line, output_line)
    except ValueError as error:
        print(f"USIエンジンエラー: {error}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
