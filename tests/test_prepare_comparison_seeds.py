"""乱数種準備CLIの入力検証・出力境界・終了コードを確認する。"""

import contextlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    prepare_module = importlib.import_module("kaname_shogi.prepare_comparison_seeds")
except ModuleNotFoundError as error:
    if error.name != "kaname_shogi.prepare_comparison_seeds":
        raise
    prepare_module = None

main = getattr(prepare_module, "main", None)


class PrepareComparisonSeedsCliTests(unittest.TestCase):
    def _require_implementation(self):
        """CLI入口が未実装なら機能不足として失敗させる。"""
        self.assertIsNotNone(main, "乱数種準備CLIが未実装です")

    @staticmethod
    def _write_positions(directory, *, second_setup_moves=None):
        """指定した全準備手順を持つ最小の局面セットを保存する。"""
        entries = [
            {"id": "a", "setup_moves": [], "rationale": "平手"},
        ]
        if second_setup_moves is not None:
            entries.append(
                {
                    "id": "b",
                    "setup_moves": second_setup_moves,
                    "rationale": "追加局面",
                }
            )
        path = Path(directory) / "positions.json"
        path.write_text(
            json.dumps(
                {
                    "format": "kaname-shogi-comparison-positions-v1",
                    "id": "fixture",
                    "positions": entries,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _args(positions_path, output_path, **overrides):
        """準備CLIの必須引数を作り、指定値だけを上書きする。"""
        values = {
            "--positions": str(positions_path),
            "--pairs-per-position": "1",
            "--purpose": "pilot",
            "--output": str(output_path),
        }
        values.update(overrides)
        return [item for pair in values.items() for item in pair]

    def _capture(self, argv):
        """CLIの終了コードと標準出力・標準エラーを回収する。"""
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(argv)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_help_needs_no_seed_inputs(self):
        """helpは局面ファイルや保存先なしで使い方を表示する。

        入力の読込や乱数抽出をhelp表示前に始める誤りを検出する。
        """
        self._require_implementation()
        with patch.object(prepare_module, "positions_from_bytes") as read_positions:
            exit_code, stdout, stderr = self._capture(["--help"])

        self.assertEqual(exit_code, 0)
        self.assertIn("--positions", stdout)
        self.assertIn("--pairs-per-position", stdout)
        self.assertIn("--purpose", stdout)
        self.assertIn("--output", stdout)
        self.assertEqual(stderr, "")
        read_positions.assert_not_called()

    def test_real_process_creates_one_pair_for_one_position(self):
        """実プロセスがOS乱数源で一局面一組の一覧を新規生成する。

        CLI関数の直接呼出しだけ成功し、module実行入口や保存契約が壊れる誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._write_positions(directory)
            output_path = Path(directory) / "seeds.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "kaname_shogi.prepare_comparison_seeds",
                    *self._args(positions_path, output_path),
                ],
                cwd=Path(__file__).parents[1],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["purpose"], "pilot")
            self.assertEqual(payload["position_ids"], ["a"])
            self.assertEqual(payload["pairs_per_position"], 1)
            self.assertEqual(len(payload["pairs"]), 1)
            self.assertEqual(payload["pairs"][0]["position_id"], "a")
            self.assertEqual(payload["pairs"][0]["repetition_index"], 0)
            for key in ("baseline_seed", "candidate_seed"):
                self.assertGreaterEqual(payload["pairs"][0][key], 0)
                self.assertLess(payload["pairs"][0][key], 1 << 128)

    def test_invalid_later_position_fails_before_randomness_or_output(self):
        """後半局面の不正手を検出し、乱数抽出と出力作成を行わない。

        先頭局面だけを検証して種を消費し、実験一覧を不完全な状態で作る誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._write_positions(
                directory, second_setup_moves=["7g7f", "7g7f"]
            )
            output_path = Path(directory) / "seeds.json"
            with patch.object(prepare_module, "generate_seed_plan") as generator:
                exit_code, _, stderr = self._capture(
                    self._args(positions_path, output_path)
                )

            self.assertEqual(exit_code, 2)
            self.assertIn("入力エラー", stderr)
            generator.assert_not_called()
            self.assertFalse(output_path.exists())

    def test_existing_output_and_missing_parent_fail_before_randomness(self):
        """既存出力と未作成の親を入力エラーとして、乱数前に拒否する。

        既存の種一覧を上書きする、または検証途中に階層を作る誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._write_positions(directory)
            existing = Path(directory) / "existing.json"
            existing.write_text("keep", encoding="utf-8")
            missing_parent = Path(directory) / "missing" / "seeds.json"
            for output_path in (existing, missing_parent):
                with self.subTest(output=output_path):
                    with patch.object(
                        prepare_module, "generate_seed_plan"
                    ) as generator:
                        exit_code, _, stderr = self._capture(
                            self._args(positions_path, output_path)
                        )
                    self.assertEqual(exit_code, 2)
                    self.assertIn("入力エラー", stderr)
                    generator.assert_not_called()
            self.assertEqual(existing.read_text(encoding="utf-8"), "keep")
            self.assertFalse(missing_parent.parent.exists())

            dangling_link = Path(directory) / "dangling.json"
            dangling_link.symlink_to(Path(directory) / "not-created.json")
            with patch.object(prepare_module, "generate_seed_plan") as generator:
                exit_code, _, stderr = self._capture(
                    self._args(positions_path, dangling_link)
                )
            self.assertEqual(exit_code, 2)
            self.assertIn("入力エラー", stderr)
            generator.assert_not_called()
            self.assertTrue(dangling_link.is_symlink())
            self.assertFalse((Path(directory) / "not-created.json").exists())

    def test_save_failure_returns_one_and_keyboard_interrupt_returns_130(self):
        """保存故障は1、中断は130で返し、後続の保存を行わない。

        実行・保存失敗を入力エラー2や正常終了0として報告する誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._write_positions(directory)
            output_path = Path(directory) / "seeds.json"
            with patch.object(
                prepare_module, "write_new_json", side_effect=OSError("保存故障")
            ):
                save_code, _, save_stderr = self._capture(
                    self._args(positions_path, output_path)
                )
            self.assertEqual(save_code, 1)
            self.assertIn("保存", save_stderr)
            self.assertFalse(output_path.exists())

            with patch.object(
                prepare_module,
                "generate_seed_plan",
                side_effect=KeyboardInterrupt,
            ) as generator:
                with patch.object(prepare_module, "write_new_json") as writer:
                    interrupt_code, _, _ = self._capture(
                        self._args(positions_path, output_path)
                    )
            self.assertEqual(interrupt_code, 130)
            generator.assert_called_once()
            writer.assert_not_called()
            self.assertFalse(output_path.exists())

    def test_invalid_cli_arguments_return_two_without_output(self):
        """未知目的・不正組数・不足引数を入力エラー2で拒否する。

        値の誤りを実行故障1や正常終了として扱い、成果物を作る誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._write_positions(directory)
            output_path = Path(directory) / "seeds.json"
            invalid_args = (
                self._args(positions_path, output_path, **{"--purpose": "other"}),
                self._args(
                    positions_path,
                    output_path,
                    **{"--pairs-per-position": "0"},
                ),
                ["--positions", str(positions_path)],
            )
            for argv in invalid_args:
                with self.subTest(argv=argv):
                    with patch.object(
                        prepare_module, "generate_seed_plan"
                    ) as generator:
                        exit_code, _, stderr = self._capture(argv)
                    self.assertEqual(exit_code, 2)
                    self.assertIn("入力エラー", stderr)
                    generator.assert_not_called()
                    self.assertFalse(output_path.exists())
