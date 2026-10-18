"""時間制御付き反復探索を一回実行する開発用コマンド。"""

import argparse
import time

from ..model import Position, Side
from ..move import Move
from ..search_control import SearchControl
from ..time_management import SearchBudget
from . import comparison, iterative_deepening, shogi
from .result import ControlledCompletion, ControlledSearchResult, IterationResult


def _make_parser() -> argparse.ArgumentParser:
    """SFEN・深さ・直接指定予算を受ける解析器を返す操作。

    四引数を必須にし、深さと期間を整数として解析する。重複引数と一意な
    省略形はargparse標準に委ね、独自の数値表記規則を追加しない。
    """
    parser = comparison.make_parser("SFEN局面を時間制御付き反復探索する")
    parser.add_argument(
        "--max-depth", type=int, required=True, help="探索する最大深さ（1以上）"
    )
    parser.add_argument(
        "--target-ms", type=int, required=True, help="探索目標期間（整数ms）"
    )
    parser.add_argument(
        "--maximum-ms", type=int, required=True, help="探索上限期間（整数ms）"
    )
    return parser


def _prepare_inputs(
    sfen: str, max_depth: int, target_ms: int, maximum_ms: int
) -> tuple[Position, SearchBudget]:
    """SFEN・深さ・直接指定予算を検査して探索入力を返す操作。

    引数はSFEN文字列・1以上の整数深さ・整数msの目標/上限期間。
    戻り値は開始局面と入力期間をそのまま保持するSearchBudget。
    副作用はなく、無効値のValueErrorを伝える。設定読込や予算計算は行わない。
    """
    if type(max_depth) is not int or max_depth < 1:
        raise ValueError("最大深さは1以上の整数で指定してください")
    position = comparison.parse_position(sfen)
    budget = SearchBudget(target_ms, maximum_ms)
    return position, budget


def _run_search(
    position: Position, max_depth: int, budget: SearchBudget
) -> ControlledSearchResult[Move]:
    """開始側の制御操作と同じ原点・時計を使い、一回探索する操作。

    引数は検査済み開始局面、1以上の最大深さ、直接指定された予算。
    戻り値は既存の制御付き反復探索が返す一件の終了結果。
    副作用として操作セットを作り、時計を一度読み、探索を同期的に一回呼ぶ。
    前提・設計理由: 入力検査後に操作セット生成を終え、探索内部の合法予備手準備は
    制限時間に含めるため、原点を探索直前に取得して同じ時計をSearchControlへ渡す。
    """
    operations = shogi.make_controlled_operations(position.side_to_move)
    clock = time.monotonic_ns
    started_ns = clock()
    control = SearchControl(budget, started_ns, now_ns=clock)
    return iterative_deepening.search_controlled(
        position, max_depth, operations, control
    )


def _format_result(
    sfen: str,
    position: Position,
    max_depth: int,
    budget: SearchBudget,
    result: ControlledSearchResult[Move],
) -> str:
    """実行条件・終了状態・完了記録を順序付きの日本語行へ整形する操作。

    引数は表示用SFEN、開始側局面、指定深さ、直接指定予算、制御付き結果。
    戻り値はstdoutへ出す一件分の改行区切り表示。
    副作用はなく、手と評価の表記には既存comparison整形を使う。
    前提・設計理由: 結果型の状態/手/記録の契約を保ち、記録なしの値を作らず、
    保持記録から終了理由やSUPPRESSEDの選択手を推測しない。
    """
    completion_labels = {
        ControlledCompletion.COMPLETE: "COMPLETE（指定上限深さまで完了）",
        ControlledCompletion.NO_LEGAL_MOVE: "NO_LEGAL_MOVE（合法手なし）",
        ControlledCompletion.STOPPED: "STOPPED（通常停止）",
        ControlledCompletion.SUPPRESSED: "SUPPRESSED（応答抑制）",
    }
    if result.completion in (
        ControlledCompletion.COMPLETE,
        ControlledCompletion.STOPPED,
    ):
        move_origin = "完了結果" if result.last_completed is not None else "合法予備手"
    else:
        move_origin = "該当なし"

    lines = [
        f"入力SFEN: {sfen}",
        f"評価視点: {'先手' if position.side_to_move is Side.SENTE else '後手'}",
        f"指定上限深さ: {max_depth}",
        f"目標期間(ms): {budget.target_ms}",
        f"上限期間(ms): {budget.maximum_ms}",
        f"終了状態: {completion_labels[result.completion]}",
        f"選択手: {comparison.format_move(result.move)}",
        f"手の由来: {move_origin}",
    ]

    record: IterationResult[Move] | None = result.last_completed
    if record is None:
        lines.append("完了記録: なし（評価なし）")
    else:
        lines.extend(
            (
                "完了記録: あり",
                f"完了深さ: {record.depth}",
                f"完了深さの評価: {comparison.format_score(record.result.score)}",
                f"完了深さの訪問回数: {record.result.visited_nodes}",
                f"反復累計（完了した深さまで）: {record.total_visited_nodes}",
            )
        )
    return "\n".join(lines)
