"""飛車可動性の計数契約を確認する。"""

import unittest

from kaname_shogi.model import Board, Piece, PieceType, Position, Side, Square
from kaname_shogi.movegen import rook_move_candidates
from kaname_shogi.sfen import format_sfen, parse_sfen


class RookMobilityTests(unittest.TestCase):
    def test_counts_blocked_and_open_rook(self):
        """同じ駒得でも味方歩に塞がれた飛車の候補数を減らす。

        配置の反映漏れや中央位置への根拠のない加点を検出する。
        """
        from kaname_shogi.rook_mobility import rook_mobility_balance

        blocked = parse_sfen("8k/9/9/9/4R4/9/4P4/9/K8 b - 1").position
        opened = parse_sfen("8k/9/9/9/4R4/9/5P3/9/K8 b - 1").position

        self.assertEqual(rook_mobility_balance(blocked, Side.SENTE), 13)
        self.assertEqual(rook_mobility_balance(opened, Side.SENTE), 16)
        self.assertEqual(rook_mobility_balance(blocked, Side.GOTE), -13)

    def test_counts_edges_without_center_bonus(self):
        """遮蔽物がない飛車は中央と盤端で各16候補を持つ。

        盤端での走査漏れや中央への位置加点を検出する。
        """
        from kaname_shogi.rook_mobility import rook_mobility_balance

        for source in (Square(5, 5), Square(1, 5), Square(1, 1), Square(9, 9)):
            with self.subTest(source=source):
                board = Board()
                board.set_piece(source, Piece(PieceType.ROOK, Side.SENTE))
                position = Position(board, Side.SENTE)
                self.assertEqual(rook_mobility_balance(position, Side.SENTE), 16)

    def test_sums_each_rook_without_deduplicating(self):
        """二枚の飛車は共通候補を差し引かず個別に合算する。

        全体の到達マス集合を数えて二枚の寄与を失う誤りを検出する。
        """
        from kaname_shogi.rook_mobility import rook_mobility_balance

        board = Board()
        board.set_piece(Square(1, 1), Piece(PieceType.ROOK, Side.SENTE))
        board.set_piece(Square(9, 9), Piece(PieceType.ROOK, Side.SENTE))
        position = Position(board, Side.SENTE)

        self.assertEqual(rook_mobility_balance(position, Side.SENTE), 32)

    def test_subtracts_opponent_and_ignores_turn(self):
        """先後双方の飛車合計を引き算し、手番によらず指定側から返す。

        相手分の符号やPositionの手番を視点に誤用する実装を検出する。
        """
        from kaname_shogi.rook_mobility import rook_mobility_balance

        # 後手歩９一が後手飛車１一の横移動を一マス遮るため、後手側は9候補。
        position = parse_sfen("p7r/9/8P/9/4R4/9/4P4/9/9 b - 1").position

        self.assertEqual(rook_mobility_balance(position, Side.SENTE), 4)
        self.assertEqual(rook_mobility_balance(position, Side.GOTE), -4)
        position.side_to_move = Side.GOTE
        self.assertEqual(rook_mobility_balance(position, Side.SENTE), 4)

    def test_uses_piece_side_after_rotation(self):
        """配置と所属を180度反転しても同じ物理的な側の値を保つ。

        飛車の先手後手別の走査方向や評価符号の固定を検出する。
        """
        from kaname_shogi.rook_mobility import rook_mobility_balance

        original = parse_sfen("p7r/9/8P/9/4R4/9/4P4/9/9 b - 1").position
        rotated_board = Board()
        for file in range(1, 10):
            for rank in range(1, 10):
                piece = original.board.piece_at(Square(file, rank))
                if piece is None:
                    continue
                rotated_side = Side.GOTE if piece.side is Side.SENTE else Side.SENTE
                rotated_board.set_piece(
                    Square(10 - file, 10 - rank), Piece(piece.piece_type, rotated_side)
                )
        rotated = Position(rotated_board, Side.GOTE)

        self.assertEqual(rook_mobility_balance(rotated, Side.GOTE), 4)
        self.assertEqual(rook_mobility_balance(rotated, Side.SENTE), -4)

    def test_excludes_dragon_and_hand_rook(self):
        """可動性は盤上の未成飛車に限り竜・持ち飛には付けない。

        駒得評価に残る竜・持ち駒まで可動性へ含める誤りを検出する。
        """
        from kaname_shogi.rook_mobility import rook_mobility_balance

        rook = parse_sfen("8k/9/9/9/4R4/9/9/9/K8 b - 1").position
        dragon = parse_sfen("8k/9/9/9/4+R4/9/9/9/K8 b - 1").position
        hand_rook = parse_sfen("8k/9/9/9/9/9/9/9/K8 b R 1").position

        self.assertEqual(rook_mobility_balance(rook, Side.SENTE), 16)
        self.assertEqual(rook_mobility_balance(dragon, Side.SENTE), 0)
        self.assertEqual(rook_mobility_balance(hand_rook, Side.SENTE), 0)
        self.assertEqual(
            rook_mobility_balance(Position(Board(), Side.SENTE), Side.SENTE), 0
        )

    def test_counts_all_blocking_directions(self):
        """四方向それぞれで味方駒と相手駒に当たった位置で止まる。

        特定方向だけの走査、味方駒の加算、相手駒の除外、遮蔽物通過を検出する。
        """
        from kaname_shogi.rook_mobility import rook_mobility_balance

        blockers = (Square(5, 3), Square(5, 7), Square(3, 5), Square(7, 5))
        for side, expected in ((Side.SENTE, 13), (Side.GOTE, 14)):
            for blocker in blockers:
                with self.subTest(blocker_side=side, blocker=blocker):
                    board = Board()
                    board.set_piece(Square(5, 5), Piece(PieceType.ROOK, Side.SENTE))
                    board.set_piece(blocker, Piece(PieceType.PAWN, side))
                    self.assertEqual(
                        rook_mobility_balance(Position(board, Side.SENTE), Side.SENTE),
                        expected,
                    )

        king_blocker = Square(5, 3)
        king_blocked_board = Board()
        king_blocked_board.set_piece(Square(5, 5), Piece(PieceType.ROOK, Side.SENTE))
        king_blocked_board.set_piece(king_blocker, Piece(PieceType.KING, Side.GOTE))
        self.assertIn(
            king_blocker, rook_move_candidates(king_blocked_board, Square(5, 5))
        )
        self.assertEqual(
            rook_mobility_balance(Position(king_blocked_board, Side.SENTE), Side.SENTE),
            14,
        )

    def test_counts_pinned_and_unsafe_destinations(self):
        """自玉を危険にする候補や相手の利きにあるマスも数える。

        合法手や安全な到着先だけに絞り、可動性の定義を変える誤りを検出する。
        """
        from kaname_shogi.rook_mobility import rook_mobility_balance

        pinned_board = Board()
        pinned_board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
        pinned_board.set_piece(Square(5, 8), Piece(PieceType.ROOK, Side.SENTE))
        pinned_board.set_piece(Square(5, 1), Piece(PieceType.ROOK, Side.GOTE))
        pinned = Position(pinned_board, Side.SENTE)
        unsafe = parse_sfen("8k/9/6b2/9/4R4/9/9/9/K8 b - 1").position

        self.assertEqual(rook_mobility_balance(pinned, Side.SENTE), 0)
        self.assertIn(Square(5, 1), rook_move_candidates(unsafe.board, Square(5, 5)))
        self.assertEqual(rook_mobility_balance(unsafe, Side.SENTE), 16)

    def test_preserves_position(self):
        """計数は盤面・手番・双方の持ち駒を変更しない。

        評価中に元局面を書き換える読み取り契約違反を検出する。
        """
        from kaname_shogi.rook_mobility import rook_mobility_balance

        parsed = parse_sfen("8k/9/9/9/4R4/9/4P4/9/K8 b pR 1")
        before = format_sfen(parsed)

        rook_mobility_balance(parsed.position, Side.SENTE)

        self.assertEqual(format_sfen(parsed), before)


if __name__ == "__main__":
    unittest.main()
