"""比較対局の実験予定を確認する。"""

import random
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from kaname_shogi import comparison as comparison_module
from kaname_shogi.comparison import GameResult, MoveTiming
from kaname_shogi.comparison_seeds import PairSeeds, SeedPlan
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
from kaname_shogi.movegen import MoveSelectionPolicy, legal_moves
from kaname_shogi.repetition import RepetitionOutcome
from kaname_shogi.usi_move import parse_usi_move

ComparisonConfig = getattr(comparison_module, "ComparisonConfig", None)
ComparisonPosition = getattr(comparison_module, "ComparisonPosition", None)
GameEndReason = getattr(comparison_module, "GameEndReason", None)
RepetitionOutcomeKind = getattr(comparison_module, "RepetitionOutcomeKind", None)
make_schedule = getattr(comparison_module, "make_schedule", None)
run_game = getattr(comparison_module, "run_game", None)
summarize = getattr(comparison_module, "summarize", None)
BatchStatus = getattr(comparison_module, "BatchStatus", None)


class ComparisonScheduleTests(unittest.TestCase):
    def _require_implementation(self):
        """未実装予定生成を機能不足として失敗させる。"""
        self.assertIsNotNone(ComparisonPosition, "比較局面データが未実装です")
        self.assertIsNotNone(ComparisonConfig, "比較条件データが未実装です")
        self.assertIsNotNone(make_schedule, "比較予定生成が未実装です")

    def test_schedule_exchanges_only_policy_sides_and_uses_pair_seed_formula(self):
        """8局の予定順・先後担当・方式別種を設計の算式どおりにする。

        二局目の方式先後を交換しない、qを局面内だけで採番する、または両方式に同じ
        種を割り当てる誤りを、手書きの予定値との照合で検出する。
        """
        self._require_implementation()
        initial = create_initial_position()
        gote_start = initial.copy()
        gote_start.side_to_move = Side.GOTE
        positions = (
            ComparisonPosition("initial", (), "初期局面", initial, "sfen-initial", 1),
            ComparisonPosition(
                "gote-start", ("7g7f",), "後手番", gote_start, "sfen-gote", 2
            ),
        )
        config = ComparisonConfig(
            baseline=MoveSelectionPolicy.MATERIAL,
            candidate=MoveSelectionPolicy.RANDOM,
            positions=positions,
            pairs_per_position=2,
            seed=17,
            max_plies=40,
            output_dir=Path("results"),
            positions_path=Path("positions.json"),
            positions_json=b"{}",
        )

        games = make_schedule(config)

        self.assertEqual(
            [
                (
                    game.game_id,
                    game.position_id,
                    game.pair_number,
                    game.game_number_in_pair,
                    game.baseline_side,
                    game.candidate_side,
                    game.baseline_seed,
                    game.candidate_seed,
                )
                for game in games
            ],
            [
                ("game-000001", "initial", 0, 1, Side.SENTE, Side.GOTE, 17, 18),
                ("game-000002", "initial", 0, 2, Side.GOTE, Side.SENTE, 17, 18),
                ("game-000003", "initial", 1, 1, Side.GOTE, Side.SENTE, 19, 20),
                ("game-000004", "initial", 1, 2, Side.SENTE, Side.GOTE, 19, 20),
                ("game-000005", "gote-start", 2, 1, Side.SENTE, Side.GOTE, 21, 22),
                ("game-000006", "gote-start", 2, 2, Side.GOTE, Side.SENTE, 21, 22),
                ("game-000007", "gote-start", 3, 1, Side.GOTE, Side.SENTE, 23, 24),
                ("game-000008", "gote-start", 3, 2, Side.SENTE, Side.GOTE, 23, 24),
            ],
        )

    def test_seed_list_keeps_policy_seeds_across_swapped_games(self):
        """一覧の方式別種を二局で保ち、先後だけを交換する。

        一覧順の誤り、方式別種を局ごとに割り当て直す誤り、二局目に盤面を反転する
        誤りを手書き予定との比較で検出する。
        """
        self._require_implementation()
        initial = create_initial_position()
        gote_start = initial.copy()
        gote_start.side_to_move = Side.GOTE
        positions = (
            ComparisonPosition("initial", (), "初期局面", initial, "sfen-initial", 1),
            ComparisonPosition(
                "gote-start", ("7g7f",), "後手番", gote_start, "sfen-gote", 2
            ),
        )
        seed_plan = SeedPlan(
            "pilot",
            "a" * 64,
            ("initial", "gote-start"),
            2,
            (
                PairSeeds("initial", 0, 11, 12),
                PairSeeds("initial", 1, 13, 14),
                PairSeeds("gote-start", 0, 15, 16),
                PairSeeds("gote-start", 1, 17, 18),
            ),
        )
        config = ComparisonConfig(
            baseline=MoveSelectionPolicy.MATERIAL,
            candidate=MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY,
            positions=positions,
            pairs_per_position=2,
            seed=None,
            max_plies=40,
            output_dir=Path("results"),
            positions_path=Path("positions.json"),
            positions_json=b"{}",
            seed_plan=seed_plan,
        )

        games = make_schedule(config)

        self.assertEqual(
            [(game.baseline_seed, game.candidate_seed) for game in games],
            [
                (11, 12),
                (11, 12),
                (13, 14),
                (13, 14),
                (15, 16),
                (15, 16),
                (17, 18),
                (17, 18),
            ],
        )
        self.assertEqual(
            [(game.baseline_side, game.candidate_side) for game in games],
            [
                (Side.SENTE, Side.GOTE),
                (Side.GOTE, Side.SENTE),
                (Side.GOTE, Side.SENTE),
                (Side.SENTE, Side.GOTE),
                (Side.SENTE, Side.GOTE),
                (Side.GOTE, Side.SENTE),
                (Side.GOTE, Side.SENTE),
                (Side.SENTE, Side.GOTE),
            ],
        )
        self.assertEqual(
            [game.position_id for game in games],
            ["initial"] * 4 + ["gote-start"] * 4,
        )
        self.assertIs(positions[0].start_position.side_to_move, Side.SENTE)
        self.assertIs(positions[1].start_position.side_to_move, Side.GOTE)


class ComparisonGameTests(unittest.TestCase):
    @staticmethod
    def _ordinary_position():
        """合法な玉二枚・先手飛車の通常循環用局面を作る。"""
        board = Board()
        board.set_piece(Square(9, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 1), Piece(PieceType.KING, Side.GOTE))
        board.set_piece(Square(4, 9), Piece(PieceType.ROOK, Side.SENTE))
        return Position(board, Side.SENTE)

    @staticmethod
    def _sente_check_position():
        """先手飛車の連続王手循環用局面を作る。"""
        board = Board()
        board.set_piece(Square(9, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 1), Piece(PieceType.KING, Side.GOTE))
        board.set_piece(Square(4, 9), Piece(PieceType.ROOK, Side.SENTE))
        return Position(board, Side.SENTE)

    @staticmethod
    def _gote_check_position():
        """後手飛車の連続王手循環用局面を作る。"""
        board = Board()
        board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(1, 1), Piece(PieceType.KING, Side.GOTE))
        board.set_piece(Square(6, 1), Piece(PieceType.ROOK, Side.GOTE))
        return Position(board, Side.GOTE)

    @staticmethod
    def _mate_in_one_position():
        """先手の5三飛が詰みとなる教材局面を作る。"""
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
        return Position(board, Side.SENTE)

    @staticmethod
    def _no_legal_move_position(side_to_move=Side.SENTE):
        """王手を受けていないが合法手のない制御局面を作る。"""
        board = Board()
        owner = side_to_move
        opponent = Side.GOTE if owner is Side.SENTE else Side.SENTE
        king_square = Square(1, 1) if owner is Side.SENTE else Square(9, 9)
        opponent_king_square = Square(9, 9) if owner is Side.SENTE else Square(1, 1)
        board.set_piece(king_square, Piece(PieceType.KING, owner))
        board.set_piece(opponent_king_square, Piece(PieceType.KING, opponent))
        pawns = ((2, 1), (1, 2), (2, 2))
        for file, rank in pawns:
            if owner is Side.GOTE:
                file, rank = 10 - file, 10 - rank
            board.set_piece(Square(file, rank), Piece(PieceType.PAWN, owner))
        return Position(board, side_to_move)

    def _config(self, *, max_plies=40):
        """小さな固定条件を作る。"""
        position = self._ordinary_position()
        return ComparisonConfig(
            baseline=MoveSelectionPolicy.MATERIAL,
            candidate=MoveSelectionPolicy.RANDOM,
            positions=(
                ComparisonPosition(
                    "fixture", (), "テスト局面", position, "test-sfen", 1
                ),
            ),
            pairs_per_position=1,
            seed=17,
            max_plies=max_plies,
            output_dir=Path("results"),
            positions_path=Path("positions.json"),
            positions_json=b"{}",
        )

    def _schedule(self, position=None, *, baseline_side=Side.SENTE):
        """一局の予定を作る。"""
        if position is None:
            position = self._ordinary_position()
        config = self._config()
        comparison_position = ComparisonPosition(
            "fixture", (), "テスト局面", position, "test-sfen", 1
        )
        config = ComparisonConfig(
            baseline=config.baseline,
            candidate=config.candidate,
            positions=(comparison_position,),
            pairs_per_position=1,
            seed=17,
            max_plies=config.max_plies,
            output_dir=config.output_dir,
            positions_path=config.positions_path,
            positions_json=config.positions_json,
        )
        schedule = make_schedule(config)[0]
        if baseline_side is Side.GOTE and schedule.baseline_side is Side.SENTE:
            return comparison_module.ScheduledGame(
                game_id=schedule.game_id,
                position_id=schedule.position_id,
                pair_number=schedule.pair_number,
                game_number_in_pair=schedule.game_number_in_pair,
                baseline_side=Side.GOTE,
                candidate_side=Side.SENTE,
                baseline_seed=schedule.baseline_seed,
                candidate_seed=schedule.candidate_seed,
            )
        return schedule

    def _run_scripted(self, position, tokens, *, max_plies=40, clock_ns=None):
        """USI一手列を返す固定探索で一局を実行する。"""
        config = self._config(max_plies=max_plies)
        schedule = self._schedule(position)
        moves = iter(tokens)

        def choose_move(current, candidates, policy, rng):
            del current, policy, rng
            selected = parse_usi_move(next(moves))
            if selected not in candidates:
                raise AssertionError(f"scripted move is not legal: {selected}")
            return selected

        with patch.object(
            comparison_module.game_search, "choose_move", side_effect=choose_move
        ) as chooser:
            kwargs = {} if clock_ns is None else {"clock_ns": clock_ns}
            result = run_game(
                schedule, self._comparison_position(position), config, **kwargs
            )
        return result, chooser

    @staticmethod
    def _comparison_position(position):
        return ComparisonPosition("fixture", (), "テスト局面", position, "test-sfen", 1)

    def _require_implementation(self):
        """一局実行に必要な公開APIがない場合、機能不足として失敗させる。"""
        self.assertIsNotNone(GameEndReason, "比較対局の終局理由が未実装です")
        self.assertIsNotNone(
            RepetitionOutcomeKind, "千日手判定APIを比較処理が公開していません"
        )
        self.assertIsNotNone(run_game, "比較一局の状態遷移が未実装です")

    def test_ordinary_fifth_occurrence_ends_without_winner_at_ply_limit(self):
        """4回目を継続し、局面を打開して戻った5回目を上限より優先する。"""
        self._require_implementation()
        cycle = ("4i4h", "5a6a", "4h4i", "6a5a")
        detour = (
            "9i8i",
            "5a6a",
            "8i9i",
            "6a7a",
            "9i8i",
            "7a6a",
            "8i9i",
            "6a5a",
        )

        result, chooser = self._run_scripted(
            self._ordinary_position(), cycle * 3 + detour, max_plies=19
        )

        self.assertEqual(result.reason, GameEndReason.REPETITION)
        self.assertIsNone(result.winner_side)
        self.assertIsNone(result.winner_policy)
        self.assertEqual(result.plies, 19)
        self.assertEqual(len(result.record.moves), 19)
        self.assertEqual(chooser.call_count, 19)

    def test_each_game_starts_with_a_fresh_repetition_history(self):
        """前局の反復履歴を次局へ持ち越さず4回目を継続扱いにする。"""
        self._require_implementation()
        cycle = ("4i4h", "5a6a", "4h4i", "6a5a")

        first, _ = self._run_scripted(
            self._ordinary_position(), cycle * 3, max_plies=12
        )
        second, _ = self._run_scripted(
            self._ordinary_position(), cycle * 3, max_plies=12
        )

        self.assertEqual(first.reason, GameEndReason.PLY_LIMIT)
        self.assertEqual(second.reason, GameEndReason.PLY_LIMIT)
        self.assertEqual(first.plies, 12)
        self.assertEqual(second.plies, 12)

    def test_fourfold_continues_and_latest_four_occurrences_classify_fifth(self):
        """4回目の通常出現後も続け、5回目の最新区間を連続王手負けにする。"""
        self._require_implementation()
        ordinary_cycle = ("4i4h", "5a6a", "4h4i", "6a5a")
        checking_cycle = ("4i5i", "5a4a", "5i4i", "4a5a")

        result, chooser = self._run_scripted(
            self._sente_check_position(),
            ordinary_cycle + checking_cycle * 3,
            max_plies=16,
        )

        self.assertEqual(result.reason, GameEndReason.PERPETUAL_CHECK_LOSS)
        self.assertEqual(result.winner_side, Side.GOTE)
        self.assertEqual(result.winner_policy, MoveSelectionPolicy.RANDOM)
        self.assertEqual(result.plies, 16)
        self.assertEqual(chooser.call_count, 16)

    def test_gote_perpetual_check_loses_and_sente_policy_wins(self):
        """後手の連続王手負けを手番固定せず、先手側の方式勝ちへ写す。"""
        self._require_implementation()
        cycle = ("6a5a", "5i6i", "5a6a", "6i5i")

        result, _ = self._run_scripted(
            self._gote_check_position(), cycle * 3, max_plies=12
        )

        self.assertEqual(result.reason, GameEndReason.PERPETUAL_CHECK_LOSS)
        self.assertEqual(result.winner_side, Side.SENTE)
        self.assertEqual(result.winner_policy, MoveSelectionPolicy.MATERIAL)
        self.assertEqual(result.plies, 12)

    def test_unresolved_double_perpetual_check_has_no_winner_or_repetition_count(self):
        """双方連続王手の未裁定を勝者・通常千日手へ変換しない。"""
        self._require_implementation()

        class UnresolvedTracker:
            def __init__(self, initial_position):
                del initial_position
                self._outcome = RepetitionOutcome(
                    kind=RepetitionOutcomeKind.CONTINUE, losing_side=None
                )

            @property
            def current_outcome(self):
                return self._outcome

            def add_position(self, position):
                del position
                self._outcome = RepetitionOutcome(
                    kind=RepetitionOutcomeKind.UNRESOLVED_DOUBLE_PERPETUAL_CHECK,
                    losing_side=None,
                )
                return self._outcome

        with patch.object(comparison_module, "RepetitionTracker", UnresolvedTracker):
            result, chooser = self._run_scripted(
                self._ordinary_position(), ("4i4h",), max_plies=1
            )

        self.assertEqual(result.reason, GameEndReason.UNRESOLVED_DOUBLE_PERPETUAL_CHECK)
        self.assertIsNone(result.winner_side)
        self.assertIsNone(result.winner_policy)
        self.assertEqual(result.plies, 1)
        self.assertEqual(chooser.call_count, 1)

    def test_checkmate_after_last_allowed_move_precedes_ply_limit(self):
        """上限手数で詰ませた場合は未決着上限より詰みを優先する。"""
        self._require_implementation()
        result, chooser = self._run_scripted(
            self._mate_in_one_position(), ("5c5b",), max_plies=1
        )

        self.assertEqual(result.reason, GameEndReason.CHECKMATE)
        self.assertEqual(result.winner_side, Side.SENTE)
        self.assertEqual(result.winner_policy, MoveSelectionPolicy.MATERIAL)
        self.assertEqual(result.plies, 1)
        self.assertEqual(chooser.call_count, 1)

    def test_no_legal_move_without_check_awards_other_side(self):
        """王手でない手なしを詰みと混同せず、先後反転した勝者を返す。"""
        self._require_implementation()
        position = self._no_legal_move_position(Side.GOTE)
        self.assertEqual(legal_moves(position), ())

        config = self._config(max_plies=1)
        result = run_game(
            self._schedule(position, baseline_side=Side.GOTE),
            self._comparison_position(position),
            config,
        )

        self.assertEqual(result.reason, GameEndReason.NO_LEGAL_MOVE)
        self.assertEqual(result.winner_side, Side.SENTE)
        self.assertEqual(result.winner_policy, MoveSelectionPolicy.RANDOM)
        self.assertEqual(result.plies, 0)
        self.assertEqual(result.record.moves, ())

    def test_ply_limit_ends_nonterminal_game_without_winner(self):
        """合法な未終局局面の上限到達を勝敗や千日手へ変換しない。"""
        self._require_implementation()
        result, chooser = self._run_scripted(
            self._ordinary_position(), ("4i4h",), max_plies=1
        )

        self.assertEqual(result.reason, GameEndReason.PLY_LIMIT)
        self.assertIsNone(result.winner_side)
        self.assertIsNone(result.winner_policy)
        self.assertEqual(result.plies, 1)
        self.assertEqual(chooser.call_count, 1)

    def test_failed_selection_does_not_record_or_count_unconfirmed_move(self):
        """探索のNone・候補外・例外では未確定手を棋譜と手数へ加えない。"""
        self._require_implementation()
        for mode in ("none", "illegal", "raise"):
            with self.subTest(mode=mode):
                config = self._config(max_plies=1)
                position = self._ordinary_position()
                schedule = self._schedule(position)

                def fail_selection(
                    current, candidates, policy, rng, *, selected_mode=mode
                ):
                    del current, policy, rng
                    if selected_mode == "none":
                        return None
                    if selected_mode == "illegal":
                        return parse_usi_move("1a1b")
                    raise RuntimeError("scripted search failure")

                with patch.object(
                    comparison_module.game_search,
                    "choose_move",
                    side_effect=fail_selection,
                ):
                    result = run_game(
                        schedule, self._comparison_position(position), config
                    )

                self.assertEqual(result.reason, GameEndReason.ERROR)
                self.assertIsNone(result.winner_side)
                self.assertEqual(result.plies, 0)
                self.assertEqual(result.record.moves, ())
                self.assertEqual(result.move_times_ns, ())

    def test_failed_move_application_does_not_commit_record_or_repetition(self):
        """適用失敗時は選択済み手を棋譜・反復・成功手数へ確定しない。"""
        self._require_implementation()
        position = self._ordinary_position()
        with patch.object(
            comparison_module.RepetitionTracker, "add_position"
        ) as add_position:
            with patch.object(
                comparison_module.game_search,
                "choose_move",
                return_value=parse_usi_move("4i4h"),
            ):
                with patch.object(
                    comparison_module.GameRecord,
                    "apply_move",
                    side_effect=ValueError("scripted apply failure"),
                ):
                    result = run_game(
                        self._schedule(position),
                        self._comparison_position(position),
                        self._config(max_plies=1),
                    )

        add_position.assert_not_called()
        self.assertEqual(result.reason, GameEndReason.ERROR)
        self.assertEqual(result.error, "ValueError: scripted apply failure")
        self.assertIsNone(result.winner_side)
        self.assertEqual(result.plies, 0)
        self.assertEqual(result.record.moves, ())
        self.assertEqual(result.move_times_ns, ())
        self.assertIsNotNone(result.unfinished_calculation_ns)

    def test_move_timing_stops_when_choice_returns_before_applying_move(self):
        """一手計時は合法手生成前から探索返却までに限り、適用処理を含めない。"""
        self._require_implementation()
        now = [0]

        def clock_ns():
            return now[0]

        def choose_and_advance(current, candidates, policy, rng):
            del current, policy, rng
            now[0] += 10
            return parse_usi_move("4i4h")

        original_apply = comparison_module.GameRecord.apply_move

        def apply_and_advance(record, source, destination, *, promote=False):
            original_apply(record, source, destination, promote=promote)
            now[0] += 1000

        with patch.object(
            comparison_module.game_search,
            "choose_move",
            side_effect=choose_and_advance,
        ):
            with patch.object(
                comparison_module.GameRecord,
                "apply_move",
                apply_and_advance,
            ):
                result = run_game(
                    self._schedule(),
                    self._comparison_position(self._ordinary_position()),
                    self._config(max_plies=1),
                    clock_ns=clock_ns,
                )

        self.assertEqual(len(result.move_times_ns), 1)
        self.assertEqual(result.move_times_ns[0].elapsed_ns, 10)

    def test_clock_reversal_is_an_error_without_committing_move(self):
        """単調時計の逆行を時間異常として扱い、選択手を未確定のままにする。"""
        self._require_implementation()
        readings = iter((10, 0))

        with patch.object(
            comparison_module.game_search,
            "choose_move",
            return_value=parse_usi_move("4i4h"),
        ):
            result = run_game(
                self._schedule(),
                self._comparison_position(self._ordinary_position()),
                self._config(max_plies=1),
                clock_ns=lambda: next(readings),
            )

        self.assertEqual(result.reason, GameEndReason.ERROR)
        self.assertEqual(result.plies, 0)
        self.assertEqual(result.record.moves, ())
        self.assertEqual(result.move_times_ns, ())
        self.assertEqual(result.unfinished_calculation_ns, -10)

    def test_each_policy_gets_reproducible_independent_rng_per_game(self):
        """方式専用種を局ごとに再初期化し相手の消費から独立させる。"""
        self._require_implementation()
        observed = []

        def choose_and_observe(current, candidates, policy, rng):
            del current, policy
            observed.append((rng, rng.random()))
            return candidates[0]

        for _ in range(2):
            with patch.object(
                comparison_module.game_search,
                "choose_move",
                side_effect=choose_and_observe,
            ):
                result = run_game(
                    self._schedule(),
                    self._comparison_position(self._ordinary_position()),
                    self._config(max_plies=2),
                )
            self.assertEqual(result.reason, GameEndReason.PLY_LIMIT)

        expected_by_seed = {
            17: random.Random(17).random(),
            18: random.Random(18).random(),
        }
        self.assertEqual(
            [value for _, value in observed],
            [
                expected_by_seed[17],
                expected_by_seed[18],
                expected_by_seed[17],
                expected_by_seed[18],
            ],
        )
        self.assertIsNot(observed[0][0], observed[1][0])
        self.assertIsNot(observed[2][0], observed[3][0])
        self.assertIsNot(observed[0][0], observed[2][0])


class ComparisonSummaryTests(unittest.TestCase):
    def _require_implementation(self):
        """集計APIの不足を振る舞いテストの失敗として確認する。"""
        self.assertIsNotNone(BatchStatus, "バッチ状態が未実装です")
        self.assertIsNotNone(summarize, "比較結果の記述集計が未実装です")

    @staticmethod
    def _config_and_schedule():
        """二局面・四組の集計入力条件を作る。"""
        initial = create_initial_position()
        record = GameRecord(initial)
        record.apply_move(Square(7, 7), Square(7, 6))
        positions = (
            ComparisonPosition("initial", (), "平手", initial, "sfen-initial", 1),
            ComparisonPosition(
                "opened",
                ("7g7f",),
                "歩を進めた後",
                record.current_position,
                "sfen-opened",
                2,
            ),
        )
        config = ComparisonConfig(
            baseline=MoveSelectionPolicy.MATERIAL,
            candidate=MoveSelectionPolicy.RANDOM,
            positions=positions,
            pairs_per_position=2,
            seed=17,
            max_plies=20,
            output_dir=Path("results"),
            positions_path=Path("positions.json"),
            positions_json=b"{}",
        )
        return config, make_schedule(config)

    @staticmethod
    def _result(config, schedule, reason, *, winner_side=None, elapsed=()):
        """指定した成功手数を棋譜と計時に反映した集計用結果を作る。"""
        position = next(
            item
            for item in config.positions
            if item.position_id == schedule.position_id
        )
        record = GameRecord(position.start_position)
        move_times = []
        tokens = (
            ("7g7f", "3c3d", "2g2f")
            if schedule.position_id == "initial"
            else ("3c3d", "2g2f", "8c8d")
        )
        for ply, elapsed_ns in enumerate(elapsed, start=1):
            current = record.current_position
            side = current.side_to_move
            policy = (
                config.baseline if side is schedule.baseline_side else config.candidate
            )
            move = parse_usi_move(tokens[ply - 1])
            record.apply_move(move.source, move.destination, promote=move.promote)
            move_times.append(MoveTiming(ply, side, policy, move, elapsed_ns))
        winner_policy = None
        if winner_side is not None:
            winner_policy = (
                config.baseline
                if winner_side is schedule.baseline_side
                else config.candidate
            )
        return GameResult(
            schedule=schedule,
            start_sfen=position.start_sfen,
            initial_move_number=position.initial_move_number,
            record=record,
            reason=reason,
            winner_side=winner_side,
            winner_policy=winner_policy,
            plies=len(record.moves),
            move_times_ns=tuple(move_times),
            unfinished_calculation_ns=None,
            error="fixture error" if reason is GameEndReason.ERROR else None,
        )

    def test_summary_counts_are_exclusive_and_reconcile_by_position_side_and_policy(
        self,
    ):
        """排他的結果件数・先後内訳・方式別計時を手計算と照合する。

        開始局と未実行局の恒等式を崩す、未裁定を通常千日手へ加算する、連続王手の
        内訳を終局理由へ二重加算する、方式別平均を全体平均で置き換える誤りを検出する。
        """
        self._require_implementation()
        config, schedule = self._config_and_schedule()
        results = (
            self._result(
                config,
                schedule[0],
                GameEndReason.PERPETUAL_CHECK_LOSS,
                winner_side=Side.GOTE,
                elapsed=(10, 30),
            ),
            self._result(config, schedule[1], GameEndReason.REPETITION),
            self._result(
                config,
                schedule[2],
                GameEndReason.UNRESOLVED_DOUBLE_PERPETUAL_CHECK,
                elapsed=(20,),
            ),
            self._result(
                config,
                schedule[3],
                GameEndReason.CHECKMATE,
                winner_side=Side.SENTE,
                elapsed=(40, 50),
            ),
            self._result(
                config,
                schedule[4],
                GameEndReason.PLY_LIMIT,
                elapsed=(60,),
            ),
            self._result(
                config,
                schedule[5],
                GameEndReason.NO_LEGAL_MOVE,
                winner_side=Side.GOTE,
            ),
            self._result(config, schedule[6], GameEndReason.ERROR),
        )

        payload = summarize(
            config,
            results,
            batch_status=BatchStatus.ERROR,
            unstarted_games=1,
            elapsed_ns=987654,
        )

        self.assertEqual(
            set(payload),
            {
                "status",
                "planned_games",
                "started_games",
                "ended_games",
                "unstarted_games",
                "completed_pairs",
                "partial_pairs",
                "results",
                "perpetual_check_losses",
                "by_position",
                "by_side",
                "move_time_by_policy",
                "elapsed_ns",
                "statistical_decision",
            },
        )
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["planned_games"], 8)
        self.assertEqual(payload["started_games"], 7)
        self.assertEqual(payload["ended_games"], 7)
        self.assertEqual(payload["unstarted_games"], 1)
        self.assertEqual(payload["completed_pairs"], 3)
        self.assertEqual(payload["partial_pairs"], 1)
        self.assertEqual(
            payload["results"],
            {
                "checkmate": 1,
                "no_legal_move": 1,
                "perpetual_check_loss": 1,
                "repetition": 1,
                "unresolved_double_perpetual_check": 1,
                "ply_limit": 1,
                "interrupted": 0,
                "error": 1,
            },
        )
        self.assertEqual(sum(payload["results"].values()), payload["started_games"])
        self.assertEqual(payload["perpetual_check_losses"], {"sente": 1, "gote": 0})
        self.assertEqual(
            payload["by_position"],
            {
                "initial": {
                    "started_games": 4,
                    "results": {
                        "checkmate": 1,
                        "no_legal_move": 0,
                        "perpetual_check_loss": 1,
                        "repetition": 1,
                        "unresolved_double_perpetual_check": 1,
                        "ply_limit": 0,
                        "interrupted": 0,
                        "error": 0,
                    },
                },
                "opened": {
                    "started_games": 3,
                    "results": {
                        "checkmate": 0,
                        "no_legal_move": 1,
                        "perpetual_check_loss": 0,
                        "repetition": 0,
                        "unresolved_double_perpetual_check": 0,
                        "ply_limit": 1,
                        "interrupted": 0,
                        "error": 1,
                    },
                },
            },
        )
        self.assertEqual(
            payload["by_side"],
            {
                "sente": {"games": 7, "wins": 1, "losses": 2, "no_winner": 4},
                "gote": {"games": 7, "wins": 2, "losses": 1, "no_winner": 4},
            },
        )
        self.assertEqual(
            payload["move_time_by_policy"]["material"],
            {"successful_moves": 2, "total_ns": 50, "average_ns": 25, "max_ns": 40},
        )
        self.assertEqual(
            payload["move_time_by_policy"]["random"],
            {"successful_moves": 4, "total_ns": 160, "average_ns": 40, "max_ns": 60},
        )
        self.assertEqual(
            payload["move_time_by_policy"]["two-ply-material"],
            {"successful_moves": 0, "total_ns": 0, "average_ns": None, "max_ns": None},
        )
        self.assertEqual(payload["elapsed_ns"], 987654)
        self.assertIsNone(payload["statistical_decision"])

    def test_parallel_summary_separates_saved_in_flight_and_unstarted_games(self):
        """並列summaryで保存済み・投入中・未投入を別々に数える。

        投入中を未開始へ加算したり、保存済みと二重計上して予定8局の恒等式を崩す誤りを
        検出する。件数は棋譜再集計に依存しない独立期待値で固定する。
        """
        self._require_implementation()
        config, schedule = self._config_and_schedule()
        config = replace(config, workers=4)
        results = tuple(
            self._result(config, game, GameEndReason.PLY_LIMIT) for game in schedule[:2]
        )

        try:
            payload = summarize(
                config,
                results,
                batch_status=BatchStatus.RUNNING,
                unstarted_games=3,
                in_flight_games=3,
                elapsed_ns=123,
            )
        except ValueError as error:
            self.fail(f"投入中の3局を件数へ反映できません: {error}")

        self.assertEqual(payload["planned_games"], 8)
        self.assertEqual(payload["started_games"], 5)
        self.assertEqual(payload["ended_games"], 2)
        self.assertEqual(payload["in_flight_games"], 3)
        self.assertEqual(payload["unstarted_games"], 3)
        self.assertEqual(
            payload["started_games"] + payload["unstarted_games"],
            payload["planned_games"],
        )
        self.assertEqual(sum(payload["results"].values()), payload["ended_games"])
        self.assertEqual(
            payload["ended_games"]
            + payload["in_flight_games"]
            + payload["unstarted_games"],
            payload["planned_games"],
        )

    def test_parallel_summary_rejects_invalid_in_flight_counts(self):
        """投入中件数の負値・bool・予定との不一致を拒否する。

        Pythonでboolが整数として混入すること、また件数の誤りを不整合として扱わず
        完了状態へ保存することを検出する。
        """
        self._require_implementation()
        config, schedule = self._config_and_schedule()
        config = replace(config, workers=4)
        results = tuple(
            self._result(config, game, GameEndReason.PLY_LIMIT) for game in schedule[:2]
        )
        invalid_counts = ((-1, 7), (True, 5), (3, 4))

        for in_flight, unstarted in invalid_counts:
            with self.subTest(in_flight=in_flight, unstarted=unstarted):
                with self.assertRaises(ValueError):
                    summarize(
                        config,
                        results,
                        batch_status=BatchStatus.RUNNING,
                        unstarted_games=unstarted,
                        in_flight_games=in_flight,
                        elapsed_ns=1,
                    )

    def test_completed_parallel_summary_records_zero_in_flight_games(self):
        """並列実験が終わったsummary v2で投入中0を明示する。

        完了後に投入中フィールドを省いてsummary v1へ戻し、conditions v3と対になる
        完了形式を曖昧にする誤りを検出する。
        """
        self._require_implementation()
        config, schedule = self._config_and_schedule()
        config = replace(config, workers=4)
        results = tuple(
            self._result(config, game, GameEndReason.PLY_LIMIT) for game in schedule
        )

        payload = summarize(
            config,
            results,
            batch_status=BatchStatus.COMPLETE,
            unstarted_games=0,
            in_flight_games=0,
            elapsed_ns=456,
        )

        self.assertEqual(payload["started_games"], 8)
        self.assertEqual(payload["ended_games"], 8)
        self.assertEqual(payload.get("in_flight_games"), 0)
        self.assertEqual(payload["unstarted_games"], 0)

    def test_summary_adds_b1_timing_only_when_b1_is_part_of_the_comparison(self):
        """旧集計は五方式を保ち、B1実験だけにB1計時欄を追加する。

        enumへ方式を追加した影響で旧実験の出力キーが変わる、またはB1実験の計時欄が
        欠ける誤りを、未開始の固定予定に対する集計キーの独立期待値で検出する。
        """
        self._require_implementation()
        config, schedule = self._config_and_schedule()

        def empty_summary(current_config):
            """局を開始せず予定分を未開始として集計する。"""
            try:
                return summarize(
                    current_config,
                    (),
                    batch_status=BatchStatus.INTERRUPTED,
                    unstarted_games=len(make_schedule(current_config)),
                    elapsed_ns=0,
                )
            except KeyError as error:
                self.fail(f"方式名が集計へ登録されていません: {error}")

        old_summary = empty_summary(config)
        self.assertEqual(
            set(old_summary["move_time_by_policy"]),
            {
                "random",
                "material",
                "two-ply-material",
                "full-width-4",
                "alpha-beta-4",
            },
        )

        b1_config = replace(config, baseline=MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY)
        b1_summary = empty_summary(b1_config)
        self.assertEqual(
            set(b1_summary["move_time_by_policy"]),
            {
                "random",
                "material",
                "two-ply-material",
                "full-width-4",
                "alpha-beta-4",
                "material-rook-mobility",
            },
        )

    def test_summary_rejects_missing_or_duplicate_started_games(self):
        """開始局数・未実行数と予定件数の不整合を拒否する。

        集計入力が欠落または同じ局を二重計上したのに完了組数や結果件数を確定する
        誤りを検出する。
        """
        self._require_implementation()
        config, schedule = self._config_and_schedule()
        one_result = self._result(config, schedule[0], GameEndReason.REPETITION)

        with self.assertRaises(ValueError):
            summarize(
                config,
                (one_result,),
                batch_status=BatchStatus.COMPLETE,
                unstarted_games=0,
                elapsed_ns=1,
            )
        with self.assertRaises(ValueError):
            summarize(
                config,
                (one_result, one_result),
                batch_status=BatchStatus.ERROR,
                unstarted_games=6,
                elapsed_ns=1,
            )


if __name__ == "__main__":
    unittest.main()
