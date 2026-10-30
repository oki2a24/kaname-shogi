"""連携評価policyを5局面の種準備・比較・分析CLIまで接続する。"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_BASELINE = "material-undefended-piece-material-only"
_CANDIDATE = "material-undefended-piece"


class UndefendedPieceComparisonPipelineTests(unittest.TestCase):
    def test_seed_compare_and_analyze_keep_undefended_policies(self):
        """同じseed一覧で5局面を比較・分析し、条件・棋譜・集計を保つ。

        新方式名や重みがCLI途中で失われる、先後交換が欠ける、方式別計時がsummaryや
        analysisへ伝わらない誤りを検出する。手数上限1の接続確認で強さを判定しない。
        """
        root = Path(__file__).resolve().parents[1]
        positions = root / "data/comparison/undefended-piece-positions-v1.json"
        self.assertTrue(positions.is_file(), "連携評価比較の5局面JSONが未作成です")

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            seeds = temporary / "seeds.json"
            prepared = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "kaname_shogi.prepare_comparison_seeds",
                    "--positions",
                    str(positions),
                    "--pairs-per-position",
                    "1",
                    "--purpose",
                    "pilot",
                    "--output",
                    str(seeds),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(
                prepared.returncode,
                0,
                f"stdout={prepared.stdout}; stderr={prepared.stderr}",
            )
            seed_payload = json.loads(seeds.read_bytes())
            self.assertEqual(seed_payload["purpose"], "pilot")
            self.assertEqual(len(seed_payload["pairs"]), 5)

            run_fingerprints = []
            run_schedules = []
            for run_number in (1, 2):
                output = temporary / f"run-{run_number}"
                compared = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "kaname_shogi.compare_games",
                        "--baseline",
                        _BASELINE,
                        "--candidate",
                        _CANDIDATE,
                        "--positions",
                        str(positions),
                        "--pairs-per-position",
                        "1",
                        "--seed-list",
                        str(seeds),
                        "--max-plies",
                        "1",
                        "--workers",
                        "4",
                        "--output-dir",
                        str(output),
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                self.assertEqual(
                    compared.returncode,
                    0,
                    f"stdout={compared.stdout}; stderr={compared.stderr}",
                )
                conditions = json.loads((output / "conditions.json").read_bytes())
                self.assertEqual(
                    conditions["format"], "kaname-shogi-comparison-conditions-v3"
                )
                self.assertEqual(conditions["execution"]["workers"], 4)
                self.assertEqual(
                    (conditions["baseline"], conditions["candidate"]),
                    (_BASELINE, _CANDIDATE),
                )
                self.assertEqual(
                    conditions["policy_parameters"],
                    {
                        "baseline": {
                            "material": 10,
                            "undefended": 0,
                            "mate_priority": True,
                        },
                        "candidate": {
                            "material": 10,
                            "undefended": 1,
                            "mate_priority": True,
                        },
                    },
                )
                self.assertEqual(
                    conditions["randomization"]["seed_list_sha256"],
                    hashlib.sha256(seeds.read_bytes()).hexdigest(),
                )
                self.assertEqual(len(conditions["positions"]), 5)
                self.assertEqual(len(conditions["schedule"]), 10)
                run_schedules.append(conditions["schedule"])
                for pair_number in range(5):
                    pair = conditions["schedule"][2 * pair_number : 2 * pair_number + 2]
                    self.assertEqual(
                        {game["candidate_side"] for game in pair}, {"sente", "gote"}
                    )

                game_paths = sorted(output.glob("game-*.json"))
                self.assertEqual(len(game_paths), 10)
                games = [json.loads(path.read_bytes()) for path in game_paths]
                self.assertTrue(
                    all(
                        game["baseline"] == _BASELINE
                        and game["candidate"] == _CANDIDATE
                        for game in games
                    )
                )
                self.assertEqual(
                    {
                        timing["policy"]
                        for game in games
                        for timing in game["move_times"]
                    },
                    {_BASELINE, _CANDIDATE},
                )
                run_fingerprints.append(
                    [
                        {
                            "game_id": game["game_id"],
                            "baseline_side": game["baseline_side"],
                            "candidate_side": game["candidate_side"],
                            "record": game["record"],
                            "reason": game["reason"],
                            "winner_side": game["winner_side"],
                            "winner_policy": game["winner_policy"],
                            "plies": game["plies"],
                            "move_times": [
                                {
                                    key: timing[key]
                                    for key in ("ply", "side", "policy", "move")
                                }
                                for timing in game["move_times"]
                            ],
                        }
                        for game in games
                    ]
                )

                summary = json.loads((output / "summary.json").read_bytes())
                for policy in (_BASELINE, _CANDIDATE):
                    self.assertIn(policy, summary["move_time_by_policy"])
                    self.assertEqual(
                        summary["move_time_by_policy"][policy]["successful_moves"], 5
                    )

                analysis_path = temporary / f"analysis-{run_number}.json"
                analyzed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "kaname_shogi.analyze_comparison",
                        "--input-dir",
                        str(output),
                        "--output",
                        str(analysis_path),
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                self.assertEqual(
                    analyzed.returncode,
                    0,
                    f"stdout={analyzed.stdout}; stderr={analyzed.stderr}",
                )
                analysis = json.loads(analysis_path.read_bytes())
                self.assertEqual(
                    (analysis["baseline"], analysis["candidate"]),
                    (_BASELINE, _CANDIDATE),
                )
                self.assertEqual(analysis["planned_games"], 10)
                self.assertEqual(analysis["completed_pairs"], 5)
                self.assertEqual(analysis["counts"]["games"], 10)
                self.assertEqual(
                    analysis["by_side"]["candidate_sente"]["ply_limits"], 5
                )
                self.assertEqual(analysis["by_side"]["candidate_gote"]["ply_limits"], 5)
                for policy in (_BASELINE, _CANDIDATE):
                    self.assertIn(policy, analysis["move_time_by_policy"])
                    self.assertEqual(
                        analysis["move_time_by_policy"][policy]["successful_moves"], 5
                    )

            self.assertEqual(run_schedules[0], run_schedules[1])
            self.assertEqual(run_fingerprints[0], run_fingerprints[1])


if __name__ == "__main__":
    unittest.main()
