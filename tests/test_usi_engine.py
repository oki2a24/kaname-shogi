"""USIエンジン関数境界と起動プロセスの振る舞いを確認する。"""

import os
import random
from pathlib import Path
import selectors
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from kaname_shogi import usi_engine
from kaname_shogi.movegen import legal_moves
from kaname_shogi.usi_move import parse_usi_move
from kaname_shogi.usi_position import parse_usi_position


class ScriptedInput:
    """指定した入力行を順番に返し、尽きたらEOFErrorを送出する。"""

    def __init__(self, lines):
        self.lines = iter(lines)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        try:
            return next(self.lines)
        except StopIteration as error:
            raise EOFError from error


class PipeLineReader:
    """バイナリpipeから有限時間で改行済みの一行を読む。"""

    def __init__(self, stream):
        self.stream = stream
        self.selector = selectors.DefaultSelector()
        self.selector.register(stream, selectors.EVENT_READ)
        self.buffer = b""

    def read_line(self, timeout=2.0):
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self.selector.select(remaining):
                raise AssertionError("標準出力に改行付き応答が時間内に届きませんでした")
            chunk = os.read(self.stream.fileno(), 4096)
            if not chunk:
                raise AssertionError("応答行が届く前に標準出力が閉じられました")
            self.buffer += chunk

        line, self.buffer = self.buffer.split(b"\n", 1)
        return line.decode("utf-8")

    def read_remaining_after_exit(self):
        remaining = self.buffer
        self.buffer = b""
        while self.selector.select(0):
            chunk = os.read(self.stream.fileno(), 4096)
            if not chunk:
                break
            remaining += chunk
        return remaining

    def close(self):
        self.selector.close()


class UsiEngineFunctionTests(unittest.TestCase):
    def test_answers_usi_and_ready_in_order(self):
        """usiとisreadyへ定義済みの順序で応答する。

        応答の欠落や順序違いがGUIとの初期化を止めることを検出する。
        """
        outputs = []

        usi_engine.run_usi_engine(
            ScriptedInput(["usi", "isready", "quit"]), outputs.append
        )

        self.assertEqual(
            outputs,
            [
                "id name kaname-shogi",
                "id author kaname-shogi project",
                "usiok",
                "readyok",
            ],
        )

    def test_ignores_setoption_gameover_and_unknown_commands(self):
        """未対応の設定・終局通知・未知コマンドでは応答しない。

        これらへ独自応答するとUSI応答列を汚し、後続コマンドをずらす誤りを検出する。
        """
        outputs = []

        usi_engine.run_usi_engine(
            ScriptedInput(
                [
                    "setoption name USI_Hash value 32",
                    "gameover lose",
                    "mystery command",
                    "usi",
                    "quit",
                ]
            ),
            outputs.append,
        )

        self.assertEqual(
            outputs,
            [
                "id name kaname-shogi",
                "id author kaname-shogi project",
                "usiok",
            ],
        )

    def test_returns_legal_bestmove_from_replayed_position(self):
        """再現した局面の合法手からUSI形式の一手を返す。

        時計値を待ったり、局面の合法性と無関係な手を返したりする誤りを検出する。
        """
        outputs = []
        position_command = "position startpos moves 7g7f"

        usi_engine.run_usi_engine(
            ScriptedInput(
                [
                    position_command,
                    "go btime 591199 wtime 600000 byoyomi 30000",
                    "quit",
                ]
            ),
            outputs.append,
            random.Random(0),
        )

        self.assertEqual(len(outputs), 1)
        self.assertTrue(outputs[0].startswith("bestmove "))
        response = outputs[0].split()
        self.assertEqual(len(response), 2)
        move = parse_usi_move(response[1])
        position = parse_usi_position(position_command)
        self.assertIn(move, legal_moves(position))

    def test_returns_resign_when_no_legal_moves(self):
        """合法手がないときbestmove resignを返す。

        手のない局面で、不正な手や空のbestmoveを出力する誤りを検出する。
        """
        outputs = []

        with patch.object(usi_engine, "legal_moves", return_value=()):
            usi_engine.run_usi_engine(
                ScriptedInput(["position startpos moves 7g7f", "go", "quit"]),
                outputs.append,
                random.Random(0),
            )

        self.assertEqual(outputs, ["bestmove resign"])

    def test_reuses_one_rng_across_go_and_usinewgame(self):
        """一回の実行で作った乱数生成器を各goで再利用する。

        usinewgameごとに生成器を作り直すと乱数列の寿命が変わることを検出する。
        """
        class RecordingRng:
            def __init__(self):
                self.used = []

            def choice(self, values):
                self.used.append(self)
                return values[0]

        outputs = []
        rng = RecordingRng()
        with patch.object(usi_engine.random, "Random", return_value=rng) as factory:
            usi_engine.run_usi_engine(
                ScriptedInput(
                    [
                        "position startpos moves 7g7f",
                        "go",
                        "usinewgame",
                        "position startpos moves 2g2f",
                        "go",
                        "quit",
                    ]
                ),
                outputs.append,
            )

        self.assertEqual(factory.call_count, 1)
        self.assertEqual(rng.used, [rng, rng])
        self.assertEqual(len(outputs), 2)

    def test_clears_position_when_usinewgame_received(self):
        """usinewgame後のgoは前局の局面を使わずエラーにする。

        前局のPositionを誤って再利用し、古い局面から指す誤りを検出する。
        """
        outputs = []

        with self.assertRaises(ValueError):
            usi_engine.run_usi_engine(
                ScriptedInput(
                    [
                        "position startpos moves 7g7f",
                        "usinewgame",
                        "go",
                    ]
                ),
                outputs.append,
                random.Random(0),
            )

        self.assertEqual(outputs, [])

    def test_rejects_go_without_position(self):
        """局面指定前のgoをValueErrorにする。

        初期局面を暗黙に捏造してbestmoveを返す誤りを検出する。
        """
        with self.assertRaises(ValueError):
            usi_engine.run_usi_engine(
                ScriptedInput(["go"]), lambda response: None, random.Random(0)
            )

    def test_rejects_invalid_position_command(self):
        """未対応の初期局面形式や空の手順を拒否する。

        既存パーサーの対象外形式を有効な局面として扱う誤りを検出する。
        """
        for command in ("position startpos", "position startpos moves"):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    usi_engine.run_usi_engine(
                        ScriptedInput([command]),
                        lambda response: None,
                        random.Random(0),
                    )

    def test_rejects_unsupported_go_search_parameters(self):
        """未対応の検索条件を含むgoをValueErrorにする。

        条件を無視して制約と異なる一手を返したり、停止不能の探索を始めたりする誤りを検出する。
        """
        for go_command in (
            "go searchmoves 7g7f",
            "go depth 1",
            "go nodes 1000",
            "go mate 1",
            "go infinite",
            "go ponder",
        ):
            with self.subTest(go_command=go_command):
                with self.assertRaises(ValueError):
                    usi_engine.run_usi_engine(
                        ScriptedInput(
                            ["position startpos moves 7g7f", go_command]
                        ),
                        lambda response: None,
                        random.Random(0),
                    )

    def test_ignores_unknown_go_token(self):
        """未知のgoトークンを読み飛ばして合法手を返す。

        未知トークンを既知の未対応条件と誤認して終了する誤りを検出する。
        """
        outputs = []

        usi_engine.run_usi_engine(
            ScriptedInput(
                ["position startpos moves 7g7f", "go mystery", "quit"]
            ),
            outputs.append,
            random.Random(0),
        )

        self.assertEqual(len(outputs), 1)
        response = outputs[0].split()
        self.assertEqual(response[0], "bestmove")
        self.assertEqual(len(response), 2)
        self.assertIn(
            parse_usi_move(response[1]),
            legal_moves(parse_usi_position("position startpos moves 7g7f")),
        )

    def test_stops_cleanly_on_quit_and_input_eof(self):
        """quitと入力EOFのどちらでも無応答で処理を終える。

        終了後も入力を読み続けたり、終了通知をUSI出力したりする誤りを検出する。
        """
        outputs = []
        quit_input = ScriptedInput(["quit", "usi"])

        usi_engine.run_usi_engine(quit_input, outputs.append)
        self.assertEqual(quit_input.calls, 1)
        self.assertEqual(outputs, [])

        usi_engine.run_usi_engine(ScriptedInput([]), outputs.append)
        self.assertEqual(outputs, [])


class UsiEngineProcessTests(unittest.TestCase):
    def start_engine(self):
        return subprocess.Popen(
            [sys.executable, "-m", "kaname_shogi.usi_engine"],
            cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    @staticmethod
    def send_line(process, line):
        try:
            process.stdin.write(line.encode("utf-8") + b"\n")
            process.stdin.flush()
        except BrokenPipeError:
            # Red状態では入口がまだなく、子プロセスが先に終了する。
            pass

    @staticmethod
    def close_stdin(process):
        if process.stdin is not None and not process.stdin.closed:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass

    @staticmethod
    def stop_process(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)

    def test_entrypoint_flushes_protocol_and_bestmove(self):
        """実行入口が終了前に改行付きUSI応答をflushする。

        flush欠落、局面の手を返さないこと、診断混入や余分なstdoutを検出する。
        """
        process = self.start_engine()
        reader = PipeLineReader(process.stdout)
        try:
            self.send_line(process, "usi")
            self.assertEqual(reader.read_line(), "id name kaname-shogi")
            self.assertEqual(reader.read_line(), "id author kaname-shogi project")
            self.assertEqual(reader.read_line(), "usiok")

            self.send_line(process, "isready")
            self.assertEqual(reader.read_line(), "readyok")

            position_command = "position startpos moves 7g7f"
            self.send_line(process, position_command)
            self.send_line(
                process, "go btime 591199 wtime 600000 byoyomi 30000"
            )
            response = reader.read_line().split()
            self.assertEqual(response[0], "bestmove")
            self.assertEqual(len(response), 2)
            move = parse_usi_move(response[1])
            self.assertIn(
                move, legal_moves(parse_usi_position(position_command))
            )

            self.send_line(process, "quit")
            self.close_stdin(process)
            self.assertEqual(process.wait(timeout=2.0), 0)
            self.assertEqual(reader.read_remaining_after_exit(), b"")
            self.assertEqual(process.stderr.read(), b"")
        finally:
            self.stop_process(process)
            self.close_stdin(process)
            reader.close()
            process.stdout.close()
            process.stderr.close()

    def test_entrypoint_reports_invalid_position_on_stderr(self):
        """不正なpositionはstdoutに出さずstderrと非0終了で診断する。

        不正局面を通常応答へ進めたり、診断をUSI応答列へ混ぜる誤りを検出する。
        """
        process = self.start_engine()
        reader = PipeLineReader(process.stdout)
        try:
            self.send_line(process, "position startpos")
            self.close_stdin(process)
            return_code = process.wait(timeout=2.0)

            self.assertNotEqual(return_code, 0)
            self.assertEqual(reader.read_remaining_after_exit(), b"")
            diagnostic = process.stderr.read().decode("utf-8")
            self.assertTrue(diagnostic.strip())
        finally:
            self.stop_process(process)
            self.close_stdin(process)
            reader.close()
            process.stdout.close()
            process.stderr.close()
