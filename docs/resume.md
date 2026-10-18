# 学習・開発の再開案内

## 現在地

2026-10-18更新。次テーマは本人「2」により「時間制御付き反復を試す開発用コマンドの学習・設計」に選定済み。[新セッション用引き継ぎ](handover-controlled-iterative-search-command-design.md)に選定理由・完了事項・Git状態・読む資料・未決定事項と[再開プロンプト](handover-controlled-iterative-search-command-design.md#再開用プロンプト)を保存した。

次は本人が再開プロンプトを新しいセッションへ入力するのを待つ。入力前に次テーマの学習・設計を始めない。次テーマは学習・設計・独立設計レビュー・設計提示までで、実装計画・TDD・コード/テスト変更は未承認。予算や表示の仕様、コマンド構成、Ctrl+Cの扱いも未決定。通常三方式を維持し、通常対局・USIへの新方式接続、予算式変更、時間保証は対象外。

作業場所 `/Users/oki2a24/kaname-shogi`、main。引き継ぎ作成開始HEAD605b0a3、clean、origin/mainより14コミット先。今回の作業ブランチは統合・検証後に削除済み、pushなし。引き継ぎ保存後のHEAD・差分は再取得する。今回の作業で別worktreeを作成/利用していないが、他テーマの既存worktree4件は現物で確認しており未操作。

## 完了した前テーマ

時間制御付き反復深化の計画承認、5段階の実装・検証・各段階と全体の独立レビュー、本人の別承認によるmain統合、取り込み先検証、最後の理解確認まで完了した。[実装計画と結果](plans/2026-10-18-iterative-deepening-stop-time-control-implementation-plan.md)、[学習・実施・本人回答](learning/iterative-deepening-stop-time-control-implementation.md)を参照する。

実装5コミットはca59b63・8d4ced6・73a0264・db31d03・30fe837、最終記録80e3db0まで統合、統合記録04de2ae、回答補足0be1c7a、理解確認と次候補605b0a3。最後の理解確認は初回の抑制時の手の扱いを補足し、再確認回答を記録して完了した。

直近の製品検証は取り込み先80e3db0で全体546件30.083秒OK、Ruff63ファイル整形確認・check、差分検査成功。代表変異11件と独立全体レビューは取り込み前の実績（最終Critical/Important/Minor 0/0/0）。これらを新セッションの実測として流用しない。以降は文書変更だけで、製品テストは再実行していない。過去の設計と反復深化補強の履歴は学習記録と各開始時引き継ぎからたどる。

## 次に読むもの

1. 現在のGit状態、AGENTS.md、本書、[新しい引き継ぎ](handover-controlled-iterative-search-command-design.md)。
2. [文書索引](README.md)、[選定済み候補と理由](next-topics.md)、ルートREADMEの開発用比較と制約、[方向性](02-project-direction.md)。
3. [探索停止](knowledge/search-stop.md)、[時計予算](knowledge/time-budget.md)、[探索比較](knowledge/search-comparison.md)、引き継ぎに列挙したコード・テスト。
4. [承認済み探索部品設計](plans/2026-10-18-iterative-deepening-stop-time-control-design.md)、[実施記録](learning/iterative-deepening-stop-time-control-implementation.md)、[検出力の点検](knowledge/test-coverage-review.md)、[文書更新ガイド](documentation-guide.md)。

全局面・全競合・実時間性能・期限内応答・新方式USI競合・実機対局・棋力・最適予算は未検証。過去の引き継ぎの現在地は保存当時の情報として読む。
