# 学習・開発の再開案内

第44回「文書ナビゲーションの最小改善」を `codex/document-navigation` ブランチで進めている。
第43回で承認した設計に基づき、実装計画は承認済みである。

現在までに、`docs/README.md` のテーマ・学習回別索引、簡潔な `README.md`、第44回学習記録を作成した。開始前の全240テスト、相対リンク、文書の網羅性、コード・テストに差分がないことを確認した。初回の独立レビューで、着手前の再開案内を現在情報として扱う矛盾がCritical 1件、導入見出しの不足がMinor 1件として確認されたため、本人の承認を得て本書と索引を修正した。再レビューはCritical・Important・Minorすべて0件で、実装とレビューは完了している。

作業を再開するときは、次の順で現在状態を確認する。

1. `git status --short --branch` で実際のブランチと差分を確認する。
2. `AGENTS.md`、ルートの `README.md`、[文書索引](README.md) を読む。
3. [承認済み設計](plans/2026-09-27-repository-document-navigation-design.md) と [実装計画](plans/2026-09-27-repository-document-navigation.md) を読み、未完了のチェック項目から再開する。
4. [リポジトリ基盤整理ロードマップ](roadmap-repository-foundation.md) でテーマ2がmain取り込み待ちであることを確認する。

[テーマ開始時点の引き継ぎ](handover-repository-foundation-document-navigation.md) にあるブランチ、HEAD、リモートとの差、テスト件数、未実施事項は、作成時点の情報である。現在値として使わず、現在のGit状態と実装計画を優先する。

次は、相対リンク、変更範囲、Markdown差分を最終検証し、作業ブランチへコミットする。その後、実装・検証・レビュー・記録を提示して本人の明示的承認を得る。承認までmainへ取り込まない。

テーマ2をmainへ取り込み、取り込み先での検証と最後の理解確認を終えるまで、テーマ3以降へ進まない。
