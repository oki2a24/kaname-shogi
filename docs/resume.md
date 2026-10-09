# 学習・開発の再開案内

## 現在地

2026-10-10更新。テーマは「評価・探索の章へ進む前の文書整理」。本人は入口5文書の整理案を「良い」と承認し、今後の更新ガイドとAGENTS.mdへの参照追加も「良い」と承認した。文書整理・更新ガイド追加・文書検証・独立レビューとMinor対応まで完了。本人は「良い」と記録確認・コミット・main取り込みを承認済み。コミット・main取り込み・取り込み先検証・最後の理解確認はこれから行う。

- 作業場所：`/Users/oki2a24/kaname-shogi`。作業ブランチ `codex/documentation-chapter`、整理開始HEAD `86e6794`。今回は別worktreeを作成していない。既存worktreeの有無はGitで確認する。
- mainは `7389138`。引き継ぎ準備 `86e6794` と今回の整理はmain未取り込み。pushなし。状態は再開時に実測する。
- 次の作業：承認済みのコミット・main取り込みを行い、取り込み先で検証して最後の理解確認を一問出す。
- 評価・探索の学習・設計・実装、コード・テスト・Ruff設定変更、ShogiHome操作は今回の範囲外。

## 次に読む資料

1. `git status --short --branch` と `git log -3 --oneline` で現物を確認する。
2. [AGENTS.md](../AGENTS.md)、[ルートREADME](../README.md)、[更新ガイド](documentation-guide.md)。
3. [今回の整理記録](learning/documentation-chapter.md)、[次テーマ候補](next-topics.md)、必要な資料は[文書索引](README.md)から選ぶ。
4. [今回の開始時引き継ぎ](handover-documentation-chapter.md)は開始時の背景として読む。そこにある承認待ちは現在の承認状態の代用にしない。

## 完了済みの土台と履歴

第75回までの接続整備とRuffの導入・拡張・運用方針・理解確認は完了。現行運用は[Python品質検査](knowledge/python-quality-checks.md)、経緯と本人回答は[追加検査・運用方針の記録](learning/ruff-practical-rules.md)。過去の成功を今回の検証結果として扱わない。

整理前の再開案内は[履歴](resume-history.md)に保存した。現在地へ過去の状態や古い再開用プロンプトを積み重ねない。
