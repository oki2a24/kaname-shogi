"""C2の種準備・比較・分析を小さい実プロセスで確認する。"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class KingSafetyComparisonPipelineTests(unittest.TestCase):
    def test_c2_seed_compare_and_analyze_reproduce_results(self):
        """同じ種一覧でC2四局面を比較・分析し、棋譜と条件を再現する。

        方式名や重みの接続漏れ、先後交換の予定欠落、保存結果の再読込失敗を
        検出する。手数上限1の短い接続確認であり、強さの比較ではない。
        """
        root = Path(__file__).resolve().parents[1]
        positions = root / "data/comparison/c2-king-safety-positions-v1.json"
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
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            self.assertEqual(json.loads(seeds.read_bytes())["purpose"], "pilot")
            fingerprints = []
            schedules = []
            for index in (1, 2):
                output = temporary / f"run-{index}"
                compared = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "kaname_shogi.compare_games",
                        "--baseline",
                        "material-king-safety-material-only",
                        "--candidate",
                        "material-king-safety",
                        "--positions",
                        str(positions),
                        "--pairs-per-position",
                        "1",
                        "--seed-list",
                        str(seeds),
                        "--max-plies",
                        "1",
                        "--output-dir",
                        str(output),
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                self.assertEqual(compared.returncode, 0, compared.stderr)
                conditions = json.loads((output / "conditions.json").read_bytes())
                self.assertEqual(
                    conditions["policy_parameters"],
                    {
                        "baseline": {
                            "material": 10,
                            "safety": 0,
                            "mate_priority": True,
                        },
                        "candidate": {
                            "material": 10,
                            "safety": 1,
                            "mate_priority": True,
                        },
                    },
                )
                self.assertEqual(
                    conditions["randomization"]["seed_list_sha256"],
                    hashlib.sha256(seeds.read_bytes()).hexdigest(),
                )
                schedules.append(conditions["schedule"])
                games = sorted(output.glob("game-*.json"))
                self.assertEqual(len(games), 8)
                fingerprints.append(
                    [
                        {
                            key: game[key]
                            for key in (
                                "record",
                                "reason",
                                "winner_side",
                                "winner_policy",
                                "plies",
                            )
                        }
                        for game in (json.loads(path.read_bytes()) for path in games)
                    ]
                )
                analysis_path = temporary / f"analysis-{index}.json"
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
                self.assertEqual(analyzed.returncode, 0, analyzed.stderr)
                analysis = json.loads(analysis_path.read_bytes())
                self.assertEqual(analysis["purpose"], "pilot")
                self.assertEqual(analysis["planned_games"], 8)
                self.assertEqual(analysis["completed_pairs"], 4)
                self.assertEqual(analysis["counts"]["games"], 8)
            self.assertEqual(schedules[0], schedules[1])
            self.assertEqual(fingerprints[0], fingerprints[1])
