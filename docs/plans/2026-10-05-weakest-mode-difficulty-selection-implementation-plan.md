# 最弱モードを残す難易度選択 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画を実行するには、タスクごとの実装に移植された subagent-driven-development（推奨）または executing-plans スキルを使用してください。各ステップはチェックボックスで追跡します。

**目標:** 既存の一様ランダムを最弱として維持し、CLIとShogiHomeから対局ごとに選べる一手選択方針として、谷川浩司さんの参考駒価値を使う一手後の駒得評価を追加する。

**アーキテクチャ:** 共通の MoveSelectionPolicy と選択処理を kaname_shogi.movegen に置き、RANDOM は既存の choose_weak_move へ委譲し、MATERIAL は合法手ごとに複製局面へ一手だけ適用して駒得差を比較する。CLIは対局形式の後に必要な場合だけ方針を尋ね、USIは Difficulty の combo と setoption で方針を受け取り、最初の go でその局の方針を固定する。

**技術スタック:** Python 3.9.6、標準ライブラリ random / enum / typing / unittest / subprocess、既存の kaname_shogi.movegen / model / cli / usi_engine。

**仕様 (Spec):** [承認済み難易度選択設計](2026-10-05-weakest-mode-difficulty-selection-design.md)

**この計画で確定した細則:** 設計仕様では後続テーマに残していた採点・表記・確認範囲を、今回の設計対話で次のように確定した。通常の勝敗ルールとは別の局面評価ヒューリスティックとして扱う。盤上と持ち駒は同じ値で数え、玉将は除外する。谷川参考値は歩1、と金12、香5、成香10、桂6、成桂10、銀8、成銀9、金9、角13、馬15、飛15、竜17。候補手後の評価は「指し手側の盤上・持ち駒合計 − 相手側の盤上・持ち駒合計」で、指し手側から見て最大の手を選び、同点は注入された乱数生成器で選ぶ。CLI表示は「最弱（一様ランダム）」「駒得を考える」、USI option は name Difficulty、values Random / Material とする。

数値表の出典は[北海道大学講義資料 p.6「参考：将棋の駒の価値（谷川浩司）」](https://ocw.hokudai.ac.jp/wp-content/uploads/2016/01/IntelligentInformationProcessing-2005-Note-06.pdf)。通常対局の評価値が勝敗規則ではないこと、および持将棋・入玉の規則上の点数計算とは別であることを、[日本将棋連盟の対局規則](https://www.shogi.or.jp/match/taikyoku_rules/)と[持将棋に関するFAQ](https://www.shogi.or.jp/faq/rules/)に基づき記録する。USI comboの境界は承認済み設計仕様が参照する[USI仕様](https://hgm.nubati.net/usi.html)に従う。

**状態:** 2026-10-05に本人が明示承認し、作業ブランチ codex/weakest-mode-difficulty-selection-implementation で実装に着手した。ShogiHome実機の設定・対局・ログ採取は対象外とする。

**グローバル制約 (Global Constraints):**
- 学習は一回一テーマで進める。
- 学習記録は docs/learning/ に、実装に関係する確定知識は docs/knowledge/ に日本語で記録し、判断理由、合意範囲、実装、検証、未解決事項と参照先を明確にする。
- 説明・学習記録・知識メモは日本語で書く。
- 公開インターフェースのdocstringに引数・戻り値・副作用・前提条件と設計理由を記録し、処理を変えたら説明も更新する。
- 英語の駒名は、定義箇所で日本語名を併記する。
- テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞い、続く本文に検出したい誤りや背景を書く。標準の unittest -v で日本語の説明を表示する。
- 関連する振る舞いごとにテストのRed理由を確認し、読み込みエラーだけでRed確認を完了と扱わず、最小実装、Green、Refactorの要否確認を行う。
- Refactor確認後は変更の有無にかかわらず独立レビューを行い、Critical・Important・Minorの結論と対応を学習記録へ残す。CriticalまたはImportantがあれば修正後に再検証・再レビューする。
- 学習記録・知識メモの内容を本人に確認してからGitにコミットする。mainへの取り込みには別途本人の承認を得る。
- この計画を本人が明示承認するまで、TDD、コード・テスト変更、テスト実行、ShogiHome実機操作を始めない。

## レビューフォーカス (Review Focus)

- Material評価で成駒を参考値どおりに評価し、取った成駒は基本駒の持ち駒値へ戻ること（tests/test_movegen.py）。
- Material評価が指し手側の視点を使い、盤上・持ち駒を合算して相手との差を比較し、玉を含めないこと（tests/test_movegen.py）。
- 同点の最高評価手だけから注入乱数で選び、候補適用後も元のPositionを変更しないこと（tests/test_movegen.py）。
- CLIで空入力はRandomを選び、不正入力は再質問し、人間対人間では難易度を尋ねないこと（tests/test_cli.py、tests/test_cli_entrypoint.py）。
- USIの設定欠落・不正値・対局途中の変更でも、既定値またはその局で固定済みの方針を壊さず、変更を次局で有効にすること（tests/test_usi_engine.py）。

## ファイル構成

- 変更: kaname_shogi/movegen.py — MoveSelectionPolicy、material_balance、choose_move を追加し、既存の choose_weak_move を維持する。
- 変更: kaname_shogi/cli.py — CLI方針メニュー、run_game の既定方針、各コンピュータ手への共通選択処理の受け渡し。
- 変更: kaname_shogi/__main__.py — テスト可能なmain()を設け、対局形式の後、人間対人間以外で方針メニューを呼び、選択結果を run_game へ渡す。
- 変更: kaname_shogi/usi_engine.py — USI Difficulty combo の通知、setoption の既知値の保持、局ごとの方針固定。
- 変更: tests/test_movegen.py — 駒価値、合計、候補選択、同点、乱数、局面非変更の振る舞い。
- 変更: tests/test_cli.py、tests/test_cli_entrypoint.py — メニュー、既定値、再質問、対局形式ごとの表示順。
- 変更: tests/test_usi_engine.py、tests/test_usi_engine_launcher.py — USIオプション、設定保持、ゲーム境界、起動応答。
- 変更: docs/knowledge/31-weak-move-selection.md — 現行一様ランダムと追加するMaterial方針の契約・参考値を記録する。
- 変更: docs/knowledge/usi-engine-response.md — Difficulty combo と setoption、局ごとの方針寿命を記録する。
- 作成: docs/learning/64-weakest-mode-difficulty-selection-implementation.md — 合意、TDDの実際のRed/Green、Refactor、独立レビュー、検証、本人回答と補足を記録する。
- 変更: docs/plans/2026-10-05-weakest-mode-difficulty-selection-design.md — 後続テーマで確定した細則を、元の設計時点の未決事項と区別して追記する。
- 変更: README.md、docs/README.md、docs/resume.md、docs/02-project-direction.md — 実装完了時に現在の利用方法・索引・方向性を更新する。docs/next-topics.md は最終理解確認への本人回答後に見直す。
- 変更しない: ShogiHomeの登録・設定、対局、USI通信ログ。実機確認は別途対象・方法を合意し、本人の別承認を得た場合だけ行う。

**共通インターフェース (Interfaces):**

- MoveSelectionPolicy は RANDOM と MATERIAL の二値を持つ方針データとする。
- material_balance(position: Position, perspective: Side) -> int は、盤上の非玉駒を成駒別の値で合計し、持ち駒を基本駒種の値で合計して、指定側の合計から相手側の合計を引く。Positionを変更しない。
- choose_move(position: Position, moves: Tuple[Move, ...], policy: MoveSelectionPolicy, rng: random.Random) -> Optional[Move] は共通選択操作。空のmovesならNone。RANDOMはchoose_weak_moveへ委譲する。MATERIALは各手をPosition.copy()へ一度だけ適用し、元のposition.side_to_move視点のmaterial_balanceが最大の候補からrng.choiceで選ぶ。
- choose_move_selection_policy(input_fn: Callable[[], str] = input, output_fn: Callable[[str], None] = print) -> MoveSelectionPolicy はCLIメニュー操作。空入力はRANDOM、不正値はエラー表示後に再入力する。
- run_game は move_selection_policy: MoveSelectionPolicy = MoveSelectionPolicy.RANDOM を受け取り、一局中に同じ値をコンピュータ手へ渡す。
- kaname_shogi.__main__.main() -> int は対局形式を選び、必要な場合だけ方針メニューを呼んでrun_gameへ渡す実行操作。モジュールを直接実行する場合も同じmain()を使う。
- USIでは Difficulty / Random / Material を外部文字列とし、内部ではそれぞれ選択オプション、MoveSelectionPolicy.RANDOM、MoveSelectionPolicy.MATERIALに対応させる。設定値は局面を保持する _UsiEngineState に混ぜない。

---

### Task 1: 谷川参考値による評価と共通一手選択

**ファイル:**
- 変更: kaname_shogi/movegen.py
- 変更: tests/test_movegen.py

**生産 (Produces):** MoveSelectionPolicy、material_balance、choose_move。以降のCLIとUSIはこの共通境界だけを使う。

- [x] **ステップ1: 振る舞いテストを追加する**

次のテストを tests/test_movegen.py に追加する。新しい公開名はモジュール属性として取得し、未定義時はassertIsNotNoneで失敗させる。テストモジュールのimport失敗だけをRed理由にしない。

1. test_material_balance_counts_tanigawa_values_on_board_and_in_hands — 先手の盤上に谷川表の非玉13種類を一枚ずつ、先手の持ち駒に非玉基本7種類を一枚ずつ置く。双方の玉も置く。material_balance(position, Side.SENTE) が盤上130 + 持ち駒57 = 187、Side.GOTE視点が-187となることを確認する。
2. test_material_policy_prefers_highest_post_move_balance — 銀を取る合法手と駒得を変えない合法手を候補に渡し、MATERIALが銀を取る手を返すことを確認する。銀8点が相手から指し手側の持ち駒へ移るため、指し手側−相手側の差が16点増えることも評価値で確認する。
3. test_material_policy_values_captured_promoted_piece_as_basic_in_hand — 竜を取る合法手を局面へ適用した複製で、竜17点が飛車の持ち駒15点に戻り、指し手側の差が32点増えることを確認する。
4. test_material_policy_uses_only_supplied_one_ply_moves — 候補適用時にchoose_moveがlegal_movesを再呼び出さず、渡された候補だけを一手適用して評価することを確認する。
5. test_material_policy_uses_injected_rng_for_equal_best_moves — 同じ最高点になる二手だけを渡し、注入乱数器がその二手のタプルを受け取ること、選んだ一方を返すことを確認する。
6. test_choose_move_returns_none_for_no_moves — どちらの方針でも空タプルからNoneを返すこと、rng.choiceを呼ばないことを確認する。
7. test_choose_move_preserves_position_when_scoring_moves — 盤面、手番、双方の持ち駒が候補採点の前後で同一であることを確認する。
8. test_random_policy_keeps_uniform_selector — 同じmovesと同じseedで、RANDOMの結果が既存choose_weak_moveの結果と等しいことを確認する。

- [x] **ステップ2: Redを振る舞いの理由で確認する**

実行: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_movegen.MaterialEvaluationTests -v

期待値: 未実装のmaterial_balance / choose_moveに対する明示的なassertion failureと、個別の期待値・選択結果の不一致が出る。ModuleNotFoundErrorだけならRed完了とせず、テストをモジュールimport可能な形に直して再実行する。

- [x] **ステップ3: 最小実装を追加する**

movegen.py に二値のMoveSelectionPolicy、非公開の谷川参考値表、material_balance、choose_moveを追加する。駒価値表は日本語駒名の対応が分かるdocstringまたは定数コメントを付ける。MATERIALでは元局面のside_to_moveを評価視点として保存し、各BoardMoveまたはDropMoveを専用Position.copy()へ一回だけ既存apply操作で適用して採点する。選択後も合法手やPositionを変更しない。既存choose_weak_moveの契約は変えない。

- [x] **ステップ4: Greenと既存ランダム契約を確認する**

実行: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_movegen.MaterialEvaluationTests tests.test_movegen.WeakMoveSelectionTests -v

期待値: 参考値187/-187、銀捕獲の差分16、竜捕獲の差分32、単一手適用、最高点と同点抽選、空候補、Position非変更、既存一様ランダムの全アサーションが成功する。

---

### Task 2: CLIで対局前に方針を選ぶ

**ファイル:**
- 変更: kaname_shogi/cli.py
- 変更: kaname_shogi/__main__.py
- 変更: tests/test_cli.py
- 変更: tests/test_cli_entrypoint.py

**消費 (Consumes):** タスク1のMoveSelectionPolicy / choose_move。

**生産 (Produces):** choose_move_selection_policy と run_game の明示的な方針引数。未指定時はRANDOM。

- [x] **ステップ1: メニューと対局進行の振る舞いテストを追加する**

未実装のmainはモジュール属性のguard assertionで確認する。choose_moveのmock先がまだないRed段階はpatch.object(..., create=True)で監視し、既存run_gameが呼ばないことによる振る舞いassertionを失敗させる。

1. test_choose_move_selection_policy_maps_choices — 入力1がRANDOM、2がMATERIALとなることを確認する。表示には「最弱（一様ランダム）」「駒得を考える」を含める。
2. test_choose_move_selection_policy_defaults_to_random_on_empty_input — 空入力がRANDOMとなることを確認する。
3. test_choose_move_selection_policy_reprompts_after_invalid_choice — 無効値後に再表示し、次の有効入力を選ぶことを確認する。
4. test_run_game_defaults_to_random_policy — 方針を渡さないrun_gameの自動手でchoose_moveへRANDOMが渡ることをmockで確認する。
5. test_run_game_passes_selected_policy_to_computer_turn — run_gameへMATERIALを明示し、自動手でchoose_moveへMATERIALが渡ることをmockで確認する。
6. test_main_prompts_for_policy_only_when_computer_participates（tests/test_cli_entrypoint.py の CliEntrypointTests）— main()の依存をmockし、人間対人間では選択メニューを呼ばず、人間対コンピュータとコンピュータ対コンピュータでは各一回呼び、選択方針をrun_gameへ渡すことを確認する。
7. test_entrypoint_prompts_for_policy_after_computer_game_mode（tests/test_cli_entrypoint.py の CliEntrypointSmokeTests）— 実プロセスへ人間対コンピュータ、空の方針入力、投了を与え、方針メニューが対局形式選択の後かつ対局表示の前に一度表示されることを確認する。

- [x] **ステップ2: Redを振る舞いの理由で確認する**

実行: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.MoveSelectionPolicyMenuTests tests.test_cli_entrypoint.CliEntrypointTests.test_main_prompts_for_policy_only_when_computer_participates tests.test_cli_entrypoint.CliEntrypointSmokeTests.test_entrypoint_prompts_for_policy_after_computer_game_mode -v

期待値: 未実装の選択メニュー、表示または既定値に対するassertion failureとなる。入口テストでは人間対コンピュータの方針表示が欠ける期待値不一致を確認する。

- [x] **ステップ3: CLI選択と既定値を実装する**

cli.py にchoose_move_selection_policy(input_fn, output_fn)を追加し、1 / 2、空入力、無効入力の再質問を実装する。run_gameへmove_selection_policyを追加し既定値をRANDOMとする。_run_computer_turnへ値を渡してchoose_moveを使い、既存の合法手なし表示と一手適用順序を維持する。__main__.pyにmain()を追加し、choose_game_modeの直後、人間対人間以外だけ方針メニューを呼び、選択結果をrun_gameへ渡す。公開一覧とdocstringを更新する。

- [x] **ステップ4: CLI Greenと既存進行を確認する**

実行: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.MoveSelectionPolicyMenuTests tests.test_cli.GameplayTests tests.test_cli_entrypoint -v

期待値: 空入力の既定、無効値の再質問、人間対人間での非表示、両コンピュータ形式での選択方針受け渡し、実入口の表示順、run_game直接呼び出し時の既定RANDOMと明示MATERIALの受け渡し、既存の棋譜・対局進行が成功する。

---

### Task 3: USI comboでShogiHome向け方針を扱う

**ファイル:**
- 変更: kaname_shogi/usi_engine.py
- 変更: tests/test_usi_engine.py
- 変更: tests/test_usi_engine_launcher.py

**消費 (Consumes):** タスク1のMoveSelectionPolicy / choose_move。

**生産 (Produces):** Difficultyのcombo通知、設定値の検証と保持、各局の方針固定。

- [x] **ステップ1: USI設定と局境界のテストを追加する**

1. test_answers_usi_with_difficulty_combo_before_usiok — usi応答に「option name Difficulty type combo default Random var Random var Material」が含まれ、usiokより前に出ることを確認する。
2. test_uses_random_policy_when_difficulty_is_unset — setoptionなしの最初のgoへRANDOMが渡ることを確認する。
3. test_applies_valid_difficulty_setting_at_first_go — setoption name Difficulty value Material 後の最初のgoへMATERIALが渡ることを確認する。
4. test_ignores_invalid_and_unknown_options — 有効なMaterial後に未知名や既知名の不正値を送っても、現在の有効値が変わらないことを確認する。未設定時の不正DifficultyはRANDOMのままであることも確認する。
5. test_defers_midgame_difficulty_change_until_next_game — 最初のgoでRANDOMを固定し、局中にMaterialへ変更した後の次goはRANDOMのまま、usinewgameと新position後の最初のgoはMATERIALになることを確認する。
6. test_usinewgame_preserves_configured_difficulty — 局面を消しても設定済みDifficultyを次局へ保持することを確認する。
7. test_launcher_advertises_difficulty_combo — kaname-shogi-usi実プロセスのusi応答にcombo行がusiokより前に出ること、stdoutに他の表示を混ぜず正常終了することを確認する。

- [x] **ステップ2: Redを振る舞いの理由で確認する**

実行: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine.UsiEngineFunctionTests.test_answers_usi_with_difficulty_combo_before_usiok -v

期待値: 既存のid行とusiokは出るが、必要なcombo行を含まないため、出力列のassertionが失敗する。

- [x] **ステップ3: USI optionと局ごとの適用を実装する**

usi_engine.py のusi応答でcombo行をusiok前に一行出力する。setoption name Difficulty value <値>ではRandom / Materialのみを有効値として処理し、未知名と不正値を現在の契約どおり無視する。設定値はrun_usi_engineの局面状態とは別のローカル値とし、未設定時はRANDOM、usinewgameでは設定を維持して局の固定値だけを解除する。最初のgoで設定値を局の固定値として採用し、後続setoptionは次局の最初のgoまで反映しない。goはchoose_moveへ委譲する。

- [x] **ステップ4: USI Greenと起動境界を確認する**

実行: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine tests.test_usi_engine_launcher -v

期待値: option順、既定値、設定値、不正値、局中固定、次局適用、launcher応答、既存のposition / go / bestmove / resign / flushの全アサーションが成功する。

---

### Task 4: Refactor、独立レビュー、記録、全体検証

**ファイル:**
- 確認・必要時変更: タスク1〜3のコードとテスト
- 変更: docs/knowledge/31-weak-move-selection.md
- 変更: docs/knowledge/usi-engine-response.md
- 作成: docs/learning/64-weakest-mode-difficulty-selection-implementation.md
- 変更: docs/plans/2026-10-05-weakest-mode-difficulty-selection-design.md
- 変更: README.md、docs/README.md、docs/resume.md、docs/02-project-direction.md

- [x] **ステップ1: Refactorの要否を確認する**

方針値・採点・選択の責務、CLIとUSIからの委譲、設定値と局面状態の分離、テストの重複と過剰な抽象化を確認する。不要な構造変更は加えない。変更しない場合も理由を学習記録へ残す。変更する場合は関係するfocused testsを再実行する。

- [x] **ステップ2: 独立レビューを行い、Critical・Importantを解消する**

実装者と別のレビュアーが承認済み設計、今回の細則、コード、テスト差分を確認し、Critical / Important / Minorを記録する。CriticalまたはImportantがあれば修正し、focused testsと全テストを再実行して再レビューする。Minorも採否と理由を学習記録へ記す。

- [x] **ステップ3: 確定知識と学習記録を作成する**

駒価値とmaterial_balance、共通一手選択、CLI既定値、USI option値・状態寿命を各知識メモへ反映する。谷川参考値の資料を出典としてリンクし、通常対局の評価用参考値と持将棋・入玉の規則上の点数計算が別物であることを明記する。学習記録には本人の合意、TDDの実際の失敗理由と成功、Refactor判断、独立レビュー結果、実施した検証、未実施のShogiHome実機確認を区別して記す。設計仕様の当初未決事項は後続テーマで確定した記録へリンクする。

- [x] **ステップ4: 全体検証と文書検査を行う**

実行: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v

期待値: 全 unittest が成功する。

実行: git diff --check

期待値: 空白エラーを報告しない。ShogiHome実機テスト済みとは記録しない。

- [ ] **ステップ5: 学習・知識記録を本人に提示し、作業ブランチへコミットする**

学習記録・知識メモの内容を本人に提示して確認を受ける。承認された記録、コード、テスト、設計仕様と本計画、必要なREADME・索引更新を作業ブランチへコミットする。mainへの取り込みは別途本人の承認があるまで行わない。取り込みが別途承認された場合は取り込み先で検証し、最後の理解確認を一問だけ行う。本人の回答と補足を学習記録へ追記してからdocs/next-topics.md、README.md、プロジェクト方向性を見直し、次の候補と推薦理由を示す。本人が次テーマを選ぶまで新しい学習・実装へ進まない。

---

## 実行後の記録

この計画は実施前の手順である。各ステップの完了後に、テストの実出力、レビュー指摘と対応、文書確認、コミットの有無を追記する。実施していない手順を完了済みに書き換えない。

### 実際の実行記録

- 本人は2026-10-05にこの計画を明示承認した。作業ブランチ `codex/weakest-mode-difficulty-selection-implementation` で実施。開始時のHEADは `859742d` で、現在までコミットしていない。
- Task 1〜3のRedとGreen、およびfocused testの件数・失敗理由は[第64回学習記録](../learning/64-weakest-mode-difficulty-selection-implementation.md)を参照する。実行者の一時的な作業ログはコミット対象にしない。
- Refactor確認後の選択関連75件は成功。独立レビュー1回目はCritical 0、Important 1、Minor 1。USI option名・値の大小文字を区別しない実装とテストを追加し、玉除外・後手視点・最高点未満の候補を含む評価テストを補強した。再レビューはCritical 0、Important 0、Minor 0。
- レビュー修正後に `tests.test_movegen.MaterialEvaluationTests` の9件と、USIのケース・不正値・有効値・局固定に関する4件を再実行し、すべて成功。
- 全体検証 `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`：305 tests、成功。
- `git diff --check`：問題なし。変更した9件のMarkdown文書の相対ローカルリンク検査：リンク切れなし。
- ShogiHome実機の設定・対局・ログ採取は行っていない。文書は作成済みで本人の内容確認待ち。作業ブランチのコミット、`main` への取り込み、その承認、取り込み先検証、最終理解確認は未実施。
