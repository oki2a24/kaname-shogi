"""玉周辺安全度評価を既存一手選択へ注入したときの契約を確認する。"""

import random
import unittest
from unittest.mock import Mock, patch

from kaname_shogi.evaluation import material_balance
from kaname_shogi.material_king_safety import evaluate_material_king_safety
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

_HAND_TYPES = (
    BasicPieceType.ROOK,
    BasicPieceType.BISHOP,
    BasicPieceType.GOLD,
    BasicPieceType.SILVER,
    BasicPieceType.KNIGHT,
    BasicPieceType.LANCE,
    BasicPieceType.PAWN,
)


def _position(*pieces, side_to_move: Side = Side.SENTE) -> Position:
    """固定配置から独立した局面を作る。"""
    board = Board()
    for piece_type, side, square in pieces:
        board.set_piece(square, Piece(piece_type, side))
    return Position(board, side_to_move)


def _rotate_and_swap(pieces):
    """配置を180度回転し、駒の所属を入れ替える。"""
    result = []
    for piece_type, side, square in pieces:
        owner = Side.GOTE if side == Side.SENTE else Side.SENTE
        result.append((piece_type, owner, Square(10 - square.file, 10 - square.rank)))
    return tuple(result)


def _king_danger_case(perspective: Side) -> tuple[Position, Move, Move]:
    """設計Aの先手例またはその先後反転と危険・安全な玉移動を返す。"""
    pieces = (
        (PieceType.KING, Side.SENTE, Square(5, 5)),
        (PieceType.KING, Side.GOTE, Square(9, 1)),
        (PieceType.PAWN, Side.GOTE, Square(5, 3)),
    )
    if perspective == Side.GOTE:
        pieces = _rotate_and_swap(pieces)

    position = _position(*pieces, side_to_move=perspective)
    if perspective == Side.SENTE:
        unsafe = BoardMove(Square(5, 5), Square(4, 5), False)
        safe = BoardMove(Square(5, 5), Square(5, 6), False)
    else:
        unsafe = BoardMove(Square(5, 5), Square(6, 5), False)
        safe = BoardMove(Square(5, 5), Square(5, 4), False)
    return position, unsafe, safe


def _mate_case(perspective: Side) -> tuple[Position, Move, Move]:
    """一手詰みを含む固定局面と詰み・通常の飛車移動を返す。"""
    pieces = (
        (PieceType.KING, Side.SENTE, Square(9, 9)),
        (PieceType.ROOK, Side.SENTE, Square(5, 3)),
        (PieceType.GOLD, Side.SENTE, Square(4, 3)),
        (PieceType.KING, Side.GOTE, Square(5, 1)),
        (PieceType.PAWN, Side.GOTE, Square(4, 1)),
        (PieceType.PAWN, Side.GOTE, Square(6, 1)),
        (PieceType.PAWN, Side.GOTE, Square(4, 2)),
        (PieceType.PAWN, Side.GOTE, Square(6, 2)),
    )
    if perspective == Side.GOTE:
        pieces = _rotate_and_swap(pieces)

    position = _position(*pieces, side_to_move=perspective)
    if perspective == Side.SENTE:
        mate = BoardMove(Square(5, 3), Square(5, 2), False)
        normal = BoardMove(Square(5, 3), Square(6, 3), False)
    else:
        mate = BoardMove(Square(5, 7), Square(5, 8), False)
        normal = BoardMove(Square(5, 7), Square(4, 7), False)
    return position, mate, normal


def _mixed_move_case() -> Position:
    """成り・捕獲・歩打ちの評価差を見るTask 3共通局面を作る。"""
    position = _position(
        (PieceType.KING, Side.SENTE, Square(9, 9)),
        (PieceType.ROOK, Side.SENTE, Square(8, 8)),
        (PieceType.PAWN, Side.SENTE, Square(5, 4)),
        (PieceType.KING, Side.GOTE, Square(1, 1)),
        (PieceType.DRAGON, Side.GOTE, Square(8, 7)),
    )
    position.sente_hand.add(BasicPieceType.PAWN)
    return position


def _position_contents(position: Position):
    """局面の盤面・手番・双方の持ち駒を固定順の値にする。"""
    board = tuple(
        position.board.piece_at(Square(file, rank))
        for file in range(1, 10)
        for rank in range(1, 10)
    )
    sente_hand = tuple(position.sente_hand.count(piece) for piece in _HAND_TYPES)
    gote_hand = tuple(position.gote_hand.count(piece) for piece in _HAND_TYPES)
    return board, position.side_to_move, sente_hand, gote_hand


class _HoldingEvaluator:
    """評価された複製局面と固定評価値を保持するテスト用操作。"""

    def __init__(self) -> None:
        self.positions: list[Position] = []
        self.scores: list[int] = []

    def __call__(self, position: Position, perspective: Side) -> int:
        """局面を保存して新評価を返す。"""
        self.positions.append(position)
        score = evaluate_material_king_safety(position, perspective)
        self.scores.append(score)
        return score


class KingSafetySelectionTests(unittest.TestCase):
    def test_prefers_safer_king_move_for_both_sides(self):
        """先後双方で玉周辺が安全になる候補を選ぶ。

        指定視点・先後・候補タプル順を取り違える接続の誤りを検出する。
        """
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                position, unsafe, safe = _king_danger_case(perspective)
                self.assertIn(unsafe, legal_moves(position))
                self.assertIn(safe, legal_moves(position))
                self.assertEqual(
                    evaluate_material_king_safety(
                        position_after_move(position, unsafe), perspective
                    ),
                    -11,
                )
                self.assertEqual(
                    evaluate_material_king_safety(
                        position_after_move(position, safe), perspective
                    ),
                    -10,
                )

                for moves in ((unsafe, safe), (safe, unsafe)):
                    selected = choose_one_ply_move(
                        position,
                        moves,
                        random.Random(20261028),
                        evaluate=evaluate_material_king_safety,
                    )
                    self.assertEqual(selected, safe)

    def test_material_only_keeps_both_moves_tied(self):
        """駒得だけの注入では二候補を同点のまま一回抽選へ渡す。

        選択器への評価注入が固定されている誤りと、同点候補の欠落・複数抽選を検出する。
        """
        for perspective in (Side.SENTE, Side.GOTE):
            position, unsafe, safe = _king_danger_case(perspective)
            self.assertEqual(
                material_balance(position_after_move(position, unsafe), perspective),
                -1,
            )
            self.assertEqual(
                material_balance(position_after_move(position, safe), perspective),
                -1,
            )

            for moves in ((unsafe, safe), (safe, unsafe)):
                rng = random.Random(20261028)
                with patch.object(rng, "choice", wraps=rng.choice) as choice:
                    selected = choose_one_ply_move(
                        position, moves, rng, evaluate=material_balance
                    )

                self.assertIn(selected, moves)
                choice.assert_called_once_with(moves)

    def test_mate_priority_survives_safety_evaluator(self):
        """安全度評価に巨大な通常点を加えても一手詰みを選ぶ。

        詰みを通常評価へ渡す誤りや、通常点が詰み優先を覆す誤りを検出する。
        """
        for perspective in (Side.SENTE, Side.GOTE):
            with self.subTest(perspective=perspective):
                position, mate, normal = _mate_case(perspective)
                self.assertIn(mate, legal_moves(position))
                self.assertIn(normal, legal_moves(position))
                self.assertTrue(is_checkmate(position_after_move(position, mate)))
                self.assertFalse(is_checkmate(position_after_move(position, normal)))

                for moves in ((mate, normal), (normal, mate)):
                    evaluator = Mock(
                        side_effect=lambda after, side: (
                            evaluate_material_king_safety(after, side) + 10**30
                        )
                    )
                    rng = random.Random(20261028)
                    with patch.object(rng, "choice", wraps=rng.choice) as choice:
                        selected = choose_one_ply_move(
                            position, moves, rng, evaluate=evaluator
                        )

                    self.assertEqual(selected, mate)
                    evaluator.assert_called_once()
                    self.assertEqual(evaluator.call_args.args[1], perspective)
                    self.assertEqual(
                        _position_contents(evaluator.call_args.args[0]),
                        _position_contents(position_after_move(position, normal)),
                    )
                    choice.assert_called_once_with((mate,))

    def test_preserves_mixed_move_branches(self):
        """成り・捕獲・打ちを評価し、枝を後から変えても互いに独立させる。

        適用後局面の共有による他候補・元局面・持ち駒の破壊を検出する。
        """
        position = _mixed_move_case()
        before = _position_contents(position)
        promotion = BoardMove(Square(5, 4), Square(5, 3), True)
        capture = BoardMove(Square(8, 8), Square(8, 7), False)
        drop = DropMove(BasicPieceType.PAWN, Square(7, 6))
        candidates = (promotion, capture, drop)
        legal = legal_moves(position)
        for candidate in candidates:
            self.assertIn(candidate, legal)

        for moves in (candidates, tuple(reversed(candidates))):
            evaluator = _HoldingEvaluator()
            selected = choose_one_ply_move(
                position,
                moves,
                random.Random(20261028),
                evaluate=evaluator,
            )
            branches = dict(zip(moves, evaluator.positions, strict=True))
            score_by_move = dict(zip(moves, evaluator.scores, strict=True))

            self.assertEqual(selected, capture)
            self.assertEqual(score_by_move[promotion], 108)
            self.assertEqual(score_by_move[capture], 320)
            self.assertEqual(score_by_move[drop], -2)
            self.assertTrue(
                all(branch.side_to_move == Side.GOTE for branch in branches.values())
            )

            branch_states = {
                move: _position_contents(branch) for move, branch in branches.items()
            }
            capture_branch = branches[capture]
            capture_branch.board.set_piece(Square(8, 7), None)
            capture_branch.sente_hand.add(BasicPieceType.ROOK)
            capture_branch.gote_hand.add(BasicPieceType.PAWN)

            self.assertEqual(_position_contents(position), before)
            for move in (promotion, drop):
                self.assertEqual(
                    _position_contents(branches[move]), branch_states[move]
                )


if __name__ == "__main__":
    unittest.main()
