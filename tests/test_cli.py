"""CLIの指し手解析と対局進行を検証する。"""

import unittest
from unittest.mock import patch

from kaname_shogi import cli
from kaname_shogi.model import (BasicPieceType, Board, Piece, PieceType,
                                Position, Side, Square, create_initial_position)


class CommandParsingTests(unittest.TestCase):
    def test_parses_move_and_drop_with_halfwidth_or_fullwidth_input(self):
        """半角・全角の座標と空白を、移動・駒打ちの指示へ変換する。"""
        move = cli.parse_command("move　７　７　７　６")
        promoted = cli.parse_command("move 2 2 2 1 +")
        drop = cli.parse_command("drop　歩　５　５")

        self.assertEqual((move.source, move.destination, move.promote),
                         (Square(7, 7), Square(7, 6), False))
        self.assertEqual((promoted.source, promoted.destination,
                          promoted.promote),
                         (Square(2, 2), Square(2, 1), True))
        self.assertEqual((drop.piece_type, drop.destination),
                         (BasicPieceType.PAWN, Square(5, 5)))

    def test_parses_resign_command(self):
        """resignを、局面を変更しない投了指示へ変換する。"""
        command = cli.parse_command("resign")

        self.assertIsInstance(command, cli._ResignCommand)

    def test_rejects_invalid_command_format(self):
        """未知の操作語・記号・引数・座標を入力形式エラーとして拒否する。"""
        invalid_commands = (
            "",
            "ｍｏｖｅ 7 7 7 6",
            "move 7 7 7 6 ＋",
            "move 7 7 7",
            "move 7 7 7 6 extra",
            "resign now",
            "ｒｅｓｉｇｎ",
            "drop 王 5 5",
            "drop 歩 10 5",
        )

        for command in invalid_commands:
            with self.subTest(command=command):
                with self.assertRaisesRegex(ValueError,
                                             "入力形式が正しくありません。"):
                    cli.parse_command(command)


class ScriptedInput:
    """テスト用に入力列を返し、列が尽きたらEOFを発生させる。"""

    def __init__(self, values):
        self._values = iter(values)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        try:
            return next(self._values)
        except StopIteration as error:
            raise EOFError from error


class GameplayTests(unittest.TestCase):
    def _mated_sente_position(self):
        """先手玉が飛車王手を防げない局面を作る。"""
        board = Board()
        board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 8), Piece(PieceType.ROOK, Side.GOTE))
        board.set_piece(Square(6, 7), Piece(PieceType.GOLD, Side.GOTE))
        for square in (Square(4, 8), Square(6, 8),
                       Square(4, 9), Square(6, 9)):
            board.set_piece(square, Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(9, 1), Piece(PieceType.KING, Side.GOTE))
        return Position(board, Side.SENTE)

    def _mate_after_sente_rook_move(self):
        """先手の５三飛から５二飛で後手を詰ます局面を作る。"""
        board = Board()
        board.set_piece(Square(5, 1), Piece(PieceType.KING, Side.GOTE))
        board.set_piece(Square(9, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 3), Piece(PieceType.ROOK, Side.SENTE))
        board.set_piece(Square(4, 3), Piece(PieceType.GOLD, Side.SENTE))
        for square in (Square(4, 1), Square(6, 1),
                       Square(4, 2), Square(6, 2)):
            board.set_piece(square, Piece(PieceType.PAWN, Side.GOTE))
        return Position(board, Side.SENTE)

    def test_reprompts_after_format_and_legality_errors(self):
        """形式エラーと合法性エラーの後も、同じ手番で合法手を受け付ける。"""
        outputs = []
        inputs = ScriptedInput(["move 7", "move 7 7 7 8",
                                "move 7 7 7 6", "move 3 3 3 4"])

        cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertIn("エラー：入力形式が正しくありません。", outputs)
        self.assertIn("エラー：到着マスは出発駒の移動先候補に含まれません",
                      outputs)
        self.assertEqual(sum("手番：後手" in output for output in outputs), 1)
        self.assertEqual(sum("手番：先手" in output for output in outputs), 2)

    def test_applies_drop_command_to_position(self):
        """drop入力を既存の駒打ちへ渡し、持ち駒と盤面を更新する。"""
        board = Board()
        board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 1), Piece(PieceType.KING, Side.GOTE))
        position = Position(board, Side.SENTE)
        position.sente_hand.add(BasicPieceType.PAWN)
        inputs = ScriptedInput(["drop 歩 5 5"])
        outputs = []

        with patch.object(cli, "create_initial_position",
                          return_value=position, create=True):
            cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertEqual(position.board.piece_at(Square(5, 5)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(position.sente_hand.count(BasicPieceType.PAWN), 0)

    def test_stops_when_sente_resigns_without_changing_position(self):
        """先手が投了すると、局面を変えず後手の勝ちを表示して終了する。"""
        position = create_initial_position()
        position.sente_hand.add(BasicPieceType.PAWN)
        inputs = ScriptedInput(["resign"])
        outputs = []

        with patch.object(cli, "create_initial_position",
                          return_value=position, create=True):
            cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertEqual(inputs.calls, 1)
        self.assertEqual(position.side_to_move, Side.SENTE)
        self.assertEqual(position.board.piece_at(Square(7, 7)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(position.sente_hand.count(BasicPieceType.PAWN), 1)
        self.assertIn("先手が投了しました。後手の勝ちです。", outputs)
        self.assertNotIn("入力を終了しました。", outputs)

    def test_stops_when_gote_resigns_after_sente_move(self):
        """後手が投了すると、後手の投了と先手の勝ちを表示して終了する。"""
        position = create_initial_position()
        inputs = ScriptedInput(["move 7 7 7 6", "resign"])
        outputs = []

        with patch.object(cli, "create_initial_position",
                          return_value=position, create=True):
            cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertEqual(inputs.calls, 2)
        self.assertEqual(position.side_to_move, Side.GOTE)
        self.assertEqual(position.board.piece_at(Square(7, 6)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertIn("後手が投了しました。先手の勝ちです。", outputs)
        self.assertNotIn("入力を終了しました。", outputs)

    def test_stops_without_input_when_position_is_already_checkmate(self):
        """開始時点で詰みなら入力を読まず、勝者を表示して終了する。"""
        inputs = ScriptedInput([])
        outputs = []

        with patch.object(cli, "create_initial_position",
                          side_effect=self._mated_sente_position, create=True):
            cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertEqual(inputs.calls, 0)
        self.assertIn("詰みです。後手の勝ちです。", outputs)

    def test_stops_after_a_move_gives_checkmate(self):
        """合法手で詰みになった後は次の入力を読まず、勝者を表示する。"""
        position = self._mate_after_sente_rook_move()
        inputs = ScriptedInput(["move 5 3 5 2"])
        outputs = []

        with patch.object(cli, "create_initial_position",
                          return_value=position, create=True):
            cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertEqual(inputs.calls, 1)
        self.assertIn("詰みです。先手の勝ちです。", outputs)

    def test_finishes_normally_on_eof(self):
        """EOFは勝敗にせず、終了メッセージを表示して正常終了する。"""
        inputs = ScriptedInput([])
        outputs = []

        cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertEqual(inputs.calls, 1)
        self.assertEqual(outputs[-1], "入力を終了しました。")
        self.assertFalse(any("投了しました。" in output for output in outputs))
        self.assertFalse(any("勝ちです。" in output for output in outputs))

    def test_finishes_normally_on_keyboard_interrupt(self):
        """Ctrl-Cは勝敗にせず、終了メッセージを表示して正常終了する。"""
        outputs = []

        def interrupt():
            raise KeyboardInterrupt

        cli.run_game(input_fn=interrupt, output_fn=outputs.append)

        self.assertEqual(outputs[-1], "入力を終了しました。")
        self.assertFalse(any("投了しました。" in output for output in outputs))
        self.assertFalse(any("勝ちです。" in output for output in outputs))
