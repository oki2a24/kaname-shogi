"""USIエンジン関数境界と起動プロセスの振る舞いを確認する。"""

import os
import random
import selectors
import subprocess
import sys
import time
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from kaname_shogi import usi_engine
from kaname_shogi.model import (
    BasicPieceType,
    Board,
    Piece,
    PieceType,
    Position,
    Side,
    Square,
)
from kaname_shogi.movegen import (
    MoveSelectionPolicy,
    SearchCompletion,
    SearchResult,
    legal_moves,
)
from kaname_shogi.sfen import SfenPosition, format_sfen
from kaname_shogi.usi_move import parse_usi_move
from kaname_shogi.usi_position import parse_usi_position


def _run_engine(input_fn, output_fn, *args, **kwargs):
    """通常応答テストでは次命令をbestmove後に配送し、異常時は待機解除する。"""
    completed = Event()
    cancelled = Event()
    pending = False

    def read():
        nonlocal pending
        if pending:
            if not completed.wait(5):
                raise AssertionError("通常応答を待てませんでした")
            if cancelled.is_set():
                raise EOFError
        line = input_fn()
        pending = bool(line.split() and line.split()[0] == "go")
        if pending:
            completed.clear()
        return line

    def write(line):
        output_fn(line)
        if line.startswith("bestmove "):
            completed.set()

    def cancel():
        cancelled.set()
        completed.set()

    usi_engine.run_usi_engine(read, write, *args, cancel_input_fn=cancel, **kwargs)


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


class UsiEngineStateTests(unittest.TestCase):
    """USIエンジンの非公開局面状態オブジェクトを確認する。"""

    def create_state(self):
        state_type = getattr(usi_engine, "_UsiEngineState", None)
        self.assertIsNotNone(state_type, "_UsiEngineStateが定義されていません")
        return state_type()

    def test_requires_position_when_unset(self):
        """局面未設定の状態から局面を要求するとValueErrorにする。

        初期局面を暗黙に作って、未受信の局面から指す誤りを検出する。
        """
        state = self.create_state()

        with self.assertRaises(ValueError):
            state.require_position()

    def test_replaces_position(self):
        """局面の置換後は最新のPosition参照を返す。

        古い局面を残したり、局面を不要に複製したりする誤りを検出する。
        """
        state = self.create_state()
        first = parse_usi_position("position startpos moves 7g7f").position
        latest = parse_usi_position("position startpos moves 2g2f").position

        state.replace_position(first)
        self.assertIs(state.require_position(), first)

        state.replace_position(latest)
        self.assertIs(state.require_position(), latest)

    def test_clears_position(self):
        """局面を消去した後は未設定として扱う。

        `usinewgame`後に前の局面を参照できる状態へ残す誤りを検出する。
        """
        state = self.create_state()
        state.replace_position(
            parse_usi_position("position startpos moves 7g7f").position
        )

        state.clear_position()

        with self.assertRaises(ValueError):
            state.require_position()


class UsiEngineFunctionTests(unittest.TestCase):
    def _run_with_policy_spy(self, commands):
        """一手選択境界に届く局面・方針を記録してUSIコマンドを実行する。"""
        calls = []
        outputs = []

        def choose(position, policy, rng, control):
            moves = legal_moves(position)
            calls.append((position, moves, policy, rng))
            return SearchResult(SearchCompletion.COMPLETE, moves[0] if moves else None)

        with patch.object(usi_engine, "search_move", side_effect=choose):
            _run_engine(ScriptedInput(commands), outputs.append, random.Random(0))
        return calls, outputs

    def test_answers_usi_with_difficulty_combo_before_usiok(self):
        """usiへDifficulty comboをusiokより先に通知する。

        optionを通知し忘れたり、usiokの後へ出してGUI側の設定機会を失う誤りを
        検出する。
        """
        outputs = []

        _run_engine(ScriptedInput(["usi", "isready", "quit"]), outputs.append)

        self.assertEqual(
            outputs,
            [
                "id name kaname-shogi",
                "id author kaname-shogi project",
                "option name Difficulty type combo default Random var Random var Material var TwoPlyMaterial",
                "usiok",
                "readyok",
            ],
        )

    def test_ignores_setoption_gameover_and_unknown_commands(self):
        """未対応の設定・終局通知・未知コマンドでは応答しない。

        これらへ独自応答するとUSI応答列を汚し、後続コマンドをずらす誤りを検出する。
        """
        outputs = []

        _run_engine(
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
                "option name Difficulty type combo default Random var Random var Material var TwoPlyMaterial",
                "usiok",
            ],
        )

    def test_uses_random_policy_when_difficulty_is_unset(self):
        """setoptionなしの最初のgoは既定のRANDOMを使う。

        設定未指定時に新しい駒得方針を使ったり、選択方針を共有境界へ渡さない誤りを
        検出する。
        """
        calls, outputs = self._run_with_policy_spy(
            [
                "position startpos moves 7g7f",
                "go",
                "quit",
            ]
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], MoveSelectionPolicy.RANDOM)
        self.assertTrue(outputs[0].startswith("bestmove "))

    def test_applies_valid_difficulty_setting_at_first_go(self):
        """最初のgoはそれより前の有効なMaterial設定を使う。

        USIが既知の設定を読み飛ばしたり、設定前に選択した既定値を使い続ける誤りを
        検出する。
        """
        calls, _ = self._run_with_policy_spy(
            [
                "setoption name Difficulty value Material",
                "position startpos moves 7g7f",
                "go",
                "quit",
            ]
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], MoveSelectionPolicy.MATERIAL)

    def test_accepts_difficulty_option_case_insensitively(self):
        """Difficulty名とRandom/Material値の大文字小文字を区別しない。

        USI仕様がcase-insensitiveと定める既知optionを表記揺れだけで読み飛ばす誤りを
        検出する。
        """
        calls, _ = self._run_with_policy_spy(
            [
                "setoption name difficulty value mAtErIaL",
                "position startpos moves 7g7f",
                "go",
                "quit",
            ]
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], MoveSelectionPolicy.MATERIAL)

    def test_accepts_two_ply_material_case_insensitively(self):
        """TwoPlyMaterialと大小混在の値を二手先読み方針として渡す。

        新値の受付漏れ、大小混在だけの受付漏れ、旧方針への取り違えを検出する。
        値ごとにエンジンを新しく実行し、前の有効設定による偽成功を防ぐ。
        """
        for value in ("TwoPlyMaterial", "tWoPlYmAtErIaL"):
            with self.subTest(value=value):
                calls, _ = self._run_with_policy_spy(
                    [
                        f"setoption name Difficulty value {value}",
                        "position startpos moves 7g7f",
                        "go",
                        "quit",
                    ]
                )

                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][2], MoveSelectionPolicy.TWO_PLY_MATERIAL)

    def test_invalid_value_preserves_two_ply_setting(self):
        """新値後の未知値で設定を失わず、無設定と旧値も従来方針を使う。

        未知値による既定値への消去や別方針への取り違えを検出する。
        最初のgoより前に未知値を送り、局内固定による偽成功を防ぐ。
        選択境界だけをspyにし、設定受付と状態処理は実際に動かす。
        """
        cases = [
            (
                [
                    "setoption name Difficulty value TwoPlyMaterial",
                    "setoption name Difficulty value Strong",
                ],
                MoveSelectionPolicy.TWO_PLY_MATERIAL,
            ),
            ([], MoveSelectionPolicy.RANDOM),
            (
                ["setoption name Difficulty value Random"],
                MoveSelectionPolicy.RANDOM,
            ),
            (
                ["setoption name Difficulty value Material"],
                MoveSelectionPolicy.MATERIAL,
            ),
        ]
        for settings, expected in cases:
            with self.subTest(settings=settings):
                calls, _ = self._run_with_policy_spy(
                    settings + ["position startpos moves 7g7f", "go", "quit"]
                )

                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][2], expected)

    def test_ignores_invalid_and_unknown_options(self):
        """未知名を無視し、不正Difficulty値では最後の有効値を保つ。

        未知optionで状態を壊したり、未設定の不正値を受け入れたりする誤りを検出する。
        """
        calls, _ = self._run_with_policy_spy(
            [
                "setoption name Difficulty value Material",
                "setoption name USI_Hash value 32",
                "setoption name Difficulty value Strong",
                "position startpos moves 7g7f",
                "go",
                "quit",
            ]
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], MoveSelectionPolicy.MATERIAL)

        calls, _ = self._run_with_policy_spy(
            [
                "setoption name Difficulty value Strong",
                "position startpos moves 7g7f",
                "go",
                "quit",
            ]
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], MoveSelectionPolicy.RANDOM)

    def test_defers_midgame_difficulty_change_until_next_game(self):
        """最初のgoで固定した方針は局中変更で変わらず次局で切り替わる。

        二回目のgoへ変更値を早期適用したり、usinewgame後も古い固定値を残す誤りを
        検出する。
        """
        calls, _ = self._run_with_policy_spy(
            [
                "position startpos moves 7g7f",
                "go",
                "setoption name Difficulty value Material",
                "position startpos moves 2g2f",
                "go",
                "usinewgame",
                "position startpos moves 7g7f",
                "go",
                "quit",
            ]
        )

        self.assertEqual(
            [call[2] for call in calls],
            [
                MoveSelectionPolicy.RANDOM,
                MoveSelectionPolicy.RANDOM,
                MoveSelectionPolicy.MATERIAL,
            ],
        )

    def test_keeps_two_ply_policy_for_current_game(self):
        """二手先読みは局中固定し、局中のMaterial設定は次局へ継承する。

        局中変更の早期適用、新値だけの固定漏れ、次局に古い方針を残す誤り、
        設定の既定値への消去、後続goへ方針を渡し忘れる誤りを検出する。
        選択境界だけをspyにし、設定受付と局の状態処理は実際に動かす。
        """
        calls, _ = self._run_with_policy_spy(
            [
                "setoption name Difficulty value TwoPlyMaterial",
                "position startpos moves 7g7f",
                "go",
                "setoption name Difficulty value Material",
                "go",
                "usinewgame",
                "position startpos moves 7g7f",
                "go",
                "quit",
            ]
        )

        self.assertEqual(len(calls), 3)
        expected_policies = [
            MoveSelectionPolicy.TWO_PLY_MATERIAL,
            MoveSelectionPolicy.TWO_PLY_MATERIAL,
            MoveSelectionPolicy.MATERIAL,
        ]
        for go_number, (call, expected) in enumerate(
            zip(calls, expected_policies, strict=True), start=1
        ):
            with self.subTest(go_number=go_number):
                self.assertEqual(call[2], expected)

    def test_usinewgame_preserves_configured_difficulty(self):
        """usinewgameは局面を消しても設定済み方針を次局へ保つ。

        新局開始時にDifficultyまで既定値へ消去して、利用者の設定を失う誤りを検出する。
        """
        calls, _ = self._run_with_policy_spy(
            [
                "setoption name Difficulty value Material",
                "usinewgame",
                "position startpos moves 2g2f",
                "go",
                "quit",
            ]
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], MoveSelectionPolicy.MATERIAL)

    def test_returns_legal_bestmove_from_replayed_position(self):
        """再現した局面の合法手からUSI形式の一手を返す。

        時計値を待ったり、局面の合法性と無関係な手を返したりする誤りを検出する。
        """
        outputs = []
        position_command = "position startpos moves 7g7f"

        _run_engine(
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
        position = parse_usi_position(position_command).position
        self.assertIn(move, legal_moves(position))

    def test_two_ply_bestmove_is_legal_and_preserves_position(self):
        """二手先読みで二回の合法応答を返し、局面を保存して手なしは投了する。

        実選択を使い、不合法応答・応答欠落・局面変更・手なしの誤応答を検出する。
        全合法手からの選択なので、教材の４五飛だけを期待値にしない。
        """
        board = Board()
        for square, piece_type, side in (
            (Square(9, 9), PieceType.KING, Side.SENTE),
            (Square(5, 5), PieceType.ROOK, Side.SENTE),
            (Square(1, 1), PieceType.KING, Side.GOTE),
            (Square(5, 3), PieceType.GOLD, Side.GOTE),
            (Square(5, 4), PieceType.PAWN, Side.GOTE),
        ):
            board.set_piece(square, Piece(piece_type, side))
        position = Position(board, Side.SENTE)
        sfen = format_sfen(SfenPosition(position, 1))
        expected_moves = legal_moves(position)
        self.assertTrue(expected_moves)
        outputs = []
        observed_positions = []
        choose_move = usi_engine.search_move

        def snapshot(current):
            return (
                tuple(
                    current.board.piece_at(Square(file, rank))
                    for file in range(1, 10)
                    for rank in range(1, 10)
                ),
                current.side_to_move,
                tuple(
                    hand.count(piece_type)
                    for hand in (current.sente_hand, current.gote_hand)
                    for piece_type in BasicPieceType
                    if piece_type != BasicPieceType.KING
                ),
            )

        expected_state = snapshot(position)

        def record_choose_move(current, policy, rng, control):
            self.assertEqual(policy, MoveSelectionPolicy.TWO_PLY_MATERIAL)
            self.assertEqual(snapshot(current), expected_state)
            observed_positions.append(current)
            selected = choose_move(current, policy, rng, control)
            self.assertEqual(snapshot(current), expected_state)
            return selected

        with patch.object(usi_engine, "search_move", side_effect=record_choose_move):
            _run_engine(
                ScriptedInput(
                    [
                        "setoption name Difficulty value TwoPlyMaterial",
                        f"position sfen {sfen}",
                        "go",
                        "go",
                        "quit",
                    ]
                ),
                outputs.append,
                random.Random(0),
            )

        self.assertEqual(len(observed_positions), 2)
        self.assertIsNot(observed_positions[0], observed_positions[1])
        self.assertEqual(snapshot(observed_positions[0]), expected_state)
        self.assertEqual(len(outputs), 2)
        for response in outputs:
            tokens = response.split()
            self.assertEqual(len(tokens), 2)
            self.assertEqual(tokens[0], "bestmove")
            self.assertNotEqual(tokens[1], "resign")
            self.assertIn(parse_usi_move(tokens[1]), expected_moves)

        # 玉なし部分局面も既存モデルで表現できる。空盤なら実合法手は空になる。
        no_move_position = Position(Board(), Side.SENTE)
        self.assertEqual(legal_moves(no_move_position), ())
        no_move_sfen = format_sfen(SfenPosition(no_move_position, 1))
        expected_state = snapshot(no_move_position)
        outputs = []
        observed_positions = []
        with patch.object(usi_engine, "search_move", side_effect=record_choose_move):
            _run_engine(
                ScriptedInput(
                    [
                        "setoption name Difficulty value TwoPlyMaterial",
                        f"position sfen {no_move_sfen}",
                        "go",
                        "quit",
                    ]
                ),
                outputs.append,
                random.Random(0),
            )

        self.assertEqual(outputs, ["bestmove resign"])
        self.assertEqual(len(observed_positions), 1)
        self.assertEqual(snapshot(observed_positions[0]), expected_state)

    def test_uses_most_recent_position_before_go(self):
        """複数のposition後に受けたgoは最後の局面を使う。

        以前のPositionを参照して、古い局面から合法手を選ぶ誤りを検出する。
        """
        outputs = []
        first_command = "position startpos moves 7g7f"
        latest_command = "position startpos moves 2g2f"
        parse_position = usi_engine.parse_usi_position
        parsed_positions = []
        observed_positions = []

        def record_parse_position(command):
            result = parse_position(command)
            parsed_positions.append(result)
            return result

        search = usi_engine.search_move

        def record_legal_moves(position, policy, rng, control):
            observed_positions.append(position)
            return search(position, policy, rng, control)

        with (
            patch.object(
                usi_engine, "parse_usi_position", side_effect=record_parse_position
            ),
            patch.object(usi_engine, "search_move", side_effect=record_legal_moves),
        ):
            _run_engine(
                ScriptedInput([first_command, latest_command, "go", "quit"]),
                outputs.append,
                random.Random(0),
            )

        latest_position = parsed_positions[1].position
        self.assertEqual(len(parsed_positions), 2)
        self.assertEqual(len(observed_positions), 1)
        self.assertIsNot(observed_positions[0], latest_position)
        self.assertEqual(
            format_sfen(SfenPosition(observed_positions[0], 1)),
            format_sfen(SfenPosition(latest_position, 1)),
        )
        response = outputs[0].split()
        self.assertEqual(response[0], "bestmove")
        self.assertIn(parse_usi_move(response[1]), legal_moves(latest_position))

    def test_returns_resign_when_no_legal_moves(self):
        """合法手がないときbestmove resignを返す。

        手のない局面で、不正な手や空のbestmoveを出力する誤りを検出する。
        """
        outputs = []

        with patch.object(
            usi_engine,
            "search_move",
            return_value=SearchResult(SearchCompletion.COMPLETE, None),
        ):
            _run_engine(
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
            _run_engine(
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
            _run_engine(
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
            _run_engine(ScriptedInput(["go"]), lambda response: None, random.Random(0))

    def test_rejects_invalid_position_command(self):
        """未対応の初期局面形式や空の手順を拒否する。

        既存パーサーの対象外形式を有効な局面として扱う誤りを検出する。
        """
        for command in ("position startpos", "position startpos moves"):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    _run_engine(
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
                    _run_engine(
                        ScriptedInput(["position startpos moves 7g7f", go_command]),
                        lambda response: None,
                        random.Random(0),
                    )

    def test_ignores_unknown_go_token(self):
        """未知のgoトークンを読み飛ばして合法手を返す。

        未知トークンを既知の未対応条件と誤認して終了する誤りを検出する。
        """
        outputs = []

        _run_engine(
            ScriptedInput(["position startpos moves 7g7f", "go mystery", "quit"]),
            outputs.append,
            random.Random(0),
        )

        self.assertEqual(len(outputs), 1)
        response = outputs[0].split()
        self.assertEqual(response[0], "bestmove")
        self.assertEqual(len(response), 2)
        self.assertIn(
            parse_usi_move(response[1]),
            legal_moves(parse_usi_position("position startpos moves 7g7f").position),
        )

    def test_stops_cleanly_on_quit_and_input_eof(self):
        """quitと入力EOFのどちらでも無応答で処理を終える。

        終了後も入力を読み続けたり、終了通知をUSI出力したりする誤りを検出する。
        """
        outputs = []
        quit_input = ScriptedInput(["quit", "usi"])

        _run_engine(quit_input, outputs.append)
        self.assertEqual(outputs, [])

        _run_engine(ScriptedInput([]), outputs.append)
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

        新方式を設定しても合法な手を返さないこと、flush欠落、診断混入や
        余分なstdoutを検出する。合法性だけでは方針の取り違えは検出しない。
        """
        process = self.start_engine()
        reader = PipeLineReader(process.stdout)
        try:
            self.send_line(process, "usi")
            self.assertEqual(reader.read_line(), "id name kaname-shogi")
            self.assertEqual(reader.read_line(), "id author kaname-shogi project")
            self.assertEqual(
                reader.read_line(),
                "option name Difficulty type combo default Random var Random var Material var TwoPlyMaterial",
            )
            self.assertEqual(reader.read_line(), "usiok")

            self.send_line(process, "isready")
            self.assertEqual(reader.read_line(), "readyok")

            self.send_line(process, "setoption name Difficulty value TwoPlyMaterial")
            position_command = "position startpos moves 7g7f"
            self.send_line(process, position_command)
            self.send_line(process, "go btime 591199 wtime 600000 byoyomi 30000")
            response = reader.read_line().split()
            self.assertEqual(response[0], "bestmove")
            self.assertEqual(len(response), 2)
            move = parse_usi_move(response[1])
            self.assertIn(
                move,
                legal_moves(parse_usi_position(position_command).position),
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

    def test_entrypoint_accepts_sfen_position(self):
        """SFEN単独局面を受け、合法なbestmoveを終了前に返す。

        SFEN対応の局面結果をPositionとして扱えず、検索応答を失う誤りを検出する。
        """
        process = self.start_engine()
        reader = PipeLineReader(process.stdout)
        position_command = (
            "position sfen lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/"
            "1B5R1/LNSGKGSNL b - 17"
        )
        try:
            self.send_line(process, position_command)
            self.send_line(process, "go btime 591199 wtime 600000 byoyomi 30000")
            first_response = reader.read_line()
            self.send_line(process, "quit")
            self.close_stdin(process)
            return_code = process.wait(timeout=2.0)
            output = (
                first_response
                + "\n"
                + reader.read_remaining_after_exit().decode("utf-8")
            )

            self.assertEqual(return_code, 0)
            responses = output.splitlines()
            self.assertEqual(len(responses), 1)
            response = responses[0].split()
            self.assertEqual(response[0], "bestmove")
            self.assertEqual(len(response), 2)
            move = parse_usi_move(response[1])
            position = parse_usi_position(position_command).position
            self.assertIn(move, legal_moves(position))
            self.assertEqual(process.stderr.read(), b"")
        finally:
            self.stop_process(process)
            self.close_stdin(process)
            reader.close()
            process.stdout.close()
            process.stderr.close()

    def test_entrypoint_reports_invalid_sfen_position_on_stderr(self):
        """不正なSFENはstdoutに混ぜずstderrへ診断して終了する。

        壊れたSFENを検索処理へ渡したり、診断文をUSI応答として返す誤りを検出する。
        """
        process = self.start_engine()
        reader = PipeLineReader(process.stdout)
        try:
            self.send_line(process, "setoption name Difficulty value TwoPlyMaterial")
            self.send_line(process, "position sfen 9/8 b - 1")
            self.close_stdin(process)
            return_code = process.wait(timeout=2.0)

            self.assertNotEqual(return_code, 0)
            self.assertEqual(reader.read_remaining_after_exit(), b"")
            diagnostic = process.stderr.read().decode("utf-8")
            self.assertIn("SFEN", diagnostic)
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
            self.send_line(process, "setoption name Difficulty value TwoPlyMaterial")
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


class UsiClockConnectionTests(unittest.TestCase):
    """時計準備の順序と起動設定の寿命を実処理で確認する。"""

    def config(self, turns=20):
        from fractions import Fraction

        from kaname_shogi.time_management import TimeManagementConfig

        return TimeManagementConfig(turns, Fraction(2), Fraction(3, 4), 2000)

    def test_go_prepares_budget_before_move_generation(self):
        """SFENと履歴適用後の手番から、手生成前に予算を準備する。

        手数や開始側で時計を選ぶ誤りと、予算準備を省く接続漏れを検出する。
        """
        base = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL"
        for command, side, expected in (
            (f"position sfen {base} b - 17", Side.SENTE, (30000, 60000)),
            (f"position sfen {base} w - 17", Side.GOTE, (6000, 12000)),
            ("position startpos moves 7g7f", Side.GOTE, (6000, 12000)),
        ):
            with self.subTest(command=command):
                config = self.config()
                events, budgets, outputs = [], [], []
                prepare = usi_engine._prepare_search_budget
                choose = usi_engine.search_move

                def prepare_spy(
                    clock,
                    current_side,
                    setting,
                    events=events,
                    side=side,
                    config=config,
                    prepare=prepare,
                    budgets=budgets,
                ):
                    events.append("prepare")
                    self.assertEqual(current_side, side)
                    self.assertIs(setting, config)
                    budget = prepare(clock, current_side, setting)
                    budgets.append((budget.target_ms, budget.maximum_ms))
                    return budget

                def generate(position, events=events):
                    events.append("generate")
                    return legal_moves(position)

                def select(*args, events=events, choose=choose):
                    events.append("search")
                    return choose(*args)

                with (
                    patch.object(
                        usi_engine, "_prepare_search_budget", side_effect=prepare_spy
                    ),
                    patch.object(usi_engine, "search_move", side_effect=select),
                ):
                    _run_engine(
                        ScriptedInput(
                            [
                                command,
                                "go btime 600000 wtime 120000 byoyomi 30000",
                                "quit",
                            ]
                        ),
                        outputs.append,
                        random.Random(0),
                        time_config=config,
                    )
                self.assertEqual(events, ["prepare", "search"])
                self.assertEqual(budgets, [expected])
                self.assertEqual(len(outputs), 1)
                self.assertTrue(outputs[0].startswith("bestmove "))

    def test_each_go_uses_only_its_own_clock(self):
        """連続goで時計なし・0・非0を流用せず通常応答する。

        前回予算の残留と、未接続段階で0を投了や無応答へ変える誤りを検出する。
        """
        from kaname_shogi.time_management import SearchBudget

        budgets, outputs = [], []
        prepare = usi_engine._prepare_search_budget

        def record(*args):
            result = prepare(*args)
            budgets.append(result)
            return result

        with patch.object(usi_engine, "_prepare_search_budget", side_effect=record):
            _run_engine(
                ScriptedInput(
                    [
                        "position startpos moves 7g7f",
                        "go btime 600000 wtime 120000 byoyomi 30000",
                        "go",
                        "go btime 0 wtime 0",
                        "go btime 600000 wtime 120000 byoyomi 30000",
                        "quit",
                    ]
                ),
                outputs.append,
                time_config=self.config(),
            )
        self.assertEqual(
            budgets,
            [
                SearchBudget(6000, 12000),
                None,
                SearchBudget(0, 0),
                SearchBudget(6000, 12000),
            ],
        )
        self.assertEqual(len(outputs), 4)
        self.assertTrue(
            all(
                line.startswith("bestmove ") and line != "bestmove resign"
                for line in outputs
            )
        )

    def test_invalid_go_never_starts_search(self):
        """相手側不正・不足・未対応条件を探索前に拒否する。

        使う側だけの検査、無制限への読み替え、エラー時bestmoveを検出する。
        """
        for command in (
            "go btime bad wtime 120000",
            "go wtime 0",
            "go binc 1",
            "go movetime 1",
        ):
            with self.subTest(command=command):
                outputs = []
                with (
                    patch.object(usi_engine, "search_move") as choose,
                    patch.object(usi_engine, "calculate_search_budget") as calculate,
                ):
                    with self.assertRaises(ValueError):
                        _run_engine(
                            ScriptedInput(["position startpos moves 7g7f", command]),
                            outputs.append,
                            time_config=self.config(),
                        )
                    choose.assert_not_called()
                    calculate.assert_not_called()
                self.assertEqual(outputs, [])

    def test_run_loads_config_once_before_input(self):
        """各実行の入力前に一回読み、新局でも同じ設定を使う。

        goごと再読込、実行間キャッシュ、注入破棄を検出する。
        """
        first, second = self.config(), self.config(4)
        events, settings, budgets = [], [], []
        prepare = usi_engine._prepare_search_budget

        def load():
            events.append("load")
            return first if events.count("load") == 1 else second

        def record(clock, side, config):
            settings.append(config)
            budget = prepare(clock, side, config)
            budgets.append((budget.target_ms, budget.maximum_ms))
            return budget

        lines = [
            "usi",
            "isready",
            "position startpos moves 7g7f",
            "go btime 600000 wtime 120000",
            "usinewgame",
            "position startpos moves 7g7f",
            "go btime 600000 wtime 120000",
            "quit",
        ]
        with (
            patch.object(
                usi_engine, "load_time_management_config", side_effect=load
            ) as loader,
            patch.object(usi_engine, "_prepare_search_budget", side_effect=record),
        ):
            for _ in range(2):
                scripted = ScriptedInput(lines)

                def read(scripted=scripted):
                    events.append("input")
                    return scripted()

                begin = len(events)
                _run_engine(read, lambda line: None)
                self.assertEqual(events[begin], "load")
            self.assertEqual(loader.call_count, 2)
            self.assertEqual(
                loader.call_args_list, [unittest.mock.call(), unittest.mock.call()]
            )
            self.assertEqual(events[0], "load")
            _run_engine(ScriptedInput(["quit"]), lambda line: None, time_config=first)
            self.assertEqual(loader.call_count, 2)
        self.assertTrue(all(setting is first for setting in settings[:2]))
        self.assertTrue(all(setting is second for setting in settings[2:]))
        self.assertEqual(
            budgets, [(6000, 12000), (6000, 12000), (30000, 60000), (30000, 60000)]
        )

    def test_main_loads_and_injects_config_once(self):
        """mainは設定一回読込後に入力源を作り共通sessionへ注入する。

        二重読込・設定置換・入力源の回収漏れを検出する。
        """
        from io import StringIO
        from unittest.mock import Mock

        config = self.config(4)
        source = Mock()
        events = []

        def load():
            events.append("load")
            return config

        def make_source(stream):
            events.append("source")
            return source

        def session(read, output, rng, setting, cancel):
            events.append("session")
            self.assertIs(setting, config)
            self.assertEqual(read, source.read_line)
            self.assertEqual(cancel, source.cancel)
            output("readyok")

        with (
            patch.object(
                usi_engine, "load_time_management_config", side_effect=load
            ) as loader,
            patch.object(usi_engine, "_StdinLineSource", side_effect=make_source),
            patch.object(usi_engine, "_run_session", side_effect=session),
            patch.object(sys, "stdin", StringIO("quit\n")),
            patch.object(sys, "stdout", StringIO()) as output,
        ):
            self.assertEqual(usi_engine.main(), 0)
            loader.assert_called_once_with()
            self.assertEqual(output.getvalue(), "readyok\n")
        self.assertEqual(events, ["load", "source", "session"])
        source.close.assert_called_once_with()

    def test_main_input_source_failure_is_diagnosed(self):
        """入力源構築の故障をstderrへ出し終了1にする。

        設定故障との混同・stdoutへの診断混入を検出する。
        """
        from io import StringIO

        with (
            patch.object(
                usi_engine, "_StdinLineSource", side_effect=OSError("入力源故障")
            ),
            patch.object(sys, "stdin", StringIO("quit\n")),
            patch.object(sys, "stdout", StringIO()) as output,
            patch.object(sys, "stderr", StringIO()) as diagnostic,
        ):
            self.assertEqual(usi_engine.main(), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("入力源故障", diagnostic.getvalue())

    def test_main_rejects_invalid_or_unreadable_config_before_input(self):
        """設定故障時は入力を読まずstderrと終了1を返す。

        代替値への置換、診断のstdout混入、runの開始を検出する。
        """
        from io import StringIO
        from unittest.mock import Mock

        for error in (
            ValueError("/settings.json: 不正項目"),
            OSError("/settings.json: 読込不能"),
        ):
            with self.subTest(error=error):
                stream = Mock(wraps=StringIO("usi\nquit\n"))
                with (
                    patch.object(
                        usi_engine, "load_time_management_config", side_effect=error
                    ),
                    patch.object(sys, "stdin", stream),
                    patch.object(sys, "stdout", StringIO()) as output,
                    patch.object(sys, "stderr", StringIO()) as diagnostic,
                ):
                    self.assertEqual(usi_engine.main(), 1)
                    self.assertEqual(output.getvalue(), "")
                    self.assertIn("USIエンジンエラー:", diagnostic.getvalue())
                    self.assertIn(str(error), diagnostic.getvalue())
                    stream.readline.assert_not_called()
                source = ScriptedInput(["usi"])
                outputs = []
                with patch.object(
                    usi_engine, "load_time_management_config", side_effect=error
                ):
                    with self.assertRaises(type(error)):
                        _run_engine(source, outputs.append)
                self.assertEqual(source.calls, 0)
                self.assertEqual(outputs, [])

    def test_entrypoint_rejects_invalid_clock(self):
        """実プロセスでも不正時計をbestmoveなし・終了1で診断する。

        関数境界だけ検査し、mainの診断や終了コードへの接続を落とす誤りを検出する。
        """
        for command, key in (
            ("go btime bad wtime 120000", "btime"),
            ("go wtime 0", "btime"),
            ("go binc 1", "binc"),
            ("go movetime 1", "movetime"),
        ):
            with self.subTest(command=command):
                result = subprocess.run(
                    [sys.executable, "-m", "kaname_shogi.usi_engine"],
                    cwd=Path(__file__).resolve().parents[1],
                    input="position startpos moves 7g7f\n" + command + "\nquit\n",
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=5,
                    check=False,
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn("USIエンジンエラー:", result.stderr)
                self.assertIn(key, result.stderr)

    def test_main_reports_all_nested_cleanup_failures(self):
        """主故障後の入力源解放で重なった故障もすべて診断する。

        入れ子の回収例外を先頭だけ印字して後続原因を失う誤りを検出する。
        """
        import io
        from unittest.mock import Mock

        source = Mock()
        cleanup = OSError("close-first")
        cleanup._usi_cleanup_errors = (OSError("close-second"),)
        source.close.side_effect = cleanup
        for primary in (None, ValueError("session-primary")):
            with self.subTest(primary=primary):
                stderr = io.StringIO()
                with (
                    patch.object(usi_engine, "load_time_management_config"),
                    patch.object(usi_engine, "_StdinLineSource", return_value=source),
                    patch.object(usi_engine, "_run_session", side_effect=primary),
                    patch.object(sys, "stderr", stderr),
                ):
                    self.assertEqual(usi_engine.main(), 1)
                diagnostic = stderr.getvalue()
                self.assertIn("close-first", diagnostic)
                self.assertIn("close-second", diagnostic)
                if primary is not None:
                    self.assertIn("USIエンジンエラー: session-primary", diagnostic)
                self.assertEqual(diagnostic.count("close-first"), 1)
                self.assertEqual(diagnostic.count("close-second"), 1)
