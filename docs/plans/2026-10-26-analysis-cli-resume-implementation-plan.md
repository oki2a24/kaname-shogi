# 分析CLIの局単位再開機能：実装計画

> **実装者への指示:** 本計画をタスクごとに実行する際は `superpowerssuperpowers:executing-plans` を使用する。各ステップはチェックボックスで追跡する。

**目標:** 分析CLIが検証完了した局を保存し、同一入力・同一ソースで中断後に未検証局だけを処理できるようにする。

**構成:** 新しい `analysis_resume.py` が排他ロック、manifest、一局ごとの検証済みチェックポイントを管理する。`comparison_result_io.py` は検証済み局を集計に必要な小さな型へ変換し、既存summaryを再構成して照合する。既存比較読込APIは保ち、分析CLIは新しい分析用ローダーを使う。

**技術基盤:** Python 3.14以上、標準ライブラリ、`unittest`、既存のJSON読込・原子的保存・比較条件・棋譜検証コード。

**仕様:** [分析CLIの局単位再開機能：設計案](2026-10-26-analysis-cli-resume-design.md)

## 全体制約

- Python 3.14以上を使い、新しい実行時依存を追加しない。
- 比較入力ディレクトリは読取専用とし、分析JSONは新しいパスへだけ保存する。
- 完成分析JSON v2の項目、95%区間、判定、得点視点を維持する。
- 再開時に、条件・summary・予定・保存済み局入力ハッシュ・分析器Pythonソース指紋を照合する。
- 完了局だけを保存し、処理中局は次回に局頭から検証する。
- 説明、利用手順、学習記録は日本語で書く。
- 長時間のC1実データ分析は本人が端末から実行する。本実装の検証では実験データ4,080局を使わない。
- 比較CLIの速度改善、対局の並列分析、局途中保存、通常CLIのSFEN入出力、飛車可動性バージョン2を今回へ加えない。
- mainへの統合は別の本人承認を得るまで行わない。

## レビュー重点

1. チェックポイント後に保存済み局JSONが変わった場合、古い勝敗を使わず再開を拒否する。
2. summaryが棋譜・計時と不一致の場合、全局のキャッシュがあっても分析JSONを作らない。
3. 一局の検証・チェックポイント保存の途中で割り込まれた場合、その局を完了扱いにしない。
4. 最終JSON保存が失敗・中断しても、既存JSONを上書きせず、完成済み局から再試行できる。
5. 同じ出力先への同時実行・残存ロックで、チェックポイントや完成結果を壊さない。

## 作業開始前

- [ ] `superpowerssuperpowers:using-git-worktrees` を適用し、既存worktree一覧から再利用可能なものがないことを確認する。
- [ ] `codex/c1-analysis-legal-witness` の確認済みHEAD `6fd2dba` からmanaged worktreeを作る。予定場所は `/Users/oki2a24/.codex/worktrees/c1-analysis-resume/kaname-shogi`。worktree内で `git switch -c codex/c1-analysis-resume` を行う。元の `/Users/oki2a24/kaname-shogi` にある未コミット記録・実験データをコピー、変更、削除しない。
- [ ] 新worktreeの `.venv/bin/ruff --version` が `requirements-dev.txt` の固定版と一致し、`git config --local --get core.hooksPath` が `.githooks` であることを確認する。不足時はREADMEの `python3 scripts/setup_dev.py` を使う。
- [ ] `git status --short --branch` とHEADが新ブランチ・クリーンであることを確認してからTDDを開始する。設計書と本計画を新worktreeへ追加する。

## タスク 1：再開CLIの引数と状態境界

**ファイル:**

- 変更：`kaname_shogi/comparison_result_io.py` の `main` と引数parser
- 変更：`tests/test_analyze_comparison.py`
- 作成：`kaname_shogi/analysis_resume.py` の出力隣接チェックポイントパス関数

**インターフェース:**

- `checkpoint_path_for_output(output: Path) -> Path` は `output.name + ".checkpoint"` の隣接ディレクトリを返す。
- CLIは既存の `--input-dir`・`--output` に `--resume` の真偽フラグを追加する。

- [x] **ステップ1：存在しない再開状態のテストを書く**

  `test_resume_requires_existing_checkpoint` を追加する。`--resume` 付きでcheckpointがない場合、終了コード2、標準エラーに「再開用チェックポイントが見つかりません」、完成output不在を期待する。通常起動でcheckpointが既にある場合に拒否する `test_new_run_rejects_existing_checkpoint` も追加し、進捗を黙って消さない契約を固定する。

- [x] **ステップ2：既存実装でRedを確認する**

  実行：`.venv/bin/python -m unittest tests.test_analyze_comparison.AnalyzeComparisonCliTests.test_resume_requires_existing_checkpoint tests.test_analyze_comparison.AnalyzeComparisonCliTests.test_new_run_rejects_existing_checkpoint -v`

  期待：旧parserの `--resume` 未対応または既存checkpoint無視により、指定した診断・出力保護のアサーションが失敗する。import・読込エラーをRedの証拠にしない。

- [x] **ステップ3：引数と事前条件を実装する**

  `main` で `--resume` を解析し、output既存・resume checkpoint不在・通常実行でのcheckpoint既存を、入力エラー2として棋譜読込前に拒否する。

- [x] **ステップ4：対象テストをGreenにする**

  ステップ2と同じコマンドを実行し、両テストが成功することを確認する。通常の新規出力経路と既存分析CLIテストも維持する。

- [x] **ステップ5：Refactor要否を確認し、変更をコミットする**

  parser・path判定の重複がないことを確認し、対象PythonファイルをRuffで整え、差分・テストを確認してこのタスクのファイルだけをコミットする。

## タスク 2：局単位チェックポイントを初回実行で保存

**ファイル:**

- 変更：`kaname_shogi/analysis_resume.py`
- 変更：`kaname_shogi/comparison_result_io.py` の局読込境界と `main`
- 作成：`tests/test_analysis_resume.py`
- 変更：`tests/test_analyze_comparison.py`

**インターフェース:**

- `AnalysisCheckpointStore.create(root: Path, manifest: Mapping[str, object]) -> AnalysisCheckpointStore` は新規checkpointを作る。
- `AnalysisCheckpointStore.read_manifest() -> Mapping[str, object]` はmanifestを形式・checksum検証後に返す。
- `AnalysisCheckpointStore.save_game(game_id: str, payload: Mapping[str, object]) -> None` は完全検証済み一局を同一ディレクトリの原子的JSONで保存する。
- `AnalysisCheckpointStore.load_game(game_id: str) -> Mapping[str, object] | None` は一局記録を読み、形式と記録チェックサムを検証する。
- `AnalysisCheckpointStore.remove() -> None` は成功finalize後のcheckpoint directoryを除去する。
- `analysis_run_lock(output: Path) -> Iterator[None]` は同じ分析outputの同時実行を拒否する。
- `AnalysisInput` は `input_dir: Path`、読込済み `conditions: dict[str, object]` と `summary: dict[str, object]`、各SHA-256、`config: ComparisonConfig`、`schedule: tuple[ScheduledGame, ...]` を保持する。
- `AnalysisGameSummary` は `schedule: ScheduledGame`、`reason: GameEndReason`、`winner_side: Side | None`、`winner_policy: MoveSelectionPolicy | None`、`plies: int`、`move_time_by_policy: tuple[tuple[MoveSelectionPolicy, int, int, int | None], ...]` を保持する。内側の整数は方式ごとの成功手数・計時合計ns・最大計時nsである。棋譜本文や手ごとの時刻配列は保持しない。
- `LoadedAnalysis` は `input: AnalysisInput`、`games: tuple[AnalysisGameSummary, ...]`、再集計済みsummary、`pair_scores: tuple[PairScore, ...]`、予定順の全入力SHA、`elapsed_ns: int` を保持する。
- `prepare_analysis_input(input_dir: Path) -> AnalysisInput` はconditions・summary・予定を読み、SHA-256と期待局ファイル集合を保持する。
- `analysis_checkpoint_manifest(input: AnalysisInput, *, source_root: Path) -> dict[str, object]` は入力識別・schedule・source fingerprintからmanifestを作る。
- `load_analysis_comparison(input: AnalysisInput, *, checkpoint: AnalysisCheckpointStore, source_root: Path) -> LoadedAnalysis` は初回実行で全局を検証して要約し、各局完了後に保存する。
- `summary_payload_for_game_summaries(config: ComparisonConfig, games: Sequence[AnalysisGameSummary], *, elapsed_ns: int, summary_format: str, elapsed_lower_bound: bool) -> dict[str, object]` は既存summary v1/v2/v3と同じ集計値を作る。

- [x] **ステップ1：中断時保存・正常終了後の後始末・ロックをテストする**

  `test_interruption_keeps_only_fully_validated_game_checkpoint` を追加する。2局fixtureで一局目を実際に `_load_game` し、二局目の `_load_game` 開始時に `KeyboardInterrupt` を注入する。終了コード130、最終output不在、一局目の有効なcheckpointあり、二局目のcheckpointなしを期待する。`test_success_removes_checkpoint_after_output_write` では最終output writer呼出し時に完成済みcheckpointが存在し、成功後にoutputがありcheckpointが消えることを確認する。`test_concurrent_analysis_is_rejected` では同じoutputを既にlockした状態でCLIを呼び、入力を処理せず拒否することを確認する。`test_analysis_summary_matches_handwritten_v1_v2_v3` を追加し、現行loaderの出力が手書き二局fixtureの独立期待値と合うことを確認する。この最後のcharacterizationは既存コードで初回Greenと記録する。

- [x] **ステップ2：旧動作でRedを確認する**

  実行：`.venv/bin/python -m unittest tests.test_analyze_comparison.AnalyzeComparisonCliTests.test_interruption_keeps_only_fully_validated_game_checkpoint tests.test_analyze_comparison.AnalyzeComparisonCliTests.test_success_removes_checkpoint_after_output_write tests.test_analyze_comparison.AnalyzeComparisonCliTests.test_concurrent_analysis_is_rejected -v`

  期待：旧CLIは130を返してもcheckpointを作らず、「一局目が残る」という専用アサーションが失敗する。正常保存時のcheckpoint確認と既存lock拒否の専用アサーションも失敗し、import/読込エラーだけには依存しない。

- [x] **ステップ3：manifest・ロック・一局の保存を実装する**

  `analysis_resume.py` に厳密形式版付きmanifest、`analysis_run_lock`、`AnalysisCheckpointStore.create`、`save_game`、チェックポイントパスを実装する。一局記録には元JSON SHA-256、`AnalysisGameSummary`、記録内容のチェックサムを含める。`comparison_result_io.py` に `AnalysisInput`・`LoadedAnalysis`・`prepare_analysis_input`・`load_analysis_comparison` を加える。初回経路はconditions・summary・予定・ソース指紋をmanifestへ記録し、各局が `_load_game` を通過してからcheckpointを保存する。既存の完成分析JSONを作る直前までの検証は維持し、成功後はcheckpointを削除する。

- [x] **ステップ4：RedテストをGreenにし、保存故障を確認する**

  先のテストを再実行する。`test_checkpoint_write_failure_returns_one` を追加し、checkpointの保存失敗は終了コード1、最終output不在、既存checkpointの保護を確認する。書込み例外と入力読込エラーの終了コードを混同しない。

- [x] **ステップ5：checkpoint単体境界を追加してRefactor要否を確認する**

  `tests/test_analysis_resume.py` で通常保存・再読込・重複ID・未知形式・JSON破損・チェックサム不一致・symlink・ロック競合をテストする。ロックの残存は自動除去せず、人がPIDを確認してから解除する。

- [x] **ステップ6：タスク2を検証してコミットする**

  `.venv/bin/python -m unittest tests.test_analysis_resume tests.test_analyze_comparison -v` を実行する。import順、Ruff format/check、`git diff --check` と差分を確認してコミットする。

## タスク 3：中断後に完了局を飛ばして分析を再構成

**ファイル:**

- 変更：`kaname_shogi/analysis_resume.py` のcheckpoint読込・条件照合
- 変更：`kaname_shogi/comparison_result_io.py` の分析用ローダー、summary再集計、分析payload
- 変更：`tests/test_analysis_resume.py`
- 変更：`tests/test_analyze_comparison.py`
- 変更：必要な場合は `tests/test_comparison_result_io.py`

**インターフェース:**

- `AnalysisCheckpointStore.resume(root: Path, expected_manifest: Mapping[str, object]) -> AnalysisCheckpointStore` は形式・条件・summary・schedule・source fingerprintを照合する。
- `AnalysisCheckpointStore.load_game(game_id: str) -> Mapping[str, object] | None` は厳密に検証した局記録を返す。
- `AnalysisCheckpointStore.completed_game_ids() -> frozenset[str]` は予定外・重複・symlinkの局ファイルがないことを確認して完了ID集合を返す。
- `AnalysisCheckpointStore.remove() -> None` は成功finalize後のcheckpoint directoryを除去する。
- `prepare_analysis_input(input_dir: Path) -> AnalysisInput` はconditions・summary・予定を読み、SHA-256と期待局ファイル集合を保持する。
- `load_analysis_comparison(input: AnalysisInput, *, checkpoint: AnalysisCheckpointStore, source_root: Path) -> LoadedAnalysis` は各保存局をハッシュ照合し、checkpointにある局の棋譜再生を省略し、未保存局だけ `_load_game` で検証する。

- [x] **ステップ1：再開・入力一致・summary検証のテストを書く**

  `test_resume_reuses_completed_game_and_matches_fresh_analysis` を追加する。まずタスク2の仕組みで一局目完了後に割り込み、次に `--resume` で完了する。再開時の `_load_game` 呼出しが `game-000002` だけであること、終了コード0、初回中断前からある入力ハッシュ・全分析JSON項目が独立した未中断fixtureと一致することを期待する（`analyzer` 識別だけは除外）。`test_resume_rejects_changed_completed_game_hash` と `test_resume_rejects_changed_conditions_or_summary` は一つずつ入力を変更し、outputを作らず拒否することを確認する。checkpoint破損ケースもこの段階で追加する。タスク2で初回Greenとして確認したsummary v1/v2/v3のcharacterizationも維持する。

- [x] **ステップ2：既存の再開挙動でRedを確認する**

  実行：`.venv/bin/python -m unittest tests.test_analyze_comparison.AnalyzeComparisonCliTests.test_resume_reuses_completed_game_and_matches_fresh_analysis tests.test_analyze_comparison.AnalyzeComparisonCliTests.test_resume_rejects_changed_completed_game_hash tests.test_analyze_comparison.AnalyzeComparisonCliTests.test_resume_rejects_changed_conditions_or_summary -v`

  期待：全面再読込が残っている段階では呼出し一覧に `game-000001` が含まれ、再利用契約のアサーションが失敗する。入力変更・破損を拒否しない場合も専用assertionが失敗する。CLI構文エラーだけをRed確認にしない。

- [x] **ステップ3：保存済み局の再読込と省略を実装する**

  `analysis_resume.py` の `completed_game_ids` で予定外・重複・symlinkの局ファイルがないことを確認する。各局要約をscheduleへ照合し、checkpointの入力SHAと現在の元JSON SHAが一致する局だけを読み戻す。欠落局だけ通常の `_load_game` で検証してcheckpointへ保存する。両経路の `AnalysisGameSummary` 列からsummaryを再構成し、条件・summary・ソース指紋と照合する。pair scoreと局面別/先後別集計は既存の方式視点で再導出し、保存された得点値は使わない。既存 `load_completed_comparison` の戻り値・用途は維持する。

- [x] **ステップ4：再開テストとcharacterizationをGreenに保つ**

  再開テストを再実行する。初回Greenだったsummary characterizationが、cached summary経路でも同じ値を保つことを確認する。手書きfixtureでは基準方式の件数2・合計302ns・最大201ns、候補方式の件数2・合計304ns・最大202nsを期待する。既存分析JSONの統計値・区間・入力SHA不変テストも通す。

- [x] **ステップ5：Refactor要否を点検する**

  既存の全件ローダーと再開ローダーが条件・summary・ゲームID照合を二重実装していないか確認する。共通化は読込境界だけに限り、既存 `load_completed_comparison` の契約を変えない。確認後、対象テストをGreenに保つ。

- [x] **ステップ6：対象検証を行いタスク3をコミットする**

  `.venv/bin/python -m unittest tests.test_analysis_resume tests.test_analyze_comparison tests.test_comparison_result_io -v` を実行し、Ruff import整理・format・check、差分検査を行ってコミットする。

## タスク 4：再開拒否条件・最終化・利用記録を仕上げる

**ファイル:**

- 変更：`kaname_shogi/analysis_resume.py`、`kaname_shogi/comparison_result_io.py`
- 変更：`tests/test_analysis_resume.py`、`tests/test_analyze_comparison.py`
- 変更：`README.md`、`docs/knowledge/search-comparison.md`、`docs/README.md`
- 作成：`docs/learning/c1-analysis-resume.md`
- 変更：設計書と本実装計画へ実績を追記
- `docs/resume.md` は元checkoutにある未コミットC1進捗を上書きしないため、このworktreeでは変更しない。統合承認後に現物を確認し、別途現在地を更新する。

- [x] **ステップ1：最終保存・ソース変更時のテストを追加する**

  `test_interrupted_final_save_can_resume_without_replay` を追加する。全局checkpoint作成後に最終output保存で割り込ませ、二回目は `_load_game` を呼ばずに完成することを確認する。`test_source_change_during_analysis_prevents_final_output` では開始時とfinalize時のソース指紋を変え、終了コード2・output不在・checkpoint保持を確認する。`test_existing_output_is_never_overwritten` はタスク1のテストを再利用する。

- [x] **ステップ2：新しく導入する拒否条件のRedを確認する**

  ソース指紋のfinalize直前照合がまだないため、ソース変更ケースの期待assertionが失敗することを確認する。最終保存割込み後に再開して完了局を再生しない契約で、再開時の再生回数が0でない場合に専用assertionが失敗することを確認する。これらが既にGreenなら初回Greenとして記録し、Redを捏造しない。ファイル読込エラーやimport失敗だけを検出成功に含めない。

- [x] **ステップ3：照合と最終化の境界を最小実装する**

  checkpoint済み局の元JSONハッシュ、manifest、局記録チェックサムを再開前に照合する。再開元summaryと局要約の不一致を拒否する。分析JSONは全局の要約・summary照合・score計算後に `write_new_json` で保存し、保存成功後にcheckpointを削除する。final save失敗・割込みではcheckpointを保持し、再開で再検証せずfinal saveだけ再試行できるようにする。削除に失敗した場合は完成outputを保ち、cleanup警告を表示して成功結果を失敗扱いにしない。ソースfingerprintは開始時とfinalize直前に照合する。

- [x] **ステップ4：TDD GreenとRefactor要否を確認する**

  ステップ1の全テストと既存分析CLIテストを通す。チェックポイント保存失敗は1、入力・条件・形式不正は2、中断は130、完了は0であることを確認する。状態遷移を単純化できるRefactorだけを行い、全対象テストを再実行する。

- [x] **ステップ5：代表的な誤実装を隔離コピーへ注入する**

  元ファイルSHA比較の省略、summary再集計比較の省略、局要約保存の検証前移動、resume時の完了局再生または二重計上を注入する。各変更で対応する意図したassertionがFAILすること、復元後にPASSすることを記録する。

- [x] **ステップ6：独立コードレビューを行う**

  `superpowerssuperpowers:requesting-code-review` を使用して、契約・5件のレビューフォーカス・単独/全体テスト範囲・未検証事項を確認する。Critical/Importantがあれば先に修正し、関連TDDとレビューをやり直す。Minorは対応または理由付き保留を記録する。レビュー完了までは利用文書・コミットへ進まない。

- [x] **ステップ7：利用資料と実施記録を更新する**

  READMEと比較知識メモに初回コマンド、中断時の130、同じパスへ `--resume` を付けて再実行する手順、checkpoint不一致時の削除判断、強制終了後のロック確認を記録する。学習記録に本人承認、対象ファイル、実変更、検証・変異・レビュー結果、未検証範囲を記録し、文書索引を更新する。テストせずに実データ4,080局を分析しない。

- [x] **ステップ8：整形・関連回帰・全体回帰を検証する**

  実行：`.venv/bin/python -m unittest tests.test_analysis_resume tests.test_analyze_comparison tests.test_comparison_result_io -v`。続けて `.venv/bin/python scripts/run_tests_parallel.py`、`.venv/bin/ruff format .`、`.venv/bin/ruff format --check .`、`.venv/bin/ruff check .`、`git diff --check`、変更と文書リンクの確認を行う。importを追加・変更した場合は先に `.venv/bin/ruff check --select I --fix .` を実行し、差分を確認する。テスト全体はすべて成功し、Ruff診断なし、リンク欠落なしを完了条件とする。

- [x] **ステップ9：最終レビュー状態・作業状態を記録しコミットする**

  worktree上の `git status --short --branch` と差分を確認し、この機能のファイルだけをステージ・コミットする。既存の比較結果、他worktree、元checkoutの未コミット内容を含めない。mainまたは元checkoutへ統合せず、コミットSHA・worktree path・検証結果を本人へ示して別途承認を待つ。

## 完了条件

- TDDで初回生成・局単位保存・再開・条件/入力不一致拒否・summary整合・ロック・最終保存再試行を検証している。
- 正常分析結果は小規模独立fixture上で既存JSON v2と一致し、完了局の再生を省略しても全局面・先後別集計とpair scoreが同じである。
- 代表変異が意図したassertionで検出され、全体unittest・Ruff・差分・リンク確認が成功している。
- 独立レビューCritical 0・Important 0、Minorは対応または保留理由が記録されている。
- 利用方法・実施経緯・未検証事項が日本語資料に記録され、元checkoutのユーザーデータとmainは未変更である。

## タスク4の実施結果（2026-10-26）

- `fstat` 直後・初期化・最終cleanupの割込み、完了局summaryの勝者復元、manifest再解析の回避とcache分離をTDDで確認した。各追加テストは対象となる不具合を専用assertionで検出した。
- source SHA省略、summary照合省略、検証前checkpoint保存、cached局再生の4代表変異を隔離コピーに注入し、それぞれ意図したテストが失敗することを確認した。
- 独立レビュー最終状態はCritical 0・Important 0。外部プロセスがfstat前のlock pathを差し替える狭い競合は保証対象外としてコードdocstring・学習記録に明記した。
- 最終検証は関連62件、全体894件/58 modules、Ruff format/check成功、6文書の相対リンク欠落0、`git diff --check` 成功。実データ4,080局は分析していない。
- 作業場所は `/Users/oki2a24/.codex/worktrees/c1-analysis-resume/kaname-shogi`、branch `codex/c1-analysis-resume`。main・元checkoutには未統合。
- 機能・利用資料のコミットは `0fcb157` (`feat: 分析CLIの局単位再開を完成`)。task-doneの関連テスト再実行も62件成功した。main統合は別承認を待つ。
