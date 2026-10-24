"""比較用乱数種一覧を作成する専用コマンドライン入口。"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from .comparison_artifact_io import write_new_json
from .comparison_io import positions_from_bytes
from .comparison_seeds import generate_seed_plan, seed_plan_payload


class _ValueErrorArgumentParser(argparse.ArgumentParser):
    """parse_argsの入力エラーをCLI内で扱えるValueErrorに変換する。"""

    def error(self, message: str) -> None:
        raise ValueError(message)


def main(argv: Sequence[str] | None = None) -> int:
    """検証済み局面から種を抽出し、未使用パスへ乱数種JSONを新規保存する。

    引数:
        argv: CLI引数列。Noneならプロセスのコマンドラインを使う。

    戻り値:
        正常保存は0、入力不正は2、生成・保存故障は1、KeyboardInterruptは130。

    例外:
        予期しない例外は実行故障1として診断する。KeyboardInterruptは通常中断130。

    副作用:
        局面JSONを読み、検証済み全局面分の種をOS乱数源から抽出し、指定した新規パスへ
        JSONを保存する。標準出力・標準エラーへ日本語の結果を表示する。

    前提条件:
        出力JSONは全局面・引数を検証して乱数抽出を終えた後だけ保存する。既存パスは
        上書きせず、baseline/candidateの各種は二局一組の先後交換で再利用する。
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if any(argument in {"-h", "--help"} for argument in arguments):
        parser = _make_parser(add_help=True)
        parser.prog = "python -m kaname_shogi.prepare_comparison_seeds"
        parser.description = "比較実験の乱数種一覧を新規作成します。"
        parser.print_help()
        return 0

    try:
        args = _make_parser().parse_args(arguments)
        pairs_per_position = _parse_positive_int(args.pairs_per_position)
        positions_path = Path(args.positions)
        positions_raw = positions_path.read_bytes()
        positions = positions_from_bytes(positions_raw)
        output_path = Path(args.output)
        if os.path.lexists(output_path):
            raise ValueError("出力先は存在しないパスを指定してください")
        if not output_path.parent.exists() or not output_path.parent.is_dir():
            raise ValueError("出力先の親ディレクトリは事前に作成してください")
    except KeyboardInterrupt:
        print("入力検証を中断しました。", file=sys.stderr)
        return 130
    except (OSError, ValueError) as error:
        print(f"入力エラー: {error}", file=sys.stderr)
        return 2

    try:
        plan = generate_seed_plan(
            tuple(position.position_id for position in positions),
            hashlib.sha256(positions_raw).hexdigest(),
            pairs_per_position,
            args.purpose,
        )
        write_new_json(output_path, seed_plan_payload(plan))
    except KeyboardInterrupt:
        print("乱数種一覧の作成を中断しました。", file=sys.stderr)
        return 130
    except Exception as error:
        print(
            f"乱数種一覧を保存できません: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        f"乱数種一覧を作成しました: {output_path} "
        f"({len(positions)}局面 × {pairs_per_position}組)"
    )
    return 0


def _make_parser(*, add_help: bool = False) -> _ValueErrorArgumentParser:
    """準備CLIが受け付ける必須引数を宣言したparserを返す。"""
    parser = _ValueErrorArgumentParser(add_help=add_help)
    parser.add_argument("--positions", required=True)
    parser.add_argument("--pairs-per-position", required=True)
    parser.add_argument("--purpose", choices=("pilot", "confirmation"), required=True)
    parser.add_argument("--output", required=True)
    return parser


def _parse_positive_int(value: str) -> int:
    """ASCII十進数字だけを整数化し、組数1以上を検証する。"""
    if re.fullmatch(r"[0-9]+", value) is None:
        raise ValueError("局面ごとの組数は整数で指定してください")
    parsed = int(value)
    if parsed < 1:
        raise ValueError("局面ごとの組数は1以上で指定してください")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
