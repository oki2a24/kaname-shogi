# 学習・開発の再開案内

## 現在地

2026-10-18更新。承認済み[実装計画](plans/2026-10-18-controlled-iterative-search-command-implementation-plan.md)に沿うTask 1〜5、TDD、検出力補強、独立レビュー、理解確認を作業ブランチで完了した後、本人の明示許可を得て`codex/controlled-iterative-search-command`をローカル`main`へfast-forward統合した。統合後のmainでこのターンに全体テスト560件（35.310秒）、`.venv/bin/ruff format --check .`（65ファイル）、`.venv/bin/ruff check .`が成功した。詳細は[作成・承認・実施・統合記録](learning/controlled-iterative-search-command-implementation-plan.md)を参照する。

最後の理解確認は、既に保存済みの本人回答と補足を本人が完了済みと確認した。回答を新たに作らず、[学習記録](learning/controlled-iterative-search-command-implementation-plan.md)の内容を正本とする。本人は次候補1「小さいSFENで開発用コマンドを試し、出力を読む」を選択した。新セッション用の[引き継ぎ](handover-controlled-iterative-search-command-output-reading.md)を準備済みで、本人が再開プロンプトを新セッションへ入力するまで、この次テーマを始めない。

作業場所は`/Users/oki2a24/kaname-shogi`。統合時のmain HEADは`f0f4027`で、作業ブランチの7コミットをfast-forwardした。pushはしていない。統合検証時、`main`は`origin/main`より27コミット先で、未追跡の`.antigravity/tasks/`があったため保持した。その後の引き継ぎ文書コミット分を含む正確なHEADと状態は再開時にGitから確認する。

## 完了した開発用コマンド設計

学習・設計・独立レビュー・本人による[設計全体](plans/2026-10-18-controlled-iterative-search-command-design.md)の明示承認と、最後の理解確認まで完了。[学習記録](learning/controlled-iterative-search-command-design.md)に個別選択・承認・レビュー・初回誤答と再確認正解を区別して保存した。設計承認0e5ea66、理解確認/候補8d29088。独立レビューの初回Minor 1は記録更新で解消、最終Critical/Important/Minorすべて0。

専用コマンドで一回探索。SFEN・上限深さ・目標/上限msは必須。操作セット生成後の探索直前から計時し、探索内部の合法予備手準備を含む。Task 1〜5として入力検査、一回探索接続、四状態表示、`main`・例外境界・実プロセス入口、全体検証を完了。最終専用テスト14/14、関連68/68、全体560/560、Ruff成功。代表変異8件と最終独立ブランチレビューCritical 0 / Important 0 / Minor 0。既存三方式と比較入口を維持し、通常対局・USIへの新方式接続、予算式変更、時間保証は対象外。

計画作成時点では製品テスト未実行だった。その後の実装テスト結果は上記Task 1〜5の今回実測に限る。過去の探索部品546件成功などを今回の実測とは扱わない。実時間性能・期限内応答、SIGINT実プロセス配送、USI競合、全局面/OS、棋力などは未検証。

## 完了した前テーマ

時間制御付き反復深化の計画承認、5段階の実装・検証・各段階と全体の独立レビュー、本人の別承認によるmain統合、取り込み先検証、最後の理解確認まで完了した。[実装計画と結果](plans/2026-10-18-iterative-deepening-stop-time-control-implementation-plan.md)、[学習・実施・本人回答](learning/iterative-deepening-stop-time-control-implementation.md)を参照する。

実装5コミットはca59b63・8d4ced6・73a0264・db31d03・30fe837、最終記録80e3db0まで統合、統合記録04de2ae、回答補足0be1c7a、理解確認と次候補605b0a3。最後の理解確認は初回の抑制時の手の扱いを補足し、再確認回答を記録して完了した。

直近の製品検証は取り込み先80e3db0で全体546件30.083秒OK、Ruff63ファイル整形確認・check、差分検査成功。代表変異11件と独立全体レビューは取り込み前の実績（最終Critical/Important/Minor 0/0/0）。これらを新セッションの実測として流用しない。以降は文書変更だけで、製品テストは再実行していない。過去の設計と反復深化補強の履歴は学習記録と各開始時引き継ぎからたどる。

## 次に読むもの

1. 再開時のGit状態、AGENTS.md、本書、[選定済み次テーマの引き継ぎ](handover-controlled-iterative-search-command-output-reading.md)。
2. ルートREADMEの「時間制御付き反復探索を一回試す」、[承認済みコマンド設計](plans/2026-10-18-controlled-iterative-search-command-design.md)、[探索停止](knowledge/search-stop.md)。
3. [実装計画・結果・本人回答](learning/controlled-iterative-search-command-implementation-plan.md)と、必要なら[実装計画](plans/2026-10-18-controlled-iterative-search-command-implementation-plan.md)、`kaname_shogi/search/run_controlled_iterative.py`、`kaname_shogi/search/result.py`。
4. [文書索引](README.md)、[次テーマ候補](next-topics.md)、[文書更新ガイド](documentation-guide.md)。テストの変更予定はなく、過去の製品テスト成功を今回の出力観察として扱わない。

全局面・全競合・実時間性能・期限内応答・新方式USI競合・実機対局・棋力・最適予算は未検証。過去の引き継ぎの現在地は保存当時の情報として読む。
