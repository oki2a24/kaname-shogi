"""CLI実行入口の実プロセス境界を限定的なスモークテストで確認する。"""

import subprocess
import sys
import unittest
from fractions import Fraction
from io import StringIO
from pathlib import Path
from unittest.mock import call, patch

from kaname_shogi import __main__ as entrypoint
from kaname_shogi.cli import GameMode
from kaname_shogi.cli_clock import CliClockSettings
from kaname_shogi.model import Side
from kaname_shogi.movegen import MoveSelectionPolicy
from kaname_shogi.time_management import TimeManagementConfig


class CliEntrypointTests(unittest.TestCase):
    def test_main_prompts_and_loads_config_only_for_computer(self):
        """mainは対局形式ごとに必要側だけを選び設定を対局へ渡す。

        人間同士への選択追加、HVCの先手選択、CVCの選択回数・順序、設定の欠落を検出する。
        """
        main = getattr(entrypoint, "main", None)
        self.assertIsNotNone(main, "main がまだ実装されていません")
        settings = CliClockSettings(600_000, 30_000)
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 2000)
        selected_policies = {
            Side.SENTE: MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE,
            Side.GOTE: MoveSelectionPolicy.MATERIAL,
        }

        for mode in GameMode:
            with self.subTest(mode=mode):
                events = []
                outputs = []

                def choose_mode(events=events, mode=mode):
                    events.append("mode")
                    return mode

                def choose_policy(*, side=None, events=events):
                    events.append(("policy", side))
                    return selected_policies.get(side, selected_policies[Side.GOTE])

                def choose_clock(events=events):
                    events.append("clock")
                    return settings

                def load_config(events=events):
                    events.append("config")
                    return config

                def display(text, events=events, outputs=outputs):
                    events.append(("display", text))
                    outputs.append(text)

                def run_game_side_effect(events=events, **kwargs):
                    events.append("game")

                with (
                    patch.object(
                        entrypoint, "choose_game_mode", side_effect=choose_mode
                    ),
                    patch.object(
                        entrypoint,
                        "choose_move_selection_policy",
                        create=True,
                        side_effect=choose_policy,
                    ) as choose_policy_mock,
                    patch.object(
                        entrypoint,
                        "choose_clock_settings",
                        create=True,
                        side_effect=choose_clock,
                    ) as choose_clock_mock,
                    patch.object(
                        entrypoint,
                        "load_time_management_config",
                        create=True,
                        side_effect=load_config,
                    ) as load_config_mock,
                    patch.object(
                        entrypoint, "run_game", side_effect=run_game_side_effect
                    ) as run_game,
                    patch("builtins.print", side_effect=display),
                ):
                    result = main()

                self.assertEqual(result, 0)
                if mode == GameMode.HUMAN_VS_HUMAN:
                    choose_policy_mock.assert_not_called()
                    choose_clock_mock.assert_not_called()
                    load_config_mock.assert_not_called()
                    run_game.assert_called_once_with(mode=mode)
                    self.assertEqual(events, ["mode", "game"])
                    self.assertEqual(outputs, [])
                else:
                    self.assertEqual(
                        choose_policy_mock.call_args_list,
                        (
                            [call(side=Side.GOTE)]
                            if mode == GameMode.HUMAN_VS_COMPUTER
                            else [call(side=Side.SENTE), call(side=Side.GOTE)]
                        ),
                    )
                    choose_clock_mock.assert_called_once_with()
                    load_config_mock.assert_called_once_with()
                    expected_policies = (
                        {Side.GOTE: selected_policies[Side.GOTE]}
                        if mode == GameMode.HUMAN_VS_COMPUTER
                        else selected_policies
                    )
                    run_game.assert_called_once_with(
                        mode=mode,
                        move_selection_policies=expected_policies,
                        clock_settings=settings,
                        time_config=config,
                    )
                    self.assertLess(events.index("config"), events.index("game"))
                    self.assertEqual(len(outputs), 1)
                    self.assertLess(
                        events.index(
                            next(event for event in events if isinstance(event, tuple))
                        ),
                        events.index("game"),
                    )

    def test_main_prompts_sente_then_gote_for_computer_vs_computer(self):
        """CVCは先手を選んだ後に後手を選び、割当名を開始前に表示する。

        二つの選択を逆順にしたり、表示名とrun_gameへ渡す方針を食い違わせる誤りを検出する。
        """
        outputs = []
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 2000)
        choices = iter(
            (
                MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE,
                MoveSelectionPolicy.MATERIAL,
            )
        )
        with (
            patch.object(
                entrypoint,
                "choose_game_mode",
                return_value=GameMode.COMPUTER_VS_COMPUTER,
            ),
            patch.object(
                entrypoint,
                "choose_move_selection_policy",
                create=True,
                side_effect=lambda **kwargs: next(choices),
            ) as choose_policy,
            patch.object(
                entrypoint,
                "choose_clock_settings",
                return_value=CliClockSettings(600_000, 30_000),
            ),
            patch.object(
                entrypoint, "load_time_management_config", return_value=config
            ),
            patch.object(entrypoint, "run_game") as run_game,
            patch("builtins.print", side_effect=outputs.append),
        ):
            self.assertEqual(entrypoint.main(), 0)

        self.assertEqual(
            choose_policy.call_args_list,
            [call(side=Side.SENTE), call(side=Side.GOTE)],
        )
        run_game.assert_called_once_with(
            mode=GameMode.COMPUTER_VS_COMPUTER,
            move_selection_policies={
                Side.SENTE: MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE,
                Side.GOTE: MoveSelectionPolicy.MATERIAL,
            },
            clock_settings=CliClockSettings(600_000, 30_000),
            time_config=config,
        )
        self.assertEqual(
            outputs,
            ["選択方針：先手=一手駒得＋支えのない狙われた駒、後手=一手駒得"],
        )

    def test_main_selects_only_gote_for_human_vs_computer(self):
        """人間対コンピュータは自動担当の後手だけを選び先手を人間と表示する。

        人間側へ無意味な方針を尋ねたり、人間を自動担当として表示する誤りを検出する。
        """
        config = TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 2000)
        outputs = []
        with (
            patch.object(
                entrypoint,
                "choose_game_mode",
                return_value=GameMode.HUMAN_VS_COMPUTER,
            ),
            patch.object(
                entrypoint,
                "choose_move_selection_policy",
                create=True,
                return_value=MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE,
            ) as choose_policy,
            patch.object(
                entrypoint,
                "choose_clock_settings",
                return_value=CliClockSettings(600_000, 30_000),
            ),
            patch.object(
                entrypoint, "load_time_management_config", return_value=config
            ),
            patch.object(entrypoint, "run_game") as run_game,
            patch("builtins.print", side_effect=outputs.append),
        ):
            self.assertEqual(entrypoint.main(), 0)

        choose_policy.assert_called_once_with(side=Side.GOTE)
        run_game.assert_called_once_with(
            mode=GameMode.HUMAN_VS_COMPUTER,
            move_selection_policies={
                Side.GOTE: MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE
            },
            clock_settings=CliClockSettings(600_000, 30_000),
            time_config=config,
        )
        self.assertEqual(
            outputs,
            ["選択方針：先手=人間、後手=一手駒得＋支えのない狙われた駒"],
        )

    def test_config_failure_is_stderr_exit_one_before_game(self):
        """時間設定の読込故障だけをstderrと終了1へ変換する。

        設定故障後に対局を始める誤りと、探索・対局のValueErrorを設定失敗として
        誤分類する境界の広げ過ぎを検出する。
        """
        for error in (ValueError("invalid settings"), OSError("missing settings")):
            with self.subTest(error=type(error).__name__):
                stderr = StringIO()
                with (
                    patch.object(
                        entrypoint,
                        "choose_game_mode",
                        return_value=GameMode.HUMAN_VS_COMPUTER,
                    ),
                    patch.object(
                        entrypoint,
                        "choose_move_selection_policy",
                        create=True,
                        return_value=MoveSelectionPolicy.RANDOM,
                    ),
                    patch.object(
                        entrypoint,
                        "choose_clock_settings",
                        create=True,
                        return_value=CliClockSettings(600_000, 30_000),
                    ),
                    patch.object(
                        entrypoint,
                        "load_time_management_config",
                        create=True,
                        side_effect=error,
                    ),
                    patch.object(entrypoint, "run_game") as run_game,
                    patch.object(sys, "stderr", stderr),
                ):
                    result = entrypoint.main()

                self.assertEqual(result, 1)
                self.assertIn(str(error), stderr.getvalue())
                run_game.assert_not_called()

        search_error = ValueError("search fault")
        stderr = StringIO()
        with (
            patch.object(
                entrypoint,
                "choose_game_mode",
                return_value=GameMode.HUMAN_VS_COMPUTER,
            ),
            patch.object(
                entrypoint,
                "choose_move_selection_policy",
                create=True,
                return_value=MoveSelectionPolicy.RANDOM,
            ),
            patch.object(
                entrypoint,
                "choose_clock_settings",
                create=True,
                return_value=CliClockSettings(600_000, 30_000),
            ),
            patch.object(
                entrypoint,
                "load_time_management_config",
                create=True,
                return_value=TimeManagementConfig(
                    20, Fraction(2), Fraction(3, 4), 2000
                ),
            ),
            patch.object(entrypoint, "run_game", side_effect=search_error),
            patch.object(sys, "stderr", stderr),
        ):
            with self.assertRaises(ValueError) as raised:
                entrypoint.main()

        self.assertIs(raised.exception, search_error)
        self.assertEqual(stderr.getvalue(), "")

    def test_clock_input_eof_or_interrupt_ends_before_game(self):
        """時計メニューのEOFとCtrl-Cは対局を始めず正常終了する。"""
        for interruption in (EOFError, KeyboardInterrupt):
            with self.subTest(interruption=interruption.__name__):
                stdout = StringIO()
                with (
                    patch.object(
                        entrypoint,
                        "choose_game_mode",
                        return_value=GameMode.HUMAN_VS_COMPUTER,
                    ),
                    patch.object(
                        entrypoint,
                        "choose_move_selection_policy",
                        create=True,
                        return_value=MoveSelectionPolicy.RANDOM,
                    ),
                    patch.object(
                        entrypoint,
                        "choose_clock_settings",
                        create=True,
                        side_effect=interruption,
                    ),
                    patch.object(entrypoint, "run_game") as run_game,
                    patch(
                        "builtins.print",
                        side_effect=lambda *args, output=stdout, **kwargs: output.write(
                            "入力を終了しました。\n"
                        ),
                    ),
                ):
                    result = entrypoint.main()

                self.assertEqual(result, 0)
                self.assertEqual(stdout.getvalue(), "入力を終了しました。\n")
                run_game.assert_not_called()


class CliEntrypointSmokeTests(unittest.TestCase):
    def test_cli_exits_from_game_mode_menu_on_eof(self):
        """CLIは対局形式メニューでEOFなら、対局を始めず終了する。

        実プロセスで起動し、入口のメニュー・入力終了・対局開始前に盤面を表示しない
        ことを確認する。
        """
        result = subprocess.run(
            [sys.executable, "-m", "kaname_shogi"],
            cwd=Path(__file__).resolve().parents[1],
            input="",
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "対局形式を選んでください（1: 人間対人間、2: 人間対コンピュータ、"
            "3: コンピュータ対コンピュータ）:\n"
            "入力を終了しました。\n",
        )
        self.assertEqual(result.stderr, "")

    def test_entrypoint_prompts_for_policy_after_computer_game_mode(self):
        """実入口は方針・時計を設定してから初期盤面と対局を始める。

        対局開始後に方針を選ばせたり、コンピュータ参加形式で選択を飛ばす誤りを
        検出する。
        """
        result = subprocess.run(
            [sys.executable, "-m", "kaname_shogi"],
            cwd=Path(__file__).resolve().parents[1],
            input="2\n\n\n\nresign\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.count("後手の一手選択方針を選んでください"), 1)
        self.assertEqual(result.stdout.count("コンピュータの持ち時間"), 1)
        self.assertEqual(result.stdout.count("秒読み（秒"), 1)
        mode_index = result.stdout.index("対局形式を選んでください")
        policy_index = result.stdout.index("後手の一手選択方針を選んでください")
        clock_index = result.stdout.index("コンピュータの持ち時間")
        byoyomi_index = result.stdout.index("秒読み（秒")
        board_index = result.stdout.index("手番：先手")
        selection_index = result.stdout.index("選択方針：先手=人間、後手=ランダム")
        self.assertLess(mode_index, policy_index)
        self.assertLess(policy_index, clock_index)
        self.assertLess(clock_index, byoyomi_index)
        self.assertLess(byoyomi_index, selection_index)
        self.assertLess(selection_index, board_index)

    def test_human_vs_human_entry_skips_clock_and_config(self):
        """実入口の人間同士は時計欄を出さず対局を始める。"""
        result = subprocess.run(
            [sys.executable, "-m", "kaname_shogi"],
            cwd=Path(__file__).resolve().parents[1],
            input="1\nresign\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertNotIn("一手選択方針を選んでください", result.stdout)
        self.assertNotIn("コンピュータの持ち時間", result.stdout)
        self.assertNotIn("秒読み（秒", result.stdout)
        self.assertIn("先手が投了しました。後手の勝ちです。", result.stdout)

    def test_entrypoint_clock_input_eof_exits_without_starting_game(self):
        """実入口は時計欄の入力終了時に盤面を出さず正常終了する。"""
        result = subprocess.run(
            [sys.executable, "-m", "kaname_shogi"],
            cwd=Path(__file__).resolve().parents[1],
            input="2\n\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("コンピュータの持ち時間", result.stdout)
        self.assertIn("入力を終了しました。", result.stdout)
        self.assertNotIn("手番：先手", result.stdout)
