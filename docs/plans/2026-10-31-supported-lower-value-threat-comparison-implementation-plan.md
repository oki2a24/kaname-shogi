# V比較接続・実験 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: 新しい実装セッションで計画をタスクごとに実行する前に、本人の実装計画承認と、合意した新セッションへの引き継ぎ完了を確認してください。実装時は `superpowerssuperpowers:executing-plans` を使用し、各タスクの進捗へ追跡チェックボックスを付けます。

**目標:** 比較CLIだけに `10M+U` と `10M+U+V` を接続し、V典型局面での予備比較と、独立した幅広い局面での確認比較を行えるようにする。

**アーキテクチャ:** 二つの比較policyを既存の一手選択経路へ追加し、同じM/U/V評価器でV係数だけを0/1にする。CLI条件・保存・読込へ重みを固定記録し、独立した二つの局面セットと短いpipeline検証を用意する。通常CLI・USI、探索深さ、他の評価項目は変更しない。

**技術スタック:** Python標準ライブラリ、`unittest`、既存の比較・seed準備・分析CLI、`requirements-dev.txt` 固定版Ruff。

**仕様 (Spec):** [V比較設計案](2026-10-31-supported-lower-value-threat-comparison-design.md)。本人は設計と本計画を2026-10-31に明示承認済み。承認したセッション区切りに従い、引き継ぎをコミットして本人が新セッション用プロンプトを入力するまではTDD・コード・テスト変更を始めない。

## グローバル制約

- 計画と設計は本人が明示承認済み。TDDに入る前にhandoffを作成・コミットし、新セッションで本人が再開プロンプトを入力するまで実装を始めない。
- 実装は `main` ではなく、提案topic branch `codex/supported-lower-value-threat-comparison` で行う。元の `/Users/oki2a24/kaname-shogi` は編集・切替・上書きしない。
- 比較の対照は `PieceThreatWeights(material=10, undefended=1, supported_threat=0)`、候補は同じ値で `supported_threat=1` とする。比較差はV重みだけ。
- 新policyは比較CLI用である。通常CLI・USI、`search_move` の制御付きpolicy、二手・四手探索へ登録しない。
- 通常CLIのSFEN入出力、飛車可動性バージョン2、玉安全度との合成は追加しない。
- 比較時は先後交換二局を一組とし、予備と確認で別々のseed一覧・局面セット・出力先を使う。
- 本人は2026-10-31に予備・確認の両比較を `--workers 4` で行うよう指示した。設計・本計画の承認、比較CLIの接続・検証、条件固定の完了後にこの承認に従って実行する。実行前に `--help` で4 workerが利用可能か確認し、使えなければ他のworker数へ縮退せず停止して報告する。条件を実質変更する場合は再度承認を得る。実行中は約一時間ごとに保存summaryを確認して実測進捗を報告する。
- `.agents/tasks/`、`data/comparison/runs/` の未追跡物、特にC2保護4件を維持する。既存出力を上書き・移動・削除しない。新規保存先は実行前に不存在を確認する。
- テスト設計・レビュー前に `~/.codex/observations/test-driven-development.md` と `docs/knowledge/test-coverage-review.md` を読み、対象契約、検出対象、代表例、単独/全体の検出範囲、未検証を記録する。
- Python変更後は、import変更時の整理、Ruff format/check、`git diff --check`、対象テスト、全体テスト `python3 scripts/run_tests_parallel.py` を行う。フックを回避しない。
- テスト名は英語とし、日本語docstringには確認する振る舞いと検出したい誤りを書く。
- 各タスクでRefactor要否確認後に独立コードレビューを行う。Critical/Importantが解消され再レビューを終えるまで次タスク・記録コミットへ進まない。最後にブランチ全体の独立レビューを行う。main統合とpushは各々別途承認を得る。

## レビューフォーカス

| 優先 | 条件・失敗モード | 対応する検査 |
| --- | --- | --- |
| 1 | V0/V1の重みを逆転する、両方を同じ値にする、またはUを0にする | 固定V局面で両policyの重み・得点・選択差を先後と候補順を反転して確認する。タスク1 |
| 2 | V0でもV1でも同じ評価器を使わない、または一手詰み優先が外れる | 選択器への評価関数・実効重みと、両policyの詰み優先を独立確認する。タスク1 |
| 3 | conditionsの方式名・`supported_threat` が欠落/逆転しreaderが受け入れる | 重み変更・欠落artifactをconditions hash再計算後にreaderが拒否する。タスク2 |
| 4 | 対局用policyが通常CLI/USIへ漏れる、または旧artifact/summary順が変わる | CLI/USI選択肢、既存conditions/result読込、未選択policyの時間列を回帰確認する。タスク1・2 |
| 5 | 局面が違法・重複・独立値と不一致、先後交換や未決着分析が誤る | 局面ごとの独立M/U/V値、両セット間の重複、短いworker4 pipelineの予定・分析を照合する。タスク3 |

## ファイル構成

**製品コード:**

- 変更 `kaname_shogi/movegen.py`: policy enumとV0/V1から同一M/U/V評価器への配線。
- 変更 `kaname_shogi/game_search.py`: 通常の一手選択経路だけに二policyを許可。制御付き・USI経路は変更しない。
- 変更 `kaname_shogi/comparison.py`: 安定方式名と、選択したV policyだけのsummary計時。
- 変更 `kaname_shogi/comparison_io.py`: 比較CLI方式名、重み条件の保存。
- 変更 `kaname_shogi/comparison_result_io.py`: 新方式の重み照合・summary/result/resume読込。

**テスト:**

- 作成 `tests/test_piece_threat_comparison_policy.py`: V0/V1の重み、独立選択値、先後/候補順、一手詰み優先。
- 変更 `tests/test_cli.py`、`tests/test_usi_engine.py`、`tests/test_game_search.py`: 新方式が通常CLI/USIや制御付き探索に漏れないこと。
- 作成 `tests/test_piece_threat_comparison_io.py`: CLI方式、conditions重み、旧形式との互換。
- 作成 `tests/test_piece_threat_comparison_results.py`: readerの重み検査、summary、再開。
- 作成 `tests/test_piece_threat_comparison_positions.py`: 予備/確認セットのM/U/V独立値・合法性・重複・手番配分。
- 作成 `tests/test_piece_threat_comparison_pipeline.py`: 一時ディレクトリ内のseed→比較→分析の短い再現可能pipeline。
- 既存 `tests/test_cli.py`、`tests/test_usi_engine.py`、選択器・比較artifact・resume関連テストを実行する。

**比較データ・記録:**

- 作成 `data/comparison/supported-piece-threat-pilot-positions-v1.json`。
- 作成 `data/comparison/supported-piece-threat-confirmation-positions-v1.json`。
- 変更 `README.md`、`docs/knowledge/supported-piece-lower-value-threat.md`、`docs/knowledge/search-comparison.md`。
- 変更 `docs/learning/supported-piece-lower-value-threat.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/roadmap-non-material-position-evaluation.md`。
- 比較seed一覧・対局・分析は実行承認後、設計書記載の専用 `data/comparison/runs/supported-piece-threat-*` パスへ保存する。

## 実行前ゲート：承認後のhandoff

- [ ] 設計と本計画の明示承認を記録する。統計条件はC1を参考にしたアシスタント提案で、ユーザー選択済みとは扱わない。
- [ ] 現在のmain HEAD・dirty状態・保護対象を再確認し、作業ブランチを用意する。branch作成・切替で保護対象を動かさない。
- [ ] `superpowerssuperpowers:session-handoff` を使い、`docs/handover-supported-lower-value-threat-comparison.md` と `docs/resume.md` にGit状態、承認内容、次に読むファイル、未開始事項、再開プロンプトを記録する。
- [ ] 設計・計画・handoffの文書を確認し、リンクと差分を検査して専用ファイルだけコミットする。今回のhandoffコミットはmainへ統合・pushしない。
- [ ] 再開用プロンプトを本人へ提示し、本人が新しいセッションへ入力するまでTDD・コード・テスト変更を始めない。

新セッションで最初に `git status --short --branch`、`git branch --show-current`、`git rev-parse main`、`git rev-parse HEAD` を確認する。開発環境は `.venv/bin/ruff --version` と `git config --local --get core.hooksPath` を確認し、不足・不一致はREADMEの手順で整える。グローバル環境・Git設定・既存hookを変更しない。

## タスク

### タスク1：V0/V1の比較policyを同一一手選択経路へ接続する

**ファイル:** `kaname_shogi/movegen.py`、`kaname_shogi/game_search.py`、`kaname_shogi/comparison.py`、`tests/test_piece_threat_comparison_policy.py`、`tests/test_cli.py`、`tests/test_usi_engine.py`、`tests/test_game_search.py`。

**生産するpolicy:**

- `MoveSelectionPolicy.MATERIAL_PIECE_THREAT_V0` → `PieceThreatWeights(material=10, undefended=1, supported_threat=0)`。
- `MoveSelectionPolicy.MATERIAL_PIECE_THREAT_V1` → `PieceThreatWeights(material=10, undefended=1, supported_threat=1)`。
- 比較CLI識別子は `material-piece-threat-v0` と `material-piece-threat-v1`。
- 両方とも `partial(evaluate_material_piece_threat, weights=...)` を `choose_one_ply_move` へ渡す。`game_search._ONE_PLY_POLICIES` と `movegen.choose_move` に限って通す。

- [ ] **ステップ0: baselineと開始前条件を確認**

  先に全体テスト `python3 scripts/run_tests_parallel.py` を実行し、結果をコード変更前のbaselineとして記録する。失敗があれば既存成功と決めつけず、原因・影響を調べてから進む。`.agents/tasks/` と `data/comparison/runs/` の保護対象は一覧と現状を記録するだけにし、移動・上書き・削除しない。

- [ ] **ステップ1: 固定局面のpolicy振る舞いテストを作成**

  `supported_piece_threat_support` の独立V局面と `undefended_piece_support.mate_case` を使い、以下を確認する。

  - `test_v_comparison_policies_use_exact_weights`: 先後両方でV0/V1の実効重みがそれぞれ10/1/0と10/1/1。
  - `test_v_weight_changes_choice_only_for_v_different_candidates`: V設計Aの逃げ手/維持手でV0は同点、V1は独立得点どおり逃げ手を優先し、候補順反転でも結果が同じ。
  - `test_v_comparison_policies_prioritize_one_ply_mate`: 巨大な通常点を与えても両policyが先後両方の一手詰みを優先する。
  - `test_unselected_v_policies_keep_legacy_summary_timing_order`: 旧方式選択時にV未選択policyの計時列が混ざらない。
  - 既存 `tests/test_cli.py` に `test_comparison_only_v_policies_are_not_cli_choices`、`tests/test_usi_engine.py` に `test_comparison_only_v_policies_are_not_usi_options`、`tests/test_game_search.py` に `test_search_move_rejects_comparison_only_v_policy` を追加し、比較専用の境界を確認する。

- [ ] **ステップ2: 対象テストで意図したRedを確認**

  実行: `PYTHONPATH=tests .venv/bin/python3 -m unittest tests.test_piece_threat_comparison_policy -v`。

  期待: 新policyの未登録またはV0/V1の重み/選択assertionが失敗する。import error、読み込み失敗、テスト名だけの失敗ではRed完了としない。

- [ ] **ステップ3: 最小policy配線を実装**

  `MoveSelectionPolicy`へ二値を追加し、既存一手選択器を再利用する。`_CONTROLLED_ONE_PLY_POLICIES`、通常CLIの選択肢、USI方式、探索policyには加えない。比較計時は選択した新policyのみ追加する。

- [ ] **ステップ4: 対象テストでGreenを確認**

  実行: `PYTHONPATH=tests .venv/bin/python3 -m unittest tests.test_piece_threat_comparison_policy tests.test_piece_threat_selection tests.test_one_ply_selection -v`。

- [ ] **ステップ5: Refactor要否を確認**

  玉安全度/Uの重み配線と比較し、新しい重複が実際に発生したか確認する。未決定の一般評価policy抽象化は追加しない。

- [ ] **ステップ6: このタスクの独立コードレビュー**

  policyのV0/V1差、一手詰み、通常CLI/USI・制御付き経路の境界をレビュー対象にする。Critical/Importantがあれば修正・対象テスト・再レビュー後にタスク2へ進む。

### タスク2：比較CLIのconditions・保存・読込へ接続する

**ファイル:** `kaname_shogi/comparison_io.py`、`kaname_shogi/comparison_result_io.py`、`tests/test_piece_threat_comparison_io.py`、`tests/test_piece_threat_comparison_results.py`。

**conditions実効値:**

```json
{
  "baseline": {"material": 10, "undefended": 1, "supported_threat": 0, "mate_priority": true},
  "candidate": {"material": 10, "undefended": 1, "supported_threat": 1, "mate_priority": true}
}
```

- [ ] **ステップ1: 条件・artifact契約テストを作成**

  - `test_cli_maps_v_zero_and_v_one_to_distinct_policies`: 二識別子がそれぞれ正しいpolicyへ対応する。
  - `test_seed_list_conditions_store_exact_v_weights_and_workers`: seed-list conditionsに両重み、方式名、workers=4、seed一覧hashが保存される。
  - `test_reader_rejects_missing_or_swapped_v_weight`: `supported_threat`を欠落/交換しconditions hashを更新した条件を拒否する。
  - `test_legacy_undefended_conditions_remain_readable`: Vなしの既存U artifactを従来どおり読み込む。
  - `test_resume_keeps_completed_v_comparison_games`: 同一条件のresumeで完了済み局を再実行しない。

- [ ] **ステップ2: 対象テストで意図したRedを確認**

  実行: `PYTHONPATH=tests .venv/bin/python3 -m unittest tests.test_piece_threat_comparison_io tests.test_piece_threat_comparison_results -v`。

  期待: 新識別子の未登録または実効V重みを照合するassertionが失敗する。読み込みエラーだけをRedと数えない。

- [ ] **ステップ3: writer/readerへ最小対応を追加**

  `comparison_io._POLICIES` と `_policy_parameters` を重み対応表の正本にし、conditions保存の対象policy集合、`comparison_result_io` の固定重み検証・許可policy・summary時刻読込へ接続する。旧conditions/summary/analysis形式と旧policy順は維持する。

- [ ] **ステップ4: 対象・既存artifactテストを実行**

  実行: `PYTHONPATH=tests .venv/bin/python3 -m unittest tests.test_piece_threat_comparison_io tests.test_piece_threat_comparison_results tests.test_comparison_io tests.test_comparison_result_io tests.test_comparison_resume -v`。

- [ ] **ステップ5: Refactor要否を確認**

  writer/reader間で方式・重みを二重定義していないこと、V未選択のsummary順と既存artifact互換が保たれることを確認する。

- [ ] **ステップ6: このタスクの独立コードレビュー**

  条件ハッシュ、実効重み、旧artifact互換、resume保持をレビュー対象にする。Critical/Importantがあれば修正・関連テスト・再レビュー後にタスク3へ進む。

### タスク3：二種類の局面セットと短いpipelineを用意する

**ファイル:** 二つの `data/comparison/supported-piece-threat-*-positions-v1.json`、`tests/test_piece_threat_comparison_positions.py`、`tests/test_piece_threat_comparison_pipeline.py`。

- [ ] **ステップ1: 予備・確認局面の独立期待値テストを作成**

  - `test_pilot_positions_match_hand_calculated_muv`: V典型5局面のM/U/V差、手番、対象駒の内訳を設計値と照合する。
  - `test_confirmation_positions_are_distinct_and_cover_both_sides`: 幅広い新規6局面の手番3/3、重複なし、予備との局面重複なし、設計済み範囲を照合する。
  - `test_seed_compare_and_analyze_keep_v_policies`: 一時ディレクトリで小規模seed-list比較を実行し、条件・棋譜・summary・analysisのpolicyと重み、先後交換、候補得点範囲を照合する。同じseedの再実行で決定的な棋譜を確認する。

  setup_movesは平手からの合法列とし、各局面のM/U/V期待値は定義から手計算する。確認用の具体6局面を比較前に固定し、結果を見た入替を禁止する。

- [ ] **ステップ2: 未接続の局面・pipeline契約をRedで確認**

  実行: `PYTHONPATH=tests .venv/bin/python3 -m unittest tests.test_piece_threat_comparison_positions tests.test_piece_threat_comparison_pipeline -v`。

  期待: 新しい局面セットまたは新policyの未対応が意図したassertionで失敗する。テスト読み込みエラーはRed完了としない。

- [ ] **ステップ3: 局面セットと一時出力pipelineを実装**

  5件と6件のセットを追加する。pipelineは `prepare_comparison_seeds`、`compare_games`、`analyze_comparison` の公開CLI契約を使い、各局面1組、`--max-plies 1`、`--workers 4` の短い検証条件で一時ディレクトリへ出す。実行用runs配下へ出力しない。

- [ ] **ステップ4: 対象pipelineテストでGreenを確認**

  実行: `PYTHONPATH=tests .venv/bin/python3 -m unittest tests.test_piece_threat_comparison_positions tests.test_piece_threat_comparison_pipeline -v`。

- [ ] **ステップ5: Refactor要否を確認**

  既存の位置reader・種準備・比較/分析CLI test supportを再利用し、無関係な共有fixtureやproductionデータを変更しない。

- [ ] **ステップ6: このタスクの独立コードレビュー**

  独立期待値、合法な初期局面列、二セットの非重複、先後交換、短いpipelineの保存/分析をレビュー対象にする。Critical/Importantがあれば修正・関連テスト・再レビュー後にタスク4へ進む。

### タスク4：検出範囲・全体検証・レビュー・記録を完了する

- [ ] **ステップ1: 代表的な誤実装を隔離コピーで変異検査**

  V重みを0/1で反転、両方0、候補のU係数変更、詰み優先迂回、conditions V重み欠落、summary policy漏れ、局面V期待値の誤り、先後割当の反転を一つずつ試す。各々が狙ったassertionで失敗し、復元後成功することを記録する。読込/構文エラーは検出成功と扱わない。C2成果物、元checkout、`.git`は隔離コピーへ含めない。

- [ ] **ステップ2: Ruff・差分・関連テストを実行**

  import変更時のみ `.venv/bin/ruff check --select I --fix .` を行い、続けて `.venv/bin/ruff format .`、`.venv/bin/ruff check .`、`git diff --check`、差分確認を行う。関連群はタスク1〜3の新規テスト、`test_cli`、`test_usi_engine`、`test_game_search`、比較IO/result/resume/analysis/seed準備の既存テスト。

- [ ] **ステップ3: 全体テストを実行**

  実行: `python3 scripts/run_tests_parallel.py`。全発見モジュールの成否と実行数を記録する。失敗があれば解消後に影響範囲と全体テストを再実行する。

- [ ] **ステップ4: Refactorの有無にかかわらず独立レビュー**

  `.agents/tasks/` や保護対象runsへ触れない独立レビュアーに、Critical/Important/Minor、テストの検出範囲、未検証を分けて報告してもらう。Critical/Importantを修正し、対象テスト・全体テスト・再レビューを行う。

- [ ] **ステップ5: 実績記録と限定コミット**

  実際に行った変更、コマンド、検証結果、レビューの重大度と対応、未検証をV学習記録へ記す。documentation guideに従い索引・現在地を更新し、相対リンクと `git diff --check` を確認して対象ファイルだけをコミットする。main統合・pushは行わない。

### タスク5：実装検証後、承認済み条件で予備比較と確認比較を実行する

本人は2026-10-31に、予備・確認の両比較をworker 4で行うよう指示済みである。このタスクは設計・実装計画の承認と実装検証後に行う。実行時のCLI `--help` と出力パスの不存在を再確認し、承認された条件を変更する場合は再承認を得る。

- [ ] **ステップ1: 予備比較だけを実行**

  実行前に両局面JSONと独立M/U/V期待値、局面選定理由、比較条件を点検する。出力先・seed一覧の新規パスを確認し、承認済み条件からの差がないことを照合する。

  条件案: V典型5局面、各10組（50組・100局）、`--max-plies 1024`、独立 `purpose=pilot` seed一覧、`--workers 4`。現在の比較CLIは1〜4 workerを受け付ける。結果は参考に限り、確認比較へ加算しない。完了局数・組数・残数・未決着・時間を保存summaryから約一時間ごとに報告する。

- [ ] **ステップ2: 予備結果を提示し、確認条件を固定**

  所要時間・未決着率・失敗を提示する。予備後に確認用の一局手数上限を最終固定する。承認済み初期案から手数上限・規模などを実質変更する必要があれば、確認比較を開始する前に設計差分と新条件を示して本人承認を得る。得点を理由に確認セットを入れ替えない。

- [ ] **ステップ3: 承認済み条件を凍結して独立確認比較を実行**

  本人が承認した初期案は6局面各340組、計2040組・4080局、`purpose=confirmation` の独立seed一覧、`--max-plies 1024`、`--workers 4`。統計条件は互角境界50％、目標効果55％、信頼水準95％、検出力80％で、未決着なしのHoeffding十分条件が2035組超となるため2040組へ切り上げる。予備後に手数上限を含む実効条件を凍結する。変更承認が必要な場合は得てから実行する。

- [ ] **ステップ4: 分析・採否材料と実行記録を残す**

  独立分析CLIでconditions・全棋譜・summaryを検証する。全体得点区間、未決着を含む幅、局面別/先後別の記述値、計時、結論の適用範囲を示す。一般棋力向上と呼ばず、採用・修正・保留の判断は本人へ委ねる。実行成果物は新規固有パスへ保存し、C2保護対象へ触れない。

## 計画作成時のセルフレビュー

- 設計の比較差・接続範囲・承認済み統計条件・実行前の検証ゲートを各タスクへ対応させた。
- テスト名、インターフェース、公開CLIと非公開経路、既存artifact互換の責務を明記した。
- `--max-plies 1` のpipelineを長時間比較と混同せず、一時出力へ限定した。
- 比較の統計条件は本人承認済み。正確な `setup_moves` とM/U/V期待値は実装計画に従って作成し、比較前に独立検査して固定する。これらの作成は承認済み作業の範囲内である。
- 本計画の実装方式はネイティブ実行（依存順の強い接続変更を一人が連続して行い、必須の独立レビューを別途通す）。本人は本計画全体を2026-10-31に明示承認したため、この実装方式を含めて承認済み。実装・検証後は計画どおり独立レビューを行う。
