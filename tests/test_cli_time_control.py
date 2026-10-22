"""通常CLIの探索制御・時計接続の契約を検証する。"""

import json
import random
import unittest
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from kaname_shogi import cli, game_search, movegen
from kaname_shogi.cli_clock import CliClock, CliClockSettings
from kaname_shogi.cli_session import CliSession
from kaname_shogi.game_record import GameRecord, RecordedMove
from kaname_shogi.model import (
    Board,
    Piece,
    PieceType,
    Position,
    Side,
    Square,
    create_initial_position,
)
from kaname_shogi.move import BoardMove
from kaname_shogi.movegen import MoveSelectionPolicy, SearchCompletion, SearchResult
from kaname_shogi.repetition import RepetitionTracker
from kaname_shogi.search_control import SearchControl
from kaname_shogi.time_management import SearchBudget, TimeManagementConfig


class CliTimeControlTests(unittest.TestCase):
    def test_five_policies_call_controlled_adapter_without_uncontrolled_prework(self):
        """五方式・先後とも制御付き共通入口だけで一手を選ぶ。

        CLIの詰み事前判定、旧choose_move、全合法手生成を探索前に呼ぶ誤りを
        禁止操作のspyで検出し、方針・rng・制御・成功履歴の接続を確認する。
        """
        policies = (
            MoveSelectionPolicy.RANDOM,
            MoveSelectionPolicy.MATERIAL,
            MoveSelectionPolicy.TWO_PLY_MATERIAL,
            MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH,
            MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA,
        )
        for side in (Side.SENTE, Side.GOTE):
            for policy in policies:
                with self.subTest(side=side, policy=policy):
                    position = create_initial_position()
                    position.side_to_move = side
                    selected_move = (
                        BoardMove(Square(7, 7), Square(7, 6), False)
                        if side is Side.SENTE
                        else BoardMove(Square(3, 3), Square(3, 4), False)
                    )
                    rng = random.Random(20261020)
                    calls = []

                    def controlled_search(
                        search_position,
                        selected_policy,
                        given_rng,
                        control,
                        calls=calls,
                        selected_move=selected_move,
                    ):
                        calls.append(
                            (search_position, selected_policy, given_rng, control)
                        )
                        if len(calls) == 1:
                            return SearchResult(
                                SearchCompletion.COMPLETE, selected_move
                            )
                        raise KeyboardInterrupt

                    config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 2000)
                    with (
                        patch.object(
                            cli,
                            "create_initial_position",
                            return_value=position,
                        ),
                        patch.object(
                            cli,
                            "is_game_over",
                            side_effect=AssertionError(
                                "コンピュータ手前で詰み判定をしない"
                            ),
                        ),
                        patch.object(
                            cli,
                            "legal_moves",
                            side_effect=AssertionError("CLIで全合法手を生成しない"),
                            create=True,
                        ),
                        patch.object(
                            movegen,
                            "legal_moves",
                            side_effect=AssertionError("旧合法手生成を呼ばない"),
                        ),
                        patch.object(
                            cli,
                            "choose_move",
                            side_effect=AssertionError("旧選択入口を呼ばない"),
                            create=True,
                        ),
                        patch.object(
                            game_search,
                            "choose_move",
                            side_effect=AssertionError("無制御アダプターを呼ばない"),
                        ),
                        patch.object(
                            game_search,
                            "search_move",
                            side_effect=controlled_search,
                        ) as search_move,
                        patch.object(
                            cli,
                            "load_time_management_config",
                            return_value=config,
                            create=True,
                        ),
                    ):
                        record = cli.run_game(
                            input_fn=lambda: self.fail("自動対局で入力を読まない"),
                            output_fn=lambda _: None,
                            rng=rng,
                            mode=cli.GameMode.COMPUTER_VS_COMPUTER,
                            move_selection_policy=policy,
                        )

                    self.assertEqual(search_move.call_count, 2)
                    self.assertEqual(len(record.moves), 1)
                    self.assertEqual(calls[0][0].side_to_move, side)
                    self.assertIs(calls[0][1], policy)
                    self.assertIs(calls[0][2], rng)
                    self.assertIsInstance(calls[0][3], SearchControl)

    def test_origin_precedes_budget_and_search_position_and_return_is_immediate(self):
        """思考表示後に原点を取り、予算・局面複製を含めて返却まで計時する。

        担当判定用局面の取得と探索用複製を区別し、原点の後で予算や局面複製を行う
        よう順序が逆転する誤りと、表示・適用を消費時間へ含める誤りを検出する。
        """
        events = []
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        clock = CliClock.start(CliClockSettings(600, 300))
        original_control = SearchControl
        original_budget = cli.calculate_search_budget
        original_after_turn = CliClock.after_turn
        original_is_expired = CliClock.is_expired
        original_apply = cli._apply_selected_move

        class TrackingRecord(GameRecord):
            def __init__(self, initial_position):
                super().__init__(initial_position)
                self.position_reads = 0

            @property
            def current_position(self):
                self.position_reads += 1
                events.append(
                    "position-for-side"
                    if self.position_reads == 1
                    else "position-for-search"
                    if self.position_reads == 2
                    else "position-for-display"
                )
                return super().current_position

        record = TrackingRecord(create_initial_position())
        selected = BoardMove(Square(7, 7), Square(7, 6), False)
        now_values = iter((123_000_000, 223_000_000))
        now_calls = 0

        def now_ns():
            nonlocal now_calls
            events.append("clock-start" if now_calls == 0 else "clock-return")
            now_calls += 1
            return next(now_values)

        def calculate(remaining_ms, byoyomi_ms, time_config):
            events.append("budget")
            self.assertEqual(
                (remaining_ms, byoyomi_ms, time_config), (600, 300, config)
            )
            return original_budget(remaining_ms, byoyomi_ms, time_config)

        def create_control(budget, started_ns, *, now_ns):
            events.append("control")
            self.assertEqual((budget, started_ns), (SearchBudget(30, 60), 123_000_000))
            return original_control(budget, started_ns, now_ns=now_ns)

        def search(search_position, policy, rng, control):
            events.append("search")
            self.assertEqual(search_position.side_to_move, Side.SENTE)
            self.assertEqual(policy, MoveSelectionPolicy.RANDOM)
            self.assertIsInstance(control, SearchControl)
            return SearchResult(SearchCompletion.COMPLETE, selected)

        def output(text):
            if "思考中です" in text:
                events.append("start-display")
            elif "の指し手: " in text:
                events.append("move-display")
            elif text.startswith("探索状態:"):
                events.append("state-display")
            elif text.startswith("消費時間:") or "残り持ち時間:" in text:
                events.append("time-display")
            else:
                events.append("board-display")

        def after_turn(instance, side, elapsed_ns):
            events.append("clock-update")
            self.assertEqual((side, elapsed_ns), (Side.SENTE, 100_000_000))
            return original_after_turn(instance, side, elapsed_ns)

        def is_expired(instance, side, elapsed_ns):
            events.append("clock-expiry-check")
            self.assertEqual((side, elapsed_ns), (Side.SENTE, 100_000_000))
            return original_is_expired(instance, side, elapsed_ns)

        def apply(record, move):
            events.append("apply")
            return original_apply(record, move)

        def render(position):
            events.append("render")
            return "board"

        rng = random.Random(20261020)
        with (
            patch.object(cli, "calculate_search_budget", side_effect=calculate),
            patch.object(cli, "SearchControl", side_effect=create_control),
            patch.object(game_search, "search_move", side_effect=search),
            patch.object(CliClock, "after_turn", new=after_turn),
            patch.object(CliClock, "is_expired", new=is_expired),
            patch.object(cli, "_apply_selected_move", side_effect=apply),
            patch.object(cli, "render_position", side_effect=render),
        ):
            updated_clock, should_continue = cli._run_computer_turn(
                record,
                RepetitionTracker.from_positions(record.iter_positions()),
                rng,
                output,
                MoveSelectionPolicy.RANDOM,
                clock,
                config,
                now_ns,
            )

        self.assertEqual(
            events,
            [
                "position-for-side",
                "start-display",
                "clock-start",
                "budget",
                "control",
                "position-for-search",
                "search",
                "clock-return",
                "clock-update",
                "clock-expiry-check",
                "state-display",
                "time-display",
                "time-display",
                "move-display",
                "apply",
                "position-for-display",
                "render",
                "board-display",
            ],
        )
        self.assertTrue(should_continue)
        self.assertEqual(updated_clock.sente_remaining_ns, 500_000_000)
        self.assertEqual(
            record.moves,
            (RecordedMove(Square(7, 7), Square(7, 6), False),),
        )

    def test_budget_receives_side_clock_in_ms_but_keeps_ns(self):
        """先後の残りnsを担当側だけmsへ切り捨て、既存予算式へ渡す。

        設定値から独立に計算した目標・上限と計算関数への引数を照合し、相手側の
        時計参照、式の複製、nsの丸めによる持ち時間加算を検出する。
        """
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 2000)
        settings = CliClockSettings(600000, 30000)
        cases = (
            (
                Side.SENTE,
                600_000_000_000,
                600000,
                SearchBudget(30000, 60000),
            ),
            (
                Side.GOTE,
                120_000_000_000,
                120000,
                SearchBudget(6000, 12000),
            ),
            (Side.SENTE, 999999, 0, SearchBudget(21000, 28000)),
            (Side.SENTE, 1000000, 1, SearchBudget(0, 0)),
        )
        original_control = SearchControl
        original_budget = cli.calculate_search_budget

        for side, side_remaining_ns, remaining_ms, expected_budget in cases:
            with self.subTest(side=side, remaining_ns=side_remaining_ns):
                position = create_initial_position()
                position.side_to_move = side
                remaining = (
                    (side_remaining_ns, 120_000_000_000)
                    if side is Side.SENTE
                    else (600_000_000_000, side_remaining_ns)
                )
                clock = CliClock(settings, *remaining)
                record = GameRecord(position)
                budget_arguments = []
                controls = []

                def calculate(
                    given_remaining_ms,
                    byoyomi_ms,
                    given_config,
                    budget_arguments=budget_arguments,
                ):
                    budget_arguments.append(
                        (given_remaining_ms, byoyomi_ms, given_config)
                    )
                    return original_budget(given_remaining_ms, byoyomi_ms, given_config)

                def create_control(budget, started_ns, *, now_ns, controls=controls):
                    controls.append((budget, started_ns))
                    return original_control(budget, started_ns, now_ns=now_ns)

                with (
                    patch.object(cli, "calculate_search_budget", side_effect=calculate),
                    patch.object(cli, "SearchControl", side_effect=create_control),
                    patch.object(
                        game_search,
                        "search_move",
                        return_value=SearchResult(SearchCompletion.COMPLETE, None),
                    ) as search_move,
                ):
                    updated_clock, should_continue = cli._run_computer_turn(
                        record,
                        RepetitionTracker.from_positions(record.iter_positions()),
                        random.Random(20261020),
                        lambda _: None,
                        MoveSelectionPolicy.RANDOM,
                        clock,
                        config,
                        lambda: 10_000_000,
                    )

                self.assertEqual(
                    budget_arguments,
                    [(remaining_ms, 30000, config)],
                )
                self.assertEqual(controls, [(expected_budget, 10_000_000)])
                self.assertEqual(search_move.call_count, 1)
                self.assertFalse(should_continue)
                self.assertEqual(updated_clock.remaining_ns(side), side_remaining_ns)
                other_side = Side.GOTE if side is Side.SENTE else Side.SENTE
                self.assertEqual(
                    updated_clock.remaining_ns(other_side),
                    clock.remaining_ns(other_side),
                )

    def test_result_priority_suppression_expiry_resignation_and_move(self):
        """抑制・時間切れ・投了・完了手・中断予備手の優先順を守る。

        35秒境界ではなく手書き時計1ms+1msの等号境界を使い、抑制を勝敗へ変換する、
        非抑制の返却手を時間切れ後に適用する、手なしを時間内に投了へ結ばない誤りを検出する。
        """
        sente_move = BoardMove(Square(7, 7), Square(7, 6), False)
        gote_move = BoardMove(Square(3, 3), Square(3, 4), False)
        cases = (
            (
                "suppressed-inside",
                Side.SENTE,
                SearchCompletion.SUPPRESSED,
                None,
                1_000_000,
                False,
                "探索結果が抑制されたため対局を終了しました。",
                (),
            ),
            (
                "suppressed-after-expiry",
                Side.GOTE,
                SearchCompletion.SUPPRESSED,
                None,
                3_000_000,
                False,
                "探索結果が抑制されたため対局を終了しました。",
                (),
            ),
            (
                "move-at-expiry",
                Side.SENTE,
                SearchCompletion.COMPLETE,
                sente_move,
                2_000_000,
                False,
                "先手が時間切れです。後手の勝ちです。",
                (),
            ),
            (
                "interrupted-move-at-expiry",
                Side.GOTE,
                SearchCompletion.INTERRUPTED,
                gote_move,
                2_000_000,
                False,
                "後手が時間切れです。先手の勝ちです。",
                (),
            ),
            (
                "none-at-expiry",
                Side.GOTE,
                SearchCompletion.COMPLETE,
                None,
                2_000_000,
                False,
                "後手が時間切れです。先手の勝ちです。",
                (),
            ),
            (
                "complete-none-inside",
                Side.GOTE,
                SearchCompletion.COMPLETE,
                None,
                1_000_000,
                False,
                "後手が投了しました。先手の勝ちです。",
                (),
            ),
            (
                "complete-move-inside",
                Side.SENTE,
                SearchCompletion.COMPLETE,
                sente_move,
                1_000_000,
                True,
                "先手の指し手: move 7 7 7 6",
                (RecordedMove(Square(7, 7), Square(7, 6), False),),
            ),
            (
                "interrupted-move-inside",
                Side.GOTE,
                SearchCompletion.INTERRUPTED,
                gote_move,
                1_000_000,
                True,
                "後手の指し手: move 3 3 3 4",
                (RecordedMove(Square(3, 3), Square(3, 4), False),),
            ),
        )
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        settings = CliClockSettings(1, 1)

        for (
            label,
            side,
            completion,
            move,
            elapsed_ns,
            expected_continue,
            expected_message,
            expected_moves,
        ) in cases:
            with self.subTest(case=label):
                position = create_initial_position()
                position.side_to_move = side
                record = GameRecord(position)
                clock = CliClock(settings, 1_000_000, 1_000_000)
                outputs = []
                start_ns = 5_000_000
                times = iter((start_ns, start_ns + elapsed_ns))
                with patch.object(
                    game_search,
                    "search_move",
                    return_value=SearchResult(completion, move),
                ) as search_move:
                    updated_clock, should_continue = cli._run_computer_turn(
                        record,
                        RepetitionTracker.from_positions(record.iter_positions()),
                        random.Random(20261020),
                        outputs.append,
                        MoveSelectionPolicy.RANDOM,
                        clock,
                        config,
                        lambda times=times: next(times),
                    )

                self.assertEqual(should_continue, expected_continue)
                self.assertEqual(record.moves, expected_moves)
                self.assertEqual(search_move.call_count, 1)
                self.assertIn(expected_message, outputs)
                side_remaining = max(0, 1_000_000 - elapsed_ns)
                self.assertEqual(updated_clock.remaining_ns(side), side_remaining)
                self.assertEqual(
                    updated_clock.remaining_ns(
                        Side.GOTE if side is Side.SENTE else Side.SENTE
                    ),
                    1_000_000,
                )
                if completion is SearchCompletion.SUPPRESSED:
                    self.assertFalse(any("勝ちです。" in line for line in outputs))
                    self.assertFalse(any("投了しました。" in line for line in outputs))
                if elapsed_ns == 2_000_000:
                    self.assertFalse(any("の指し手: " in line for line in outputs))

    def test_time_and_completion_display_matches_fixed_values(self):
        """固定経過と時計から状態・消費・残り時間を表示する。

        独立に手計算したns→ms切捨てと60分超の時刻を照合し、表示値から内部時計を
        作り直す誤りや、完了深さ・評価・手の由来を出す誤りを検出する。
        """
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        settings = CliClockSettings(600_001, 30_000)
        elapsed_ns = 1_234_567_890

        for side, move, expected_move in (
            (
                Side.SENTE,
                BoardMove(Square(7, 7), Square(7, 6), False),
                "先手の指し手: move 7 7 7 6",
            ),
            (
                Side.GOTE,
                BoardMove(Square(3, 3), Square(3, 4), False),
                "後手の指し手: move 3 3 3 4",
            ),
        ):
            for completion, label in (
                (SearchCompletion.COMPLETE, "完了"),
                (SearchCompletion.INTERRUPTED, "通常停止"),
            ):
                with self.subTest(side=side, completion=completion):
                    position = create_initial_position()
                    position.side_to_move = side
                    outputs = []
                    now_values = iter((10_000_000_000, 10_000_000_000 + elapsed_ns))
                    with (
                        patch.object(
                            game_search,
                            "search_move",
                            return_value=SearchResult(completion, move),
                        ),
                        patch.object(cli, "render_position", return_value="board"),
                    ):
                        updated_clock, should_continue = cli._run_computer_turn(
                            GameRecord(position),
                            RepetitionTracker.from_positions(
                                GameRecord(position).iter_positions()
                            ),
                            random.Random(20261020),
                            outputs.append,
                            MoveSelectionPolicy.RANDOM,
                            CliClock.start(settings),
                            config,
                            lambda now_values=now_values: next(now_values),
                        )

                    self.assertTrue(should_continue)
                    self.assertEqual(updated_clock.remaining_ns(side), 598_766_432_110)
                    self.assertEqual(
                        outputs,
                        [
                            f"{'先手' if side is Side.SENTE else '後手'}のコンピュータが思考中です。",
                            f"探索状態: {label}",
                            "消費時間: 1.234秒",
                            f"{'先手' if side is Side.SENTE else '後手'}の残り持ち時間: 09:58.766（秒読み30秒）",
                            expected_move,
                            "board",
                        ],
                    )
                    self.assertFalse(
                        any(
                            marker in line
                            for line in outputs
                            for marker in ("深さ", "評価値", "手の由来", "停止理由")
                        )
                    )

        long_clock = CliClockSettings(3_600_000, 30_000)
        long_outputs = []
        with (
            patch.object(
                game_search,
                "search_move",
                return_value=SearchResult(
                    SearchCompletion.COMPLETE,
                    BoardMove(Square(7, 7), Square(7, 6), False),
                ),
            ),
            patch.object(cli, "render_position", return_value="board"),
        ):
            cli._run_computer_turn(
                GameRecord(create_initial_position()),
                RepetitionTracker.from_positions(
                    GameRecord(create_initial_position()).iter_positions()
                ),
                random.Random(20261020),
                long_outputs.append,
                MoveSelectionPolicy.RANDOM,
                CliClock.start(long_clock),
                config,
                lambda: 0,
            )
        self.assertIn("先手の残り持ち時間: 60:00.000（秒読み30秒）", long_outputs)

        submillisecond_outputs = []
        with (
            patch.object(
                game_search,
                "search_move",
                return_value=SearchResult(
                    SearchCompletion.COMPLETE,
                    BoardMove(Square(7, 7), Square(7, 6), False),
                ),
            ),
            patch.object(cli, "render_position", return_value="board"),
        ):
            cli._run_computer_turn(
                GameRecord(create_initial_position()),
                RepetitionTracker.from_positions(
                    GameRecord(create_initial_position()).iter_positions()
                ),
                random.Random(20261020),
                submillisecond_outputs.append,
                MoveSelectionPolicy.RANDOM,
                CliClock.start(CliClockSettings(1, 0)),
                config,
                iter((0, 999)).__next__,
            )
        self.assertIn("消費時間: 0.000秒", submillisecond_outputs)
        self.assertIn(
            "先手の残り持ち時間: 00:00.000（秒読み0秒）",
            submillisecond_outputs,
        )

    def test_terminal_display_has_no_played_move(self):
        """時間切れ・投了・抑制を時計情報と勝敗の有無で区別する。

        期限後の結果手を表示する誤り、抑制を勝敗や投了へ変える誤り、終局時計を
        表示しない誤りを固定時計と成功履歴で検出する。
        """
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        settings = CliClockSettings(1, 1)
        move = BoardMove(Square(7, 7), Square(7, 6), False)
        cases = (
            (
                "expired",
                SearchCompletion.COMPLETE,
                move,
                2_000_000,
                "先手が時間切れです。後手の勝ちです。",
                "0.002秒",
                True,
            ),
            (
                "resigned",
                SearchCompletion.COMPLETE,
                None,
                1_000_000,
                "先手が投了しました。後手の勝ちです。",
                "0.001秒",
                True,
            ),
            (
                "suppressed",
                SearchCompletion.SUPPRESSED,
                None,
                2_000_000,
                "探索結果が抑制されたため対局を終了しました。",
                "",
                False,
            ),
        )
        for (
            label,
            completion,
            result_move,
            elapsed_ns,
            terminal_message,
            expected_elapsed,
            has_clock,
        ) in cases:
            with self.subTest(case=label):
                outputs = []
                record = GameRecord(create_initial_position())
                now_values = iter((5_000_000, 5_000_000 + elapsed_ns))
                with patch.object(
                    game_search,
                    "search_move",
                    return_value=SearchResult(completion, result_move),
                ):
                    updated_clock, should_continue = cli._run_computer_turn(
                        record,
                        RepetitionTracker.from_positions(record.iter_positions()),
                        random.Random(20261020),
                        outputs.append,
                        MoveSelectionPolicy.RANDOM,
                        CliClock(settings, 1_000_000, 1_000_000),
                        config,
                        lambda now_values=now_values: next(now_values),
                    )

                self.assertFalse(should_continue)
                self.assertIn(terminal_message, outputs)
                self.assertEqual(record.moves, ())
                self.assertFalse(any("の指し手: " in line for line in outputs))
                if has_clock:
                    self.assertIn("消費時間: " + expected_elapsed, outputs)
                    self.assertIn(
                        "先手の残り持ち時間: 00:00.000（秒読み0.001秒）", outputs
                    )
                else:
                    self.assertFalse(any("消費時間:" in line for line in outputs))
                    self.assertFalse(any("残り持ち時間:" in line for line in outputs))
                if label == "resigned":
                    self.assertIn("探索状態: 完了", outputs)
                else:
                    self.assertFalse(any("探索状態:" in line for line in outputs))

    def test_clock_menu_defaults_units_and_retries(self):
        """時計入力は分・秒をmsへ変換し、不正なら二欄ともやり直す。

        空入力の既定値、0片側、空白・先頭0、半角整数だけの文法と0+0拒否を
        独立した期待値で確認し、全角数字や符号等を受理する誤りを検出する。
        """
        choose_clock_settings = getattr(cli, "choose_clock_settings", None)
        self.assertIsNotNone(
            choose_clock_settings, "choose_clock_settingsがまだ実装されていません"
        )

        cases = (
            (["", ""], CliClockSettings(600_000, 30_000), 2, 0),
            (["0", "30"], CliClockSettings(0, 30_000), 2, 0),
            (["10", "0"], CliClockSettings(600_000, 0), 2, 0),
            ([" 0002 ", " 0005 "], CliClockSettings(120_000, 5_000), 2, 0),
            (["0", "0", "1", "0"], CliClockSettings(60_000, 0), 4, 1),
        )
        invalid_values = ("１", "+1", "-1", "1.0", "1e1", "abc")
        for invalid in invalid_values:
            cases += (
                ([invalid, "30", "1", "30"], CliClockSettings(60_000, 30_000), 4, 1),
                (["10", invalid, "1", "30"], CliClockSettings(60_000, 30_000), 4, 1),
            )

        for responses, expected_settings, expected_reads, expected_errors in cases:
            with self.subTest(responses=responses):
                outputs = []
                input_fn = Mock(side_effect=responses)

                result = choose_clock_settings(
                    input_fn=input_fn, output_fn=outputs.append
                )

                self.assertEqual(result, expected_settings)
                self.assertEqual(input_fn.call_count, expected_reads)
                self.assertEqual(
                    sum(line.startswith("エラー：") for line in outputs),
                    expected_errors,
                )
                self.assertEqual(
                    sum("コンピュータの持ち時間" in line for line in outputs),
                    expected_reads // 2,
                )
                self.assertEqual(
                    sum("秒読み（秒" in line for line in outputs), expected_reads // 2
                )

        with self.assertRaises(TypeError):
            choose_clock_settings(lambda: "", lambda _: None)

    def test_run_game_uses_default_clock_settings_for_direct_calls(self):
        """直接呼出しの省略時は承認済み10分・30秒の時計を作る。

        起動メニューを通らない既存呼出しでも初期値を適用することを確認し、時計なし
        や探索予算設定の初期値との混同を検出する。
        """
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        with (
            patch.object(
                cli, "load_time_management_config", return_value=config
            ) as loader,
            patch.object(CliClock, "start", wraps=CliClock.start) as start_clock,
            patch.object(
                game_search, "search_move", side_effect=KeyboardInterrupt
            ) as search,
        ):
            record = cli.run_game(
                input_fn=lambda: self.fail("自動対局で入力を読まない"),
                output_fn=lambda _: None,
                mode=cli.GameMode.COMPUTER_VS_COMPUTER,
                now_ns=lambda: 0,
            )

        self.assertEqual(record.moves, ())
        loader.assert_called_once_with()
        start_clock.assert_called_once_with(CliClockSettings(600_000, 30_000))
        search.assert_called_once()

    def test_load_commits_record_and_clock_together_or_preserves_both(self):
        """読込失敗では棋譜と時計の双方を保ち、同じ手番から保存できる。

        不正clock、不合法履歴、壊れたJSON、I/O失敗の後に独立した元の棋譜payloadと
        時計値を再保存で比較し、片方だけの置換や出力だけで成功と誤認する漏れを検出する。
        """
        settings = CliClockSettings(600_000, 30_000)
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        expected_record = GameRecord(create_initial_position())
        expected_clock = CliClock.start(settings)

        with TemporaryDirectory() as directory:
            directory_path = Path(directory)
            valid_path = directory_path / "valid.json"
            CliSession(expected_record, expected_clock).save(valid_path)
            valid_payload = json.loads(valid_path.read_text(encoding="utf-8"))

            invalid_clock = json.loads(json.dumps(valid_payload))
            invalid_clock["clock"]["byoyomi_ms"] = True
            invalid_clock_path = directory_path / "invalid-clock.json"
            invalid_clock_path.write_text(json.dumps(invalid_clock), encoding="utf-8")

            illegal_history = json.loads(json.dumps(valid_payload))
            illegal_history["game_record"]["moves"] = [
                {
                    "kind": "move",
                    "source": {"file": 7, "rank": 7},
                    "destination": {"file": 7, "rank": 8},
                    "promote": False,
                }
            ]
            illegal_history_path = directory_path / "illegal-history.json"
            illegal_history_path.write_text(
                json.dumps(illegal_history), encoding="utf-8"
            )

            broken_json_path = directory_path / "broken.json"
            broken_json_path.write_text("{", encoding="utf-8")
            missing_path = directory_path / "missing" / "session.json"
            load_failures = (
                invalid_clock_path,
                illegal_history_path,
                broken_json_path,
                missing_path,
            )
            saved_paths = tuple(
                directory_path / f"after-{index}.json"
                for index in range(len(load_failures))
            )
            commands = []
            for load_path, save_path in zip(load_failures, saved_paths, strict=True):
                commands.extend((f"load {load_path}", f"save {save_path}"))
            commands.append("resign")
            outputs = []

            record = cli.run_game(
                input_fn=iter(commands).__next__,
                output_fn=outputs.append,
                mode=cli.GameMode.HUMAN_VS_COMPUTER,
                clock_settings=settings,
                time_config=config,
                now_ns=lambda: 0,
            )

            saved_sessions = tuple(CliSession.load(path) for path in saved_paths)

        self.assertEqual(record.to_payload(), expected_record.to_payload())
        for saved_session in saved_sessions:
            self.assertEqual(
                saved_session.record.to_payload(), expected_record.to_payload()
            )
            self.assertEqual(saved_session.clock, expected_clock)
        self.assertEqual(sum(line.startswith("エラー：") for line in outputs), 4)

    def test_clocked_then_legacy_load_uses_original_startup_settings(self):
        """旧v1読込は直前の保存時計でなくCLI起動時の初期条件へ戻す。

        10分/30秒で起動後に5分/10秒セッションを読み、続けて旧v1を読む順序と
        保存済み先後値を照合し、前の読込設定を流用する誤りを検出する。
        """
        startup_settings = CliClockSettings(600_000, 30_000)
        loaded_clock = CliClock(
            CliClockSettings(300_000, 10_000), 280_123_456_789, 245_987_654_321
        )
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)

        with TemporaryDirectory() as directory:
            clocked_path = Path(directory) / "clocked.json"
            legacy_path = Path(directory) / "legacy.json"
            result_path = Path(directory) / "after-legacy.json"
            initial_record = GameRecord(create_initial_position())
            CliSession(initial_record, loaded_clock).save(clocked_path)
            initial_record.save(legacy_path)
            outputs = []

            record = cli.run_game(
                input_fn=iter(
                    (
                        f"load {clocked_path}",
                        f"load {legacy_path}",
                        f"save {result_path}",
                        "resign",
                    )
                ).__next__,
                output_fn=outputs.append,
                mode=cli.GameMode.HUMAN_VS_COMPUTER,
                clock_settings=startup_settings,
                time_config=config,
                now_ns=lambda: 0,
            )
            saved_session = CliSession.load(result_path)

        expected_clock = CliClock.start(startup_settings)
        self.assertEqual(record.to_payload(), initial_record.to_payload())
        self.assertEqual(saved_session.record.to_payload(), initial_record.to_payload())
        self.assertEqual(saved_session.clock, expected_clock)
        self.assertIn(
            "時計情報がないため、対局開始時に選んだ初期値を使用しました。", outputs
        )

    def test_preserves_clock_in_human_game_and_legacy_without_clock(self):
        """人間同士は読込時計を保持し、時計なしなら従来v1で保存する。

        時計つき棋譜を読んで着手・保存した後に同じ対局で旧v1を読んだとき、時計が
        残留せず従来形式で保存されることと、新規棋譜の形式を手書き状態と比較する。
        """
        loaded_clock = CliClock(
            CliClockSettings(600_000, 30_000), 500_123_456_789, 400_987_654_321
        )

        with TemporaryDirectory() as directory:
            directory_path = Path(directory)
            initial_record = GameRecord(create_initial_position())
            clocked_path = directory_path / "clocked.json"
            after_move_path = directory_path / "after-human-move.json"
            legacy_path = directory_path / "legacy.json"
            after_legacy_path = directory_path / "after-legacy.json"
            new_path = directory_path / "new.json"
            CliSession(initial_record, loaded_clock).save(clocked_path)
            initial_record.save(legacy_path)

            legacy_record = cli.run_game(
                input_fn=iter(
                    (
                        f"load {clocked_path}",
                        "move 7 7 7 6",
                        f"save {after_move_path}",
                        f"load {legacy_path}",
                        f"save {after_legacy_path}",
                        "resign",
                    )
                ).__next__,
                output_fn=lambda _: None,
                mode=cli.GameMode.HUMAN_VS_HUMAN,
                now_ns=lambda: self.fail("人間同士で実時間時計を読まない"),
            )
            clocked_saved = CliSession.load(after_move_path)

            new_record = cli.run_game(
                input_fn=iter((f"save {new_path}", "resign")).__next__,
                output_fn=lambda _: None,
                mode=cli.GameMode.HUMAN_VS_HUMAN,
                now_ns=lambda: self.fail("人間同士で実時間時計を読まない"),
            )
            legacy_payload = json.loads(after_legacy_path.read_text(encoding="utf-8"))
            new_payload = json.loads(new_path.read_text(encoding="utf-8"))

        expected_clocked_record = GameRecord(create_initial_position())
        expected_clocked_record.apply_move(Square(7, 7), Square(7, 6))
        expected_legacy_record = GameRecord(create_initial_position())
        self.assertEqual(
            clocked_saved.record.to_payload(), expected_clocked_record.to_payload()
        )
        self.assertEqual(clocked_saved.clock, loaded_clock)
        self.assertEqual(
            legacy_record.to_payload(), expected_legacy_record.to_payload()
        )
        self.assertEqual(new_record.to_payload(), expected_legacy_record.to_payload())
        self.assertEqual(legacy_payload, expected_legacy_record.to_payload())
        self.assertEqual(new_payload, expected_legacy_record.to_payload())

    def test_loaded_computer_side_uses_its_saved_remainder(self):
        """読込局面の後手探索は保存残りから予算を作り、返却後だけ減算する。

        手書き時計の後手123456789nsから独立に123ms予算・15ms消費後108456689nsを
        期待し、先手値・起動既定時計への置換・残り時計のms丸めを検出する。
        """
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        settings = CliClockSettings(600_000, 10_000)
        saved_clock = CliClock(settings, 550_123_456_789, 123_456_789)
        saved_record = GameRecord(create_initial_position())
        saved_record.apply_move(Square(7, 7), Square(7, 6))
        gote_move = BoardMove(Square(3, 3), Square(3, 4), False)
        budget_inputs = []
        original_budget = cli.calculate_search_budget

        def calculate_budget(remaining_ms, byoyomi_ms, time_config):
            budget_inputs.append((remaining_ms, byoyomi_ms, time_config))
            return original_budget(remaining_ms, byoyomi_ms, time_config)

        with TemporaryDirectory() as directory:
            session_path = Path(directory) / "gote-to-move.json"
            saved_path = Path(directory) / "after-gote-move.json"
            CliSession(saved_record, saved_clock).save(session_path)
            times = iter((100_000, 15_100_100))
            with (
                patch.object(
                    cli, "calculate_search_budget", side_effect=calculate_budget
                ),
                patch.object(
                    game_search,
                    "search_move",
                    return_value=SearchResult(SearchCompletion.COMPLETE, gote_move),
                ) as search,
            ):
                record = cli.run_game(
                    input_fn=iter(
                        (f"load {session_path}", f"save {saved_path}", "resign")
                    ).__next__,
                    output_fn=lambda _: None,
                    mode=cli.GameMode.HUMAN_VS_COMPUTER,
                    clock_settings=CliClockSettings(10_000, 50_000),
                    time_config=config,
                    now_ns=times.__next__,
                )
            saved_session = CliSession.load(saved_path)

        expected_record = GameRecord.from_payload(saved_record.to_payload())
        expected_record.apply_move(gote_move.source, gote_move.destination)
        self.assertEqual(record.to_payload(), expected_record.to_payload())
        self.assertEqual(
            saved_session.record.to_payload(), expected_record.to_payload()
        )
        self.assertEqual(budget_inputs, [(123, 10_000, config)])
        self.assertEqual(search.call_count, 1)
        self.assertEqual(
            saved_session.clock,
            CliClock(settings, 550_123_456_789, 108_456_689),
        )

    def test_save_excludes_idle_time_and_preserves_error_state(self):
        """人間の待ち時間と保存失敗は時計を減らさず、成功保存は手と時計を揃える。

        load・人間入力・表示・save失敗の間に偽時計を大きく進め、探索中の15msだけを
        時計から差し引いた固定値と保存履歴を照合する。失敗後の同手番継続も確認する。
        """
        settings = CliClockSettings(600_000, 30_000)
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        gote_move = BoardMove(Square(3, 3), Square(3, 4), False)
        fake_now = [1_000]
        budget_inputs = []
        original_budget = cli.calculate_search_budget

        def input_with_idle_time():
            fake_now[0] += 3_600_000_000_000
            return next(commands)

        def output_with_idle_time(_text):
            fake_now[0] += 600_000_000_000

        def search_with_fixed_elapsed(_position, _policy, _rng, _control):
            fake_now[0] += 15_000_000
            return SearchResult(SearchCompletion.COMPLETE, gote_move)

        def calculate_budget(remaining_ms, byoyomi_ms, time_config):
            budget_inputs.append((remaining_ms, byoyomi_ms, time_config))
            return original_budget(remaining_ms, byoyomi_ms, time_config)

        with TemporaryDirectory() as directory:
            directory_path = Path(directory)
            legacy_path = directory_path / "legacy.json"
            failed_save_path = directory_path / "missing-parent" / "failed.json"
            saved_path = directory_path / "after-search.json"
            GameRecord(create_initial_position()).save(legacy_path)
            commands = iter(
                (
                    f"load {legacy_path}",
                    "move 7 7 7 6",
                    f"save {failed_save_path}",
                    f"save {saved_path}",
                    "resign",
                )
            )
            with (
                patch.object(
                    cli, "calculate_search_budget", side_effect=calculate_budget
                ),
                patch.object(
                    game_search, "search_move", side_effect=search_with_fixed_elapsed
                ),
            ):
                record = cli.run_game(
                    input_fn=input_with_idle_time,
                    output_fn=output_with_idle_time,
                    mode=cli.GameMode.HUMAN_VS_COMPUTER,
                    clock_settings=settings,
                    time_config=config,
                    now_ns=lambda: fake_now[0],
                )
            saved_session = CliSession.load(saved_path)

        expected_record = GameRecord(create_initial_position())
        expected_record.apply_move(Square(7, 7), Square(7, 6))
        expected_record.apply_move(gote_move.source, gote_move.destination)
        self.assertEqual(record.to_payload(), expected_record.to_payload())
        self.assertEqual(
            saved_session.record.to_payload(), expected_record.to_payload()
        )
        self.assertEqual(budget_inputs, [(600_000, 30_000, config)])
        self.assertEqual(
            saved_session.clock,
            CliClock(settings, 600_000_000_000, 599_985_000_000),
        )

    def test_keyboard_interrupt_from_computer_output_keeps_record_unmodified(self):
        """探索後の指し手表示中に中断したら履歴を変更せず対局を終える。

        出力完了前に手を適用する誤りや、中断後に探索を再実行する誤りを、履歴と
        探索呼出し回数で検出する。出力自体の原子性は要求しない。
        """
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        move = BoardMove(Square(7, 7), Square(7, 6), False)

        def interrupt_before_apply(text):
            if text.startswith("先手の指し手:"):
                raise KeyboardInterrupt

        with (
            patch.object(cli, "render_position", return_value="board"),
            patch.object(
                game_search,
                "search_move",
                return_value=SearchResult(SearchCompletion.COMPLETE, move),
            ) as search,
        ):
            record = cli.run_game(
                input_fn=lambda: self.fail("自動対局で入力を読まない"),
                output_fn=interrupt_before_apply,
                mode=cli.GameMode.COMPUTER_VS_COMPUTER,
                clock_settings=CliClockSettings(600, 30),
                time_config=config,
                now_ns=lambda: 0,
            )

        self.assertEqual(record.moves, ())
        search.assert_called_once()

    def test_search_and_clock_failures_propagate(self):
        """探索・予算・時刻の故障を停止結果や投了へ変換せず伝える。

        ValueError/RuntimeError/OSErrorの同一例外伝播と単調時計の逆行を確認し、
        予算・探索の障害を合法手なしや通常停止として隠す誤りを検出する。
        """
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        clock = CliClock.start(CliClockSettings(600, 30))

        for error in (
            ValueError("search failed"),
            RuntimeError("search failed"),
            OSError("search failed"),
        ):
            with self.subTest(error=type(error).__name__):
                record = GameRecord(create_initial_position())
                times = iter((100,))
                with patch.object(game_search, "search_move", side_effect=error):
                    with self.assertRaises(type(error)) as raised:
                        cli._run_computer_turn(
                            record,
                            RepetitionTracker.from_positions(record.iter_positions()),
                            random.Random(20261020),
                            lambda _: None,
                            MoveSelectionPolicy.RANDOM,
                            clock,
                            config,
                            lambda times=times: next(times),
                        )
                self.assertIs(raised.exception, error)
                self.assertEqual(record.moves, ())

        clock_error = RuntimeError("budget failed")
        with patch.object(cli, "calculate_search_budget", side_effect=clock_error):
            with self.assertRaises(RuntimeError) as raised:
                cli._run_computer_turn(
                    GameRecord(create_initial_position()),
                    RepetitionTracker.from_positions(
                        GameRecord(create_initial_position()).iter_positions()
                    ),
                    random.Random(20261020),
                    lambda _: None,
                    MoveSelectionPolicy.RANDOM,
                    clock,
                    config,
                    lambda: 100,
                )
        self.assertIs(raised.exception, clock_error)

        update_error = RuntimeError("clock update failed")
        with (
            patch.object(
                game_search,
                "search_move",
                return_value=SearchResult(SearchCompletion.COMPLETE, None),
            ),
            patch.object(CliClock, "after_turn", side_effect=update_error),
        ):
            with self.assertRaises(RuntimeError) as raised:
                cli._run_computer_turn(
                    GameRecord(create_initial_position()),
                    RepetitionTracker.from_positions(
                        GameRecord(create_initial_position()).iter_positions()
                    ),
                    random.Random(20261020),
                    lambda _: None,
                    MoveSelectionPolicy.RANDOM,
                    clock,
                    config,
                    lambda: 100,
                )
        self.assertIs(raised.exception, update_error)

        expiry_error = OSError("clock expiry check failed")
        with (
            patch.object(
                game_search,
                "search_move",
                return_value=SearchResult(SearchCompletion.COMPLETE, None),
            ),
            patch.object(CliClock, "is_expired", side_effect=expiry_error),
        ):
            with self.assertRaises(OSError) as raised:
                cli._run_computer_turn(
                    GameRecord(create_initial_position()),
                    RepetitionTracker.from_positions(
                        GameRecord(create_initial_position()).iter_positions()
                    ),
                    random.Random(20261020),
                    lambda _: None,
                    MoveSelectionPolicy.RANDOM,
                    clock,
                    config,
                    lambda: 100,
                )
        self.assertIs(raised.exception, expiry_error)

        regressing_times = iter((100, 99))
        with patch.object(
            game_search,
            "search_move",
            return_value=SearchResult(
                SearchCompletion.COMPLETE,
                BoardMove(Square(7, 7), Square(7, 6), False),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "elapsed_ns"):
                cli._run_computer_turn(
                    GameRecord(create_initial_position()),
                    RepetitionTracker.from_positions(
                        GameRecord(create_initial_position()).iter_positions()
                    ),
                    random.Random(20261020),
                    lambda _: None,
                    MoveSelectionPolicy.RANDOM,
                    clock,
                    config,
                    lambda: next(regressing_times),
                )

    def test_human_checkmate_and_clock_are_preserved(self):
        """人間手番の詰み判定を保ち、人間側の経過を時計から除く。

        コンピュータの着手で人間が詰んだ局面を次の人間手番で検出し、さらに入力・
        表示・適用が偽時計を進めても、コンピュータ探索の開始から返却までだけを
        消費時間へ計上することを確認する。
        """
        mate_board = Board()
        mate_board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
        mate_board.set_piece(Square(3, 8), Piece(PieceType.ROOK, Side.GOTE))
        mate_board.set_piece(Square(4, 7), Piece(PieceType.GOLD, Side.GOTE))
        for square in (Square(6, 8), Square(4, 9), Square(6, 9)):
            mate_board.set_piece(square, Piece(PieceType.PAWN, Side.SENTE))
        mate_board.set_piece(Square(9, 1), Piece(PieceType.KING, Side.GOTE))
        mate_position = Position(mate_board, Side.GOTE)
        mating_move = BoardMove(Square(3, 8), Square(5, 8), False)
        mate_outputs = []
        with (
            patch.object(cli, "create_initial_position", return_value=mate_position),
            patch.object(
                game_search,
                "search_move",
                return_value=SearchResult(SearchCompletion.COMPLETE, mating_move),
            ) as mate_search,
        ):
            mate_record = cli.run_game(
                input_fn=lambda: self.fail("詰み後の人間入力を読まない"),
                output_fn=mate_outputs.append,
                mode=cli.GameMode.HUMAN_VS_COMPUTER,
                clock_settings=CliClockSettings(600, 30),
                time_config=TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0),
                now_ns=lambda: 0,
            )

        self.assertEqual(mate_search.call_count, 1)
        self.assertEqual(
            mate_record.moves,
            (RecordedMove(Square(3, 8), Square(5, 8), False),),
        )
        self.assertIn("詰みです。後手の勝ちです。", mate_outputs)

        fake_time = [0]
        input_values = iter(("move 7 7 7 6", "resign"))
        elapsed_values = []
        search_move_value = BoardMove(Square(3, 3), Square(3, 4), False)
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        settings = CliClockSettings(600, 30)
        original_apply_command = cli._apply_command
        original_apply_selected_move = cli._apply_selected_move
        original_after_turn = CliClock.after_turn

        def render_with_elapsed(_position):
            fake_time[0] += 50_000_000
            return "board"

        def input_with_elapsed():
            fake_time[0] += 100_000_000
            return next(input_values)

        def output_with_elapsed(text):
            if "思考中です" in text:
                fake_time[0] += 70_000_000
            elif "の指し手: " in text:
                fake_time[0] += 20_000_000

        def apply_human_with_elapsed(record, command):
            fake_time[0] += 30_000_000
            original_apply_command(record, command)

        def apply_computer_with_elapsed(record, move):
            fake_time[0] += 30_000_000
            original_apply_selected_move(record, move)

        def search_with_elapsed(position, policy, rng, control):
            fake_time[0] += 25_000_000
            return SearchResult(SearchCompletion.COMPLETE, search_move_value)

        def after_turn(clock, side, elapsed_ns):
            elapsed_values.append((side, elapsed_ns))
            return original_after_turn(clock, side, elapsed_ns)

        now_reads = []

        def now_ns():
            now_reads.append(fake_time[0])
            return fake_time[0]

        with (
            patch.object(cli, "render_position", side_effect=render_with_elapsed),
            patch.object(cli, "_apply_command", side_effect=apply_human_with_elapsed),
            patch.object(
                cli, "_apply_selected_move", side_effect=apply_computer_with_elapsed
            ),
            patch.object(game_search, "search_move", side_effect=search_with_elapsed),
            patch.object(CliClock, "after_turn", new=after_turn),
        ):
            record = cli.run_game(
                input_fn=input_with_elapsed,
                output_fn=output_with_elapsed,
                rng=random.Random(20261020),
                clock_settings=settings,
                time_config=config,
                now_ns=now_ns,
            )

        self.assertEqual(
            record.moves,
            (
                RecordedMove(Square(7, 7), Square(7, 6), False),
                RecordedMove(Square(3, 3), Square(3, 4), False),
            ),
        )
        self.assertEqual(elapsed_values, [(Side.GOTE, 25_000_000)])
        self.assertEqual(len(now_reads), 2)
        self.assertEqual(now_reads[0], 300_000_000)
        self.assertEqual(
            now_reads[1] - now_reads[0],
            25_000_000,
        )
        self.assertEqual(
            fake_time[0] - now_reads[1],
            20_000_000 + 30_000_000 + 50_000_000 + 100_000_000,
        )

    def test_each_turn_owns_new_control_and_keeps_rng_policy_config(self):
        """複数手で制御を作り直し、対局のrng・方針・設定だけを共有する。

        一手目のstopを二手目へ引き継ぐ誤り、表示遅延の累積、方針・乱数・時間設定を
        手ごとに初期化または読み直す誤りを二手の独立イベントと三回目の中断で検出する。
        """
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        settings = CliClockSettings(600, 300)
        rng = random.Random(20261020)
        calls = []
        budget_inputs = []
        elapsed_values = []
        fake_now_ns = [0]
        policy = MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA
        sente_move = BoardMove(Square(7, 7), Square(7, 6), False)
        gote_move = BoardMove(Square(3, 3), Square(3, 4), False)

        def controlled_search(position, selected_policy, given_rng, control):
            calls.append((position, selected_policy, given_rng, control))
            if len(calls) == 1:
                control.request_stop()
                self.assertEqual(control.check().name, "STOP")
                fake_now_ns[0] += 10
                return SearchResult(SearchCompletion.COMPLETE, sente_move)
            if len(calls) == 2:
                self.assertEqual(control.check().name, "CONTINUE")
                fake_now_ns[0] += 20
                return SearchResult(SearchCompletion.COMPLETE, gote_move)
            raise KeyboardInterrupt

        def output(text):
            fake_now_ns[0] += 100_000 if "思考中です" in text else 200_000

        original_after_turn = CliClock.after_turn

        def after_turn(clock, side, elapsed_ns):
            elapsed_values.append((side, elapsed_ns))
            return original_after_turn(clock, side, elapsed_ns)

        original_budget = cli.calculate_search_budget

        def calculate(remaining_ms, byoyomi_ms, given_config):
            budget_inputs.append((remaining_ms, byoyomi_ms, given_config))
            return original_budget(remaining_ms, byoyomi_ms, given_config)

        with (
            patch.object(cli, "calculate_search_budget", side_effect=calculate),
            patch.object(
                game_search, "search_move", side_effect=controlled_search
            ) as search,
            patch.object(CliClock, "after_turn", new=after_turn),
        ):
            record = cli.run_game(
                input_fn=lambda: self.fail("自動対局で入力を読まない"),
                output_fn=output,
                rng=rng,
                mode=cli.GameMode.COMPUTER_VS_COMPUTER,
                move_selection_policy=policy,
                clock_settings=settings,
                time_config=config,
                now_ns=lambda: fake_now_ns[0],
            )

        self.assertEqual(search.call_count, 3)
        self.assertEqual(len(record.moves), 2)
        self.assertEqual(
            [call[0].side_to_move for call in calls[:2]], [Side.SENTE, Side.GOTE]
        )
        self.assertEqual([call[1] for call in calls], [policy, policy, policy])
        self.assertTrue(all(call[2] is rng for call in calls))
        self.assertIsNot(calls[0][3], calls[1][3])
        self.assertEqual(elapsed_values, [(Side.SENTE, 10), (Side.GOTE, 20)])
        self.assertEqual(
            budget_inputs,
            [(600, 300, config), (600, 300, config), (599, 300, config)],
        )

    def test_run_game_loads_config_once_and_reuses_injected_instance(self):
        """予算設定を対局準備時に一度読み、読込後も同一設定を使う。

        手番ごとや棋譜読込後にJSONを再読込する誤りと、直接呼出しで設定未注入時に
        読込を省く・注入済み設定を置き換える誤りを検出する。
        """
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 0)
        settings = CliClockSettings(600, 300)
        selected_moves = (
            BoardMove(Square(7, 7), Square(7, 6), False),
            BoardMove(Square(3, 3), Square(3, 4), False),
        )
        original_budget = cli.calculate_search_budget

        def play_computer_game(injected_config):
            search_calls = []
            budget_configs = []

            def search(position, policy, rng, control):
                search_calls.append((position, policy, rng, control))
                if len(search_calls) == 3:
                    raise KeyboardInterrupt
                return SearchResult(
                    SearchCompletion.COMPLETE, selected_moves[len(search_calls) - 1]
                )

            def calculate(remaining_ms, byoyomi_ms, time_config):
                budget_configs.append(time_config)
                return original_budget(remaining_ms, byoyomi_ms, time_config)

            with (
                patch.object(
                    cli, "load_time_management_config", return_value=config
                ) as load_config,
                patch.object(cli, "calculate_search_budget", side_effect=calculate),
                patch.object(game_search, "search_move", side_effect=search),
            ):
                record = cli.run_game(
                    input_fn=lambda: self.fail("自動対局で入力を読まない"),
                    output_fn=lambda _: None,
                    mode=cli.GameMode.COMPUTER_VS_COMPUTER,
                    clock_settings=settings,
                    time_config=injected_config,
                    now_ns=lambda: 10_000,
                )
            return record, search_calls, budget_configs, load_config

        record, calls, budget_configs, loader = play_computer_game(None)
        self.assertEqual(len(record.moves), 2)
        self.assertEqual(len(calls), 3)
        loader.assert_called_once_with()
        self.assertEqual(budget_configs, [config, config, config])
        self.assertTrue(all(used_config is config for used_config in budget_configs))

        record, calls, budget_configs, loader = play_computer_game(config)
        self.assertEqual(len(record.moves), 2)
        self.assertEqual(len(calls), 3)
        loader.assert_not_called()
        self.assertEqual(budget_configs, [config, config, config])
        self.assertTrue(all(used_config is config for used_config in budget_configs))

        loaded_position = create_initial_position()
        loaded_position.side_to_move = Side.GOTE
        loaded_record = GameRecord(loaded_position)
        loaded_budget_configs = []

        def calculate_loaded(remaining_ms, byoyomi_ms, time_config):
            loaded_budget_configs.append(time_config)
            return original_budget(remaining_ms, byoyomi_ms, time_config)

        with (
            patch.object(
                cli, "load_time_management_config", return_value=config
            ) as load_config,
            patch.object(
                CliSession, "load", return_value=CliSession(loaded_record, None)
            ) as load_session,
            patch.object(cli, "calculate_search_budget", side_effect=calculate_loaded),
            patch.object(
                game_search,
                "search_move",
                return_value=SearchResult(SearchCompletion.COMPLETE, selected_moves[1]),
            ),
        ):
            record = cli.run_game(
                input_fn=iter(("load saved.json", "resign")).__next__,
                output_fn=lambda _: None,
                mode=cli.GameMode.HUMAN_VS_COMPUTER,
                clock_settings=settings,
                now_ns=lambda: 10_000,
            )

        load_config.assert_called_once_with()
        load_session.assert_called_once_with("saved.json")
        self.assertEqual(loaded_budget_configs, [config])
        self.assertEqual(len(record.moves), 1)


if __name__ == "__main__":
    unittest.main()
