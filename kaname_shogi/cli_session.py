"""通常対局CLIで棋譜と時計を一緒に保存・読込する。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .cli_clock import CliClock, CliClockSettings
from .game_record import GameRecord

_GAME_RECORD_FORMAT = "kaname-shogi-game-record-v1"
_CLI_SESSION_FORMAT = "kaname-shogi-cli-session-v1"
_SESSION_KEYS = {"format", "game_record", "clock"}
_CLOCK_KEYS = {
    "initial_time_ms",
    "byoyomi_ms",
    "sente_remaining_ns",
    "gote_remaining_ns",
}


@dataclass(frozen=True)
class CliSession:
    """通常対局CLIの棋譜と、任意の先後時計状態をまとめるデータ。

    引数:
        record: 開始局面と成功手を保持するGameRecord。
        clock: 先後の時計状態。時計なしの旧v1棋譜ではNone。

    戻り値:
        棋譜と時計の組を保持する変更不可のセッションデータ。

    副作用:
        なし。時計や棋譜の進行、ファイルI/Oはsave/loadが呼ばれるまで行わない。

    セッションの外側形式は既存v1棋譜を内包し、時計設定と先後の残りnsだけを追加する。
    計時原点や探索途中状態を保存しないことで、再開時の対局管理と探索制御を分離する。
    """

    record: GameRecord
    clock: CliClock | None

    def save(self, path: str | Path) -> None:
        """棋譜と任意の時計を一つのJSONファイルへ保存する。

        引数:
            path: 保存先を表す文字列またはPath。

        戻り値:
            なし（None）。

        副作用:
            保存先を作成または上書きする。時計がNoneなら既存の棋譜v1形式を保存し、
            時計があれば外側セッション形式へ棋譜v1と時計四値を保存する。

        例外:
            ValueError: recordまたはclockの型が想定したデータでない場合。
            OSError: 保存先を開けない、または書き込めない場合。

        時計値を更新せず、棋譜の公開payload変換へ委譲する。時計なしの既存CLI保存も
        同じv1表現を保つため、session情報を含めない。
        """
        if not isinstance(self.record, GameRecord):
            raise ValueError("recordはGameRecordが必要です")
        if self.clock is not None and not isinstance(self.clock, CliClock):
            raise ValueError("clockはCliClockまたはNoneが必要です")

        if self.clock is None:
            payload = self.record.to_payload()
        else:
            payload = {
                "format": _CLI_SESSION_FORMAT,
                "game_record": self.record.to_payload(),
                "clock": {
                    "initial_time_ms": self.clock.settings.initial_time_ms,
                    "byoyomi_ms": self.clock.settings.byoyomi_ms,
                    "sente_remaining_ns": self.clock.sente_remaining_ns,
                    "gote_remaining_ns": self.clock.gote_remaining_ns,
                },
            }

        with Path(path).open("w", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=False, indent=2)
            output.write("\n")

    @classmethod
    def load(cls, path: str | Path) -> CliSession:
        """既存棋譜v1または時計つきセッションを検証して読み込む。

        引数:
            path: 読み込むJSONファイルを表す文字列またはPath。

        戻り値:
            合法履歴を再生した棋譜と、形式に応じた時計状態を持つ新しいCliSession。
            既存棋譜v1を読んだ場合はclockがNone。

        副作用:
            ファイルを読み、新しい棋譜・時計データを作る。読込中に既存の記録や時計は
            変更しない。棋譜の検証と再生はGameRecord.from_payloadへ委譲する。

        例外:
            ValueError: JSON形式、値、時計、棋譜または履歴が不正な場合。
            OSError: ファイルを開けない、または読み込めない場合。
            UnicodeDecodeError: ファイルがUTF-8として読めない場合。

        時計つき形式の不足・不正値は旧棋譜として扱わない。形式識別子を先に分けることで、
        壊れた時計を隠した時計なし保存へのフォールバックを防ぐ。
        """
        with Path(path).open(encoding="utf-8") as source:
            payload = json.load(source)

        if not isinstance(payload, dict):
            raise ValueError("トップレベルはオブジェクトで指定してください")

        payload_format = payload.get("format")
        if payload_format == _GAME_RECORD_FORMAT:
            return cls(GameRecord.from_payload(payload), None)
        if payload_format != _CLI_SESSION_FORMAT:
            raise ValueError("JSON形式識別子が正しくありません")

        if set(payload) != _SESSION_KEYS:
            raise ValueError("セッションの項目が正しくありません")
        clock_payload = payload["clock"]
        if not isinstance(clock_payload, dict):
            raise ValueError("clockはオブジェクトで指定してください")
        if set(clock_payload) != _CLOCK_KEYS:
            raise ValueError("clockの項目が正しくありません")

        settings = CliClockSettings(
            clock_payload["initial_time_ms"], clock_payload["byoyomi_ms"]
        )
        clock = CliClock(
            settings,
            clock_payload["sente_remaining_ns"],
            clock_payload["gote_remaining_ns"],
        )
        record = GameRecord.from_payload(payload["game_record"])
        return cls(record, clock)
