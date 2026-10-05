"""python3 -m kaname_shogiで実行するCLIの入口。"""

from .cli import (GameMode, choose_game_mode,
                  choose_move_selection_policy, run_game)


def main() -> int:
    """対局形式と必要な一手選択方針を選び、CLI対局を始める。

    引数:
        なし。選択と対局はCLIの標準入出力を使う。

    戻り値:
        正常に対局を終了した場合のプロセス終了コード0。

    副作用:
        対局形式を選び、コンピュータが参加する場合は一手選択方針を尋ねてから
        run_gameを呼び出す。EOFまたはCtrl-Cでは終了メッセージを表示する。

    対局形式と一手選択方針の責務を分け、選んだ方針を対局開始後に切り替えない。
    人間対人間にはコンピュータの選択方針が不要なため尋ねない。
    """
    try:
        mode = choose_game_mode()
        if mode == GameMode.HUMAN_VS_HUMAN:
            run_game(mode=mode)
        else:
            move_selection_policy = choose_move_selection_policy()
            run_game(mode=mode,
                     move_selection_policy=move_selection_policy)
    except (EOFError, KeyboardInterrupt):
        print("入力を終了しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
