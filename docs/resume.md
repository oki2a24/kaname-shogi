# 学習・開発の再開案内

## 現在地

2026-10-18更新。本人「2」により次テーマ「承認済み開発用コマンド設計から実装計画を作る」を選定済み。[新セッション用引き継ぎ](handover-controlled-iterative-search-command-plan.md)に選定理由・完了事項・Git状態・参照資料・[再開プロンプト](handover-controlled-iterative-search-command-plan.md#再開用プロンプト)を保存した。

次は本人が再開プロンプトを新セッションへ入力するのを待つ。次テーマは実装計画の作成・独立レビュー・提示まで。具体的な計画の明示承認を待ち、TDD・コード/テスト変更・実装は始めない。選定と設計承認を、まだ存在しない計画への承認へ読み替えない。

作業場所 `/Users/oki2a24/kaname-shogi`、main。引き継ぎ作成開始HEAD8d29088、clean、origin/mainより17コミット先。今回も文書のみで、別worktreeの追加利用なし。他テーマの既存4件は確認したが未操作。Ruff0.16.10とhooksPath=.githooksを再確認済み。引き継ぎ保存後のHEAD・差分は再取得する。

## 完了した開発用コマンド設計

学習・設計・独立レビュー・本人による[設計全体](plans/2026-10-18-controlled-iterative-search-command-design.md)の明示承認と、最後の理解確認まで完了。[学習記録](learning/controlled-iterative-search-command-design.md)に個別選択・承認・レビュー・初回誤答と再確認正解を区別して保存した。設計承認0e5ea66、理解確認/候補8d29088。独立レビューの初回Minor 1は記録更新で解消、最終Critical/Important/Minorすべて0。

専用コマンドで一回探索。SFEN・上限深さ・目標/上限msは必須。探索直前から計時して合法予備手準備を含み、終了時に状態・選択手/由来・最新完了記録を表示する。Ctrl+Cは中断130。コマンドは未実装。既存三方式と比較入口を維持し、通常対局・USIへの新方式接続、予算式変更、時間保証は対象外。

今回の設計セッションで製品テストは実行していない。文書検査と通常フックの成功のみ。過去の探索部品546件成功などを今回の実測とは扱わない。新コマンド動作、実時間性能・期限内応答、SIGINT実プロセス、USI競合、全局面/OS、棋力などは未検証。

## 完了した前テーマ

時間制御付き反復深化の計画承認、5段階の実装・検証・各段階と全体の独立レビュー、本人の別承認によるmain統合、取り込み先検証、最後の理解確認まで完了した。[実装計画と結果](plans/2026-10-18-iterative-deepening-stop-time-control-implementation-plan.md)、[学習・実施・本人回答](learning/iterative-deepening-stop-time-control-implementation.md)を参照する。

実装5コミットはca59b63・8d4ced6・73a0264・db31d03・30fe837、最終記録80e3db0まで統合、統合記録04de2ae、回答補足0be1c7a、理解確認と次候補605b0a3。最後の理解確認は初回の抑制時の手の扱いを補足し、再確認回答を記録して完了した。

直近の製品検証は取り込み先80e3db0で全体546件30.083秒OK、Ruff63ファイル整形確認・check、差分検査成功。代表変異11件と独立全体レビューは取り込み前の実績（最終Critical/Important/Minor 0/0/0）。これらを新セッションの実測として流用しない。以降は文書変更だけで、製品テストは再実行していない。過去の設計と反復深化補強の履歴は学習記録と各開始時引き継ぎからたどる。

## 次に読むもの

1. 現在のGit状態、AGENTS.md、本書、[新セッション用引き継ぎ](handover-controlled-iterative-search-command-plan.md)。
2. [承認済みコマンド設計](plans/2026-10-18-controlled-iterative-search-command-design.md)、[学習記録](learning/controlled-iterative-search-command-design.md)、新しい引き継ぎに列挙した資料。
3. [文書索引](README.md)、[選定済み候補と理由](next-topics.md)、ルートREADMEの開発用比較と制約、[方向性](02-project-direction.md)。
4. [探索停止](knowledge/search-stop.md)、[時計予算](knowledge/time-budget.md)、[探索比較](knowledge/search-comparison.md)、引き継ぎに列挙したコード・テスト。
5. [承認済み探索部品設計](plans/2026-10-18-iterative-deepening-stop-time-control-design.md)、[実施記録](learning/iterative-deepening-stop-time-control-implementation.md)、[検出力の点検](knowledge/test-coverage-review.md)、[文書更新ガイド](documentation-guide.md)。

全局面・全競合・実時間性能・期限内応答・新方式USI競合・実機対局・棋力・最適予算は未検証。過去の引き継ぎの現在地は保存当時の情報として読む。
