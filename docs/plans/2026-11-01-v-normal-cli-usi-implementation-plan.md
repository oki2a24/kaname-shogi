# V通常CLI・USI接続 実装計画

> AIエージェントへの指示: 本計画を実施する場合は、承認後にsuperpowerssuperpowers:executing-plansを起動し、チェック項目を順に進める。実装方法の提案はネイティブ実行である。

**目標:** 比較で使った10M+U+V候補を通常CLIとUSIから選べるようにし、既定Randomと既存探索制御を保つ。

**アーキテクチャ:** 既存のMATERIAL_PIECE_THREAT_V1を通常方針として再利用し、時計・停止制御付きの一手探索へ接続する。CLIは既存の先後別方針設定へ7番を加え、USIはDifficulty値MaterialSupportedPieceThreatを同じ内部方針へ対応させる。

**技術スタック:** Python標準ライブラリ、unittest、固定版Ruff 0.16.10。新規依存なし。

**仕様:** [本人承認済み設計](2026-11-01-v-normal-cli-usi-design.md)。本人は2026-11-01に設計・実装計画全体とネイティブ実行を承認した。

## グローバル制約

- Python変更前にRuff固定版とhook設定を再確認し、不足時はREADMEのsetup手順を使う。グローバル設定や既存hookを上書きしない。
- 開発場所は /private/tmp/kaname-shogi-main-integration-clone の codex/v-supported-threat-normal-cli-usi-connection。元の /Users/oki2a24/kaname-shogi、その作業状態、.agents/tasks/、data/comparison/runs/、C2保護4件を変更・stageしない。
- Randomを既定のまま保ち、V0を通常CLI/USIへ公開しない。比較CLI・比較成果物・Vの定義・重み・二手/四手評価は変更しない。
- main統合とpushは本テーマの別承認まで行わない。
- テスト名は英語、日本語docstringを付ける。振る舞いごとにassertion Redを確認し、読み込みエラーをRedとしない。検出力と範囲は個人観察メモおよび docs/knowledge/test-coverage-review.md に従う。
- Python差分はimport整理、Ruff format/check、差分確認、関連テスト、全体テストの順に検証し、Refactor要否確認後に独立レビューする。

## レビューフォーカス

1. CLI/USIから選んだV1が制御付き探索で未知方針として拒否されず、実際にVを評価する。
2. 先後反転で評価視点とVの符号が反転し、候補選択が一方の側へ固定されない。
3. V1でも一手詰みを通常点より優先し、停止時に未完了点を採用しない。
4. V0が通常候補へ漏れず、既存比較CLIのV0/V1識別と結果保存が変わらない。
5. 選択なしのRandom、CVCの側別選択、USI設定の局内固定が維持される。

## 承認後の準備

- [x] Git状態、requirements-dev.txt、.venv/bin/ruff --version、git config --local --get core.hooksPathを再確認する。branch `codex/v-supported-threat-normal-cli-usi-connection`、ruff 0.16.10、hook `.githooks`。
- [x] 変更前全体テストを実行し、1,031件・84モジュール・24.719秒で成功した。
- [x] `docs/knowledge/test-coverage-review.md` と個人テスト点検手順を参照してからTDDを始めた。

## タスク 1：V1を時計・停止制御付き一手探索へ接続

**変更ファイル:** kaname_shogi/game_search.py、kaname_shogi/movegen.py、tests/test_game_search.py、tests/test_search_movegen.py。

**使用する既存契約:** game_search.search_move(position, policy, rng, control) はmovegen.SearchResultを返す。Vの実装はmaterial_piece_threat.evaluate_material_piece_threat(position, perspective, *, weights) と PieceThreatWeights(material=10, undefended=1, supported_threat=1) を使う。

- [x] GameSearchTests.test_v1_uses_controlled_one_ply_search を追加し、先後双方でV1が同じposition/policy/rng/controlを一度だけmovegen.search_moveへ渡し、実探索で合法手を返し、四手探索へ進まないことを確認した。
- [x] 未実装時にV1を未知方式として拒否する assertion failure を確認した。読み込みエラーではない。
- [x] ControlledEvaluationTests.test_supported_piece_threat_v1_uses_post_move_position_and_turn_perspective と test_supported_piece_threat_v1_prioritizes_mate と test_supported_piece_threat_v1_discards_stopped_evaluation を追加した。先後、着手後の既知210/209点、一手詰み、採点後停止を区別する。
- [x] RootSearchTests.test_v1_selects_v_move_for_both_sides_and_orders を追加し、実合法手からV比較対象の二候補を抽出して先後・候補順を反転し、Vの逃げ手を選ぶことを確認した。V0は通常の制御付き入口で拒否される。
- [x] 既存U制御探索の評価・停止・予備手・抑制テストを通し、既存契約を保つ最小変更でGreenにした。
- [x] Red/Green: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest tests.test_game_search.GameSearchTests.test_v1_uses_controlled_one_ply_search tests.test_game_search.GameSearchTests.test_search_move_rejects_comparison_only_v0_policy tests.test_search_movegen.ControlledEvaluationTests tests.test_search_movegen.RootSearchTests -v`（27 tests, OK）。初回Rootテストの期待範囲不一致は調査記録を参照。

## タスク 2：通常CLIでV1を候補にしCVC先後へ渡す

**変更ファイル:** kaname_shogi/cli.py、tests/test_cli.py、tests/test_cli_entrypoint.py。入口の先後別設定構造は既存実装を使い、不要な変更を加えない。

- [x] MoveSelectionPolicyMenuTests.test_choose_move_selection_policy_maps_choices と test_choose_move_selection_policy_prompts_for_side を更新し、1〜6を維持して7がMATERIAL_PIECE_THREAT_V1になり、表示名とエラー範囲が一致することを確認した。
- [x] 空入力が先後別にRandomのままで、7番の表示が先手・後手のどちらにも付くことを確認した。
- [x] GameplayTests.test_run_game_routes_distinct_policies_by_side と CliEntrypointTests.test_main_prompts_sente_then_gote_for_computer_vs_computer を更新し、V1と10M+Uの両側割当・逆順・開始前表示を確認した。HVCはコンピュータ側だけ、人間同士は方式選択なしの既存テストも通した。
- [x] 隔離コピーの番号入替・両側同一方針・空入力V1化が、それぞれ意図したassertion failureを起こすことを確認した。
- [x] Red/Green: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest tests.test_cli.MoveSelectionPolicyMenuTests tests.test_cli.GameplayTests tests.test_cli_entrypoint -v`（64 tests, OK）。未実装時は選択・表示・範囲のassertion failureを確認した。

## タスク 3：USI DifficultyへV1を追加

**変更ファイル:** kaname_shogi/usi_engine.py、tests/test_usi_engine.py、tests/test_usi_engine_launcher.py。

- [x] UsiEngineFunctionTests.test_answers_usi_with_difficulty_combo_before_usiok と UsiEngineLauncherTests.test_launcher_advertises_difficulty_combo を更新し、MaterialSupportedPieceThreatがoption列挙にありusiokより前に通知されることを確認した。
- [x] test_applies_material_supported_piece_threat_at_first_go と test_accepts_material_supported_piece_threat_case_insensitively を追加し、Difficulty値がMATERIAL_PIECE_THREAT_V1へ対応することを確認した。
- [x] test_material_supported_piece_threat_is_fixed_until_next_game を追加し、局中setoptionの反映延期、usinewgame後の変更、未知option/値後の有効設定保持、未設定Randomを確認した。
- [x] 実入口processテストをV1設定・position・goで実行し、合法なbestmoveを一度受信し、終了後に余分な出力がないことを確認した。
- [x] Red/Green: V1の先頭go・case-insensitive・局内固定・V0拒否・未知設定/Random・option応答・launcher通知を含む40 testsが成功した。Redでは設定がRandomへ落ちる、option通知欠落などのassertion failureを確認した。

## タスク 4：利用文書、検出力、全体検証と独立レビュー

**更新対象:** README.md、AGENTS.md、docs/knowledge/31-weak-move-selection.md、docs/knowledge/usi-engine-response.md、docs/knowledge/supported-piece-lower-value-threat.md、docs/learning/supported-piece-lower-value-threat.md、docs/plans/2026-11-01-v-normal-cli-usi-design.md、docs/README.md、docs/resume.md。

- [x] README・確定知識へCLIの7番、USIのDifficulty値、10M+U+Vの一手評価とV0比較専用を反映し、一般的な棋力向上を示す表現を避けた。学習記録へ本人承認、変更範囲、Red/Green、CVC操作、限界を区別して追記した。
- [x] 通常CLIのCVCを2局完局した。1局目は先手V1・後手10M+U、2局目は先手10M+U・後手V1。空入力の持ち時間10分・秒読み30秒を使い、開始前表示、両側の実着手、各局の終局を確認した。勝敗から棋力を推定せず、操作接続の実証として[学習記録](../learning/supported-piece-lower-value-threat.md)に記録した。新しい長時間比較とShogiHome操作はしていない。
- [x] AGENTS.mdへ、通常CLIから選べる一手選択方式を追加・変更する今後のテーマで、CVCを2局以上・可能な範囲で先後を入れ替えて完局する操作確認を行うという本人の継続希望を記録した。
- [x] 隔離コピーで制御付きV係数除去、詰み優先欠落、V0選択表への漏出、USI局中再適用を実行した。Task 2ではCVC同側流用、CLI番号6/7入替、空入力既定変更も検出した。意図したAssertionErrorと復元後の成功を[学習記録](../learning/supported-piece-lower-value-threat.md)へ分けて記録した。無関係な経路への最初の変異、および時計設定を含めなかった初回コピーは検出証拠に数えていない。
- [x] 関連回帰: `PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest tests.test_game_search tests.test_search_movegen tests.test_piece_threat_selection tests.test_cli tests.test_cli_entrypoint tests.test_usi_engine tests.test_usi_engine_launcher -v`（185件成功）。`test_piece_threat_selection` の補助モジュールを解決するため `PYTHONPATH=tests` を設定した。
- [x] Ruff import整理、`.venv/bin/ruff format .`、`.venv/bin/ruff check .`、`git diff --check`を行った。import整理成功、142ファイル整形済み、Ruff全ルール成功。最初の全Ruff checkは追加したloop closureのB023を検出し、ループ変数を明示束縛して解消した。
- [x] 全体回帰: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py`（1039 tests・84 modules・24.987秒、成功）。共有状態・順序依存およびランナー変更がないため逐次全体実行は追加しない。
- [x] Refactor要否を確認してから独立レビューを行った。初回Critical 0 / Important 0 / Minor 1。MinorはV1を含む共通一手方針ループに対し、二つの停止・予備手テストdocstringが旧三方式+Uと記載する説明範囲ずれで、文言を修正した。製品挙動は変えていない。独立レビューの差分再確認はCritical 0 / Important 0 / Minor 0。修正した2テスト、Ruff、差分検査を再実行して成功。結論と対象範囲を[学習記録](../learning/supported-piece-lower-value-threat.md)に記録した。
- [ ] 学習記録・知識メモの内容を本人が確認した後、通常hook付きで作業ブランチへ対象差分をコミットする。main統合・pushは別途本人承認を待つ。

## 計画のセルフレビューと未検証事項

対象契約は選択経路、先後視点、着手後局面、一手詰み、停止、CLI選択、USI option/lifetime、既定Random、比較専用V0、説明範囲。これらをタスク1〜4に割り当てた。重み係数や評価器は既存V1と一致させ、新たな設計選択を加えない。テストは両側・候補順・設定前後・未知値を代表条件にする。固定テスト・短いCLI/USI操作は全局面の正しさや一般的な棋力向上を証明しない。ShogiHome、実戦力、別OSでの互換性は未検証のまま残す。
