"""比較CLIがV方式とworker条件を保存する契約を確認する。"""

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kaname_shogi.comparison import make_schedule
from kaname_shogi.comparison_io import conditions_payload, load_config
from kaname_shogi.movegen import MoveSelectionPolicy


class PieceThreatComparisonIOTests(unittest.TestCase):
    @staticmethod
    def _config(
        root: Path,
        *,
        baseline: str,
        candidate: str,
        pairs: int = 1,
        workers: int = 4,
        resume: bool = False,
    ):
        """独立seed一覧と一局面で比較CLIの条件を作る。"""
        positions_path = root / "positions.json"
        positions_raw = json.dumps(
            {
                "format": "kaname-shogi-comparison-positions-v1",
                "id": "supported-threat-policy-test",
                "positions": [
                    {"id": "initial", "setup_moves": [], "rationale": "テスト局面"}
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        positions_path.write_bytes(positions_raw)

        seed_path = root / "seeds.json"
        seed_path.write_text(
            json.dumps(
                {
                    "format": "kaname-shogi-comparison-seeds-v1",
                    "purpose": "pilot",
                    "positions_sha256": hashlib.sha256(positions_raw).hexdigest(),
                    "position_ids": ["initial"],
                    "pairs_per_position": pairs,
                    "source": "os",
                    "bits": 128,
                    "pairs": [
                        {
                            "position_id": "initial",
                            "repetition_index": index,
                            "baseline_seed": 11 + 2 * index,
                            "candidate_seed": 12 + 2 * index,
                        }
                        for index in range(pairs)
                    ],
                }
            ),
            encoding="utf-8",
        )
        output_dir = root / "results"
        if resume:
            output_dir.mkdir()
        args = [
            "--baseline",
            baseline,
            "--candidate",
            candidate,
            "--positions",
            str(positions_path),
            "--pairs-per-position",
            str(pairs),
            "--seed-list",
            str(seed_path),
            "--max-plies",
            "1",
            "--workers",
            str(workers),
            "--output-dir",
            str(output_dir),
        ]
        if resume:
            args.append("--resume")
        try:
            config = load_config(args)
        except ValueError as error:
            raise AssertionError(f"比較CLIが方式を受理できません: {error}") from error
        return config, seed_path

    def test_cli_maps_v_zero_and_v_one_to_distinct_policies(self):
        """V0/V1の安定識別子を別々の比較policyへ対応づける。

        parserへの登録漏れや、対照・候補のV重みを逆にする誤りを検出する。
        """
        with TemporaryDirectory() as directory:
            config, _ = self._config(
                Path(directory),
                baseline="material-piece-threat-v0",
                candidate="material-piece-threat-v1",
            )
        self.assertIs(config.baseline, MoveSelectionPolicy.MATERIAL_PIECE_THREAT_V0)
        self.assertIs(config.candidate, MoveSelectionPolicy.MATERIAL_PIECE_THREAT_V1)

    def test_seed_list_conditions_store_exact_v_weights_and_workers(self):
        """worker 4のseed-list conditionsへ方式・重み・seed hashを保存する。

        V0/V1の係数、seedスナップショット、並列実行条件の欠落や取り違えを検出する。
        """
        with TemporaryDirectory() as directory:
            config, seed_path = self._config(
                Path(directory),
                baseline="material-piece-threat-v0",
                candidate="material-piece-threat-v1",
            )
            payload = conditions_payload(
                config,
                make_schedule(config),
                source_root=Path(__file__).parents[1],
            )
            expected_seed_sha256 = hashlib.sha256(seed_path.read_bytes()).hexdigest()
            expected_seed_json = seed_path.read_text(encoding="utf-8")

        self.assertEqual(payload["format"], "kaname-shogi-comparison-conditions-v3")
        self.assertEqual(
            (payload["baseline"], payload["candidate"]),
            ("material-piece-threat-v0", "material-piece-threat-v1"),
        )
        self.assertEqual(
            payload["policy_parameters"],
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
            payload["execution"], {"executor": "process-pool", "workers": 4}
        )
        self.assertEqual(
            payload["randomization"]["seed_list_sha256"],
            expected_seed_sha256,
        )
        self.assertEqual(
            payload["randomization"]["seed_list_json"],
            expected_seed_json,
        )


if __name__ == "__main__":
    unittest.main()
