# 学習・開発の再開案内

## 現在地

2026-10-18更新。選定済みテーマ「承認済み設計から実装計画を作り、計画の明示承認後に、段階的に実装・検証・独立レビューまで進める」を開始した。[実装計画](plans/2026-10-18-iterative-deepening-stop-time-control-implementation-plan.md)を作成し、独立レビュー・Minor 1件の補強・再確認を完了した。未解決Critical 0・Important 0・Minor 0。本人の計画承認はまだなく、計画を提示して明示承認を待つ。

承認前にTDD・コード・テスト変更を開始しない。main取り込みは別承認。中断は完了と中断の別型をユニオン型で返す。既存時間管理と三方式を維持し、通常対局・USI・CLIへの新方式接続、予算式変更、時間保証は対象外。

作業場所は `/Users/oki2a24/kaname-shogi`、ブランチ `codex/iterative-deepening-stop-time-control-implementation`。開始HEADは `6418379`。mainから同じディレクトリで作業ブランチを作成し、別worktreeなし。計画・記録は内容確認と文書検証後にこのブランチへ保存する。main未取り込み、pushなし。現在の差分とHEADは再開時に再取得する。

## 次に読むもの

- [今回の計画・学習・実施記録](learning/iterative-deepening-stop-time-control-implementation.md)：開始時Git・環境照合、判断、レビュー、検証と未完了。
- [実装計画](plans/2026-10-18-iterative-deepening-stop-time-control-implementation-plan.md)：5段階の対象・API・検出対象・手順と承認状態。
- [承認済み設計](plans/2026-10-18-iterative-deepening-stop-time-control-design.md)、[設計の学習・独立レビュー](learning/iterative-deepening-stop-time-control-design.md)。設計承認は計画承認の代わりにならない。
- [今回の開始時引き継ぎ](handover-iterative-deepening-stop-time-control-implementation.md)：開始前の背景と読むコード・テスト。新セッション開始待ちという記述は当時の状態。
- [探索停止](knowledge/search-stop.md)、[時計予算](knowledge/time-budget.md)、[探索比較](knowledge/search-comparison.md)、[検出力点検](knowledge/test-coverage-review.md)、[文書更新ガイド](documentation-guide.md)。

## 前テーマの履歴と検証の区別

時間制御接続の設計は本人が全体承認し、57346acで文書保存、044f117で統合記録、6b1f288で最後の理解確認を保存。独立設計レビューはmain統合後に補完し、Critical 0・Important 0・Minor 0、契約変更不要と判断した。順序不備の経緯は設計の学習記録に残る。引き継ぎ保存は6418379。前テーマの作業ブランチは削除済み。

反復深化実装4253c77、統合記録1e43f4b、理解確認fceea8d、テスト補強7f32f3e・54fc53a、統合記録0e4d079は過去の履歴。[補強記録](learning/iterative-deepening-test-strengthening.md)と[計画・結果](plans/2026-10-17-iterative-deepening-test-strengthening-plan.md)を参照。過去の全体513件成功、設計統合時のRuff・文書検査を今回の実測として扱わない。

今回、製品テストは未実施。文書のみの計画段階であり、新入口は未実装・未検証。文書全体の参照先は[索引](README.md)。
