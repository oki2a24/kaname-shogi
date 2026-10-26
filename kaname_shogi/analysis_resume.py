"""分析CLIの再開チェックポイント用パスを扱う。"""

from __future__ import annotations

from pathlib import Path


def checkpoint_path_for_output(output: Path) -> Path:
    """分析JSONの隣に置くチェックポイントdirectoryのPathを返す。

    引数:
        output: 完成分析JSONの保存先。

    戻り値:
        保存先のbasenameへ `.checkpoint` を足した隣接directoryのPath。

    副作用:
        なし。ファイルやdirectoryは作成しない。

    前提条件:
        outputはファイル名を持つ分析JSONの保存先である。
    """
    output = Path(output)
    return output.with_name(f"{output.name}.checkpoint")
