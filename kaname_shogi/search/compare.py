"""SFENから指定深さ探索を比較する開発用コマンド。"""

import sys

from ..model import Side
from . import alpha_beta, minimax
from .comparison import best_moves, format_score, make_parser, parse_position
from .comparison import format_move as format_move
from .comparison import results_match as results_match
from .shogi import make_operations


def main(argv: list[str] | None = None) -> int:
    """SFENを二・三・四手で比較し、結果表示と終了コードを返す操作。

    argv=Noneなら実行時引数を使う。結果は標準出力、診断は標準エラーへ出す。
    成功0、不一致1、入力不正2、中断130。局面を変更せず、時間制御は行わない。
    入力変換だけのValueErrorを捕捉し、探索内部の例外は原因を保って伝播する。
    """
    parser = make_parser("SFEN局面を二・三・四手の全幅／αβ探索で比較する")
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
    print("深さ\t方式\t評価\t選択手\t訪問回数", flush=True)
    mismatch = False
    active = "開始前"
    try:
        for depth in (2, 3, 4):
            results = []
            for name, search in (("全幅", minimax.search), ("αβ", alpha_beta.search)):
                active = f"深さ{depth}・{name}"
                result = search(position, depth, operations)
                results.append(result)
                print(
                    f"{depth}\t{name}\t{format_score(result.score)}\t{format_move(result.move)}\t{result.visited_nodes}",
                    flush=True,
                )
            full, pruned = results
            matched = results_match(full, pruned)
            label = "比較成功" if matched else "比較不一致"
            member = (
                pruned.move in best_moves(full)
                if pruned.move is not None
                else full.move is None
            )
            print(
                f"深さ{depth}: {label}（評価一致={full.score == pruned.score}・最善候補所属={member}）",
                flush=True,
            )
            if not matched:
                mismatch = True
                print(
                    f"深さ{depth}: 比較不一致。評価値と最善候補を確認してください",
                    file=sys.stderr,
                )
    except KeyboardInterrupt:
        print(
            f"{active}: 未完了（中断）。完了済みの行だけを表示しています",
            file=sys.stderr,
        )
        return 130
    if not mismatch:
        print("全深さで比較成功", flush=True)
    return 1 if mismatch else 0


if __name__ == "__main__":
    raise SystemExit(main())
