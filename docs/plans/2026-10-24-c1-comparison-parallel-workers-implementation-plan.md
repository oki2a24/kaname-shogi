# C1比較CLI：最大4ワーカー並列化 実装計画

> **状態:** 2026-10-24に本人が計画全体を明示承認。実装・全体検証・再現性pilot・独立レビュー・レビュー記録と利用文書の更新を完了。通常コミットが次段階で、main統合と確認比較条件の選択は別段階。

**目標:** 比較CLIの対局実行を、既定の逐次動作を保ったまま、必要時に最大4プロセスで並行実行できるようにする。固定乱数種による再現性、局別保存、summaryと分析の検証を維持し、既存の256/512手pilotを同条件で再実行して並列経路を確認する。

**対象の本人選択:**

- `--workers` は1〜4。省略時は1で、現行の逐次実行を使う。
- 必要な比較時は `--workers 4` を指定できる。上限は4プロセス。
- 作業場所は `/Users/oki2a24/kaname-shogi`、ブランチは既存の `codex/c1-rook-mobility-evaluation`。

**判断の根拠:** 比較CLIの選択・合法手処理はCPUを使うPython処理で、スレッドはGILのためCPU並列性を十分得にくい。対局ごとに別の予定、乱数種、棋譜、反復記録を持つため、プロセス並列化と相性がよい。一方、保存ファイル・summaryは一つの親プロセスだけが書き、局IDで結果を対応付ける。条件・棋譜・終局・勝敗は同じ入力とソースなら逐次時と一致させ、計時と全体経過時間は一致対象から外す。

**先行測定と所要時間の目安:** 512手pilotは12局を逐次実行して319.985秒（約5分20秒）だった。同じソースで逐次対照と4ワーカーを実行するため、完全な4倍速なら80秒ずつだが、局ごとの時間差・プロセス起動・保存処理がある。逐次約5分20秒と並列約2〜4分を合わせ、pilotは概ね8〜10分を見込む。これは予測であり保証ではない。512手条件の単純比例目安30.2時間は4倍速なら約7.6時間だが、確認比較の必要時間や目標検出力を保証しない。実装・テスト・レビュー・記録には別途およそ4〜7時間を見込む。

## グローバル制約

- C1で既に承認された比較条件、B1評価値、乱数種、局面、対局規則、分析方法を変えない。
- 通常CLIのSFEN入出力、通常CLI/USIへのB1追加、飛車可動性バージョン2、確認比較の組数・手数上限・時間予算は今回の範囲に含めない。
- 既定値1は現在の逐次経路を使い、既存v1/v2 conditionsとsummary v1を保つ。明示的に2〜4を選んだ時だけプロセス並列経路へ入る。
- 並列実行は比較CLIの既存入力方式で利用可能とする。C1の分析に用いるのは従来どおり乱数種一覧方式である。主乱数種方式の分析非対応をこの計画で拡張しない。
- 子プロセスは一局だけ実行して結果を返す。条件・局・summaryのファイル保存、標準出力、進行表示は親だけが担当する。
- 同じ予定から得る結果は予定IDで対応させ、完了順で局ID・種・先後・勝敗をずらさない。保存順そのものは完了順でもよいが、summary内の結果は予定順で安定化する。
- 乱数生成器は現在どおり各局・各方式の保存済み種から独立に初期化する。プロセス間で乱数状態・局面状態を共有しない。
- Python 3.9互換の標準ライブラリ範囲で実装し、外部依存を増やさない。
- `~/.codex/observations/test-driven-development.md` と [検出力・範囲の点検手順](../knowledge/test-coverage-review.md)を適用する。テスト件数を検出力と同一視しない。

## 実行と保存の契約案

### CLI・conditions

- 比較CLIに `--workers N` を加える。Nは整数1〜4、既定値1。0、5、整数でない値、範囲外値は出力先作成・対局開始前に終了コード2で拒否する。
- `ComparisonConfig` の末尾に既定1のワーカー数を追加する。
- 1ワーカーでは現行逐次経路・conditions v1/v2・summary v1の形式を変えない。
- 2〜4ワーカーで実行した新しいconditionsは `kaname-shogi-comparison-conditions-v3` とする。乱数種一覧方式は既存v2の厳密なキーへ `execution` を一つ追加し、主乱数種方式は既存v1の厳密なキーへ同じ `execution` を追加する。`execution` の厳密なキーは `executor` と `workers`、値は `process-pool` と選択数2〜4。分析読込器はv3の種一覧方式だけを分析可能とし、主乱数種方式の分析非対応は従来どおりとする。
- 分析読込器は従来のconditions v2 / summary v1を引き続き受理し、v3ではexecutionの未知キー・欠落・不正値を拒否する。v2読込時はConfigのworkersを1、v3では保存値にする。v3の種一覧実験ではv2と同じ予定・局面・方式・結果照合を行い、v3 conditionsにはsummary v2だけを対応させる。

### 並列スケジューラ・局保存・summary

- 最上位関数を子プロセスのworker入口とし、macOSを含むspawn方式で起動できるようにする。`ProcessPoolExecutor` は最大4プロセスに制限する。
- 同時に親が管理する未回収futureは最大ワーカー数に抑える。完了した局だけを回収して親が保存し、次の予定を投入する。
- 並列中に走行中/回収待ちの仕事数を正しく残すため、summaryは `kaname-shogi-comparison-summary-v2` とし、summary v1の厳密なキーへ `in_flight_games` を追加する。v2の `started_games` は保存済み結果数とin-flight数の和、`ended_games` は保存済み結果数、`unstarted_games` は未投入またはworker開始前の取消しに成功した予定数とし、3項の合計が予定数に一致する。ここでin-flightは親から投入済みでまだ回収しておらず、取消しにも成功していない仕事を指し、キュー待ち・実行中・完了済み未回収を含む。OS上で実際にCPU実行を始めた瞬間までは識別しない。
- 並列summaryは一局保存のたびに親が原子的に更新する。従来summary v1も分析可能なままにする。分析器はv2を厳密に検証し、完了結果ではin-flightが0であることを要求する。
- 子の例外は当該予定のERROR結果へ変換する。ERROR/INTERRUPTEDまたは親のCtrl-C後は新規投入を停止し、未開始のfutureを取消し、投入済みの他局を回収して局別保存する。最後に失敗/中断summaryを保存し、既存の終了コード契約を保つ。
- Ctrl-C時に実行中の子が安全に終了するまで親は待つ。環境によっては子の一局が自然終了するまで応答が遅れる場合がある。強制kill後の中間棋譜復元は実装しない。
- summary・局JSON保存に失敗したら成功を表示せず終了コード1とする。終了時にworkerを回収し、バックグラウンドの対局を残さない。

### 再現性と比較pilot

- 同じPython/ソース/局面/種一覧/上限を逐次と4ワーカーで実行し、局面ID・予定ID・先後・方式別種・棋譜・成功手数・終局理由・勝者・分析得点が一致することを確認する。
- 比較対象の直近512手pilotは同じ6局面×各1組・同じ乱数種一覧。新pilotは独立標本ではなく、並列実行の再現性・時間の確認として扱う。
- 一手計時、バッチ経過時間、conditions SHA、summary/局JSONの全バイト一致は期待しない。conditions v3の実行数、計時値と経過時間は実行ごとに異なる。
- 旧512手結果は `/Users/oki2a24/kaname-shogi/data/comparison/runs/c1-rook-mobility-pilot-512-2026-10-24/`、同じ種一覧は `data/comparison/runs/c1-rook-mobility-pilot-2026-10-24-seeds.json`。新コードの逐次対照と4ワーカーpilotは別々の新しい出力ディレクトリへ保存する。両実行の間でPythonソースを変えず、同一source fingerprintを使う。旧512手結果は過去版との回帰照合に用いるが、新コード内の並列再現性の根拠は逐次対照との比較とする。

## レビューフォーカス

1. 完了順を予定順と取り違え、別局の棋譜・種・先後・勝敗が結び付く。
2. ワーカー上限が4を超える、またはfutureを全予定数分無制限に保持する。
3. 子プロセスが共有Position/RNGを使って局間へ状態を漏らす、または結果ファイルへ直接書く。
4. 並列中のsummaryでin-flightをunstarted/endedへ誤算入し、件数恒等式を崩す。
5. worker例外・Ctrl-C後に新規局を開始する、回収済み結果を落とす、未開始を開始済みとして記録する、またはworkerを残す。
6. 旧conditions v2/summary v1が分析できなくなる、または未知のv3 execution値を受け入れる。
7. 条件・棋譜・勝敗以外の計時差まで再現性の失敗と誤判定する。

## ファイルとタスク

## 各振る舞いに適用するTDDサイクル

タスク1〜4の新規・変更契約は、振る舞いごとに次のRed→Green→Refactorを行う。テスト実装をまとめて先に作ってから製品コードへ進むのではなく、一つの契約で失敗理由を確かめてから最小変更を行う。

1. **Red:** 独立した期待値を持つテストを一つ追加し、対象テストを実行する。実装がない場合はテストをimportできる最小のAPI骨格だけを用意し、契約アサーションが意図した理由で失敗することを確認する。import error、構文エラー、環境エラーだけではRedとしない。既存実装がある契約の初回成功は特性確認として区別する。
2. **Green:** その失敗を直す最小の製品コードだけを実装し、同じテストを再実行して成功を確認する。隣接する失敗契約を先回りして一括実装しない。
3. **Refactor:** Green後に責務・重複・名前・副作用境界を確認する。改善が不要なら「Refactor不要」と理由を記録する。変更する場合は一つの整理に絞り、関係テストを再実行して振る舞いを保つ。
4. **範囲記録:** 各振る舞いについて対象契約・検出対象・独立期待値・専用テストが検出しない誤り・既存関連/全体テストの補完・未検証事項を記録する。Red/Green/Refactorの結果とコマンドも残す。

代表的な並列スケジューラ・保存・件数誤りは、一時コピーへ注入し、狙ったアサーションのFAILを確認する。読み込み失敗やテスト実行失敗を変異検出と扱わず、復元後に対象テストが成功することを確認する。タスク1〜4のRefactor要否確認を終えた後、タスク5で独立レビューを行う。

### タスク 1：ワーカー引数・実行メタデータ

**変更:** `kaname_shogi/comparison.py`、`comparison_io.py`、`compare_games.py`、`comparison_result_io.py`。**テスト:** `tests/test_comparison.py`、`test_comparison_io.py`、`test_compare_games.py`、`test_comparison_result_io.py`。

- [x] CLIで省略時1、1〜4受理、0/5/負数/非整数拒否を個別に検査する。拒否ケースは出力先未作成・worker未呼出しを確認する。
- [x] 1ワーカーのconditions v1/v2はキー・値・formatが従来どおりで、summary v1も従来どおりであることを確認する。
- [x] 2〜4ワーカー時のconditions v3 executionの正確なキー・選択数と、旧v2分析の継続を確認する。未知キー、boolを含む不正整数、1/5、executor不一致を拒否する。
- [x] 既存比較CLI引数と旧 `ComparisonConfig` 呼出しが互換であることを確認する。
- [x] 各契約（引数境界、既定値、conditions版、既存Config互換）を共通TDDサイクルで一件ずつ進める。追加したテストが失敗する理由をケースごとに確認する。

### タスク 2：summaryのin-flight契約

**変更:** `kaname_shogi/comparison.py`、`comparison_io.py`、`comparison_result_io.py`。**テスト:** `tests/test_comparison.py`、`test_comparison_io.py`、`test_comparison_result_io.py`、`test_analyze_comparison.py`。

- [x] 例として予定8局・保存済み2局・in-flight 3局なら、started=5、ended=2、in-flight=3、unstarted=3を独立期待値として固定する。二重計上・脱落を検出する。
- [x] すべて終了時in-flight=0、途中/中断/故障で予定・保存・投入中の恒等式が保たれることを確認する。負値、bool、合計不一致は拒否する。
- [x] summary v1の既存JSONと新summary v2の厳密キー・終局/中断読込を個別確認し、分析器は未完了・in-flightありを受理しない。
- [x] 誤ってin-flightをunstartedへも加える代表変異を隔離コピーで注入し、件数期待値のアサーションが失敗することを確認する。
- [x] 各件数・不正値・旧版互換のテストと最小実装を、共通TDDサイクルで一項目ずつ進める。

### タスク 3：親書込のプロセス並列スケジューラ

**変更:** `kaname_shogi/compare_games.py`。必要になったときだけ小さな並列実行補助を同モジュールへ置く。**テスト:** `tests/test_compare_games.py`、`test_comparison_pipeline.py`。

- [x] 逐次経路の既存保存・中断・故障テストを保つ。worker関数はモジュール最上位に置き、spawnでpickle可能な引数/戻り値だけを受け渡す。
- [x] fake worker/executorによる独立テストで、予定IDと戻り値の対応、完了順の逆転、同時in-flight上限、親だけが局別JSONとsummaryを書くことを確認する。時計やsleepの速さに依存したテストにしない。
- [x] 小さい実プロセス比較を1/2/4ワーカーで行い、条件・局結果・summaryの保存と分析入口を確認する。並列テストはmacOSのspawn境界を通す。
- [x] 一局のERROR、future送出例外、worker内INTERRUPTED、親Ctrl-C、局JSON保存失敗、summary保存失敗を分けて検査する。投入停止、回収、未開始数、終了コード、worker解放、誤った成功表示がないことを照合する。
- [x] 並列と逐次の安定結果（予定/棋譜/終局/勝敗）を同じseedで比較し、計時と実行metadataを比較から除外する。
- [x] 対応付け、上限、親のみ書込、失敗・中断の各契約を共通TDDサイクルで一つずつ実装する。実プロセス確認は単体Red/Greenを補う接続確認として扱う。

### タスク 4：conditions v3・summary v2分析読込と実プロセス接続

**変更:** `kaname_shogi/comparison_result_io.py`、`analyze_comparison.py` は必要最小限。**テスト:** `tests/test_comparison_result_io.py`、`test_analyze_comparison.py`、`test_comparison_pipeline.py`。

- [x] 既存conditions v2/summary v1のC1 fixtureを変更せず読み込み、保存済み512手pilotが引き続き分析できることを確認する。
- [x] conditions v3/summary v2ではexecution worker数・局予定・各局conditions SHA・summary件数・手書き得点を検証する。v3の未対応execution、summary版の組合せ違い、in-flightのあるバッチは拒否する。
- [x] 新規実プロセスpipelineをworkers=2または4で実行し、compare CLI終了コード0、全局JSON、summary、analyze CLIの分析JSONを確認する。
- [x] 実験条件の異なる局JSON差替え、worker metadata改変、並列途中状態を隔離コピーで変異し、各々の意図したassertionで拒否する。
- [x] conditions/summary読込の各新契約を共通TDDサイクルで一つずつ進め、古いv2/v1の初回成功は回帰確認としてRedと区別する。

### タスク 5：4ワーカー再現性pilot・全体検証・独立レビュー・記録

**変更:** 上記コード/テスト、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/learning/c1-rook-mobility-evaluation.md`、必要なら本計画の実績欄。

- [x] Ruff import整理が必要な場合は `.venv/bin/ruff check --select I --fix .`、続いて `.venv/bin/ruff format .`、`.venv/bin/ruff check .` を実行する。unsafe修正は自動適用しない。
- [x] 関連テストと全体テストを実行する。予定コマンドは `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_compare_games.py' -v`、`... -p 'test_comparison_result_io.py' -v`、`... -p 'test_comparison_pipeline.py' -v`、`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py`。共有状態・spawn・並列順序の差が疑われる場合のみ逐次全体も調べる。
- [x] 条件・棋譜・勝敗・計時/時間の契約に対する代表変異を一時コピーへ注入し、狙ったアサーションのFAILと復元後PASSを確認する。少なくとも局ID付替え、workers上限無視、in-flight件数ずれ、v2拒否、失敗後の追加投入を対象にする。
- [x] 新コードを固定し、同じ6局面・同じ6組の乱数種・512手上限をまずworkers=1、その後workers=4で別々の新規出力先へ実行する。両条件のsource fingerprint、予定、棋譜、終局、勝敗、分析得点を照合する。計時値・全体時間・conditions hash・実行metadataは一致対象から外す。さらに旧512手pilotとも棋譜/終局/勝敗を照合し、差の有無を記録する。この再実行は強さの独立標本に加えない。
- [x] pilotが同じ棋譜・結果にならなければ、速度報告より先に原因を調査し、結果の取り違えやworker状態共有を解消する。成功時は実測所要時間・倍率・CPU環境・差異項目を記録する。
- [x] 全対象のrefactor要否確認後、独立コードレビューを行いCritical/Important/Minorを記録する。Critical/Importantは解消・再検証・再レビューし、Minorは対応または理由付きDeferredとする。
- [x] READMEに `--workers` の利用法とCPU/時間・中断限界を必要な範囲で追加し、実装・結果・検出範囲・未検証・レビューを学習記録へ記す。相対リンク・見出しリンク・`git diff --check` を確認し、無関係な未追跡ディレクトリは保持する。
- [ ] 変更対象だけを通常フック付きでコミットする。mainへの統合は別途本人承認後に行う。

## タスク5実施記録（2026-10-24）

- 環境: ブランチ `codex/c1-rook-mobility-evaluation`、開始HEAD `7b2286be5f5b18a77bb4fcb4c96a8ee6412ae672`、Ruff `0.16.10`、`core.hooksPath=.githooks`。
- 整形・静的検査: `.venv/bin/ruff check --select I .`、`.venv/bin/ruff format --check .`（103ファイル整形済み）、`.venv/bin/ruff check .`、`git diff --check` が成功。
- 比較関連検証: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest tests.test_comparison tests.test_comparison_io tests.test_compare_games tests.test_comparison_result_io tests.test_analyze_comparison tests.test_comparison_pipeline -v` → 102 tests / 74.772秒 OK。
- 全体検証: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py` → 821 tests / 55 modules / 73.937秒 OK。
- 代表変異: 局ID付替え、worker上限無視、in-flightの二重計上、既存conditions v2拒否、ERROR後の追加投入を隔離コピーで試し、対象契約のアサーションが各変異を検出した。v2拒否変異は、対象testが明示する `既存conditions v2を読み込めません` のAssertionErrorで再確認し、import/runtime読み込み失敗ではないことを確認。
- pilot: 新コードのworkers=1と4を同じ6局面×各1組・同じ種一覧・512手上限で実行。双方12/12局・2,716手、詰み7・合法手なし5。新コードsource SHA、schedule、全局の安定棋譜・結果、summary集計、分析得点が一致し、旧512手pilotとも安定結果が一致。比較時間は320.167秒と125.555秒（今回一回の約2.55倍）。両結果は候補平均 `[0.5, 0.5]`、95%区間 `[0,1]`、強さの結論なし。CPU/環境差、4倍速保証、独立標本・検出力は示さない。
- 文書: 対象文書の相対Markdownリンク781件とローカル見出し参照を確認し欠落なし。`git diff --check` 成功。`.antigravity/tasks/` と `.venv.backup-2026-10-22/` は無関係な既存未追跡物として保持。
- 初回修正直後時点の記録: 初回独立レビューはCritical 0・Important 1・Minor 1。Importantの親Ctrl-C漏れを3振る舞いのRed→Greenテストで修正し、Ruff、比較CLI27 tests、全体824 tests/55 modulesを再検証した。Minorの主乱数種と分析CLIの非接続はREADME・知識メモへ明記した。当時は追加レビューと通常コミットが未完了で、その後のレビュー・修正・検証は次節に記録する。main統合は別途承認待ち。

### 初回独立レビューとImportant修正（2026-10-24）

初回レビューの結果はCritical 0・Important 1・Minor 1。Importantは、親Ctrl-Cを`wait()`だけで捕捉し、初回/追加submit、局JSON保存、summary保存で漏らすため、中断後の結果・summaryを欠く可能性があるという指摘。Minorは、`--seed`実験を条件v3のため分析可能と誤読しうる知識メモの説明不足だった。

原因は並列経路のKeyboardInterrupt境界がwaitだけに限定され、serial経路の局/summary保存時の中断契約を共有していなかったこと。逐次経路と比較し、初回submit、局JSONwriter、summary writerへ一回限りのKeyboardInterruptを注入する三つの独立テストを追加した。それぞれ現実装で例外漏れが起きてテストがFAILすることを確認後、初回・追加submitの停止とpending取消し、局JSON中断時の結果再保存、summary中断後のworker回収と最終summary保存を実装した。取消し・状態変更は `stop_after_parent_interrupt` へ集約した。

修正後は割込み系を含む `tests.test_compare_games` 27件 / 0.906秒が成功し、全体 `scripts/run_tests_parallel.py` 824件・55 modules / 73.476秒が成功。Ruff format/checkと差分検査も成功した。Minor指摘は、`--seed`の逐次conditions v1/並列conditions v3は比較実行できるが、現readerが受理する独立種一覧conditions v2/v3にはならない、とREADME・知識メモへ明記して対応した。全OSでの実SIGINT配送や複数回連続Ctrl-Cは未検証事項に残す。修正後の独立レビューはこれから行う。

### submit境界とworker SIGINTの再レビュー対応（2026-10-24）

二回目の独立レビューはCritical 0・Important 1・Minor 0。submitの副作用後、Futureを`pending`へ登録する前にSIGINTが届くと、投入済み局を回収できずsummaryで未開始へ誤算入する可能性と、`submit()`から出る`BrokenProcessPool`等がCLI外へ漏れる問題が残っていた。二件目のsubmit中に`signal.raise_signal(SIGINT)`を送り、先行Futureも実行中にしたテストを追加すると、修正前は二件目の局JSONが欠けてFAILした。submit失敗テストは修正前に`BrokenProcessPool`がCLI外へ漏れてERRORとなった。

最小修正では、submitとFutureの予定IDへの登録だけSIGINT handlerを一時保留し、対応付けてから元handlerへ引き渡す。`submit()`が通常例外を送出した予定は、例外を持つ完了Futureにして局のERROR記録へ流し、後続submitを止める。この二振る舞いのRed→Green後、Refactorは不要と判断した。

三回目の独立レビューはCritical 0・Important 1・Minor 1。端末Ctrl-Cはforeground process groupのspawn workerにも届き、初期化後のworkerが実行中局を部分中断する可能性があると指摘された。計画上の自然終了・親回収に合わせ、worker initializer `_ignore_worker_sigint` を設定し、workerは初期化後SIGINTを無視するようにした。Fake executorがinitializerを受け取る接続テストは修正前に期待どおりFAILし、spawn実プロセスのhandlerを読むテストと修正後の比較CLIテスト31件 / 1.071秒は成功した。

最終独立レビューはCritical 0・Important 0・Minor 2。Future未追跡、submit例外漏出、初期化後workerへのSIGINTは解消したと確認された。Minorは (1) worker初期化前の短い起動窓では実端末SIGINTによりworker故障/ERRORとなる可能性、(2) レビュー結果と検証件数が文書に未反映、の二点。二点目はこの節・学習記録・README・知識メモ・再開案内の更新で対応する。一点目は実プロセスグループからのSIGINTを試しておらず、未検証範囲としてREADME・知識メモへ明記する。コード上のCritical/Importantは0件で、レビュー担当は統合可能と判断した。実端末からのSIGINT配送、worker起動窓、複数回連続Ctrl-C、強制終了後の復旧は未検証。

修正後の検証は `tests.test_compare_games` 31件 / 1.071秒、全体 `scripts/run_tests_parallel.py` 828件・55 modules / 73.109秒、Ruff `check --select I --fix`・format・check・format --check、`git diff --check` が成功した。新しいテストは、二件目submitのside effect後SIGINT、submit直接例外、initializer接続、spawn child内のSIGINT dispositionを狙う。`signal.raise_signal`による親内テストとspawn handler確認は、OSが端末Ctrl-Cを各workerへ配送する実動作までは証明しない。

## 検出範囲と未検証事項

- **専用テスト:** workers引数の境界、worker数の上限、予定ID対応、親プロセスだけの書込、in-flightを含むsummary恒等式、workerエラー/中断、conditions/summary旧版互換を検出する。
- **実プロセスpipeline:** spawn・pickle・実ファイル保存・分析器読込をまたぐ接続を確認する。mockだけでは検出できないプロセス境界の失敗を補う。
- **既存全体テスト:** 比較以外の通常CLI、USI、探索、棋譜、千日手処理への回帰を確認する。個々のworkerスケジュールや全OSでのプロセス挙動を証明するものではない。
- **代表変異:** worker数無制限、結果の局ID誤結合、in-flightの誤集計、v2拒否、失敗後の追加投入が意図したアサーションで検出されるかを確認する。
- **再現性pilot:** 同じC1種一覧・新コードの逐次対照と4ワーカー結果が一致するか、旧512手pilotから差がないか、所要時間がこの環境でどう変わるかを確認する。独立な棋力比較・有意性・目標検出力・2,040組の実所要時間は示さない。
- **未検証:** 全OS/Python配布形態でのCtrl-C配送、強制終了・電源断、ディスク満杯時の複数ファイル完全性、workerの強制kill後に棋譜途中を復元する機能、CPU温度/負荷変化を含む性能保証、4倍の速度向上、棋力差。

## 承認後の実施方針

本人の明示承認を受け、作業ブランチ上でTDD、実装、追加pilotを実施した。追加pilotはこの計画内に限る再現性/性能確認であり、確認比較の条件選択や強さ判定には進んでいない。mainへの統合は別途本人承認を得てから行う。

## 計画セルフレビュー

- worker選択から条件保存、実行、局別記録、途中状態、分析互換、既存逐次結果、pilot、学習記録まで依存順に割り当てた。
- ワーカー上限、完了順の不定性、子の例外と親Ctrl-C、summaryのin-flight数、旧条件形式、workerごとの乱数と局面独立性を別契約にした。
- 成功例だけでなく、入力境界、逆順完了、上限超過変異、失敗・中断・保存失敗、旧形式の回帰、未決着pilotの証拠限界を含めた。
- 本人の確認を受け、タスクごとのテスト名一覧だけでなく、各振る舞いにRed→Green→Refactorを適用する明示手順と、import errorをRedと扱わない条件を追記した。
- 計画承認後にタスク1〜5を実施した。TDDの各Red/Green/Refactor、検出範囲、pilot、最終検証を以下の実施記録と学習記録に記す。
