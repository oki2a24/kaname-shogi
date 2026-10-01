"""CLIの指し手解析と対局進行を検証する。"""

import random
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from kaname_shogi.game_record import GameRecord, RecordedDrop, RecordedMove
from kaname_shogi.move import DropMove
from kaname_shogi import cli
from kaname_shogi.display import render_position
from kaname_shogi.model import (BasicPieceType, Board, Piece, PieceType,
                                Position, Side, Square, create_initial_position)


class CommandParsingTests(unittest.TestCase):
    def test_parses_help_command(self):
        """helpを公開コマンド型へ変換し、公開一覧の順序を保つ。

        単独helpの解析、HelpCommandの配置、大文字や余分な引数の形式エラーを確認し、
        公開境界の漏れや既存API順序の意図しない変更を検出する。
        """
        command = cli.parse_command("help")

        self.assertEqual(command, cli.HelpCommand())
        self.assertEqual(cli.__all__, (
            "GameMode", "choose_game_mode", "MoveCommand", "DropCommand",
            "ResignCommand", "SaveCommand", "LoadCommand", "HelpCommand",
            "Command", "parse_command", "run_game",
        ))
        for invalid in ("help now", "HELP"):
            with self.subTest(command=invalid):
                with self.assertRaisesRegex(
                        ValueError, "入力形式が正しくありません。"):
                    cli.parse_command(invalid)

    def test_parses_move_and_drop_with_halfwidth_or_fullwidth_input(self):
        """半角・全角の座標と空白を、移動・駒打ちの指示へ変換する。"""
        move = cli.parse_command("move　７　７　７　６")
        promoted = cli.parse_command("move 2 2 2 1 +")
        drop = cli.parse_command("drop　歩　５　５")

        self.assertIsInstance(move, cli.MoveCommand)
        self.assertEqual((move.source, move.destination, move.promote),
                         (Square(7, 7), Square(7, 6), False))
        self.assertIsInstance(promoted, cli.MoveCommand)
        self.assertEqual((promoted.source, promoted.destination,
                          promoted.promote),
                         (Square(2, 2), Square(2, 1), True))
        self.assertIsInstance(drop, cli.DropCommand)
        self.assertEqual((drop.piece_type, drop.destination),
                         (BasicPieceType.PAWN, Square(5, 5)))

    def test_parses_resign_command(self):
        """resignを公開投了型へ変換し、CLIの公開APIを明示する。"""
        command = cli.parse_command("resign")

        self.assertEqual(cli.__all__, (
            "GameMode", "choose_game_mode", "MoveCommand", "DropCommand",
            "ResignCommand", "SaveCommand", "LoadCommand", "HelpCommand",
            "Command", "parse_command", "run_game",
        ))
        self.assertIsInstance(command, cli.ResignCommand)

    def test_parses_save_and_load_commands(self):
        """save/loadの一語パスを、ファイル操作前の指示へ変換する。"""
        try:
            save = cli.parse_command("save records/game.json")
            load = cli.parse_command("load /tmp/game.json")
        except ValueError as error:
            self.fail(f"save/load入力が未実装です: {error}")

        self.assertIsInstance(save, cli.SaveCommand)
        self.assertEqual(save.path, "records/game.json")
        self.assertIsInstance(load, cli.LoadCommand)
        self.assertEqual(load.path, "/tmp/game.json")

    def test_rejects_save_and_load_without_one_path(self):
        """パスなし・空白を含むパスは入力形式エラーとして拒否する。"""
        for command in ("save", "load", "save a b", "load a b"):
            with self.subTest(command=command):
                with self.assertRaisesRegex(
                        ValueError, "入力形式が正しくありません。"):
                    cli.parse_command(command)

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


class GameModeMenuTests(unittest.TestCase):
    def test_choose_game_mode_maps_each_number_to_mode(self):
        """メニューの1・2・3を三つの対局形式へ対応付ける。"""
        expected = (
            ("1", "HUMAN_VS_HUMAN"),
            ("2", "HUMAN_VS_COMPUTER"),
            ("3", "COMPUTER_VS_COMPUTER"),
        )

        for value, mode_name in expected:
            with self.subTest(value=value):
                self.assertEqual(
                    cli.choose_game_mode(input_fn=ScriptedInput([value]),
                                         output_fn=lambda _: None),
                    getattr(cli.GameMode, mode_name),
                )

    def test_choose_game_mode_reprompts_after_invalid_choice(self):
        """無効な番号の後に、人間対コンピュータを選び直せる。"""
        outputs = []

        mode = cli.choose_game_mode(input_fn=ScriptedInput(["4", "2"]),
                                    output_fn=outputs.append)

        self.assertEqual(mode, cli.GameMode.HUMAN_VS_COMPUTER)
        self.assertIn("エラー：対局形式を1〜3で選んでください。", outputs)


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
    def test_help_displays_commands_and_reprompts_same_turn(self):
        """help表示後は案内を再表示して同じ手番から入力を続ける。

        helpが手番・局面・棋譜を消費せず、案内文や5コマンドの説明を欠かしたり、
        次の合法手まで入力を進めない誤りを検出する。
        """
        inputs = ScriptedInput(["help", "move 7 7 7 6", "resign"])
        outputs = []

        record = cli.run_game(mode=cli.GameMode.HUMAN_VS_HUMAN,
                              input_fn=inputs, output_fn=outputs.append)

        help_text = next(output for output in outputs if "move <出発筋>" in output)
        for expected in (
                "move <出発筋> <出発段> <到着筋> <到着段> [+]",
                "drop <歩|香|桂|銀|金|角|飛> <筋> <段>",
                "resign", "save <path>", "load <path>", "+",
                "全角数字", "空白を含まない一語", "保存成功後",
                "読込成功後"):
            with self.subTest(expected=expected):
                self.assertIn(expected, help_text)
        prompt = "指し手を入力してください（例: move 7 7 7 6）:"
        help_index = outputs.index(help_text)
        self.assertEqual(outputs[help_index + 1], prompt)
        self.assertEqual(inputs.calls, 3)
        self.assertEqual(record.moves,
                         (RecordedMove(Square(7, 7), Square(7, 6), False),))
        self.assertEqual(record.current_position.side_to_move, Side.GOTE)
        self.assertEqual(record.current_position.board.piece_at(Square(7, 6)),
                         Piece(PieceType.PAWN, Side.SENTE))

    def test_help_preserves_record_when_input_ends(self):
        """help後のEOFは開始局面と空の棋譜を保って終了する。

        ヘルプ表示を投了や勝敗として記録したり、EOF後に局面を変えたりする誤りを
        検出する。
        """
        inputs = ScriptedInput(["help"])
        outputs = []

        record = cli.run_game(mode=cli.GameMode.HUMAN_VS_HUMAN,
                              input_fn=inputs, output_fn=outputs.append)

        self.assertEqual(inputs.calls, 2)
        self.assertEqual(record.moves, ())
        self.assertEqual(render_position(record.current_position),
                         render_position(record.initial_position))
        self.assertEqual(outputs[-1], "入力を終了しました。")
        self.assertFalse(any("投了しました。" in output for output in outputs))
        self.assertFalse(any("勝ちです。" in output for output in outputs))

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

    def test_human_vs_human_reads_both_sides_and_records_both_moves(self):
        """人間対人間では、先手・後手の成功手を順に記録する。

        後手をコンピュータ扱いして入力を読まない誤りと、EOFを棋譜へ残す誤りを
        検出する。
        """
        inputs = ScriptedInput(["move 7 7 7 6", "move 3 3 3 4"])

        record = cli.run_game(
            mode=cli.GameMode.HUMAN_VS_HUMAN,
            input_fn=inputs,
            output_fn=lambda _: None,
        )

        self.assertEqual(inputs.calls, 3)
        self.assertEqual(record.moves, (
            RecordedMove(Square(7, 7), Square(7, 6), False),
            RecordedMove(Square(3, 3), Square(3, 4), False),
        ))

    def test_computer_vs_computer_plays_alternately_until_ctrl_c(self):
        """コンピュータ対コンピュータは、交互に二手指してCtrl-Cで中断する。

        自動手でCtrl-Cを捕捉できない誤りと、入力を読んだり中断を棋譜へ残したり
        する誤りを検出する。
        """
        class InterruptingRandom(random.Random):
            def __init__(self):
                super().__init__(20260927)
                self.choice_calls = 0

            def choice(self, sequence):
                self.choice_calls += 1
                if self.choice_calls == 3:
                    raise KeyboardInterrupt
                return super().choice(sequence)

        inputs = ScriptedInput([])
        outputs = []

        record = cli.run_game(
            mode=cli.GameMode.COMPUTER_VS_COMPUTER,
            input_fn=inputs,
            output_fn=outputs.append,
            rng=InterruptingRandom(),
        )

        self.assertEqual(inputs.calls, 0)
        self.assertEqual(len(record.moves), 2)
        self.assertEqual(record.current_position.side_to_move, Side.SENTE)
        self.assertIn("入力を終了しました。", outputs)

    def test_human_vs_human_does_not_consume_rng(self):
        """人間対人間では注入した乱数生成器を消費しない。"""
        class FailingRandom(random.Random):
            def choice(self, sequence):
                raise AssertionError("人間対人間でchoiceを呼んではいけません")

        cli.run_game(mode=cli.GameMode.HUMAN_VS_HUMAN,
                     input_fn=ScriptedInput(["move 7 7 7 6", "move 3 3 3 4"]),
                     output_fn=lambda _: None, rng=FailingRandom())

    def test_computer_vs_computer_stops_without_winner_when_no_legal_move(self):
        """自動対局の合法手空一覧は入力せず勝者なしで停止する。"""
        inputs = ScriptedInput([])
        outputs = []
        with patch.object(cli, "legal_moves", return_value=()):
            record = cli.run_game(mode=cli.GameMode.COMPUTER_VS_COMPUTER,
                                  input_fn=inputs, output_fn=outputs.append)

        self.assertEqual(inputs.calls, 0)
        self.assertEqual(record.moves, ())
        self.assertFalse(any("勝ちです。" in line for line in outputs))

    def test_human_sente_move_is_followed_by_one_computer_gote_move(self):
        """先手の成功手の後に、後手のコンピュータが一手だけ指す。

        後手入力を要求するまま残る誤りと、同じ側が続けて指す誤りを検出する。
        """
        inputs = ScriptedInput(["move 7 7 7 6"])
        outputs = []

        record = cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertEqual(inputs.calls, 2)
        self.assertEqual(len(record.moves), 2)
        self.assertEqual(record.moves[0], RecordedMove(Square(7, 7),
                                                        Square(7, 6), False))
        self.assertEqual(record.current_position.side_to_move, Side.SENTE)
        self.assertTrue(any(line.startswith("後手の指し手: ")
                            for line in outputs))

    def test_fixed_rng_reproduces_computer_move(self):
        """同じ乱数種の対局は、コンピュータ手と表示を再現する。

        乱数生成器を手ごとに作り直す誤りと、テストから注入できない設計を検出する。
        """
        outputs_a = []
        outputs_b = []
        record_a = cli.run_game(
            input_fn=ScriptedInput(["move 7 7 7 6"]),
            output_fn=outputs_a.append,
            rng=random.Random(20260926),
        )
        record_b = cli.run_game(
            input_fn=ScriptedInput(["move 7 7 7 6"]),
            output_fn=outputs_b.append,
            rng=random.Random(20260926),
        )

        self.assertEqual(record_a.moves, record_b.moves)
        self.assertEqual(outputs_a, outputs_b)

    def test_explicit_human_vs_computer_matches_default_mode(self):
        """明示した人間対コンピュータは既定値と棋譜・表示が同じになる。"""
        default_outputs = []
        explicit_outputs = []
        default_record = cli.run_game(input_fn=ScriptedInput(["move 7 7 7 6"]),
                                      output_fn=default_outputs.append,
                                      rng=random.Random(20260927))
        explicit_record = cli.run_game(
            mode=cli.GameMode.HUMAN_VS_COMPUTER,
            input_fn=ScriptedInput(["move 7 7 7 6"]),
            output_fn=explicit_outputs.append,
            rng=random.Random(20260927),
        )

        self.assertEqual(explicit_record.moves, default_record.moves)
        self.assertEqual(explicit_outputs, default_outputs)

    def test_one_rng_is_reused_for_multiple_computer_moves(self):
        """一局の複数の自動手で同じ乱数生成器を使い続ける。

        自動手ごとに乱数生成器を作り直して同じ初期状態へ戻す誤りを検出する。
        """
        class CountingRandom(random.Random):
            def __init__(self):
                super().__init__(20260926)
                self.choice_calls = 0

            def choice(self, sequence):
                self.choice_calls += 1
                return super().choice(sequence)

        rng = CountingRandom()
        inputs = ScriptedInput(["move 7 7 7 6", "move 2 7 2 6"])
        outputs = []

        record = cli.run_game(input_fn=inputs, output_fn=outputs.append,
                              rng=rng)

        self.assertEqual(rng.choice_calls, 2)
        self.assertEqual(len(record.moves), 4)

    def test_displays_human_board_then_computer_move_then_computer_board(self):
        """人間手後の盤面、自動手、自動手後の盤面を順番に表示する。

        自動手を盤面更新後に表示する誤りと、次の入力案内を先に出す誤りを検出する。
        """
        outputs = []
        cli.run_game(input_fn=ScriptedInput(["move 7 7 7 6"]),
                     output_fn=outputs.append,
                     rng=random.Random(20260926))

        gote_boards = [i for i, line in enumerate(outputs)
                       if line.startswith("手番：後手")]
        computer_moves = [i for i, line in enumerate(outputs)
                          if line.startswith("後手の指し手: ")]
        sente_boards = [i for i, line in enumerate(outputs)
                        if line.startswith("手番：先手")]
        prompts = [i for i, line in enumerate(outputs)
                   if line.startswith("指し手を入力してください")]

        self.assertEqual(len(gote_boards), 1)
        self.assertEqual(len(computer_moves), 1)
        self.assertGreater(computer_moves[0], gote_boards[0])
        self.assertGreater(sente_boards[-1], computer_moves[0])
        self.assertGreater(prompts[-1], sente_boards[-1])

    def test_stops_without_winner_when_computer_has_no_legal_move(self):
        """詰みでない合法手空一覧は、勝敗なしの異常終了として扱う。

        選択器のNoneを投了や勝敗へ変換する誤りを検出する。
        """
        inputs = ScriptedInput(["move 7 7 7 6"])
        outputs = []

        with patch.object(cli, "legal_moves", return_value=()):
            record = cli.run_game(input_fn=inputs, output_fn=outputs.append,
                                  rng=random.Random(20260926))

        self.assertEqual(inputs.calls, 1)
        self.assertEqual(len(record.moves), 1)
        self.assertIn("コンピュータの合法手がありません。", outputs)
        self.assertFalse(any("勝ちです。" in output for output in outputs))
        self.assertFalse(any("投了しました。" in output for output in outputs))

    def test_records_computer_drop_move(self):
        """コンピュータの駒打ちを表示し、GameRecordへ記録する。

        盤上移動だけを自動手の適用対象にし、駒打ちを落とす誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 1), Piece(PieceType.KING, Side.GOTE))
        board.set_piece(Square(7, 7), Piece(PieceType.PAWN, Side.SENTE))
        position = Position(board, Side.SENTE)
        position.gote_hand.add(BasicPieceType.PAWN)
        inputs = ScriptedInput(["move 7 7 7 6"])
        outputs = []

        with patch.object(cli, "create_initial_position",
                          return_value=position, create=True), \
                patch.object(cli, "legal_moves",
                             return_value=(DropMove(BasicPieceType.PAWN,
                                                    Square(5, 5)),)):
            record = cli.run_game(input_fn=inputs, output_fn=outputs.append,
                                  rng=random.Random(20260926))

        self.assertEqual(record.moves[1],
                         RecordedDrop(BasicPieceType.PAWN, Square(5, 5)))
        self.assertIn("後手の指し手: drop 歩 5 5", outputs)
        self.assertEqual(record.current_position.board.piece_at(Square(5, 5)),
                         Piece(PieceType.PAWN, Side.GOTE))

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

    def test_save_keeps_position_and_reprompts_same_human_turn(self):
        """save成功後は記録を変えず、同じ人間手番で入力を受け直す。"""
        with TemporaryDirectory() as directory:
            path = f"{directory}/record.json"
            inputs = ScriptedInput([
                f"save {path}",
                "move 7 7 7 6",
            ])
            outputs = []

            try:
                record = cli.run_game(
                    mode=cli.GameMode.HUMAN_VS_HUMAN,
                    input_fn=inputs,
                    output_fn=outputs.append,
                )
            except AttributeError as error:
                self.fail(f"save/load進行が未実装です: {error}")

            saved = GameRecord.load(path)

        self.assertEqual(saved.moves, ())
        self.assertEqual(record.moves, (
            RecordedMove(Square(7, 7), Square(7, 6), False),
        ))
        self.assertIn("棋譜を保存しました。", outputs)
        self.assertEqual(record.current_position.side_to_move, Side.GOTE)

    def test_load_replaces_record_displays_position_and_reprompts_loaded_turn(self):
        """load成功後は記録を置換して局面を表示し、読込後の手番で進める。"""
        loaded_record = GameRecord(create_initial_position())
        loaded_record.apply_move(Square(2, 7), Square(2, 6))

        with TemporaryDirectory() as directory:
            path = f"{directory}/record.json"
            loaded_record.save(path)
            inputs = ScriptedInput([
                "move 7 7 7 6",
                f"load {path}",
                "resign",
            ])
            outputs = []

            try:
                record = cli.run_game(
                    mode=cli.GameMode.HUMAN_VS_HUMAN,
                    input_fn=inputs,
                    output_fn=outputs.append,
                )
            except AttributeError as error:
                self.fail(f"save/load進行が未実装です: {error}")

        self.assertEqual(record.moves, (
            RecordedMove(Square(2, 7), Square(2, 6), False),
        ))
        self.assertIsNone(record.current_position.board.piece_at(
            Square(7, 6)))
        self.assertEqual(record.current_position.side_to_move, Side.GOTE)
        self.assertIn("棋譜を読み込みました。", outputs)
        load_index = outputs.index("棋譜を読み込みました。")
        self.assertEqual(outputs[load_index + 1],
                         render_position(loaded_record.current_position))

    def test_load_to_computer_turn_plays_and_records_computer_move(self):
        """load後がコンピュータ手番なら自動手を表示して履歴へ追加する。"""
        loaded_record = GameRecord(create_initial_position())
        loaded_record.apply_move(Square(2, 7), Square(2, 6))

        with TemporaryDirectory() as directory:
            path = f"{directory}/record.json"
            loaded_record.save(path)
            inputs = ScriptedInput([
                f"load {path}",
                "resign",
            ])
            outputs = []

            record = cli.run_game(
                mode=cli.GameMode.HUMAN_VS_COMPUTER,
                input_fn=inputs,
                output_fn=outputs.append,
                rng=random.Random(20260927),
            )

        self.assertEqual(record.moves[0],
                         RecordedMove(Square(2, 7), Square(2, 6), False))
        self.assertEqual(len(record.moves), 2)
        self.assertTrue(any(line.startswith("後手の指し手: ")
                            for line in outputs))

    def test_appends_human_move_after_loaded_record(self):
        """load後の成功手を、読込済み履歴の末尾へ追加する。"""
        loaded_record = GameRecord(create_initial_position())
        loaded_record.apply_move(Square(2, 7), Square(2, 6))

        with TemporaryDirectory() as directory:
            path = f"{directory}/record.json"
            loaded_record.save(path)
            inputs = ScriptedInput([
                f"load {path}",
                "move 3 3 3 4",
            ])

            record = cli.run_game(
                mode=cli.GameMode.HUMAN_VS_HUMAN,
                input_fn=inputs,
                output_fn=lambda _: None,
            )

        self.assertEqual(record.moves, (
            RecordedMove(Square(2, 7), Square(2, 6), False),
            RecordedMove(Square(3, 3), Square(3, 4), False),
        ))

    def test_reprompts_without_replacing_record_after_load_error(self):
        """load失敗は元の記録を保ち、同じ人間手番で再入力する。"""
        with TemporaryDirectory() as directory:
            path = f"{directory}/missing/record.json"
            inputs = ScriptedInput([
                "move 7 7 7 6",
                f"load {path}",
                "move 3 3 3 4",
            ])
            outputs = []

            try:
                record = cli.run_game(
                    mode=cli.GameMode.HUMAN_VS_HUMAN,
                    input_fn=inputs,
                    output_fn=outputs.append,
                )
            except AttributeError as error:
                self.fail(f"save/load進行が未実装です: {error}")

        self.assertEqual(record.moves, (
            RecordedMove(Square(7, 7), Square(7, 6), False),
            RecordedMove(Square(3, 3), Square(3, 4), False),
        ))
        self.assertTrue(any(line.startswith("エラー：") for line in outputs))

    def test_reprompts_without_replacing_record_after_invalid_json(self):
        """不正JSONのload失敗も元の記録を保ち、同じ手番で再入力する。"""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{", encoding="utf-8")
            inputs = ScriptedInput([
                "move 7 7 7 6",
                f"load {path}",
                "move 3 3 3 4",
            ])
            outputs = []

            record = cli.run_game(
                mode=cli.GameMode.HUMAN_VS_HUMAN,
                input_fn=inputs,
                output_fn=outputs.append,
            )

        self.assertEqual(record.moves, (
            RecordedMove(Square(7, 7), Square(7, 6), False),
            RecordedMove(Square(3, 3), Square(3, 4), False),
        ))
        self.assertTrue(any(line.startswith("エラー：") for line in outputs))

    def test_reprompts_after_save_file_error_without_changing_record(self):
        """save失敗は記録を保ち、同じ人間手番で再入力する。"""
        with TemporaryDirectory() as directory:
            path = f"{directory}/missing/record.json"
            inputs = ScriptedInput([
                "move 7 7 7 6",
                f"save {path}",
                "move 3 3 3 4",
            ])
            outputs = []

            try:
                record = cli.run_game(
                    mode=cli.GameMode.HUMAN_VS_HUMAN,
                    input_fn=inputs,
                    output_fn=outputs.append,
                )
            except AttributeError as error:
                self.fail(f"save/load進行が未実装です: {error}")

        self.assertEqual(record.moves, (
            RecordedMove(Square(7, 7), Square(7, 6), False),
            RecordedMove(Square(3, 3), Square(3, 4), False),
        ))
        self.assertTrue(any(line.startswith("エラー：") for line in outputs))

    def test_does_not_read_save_or_load_after_checkmate(self):
        """詰み後はsave/loadを含む入力を読まず、終局表示で停止する。"""
        inputs = ScriptedInput(["save ignored.json"])
        outputs = []

        with patch.object(cli, "create_initial_position",
                          side_effect=self._mated_sente_position, create=True):
            cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertEqual(inputs.calls, 0)
        self.assertIn("詰みです。後手の勝ちです。", outputs)

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
            record = cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertIsNotNone(record, "run_gameが対局記録を返していません")
        if record is None:
            return
        self.assertEqual(record.moves[0],
                         RecordedDrop(BasicPieceType.PAWN, Square(5, 5)))
        self.assertEqual(len(record.moves), 2)
        self.assertEqual(record.current_position.board.piece_at(Square(5, 5)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(record.current_position.sente_hand.count(
            BasicPieceType.PAWN), 0)

    def test_returns_record_with_successful_moves_on_eof(self):
        """EOF時に成功手を含む対局記録を返す。

        CLI表示だけで履歴を失わず、終了時点の局面と順序どおりの記録を呼び出し側へ
        渡せることを検出する。
        """
        inputs = ScriptedInput(["move 7 7 7 6"])
        outputs = []

        record = cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertIsNotNone(record, "run_gameが対局記録を返していません")
        if record is None:
            return
        self.assertEqual(record.moves[0],
                         RecordedMove(Square(7, 7), Square(7, 6), False))
        self.assertEqual(len(record.moves), 2)
        self.assertEqual(record.current_position.side_to_move, Side.SENTE)

    def test_returns_empty_record_when_sente_resigns(self):
        """投了時に空の対局記録を返す。

        投了は指し手履歴へ含めず、開始局面から変化していない記録を呼び出し側へ
        渡すことを検出する。
        """
        inputs = ScriptedInput(["resign"])
        outputs = []

        record = cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertIsNotNone(record, "run_gameが対局記録を返していません")
        if record is None:
            return
        self.assertEqual(record.moves, ())
        initial = record.position_at(0)
        current = record.current_position
        self.assertEqual(current.side_to_move, Side.SENTE)
        for square in (Square(7, 7), Square(2, 8), Square(5, 9),
                       Square(5, 1)):
            self.assertEqual(current.board.piece_at(square),
                             initial.board.piece_at(square))

    def test_stops_when_sente_resigns_without_changing_position(self):
        """先手が投了すると、局面を変えず後手の勝ちを表示して終了する。"""
        position = create_initial_position()
        position.sente_hand.add(BasicPieceType.PAWN)
        inputs = ScriptedInput(["resign"])
        outputs = []

        with patch.object(cli, "create_initial_position",
                          return_value=position, create=True):
            record = cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertIsNotNone(record, "run_gameが対局記録を返していません")
        if record is None:
            return
        self.assertEqual(inputs.calls, 1)
        self.assertEqual(record.current_position.side_to_move, Side.SENTE)
        self.assertEqual(record.current_position.board.piece_at(Square(7, 7)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(record.current_position.sente_hand.count(
            BasicPieceType.PAWN), 1)
        self.assertIn("先手が投了しました。後手の勝ちです。", outputs)
        self.assertNotIn("入力を終了しました。", outputs)

    def test_stops_when_sente_resigns_after_computer_move(self):
        """コンピュータ手の後に先手が投了すると、後手の勝ちを表示して終了する。

        コンピュータへ投了入力を要求せず、人間の投了だけを受け付けることを検出する。
        """
        position = create_initial_position()
        inputs = ScriptedInput(["move 7 7 7 6", "resign"])
        outputs = []

        with patch.object(cli, "create_initial_position",
                          return_value=position, create=True):
            record = cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertIsNotNone(record, "run_gameが対局記録を返していません")
        if record is None:
            return
        self.assertEqual(inputs.calls, 2)
        self.assertEqual(record.current_position.side_to_move, Side.SENTE)
        self.assertEqual(record.current_position.board.piece_at(Square(7, 6)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(len(record.moves), 2)
        self.assertIn("先手が投了しました。後手の勝ちです。", outputs)
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

        record = cli.run_game(input_fn=interrupt, output_fn=outputs.append)

        self.assertEqual(record.moves, ())
        self.assertEqual(record.current_position.side_to_move, Side.SENTE)
        self.assertEqual(outputs[-1], "入力を終了しました。")
        self.assertFalse(any("投了しました。" in output for output in outputs))
        self.assertFalse(any("勝ちです。" in output for output in outputs))

    def test_returns_record_when_position_is_already_checkmate(self):
        """開始時点の詰みでも空の対局記録を返す。

        入力を読まずに終局する分岐でも、呼び出し側が局面を再現できる記録を
        受け取れることを検出する。
        """
        inputs = ScriptedInput([])
        outputs = []

        with patch.object(cli, "create_initial_position",
                          side_effect=self._mated_sente_position, create=True):
            record = cli.run_game(input_fn=inputs, output_fn=outputs.append)

        self.assertEqual(inputs.calls, 0)
        self.assertEqual(record.moves, ())
        self.assertEqual(record.current_position.side_to_move, Side.SENTE)
        self.assertIn("詰みです。後手の勝ちです。", outputs)
