"""USIプロトコルで一手を返すエンジン境界。"""

import codecs
import io
import os
import random
import selectors
import sys
import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from queue import Queue
from threading import Lock, Thread
from typing import TextIO

from .game_search import search_move
from .model import Position, Side
from .movegen import MoveSelectionPolicy, SearchCompletion
from .search_control import SearchControl, SearchSignal
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
    "fullwidth4": MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH,
    "alphabeta4": MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA,
}


@dataclass(frozen=True)
class _InputLine:
    """完成行と読取り時点の整数nsを保持する不変データ。"""

    text: str
    read_ns: int


class _InputCancelled(Exception):
    """内部終了通知による読取り解除。EOFや故障とは区別する。"""


class _StdinLineSource:
    """macOSの標準入力と内部終了pipeを同時に待つ入力源。

    借用streamは先読みされていないテキスト標準入力を前提とし、closeしない。
    入力担当だけがread_lineを呼び、主担当はcancel後に担当を回収してcloseする。
    自前pipe/selectorを所有し、標準入力のblocking属性を終了後に復元する。
    他OSへの移植ではfd同時待機、nonblocking read、復号・改行、回収を再点検する。
    """

    def __init__(self, stream: TextIO):
        self._fd = stream.fileno()
        self._blocking = os.get_blocking(self._fd)
        self._wake_read = self._wake_write = None
        self._selector = None
        self._cancel_lock = Lock()
        self._cancelled = False
        self._closed = False
        self._lines = deque()
        self._pending = ""
        self._eof = False
        try:
            decoder = codecs.getincrementaldecoder(stream.encoding or "utf-8")(
                errors=stream.errors or "strict"
            )
            self._decoder = io.IncrementalNewlineDecoder(decoder, translate=True)
            self._wake_read, self._wake_write = os.pipe()
            os.set_blocking(self._wake_write, False)
            os.set_blocking(self._fd, False)
            self._selector = selectors.DefaultSelector()
            self._selector.register(self._fd, selectors.EVENT_READ)
            self._selector.register(self._wake_read, selectors.EVENT_READ)
        except BaseException as primary:
            try:
                self.close()
            except BaseException as cleanup:
                primary._usi_cleanup_errors = (cleanup,) + getattr(
                    cleanup, "_usi_cleanup_errors", ()
                )
            raise

    def read_line(self) -> _InputLine:
        """完成行を時刻付きで返す。EOF・取消・読取り故障は別の例外。"""
        while True:
            with self._cancel_lock:
                if self._cancelled:
                    self._lines.clear()
                    self._pending = ""
                    raise _InputCancelled
            if self._lines:
                return self._lines.popleft()
            if self._eof:
                raise EOFError
            ready = self._selector.select()
            if any(key.fd == self._wake_read for key, _ in ready):
                raise _InputCancelled
            if not ready:
                continue
            try:
                chunk = os.read(self._fd, 4096)
            except BlockingIOError:
                continue
            self._eof = not chunk
            self._pending += self._decoder.decode(chunk, final=self._eof)
            while "\n" in self._pending:
                line, self._pending = self._pending.split("\n", 1)
                self._lines.append(_InputLine(line + "\n", time.monotonic_ns()))
            if self._eof and self._pending:
                self._lines.append(_InputLine(self._pending, time.monotonic_ns()))
                self._pending = ""

    def cancel(self) -> None:
        """反復可能な内部終了通知。部分行や無言入力の待機も解除する。"""
        with self._cancel_lock:
            if self._cancelled or self._closed:
                return
            self._cancelled = True
            os.write(self._wake_write, b"x")

    def close(self) -> None:
        """入力担当回収後、自前資源を解放し借用stdinの属性を復元する。"""
        if self._closed:
            return
        self._closed = True
        errors = []
        actions = []
        if self._selector is not None:
            actions.append(self._selector.close)
        for fd in (self._wake_read, self._wake_write):
            if fd is not None:
                actions.append(lambda fd=fd: os.close(fd))
        actions.append(lambda: os.set_blocking(self._fd, self._blocking))
        for action in actions:
            try:
                action()
            except BaseException as error:
                errors.append(error)
        if errors:
            primary = errors[0]
            primary._usi_cleanup_errors = tuple(errors[1:])
            raise primary


@dataclass(frozen=True)
class _UsiClock:
    """解析操作だけが生成する、先後の残り時間と秒読みの非負整数msデータ。"""

    btime_ms: int
    wtime_ms: int
    byoyomi_ms: int


def _parse_go_clock(arguments: Sequence[str]) -> _UsiClock | None:
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
    clock: _UsiClock | None, side_to_move: Side, config: TimeManagementConfig
) -> SearchBudget | None:
    """現在手番の時計から期間を準備する。時計なしはNoneで、時刻取得はしない。"""
    if clock is None:
        return None
    remaining = clock.btime_ms if side_to_move == Side.SENTE else clock.wtime_ms
    return calculate_search_budget(remaining, clock.byoyomi_ms, config)


class _UsiEngineState:
    """最新のPositionまたは未設定を保持する、モジュール内の状態データ。"""

    def __init__(self) -> None:
        self._position: Position | None = None

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


@dataclass(frozen=True)
class _InputEnded:
    """EOF通知データ。"""


@dataclass(frozen=True)
class _WorkerFailed:
    """担当名と通常停止でない例外の通知データ。"""

    worker: str
    error: BaseException


@dataclass(frozen=True)
class _SearchFinished:
    """送信完了とは別の、探索担当終了の通知データ。"""

    context: _SearchContext


@dataclass
class _SearchContext:
    """一goの局面・制御・送信状態。共通Lock下で寿命を順序付ける。"""

    position: Position
    policy: MoveSelectionPolicy
    control: SearchControl
    thread: Thread | None = None
    suppressed: bool = False
    sent: bool = False
    finished: bool = False
    error: BaseException | None = None

    def suppress(self) -> None:
        """共通Lock保持中に呼ぶ、応答抑制付き停止操作。"""
        self.suppressed = True
        self.control.request_stop(suppress_response=True)


def _search_and_respond(context, output_fn, rng, lock, events) -> None:
    """探索結果を一回送る。抑制・送信・完了は共通Lockで同期する。

    search_moveの結果だけを利用し、予備手や候補を重複所有しない。
    出力関数は改行・flushが終わって戻る操作で、再入を認めない。
    例外は故障通知し、送信失敗を完了扱いせず再送しない。
    """
    try:
        result = search_move(context.position, context.policy, rng, context.control)
        with lock:
            if (
                context.suppressed
                or context.control.check() == SearchSignal.SUPPRESS
                or result.completion == SearchCompletion.SUPPRESSED
            ):
                return
            if not context.sent:
                response = (
                    "resign" if result.move is None else format_usi_move(result.move)
                )
                output_fn(f"bestmove {response}")
                context.sent = True
    except BaseException as error:
        with lock:
            context.error = error
            context.suppress()
        events.put(_WorkerFailed("探索", error))
    finally:
        with lock:
            context.finished = True
        events.put(_SearchFinished(context))


def _run_session(read_line, output_fn, rng, config, cancel_input) -> None:
    """主担当で命令・故障を受け、入力と各探索担当を放棄せず回収する。

    read_lineは時刻付き行またはEOFErrorを返し、cancel_inputで待機解除可能であること。
    呼出し元が入力源を所有し、この操作の返却後にcloseする。
    通常終了はNone、故障は回収後に元例外を送出する。joinは共通Lock外。
    """
    events = Queue()
    lock = Lock()
    input_failures = []
    state = _UsiEngineState()
    configured_policy = MoveSelectionPolicy.RANDOM
    game_policy = None
    active = None
    primary_error = None
    cleanup_errors = []

    def read_commands():
        try:
            while True:
                events.put(read_line())
        except EOFError:
            events.put(_InputEnded())
        except _InputCancelled:
            pass
        except BaseException as error:
            with lock:
                input_failures.append(error)
            events.put(_WorkerFailed("入力", error))

    def retire(context):
        if context is not None:
            if context.thread is not None and context.thread.ident is not None:
                context.thread.join()
            if context.error is not None:
                raise context.error

    def emit(response):
        with lock:
            output_fn(response)

    reader = Thread(target=read_commands, name="usi-input")
    try:
        reader.start()
        while True:
            event = events.get()
            if isinstance(event, _WorkerFailed):
                raise event.error
            if isinstance(event, _SearchFinished):
                if event.context is active:
                    retire(active)
                    active = None
                continue
            tokens = [] if isinstance(event, _InputEnded) else event.text.split()
            name = (
                "quit"
                if isinstance(event, _InputEnded)
                else (tokens[0] if tokens else "")
            )
            # 入力確定と送信前確認は同じLock。read/Queue投入は確定ではない。
            with lock:
                if active is not None and active.error is not None:
                    raise active.error
                busy = active is not None and not active.sent and not active.finished
                if busy and name in {"position", "go", "usinewgame"}:
                    active.suppress()
                    raise ValueError(f"探索・応答未完了中の{name}は受け付けません")
                if active is not None and name in {"quit", "gameover"}:
                    active.suppress()
                if busy and name == "stop":
                    active.control.request_stop()
                completed = active is not None and (active.sent or active.finished)
            # 送信済みでも前担当終了前に次の命令や探索を開始しない。
            if completed or name in {"quit", "gameover"}:
                retire(active)
                active = None
            if name == "quit":
                break
            if name in {"", "stop", "gameover"}:
                continue
            if name == "usi":
                for response in (
                    "id name kaname-shogi",
                    "id author kaname-shogi project",
                    "option name Difficulty type combo default Random "
                    "var Random var Material var TwoPlyMaterial "
                    "var FullWidth4 var AlphaBeta4",
                    "usiok",
                ):
                    emit(response)
            elif name == "isready":
                emit("readyok")
            elif name == "setoption":
                if len(tokens) == 5 and tuple(t.casefold() for t in tokens[1:4]) == (
                    "name",
                    "difficulty",
                    "value",
                ):
                    value = tokens[4].casefold()
                    if value in _USI_DIFFICULTY_VALUES:
                        configured_policy = _USI_DIFFICULTY_VALUES[value]
            elif name == "usinewgame":
                state.clear_position()
                game_policy = None
            elif name == "position":
                state.replace_position(parse_usi_position(event.text).position)
            elif name == "go":
                clock = _parse_go_clock(tokens[1:])
                position = state.require_position()
                budget = _prepare_search_budget(clock, position.side_to_move, config)
                if game_policy is None:
                    game_policy = configured_policy
                context = _SearchContext(
                    position.copy(), game_policy, SearchControl(budget, event.read_ns)
                )
                context.thread = Thread(
                    target=_search_and_respond,
                    args=(context, output_fn, rng, lock, events),
                    name="usi-search",
                )
                with lock:
                    active = context
                context.thread.start()
    except BaseException as error:
        primary_error = error
    finally:
        with lock:
            if active is not None:
                active.suppress()
        # 各後片付けの失敗後も、残る担当・資源の回収を試みる。
        for cleanup in (
            cancel_input,
            lambda: retire(active),
            lambda: reader.join() if reader.ident is not None else None,
        ):
            try:
                cleanup()
            except BaseException as error:
                cleanup_errors.append(error)
        if primary_error is None:
            primary_error = next(iter(input_failures + cleanup_errors), None)
        if primary_error is not None:
            primary_error._usi_cleanup_errors = tuple(
                error for error in cleanup_errors if error is not primary_error
            )
            raise primary_error


def run_usi_engine(
    input_fn: Callable[[], str],
    output_fn: Callable[[str], None],
    rng: random.Random | None = None,
    *,
    time_config: TimeManagementConfig | None = None,
    cancel_input_fn: Callable[[], None] | None = None,
) -> None:
    """注入した一行入出力で、探索中もUSI入力を処理する。

    引数:
        input_fn: 一行を返しEOF時はEOFError。待機する場合はcancel_input_fnで
            別スレッドから必ず解除可能であること。有限入力だけなら解除省略可。
        output_fn: 改行なしの一行を受け、送信完了後に戻る操作。再入しないこと。
        rng: 実行中の全goで共有する乱数器。省略時は一つ作る。
        time_config: 実行中不変の設定。省略時だけ入力開始前に一回読む。
        cancel_input_fn: 入力待機を解除する反復可能な操作。省略時は何もしない。
    戻り値:
        なし。quit/EOFは抑制・担当回収後に正常終了する。
    副作用:
        入力/探索担当を起動・回収しUSI応答を送る。最初のgoで局内方針を固定し、
        usinewgameで局面・局内固定を解除する。設定値とrngは次局へ保持する。
        保存局面へ指し手を適用しない。時計原点はinput_fn返却直後の整数ns。
    前提条件・理由:
        positionは既存パーサー対応形式。時計は既存検証後に探索制御へ渡す。
        任意のブロッキングCallableは強制停止できないため取消可能入力が必要。
        抑制と手なしを区別し、各goの応答は最大一回。厳密な期限保証はしない。
    例外:
        ValueErrorは既存局面/時計/未対応go、探索中の禁止入力等。
        設定・入力・探索・出力の故障は担当回収後に元例外を伝達する。
    """
    config = time_config if time_config is not None else load_time_management_config()
    engine_rng = rng if rng is not None else random.Random()

    def read_line():
        text = input_fn()
        return _InputLine(text, time.monotonic_ns())

    _run_session(
        read_line,
        output_fn,
        engine_rng,
        config,
        cancel_input_fn if cancel_input_fn is not None else lambda: None,
    )


def main() -> int:
    """macOS向け中断可能入力をUSI共通sessionへ接続する操作。

    引数・戻り値:
        引数なし。quit/EOFは0、設定・入力・探索・送信の故障はstderr診断と1。
    副作用:
        設定を入力源構築前に一回読み、入力と探索担当を起動・回収する。
        stdoutへ改行付きUSI応答をwrite/flushし、返却後に入力源をcloseする。
    前提条件・理由:
        先読みされていないテキスト標準ストリームとmacOSの入力fdを前提とする。
        他OSでは入力待機・nonblocking読取り・通知・回収方式の点検が必要。
        KeyboardInterruptは回収後に再送出する。出力待ちの上限は保証しない。
    """

    def output_line(response: str) -> None:
        sys.stdout.write(response + "\n")
        sys.stdout.flush()

    source = None
    failure = None
    cleanup_errors = []
    try:
        config = load_time_management_config()
        source = _StdinLineSource(sys.stdin)
        _run_session(
            source.read_line, output_line, random.Random(), config, source.cancel
        )
    except BaseException as error:
        failure = error
    finally:
        if source is not None:
            try:
                source.close()
            except BaseException as error:
                cleanup_errors.append(error)
    if failure is None and cleanup_errors:
        failure = cleanup_errors.pop(0)
    if isinstance(failure, KeyboardInterrupt):
        raise failure
    if failure is not None:
        print(f"USIエンジンエラー: {failure}", file=sys.stderr, flush=True)
        pending = deque(getattr(failure, "_usi_cleanup_errors", ()))
        pending.extend(cleanup_errors)
        reported = {id(failure)}
        while pending:
            error = pending.popleft()
            if id(error) in reported:
                continue
            reported.add(id(error))
            print(f"USI回収エラー: {error}", file=sys.stderr, flush=True)
            pending.extend(getattr(error, "_usi_cleanup_errors", ()))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
