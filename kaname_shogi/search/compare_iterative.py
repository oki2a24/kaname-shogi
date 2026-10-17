"""反復深化と指定深さ探索をSFENから比較する開発用コマンド。"""

import sys

from ..model import Side
from ..move import Move
from . import alpha_beta, iterative_deepening, minimax
from .comparison import (
    best_moves,
    format_move,
    format_score,
    make_parser,
    parse_position,
    results_match,
)
from .result import IterationResult
from .shogi import make_operations

DEFAULT_MAX_DEPTH = 4


def _report_interrupt(
    active: str, latest: IterationResult[Move] | None, compared_depth: int
) -> None:
    print(f"{active}: 未完了（中断）", file=sys.stderr)
    if latest is None:
        print("反復深化：完了結果なし", file=sys.stderr)
    else:
        result = latest.result
        print(
            f"反復深化：深さ{latest.depth}まで完了・評価={format_score(result.score)}・"
            f"選択手={format_move(result.move)}・"
            f"反復累計（完了した深さまで）={latest.total_visited_nodes}",
            file=sys.stderr,
        )
        if latest.depth > compared_depth:
            print(f"深さ{latest.depth}の比較：未完了", file=sys.stderr)
    print(f"比較完了深さ：{compared_depth}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """SFENを深さ1〜4で比較し、表示と終了コードを返す操作。

    argv=Noneは実行時引数。入力誤りだけを捕捉して2、比較不一致は1、
    成功は0、Ctrl+Cは130（不一致より優先）。内部故障は原因を保って伝える。
    出力は標準出力、診断は標準エラー。局面を変更せず時間制御を行わない。
    反復の完了結果を先に保持してから全幅・単独αβの順に比較する。
    累計は完了反復だけで、中断分と確認用探索を含めない。
    """
    parser = make_parser("SFEN局面の反復深化を全幅・単独αβと深さ1〜4で比較する")
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)
    try:
        position = parse_position(args.sfen)
    except ValueError as error:
        print(f"入力エラー: {error}", file=sys.stderr)
        return 2
    operations = make_operations(position.side_to_move)
    side = "先手" if position.side_to_move == Side.SENTE else "後手"
    print(f"入力SFEN: {args.sfen}\n評価視点: 開始側（{side}）", flush=True)
    print(
        "深さ\t反復評価\t反復選択手\t比較\t単独αβ訪問\t反復今回訪問\t"
        "反復累計（完了した深さまで）",
        flush=True,
    )
    latest = None
    compared_depth = 0
    active = "深さ1・反復深化"
    mismatch = False
    try:
        for completed in iterative_deepening.search(
            position, DEFAULT_MAX_DEPTH, operations
        ):
            latest = completed
            depth, result = completed.depth, completed.result
            active = f"深さ{depth}・全幅"
            full = minimax.search(position, depth, operations)
            active = f"深さ{depth}・単独αβ"
            standalone = alpha_beta.search(position, depth, operations)
            active = f"深さ{depth}・比較表示"
            matched = results_match(full, result)
            label = "比較成功" if matched else "比較不一致"
            member = (
                result.move in best_moves(full)
                if result.move is not None
                else full.move is None
            )
            print(
                f"{depth}\t{format_score(result.score)}\t{format_move(result.move)}\t"
                f"{label}（評価一致={full.score == result.score}・最善候補所属={member}）\t"
                f"{standalone.visited_nodes}\t{result.visited_nodes}\t{completed.total_visited_nodes}",
                flush=True,
            )
            if not matched:
                mismatch = True
                print(
                    f"深さ{depth}: 比較不一致。評価値と最善候補を確認してください",
                    file=sys.stderr,
                )
            compared_depth = depth
            if result.move is None:
                print("手なしで終了（深さ1のみ比較）", flush=True)
                break
            active = f"深さ{depth + 1}・反復深化"
    except KeyboardInterrupt:
        _report_interrupt(active, latest, compared_depth)
        return 130
    if not mismatch and latest is not None and latest.result.move is not None:
        print("全深さで比較成功", flush=True)
    return 1 if mismatch else 0


if __name__ == "__main__":
    raise SystemExit(main())
