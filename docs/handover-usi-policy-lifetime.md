# 次テーマへの引き継ぎ：USI新方式の局中固定・次局継承だけ

## 最終目標と選定理由

2026-10-11、本人はロードマップ説明後「局中固定・次局継承だけを次のテーマとする。新セッションの準備して」と選定した。対象は[承認済み計画タスク4](plans/2026-10-10-two-ply-implementation-plan.md#タスク4usi設定と実応答)の `test_keeps_two_ply_policy_for_current_game` 1項目のみ。通知・受付の次に、設定がいつの局へ適用されるかを一テーマで学べるため推薦した。

今回は文書準備だけ。本人が再開用プロンプトを新セッションへ入力するまで、新テーマの学習・テスト変更・誤り注入・製品変更を開始しない。対象は既存承認済み計画の一部で再承認不要。計画訂正が必要なら具体案を提示し明示承認を待つ。この引き継ぎは新規実装計画ではなく、再開案内である。

## 完了事項と意思決定の背景

タスク1・2の内部二手比較・詰み・境界・枝独立性、タスク3のCLI三択はmain統合・理解確認まで完了。前テーマはタスク4先頭2項目だけを実施した。

- `usi` の通知を三択へ拡張し、辞書へ `twoplymaterial` を追加。公開シグネチャを維持した。通知欠落のアサーションRed→最小追加→Green、通常表記と大小混在の受付もRANDOMのままになるRed→辞書追加→Green。
- 受付は値ごとに新実行して、前の有効設定が未受付を隠さないようにした。隔離8変異は対象アサーションFAIL（ERRORなし）・各復元成功。Refactor不要。
- ランチャーテストの旧通知期待値を見落とし、USI28件・全体359件で各1件失敗。対象ファイル外のため停止し、期待値1箇所のみ同期する計画訂正を説明。本人「承認する」で訂正承認を得て同期、USI28件・全体359件成功。失敗を隠して完了とはしなかった。
- 独立コード・文書再レビュー各Critical 0・Important 0・Minor 0。レビュアーも359件・Ruff・リンク448件問題0を確認。実装 `ee9db95`、準備 `c9f1e95`。
- 本人「ok」でmainへ `de357be` → `ee9db95` をfast-forward。取り込み後main上359件・Ruff整形28ファイル・lint・差分成功。統合記録 `6202640`。
- 最後の一問は大小混在 `tWoPlYmAtErIaL` が二手先読みか既定ランダムか。本人回答「二手先読み」、正解と補足を記録。回答・完了 `f5f8f82`。具体例の確認であり探索全般や新値の局中固定を習得・検証済みとは扱わない。

[前テーマ実施記録](learning/usi-three-policies.md)に失敗・承認・検証・回答を保存済み。タスク4全体は未完了。今回の選定は未知値保持・実選択・実プロセスbestmove・性能・棋力・ShogiHomeまで開始する許可ではない。

## 対象契約・表現・確認方法

計画の1項目をそのまま使う。

`test_keeps_two_ply_policy_for_current_game`：新値設定→position→go→Material設定→go。最初の二回はTWO_PLY_MATERIALを選択境界へ渡す。続くusinewgame→position→goはMATERIALを渡す。期待する三回の方針は独立に `[TWO_PLY_MATERIAL, TWO_PLY_MATERIAL, MATERIAL]` とする。既存spy境界を使い、実際の設定受付・状態処理を動かす。呼び出し数も3回を確認する。

`MoveSelectionPolicy` は方針データ、`run_usi_engine` はコマンドを処理する操作、`choose_move` は手を選ぶ操作。設定値 `configured_policy` と局内固定値 `game_policy` を分ける既存構造が対象。最初のgoで局内固定し、usinewgameで固定を解除して設定値を残す。

検出したい誤り：局中のMaterial設定が直ちに反映される、新局でも古い二手先読みが残る、usinewgameで設定がRANDOMへ戻る、新値だけ固定されない、二回目以降に選択方針を落とす。初回Greenなら既存成立と明記し、リスクに見合う隔離変異で対象アサーションFAILと各復元成功を確認する。読み込みERRORは振る舞いRedの証拠にしない。局中固定と次局継承の各アサーションの検出範囲を区別する。

旧方式の固定・継承、通知、新値受付、未指定は既存テストが補完する。新値後の未知値保持、新方式の実選択・局面保存・手なしresign・実プロセスbestmove、性能・棋力・ShogiHomeは未検証・対象外。後続へ自動継続しない。

## 現在の物理的状態

- 場所 `/Users/oki2a24/kaname-shogi`。準備開始main HEAD `f5f8f82`、清潔、origin/main `de357be` より4コミット先を実測。今回pushなし。次回も現物を照合する。
- 準備ブランチ `codex/usi-policy-lifetime-handoff` を作成。新規worktreeなし。準備のmain統合なし。
- Ruff 0.16.10と固定版一致、ローカルフック `.githooks` を今回確認。次回不足・不一致はREADMEのセットアップ手順で解消する。
- `kaname_shogi/usi_engine.py`：設定値80行、局内固定81行、設定受付118行、usinewgame固定解除123行、初回go固定135行、選択呼び出し138行付近。
- `tests/test_usi_engine.py`：既存spy121行、旧局中変更292行、旧設定継承321行付近。新テーマのテストは未追加。
- 必読：AGENTS.md、README、docs/documentation-guide.md、docs/resume.md、本引き継ぎ、docs/plans/2026-10-10-two-ply-implementation-plan.md、docs/plans/2026-10-10-evaluation-next-stage-design.md、docs/learning/usi-three-policies.md、docs/knowledge/usi-engine-response.md、docs/knowledge/test-coverage-review.md、`/Users/oki2a24/.codex/observations/test-driven-development.md`。
- 補助台帳 `.superpowers/sdd/2026-10-10-two-ply-implementation-plan/progress.md` は部分実施履歴。恒久記録とGit現物を優先する。task-startは日本語見出し非対応だったので本文を直接照合する。補助ツール都合で計画を訂正しない。
- 前テーマの一時ログ `/tmp/usi-main-full.log`、変異 `/tmp/check_usi_mutations.py` は消える可能性がある。恒久結果は学習記録へ保存済み。

## 次の具体的な行動

1. 指定ディレクトリで `git status --short --branch`、`git log -4 --oneline`、`.venv/bin/ruff --version`、`git config --local --get core.hooksPath` を実行。準備文書と現Gitを照合する。
2. 必読資料とコードを読み、タスク4の局中固定・次局継承1項目だけに範囲を固定。契約・独立期待値・検出対象・既存補完・未検証を確認。訂正が必要なら具体案の明示承認を待つ。
3. using-superpowers、roadmap-management、実行スキル、TDD・完了前検証・独立レビューを適用し、main以外で現在の基準全体テストを実行。前回359件を現在結果へ流用しない。
4. 対象テストを追加し、各振る舞いのRed→最小実装→Green→Refactor要否を確認。初回Greenは既存成立と区別し、隔離誤り注入と復元を確認する。不要な製品変更をしない。
5. USI関連テストと全体回帰、Ruff、差分、独立レビューを実施。Critical/Importantを解消・再検証・再レビューし、今回の範囲だけ記録・案内を更新、リンク確認後通常コミット。タスク4全体完了とはしない。
6. main取り込みは別途本人承認。取り込み先検証後に最後の理解確認を一問だけ出し、回答を待って記録。本人が次テーマを選ぶまで後続を開始しない。

## 再開用プロンプト

> `/Users/oki2a24/kaname-shogi` で「USI新方式の局中固定・次局継承だけ」を再開してください。Git状態、AGENTS.md、docs/resume.md、docs/handover-usi-policy-lifetime.mdを確認し、「次の具体的な行動」に従ってください。対象は承認済み計画タスク4の test_keeps_two_ply_policy_for_current_game 1項目のみです。振る舞いごとにTDDを行い、初回Greenなら検出力と復元を確認してください。計画訂正は明示承認を待ち、未知値保持・実応答・性能測定へ自動継続せず、main取り込みは別途本人承認を得てください。

## 今回準備の検証・保存状態

今回は文書のみ。新テーマの学習・テスト変更・TDD・変異・製品変更・全体テスト再実行なし。リンク・Ruff・差分・独立文書レビューを実施して結果を追記し、通常コミットへ保存する。

準備5文書の相対リンク・見出し413件問題0、Ruff整形28ファイル・lint・差分成功。独立文書レビューはCritical 0・Important 0・Minor 1（再開案内の「計画訂正は明示承認待ち」が現在の未承認案の存在に読める）。「必要になった場合は明示承認を待つ」へ修正し、条件であることを明確にした。未解消指摘なし。結果追記後の最終検査を行い、通常コミットへ保存する。準備のmain統合・pushなし。
