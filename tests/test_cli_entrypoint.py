"""CLI実行入口の実プロセス境界を限定的なスモークテストで確認する。"""

from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from kaname_shogi import __main__ as entrypoint
from kaname_shogi.cli import GameMode
from kaname_shogi.movegen import MoveSelectionPolicy


class CliEntrypointTests(unittest.TestCase):
    def test_main_prompts_for_policy_only_when_computer_participates(self):
        """mainはコンピュータ参加時だけ一度方針を尋ね、結果を対局へ渡す。

        人間対人間で不要な選択を表示したり、コンピュータ対局へ選択値を渡さない
        誤りを検出する。
        """
        main = getattr(entrypoint, "main", None)
        self.assertIsNotNone(main, "main がまだ実装されていません")

        for mode in GameMode:
            with self.subTest(mode=mode):
                with patch.object(entrypoint, "choose_game_mode",
                                  return_value=mode), \
                        patch.object(entrypoint, "choose_move_selection_policy",
                                     create=True,
                                     return_value=MoveSelectionPolicy.MATERIAL) as choose_policy, \
                        patch.object(entrypoint, "run_game") as run_game:
                    result = main()

                self.assertEqual(result, 0)
                if mode == GameMode.HUMAN_VS_HUMAN:
                    choose_policy.assert_not_called()
                    run_game.assert_called_once_with(mode=mode)
                else:
                    choose_policy.assert_called_once_with()
                    run_game.assert_called_once_with(
                        mode=mode,
                        move_selection_policy=MoveSelectionPolicy.MATERIAL)


class CliEntrypointSmokeTests(unittest.TestCase):
    def test_cli_exits_from_game_mode_menu_on_eof(self):
        """CLIは対局形式メニューでEOFなら、対局を始めず終了する。

        実プロセスで起動し、入口のメニュー・入力終了・対局開始前に盤面を表示しない
        ことを確認する。
        """
        result = subprocess.run(
            [sys.executable, "-m", "kaname_shogi"],
            cwd=Path(__file__).resolve().parents[1],
            input="", capture_output=True, text=True, encoding="utf-8", check=False,
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
        """実入口は対局形式の後、初期盤面を出す前に一度だけ方針を尋ねる。

        対局開始後に方針を選ばせたり、コンピュータ参加形式で選択を飛ばす誤りを
        検出する。
        """
        result = subprocess.run(
            [sys.executable, "-m", "kaname_shogi"],
            cwd=Path(__file__).resolve().parents[1],
            input="2\n\nresign\n", capture_output=True, text=True,
            encoding="utf-8", check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.count("一手選択方針を選んでください"), 1)
        mode_index = result.stdout.index("対局形式を選んでください")
        policy_index = result.stdout.index("一手選択方針を選んでください")
        board_index = result.stdout.index("手番：先手")
        self.assertLess(mode_index, policy_index)
        self.assertLess(policy_index, board_index)
