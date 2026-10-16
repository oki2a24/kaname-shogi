"""SFENから指定深さ探索を比較する開発用コマンド。"""

import argparse
import sys

from ..model import BasicPieceType, Side, Square
from ..move import BoardMove, Move
from ..sfen import parse_sfen
from ..usi_move import format_usi_move
from . import alpha_beta, minimax
from .result import Score, SearchResult
from .shogi import make_operations

_DROP_NAMES = {
    BasicPieceType.PAWN: "歩",
    BasicPieceType.LANCE: "香",
    BasicPieceType.KNIGHT: "桂",
    BasicPieceType.SILVER: "銀",
    BasicPieceType.GOLD: "金",
    BasicPieceType.BISHOP: "角",
    BasicPieceType.ROOK: "飛",
}


def _square(square: Square) -> str:
    return f"{square.file}{'一二三四五六七八九'[square.rank - 1]}"


def format_move(move: Move | None) -> str:
    """一手をUSIと日本語の移動説明で返し、手なしは「なし」とする操作。

    局面非依存のMoveを受け取り、変更しない。既存USI変換に従い不正値は
    ValueError。成りと駒打ちを区別し、開発結果を筋・段で読めるようにする。
    """
    if move is None:
        return "なし"
    usi = format_usi_move(move)
    if isinstance(move, BoardMove):
        description = f"{_square(move.source)}→{_square(move.destination)}"
        if move.promote:
            description += "・成り"
    else:
        description = (
            f"{_square(move.destination)}に{_DROP_NAMES[move.piece_type]}を打つ"
        )
    return f"{usi}（{description}）"


def _best_moves(full: SearchResult[Move]) -> tuple[Move, ...]:
    return tuple(
        move for move, score in (full.root_scores or ()) if score == full.score
    )


def results_match(full: SearchResult[Move], pruned: SearchResult[Move]) -> bool:
    """完了した全幅とαβの評価・最善候補への所属が一致するか返す操作。

    fullは全根候補の確定値を持ち、開始側の最大値を求めた結果を前提とする。
    同点の別手は許容し、手なしは両方なし・同評価・根候補なしで成功とする。
    入力を変更せず、再探索を行わない。訪問回数は合否条件に含めない。
    """
    if full.score != pruned.score:
        return False
    if full.move is None or pruned.move is None:
        return full.move is None and pruned.move is None and full.root_scores == ()
    if not full.root_scores or full.score != max(
        score for _, score in full.root_scores
    ):
        return False
    best = _best_moves(full)
    return full.move in best and pruned.move in best


def _format_score(score: Score) -> str:
    outcome, material = score
    if outcome:
        return "勝ち" if outcome > 0 else "負け"
    return f"＋{material}" if material >= 0 else f"−{-material}"


def main(argv: list[str] | None = None) -> int:
    """SFENを二・三・四手で比較し、結果表示と終了コードを返す操作。

    argv=Noneなら実行時引数を使う。結果は標準出力、診断は標準エラーへ出す。
    成功0、不一致1、入力不正2、中断130。局面を変更せず、時間制御は行わない。
    入力変換だけのValueErrorを捕捉し、探索内部の例外は原因を保って伝播する。
    """
    parser = argparse.ArgumentParser(
        description="SFEN局面を二・三・四手の全幅／αβ探索で比較する"
    )
    parser.add_argument(
        "--sfen", required=True, help="盤面・手番・持ち駒・手数のSFEN文字列"
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)
    try:
        position = parse_sfen(args.sfen).position
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
                    f"{depth}\t{name}\t{_format_score(result.score)}\t{format_move(result.move)}\t{result.visited_nodes}",
                    flush=True,
                )
            full, pruned = results
            matched = results_match(full, pruned)
            label = "比較成功" if matched else "比較不一致"
            member = (
                pruned.move in _best_moves(full)
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
