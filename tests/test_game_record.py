"""対局記録の履歴と更新を検証する。"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
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

    def test_rejected_drop_does_not_change_record(self):
        """失敗した駒打ちでは履歴と現在局面を変更しない。

        持ち駒不足による合法性エラーを使い、盤上移動だけでなく駒打ちでも失敗した
        入力を棋譜へ追加しないことを検出する。
        """
        self._require_implementation()
        record = GameRecord(create_initial_position())
        before = record.current_position

        with self.assertRaisesRegex(ValueError, "持ち駒"):
            record.apply_drop(BasicPieceType.ROOK, Square(5, 5))

        self.assertEqual(record.moves, ())
        after = record.current_position
        self.assertEqual(after.side_to_move, before.side_to_move)
        for file in range(1, 10):
            for rank in range(1, 10):
                square = Square(file, rank)
                self.assertEqual(after.board.piece_at(square),
                                 before.board.piece_at(square))

    def test_exposed_positions_are_independent_copies(self):
        """開始局面・現在局面の返却値を変更しても記録内部を変更しない。

        呼び出し側が表示用の局面へ駒や持ち駒を追加しても、履歴の基準となる
        開始局面と最新の現在局面が共有されないことを検出する。
        """
        self._require_implementation()
        record = GameRecord(create_initial_position())
        record.apply_move(Square(7, 7), Square(7, 6))

        initial = getattr(record, "initial_position", None)
        self.assertIsNotNone(initial, "開始局面の読み取り値が未実装です")
        if initial is None:
            return
        initial.board.set_piece(Square(1, 5),
                                Piece(PieceType.ROOK, Side.SENTE))
        current = record.current_position
        current.board.set_piece(Square(1, 5),
                                Piece(PieceType.ROOK, Side.SENTE))
        current.sente_hand.add(BasicPieceType.PAWN)

        self.assertIsNone(record.initial_position.board.piece_at(Square(1, 5)))
        self.assertIsNone(record.current_position.board.piece_at(Square(1, 5)))
        self.assertEqual(record.current_position.sente_hand.count(
            BasicPieceType.PAWN), 0)

    def test_replays_position_at_each_recorded_move(self):
        """開始局面から任意の手数まで適用した局面を再現する。

        途中局面を最新局面の参照で済ませず、履歴の先頭から指定手数までを
        既存の局面操作で再適用することを検出する。
        """
        self._require_implementation()
        record = GameRecord(create_initial_position())
        record.apply_move(Square(7, 7), Square(7, 6))
        record.apply_move(Square(3, 3), Square(3, 4))

        position_at = getattr(record, "position_at", None)
        self.assertIsNotNone(position_at, "局面再現操作が未実装です")
        if position_at is None:
            return
        position_zero = position_at(0)
        position_one = position_at(1)
        position_two = position_at(2)

        self.assertEqual(position_zero.side_to_move, Side.SENTE)
        self.assertEqual(position_zero.board.piece_at(Square(7, 7)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertIsNone(position_zero.board.piece_at(Square(7, 6)))
        self.assertEqual(position_one.side_to_move, Side.GOTE)
        self.assertEqual(position_one.board.piece_at(Square(7, 6)),
                         Piece(PieceType.PAWN, Side.SENTE))
        self.assertEqual(position_two.side_to_move, Side.SENTE)
        self.assertEqual(position_two.board.piece_at(Square(3, 4)),
                         Piece(PieceType.PAWN, Side.GOTE))

    def test_rejects_position_at_outside_recorded_range(self):
        """履歴の範囲外の手数を局面再現から拒否する。

        負数や履歴長超過を黙って切り詰めず、呼び出し側の指定ミスをValueErrorで
        検出する。
        """
        self._require_implementation()
        record = GameRecord(create_initial_position())
        position_at = getattr(record, "position_at", None)
        self.assertIsNotNone(position_at, "局面再現操作が未実装です")
        if position_at is None:
            return

        with self.assertRaisesRegex(ValueError, "手数"):
            position_at(-1)
        with self.assertRaisesRegex(ValueError, "手数"):
            position_at(1)

    def test_saves_initial_position_and_recorded_moves_as_json(self):
        """開始局面と成功手を固定文字列のJSONへ保存する。

        現在局面やEnumの内部番号を保存してしまう誤り、通常移動・成り・駒打ちの
        いずれかを履歴から落とす誤りを検出する。
        """
        self._require_implementation()
        board = Board()
        board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 1), Piece(PieceType.KING, Side.GOTE))
        board.set_piece(Square(2, 2), Piece(PieceType.PAWN, Side.SENTE))
        position = Position(board, Side.SENTE)
        position.sente_hand.add(BasicPieceType.PAWN)
        position.gote_hand.add(BasicPieceType.PAWN)
        record = GameRecord(position)

        save = getattr(record, "save", None)
        self.assertIsNotNone(save, "GameRecordのJSON保存操作が未実装です")
        if save is None:
            return

        record.apply_move(Square(2, 2), Square(2, 1), promote=True)
        record.apply_drop(BasicPieceType.PAWN, Square(4, 4))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            save(path)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["format"], "kaname-shogi-game-record-v1")
        self.assertEqual(payload["initial_position"]["side_to_move"], "SENTE")
        self.assertIn({"file": 2, "rank": 2, "piece_type": "PAWN",
                       "side": "SENTE"},
                      payload["initial_position"]["pieces"])
        self.assertEqual(payload["initial_position"]["hands"]["SENTE"],
                         {"PAWN": 1})
        self.assertEqual(payload["initial_position"]["hands"]["GOTE"],
                         {"PAWN": 1})
        self.assertEqual(payload["moves"], [
            {"kind": "move", "source": {"file": 2, "rank": 2},
             "destination": {"file": 2, "rank": 1}, "promote": True},
            {"kind": "drop", "piece_type": "PAWN",
             "destination": {"file": 4, "rank": 4}},
        ])

    def test_loads_saved_record_and_replays_current_position(self):
        """保存済みの開始局面と履歴から独立した記録を再現する。

        現在局面をJSONから直接採用する誤り、返却記録が元の記録と可変状態を
        共有する誤りを検出する。
        """
        self._require_implementation()
        record = GameRecord(create_initial_position())
        record.apply_move(Square(7, 7), Square(7, 6))
        record.apply_move(Square(3, 3), Square(3, 4))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            record.save(path)
            load = getattr(GameRecord, "load", None)
            self.assertIsNotNone(load, "GameRecordのJSON読込操作が未実装です")
            if load is None:
                return
            loaded = load(path)

        self.assertEqual(loaded.moves, record.moves)
        self.assertEqual(loaded.current_position.board.piece_at(Square(7, 6)),
                         Piece(PieceType.PAWN, Side.SENTE))
        loaded.apply_move(Square(7, 6), Square(7, 5))
        self.assertEqual(len(record.moves), 2)

    def test_rejects_invalid_json_values_and_illegal_history(self):
        """形式不正または不合法な履歴のJSONをValueErrorで拒否する。"""
        self._require_implementation()
        invalid_payloads = (
            "{",
            json.dumps({"format": "wrong", "initial_position": {},
                        "moves": []}),
            json.dumps({
                "format": "kaname-shogi-game-record-v1",
                "initial_position": {
                    "side_to_move": "SENTE", "pieces": [],
                    "hands": {"SENTE": {"KING": 1}, "GOTE": {}},
                },
                "moves": [],
            }),
            json.dumps({
                "format": "kaname-shogi-game-record-v1",
                "initial_position": {
                    "side_to_move": "SENTE", "pieces": [],
                    "hands": {"SENTE": {}, "GOTE": {}},
                },
                "moves": [{
                    "kind": "move",
                    "source": {"file": 7, "rank": 7},
                    "destination": {"file": 7, "rank": 6},
                    "promote": False,
                }],
            }),
        )
        load = getattr(GameRecord, "load", None)
        self.assertIsNotNone(load, "GameRecordのJSON読込操作が未実装です")
        if load is None:
            return
        with TemporaryDirectory() as directory:
            for index, text in enumerate(invalid_payloads):
                path = Path(directory) / f"invalid-{index}.json"
                path.write_text(text, encoding="utf-8")
                with self.subTest(index=index):
                    with self.assertRaises(ValueError):
                        load(path)

    def test_propagates_missing_file_error_when_loading(self):
        """存在しない読込先はOSErrorとして通知する。"""
        self._require_implementation()
        load = getattr(GameRecord, "load", None)
        self.assertIsNotNone(load, "GameRecordのJSON読込操作が未実装です")
        if load is None:
            return
        with TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                load(Path(directory) / "missing.json")

    def test_save_does_not_change_record_and_overwrites_existing_file(self):
        """保存しても記録を変更せず、既存ファイルは新しい内容へ置き換える。

        保存用の局面参照が内部状態を直接変更する誤りと、既存ファイルを残して
        新しい棋譜を書き込まない誤りを検出する。
        """
        self._require_implementation()
        record = GameRecord(create_initial_position())
        before = record.current_position
        with TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            path.write_text("old", encoding="utf-8")
            record.save(path)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["format"], "kaname-shogi-game-record-v1")
        self.assertEqual(record.moves, ())
        self.assertEqual(record.current_position.side_to_move,
                         before.side_to_move)
        self.assertEqual(record.current_position.board.piece_at(Square(7, 7)),
                         before.board.piece_at(Square(7, 7)))

    def test_rejects_malformed_nested_values(self):
        """余分キー、重複マス、0枚、真偽値座標、不正な成りを拒否する。

        JSONの形だけを受理して、局面や履歴の値を曖昧に解釈する誤りを検出する。
        """
        self._require_implementation()
        record = GameRecord(create_initial_position())
        record.apply_move(Square(7, 7), Square(7, 6))
        load = getattr(GameRecord, "load", None)
        self.assertIsNotNone(load, "GameRecordのJSON読込操作が未実装です")
        if load is None:
            return
        with TemporaryDirectory() as directory:
            valid_path = Path(directory) / "valid.json"
            record.save(valid_path)
            valid = json.loads(valid_path.read_text(encoding="utf-8"))
            invalid_payloads = []

            extra = json.loads(json.dumps(valid))
            extra["extra"] = True
            invalid_payloads.append(extra)

            duplicate = json.loads(json.dumps(valid))
            duplicate["initial_position"]["pieces"].append(
                duplicate["initial_position"]["pieces"][0])
            invalid_payloads.append(duplicate)

            zero_hand = json.loads(json.dumps(valid))
            zero_hand["initial_position"]["hands"]["SENTE"] = {"PAWN": 0}
            invalid_payloads.append(zero_hand)

            bool_file = json.loads(json.dumps(valid))
            bool_file["initial_position"]["pieces"][0]["file"] = True
            invalid_payloads.append(bool_file)

            bad_promote = json.loads(json.dumps(valid))
            bad_promote["moves"][0]["promote"] = "false"
            invalid_payloads.append(bad_promote)

            for index, payload in enumerate(invalid_payloads):
                path = Path(directory) / f"malformed-{index}.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(index=index):
                    with self.assertRaises(ValueError):
                        load(path)

    def test_raises_file_error_when_save_parent_is_missing(self):
        """存在しない保存先の親ディレクトリはOSErrorとして通知する。"""
        self._require_implementation()
        record = GameRecord(create_initial_position())
        with TemporaryDirectory() as directory:
            path = Path(directory) / "missing" / "record.json"
            with self.assertRaises(FileNotFoundError):
                record.save(path)


if __name__ == "__main__":
    unittest.main()
