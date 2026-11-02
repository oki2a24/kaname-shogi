"""価値比較policyをseed準備・比較・分析CLIへ接続して検査する。"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from undefended_piece_value_comparison_support import POSITION_EXPECTATIONS

_BASELINE = "material-piece-threat-v1"
_CANDIDATE = "material-piece-threat-value-v1"


class UndefendedPieceValueComparisonPipelineTests(unittest.TestCase):
    def test_seed_compare_and_analyze_preserve_old_and_value_policies(self):
        """同じseedで7局面を先後交換比較し、条件・局棋譜・分析を保つ。

        新policyの方式名・重み・計時がCLIの途中で失われる、組の先後交換が欠ける、
        再実行で局面予定や棋譜が変わる誤りを検出する。1手上限で強さは判定しない。
        """
        root = Path(__file__).resolve().parents[1]
        positions = root / "data/comparison/undefended-piece-value-positions-v1.json"
        self.assertTrue(
            positions.is_file(), "被攻撃駒価値比較の新規7局面JSONが未作成です"
        )

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
            expected_position_ids = tuple(POSITION_EXPECTATIONS)
            self.assertEqual(seed_payload["purpose"], "pilot")
            self.assertEqual(len(seed_payload["pairs"]), len(expected_position_ids))
            self.assertEqual(
                tuple(pair["position_id"] for pair in seed_payload["pairs"]),
                expected_position_ids,
            )

            schedules = []
            fingerprints = []
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
                    timeout=120,
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
                            "undefended": 1,
                            "supported_threat": 1,
                            "mate_priority": True,
                        },
                        "candidate": {
                            "material": 10,
                            "undefended_value": 1,
                            "supported_threat": 1,
                            "mate_priority": True,
                        },
                    },
                )
                self.assertEqual(
                    conditions["randomization"]["seed_list_sha256"],
                    hashlib.sha256(seeds.read_bytes()).hexdigest(),
                )
                self.assertEqual(len(conditions["positions"]), 7)
                self.assertEqual(
                    tuple(position["id"] for position in conditions["positions"]),
                    expected_position_ids,
                )
                self.assertEqual(len(conditions["schedule"]), 14)
                schedules.append(conditions["schedule"])
                for pair_number in range(7):
                    pair = conditions["schedule"][2 * pair_number : 2 * pair_number + 2]
                    self.assertEqual(
                        {game["candidate_side"] for game in pair}, {"sente", "gote"}
                    )
                    self.assertEqual(
                        {game["position_id"] for game in pair},
                        {expected_position_ids[pair_number]},
                    )

                game_paths = sorted(output.glob("game-*.json"))
                self.assertEqual(len(game_paths), 14)
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
                fingerprints.append(
                    [
                        {
                            "game_id": game["game_id"],
                            "position_id": game["position_id"],
                            "baseline_side": game["baseline_side"],
                            "candidate_side": game["candidate_side"],
                            "record": game["record"],
                            "reason": game["reason"],
                            "winner_side": game["winner_side"],
                            "winner_policy": game["winner_policy"],
                            "plies": game["plies"],
                        }
                        for game in games
                    ]
                )

                summary = json.loads((output / "summary.json").read_bytes())
                for policy in (_BASELINE, _CANDIDATE):
                    self.assertIn(policy, summary["move_time_by_policy"])
                    self.assertEqual(
                        summary["move_time_by_policy"][policy]["successful_moves"], 7
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
                self.assertEqual(analysis["planned_games"], 14)
                self.assertEqual(analysis["completed_pairs"], 7)
                self.assertEqual(analysis["counts"]["games"], 14)
                self.assertEqual(
                    analysis["by_side"]["candidate_sente"]["ply_limits"], 7
                )
                self.assertEqual(analysis["by_side"]["candidate_gote"]["ply_limits"], 7)
                for policy in (_BASELINE, _CANDIDATE):
                    self.assertIn(policy, analysis["move_time_by_policy"])
                    self.assertEqual(
                        analysis["move_time_by_policy"][policy]["successful_moves"], 7
                    )

            self.assertEqual(schedules[0], schedules[1])
            self.assertEqual(fingerprints[0], fingerprints[1])
