"""完了した比較成果物を照合し、分析可能な一組得点へ変換する。"""

from __future__ import annotations

import argparse
import hashlib
import platform
import re
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from . import comparison_io
from .comparison import (
    BatchStatus,
    ComparisonConfig,
    ComparisonPosition,
    GameEndReason,
    GameResult,
    MoveTiming,
    ScheduledGame,
    board_terminal,
    make_schedule,
    repetition_terminal,
    summarize,
)
from .comparison_analysis import (
    CONFIDENCE_LEVEL,
    PairScore,
    ScoreAnalysis,
    analyze_scores,
    game_score_bounds,
    make_pair_score,
)
from .comparison_artifact_io import decode_object, write_new_json
from .comparison_seeds import parse_seed_plan, validate_seed_plan
from .game_record import GameRecord, RecordedDrop, RecordedMove
from .model import Side
from .move import BoardMove, DropMove
from .movegen import MoveSelectionPolicy, legal_moves
from .repetition import RepetitionTracker
from .sfen import SfenPosition, format_sfen, parse_sfen
from .usi_move import format_usi_move, parse_usi_move

_CONDITIONS_FORMAT = "kaname-shogi-comparison-conditions-v2"
_CONDITIONS_V3_FORMAT = "kaname-shogi-comparison-conditions-v3"
_GAME_FORMAT = "kaname-shogi-comparison-game-v1"
_SUMMARY_FORMAT = "kaname-shogi-comparison-summary-v1"
_SUMMARY_V2_FORMAT = "kaname-shogi-comparison-summary-v2"
_ANALYSIS_FORMAT = "kaname-shogi-comparison-analysis-v1"
_CONDITIONS_KEYS = {
    "format",
    "baseline",
    "candidate",
    "positions_file",
    "positions_sha256",
    "positions",
    "pairs_per_position",
    "seed",
    "max_plies",
    "schedule",
    "timing",
    "clock",
    "repetition",
    "git",
    "runtime",
    "source_sha256",
    "positions_json",
    "randomization",
    "policy_parameters",
}
_CONDITIONS_V3_KEYS = _CONDITIONS_KEYS | {"execution"}
_GAME_KEYS = {
    "format",
    "conditions_sha256",
    "game_id",
    "position_id",
    "pair_number",
    "game_number_in_pair",
    "baseline",
    "candidate",
    "baseline_seed",
    "candidate_seed",
    "baseline_side",
    "candidate_side",
    "start_sfen",
    "initial_move_number",
    "plies",
    "reason",
    "winner_side",
    "winner_policy",
    "record",
    "move_times",
    "unfinished_calculation",
    "error",
}
_SUMMARY_KEYS = {
    "format",
    "status",
    "planned_games",
    "started_games",
    "ended_games",
    "unstarted_games",
    "completed_pairs",
    "partial_pairs",
    "results",
    "perpetual_check_losses",
    "by_position",
    "by_side",
    "move_time_by_policy",
    "elapsed_ns",
    "statistical_decision",
}
_SUMMARY_V2_KEYS = _SUMMARY_KEYS | {"in_flight_games"}


@dataclass(frozen=True)
class LoadedComparison:
    """成果物の相互検証を終え、分析へ渡せる比較実験データ。

    引数:
        input_dir: 読み込んだ完了成果物ディレクトリ。
        conditions: 厳密検証済みのconditions v2/v3辞書。
        conditions_sha256: 読込時条件JSONバイト列のSHA-256。
        artifact_hashes: 読込時のconditions・予定局・summaryのファイル名とSHA-256。
        config: 条件スナップショットから復元した比較条件。
        schedule: 固定種一覧から再生成した全局予定。
        results: 合法再生・終局照合済みの局結果。
        summary: 再集計と完全一致したsummary辞書。
        pair_scores: 先後交換各組の候補方式得点上下限。
        elapsed_ns: summaryに保存された実験の経過ナノ秒。

    戻り値:
        分析済みの比較実験全体を保持する変更不可データ。

    副作用:
        なし。辞書とPositionは内包するが読取後に変更しない。

    前提条件:
        旧conditions v1、中断・故障、欠落・余分な局、外部リンク、条件不一致を
        受け入れず、確定済みの全組だけを保持する。
    """

    input_dir: Path
    conditions: dict[str, object]
    conditions_sha256: str
    config: ComparisonConfig
    schedule: tuple[ScheduledGame, ...]
    results: tuple[GameResult, ...]
    summary: dict[str, object]
    pair_scores: tuple[PairScore, ...]
    artifact_hashes: tuple[tuple[str, str], ...]
    elapsed_ns: int

    @property
    def baseline(self) -> MoveSelectionPolicy:
        """条件で使った基準方式を返す読み取り値。"""
        return self.config.baseline

    @property
    def candidate(self) -> MoveSelectionPolicy:
        """条件で使った候補方式を返す読み取り値。"""
        return self.config.candidate

    @property
    def purpose(self) -> str:
        """pilotまたはconfirmationの事前登録目的を返す読み取り値。"""
        assert self.config.seed_plan is not None
        return self.config.seed_plan.purpose


def load_completed_comparison(input_dir: Path) -> LoadedComparison:
    """完了比較一式を厳密検証し、候補方式視点の組得点へ変換する。

    引数:
        input_dir: conditions.json・全予定局・summary.jsonを含むディレクトリ。

    戻り値:
        一件の成果物も欠かさず条件、棋譜、終局、計時、再集計を照合した値。

    例外:
        ValueError: 形式、ハッシュ、予定、局、棋譜、終局、summaryが不整合の場合。
        OSError: 必要成果物を読めない場合。

    副作用:
        入力ディレクトリ内のJSONだけを読み、ファイルや他の場所を変更しない。

    前提条件:
        独立抽出種一覧を保存したconditions v2/v3を分析対象とし、summary v1/v2の完了状態を
        検証する。v2 conditionsは逐次、v3はprocess-pool 2〜4 workerで、summary版も
        対応させる。v2 summaryは投入中0が必須。ファイル名は予定IDから構成し、JSONの任意
        パス参照を開かない。乱数や壁時計を再実行しない。
    """
    root = Path(input_dir)
    if not root.is_dir():
        raise ValueError("比較結果入力先はディレクトリで指定してください")
    root = root.resolve()
    conditions_raw = _read_artifact(root, "conditions.json")
    conditions = decode_object(conditions_raw, context="比較条件")
    config, schedule = _load_conditions(conditions, root)
    conditions_sha256 = hashlib.sha256(conditions_raw).hexdigest()
    artifact_hashes: list[tuple[str, str]] = [("conditions.json", conditions_sha256)]

    expected_names = {f"{game.game_id}.json" for game in schedule}
    actual_names = {path.name for path in root.glob("game-*.json")}
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        raise ValueError(
            f"保存局の集合が予定と不一致です (不足={missing}, 余分={extra})"
        )

    results: list[GameResult] = []
    for game in schedule:
        raw = _read_artifact(root, f"{game.game_id}.json")
        artifact_hashes.append(
            (f"{game.game_id}.json", hashlib.sha256(raw).hexdigest())
        )
        payload = decode_object(raw, context=f"{game.game_id}局")
        results.append(
            _load_game(
                payload,
                game,
                config,
                conditions_sha256=conditions_sha256,
            )
        )

    summary_raw = _read_artifact(root, "summary.json")
    artifact_hashes.append(("summary.json", hashlib.sha256(summary_raw).hexdigest()))
    summary = decode_object(summary_raw, context="比較summary")
    summary_format = summary.get("format")
    if summary_format == _SUMMARY_FORMAT:
        _require_exact_keys(summary, _SUMMARY_KEYS, "比較summary")
    elif summary_format == _SUMMARY_V2_FORMAT:
        _require_exact_keys(summary, _SUMMARY_V2_KEYS, "比較summary")
        in_flight_games = summary["in_flight_games"]
        if type(in_flight_games) is not int or in_flight_games < 0:
            raise ValueError("summary投入中局数は0以上の整数で指定してください")
        if in_flight_games != 0:
            raise ValueError("投入中の局が残るsummaryは分析できません")
    else:
        raise ValueError("比較summary形式が対応していません")
    expected_summary_format = (
        _SUMMARY_V2_FORMAT if config.workers > 1 else _SUMMARY_FORMAT
    )
    if summary_format != expected_summary_format:
        raise ValueError("比較条件とsummary形式の組み合わせが不正です")
    elapsed_ns = summary["elapsed_ns"]
    if type(elapsed_ns) is not int or elapsed_ns < 0:
        raise ValueError("summary経過時間は0以上の有限整数で指定してください")
    expected_summary = summary_payload_for_results(
        config, results, elapsed_ns=elapsed_ns
    )
    if not _json_values_equal(summary, expected_summary):
        raise ValueError("summaryが保存局の再集計または実行件数と一致しません")

    pair_scores = _score_pairs(schedule, results, config.candidate)
    return LoadedComparison(
        input_dir=root,
        conditions=conditions,
        conditions_sha256=conditions_sha256,
        config=config,
        schedule=schedule,
        results=tuple(results),
        summary=summary,
        pair_scores=pair_scores,
        artifact_hashes=tuple(artifact_hashes),
        elapsed_ns=elapsed_ns,
    )


def summary_payload_for_results(
    config: ComparisonConfig, results: Sequence[GameResult], *, elapsed_ns: int
) -> dict[str, object]:
    """保存局から既存の記述集計形式を再構成する。"""
    return comparison_io.summary_payload(
        summarize(
            config,
            results,
            batch_status=BatchStatus.COMPLETE,
            unstarted_games=0,
            elapsed_ns=elapsed_ns,
        )
    )


def analysis_payload(
    loaded: LoadedComparison,
    analysis: ScoreAnalysis,
    *,
    source_root: Path,
) -> dict[str, object]:
    """全体一回の区間判定と記述集計をJSON値へまとめる。

    引数:
        loaded: 相互検証済み完了比較。
        analysis: 全組を一度だけ集計した主判定。
        source_root: 現在のソース指紋とGit情報を読む作業ルート。

    戻り値:
        入力ファイルハッシュ・分析時識別・全体95%区間・全局件数・局面別/先後別記述集計・
        実験時間と計時を含む承認済み形式のJSON互換辞書。

    例外:
        ValueError: 入力型、組数、目的がloadedと一致しない場合。

    副作用:
        現行パッケージのPythonソースとGit状態を読み取る。入力成果物は変更しない。

    前提条件:
        局面別・先後別集計は記述値として扱い、95%信頼水準の主判定を重複適用しない。
        現在ソースの違いは記録するだけで、当時のソース識別と違っても拒否しない。
    """
    if not isinstance(loaded, LoadedComparison) or not isinstance(
        analysis, ScoreAnalysis
    ):
        raise ValueError("分析成果物には検証済み比較とScoreAnalysisが必要です")
    if analysis != analyze_scores(loaded.pair_scores, purpose=loaded.purpose):
        raise ValueError("分析値が検証済み比較の組数・目的・得点と一致しません")
    hashes = dict(loaded.artifact_hashes)
    return {
        "format": _ANALYSIS_FORMAT,
        "inputs": {
            "conditions": {
                "file": "conditions.json",
                "sha256": hashes["conditions.json"],
            },
            "games": [
                {"file": filename, "sha256": digest}
                for filename, digest in loaded.artifact_hashes
                if filename.startswith("game-")
            ],
            "summary": {"file": "summary.json", "sha256": hashes["summary.json"]},
        },
        "analyzer": {
            "source_sha256": comparison_io._source_sha256(
                Path(source_root) / "kaname_shogi"
            ),
            "git": comparison_io._git_metadata(Path(source_root)),
            "runtime": {
                "python_version": sys.version.split()[0],
                "python_implementation": platform.python_implementation(),
                "platform": platform.platform(),
            },
        },
        "purpose": loaded.purpose,
        "baseline": comparison_io._policy_name(loaded.baseline),
        "candidate": comparison_io._policy_name(loaded.candidate),
        "assumptions": {
            "independent_unit": "pair",
            "games_within_pair_independent": False,
            "identically_distributed_pairs_required": False,
            "primary_comparisons": 1,
            "configured_positions_equal_weight": True,
            "unresolved_game_score_bounds": [0.0, 1.0],
        },
        "confidence_level": CONFIDENCE_LEVEL,
        "method": "hoeffding-paired-bounds-v1",
        "planned_games": len(loaded.schedule),
        "completed_pairs": len(loaded.pair_scores),
        "counts": _overall_counts(loaded),
        "score": {
            "lower_mean": float(analysis.lower_mean),
            "upper_mean": float(analysis.upper_mean),
            "radius": analysis.radius,
            "lower": analysis.lower,
            "upper": analysis.upper,
            "decision": analysis.decision,
        },
        "by_position": _position_summaries(loaded),
        "by_side": _candidate_side_summaries(loaded),
        "move_time_by_policy": loaded.summary["move_time_by_policy"],
        "elapsed_ns": loaded.elapsed_ns,
    }


def _load_conditions(
    conditions: dict[str, object], input_dir: Path
) -> tuple[ComparisonConfig, tuple[ScheduledGame, ...]]:
    """条件v2/v3全体を検証し、予定生成へ必要な型付き条件を作る。"""
    conditions_format = conditions.get("format")
    if conditions_format == _CONDITIONS_FORMAT:
        _require_exact_keys(conditions, _CONDITIONS_KEYS, "比較条件")
        workers = 1
    elif conditions_format == _CONDITIONS_V3_FORMAT:
        _require_exact_keys(conditions, _CONDITIONS_V3_KEYS, "比較条件")
        workers = _execution_workers(conditions["execution"])
    else:
        _require_exact_keys(conditions, _CONDITIONS_KEYS, "比較条件")
        raise ValueError("独立抽出種一覧に対応したconditions v2/v3が必要です")
    baseline = _policy(conditions["baseline"], "基準方式")
    candidate = _policy(conditions["candidate"], "候補方式")
    if baseline is candidate:
        raise ValueError("基準方式と候補方式は異なる必要があります")
    if not isinstance(conditions["positions_file"], str):
        raise ValueError("元局面ファイル名が文字列ではありません")
    if conditions["seed"] is not None:
        raise ValueError("conditions v2の独立抽出方式に主乱数種は指定できません")
    positions_raw = _embedded_json(conditions["positions_json"], "局面スナップショット")
    positions_sha256 = _sha256_value(conditions["positions_sha256"], "局面SHA-256")
    if hashlib.sha256(positions_raw).hexdigest() != positions_sha256:
        raise ValueError("局面スナップショットのSHA-256が条件と一致しません")
    positions = comparison_io.positions_from_bytes(positions_raw)
    position_descriptors = [
        {
            "id": position.position_id,
            "setup_moves": list(position.setup_moves),
            "rationale": position.rationale,
            "start_sfen": position.start_sfen,
            "initial_move_number": position.initial_move_number,
        }
        for position in positions
    ]
    if not _json_values_equal(conditions["positions"], position_descriptors):
        raise ValueError("条件局面と局面JSONスナップショットが一致しません")

    randomization = _object(conditions["randomization"], "乱数条件")
    _require_exact_keys(
        randomization,
        {"purpose", "source", "bits", "seed_list_sha256", "seed_list_json"},
        "乱数条件",
    )
    seed_raw = _embedded_json(randomization["seed_list_json"], "乱数種スナップショット")
    seed_sha256 = _sha256_value(randomization["seed_list_sha256"], "乱数種SHA-256")
    if hashlib.sha256(seed_raw).hexdigest() != seed_sha256:
        raise ValueError("乱数種スナップショットのSHA-256が条件と一致しません")
    seed_plan = parse_seed_plan(seed_raw)
    if (
        randomization["purpose"] != seed_plan.purpose
        or randomization["source"] != "os"
        or type(randomization["bits"]) is not int
        or randomization["bits"] != 128
    ):
        raise ValueError("乱数条件が保存済み一覧の目的・抽出仕様と一致しません")
    pairs_per_position = conditions["pairs_per_position"]
    validate_seed_plan(
        seed_plan,
        position_ids=tuple(position.position_id for position in positions),
        positions_sha256=positions_sha256,
        pairs_per_position=pairs_per_position,
    )
    if not _json_values_equal(
        conditions["policy_parameters"],
        {
            "baseline": _policy_parameter_payload(baseline),
            "candidate": _policy_parameter_payload(candidate),
        },
    ):
        raise ValueError("実験時方式の評価重みが現在の方式契約と一致しません")
    _validate_condition_metadata(conditions)
    config = ComparisonConfig(
        baseline=baseline,
        candidate=candidate,
        positions=positions,
        pairs_per_position=pairs_per_position,
        seed=None,
        max_plies=conditions["max_plies"],
        output_dir=input_dir,
        positions_path=Path(conditions["positions_file"]),
        positions_json=positions_raw,
        workers=workers,
        seed_plan=seed_plan,
        seed_list_json=seed_raw,
        seed_list_path=None,
    )
    schedule = make_schedule(config)
    expected_schedule = [
        comparison_io._scheduled_game_payload(game) for game in schedule
    ]
    if not _json_values_equal(conditions["schedule"], expected_schedule):
        raise ValueError("条件に保存された局予定が種一覧から再生成した予定と違います")
    return config, schedule


def _execution_workers(value: object) -> int:
    """conditions v3の固定spawn実行条件を検証し、worker数を返す。"""
    execution = _object(value, "実行条件")
    _require_exact_keys(execution, {"executor", "workers"}, "実行条件")
    if execution["executor"] != "process-pool":
        raise ValueError("実行方式はprocess-poolで指定してください")
    workers = execution["workers"]
    if type(workers) is not int or not 2 <= workers <= 4:
        raise ValueError("worker数は2〜4の整数で指定してください")
    return workers


def _validate_condition_metadata(conditions: Mapping[str, object]) -> None:
    """条件の固定仕様、実行環境、コード識別の型と値を検証する。"""
    if (
        type(conditions["pairs_per_position"]) is not int
        or conditions["pairs_per_position"] < 1
    ):
        raise ValueError("局面ごとの組数は1以上の整数で指定してください")
    if type(conditions["max_plies"]) is not int or conditions["max_plies"] < 1:
        raise ValueError("成功手上限は1以上の整数で指定してください")
    if conditions["clock"] is not None:
        raise ValueError("比較条件に対応しない時計設定があります")
    timing = _object(conditions["timing"], "計時条件")
    _require_exact_keys(timing, {"source", "start", "end", "unit"}, "計時条件")
    if not _json_values_equal(
        timing,
        {
            "source": "time.monotonic_ns",
            "start": "immediately_before_legal_moves",
            "end": "immediately_after_choose_move_returns",
            "unit": "nanoseconds",
        },
    ):
        raise ValueError("計時条件が対応形式と一致しません")
    repetition = _object(conditions["repetition"], "千日手条件")
    _require_exact_keys(
        repetition,
        {
            "ordinary_fourth_occurrence",
            "ordinary_fifth_occurrence",
            "ordinary_rematch",
            "perpetual_check_loss",
            "double_perpetual_check",
        },
        "千日手条件",
    )
    if not _json_values_equal(
        repetition,
        {
            "ordinary_fourth_occurrence": "continue",
            "ordinary_fifth_occurrence": "terminal",
            "ordinary_rematch": False,
            "perpetual_check_loss": "opposite_side_wins",
            "double_perpetual_check": "unresolved_no_winner",
        },
    ):
        raise ValueError("千日手条件が対応形式と一致しません")
    git = _object(conditions["git"], "実験時Git情報")
    _require_exact_keys(git, {"head", "dirty", "diagnostic"}, "実験時Git情報")
    if git["head"] is not None and (
        not isinstance(git["head"], str)
        or re.fullmatch(r"[0-9a-f]{40,64}", git["head"]) is None
    ):
        raise ValueError("実験時Git HEADが不正です")
    if git["dirty"] is not None and type(git["dirty"]) is not bool:
        raise ValueError("実験時Git dirty値が不正です")
    if git["diagnostic"] is not None and not isinstance(git["diagnostic"], str):
        raise ValueError("実験時Git診断が不正です")
    runtime = _object(conditions["runtime"], "実行環境")
    _require_exact_keys(
        runtime,
        {
            "python_version",
            "python_implementation",
            "platform",
            "machine",
            "processor",
        },
        "実行環境",
    )
    for key in ("python_version", "python_implementation", "platform"):
        if not isinstance(runtime[key], str) or not runtime[key]:
            raise ValueError(f"実行環境の{key}が空または文字列ではありません")
    for key in ("machine", "processor"):
        if runtime[key] is not None and not isinstance(runtime[key], str):
            raise ValueError(f"実行環境の{key}が文字列またはnullではありません")
    _sha256_value(conditions["source_sha256"], "実験時ソースSHA-256")


def _load_game(
    payload: dict[str, object],
    expected_schedule: ScheduledGame,
    config: ComparisonConfig,
    *,
    conditions_sha256: str,
) -> GameResult:
    """一局の保存値を予定・合法棋譜・終局・計時と照合してGameResultにする。"""
    _require_exact_keys(payload, _GAME_KEYS, f"{expected_schedule.game_id}局")
    if payload["format"] != _GAME_FORMAT:
        raise ValueError(f"{expected_schedule.game_id}局形式が対応していません")
    if payload["conditions_sha256"] != conditions_sha256:
        raise ValueError(f"{expected_schedule.game_id}局が別conditionsを参照しています")
    expected_payload = comparison_io._scheduled_game_payload(expected_schedule)
    for key, value in expected_payload.items():
        if not _json_values_equal(payload[key], value):
            raise ValueError(
                f"{expected_schedule.game_id}局の予定値 {key} が一致しません"
            )
    if payload["baseline"] != comparison_io._policy_name(config.baseline) or payload[
        "candidate"
    ] != comparison_io._policy_name(config.candidate):
        raise ValueError(f"{expected_schedule.game_id}局の方式が条件と一致しません")

    position_by_id = {position.position_id: position for position in config.positions}
    position = position_by_id[expected_schedule.position_id]
    start_sfen = payload["start_sfen"]
    initial_move_number = payload["initial_move_number"]
    if (
        not isinstance(start_sfen, str)
        or type(initial_move_number) is not int
        or initial_move_number != position.initial_move_number
        or start_sfen != position.start_sfen
    ):
        raise ValueError(f"{expected_schedule.game_id}局の比較開始SFENが一致しません")
    try:
        parsed_start = parse_sfen(start_sfen)
    except ValueError as error:
        raise ValueError(f"{expected_schedule.game_id}局のSFENが不正です") from error
    if parsed_start.move_number != initial_move_number:
        raise ValueError(f"{expected_schedule.game_id}局のSFEN手数が一致しません")

    record = GameRecord.from_payload(payload["record"])
    recorded_start = format_sfen(
        SfenPosition(record.initial_position, initial_move_number)
    )
    if recorded_start != start_sfen:
        raise ValueError(f"{expected_schedule.game_id}局の棋譜開始局面が一致しません")
    plies = payload["plies"]
    if type(plies) is not int or plies != len(record.moves):
        raise ValueError(f"{expected_schedule.game_id}局の手数と棋譜が一致しません")
    if payload["unfinished_calculation"] is not None or payload["error"] is not None:
        raise ValueError(
            f"{expected_schedule.game_id}局に未確定計算または故障が残っています"
        )

    terminal, move_times = _validate_and_replay(
        payload["move_times"],
        expected_schedule,
        config,
        position,
        record,
    )
    reason = _reason(payload["reason"])
    winner_side = _optional_side(payload["winner_side"], "勝者先後")
    winner_policy = _optional_policy(payload["winner_policy"], "勝者方式")
    if terminal != (reason, winner_side):
        raise ValueError(
            f"{expected_schedule.game_id}局の終局理由または勝者が棋譜と違います"
        )
    expected_winner_policy = None
    if winner_side is not None:
        expected_winner_policy = (
            config.baseline
            if winner_side is expected_schedule.baseline_side
            else config.candidate
        )
    if winner_policy is not expected_winner_policy:
        raise ValueError(f"{expected_schedule.game_id}局の勝者先後と方式が一致しません")
    return GameResult(
        schedule=expected_schedule,
        start_sfen=start_sfen,
        initial_move_number=initial_move_number,
        record=record,
        reason=reason,
        winner_side=winner_side,
        winner_policy=winner_policy,
        plies=plies,
        move_times_ns=move_times,
        unfinished_calculation_ns=None,
        error=None,
    )


def _validate_and_replay(
    timings_value: object,
    schedule: ScheduledGame,
    config: ComparisonConfig,
    comparison_position: ComparisonPosition,
    record: GameRecord,
) -> tuple[tuple[GameEndReason, Side | None], tuple[MoveTiming, ...]]:
    """棋譜履歴を最初から再生し、途中終局・各手計時・最終終局を照合する。"""
    if type(timings_value) is not list or len(timings_value) != len(record.moves):
        raise ValueError(f"{schedule.game_id}局の成功手と計時件数が一致しません")
    replay = GameRecord(record.initial_position)
    tracker = RepetitionTracker(replay.current_position)
    move_times: list[MoveTiming] = []
    terminal: tuple[GameEndReason, Side | None] | None = None

    for ply in range(1, len(record.moves) + 1):
        recorded_move = record.moves[ply - 1]
        timing_value = timings_value[ply - 1]
        if terminal is not None:
            raise ValueError(f"{schedule.game_id}局が既終局後も指し継いでいます")
        timing = _object(timing_value, f"{schedule.game_id}局第{ply}計時")
        _require_exact_keys(
            timing, {"ply", "side", "policy", "move", "elapsed_ns"}, "一手計時"
        )
        current = replay.current_position
        side = current.side_to_move
        expected_policy = (
            config.baseline if side is schedule.baseline_side else config.candidate
        )
        if (
            type(timing["ply"]) is not int
            or timing["ply"] != ply
            or timing["side"] != _side_name(side)
            or timing["policy"] != comparison_io._policy_name(expected_policy)
        ):
            raise ValueError(f"{schedule.game_id}局第{ply}計時の手番・方式が不一致です")
        elapsed_ns = timing["elapsed_ns"]
        if type(elapsed_ns) is not int or elapsed_ns < 0:
            raise ValueError(
                f"{schedule.game_id}局第{ply}計時が0以上の整数ではありません"
            )
        move_token = timing["move"]
        if not isinstance(move_token, str):
            raise ValueError(
                f"{schedule.game_id}局第{ply}計時の手が文字列ではありません"
            )
        try:
            parsed_move = parse_usi_move(move_token)
        except ValueError as error:
            raise ValueError(
                f"{schedule.game_id}局第{ply}計時の手が不正です"
            ) from error
        if format_usi_move(parsed_move) != _format_recorded_move(recorded_move):
            raise ValueError(f"{schedule.game_id}局第{ply}計時の手が棋譜と一致しません")
        if isinstance(recorded_move, RecordedMove):
            replay.apply_move(
                recorded_move.source,
                recorded_move.destination,
                promote=recorded_move.promote,
            )
        else:
            replay.apply_drop(recorded_move.piece_type, recorded_move.destination)
        current = replay.current_position
        outcome = tracker.add_position(current)
        terminal = repetition_terminal(outcome)
        if terminal is None:
            candidates = legal_moves(current)
            terminal = board_terminal(
                current,
                has_legal_moves=bool(candidates),
                plies=ply,
                max_plies=config.max_plies,
            )
        move_times.append(
            MoveTiming(
                ply=ply,
                side=side,
                policy=expected_policy,
                move=parsed_move,
                elapsed_ns=elapsed_ns,
            )
        )

    if terminal is None:
        raise ValueError(f"{schedule.game_id}局の棋譜末尾で終局が成立していません")
    if replay.current_position.side_to_move is not record.current_position.side_to_move:
        raise ValueError(f"{schedule.game_id}局の合法再生結果が保存棋譜と違います")
    if format_sfen(
        SfenPosition(
            replay.current_position,
            comparison_position.initial_move_number + len(record.moves),
        )
    ) != format_sfen(
        SfenPosition(
            record.current_position,
            comparison_position.initial_move_number + len(record.moves),
        )
    ):
        raise ValueError(f"{schedule.game_id}局の合法再生局面が保存棋譜と違います")
    return terminal, tuple(move_times)


def _score_pairs(
    schedule: Sequence[ScheduledGame],
    results: Sequence[GameResult],
    candidate: MoveSelectionPolicy,
) -> tuple[PairScore, ...]:
    """予定済み各組の二局を候補方式視点で一度だけ平均する。"""
    results_by_id = {result.schedule.game_id: result for result in results}
    games_by_pair: dict[int, list[ScheduledGame]] = defaultdict(list)
    for game in schedule:
        games_by_pair[game.pair_number].append(game)
    scores = []
    for pair_number in sorted(games_by_pair):
        games = sorted(
            games_by_pair[pair_number], key=lambda game: game.game_number_in_pair
        )
        if len(games) != 2:
            raise ValueError(f"比較組{pair_number}に二局がありません")
        bounds = []
        for game in games:
            result = results_by_id[game.game_id]
            bounds.append(
                game_score_bounds(result.reason, result.winner_policy, candidate)
            )
        scores.append(make_pair_score((bounds[0], bounds[1])))
    return tuple(scores)


def _position_summaries(loaded: LoadedComparison) -> dict[str, object]:
    """局面別の結果件数と得点上下限平均を記述集計として返す。"""
    grouped: dict[str, list[PairScore]] = defaultdict(list)
    schedule_by_pair: dict[int, str] = {}
    for game in loaded.schedule:
        schedule_by_pair[game.pair_number] = game.position_id
    for pair_number, score in enumerate(loaded.pair_scores):
        grouped[schedule_by_pair[pair_number]].append(score)
    result_groups = {
        position.position_id: {
            **_empty_descriptive_counts(),
            "pairs": 0,
        }
        for position in loaded.config.positions
    }
    for result in loaded.results:
        counts = result_groups[result.schedule.position_id]
        _add_descriptive_result(counts, result, loaded.candidate)
    for position_id in schedule_by_pair.values():
        result_groups[position_id]["pairs"] = (
            int(result_groups[position_id]["pairs"]) + 1
        )
    return {
        position.position_id: {
            **result_groups[position.position_id],
            "mean_score_bounds": _mean_bounds(grouped[position.position_id]),
        }
        for position in loaded.config.positions
    }


def _candidate_side_summaries(loaded: LoadedComparison) -> dict[str, object]:
    """候補方式が先手・後手を担当した局の結果件数と得点を記述集計する。"""
    summaries = {side: _empty_descriptive_counts() for side in Side}
    for result in loaded.results:
        _add_descriptive_result(
            summaries[result.schedule.candidate_side], result, loaded.candidate
        )
    return {
        f"candidate_{_side_name(side)}": values for side, values in summaries.items()
    }


def _overall_counts(loaded: LoadedComparison) -> dict[str, object]:
    """全局の結果理由と候補方式視点の排他的結果件数を返す。"""
    counts = _empty_descriptive_counts()
    for result in loaded.results:
        _add_descriptive_result(counts, result, loaded.candidate)
    counts["completed_pairs"] = len(loaded.pair_scores)
    return counts


def _empty_descriptive_counts() -> dict[str, object]:
    """全終局理由を含む記述集計のゼロ値を作る。"""
    return {
        "games": 0,
        "candidate_wins": 0,
        "candidate_losses": 0,
        "ordinary_repetitions": 0,
        "ply_limits": 0,
        "unresolved_double_perpetual_checks": 0,
        "results": {reason.value: 0 for reason in GameEndReason},
    }


def _add_descriptive_result(
    counts: dict[str, object], result: GameResult, candidate: MoveSelectionPolicy
) -> None:
    """一局を終局理由と候補方式視点の勝敗件数へ加える。"""
    counts["games"] = int(counts["games"]) + 1
    result_counts = counts["results"]
    assert isinstance(result_counts, dict)
    result_counts[result.reason.value] = int(result_counts[result.reason.value]) + 1
    if result.winner_policy is candidate:
        counts["candidate_wins"] = int(counts["candidate_wins"]) + 1
    elif result.winner_policy is not None:
        counts["candidate_losses"] = int(counts["candidate_losses"]) + 1
    if result.reason is GameEndReason.REPETITION:
        counts["ordinary_repetitions"] = int(counts["ordinary_repetitions"]) + 1
    elif result.reason is GameEndReason.PLY_LIMIT:
        counts["ply_limits"] = int(counts["ply_limits"]) + 1
    elif result.reason is GameEndReason.UNRESOLVED_DOUBLE_PERPETUAL_CHECK:
        counts["unresolved_double_perpetual_checks"] = (
            int(counts["unresolved_double_perpetual_checks"]) + 1
        )


def _mean_bounds(scores: Sequence[PairScore]) -> dict[str, object]:
    """組得点列の上下限平均を記述用有限小数で返す。"""
    if not scores:
        return {"lower_mean": None, "upper_mean": None}
    lower = sum((score.lower for score in scores), Fraction(0)) / len(scores)
    upper = sum((score.upper for score in scores), Fraction(0)) / len(scores)
    return {
        "lower_mean": float(lower),
        "upper_mean": float(upper),
    }


def _format_recorded_move(move: RecordedMove | RecordedDrop) -> str:
    """棋譜形式の成功手をUSI形式へ変換する。"""
    if isinstance(move, RecordedMove):
        return format_usi_move(
            BoardMove(move.source, move.destination, promote=move.promote)
        )
    if isinstance(move, RecordedDrop):
        return format_usi_move(DropMove(move.piece_type, move.destination))
    raise ValueError("未知の棋譜手です")


def _policy_parameter_payload(policy: MoveSelectionPolicy) -> dict[str, object]:
    """conditions v2に保存した方式重みを独立した固定値で返す。"""
    return comparison_io._policy_parameters(policy)


def _policy(value: object, context: str) -> MoveSelectionPolicy:
    """安定した方式名をMoveSelectionPolicyへ検証変換する。"""
    if not isinstance(value, str) or value not in comparison_io._POLICIES:
        raise ValueError(f"{context}が未対応です")
    return comparison_io._POLICIES[value]


def _optional_policy(value: object, context: str) -> MoveSelectionPolicy | None:
    """勝者方式のnullまたは既知方式を読む。"""
    return None if value is None else _policy(value, context)


def _reason(value: object) -> GameEndReason:
    """保存文字列を終局理由へ厳密変換する。"""
    try:
        return GameEndReason(value)
    except (TypeError, ValueError) as error:
        raise ValueError("局の終局理由が未対応です") from error


def _optional_side(value: object, context: str) -> Side | None:
    """勝者先後のnullまたは既知値を読む。"""
    if value is None:
        return None
    if value == "sente":
        return Side.SENTE
    if value == "gote":
        return Side.GOTE
    raise ValueError(f"{context}が不正です")


def _side_name(side: Side) -> str:
    """先後列挙値を成果物用の小文字名へ変換する。"""
    return "sente" if side is Side.SENTE else "gote"


def _embedded_json(value: object, context: str) -> bytes:
    """conditions内のJSON文字列をUTF-8バイト列へ戻す。"""
    if not isinstance(value, str):
        raise ValueError(f"{context}はJSON文字列で指定してください")
    try:
        return value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(f"{context}は有効なUTF-8文字列ではありません") from error


def _sha256_value(value: object, context: str) -> str:
    """小文字16進SHA-256文字列を検証して返す。"""
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{context}は小文字16進64文字で指定してください")
    return value


def _read_artifact(root: Path, filename: str) -> bytes:
    """固定ファイル名の通常ファイルだけを入力ディレクトリ内から読む。"""
    path = root / filename
    if path.is_symlink() or not path.is_file() or path.resolve().parent != root:
        raise ValueError(f"必要な比較成果物が通常ファイルではありません: {filename}")
    return path.read_bytes()


def _object(value: object, context: str) -> dict[str, object]:
    """辞書型のJSONオブジェクトを取得する。"""
    if type(value) is not dict:
        raise ValueError(f"{context}はJSONオブジェクトで指定してください")
    return value


def _require_exact_keys(
    value: dict[str, object], expected: set[str], context: str
) -> None:
    """必須キー欠落と未知キーを拒否する。"""
    actual = set(value)
    missing = expected - actual
    unknown = actual - expected
    if missing or unknown:
        raise ValueError(
            f"{context}のキーが不正です (不足={sorted(missing)}, 未知={sorted(unknown)})"
        )


def _json_values_equal(left: object, right: object) -> bool:
    """JSON値をboolと数値型の同値混同なく再帰比較する。"""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(
            _json_values_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _json_values_equal(left[index], right[index]) for index in range(len(left))
        )
    return left == right


def main(argv: Sequence[str] | None = None) -> int:
    """完了した独立抽出比較を分析し、分析JSONを新規保存するCLI入口。

    引数:
        argv: `--input-dir`と`--output`を含む引数列。Noneなら通常CLI引数。

    戻り値:
        正常保存または判断不能/pilotは0、入力不正2、保存失敗1、中断130。

    例外:
        想定された入力・保存エラーとKeyboardInterruptは戻り値へ変換する。

    副作用:
        入力JSONを読み、指定先へ新規限定で分析JSONを保存し、日本語の要約を表示する。

    前提条件:
        既存の比較結果を再実行せず、一組単位で全体主判定を一回だけ計算する。
    """
    parser = _ValueErrorArgumentParser(
        prog="analyze-comparison",
        description="完了した比較実験の候補方式得点を分析します。",
    )
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    try:
        args = parser.parse_args(argv)
    except ValueError as error:
        parser.print_usage()
        print(f"入力エラー: {error}", file=sys.stderr)
        return 2
    try:
        _validate_new_output_path(args.output)
        loaded = load_completed_comparison(args.input_dir)
        analysis = analyze_scores(loaded.pair_scores, purpose=loaded.purpose)
        payload = analysis_payload(
            loaded,
            analysis,
            source_root=Path(__file__).resolve().parent.parent,
        )
    except KeyboardInterrupt:
        print("分析を中断しました。", file=sys.stderr)
        return 130
    except (OSError, ValueError) as error:
        print(f"入力エラー: {error}", file=sys.stderr)
        return 2
    try:
        write_new_json(args.output, payload)
    except KeyboardInterrupt:
        print("分析結果の保存を中断しました。", file=sys.stderr)
        return 130
    except (OSError, TypeError, ValueError) as error:
        print(f"分析結果を保存できません: {error}", file=sys.stderr)
        return 1
    print(f"分析完了: {len(loaded.results)}局、{len(loaded.pair_scores)}組")
    print(f"候補方式得点区間: [{analysis.lower:.3f}, {analysis.upper:.3f}]")
    print(f"判定: {_decision_ja(analysis.decision)}")
    print(f"分析結果: {args.output}")
    return 0


def _validate_new_output_path(path: Path) -> None:
    """出力先の既存・不在親・非ディレクトリ親を保存前に拒否する。"""
    output = Path(path)
    if output.exists() or output.is_symlink():
        raise ValueError(f"分析結果の出力先は新規パスが必要です: {output}")
    if not output.parent.is_dir():
        raise ValueError(f"分析結果の出力先親ディレクトリがありません: {output.parent}")


class _ValueErrorArgumentParser(argparse.ArgumentParser):
    """CLI構文不正を終了例外ではなく入力エラーへ変換する。"""

    def error(self, message: str) -> None:
        raise ValueError(message)


def _decision_ja(decision: str) -> str:
    """判定値を短い日本語表示へ変換する。"""
    return {
        "exploratory": "予備比較（強さの結論は出さない）",
        "improved": "改善を支持",
        "worsened": "悪化を支持",
        "inconclusive": "判断不能",
    }.get(decision, decision)
