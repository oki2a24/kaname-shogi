"""SFEN局面変換APIの公開境界を確認する。"""

import importlib.util
import unittest
from unittest.mock import patch

from kaname_shogi.model import (BasicPieceType, Board, Piece, PieceType,
                                Hand, Position, Side, Square,
                                create_initial_position)
from kaname_shogi.sfen import SfenPosition, format_sfen, parse_sfen


HAND_PIECE_TYPES = (
    BasicPieceType.ROOK, BasicPieceType.BISHOP, BasicPieceType.GOLD,
    BasicPieceType.SILVER, BasicPieceType.KNIGHT, BasicPieceType.LANCE,
    BasicPieceType.PAWN,
)


class SfenConversionTests(unittest.TestCase):
    def assert_positions_match(self, expected, actual):
        """局面の盤面・手番・先後の持ち駒を個別に比較する。"""
        self.assertEqual(actual.side_to_move, expected.side_to_move)
        for file in range(1, 10):
            for rank in range(1, 10):
                square = Square(file, rank)
                with self.subTest(file=file, rank=rank):
                    self.assertEqual(actual.board.piece_at(square),
                                     expected.board.piece_at(square))
        for piece_type in HAND_PIECE_TYPES:
            with self.subTest(side="sente", piece_type=piece_type):
                self.assertEqual(actual.sente_hand.count(piece_type),
                                 expected.sente_hand.count(piece_type))
            with self.subTest(side="gote", piece_type=piece_type):
                self.assertEqual(actual.gote_hand.count(piece_type),
                                 expected.gote_hand.count(piece_type))

    def snapshot_position(self, position):
        """書出し前後を比較するため、局面の公開状態を値に写す。"""
        board = tuple(
            position.board.piece_at(Square(file, rank))
            for rank in range(1, 10)
            for file in range(1, 10)
        )
        sente_hand = tuple(position.sente_hand.count(piece_type)
                           for piece_type in HAND_PIECE_TYPES)
        gote_hand = tuple(position.gote_hand.count(piece_type)
                          for piece_type in HAND_PIECE_TYPES)
        return board, position.side_to_move, sente_hand, gote_hand

    def test_parses_and_formats_initial_sfen(self):
        """平手初期局面をSFENから読み込み、同じ表記へ書き出す。

        筋段の向きや先後の配置を逆に読み、見かけだけ同じ文字列になる誤りを検出する。
        """
        sfen = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"

        result = parse_sfen(sfen)

        self.assertIsInstance(result, SfenPosition)
        self.assertEqual(result.move_number, 1)
        self.assert_positions_match(create_initial_position(), result.position)
        self.assertEqual(format_sfen(result), sfen)

    def test_round_trips_promoted_piece_hands_and_move_number(self):
        """成駒・先後の持ち駒・手数を読み書きで保つ。

        成駒の所有者、持ち駒の大文字小文字、2枚以上の枚数を取り違える誤りを検出する。
        """
        sfen = "9/9/9/3+P5/9/9/9/9/K8 b 2RBGsnp 17"

        result = parse_sfen(sfen)

        self.assertEqual(result.move_number, 17)
        self.assertEqual(result.position.board.piece_at(Square(6, 4)),
                         Piece(PieceType.PRO_PAWN, Side.SENTE))
        self.assertEqual(result.position.sente_hand.count(BasicPieceType.ROOK), 2)
        self.assertEqual(result.position.sente_hand.count(BasicPieceType.BISHOP), 1)
        self.assertEqual(result.position.sente_hand.count(BasicPieceType.GOLD), 1)
        self.assertEqual(result.position.gote_hand.count(BasicPieceType.SILVER), 1)
        self.assertEqual(result.position.gote_hand.count(BasicPieceType.KNIGHT), 1)
        self.assertEqual(result.position.gote_hand.count(BasicPieceType.PAWN), 1)
        self.assertEqual(format_sfen(result), sfen)

    def test_defaults_missing_move_number_to_one_and_writes_it(self):
        """手数欄のないSFENを受け入れ、手数1を明示して書き出す。

        ShogiHomeの貼り付けSFENで省略可能な欄を拒否したり、書出しで再び落とす誤りを検出する。
        """
        sfen = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b -"

        result = parse_sfen(sfen)

        self.assertEqual(result.move_number, 1)
        self.assert_positions_match(create_initial_position(), result.position)
        self.assertEqual(format_sfen(result), f"{sfen} 1")

    def test_accepts_composed_position_without_king(self):
        """玉がない詰将棋用などの局面も構文上表現できれば受け付ける。

        SFEN変換が局面の合法性や実戦到達可能性を先取りして検査する誤りを検出する。
        """
        result = parse_sfen("9/9/9/9/9/9/9/9/9 w - 8")

        self.assertEqual(result.move_number, 8)
        self.assertEqual(result.position.side_to_move, Side.GOTE)
        for file in range(1, 10):
            for rank in range(1, 10):
                with self.subTest(file=file, rank=rank):
                    self.assertIsNone(
                        result.position.board.piece_at(Square(file, rank)))

    def test_rejects_malformed_sfen_fields(self):
        """不正な盤面・手番・持ち駒・手数を理由付きValueErrorにする。

        欄不足や未対応値を誤って受け入れたり、入力者に原因が分からない例外を返す誤りを検出する。
        """
        empty_board = "9/9/9/9/9/9/9/9/9"
        cases = [
            ("9/9 b - 1", "盤面"),
            ("8/9/9/9/9/9/9/9/9 b - 1", "盤面"),
            ("X8/9/9/9/9/9/9/9/9 b - 1", "盤面"),
            ("ſ8/9/9/9/9/9/9/9/9 b - 1", "駒記号"),
            ("3+K5/9/9/9/9/9/9/9/9 b - 1", "盤面"),
            (f"{empty_board} x - 1", "手番"),
            (f"{empty_board} b K 1", "持ち駒"),
            (f"{empty_board} b ſ 1", "駒"),
            (f"{empty_board} b 0P 1", "持ち駒"),
            (f"{empty_board} b - x", "手数"),
            (f"{empty_board} b - 0", "手数"),
        ]
        for sfen, reason in cases:
            with self.subTest(sfen=sfen):
                with self.assertRaisesRegex(ValueError, reason):
                    parse_sfen(sfen)

    def test_parses_and_formats_large_hand_count_without_per_piece_add(self):
        """巨大な持ち駒枚数も一括で読み書きする。

        入力枚数に比例してHand.addを繰り返し、USI処理を止める誤りをガード付きで検出する。
        """
        sfen = "9/9/9/9/9/9/9/9/9 b 1000000000000P 1"

        with patch.object(Hand, "add",
                          side_effect=AssertionError("1枚ずつの追加は禁止")):
            result = parse_sfen(sfen)

        self.assertEqual(
            result.position.sente_hand.count(BasicPieceType.PAWN),
            1_000_000_000_000,
        )
        self.assertEqual(format_sfen(result), sfen)

    def test_formatting_does_not_mutate_position(self):
        """SFEN書出しは局面や持ち駒の枚数を変更しない。

        変換中に手のカウントを消費したり、盤上の値を正規化のため書き換える誤りを検出する。
        """
        result = parse_sfen("9/9/9/3+P5/9/9/9/9/K8 b 2RBGsnp 17")
        before = self.snapshot_position(result.position)

        format_sfen(result)

        self.assertEqual(self.snapshot_position(result.position), before)

    def test_formats_hands_in_canonical_order(self):
        """持ち駒を飛・角・金・銀・桂・香・歩の順に書き出す。

        追加された順や辞書の順序で表記が揺れ、同じ局面のSFEN比較が不安定になる誤りを検出する。
        """
        position = Position(Board(), Side.SENTE)
        for piece_type in (BasicPieceType.PAWN, BasicPieceType.GOLD,
                           BasicPieceType.ROOK):
            position.sente_hand.add(piece_type)
        for piece_type in (BasicPieceType.PAWN, BasicPieceType.KNIGHT,
                           BasicPieceType.SILVER):
            position.gote_hand.add(piece_type)

        self.assertEqual(format_sfen(SfenPosition(position, 1)),
                         "9/9/9/9/9/9/9/9/9 b RGPsnp 1")

    def test_rejects_invalid_move_number_in_sfen_position(self):
        """SFEN専用結果は1以上の整数手数だけを保持する。

        0手や真偽値を有効なSFEN手数として書き出す不整合を検出する。
        """
        position = create_initial_position()
        for move_number in (0, -1, True, 1.5):
            with self.subTest(move_number=move_number):
                with self.assertRaises(ValueError):
                    SfenPosition(position, move_number)


class SfenApiTests(unittest.TestCase):
    def test_sfen_api_is_available(self):
        """SFEN変換モジュールと読込・書出し関数を公開する。

        初めて利用する呼び出し側が、SFEN用APIをインポートできない状態を検出する。
        """
        spec = importlib.util.find_spec("kaname_shogi.sfen")
        self.assertIsNotNone(spec, "kaname_shogi.sfen がありません")
        from kaname_shogi import sfen

        self.assertTrue(callable(sfen.parse_sfen))
        self.assertTrue(callable(sfen.format_sfen))


if __name__ == "__main__":
    unittest.main()
