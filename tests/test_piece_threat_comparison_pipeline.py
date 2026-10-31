"""V比較を種準備・並列対局・分析CLIまで短く接続する。"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kaname_shogi.comparison_result_io import load_completed_comparison

_BASELINE = "material-piece-threat-v0"
_CANDIDATE = "material-piece-threat-v1"


class PieceThreatComparisonPipelineTests(unittest.TestCase):
    def test_seed_compare_and_analyze_keep_v_policies(self):
        """固定seed・worker4・1手上限の二回実行を条件から分析まで照合する。

        Vの方式名と重みの脱落、先後交換の欠落、未決着の得点範囲の決め打ち、
        同seedの棋譜非決定性を検出する。これは接続確認で強さを判定しない。
        """
        root = Path(__file__).resolve().parents[1]
        positions = (
            root
            / "data/comparison/supported-piece-threat-confirmation-positions-v1.json"
        )
        self.assertTrue(positions.is_file(), "確認比較用6局面JSONが未作成です")

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            seeds = temporary / "confirmation-seeds.json"
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
                    "confirmation",
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
            self.assertEqual(seed_payload["purpose"], "confirmation")
            self.assertEqual(len(seed_payload["pairs"]), 6)

            stable_runs = []
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
                conditions_raw = (output / "conditions.json").read_bytes()
                conditions = json.loads(conditions_raw)
                self.assertEqual(
                    conditions["format"], "kaname-shogi-comparison-conditions-v3"
                )
                self.assertEqual(
                    conditions["execution"], {"executor": "process-pool", "workers": 4}
                )
                self.assertEqual(
                    (conditions["baseline"], conditions["candidate"]),
                    (_BASELINE, _CANDIDATE),
                )
                self.assertEqual(
                    conditions["policy_parameters"],
                    {
                        "baseline": {
                            "material": 10,
                            "undefended": 1,
                            "supported_threat": 0,
                            "mate_priority": True,
                        },
                        "candidate": {
                            "material": 10,
                            "undefended": 1,
                            "supported_threat": 1,
                            "mate_priority": True,
                        },
                    },
                )
                self.assertEqual(
                    conditions["randomization"]["seed_list_sha256"],
                    hashlib.sha256(seeds.read_bytes()).hexdigest(),
                )
                self.assertEqual(len(conditions["positions"]), 6)
                self.assertEqual(len(conditions["schedule"]), 12)
                for pair_number in range(6):
                    pair = conditions["schedule"][2 * pair_number : 2 * pair_number + 2]
                    self.assertEqual(
                        {game["candidate_side"] for game in pair}, {"sente", "gote"}
                    )

                games = [
                    json.loads(path.read_bytes())
                    for path in sorted(output.glob("game-*.json"))
                ]
                self.assertEqual(len(games), 12)
                self.assertTrue(
                    all(
                        game["conditions_sha256"]
                        == hashlib.sha256(conditions_raw).hexdigest()
                        and game["baseline"] == _BASELINE
                        and game["candidate"] == _CANDIDATE
                        and game["plies"] == 1
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
                summary = json.loads((output / "summary.json").read_bytes())
                self.assertEqual(summary["status"], "complete")
                self.assertEqual(summary["ended_games"], 12)
                self.assertEqual(summary["completed_pairs"], 6)
                for policy in (_BASELINE, _CANDIDATE):
                    self.assertEqual(
                        summary["move_time_by_policy"][policy]["successful_moves"], 6
                    )

                loaded = load_completed_comparison(output)
                self.assertEqual(
                    tuple((pair.lower, pair.upper) for pair in loaded.pair_scores),
                    ((0, 1),) * 6,
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
                self.assertEqual(analysis["purpose"], "confirmation")
                self.assertEqual(
                    (analysis["baseline"], analysis["candidate"]),
                    (_BASELINE, _CANDIDATE),
                )
                self.assertEqual(
                    (analysis["planned_games"], analysis["completed_pairs"]), (12, 6)
                )
                self.assertEqual(analysis["counts"]["games"], 12)
                self.assertEqual(
                    (analysis["score"]["lower_mean"], analysis["score"]["upper_mean"]),
                    (0.0, 1.0),
                )
                self.assertEqual(
                    analysis["by_side"]["candidate_sente"]["ply_limits"], 6
                )
                self.assertEqual(analysis["by_side"]["candidate_gote"]["ply_limits"], 6)
                stable_runs.append(
                    (
                        conditions["schedule"],
                        [
                            (
                                game["game_id"],
                                game["record"],
                                game["reason"],
                                game["winner_side"],
                            )
                            for game in games
                        ],
                        analysis["score"],
                    )
                )

            self.assertEqual(stable_runs[0], stable_runs[1])


if __name__ == "__main__":
    unittest.main()
