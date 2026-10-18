"""時間制御付き反復探索を一回実行する開発用コマンド。"""

import argparse

from ..model import Position
from ..time_management import SearchBudget
from . import comparison


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
