"""価値合計比較conditions・summaryのreader互換を確認する。"""

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kaname_shogi import comparison_io, comparison_result_io
from kaname_shogi.movegen import MoveSelectionPolicy
from tests import test_comparison_result_io as result_fixtures
from tests import test_piece_threat_comparison_io as input_fixtures

_OLD = "material-piece-threat-v1"
_VALUE = "material-piece-threat-value-v1"
_OLD_PARAMETERS = {
    "material": 10,
    "undefended": 1,
    "supported_threat": 1,
    "mate_priority": True,
}
_VALUE_PARAMETERS = {
    "material": 10,
    "undefended_value": 1,
    "supported_threat": 1,
    "mate_priority": True,
}


def _write_handwritten_value_experiment(directory: Path) -> Path:
    """手書き二局artifactを旧U・価値合計policyとして保存する。"""
    conditions_path, root = result_fixtures._write_handwritten_experiment(directory)
    conditions = json.loads(conditions_path.read_bytes())
    conditions["baseline"] = _OLD
    conditions["candidate"] = _VALUE
    conditions["policy_parameters"] = {
        "baseline": _OLD_PARAMETERS,
        "candidate": _VALUE_PARAMETERS,
    }
    conditions_raw = result_fixtures._json_bytes(conditions)
    conditions_path.write_bytes(conditions_raw)
    digest = hashlib.sha256(conditions_raw).hexdigest()

    timing_policy_names = {
        "material": _OLD,
        "material-rook-mobility": _VALUE,
    }
    for game_path in root.glob("game-*.json"):
        game = json.loads(game_path.read_bytes())
        game["conditions_sha256"] = digest
        game["baseline"] = _OLD
        game["candidate"] = _VALUE
        for timing in game["move_times"]:
            timing["policy"] = timing_policy_names[timing["policy"]]
        game_path.write_bytes(result_fixtures._json_bytes(game))

    summary_path = root / "summary.json"
    summary = json.loads(summary_path.read_bytes())
    times = summary["move_time_by_policy"]
    old_times = times["material"]
    value_times = times.pop("material-rook-mobility")
    times["material"] = {
        "successful_moves": 0,
        "total_ns": 0,
        "average_ns": None,
        "max_ns": None,
    }
    times[_OLD] = old_times
    times[_VALUE] = value_times
    summary_path.write_bytes(result_fixtures._json_bytes(summary))
    return root


class PieceThreatValueComparisonResultTests(unittest.TestCase):
    def test_reader_accepts_value_weights_and_selected_summary_timing(self):
        """readerが価値合計の条件重みと選択方式の計時欄を受理する。

        旧U重みとのキー混同、方式名不登録、summary順の不整合を検出する。
        """
        self.assertEqual(
            comparison_io._policy_parameters(
                MoveSelectionPolicy.MATERIAL_PIECE_THREAT_VALUE_V1
            ),
            _VALUE_PARAMETERS,
        )
        with TemporaryDirectory() as directory:
            root = _write_handwritten_value_experiment(Path(directory))
            loaded = comparison_result_io.load_completed_comparison(root)

        self.assertIs(loaded.baseline, MoveSelectionPolicy.MATERIAL_PIECE_THREAT_V1)
        self.assertIs(
            loaded.candidate, MoveSelectionPolicy.MATERIAL_PIECE_THREAT_VALUE_V1
        )
        self.assertEqual(
            loaded.conditions["policy_parameters"],
            {"baseline": _OLD_PARAMETERS, "candidate": _VALUE_PARAMETERS},
        )
        self.assertEqual(
            tuple(loaded.summary["move_time_by_policy"]),
            (
                "random",
                "material",
                "two-ply-material",
                "full-width-4",
                "alpha-beta-4",
                _OLD,
                _VALUE,
            ),
        )
        self.assertEqual(loaded.summary["move_time_by_policy"][_OLD]["total_ns"], 302)
        self.assertEqual(loaded.summary["move_time_by_policy"][_VALUE]["total_ns"], 304)

    def test_reader_rejects_legacy_undefended_key_for_value_policy(self):
        """readerが価値合計係数を旧undefended枚数係数へ置き換えた条件を拒否する。

        hashを合わせたままの意味の異なる条件JSONを受理する誤りを検出する。
        """
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config, _ = input_fixtures.PieceThreatComparisonIOTests._config(
                root, baseline=_OLD, candidate=_VALUE, workers=4
            )
            conditions = comparison_io.conditions_payload(
                config,
                comparison_io.make_schedule(config),
                source_root=Path(__file__).parents[1],
            )
            self.assertEqual(
                conditions["policy_parameters"],
                {"baseline": _OLD_PARAMETERS, "candidate": _VALUE_PARAMETERS},
            )
            candidate_parameters = conditions["policy_parameters"]["candidate"]
            candidate_parameters["undefended"] = candidate_parameters.pop(
                "undefended_value"
            )
            with self.assertRaisesRegex(ValueError, "評価重み"):
                comparison_result_io._load_conditions(conditions, config.output_dir)


if __name__ == "__main__":
    unittest.main()
