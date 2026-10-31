"""V比較conditionsの読込・summary・resume契約を確認する。"""

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kaname_shogi import comparison_io, comparison_result_io
from kaname_shogi.comparison import (
    GameEndReason,
    GameResult,
    MoveTiming,
    make_schedule,
)
from kaname_shogi.comparison_resume import load_resume_state
from kaname_shogi.game_record import GameRecord
from kaname_shogi.movegen import MoveSelectionPolicy
from kaname_shogi.usi_move import parse_usi_move
from tests import test_comparison_result_io as result_fixtures
from tests import test_piece_threat_comparison_io as input_fixtures
from tests import test_undefended_piece_comparison_io as undefended_fixtures

_V0 = "material-piece-threat-v0"
_V1 = "material-piece-threat-v1"
_V_PARAMETERS = {
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
}
_U_BASELINE = "material-undefended-piece-material-only"
_U_CANDIDATE = "material-undefended-piece"


def _write_handwritten_policy_experiment(
    directory: Path,
    *,
    baseline: str,
    candidate: str,
    policy_parameters: dict[str, object],
) -> Path:
    """手書き二局artifactを指定policy名と実効重みに対応させる。"""
    conditions_path, root = result_fixtures._write_handwritten_experiment(directory)
    conditions = json.loads(conditions_path.read_bytes())
    conditions["baseline"] = baseline
    conditions["candidate"] = candidate
    conditions["policy_parameters"] = policy_parameters
    conditions_raw = result_fixtures._json_bytes(conditions)
    conditions_path.write_bytes(conditions_raw)
    digest = hashlib.sha256(conditions_raw).hexdigest()

    timing_policy_names = {
        "material": baseline,
        "material-rook-mobility": candidate,
    }
    for game_path in root.glob("game-*.json"):
        game = json.loads(game_path.read_bytes())
        game["conditions_sha256"] = digest
        game["baseline"] = baseline
        game["candidate"] = candidate
        for timing in game["move_times"]:
            timing["policy"] = timing_policy_names[timing["policy"]]
        game_path.write_bytes(result_fixtures._json_bytes(game))

    summary_path = root / "summary.json"
    summary = json.loads(summary_path.read_bytes())
    times = summary["move_time_by_policy"]
    baseline_times = times["material"]
    candidate_times = times.pop("material-rook-mobility")
    times["material"] = {
        "successful_moves": 0,
        "total_ns": 0,
        "average_ns": None,
        "max_ns": None,
    }
    times[baseline] = baseline_times
    times[candidate] = candidate_times
    summary_path.write_bytes(result_fixtures._json_bytes(summary))
    return root


class PieceThreatComparisonResultTests(unittest.TestCase):
    def test_reader_accepts_v_conditions_and_summary(self):
        """readerがV重み・二方式の計時summaryを一体として受理する。

        条件のV係数やsummary policy順を保存後に誤って拒否する不整合を検出する。
        """
        with TemporaryDirectory() as directory:
            root = _write_handwritten_policy_experiment(
                Path(directory),
                baseline=_V0,
                candidate=_V1,
                policy_parameters=_V_PARAMETERS,
            )
            loaded = comparison_result_io.load_completed_comparison(root)

        self.assertIs(loaded.baseline, MoveSelectionPolicy.MATERIAL_PIECE_THREAT_V0)
        self.assertIs(loaded.candidate, MoveSelectionPolicy.MATERIAL_PIECE_THREAT_V1)
        self.assertEqual(
            tuple(loaded.summary["move_time_by_policy"]),
            (
                "random",
                "material",
                "two-ply-material",
                "full-width-4",
                "alpha-beta-4",
                _V0,
                _V1,
            ),
        )
        self.assertEqual(loaded.summary["move_time_by_policy"][_V0]["total_ns"], 302)
        self.assertEqual(loaded.summary["move_time_by_policy"][_V1]["total_ns"], 304)

    def test_reader_rejects_missing_or_swapped_v_weight(self):
        """hashを更新しても欠落・逆転したV重みをreaderが拒否する。

        conditions hashだけに整合した誤った評価契約を読み込む誤りを検出する。
        """
        for mutation in ("swapped", "missing"):
            with self.subTest(mutation=mutation), TemporaryDirectory() as directory:
                root = Path(directory)
                config, _ = input_fixtures.PieceThreatComparisonIOTests._config(
                    root, baseline=_V0, candidate=_V1
                )
                conditions = comparison_io.conditions_payload(
                    config,
                    make_schedule(config),
                    source_root=Path(__file__).parents[1],
                )
                parameters = conditions["policy_parameters"]
                if mutation == "swapped":
                    parameters["baseline"]["supported_threat"] = 1
                    parameters["candidate"]["supported_threat"] = 0
                else:
                    del parameters["candidate"]["supported_threat"]

                config.output_dir.mkdir()
                comparison_io.atomic_write_json(
                    config.output_dir / "conditions.json", conditions
                )
                digest = hashlib.sha256(
                    (config.output_dir / "conditions.json").read_bytes()
                ).hexdigest()
                comparison_io.atomic_write_json(
                    config.output_dir / "game-000001.json",
                    {"conditions_sha256": digest},
                )
                with self.assertRaisesRegex(ValueError, "評価重み"):
                    comparison_result_io.load_completed_comparison(config.output_dir)

    def test_legacy_undefended_conditions_remain_readable(self):
        """既存U条件をV重みなしのままreaderが読み込む。

        新しいV必須欄を旧U方式へ遡及要求し、既存artifactを拒否する誤りを検出する。
        """
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config, _ = undefended_fixtures.UndefendedPieceComparisonIOTests._config(
                root,
                baseline=_U_BASELINE,
                candidate=_U_CANDIDATE,
            )
            conditions = comparison_io.conditions_payload(
                config,
                make_schedule(config),
                source_root=Path(__file__).parents[1],
            )
            loaded, schedule = comparison_result_io._load_conditions(
                conditions, config.output_dir
            )

        self.assertIs(
            loaded.baseline, MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE_MATERIAL_ONLY
        )
        self.assertIs(loaded.candidate, MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE)
        self.assertEqual(len(schedule), 2)
        self.assertNotIn(
            "supported_threat", conditions["policy_parameters"]["candidate"]
        )

    def test_reader_keeps_legacy_undefended_summary_order(self):
        """Vを含まない旧U artifactをreaderが従来のsummary順で読む。

        未選択Vの計時欄を旧conditionsやsummaryへ要求する互換性破壊を検出する。
        """
        parameters = {
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
        }
        with TemporaryDirectory() as directory:
            root = _write_handwritten_policy_experiment(
                Path(directory),
                baseline=_U_BASELINE,
                candidate=_U_CANDIDATE,
                policy_parameters=parameters,
            )
            conditions = json.loads((root / "conditions.json").read_bytes())
            config, _ = comparison_result_io._load_conditions(conditions, root)
            self.assertEqual(
                comparison_result_io._summary_policy_order(config),
                (
                    MoveSelectionPolicy.RANDOM,
                    MoveSelectionPolicy.MATERIAL,
                    MoveSelectionPolicy.TWO_PLY_MATERIAL,
                    MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH,
                    MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA,
                    MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE_MATERIAL_ONLY,
                    MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE,
                ),
            )
            loaded = comparison_result_io.load_completed_comparison(root)

        self.assertEqual(
            tuple(loaded.summary["move_time_by_policy"]),
            (
                "random",
                "material",
                "two-ply-material",
                "full-width-4",
                "alpha-beta-4",
                _U_BASELINE,
                _U_CANDIDATE,
            ),
        )
        self.assertNotIn(
            "supported_threat", loaded.conditions["policy_parameters"]["candidate"]
        )

    def test_resume_keeps_completed_v_comparison_games(self):
        """resumeは完了済みV局を保持し、未完了予定だけを返す。

        完了局の再実行や条件不一致としての誤拒否を検出する。
        """
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config, _ = input_fixtures.PieceThreatComparisonIOTests._config(
                root, baseline=_V0, candidate=_V1, pairs=2, resume=True
            )
            schedule = make_schedule(config)
            conditions = comparison_io.conditions_payload(
                config,
                schedule,
                source_root=Path(__file__).parents[1],
            )
            comparison_io.atomic_write_json(
                config.output_dir / "conditions.json", conditions
            )
            conditions_sha256 = hashlib.sha256(
                (config.output_dir / "conditions.json").read_bytes()
            ).hexdigest()

            first_game = schedule[0]
            position = config.positions[0]
            record = GameRecord(position.start_position)
            move = parse_usi_move("7g7f")
            side = record.current_position.side_to_move
            policy = (
                config.baseline
                if side is first_game.baseline_side
                else config.candidate
            )
            record.apply_move(move.source, move.destination, promote=move.promote)
            result = GameResult(
                schedule=first_game,
                start_sfen=position.start_sfen,
                initial_move_number=position.initial_move_number,
                record=record,
                reason=GameEndReason.PLY_LIMIT,
                winner_side=None,
                winner_policy=None,
                plies=1,
                move_times_ns=(MoveTiming(1, side, policy, move, 15),),
                unfinished_calculation_ns=None,
                error=None,
            )
            game_path = config.output_dir / f"{first_game.game_id}.json"
            comparison_io.atomic_write_json(
                game_path,
                comparison_io.game_payload(
                    result, config, conditions_sha256=conditions_sha256
                ),
            )
            completed_bytes = game_path.read_bytes()

            state = load_resume_state(config, source_root=Path(__file__).parents[1])
            bytes_after_resume = game_path.read_bytes()

        self.assertEqual(
            tuple(result.schedule.game_id for result in state.completed_results),
            (first_game.game_id,),
        )
        self.assertEqual(
            tuple(game.game_id for game in state.pending_schedule),
            tuple(game.game_id for game in schedule[1:]),
        )
        self.assertEqual(bytes_after_resume, completed_bytes)


if __name__ == "__main__":
    unittest.main()
