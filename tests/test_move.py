"""中立な指し手データの値と不変性を検証する。"""

from dataclasses import FrozenInstanceError
import unittest

from kaname_shogi.model import BasicPieceType, Square

try:
    from kaname_shogi.move import BoardMove, DropMove, Move
except ModuleNotFoundError as error:
    if error.name != "kaname_shogi.move":
        raise
    BoardMove = DropMove = Move = None


class MoveDataTests(unittest.TestCase):
    def _require_implementation(self):
        """一手データの実装不足を読み込みエラーでなく明示的に失敗させる。"""
        if BoardMove is None or DropMove is None or Move is None:
            self.fail("中立な指し手データがまだ実装されていません")

    def test_board_move_keeps_values_and_is_immutable(self):
        """盤上移動は出発・到着・成り指定を変更不可の値として保持する。

        指し手を局面変更の操作や可変な入力解析結果と混同せず、後から値を
        書き換えられないデータとして扱えることを確認する。
        """
        self._require_implementation()
        move = BoardMove(Square(7, 7), Square(7, 6), False)

        self.assertEqual(move.source, Square(7, 7))
        self.assertEqual(move.destination, Square(7, 6))
        self.assertFalse(move.promote)
        with self.assertRaises(FrozenInstanceError):
            move.promote = True

    def test_drop_move_keeps_values_and_is_immutable(self):
        """駒打ちは駒種・打ち先を変更不可の値として保持する。

        盤上移動とは異なる駒打ちも、外部形式の文字列ではなく同じ一手の
        データ境界で扱えることを確認する。
        """
        self._require_implementation()
        move = DropMove(BasicPieceType.PAWN, Square(5, 5))

        self.assertEqual(move.piece_type, BasicPieceType.PAWN)
        self.assertEqual(move.destination, Square(5, 5))
        with self.assertRaises(FrozenInstanceError):
            move.destination = Square(5, 4)


if __name__ == "__main__":
    unittest.main()
