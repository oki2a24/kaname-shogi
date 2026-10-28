"""C2比較の集計・保存結果読込を独立な小さい成果物で確認する。"""

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from kaname_shogi import compare_games, comparison_result_io
from kaname_shogi.comparison import BatchStatus, make_schedule, summarize
from kaname_shogi.comparison_io import load_config
from kaname_shogi.comparison_result_io import load_completed_comparison
from kaname_shogi.movegen import MoveSelectionPolicy
from tests import test_comparison_io as input_fixtures
from tests import test_comparison_result_io as result_fixtures

_BASELINE = "material-king-safety-material-only"
_CANDIDATE = "material-king-safety"


def write_handwritten_c2_experiment(directory):
    """既存の手書き二局fixtureをC2の条件と手計算済み集計にする。"""
    conditions_path, root = result_fixtures._write_handwritten_experiment(directory)
    conditions = json.loads(conditions_path.read_bytes())
    conditions["baseline"] = _BASELINE
    conditions["candidate"] = _CANDIDATE
    conditions["policy_parameters"] = {
        "baseline": {"material": 10, "safety": 0, "mate_priority": True},
        "candidate": {"material": 10, "safety": 1, "mate_priority": True},
    }
    raw = result_fixtures._json_bytes(conditions)
    conditions_path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    for game_path in root.glob("game-*.json"):
        game = json.loads(game_path.read_bytes())
        game["conditions_sha256"] = digest
        game["baseline"] = _BASELINE
        game["candidate"] = _CANDIDATE
        for timing in game["move_times"]:
            timing["policy"] = {
                "material": _BASELINE,
                "material-rook-mobility": _CANDIDATE,
            }[timing["policy"]]
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
    times[_BASELINE] = baseline_times
    times[_CANDIDATE] = candidate_times
    summary_path.write_bytes(result_fixtures._json_bytes(summary))
    return root


class KingSafetyComparisonResultTests(unittest.TestCase):
    def test_summary_includes_only_the_selected_new_policies(self):
        """C2比較のsummaryには両方式の計時欄が追加される。

        列挙追加時に方式別計時欄を落とし、記録や再開を壊す誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            positions = input_fixtures.ComparisonInputTests._write_positions(
                directory, [input_fixtures.ComparisonInputTests._position_entry()]
            )
            args = input_fixtures.ComparisonInputTests._config_args(
                positions,
                Path(directory) / "results",
                **{"--baseline": _BASELINE, "--candidate": _CANDIDATE},
            )
            config = load_config(args)
            summary = summarize(
                config,
                (),
                batch_status=BatchStatus.INTERRUPTED,
                unstarted_games=len(make_schedule(config)),
                elapsed_ns=0,
            )
        self.assertEqual(
            tuple(summary["move_time_by_policy"]),
            (
                "random",
                "material",
                "two-ply-material",
                "full-width-4",
                "alpha-beta-4",
                _BASELINE,
                _CANDIDATE,
            ),
        )

    def test_reader_accepts_handwritten_c2_games_and_summary(self):
        """手書き二局のC2結果を読み、方式別計時と未決着を保持する。

        分析時の新方式の計時欄欠落や先後交換後の方式対応の誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            root = write_handwritten_c2_experiment(Path(directory))
            try:
                loaded = load_completed_comparison(root)
            except ValueError as error:
                self.fail(f"C2の保存済み二局を読み込めません: {error}")
        self.assertIs(
            loaded.baseline, MoveSelectionPolicy.MATERIAL_KING_SAFETY_MATERIAL_ONLY
        )
        self.assertIs(loaded.candidate, MoveSelectionPolicy.MATERIAL_KING_SAFETY)
        self.assertEqual(len(loaded.results), 2)
        self.assertEqual(
            tuple((score.lower, score.upper) for score in loaded.pair_scores), ((0, 1),)
        )
        self.assertEqual(
            loaded.summary["move_time_by_policy"][_BASELINE]["total_ns"], 302
        )
        self.assertEqual(
            loaded.summary["move_time_by_policy"][_CANDIDATE]["total_ns"], 304
        )

    def test_reader_rejects_changed_or_missing_king_safety_weights(self):
        """C2条件の重みを改変・欠落した結果は分析前に拒否する。

        条件ハッシュを整えても、候補と対照の安全度係数の入れ替えを見逃さない。
        """
        for mutation in ("baseline", "candidate", "missing"):
            with (
                self.subTest(mutation=mutation),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = write_handwritten_c2_experiment(Path(directory))
                path = root / "conditions.json"
                conditions = json.loads(path.read_bytes())
                if mutation == "missing":
                    del conditions["policy_parameters"]["candidate"]["safety"]
                else:
                    conditions["policy_parameters"][mutation]["safety"] = (
                        1 if mutation == "baseline" else 0
                    )
                path.write_bytes(result_fixtures._json_bytes(conditions))
                result_fixtures._rewrite_conditions_hash(root)
                with self.assertRaisesRegex(ValueError, "評価重み"):
                    load_completed_comparison(root)

    def test_analysis_checkpoint_resumes_c2_without_replaying_completed_games(self):
        """C2二局を分析途中で保存し、完了局を再生せず再開できる。

        checkpointに新方式の計時欄を保存・復元できない誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory) / "input"
            input_dir.mkdir()
            write_handwritten_c2_experiment(input_dir)
            output = Path(directory) / "analysis.json"
            checkpoint = output.with_name(output.name + ".checkpoint")
            args = ["--input-dir", str(input_dir), "--output", str(output)]
            with (
                patch.object(
                    comparison_result_io,
                    "write_new_json",
                    side_effect=KeyboardInterrupt,
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                status = comparison_result_io.main(args)
            self.assertEqual(status, 130)
            self.assertEqual(len(tuple((checkpoint / "games").glob("*.json"))), 2)
            self.assertFalse(output.exists())
            with (
                patch.object(
                    comparison_result_io,
                    "_load_game",
                    wraps=comparison_result_io._load_game,
                ) as load_game,
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                status = comparison_result_io.main([*args, "--resume"])
            self.assertEqual(status, 0)
            load_game.assert_not_called()
            payload = json.loads(output.read_bytes())
            self.assertEqual(payload["move_time_by_policy"][_BASELINE]["total_ns"], 302)
            self.assertEqual(
                payload["move_time_by_policy"][_CANDIDATE]["total_ns"], 304
            )
            self.assertFalse(checkpoint.exists())

    def test_comparison_resume_keeps_completed_c2_games(self):
        """短いC2比較を再開すると、完了局を再実行せずそのまま保持する。

        新方式の条件や先後別計時を検証できず再開を拒む誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            positions = input_fixtures.ComparisonInputTests._write_positions(
                directory, [input_fixtures.ComparisonInputTests._position_entry()]
            )
            seeds = input_fixtures.ComparisonInputTests._write_seed_list(
                directory, positions, pairs_per_position=1
            )
            output = Path(directory) / "results"
            args = input_fixtures.ComparisonInputTests._config_args(
                positions,
                output,
                **{
                    "--baseline": _BASELINE,
                    "--candidate": _CANDIDATE,
                    "--pairs-per-position": "1",
                    "--max-plies": "1",
                },
            )
            args.remove("--seed")
            args.remove("17")
            args.extend(("--seed-list", str(seeds)))
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                status = compare_games.main(args)
            self.assertEqual(status, 0)
            games = sorted(output.glob("game-*.json"))
            self.assertEqual(len(games), 2)
            before = [path.read_bytes() for path in games]
            with (
                patch.object(
                    compare_games, "run_game", wraps=compare_games.run_game
                ) as run_game,
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                status = compare_games.main([*args, "--resume"])
            self.assertEqual(status, 0)
            run_game.assert_not_called()
            self.assertEqual([path.read_bytes() for path in games], before)
