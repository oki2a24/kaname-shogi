"""比較実験の入力検証と局面準備を行う。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from . import movegen
from .comparison import (
    ComparisonConfig,
    ComparisonPosition,
    GameEndReason,
    GameResult,
    ScheduledGame,
    _policy_name,
    _side_name,
    make_schedule,
)
from .game_record import GameRecord
from .model import BasicPieceType, Position, Square, create_initial_position
from .move import BoardMove, DropMove
from .movegen import legal_moves
from .repetition import RepetitionOutcomeKind, RepetitionTracker
from .sfen import SfenPosition, format_sfen
from .usi_move import format_usi_move, parse_usi_move

_POSITION_FORMAT = "kaname-shogi-comparison-positions-v1"
_CONDITIONS_FORMAT = "kaname-shogi-comparison-conditions-v1"
_GAME_FORMAT = "kaname-shogi-comparison-game-v1"
_SUMMARY_FORMAT = "kaname-shogi-comparison-summary-v1"
_POSITION_SET_KEYS = {"format", "id", "positions"}
_POSITION_KEYS = {"id", "setup_moves", "rationale"}
_POLICIES = {
    "random": movegen.MoveSelectionPolicy.RANDOM,
    "material": movegen.MoveSelectionPolicy.MATERIAL,
    "two-ply-material": movegen.MoveSelectionPolicy.TWO_PLY_MATERIAL,
    "full-width-4": movegen.MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH,
    "alpha-beta-4": movegen.MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA,
}
_WINNING_END_REASONS = {
    GameEndReason.CHECKMATE,
    GameEndReason.NO_LEGAL_MOVE,
    GameEndReason.PERPETUAL_CHECK_LOSS,
}


class _ValueErrorArgumentParser(argparse.ArgumentParser):
    """parse_argsの入力エラーをCLI内部で扱えるValueErrorにする。"""

    def error(self, message: str) -> None:
        raise ValueError(message)


def load_positions(path: Path) -> tuple[ComparisonPosition, ...]:
    """局面セット全体を厳密に検証し、合法手順から開始局面を作る。

    引数:
        path: UTF-8 JSON局面セットファイルのパス。

    戻り値:
        配列順に並ぶ、準備手順と生成局面を保持した比較開始局面データ。

    例外:
        ValueError: JSON形式・必須値・重複・局面準備手順・準備中終局が不正な場合。
        OSError: ファイルを読めない場合。利用側で入力エラーへ変換する。

    副作用:
        ファイルを読み込むが、ファイル・盤面・CLI出力先を変更しない。準備手順を
        平手初期局面へ再生し、比較開始時点を一局の新しい初期履歴として扱えるよう
        比較開始SFEN・由来手数を確定する。
    """
    raw = Path(path).read_bytes()
    return _positions_from_bytes(raw)


def _positions_from_bytes(raw: bytes) -> tuple[ComparisonPosition, ...]:
    """読込済み局面セットの一つのバイト列を解析し、全項目を検証する。"""
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"局面セットJSONを読み込めません: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("局面セットのトップレベルはJSONオブジェクトで指定してください")
    _require_exact_keys(payload, _POSITION_SET_KEYS, "局面セット")
    if payload["format"] != _POSITION_FORMAT:
        raise ValueError("局面セット形式が対応していません")
    _require_id(payload["id"], "局面セットID")
    entries = payload["positions"]
    if type(entries) is not list or not entries:
        raise ValueError("局面セットには1件以上の局面を指定してください")

    loaded: list[ComparisonPosition] = []
    seen_ids: set[str] = set()
    seen_positions: set[tuple] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"第{index}局面はJSONオブジェクトで指定してください")
        _require_exact_keys(entry, _POSITION_KEYS, f"第{index}局面")
        position_id = _require_id(entry["id"], f"第{index}局面ID")
        if position_id in seen_ids:
            raise ValueError(f"局面IDが重複しています: {position_id}")
        seen_ids.add(position_id)

        rationale = entry["rationale"]
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"局面 {position_id} の理由を空でない文字列にしてください")
        setup_moves = entry["setup_moves"]
        if type(setup_moves) is not list or any(
            not isinstance(token, str) for token in setup_moves
        ):
            raise ValueError(
                f"局面 {position_id} の準備手順は文字列配列で指定してください"
            )

        record = GameRecord(create_initial_position())
        tracker = RepetitionTracker(record.current_position)
        for ply, token in enumerate(setup_moves, start=1):
            if tracker.current_outcome.kind in _TERMINAL_REPETITION_KINDS:
                raise ValueError(
                    f"局面 {position_id} の準備手順中に千日手が成立しました"
                )
            try:
                move = parse_usi_move(token)
                _apply_record_move(record, move)
            except ValueError as error:
                raise ValueError(
                    f"局面 {position_id} の準備第{ply}手 ({token}) が不正です: {error}"
                ) from error
            current = record.current_position
            outcome = tracker.add_position(current)
            if outcome.kind in _TERMINAL_REPETITION_KINDS:
                raise ValueError(
                    f"局面 {position_id} の準備手順中に千日手が成立しました"
                )
            if not legal_moves(current):
                raise ValueError(f"局面 {position_id} の準備手順中に終局しました")

        start_position = record.current_position
        if not legal_moves(start_position):
            raise ValueError(f"局面 {position_id} の比較開始時に合法手がありません")
        key = _position_key(start_position)
        if key in seen_positions:
            raise ValueError("盤面・持ち駒・手番が同一の開始局面が重複しています")
        seen_positions.add(key)
        move_number = len(setup_moves) + 1
        loaded.append(
            ComparisonPosition(
                position_id=position_id,
                setup_moves=tuple(setup_moves),
                rationale=rationale,
                start_position=start_position,
                start_sfen=format_sfen(SfenPosition(start_position, move_number)),
                initial_move_number=move_number,
            )
        )
    return tuple(loaded)


def load_config(argv: Sequence[str]) -> ComparisonConfig:
    """必須CLI条件と局面セット全件を検証し比較条件データを返す。

    引数:
        argv: `--baseline`等のオプションと値からなるCLI引数列。

    戻り値:
        有効な局面・方式・回数・種・手数上限・未使用の出力先を含む条件データ。

    例外:
        ValueError: 引数・値・局面セットまたは出力先の条件が無効な場合。
        OSError: 局面ファイルを読めない場合。

    副作用:
        引数と局面ファイルを読む。出力先を作らず、同名ファイルも上書きしない。
        すべての入力検証が終わってから呼出側が出力先を作れるよう、条件を先に確定する。
    """
    parser = _make_parser()
    args = parser.parse_args(list(argv))
    baseline = _POLICIES[args.baseline]
    candidate = _POLICIES[args.candidate]
    if baseline is candidate:
        raise ValueError("基準方式と候補方式は別々に指定してください")

    pairs_per_position = _parse_nonnegative_int(
        args.pairs_per_position, "組数", minimum=1
    )
    seed = _parse_nonnegative_int(args.seed, "乱数種", minimum=0)
    max_plies = _parse_nonnegative_int(args.max_plies, "手数上限", minimum=1)
    positions_path = Path(args.positions)
    positions_json = positions_path.read_bytes()
    positions = _positions_from_bytes(positions_json)

    output_dir = Path(args.output_dir)
    if output_dir.exists():
        raise ValueError("出力先は存在しないパスを指定してください")
    if not output_dir.parent.exists() or not output_dir.parent.is_dir():
        raise ValueError("出力先の親ディレクトリは事前に作成してください")

    return ComparisonConfig(
        baseline=baseline,
        candidate=candidate,
        positions=positions,
        pairs_per_position=pairs_per_position,
        seed=seed,
        max_plies=max_plies,
        output_dir=output_dir,
        positions_path=positions_path,
        positions_json=positions_json,
    )


def _make_parser(*, add_help: bool = False) -> _ValueErrorArgumentParser:
    """比較CLIが使う全必須引数を宣言したparserを返す。"""
    parser = _ValueErrorArgumentParser(add_help=add_help)
    parser.add_argument("--baseline", choices=tuple(_POLICIES), required=True)
    parser.add_argument("--candidate", choices=tuple(_POLICIES), required=True)
    parser.add_argument("--positions", required=True)
    parser.add_argument("--pairs-per-position", required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--max-plies", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser


def _parse_nonnegative_int(value: str, name: str, *, minimum: int) -> int:
    """ASCII十進数字だけを整数化し、指定最小値以上を確認する。"""
    if re.fullmatch(r"[0-9]+", value) is None:
        raise ValueError(f"{name}は整数で指定してください")
    parsed = int(value)
    if parsed < minimum:
        raise ValueError(f"{name}は{minimum}以上で指定してください")
    return parsed


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """JSONオブジェクト内の重複キーを拒否して辞書を作る。"""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSONキーが重複しています: {key}")
        result[key] = value
    return result


def _require_exact_keys(payload: dict, expected: set[str], context: str) -> None:
    """辞書の必須キーと未知キーを同時に検証する。"""
    actual = set(payload)
    missing = expected - actual
    unknown = actual - expected
    if missing or unknown:
        raise ValueError(
            f"{context}のキーが不正です (不足={sorted(missing)}, 未知={sorted(unknown)})"
        )


def _require_id(value: object, context: str) -> str:
    """空白・日本語・記号を含まないASCII識別子を返す。"""
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
        raise ValueError(
            f"{context}はASCII英数字・ハイフン・アンダースコアで指定してください"
        )
    return value


def _apply_record_move(record: GameRecord, move: object) -> None:
    """解析した一手を既存棋譜の合法手適用へ渡す。"""
    if isinstance(move, BoardMove):
        record.apply_move(move.source, move.destination, promote=move.promote)
    elif isinstance(move, DropMove):
        record.apply_drop(move.piece_type, move.destination)
    else:
        raise ValueError("未対応の一手データです")


def _position_key(position: Position) -> tuple:
    """盤上駒・所有側、双方の持ち駒、手番を完全値で比べるキーを返す。"""
    board = tuple(
        (piece.piece_type, piece.side)
        if (piece := position.board.piece_at(square))
        else None
        for square in _all_squares()
    )
    hands = tuple(
        hand.count(piece_type)
        for hand in (position.sente_hand, position.gote_hand)
        for piece_type in BasicPieceType
        if piece_type is not BasicPieceType.KING
    )
    return board, hands, position.side_to_move


def _all_squares():
    """比較キーに使う全81マスを筋・段順で返す。"""
    return tuple(Square(file, rank) for file in range(1, 10) for rank in range(1, 10))


_TERMINAL_REPETITION_KINDS = {
    RepetitionOutcomeKind.REPETITION,
    RepetitionOutcomeKind.PERPETUAL_CHECK_LOSS,
    RepetitionOutcomeKind.UNRESOLVED_DOUBLE_PERPETUAL_CHECK,
}


def conditions_payload(
    config: ComparisonConfig,
    schedule: Sequence[ScheduledGame],
    *,
    source_root: Path,
) -> dict[str, object]:
    """実験条件・局面入力・環境・ソース指紋をJSON値へ変換する。

    引数:
        config: 入力検証済み比較条件。局面ファイルの読込時バイト列を含む。
        schedule: 条件から生成済みの全局予定。
        source_root: `kaname_shogi` パッケージを含むGit作業ルート。

    戻り値:
        条件のハッシュ対象内容を持つ新しいJSON互換辞書。

    副作用:
        読込済み局面バイト列、パッケージ内の全Pythonソース、Git状態、実行環境を読む。
        ファイルやGit作業状態を変更しない。

    前提条件:
        `schedule` は `make_schedule(config)` の全予定であり、`source_root` 以下に
        `kaname_shogi` パッケージがある。ソース指紋は未追跡を含む全 `.py` を
        POSIX相対パス順にし、4バイトのパス長・パス・8バイトの内容長・内容を連結する。
        Git情報が取れない場合はnull値と診断を記録し、実験条件の他部分は残す。
    """
    if tuple(schedule) != make_schedule(config):
        raise ValueError("条件JSONの予定が比較条件から生成した予定と一致しません")
    package_root = Path(source_root) / "kaname_shogi"
    return {
        "format": _CONDITIONS_FORMAT,
        "baseline": _policy_name(config.baseline),
        "candidate": _policy_name(config.candidate),
        "positions_file": str(config.positions_path),
        "positions_sha256": hashlib.sha256(config.positions_json).hexdigest(),
        "positions": [
            {
                "id": position.position_id,
                "setup_moves": list(position.setup_moves),
                "rationale": position.rationale,
                "start_sfen": position.start_sfen,
                "initial_move_number": position.initial_move_number,
            }
            for position in config.positions
        ],
        "pairs_per_position": config.pairs_per_position,
        "seed": config.seed,
        "max_plies": config.max_plies,
        "schedule": [_scheduled_game_payload(game) for game in schedule],
        "timing": {
            "source": "time.monotonic_ns",
            "start": "immediately_before_legal_moves",
            "end": "immediately_after_choose_move_returns",
            "unit": "nanoseconds",
        },
        "clock": None,
        "repetition": {
            "ordinary_fourth_occurrence": "continue",
            "ordinary_fifth_occurrence": "terminal",
            "ordinary_rematch": False,
            "perpetual_check_loss": "opposite_side_wins",
            "double_perpetual_check": "unresolved_no_winner",
        },
        "git": _git_metadata(source_root),
        "runtime": {
            "python_version": sys.version.split()[0],
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine() or None,
            "processor": platform.processor() or None,
        },
        "source_sha256": _source_sha256(package_root),
    }


def game_payload(
    result: GameResult,
    config: ComparisonConfig,
    *,
    conditions_sha256: str,
) -> dict[str, object]:
    """確定済み一局の比較情報と既存棋譜v1をJSON値へ変換する。

    引数:
        result: 成功手、排他的終局理由、勝者、計時を保持する一局結果。
        config: 基準・候補方式を持つ比較条件。
        conditions_sha256: 条件JSONの保存済みバイト列に対するSHA-256小文字16進値。

    戻り値:
        予定・終局・計時・棋譜v1を含む新しいJSON互換辞書。

    例外:
        ValueError: 条件ハッシュ、勝者と終局理由、成功手数と記録が不整合の場合。

    副作用:
        なし。`GameRecord.to_payload()` が返す新しい辞書を読み、棋譜内部を変更しない。

    前提条件:
        比較固有情報は棋譜v1の外側に置く。勝者を持てる理由は詰み・合法手なし・
        片側連続王手負けだけで、通常千日手・双方未裁定・上限・割込み・故障は勝者なし。
    """
    if re.fullmatch(r"[0-9a-f]{64}", conditions_sha256) is None:
        raise ValueError("条件SHA-256は小文字16進64文字で指定してください")
    if result.plies != len(result.record.moves):
        raise ValueError("成功手数と棋譜手数が一致しません")
    if result.plies != len(result.move_times_ns):
        raise ValueError("成功手数と一手計時件数が一致しません")
    if result.reason is GameEndReason.ERROR:
        if not result.error:
            raise ValueError("故障理由には診断文字列が必要です")
    elif result.error is not None:
        raise ValueError("故障以外の終局理由に故障文字列を指定できません")
    has_winner = result.reason in _WINNING_END_REASONS
    if has_winner != (
        result.winner_side is not None and result.winner_policy is not None
    ):
        raise ValueError("終局理由と勝者情報が一致しません")
    if (result.winner_side is None) != (result.winner_policy is None):
        raise ValueError("勝者の先後と方式を同時に指定してください")
    if result.winner_side is not None:
        expected_winner_policy = (
            config.baseline
            if result.winner_side is result.schedule.baseline_side
            else config.candidate
        )
        if result.winner_policy is not expected_winner_policy:
            raise ValueError("勝者側と勝者方式が予定に一致しません")

    for expected_ply, timing in enumerate(result.move_times_ns, start=1):
        expected_policy = (
            config.baseline
            if timing.side is result.schedule.baseline_side
            else config.candidate
        )
        if timing.ply != expected_ply:
            raise ValueError("一手計時の手数順が成功手と一致しません")
        if timing.policy is not expected_policy:
            raise ValueError("一手計時の先後と方式が予定に一致しません")
        if type(timing.elapsed_ns) is not int or timing.elapsed_ns < 0:
            raise ValueError("成功手計時は0以上の整数で指定してください")

    game = result.schedule
    return {
        "format": _GAME_FORMAT,
        "conditions_sha256": conditions_sha256,
        **_scheduled_game_payload(game),
        "baseline": _policy_name(config.baseline),
        "candidate": _policy_name(config.candidate),
        "start_sfen": result.start_sfen,
        "initial_move_number": result.initial_move_number,
        "plies": result.plies,
        "reason": result.reason.value,
        "winner_side": _side_name(result.winner_side)
        if result.winner_side is not None
        else None,
        "winner_policy": _policy_name(result.winner_policy)
        if result.winner_policy is not None
        else None,
        "record": result.record.to_payload(),
        "move_times": [
            {
                "ply": timing.ply,
                "side": _side_name(timing.side),
                "policy": _policy_name(timing.policy),
                "move": _format_move(timing.move),
                "elapsed_ns": timing.elapsed_ns,
            }
            for timing in result.move_times_ns
        ],
        "unfinished_calculation": result.unfinished_calculation_ns,
        "error": result.error,
    }


def summary_payload(summary: Mapping[str, object]) -> dict[str, object]:
    """記述集計へ固定形式版を加え、summary JSON値を作る。

    引数:
        summary: `comparison.summarize()` が返した書式版なしの集計辞書。

    戻り値:
        summary形式版を先頭に加え、入力項目を保持した新しい辞書。

    例外:
        ValueError: 入力がMappingでない、または形式版をすでに含む場合。

    副作用:
        なし。入力mappingを変更しない。

    前提条件:
        勝率・統計的判断を追加せず、集計をJSONへ渡す形式版だけを補う。
    """
    if not isinstance(summary, Mapping):
        raise ValueError("summaryはMappingで指定してください")
    if "format" in summary:
        raise ValueError("summaryには形式版を重ねて指定できません")
    return {"format": _SUMMARY_FORMAT, **summary}


def atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    """同じディレクトリの一時ファイルからJSONを原子的に置換する。

    引数:
        path: 保存先ファイル。親ディレクトリは事前に存在する。
        payload: JSONへ変換可能なmapping。

    戻り値:
        なし（None）。成功時はpathが新しい整形済みUTF-8 JSONを指す。

    例外:
        OSError: 一時ファイルの作成・書込・置換に失敗した場合。
        TypeError / ValueError: payloadがJSONへ変換できない場合。

    副作用:
        同じディレクトリに一時ファイルを作り、flush・close後に`os.replace`で置換する。
        失敗時は一時ファイルを削除し、既存確定ファイルを直接変更しない。

    前提条件:
        同一ファイルシステム内のrename置換を使うため一ファイル単位の原子性を提供する。
        複数JSON間のトランザクションや電源断後の永続性は保証しない。
    """
    destination = Path(path)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary_path = Path(output.name)
            output.write(_json_bytes(payload))
            output.flush()
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def _json_bytes(payload: Mapping[str, object]) -> bytes:
    """JSON値を一時保存・SHA対象に共有するUTF-8バイト列へ整形する。"""
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def _scheduled_game_payload(game: ScheduledGame) -> dict[str, object]:
    """一局予定の比較条件をJSON値へ変換する。"""
    return {
        "game_id": game.game_id,
        "position_id": game.position_id,
        "pair_number": game.pair_number,
        "game_number_in_pair": game.game_number_in_pair,
        "baseline_side": _side_name(game.baseline_side),
        "candidate_side": _side_name(game.candidate_side),
        "baseline_seed": game.baseline_seed,
        "candidate_seed": game.candidate_seed,
    }


def _git_metadata(source_root: Path) -> dict[str, object]:
    """HEAD・dirty状態を読み、取得不能ならnullと診断を返す。"""
    try:
        head_result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=source_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if head_result.returncode != 0:
            detail = head_result.stderr.strip() or "git rev-parse failed"
            raise RuntimeError(detail)
        status_result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=source_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if status_result.returncode != 0:
            detail = status_result.stderr.strip() or "git status failed"
            raise RuntimeError(detail)
        return {
            "head": head_result.stdout.strip() or None,
            "dirty": bool(status_result.stdout.strip()),
            "diagnostic": None,
        }
    except (OSError, RuntimeError) as error:
        return {
            "head": None,
            "dirty": None,
            "diagnostic": f"{type(error).__name__}: {error}",
        }


def _source_sha256(package_root: Path) -> str:
    """全PythonソースをPOSIX相対パス順・長さ前置でSHA-256化する。"""
    if not package_root.is_dir():
        raise ValueError("kaname_shogiソースディレクトリがありません")
    digest = hashlib.sha256()
    paths = sorted(
        package_root.rglob("*.py"),
        key=lambda path: path.relative_to(package_root).as_posix(),
    )
    for path in paths:
        relative_path = path.relative_to(package_root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative_path).to_bytes(4, "big", signed=False))
        digest.update(relative_path)
        digest.update(len(content).to_bytes(8, "big", signed=False))
        digest.update(content)
    return digest.hexdigest()


def _format_move(move: BoardMove | DropMove) -> str:
    """局面非依存Move値を保存可能なUSI一手文字列へ変換する。"""
    return format_usi_move(move)
