"""比較CLIが価値合計方式の識別子と条件重みを保存する契約を確認する。"""

import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kaname_shogi.comparison import (
    BatchStatus,
    make_schedule,
    summarize,
)
from kaname_shogi.comparison_io import conditions_payload
from kaname_shogi.movegen import MoveSelectionPolicy
from tests import test_piece_threat_comparison_io as input_fixtures


class PieceThreatValueComparisonIOTests(unittest.TestCase):
    def test_cli_maps_old_u_and_value_policies_to_distinct_modes(self):
        """CLIが旧U方式と価値合計方式を別policyとして受け付ける。

        方式識別子の未登録・逆転や新方式を旧U評価器へ結び付ける誤りを検出する。
        """
        with TemporaryDirectory() as directory:
            config, _ = input_fixtures.PieceThreatComparisonIOTests._config(
                Path(directory),
                baseline="material-piece-threat-v1",
                candidate="material-piece-threat-value-v1",
                workers=4,
            )

        self.assertIs(config.baseline, MoveSelectionPolicy.MATERIAL_PIECE_THREAT_V1)
        self.assertIs(
            config.candidate, MoveSelectionPolicy.MATERIAL_PIECE_THREAT_VALUE_V1
        )
        self.assertEqual(config.workers, 4)

    def test_worker_four_conditions_keep_old_and_value_weight_keys_distinct(self):
        """worker 4条件に旧Uと価値合計の実効重みを別キーで保存する。

        新方式のundefended_value欠落・undefendedへの混同、重みやseed snapshotの誤りを検出する。
        """
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config, seed_path = input_fixtures.PieceThreatComparisonIOTests._config(
                root,
                baseline="material-piece-threat-v1",
                candidate="material-piece-threat-value-v1",
                workers=4,
            )
            payload = conditions_payload(
                config,
                make_schedule(config),
                source_root=Path(__file__).parents[1],
            )
            seed_sha256 = hashlib.sha256(seed_path.read_bytes()).hexdigest()
            seed_json = seed_path.read_text(encoding="utf-8")

        self.assertEqual(payload["format"], "kaname-shogi-comparison-conditions-v3")
        self.assertEqual(
            payload["policy_parameters"],
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
            payload["execution"], {"executor": "process-pool", "workers": 4}
        )
        self.assertEqual(payload["randomization"]["seed_list_sha256"], seed_sha256)
        self.assertEqual(payload["randomization"]["seed_list_json"], seed_json)

    def test_value_policy_summary_timing_is_present_only_when_selected(self):
        """比較条件に選んだ価値合計方式だけをsummary計時へ追加する。

        旧比較summaryへの未選択新方式混入と、選択時の計時欄欠落を検出する。
        """
        with TemporaryDirectory() as directory:
            root = Path(directory)
            selected, _ = input_fixtures.PieceThreatComparisonIOTests._config(
                root,
                baseline="material-piece-threat-v1",
                candidate="material-piece-threat-value-v1",
                workers=4,
            )
            unselected, _ = input_fixtures.PieceThreatComparisonIOTests._config(
                root,
                baseline="material",
                candidate="random",
                workers=4,
            )

        def empty_summary(config):
            return summarize(
                config,
                (),
                batch_status=BatchStatus.INTERRUPTED,
                unstarted_games=2,
                elapsed_ns=0,
            )

        selected_names = tuple(empty_summary(selected)["move_time_by_policy"])
        self.assertEqual(
            selected_names,
            (
                "random",
                "material",
                "two-ply-material",
                "full-width-4",
                "alpha-beta-4",
                "material-piece-threat-v1",
                "material-piece-threat-value-v1",
            ),
        )
        self.assertNotIn(
            "material-piece-threat-value-v1",
            empty_summary(unselected)["move_time_by_policy"],
        )


if __name__ == "__main__":
    unittest.main()
