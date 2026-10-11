# USI新方式の局中固定・次局継承

## 目的・承認範囲と開始状態

2026-10-11、本人の再開指示を受け、[引き継ぎ](../handover-usi-policy-lifetime.md)と現物を照合し、[承認済み計画タスク4](../plans/2026-10-10-two-ply-implementation-plan.md#タスク4usi設定と実応答)の `test_keeps_two_ply_policy_for_current_game` 1項目だけを実施した。計画訂正なし。

場所 `/Users/oki2a24/kaname-shogi`、ブランチ `codex/usi-policy-lifetime-handoff`、開始HEAD `e69bf25`、差分なし。Ruff 0.16.10と固定版、ローカルフック `.githooks` の一致を確認。基準全体359件成功。新規worktree・push・main統合なし。

## 要点・契約・実際の変更

`MoveSelectionPolicy` は選択方針を表すデータ、`run_usi_engine` はコマンドを処理する操作、`choose_move` は手を選ぶ操作。`configured_policy` は最新の設定データ、`game_policy` は現在局で固定した方針データである。

指定テスト1メソッドを `tests/test_usi_engine.py` に追加。新値設定→position→go→Material設定→go→usinewgame→position→goの実コマンドを処理し、選択境界への呼び出しが3回で、独立期待値 `[TWO_PLY_MATERIAL, TWO_PLY_MATERIAL, MATERIAL]` になることを確認した。各goをsubTestで区別する。局中の二回目はpositionを再送せず、計画どおり現在局の固定を確認する。

既存spyを使用し、選択境界だけを置換した。設定受付・局面再現・合法手列挙・局の状態処理は実際に動かす。実選択による手の正しさは今回の契約に含まない。

## 振る舞いごとのTDD・検出力

単独実行コマンドは `PYTHONPATH=tests python3 -m unittest test_usi_engine.UsiEngineFunctionTests.test_keeps_two_ply_policy_for_current_game -v`。

初回有効実行は1件Green。最初のgoで固定し、usinewgameで固定だけを解除する既存処理が新方針にも適用されていた。未実装Red→製品修正の実績とは扱わない。製品変更は不要であり、隔離コピーへの誤り注入で検出力を確認した。

| 注入した誤り | 対象アサーションのFAIL | 復元 |
| --- | --- | --- |
| 全goで最新設定を使い局中変更を即時反映 | go 2の方針 | 単独1件成功・ソース一致 |
| usinewgameで固定を解除しない | go 3の方針 | 単独1件成功・ソース一致 |
| usinewgameで設定までRANDOMへ消去 | go 3の方針 | 単独1件成功・ソース一致 |
| TWO_PLY_MATERIALだけ毎回固定し直す | go 2の方針 | 単独1件成功・ソース一致 |
| 設定変更後の選択境界へRANDOMを渡す | go 2の方針 | 単独1件成功・ソース一致 |
| 設定変更後の選択呼び出しを省略 | 呼び出し数2≠3 | 単独1件成功・ソース一致 |

全6変異は読み込みERRORなしのアサーションFAIL。局中固定はgo 2、次局継承はgo 3、選択呼び出し欠落は回数で区別した。元作業ツリーの製品ソースには注入していない。一時スクリプト `/tmp/check_usi_lifetime_mutations.py` とログ `/tmp/usi-lifetime-mutation-1.log`〜`6.log` は恒久保存を保証しないため、結果を本記録へ保存した。

Refactor要否を確認し、既存の設定値と局内固定値の分離を維持する小さいテスト追加なので不要と判断した。import変更なし。

## 回帰検証・範囲と限界

- `python3 -m unittest discover -s tests -p 'test_usi_engine*.py' -v`：29件成功。
- `python3 -m unittest discover -s tests -v`：360件成功。
- `.venv/bin/ruff format .`：28ファイル変更なし。`.venv/bin/ruff check .`、`git diff --check` 成功。

代表ケースは新方針→局中Material→次局の1系列。順序と局境界が対象条件で、先後・駒価値の組合せは選択設定の寿命と独立なので追加しない。期待値を製品の辞書や状態から生成していない。

単独テストは上表の6誤りを検出する。旧方式の固定・次局継承、通知、新値の大小混在受付、未指定RANDOMは既存テストが補完する。新値後の未知値保持、実選択・局面保存・手なしresign・実プロセスbestmove、性能・棋力・ShogiHomeは今回未検証・対象外。全体回帰に既存の実プロセステストが含まれることを、新方式の実応答を確認した証拠とは扱わない。

## 独立レビュー・記録・統合状態

独立コードレビューはCritical 0・Important 0・Minor 0、修正要求なし。レビュアー自身が `test_usi_engine.py` 27件と隔離6変異・各復元・ソース一致を再確認した。ランチャーを含む29件と全体360件は実行者の結果であり、レビュアーの再実行とは記録しない。独立文書レビューもCritical 0・Important 0・Minor 0、修正要求なし。実行者とレビュアーが変更7文書の相対リンク・見出し446件問題0と差分検査成功を確認した。文書レビュアーは全体回帰・Ruffを再実行していない。未解消指摘・辞退したMinorなし。結果追記後に最終検査し、通常フック付きコミットへ保存する。タスク4全体は未完了。main取り込みは別途本人承認が必要で、取り込み先検証と最後の理解確認は未実施。

## 確認問題・回答・振り返り・次回への問い

最後の理解確認は取り込み先検証後に一問だけ出す。現時点では未出題・未回答。

振り返り：新方針固有の製品分岐を増やさず、既存の設定と局内固定の分離が働くことを確認できた。初回Greenを機能追加のRedと混同せず、誤り注入と復元でテストの検出力を確認した。

次回への問い：今回の1項目をmainへ取り込むか。承認後は取り込み先で検証し、理解確認を再開する。本人が次テーマを選ぶまで後続へ進まない。


## main取り込みと取り込み先検証（2026-10-11）

実装保存 `d3a7f32` 後、本人はmain取り込みの問いへ「ok」と回答した。元ディレクトリ `/Users/oki2a24/kaname-shogi` で `git switch main`、`git merge --ff-only codex/usi-policy-lifetime-handoff` を実行し、mainを `f5f8f82` → `d3a7f32` へfast-forwardした。準備 `e69bf25` も含む。push・新規worktreeなし。

取り込み先main上で `python3 -m unittest discover -s tests -v` を改めて実行し360件成功。Ruff整形確認28ファイル・lint・差分検査成功。作業ブランチでの成功を流用していない。取り込み直後はmainがorigin/mainより6コミット先、差分なしを確認した。

現在地・案内・知識を統合済みへ更新する。前節の未統合表記は実装保存前の経緯として保持する。最後の理解確認は未出題・未回答。統合記録を確認・保存後に一問だけ出し、回答を待つ。タスク4後続へ進まない。

統合記録7文書の独立レビューはCritical 0・Important 0・Minor 0。レビュアーもmain・HEAD・相対リンクと見出し446件問題0・差分成功を確認した。全体テスト・Ruffは実行者の取り込み先結果を参照し、文書レビューでは再実行していない。結果追記後にリンク・差分・Ruffを最終確認し、通常コミットへ保存する。
