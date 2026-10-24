"""完了した比較成果物の検証を確認する。"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kaname_shogi import (
    comparison as comparison_module,
)
from kaname_shogi import (
    comparison_io,
    comparison_result_io,
)
from kaname_shogi.comparison import (
    ComparisonConfig,
    ComparisonPosition,
    GameEndReason,
    ScheduledGame,
)
from kaname_shogi.comparison_analysis import game_score_bounds
from kaname_shogi.game_record import GameRecord
from kaname_shogi.model import (
    Board,
    Piece,
    PieceType,
    Position,
    Side,
    Square,
    create_initial_position,
)
from kaname_shogi.movegen import MoveSelectionPolicy
from kaname_shogi.repetition import RepetitionOutcome, RepetitionOutcomeKind
from kaname_shogi.sfen import SfenPosition, format_sfen
from kaname_shogi.usi_move import parse_usi_move

try:
    from kaname_shogi.comparison_result_io import load_completed_comparison
except ModuleNotFoundError as error:
    if error.name != "kaname_shogi.comparison_result_io":
        raise
    load_completed_comparison = None


_REASONS = (
    "checkmate",
    "no_legal_move",
    "perpetual_check_loss",
    "repetition",
    "ply_limit",
    "interrupted",
    "error",
    "unresolved_double_perpetual_check",
)
_START_SFEN = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"


def _json_bytes(value: object) -> bytes:
    """fixture専用の整形済みUTF-8 JSONを返す。比較成果物writerは使わない。"""
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _summary_fixture() -> dict[str, object]:
    """二局の棋譜と計時から独立に書いた、完了summary期待値を返す。"""
    counts = {reason: 0 for reason in _REASONS}
    counts["ply_limit"] = 2
    zero_time = {
        "successful_moves": 0,
        "total_ns": 0,
        "average_ns": None,
        "max_ns": None,
    }
    move_times = {
        "random": dict(zero_time),
        "material": {
            "successful_moves": 2,
            "total_ns": 302,
            "average_ns": 151.0,
            "max_ns": 201,
        },
        "two-ply-material": dict(zero_time),
        "full-width-4": dict(zero_time),
        "alpha-beta-4": dict(zero_time),
        "material-rook-mobility": {
            "successful_moves": 2,
            "total_ns": 304,
            "average_ns": 152.0,
            "max_ns": 202,
        },
    }
    side_counts = {
        side: {"games": 2, "wins": 0, "losses": 0, "no_winner": 2}
        for side in ("sente", "gote")
    }
    return {
        "format": "kaname-shogi-comparison-summary-v1",
        "status": "complete",
        "planned_games": 2,
        "started_games": 2,
        "ended_games": 2,
        "unstarted_games": 0,
        "completed_pairs": 1,
        "partial_pairs": 0,
        "results": counts,
        "perpetual_check_losses": {"sente": 0, "gote": 0},
        "by_position": {"initial": {"started_games": 2, "results": dict(counts)}},
        "by_side": side_counts,
        "move_time_by_policy": move_times,
        "elapsed_ns": 999,
        "statistical_decision": None,
    }


def _write_handwritten_experiment(directory: Path) -> tuple[Path, Path]:
    """writer APIに依存せず、手書き条件・二局・summaryを作る。"""
    positions_value = {
        "format": "kaname-shogi-comparison-positions-v1",
        "id": "tiny-c1-fixture",
        "positions": [
            {"id": "initial", "setup_moves": [], "rationale": "手書きfixture"}
        ],
    }
    positions_raw = _json_bytes(positions_value)
    seed_value = {
        "format": "kaname-shogi-comparison-seeds-v1",
        "purpose": "pilot",
        "positions_sha256": hashlib.sha256(positions_raw).hexdigest(),
        "position_ids": ["initial"],
        "pairs_per_position": 1,
        "source": "os",
        "bits": 128,
        "pairs": [
            {
                "position_id": "initial",
                "repetition_index": 0,
                "baseline_seed": 17,
                "candidate_seed": 18,
            }
        ],
    }
    seed_raw = _json_bytes(seed_value)
    schedule = [
        {
            "game_id": "game-000001",
            "position_id": "initial",
            "pair_number": 0,
            "game_number_in_pair": 1,
            "baseline_side": "sente",
            "candidate_side": "gote",
            "baseline_seed": 17,
            "candidate_seed": 18,
        },
        {
            "game_id": "game-000002",
            "position_id": "initial",
            "pair_number": 0,
            "game_number_in_pair": 2,
            "baseline_side": "gote",
            "candidate_side": "sente",
            "baseline_seed": 17,
            "candidate_seed": 18,
        },
    ]
    conditions = {
        "format": "kaname-shogi-comparison-conditions-v2",
        "baseline": "material",
        "candidate": "material-rook-mobility",
        "positions_file": "unused-original-input.json",
        "positions_sha256": hashlib.sha256(positions_raw).hexdigest(),
        "positions": [
            {
                "id": "initial",
                "setup_moves": [],
                "rationale": "手書きfixture",
                "start_sfen": _START_SFEN,
                "initial_move_number": 1,
            }
        ],
        "pairs_per_position": 1,
        "seed": None,
        "max_plies": 2,
        "schedule": schedule,
        "timing": {
            "source": "time.monotonic_ns",
            "start": "immediately_before_legal_moves",
            "end": "immediately_after_choose_move_returns",
            "unit": "nanoseconds",
        },
        "clock": None,
        "repetition": {
            "ordinary_fourth_occurrence": "continue",
            "ordinary_fifth_occurrence": "terminal",
            "ordinary_rematch": False,
            "perpetual_check_loss": "opposite_side_wins",
            "double_perpetual_check": "unresolved_no_winner",
        },
        "git": {"head": "a" * 40, "dirty": True, "diagnostic": None},
        "runtime": {
            "python_version": "3.9.0",
            "python_implementation": "CPython",
            "platform": "fixture-platform",
            "machine": "fixture-machine",
            "processor": "fixture-processor",
        },
        "source_sha256": "b" * 64,
        "positions_json": positions_raw.decode("utf-8"),
        "randomization": {
            "purpose": "pilot",
            "source": "os",
            "bits": 128,
            "seed_list_sha256": hashlib.sha256(seed_raw).hexdigest(),
            "seed_list_json": seed_raw.decode("utf-8"),
        },
        "policy_parameters": {
            "baseline": {},
            "candidate": {
                "material": 10,
                "mobility": 1,
                "mate_priority": True,
            },
        },
    }
    conditions_path = directory / "conditions.json"
    conditions_raw = _json_bytes(conditions)
    conditions_path.write_bytes(conditions_raw)
    conditions_hash = hashlib.sha256(conditions_raw).hexdigest()

    games = (
        (
            schedule[0],
            ("7g7f", "3c3d"),
            (
                ("sente", "material", "7g7f", 101),
                ("gote", "material-rook-mobility", "3c3d", 102),
            ),
        ),
        (
            schedule[1],
            ("7g7f", "3c3d"),
            (
                ("sente", "material-rook-mobility", "7g7f", 202),
                ("gote", "material", "3c3d", 201),
            ),
        ),
    )
    for scheduled, moves, timings in games:
        record = GameRecord(create_initial_position())
        for token in moves:
            move = parse_usi_move(token)
            if hasattr(move, "source"):
                record.apply_move(move.source, move.destination, promote=move.promote)
            else:
                record.apply_drop(move.piece_type, move.destination)
        game = {
            "format": "kaname-shogi-comparison-game-v1",
            "conditions_sha256": conditions_hash,
            **scheduled,
            "baseline": "material",
            "candidate": "material-rook-mobility",
            "start_sfen": _START_SFEN,
            "initial_move_number": 1,
            "plies": 2,
            "reason": "ply_limit",
            "winner_side": None,
            "winner_policy": None,
            "record": record.to_payload(),
            "move_times": [
                {
                    "ply": ply,
                    "side": side,
                    "policy": policy,
                    "move": move,
                    "elapsed_ns": elapsed_ns,
                }
                for ply, (side, policy, move, elapsed_ns) in enumerate(timings, start=1)
            ],
            "unfinished_calculation": None,
            "error": None,
        }
        (directory / f"{scheduled['game_id']}.json").write_bytes(_json_bytes(game))

    (directory / "summary.json").write_bytes(_json_bytes(_summary_fixture()))
    return conditions_path, directory


def _rewrite_conditions_hash(input_dir: Path) -> str:
    """conditionsを保存し直して全局から参照するSHA-256を更新する。"""
    conditions_raw = (input_dir / "conditions.json").read_bytes()
    digest = hashlib.sha256(conditions_raw).hexdigest()
    for game_path in input_dir.glob("game-*.json"):
        game = json.loads(game_path.read_bytes())
        game["conditions_sha256"] = digest
        game_path.write_bytes(_json_bytes(game))
    return digest


class ComparisonResultReadTests(unittest.TestCase):
    def _require_implementation(self):
        """未実装APIは振る舞いの未実装として表示する。"""
        self.assertIsNotNone(
            load_completed_comparison, "完了比較の検証読込が未実装です"
        )

    def test_reads_handwritten_complete_v2_and_candidate_score_bounds(self):
        """手書き成果物を検証し、候補視点の上限・下限を保持する。

        条件JSONの入れ子、予定・方式別種、開始SFEN、合法棋譜・計時、summaryを読まず
        勝ち負けの先後や勝者なしの手数上限を候補得点へ誤変換する誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            _, input_dir = _write_handwritten_experiment(Path(directory))

            loaded = load_completed_comparison(input_dir)

        self.assertEqual(loaded.purpose, "pilot")
        self.assertEqual(loaded.baseline, MoveSelectionPolicy.MATERIAL)
        self.assertEqual(loaded.candidate, MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY)
        self.assertEqual(len(loaded.results), 2)
        self.assertEqual(
            tuple((score.lower, score.upper) for score in loaded.pair_scores),
            ((0, 1),),
        )
        self.assertEqual(loaded.summary["elapsed_ns"], 999)

    def test_maps_winner_side_to_candidate_policy_and_score(self):
        """先後交換した勝者を方式へ対応付けて候補得点を反転する。

        勝者先後を候補方式へ固定したり、先後交換後の勝ち負けを反転しない誤りを検出する。
        このreader境界テストは比較writerや集計結果から期待値を作らない。
        """
        self._require_implementation()
        board = Board()
        for file, rank, piece_type, side in (
            (5, 1, PieceType.KING, Side.GOTE),
            (9, 9, PieceType.KING, Side.SENTE),
            (5, 3, PieceType.ROOK, Side.SENTE),
            (4, 3, PieceType.GOLD, Side.SENTE),
            (4, 1, PieceType.PAWN, Side.GOTE),
            (6, 1, PieceType.PAWN, Side.GOTE),
            (4, 2, PieceType.PAWN, Side.GOTE),
            (6, 2, PieceType.PAWN, Side.GOTE),
        ):
            board.set_piece(Square(file, rank), Piece(piece_type, side))
        position = Position(board, Side.SENTE)
        start_sfen = format_sfen(SfenPosition(position, 1))
        comparison_position = ComparisonPosition(
            "mate-in-one", (), "既知の一手詰め", position, start_sfen, 1
        )
        config = ComparisonConfig(
            baseline=MoveSelectionPolicy.MATERIAL,
            candidate=MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY,
            positions=(comparison_position,),
            pairs_per_position=1,
            seed=None,
            max_plies=1,
            output_dir=Path("unused-output"),
            positions_path=Path("unused-positions.json"),
            positions_json=b"{}",
        )
        record = GameRecord(position)
        record.apply_move(Square(5, 3), Square(5, 2))

        for game_id, candidate_side, expected_score in (
            ("game-000001", Side.SENTE, (1, 1)),
            ("game-000002", Side.GOTE, (0, 0)),
        ):
            baseline_side = Side.GOTE if candidate_side is Side.SENTE else Side.SENTE
            schedule = ScheduledGame(
                game_id=game_id,
                position_id="mate-in-one",
                pair_number=0,
                game_number_in_pair=1,
                baseline_side=baseline_side,
                candidate_side=candidate_side,
                baseline_seed=11,
                candidate_seed=12,
            )
            policy = (
                "material-rook-mobility" if candidate_side is Side.SENTE else "material"
            )
            payload = {
                "format": "kaname-shogi-comparison-game-v1",
                "conditions_sha256": "a" * 64,
                **comparison_io._scheduled_game_payload(schedule),
                "baseline": "material",
                "candidate": "material-rook-mobility",
                "start_sfen": start_sfen,
                "initial_move_number": 1,
                "plies": 1,
                "reason": "checkmate",
                "winner_side": "sente",
                "winner_policy": policy,
                "record": record.to_payload(),
                "move_times": [
                    {
                        "ply": 1,
                        "side": "sente",
                        "policy": policy,
                        "move": "5c5b",
                        "elapsed_ns": 1,
                    }
                ],
                "unfinished_calculation": None,
                "error": None,
            }

            result = comparison_result_io._load_game(
                payload, schedule, config, conditions_sha256="a" * 64
            )
            self.assertEqual(
                game_score_bounds(
                    result.reason, result.winner_policy, config.candidate
                ),
                expected_score,
            )
            self.assertEqual(
                result.winner_policy,
                config.candidate if candidate_side is Side.SENTE else config.baseline,
            )

    def test_rejects_one_game_from_another_experiment(self):
        """一局だけ条件参照が違う完了結果を混ぜない。

        同じ方式・予定番号・棋譜でもconditions SHAが異なる局を受け入れ、別実験の結果を
        同じ乱数種一覧からの一組として誤集計する誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            _, input_dir = _write_handwritten_experiment(Path(directory))
            game_path = input_dir / "game-000002.json"
            game = json.loads(game_path.read_bytes())
            game["conditions_sha256"] = "c" * 64
            game_path.write_bytes(_json_bytes(game))

            with self.assertRaises(ValueError):
                load_completed_comparison(input_dir)

    def test_rejects_legacy_conditions_and_non_exact_game_set(self):
        """旧条件・欠落局・余分な局を分析対象にしない。

        v1主乱数種実験を独立抽出一覧へ自動昇格する、または予定と違う局集合を完了済みと
        扱う誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            _, input_dir = _write_handwritten_experiment(Path(directory))
            conditions_path = input_dir / "conditions.json"
            conditions = json.loads(conditions_path.read_bytes())
            conditions["format"] = "kaname-shogi-comparison-conditions-v1"
            conditions_path.write_bytes(_json_bytes(conditions))
            with self.assertRaises(ValueError):
                load_completed_comparison(input_dir)

        for mutation in ("missing", "extra"):
            with (
                self.subTest(mutation=mutation),
                tempfile.TemporaryDirectory() as directory,
            ):
                _, input_dir = _write_handwritten_experiment(Path(directory))
                if mutation == "missing":
                    (input_dir / "game-000002.json").unlink()
                else:
                    (input_dir / "game-999999.json").write_bytes(b"{}")
                with self.assertRaises(ValueError):
                    load_completed_comparison(input_dir)

    def test_rejects_forged_summary_and_position_hash_mismatch(self):
        """再集計とスナップショットハッシュでsummary・局面改ざんを拒否する。

        正しい形式に見える偽の完了件数や、JSON文字列と保存ハッシュが違う条件を通す
        誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            _, input_dir = _write_handwritten_experiment(Path(directory))
            summary_path = input_dir / "summary.json"
            summary = json.loads(summary_path.read_bytes())
            summary["ended_games"] = 1
            summary_path.write_bytes(_json_bytes(summary))
            with self.assertRaises(ValueError):
                load_completed_comparison(input_dir)

    def test_rejects_unknown_nested_condition_and_bool_as_integer(self):
        """conditions v2の入れ子を厳密にし、boolを数値欄へ通さない。

        将来の未知フィールドを黙認したり、Python上で整数と等しいtrueを種ビット数や
        手数上限として解釈する誤りを検出する。
        """
        self._require_implementation()
        for path, mutate in (
            (
                "conditions",
                lambda data: data["repetition"].update({"unknown": "allow"}),
            ),
            ("conditions", lambda data: data.update({"max_plies": True})),
            (
                "conditions",
                lambda data: data["repetition"].update({"ordinary_rematch": 0}),
            ),
            (
                "conditions",
                lambda data: data["randomization"].update({"bits": True}),
            ),
        ):
            with (
                self.subTest(mutation=mutate),
                tempfile.TemporaryDirectory() as directory,
            ):
                _, input_dir = _write_handwritten_experiment(Path(directory))
                target = input_dir / f"{path}.json"
                payload = json.loads(target.read_bytes())
                mutate(payload)
                target.write_bytes(_json_bytes(payload))
                _rewrite_conditions_hash(input_dir)
                with self.assertRaises(ValueError):
                    load_completed_comparison(input_dir)

    def test_rejects_legal_moves_continuing_after_fifth_repetition(self):
        """合法な棋譜でも五回目の局面反復後に続く手を拒否する。

        各手が個別に合法であることだけを見て、千日手終局後へ棋譜を継ぎ足した完了局を
        有効な比較結果として集計する誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            _, input_dir = _write_handwritten_experiment(Path(directory))
            conditions_path = input_dir / "conditions.json"
            conditions = json.loads(conditions_path.read_bytes())
            conditions["max_plies"] = 20
            conditions_path.write_bytes(_json_bytes(conditions))
            conditions_hash = _rewrite_conditions_hash(input_dir)

            cycle = ("5i5h", "5a5b", "5h5i", "5b5a")
            moves = cycle * 4 + ("5i5h",)
            record = GameRecord(create_initial_position())
            timings = []
            for ply, token in enumerate(moves, start=1):
                move = parse_usi_move(token)
                if hasattr(move, "source"):
                    record.apply_move(
                        move.source, move.destination, promote=move.promote
                    )
                else:
                    record.apply_drop(move.piece_type, move.destination)
                side = "sente" if ply % 2 else "gote"
                policy = "material" if ply % 2 else "material-rook-mobility"
                timings.append(
                    {
                        "ply": ply,
                        "side": side,
                        "policy": policy,
                        "move": token,
                        "elapsed_ns": ply,
                    }
                )
            game_path = input_dir / "game-000001.json"
            game = json.loads(game_path.read_bytes())
            game.update(
                {
                    "conditions_sha256": conditions_hash,
                    "plies": len(moves),
                    "reason": "ply_limit",
                    "record": record.to_payload(),
                    "move_times": timings,
                }
            )
            game_path.write_bytes(_json_bytes(game))

            with self.assertRaisesRegex(ValueError, "既終局後"):
                load_completed_comparison(input_dir)

    def test_ignores_analysis_named_file_and_rejects_symlinked_game(self):
        """別名分析JSONは局数にせず、入力ディレクトリ外の局symlinkを拒否する。

        analysis.jsonを予定外局として数える、または局ファイル名から外部へ到達する
        シンボリックリンクを読み込む誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            _, input_dir = _write_handwritten_experiment(Path(directory))
            (input_dir / "analysis.json").write_text("{}", encoding="utf-8")
            self.assertEqual(len(load_completed_comparison(input_dir).results), 2)

        with tempfile.TemporaryDirectory() as directory:
            _, input_dir = _write_handwritten_experiment(Path(directory))
            outside = Path(directory) / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            (input_dir / "game-000002.json").unlink()
            (input_dir / "game-000002.json").symlink_to(outside)
            with self.assertRaises(ValueError):
                load_completed_comparison(input_dir)

    def test_rejects_bool_summary_elapsed_instead_of_integer(self):
        """summary elapsed_nsを有限の非負整数に限定する。

        JSONのtrueがPython上で1と等しいことを利用し、壁時計時間の記録へboolを混ぜる
        誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            _, input_dir = _write_handwritten_experiment(Path(directory))
            summary_path = input_dir / "summary.json"
            summary = json.loads(summary_path.read_bytes())
            summary["elapsed_ns"] = True
            summary_path.write_bytes(_json_bytes(summary))

            with self.assertRaises(ValueError):
                load_completed_comparison(input_dir)

        with tempfile.TemporaryDirectory() as directory:
            conditions_path, input_dir = _write_handwritten_experiment(Path(directory))
            conditions = json.loads(conditions_path.read_bytes())
            conditions["positions_json"] += " "
            conditions_path.write_bytes(_json_bytes(conditions))
            with self.assertRaises(ValueError):
                load_completed_comparison(input_dir)

        with tempfile.TemporaryDirectory() as directory:
            conditions_path, input_dir = _write_handwritten_experiment(Path(directory))
            conditions = json.loads(conditions_path.read_bytes())
            conditions["randomization"]["seed_list_json"] += " "
            conditions_path.write_bytes(_json_bytes(conditions))
            with self.assertRaisesRegex(ValueError, "乱数種スナップショット"):
                load_completed_comparison(input_dir)

    def test_rejects_unfinished_or_misreported_completed_game(self):
        """完了局の未確定計算と終局理由・上限の食い違いを拒否する。

        中断・探索失敗の残余値や、上限前に成立していない終局理由を完了済み局として
        得点集計へ混ぜる誤りを検出する。
        """
        self._require_implementation()
        for field, value in (("unfinished_calculation", 9), ("reason", "repetition")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                _, input_dir = _write_handwritten_experiment(Path(directory))
                game_path = input_dir / "game-000001.json"
                game = json.loads(game_path.read_bytes())
                game[field] = value
                game_path.write_bytes(_json_bytes(game))
                expected_message = (
                    "未確定計算" if field == "unfinished_calculation" else "終局理由"
                )
                with self.assertRaisesRegex(ValueError, expected_message):
                    load_completed_comparison(input_dir)

    def test_rejects_schedule_seed_and_timing_mismatch(self):
        """保存予定・局の乱数種と一手計時を条件・合法棋譜に結び付ける。

        別種の局を同じファイル名で混ぜたり、棋譜手と無関係な計時を保存しても分析へ
        進めてしまう誤りを検出する。
        """
        self._require_implementation()
        for target_name, mutate, message in (
            (
                "conditions.json",
                lambda data: data["schedule"][0].update({"candidate_seed": 19}),
                "局予定",
            ),
            (
                "game-000001.json",
                lambda data: data.update({"baseline_seed": 19}),
                "予定値 baseline_seed",
            ),
            (
                "game-000001.json",
                lambda data: data["move_times"][0].update({"move": "2g2f"}),
                "計時の手が棋譜",
            ),
        ):
            with (
                self.subTest(target=target_name, message=message),
                tempfile.TemporaryDirectory() as directory,
            ):
                _, input_dir = _write_handwritten_experiment(Path(directory))
                target = input_dir / target_name
                payload = json.loads(target.read_bytes())
                mutate(payload)
                target.write_bytes(_json_bytes(payload))
                if target_name == "conditions.json":
                    _rewrite_conditions_hash(input_dir)
                with self.assertRaisesRegex(ValueError, message):
                    load_completed_comparison(input_dir)

    def test_terminal_conversion_preserves_repetition_before_board_limit(self):
        """終局理由を千日手、合法手なし、手数上限の順に一意に写す。

        上限到達後に反復成立を上書きする、または合法手なしの詰みと上限を取り違える
        誤りを検出する。
        """
        repetition_terminal = getattr(comparison_module, "repetition_terminal", None)
        board_terminal = getattr(comparison_module, "board_terminal", None)
        self.assertIsNotNone(repetition_terminal, "反復終局変換の抽出が未実装です")
        self.assertIsNotNone(board_terminal, "盤面終局変換の抽出が未実装です")

        self.assertIsNone(
            repetition_terminal(RepetitionOutcome(RepetitionOutcomeKind.CONTINUE))
        )
        self.assertEqual(
            repetition_terminal(RepetitionOutcome(RepetitionOutcomeKind.REPETITION)),
            (GameEndReason.REPETITION, None),
        )
        self.assertEqual(
            repetition_terminal(
                RepetitionOutcome(
                    RepetitionOutcomeKind.PERPETUAL_CHECK_LOSS, Side.SENTE
                )
            ),
            (GameEndReason.PERPETUAL_CHECK_LOSS, Side.GOTE),
        )
        self.assertEqual(
            repetition_terminal(
                RepetitionOutcome(
                    RepetitionOutcomeKind.UNRESOLVED_DOUBLE_PERPETUAL_CHECK
                )
            ),
            (GameEndReason.UNRESOLVED_DOUBLE_PERPETUAL_CHECK, None),
        )
        for invalid_outcome in (
            RepetitionOutcome(RepetitionOutcomeKind.REPETITION, Side.SENTE),
            RepetitionOutcome(
                RepetitionOutcomeKind.UNRESOLVED_DOUBLE_PERPETUAL_CHECK,
                Side.SENTE,
            ),
        ):
            with self.subTest(invalid_outcome=invalid_outcome):
                with self.assertRaises(ValueError):
                    repetition_terminal(invalid_outcome)

        initial = create_initial_position()
        self.assertIsNone(
            board_terminal(initial, has_legal_moves=True, plies=1, max_plies=2)
        )
        self.assertEqual(
            board_terminal(initial, has_legal_moves=True, plies=2, max_plies=2),
            (GameEndReason.PLY_LIMIT, None),
        )
        board = Board()
        board.set_piece(Square(1, 1), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(9, 9), Piece(PieceType.KING, Side.GOTE))
        for file, rank in ((2, 1), (1, 2), (2, 2)):
            board.set_piece(Square(file, rank), Piece(PieceType.PAWN, Side.SENTE))
        no_legal_moves = Position(board, Side.SENTE)
        self.assertEqual(
            board_terminal(no_legal_moves, has_legal_moves=False, plies=2, max_plies=2),
            (GameEndReason.NO_LEGAL_MOVE, Side.GOTE),
        )
