"""USI一手表記と中立な指し手データの対応を検証する。"""

import unittest

from kaname_shogi.model import BasicPieceType, Square
from kaname_shogi.move import BoardMove, DropMove
from kaname_shogi.usi_move import format_usi_move, parse_usi_move


class UsiMoveParseTests(unittest.TestCase):
    def test_parse_board_move_without_promotion(self):
        """通常移動の座標を成らない盤上移動として読む。

        実機観測の一例だけに依存せず、筋をfile、段をrankとして保持する
        対応が、既存のSquare値に正しく反映されることを確認する。
        """
        self.assertEqual(
            parse_usi_move("7g7f"),
            BoardMove(Square(7, 7), Square(7, 6), False),
        )

    def test_parse_board_move_with_promotion(self):
        """末尾の成り記号を盤上移動のpromote値に対応づける。

        成り指定を座標の一部と誤認せず、BoardMoveの独立した値として
        取り出せることを確認する。
        """
        self.assertEqual(
            parse_usi_move("8h2b+"),
            BoardMove(Square(8, 8), Square(2, 2), True),
        )

    def test_parse_maps_edge_squares_without_legality_check(self):
        """座標端を正しく読み、局面なしでは合法性を判定しない。

        1aと9iが盤の両端に対応し、駒の動きや局面合法性を解析へ混ぜない
        ことを確認する。
        """
        self.assertEqual(
            parse_usi_move("1a9i"),
            BoardMove(Square(1, 1), Square(9, 9), False),
        )

    def test_parse_rejects_malformed_tokens(self):
        """単独USI一手の文法から外れる文字列を拒否する。

        コマンド列、空白、範囲外座標、大小文字違い、未知記号を受け入れると
        局面履歴の境界で誤ったMove値を作るため、すべてValueErrorを確認する。
        """
        malformed_tokens = (
            "",
            "7g7",
            "7g7f++",
            " 7g7f",
            "7g7f ",
            "position startpos moves 7g7f",
            "0g7f",
            "10g7f",
            "7j7f",
            "7g7F",
            "p*5e",
            "X*5e",
            "*P5e",
            "P+*5e",
            "P*5e+",
        )
        for token in malformed_tokens:
            with self.subTest(token=token):
                with self.assertRaises(ValueError):
                    parse_usi_move(token)

    def test_parse_drop_move_for_each_hand_piece(self):
        """7種類の持ち駒記号を対応するDropMoveへ変換する。

        記号の順番や駒種の対応を誤ると、後続の局面履歴で異なる駒を
        打ったデータになるため、全種類をそれぞれ確認する。
        """
        cases = (
            ("P*5e", BasicPieceType.PAWN),
            ("L*5e", BasicPieceType.LANCE),
            ("N*5e", BasicPieceType.KNIGHT),
            ("S*5e", BasicPieceType.SILVER),
            ("G*5e", BasicPieceType.GOLD),
            ("B*5e", BasicPieceType.BISHOP),
            ("R*5e", BasicPieceType.ROOK),
        )
        for token, piece_type in cases:
            with self.subTest(token=token):
                try:
                    actual = parse_usi_move(token)
                except ValueError as error:
                    self.fail(f"有効な駒打ち表記を拒否しました: {error}")
                self.assertEqual(
                    actual,
                    DropMove(piece_type, Square(5, 5)),
                )

    def test_parse_rejects_king_drop(self):
        """持ち駒にできない玉の打ち表記を拒否する。

        BasicPieceTypeに玉があることをUSI駒打ちの許可と混同せず、
        局面に依存しない値変換の境界で拒否することを確認する。
        """
        with self.assertRaises(ValueError):
            parse_usi_move("K*5e")


class UsiMoveFormatTests(unittest.TestCase):
    def test_format_board_move_with_and_without_promotion(self):
        """成り指定の有無と座標端をUSI盤上移動表記へ戻す。

        promote値を落としたり、筋・段を逆順に出力したりせず、読み取りと
        同じ一手トークンを作ることを確認する。
        """
        cases = (
            (BoardMove(Square(7, 7), Square(7, 6), False), "7g7f"),
            (BoardMove(Square(8, 8), Square(2, 2), True), "8h2b+"),
            (BoardMove(Square(1, 1), Square(9, 9), False), "1a9i"),
        )
        for move, expected in cases:
            with self.subTest(move=move):
                self.assertEqual(format_usi_move(move), expected)

    def test_format_drop_move_for_each_hand_piece(self):
        """7種のDropMoveをUSI駒記号へ対応づける。

        出力記号と内部駒種の対応違いは、相手側が別の駒として読む原因に
        なるため、すべての持ち駒種で対応を確認する。
        """
        cases = (
            (BasicPieceType.PAWN, "P*5e"),
            (BasicPieceType.LANCE, "L*5e"),
            (BasicPieceType.KNIGHT, "N*5e"),
            (BasicPieceType.SILVER, "S*5e"),
            (BasicPieceType.GOLD, "G*5e"),
            (BasicPieceType.BISHOP, "B*5e"),
            (BasicPieceType.ROOK, "R*5e"),
        )
        for piece_type, expected in cases:
            move = DropMove(piece_type, Square(5, 5))
            with self.subTest(piece_type=piece_type):
                self.assertEqual(format_usi_move(move), expected)

    def test_parse_and_format_round_trip(self):
        """各種の正しいUSI一手が解析後も同じ表記へ戻る。

        読み取りと出力の対応が片方向だけずれていると、入力履歴と
        bestmove出力で表記が一致しなくなるため往復を確認する。
        """
        tokens = (
            "7g7f",
            "8h2b+",
            "1a9i",
            "P*5e",
            "L*5e",
            "N*5e",
            "S*5e",
            "G*5e",
            "B*5e",
            "R*5e",
        )
        for token in tokens:
            with self.subTest(token=token):
                self.assertEqual(format_usi_move(parse_usi_move(token)), token)

    def test_format_rejects_non_move_values(self):
        """Moveを構成しないオブジェクトをUSIへ形式化しない。

        型別の分岐で属性参照エラーなどを漏らさず、APIの失敗型を
        ValueErrorへ揃えることを確認する。
        """
        with self.assertRaises(ValueError):
            format_usi_move(object())

    def test_format_rejects_invalid_move_fields(self):
        """構成型のフィールドが型契約に反する値を拒否する。

        dataclassは実行時に注釈型を強制しないため、不正な座標や成り値、
        打ち駒種を誤ったトークンへ出力しないことを確認する。
        """
        invalid_moves = (
            BoardMove("1a", Square(1, 2), False),
            BoardMove(Square(1, 1), "1a", False),
            BoardMove(Square(1, 1), Square(1, 2), 1),
            DropMove("P", Square(5, 5)),
            DropMove(BasicPieceType.KING, Square(5, 5)),
            DropMove(BasicPieceType.PAWN, "5e"),
        )
        for move in invalid_moves:
            with self.subTest(move=move):
                with self.assertRaises(ValueError):
                    format_usi_move(move)


if __name__ == "__main__":
    unittest.main()
