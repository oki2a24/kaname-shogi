"""通常対局CLIが保持するコンピュータ側の時計データと更新操作。"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Side

_NANOSECONDS_PER_MILLISECOND = 1_000_000


@dataclass(frozen=True)
class CliClockSettings:
    """対局開始時に固定する持ち時間と秒読みの設定データ。

    引数:
        initial_time_ms: 初期持ち時間。0以上の整数msでbool不可。
        byoyomi_ms: 各手で利用する秒読み。0以上の整数msでbool不可。

    戻り値:
        初期条件を保持する変更不可の時計設定データ。

    副作用:
        なし。探索・入出力・時計取得は行わない。

    例外:
        ValueError: 型・範囲が不正、または持ち時間と秒読みが両方0の場合。

    初期値と秒読みを分離して保持し、秒読みの使い残しを次の手へ持ち越さない。
    """

    initial_time_ms: int
    byoyomi_ms: int

    def __post_init__(self) -> None:
        for name, value in (
            ("initial_time_ms", self.initial_time_ms),
            ("byoyomi_ms", self.byoyomi_ms),
        ):
            if type(value) is not int or value < 0:
                raise ValueError(f"{name}は0以上の整数msが必要です")
        if self.initial_time_ms == 0 and self.byoyomi_ms == 0:
            raise ValueError("持ち時間と秒読みは同時に0にできません")


@dataclass(frozen=True)
class CliClock:
    """先後の残り持ち時間をnsで保持する通常CLIの時計データ。

    引数:
        settings: 対局開始時から変えない初期持ち時間・秒読み。
        sente_remaining_ns: 先手の残り持ち時間。0以上かつ初期値以下。
        gote_remaining_ns: 後手の残り持ち時間。0以上かつ初期値以下。

    戻り値:
        設定と先後の残り時間を持つ変更不可の時計データ。

    副作用:
        なし。局面・棋譜・実時間時計を変更または参照しない。

    例外:
        ValueError: 設定の型、残りnsの型または範囲が不正な場合。

    nsを保持して手ごとの1ms未満の切り捨てを避け、予算計算用変換と実際の
    時間切れ判定を分離する。初期持ち時間0でも読込状態として保持できる。
    """

    settings: CliClockSettings
    sente_remaining_ns: int
    gote_remaining_ns: int

    def __post_init__(self) -> None:
        if not isinstance(self.settings, CliClockSettings):
            raise ValueError("settingsはCliClockSettingsが必要です")
        maximum_remaining_ns = (
            self.settings.initial_time_ms * _NANOSECONDS_PER_MILLISECOND
        )
        for name, value in (
            ("sente_remaining_ns", self.sente_remaining_ns),
            ("gote_remaining_ns", self.gote_remaining_ns),
        ):
            if type(value) is not int or value < 0 or value > maximum_remaining_ns:
                raise ValueError(f"{name}は初期持ち時間内の非負整数nsが必要です")

    @classmethod
    def start(cls, settings: CliClockSettings) -> CliClock:
        """設定から先後を同じ初期残り時間で開始する。

        引数:
            settings: 開始時の持ち時間と秒読み。

        戻り値:
            先後の残り時間を初期持ち時間のns換算にした新しい時計。

        副作用:
            なし。時計の現在値を読み取らず、入力設定も変更しない。

        例外:
            ValueError: settingsが時計設定データでない場合。

        CLI新規対局の開始時計を作る操作であり、人間側を計時するかどうかは
        対局管理層が決める。
        """
        if not isinstance(settings, CliClockSettings):
            raise ValueError("settingsはCliClockSettingsが必要です")
        initial_remaining_ns = settings.initial_time_ms * _NANOSECONDS_PER_MILLISECOND
        return cls(settings, initial_remaining_ns, initial_remaining_ns)

    def remaining_ns(self, side: Side) -> int:
        """指定側の残り持ち時間を整数nsで返す。

        引数:
            side: 残り時間を調べる先手または後手。

        戻り値:
            指定側が保持する、切り捨てていない残り持ち時間ns。

        副作用:
            なし。時計を更新しない。

        例外:
            ValueError: sideがSideの値でない場合。

        側の選択を呼出し側へ明示させ、相手時計の誤参照を避ける。
        """
        if side is Side.SENTE:
            return self.sente_remaining_ns
        if side is Side.GOTE:
            return self.gote_remaining_ns
        raise ValueError("sideは先手または後手が必要です")

    def after_turn(self, side: Side, elapsed_ns: int) -> CliClock:
        """指定側だけの一手消費を差し引いた時計データを返す。

        引数:
            side: 時計を減らす先手または後手。
            elapsed_ns: 一手の非負整数消費時間ns。bool不可。

        戻り値:
            指定側を0以上へ減らし、相手側と設定を保持した新しい時計。

        副作用:
            なし。元の不変時計データは変更しない。

        例外:
            ValueError: sideまたは経過時間の型・範囲が不正な場合。

        秒読みは設定として各手で再利用し、今回の未使用時間を残り持ち時間へ
        加算しない。
        """
        self._validate_elapsed(elapsed_ns)
        if side is Side.SENTE:
            return CliClock(
                self.settings,
                max(0, self.sente_remaining_ns - elapsed_ns),
                self.gote_remaining_ns,
            )
        if side is Side.GOTE:
            return CliClock(
                self.settings,
                self.sente_remaining_ns,
                max(0, self.gote_remaining_ns - elapsed_ns),
            )
        raise ValueError("sideは先手または後手が必要です")

    def is_expired(self, side: Side, elapsed_ns: int) -> bool:
        """一手の経過が開始時残り時間と秒読みの合計へ達したか判定する。

        引数:
            side: 時間切れを判定する先手または後手。
            elapsed_ns: 一手の非負整数消費時間ns。bool不可。

        戻り値:
            `elapsed_ns >= 残りns + byoyomi_ms × 1000000`ならTrue。

        副作用:
            なし。時計値を更新せず、表示用丸めや探索予算を参照しない。

        例外:
            ValueError: sideまたは経過時間の型・範囲が不正な場合。

        対局時計の時間切れと探索予算の停止を分離するため、返却後の経過と
        開始時点の残り時間から等号を含む境界を判定する。
        """
        self._validate_elapsed(elapsed_ns)
        if side not in (Side.SENTE, Side.GOTE):
            raise ValueError("sideは先手または後手が必要です")
        allowed_ns = self.remaining_ns(side) + (
            self.settings.byoyomi_ms * _NANOSECONDS_PER_MILLISECOND
        )
        return elapsed_ns >= allowed_ns

    @staticmethod
    def _validate_elapsed(elapsed_ns: int) -> None:
        """一手の経過時間を型・非負条件で検証する。"""
        if type(elapsed_ns) is not int or elapsed_ns < 0:
            raise ValueError("elapsed_nsは非負整数nsが必要です")
