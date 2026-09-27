# 学習・開発の再開案内

第44回「文書ナビゲーションの最小改善」は、mainへの取り込み、取り込み先検証、最後の理解確認まで完了した。次テーマは、本人が選んだ小テーマ「古い文書記述の是正」である。設計仕様と実装計画の承認を終え、現在は `codex/stale-document-correction` ブランチで実装中である。

以下の「現在の物理状態」以降は、この案内を作成した時点の記録であり、現在の手順ではない。現在の状態は上記の進行状況、現在のGit状態、承認済みの設計仕様と実装計画で確認する。

## 現在の物理状態

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`
- ブランチ：`main`
- 引き継ぎ準備開始時のHEAD：`e6fa7436761633d026d950be3c5ef282d4996871`
- リモートとの差：`origin/main` より6コミット先行。引き継ぎ準備のコミット後は7コミット先行する見込み
- 引き継ぎ準備開始時の作業ツリー：クリーン
- 直近の検証：全240テスト成功、引き継ぎ関連5文書の相対リンク181件解決、`kaname_shogi/` と `tests/` に差分なし、`git diff --check` 成功

上記のGit状態は引き継ぎ準備開始時点の記録である。再開時は必ず `git status --short --branch` と `git log -3 --oneline` で現在値を確認する。

## 次テーマの境界

- 第43回の棚卸しで、ナビゲーション改善と古い内容の是正を別テーマにすることを合意済みである。
- 主な対象候補は `docs/02-project-direction.md` と `docs/next-topics.md`。入口文書は、調査で根拠付きの古い記述が見つかった場合だけ扱う。
- 過去の学習記録・設計書・実装計画・引き継ぎは、その時点の履歴として原則変更しない。
- 既存文書の移動・改名・削除、コード・テスト・将棋規則・CLI動作・JSON保存形式の変更は対象外である。
- 新しいセッションでは `brainstorming` で範囲と表現を決め、設計を提示して本人の承認を待つ。承認前に対象文書を変更しない。

## 再開時に読む文書

1. `git status --short --branch` と `git log -3 --oneline` の現在結果
2. `AGENTS.md`
3. ルートの `README.md` と [文書索引](README.md)
4. この `docs/resume.md` と [開始時点の引き継ぎ](handover-repository-foundation-stale-document-correction.md)
5. [リポジトリ基盤整理ロードマップ](roadmap-repository-foundation.md)
6. [文書構成の棚卸しと入口設計](plans/2026-09-27-repository-document-navigation-design.md) の「方向性、次テーマ、ロードマップ」「優先度2：古い記述の是正」
7. [第43回学習記録](learning/43-document-structure-audit.md) の古い内容の修正方針と、[第44回学習記録](learning/44-document-navigation.md) の完了状態
8. 対象候補の [プロジェクトの方向性](02-project-direction.md) と [次テーマの候補と選定履歴](next-topics.md)

## 再開用プロンプト

```text
kaname-shogiの次テーマ「古い文書記述の是正」を始めてください。最初にgit status --short --branchとgit log -3 --onelineで現在の状態を確認し、AGENTS.md、README.md、docs/README.md、docs/resume.md、docs/handover-repository-foundation-stale-document-correction.md、docs/roadmap-repository-foundation.md、docs/plans/2026-09-27-repository-document-navigation-design.md、docs/learning/43-document-structure-audit.md、docs/learning/44-document-navigation.md、docs/02-project-direction.md、docs/next-topics.mdを読んでください。第43回でナビゲーション改善と古い内容の是正を分離し、第44回のナビゲーション改善は完了済みです。主な対象候補はdocs/02-project-direction.mdとdocs/next-topics.mdですが、履歴文書は原則その時点の記録として維持し、現在情報として読まれる根拠付きの古い記述だけを必要最小限に直してください。既存文書の移動・改名・削除、コード・テスト・将棋規則・CLI動作・JSON保存形式の変更は対象外です。superpowerssuperpowers:brainstormingを使って対象範囲、現在情報と履歴の境界、表現、検証方法を設計し、一度に一問ずつ確認してください。設計を提示して私の明示的な承認を待ち、承認前に対象文書を変更しないでください。実装計画を文書化した後も、その計画を提示して私の明示的な承認を待ってください。実装は原則としてmain以外の目的が分かる作業ブランチで行い、リンク検査、コード・テスト差分がないことの確認、独立レビュー、検証、学習記録を含めてください。コミットメッセージは日本語のConventional Commitにしてください。
```

このプロンプトを人間が新しいセッションへ入力するまで、次テーマの調査・設計・実装を開始しない。
