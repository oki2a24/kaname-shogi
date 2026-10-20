"""CLI時計と既存棋譜を一つの保存単位へまとめる契約を検証する。"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kaname_shogi.cli_clock import CliClock, CliClockSettings
from kaname_shogi.game_record import GameRecord

try:
    from kaname_shogi.cli_session import CliSession
except ModuleNotFoundError as error:
    if error.name != "kaname_shogi.cli_session":
        raise
    CliSession = None


def literal_game_record_payload():
    """時計形式テスト用の独立した、手数0の既存v1辞書を返す。"""
    return {
        "format": "kaname-shogi-game-record-v1",
        "initial_position": {
            "side_to_move": "SENTE",
            "pieces": [],
            "hands": {"SENTE": {}, "GOTE": {}},
        },
        "moves": [],
    }


class CliSessionTests(unittest.TestCase):
    def _require_implementation(self):
        """未実装APIを読み込み失敗ではなく機能不足として検出する。"""
        if CliSession is None:
            self.fail("CliSessionの保存・読込APIが未実装です")

    def test_session_payload_contains_only_record_and_four_clock_values(self):
        """時計つきJSONが既存棋譜と四つの時計値だけを一緒に保存する。

        先後で異なるnsを手書きJSONから読んで再保存し、msへ丸める誤りや
        経過時刻・探索状態などを保存形式へ混ぜる誤りを検出する。
        """
        self._require_implementation()
        game_record_payload = literal_game_record_payload()
        expected = {
            "format": "kaname-shogi-cli-session-v1",
            "game_record": game_record_payload,
            "clock": {
                "initial_time_ms": 600000,
                "byoyomi_ms": 30000,
                "sente_remaining_ns": 123456789,
                "gote_remaining_ns": 987654321,
            },
        }

        with TemporaryDirectory() as directory:
            input_path = Path(directory) / "session.json"
            output_path = Path(directory) / "resaved.json"
            input_path.write_text(json.dumps(expected), encoding="utf-8")
            session = CliSession.load(input_path)
            session.save(output_path)
            saved = json.loads(output_path.read_text(encoding="utf-8"))

            legacy_path = Path(directory) / "legacy.json"
            legacy_path.write_text(json.dumps(game_record_payload), encoding="utf-8")
            legacy_session = CliSession.load(legacy_path)
            legacy_output = Path(directory) / "legacy-resaved.json"
            legacy_session.save(legacy_output)
            legacy_saved = json.loads(legacy_output.read_text(encoding="utf-8"))

        self.assertEqual(saved, expected)
        self.assertEqual(set(saved), {"format", "game_record", "clock"})
        self.assertEqual(
            set(saved["clock"]),
            {
                "initial_time_ms",
                "byoyomi_ms",
                "sente_remaining_ns",
                "gote_remaining_ns",
            },
        )
        self.assertIsInstance(session.record, GameRecord)
        self.assertEqual(
            session.clock,
            CliClock(CliClockSettings(600000, 30000), 123456789, 987654321),
        )
        self.assertIsNone(legacy_session.clock)
        self.assertEqual(legacy_saved, game_record_payload)

    def test_session_rejects_malformed_envelope_without_legacy_fallback(self):
        """新形式の外側・時計・棋譜を厳密に検証し旧形式へ落とさない。

        欠落、余分、null、bool、負数、浮動小数、文字列、残り上限超過と
        不正履歴を拒否し、時計つきとして無効な保存を時計なし棋譜にする誤りを検出する。
        """
        self._require_implementation()
        valid = {
            "format": "kaname-shogi-cli-session-v1",
            "game_record": literal_game_record_payload(),
            "clock": {
                "initial_time_ms": 600000,
                "byoyomi_ms": 30000,
                "sente_remaining_ns": 123456789,
                "gote_remaining_ns": 987654321,
            },
        }
        invalid_payloads = [None, []]

        unknown_outer = json.loads(json.dumps(valid))
        unknown_outer["extra"] = 1
        invalid_payloads.append(unknown_outer)

        for missing_key in ("game_record", "clock"):
            missing = json.loads(json.dumps(valid))
            del missing[missing_key]
            invalid_payloads.append(missing)

        for malformed_clock in (None, [], {**valid["clock"], "extra": 1}):
            invalid = json.loads(json.dumps(valid))
            invalid["clock"] = malformed_clock
            invalid_payloads.append(invalid)

        missing_clock_value = json.loads(json.dumps(valid))
        del missing_clock_value["clock"]["gote_remaining_ns"]
        invalid_payloads.append(missing_clock_value)

        wrong_format = json.loads(json.dumps(valid))
        wrong_format["format"] = "wrong"
        invalid_payloads.append(wrong_format)

        for field in (
            "initial_time_ms",
            "byoyomi_ms",
            "sente_remaining_ns",
            "gote_remaining_ns",
        ):
            for invalid_value in (None, True, -1, 1.5, "1"):
                invalid = json.loads(json.dumps(valid))
                invalid["clock"][field] = invalid_value
                invalid_payloads.append(invalid)

        too_much_remaining = json.loads(json.dumps(valid))
        too_much_remaining["clock"]["sente_remaining_ns"] = 600000000001
        invalid_payloads.append(too_much_remaining)

        no_time = json.loads(json.dumps(valid))
        no_time["clock"]["initial_time_ms"] = 0
        no_time["clock"]["byoyomi_ms"] = 0
        no_time["clock"]["sente_remaining_ns"] = 0
        no_time["clock"]["gote_remaining_ns"] = 0
        invalid_payloads.append(no_time)

        illegal_record = json.loads(json.dumps(valid))
        illegal_record["game_record"]["moves"] = [
            {
                "kind": "move",
                "source": {"file": 7, "rank": 7},
                "destination": {"file": 7, "rank": 6},
                "promote": False,
            }
        ]
        invalid_payloads.append(illegal_record)

        with TemporaryDirectory() as directory:
            for index, payload in enumerate(invalid_payloads):
                path = Path(directory) / f"invalid-{index}.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(index=index):
                    with self.assertRaises(ValueError):
                        CliSession.load(path)

            corrupt_json = Path(directory) / "corrupt.json"
            corrupt_json.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                CliSession.load(corrupt_json)

            bad_encoding = Path(directory) / "encoding.json"
            bad_encoding.write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError):
                CliSession.load(bad_encoding)

    def test_session_propagates_io_error_without_changing_state(self):
        """保存・読込のI/O失敗を伝え、棋譜と時計の値を変更しない。

        保存先の親なしと読込ファイルなしを検出し、I/O失敗を空セッションや
        時計初期化へ置き換える誤りを防ぐ。ファイル置換の原子性は対象外とする。
        """
        self._require_implementation()
        record = GameRecord.from_payload(literal_game_record_payload())
        clock = CliClock(CliClockSettings(600000, 30000), 123456789, 987654321)
        session = CliSession(record, clock)

        with TemporaryDirectory() as directory:
            missing = Path(directory) / "missing" / "session.json"
            with self.assertRaises(FileNotFoundError):
                session.save(missing)
            with self.assertRaises(FileNotFoundError):
                CliSession.load(missing)

        self.assertEqual(session.record.to_payload(), literal_game_record_payload())
        self.assertEqual(session.clock, clock)


if __name__ == "__main__":
    unittest.main()
