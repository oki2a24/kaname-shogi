"""時計設定の読込と時間予算計算。"""

import json
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class TimeManagementConfig:
    """配分係数を検証し、一回の実行中に共有できる不変の設定データ。

    引数:
        allocation_turns: 固定分母となる1以上の整数。
        maximum_multiplier: 1超の有限な倍率を表すFraction。
        byoyomi_target_ratio: 0超1未満の秒読み目標割合を表すFraction。
        response_margin_ms: 0以上の応答余裕、単位ms。

    戻り値:
        構築結果は四欄を保持するTimeManagementConfig。
    副作用:
        なし。不正な型・範囲はValueError。boolを整数扱いしない。
    前提条件・設計理由:
        係数は正確な分数で受ける。暗黙のfloat変換や代替既定値を避け、
        後続の計算で丸め誤差を持ち込まない。起動時の保持は呼出し側の責務。
    """

    allocation_turns: int
    maximum_multiplier: Fraction
    byoyomi_target_ratio: Fraction
    response_margin_ms: int

    def __post_init__(self) -> None:
        if type(self.allocation_turns) is not int or self.allocation_turns < 1:
            raise ValueError("allocation_turnsは1以上の整数が必要です")
        if (
            not isinstance(self.maximum_multiplier, Fraction)
            or self.maximum_multiplier <= 1
        ):
            raise ValueError("maximum_multiplierは1超のFractionが必要です")
        if (
            not isinstance(self.byoyomi_target_ratio, Fraction)
            or not 0 < self.byoyomi_target_ratio < 1
        ):
            raise ValueError("byoyomi_target_ratioは0超1未満のFractionが必要です")
        if type(self.response_margin_ms) is not int or self.response_margin_ms < 0:
            raise ValueError("response_margin_msは0以上の整数が必要です")


def _coefficient(value, key):
    if type(value) is not int and not isinstance(value, Decimal):
        raise ValueError(f"{key}は有限数が必要です")
    if isinstance(value, Decimal) and not value.is_finite():
        raise ValueError(f"{key}は有限数が必要です")
    return Fraction(value)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"重複キーです: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"非有限数は使えません: {value}")


def load_time_management_config(path: Optional[Path] = None) -> TimeManagementConfig:
    """UTF-8 JSONを検証し、新しい時間設定データを返す。

    引数:
        path: 読込先Path。Noneはこのモジュールから見たリポジトリ直下の
            config/time-management.json。明示相対パスは呼出し時cwd基準。
    戻り値:
        四項目を持つ不変のTimeManagementConfig。係数は正確なFraction。
    副作用:
        ファイルを読む。キャッシュ・出力・既定値への置換は行わない。
    例外:
        ValueError: JSON構文・項目・型・範囲・文字コードが不正。
        OSError: 開く/読む操作が失敗。例外の説明に対象パスを含める。
    前提条件・設計理由:
        Git checkoutに設定を同梱する運用。cwdに依存しない既定パスを使い、
        十進数はDecimalで保持してFractionへ変換する。stderrと終了コードへの
        変換、一回読込と保持は将来のUSI入口が担当する。
    """
    source_path = (
        path
        if path is not None
        else Path(__file__).resolve().parents[1] / "config" / "time-management.json"
    )
    try:
        with source_path.open(encoding="utf-8") as source:
            payload = json.load(
                source,
                parse_float=Decimal,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_constant,
            )
        if not isinstance(payload, dict):
            raise ValueError("トップレベルはobjectが必要です")
        keys = {
            "allocation_turns",
            "maximum_multiplier",
            "byoyomi_target_ratio",
            "response_margin_ms",
        }
        missing = keys - payload.keys()
        unknown = payload.keys() - keys
        if missing or unknown:
            raise ValueError(
                f"項目欠落: {sorted(missing)}; 未知項目: {sorted(unknown)}"
            )
        return TimeManagementConfig(
            payload["allocation_turns"],
            _coefficient(payload["maximum_multiplier"], "maximum_multiplier"),
            _coefficient(payload["byoyomi_target_ratio"], "byoyomi_target_ratio"),
            payload["response_margin_ms"],
        )
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"{source_path}: {error}") from error
    except OSError as error:
        raise OSError(f"{source_path}: {error}") from error
