# 探索停止と途中結果

2026-10-12、探索部品として実装。USI接続もmain取り込み・取り込み先検証済み。仕様は[承認済み計画](../plans/2026-10-12-search-stop-implementation-plan.md)、判断と検証は[実装記録](../learning/search-stop-implementation-plan.md)を参照する。

## 制御と結果

`SearchControl` は一探索の制御データ。計算済みの `SearchBudget`（期間データ）とgoを読んだ時点の整数nsを受け、整数演算で目標・上限期限を作る。時計なしのNoneと明示0は区別する。`request_stop` は要求を記録する操作、`check` は継続・通常停止・抑制付き停止を返す操作。

目標は根の生成と新候補開始を止め、評価中の候補は続ける。上限・通常stopは次の確認点で中断する。根の合法手がまだない間だけ、通常停止を最初の合法手確保または全調査の手なし確定まで保留する。抑制付き停止は保護しない。単一の複製・利き計算・静的採点を強制切断しないため、期限内応答の保証ではない。

`search_move` は根の生成から最終選択まで行う操作。元局面を変更せず、乱数器は抽選時だけ進める。`SearchResult` は結果データで、状態は次の通り。

| 状態 | 手の意味 |
| --- | --- |
| COMPLETE | 必要な全調査完了。Noneだけが合法手なし |
| INTERRUPTED | 合法な予備手、または完了候補の最高同点から一回抽選した手 |
| SUPPRESSED | None。応答を抑制する意味で、投了へ変換しない |

一候補は適用・必要な詰み確認・全応手評価・復帰後の停止確認まで終えて完了とする。未完了の点は使わない。完了候補0なら生成順の最初の合法手を抽選せず返す。Randomは全生成完了なら全手から一回抽選し、中断なら予備手を返す。

合法生成・手あり・詰み確認は完了状態と値を分ける。中断の空一覧を合法手なし、詰みの不明をFalseへ変換しない。手ありは一手確定でTrueとなり、以後を調べない。従来APIは停止なしで同じ規則・評価処理を利用し、固定順・戻り値・例外を保つ。

## 後続接続

USIは各goの独立局面・新制御から`search_move`を呼ぶ。go完成行の読取り原点、stopと抑制、一回送信、故障通知、入力待機解除・担当回収を[接続仕様](usi-engine-response.md#入力送信故障回収2026-10-12接続)へまとめた。2026-10-19にCLIとUSIへ全幅四手・αβ四手を選択肢として接続した。新方式は共通反復探索を深さ1→4で使う。USIの接続境界・設定寿命・検証範囲は[承認済み設計](../plans/2026-10-19-four-ply-search-game-integration-design.md)と[実施記録](../learning/four-ply-search-game-integration-plan.md)を参照する。[引渡し契約](../plans/2026-10-12-search-stop-implementation-plan.md#後続の入力並行処理usi接続への引き渡し)は当時の記録として保持する。

2026-10-20に通常対局CLIも同じ`game_search.search_move`・公開予算計算・`SearchControl`を使うよう接続した。CLIは時計・返却後の時間切れ判定・表示・保存を担い、USIエンジン経路や共通探索・予算式を変更しない。CLIの計時原点はコンピュータ手番の思考開始表示後で、返却直後に終点を読む。コンピュータ手前の独自詰み確認・全合法手生成、完了深さや手の由来表示を行わない。時間切れ後の返却手は適用せず、通常停止結果は時計内なら扱い、抑制は勝敗へ変換しない。人間手番の詰み確認は維持する。詳細は[通常対局CLI時計メモ](32-human-vs-computer-cli.md)、[承認済み設計](../plans/2026-10-20-cli-search-time-control-design.md)、[実装・検証記録](../learning/cli-search-time-control-plan.md)を参照する。

専用制御Lockは送信同期を代替しない。接続側の共通Lockで結果返却直後の抑制を再確認する。実時間安全性、全OS・全競合、計測・対局は未検証。

## 制御付き反復深化の探索部品（2026-10-18）

`search.iterative_deepening.search_controlled(node, max_depth, operations, control)` は最終終了結果を一件返す同期操作。`shogi.make_controlled_operations(perspective)` は開始側視点の将棋用操作セットを作る操作。呼出し元のSearchControlを準備・各深さ・子へ共通で渡し、予算計算や原点設定をやり直さない。2026-10-19から、対局用 `game_search` が全幅四手・αβ四手をこの共通入口へ接続する。比較コマンドは独立した比較手順のままで、対局選択・時計引数を受け付けない。

準備は生成順の最初の合法手だけを確保する。通常停止の保護は、この手の合法性確認（打ち歩詰めの防御調査を含む）または全調査の手なし確定までで、抑制は保護しない。準備の手なしは反復完了記録を作らない。目標は新しい深さを始める前だけ、上限・通常停止・抑制は深さ内部でも確認する。

| データ | 意味 |
| --- | --- |
| `SearchInterrupted(reason)` | 探索中断。STOP/SUPPRESSだけを理由とし、評価・手・訪問数は持たない |
| `PreparedRoot(move)` | 初回準備の完了。Noneは手なし確定 |
| `AdvancedNode(node)` | 正常適用した独立局面 |
| `ControlledSearchOperations` | 準備・調査・遷移・評価の操作を束ねるデータ |
| `ControlledSearchResult(completion, move, last_completed)` | 反復の最終終了結果。最後の完了記録と応答候補を区別 |

指定深さの `alpha_beta.search_controlled` は完了したSearchResultまたはSearchInterruptedのユニオンを返す。中断は専用例外を使わず各段で判別して伝播する。故障は例外のまま伝える。再帰の評価・枝刈り・計数は停止なし入口と共有する。

| 終了状態 | 手と記録 |
| --- | --- |
| COMPLETE | 要求上限まで完了し、その記録と手を持つ |
| NO_LEGAL_MOVE | 準備で手なし確定。手・記録ともなし |
| STOPPED | 最新完了記録の手、記録がなければ予備手。目標による反復終了も含む |
| SUPPRESSED | 手はなし。既存の完了記録は保持できる |

最後の評価後と根の最終停止確認を通過してから一深さの完了を確定する。未完了の手・評価・訪問数は保持記録へ入れない。確定後の通常停止で記録を取り消さず、返却直前の抑制は手を除く。累計は完了反復の訪問数の和。準備・中断反復・比較探索は含めない。将来の送信側には送信前抑制確認が別途必要である。

movegenの `legal_moves_controlled`（全調査）、`first_legal_move_controlled`（最初の取得）、`position_after_move_controlled`（独立局面への適用）は既存本体へ委譲する公開操作。目標適用と初手保護を分け、旧root指定の停止意味は維持する。将棋側はcompleted付き結果を維持し、接続部で探索用の別型へ変換する。MoveApplicationResultは完了ならPosition、中断ならNoneだけを許す。

新しい終了データは不変で、状態と手・記録の不整合を構築時に拒否する。手の合法性と上限一致は探索側の契約。単一処理の強制切断・時間内応答保証は行わない。[承認済み設計](../plans/2026-10-18-iterative-deepening-stop-time-control-design.md)、[実装計画・結果](../plans/2026-10-18-iterative-deepening-stop-time-control-implementation-plan.md)、[検証・レビュー記録](../learning/iterative-deepening-stop-time-control-implementation.md)を参照。
