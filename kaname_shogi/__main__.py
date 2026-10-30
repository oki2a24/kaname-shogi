"""python3 -m kaname_shogiで実行するCLIの入口。"""

import sys

from .cli import (
    GameMode,
    _format_move_selection_policy_name,
    choose_clock_settings,
    choose_game_mode,
    choose_move_selection_policy,
    run_game,
)
from .model import Side
from .time_management import load_time_management_config


def main() -> int:
    """対局形式と必要な一手選択方針を選び、CLI対局を始める。

    引数:
        なし。選択と対局はCLIの標準入出力を使う。

    戻り値:
        正常に対局を終了した場合のプロセス終了コード0。

    副作用:
        対局形式を選び、コンピュータが参加する場合は方針・時計を選び、時間予算設定を
        一度読み込んでrun_gameへ渡す。設定読込のValueError/OSErrorはstderrへ診断して
        終了コード1を返す。EOFまたはCtrl-Cでは終了メッセージを表示する。

    対局形式と一手選択方針の責務を分け、選んだ方針を対局開始後に切り替えない。
    人間対人間にはコンピュータ設定とJSON読込が不要なため行わない。設定読込の失敗を
    実行時の探索・時計故障と混同しないよう、読込操作だけを狭い例外境界で扱う。
    """
    try:
        mode = choose_game_mode()
        if mode == GameMode.HUMAN_VS_HUMAN:
            run_game(mode=mode)
        else:
            if mode == GameMode.HUMAN_VS_COMPUTER:
                move_selection_policies = {
                    Side.GOTE: choose_move_selection_policy(side=Side.GOTE)
                }
            else:
                move_selection_policies = {
                    Side.SENTE: choose_move_selection_policy(side=Side.SENTE),
                    Side.GOTE: choose_move_selection_policy(side=Side.GOTE),
                }
            clock_settings = choose_clock_settings()
            try:
                time_config = load_time_management_config()
            except (ValueError, OSError) as error:
                print("時間設定を読み込めませんでした: " + str(error), file=sys.stderr)
                return 1
            if mode == GameMode.HUMAN_VS_COMPUTER:
                print(
                    "選択方針：先手=人間、後手="
                    + _format_move_selection_policy_name(
                        move_selection_policies[Side.GOTE]
                    )
                )
            else:
                print(
                    "選択方針：先手="
                    + _format_move_selection_policy_name(
                        move_selection_policies[Side.SENTE]
                    )
                    + "、後手="
                    + _format_move_selection_policy_name(
                        move_selection_policies[Side.GOTE]
                    )
                )
            run_game(
                mode=mode,
                move_selection_policies=move_selection_policies,
                clock_settings=clock_settings,
                time_config=time_config,
            )
    except EOFError, KeyboardInterrupt:
        print("入力を終了しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
