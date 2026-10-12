"""明示同期点でUSIの探索中入力と送信・回収順序を確認する。"""

import unittest

from usi_test_support import run_isolated

PRELUDE = r"""
import random, threading, queue, time
from types import SimpleNamespace
from unittest.mock import patch
from kaname_shogi import usi_engine as u
from kaname_shogi.movegen import SearchResult, SearchCompletion, MoveSelectionPolicy
from kaname_shogi.search_control import SearchControl, SearchSignal
from kaname_shogi.usi_move import parse_usi_move
from kaname_shogi.time_management import TimeManagementConfig
from fractions import Fraction

config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 2000)
move = parse_usi_move("7c7d")
line_type = getattr(u, "_InputLine", lambda text, read_ns: SimpleNamespace(text=text, read_ns=read_ns))

class Harness:
    def __init__(self):
        self.input = queue.Queue()
        self.output = queue.Queue()
        self.errors = []
        self.cancelled = threading.Event()
        self.lines = []
    def send(self, text, read_ns=100):
        self.input.put(line_type(text, read_ns) if text is not None else None)
    def read(self):
        item = self.input.get()
        if item is None: raise EOFError
        return item
    def cancel(self):
        self.cancelled.set(); self.input.put(None)
    def write(self, line):
        self.lines.append(line); self.output.put(line)
    def run(self):
        try:
            if hasattr(u, "_run_session"):
                u._run_session(self.read, self.write, random.Random(0), config, self.cancel)
            else:
                u.run_usi_engine(lambda: self.read().text, self.write, time_config=config)
        except BaseException as error: self.errors.append(error)
    def start(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
    def finish(self):
        self.thread.join(1)
        assert not self.thread.is_alive(), "sessionが担当を回収できない"
        assert not [t for t in threading.enumerate() if t.name.startswith("usi-")], "担当が残留"

h = Harness()
entered = threading.Event()
release = threading.Event()
stop_seen = threading.Event()
controls = []
policies = []
positions = []
rngs = []
result = SearchResult(SearchCompletion.COMPLETE, move)
def search(position, policy, rng, control):
    positions.append(position); policies.append(policy); rngs.append(rng); controls.append(control)
    entered.set()
    assert release.wait(2), "テスト探索を解除できない"
    return result

def choose(position, moves, policy, rng):
    return search(position, policy, rng, SearchControl(None, 0)).move

original_stop = SearchControl.request_stop
def observed_stop(control, **kwargs):
    original_stop(control, **kwargs)
    stop_seen.set()

search_patch = patch.object(u, "search_move", side_effect=search, create=True)
choose_patch = patch.object(u, "choose_move", side_effect=choose, create=True)
stop_patch = patch.object(SearchControl, "request_stop", observed_stop)
search_patch.start(); choose_patch.start(); stop_patch.start()
h.send("position startpos moves 7g7f")
"""


class UsiConcurrencyTests(unittest.TestCase):
    def test_commands_during_search(self):
        """探索中もreadyokを返し通常stopで最終応答を一回送る。

        同期入力への逆戻りとstopの抑制扱い・二重応答を検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
h.send("go"); h.start()
assert entered.wait(1)
h.send("isready")
try: response = h.output.get(timeout=1)
except queue.Empty: raise AssertionError("探索中の入力を受け付けない")
assert response == "readyok"
h.send("stop"); assert stop_seen.wait(1)
h.send("stop"); release.set()
assert h.output.get(timeout=1) == "bestmove 7c7d"
h.send("quit"); h.finish()
assert not h.errors, h.errors
assert h.lines == ["readyok", "bestmove 7c7d"], h.lines
""",
        )

    def test_search_results_send_once_or_suppress(self):
        """完了・中断の手と完了手なしを送り抑制結果は送らない。

        SUPPRESSEDのNoneを投了へ変換する誤りを検出する。
        """
        for completion, selected, expected in (
            ("COMPLETE", True, "bestmove 7c7d"),
            ("INTERRUPTED", True, "bestmove 7c7d"),
            ("COMPLETE", False, "bestmove resign"),
            ("SUPPRESSED", False, None),
        ):
            with self.subTest(completion=completion, selected=selected):
                run_isolated(
                    self,
                    PRELUDE
                    + f"""
result = SearchResult(SearchCompletion.{completion}, {"move" if selected else "None"})
release.set(); h.send("go"); h.start()
assert entered.wait(1)
"""
                    + (
                        r"""
assert h.output.get(timeout=1) == EXPECTED
h.send("quit"); h.finish()
assert h.lines == [EXPECTED]
""".replace("EXPECTED", repr(expected))
                        if expected
                        else r"""
# 結果返却後の担当終了を待ってから入力を進め、抑制をquitで隠さない。
while any(t.name.startswith("usi-search") for t in threading.enumerate()):
    for t in threading.enumerate():
        if t.name.startswith("usi-search"): t.join(1)
    if not hasattr(u, "_run_session"): break
h.send("quit"); h.finish()
assert h.lines == [], h.lines
"""
                    )
                    + r"""
assert not h.errors, h.errors
""",
                )

    def test_input_confirmation_orders_suppression_and_send(self):
        """送信前の終了・禁止入力を確定すると応答を抑制する。

        検索返却後の抑制確認欠落と禁止入力の受付を検出する。
        """
        for command in (
            "quit",
            None,
            "gameover lose",
            "position startpos moves 2g2f",
            "go",
            "usinewgame",
        ):
            with self.subTest(command=command):
                run_isolated(
                    self,
                    PRELUDE
                    + f"""
h.send("go"); h.start(); assert entered.wait(1)
h.send({command!r})
assert stop_seen.wait(1), "停止/抑制要求を受け付けない"
assert controls[0].check() == SearchSignal.SUPPRESS
release.set()
"""
                    + (
                        r"""
h.send("isready")
assert h.output.get(timeout=1) == "readyok"
h.send("quit")
"""
                        if command == "gameover lose"
                        else ""
                    )
                    + f"""
h.finish()
assert not any(x.startswith("bestmove") for x in h.lines), h.lines
assert bool(h.errors) == {command in ("position startpos moves 2g2f", "go", "usinewgame")!r}, h.errors
""",
                )

    def test_go_uses_read_origin_and_new_context(self):
        """連続goが読取り原点・独立局面・新制御と共有rngを使う。

        起動原点への置換、前予算流用と保存局面の共有を検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
release.set()
h.send("go btime 600000 wtime 120000 byoyomi 30000", 100)
h.start(); assert h.output.get(timeout=1) == "bestmove 7c7d"
h.send("go", 200); assert h.output.get(timeout=1) == "bestmove 7c7d"
h.send("go btime 0 wtime 0", 300); assert h.output.get(timeout=1) == "bestmove 7c7d"
h.send("quit"); h.finish()
assert not h.errors, h.errors
assert [c._maximum_ns for c in controls] == [12000000100, None, 300]
assert len({id(c) for c in controls}) == 3
assert len({id(p) for p in positions}) == 3
assert rngs[0] is rngs[1] is rngs[2]
assert all(p.side_to_move == positions[0].side_to_move for p in positions)
""",
        )

    def test_setting_lifetime_and_protocol_while_searching(self):
        """探索中の設定通知と変更を受け局内固定・次局継承を守る。

        探索中入力停止と現在探索のpolicy書換えを検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
h.send("setoption name Difficulty value TwoPlyMaterial")
h.send("stop"); h.send("go"); h.start(); assert entered.wait(1)
assert controls[0].check() == SearchSignal.CONTINUE
h.send("setoption name Difficulty value Material")
h.send("unknown"); h.send("usi")
received = [h.output.get(timeout=1) for _ in range(4)]
assert received[-1] == "usiok"
assert "var TwoPlyMaterial" in received[-2]
release.set(); assert h.output.get(timeout=1) == "bestmove 7c7d"
h.send("go"); assert h.output.get(timeout=1) == "bestmove 7c7d"
h.send("usinewgame"); h.send("position startpos moves 7g7f"); h.send("go")
assert h.output.get(timeout=1) == "bestmove 7c7d"
h.send("quit"); h.finish()
assert policies == [MoveSelectionPolicy.TWO_PLY_MATERIAL, MoveSelectionPolicy.TWO_PLY_MATERIAL, MoveSelectionPolicy.MATERIAL]
assert not h.errors, h.errors
""",
        )

    def test_returned_result_is_rechecked_before_send(self):
        """探索が返した手でも送信前に確定した抑制なら送らない。

        search_move内部の確認だけへ依存する誤りを直接検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
from queue import Queue
context = u._SearchContext(u.parse_usi_position("position startpos moves 7g7f").position, MoveSelectionPolicy.RANDOM, SearchControl(None, 0))
lock = threading.Lock()
returned = threading.Event()
def result_ready(*args):
    returned.set()
    return SearchResult(SearchCompletion.COMPLETE, move)
u.search_move = result_ready
with lock:
    worker = threading.Thread(target=u._search_and_respond, args=(context, h.write, random.Random(0), lock, Queue()))
    worker.start()
    assert returned.wait(1)
    context.suppress()
worker.join(1)
assert not worker.is_alive()
assert h.lines == []
assert not context.sent
""",
        )

    def test_next_command_waits_for_previous_worker(self):
        """送信後の次goは前担当のLockを使う後片付けを待つ。

        共通Lock内joinと回収前の次担当起動を検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
original = u._search_and_respond
next_read = threading.Event()
join_entered = threading.Event()
original_join = u.Thread.join
def observed_join(thread, *args, **kwargs):
    if thread.name == "usi-search": join_entered.set()
    return original_join(thread, *args, **kwargs)
u.Thread.join = observed_join
retired = threading.Event()
count = [0]
def worker(context, output_fn, rng, lock, events):
    count[0] += 1
    assert count[0] == 1, "前担当回収前に次探索を起動"
    original(context, output_fn, rng, lock, events)
    assert next_read.wait(1)
    assert join_entered.wait(1)
    with lock:
        count[0] -= 1
        retired.set()
u._search_and_respond = worker
read = h.read
def observed_read():
    line = read()
    if line.read_ns == 200: next_read.set()
    return line
h.read = observed_read
release.set(); h.send("go"); h.start()
assert h.output.get(timeout=1) == "bestmove 7c7d"
h.send("go", 200)
assert h.output.get(timeout=1) == "bestmove 7c7d"
h.send("quit"); h.finish()
assert retired.is_set()
assert not h.errors, h.errors
assert len(controls) == 2
""",
        )

    def test_worker_failure_wakes_idle_input(self):
        """探索故障が次入力なしで主担当を起こし全担当を回収する。

        例外を担当内だけで失い入力待ちが残る誤りを検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
def failed(*args): raise RuntimeError("探索故障")
u.search_move = failed
h.send("go"); h.start(); h.finish()
assert h.cancelled.is_set()
assert len(h.errors) == 1 and str(h.errors[0]) == "探索故障", h.errors
assert not h.lines
""",
        )

    def test_input_failure_is_not_normal_eof(self):
        """入力故障を正常EOFへ変換せず入力担当を回収する。

        無言GUIへの再待機と原因の黙殺を検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
def failed_read(): raise OSError("入力故障")
h.read = failed_read
h.start(); h.finish()
assert len(h.errors) == 1 and str(h.errors[0]) == "入力故障", h.errors
assert h.cancelled.is_set()
""",
        )

    def test_send_failure_is_not_completed_or_retried(self):
        """送信故障はsentを確定せず再送しない。

        flush失敗を応答完了や投了として扱う誤りを検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
contexts = []
original = u._search_and_respond
calls = []
def capture(context, *args):
    contexts.append(context)
    original(context, *args)
u._search_and_respond = capture
def failed_write(line):
    calls.append(line)
    raise BrokenPipeError("送信故障")
h.write = failed_write
release.set(); h.send("go"); h.start(); h.finish()
assert len(h.errors) == 1 and str(h.errors[0]) == "送信故障", h.errors
assert not contexts[0].sent
assert calls == ["bestmove 7c7d"], calls
""",
        )

    def test_start_failure_cancels_input_without_joining_unstarted_worker(self):
        """探索担当の起動失敗でも未起動担当をjoinせず入力を回収する。

        起動例外の上書きと入力担当放棄を検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
start = threading.Thread.start
def fail_start(thread):
    if thread.name == "usi-search": raise RuntimeError("探索起動故障")
    return start(thread)
with patch.object(threading.Thread, "start", fail_start):
    h.send("go"); h.start(); h.finish()
assert len(h.errors) == 1 and str(h.errors[0]) == "探索起動故障", h.errors
assert h.cancelled.is_set()
""",
        )

    def test_cleanup_failure_preserves_primary_error(self):
        """回収操作の追加故障でも主原因を保持し残りの回収を試みる。

        finallyの例外で入力エラーを隠す誤りを検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
cancel = h.cancel
def failing_cancel():
    cancel()
    raise OSError("解除後の故障")
h.cancel = failing_cancel
h.send("position invalid"); h.start(); h.finish()
assert len(h.errors) == 1 and isinstance(h.errors[0], ValueError), h.errors
assert any("解除後の故障" in str(e) for e in h.errors[0]._usi_cleanup_errors)
""",
        )

    def test_input_start_failure_is_preserved(self):
        """入力担当の起動失敗でも未起動threadをjoinせず主原因を保つ。

        初期化途中の回収が元の故障を上書きする誤りを検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
original_start = u.Thread.start
def start(thread):
    if thread.name == "usi-input": raise RuntimeError("入力起動故障")
    return original_start(thread)
with patch.object(u.Thread, "start", start):
    h.start(); h.finish()
assert len(h.errors) == 1 and str(h.errors[0]) == "入力起動故障"
assert h.cancelled.is_set()
""",
        )

    def test_sent_response_survives_later_terminal_input(self):
        """送信後の終了・状態変更命令は既送信応答を消さず次命令を処理する。

        抑制先行の表と対にしてEOF・gameover・禁止対象命令の先後を確認する。
        """
        for command in (
            "quit",
            None,
            "gameover",
            "position startpos moves 7g7f",
            "usinewgame",
            "go",
        ):
            with self.subTest(command=command):
                run_isolated(
                    self,
                    PRELUDE
                    + f"command = {command!r}\n"
                    + r"""
h.send("go"); h.start(); assert entered.wait(1)
release.set()
assert h.output.get(timeout=1) == "bestmove 7c7d"
h.send(command)
if command not in (None, "quit"):
    if command == "go": assert h.output.get(timeout=1) == "bestmove 7c7d"
    h.send("isready"); assert h.output.get(timeout=1) == "readyok"
    h.send("quit")
h.finish(); assert not h.errors
assert len([line for line in h.lines if line.startswith("bestmove")]) == (2 if command == "go" else 1)
""",
                )

    def test_main_output_failure_and_interrupt_are_rethrown(self):
        """主担当の出力故障とKeyboardInterruptも入力を回収して元例外を返す。

        探索担当だけを保護し主担当の異常終了で入力を残す誤りを検出する。
        """
        for interrupt in (False, True):
            with self.subTest(interrupt=interrupt):
                run_isolated(
                    self,
                    PRELUDE
                    + f"interrupt = {interrupt!r}\n"
                    + r"""
error = KeyboardInterrupt() if interrupt else BrokenPipeError("主出力故障")
def failed(line): raise error
h.write = failed
h.send("isready"); h.start(); h.finish()
assert h.errors == [error]
assert h.cancelled.is_set()
""",
                )
