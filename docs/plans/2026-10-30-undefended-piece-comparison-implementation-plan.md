# 駒の連携評価の接続・比較 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、`superpowerssuperpowers:executing-plans` を使用してください。各タスクの進捗には追跡用チェックボックスを使用します。

**目標:** 比較CLIに連携評価Uの重み0/1を同じ一手選択経路で追加し、独立したpilotとconfirmationで差を調べる。

**アーキテクチャ:** 既存の `MoveSelectionPolicy` と比較CLIの方式対応に二方式を加え、どちらもB段階の評価関数と `choose_one_ply_move` を使う。新規局面セット、seed一覧、比較結果、分析を既存CLI契約へ接続する。通常CLI・USIの選択肢、二手・四手探索、他の評価項目は変更しない。

**技術スタック:** Python 3.9以上、標準ライブラリ、`unittest`、既存の比較・分析CLI、固定版Ruff。

**仕様 (Spec):** [承認済み設計](2026-10-30-undefended-piece-comparison-design.md)

## グローバル制約

- 開発用比較CLIでは基準・候補を先後交換し、一組を二局として扱う。
- CLIのworker数には `--workers` を使い、今回の長時間実験では4を指定する。
- 対局比較では独立seed一覧を使い、pilotとconfirmationの一覧を分ける。
- 比較CLIの方式を通常CLI・USIの利用者向け選択肢へ公開しない。
- 通常CLIのSFEN入出力、飛車可動性バージョン2、玉周辺安全度との合成、二手・四手適用を追加しない。
- C2成果物4件および元の `/Users/oki2a24/kaname-shogi` の作業状態を保持する。clean、reset、switch、削除、上書きを行わない。
- Python変更後はimport整理、Ruff format、Ruff check、差分確認、変更に見合うテストを行う。全体テストは `python3 scripts/run_tests_parallel.py` を使う。
- テスト名は英語、日本語docstringの先頭行に確認する振る舞い、その後に検出したい誤りを書く。
- main統合とpushは、それぞれ別途本人承認を得る。

## レビューフォーカス

| 優先 | 条件・失敗モード | 期待する挙動と所有タスク |
| --- | --- | --- |
| 1 | U重み0/1のpolicyを逆に割り当てる、または両方を同じ重みにする | 固定局面の両方式の独立得点と候補選択を照合する。タスク1・2 |
| 2 | 新方式で一手詰み優先を失う、または通常CLI/USIへ誤って公開する | 両新方式の巨大通常点に対する詰み優先を確認し、既存CLI/USIの選択肢テストで公開範囲を保つ。タスク1・4 |
| 3 | conditionsの評価重みや方式名が欠落・逆転し、分析readerが誤った条件を受け入れる | weightsを改変してconditions hashを更新したartifactをreaderが拒否する。タスク2 |
| 4 | 先後交換・候補勝者・方式別計時・得点区間の対応を誤る | 小規模pipelineで両先後の予定、保存名、summary、分析結果を照合する。タスク2・3 |
| 5 | 既存成果物の互換や `--resume` が壊れる、C2出力を再利用・上書きする | 旧artifactの既存検査と新方式の再開検査を通し、実比較前に全出力先の不存在を確認する。タスク2・5 |

## ファイル構成

**製品コード:**

- 変更 `kaname_shogi/movegen.py`: policy値、選択器へのU重み0/1の配線、公開docstring。
- 変更 `kaname_shogi/comparison.py`: 安定方式名、新方式選択時のsummary計時追加。
- 変更 `kaname_shogi/game_search.py`: 一手選択policy whitelistと公開docstring。
- 変更 `kaname_shogi/comparison_io.py`: CLI方式名、conditionsの実効重み。
- 変更 `kaname_shogi/comparison_result_io.py`: summary計時順の維持、新方式の重み検証とsummary/result読込契約。

**テスト:**

- 作成 `tests/test_undefended_piece_policy.py`: 二方式の一手選択、重み、先後、候補順、一手詰み優先。
- 作成 `tests/test_undefended_piece_comparison_io.py`: CLI選択とconditions重み。
- 作成 `tests/test_undefended_piece_comparison_results.py`: 新旧artifact、重み検査、再開。
- 作成 `tests/test_undefended_piece_comparison_positions.py`: 設計局面と独立C/U値。
- 作成 `tests/test_undefended_piece_comparison_pipeline.py`: 種一覧から比較CLI・分析CLIまでの小規模統合。
- 既存 `tests/test_cli.py` と `tests/test_usi_engine.py` を実行し、通常CLI/USIの利用者向け選択肢が変わっていないことを確認する。

**比較・記録:**

- 作成 `data/comparison/undefended-piece-positions-v1.json`。
- 変更 `README.md`: 比較CLIに追加する二方式と使い方。
- 変更 `docs/knowledge/undefended-piece-evaluation.md`、`docs/knowledge/search-comparison.md`: 確定した比較方式と利用契約。
- 変更 `docs/learning/undefended-piece-coordination-evaluation.md`: 実装・検証・レビュー・pilot・confirmationの経緯と限界。
- 変更 `docs/resume.md`、`docs/next-topics.md`、`docs/README.md`: 現在地と索引。
- 実験結果は設計案に記した新規pilot/confirmationパスに保存する。C2の4成果物へ書き込まない。

## タスク

### タスク 1: 二つの比較policyを一手選択へ接続する

**ファイル:**

- 変更 `kaname_shogi/movegen.py`
- 変更 `kaname_shogi/comparison.py`
- 作成 `tests/test_undefended_piece_policy.py`

**インターフェース:**

- 消費: `UndefendedPieceWeights(material: int = 10, undefended: int = 1)` と `evaluate_material_undefended_piece(position, perspective, *, weights)`。
- 生産: `MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE_MATERIAL_ONLY` と `MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE`。`game_search.choose_move(position, moves, policy, rng)` から同じ一手選択器へつなぐ。

- [x] **ステップ0: 作業開始前の状態・開発環境を確認**

  読み取り確認: `git status --short --branch`、`git branch --show-current`、`git rev-parse main`、`git rev-parse HEAD`。topic branch上であること、保護対象のC2成果物4件と他の作業状態を識別し、clean/reset/switchで状態を変えないことを確認する。`.venv/bin/ruff --version` を `requirements-dev.txt` の固定版と照合し、`git config --local --get core.hooksPath` が `.githooks` であることを確認する。不足・不一致時は README の手順で開発環境を整え、既存hookと競合する場合は上書きせず解決してから進む。

- [x] **ステップ1: policy接続を確認するテストを作成**

  - `test_policy_uses_exact_undefended_weights_for_both_sides`: 設計Aの支えあり/なし二候補で、候補は先手・後手とも `[140, 139]`、対照は `[140, 140]` となることを確認する。
  - `test_candidate_prefers_supported_piece_for_both_sides_and_orders`: 先後と候補順を反転しても候補方式は支えを作る合法手を選ぶ。
  - `test_both_policies_prioritize_one_ply_mate`: 先後と候補順の両方で、巨大な通常点より一手詰みを優先する。
  - `test_unselected_undefended_policies_do_not_change_legacy_summary_order`: 未選択の新policyが従来比較のsummary計時へ混入しない。
  - 既存の `tests/undefended_piece_support.py` とB段階の独立期待値を使う。

- [x] **ステップ2: 対象テストで振る舞いのRedを確認**

  実行: `.venv/bin/python3 -m unittest tests.test_undefended_piece_policy -v`

  期待: policy名の未接続・未知方針として失敗する。import失敗やテスト読み込み失敗だけでRed完了としない。

- [x] **ステップ3: 最小配線を実装**

  `movegen.py` に二つのpolicy値を加え、game_search.py の一手方式一覧と公開docstringへ登録し、両方を既存 `choose_one_ply_move` へ渡す。baselineは `UndefendedPieceWeights(material=10, undefended=0)`、candidateは `UndefendedPieceWeights(material=10, undefended=1)` を使う。`comparison.py` に安定名を追加し、新方式を選んだ場合だけsummary計時へ追加する。 `comparison_result_io.py` は未選択の新policyをsummary順へ混入させず、旧summaryの列挙順を保つ。既存の列挙順とsummaryの旧方式順は変えない。

- [x] **ステップ4: 対象テストでGreenを確認**

  実行: PYTHONPATH=tests `.venv/bin/python3 -m unittest tests.test_undefended_piece_policy tests.test_undefended_piece_selection tests.test_one_ply_selection -v`

  期待: 新policyの固定値・選択結果・詰み優先と既存一手選択検査が成功する。

- [x] **ステップ5: Refactorの要否を確認**

  既存C2の二方式配線と差分を比較し、重複する共通処理が新たに生じたかを確認する。共通化を先取りしない。

### タスク 2: 比較CLIの条件・保存・読込へ接続する

**ファイル:**

- 変更 `kaname_shogi/comparison_io.py`
- 変更 `kaname_shogi/comparison_result_io.py`
- 作成 `tests/test_undefended_piece_comparison_io.py`
- 作成 `tests/test_undefended_piece_comparison_results.py`

**インターフェース:**

- 消費: タスク1の二policyと `_policy_name(policy)`。
- 生産: `--baseline material-undefended-piece-material-only --candidate material-undefended-piece` を含む比較条件。`policy_parameters` はbaseline `{material: 10, undefended: 0, mate_priority: true}`、candidate `{material: 10, undefended: 1, mate_priority: true}`。

- [x] **ステップ1: CLI条件・保存・読込の契約テストを作成**

  - `test_comparison_cli_accepts_both_undefended_piece_policies`: 両方式名が正しいenumへ対応する。
  - `test_conditions_save_weights_with_seed_list_and_four_workers`: conditions v3に方式名、10/0と10/1、worker 4、seed一覧参照が保存される。
  - `test_conditions_save_parameters_when_only_one_side_uses_undefended_policy`: 片側だけの新方式でもその側の実効重みが保存される。
  - `test_sequential_conditions_save_weights_for_undefended_policy`: seed一覧なしの逐次conditions v1でも新方式の実効重みを保存する。
  - `test_reader_rejects_swapped_or_missing_undefended_weights`: 重みを改変しconditions hashを再計算したartifactをreaderが拒否する。
  - `test_resume_keeps_completed_undefended_piece_games`: 同一条件のresumeで完成局を保持し、完了局を再実行しない。

- [x] **ステップ2: 対象テストで振る舞いのRedを確認**

  実行: `PYTHONPATH=tests .venv/bin/python3 -m unittest tests.test_undefended_piece_comparison_io tests.test_undefended_piece_comparison_results -v`

  期待: 新方式名の条件受理または重み保存が意図したassertionで失敗する。逐次seed経路は重み条件を外した一時変異で、重み欠落のassertion failureを確認する。読み込みエラーだけをRedと数えない。

- [x] **ステップ3: CLIとartifactの最小対応を実装**

  `comparison_io.py` にCLI識別子と実効重みを追加し、baseline/candidateの片側だけが新方式の場合も実効値を保存する。`comparison_result_io.py` の許可policy・固定重み検証・summary時間読込に二方式を加える。新旧conditions、summary、analysisの既存形式を維持する。

- [x] **ステップ4: 対象テストと既存artifact回帰を確認**

  実行: `PYTHONPATH=tests .venv/bin/python3 -m unittest tests.test_undefended_piece_comparison_io tests.test_undefended_piece_comparison_results tests.test_comparison_io tests.test_comparison_result_io tests.test_comparison_resume -v`

  期待: 新方式のconditions・保存・resume検証と既存方式のartifact読込が成功する。

- [x] **ステップ5: Refactorの要否を確認**

  `policy_parameters` はseed一覧条件で両方式を保存し、逐次conditionsは該当policy使用時だけ追加する。result readerの方式名・固定重みは `comparison_io` の既存対応表へ委譲するため二重管理しない。通常方式の旧条件形式へ新規必須キーを加えていないことを確認する。

### タスク 3: 独立局面セットと小規模pipelineを追加する

**ファイル:**

- 作成 `data/comparison/undefended-piece-positions-v1.json`
- 作成 `tests/test_undefended_piece_comparison_positions.py`
- 作成 `tests/test_undefended_piece_comparison_pipeline.py`

**インターフェース:**

- 消費: 比較CLIの `kaname-shogi-comparison-positions-v1`、seed一覧conditions v3、タスク2の二方式。
- 生産: 5局面の固定JSONセットと、同じ入力で再現可能な短いseed-list比較pipeline。

- [x] **ステップ1: 局面期待値・pipelineテストを作成**

  - `test_positions_match_hand_calculated_undefended_counts`: 設計書の5局面が独立C値・U値と一致し、重複局面がない。
  - `test_seed_compare_and_analyze_keep_undefended_policies`: 5局面各1組のseed-list・worker 4・手数上限1で比較・分析を同一seed一覧から2回行い、条件JSON、局別policy、summary、analysis、決定的な棋譜内容が一致する。
  - 確認比較の組数・手数上限を使わない。seed・比較・分析の出力は一時ディレクトリへ保存し、実時間計測値は再現性fingerprintから除く。

- [x] **ステップ2: 新局面・pipelineテストでRedを確認**

  実行: `PYTHONPATH=tests .venv/bin/python3 -m unittest tests.test_undefended_piece_comparison_positions tests.test_undefended_piece_comparison_pipeline -v`

  期待: 新しい局面ファイルまたはpolicyを使う小規模pipelineが未接続として失敗する。読み込みエラーだけを契約失敗と扱わない。

- [x] **ステップ3: 局面データと最小pipeline検査を追加**

  設計書の5つのsetup_movesとC/U期待値をJSONへ保存する。pipelineテストは一時ディレクトリ内でprepare_comparison_seeds CLIから1組/局面のseed一覧を作り、同じ一覧をworker4・手数上限1のcompare CLIとanalyze CLIへ2回渡す。

- [x] **ステップ4: 対象テストでGreenを確認**

  実行: `PYTHONPATH=tests .venv/bin/python3 -m unittest tests.test_undefended_piece_comparison_positions tests.test_undefended_piece_comparison_pipeline -v`

  期待: 局面の独立C/U値・手番・重複有無、先後交換、policy名と重み、summaryの方式別計時、analysisの候補先後集計を確認し、同じseedで決定的な棋譜が一致する。実時間計測値は再現性比較から除く。

- [x] **ステップ5: Refactorの要否を確認**

  既存positions reader、seed準備CLI、compare/analyze CLIとC2 pipelineのテスト手法を再利用する。今回の局面データ以外のproductionデータや他テーマのテスト支援を変更しない。

### タスク 4: 検出力・全体検証・独立レビュー・実装記録

**ファイル:**

- 変更 `README.md`
- 変更 `docs/knowledge/undefended-piece-evaluation.md`
- 変更 `docs/knowledge/search-comparison.md`
- 変更 `docs/learning/undefended-piece-coordination-evaluation.md`
- 変更 `docs/README.md`
- 変更 `docs/resume.md`
- 変更 `docs/next-topics.md`
- 変更 `docs/roadmap-non-material-position-evaluation.md`
- 承認済みの設計案 docs/plans/2026-10-30-undefended-piece-comparison-design.md と実装計画 docs/plans/2026-10-30-undefended-piece-comparison-implementation-plan.md。
- コード・テスト差分はタスク1〜3の対象ファイル。

- [x] **ステップ1: 代表的な誤実装を隔離コピーへ入れ、狙ったassertion failureと復元後成功を確認**

  `/private/tmp` の新規コピーへソース・テストだけを複製し、C2成果物、`.git`、元checkoutをコピーしない。以下を一つずつ試す。

  | 変異 | 狙う検査 |
  | --- | --- |
  | baseline/candidateのU重みを交換 | `test_policy_uses_exact_undefended_weights_for_both_sides`、conditions重みテスト |
  | 候補を材料評価またはU重み0へ配線 | 支えあり/なしの候補選択 assertion |
  | 一手詰み優先を外す | `test_both_policies_prioritize_one_ply_mate` |
  | 保存時のweightsキーを落とす・値を逆にする | readerの重み拒否テスト |
  | 新方式をsummary計時policyから落とす | 小規模pipelineのsummary・analysis assertion |

  読込・構文エラーは検出成功と数えない。各変異後は隔離コピーを新規複製から戻し、同じ検査の復元後成功を記録する。

  実績: `/private/tmp/undefended-piece-mutation-4_wy6h2q` で指定5変異を実行した。すべて狙ったassertionが失敗し、復元用の新規コピーは成功した。具体的にはconditionsの重み順、候補U重み0、詰み優先迂回、reader重み検査、summary/analysis計時の各検査で検出した。

- [x] **ステップ2: import・整形・lint・差分検査を行う**

  importを追加・変更した場合は `.venv/bin/ruff check --select I --fix .`、続けて `.venv/bin/ruff format .`、`.venv/bin/ruff check .`、`git diff --check` を実行する。

  実績: 上記4コマンドが成功し、format対象130ファイルは変更なし、Ruff checkと差分検査に指摘はなかった。

- [x] **ステップ3: 関連テストと全体テストを実行**

  実行する関連群: `tests.test_undefended_piece_policy`、`tests.test_undefended_piece_comparison_io`、`tests.test_undefended_piece_comparison_results`、`tests.test_undefended_piece_comparison_positions`、`tests.test_undefended_piece_comparison_pipeline`、`tests.test_undefended_piece_selection`、`tests.test_material_undefended_piece`、`tests.test_undefended_piece`、`tests.test_cli`、`tests.test_usi_engine`、比較CLIのIO・結果読込・resume・analysis関連。

  全体: `python3 scripts/run_tests_parallel.py`

  期待: 全発見モジュールが成功する。テスト失敗があれば意図した条件を解消し、影響する検査と全体テストを再実行する。

  実績: 計画対象を含む関連30モジュール・327件が成功した。`python3 scripts/run_tests_parallel.py` は973件・75モジュールが成功した。全体ログは `/private/tmp/task4-full.log` に保存した。

- [x] **ステップ4: Refactor要否を記録し、独立コードレビューを行う**

  レビュアーへ設計、契約、独立期待値、変異結果、単独/全体検査の範囲、未検証事項を渡す。Critical・Importantは修正し、影響テストと独立レビューを再実施する。重大度をCritical / Important / Minorで記録する。

  実績: Refactorは不要。policy重み表を `comparison_io` に集約し、readerも同じ定義を参照する。独立レビューはCritical 0 / Important 0 / Minor 2で続行可。Minorはconditions docstringの説明不足と設計書の古い承認状態で、Task 4の記録更新時に両方修正する。判断辞退は長時間比較の結果・一般棋力、保護対象C2成果物と `.agents/tasks/` の変更範囲。

- [x] **ステップ5: 利用説明・確定仕様・実装結果を更新**

  READMEに比較CLIの二方式名と重み0/1を記す。通常CLI/USIの選択肢へ公開したと書かない。知識・学習記録・索引・再開案内を更新し、設計の根拠、実変更、検証コマンドと結果、レビュー重大度、実測していない範囲を記録する。相対リンク、見出し参照、更新文書の末尾空白を検査する。

  実績: README、確定知識2件、学習記録、再開案内、次テーマ入口、ロードマップ、docs README、承認済み設計を更新した。対象10文書から辿る相対Markdownリンク848件・見出し参照9件は欠落0件。`git diff --check` は成功。Task 4後の通常コミットと確認はステップ6で記録する。

- [x] **ステップ6: 実装・記録を明示パスだけで通常コミット**

  `git status --short --branch` と差分を確認し、設計案・実装計画を含め、タスク1〜4で変更した個別ファイルだけを指定してstageする。C2成果物4件・他の未追跡ファイルをstageしない。stage後に git diff --cached --check とstaged diffを確認し、通常hookを通してtopic branch上へコミットする。main統合・pushはしない。

  実績: 明示した21ファイルだけをstageし、C2成果物4件と `.agents/tasks/` がindex外であることを確認した。`git diff --cached --check` が成功し、通常hookのRuff整形・checkも成功した。`codex/undefended-piece-evaluation` へ `75dcf81b`（`feat: 比較CLIに駒の連携評価を接続`）をコミットした。main統合・pushは行っていない。

  コミット後検証: Task 4の `task-done` で対象policy・条件保存・artifact reader・resume・analysis・通常CLI/USIテストを実行し、全体 `python3 scripts/run_tests_parallel.py` も再実行した。全973件・75モジュールが21.753秒で成功した。Task完了ledgerは `.superpowers/sdd/2026-10-30-undefended-piece-comparison-implementation-plan/progress.md` に記録した。

### タスク 5: pilot、confirmation、分析を行い結果を記録する

**ファイル:**

- 新規seed一覧、比較ディレクトリ、analysis JSONは設計書で指定した個別の新規パス。
- 変更 `docs/learning/undefended-piece-coordination-evaluation.md`
- 変更 `docs/resume.md`、`docs/next-topics.md`

- [ ] **ステップ1: 比較実行前の条件・保持物を確認**

  C2の保護対象4パスが存在し、今回の成果物として変更されていないことを確認する。設計書にある全ての新規出力パスが未使用であることも確認する。出力先が一つでも既存なら書き込まず、別の日時付きprefixを決めて記録する。

- [ ] **ステップ2: pilot seed一覧を新規生成**

  実行: `.venv/bin/python -m kaname_shogi.prepare_comparison_seeds --positions data/comparison/undefended-piece-positions-v1.json --pairs-per-position 10 --purpose pilot --output data/comparison/runs/undefended-piece-evaluation-pilot-2026-10-30-seeds.json`

  期待: 終了コード0で5局面各10組のpilot seed一覧を新規保存する。失敗時は比較へ進まない。

- [ ] **ステップ3: pilot比較と分析を行う**

  比較: `.venv/bin/python -m kaname_shogi.compare_games --baseline material-undefended-piece-material-only --candidate material-undefended-piece --positions data/comparison/undefended-piece-positions-v1.json --pairs-per-position 10 --seed-list data/comparison/runs/undefended-piece-evaluation-pilot-2026-10-30-seeds.json --max-plies 1024 --workers 4 --output-dir data/comparison/runs/undefended-piece-evaluation-pilot-2026-10-30`

  正常終了後、`.venv/bin/python -m kaname_shogi.analyze_comparison --input-dir data/comparison/runs/undefended-piece-evaluation-pilot-2026-10-30 --output data/comparison/runs/undefended-piece-evaluation-pilot-2026-10-30-analysis.json` を実行する。

  pilot成績は採否・改善判定へ使わない。比較・分析はアシスタントが実行し、おおむね1時間ごとに実ファイルから局数・組数・残数・故障・保存状態を報告する。本人から進捗質問があればその時点の実状態を確認する。

- [ ] **ステップ4: 独立confirmation seed一覧を新規生成**

  実行: `.venv/bin/python -m kaname_shogi.prepare_comparison_seeds --positions data/comparison/undefended-piece-positions-v1.json --pairs-per-position 407 --purpose confirmation --output data/comparison/runs/undefended-piece-evaluation-confirmation-2026-10-30-seeds.json`

  期待: 終了コード0でpilotと独立した5局面各407組、合計2035組のseed一覧を保存する。

- [ ] **ステップ5: confirmation比較と分析を行う**

  比較: `.venv/bin/python -m kaname_shogi.compare_games --baseline material-undefended-piece-material-only --candidate material-undefended-piece --positions data/comparison/undefended-piece-positions-v1.json --pairs-per-position 407 --seed-list data/comparison/runs/undefended-piece-evaluation-confirmation-2026-10-30-seeds.json --max-plies 1024 --workers 4 --output-dir data/comparison/runs/undefended-piece-evaluation-confirmation-2026-10-30`

  正常終了後、`.venv/bin/python -m kaname_shogi.analyze_comparison --input-dir data/comparison/runs/undefended-piece-evaluation-confirmation-2026-10-30 --output data/comparison/runs/undefended-piece-evaluation-confirmation-2026-10-30-analysis.json` を実行する。中断時は同じ条件・seed・出力先を保って `--resume` する。

  区間判定は設計書どおり、改善支持・悪化支持・判断不能を記録する。未決着・双方未裁定はanalysisの上下限に含める。今回の固定局面と条件の結果を一般的な棋力へ拡張しない。

- [ ] **ステップ6: 実測結果と限界を学習・再開案内へ記録**

  seed、条件、局数・組数、終局理由、未決着、経過時間、分析区間、終了コード、出力先、pilot/confirmation独立性、途中再開の有無を実物と照合して記録する。pilotをconfirmへ合算しない。結果JSONを保存し、C2成果物を変更していないことを確認する。

- [ ] **ステップ7: 文書差分・リンクを確認して限定コミット**

  `git diff --check`、相対リンク、見出し参照、更新した文書の重複・履歴を確認する。学習記録・再開案内・ロードマップの対象ファイルだけをstageし、比較出力やC2成果物を含めず通常コミットする。main統合とpushは行わない。

## GREEN条件

- 二方式が重み10/0と10/1で同じ一手選択・詰み優先を使う。
- CLI条件、局別結果、summary、resume、analysisで方式名と実効重みが一貫し、既存artifactの読込を保つ。
- 5局面の合法性と独立C/U値を確認し、少数fixtureのpipelineでworkers4の保存・分析を通す。
- 対象テスト、全体テスト、Ruff、差分、代表変異、独立レビューが完了する。
- 承認条件でpilotと独立confirmationが完了し、結果と範囲を学習記録へ残す。
- topic branchの明示したファイルだけをコミットし、C2成果物4件と元checkoutを保持する。main統合・pushは別途本人承認を得る。

## 計画作成時の自己レビュー

- 設計の全要件はタスク1〜5に対応している。
- 対照/候補の数値、局面列、組数、手数上限、worker、seed目的、分析式、出力先を設計書と相互照合した。
- Red/Greenコマンドは標準 `unittest` と既存 `scripts/run_tests_parallel.py` を使う。比較の `--workers` は4、局面ごとの全体比較テストと混同しない。
- 全局面一般、重み最適性、通常CLI/USI、他の評価との合成、棋力一般化、実行時間保証は未検証であり、GREEN条件へ含めていない。
- 実装方式はこのセッション内で `executing-plans` に従って進め、独立コードレビューを別途行う案とする。
