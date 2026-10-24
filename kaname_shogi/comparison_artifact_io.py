"""比較実験の成果物に共通する厳密なJSON読込と新規限定保存。"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path


def decode_object(raw: bytes, *, context: str) -> dict[str, object]:
    """重複キー・非有限数を拒否し、トップJSONオブジェクトを返す。

    引数:
        raw: 成果物のUTF-8 JSONバイト列。
        context: エラー診断に付ける成果物名。

    戻り値:
        すべての階層で重複キーと非有限数がないJSONオブジェクト。

    例外:
        ValueError: 入力がbytesでない、UTF-8/JSONが不正、重複キーまたは非有限数、
            トップレベルがオブジェクトでない場合。

    副作用:
        なし。受け取ったバイト列を変更しない。

    前提条件:
        JSONの重複キーを後勝ちで解決せず、値の意味を黙って変えない。
    """
    if type(raw) is not bytes:
        raise ValueError(f"{context}JSONはbytesで指定してください")
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{context}JSONを読み込めません: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{context}のトップレベルはJSONオブジェクトで指定してください")
    return payload


def write_new_json(path: Path, payload: Mapping[str, object]) -> None:
    """JSONを先に完全直列化し、既存パスを上書きせず新規保存する。

    引数:
        path: 親ディレクトリが存在する、まだ存在しない保存先。
        payload: JSONへ変換可能な文字列キーのmapping。

    戻り値:
        なし（None）。成功時に新規UTF-8 JSONファイルを作成する。

    例外:
        FileExistsError / OSError: 保存先または親パスが不正、既存、書込不能の場合。
        TypeError / ValueError: payloadがJSONへ変換できない場合。
        OSError: 保存失敗後に自分が作成した途中ファイルを除去できない場合。

    副作用:
        `xb`による排他的作成でファイルを新規保存する。作成後の書込失敗時は可能なら
        途中ファイルを削除する。既存ファイルを開いたり削除したりしない。

    前提条件:
        直列化を作成前に完了し、並行実行で他者が先に作成したファイルも上書きしない。
    """
    destination = Path(path)
    if not isinstance(payload, Mapping):
        raise TypeError("JSON成果物はMappingで指定してください")
    serialized = (
        json.dumps(dict(payload), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")

    created = False
    try:
        with destination.open("xb") as output:
            created = True
            written = output.write(serialized)
            if written != len(serialized):
                raise OSError("JSON成果物を最後まで書き込めませんでした")
    except BaseException as error:
        if created:
            try:
                destination.unlink()
            except FileNotFoundError:
                pass
            except OSError as cleanup_error:
                raise OSError(
                    f"JSON成果物の保存に失敗しました ({error}); "
                    f"途中ファイルの除去にも失敗しました ({cleanup_error})"
                ) from error
        raise


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """JSONオブジェクト内の重複キーを拒否して辞書を作る。"""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSONキーが重複しています: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    """JSON標準外のNaN/Infinity表現を拒否する。"""
    raise ValueError(f"JSONの非有限数は使用できません: {value}")


def _finite_float(value: str) -> float:
    """指数表記のオーバーフローを含む非有限浮動小数を拒否する。"""
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"JSONの非有限数は使用できません: {value}")
    return parsed
