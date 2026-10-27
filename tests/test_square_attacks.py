"""盤上の駒が占有マスを含めて利く範囲を検証する。"""

import unittest
from unittest.mock import patch

from kaname_shogi import movegen
from kaname_shogi.model import Board, Piece, PieceType, Side, Square


def _board_contents(board: Board) -> tuple[Piece | None, ...]:
    """盤の筋・段順を固定して全マスの内容を返すテスト用読み取り。"""
    return tuple(
        board.piece_at(Square(file, rank))
        for file in range(1, 10)
        for rank in range(1, 10)
    )


def _query(board: Board, target: Square, side: Side) -> bool:
    """公開関数がない初回Redでもassertionまで到達する呼び出し。"""
    function = getattr(movegen, "is_square_attacked", None)
    if function is None:
        return False
    return function(board, target, side)


def _sliding_offsets(directions: tuple[tuple[int, int], ...]) -> set[tuple[int, int]]:
    """５五から盤端まで、指定された長距離方向の差分を作る。"""
    return {
        (file_delta * distance, rank_delta * distance)
        for file_delta, rank_delta in directions
        for distance in range(1, 5)
    }


def _expected_offsets(piece_type: PieceType, side: Side) -> set[tuple[int, int]]:
    """駒の規則から独立に手書きした、５五起点の利き差分を返す。"""
    forward = -1 if side == Side.SENTE else 1
    orthogonal = ((-1, 0), (1, 0), (0, -1), (0, 1))
    diagonal = ((-1, -1), (-1, 1), (1, -1), (1, 1))

    if piece_type == PieceType.KING:  # 玉・王
        return {
            (file_delta, rank_delta)
            for file_delta in (-1, 0, 1)
            for rank_delta in (-1, 0, 1)
            if (file_delta, rank_delta) != (0, 0)
        }
    if piece_type == PieceType.ROOK:  # 飛車
        return _sliding_offsets(orthogonal)
    if piece_type == PieceType.BISHOP:  # 角行
        return _sliding_offsets(diagonal)
    if piece_type in (  # 金将相当
        PieceType.GOLD,
        PieceType.PRO_PAWN,  # と金
        PieceType.PRO_LANCE,  # 成香
        PieceType.PRO_KNIGHT,  # 成桂
        PieceType.PRO_SILVER,  # 成銀
    ):
        return {
            (-1, forward),
            (0, forward),
            (1, forward),
            (-1, 0),
            (1, 0),
            (0, -forward),
        }
    if piece_type == PieceType.SILVER:  # 銀将
        return {
            (-1, forward),
            (0, forward),
            (1, forward),
            (-1, -forward),
            (1, -forward),
        }
    if piece_type == PieceType.KNIGHT:  # 桂馬
        return {(-1, 2 * forward), (1, 2 * forward)}
    if piece_type == PieceType.LANCE:  # 香車
        return {(0, distance * forward) for distance in range(1, 5)}
    if piece_type == PieceType.PAWN:  # 歩兵
        return {(0, forward)}
    if piece_type == PieceType.HORSE:  # 馬
        return _sliding_offsets(diagonal) | set(orthogonal)
    if piece_type == PieceType.DRAGON:  # 竜
        return _sliding_offsets(orthogonal) | set(diagonal)
    raise AssertionError(f"未定義の駒種: {piece_type}")


def _friendly_target(piece_type: PieceType, side: Side) -> Square:
    """各駒種が利く、味方駒で占有するための固定マスを返す。"""
    fixed_targets = {
        PieceType.KING: Square(5, 4),  # 玉・王
        PieceType.ROOK: Square(5, 4),  # 飛車
        PieceType.BISHOP: Square(4, 4),  # 角行
        PieceType.GOLD: Square(5, 4),  # 金将
        PieceType.SILVER: Square(4, 4),  # 銀将
        PieceType.PRO_PAWN: Square(5, 4),  # と金
        PieceType.PRO_LANCE: Square(5, 4),  # 成香
        PieceType.PRO_KNIGHT: Square(5, 4),  # 成桂
        PieceType.PRO_SILVER: Square(5, 4),  # 成銀
        PieceType.HORSE: Square(5, 4),  # 馬
        PieceType.DRAGON: Square(4, 4),  # 竜
    }
    if piece_type == PieceType.KNIGHT:  # 桂馬
        return Square(4, 3 if side == Side.SENTE else 7)
    if piece_type in (PieceType.LANCE, PieceType.PAWN):  # 香車・歩兵
        return Square(5, 4 if side == Side.SENTE else 6)
    return fixed_targets[piece_type]


class SquareAttacksTests(unittest.TestCase):
    def test_matches_all_piece_geometries_for_both_sides(self):
        """全14駒種の利き形状を先後両方で手書き集合と照合する。

        駒種の候補関数漏れ、先後の向き違い、成駒の利き違いを検出する。
        """
        source = Square(5, 5)
        for piece_type in PieceType:
            for side in Side:
                board = Board()
                board.set_piece(source, Piece(piece_type, side))
                expected = {
                    Square(5 + file_delta, 5 + rank_delta)
                    for file_delta, rank_delta in _expected_offsets(piece_type, side)
                }
                with self.subTest(piece_type=piece_type, side=side):
                    for file in range(1, 10):
                        for rank in range(1, 10):
                            target = Square(file, rank)
                            self.assertEqual(
                                target in expected,
                                _query(board, target, side),
                                f"{piece_type} {side}: {target}",
                            )

    def test_counts_friendly_occupied_target(self):
        """攻撃側の味方が占める到着マスも利きとして数える。

        移動候補から味方占有マスを除外する規則を利き照会へ誤用する実装を検出する。
        """
        source = Square(5, 5)
        for piece_type in PieceType:
            for side in Side:
                target = _friendly_target(piece_type, side)
                board = Board()
                board.set_piece(source, Piece(piece_type, side))
                board.set_piece(target, Piece(PieceType.PAWN, side))
                with self.subTest(piece_type=piece_type, side=side):
                    self.assertTrue(_query(board, target, side))

    def test_counts_opponent_occupied_target(self):
        """相手側が占める到着マスを利きとして数える。

        駒取り候補に含まれる相手駒のマスを攻撃判定から落とす誤りを検出する。
        """
        source = Square(5, 5)
        for piece_type in PieceType:
            for side in Side:
                target = _friendly_target(piece_type, side)
                opponent = Side.GOTE if side == Side.SENTE else Side.SENTE
                board = Board()
                board.set_piece(source, Piece(piece_type, side))
                board.set_piece(target, Piece(PieceType.PAWN, opponent))
                with self.subTest(piece_type=piece_type, side=side):
                    self.assertTrue(_query(board, target, side))

    def test_excludes_self_attack_and_empty_attackers(self):
        """駒の出発マス自身と攻撃元のない盤を利きとして数えない。

        移動候補に出発マスを誤って含める実装や、空盤を攻撃ありとする実装を検出する。
        """
        source = Square(5, 5)
        empty_board = Board()
        self.assertFalse(_query(empty_board, source, Side.SENTE))

        for piece_type in PieceType:
            for side in Side:
                board = Board()
                board.set_piece(source, Piece(piece_type, side))
                with self.subTest(piece_type=piece_type, side=side):
                    self.assertFalse(_query(board, source, side))

    def test_ignores_attacks_from_the_other_side(self):
        """照会した側と異なる駒の利きを数えない。

        盤上に一方の歩だけがあるとき、反対側の利きとして返す誤りを先後両方で検出する。
        """
        cases = (
            (Piece(PieceType.PAWN, Side.SENTE), Square(5, 4), Side.GOTE),
            (Piece(PieceType.PAWN, Side.GOTE), Square(5, 6), Side.SENTE),
        )
        for piece, target, requested_side in cases:
            board = Board()
            board.set_piece(Square(5, 5), piece)
            with self.subTest(piece=piece, requested_side=requested_side):
                self.assertFalse(_query(board, target, requested_side))

    def test_stops_at_first_blocker_in_every_sliding_direction(self):
        """長距離の利きは最初の遮蔽マスで止まる。

        飛車・角行・香車・馬・竜が遮蔽を飛び越す誤りを検出する。
        """
        directions = {
            PieceType.ROOK: ((-1, 0), (1, 0), (0, -1), (0, 1)),  # 飛車
            PieceType.BISHOP: ((-1, -1), (-1, 1), (1, -1), (1, 1)),  # 角行
            PieceType.HORSE: ((-1, -1), (-1, 1), (1, -1), (1, 1)),  # 馬
            PieceType.DRAGON: ((-1, 0), (1, 0), (0, -1), (0, 1)),  # 竜
        }
        source = Square(5, 5)
        for piece_type in (
            PieceType.ROOK,
            PieceType.BISHOP,
            PieceType.LANCE,
            PieceType.HORSE,
            PieceType.DRAGON,
        ):
            for attacker_side in Side:
                vectors = (
                    ((0, -1 if attacker_side == Side.SENTE else 1),)
                    if piece_type == PieceType.LANCE
                    else directions[piece_type]
                )
                for blocker_side in Side:
                    for file_delta, rank_delta in vectors:
                        board = Board()
                        board.set_piece(source, Piece(piece_type, attacker_side))
                        blocker = Square(5 + 2 * file_delta, 5 + 2 * rank_delta)
                        board.set_piece(blocker, Piece(PieceType.KNIGHT, blocker_side))
                        with self.subTest(
                            piece_type=piece_type,
                            attacker_side=attacker_side,
                            blocker_side=blocker_side,
                            direction=(file_delta, rank_delta),
                        ):
                            self.assertTrue(
                                _query(
                                    board,
                                    Square(5 + file_delta, 5 + rank_delta),
                                    attacker_side,
                                )
                            )
                            self.assertTrue(_query(board, blocker, attacker_side))
                            self.assertFalse(
                                _query(
                                    board,
                                    Square(
                                        5 + 3 * file_delta,
                                        5 + 3 * rank_delta,
                                    ),
                                    attacker_side,
                                )
                            )

    def test_knight_jumps_over_unrelated_blockers(self):
        """桂馬の利きは途中の占有マスに遮られない。

        桂馬を長距離駒と同じ連続移動として実装する誤りを検出する。
        """
        source = Square(5, 5)
        for side in Side:
            board = Board()
            board.set_piece(source, Piece(PieceType.KNIGHT, side))
            board.set_piece(Square(5, 4), Piece(PieceType.ROOK, Side.SENTE))
            board.set_piece(Square(5, 6), Piece(PieceType.ROOK, Side.GOTE))
            rank = 3 if side == Side.SENTE else 7
            with self.subTest(side=side):
                self.assertTrue(_query(board, Square(4, rank), side))
                self.assertTrue(_query(board, Square(6, rank), side))

    def test_preserves_board_on_success_and_failure(self):
        """成功時と候補照会の例外時に元盤を変更しない。

        味方占有targetを照会盤から取り除く際に、元盤を直接変更する誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        target = Square(5, 4)
        board.set_piece(source, Piece(PieceType.ROOK, Side.SENTE))
        board.set_piece(target, Piece(PieceType.PAWN, Side.SENTE))
        before = _board_contents(board)

        self.assertTrue(_query(board, target, Side.SENTE))
        self.assertEqual(_board_contents(board), before)

        with patch.object(
            movegen, "_move_candidates_for_piece", side_effect=RuntimeError("照会失敗")
        ):
            with self.assertRaisesRegex(RuntimeError, "照会失敗"):
                _query(board, target, Side.SENTE)
        self.assertEqual(_board_contents(board), before)


if __name__ == "__main__":
    unittest.main()
