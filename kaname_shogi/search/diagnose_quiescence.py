"""小局面で静止探索の追加量と完了状態を診断する開発用コマンド。"""

import argparse
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

from ..model import Position, Side
from ..move import Move
from ..search_control import SearchControl, SearchSignal
from ..time_management import (
    SearchBudget,
    TimeManagementConfig,
    calculate_search_budget,
    load_time_management_config,
)
from . import comparison, iterative_deepening, shogi
from .diagnostics import SearchCounters
from .result import (
    ControlledCompletion,
    ControlledSearchResult,
    IterationResult,
    QuiescenceLimit,
    SearchInterrupted,
)

_VARIANTS = ("baseline", "q2", "q4")
_MAX_DEPTH = 4


@dataclass(frozen=True)
class IterationDiagnostic:
    """反復一回の終了結果と、その反復内に増えた計数を保持する不変データ。

    引数:
        depth: 開始した通常探索の深さ、1以上。
        result: 完了記録、通常中断、静止探索上限のいずれか。
        normal_nodes: この反復中に増えた通常inspect呼出し数。
        quiescence_calls: この反復中に増えた静止探索呼出し数。
    戻り値:
        四つの値を保持する不変スナップショット。
    副作用:
        なし。累計カウンターは変更しない。
    前提条件・設計理由:
        探索本体の可変カウンターから反復終了時点で差分を切り出し、完了・未完了を
        同じ形式で観測する。終了結果の型を保ち、未完了反復に評価や訪問数を作らない。
    """

    depth: int
    result: IterationResult[Move] | SearchInterrupted | QuiescenceLimit
    normal_nodes: int
    quiescence_calls: int


@dataclass(frozen=True)
class DiagnosticResult:
    """一回の診断探索、経過時間、反復差分と全体計数を保持する不変データ。

    引数:
        result: 既存の制御付き反復深化が返した終了状態・手・最後の完了記録。
        elapsed_ns: 操作構築後から予備手準備・反復・観測保存までの経過ns。
        iterations: 開始した通常深さごとの終了結果と計数差分。
        total_normal_nodes: 探索中に増えた通常inspect呼出し総数。
        total_quiescence_calls: 探索中に増えた静止探索呼出し総数。
    戻り値:
        一回分の診断結果。各フィールドは代入で変更できない。
    副作用:
        なし。
    前提条件・設計理由:
        完了済み累計と未完了作業を混同しないよう、反復別差分と探索全体の実計数を
        別々に保持する。出力整形は計時の外で行う。
    """

    result: ControlledSearchResult[Move]
    elapsed_ns: int
    iterations: tuple[IterationDiagnostic, ...]
    total_normal_nodes: int
    total_quiescence_calls: int


def _make_parser() -> argparse.ArgumentParser:
    """局面・方式・時計値を必須で受け取る引数解析器を返す操作。

    戻り値はargparseの解析器。実行・設定読込は行わず、方式候補を三種類に限定する。
    一意な省略形・重複引数などはargparseの標準動作を使う。
    """
    parser = comparison.make_parser("SFEN局面で静止探索の追加量を診断する")
    parser.add_argument(
        "--variant",
        required=True,
        choices=_VARIANTS,
        help="baseline（追加なし）、q2（追加2手）、q4（追加4手）",
    )
    parser.add_argument(
        "--remaining-ms", type=int, required=True, help="自分側の残り持ち時間（整数ms）"
    )
    parser.add_argument(
        "--byoyomi-ms", type=int, required=True, help="秒読み期間（整数ms、なしは0）"
    )
    return parser


def _prepare_inputs(
    sfen: str,
    variant: str,
    remaining_ms: int,
    byoyomi_ms: int,
    config: TimeManagementConfig,
) -> tuple[Position, SearchBudget]:
    """SFEN・方式・時計入力を検証し、開始局面と公開計算の予算を返す操作。

    引数は解析対象SFEN、baseline/q2/q4の方式名、先に引数解析された時計ms値、
    ロード済みの不変な時間設定。戻り値は局面とSearchBudget。副作用なし。
    無効値はValueErrorを伝える。予算式を独自実装せず公開計算へ委譲する。
    """
    if not isinstance(variant, str) or variant not in _VARIANTS:
        raise ValueError("方式はbaseline、q2、q4のいずれかで指定してください")
    position = comparison.parse_position(sfen)
    budget = calculate_search_budget(remaining_ms, byoyomi_ms, config)
    return position, budget


def _run_search(
    position: Position,
    variant: str,
    budget: SearchBudget,
    *,
    now_ns: Callable[[], int] = time.monotonic_ns,
) -> DiagnosticResult:
    """選択方式を固定通常深さ4で一度探索し、時間・反復計数を記録する操作。

    引数は検証済み局面・方式・予算、制御にも共有する単調時計。戻り値は一回分の
    終了結果・経過ns・各反復の計数差分・全体計数。副作用は操作セットを一つ生成し、
    既存の制御付き反復深化を一度実行する。
    前提・設計理由: 操作セット構築後に時計原点を読み、予備手の準備から時間へ含める。
    観測コールバックは各反復終了時の計数を差分化し、上限未完了時も実作業を残す。
    """
    if variant not in _VARIANTS:
        raise ValueError("方式はbaseline、q2、q4のいずれかで指定してください")

    counters = SearchCounters()
    if variant == "baseline":
        operations = shogi.make_controlled_operations(
            position.side_to_move, counters=counters
        )
    else:
        additional_depth = 2 if variant == "q2" else 4
        operations = shogi.make_quiescence_operations(
            position.side_to_move, additional_depth, counters=counters
        )

    started_ns = now_ns()
    control = SearchControl(budget, started_ns, now_ns=now_ns)
    iterations: list[IterationDiagnostic] = []
    previous_normal_nodes = 0
    previous_quiescence_calls = 0

    def observe_iteration(
        depth: int,
        result: IterationResult[Move] | SearchInterrupted | QuiescenceLimit,
    ) -> None:
        nonlocal previous_normal_nodes, previous_quiescence_calls
        current_normal_nodes = counters.normal_nodes
        current_quiescence_calls = counters.quiescence_calls
        iterations.append(
            IterationDiagnostic(
                depth,
                result,
                current_normal_nodes - previous_normal_nodes,
                current_quiescence_calls - previous_quiescence_calls,
            )
        )
        previous_normal_nodes = current_normal_nodes
        previous_quiescence_calls = current_quiescence_calls

    result = iterative_deepening.search_controlled(
        position,
        _MAX_DEPTH,
        operations,
        control,
        on_iteration=observe_iteration,
    )
    elapsed_ns = now_ns() - started_ns
    return DiagnosticResult(
        result,
        elapsed_ns,
        tuple(iterations),
        counters.normal_nodes,
        counters.quiescence_calls,
    )


def _format_result(
    sfen: str,
    position: Position,
    variant: str,
    budget: SearchBudget,
    diagnostic: DiagnosticResult,
) -> str:
    """実行条件・結果・反復計数を日本語の行へ整形する操作。

    入力値と診断記録を読むだけで、探索・時計読取・標準出力は行わない。
    完了深さはIterationResultからだけ取り出し、終了状態や手の出所を推測しない。
    """
    completion_labels = {
        ControlledCompletion.COMPLETE: "COMPLETE（深さ4まで完了）",
        ControlledCompletion.NO_LEGAL_MOVE: "NO_LEGAL_MOVE（合法手なし）",
        ControlledCompletion.STOPPED: "STOPPED（時間上限または停止要求）",
        ControlledCompletion.QUIESCENCE_LIMIT: "QUIESCENCE_LIMIT（追加手数上限で未完了）",
        ControlledCompletion.SUPPRESSED: "SUPPRESSED（応答抑制）",
    }
    result = diagnostic.result
    if result.move is None:
        move_origin = "該当なし"
    elif result.last_completed is not None:
        move_origin = "最後に完了した通常深さの探索結果"
    else:
        move_origin = "合法予備手"

    completed_depths = tuple(
        item.depth
        for item in diagnostic.iterations
        if isinstance(item.result, IterationResult)
    )
    depth_text = ", ".join(map(str, completed_depths)) or "なし"
    lines = [
        f"入力SFEN: {sfen}",
        f"評価視点: {'先手' if position.side_to_move is Side.SENTE else '後手'}",
        f"方式: {variant}",
        f"目標期間(ms): {budget.target_ms}",
        f"上限期間(ms): {budget.maximum_ms}",
        f"消費時間(ms): {diagnostic.elapsed_ns / 1_000_000:.3f}",
        f"終了状態: {completion_labels[result.completion]}",
        f"選択手: {comparison.format_move(result.move)}",
        f"手の由来: {move_origin}",
        f"完了した通常深さ: {depth_text}",
    ]
    if result.last_completed is None:
        lines.append("完了記録: なし（評価なし）")
    else:
        record = result.last_completed
        lines.extend(
            (
                "完了記録: あり",
                f"最終完了深さの評価: {comparison.format_score(record.result.score)}",
                f"最終完了深さの通常調査回数: {record.result.visited_nodes}",
                f"反復累計（完了した通常深さまで）: {record.total_visited_nodes}",
            )
        )

    lines.append("各反復の通常調査回数:")
    if not diagnostic.iterations:
        lines.append("  なし")
    for item in diagnostic.iterations:
        if isinstance(item.result, IterationResult):
            state = f"通常深さ{item.result.depth}完了"
        elif isinstance(item.result, QuiescenceLimit):
            state = "静止探索上限で未完了"
        elif item.result.reason is SearchSignal.SUPPRESS:
            state = "応答抑制で未完了"
        else:
            state = "停止で未完了"
        lines.append(f"  反復{item.depth}: {state}・通常調査回数={item.normal_nodes}")

    lines.append("各反復の静止探索呼出し回数:")
    if not diagnostic.iterations:
        lines.append("  なし")
    for item in diagnostic.iterations:
        lines.append(f"  反復{item.depth}: 静止探索呼出し回数={item.quiescence_calls}")
    lines.extend(
        (
            f"全体の通常調査回数: {diagnostic.total_normal_nodes}",
            f"全体の静止探索呼出し回数: {diagnostic.total_quiescence_calls}",
        )
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """一局面を選択方式で診断し、結果を表示して終了コードを返す公開入口。

    argvはテスト引数、Noneはプロセス引数。正常0、引数/SFEN/時計不正2、
    設定読込故障1、Ctrl+C中断130。副作用は設定を一度読み、探索一回と表示一回を行う。
    前提・設計理由: 時計予算は既存の設定読込・公開計算に委譲する。入力準備の
    ValueErrorだけを入力エラーとして扱い、探索内部の故障は原因を保って伝える。
    """
    try:
        parser = _make_parser()
        try:
            arguments = parser.parse_args(argv)
        except SystemExit as error:
            return int(error.code)

        try:
            config = load_time_management_config()
        except (OSError, ValueError) as error:
            print(f"時計設定エラー: {error}", file=sys.stderr)
            return 1

        try:
            position, budget = _prepare_inputs(
                arguments.sfen,
                arguments.variant,
                arguments.remaining_ms,
                arguments.byoyomi_ms,
                config,
            )
        except ValueError as error:
            print(f"入力エラー: {error}", file=sys.stderr)
            return 2

        diagnostic = _run_search(position, arguments.variant, budget)
        print(
            _format_result(
                arguments.sfen, position, arguments.variant, budget, diagnostic
            )
        )
        return 0
    except KeyboardInterrupt:
        print("中断: Ctrl+C。結果表示は未完了です", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
