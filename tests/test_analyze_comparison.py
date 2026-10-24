"""完了比較の分析CLIと保存境界を確認する。"""

from __future__ import annotations

import hashlib
import io
import json
import math
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from kaname_shogi import comparison_result_io
from kaname_shogi.analyze_comparison import main
from tests.test_comparison_result_io import (
    _make_parallel_conditions,
    _write_handwritten_experiment,
)


class AnalyzeComparisonCliTests(unittest.TestCase):
    def test_pilot_writes_one_overall_interval_and_keeps_inputs_unchanged(self):
        """pilotを正常保存し、判断を予備比較扱いにして原実験を保つ。

        判断不能/pilotを異常終了へ変換する、複数の層別区間を正式判断扱いする、または
        conditions・棋譜・summaryを分析時に書き換える誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            snapshots = {path.name: path.read_bytes() for path in input_dir.iterdir()}
            output = Path(directory) / "analysis.json"

            status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 0)
            payload = json.loads(output.read_bytes())
            self.assertEqual(
                set(payload),
                {
                    "format",
                    "inputs",
                    "analyzer",
                    "purpose",
                    "baseline",
                    "candidate",
                    "assumptions",
                    "confidence_level",
                    "method",
                    "planned_games",
                    "completed_pairs",
                    "counts",
                    "score",
                    "by_position",
                    "by_side",
                    "move_time_by_policy",
                    "elapsed_ns",
                },
            )
            self.assertEqual(payload["format"], "kaname-shogi-comparison-analysis-v1")
            self.assertEqual(payload["purpose"], "pilot")
            self.assertEqual(payload["planned_games"], 2)
            self.assertEqual(payload["completed_pairs"], 1)
            self.assertEqual(payload["confidence_level"], 0.95)
            self.assertEqual(payload["method"], "hoeffding-paired-bounds-v1")
            self.assertEqual(
                payload["score"],
                {
                    "lower_mean": 0.0,
                    "upper_mean": 1.0,
                    "radius": payload["score"]["radius"],
                    "lower": 0.0,
                    "upper": 1.0,
                    "decision": "exploratory",
                },
            )
            self.assertAlmostEqual(
                payload["score"]["radius"], math.sqrt(math.log(40) / 2)
            )
            self.assertTrue(
                all(
                    isinstance(payload["score"][key], (int, float))
                    and math.isfinite(payload["score"][key])
                    for key in ("lower_mean", "upper_mean", "radius", "lower", "upper")
                )
            )
            self.assertEqual(
                payload["assumptions"],
                {
                    "independent_unit": "pair",
                    "games_within_pair_independent": False,
                    "identically_distributed_pairs_required": False,
                    "primary_comparisons": 1,
                    "configured_positions_equal_weight": True,
                    "unresolved_game_score_bounds": [0.0, 1.0],
                },
            )
            self.assertEqual(payload["counts"]["games"], 2)
            self.assertEqual(payload["counts"]["completed_pairs"], 1)
            self.assertEqual(payload["counts"]["results"]["ply_limit"], 2)
            self.assertEqual(payload["counts"]["candidate_wins"], 0)
            self.assertEqual(payload["counts"]["candidate_losses"], 0)
            self.assertEqual(payload["counts"]["ordinary_repetitions"], 0)
            self.assertEqual(payload["counts"]["ply_limits"], 2)
            self.assertEqual(payload["counts"]["unresolved_double_perpetual_checks"], 0)
            self.assertEqual(payload["by_position"]["initial"]["pairs"], 1)
            self.assertEqual(
                payload["by_position"]["initial"]["results"]["ply_limit"], 2
            )
            self.assertEqual(payload["by_side"]["candidate_sente"]["games"], 1)
            self.assertEqual(payload["by_side"]["candidate_gote"]["games"], 1)
            self.assertEqual(
                payload["move_time_by_policy"],
                json.loads(snapshots["summary.json"])["move_time_by_policy"],
            )
            self.assertEqual(payload["elapsed_ns"], 999)
            self.assertEqual(
                payload["inputs"]["conditions"],
                {
                    "file": "conditions.json",
                    "sha256": hashlib.sha256(snapshots["conditions.json"]).hexdigest(),
                },
            )
            self.assertEqual(
                payload["inputs"]["games"],
                [
                    {
                        "file": name,
                        "sha256": hashlib.sha256(snapshots[name]).hexdigest(),
                    }
                    for name in ("game-000001.json", "game-000002.json")
                ],
            )
            self.assertEqual(
                payload["inputs"]["summary"],
                {
                    "file": "summary.json",
                    "sha256": hashlib.sha256(snapshots["summary.json"]).hexdigest(),
                },
            )
            self.assertEqual(
                set(payload["analyzer"]), {"source_sha256", "git", "runtime"}
            )
            self.assertEqual(len(payload["analyzer"]["source_sha256"]), 64)
            self.assertEqual(
                set(payload["analyzer"]["runtime"]),
                {"python_version", "python_implementation", "platform"},
            )
            self.assertEqual(
                set(path.name for path in input_dir.iterdir()), set(snapshots)
            )
            self.assertEqual(
                {path.name: path.read_bytes() for path in input_dir.iterdir()},
                snapshots,
            )

    def test_rejects_in_flight_or_running_summary_v2_before_analysis_output(self):
        """投入中または実行中のsummary v2は分析結果を作らない。

        完了前の比較を確定データとして分析したり、投入中局を無視して強さ判定へ渡す
        誤りを検出する。
        """
        cases = (
            ("in-flight", "投入中の局が残るsummary"),
            ("running", "summaryが保存局の再集計または実行件数と一致しません"),
        )
        for name, error_text in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                input_dir = Path(directory) / "input"
                input_dir.mkdir()
                _write_handwritten_experiment(input_dir)
                _make_parallel_conditions(input_dir)
                summary_path = input_dir / "summary.json"
                summary = json.loads(summary_path.read_bytes())
                summary["format"] = "kaname-shogi-comparison-summary-v2"
                summary["in_flight_games"] = 1 if name == "in-flight" else 0
                if name == "running":
                    summary["status"] = "running"
                summary_path.write_text(json.dumps(summary), encoding="utf-8")
                output = Path(directory) / "analysis.json"
                stderr = io.StringIO()

                with redirect_stderr(stderr):
                    status = main(
                        ["--input-dir", str(input_dir), "--output", str(output)]
                    )

                self.assertEqual(status, 2)
                self.assertIn(error_text, stderr.getvalue())
                self.assertFalse(output.exists())

    def test_input_error_creates_no_output_and_existing_output_is_preserved(self):
        """入力/既存出力先の不正は2を返し、既存ファイルを上書きしない。

        一局のconditions参照不一致を通す、出力前にanalysisを作る、または既存成果物を
        置き換える誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            game_path = input_dir / "game-000002.json"
            game = json.loads(game_path.read_bytes())
            game["conditions_sha256"] = "d" * 64
            game_path.write_text(json.dumps(game), encoding="utf-8")
            output = Path(directory) / "invalid-analysis.json"

            status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 2)
            self.assertFalse(output.exists())

        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "existing-analysis.json"
            output.write_text("keep this", encoding="utf-8")

            status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep this")

    def test_save_failure_returns_one_after_valid_input(self):
        """検証後の保存故障は1を返し、入力不正と終了コードを分ける。

        書込み失敗を入力エラー2や成功0へ誤変換するCLI契約違反を検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "failed-save.json"
            with patch.object(
                comparison_result_io,
                "write_new_json",
                side_effect=OSError("simulated write failure"),
            ):
                status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 1)
            self.assertFalse(output.exists())

    def test_interruption_returns_130_without_creating_output(self):
        """分析開始中のCtrl-Cを130へ写し、出力ファイルを作らない。

        KeyboardInterruptを入力不正や通常完了として扱う、または分析途中のJSONを
        残す誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            output = Path(directory) / "interrupted.json"
            with patch.object(
                comparison_result_io,
                "load_completed_comparison",
                side_effect=KeyboardInterrupt,
            ):
                status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 130)
            self.assertFalse(output.exists())

    def test_interruption_during_save_returns_130(self):
        """排他的保存中のKeyboardInterruptも通常中断コードへ写す。

        ファイル書込みの割込みを例外で漏らし、CLIを130以外で終了させる誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "interrupted-save.json"
            with patch.object(
                comparison_result_io,
                "write_new_json",
                side_effect=KeyboardInterrupt,
            ):
                status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 130)
            self.assertFalse(output.exists())
