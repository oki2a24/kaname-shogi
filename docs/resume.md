# 学習・開発の再開案内

第45回「古い文書記述の是正」は、mainへの取り込み、取り込み先検証、最後の理解確認まで完了した。次テーマは、本人が選んだ「コードとユニットテストの構造レビュー」である。新しいセッションで調査と設計から始めるため、次テーマの調査・設計・実装はまだ開始していない。

## 現在の物理状態

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`
- ブランチ：`main`
- 引き継ぎ準備開始時のHEAD：`04b07e6`
- リモートとの差：`origin/main` との差なし
- 引き継ぎ準備開始時の作業ツリー：クリーン
- 直近の検証：main取り込み後の全240テスト成功、マージ差分の書式検査成功、`kaname_shogi/` と `tests/` のマージ差分なし

上記のGit状態は引き継ぎ準備開始時点の記録である。再開時は必ず `git status --short --branch` と `git log -3 --oneline` で現在値を確認する。

## 次テーマの境界

- 対象は `kaname_shogi/` と `tests/` の責務、公開インターフェース、テスト分類、重複、内部実装への依存の調査である。
- GREENは、モジュールとテストの対応表、保守上の懸念、変更不要の根拠、必要なら候補となる小リファクタリングを記録することである。振る舞いは変更しない。
- 調査と設計を分け、リファクタリングは承認済みの別テーマにしない限り実施しない。
- 新しいセッションでは `brainstorming` を使って対象範囲、調査方法、記録形式、検証方法を設計し、一度に一問ずつ確認する。設計承認前にコード・テスト・既存文書を変更しない。

## 再開時に読む文書

1. `git status --short --branch` と `git log -3 --oneline` の現在結果
2. `AGENTS.md`
3. ルートの `README.md` と [文書索引](README.md)
4. この `docs/resume.md` と [コードとユニットテストの構造レビュー 開始時点の引き継ぎ](handover-code-and-unit-test-structure-review.md)
5. [リポジトリ基盤整理ロードマップ](roadmap-repository-foundation.md) のテーマ3
6. [第45回学習記録](learning/45-stale-document-correction.md)
7. `kaname_shogi/` の全モジュールと `tests/` の全テストファイル

## 再開用プロンプト

```text
kaname-shogiの次テーマ「コードとユニットテストの構造レビュー」を始めてください。最初にgit status --short --branchとgit log -3 --onelineで現在の状態を確認し、AGENTS.md、README.md、docs/README.md、docs/resume.md、docs/handover-code-and-unit-test-structure-review.md、docs/roadmap-repository-foundation.md、docs/learning/45-stale-document-correction.mdを読んでください。その後、kaname_shogi/とtests/の全ファイルを読み、モジュールとテストの対応、責務、公開インターフェース、重複、内部実装への依存を調査してください。今回のGREENは、対応表、保守上の懸念、変更不要の根拠、必要なら別テーマにする小リファクタリング候補を記録することです。振る舞いは変更しません。superpowerssuperpowers:brainstormingを使い、対象範囲、調査方法、記録形式、検証方法を設計し、一度に一問ずつ確認してください。設計を提示して私の明示的な承認を待ち、承認前にコード・テスト・既存文書を変更しないでください。調査結果を記録する実装計画を文書化した後も、計画を提示して私の明示的な承認を待ってください。必要な文書更新は目的が分かる作業ブランチで行い、日本語のConventional Commitにしてください。
```

このプロンプトを人間が新しいセッションへ入力するまで、次テーマの調査・設計・実装を開始しない。
