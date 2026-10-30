"""連携評価conditionsのreader検証と再開契約を確認する。"""

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
from kaname_shogi.usi_move import parse_usi_move


class UndefendedPieceComparisonResultTests(unittest.TestCase):
    """連携評価conditions readerとresumeの契約を検証する。"""

    @staticmethod
    def _config(root, *, pairs=1, resume=False):
        """独立seed一覧を使うU方式比較条件を作る。"""
        positions_path = root / "positions.json"
        positions_raw = json.dumps(
            {
                "format": "kaname-shogi-comparison-positions-v1",
                "id": "undefended-result-test",
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
            "material-undefended-piece-material-only",
            "--candidate",
            "material-undefended-piece",
            "--positions",
            str(positions_path),
            "--pairs-per-position",
            str(pairs),
            "--seed-list",
            str(seed_path),
            "--max-plies",
            "1",
            "--workers",
            "4",
            "--output-dir",
            str(output_dir),
        ]
        if resume:
            args.append("--resume")
        try:
            return comparison_io.load_config(args)
        except ValueError as error:
            raise AssertionError(f"比較CLIがU方式を受理できません: {error}") from error

    def test_reader_rejects_swapped_or_missing_undefended_weights(self):
        """conditions hash更新後も逆転・欠落したU重みをreaderが拒否する。

        保存側で誤った値へconditionsと局参照hashを付け直しても、方式名だけを信用して
        異なる評価契約の実験を受理する誤りを検出する。
        """
        mutations = (
            (
                "swapped",
                lambda parameters: parameters.update(
                    baseline=parameters["candidate"], candidate=parameters["baseline"]
                ),
            ),
            (
                "missing-undefended",
                lambda parameters: parameters["candidate"].pop("undefended"),
            ),
        )
        for name, mutate in mutations:
            with self.subTest(case=name), TemporaryDirectory() as directory:
                root = Path(directory)
                config = self._config(root)
                conditions = comparison_io.conditions_payload(
                    config, make_schedule(config), source_root=Path(__file__).parents[1]
                )
                mutate(conditions["policy_parameters"])
                output_dir = config.output_dir
                output_dir.mkdir()
                comparison_io.atomic_write_json(
                    output_dir / "conditions.json", conditions
                )
                digest = hashlib.sha256(
                    (output_dir / "conditions.json").read_bytes()
                ).hexdigest()
                comparison_io.atomic_write_json(
                    output_dir / "game-000001.json",
                    {"conditions_sha256": digest},
                )

                try:
                    comparison_result_io.load_completed_comparison(output_dir)
                except ValueError as error:
                    self.assertIn(
                        "評価重み",
                        str(error),
                        f"重み検証より前の別エラーで拒否されています: {error}",
                    )
                else:
                    self.fail("不正なU重みを持つconditionsがreaderに受理されました")

    def test_resume_keeps_completed_undefended_piece_games(self):
        """resumeが完成済みU方式の局を保持し、残り予定だけを返す。

        完成局を再実行対象へ混ぜて確定棋譜を上書きする誤りを検出する。
        """
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config = self._config(root, pairs=2, resume=True)
            schedule = make_schedule(config)
            conditions = comparison_io.conditions_payload(
                config, schedule, source_root=Path(__file__).parents[1]
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

            self.assertEqual(
                tuple(result.schedule.game_id for result in state.completed_results),
                (first_game.game_id,),
            )
            self.assertEqual(
                tuple(game.game_id for game in state.pending_schedule),
                tuple(game.game_id for game in schedule[1:]),
            )
            self.assertEqual(game_path.read_bytes(), completed_bytes)


if __name__ == "__main__":
    unittest.main()
