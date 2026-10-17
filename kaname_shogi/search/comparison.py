"""開発用探索比較の入力・表示・一致判定を共用する。"""

import argparse

from ..model import BasicPieceType, Position, Square
from ..move import BoardMove, Move
from ..sfen import parse_sfen
from ..usi_move import format_usi_move
from .result import Score, SearchResult


def make_parser(description: str) -> argparse.ArgumentParser:
    """説明文からSFEN必須の比較コマンド用パーサーを返す操作。

    入力の説明文を保持し、--sfenだけを登録する。解析や探索はまだ行わない。
    各コマンド側が終了コードとエラーの境界を管理するための共通設定。
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--sfen", required=True, help="盤面・手番・持ち駒・手数のSFEN文字列"
    )
    return parser


def parse_position(sfen: str) -> Position:
    """SFEN文字列から探索開始局面を作る操作。

    既存変換へ委譲し、不正入力のValueErrorをそのまま伝える。
    探索や出力は行わず、呼出し側が入力エラーの捕捉範囲を限定できる。
    """
    return parse_sfen(sfen).position


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


def best_moves(full: SearchResult[Move]) -> tuple[Move, ...]:
    """全幅の確定根評価から最善候補を順番どおり取り出す操作。

    最大側の全候補の確定値を持つ結果が前提。入力を変更せず再探索しない。
    """
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
    best = best_moves(full)
    return full.move in best and pruned.move in best


def format_score(score: Score) -> str:
    """勝敗・駒得の評価データを日本語表示へ変換する操作。

    勝敗区分を駒得より優先し、入力を変更せず文字列を返す。
    """
    outcome, material = score
    if outcome:
        return "勝ち" if outcome > 0 else "負け"
    return f"＋{material}" if material >= 0 else f"−{-material}"
