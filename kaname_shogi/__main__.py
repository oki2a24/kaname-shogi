"""python3 -m kaname_shogiで実行するCLIの入口。"""

from .cli import choose_game_mode, run_game


if __name__ == "__main__":
    try:
        run_game(mode=choose_game_mode())
    except (EOFError, KeyboardInterrupt):
        print("入力を終了しました。")
