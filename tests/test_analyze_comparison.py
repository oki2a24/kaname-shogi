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
    def _interrupt_after_first_game(self, input_dir: Path, output: Path) -> Path:
        """一局完了直後に中断し、作成済みcheckpoint pathを返す。"""
        original_load_game = comparison_result_io._load_game

        def interrupt_on_second_game(payload, scheduled_game, config, **kwargs):
            if scheduled_game.game_id == "game-000002":
                raise KeyboardInterrupt
            return original_load_game(payload, scheduled_game, config, **kwargs)

        with patch.object(
            comparison_result_io, "_load_game", side_effect=interrupt_on_second_game
        ):
            self.assertEqual(
                main(["--input-dir", str(input_dir), "--output", str(output)]), 130
            )
        return output.with_name(output.name + ".checkpoint")

    def test_resume_requires_existing_checkpoint(self):
        """再開指定には既存checkpointが必要で、分析出力を作らない。"""
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "empty-input"
            input_dir.mkdir()
            output = Path(directory) / "analysis.json"
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                status = main(
                    [
                        "--input-dir",
                        str(input_dir),
                        "--output",
                        str(output),
                        "--resume",
                    ]
                )

            self.assertEqual(status, 2)
            self.assertIn("再開用チェックポイントが見つかりません", stderr.getvalue())
            self.assertFalse(output.exists())

    def test_new_run_rejects_existing_checkpoint(self):
        """通常起動は既存checkpointを無視せず進捗を保護する。"""
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "analysis.json"
            checkpoint = output.with_name(output.name + ".checkpoint")
            checkpoint.mkdir()
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 2)
            self.assertIn("既存の再開用チェックポイント", stderr.getvalue())
            self.assertTrue(checkpoint.is_dir())
            self.assertFalse(output.exists())

    def test_interruption_keeps_only_fully_validated_game_checkpoint(self):
        """中断時は合法再生済みの局だけを再開checkpointへ保存する。

        未検証または途中の二局目を完了扱いする、あるいは確定した一局目まで失う誤りを
        検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "analysis.json"
            checkpoint = output.with_name(output.name + ".checkpoint")
            game_checkpoint_dir = checkpoint / "games"
            original_load_game = comparison_result_io._load_game
            loaded_game_ids = []
            stderr = io.StringIO()

            def interrupt_on_second_game(payload, scheduled_game, config, **kwargs):
                loaded_game_ids.append(scheduled_game.game_id)
                if scheduled_game.game_id == "game-000002":
                    raise KeyboardInterrupt
                return original_load_game(payload, scheduled_game, config, **kwargs)

            with (
                patch.object(
                    comparison_result_io,
                    "_load_game",
                    side_effect=interrupt_on_second_game,
                ),
                redirect_stderr(stderr),
            ):
                status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 130)
            self.assertIn("完了済み1局", stderr.getvalue())
            self.assertIn("--resume", stderr.getvalue())
            self.assertEqual(loaded_game_ids, ["game-000001", "game-000002"])
            self.assertFalse(output.exists())
            self.assertTrue((checkpoint / "manifest.json").is_file())
            first_checkpoint = game_checkpoint_dir / "game-000001.json"
            second_checkpoint = game_checkpoint_dir / "game-000002.json"
            self.assertTrue(first_checkpoint.is_file())
            self.assertFalse(second_checkpoint.exists())
            stored = json.loads(first_checkpoint.read_bytes())
            self.assertEqual(stored["game_id"], "game-000001")
            self.assertEqual(
                stored["record"]["input_sha256"],
                hashlib.sha256(
                    (input_dir / "game-000001.json").read_bytes()
                ).hexdigest(),
            )
            unsigned = {key: value for key, value in stored.items() if key != "sha256"}
            canonical = json.dumps(
                unsigned,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            self.assertEqual(stored["sha256"], hashlib.sha256(canonical).hexdigest())

    def test_resume_reuses_completed_game_and_matches_fresh_analysis(self):
        """再開では検証済み一局を再生せず、全分析値を初回実行と一致させる。

        checkpoint局のhashを照合せず再利用する誤り、完了局を再生する誤り、または再構成した
        得点・区間・集計が通常の全局読込と異なる誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            resumed_output = Path(directory) / "resumed.json"
            fresh_output = Path(directory) / "fresh.json"
            checkpoint = self._interrupt_after_first_game(input_dir, resumed_output)

            with patch.object(
                comparison_result_io,
                "_load_game",
                wraps=comparison_result_io._load_game,
            ) as load_game:
                resumed_status = main(
                    [
                        "--input-dir",
                        str(input_dir),
                        "--output",
                        str(resumed_output),
                        "--resume",
                    ]
                )

            self.assertEqual(resumed_status, 0)
            self.assertEqual(
                [call.args[1].game_id for call in load_game.call_args_list],
                ["game-000002"],
            )
            self.assertFalse(checkpoint.exists())
            self.assertEqual(
                main(["--input-dir", str(input_dir), "--output", str(fresh_output)]),
                0,
            )
            resumed = json.loads(resumed_output.read_bytes())
            fresh = json.loads(fresh_output.read_bytes())
            self.assertEqual(resumed["inputs"], fresh["inputs"])
            resumed.pop("analyzer")
            fresh.pop("analyzer")
            self.assertEqual(resumed, fresh)

    def test_resume_rejects_changed_completed_game_hash(self):
        """完了済み局の入力bytesが変われば同じ棋譜内容でも再開しない。"""
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "analysis.json"
            checkpoint = self._interrupt_after_first_game(input_dir, output)
            game_path = input_dir / "game-000001.json"
            game_path.write_bytes(game_path.read_bytes() + b"\n")
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                status = main(
                    [
                        "--input-dir",
                        str(input_dir),
                        "--output",
                        str(output),
                        "--resume",
                    ]
                )

            self.assertEqual(status, 2)
            self.assertIn("SHA-256", stderr.getvalue())
            self.assertFalse(output.exists())
            self.assertTrue(checkpoint.is_dir())

    def test_resume_rejects_changed_conditions_or_summary(self):
        """conditionsまたはsummaryのbytesが変われば既存checkpointと分ける。"""
        for filename in ("conditions.json", "summary.json"):
            with (
                self.subTest(filename=filename),
                tempfile.TemporaryDirectory() as directory,
            ):
                input_dir = Path(directory) / "input"
                input_dir.mkdir()
                _write_handwritten_experiment(input_dir)
                output = Path(directory) / "analysis.json"
                checkpoint = self._interrupt_after_first_game(input_dir, output)
                input_path = input_dir / filename
                input_path.write_bytes(input_path.read_bytes() + b"\n")
                stderr = io.StringIO()

                with redirect_stderr(stderr):
                    status = main(
                        [
                            "--input-dir",
                            str(input_dir),
                            "--output",
                            str(output),
                            "--resume",
                        ]
                    )

                self.assertEqual(status, 2)
                self.assertIn("manifest", stderr.getvalue())
                self.assertFalse(output.exists())
                self.assertTrue(checkpoint.is_dir())

    def test_resume_rejects_corrupt_game_checkpoint(self):
        """checksumが壊れた完了局checkpointを再利用しない。"""
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "analysis.json"
            checkpoint = self._interrupt_after_first_game(input_dir, output)
            game_checkpoint = checkpoint / "games" / "game-000001.json"
            stored = json.loads(game_checkpoint.read_bytes())
            stored["record"]["summary"]["plies"] = 999
            game_checkpoint.write_text(json.dumps(stored), encoding="utf-8")
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                status = main(
                    [
                        "--input-dir",
                        str(input_dir),
                        "--output",
                        str(output),
                        "--resume",
                    ]
                )

            self.assertEqual(status, 2)
            self.assertIn("checksum", stderr.getvalue())
            self.assertFalse(output.exists())
            self.assertTrue(checkpoint.is_dir())

    def test_interrupted_final_save_can_resume_without_replay(self):
        """最終JSON保存の割込み後、完了局を再生せず保存だけを再試行する。

        最終保存割込みで有効なcheckpointを失う、再試行時に完了局を再生する、または保存前の
        部分JSONを完成結果として残す誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "analysis.json"
            fresh_output = Path(directory) / "fresh.json"
            checkpoint = output.with_name(output.name + ".checkpoint")
            stderr = io.StringIO()

            with (
                patch.object(
                    comparison_result_io,
                    "write_new_json",
                    side_effect=KeyboardInterrupt,
                ),
                redirect_stderr(stderr),
            ):
                interrupted_status = main(
                    ["--input-dir", str(input_dir), "--output", str(output)]
                )

            self.assertEqual(interrupted_status, 130)
            self.assertIn("完了済み2局", stderr.getvalue())
            self.assertFalse(output.exists())
            self.assertEqual(len(tuple((checkpoint / "games").glob("*.json"))), 2)

            with patch.object(
                comparison_result_io,
                "_load_game",
                wraps=comparison_result_io._load_game,
            ) as load_game:
                resumed_status = main(
                    [
                        "--input-dir",
                        str(input_dir),
                        "--output",
                        str(output),
                        "--resume",
                    ]
                )

            self.assertEqual(resumed_status, 0)
            load_game.assert_not_called()
            self.assertFalse(checkpoint.exists())
            self.assertEqual(
                main(["--input-dir", str(input_dir), "--output", str(fresh_output)]),
                0,
            )
            resumed = json.loads(output.read_bytes())
            fresh = json.loads(fresh_output.read_bytes())
            self.assertEqual(resumed["inputs"], fresh["inputs"])
            resumed.pop("analyzer")
            fresh.pop("analyzer")
            self.assertEqual(resumed, fresh)

    def test_source_change_during_analysis_prevents_final_output(self):
        """開始時からfinalize時までのソース指紋が変われば保存を拒否する。"""
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "analysis.json"
            checkpoint = output.with_name(output.name + ".checkpoint")
            stderr = io.StringIO()
            fingerprints = []

            def change_fingerprint(_path):
                fingerprints.append(None)
                return "a" * 64 if len(fingerprints) <= 3 else "b" * 64

            with (
                patch.object(
                    comparison_result_io.comparison_io,
                    "_source_sha256",
                    side_effect=change_fingerprint,
                ),
                redirect_stderr(stderr),
            ):
                status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 2)
            self.assertIn("ソース", stderr.getvalue())
            self.assertFalse(output.exists())
            self.assertEqual(len(fingerprints), 4)
            self.assertEqual(len(tuple((checkpoint / "games").glob("*.json"))), 2)

    def test_summary_mismatch_prevents_final_output_after_all_games(self):
        """全局をcheckpointしても、元summaryとの再集計不一致なら完成扱いしない。"""
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            summary_path = input_dir / "summary.json"
            summary = json.loads(summary_path.read_bytes())
            summary["started_games"] = 3
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            output = Path(directory) / "analysis.json"
            checkpoint = output.with_name(output.name + ".checkpoint")
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 2)
            self.assertIn("summary", stderr.getvalue())
            self.assertFalse(output.exists())
            self.assertEqual(len(tuple((checkpoint / "games").glob("*.json"))), 2)

    def test_checkpoint_cleanup_failure_keeps_successful_output(self):
        """最終JSON後のcheckpoint削除失敗を成功結果の喪失にしない。"""
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "analysis.json"
            checkpoint = output.with_name(output.name + ".checkpoint")
            stderr = io.StringIO()

            with (
                patch.object(
                    comparison_result_io.AnalysisCheckpointStore,
                    "remove",
                    side_effect=OSError("injected cleanup failure"),
                ),
                redirect_stderr(stderr),
            ):
                status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 0)
            self.assertTrue(output.is_file())
            self.assertTrue(checkpoint.is_dir())
            self.assertIn("checkpointを削除できません", stderr.getvalue())

    def test_interruption_during_checkpoint_cleanup_keeps_successful_output(self):
        """最終JSON保存後の削除中断を、再開不能な失敗として案内しない。"""
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "analysis.json"
            stderr = io.StringIO()

            with (
                patch.object(
                    comparison_result_io.AnalysisCheckpointStore,
                    "remove",
                    side_effect=KeyboardInterrupt,
                ),
                redirect_stderr(stderr),
            ):
                status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 0)
            self.assertTrue(output.is_file())
            self.assertIn("分析結果は保存済み", stderr.getvalue())
            self.assertNotIn("--resume", stderr.getvalue())

    def test_checkpoint_write_failure_returns_one_and_keeps_completed_games(self):
        """checkpoint保存故障は1を返し、完成済み局だけを残す。"""
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "analysis.json"
            checkpoint = output.with_name(output.name + ".checkpoint")
            original_write = comparison_result_io.comparison_io.atomic_write_json
            stderr = io.StringIO()

            def fail_second_game(path, payload):
                if path.name == "game-000002.json":
                    raise OSError("injected checkpoint write failure")
                return original_write(path, payload)

            with (
                patch.object(
                    comparison_result_io.comparison_io,
                    "atomic_write_json",
                    side_effect=fail_second_game,
                ),
                redirect_stderr(stderr),
            ):
                status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 1)
            self.assertIn("checkpoint", stderr.getvalue().lower())
            self.assertFalse(output.exists())
            self.assertTrue((checkpoint / "manifest.json").is_file())
            self.assertTrue((checkpoint / "games" / "game-000001.json").is_file())
            self.assertFalse((checkpoint / "games" / "game-000002.json").exists())

    def test_success_removes_checkpoint_after_output_write(self):
        """完成分析JSONを書いた後にcheckpointを片付ける。"""
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "analysis.json"
            checkpoint = output.with_name(output.name + ".checkpoint")
            checkpoint_at_write = []
            original_write = comparison_result_io.write_new_json

            def observe_write(path, payload):
                saved_games = tuple((checkpoint / "games").glob("*.json"))
                checkpoint_at_write.append(
                    checkpoint.is_dir()
                    and len(saved_games) == 2
                    and (checkpoint / "manifest.json").is_file()
                )
                return original_write(path, payload)

            with patch.object(
                comparison_result_io, "write_new_json", side_effect=observe_write
            ):
                status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 0)
            self.assertEqual(checkpoint_at_write, [True])
            self.assertTrue(output.is_file())
            self.assertFalse(checkpoint.exists())

    def test_concurrent_analysis_is_rejected(self):
        """同じ出力先の残存lockを拒否し、比較入力を読み込まない。"""
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            output = Path(directory) / "analysis.json"
            lock_path = output.with_name(output.name + ".lock")
            lock_path.write_text("pid=another-process\n", encoding="ascii")
            stderr = io.StringIO()

            with (
                patch.object(
                    comparison_result_io,
                    "_load_game",
                    wraps=comparison_result_io._load_game,
                ) as load_game,
                redirect_stderr(stderr),
            ):
                status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 2)
            self.assertIn("ロック", stderr.getvalue())
            load_game.assert_not_called()
            self.assertTrue(lock_path.is_file())
            self.assertFalse(output.exists())

    def test_analysis_summary_matches_handwritten_v1_v2_v3(self):
        """summary v1・v2・v3を同じ局別件数・計時集計として分析する。

        手書きの二局から独立に定めた成功手数・計時合計・平均・最大値を保ち、形式版に
        よって値を落としたり誤変換したりする誤りを検出する。
        """
        expected_times = {
            "random": {
                "successful_moves": 0,
                "total_ns": 0,
                "average_ns": None,
                "max_ns": None,
            },
            "material": {
                "successful_moves": 2,
                "total_ns": 302,
                "average_ns": 151.0,
                "max_ns": 201,
            },
            "two-ply-material": {
                "successful_moves": 0,
                "total_ns": 0,
                "average_ns": None,
                "max_ns": None,
            },
            "full-width-4": {
                "successful_moves": 0,
                "total_ns": 0,
                "average_ns": None,
                "max_ns": None,
            },
            "alpha-beta-4": {
                "successful_moves": 0,
                "total_ns": 0,
                "average_ns": None,
                "max_ns": None,
            },
            "material-rook-mobility": {
                "successful_moves": 2,
                "total_ns": 304,
                "average_ns": 152.0,
                "max_ns": 202,
            },
        }
        for version in ("v1", "v2", "v3"):
            with (
                self.subTest(summary=version),
                tempfile.TemporaryDirectory() as directory,
            ):
                input_dir = Path(directory) / "input"
                input_dir.mkdir()
                _write_handwritten_experiment(input_dir)
                if version != "v1":
                    _make_parallel_conditions(input_dir)
                    summary_path = input_dir / "summary.json"
                    summary = json.loads(summary_path.read_bytes())
                    summary["format"] = f"kaname-shogi-comparison-summary-{version}"
                    summary["in_flight_games"] = 0
                    if version == "v3":
                        summary["elapsed_lower_bound"] = True
                    summary_path.write_text(
                        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                output = Path(directory) / "analysis.json"
                resumed_output = Path(directory) / "resumed-analysis.json"

                status = main(["--input-dir", str(input_dir), "--output", str(output)])

                self.assertEqual(status, 0)
                payload = json.loads(output.read_bytes())
                self.assertEqual(payload["counts"]["games"], 2)
                self.assertEqual(payload["counts"]["results"]["ply_limit"], 2)
                self.assertEqual(payload["move_time_by_policy"], expected_times)
                self.assertIs(payload["elapsed_lower_bound"], version == "v3")

                checkpoint = self._interrupt_after_first_game(input_dir, resumed_output)
                resumed_status = main(
                    [
                        "--input-dir",
                        str(input_dir),
                        "--output",
                        str(resumed_output),
                        "--resume",
                    ]
                )
                self.assertEqual(resumed_status, 0)
                resumed_payload = json.loads(resumed_output.read_bytes())
                self.assertEqual(resumed_payload["move_time_by_policy"], expected_times)
                self.assertIs(resumed_payload["elapsed_lower_bound"], version == "v3")
                payload.pop("analyzer")
                resumed_payload.pop("analyzer")
                self.assertEqual(resumed_payload, payload)
                self.assertFalse(checkpoint.exists())

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
                    "elapsed_lower_bound",
                },
            )
            self.assertEqual(payload["format"], "kaname-shogi-comparison-analysis-v2")
            self.assertEqual(payload["purpose"], "pilot")
            self.assertEqual(payload["planned_games"], 2)
            self.assertEqual(payload["completed_pairs"], 1)
            self.assertIs(payload["elapsed_lower_bound"], False)
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

    def test_analysis_preserves_resume_elapsed_lower_bound(self):
        """再開summaryの時間下限フラグを分析成果物へ伝播する。

        再開不能時間を含むelapsed_nsを、全所要時間と誤読できる分析JSONにする誤りを
        検出する。旧summaryでは下限ではないと明示する。
        """
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            _write_handwritten_experiment(input_dir)
            summary_path = input_dir / "summary.json"
            summary = json.loads(summary_path.read_bytes())
            summary.update(
                format="kaname-shogi-comparison-summary-v3",
                in_flight_games=0,
                elapsed_lower_bound=True,
            )
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            output = Path(directory) / "analysis.json"

            status = main(["--input-dir", str(input_dir), "--output", str(output)])

            self.assertEqual(status, 0)
            payload = json.loads(output.read_bytes())

        self.assertIs(payload["elapsed_lower_bound"], True)

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
                "prepare_analysis_input",
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
