# 学習・開発の再開案内

## 現在地

2026-10-11更新。「USI新方式の局中固定・次局継承だけ」の指定テスト1項目を追加し、検証済み。独立コード・文書レビュー各Critical 0・Important 0・Minor 0。

- 場所 `/Users/oki2a24/kaname-shogi`、現在ブランチ `main`。本人「ok」で `f5f8f82` → `d3a7f32` をfast-forward済み（準備 `e69bf25` を含む）。製品変更・計画訂正・pushなし。
- 対象は承認済みタスク4の `test_keeps_two_ply_policy_for_current_game` のみ。初回Green、隔離6変異で対象FAIL・各復元成功。USI29件・全体360件成功。[今回の実施記録](learning/usi-policy-lifetime.md)。
- 取り込み先main上で全体360件・Ruff整形28ファイル・lint・差分成功。統合記録を通常コミットへ保存し、最後の理解確認を一問出して回答を待つ。未回答のためテーマ完了とはしない。
- タスク4全体は未完了。未知値保持・実応答・性能・棋力へ自動継続しない。

## 次に読む資料

[今回の実施記録](learning/usi-policy-lifetime.md)、[開始時点の引き継ぎ](handover-usi-policy-lifetime.md)、[承認済み計画タスク4](plans/2026-10-10-two-ply-implementation-plan.md#タスク4usi設定と実応答)、[USI知識](knowledge/usi-engine-response.md)、[テスト点検](knowledge/test-coverage-review.md)、[AGENTS.md](../AGENTS.md)、[文書ガイド](documentation-guide.md)。

## 二手先読み設計の完了

設計記録 `3e3c4cf`、統合検証 `cd19b58`、最終回答と候補 `c41aaea` はmainにある。取り込み先の相対リンク先373件欠落0（見出しアンカー対象外）、差分、Ruff整形28ファイルとlintを確認済み。文書のみで全体テストは再実行していない。今回の準備の検証は[引き継ぎ](handover-two-ply-implementation-plan.md)へ記録する。数値比較の習得全般を確認済みとは扱わない。

## 前テーマの完了と履歴

文書整理 `bbc2619` と統合・検証記録 `6d3f7e4` は元のmainへ取り込み済み。リンク888件・履歴3本文一致・差分・Ruff整形28ファイルとlintが成功。文書のみで全体テストは再実行していない。最後の回答と補足は[整理記録](learning/documentation-chapter.md)。今回の準備の検証とGit状態は[引き継ぎ](handover-evaluation-next-stage.md)を参照する。
