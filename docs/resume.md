# 学習・開発の再開案内

## 現在地

2026-10-18更新。選定済みテーマ「承認済みの時間制御付き反復の開発用コマンド設計から実装計画を作る」の[計画](plans/2026-10-18-controlled-iterative-search-command-implementation-plan.md)は独立レビュー後、本人が明示承認した。本人は順次実装と現在のcheckout内の作業ブランチを選択した。[作成・承認・実施記録](learning/controlled-iterative-search-command-implementation-plan.md)に経緯を保存する。

作業ブランチ `codex/controlled-iterative-search-command` でTask 1〜5を完了した。TaskごとのTDDと独立レビュー、最終検出力補強を行い、未知引数ケース追加後の専用テスト14/14、関連テスト68/68、全体テスト560/560、Ruff format/checkが成功した。代表変異8件を隔離コピーで対象assertionにより検出し、最終独立ブランチレビューはCritical 0 / Important 0 / Minor 0。初回最終レビューのMinor 1は、未知引数を専用経路で拒否するケースを追加して解消した。詳細は[実施記録](learning/controlled-iterative-search-command-implementation-plan.md)と[承認済み計画](plans/2026-10-18-controlled-iterative-search-command-implementation-plan.md)を参照する。

実装・検証・記録は作業ブランチ上で完了し、mainには未統合。mainへの取り込みは別承認が必要。本人の最後の理解確認を一問提示して回答待ちにする。回答を得るまで次テーマへ進まない。通常対局・USIへの新方式接続、予算式変更、時間保証は対象外のまま維持した。

作業場所 `/Users/oki2a24/kaname-shogi`。計画作成時の開始状態はmain、HEAD `c4751e7`、clean、origin/mainより18コミット先。計画案とレビュー記録は `c61318d`、本人の承認と実行方式の記録は `f8429f8` で保存した。実装開始時は作業ブランチ `codex/controlled-iterative-search-command` を現物確認し、Ruff 0.16.10とhooksPath `.githooks` を再確認した。これらは開始時点の状態で、現在のHEADや検証結果ではない。

## 完了した開発用コマンド設計

学習・設計・独立レビュー・本人による[設計全体](plans/2026-10-18-controlled-iterative-search-command-design.md)の明示承認と、最後の理解確認まで完了。[学習記録](learning/controlled-iterative-search-command-design.md)に個別選択・承認・レビュー・初回誤答と再確認正解を区別して保存した。設計承認0e5ea66、理解確認/候補8d29088。独立レビューの初回Minor 1は記録更新で解消、最終Critical/Important/Minorすべて0。

専用コマンドで一回探索。SFEN・上限深さ・目標/上限msは必須。操作セット生成後の探索直前から計時し、探索内部の合法予備手準備を含む。Task 1〜5として入力検査、一回探索接続、四状態表示、`main`・例外境界・実プロセス入口、全体検証を完了。最終専用テスト14/14、関連68/68、全体560/560、Ruff成功。代表変異8件と最終独立ブランチレビューCritical 0 / Important 0 / Minor 0。既存三方式と比較入口を維持し、通常対局・USIへの新方式接続、予算式変更、時間保証は対象外。

計画作成時点では製品テスト未実行だった。その後の実装テスト結果は上記Task 1〜5の今回実測に限る。過去の探索部品546件成功などを今回の実測とは扱わない。実時間性能・期限内応答、SIGINT実プロセス配送、USI競合、全局面/OS、棋力などは未検証。

## 完了した前テーマ

時間制御付き反復深化の計画承認、5段階の実装・検証・各段階と全体の独立レビュー、本人の別承認によるmain統合、取り込み先検証、最後の理解確認まで完了した。[実装計画と結果](plans/2026-10-18-iterative-deepening-stop-time-control-implementation-plan.md)、[学習・実施・本人回答](learning/iterative-deepening-stop-time-control-implementation.md)を参照する。

実装5コミットはca59b63・8d4ced6・73a0264・db31d03・30fe837、最終記録80e3db0まで統合、統合記録04de2ae、回答補足0be1c7a、理解確認と次候補605b0a3。最後の理解確認は初回の抑制時の手の扱いを補足し、再確認回答を記録して完了した。

直近の製品検証は取り込み先80e3db0で全体546件30.083秒OK、Ruff63ファイル整形確認・check、差分検査成功。代表変異11件と独立全体レビューは取り込み前の実績（最終Critical/Important/Minor 0/0/0）。これらを新セッションの実測として流用しない。以降は文書変更だけで、製品テストは再実行していない。過去の設計と反復深化補強の履歴は学習記録と各開始時引き継ぎからたどる。

## 次に読むもの

1. 現在のGit状態、AGENTS.md、本書、[開始時の引き継ぎ](handover-controlled-iterative-search-command-plan.md)。
2. [実装計画案](plans/2026-10-18-controlled-iterative-search-command-implementation-plan.md)、[計画作成・レビュー記録](learning/controlled-iterative-search-command-implementation-plan.md)、[承認済みコマンド設計](plans/2026-10-18-controlled-iterative-search-command-design.md)、[設計学習記録](learning/controlled-iterative-search-command-design.md)。
3. [文書索引](README.md)、[選定済み候補と理由](next-topics.md)、ルートREADMEの開発用比較と制約、[方向性](02-project-direction.md)。
4. [探索停止](knowledge/search-stop.md)、[時計予算](knowledge/time-budget.md)、[探索比較](knowledge/search-comparison.md)、引き継ぎに列挙したコード・テスト。
5. [承認済み探索部品設計](plans/2026-10-18-iterative-deepening-stop-time-control-design.md)、[実施記録](learning/iterative-deepening-stop-time-control-implementation.md)、[検出力の点検](knowledge/test-coverage-review.md)、[文書更新ガイド](documentation-guide.md)。

全局面・全競合・実時間性能・期限内応答・新方式USI競合・実機対局・棋力・最適予算は未検証。過去の引き継ぎの現在地は保存当時の情報として読む。
