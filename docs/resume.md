# 学習・開発の再開案内

## 現在地

2026-10-20更新。前テーマ「承認済みCLI設計から実装計画を作る」は、その後の明示的な実装指示・main取り込み承認を経て、Task 1〜5の実装・検証・独立レビュー・main統合・取り込み先検証まで完了した。取り込み先の全体テストは623件成功。最後の理解確認の回答と補足は[実施記録](learning/cli-search-time-control-plan.md)へ記録済み。テーマ「時計つき棋譜を短いCLI操作で保存・再読込する」は2026-10-20にランダム方式で一回観察し、指定の棋譜二手と時計を保存・読込・再保存した。保存前後のJSON全体が一致し、本人の回答「保存・読込には時間を消費しない、人間の入力にかかった時間も消費しない」と補足を[学習記録](learning/cli-clocked-record-roundtrip.md)へ記録した。本人は次テーマ候補1「読込失敗時に棋譜と時計を保つ理由を固定例で確認する」を選定済み。これは学習のみで未開始、選定理由は本人に尋ねていない。開始時の背景・再開プロンプトは[新セッション用引き継ぎ](handover-cli-record-load-failure.md)に記録した。新セッションでこの引き継ぎを入力するまで、次テーマの学習・設計・実装は始めない。

作業ディレクトリは`/Users/oki2a24/kaname-shogi`、現在ブランチは`main`。未追跡`.antigravity/tasks/`は開始時からあり保持する。Ruff 0.16.10は固定版と一致し、ローカル`core.hooksPath`は`.githooks`。pushはしていない。

前テーマの観察開始時点のGit状態は[学習記録](learning/cli-clocked-record-roundtrip.md)に記録した。今回の引き継ぎ準備開始時の物理状態は[新テーマ用引き継ぎ](handover-cli-record-load-failure.md)に記録した。前テーマの観察実績、本人回答と補足は学習記録を、次テーマの選定状況は[次テーマ一覧](next-topics.md)を参照する。

仕様の正本は[承認済み設計](plans/2026-10-20-cli-search-time-control-design.md)、本人回答・個別合意は[設計学習記録](learning/cli-search-time-control-design.md)。共通`game_search.search_move`・予算計算・`SearchControl`を再利用し、コンピュータ手の事前詰み/全合法手生成、完了深さ/手の由来表示を追加していない。CLIが時計・返却後時間切れ判定・時計つき保存を担う。USI製品経路、共通探索、予算式、設定値は変更していない。

前テーマの開始背景は[引き継ぎ](handover-cli-clocked-record-roundtrip.md)、観察実績・本人回答・補足は[学習記録](learning/cli-clocked-record-roundtrip.md)に記録した。今回選定したテーマの開始背景は[次テーマ用引き継ぎ](handover-cli-record-load-failure.md)を参照する。

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

新しいセッションで[選定済みテーマの引き継ぎ](handover-cli-record-load-failure.md)を本人が入力するのを待つ。入力後、引き継ぎに書かれた物理状態と現在のGit状態を照合してから、学習のみの固定例を始める。
