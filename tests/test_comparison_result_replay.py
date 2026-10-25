"""比較保存棋譜の合法再生と終局境界を確認する。"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from kaname_shogi import comparison_io, comparison_result_io
from kaname_shogi.comparison import (
    ComparisonConfig,
    ComparisonPosition,
    GameEndReason,
    ScheduledGame,
)
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
from kaname_shogi.move import BoardMove, DropMove
from kaname_shogi.movegen import MoveSelectionPolicy
from kaname_shogi.sfen import SfenPosition, format_sfen
from kaname_shogi.usi_move import parse_usi_move

_CONDITIONS_SHA256 = "a" * 64


def _side_name(side: Side) -> str:
    """先後値を比較成果物の小文字名にする。"""
    return "sente" if side is Side.SENTE else "gote"


def _opposite(side: Side) -> Side:
    """先後を反転する。"""
    return Side.GOTE if side is Side.SENTE else Side.SENTE


def _policy_name(policy: MoveSelectionPolicy) -> str:
    """比較fixtureで使う二方式の成果物名を返す。"""
    return (
        "material"
        if policy is MoveSelectionPolicy.MATERIAL
        else "material-rook-mobility"
    )


def _replay_case(
    moves: tuple[str, ...],
    *,
    max_plies: int,
    reason: GameEndReason,
    position: Position | None = None,
    winner_side: Side | None = None,
    candidate_side: Side = Side.GOTE,
) -> tuple[dict[str, object], ScheduledGame, ComparisonConfig]:
    """readerへ渡す小さな局payload、予定、条件を合法操作から作る。

    棋譜手は既存の合法適用を通して作り、計時・方式は手番ごとに独立して構成する。
    比較writerや得点関数から期待値を逆算しない。
    """
    start_position = position or create_initial_position()
    start_sfen = format_sfen(SfenPosition(start_position, 1))
    comparison_position = ComparisonPosition(
        "fixture",
        (),
        "reader契約用fixture",
        start_position,
        start_sfen,
        1,
    )
    config = ComparisonConfig(
        baseline=MoveSelectionPolicy.MATERIAL,
        candidate=MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY,
        positions=(comparison_position,),
        pairs_per_position=1,
        seed=17,
        max_plies=max_plies,
        output_dir=Path("unused-output"),
        positions_path=Path("unused-positions.json"),
        positions_json=b"{}",
    )
    schedule = ScheduledGame(
        game_id="game-000001",
        position_id="fixture",
        pair_number=0,
        game_number_in_pair=1,
        baseline_side=_opposite(candidate_side),
        candidate_side=candidate_side,
        baseline_seed=11,
        candidate_seed=12,
    )
    record = GameRecord(start_position)
    move_times: list[dict[str, object]] = []
    for ply, token in enumerate(moves, start=1):
        move = parse_usi_move(token)
        side = record.current_position.side_to_move
        policy = config.baseline if side is schedule.baseline_side else config.candidate
        if isinstance(move, BoardMove):
            record.apply_move(move.source, move.destination, promote=move.promote)
        else:
            assert isinstance(move, DropMove)
            record.apply_drop(move.piece_type, move.destination)
        move_times.append(
            {
                "ply": ply,
                "side": _side_name(side),
                "policy": _policy_name(policy),
                "move": token,
                "elapsed_ns": 11 * ply,
            }
        )

    winner_policy = None
    if winner_side is not None:
        winner_policy = (
            config.baseline
            if winner_side is schedule.baseline_side
            else config.candidate
        )
    payload: dict[str, object] = {
        "format": "kaname-shogi-comparison-game-v1",
        "conditions_sha256": _CONDITIONS_SHA256,
        **comparison_io._scheduled_game_payload(schedule),
        "baseline": _policy_name(config.baseline),
        "candidate": _policy_name(config.candidate),
        "start_sfen": start_sfen,
        "initial_move_number": 1,
        "plies": len(record.moves),
        "reason": reason.value,
        "winner_side": None if winner_side is None else _side_name(winner_side),
        "winner_policy": (
            None if winner_policy is None else _policy_name(winner_policy)
        ),
        "record": record.to_payload(),
        "move_times": move_times,
        "unfinished_calculation": None,
        "error": "fixture error" if reason is GameEndReason.ERROR else None,
    }
    return payload, schedule, config


def _position(
    pieces: tuple[tuple[PieceType, Side, int, int], ...], side_to_move: Side
) -> Position:
    """最小詰み・合法手なしfixture用の盤面を作る。"""
    board = Board()
    for piece_type, side, file, rank in pieces:
        board.set_piece(Square(file, rank), Piece(piece_type, side))
    return Position(board, side_to_move)


def _reflect_position(position: Position) -> Position:
    """盤面を180度回し、先後と手番を交換する。"""
    reflected = Board()
    for file in range(1, 10):
        for rank in range(1, 10):
            piece = position.board.piece_at(Square(file, rank))
            if piece is not None:
                reflected.set_piece(
                    Square(10 - file, 10 - rank),
                    Piece(piece.piece_type, _opposite(piece.side)),
                )
    return Position(reflected, _opposite(position.side_to_move))


def _mate_position() -> Position:
    """飛車と金で一手詰みにできる、既存readerテスト由来の局面。"""
    return _position(
        (
            (PieceType.KING, Side.GOTE, 5, 1),
            (PieceType.KING, Side.SENTE, 9, 9),
            (PieceType.ROOK, Side.SENTE, 5, 3),
            (PieceType.GOLD, Side.SENTE, 4, 3),
            (PieceType.PAWN, Side.GOTE, 4, 1),
            (PieceType.PAWN, Side.GOTE, 6, 1),
            (PieceType.PAWN, Side.GOTE, 4, 2),
            (PieceType.PAWN, Side.GOTE, 6, 2),
        ),
        Side.SENTE,
    )


def _no_legal_move_position() -> Position:
    """非王手で後手の一手後に先手玉が自駒で動けない局面。"""
    return _position(
        (
            (PieceType.KING, Side.SENTE, 1, 1),
            (PieceType.PAWN, Side.SENTE, 2, 1),
            (PieceType.PAWN, Side.SENTE, 1, 2),
            (PieceType.PAWN, Side.SENTE, 2, 2),
            (PieceType.KING, Side.GOTE, 9, 8),
        ),
        Side.GOTE,
    )


class ComparisonResultReplayTests(unittest.TestCase):
    """保存棋譜読込が守る合法性と終局境界を検証する。"""

    def test_rejects_illegal_intermediate_recorded_move_or_drop(self):
        """違法な中間手と持ち駒なしの打ち手を保存棋譜として拒否する。

        次の記録手があることだけで局面の合法手存在を証明できると誤認し、
        合法再生を省略した中間手を分析へ通す誤りを検出する。
        """
        for invalid_token in ("3c3e", "P*5e"):
            with self.subTest(invalid_token=invalid_token):
                payload, schedule, config = _replay_case(
                    ("7g7f", "3c3d", "2g2f"),
                    max_plies=4,
                    reason=GameEndReason.INTERRUPTED,
                )
                corrupted = copy.deepcopy(payload)
                record_moves = corrupted["record"]["moves"]
                timing = corrupted["move_times"][1]
                if invalid_token == "3c3e":
                    record_moves[1]["destination"]["rank"] = 5
                else:
                    record_moves[1] = {
                        "kind": "drop",
                        "piece_type": "PAWN",
                        "destination": {"file": 5, "rank": 5},
                    }
                timing["move"] = invalid_token

                with self.assertRaises(ValueError):
                    comparison_result_io._load_game(
                        corrupted,
                        schedule,
                        config,
                        conditions_sha256=_CONDITIONS_SHA256,
                        allow_incomplete=True,
                    )

    def test_rejects_legal_continuation_after_ply_limit(self):
        """上限到達後に続けた合法棋譜を拒否する。

        各手が合法でも、二手上限の後に三手目を記録した局を完了局と誤集計する
        取り違えを検出する。
        """
        payload, schedule, config = _replay_case(
            ("7g7f", "3c3d", "2g2f"),
            max_plies=2,
            reason=GameEndReason.PLY_LIMIT,
        )
        with self.assertRaisesRegex(ValueError, "既終局後"):
            comparison_result_io._load_game(
                payload, schedule, config, conditions_sha256=_CONDITIONS_SHA256
            )

    def test_uses_validated_next_move_and_enumerates_only_final_position(self):
        """中間局面は検証済み次手を根拠にし、末尾だけ合法手を列挙する。

        合法棋譜を再生しながら各中間局面でも全合法手一覧を作る余分な処理を検出する。
        末尾の全列挙結果・終局・成功手計時はそのまま保持する。
        """
        payload, schedule, config = _replay_case(
            ("7g7f", "3c3d", "2g2f"),
            max_plies=3,
            reason=GameEndReason.PLY_LIMIT,
        )
        real_legal_moves = comparison_result_io.legal_moves
        with patch.object(
            comparison_result_io,
            "legal_moves",
            wraps=real_legal_moves,
        ) as legal_moves_spy:
            try:
                result = comparison_result_io._load_game(
                    payload,
                    schedule,
                    config,
                    conditions_sha256=_CONDITIONS_SHA256,
                )
            except ValueError as error:
                self.fail(f"有効な保存棋譜がreaderに拒否されました: {error}")

        self.assertEqual(legal_moves_spy.call_count, 1)
        self.assertIs(result.reason, GameEndReason.PLY_LIMIT)
        self.assertEqual(result.plies, 3)
        self.assertEqual(
            tuple(timing.elapsed_ns for timing in result.move_times_ns), (11, 22, 33)
        )
        final_position = legal_moves_spy.call_args.args[0]
        self.assertIs(final_position.side_to_move, Side.GOTE)
        for square in (Square(7, 7), Square(2, 7), Square(3, 3)):
            self.assertIsNone(final_position.board.piece_at(square))
        self.assertEqual(
            final_position.board.piece_at(Square(7, 6)),
            Piece(PieceType.PAWN, Side.SENTE),
        )
        self.assertEqual(
            final_position.board.piece_at(Square(2, 6)),
            Piece(PieceType.PAWN, Side.SENTE),
        )
        self.assertEqual(
            final_position.board.piece_at(Square(3, 4)),
            Piece(PieceType.PAWN, Side.GOTE),
        )

    def test_repeated_terminal_skips_direct_legal_enumeration(self):
        """反復終局になった末尾では盤面用の合法手列挙を呼ばない。

        千日手を盤面終局より先に決めるreaderが、終局理由を変えないためだけの
        合法手全列挙まで実行する余分な処理を検出する。
        """
        cycle = ("5i5h", "5a5b", "5h5i", "5b5a")
        payload, schedule, config = _replay_case(
            cycle * 4,
            max_plies=20,
            reason=GameEndReason.REPETITION,
        )
        real_legal_moves = comparison_result_io.legal_moves
        with patch.object(
            comparison_result_io,
            "legal_moves",
            wraps=real_legal_moves,
        ) as legal_moves_spy:
            try:
                result = comparison_result_io._load_game(
                    payload,
                    schedule,
                    config,
                    conditions_sha256=_CONDITIONS_SHA256,
                )
            except ValueError as error:
                self.fail(f"末尾の反復終局が保存棋譜から再現されません: {error}")

        self.assertEqual(legal_moves_spy.call_count, 0)
        self.assertIs(result.reason, GameEndReason.REPETITION)
        self.assertIsNone(result.winner_side)

    def test_preserves_final_mate_or_no_move_before_ply_limit_for_both_sides(self):
        """上限と同時の詰み・合法手なしを先後反転して優先する。

        最終手後の合法手存在を固定でTrueにすると、勝敗終局を上限未決着へ変える
        誤りを検出する。勝者の先後と方式対応も独立期待値で確認する。
        """
        mate = _mate_position()
        no_move = _no_legal_move_position()
        cases = (
            (
                mate,
                "5c5b",
                GameEndReason.CHECKMATE,
                Side.SENTE,
                Side.GOTE,
            ),
            (
                _reflect_position(mate),
                "5g5h",
                GameEndReason.CHECKMATE,
                Side.GOTE,
                Side.GOTE,
            ),
            (
                no_move,
                "9h9i",
                GameEndReason.NO_LEGAL_MOVE,
                Side.GOTE,
                Side.SENTE,
            ),
            (
                _reflect_position(no_move),
                "1b1a",
                GameEndReason.NO_LEGAL_MOVE,
                Side.SENTE,
                Side.SENTE,
            ),
        )
        for position, token, reason, winner, candidate_side in cases:
            with self.subTest(reason=reason.value, winner=winner.value):
                payload, schedule, config = _replay_case(
                    (token,),
                    max_plies=1,
                    reason=reason,
                    position=position,
                    winner_side=winner,
                    candidate_side=candidate_side,
                )
                try:
                    result = comparison_result_io._load_game(
                        payload,
                        schedule,
                        config,
                        conditions_sha256=_CONDITIONS_SHA256,
                    )
                except ValueError as error:
                    self.fail(f"終局fixtureがreaderに拒否されました: {error}")

                expected_policy = (
                    config.candidate
                    if winner is schedule.candidate_side
                    else config.baseline
                )
                self.assertEqual(result.reason, reason)
                self.assertEqual(result.winner_side, winner)
                self.assertIs(result.winner_policy, expected_policy)

    def test_preserves_incomplete_record_boundaries(self):
        """0手・複数手の中断と故障を未完了として保持する。

        allow_incompleteによる再開読込が未完了局を完成局へ昇格させたり、合法手を
        省いたために保存済み複数手局を一律拒否したりする誤りを検出する。
        """
        for reason in (GameEndReason.INTERRUPTED, GameEndReason.ERROR):
            for moves in ((), ("7g7f",), ("7g7f", "3c3d", "2g2f")):
                with self.subTest(reason=reason.value, plies=len(moves)):
                    payload, schedule, config = _replay_case(
                        moves,
                        max_plies=4,
                        reason=reason,
                    )
                    result = comparison_result_io._load_game(
                        payload,
                        schedule,
                        config,
                        conditions_sha256=_CONDITIONS_SHA256,
                        allow_incomplete=True,
                    )
                    self.assertIs(result.reason, reason)
                    self.assertEqual(result.plies, len(moves))
                    self.assertIsNone(result.winner_side)
                    self.assertIsNone(result.winner_policy)
                    with self.assertRaises(ValueError):
                        comparison_result_io._load_game(
                            payload,
                            schedule,
                            config,
                            conditions_sha256=_CONDITIONS_SHA256,
                            allow_incomplete=False,
                        )

        for reason in (GameEndReason.INTERRUPTED, GameEndReason.ERROR):
            payload, schedule, config = _replay_case(
                ("7g7f", "3c3d", "2g2f"),
                max_plies=3,
                reason=reason,
            )
            result = comparison_result_io._load_game(
                payload,
                schedule,
                config,
                conditions_sha256=_CONDITIONS_SHA256,
                allow_incomplete=True,
            )
            self.assertIs(result.reason, reason)
            self.assertEqual(result.plies, 3)
            self.assertIsNone(result.winner_side)

        payload, schedule, config = _replay_case(
            (), max_plies=4, reason=GameEndReason.PLY_LIMIT
        )
        with self.assertRaisesRegex(ValueError, "棋譜末尾で終局"):
            comparison_result_io._load_game(
                payload, schedule, config, conditions_sha256=_CONDITIONS_SHA256
            )


if __name__ == "__main__":
    unittest.main()
