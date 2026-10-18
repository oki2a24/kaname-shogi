# 学習・開発の再開案内

## 現在地

2026-10-18更新。「時間制御付き反復を試す開発用コマンドの学習・設計」は学習・設計・独立レビュー・設計提示を終え、本人「yes」により[設計全体](plans/2026-10-18-controlled-iterative-search-command-design.md)を明示承認済み。[学習記録](learning/controlled-iterative-search-command-design.md)に回答・補足・個別選択・全体承認・レビューを保存した。開始背景は[引き継ぎ](handover-controlled-iterative-search-command-design.md)へ保存済み。

専用コマンドで一回探索し、SFEN・上限深さ・直接指定の目標ms/上限msを必須とする。探索直前から計時し、合法予備手準備を含める。結果は終了時にまとめ、選択手と完了記録を区別する。Ctrl+Cは中断130。独立レビューは初回Minor 1（現在地記録の更新）を解消し、最終Critical・Important・Minorはすべて0。

今回の範囲は学習・設計まで。実装計画・TDD・コード/テスト変更には進んでいない。最後の理解確認は本人「1」で正解し、回答・補足を学習記録へ保存した。[次テーマ候補](next-topics.md)を提示して本人の選択を待つ。後続テーマは未選定。既存三方式を維持し、通常対局・USIへの新方式接続、予算式変更、時間保証は対象外。

作業場所 `/Users/oki2a24/kaname-shogi`、main。開始時HEAD083f230、clean、origin/mainより15コミット先を確認した。設計承認記録は0e5ea66として保存済み。その後の再確認でclean、origin/mainより16コミット先。今回は最後の理解確認と候補の文書3件を更新して保存する段階。保存後のHEAD・差分はgitで再取得する。別worktreeは利用していない。Ruff0.16.10とhooksPath=.githooksを確認済み。製品テストは今回未実行。

## 完了した前テーマ

時間制御付き反復深化の計画承認、5段階の実装・検証・各段階と全体の独立レビュー、本人の別承認によるmain統合、取り込み先検証、最後の理解確認まで完了した。[実装計画と結果](plans/2026-10-18-iterative-deepening-stop-time-control-implementation-plan.md)、[学習・実施・本人回答](learning/iterative-deepening-stop-time-control-implementation.md)を参照する。

実装5コミットはca59b63・8d4ced6・73a0264・db31d03・30fe837、最終記録80e3db0まで統合、統合記録04de2ae、回答補足0be1c7a、理解確認と次候補605b0a3。最後の理解確認は初回の抑制時の手の扱いを補足し、再確認回答を記録して完了した。

直近の製品検証は取り込み先80e3db0で全体546件30.083秒OK、Ruff63ファイル整形確認・check、差分検査成功。代表変異11件と独立全体レビューは取り込み前の実績（最終Critical/Important/Minor 0/0/0）。これらを新セッションの実測として流用しない。以降は文書変更だけで、製品テストは再実行していない。過去の設計と反復深化補強の履歴は学習記録と各開始時引き継ぎからたどる。

## 次に読むもの

1. 現在のGit状態、AGENTS.md、本書、[承認済みコマンド設計](plans/2026-10-18-controlled-iterative-search-command-design.md)、[今回の学習記録](learning/controlled-iterative-search-command-design.md)。開始時の引き継ぎは履歴として読む。
2. [文書索引](README.md)、[選定済み候補と理由](next-topics.md)、ルートREADMEの開発用比較と制約、[方向性](02-project-direction.md)。
3. [探索停止](knowledge/search-stop.md)、[時計予算](knowledge/time-budget.md)、[探索比較](knowledge/search-comparison.md)、引き継ぎに列挙したコード・テスト。
4. [承認済み探索部品設計](plans/2026-10-18-iterative-deepening-stop-time-control-design.md)、[実施記録](learning/iterative-deepening-stop-time-control-implementation.md)、[検出力の点検](knowledge/test-coverage-review.md)、[文書更新ガイド](documentation-guide.md)。

全局面・全競合・実時間性能・期限内応答・新方式USI競合・実機対局・棋力・最適予算は未検証。過去の引き継ぎの現在地は保存当時の情報として読む。
