"""中断可能な標準入力源の行処理と所有資源を確認する。"""

import unittest

from usi_test_support import run_isolated

PRELUDE = """
import os, io, threading
from types import SimpleNamespace
from unittest.mock import patch
from kaname_shogi import usi_engine as u

class LegacySource:
    def __init__(self, stream): self.stream = stream
    def read_line(self):
        line = self.stream.readline()
        if not line: raise EOFError
        return SimpleNamespace(text=line, read_ns=0)
    def cancel(self): pass
    def close(self): pass

Source = getattr(u, "_StdinLineSource", LegacySource)
read_fd, write_fd = os.pipe()
stream = io.TextIOWrapper(os.fdopen(read_fd, "rb"), encoding="utf-8")
source = Source(stream)
"""


class UsiInputTests(unittest.TestCase):
    def test_partial_line_is_cancelled_without_more_input(self):
        """部分行だけでも内部通知で読取りを解除し担当を回収する。

        readiness後のreadline再待機と通常入力待ちへの戻りを検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
entered = threading.Event()
original_read = os.read

def observed_read(fd, size):
    result = original_read(fd, size)
    if fd == read_fd: entered.set()
    return result

results = []
def reader():
    try: results.append(source.read_line())
    except BaseException as error: results.append(type(error).__name__)
with patch.object(u.os, "read", side_effect=observed_read) if hasattr(u, "os") else patch("os.read", side_effect=observed_read):
    thread = threading.Thread(target=reader)
    thread.start()
    os.write(write_fd, b"go btime")
    if isinstance(source, LegacySource): source.cancel()
    else:
        assert entered.wait(1), "部分入力を読んでいない"
        source.cancel()
    thread.join(1)
    assert not thread.is_alive(), "部分行入力待ちを解除できない"
assert results == ["_InputCancelled"], results
source.close()
assert not stream.closed
stream.close()
os.close(write_fd)
""",
        )

    def test_lines_keep_read_timestamps(self):
        """一read中の複数行の読取り時刻を配送時に取り直さない。

        goの受渡し待ちを予算から除く原点の遅れを検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
os.write(write_fd, b"go\nisready\n")
with patch("time.monotonic_ns", side_effect=[100, 101, 100]):
    first = source.read_line()
with patch("time.monotonic_ns", return_value=999):
    second = source.read_line()
assert (first.text, second.text) == ("go\n", "isready\n")
assert (first.read_ns, second.read_ns) == (100, 101)
source.close(); stream.close(); os.close(write_fd)
""",
        )

    def test_split_encoding_newlines_and_eof_tail(self):
        """分割文字と改行を復号しEOF末尾行を一回だけ渡す。

        分割UTF8の破損、CRLFの二行化と末尾行の喪失を検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
chunks = [b"\xe3", b"\x81\x82\r", b"\n\n", b"go\r", b"isready\nquit"]
for chunk in chunks: os.write(write_fd, chunk)
os.close(write_fd)
# 実os.readを一バイトずつにし、分割位置すべてを通す。
original = os.read
with patch("os.read", side_effect=lambda fd, size: original(fd, 1)):
    lines = []
    while True:
        try: lines.append(source.read_line().text)
        except EOFError: break
assert lines == ["あ\n", "\n", "go\n", "isready\n", "quit"], lines
try: source.read_line()
except EOFError: pass
else: raise AssertionError("EOF後に行を再配送")
source.close(); stream.close()
""",
        )

    def test_cancel_closes_owned_resources_and_restores_flags(self):
        """取消を反復しても通知が詰まらず借用stdinの属性を復元する。

        pipe/selectorの解放漏れと標準入力のcloseを検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
assert not os.get_blocking(read_fd), "入力をnonblockingにしていない"
owned = [source._wake_read, source._wake_write]
selector = source._selector
for _ in range(10000): source.cancel()
source.close(); source.close()
assert os.get_blocking(read_fd)
assert not stream.closed
for fd in owned:
    try: os.fstat(fd)
    except OSError: pass
    else: raise AssertionError("通知pipeが残留")
assert selector.get_map() is None
stream.close(); os.close(write_fd)
""",
        )

    def test_invalid_encoding_is_not_eof(self):
        """復号の故障を正常EOFへ変換しない。

        不正入力の黙殺と故障後の無言待ちを検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
os.write(write_fd, b"\xff\n")
try: source.read_line()
except UnicodeDecodeError: pass
else: raise AssertionError("復号故障を隠した")
source.close(); stream.close(); os.close(write_fd)
""",
        )

    def test_read_error_is_propagated(self):
        """readのOSErrorをEOFへ隠さず伝達する。

        fd故障後に再待機し続ける誤りを検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
os.write(write_fd, b"go")
with patch("os.read", side_effect=OSError("read故障")):
    try: source.read_line()
    except OSError as error: assert "read故障" in str(error)
    else: raise AssertionError("read故障を隠した")
source.close(); stream.close(); os.close(write_fd)
""",
        )

    def test_partial_initialization_releases_acquired_resources(self):
        """selector登録途中の故障でもpipeと入力属性を回収する。

        構築に失敗した入力源の資源残留を検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
source.close()
owned = []
original_pipe = os.pipe
original_selector = u.selectors.DefaultSelector

def tracked_pipe():
    result = original_pipe()
    owned.extend(result)
    return result
selector = original_selector()
register = selector.register
count = [0]
def failing_register(*args):
    count[0] += 1
    if count[0] == 2: raise OSError("登録故障")
    return register(*args)
with patch("os.pipe", side_effect=tracked_pipe), patch.object(u.selectors, "DefaultSelector", return_value=selector), patch.object(selector, "register", side_effect=failing_register):
    try: Source(stream)
    except OSError as error: assert "登録故障" in str(error)
    else: raise AssertionError("登録故障を隠した")
assert os.get_blocking(read_fd)
assert not stream.closed
for fd in owned:
    try: os.fstat(fd)
    except OSError: pass
    else: raise AssertionError("構築途中pipeが残留")
assert selector.get_map() is None
stream.close(); os.close(write_fd)
""",
        )

    def test_close_failure_still_closes_other_pipe_end(self):
        """資源解放の一箇所が失敗しても残りの解放と属性復元を試みる。

        一つのclose例外による後続pipe残留を検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
owned = [source._wake_read, source._wake_write]
original = os.close
calls = []
def failing_close(fd):
    calls.append(fd)
    original(fd)
    if fd == owned[0]: raise OSError("close故障")
with patch("os.close", side_effect=failing_close):
    try: source.close()
    except OSError as error: assert str(error) == "close故障"
    else: raise AssertionError("解放故障を隠した")
assert calls == owned, calls
assert os.get_blocking(read_fd)
assert not stream.closed
stream.close(); os.close(write_fd)
""",
        )

    def test_initialization_failure_keeps_primary_cause(self):
        """構築故障とcleanup故障が重なっても最初の原因を保つ。

        後片付け例外で登録失敗を上書きする誤りを検出する。
        """
        run_isolated(
            self,
            PRELUDE
            + r"""
source.close()
selector = u.selectors.DefaultSelector()
original_close = selector.close
def failing_close():
    original_close()
    raise OSError("selector解放故障")
with patch.object(u.selectors, "DefaultSelector", return_value=selector), patch.object(selector, "register", side_effect=ValueError("登録主原因")), patch.object(selector, "close", side_effect=failing_close):
    try: Source(stream)
    except ValueError as error:
        assert str(error) == "登録主原因"
        assert any("selector解放故障" in str(e) for e in error._usi_cleanup_errors)
    else: raise AssertionError("主原因を失った")
assert os.get_blocking(read_fd)
stream.close(); os.close(write_fd)
""",
        )
