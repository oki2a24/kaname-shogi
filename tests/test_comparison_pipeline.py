"""比較準備・対局・分析の実プロセス接続を確認する。"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ComparisonPipelineProcessTests(unittest.TestCase):
    def test_saved_512_ply_c1_pilot_remains_analyzable(self):
        """保存済みC1のconditions v2/summary v1を変更せず再分析できる。

        reader拡張で過去の512手pilotを拒否したり、分析出力を実験成果物へ書き込む
        回帰を検出する。
        """
        root = Path(__file__).resolve().parents[1]
        input_dir = root / "data/comparison/runs/c1-rook-mobility-pilot-512-2026-10-24"
        conditions = json.loads((input_dir / "conditions.json").read_bytes())
        summary = json.loads((input_dir / "summary.json").read_bytes())
        saved_artifacts = {path.name: path.read_bytes() for path in input_dir.iterdir()}

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "analysis.json"
            analyzed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "kaname_shogi.analyze_comparison",
                    "--input-dir",
                    str(input_dir),
                    "--output",
                    str(output),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(analyzed.returncode, 0, analyzed.stderr)
            result = json.loads(output.read_bytes())

        self.assertEqual(conditions["format"], "kaname-shogi-comparison-conditions-v2")
        self.assertEqual(summary["format"], "kaname-shogi-comparison-summary-v1")
        self.assertEqual(conditions["max_plies"], 512)
        self.assertEqual(result["planned_games"], 12)
        self.assertEqual(result["completed_pairs"], 6)
        self.assertEqual(result["counts"]["games"], 12)
        self.assertEqual(
            {path.name: path.read_bytes() for path in input_dir.iterdir()},
            saved_artifacts,
        )

    def test_seed_plan_runs_through_compare_and_analyze_reproducibly(self):
        """同じ保存種一覧で予定・棋譜・終局・候補得点を再現する。

        乱数一覧の目的を落とす、実験入力を受け取り違える、または計時値の差を
        棋譜・勝敗の差と混同するパイプライン接続の誤りを検出する。
        """
        root = Path(__file__).resolve().parents[1]
        positions_path = root / "data/comparison/c1-rook-mobility-positions-v1.json"

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            seed_path = temporary / "pilot-seeds.json"
            prepare = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "kaname_shogi.prepare_comparison_seeds",
                    "--positions",
                    str(positions_path),
                    "--pairs-per-position",
                    "1",
                    "--purpose",
                    "pilot",
                    "--output",
                    str(seed_path),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(prepare.returncode, 0, prepare.stderr)
            seed_plan = json.loads(seed_path.read_bytes())
            self.assertEqual(seed_plan["purpose"], "pilot")

            invalid_seed_path = temporary / "invalid-seeds.json"
            invalid_seed_plan = dict(seed_plan)
            invalid_seed_plan["positions_sha256"] = "0" * 64
            invalid_seed_path.write_text(
                json.dumps(invalid_seed_plan), encoding="utf-8"
            )
            rejected_output = temporary / "rejected-output"
            rejected = subprocess.run(
                self._compare_command(
                    sys.executable,
                    positions_path,
                    invalid_seed_path,
                    rejected_output,
                ),
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(rejected.returncode, 2, rejected.stderr)
            self.assertFalse(rejected_output.exists())

            outputs = []
            analyses = []
            for run_number in (1, 2):
                output_dir = temporary / f"run-{run_number}"
                compared = subprocess.run(
                    self._compare_command(
                        sys.executable, positions_path, seed_path, output_dir
                    ),
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(compared.returncode, 0, compared.stderr)
                conditions = json.loads((output_dir / "conditions.json").read_bytes())
                summary = json.loads((output_dir / "summary.json").read_bytes())
                self.assertEqual(conditions["randomization"]["purpose"], "pilot")
                self.assertEqual(
                    conditions["randomization"]["seed_list_sha256"],
                    hashlib.sha256(seed_path.read_bytes()).hexdigest(),
                )
                self.assertEqual(summary["status"], "complete")
                self.assertEqual(summary["planned_games"], 12)

                game_results = [
                    json.loads((output_dir / f"game-{index:06}.json").read_bytes())
                    for index in range(1, 13)
                ]
                outputs.append(
                    {
                        "conditions": conditions,
                        "summary": summary,
                        "games": game_results,
                    }
                )

                analysis_path = temporary / f"analysis-{run_number}.json"
                analyzed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "kaname_shogi.analyze_comparison",
                        "--input-dir",
                        str(output_dir),
                        "--output",
                        str(analysis_path),
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(analyzed.returncode, 0, analyzed.stderr)
                analysis = json.loads(analysis_path.read_bytes())
                self.assertEqual(analysis["purpose"], "pilot")
                self.assertEqual(analysis["planned_games"], 12)
                self.assertEqual(analysis["completed_pairs"], 6)
                self.assertEqual(analysis["counts"]["games"], 12)
                self.assertEqual(analysis["elapsed_ns"], summary["elapsed_ns"])
                analyses.append(analysis)

            self.assertEqual(
                outputs[0]["conditions"]["schedule"],
                outputs[1]["conditions"]["schedule"],
            )
            self.assertEqual(
                [self._stable_game(game) for game in outputs[0]["games"]],
                [self._stable_game(game) for game in outputs[1]["games"]],
            )
            self.assertEqual(
                outputs[0]["summary"]["results"], outputs[1]["summary"]["results"]
            )
            for key in (
                "purpose",
                "baseline",
                "candidate",
                "method",
                "planned_games",
                "completed_pairs",
                "counts",
                "score",
                "by_position",
                "by_side",
            ):
                self.assertEqual(analyses[0][key], analyses[1][key])

    def test_spawn_workers_one_two_four_preserve_seeded_games(self):
        """spawnの1・2・4 workerで局ID・種・結果を再現する。

        worker数で乱数列や予定順が変わる誤り、またはworker数に応じた
        条件・summary形式を誤って出力する不良を検出する。
        """
        root = Path(__file__).resolve().parents[1]
        positions_path = root / "data/comparison/c1-rook-mobility-positions-v1.json"

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            seed_path = temporary / "spawn-seeds.json"
            prepare = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "kaname_shogi.prepare_comparison_seeds",
                    "--positions",
                    str(positions_path),
                    "--pairs-per-position",
                    "1",
                    "--purpose",
                    "pilot",
                    "--output",
                    str(seed_path),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(prepare.returncode, 0, prepare.stderr)

            runs = {}
            for workers in (1, 2, 4):
                output_dir = temporary / f"spawn-workers-{workers}"
                command = self._compare_command(
                    sys.executable,
                    positions_path,
                    seed_path,
                    output_dir,
                    workers=workers,
                )
                compared = subprocess.run(
                    command,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(compared.returncode, 0, compared.stderr)

                conditions = json.loads((output_dir / "conditions.json").read_bytes())
                summary = json.loads((output_dir / "summary.json").read_bytes())
                self.assertEqual(summary["status"], "complete")
                self.assertEqual(summary["ended_games"], 12)
                if workers == 1:
                    self.assertIn(
                        conditions["format"],
                        (
                            "kaname-shogi-comparison-conditions-v1",
                            "kaname-shogi-comparison-conditions-v2",
                        ),
                    )
                    self.assertEqual(
                        summary["format"], "kaname-shogi-comparison-summary-v1"
                    )
                else:
                    self.assertEqual(
                        conditions["format"],
                        "kaname-shogi-comparison-conditions-v3",
                    )
                    self.assertEqual(conditions["execution"]["workers"], workers)
                    self.assertEqual(
                        summary["format"], "kaname-shogi-comparison-summary-v2"
                    )
                    self.assertEqual(summary["in_flight_games"], 0)

                games = [
                    json.loads((output_dir / f"game-{index:06}.json").read_bytes())
                    for index in range(1, 13)
                ]
                analysis_path = temporary / f"spawn-analysis-{workers}.json"
                analyzed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "kaname_shogi.analyze_comparison",
                        "--input-dir",
                        str(output_dir),
                        "--output",
                        str(analysis_path),
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(analyzed.returncode, 0, analyzed.stderr)
                runs[workers] = {
                    "conditions": conditions,
                    "summary": summary,
                    "games": games,
                    "analysis": json.loads(analysis_path.read_bytes()),
                }

            reference = runs[1]
            for workers in (2, 4):
                current = runs[workers]
                self.assertEqual(
                    current["conditions"]["schedule"],
                    reference["conditions"]["schedule"],
                )
                self.assertEqual(
                    [self._stable_game(game) for game in current["games"]],
                    [self._stable_game(game) for game in reference["games"]],
                )
                self.assertEqual(
                    current["summary"]["results"], reference["summary"]["results"]
                )
                self.assertEqual(
                    current["analysis"]["score"], reference["analysis"]["score"]
                )
                self.assertEqual(
                    current["analysis"]["counts"], reference["analysis"]["counts"]
                )

    @staticmethod
    def _compare_command(
        python: str,
        positions_path: Path,
        seed_path: Path,
        output_dir: Path,
        *,
        workers: int = 1,
    ) -> list[str]:
        """比較CLIへ一貫した小実験条件を渡す引数列を返す。"""
        return [
            python,
            "-m",
            "kaname_shogi.compare_games",
            "--baseline",
            "material",
            "--candidate",
            "material-rook-mobility",
            "--positions",
            str(positions_path),
            "--pairs-per-position",
            "1",
            "--seed-list",
            str(seed_path),
            "--max-plies",
            "2",
            "--workers",
            str(workers),
            "--output-dir",
            str(output_dir),
        ]

    @staticmethod
    def _stable_game(game: dict[str, object]) -> dict[str, object]:
        """時間計測だけを除いた、再実行で一致させる局結果部分を返す。"""
        return {
            key: game[key]
            for key in (
                "game_id",
                "position_id",
                "pair_number",
                "game_number_in_pair",
                "baseline",
                "candidate",
                "baseline_seed",
                "candidate_seed",
                "baseline_side",
                "candidate_side",
                "start_sfen",
                "initial_move_number",
                "plies",
                "reason",
                "winner_side",
                "winner_policy",
                "record",
            )
        }
