"""実入口と制御付き実pipe接続を区別して確認する。"""

import os
import pty
import select
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager

from test_usi_engine import PipeLineReader

from kaname_shogi.movegen import legal_moves
from kaname_shogi.usi_move import parse_usi_move
from kaname_shogi.usi_position import parse_usi_position

BOOTSTRAP = r"""
import os, sys, threading
from kaname_shogi import usi_engine as u
from kaname_shogi.movegen import SearchResult, SearchCompletion
from kaname_shogi.search_control import SearchControl
from kaname_shogi.usi_move import parse_usi_move
started_fd, release_fd, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
stopped = threading.Event()
original_stop = SearchControl.request_stop
original_search = u.search_move
def stop(control, **kwargs):
    original_stop(control, **kwargs)
    stopped.set()
def search(position, policy, rng, control):
    stopped.clear()
    os.write(started_fd, b"s")
    if mode == "real": return original_search(position, policy, rng, control)
    if mode == "fault":
        assert os.read(release_fd, 1) == b"x"
        raise RuntimeError("試験探索故障")
    assert stopped.wait(3), "停止要求が届かない"
    return SearchResult(SearchCompletion.INTERRUPTED, parse_usi_move("7c7d"))
u.search_move = search
SearchControl.request_stop = stop
code = u.main()
assert not [t for t in threading.enumerate() if t.name.startswith("usi-")]
os.close(started_fd); os.close(release_fd)
raise SystemExit(code)
"""


@contextmanager
def engine(mode=None):
    """検査失敗時もプロセス・親所有pipeを回収する。"""
    owned = []
    process = reader = None
    try:
        if mode is None:
            command = [sys.executable, "-m", "kaname_shogi.usi_engine"]
            pass_fds = ()
            started = release = None
        else:
            started, child_started = os.pipe()
            child_release, release = os.pipe()
            owned.extend((started, child_started, child_release, release))
            pass_fds = (child_started, child_release)
            command = [
                sys.executable,
                "-c",
                BOOTSTRAP,
                str(child_started),
                str(child_release),
                mode,
            ]
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            pass_fds=pass_fds,
        )
        for fd in pass_fds:
            os.close(fd)
            owned.remove(fd)
        reader = PipeLineReader(process.stdout)
        yield process, reader, started, release
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)
            for stream in (process.stdin, process.stdout, process.stderr):
                if not stream.closed:
                    stream.close()
        if reader is not None:
            reader.close()
        for fd in owned:
            os.close(fd)


def send(process, line):
    process.stdin.write((line + "\n").encode())
    process.stdin.flush()


def await_started(fd):
    assert select.select([fd], [], [], 2)[0], "探索開始通知が届かない"
    assert os.read(fd, 1) == b"s"


class UsiProcessConcurrencyTests(unittest.TestCase):
    def test_real_entrypoint_policies_and_zero_budget(self):
        """実入口で旧三方式は時計なし・0予算、新二方式は0予算の合法応答をflushする。

        全幅負荷を避け、新方式の実時計予算は関数統合テストで補完する。
        """
        command = "position startpos moves 7g7f"
        expected = legal_moves(parse_usi_position(command).position)
        policy_cases = (
            ("Random", ("go", "go btime 0 wtime 0 byoyomi 0")),
            ("Material", ("go", "go btime 0 wtime 0 byoyomi 0")),
            ("TwoPlyMaterial", ("go", "go btime 0 wtime 0 byoyomi 0")),
            ("FullWidth4", ("go btime 0 wtime 0 byoyomi 0",)),
            ("AlphaBeta4", ("go btime 0 wtime 0 byoyomi 0",)),
        )
        for policy, go_commands in policy_cases:
            for go in go_commands:
                with self.subTest(policy=policy, go=go), engine() as (p, reader, _, __):
                    send(p, "setoption name Difficulty value " + policy)
                    send(p, command)
                    send(p, go)
                    response = reader.read_line(timeout=5).split()
                    self.assertEqual(response[0], "bestmove")
                    self.assertEqual(len(response), 2)
                    self.assertIn(parse_usi_move(response[1]), expected)
                    send(p, "quit")
                    self.assertEqual(p.wait(timeout=2), 0)
                    self.assertEqual(reader.read_remaining_after_exit(), b"")
                    self.assertEqual(p.stderr.read(), b"")

    def test_controlled_search_accepts_and_shuts_down(self):
        """開始同期した探索中にreadyok・stop・終了・gameoverを受け付ける。

        実stdin入力源と実sessionを通すが探索結果は固定し競合の順序を作る。
        """
        for ending in ("stop", "quit", "EOF", "gameover lose"):
            with (
                self.subTest(ending=ending),
                engine("controlled") as (p, reader, started, _),
            ):
                send(p, "position startpos moves 7g7f")
                send(p, "go")
                await_started(started)
                send(p, "isready")
                self.assertEqual(reader.read_line(), "readyok")
                if ending == "EOF":
                    p.stdin.close()
                else:
                    send(p, ending)
                if ending == "stop":
                    self.assertEqual(reader.read_line(), "bestmove 7c7d")
                    send(p, "quit")
                elif ending.startswith("gameover"):
                    send(p, "isready")
                    self.assertEqual(reader.read_line(), "readyok")
                    send(p, "go")
                    await_started(started)
                    send(p, "stop")
                    self.assertEqual(reader.read_line(), "bestmove 7c7d")
                    send(p, "quit")
                self.assertEqual(p.wait(timeout=2), 0)
                self.assertEqual(reader.read_remaining_after_exit(), b"")
                self.assertEqual(p.stderr.read(), b"")

    def test_fault_unblocks_silent_or_partial_stdin(self):
        """無言・部分行の実stdin待機中でも探索故障で回収して終了1にする。

        次のGUI入力に頼る故障通知と読取り待機解除の欠落を検出する。
        """
        for partial in (b"", b"isrea"):
            with (
                self.subTest(partial=partial),
                engine("fault") as (p, reader, started, release),
            ):
                send(p, "position startpos moves 7g7f")
                send(p, "go")
                await_started(started)
                p.stdin.write(partial)
                p.stdin.flush()
                os.write(release, b"x")
                self.assertEqual(p.wait(timeout=2), 1)
                self.assertEqual(reader.read_remaining_after_exit(), b"")
                self.assertIn("試験探索故障", p.stderr.read().decode())

    def test_real_search_wrapper_receives_stop(self):
        """開始を通知するラッパーから実探索を呼び時計なしstopを接続する。

        開始通知後に自然完了する順序もあり、探索中停止の保証は制御付き検査が担う。
        """
        with engine("real") as (p, reader, started, _):
            command = "position startpos moves 7g7f"
            send(p, "setoption name Difficulty value TwoPlyMaterial")
            send(p, command)
            send(p, "go")
            await_started(started)
            send(p, "stop")
            response = reader.read_line().split()
            self.assertEqual(response[0], "bestmove")
            self.assertIn(
                parse_usi_move(response[1]),
                legal_moves(parse_usi_position(command).position),
            )
            send(p, "quit")
            self.assertEqual(p.wait(timeout=2), 0)
            self.assertEqual(reader.read_remaining_after_exit(), b"")
            self.assertEqual(p.stderr.read(), b"")

    def test_entrypoint_file_and_terminal_input(self):
        """通常ファイルと端末fdでも入口が受付・終了できる。

        macOSでの代表入力を確認し、全デバイス・他OSの保証には広げない。
        """
        for terminal in (False, True):
            with self.subTest(terminal=terminal), tempfile.TemporaryFile() as file:
                master = slave = None
                p = reader = None
                try:
                    if terminal:
                        master, slave = pty.openpty()
                        input_stream = slave
                    else:
                        file.write(b"isready\nquit\n")
                        file.seek(0)
                        input_stream = file
                    p = subprocess.Popen(
                        [sys.executable, "-m", "kaname_shogi.usi_engine"],
                        stdin=input_stream,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    reader = PipeLineReader(p.stdout)
                    if terminal:
                        os.write(master, b"isready\nquit\n")
                    self.assertEqual(reader.read_line(), "readyok")
                    self.assertEqual(p.wait(timeout=2), 0)
                    self.assertEqual(reader.read_remaining_after_exit(), b"")
                    self.assertEqual(p.stderr.read(), b"")
                finally:
                    if p is not None:
                        if p.poll() is None:
                            p.terminate()
                            try:
                                p.wait(timeout=1)
                            except subprocess.TimeoutExpired:
                                p.kill()
                                p.wait(timeout=1)
                        p.stdout.close()
                        p.stderr.close()
                    if reader is not None:
                        reader.close()
                    for fd in (master, slave):
                        if fd is not None:
                            os.close(fd)
