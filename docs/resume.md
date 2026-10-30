# 学習・開発の再開案内

## 現在地（2026-10-30）

主線「駒得以外の局面評価を一項目ずつ育てる」はC2まで完了。現在の項目「相手の利きがあり、味方の支えがない駒」はA・B段階を終え、ローカルmain統合と取り込み先検証も完了した。本人は2026-10-29にテーマを選んだが、選定理由は未聴取で推測しない。定義・改善仮説・仮重み10/1・公開利き操作の再利用・Bの範囲を個別に了承し、設計全体・実装計画全体・推薦したネイティブ方式も承認済み。A最後の理解確認には`a`、B最後の理解確認には「E=10M+U」と回答し、それぞれ正解・補足とともに記録済み。本人は次の主線段階としてこの評価の接続・比較を選んだ。具体範囲は未設計・未承認で、選定理由は未聴取。長時間比較はアシスタントが実行し、`--workers 4`、約一時間ごとの進捗確認、人間からの進捗質問への応答を希望している。章番号A3等は予約していない。

B段階Task 1〜3（C/U集計、重み付き合成、既存一手選択器への注入）の実装・Task別検証・独立レビューまで完了した。代表変異7件は各々狙ったassertionが失敗し、復元コピーで対象10件または5件が成功した。作業ブランチでの全体961件/70モジュール（21.785秒）、Ruff、最終独立レビュー（Critical 0 / Important 0 / Minor 0）も成功した。本人の「続けて」を受け、作業ブランチ先端 `554cf708` を2026-10-30にローカル `main` へfast-forwardし、統合後の全体961件/70モジュール（21.745秒）が成功した。製品コード追加コミットは `40d79a6c` と `0872aa29`、Task 3の選択器接続テスト・記録コミットは `554cf708`。統合記録コミット `5f961270` も `main` に反映済み。`origin/main` へのpushは未実施で、別途承認待ち。最後の理解確認には本人が正解し、回答・補足を学習記録に保存した。次テーマ「駒の連携評価の接続・比較」は選定済みで、新セッション用引き継ぎを準備する。具体設計・実装はまだ始めない。仕様と経緯は[確定知識](knowledge/undefended-piece-evaluation.md)、[学習記録](learning/undefended-piece-coordination-evaluation.md)、[承認済み設計](plans/2026-10-30-undefended-piece-evaluation-design.md)、[実装計画と実績](plans/2026-10-30-undefended-piece-implementation-plan.md)、開始時の背景は[B開始引き継ぎ](handover-undefended-piece-evaluation-implementation.md)を参照する。

4局面を各509組で比較したC2確認分析は、95%得点区間[0.227, 0.305]で「悪化を支持」。結論は登録4局面の条件に限られ、通常CLI・USI、別局面、別探索条件へ一般化しない。通常CLIのSFEN入出力、飛車可動性バージョン2、二手・四手への適用は保留し、C2へ追加していない。128手と256手のpilotは同一標本の再観察であり、confirmation結果と合算していない。長時間の比較・分析CLIは本人端末で実行済み。

本人承認を受け、2026-10-29に作業worktree `/Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi` で `codex/c2-king-safety-evaluation` をローカル `main` へfast-forwardした。統合コミットは `6ddeae78`。統合先で全943テスト・67モジュール、Ruff整形確認119ファイル、Ruff check、`git diff --check` が成功した。`origin/main` へのpushはしていない。最後の理解確認に本人回答があり、範囲を4局面・今回の探索条件に限る補足とともに[C2学習記録](learning/c2-king-safety-evaluation.md)へ記録した。今回の学習・個別合意は[現テーマの学習記録](learning/undefended-piece-coordination-evaluation.md)に保存した。

2026-10-30のB開始準備時、作業worktreeは`codex/undefended-piece-evaluation`へ切り替えた。切替前の基点はローカルmainのHEAD `bf826066`（作成時点でorigin/mainより20コミット先行）。Pythonは3.15.2、固定Ruffは0.16.10、local hooksPathは`.githooks`。製品変更前baselineは943件・67モジュールが21.826秒で成功した。baseline後、Task 1開始前まで製品コード・テストは未変更だった。

作業worktreeは`/Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi`、作業ブランチは`codex/undefended-piece-evaluation`。次テーマを選ぶ直前のローカル `main` は `087069c7` で、引き継ぎ・現在地更新はB用作業ブランチへ追加コミットする。次テーマ用の新しい作業ブランチはこの現在ブランチから分け、local mainが祖先であることを確認して引き継ぎ記録を含める。作業ブランチ先端 `554cf708` の統合後テストは961件・70モジュール、21.745秒で成功した。その後の文書のみの変更は全体テストを再実行せず、リンクと差分を検査している。`origin/main` へのpushはしていない。C2成果物4件は未追跡のまま保持し、元の`/Users/oki2a24/kaname-shogi`の作業ファイルは変更していない。次テーマは選定済みだが、設計・計画・実装は未着手。詳細は[接続・比較テーマの引き継ぎ](handover-undefended-piece-evaluation-comparison.md)を参照する。

### B2統合時点の実績（履歴・2026-10-28）

B2は承認済み4Taskの実装、検証、Task別・最終独立レビューを終え、2026-10-28にmainへ統合してorigin/mainへpush済み。統合先では全928テスト・62モジュールが25.003秒で成功し、Ruff整形確認・lint・差分検査も成功した。統合前の初回実行は統合用worktreeに `.venv` がなくUSI起動テスト3件が失敗したが、既存環境への一時リンクで8件を再確認してから全体テストを通した。詳細は[B2学習記録](learning/king-safety-design.md)、[確定知識](knowledge/king-safety-evaluation.md)、[承認済み設計](plans/2026-10-28-king-safety-design.md)、[実装計画と実績](plans/2026-10-28-king-safety-implementation-plan.md)を参照する。

### C2作業時点の環境・Git状態（履歴・2026-10-28）

C2作業対象は `/Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi`。開始時は `main` と `origin/main` が同期した `cdd46519` でcleanだった。実装・検証・レビューは作業ブランチ `codex/c2-king-safety-evaluation` で行い、最終全体テストは943件・67モジュールが25.382秒で成功した。別worktreeではREADMEのセットアップスクリプトが対象外として停止したため、専用仮想環境を作り固定版Ruff 0.16.10とhook `.githooks` を確認した。製品変更前baselineは928件・62モジュールが23.349秒で成功した。これらは当時の記録であり、現在のブランチ・状態・検証は冒頭の現在地と[C2後の統合記録](learning/c2-king-safety-evaluation.md)を参照する。元の `/Users/oki2a24/kaname-shogi` は未コミット文書・比較データを保持するため、clean/reset/切替を行わず保護している。B2後の本人回答「少なくとも先手玉の周囲に後手の利きが２つ以上ある状態」と、S=-2が表す差ちょうど2の補足は[学習記録](learning/king-safety-design.md)に記録済み。通常CLIのSFEN入出力と飛車可動性バージョン2は保留し、C2へ自動追加しない。

## C1開始前の状態（履歴）

2026-10-24、主線A1「駒得以外の局面評価を一項目から学び設計する」の飛車可動性について、本人承認済み計画に従うB1実装・検証・記録を作業ブランチで完了し、本人承認後にローカルmainへ統合した。未成飛車の可動性差、名前付き重みによる駒得との合成評価、評価関数を差し替えられる一手選択を個別ファイルへ追加した。詳細は[学習・本人回答・実装・検証記録](learning/rook-mobility-design.md)、[確定知識](knowledge/rook-mobility-evaluation.md)、[承認済み設計](plans/2026-10-24-rook-mobility-design.md)、[実装計画と実績](plans/2026-10-24-rook-mobility-implementation-plan.md)を参照する。

作業場所は `/Users/oki2a24/kaname-shogi`、現在の作業ブランチは `main`。C1引き継ぎ開始時のGit状態と未追跡の保持物は[C1引き継ぎ](handover-c1-rook-mobility-evaluation.md)を参照する。実装コミットは `8f39c9b`、`e9a3d45`、`bc6651b`、統合時点は `06453c9`。統合先で全体テスト729件・48モジュールが14.634秒で成功し、Ruff（90ファイル変更なし）・差分検査・文書リンク790件/アンカー5件（欠落0）も成功した。代表変異7件は意図したassertion failureですべて検出済み。独立コードレビューはCritical 0 / Important 0 / Minor 1、最終文書レビューはCritical 0 / Important 0で追加指摘なし。Minorは異なる手種の兄弟枝を混在させた相互干渉の直接検査がない範囲上の残件として学習記録に残した。pushはしていない。未追跡 `.antigravity/tasks/` と `.venv.backup-2026-10-22/` は保持している。

A1の学習・設計、B1の実装・main統合・統合先検証、最後の理解確認と回答記録まで完了した。本人は次の主線目標C1「飛車可動性を接続して比較評価する」を選定済み。C1の学習・調査・設計はまだ始めておらず、新セッション開始待ちである。接続先、比較条件、判定方法は未決定で、選定は実装承認ではない。再開時は[C1引き継ぎ](handover-c1-rook-mobility-evaluation.md)のプロンプトから始める。 引き継ぎ準備では更新した6文書の相対Markdownリンク792件が欠落0件、`git diff --check`が成功した。文書のみの変更のため製品テストは再実行していない。通常CLIのSFEN入出力と「可動性バージョン2」は別候補として[next-topics](next-topics.md)へ保持する。P2以前の記述は履歴であり、現在の段階は本節と学習記録を正本とする。

## A1開始時の背景（2026-10-23、履歴）

2026-10-22、P1「比較方法と比較用CLIを学び設計する」は設計承認・最後の理解確認・回答記録まで完了済み。[P1学習記録](learning/engine-comparison-design.md)と[承認済み比較設計](plans/2026-10-21-engine-comparison-design.md)を参照する。補助テーマ「千日手ルールを学び設計する」は一次資料・現行コード・将棋ソフト実装を確認し、本人回答と判断理由を[学習記録](learning/repetition-rule-design.md)へ保存した。設計案・実装計画の明示承認を受け、Task 1〜5を作業ブランチ `codex/repetition-rule` で実装・検証・レビュー・記録し、`4080c4a` としてコミットした。本人承認後、`1b69147` からローカルmainへfast-forwardし、統合先 `7985cb9` で全体661件・42モジュール（15.034秒）、Ruff整形確認78ファイル・check、差分検査が成功した。最終独立レビューはCritical 0 / Important 0 / Minor 2（Deferred）。

最後の理解確認と回答記録まで完了した。[千日手テーマの学習記録](learning/repetition-rule-design.md)を参照。本人は2026-10-23にP2比較CLI実装計画全体と、双方連続王手の未裁定を独立結果・集計件数にする仕様調整を「承認する」と明示した。承認済み計画に従って実装し、独立レビュー・修正・全体検証後、別途本人承認を受けてローカルmainへ統合し、統合先検証と最後の理解確認まで完了した。最終独立レビューはCritical 0 / Important 0 / Minor 0。本人はP2完了後に主線の最初の評価項目A1へ戻ると指定した。通常CLIのSFEN入出力は将来の別候補として保持し、P2へ含めない。P2の詳細は[計画・実績](plans/2026-10-22-comparison-cli-implementation-plan.md)と[学習記録](learning/engine-comparison-design.md)、A1の再開背景は[引き継ぎ](handover-a1-non-material-position-evaluation.md)を参照する。

## 今回開始前の背景（2026-10-21時点）

テーマ「ShogiHomeで全幅最大4手とαβ最大4手を実践検証する」は、合意した二局の観察と最後の理解確認まで完了した。実測・証拠・限界と本人の振り返りは[学習記録](learning/shogihome-four-ply-practice-verification.md)にある。元の主線に未完了の帰還目標はない。CLI時計の設計・実装と予定していた観察も派生した補助テーマとして完了した。

本人は次の大テーマ「駒得以外の局面評価を一項目から学び設計する」を選定した。テーマ内で非駒得評価の一項目を選び、学習・設計するところから始める。評価要素、具体設計、実装範囲は未決であり、テーマ選定を設計承認・実装承認と扱わない。今回開始時の背景・再開プロンプトは[引き継ぎ](handover-non-material-position-evaluation.md)、主線と任意候補は[学習ロードマップ](next-topics.md)を参照する。本人の序盤テンポに関する改善仮説は別の任意候補であり、今回の範囲に含めない。

本人の承認を受け、Pythonユニットテストの並列実行を実装・記録したブランチ `codex/parallel-unittest-runner` を2026-10-21にmainへfast-forward統合した（統合先コミット `c89128a`）。統合後に `PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_tests_parallel.py` を実行し、637件・41モジュールが19.843秒で成功した。並列実行は未統合ブランチで別途3回、標準逐次は1回検証済み。READMEに人間向け手順、AGENTS.mdにAI作業者向け通常コマンド・逐次診断条件を記載済み。最後の理解確認では、逐次実行を残す理由として本人が「問題発生時の切り分けのため」と回答し、補足とともに[学習記録](learning/python-unittest-parallel-runner.md)へ記録した。実装・レビュー・各コミットの経緯は同学習記録と[実装計画](plans/2026-10-21-parallel-unittest-runner-implementation-plan.md)にある。main側の未追跡 `.antigravity/tasks/TODO-codex-controlled-iterative-search-command.md` は保持した。

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

## A1開始前に指定した再開手順（履歴）

P2実装コミット `3adbd23` は、本人の別途承認を受け2026-10-23に `e595f8e` からローカルmainへfast-forward統合した。統合先で `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py` が705件・45モジュール（14.548秒）成功し、Ruff整形確認84ファイル・check、`git diff --check` も成功した。pushはしていない。最後の理解確認では、本人が「4回目で千日手ではあるが、続行も可能なため、5回目で終了とするため」と回答し、補足とともに[学習記録](learning/engine-comparison-design.md)へ保存した。本人はP2の後に戻る主線目標をA1と指定済みである。次の新セッションは[A1引き継ぎ](handover-a1-non-material-position-evaluation.md)のプロンプトから始める。引き継ぎ準備開始時の状態は `main`、HEAD `c4cd68b`、`origin/main` より7コミット先行で、既存未追跡 `.antigravity/tasks/` と `.venv.backup-2026-10-22/` を保持していた。再開時にGit状態を再確認する。
