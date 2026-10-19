"""USIと四手探索アダプターの時計・応答・停止接続を確認する。"""

import time
import unittest
from fractions import Fraction
from threading import Event
from unittest.mock import patch

from usi_test_support import run_isolated

from kaname_shogi import game_search, usi_engine
from kaname_shogi.movegen import MoveSelectionPolicy
from kaname_shogi.search import alpha_beta, minimax
from kaname_shogi.search.result import (
    ControlledCompletion,
    ControlledSearchResult,
    IterationResult,
)
from kaname_shogi.search.result import (
    SearchResult as IterationSearchResult,
)
from kaname_shogi.search_control import SearchControl
from kaname_shogi.time_management import TimeManagementConfig
from kaname_shogi.usi_move import parse_usi_move


def fixed_config() -> TimeManagementConfig:
    """確認用の決め打ち時計配分を返す。"""
    return TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 2000)


def run_commands(commands, *, config, read_origin=None, output_lines=None):
    """goごとに探索担当の終了を待ってから次行を渡す。"""
    outputs = [] if output_lines is None else output_lines
    worker_finished = Event()
    pending_go = False
    command_iter = iter(commands)
    original_worker = usi_engine._search_and_respond

    def tracked_worker(context, output_fn, rng, lock, events):
        try:
            original_worker(context, output_fn, rng, lock, events)
        finally:
            worker_finished.set()

    def read():
        nonlocal pending_go
        if pending_go:
            if not worker_finished.wait(5):
                raise AssertionError("goの探索担当が終了しませんでした")
            pending_go = False
        try:
            line = next(command_iter)
        except StopIteration as error:
            raise EOFError from error
        if line.split()[:1] == ["go"]:
            worker_finished.clear()
            pending_go = True
        return line

    with patch.object(usi_engine, "_search_and_respond", side_effect=tracked_worker):
        if read_origin is None:
            usi_engine.run_usi_engine(read, outputs.append, time_config=config)
        else:
            with patch.object(
                usi_engine.time, "monotonic_ns", return_value=read_origin
            ):
                usi_engine.run_usi_engine(read, outputs.append, time_config=config)
    return outputs


def policy_input(policy: MoveSelectionPolicy) -> str:
    """Difficulty列挙値をUSIへ対応させる。"""
    return {
        MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH: "FullWidth4",
        MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA: "AlphaBeta4",
    }[policy]


class UsiFourPlyIntegrationTests(unittest.TestCase):
    def test_usi_uses_game_search_adapter(self):
        """USIの探索入口は制御結果変換を持つ共通アダプターを参照する。

        旧三方式専用入口へ新方式を渡してValueErrorになる接続漏れを検出する。
        """
        self.assertIs(usi_engine.search_move, game_search.search_move)

    def test_new_modes_reuse_go_control_and_budget(self):
        """時計付きgoの同じ予算・読取原点・制御を全深さへ渡す。

        深さごとの制御再生成、先後時計の取り違え、Noneと明示0の混同を検出する。
        """
        clock_cases = (
            ("b", "go btime 600000 wtime 120000 byoyomi 30000", 30000, 60000),
            ("w", "go btime 600000 wtime 120000 byoyomi 30000", 6000, 12000),
            ("b", "go", None, None),
            ("b", "go btime 0 wtime 0", 0, 0),
        )
        for policy in (
            MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH,
            MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA,
        ):
            backend = (
                minimax
                if policy is MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH
                else alpha_beta
            )
            for side, command, target_ms, maximum_ms in clock_cases:
                with self.subTest(policy=policy, side=side, command=command):
                    origin = time.monotonic_ns()
                    position = f"position sfen 8k/9/9/9/9/9/9/9/K8 {side} - 1"
                    observed = []
                    original_search = backend.search_controlled

                    def record_search(
                        node,
                        depth,
                        operations,
                        control,
                        _observed=observed,
                        _original_search=original_search,
                        **kwargs,
                    ):
                        _observed.append((depth, control))
                        return _original_search(
                            node, depth, operations, control, **kwargs
                        )

                    with (
                        patch.object(
                            backend,
                            "search_controlled",
                            side_effect=record_search,
                        ),
                        patch.object(
                            usi_engine,
                            "search_move",
                            wraps=game_search.search_move,
                        ) as adapter_call,
                    ):
                        outputs = run_commands(
                            [
                                f"setoption name Difficulty value {policy_input(policy)}",
                                position,
                                command,
                            ],
                            config=fixed_config(),
                            read_origin=origin,
                        )

                    self.assertEqual(len(adapter_call.call_args_list), 1)
                    control = adapter_call.call_args.args[3]
                    self.assertIsInstance(control, SearchControl)
                    if target_ms is None:
                        self.assertIsNone(control._target_ns)
                        self.assertIsNone(control._maximum_ns)
                    else:
                        self.assertEqual(
                            control._target_ns, origin + target_ms * 1_000_000
                        )
                        self.assertEqual(
                            control._maximum_ns, origin + maximum_ms * 1_000_000
                        )
                    if maximum_ms == 0:
                        self.assertEqual(observed, [])
                    else:
                        self.assertEqual([depth for depth, _ in observed], [1, 2, 3, 4])
                        self.assertTrue(all(item is control for _, item in observed))
                    self.assertEqual(
                        sum(line.startswith("bestmove ") for line in outputs), 1
                    )

    def test_new_mode_results_send_once_or_suppress(self):
        """新方式の四制御状態からUSIが手なし・停止・抑制を正しく返す。

        手なしの空応答、停止の予備手消失、抑制のresign化、重複応答を検出する。
        """
        selected = parse_usi_move("9i9h")
        record = IterationResult(
            4, IterationSearchResult((0, 1), selected, 7, None), 20
        )
        outcomes = (
            (
                ControlledSearchResult(ControlledCompletion.COMPLETE, selected, record),
                ["bestmove 9i9h"],
            ),
            (
                ControlledSearchResult(ControlledCompletion.STOPPED, selected, None),
                ["bestmove 9i9h"],
            ),
            (
                ControlledSearchResult(ControlledCompletion.NO_LEGAL_MOVE, None, None),
                ["bestmove resign"],
            ),
            (
                ControlledSearchResult(ControlledCompletion.SUPPRESSED, None, record),
                [],
            ),
        )
        position = "position sfen 8k/9/9/9/9/9/9/9/K8 b - 1"
        for policy in (
            MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH,
            MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA,
        ):
            for controlled_result, expected in outcomes:
                with self.subTest(policy=policy, result=controlled_result.completion):
                    with patch.object(
                        game_search.iterative_deepening,
                        "search_controlled",
                        return_value=controlled_result,
                    ) as search:
                        outputs = run_commands(
                            [
                                f"setoption name Difficulty value {policy_input(policy)}",
                                position,
                                "go",
                            ],
                            config=fixed_config(),
                        )

                    self.assertEqual(
                        [line for line in outputs if line.startswith("bestmove ")],
                        expected,
                    )
                    search.assert_called_once()

    def test_search_failure_reaches_existing_usi_recovery(self):
        """新方式の探索例外はbestmoveへ変換せずUSI故障回収へ届く。

        合法予備手で実装故障を隠したり、無応答で入力担当を残す誤りを検出する。
        """
        failure = RuntimeError("四手探索故障")
        outputs = []
        with patch.object(
            game_search.iterative_deepening,
            "search_controlled",
            side_effect=failure,
        ):
            with self.assertRaises(RuntimeError) as caught:
                outputs = run_commands(
                    [
                        "setoption name Difficulty value FullWidth4",
                        "position sfen 8k/9/9/9/9/9/9/9/K8 b - 1",
                        "go",
                    ],
                    config=fixed_config(),
                    output_lines=outputs,
                )

        self.assertIs(caught.exception, failure)
        self.assertFalse(any(line.startswith("bestmove ") for line in outputs))


class UsiFourPlySuppressionRaceTests(unittest.TestCase):
    def test_suppression_between_search_return_and_send(self):
        """送信境界をイベントで順序付け、抑制後0回・送信後一回を保つ。

        探索返却後の抑制確認漏れ、Lock外送信、送信済み応答の巻き戻しを検出する。
        """
        run_isolated(
            self,
            r"""
import random, queue, threading
from unittest.mock import patch
from kaname_shogi import game_search, usi_engine as u
from kaname_shogi.movegen import MoveSelectionPolicy
from kaname_shogi.search.result import ControlledCompletion, ControlledSearchResult, IterationResult, SearchResult
from kaname_shogi.search_control import SearchControl
from kaname_shogi.usi_move import parse_usi_move
from kaname_shogi.usi_position import parse_usi_position

selected = parse_usi_move("9i9h")
record = IterationResult(4, SearchResult((0, 1), selected, 7, None), 20)
completed = ControlledSearchResult(ControlledCompletion.COMPLETE, selected, record)
position = parse_usi_position("position sfen 8k/9/9/9/9/9/9/9/K8 b - 1").position
original_adapter = game_search.search_move
original_suppress = u._SearchContext.suppress

def scenario(gate_before_send):
    returned = threading.Event()
    release = threading.Event()
    output = []
    lock = threading.Lock()
    events = queue.Queue()
    context = u._SearchContext(position.copy(), MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH, SearchControl(None, 0))
    def adapter(*args):
        result = original_adapter(*args)
        returned.set()
        if gate_before_send:
            assert release.wait(2), "抑制確認後に探索担当を解除できない"
        return result
    def release_after_suppress(self):
        original_suppress(self)
        release.set()
    def worker():
        u._search_and_respond(context, output.append, random.Random(0), lock, events)
    with patch.object(u, "search_move", side_effect=adapter), patch.object(game_search.iterative_deepening, "search_controlled", return_value=completed):
        if gate_before_send:
            with patch.object(u._SearchContext, "suppress", release_after_suppress):
                thread = threading.Thread(target=worker, name="test-usi-search")
                thread.start()
                assert returned.wait(2), "アダプター結果が返りません"
                with lock:
                    context.suppress()
                thread.join(2)
        else:
            thread = threading.Thread(target=worker, name="test-usi-search")
            thread.start()
            assert returned.wait(2), "アダプター結果が返りません"
            thread.join(2)
            with lock:
                context.suppress()
    assert not thread.is_alive(), "探索担当が回収されません"
    return output, context.sent

suppressed_lines, suppressed_sent = scenario(True)
sent_lines, sent = scenario(False)
assert suppressed_lines == [], suppressed_lines
assert not suppressed_sent
assert sent_lines == ["bestmove 9i9h"], sent_lines
assert sent
""",
        )
