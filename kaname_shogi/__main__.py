"""python3 -m kaname_shogiで実行するCLIの入口。

平手の局面を生成し、人向けの表示文字列を標準出力へ一度出して終了する。
対話入力や指し手はまだ扱わない。生成・表示の規則は各モジュールへ委ね、
ここには起動時の接続だけを置く。インポートしただけでは出力しない。
"""

from .display import render_position
from .model import create_initial_position


if __name__ == "__main__":
    print(render_position(create_initial_position()))
