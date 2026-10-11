# 次テーマへの引き継ぎ：USI新値後の未知値保持だけ

## 最終目標と選定理由

2026-10-11、本人は前テーマの理解確認後に提示した候補から「未知値保持だけ。新セッションの準備して」と選定した。対象は[承認済み計画タスク4](plans/2026-10-10-two-ply-implementation-plan.md#タスク4usi設定と実応答)の `test_invalid_value_preserves_two_ply_setting` 1項目のみ。設定状態に関する残る1項目を既存spy境界で小さく確認できるため推薦した。

今回は文書準備のみ。本人が再開用プロンプトを新セッションへ入力するまで、新テーマの学習・テスト変更・誤り注入・製品変更を開始しない。既存承認済み計画の部分再開であり再承認不要。計画訂正が必要になった場合は具体案を提示して明示承認を待つ。本書は新規実装計画ではなく再開案内である。

## 完了事項と意思決定の背景

タスク1・2の内部二手比較・詰み・境界・枝独立性、タスク3のCLI三択、タスク4の通知・新値受付はmain統合・理解確認まで完了。直前のテーマではタスク4の局中固定・次局継承1項目だけを実施した。

- `test_keeps_two_ply_policy_for_current_game` を追加。新値設定→position→go→Material設定→go→usinewgame→position→goを処理し、呼出し3回と独立期待値 `[TWO_PLY_MATERIAL, TWO_PLY_MATERIAL, MATERIAL]` を確認した。
- 初回有効Green。既存の設定値と局内固定値の分離が新方針にも働いていたため、製品コードの変更は不要だった。未実装Red→製品修正の実績と混同していない。Refactorも不要。
- 隔離6変異（局中変更の即時反映・固定解除漏れ・設定のRANDOM消去・新値だけ固定漏れ・局中変更後の方針落ち・選択呼出し欠落）は全て対象アサーションFAIL、ERRORなし、各復元成功・ソース一致。局中固定はgo 2、次局継承はgo 3、呼出し欠落は回数で検出した。
- USI関連29件・全体360件・Ruff整形28ファイル・lint・差分成功。独立コード/文書レビュー各Critical 0・Important 0・Minor 0。コードレビュアーも対象27件と6変異・復元を再実行。計画訂正なし。実装保存 `d3a7f32`。
- 本人「ok」で元ディレクトリのmainへ `f5f8f82` → `d3a7f32` をfast-forward（準備 `e69bf25` を含む）。取り込み先main上で改めて全体360件・Ruff・差分成功。統合記録 `944b214`。
- 最後の本人回答は「現在局の次のgoは二手先読み。usinewgame後の次局のgoはMaterial」。正解と補足を分けて記録した。回答と完了 `12a6d74`。具体例の理解確認であり、未知値保持や実応答を習得・検証済みとは扱わない。

失敗・検証主体・未検証範囲の詳細は[前テーマの実施記録](learning/usi-policy-lifetime.md)に保存済み。初回コミット操作はサンドボックスでindex.lock作成を拒否され、許可された権限付き再実行で通常フックを通して保存した。検査を回避していない。未解消の失敗・レビュー指摘なし。タスク4全体は未完了。

## 対象契約・表現・確認方法

計画の指定1項目をそのまま使う。

`test_invalid_value_preserves_two_ply_setting`：新値→未知値→goは新値。無設定はRANDOM、旧Random/Materialも従来値をassertする。既存spy境界で実際の設定受付・状態処理を動かし、選択処理へ届く方針を確認する。新値を設定した後、最初のgoより前に未知値を送ることで、局内固定が設定消失を隠さないようにする。positionは既存対応形式を使う。期待値は製品辞書から生成せず、計画の方針値から独立に書く。

`MoveSelectionPolicy` は選択方針データ、`run_usi_engine` はコマンドを処理する操作、`choose_move` は手を選ぶ操作。`configured_policy` は最新の有効設定データ。未知値でこれを置き換えないことが今回の焦点であり、公開シグネチャを変えない。

検出したい誤りは、未知値でRANDOMへ戻す、Materialへ取り違える、新値の後だけ設定を消す、未知値を新しい有効値として扱う、選択境界へ設定を渡さないこと。初回Greenなら既存成立と明記し、リスクに見合う隔離誤り注入で意図したアサーションFAIL・各復元成功を確認する。読み込みERRORを振る舞いRedとして数えない。

旧値後の不正値保持、無設定、不正値のみ、通知、新値の大小混在受付、局中固定・次局継承は既存テストが補完する。指定項目にある無設定・旧値のassertと既存補完の範囲を照合し、今回単独で検出する誤りと全体が補う誤りを区別して記録する。不要な全組合せや将来機能を先取りしない。計画訂正が必要なら明示承認を待つ。

実選択・局面保存・手なしresign・実プロセスbestmove・性能・棋力・ShogiHomeは今回未検証・対象外。全体回帰に既存プロセステストが含まれていても、新方式の実応答検証を完了したとは扱わない。後続へ自動継続しない。

## 現在の物理的状態

- 場所 `/Users/oki2a24/kaname-shogi`。準備開始main HEAD `12a6d74`、差分なし、origin/mainより8コミット先を確認。今回pushなし。次回も現物を照合する。
- 準備ブランチ `codex/usi-invalid-value-handoff` を作成。新規worktreeなし。準備のmain統合なし。
- Ruff 0.16.10と固定版一致、ローカルフック `.githooks` を確認。次回不足・不一致ならREADMEのセットアップ手順で解消する。
- `kaname_shogi/usi_engine.py`：値辞書12行、設定値80行、局内固定81行、既知値判定117行・更新118行、固定解除123行、初回go固定135行・選択138行付近。
- `tests/test_usi_engine.py`：既存spy121行、新値受付243行、旧未知値263行、新値局中固定321行付近。未知値保持の指定新テストは未追加。
- 必読：AGENTS.md、README、docs/documentation-guide.md、docs/resume.md、本引き継ぎ、docs/plans/2026-10-10-two-ply-implementation-plan.md、docs/plans/2026-10-10-evaluation-next-stage-design.md、docs/learning/usi-policy-lifetime.md、docs/learning/usi-three-policies.md、docs/knowledge/usi-engine-response.md、docs/knowledge/test-coverage-review.md、`/Users/oki2a24/.codex/observations/test-driven-development.md`。
- 補助台帳 `.superpowers/sdd/2026-10-10-two-ply-implementation-plan/progress.md` は部分実施履歴。恒久記録とGit現物を優先する。task-startは日本語見出し非対応のため本文を直接照合し、補助ツール都合で計画を訂正しない。
- 一時ログ `/tmp/usi-lifetime-main.log`、変異スクリプト `/tmp/check_usi_lifetime_mutations.py` は消える可能性がある。恒久結果は学習記録に保存した。

## 次の具体的な行動

1. 指定ディレクトリで `git status --short --branch`、`git log -4 --oneline`、`.venv/bin/ruff --version`、`git config --local --get core.hooksPath` を実行し、引き継ぎと現物を照合する。
2. 必読資料・コードを読み、対象を承認済みタスク4の未知値保持1項目だけに固定。契約・独立期待値・代表例・検出対象・既存補完・未検証を確認する。訂正が必要なら具体案の明示承認を待つ。
3. using-superpowers、roadmap-management、実行スキル、TDD・完了前検証・独立レビューを適用し、main以外で現在の基準全体テストを実行。前回360件を現在結果へ流用しない。
4. 指定テストを追加し、振る舞いごとに失敗理由→最小実装→成功→Refactor要否を確認。初回Greenなら既存成立と区別して隔離誤り注入・復元を確認し、不要な製品変更をしない。
5. USI関連・全体回帰・Ruff・差分・独立レビューを実施。Critical/Importantは解消・再検証・再レビューしてから今回の範囲だけ記録・案内を更新。リンク検査後通常コミット。タスク4全体完了とはしない。
6. main取り込みは別途本人承認を待つ。取り込み先検証後に最後の理解確認を一問だけ出し、回答を待って記録。本人が次テーマを選ぶまで実応答・性能等へ進まない。

## 再開用プロンプト

> `/Users/oki2a24/kaname-shogi` で「USI新値後の未知値保持だけ」を再開してください。Git状態、AGENTS.md、docs/resume.md、docs/handover-usi-invalid-value.mdを確認し、「次の具体的な行動」に従ってください。対象は承認済み計画タスク4の test_invalid_value_preserves_two_ply_setting 1項目のみです。振る舞いごとにTDDを行い、初回Greenなら検出力と復元を確認してください。計画訂正は明示承認を待ち、実応答・性能測定へ自動継続せず、main取り込みは別途本人承認を得てください。

## 今回準備の検証・保存状態

今回は文書準備のみ。新テーマの学習・テスト変更・誤り注入・製品変更・全体テスト再実行なし。文書のリンク・Ruff・差分・独立レビューを確認し結果を追記して通常コミットへ保存する。

準備5文書の相対リンク・見出し413件問題0、Ruff整形確認28ファイル・lint・差分成功。独立文書レビューはCritical 0・Important 0・Minor 0、修正要求なし。レビュアーもリンク・差分・現ブランチと開始HEADを確認した。全体テスト・Ruffはレビューでは再実行していない。結果追記後に最終検査し、通常コミットへ保存する。準備のmain統合・pushなし。
