"""対局記録の履歴と更新を検証する。"""

import unittest

from kaname_shogi.model import (BasicPieceType, Board, Piece, PieceType,
                                Position, Side, Square,
                                create_initial_position)

try:
    from kaname_shogi.game_record import (GameRecord, RecordedDrop,
                                          RecordedMove)
except ModuleNotFoundError as error:
    if error.name != "kaname_shogi.game_record":
        raise
    GameRecord = RecordedDrop = RecordedMove = None


class GameRecordTests(unittest.TestCase):
    def _require_implementation(self):
        """未実装APIを読み込みエラーではなく機能不足として失敗させる。"""
        if GameRecord is None:
            self.fail("GameRecordの対局記録機能が未実装です")

    def test_records_successful_board_moves_in_order(self):
        """成功した盤上移動を順番どおりに履歴へ追加する。

        盤上移動の値と手番更新を同時に確認し、CLIや別形式の文字列ではなく
        既存の筋・段の値を記録することを検出する。
        """
        self._require_implementation()
        record = GameRecord(create_initial_position())

        record.apply_move(Square(7, 7), Square(7, 6))
        record.apply_move(Square(3, 3), Square(3, 4))

        self.assertEqual(record.moves, (
            RecordedMove(Square(7, 7), Square(7, 6), False),
            RecordedMove(Square(3, 3), Square(3, 4), False),
        ))
        self.assertEqual(record.current_position.side_to_move, Side.SENTE)

    def test_records_successful_drop_after_updating_position(self):
        """成功した駒打ちを履歴へ追加し、持ち駒と盤面を更新する。

        盤上移動とは異なる駒打ちも記録対象であることと、既存の駒打ち規則へ
        委譲することを検出する。
        """
        self._require_implementation()
        board = Board()
        board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 1), Piece(PieceType.KING, Side.GOTE))
        position = Position(board, Side.SENTE)
        position.sente_hand.add(BasicPieceType.PAWN)
        record = GameRecord(position)

        record.apply_drop(BasicPieceType.PAWN, Square(5, 5))

        self.assertEqual(record.moves, (
            RecordedDrop(BasicPieceType.PAWN, Square(5, 5)),
        ))
        current = record.current_position
        self.assertEqual(current.board.piece_at(Square(5, 5)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(current.sente_hand.count(BasicPieceType.PAWN), 0)
        self.assertEqual(current.side_to_move, Side.GOTE)

    def test_rejected_move_does_not_change_record(self):
        """失敗した盤上移動では履歴と現在局面を変更しない。

        到着マスが移動候補でない合法性エラーを使い、失敗後に同じ手番で再入力
        できる状態を保存層が壊さないことを検出する。
        """
        self._require_implementation()
        record = GameRecord(create_initial_position())
        before = record.current_position

        with self.assertRaisesRegex(ValueError, "移動先候補"):
            record.apply_move(Square(7, 7), Square(7, 8))

        self.assertEqual(record.moves, ())
        after = record.current_position
        self.assertEqual(after.side_to_move, Side.SENTE)
        for file in range(1, 10):
            for rank in range(1, 10):
                square = Square(file, rank)
                self.assertEqual(after.board.piece_at(square),
                                 before.board.piece_at(square))
        for piece_type in (BasicPieceType.PAWN, BasicPieceType.LANCE,
                           BasicPieceType.KNIGHT, BasicPieceType.SILVER,
                           BasicPieceType.GOLD, BasicPieceType.BISHOP,
                           BasicPieceType.ROOK):
            self.assertEqual(after.sente_hand.count(piece_type),
                             before.sente_hand.count(piece_type))
            self.assertEqual(after.gote_hand.count(piece_type),
                             before.gote_hand.count(piece_type))


if __name__ == "__main__":
    unittest.main()
