# 学習・開発の再開案内

## 現在地

2026-10-20更新。選定済みテーマ「承認済みCLI設計から実装計画を作る」を新セッションで開始し、[計画案全体](plans/2026-10-20-cli-search-time-control-implementation-plan.md)を作成した。独立レビュー初回0/1/0の指摘を対応し、再確認0/0/0、文書検証まで完了。計画全体を提示し、本人の「yes」によりAPIの具体化・手順・検証方法を含め承認済み。TDD・実装は未着手で、実装開始は別の指示待ち。今回の範囲は計画作成・独立レビュー・提示までであり、計画承認後も実装へ自動移行しない。[今回の作成・レビュー記録](learning/cli-search-time-control-plan.md)を参照する。

開始時は`/Users/oki2a24/kaname-shogi`、main、HEAD f3a05b8、origin/mainより5コミット先行、追跡ファイル変更なし、未追跡`.antigravity/tasks/`あり。作業用`codex/cli-search-time-control-plan`へ切り替え、同じディレクトリで文書4件だけを変更した。承認記録を含む文書検証・独立点検を終え、通常フックによる作業ブランチへのコミット対象とした。別worktree・main取り込み・pushなし。Ruff 0.16.10は固定版と一致、ローカルhooksPathは.githooks。未追跡ディレクトリは保持する。

仕様の正本は[承認済み設計](plans/2026-10-20-cli-search-time-control-design.md)、本人回答・変更合意・設計承認と理解確認は[設計学習記録](learning/cli-search-time-control-design.md)。[今回の開始時引き継ぎ](handover-cli-search-time-control-plan.md)は開始前の履歴として保持する。共通search_move・予算・停止契約を再利用し、コンピュータ手の事前詰み/全生成、完了深さ/手の由来表示は復活させない。時計保持・返却後判定・時計つき保存はCLI管理側。棋譜v1公開変換は設計承認範囲内、USI製品経路・共通探索・予算式・設定値は対象外。

前テーマは設計全体承認、独立レビュー再確認0/0/0、本人の別承認でmain統合・文書検証、最後の回答「CLI」まで完了。設計・記録は82a7368・843efdc・ae828e5・2e9a11d、開始準備はf3a05b8。製品機能は未変更で、今回製品テスト・TDD・変異注入・対局・時間測定は実行していない。

## 以前に完了した観察テーマ（時間制御付き探索コマンド）

前テーマではREADME記載の小さいSFENで開発用コマンドを一回実行し、理解確認まで完了した。[学習記録](learning/controlled-iterative-search-command-output-reading.md)に実出力・終了コード・本人の回答と補足を保存した。

実行条件は`--max-depth 4 --target-ms 50 --maximum-ms 100`。終了コード0、状態`STOPPED（通常停止）`、選択手`9i9h`は完了結果由来、完了記録は深さ2・評価＋0・訪問9・完了深さまでの累計13だった。出力から目標50msと上限100msのどちらが停止判断の原因かは特定できず、経過時間も表示されなかった。上限msは実応答時間の保証ではない。製品コード・テストの変更はなく、テストも実行していない。

## 完了した開発用コマンド設計

学習・設計・独立レビュー・本人による[設計全体](plans/2026-10-18-controlled-iterative-search-command-design.md)の明示承認と、最後の理解確認まで完了。[学習記録](learning/controlled-iterative-search-command-design.md)に個別選択・承認・レビュー・初回誤答と再確認正解を区別して保存した。設計承認0e5ea66、理解確認/候補8d29088。独立レビューの初回Minor 1は記録更新で解消、最終Critical/Important/Minorすべて0。

専用コマンドで一回探索。SFEN・上限深さ・目標/上限msは必須。操作セット生成後の探索直前から計時し、探索内部の合法予備手準備を含む。Task 1〜5として入力検査、一回探索接続、四状態表示、`main`・例外境界・実プロセス入口、全体検証を完了。最終専用テスト14/14、関連68/68、全体560/560、Ruff成功。代表変異8件と最終独立ブランチレビューCritical 0 / Important 0 / Minor 0。既存三方式と比較入口を維持し、通常対局・USIへの新方式接続、予算式変更、時間保証は対象外。

計画作成時点では製品テスト未実行だった。その後の実装テスト結果は上記Task 1〜5の今回実測に限る。過去の探索部品546件成功などを今回の実測とは扱わない。実時間性能・期限内応答、SIGINT実プロセス配送、USI競合、全局面/OS、棋力などは未検証。

## 完了した前テーマ

時間制御付き反復深化の計画承認、5段階の実装・検証・各段階と全体の独立レビュー、本人の別承認によるmain統合、取り込み先検証、最後の理解確認まで完了した。[実装計画と結果](plans/2026-10-18-iterative-deepening-stop-time-control-implementation-plan.md)、[学習・実施・本人回答](learning/iterative-deepening-stop-time-control-implementation.md)を参照する。

実装5コミットはca59b63・8d4ced6・73a0264・db31d03・30fe837、最終記録80e3db0まで統合、統合記録04de2ae、回答補足0be1c7a、理解確認と次候補605b0a3。最後の理解確認は初回の抑制時の手の扱いを補足し、再確認回答を記録して完了した。

直近の製品検証は取り込み先80e3db0で全体546件30.083秒OK、Ruff63ファイル整形確認・check、差分検査成功。代表変異11件と独立全体レビューは取り込み前の実績（最終Critical/Important/Minor 0/0/0）。これらを新セッションの実測として流用しない。以降は文書変更だけで、製品テストは再実行していない。過去の設計と反復深化補強の履歴は学習記録と各開始時引き継ぎからたどる。

## 次にすること

[承認済み計画全体](plans/2026-10-20-cli-search-time-control-implementation-plan.md)と[承認記録](learning/cli-search-time-control-plan.md)を基準に、本人から実装開始の別の指示を待つ。計画承認を実装開始・main取り込みの承認と扱わない。
