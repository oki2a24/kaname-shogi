"""平手の初期配置を表示して終了するCLIの入口。"""

from .display import render_position
from .model import create_initial_position


if __name__ == "__main__":
    print(render_position(create_initial_position()))
