"""評価操作を差し替えられる一手選択の契約を確認する。"""

import random
import unittest
from unittest.mock import Mock, patch

from kaname_shogi.evaluation import material_balance
from kaname_shogi.material_rook_mobility import evaluate_material_rook_mobility
from kaname_shogi.model import (
    BasicPieceType,
    Board,
    Piece,
    PieceType,
    Position,
    Side,
    Square,
)
from kaname_shogi.move import BoardMove, DropMove, Move
from kaname_shogi.movegen import is_checkmate, legal_moves, position_after_move
from kaname_shogi.one_ply_selection import choose_one_ply_move
from kaname_shogi.sfen import SfenPosition, format_sfen, parse_sfen


class OnePlySelectionTests(unittest.TestCase):
    def _open_rook_case(self, perspective: Side):
        """同じ駒得で歩の移動と飛車の開通を候補に持つ局面を返す。"""
        original = parse_sfen("8k/9/9/9/4R4/9/4P4/9/K8 b - 1").position
        if perspective == Side.SENTE:
            return (
                original,
                BoardMove(Square(5, 7), Square(5, 6), False),
                BoardMove(Square(5, 5), Square(4, 5), False),
            )

        rotated_board = Board()
        for file in range(1, 10):
            for rank in range(1, 10):
                piece = original.board.piece_at(Square(file, rank))
                if piece is None:
                    continue
                rotated_side = Side.GOTE if piece.side == Side.SENTE else Side.SENTE
                rotated_board.set_piece(
                    Square(10 - file, 10 - rank), Piece(piece.piece_type, rotated_side)
                )
        rotated = Position(rotated_board, Side.GOTE)
        return (
            rotated,
            BoardMove(Square(5, 3), Square(5, 4), False),
            BoardMove(Square(5, 5), Square(6, 5), False),
        )

    def _mate_case(self, perspective: Side):
        """飛車を金で支え、後手歩で玉の退路を塞いだ詰み局面を返す。"""
        board = Board()
        for square, piece_type, side in (
            (Square(9, 9), PieceType.KING, Side.SENTE),
            (Square(5, 3), PieceType.ROOK, Side.SENTE),
            (Square(4, 3), PieceType.GOLD, Side.SENTE),
            (Square(5, 1), PieceType.KING, Side.GOTE),
            (Square(4, 1), PieceType.PAWN, Side.GOTE),
            (Square(6, 1), PieceType.PAWN, Side.GOTE),
            (Square(4, 2), PieceType.PAWN, Side.GOTE),
            (Square(6, 2), PieceType.PAWN, Side.GOTE),
        ):
            board.set_piece(square, Piece(piece_type, side))
        position = Position(board, Side.SENTE)
        if perspective == Side.SENTE:
            return (
                position,
                BoardMove(Square(5, 3), Square(5, 2), False),
                BoardMove(Square(5, 3), Square(6, 3), False),
            )

        rotated_board = Board()
        for file in range(1, 10):
            for rank in range(1, 10):
                piece = position.board.piece_at(Square(file, rank))
                if piece is None:
                    continue
                rotated_side = Side.GOTE if piece.side == Side.SENTE else Side.SENTE
                rotated_board.set_piece(
                    Square(10 - file, 10 - rank), Piece(piece.piece_type, rotated_side)
                )
        return (
            Position(rotated_board, Side.GOTE),
            BoardMove(Square(5, 7), Square(5, 8), False),
            BoardMove(Square(5, 7), Square(4, 7), False),
        )

    @staticmethod
    def _sfen(position: Position) -> str:
        """Move 1を付け、盤面・手番・持ち駒を比較可能なSFENにする。"""
        return format_sfen(SfenPosition(position, 1))

    def test_prefers_open_rook_from_equal_material(self):
        """同じ駒得なら飛車の候補を広げる一手を選ぶ。

        位置評価の無視、先手固定、候補タプル順への固定を検出する。
        """
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                position, blocked, opened = self._open_rook_case(perspective)
                for moves in ((blocked, opened), (opened, blocked)):
                    selected = choose_one_ply_move(
                        position,
                        moves,
                        random.Random(20261024),
                        evaluate=evaluate_material_rook_mobility,
                    )
                    self.assertEqual(selected, opened)
                    self.assertEqual(
                        evaluate_material_rook_mobility(
                            position_after_move(position, blocked), perspective
                        ),
                        172,
                    )
                    self.assertEqual(
                        evaluate_material_rook_mobility(
                            position_after_move(position, opened), perspective
                        ),
                        176,
                    )

    def test_swaps_evaluator_without_changing_selector(self):
        """選択器へ駒得評価と新評価を渡し、開始側視点で同じ候補を採点する。

        選択器を可動性へ固定する誤りと、適用後手番で評価する誤りを検出する。
        """
        position, blocked, opened = self._open_rook_case(Side.SENTE)
        moves = (blocked, opened)
        rng = random.Random(20261024)
        with patch.object(rng, "choice", wraps=rng.choice) as choice:
            choose_one_ply_move(position, moves, rng, evaluate=material_balance)
        choice.assert_called_once_with(moves)

        evaluator = Mock(wraps=evaluate_material_rook_mobility)
        rng = random.Random(20261024)
        with patch.object(rng, "choice", wraps=rng.choice) as choice:
            selected = choose_one_ply_move(position, moves, rng, evaluate=evaluator)

        self.assertEqual(selected, opened)
        self.assertEqual(evaluator.call_count, 2)
        choice.assert_called_once_with((opened,))
        for move, call in zip(moves, evaluator.call_args_list, strict=True):
            evaluated_position, perspective = call.args
            self.assertEqual(perspective, Side.SENTE)
            self.assertEqual(
                self._sfen(evaluated_position),
                self._sfen(position_after_move(position, move)),
            )

    def test_selects_best_ties_once(self):
        """同点最高の候補だけを元の順序で一度抽選する。

        全候補を抽選へ混ぜる誤り、最高点候補ごとの複数抽選を検出する。
        """
        position = Position(Board(), Side.SENTE)
        position.board.set_piece(Square(5, 5), Piece(PieceType.ROOK, Side.SENTE))
        first = BoardMove(Square(5, 5), Square(5, 4), False)
        second = BoardMove(Square(5, 5), Square(4, 5), False)
        tied_moves = (first, second)
        rng = random.Random(20261024)
        with patch.object(rng, "choice", wraps=rng.choice) as choice:
            selected = choose_one_ply_move(
                position,
                tied_moves,
                rng,
                evaluate=evaluate_material_rook_mobility,
            )

        self.assertIn(selected, tied_moves)
        choice.assert_called_once_with(tied_moves)
        self.assertEqual(
            evaluate_material_rook_mobility(
                position_after_move(position, first), Side.SENTE
            ),
            166,
        )
        self.assertEqual(
            evaluate_material_rook_mobility(
                position_after_move(position, second), Side.SENTE
            ),
            166,
        )

        position.sente_hand.add(BasicPieceType.PAWN)
        low = DropMove(BasicPieceType.PAWN, Square(5, 4))
        moves_with_low = (first, second, low)
        self.assertEqual(
            evaluate_material_rook_mobility(
                position_after_move(position, first), Side.SENTE
            ),
            176,
        )
        self.assertEqual(
            evaluate_material_rook_mobility(
                position_after_move(position, second), Side.SENTE
            ),
            176,
        )
        self.assertEqual(
            evaluate_material_rook_mobility(
                position_after_move(position, low), Side.SENTE
            ),
            172,
        )
        rng = random.Random(20261024)
        with patch.object(rng, "choice", wraps=rng.choice) as choice:
            choose_one_ply_move(
                position,
                moves_with_low,
                rng,
                evaluate=evaluate_material_rook_mobility,
            )
        choice.assert_called_once_with((first, second))

    def test_compares_negative_scores_without_clamping(self):
        """注入評価の負数も比較し、より高い負数を選ぶ。

        評価点を0未満で切り上げる誤りを、盤面に基づく固定関数で検出する。
        """
        position, blocked, opened = self._open_rook_case(Side.SENTE)

        def evaluate(after: Position, perspective: Side) -> int:
            pawn = after.board.piece_at(Square(5, 6))
            return -8 if pawn == Piece(PieceType.PAWN, Side.SENTE) else -3

        selected = choose_one_ply_move(
            position,
            (blocked, opened),
            random.Random(20261024),
            evaluate=evaluate,
        )

        self.assertEqual(selected, opened)
        self.assertEqual(
            evaluate(position_after_move(position, blocked), Side.SENTE), -8
        )
        self.assertEqual(
            evaluate(position_after_move(position, opened), Side.SENTE), -3
        )

    def test_mate_outranks_unbounded_normal_score(self):
        """詰みを通常点より優先し、詰み手は通常評価へ渡さない。

        先後・候補順・巨大な通常点で詰み優先が崩れる誤りを検出する。
        """
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                position, mate, normal = self._mate_case(perspective)
                self.assertTrue(is_checkmate(position_after_move(position, mate)))
                self.assertFalse(is_checkmate(position_after_move(position, normal)))
                for moves in ((mate, normal), (normal, mate)):
                    evaluator = Mock(return_value=10**30)
                    rng = random.Random(20261024)
                    with patch.object(rng, "choice", wraps=rng.choice) as choice:
                        selected = choose_one_ply_move(
                            position, moves, rng, evaluate=evaluator
                        )

                    self.assertEqual(selected, mate)
                    evaluator.assert_called_once()
                    self.assertEqual(evaluator.call_args.args[1], perspective)
                    choice.assert_called_once_with((mate,))

    def test_selects_all_mating_ties_once(self):
        """成・不成の詰み候補を両方残し、最高同点として一度抽選する。

        成り選択で詰み候補を欠落させたり、同点の詰みを一候補へ固定する誤りを検出する。
        """
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                position, mate, _ = self._mate_case(perspective)
                promote = BoardMove(mate.source, mate.destination, True)
                mating_moves = (mate, promote)
                for move in mating_moves:
                    self.assertTrue(is_checkmate(position_after_move(position, move)))

                evaluator = Mock(return_value=-(10**30))
                rng = random.Random(20261024)
                with patch.object(rng, "choice", wraps=rng.choice) as choice:
                    selected = choose_one_ply_move(
                        position, mating_moves, rng, evaluate=evaluator
                    )

                self.assertIn(selected, mating_moves)
                evaluator.assert_not_called()
                choice.assert_called_once_with(mating_moves)

    def test_empty_candidates_have_no_effects(self):
        """候補が空ならNoneを返し、評価・適用・詰み確認・抽選をしない。

        空タプルを下位APIへ渡す誤りや、不要な副作用を検出する。
        """
        position = Position(Board(), Side.SENTE)
        rng = random.Random(20261024)
        evaluator = Mock()
        with (
            patch("kaname_shogi.one_ply_selection.position_after_move") as apply,
            patch("kaname_shogi.one_ply_selection.is_checkmate") as checkmate,
            patch.object(rng, "choice", wraps=rng.choice) as choice,
        ):
            result = choose_one_ply_move(position, (), rng, evaluate=evaluator)

        self.assertIsNone(result)
        evaluator.assert_not_called()
        apply.assert_not_called()
        checkmate.assert_not_called()
        choice.assert_not_called()

    def test_noncheck_no_reply_uses_evaluator(self):
        """王手でない局面に合法手がなくても通常評価で候補を選ぶ。

        合法手なしを詰みと同一視し、通常評価を省略する誤りを検出する。
        """
        position = Position(Board(), Side.SENTE)
        position.board.set_piece(Square(5, 5), Piece(PieceType.ROOK, Side.SENTE))
        move = BoardMove(Square(5, 5), Square(5, 4), False)
        after = position_after_move(position, move)
        self.assertEqual(legal_moves(after), ())
        self.assertFalse(is_checkmate(after))

        evaluator = Mock(return_value=-8)
        rng = random.Random(20261024)
        with patch.object(rng, "choice", wraps=rng.choice) as choice:
            selected = choose_one_ply_move(position, (move,), rng, evaluate=evaluator)

        self.assertEqual(selected, move)
        evaluator.assert_called_once()
        self.assertEqual(evaluator.call_args.args[1], Side.SENTE)
        choice.assert_called_once_with((move,))

    def test_preserves_source_and_branches(self):
        """移動・成り・打ち後を別枝へ適用し、元局面と他の枝を保つ。

        適用後局面を共有して次候補や元局面を汚す誤りを検出する。
        """
        capture = parse_sfen("8k/9/9/4+r4/4R4/9/9/9/K8 b - 1")
        promotion = parse_sfen("8k/9/9/4R4/9/9/9/9/K8 b - 1")
        drop = parse_sfen("8k/9/9/9/9/9/9/9/K8 b P 1")
        cases: tuple[tuple[SfenPosition, Move, Square, Piece, int], ...] = (
            (
                capture,
                BoardMove(Square(5, 5), Square(5, 4), False),
                Square(5, 4),
                Piece(PieceType.ROOK, Side.SENTE),
                1,
            ),
            (
                promotion,
                BoardMove(Square(5, 4), Square(5, 3), True),
                Square(5, 3),
                Piece(PieceType.DRAGON, Side.SENTE),
                0,
            ),
            (
                drop,
                DropMove(BasicPieceType.PAWN, Square(5, 5)),
                Square(5, 5),
                Piece(PieceType.PAWN, Side.SENTE),
                0,
            ),
        )
        for parsed, move, destination, expected_piece, hand_count in cases:
            with self.subTest(move=move):
                before = format_sfen(parsed)
                evaluator = Mock(return_value=0)
                selected = choose_one_ply_move(
                    parsed.position,
                    (move,),
                    random.Random(20261024),
                    evaluate=evaluator,
                )

                self.assertEqual(selected, move)
                self.assertEqual(format_sfen(parsed), before)
                after = evaluator.call_args.args[0]
                self.assertIsNot(after, parsed.position)
                self.assertEqual(after.board.piece_at(destination), expected_piece)
                self.assertEqual(
                    after.sente_hand.count(BasicPieceType.ROOK), hand_count
                )

        branches = parse_sfen("8k/9/9/9/9/9/9/9/K8 b 2P 1")
        branch_moves = (
            DropMove(BasicPieceType.PAWN, Square(5, 5)),
            DropMove(BasicPieceType.PAWN, Square(4, 5)),
        )
        before = format_sfen(branches)
        evaluated_positions: list[Position] = []

        def mutate_first_branch(after: Position, perspective: Side) -> int:
            evaluated_positions.append(after)
            if len(evaluated_positions) == 1:
                after.board.set_piece(Square(9, 1), Piece(PieceType.GOLD, Side.SENTE))
            return 0

        choose_one_ply_move(
            branches.position,
            branch_moves,
            random.Random(20261024),
            evaluate=mutate_first_branch,
        )

        self.assertEqual(format_sfen(branches), before)
        self.assertEqual(
            evaluated_positions[0].board.piece_at(Square(9, 1)),
            Piece(PieceType.GOLD, Side.SENTE),
        )
        self.assertIsNone(evaluated_positions[1].board.piece_at(Square(9, 1)))
        self.assertIsNot(evaluated_positions[0], evaluated_positions[1])
        self.assertIsNot(evaluated_positions[0].board, evaluated_positions[1].board)
        self.assertEqual(branch_moves[0], DropMove(BasicPieceType.PAWN, Square(5, 5)))
        self.assertEqual(branch_moves[1], DropMove(BasicPieceType.PAWN, Square(4, 5)))

    def test_propagates_failures(self):
        """評価例外・未知手型・不合法手の既存例外を呼出元へ伝える。

        内部で例外を隠したり、失敗後に乱数選択へ進む誤りを検出する。
        """
        position = Position(Board(), Side.SENTE)
        position.board.set_piece(Square(5, 5), Piece(PieceType.ROOK, Side.SENTE))
        legal = BoardMove(Square(5, 5), Square(5, 4), False)
        rng = random.Random(20261024)
        with patch.object(rng, "choice", wraps=rng.choice) as choice:
            with self.assertRaisesRegex(RuntimeError, "evaluation failed"):
                choose_one_ply_move(
                    position,
                    (legal,),
                    rng,
                    evaluate=Mock(side_effect=RuntimeError("evaluation failed")),
                )
        choice.assert_not_called()

        with self.assertRaises(TypeError):
            choose_one_ply_move(
                position,
                (object(),),
                random.Random(20261024),
                evaluate=Mock(return_value=0),
            )

        blocked = Position(Board(), Side.SENTE)
        blocked.board.set_piece(Square(5, 5), Piece(PieceType.ROOK, Side.SENTE))
        blocked.board.set_piece(Square(5, 4), Piece(PieceType.PAWN, Side.SENTE))
        illegal = BoardMove(Square(5, 5), Square(5, 4), False)
        with self.assertRaises(ValueError):
            choose_one_ply_move(
                blocked,
                (illegal,),
                random.Random(20261024),
                evaluate=Mock(return_value=0),
            )


if __name__ == "__main__":
    unittest.main()
