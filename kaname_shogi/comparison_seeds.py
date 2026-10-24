"""比較CLIで再利用する、事前作成済み乱数種一覧の値と操作。"""

from __future__ import annotations

import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass

from .comparison_artifact_io import decode_object

_MAX_SEED = 1 << 128
_PURPOSES = {"pilot", "confirmation"}
_FORMAT = "kaname-shogi-comparison-seeds-v1"
_PLAN_KEYS = {
    "format",
    "purpose",
    "positions_sha256",
    "position_ids",
    "pairs_per_position",
    "source",
    "bits",
    "pairs",
}
_PAIR_KEYS = {
    "position_id",
    "repetition_index",
    "baseline_seed",
    "candidate_seed",
}


@dataclass(frozen=True)
class PairSeeds:
    """一局面・一反復に割り当てる基準方式と候補方式の種データ。"""

    position_id: str
    repetition_index: int
    baseline_seed: int
    candidate_seed: int


@dataclass(frozen=True)
class SeedPlan:
    """局面順と組数を固定した比較実験用の乱数種一覧データ。"""

    purpose: str
    positions_sha256: str
    position_ids: tuple[str, ...]
    pairs_per_position: int
    pairs: tuple[PairSeeds, ...]


def generate_seed_plan(
    position_ids: tuple[str, ...],
    positions_sha256: str,
    pairs_per_position: int,
    purpose: str,
    *,
    randbits: Callable[[int], int] = secrets.randbits,
) -> SeedPlan:
    """各局面・反復へ独立抽選した二方式分の128ビット種を割り当てる。

    引数:
        position_ids: 比較局面IDの順序付きタプル。
        positions_sha256: 読込時の局面JSONバイト列のSHA-256。
        pairs_per_position: 各局面に割り当てる二局一組の回数。
        purpose: 予備比較の`pilot`または確認比較の`confirmation`。
        randbits: 128ビットの非負整数を返す乱数抽出操作。未指定ならOS乱数源。

    戻り値:
        局面順・反復番号順に並ぶ、方式別の乱数種を保持した変更不可データ。

    例外:
        ValueError: ID・ハッシュ・目的・組数・乱数源の返値が契約外の場合。

    副作用:
        乱数源を各方式・各組につき一回呼び出す。ファイルや局面データは変更しない。

    前提条件:
        種は方式ごとに抽出して保存し、同じ組の先後交換二局では再利用する。
        偶然同じ値が抽出されても、再抽出や除外をせずその値を保持する。
    """
    _validate_metadata(position_ids, positions_sha256, pairs_per_position, purpose)
    if not callable(randbits):
        raise ValueError("乱数源はビット数を受け取る呼出可能値で指定してください")

    pairs = []
    for position_id in position_ids:
        for repetition_index in range(pairs_per_position):
            baseline_seed = randbits(128)
            candidate_seed = randbits(128)
            for seed in (baseline_seed, candidate_seed):
                if type(seed) is not int or not 0 <= seed < _MAX_SEED:
                    raise ValueError("乱数源は128ビット範囲の整数を返す必要があります")
            pairs.append(
                PairSeeds(
                    position_id,
                    repetition_index,
                    baseline_seed,
                    candidate_seed,
                )
            )
    plan = SeedPlan(
        purpose=purpose,
        positions_sha256=positions_sha256,
        position_ids=position_ids,
        pairs_per_position=pairs_per_position,
        pairs=tuple(pairs),
    )
    _validate_plan_shape(plan)
    return plan


def parse_seed_plan(raw: bytes) -> SeedPlan:
    """保存JSONを厳密に検証し、乱数種一覧データへ変換する。

    引数:
        raw: UTF-8のseed-list JSONバイト列。

    戻り値:
        固定形式・順序・範囲をすべて検証した乱数種一覧。

    例外:
        ValueError: JSON、項目、順序、seed、または形式が契約外の場合。

    副作用:
        なし。入力 bytesを変更しない。

    前提条件:
        乱数種の重複値は許すが、(局面ID, 反復番号)は局面順・昇順に一度ずつ並ぶ。
    """
    payload = decode_object(raw, context="乱数種一覧")
    _require_exact_keys(payload, _PLAN_KEYS, "乱数種一覧")
    if payload["format"] != _FORMAT:
        raise ValueError("乱数種一覧形式が対応していません")
    if payload["source"] != "os" or type(payload["bits"]) is not int:
        raise ValueError("乱数種一覧の乱数源またはビット数が対応していません")
    if payload["bits"] != 128:
        raise ValueError("乱数種一覧のビット数は128で指定してください")

    position_ids_value = payload["position_ids"]
    if type(position_ids_value) is not list:
        raise ValueError("局面IDはJSON配列で指定してください")
    position_ids = tuple(position_ids_value)
    _validate_metadata(
        position_ids,
        payload["positions_sha256"],
        payload["pairs_per_position"],
        payload["purpose"],
    )
    pair_values = payload["pairs"]
    if type(pair_values) is not list:
        raise ValueError("乱数種の組はJSON配列で指定してください")
    pairs = []
    for index, pair_value in enumerate(pair_values, start=1):
        if not isinstance(pair_value, dict):
            raise ValueError(f"第{index}乱数種の組はJSONオブジェクトで指定してください")
        _require_exact_keys(pair_value, _PAIR_KEYS, f"第{index}乱数種の組")
        pairs.append(
            PairSeeds(
                pair_value["position_id"],
                pair_value["repetition_index"],
                pair_value["baseline_seed"],
                pair_value["candidate_seed"],
            )
        )
    plan = SeedPlan(
        purpose=payload["purpose"],
        positions_sha256=payload["positions_sha256"],
        position_ids=position_ids,
        pairs_per_position=payload["pairs_per_position"],
        pairs=tuple(pairs),
    )
    _validate_plan_shape(plan)
    return plan


def seed_plan_payload(plan: SeedPlan) -> dict[str, object]:
    """検証済み乱数種一覧を固定JSON項目の辞書へ変換する。

    引数:
        plan: 局面順と種を保持する乱数種一覧。

    戻り値:
        format/source/bitsを含み、比較CLIへ渡せるJSON互換辞書。

    例外:
        ValueError: 一覧が内部契約に合わない場合。

    副作用:
        なし。planを変更しない。

    前提条件:
        baseline/candidateの役割ごとに抽出済みの種を保持し、方式名は含めない。
    """
    _validate_plan_shape(plan)
    return {
        "format": _FORMAT,
        "purpose": plan.purpose,
        "positions_sha256": plan.positions_sha256,
        "position_ids": list(plan.position_ids),
        "pairs_per_position": plan.pairs_per_position,
        "source": "os",
        "bits": 128,
        "pairs": [
            {
                "position_id": pair.position_id,
                "repetition_index": pair.repetition_index,
                "baseline_seed": pair.baseline_seed,
                "candidate_seed": pair.candidate_seed,
            }
            for pair in plan.pairs
        ],
    }


def validate_seed_plan(
    plan: SeedPlan,
    *,
    position_ids: tuple[str, ...],
    positions_sha256: str,
    pairs_per_position: int,
) -> None:
    """乱数種一覧が読込済み局面スナップショットと予定に一致するか検証する。

    引数:
        plan: 読込済みまたは生成済みの乱数種一覧。
        position_ids: 比較する局面IDの期待順。
        positions_sha256: 読込時局面JSONバイト列の期待SHA-256。
        pairs_per_position: 局面ごとに期待する二局一組の数。

    戻り値:
        一致時はNone。

    例外:
        ValueError: 一覧内部または外部条件との不一致がある場合。

    副作用:
        なし。一覧・入力引数を変更しない。

    前提条件:
        同一IDでも局面JSON内容の異なる一覧は同一実験として使わない。
    """
    _validate_plan_shape(plan)
    _validate_metadata(
        position_ids,
        positions_sha256,
        pairs_per_position,
        plan.purpose,
    )
    if (
        plan.position_ids != position_ids
        or plan.positions_sha256 != positions_sha256
        or plan.pairs_per_position != pairs_per_position
    ):
        raise ValueError("乱数種一覧が比較局面・内容・組数と一致しません")


def _validate_metadata(
    position_ids: object,
    positions_sha256: object,
    pairs_per_position: object,
    purpose: object,
) -> None:
    """乱数種一覧の局面・ハッシュ・組数・目的の型と値を検証する。"""
    if (
        type(position_ids) is not tuple
        or not position_ids
        or any(
            not isinstance(position_id, str)
            or re.fullmatch(r"[A-Za-z0-9_-]+", position_id) is None
            for position_id in position_ids
        )
        or len(set(position_ids)) != len(position_ids)
    ):
        raise ValueError("局面IDは重複しないASCII識別子のタプルで指定してください")
    if (
        not isinstance(positions_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", positions_sha256) is None
    ):
        raise ValueError("局面SHA-256は小文字16進64文字で指定してください")
    if type(pairs_per_position) is not int or pairs_per_position < 1:
        raise ValueError("局面ごとの組数は1以上の整数で指定してください")
    if not isinstance(purpose, str) or purpose not in _PURPOSES:
        raise ValueError("目的はpilotまたはconfirmationで指定してください")


def _validate_plan_shape(plan: SeedPlan) -> None:
    """変更不可データであっても外部生成された一覧値の全契約を確認する。"""
    if not isinstance(plan, SeedPlan):
        raise ValueError("乱数種一覧データ型が不正です")
    _validate_metadata(
        plan.position_ids,
        plan.positions_sha256,
        plan.pairs_per_position,
        plan.purpose,
    )
    if type(plan.pairs) is not tuple:
        raise ValueError("乱数種の組はタプルで保持してください")
    expected = tuple(
        (position_id, repetition_index)
        for position_id in plan.position_ids
        for repetition_index in range(plan.pairs_per_position)
    )
    actual = []
    for pair in plan.pairs:
        if not isinstance(pair, PairSeeds):
            raise ValueError("乱数種の組データ型が不正です")
        if type(pair.repetition_index) is not int or pair.repetition_index < 0:
            raise ValueError("反復番号は0以上の整数で指定してください")
        if any(
            type(seed) is not int or not 0 <= seed < _MAX_SEED
            for seed in (pair.baseline_seed, pair.candidate_seed)
        ):
            raise ValueError("乱数種は128ビット範囲の整数で指定してください")
        actual.append((pair.position_id, pair.repetition_index))
    if tuple(actual) != expected:
        raise ValueError("乱数種の組が局面順・反復番号順の予定と一致しません")


def _require_exact_keys(
    payload: dict[str, object], expected: set[str], context: str
) -> None:
    """辞書の必須キー欠落と未知キーを拒否する。"""
    actual = set(payload)
    missing = expected - actual
    unknown = actual - expected
    if missing or unknown:
        raise ValueError(
            f"{context}のキーが不正です (不足={sorted(missing)}, 未知={sorted(unknown)})"
        )
