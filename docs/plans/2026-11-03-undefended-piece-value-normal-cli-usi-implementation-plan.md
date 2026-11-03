# U価値合計+Vの通常CLI・USI接続 実装計画

> **AIエージェントへの指示:** 本計画を実施する場合は、本人承認後に `superpowerssuperpowers:executing-plans` を使用し、チェック項目を順に進める。各タスクでテストを先に失敗させ、最小変更で成功させる。

**目標:** 比較済みの固定評価 `10M+U価値合計+V` を通常CLI候補8とUSI Difficultyへ接続し、U枚数とU価値合計の違いを選択時に見分けられるようにする。

**アーキテクチャ:** 内部方式 `MATERIAL_PIECE_THREAT_VALUE_V1`、既存の値合計評価器、一般一手選択器を再利用する。時計・停止付き探索では `game_search.search_move` の許可一覧と `movegen._evaluate_candidate` の評価分岐に方式を加え、通常CLIとUSIの境界に選択肢と明確な表示名を追加する。比較専用policy、保存データ、評価重みは変更しない。

**技術スタック:** Python 3.9互換、標準ライブラリ、`unittest`、固定版Ruff 0.16.10。新規依存なし。

**仕様:** [本人承認済み設計](2026-11-03-undefended-piece-value-normal-cli-usi-design.md)。本人は2026-11-03に設計と本実装計画を承認し、ネイティブ実行を選択した。

## グローバル制約

- 作業場所は `/Users/oki2a24/kaname-shogi` の現在の `codex/shogihome-u-candidate-practice` ブランチだけとし、別worktree・別cloneを使わない。
- `.agents/tasks/`、現在の `.antigravity/tasks/`、未追跡比較データ、C2保護4件、退避アーカイブと既存 `.venv.backup-*` を変更・移動・削除・stageしない。
- 既存番号1〜7の対応、空入力・USI未設定時のRandom、既存の一局中固定と探索制御を維持する。新候補の重みは `material=10`、`undefended_value=1`、`supported_threat=1` に固定する。
- U価値合計はU枚数を置き換え、両方を加算しない。V0、U価値合計単独、V単独、係数選択UI、二手・四手への新評価接続を追加しない。
- 比較CLI、比較方式・結果・seed・出力ファイルを変更・再実行しない。
- ShogiHomeの版、表示、登録先、Ponder、棋譜、ログ、稼働状態は操作時の現画面で確認し、過去記録から推定しない。未合意の先後・局面・時計・対局数・ログ要否は一問ずつ確認する。設定変更とログ閲覧はそれぞれ具体案と別の明示承認後に限る。
- Python変更では環境確認、Ruff import整理（importを変更した場合）、format/check、関連テスト、全体テスト、差分確認を行う。代表的な誤実装を隔離環境で注入して意図したassertion failureを確認する。
- Refactor要否を確認した後に独立コードレビューを行う。CriticalまたはImportantがあれば修正後に再検証・再レビューする。
- 学習記録と知識メモの内容を本人に確認してもらってから、対象ファイルだけを通常hook付きでtopic branchへコミットする。main統合・pushは別途承認を待つ。

## レビューフォーカス

1. 新候補が時計・停止付き一手評価に届かず未知方式扱い、または四手探索へ誤配送されないこと。
2. 着手後局面を元の手番側から評価し、10M+U価値合計+Vを使い、U枚数の再加算やU枚数評価へのすり替えがないこと。
3. 新候補でも一手詰み優先、停止時の未完了評価破棄、合法手応答が保たれること。
4. CLI番号8、USIの広告名と旧名aliasが、それぞれ意図した方式へ対応し、既存番号・Random・局内固定を壊さないこと。
5. 比較専用V0と比較CLIの成果物が通常選択へ漏れず、利用者向け説明が棋力保証や一般化を主張しないこと。

## ファイル構成

- `kaname_shogi/game_search.py`、`kaname_shogi/movegen.py` — 値合計V1を制御付き一手評価の許可一覧と候補評価分岐へ加える。
- `kaname_shogi/cli.py` — 1〜8の分類表示、番号8の対応、開始前表示名を更新する。
- `kaname_shogi/usi_engine.py` — 3つの明示的U方式名を広告し、従来2値を受信aliasとして残す。
- `tests/test_game_search.py`、`tests/test_search_movegen.py` — 対局探索経路・評価・詰み・停止・選択の契約を確認する。
- `tests/test_cli.py`、`tests/test_cli_entrypoint.py` — 選択表、分類、番号、開始前表示を確認する。
- `tests/test_usi_engine.py`、`tests/test_usi_engine_launcher.py` — option通知、alias、設定寿命、実プロセス応答を確認する。
- `README.md`、`docs/knowledge/31-weak-move-selection.md`、`docs/knowledge/undefended-piece-evaluation.md`、`docs/knowledge/usi-engine-response.md` — 確定した選択名・式・利用範囲を同期する。
- `docs/learning/undefended-piece-coordination-evaluation.md`、`docs/plans/2026-11-03-undefended-piece-value-normal-cli-usi-design.md`、本計画、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/02-project-direction.md`、`docs/roadmap-non-material-position-evaluation.md` — 本人承認、実変更、検証・レビュー、ShogiHome観察と限界、未完了の主線を記録する。

## タスク 0：作業環境と基準状態を確定する

**変更ファイル:** なし。

- [ ] `git status --short --branch` と `git branch --show-current` でブランチを確認し、既存変更・保護対象を一覧と照合する。既存データや退避物は読み書きの対象にしない。Expected: 作業先は指定ブランチのまま、保護対象に差分がない。
- [ ] `requirements-dev.txt`、`.venv/bin/ruff --version`、`.venv/bin/python --version`、`git config --local --get core.hooksPath` を確認する。固定版不一致や不足がある場合だけREADMEの `python3 scripts/setup_dev.py` に従ってローカル `.venv` を整える。Expected: Ruffは0.16.10、hookは`.githooks`、Pythonは3.9以上。
- [ ] コードを変更する前に `PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_tests_parallel.py` を実行し、基準時点の全体結果を記録する。Expected: 発見した全テストモジュールが成功する。

## タスク 1：価値合計V1を制御付き一手評価へ通す

**ファイル:** `kaname_shogi/game_search.py`、`kaname_shogi/movegen.py`、`tests/test_game_search.py`、`tests/test_search_movegen.py`。

**インターフェース:** `game_search.search_move(position, policy, rng, control) -> movegen.SearchResult` は、制御付き一手方式を `movegen.search_move` へ一度委譲する。`movegen._evaluate_candidate(position, move, policy, *, control)` は一候補の完了・点数を返す既存契約を使う。

- [ ] `ControlledEvaluationTests.test_value_v1_uses_post_move_position_and_turn_perspective` を追加し、未実装コードで先に実行する。先後双方の合法な一手について、値合計V1評価器が着手後局面・開始側視点・`PieceThreatValueWeights(10, 1, 1)` で一度呼ばれることをassertし、現在の候補方針拒否がRedになることを確認する。既存 `MaterialPieceThreatValueTests.test_default_design_scores_and_old_policy_unchanged` の独立期待値（例Dの旧308点・新294点、後手符号反転）を評価器の意味確認に再利用する。Expected: テストassertionが未対応方針を示し、import/fixture errorではない。
- [ ] `ControlledEvaluationTests.test_value_v1_prioritizes_mate` と `test_value_v1_discards_stopped_evaluation` を追加する。未対応方針をテスト内で明示的にassertion failureへ変換し、Redが単なるimportやfixtureの読み込み失敗ではないことを確認する。Green後に各テストが詰み判定欠落・採点後停止確認欠落を区別することを確認する。Expected: Redはassertion failureで、Green後は詰みと停止の契約を通す。
- [ ] `movegen._evaluate_candidate` が値合計V1を一手詰み確認後に既存の `evaluate_material_piece_threat_value` と `PieceThreatValueWeights(10, 1, 1)` へ渡すよう最小変更する。枚数U評価器は使わず、旧U枚数も加えない。ControlledEvaluationテストを再実行してGreenを確認する。Expected: 先後とも指定評価器・重みで採点され、詰み優先・停止破棄テストが成功する。
- [ ] `RootSearchTests.test_value_v1_selects_value_sum_candidate_for_both_sides_and_orders` を追加する。U枚数とU価値合計で候補順位が分かれる合法局面を使い、視点と候補順を反転しても、独立に計算した `10M+U価値合計+V` の候補が選ばれることをassertする。Expected: 先後と候補順に依存しない。
- [ ] `GameSearchTests.test_value_v1_uses_controlled_one_ply_search` を追加する。先手・後手の双方で合法手を返し、`movegen.search_move(position, policy, rng, control)` が一度だけ呼ばれ、四手探索は呼ばれないことをassertする。現行許可一覧でRedになることを確認する。Expected: 未実装時は未対応方針assertion、実装後は一手経路のみ呼ばれる。
- [ ] `game_search._CONTROLLED_ONE_PLY_POLICIES` に候補を一つ加える。既存の制御付き一手評価経路だけを通し、比較V0は引き続き拒否する。追加したrouteテストと比較V0拒否テストがGreenになることを確認する。Expected: 新候補のrouteとV0拒否の双方が成功する。

## タスク 2：通常CLIへ分類表示と候補8を追加する

**ファイル:** `kaname_shogi/cli.py`、`tests/test_cli.py`、`tests/test_cli_entrypoint.py`。

**インターフェース:** `choose_move_selection_policy(input_fn, output_fn, *, side=None) -> MoveSelectionPolicy` は番号を既存または新候補へ対応付ける。`_format_move_selection_policy_name(policy) -> str` は開始前表示に同じ名称を使う。

- [ ] `MoveSelectionPolicyMenuTests.test_choose_move_selection_policy_maps_choices` を更新し、1〜7の対応を維持したまま8が `MATERIAL_PIECE_THREAT_VALUE_V1` になる期待を追加する。選択メニュー表示は「ランダム」「一手評価（1手後）」と「探索手数」の区分に分け、6・7はU枚数、8はU価値合計と式を明示する。旧U表示と8番の選択が混同する状態をRedで確認する。Expected: 8番だけが値合計+V方針となり、既存番号は不変。
- [ ] `test_choose_move_selection_policy_prompts_for_side` の先手・後手別表示へ番号8の説明を加え、既存の6・7もU枚数と明記する。Expected: 先手・後手ともUの集計方法が同じ表示になる。
- [ ] `MoveSelectionPolicyMenuTests.test_choose_move_selection_policy_reprompts_after_invalid_choice` と `test_v0_stays_outside_normal_cli_choices` を9番入力へ更新し、エラー範囲を1〜8へ変更する。空入力Random、番号1〜7、CVCの先後別選択は変わらないことを既存テストで確認する。V0は候補に出さない。Expected: 9番は再入力、空入力はRandom、V0は候補外。
- [ ] 新候補の開始前表示が `10M+U価値合計+V` と分かり、通常CLIのCVC両側へ異なる方針を渡せることをテストする。Expected: 表示にU価値合計が明記される。
- [ ] CLI関連テストを実行し、表示文だけの更新漏れを含むRedを解消したGreenを確認する。Expected: `tests.test_cli` と `tests.test_cli_entrypoint` が成功する。

## タスク 3：USI Difficultyの選択名と受信aliasをそろえる

**ファイル:** `kaname_shogi/usi_engine.py`、`tests/test_usi_engine.py`、`tests/test_usi_engine_launcher.py`。

**インターフェース:** `_USI_DIFFICULTY_VALUES` は `setoption name Difficulty value ...` のcase-insensitiveな値を内部policyへ対応させる。`usi` 応答はShogiHomeが表示するcombo値を `usiok` 前に通知する。

- [ ] `test_answers_usi_with_difficulty_combo_before_usiok` と `UsiEngineLauncherTests.test_launcher_advertises_difficulty_combo` を更新する。広告値は `MaterialUndefendedPieceCount`、`MaterialUndefendedPieceCountPlusV`、`MaterialUndefendedPieceValuePlusV` とし、曖昧な旧名をcomboへ重複表示しないことをassertする。Expected: 明示値3つが`usiok`前、旧名aliasは広告外。
- [ ] 旧値 `MaterialUndefendedPiece` と `MaterialSupportedPieceThreat` を受信aliasとして保ち、新しい明示名は対応するcount、count+V、value+Vへそれぞれ対応するテストを追加する。新値・旧値の大小文字混在も確認する。Expected: 新旧名が指定された同一内部policyへ対応する。
- [ ] 新候補の設定を最初の `go` で適用し、局中のDifficulty変更は次の `usinewgame` まで延期され、未知値が最後の有効値を消さないことを確認する。未設定時RandomとV0拒否も維持する。既存 `test_material_supported_piece_threat_is_fixed_until_next_game` と `test_invalid_value_preserves_two_ply_setting` を残して新しい広告名と互換aliasの両方に対する寿命を確認する。Expected: 局内固定・次局反映・未知値保持・未設定Randomが成功。
- [ ] `UsiEngineProcessTests.test_entrypoint_flushes_protocol_and_bestmove` を新候補で実行し、実プロセスが合法な `bestmove` を一度返し、stdout/stderrに余分な応答を出さないことを確認する。Expected: 合法なbestmoveが一度、終了0、余分な出力なし。
- [ ] USIとlauncherテストを実行し、新旧値の誤対応・広告漏れ・旧設定alias欠落を示すassertion RedがGreenになったことを確認する。Expected: `tests.test_usi_engine` と `tests.test_usi_engine_launcher` が成功する。

## タスク 4：統合検証、代表変異、独立レビュー

**ファイル:** Task 1〜3のコードとテスト。

- [ ] 変更・追加したimportがあれば `.venv/bin/ruff check --select I --fix .` を実行し、続けて `.venv/bin/ruff format .`、`.venv/bin/ruff check .` を実行する。Expected: formatと全Ruff checkが成功する。
- [ ] `git diff --check` を行い、コード・テスト差分を確認して意図しない比較CLIや保護対象の変更がないことを確かめる。Expected: 差分検査成功、比較CLI・保護対象の差分なし。
- [ ] 対象テスト `PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest tests.test_game_search tests.test_search_movegen tests.test_material_piece_threat_value tests.test_cli tests.test_cli_entrypoint tests.test_usi_engine tests.test_usi_engine_launcher -v` を実行する。Expected: 7つの対象モジュールがすべて成功する。
- [ ] 意図したテストが契約違反を検出するか隔離コピーで代表変異を確認する：制御付き許可一覧からV1を外す、価値合計評価器を枚数評価器へ置換する、詰み優先・採点後停止確認を外す、CLI番号8を別policyへ割り当てる、USIの新値または旧aliasを誤対応させる。各変異で該当assertion failureを確かめ、読み込み失敗は検出証拠に数えず、作業checkoutには変異を残さない。Expected: 各代表変異が意図したassertionで失敗し、復元後の対象テストが成功する。
- [ ] Refactor要否を確認する。既存選択器・評価器・USI応答境界を再利用できる場合、無関係な構造整理は加えない。
- [ ] `PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_tests_parallel.py` で全体テストを実行し、全モジュール成功を確認する。全体成功だけで新候補固有の確認を代替しない。Expected: 発見した全モジュールが成功する。
- [ ] 差分の作者と別の独立レビュアーで変更を確認し、Critical / Important / Minorを記録する。Critical・Importantを修正した場合、該当テスト・全体テスト・独立レビューを再実施する。

## タスク 5：通常CLI CVCとShogiHome動作確認

**操作:** 通常CLI対局、ShogiHome。保存データ・比較CLI結果は対象外。

- [x] 通常CLIで `MATERIAL_PIECE_THREAT_V1`（10M+U枚数+V）と `MATERIAL_PIECE_THREAT_VALUE_V1`（10M+U価値合計+V）のCVCを2局完局し、先後を入れ替えた。開始前表示、双方の実着手、終局を確認した。1局目は後手投了後79件、2局目は先手投了後316件の指し手記録。少数局から棋力は判定しない。
- [x] ShogiHome操作直前に `.agents/skills/shogihome-connection/SKILL.md` と `docs/shogihome-connection-guide.md` を読み直し、現在画面から版・登録先・Ponder・棋譜・稼働状態・時計・ログを確認した。ShogiHome 1.28.2、登録先は同checkoutのランチャー、Ponder OFF、既存棋譜・稼働一覧・合意時計を確認した。
- [x] ShogiHome候補の既存実機記録を照合し、確認済みのRandom、Material、TwoPlyMaterial、FullWidth4、AlphaBeta4、旧Difficulty名のU枚数方式を重ねて実施しないと決めた。未確認候補 `MaterialUndefendedPieceCountPlusV` は一度停止した後、本人の「変更して続行」の指示と設定変更承認を受け、一局を実施した。U枚数方式の新しい明示値 `MaterialUndefendedPieceCount` は直接選択していないが、同じ動作は旧名 `MaterialUndefendedPiece` で確認済み。
- [x] 方式変更と指定ログ閲覧は、値・保存後の保持・SID 8の対象行を示して本人の別承認を得た。設定を `MaterialUndefendedPieceValuePlusV` に変更・保存し、保存後の新名を再表示で確認した。対局後は値を戻す操作をしていない。最初のSID全行検索が許可外の初期化・終了行を画面に出したため、その行を使用せず、この逸脱を学習記録に残した。
- [x] 選択名・接続・応答・画面観察と、比較結果や棋力の結論を分けた。一局は43手目の先手投了で終了し、評価方式の強さや棋力を判定しない。
- [x] `MaterialUndefendedPieceCountPlusV` を `MaterialUndefendedPieceValuePlusV` から変更・保存し、設定画面を開き直して新値とPonder OFFを確認した。人間先手・エンジン後手、平手、双方10分＋30秒・加算なしで一局を開始し、画面上30手（先後各15手）まで進行。先手の盤上クリックが反映されず、再表示・複数の入力を試しても回復しなかったため先手投了で終了した。KIFは `/Users/oki2a24/Documents/20261103_104906_人_kaname-shogi.kif` に自動保存された。終了後、SID 12が監視一覧から消えUSI/CSA各0を確認した。USIログは閲覧していない。これは画面上の選択・保存・複数応答と終了を確認した一例で、完局・棋力・方式間の優劣を示さない。

## タスク 6：文書、記録、差分確認とtopic commit

**ファイル:** 上記「ファイル構成」の文書群。

- [x] README・知識メモをコードと実施結果に照合し、通常CLI 1〜8の分類、U枚数/U価値合計の式、USIの広告値・旧alias、比較policy名の位置づけを同期する。比較CLIデータ・過去記録は改変しない。
- [x] 学習記録に本人の設計承認、実際の変更、TDD Red/Green、対象テスト、変異検出範囲、全体検証、独立レビュー、CVC結果、ShogiHomeの画面条件・操作観察・未確認範囲を分けて記録する。実施していない設定承認・対局・ログ閲覧を完了扱いにしない。
- [x] U評価の知識メモ、README、学習ロードマップ、`docs/resume.md` の未完了主線を更新し、次の非駒得評価項目を選ぶ主線は完了扱いにしない。
- [x] `git diff --check` と変更文書の相対リンク確認を行った。対象ファイルと保護対象・未追跡物の不変更をdiff/statusで照合した。whitespace差分なし、相対リンク1000件で欠落0。
- [x] 本人の文書確認後、承認済みの24ファイルだけをstageし、通常hook付きでtopic commitを作成した。main統合・pushは別途承認を待つ。

## 計画のセルフレビューと未検証事項

設計の要件はタスク1〜3で制御経路・CLI・USI、タスク4でTDD/回帰/レビュー、タスク5で指定された操作確認、タスク6で正本・履歴・主線の更新へ割り当てた。U価値合計の独立期待値は既存評価テストを再利用し、制御付き候補経路が同じ評価器・係数を用いることを個別に確認する。代表変異は各境界の取り違えを対象とし、全入力・全局面の正しさを証明するものではない。

最初に選ばれた `MaterialUndefendedPieceValuePlusV` のShogiHome対局は画面表示上42手分を進め、盤上入力の継続不能後に先手投了で終了した。許可されたSID 8のDifficulty `setoption`、`position`、`go`、`bestmove` 行を照合し、開始値と応答は一致した一方、最初の検索で許可範囲外行を表示した逸脱を記録し、その行は使用しない。続く `MaterialUndefendedPieceCountPlusV` は一度停止判断があった後、本人の「変更して続行」の指示と設定変更承認に従ってDifficultyを変更・保存し、一局を開始した。画面上30手（後手15応答）後に盤上入力を継続できず投了で終了した。KIFは承認済みの自動保存でDocumentsへ保存されたが、この回のUSIログは閲覧していない。したがって新方式のUSI通信行との照合や局完遂は未確認であり、過去に実機確認した他候補は重ねて実施していない。新名のU枚数単独は未選択だが、同一方式は旧名で実施済み。CVCやShogiHomeの少数局は操作・応答の確認であり、棋力向上の根拠にはならない。主線「次の非駒得評価項目を一つ選び学ぶ」はこの補助テーマ後も未完了として保持する。

## 実行方法

インターフェースを共有する少数の連携変更なので、本人は本計画とネイティブ方式を承認した。実装後は別のレビュアーが独立レビューする。

## 実施後の状態（事後記録・2026-11-03）

タスク1〜4と通常CLI CVCは完了した。ShogiHomeでは `MaterialUndefendedPieceValuePlusV` と `MaterialUndefendedPieceCountPlusV` を各一局開始し、選択・保存後の複数応答を画面で観察した。いずれも盤上操作を継続できず先手投了で終わった。CountPlusVはUSIログを閲覧していないため通信行との照合はしていない。学習記録・知識メモ・現在地・ロードマップを更新した。文書リンク、差分、保護対象、本人の学習・知識文書レビュー後、対象24ファイルを限定してtopic commitを作成した。pre-commit hookのRuff整形・lintは成功した。main統合とpushは行っていない。
