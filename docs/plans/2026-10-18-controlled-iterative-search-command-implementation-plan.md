# 時間制御付き反復を試す開発用コマンド 実装計画

> **AIエージェントへの指示:** 本人は2026-10-18にこの計画全体を明示承認済み。実装方式は順次実装、作業場所は現在のcheckout内の作業ブランチが選択された。タスクごとにTDDとRefactor要否確認を行い、独立レビューを受ける。

**目標:** 承認済み設計の専用開発用コマンドを追加し、指定したSFEN・深さ・直接指定の時間予算に対する制御付き反復探索の終了状態、選択手、その由来、最新完了記録を表示する。

**アーキテクチャ:** 新しい `kaname_shogi.search.run_controlled_iterative` が引数解析、入力値検査、予算と制御の用意、一回の `search_controlled` 呼出し、結果表示、終了コードを担当する。既存の比較用入力・手/評価整形、SearchBudget、SearchControl、将棋用制御操作、制御付き反復結果を再利用し、探索規則や時間予算計算を複製しない。

**技術スタック:** Python 3.14以上、標準ライブラリの `argparse`・`time`・`unittest`・`unittest.mock`・`subprocess`。依存追加なし。Ruff 0.16.10、現行の `py314` 設定を維持する。

**仕様:** [2026-10-18承認済みコマンド設計](2026-10-18-controlled-iterative-search-command-design.md)。合意と理由は[設計学習記録](../learning/controlled-iterative-search-command-design.md)を参照する。

**グローバル制約（承認済み設計から抜粋）:**

- 専用コマンドは `kaname_shogi.search.run_controlled_iterative` とし、公開入口 `main(argv: list[str] | None = None) -> int` を設ける。
- `--sfen`、`--max-depth`、`--target-ms`、`--maximum-ms` はすべて必須。深さは1以上、予算は整数msで `0 ≤ target_ms ≤ maximum_ms`。既定値や独自の数値表記規則を追加しない。
- 深さ・予算に独自の上限を設けず、資源制限は残す。経過時間の計測表示は追加しない。
- 既存の `comparison.make_parser` と `parse_position`、`SearchBudget`、`shogi.make_controlled_operations`、`iterative_deepening.search_controlled`、`comparison.format_move` / `format_score` を使う。`calculate_search_budget` と設定ファイル読込は呼ばない。
- 入力検査・予算構築・操作セット生成を終えてから、探索直前に同じ `time.monotonic_ns` の時計原点を一回取得する。同一の原点・時計・SearchControlを一探索へ渡す。合法予備手の準備も予算に含める。
- 新入口は制御付き反復探索を一回だけ行う。既存三方式と既存比較入口を維持し、比較探索・途中通知・新しい設定・通常対局やUSIへの接続を加えない。
- 終了状態・選択手・手の由来・完了記録を混同せず表示する。記録なしの評価・深さを捏造しない。訪問数を実時間や全作業量として扱わない。
- 入力誤りはstderrへ `入力エラー: {error}` と表示して2、ヘルプと正常な探索結果は0、捕捉したKeyboardInterruptはstderrへ `中断: Ctrl+C。結果表示は未完了です` と表示して130。内部故障は入力誤りや正常停止に変換せず、原因を保持して伝播する。
- 上限msによる実応答時間・期限内応答を保証しない。全局面、全OS、実プロセスSIGINT配送、棋力、USI競合は検証済みと扱わない。
- 実装は目的の分かる作業ブランチで行い、mainへ直接実装しない。mainへの取り込みは別承認の対象とする。

## 承認段階

本人は2026-10-18に本書の計画全体を「yes」と明示承認した。計画承認は設計全体への過去の承認と区別して記録する。本人は順次実装方式と、現在のcheckout内に作業ブランチを作る方式を選択済み。`codex/controlled-iterative-search-command` を承認記録コミット `f8429f8` から作成し、計画固有の作業場所 `.superpowers/sdd/2026-10-18-controlled-iterative-search-command-implementation-plan/` を準備した。Task 1のTDDと独立レビューが完了し、Task 2へ進む。

## 範囲と成功条件

変更する製品ファイルは専用コマンド一つと、その振る舞いを確認する専用テスト一つに限る。SFENや探索の共通規則、既存比較コマンド、時間配分設定は変更しない。出力は比較・操作観察用の一回分で、通常対局・USIの選択肢には接続しない。

成功条件は次の通り。

1. 四つの必須引数と範囲条件が守られ、入力誤りでは探索も時計原点取得も行われない。
2. 検査済みの直接指定予算と同じ時計原点から作った制御を、指定深さ・開始側視点の操作セットと一緒に既存の制御付き反復入口へ一度渡す。
3. COMPLETE、NO_LEGAL_MOVE、STOPPED、SUPPRESSEDそれぞれで、選択手と完了記録の有無に合う表示になる。
4. ヘルプ・入力誤り・通常結果・Ctrl+C・内部故障の終了と出力境界が設計どおりである。
5. 固定時計・独立に構成した結果データ・既存テストとの補完を使い、実時間で完了深さを固定しない。

## 現物と変更対象

| ファイル | 予定 |
| --- | --- |
| `kaname_shogi/search/run_controlled_iterative.py` | 新規。コマンド、内部の入力/結果整形、`main`、モジュール実行入口 |
| `tests/test_search_run_controlled_iterative.py` | 新規。専用コマンドの単体・接続・プロセス境界 |
| `kaname_shogi/search/compare.py`、`compare_iterative.py`、`comparison.py` | 製品変更なし。既存契約を再利用し回帰範囲として参照 |
| `kaname_shogi/search/iterative_deepening.py`、`result.py`、`shogi.py`、`search_control.py`、`time_management.py` | 製品変更なし。確定済み探索・制御・データ契約を利用 |

この計画の作成時、専用コマンドと専用テストはまだ存在しない。現在のPython要件はREADMEの3.14以上、Ruff設定は`py314`、テストは標準`unittest`である。

## インターフェースとデータの流れ

新しい公開入口は次の一つだけとする。

```python
def main(argv: list[str] | None = None) -> int:
    ...
```

`argv=None`は実行時引数を使う。直接呼出しは終了コードを返す。モジュール実行は `raise SystemExit(main())` でその値をプロセスへ伝える。入力/表示の補助処理を関数へ分ける場合も、コマンドモジュール内の非公開関数に留め、追加の公開APIを作らない。

処理順は以下の通り。

1. `comparison.make_parser` の解析器に四引数を追加し、`parse_args(argv)` を行う。
2. 深さとSFENを検査し、二つのms値から `SearchBudget(target_ms, maximum_ms)` を直接作る。範囲不正またはSFENのValueErrorだけを入力誤りとして扱う。
3. `make_controlled_operations(position.side_to_move)` を一度呼ぶ。
4. 探索直前に単調時計関数を一つの参照として保持し、その関数から整数ns原点を一度取得する。`SearchControl(budget, started_ns, now_ns=same_clock)` を一つ作る。
5. `search_controlled(position, max_depth, operations, control)` を一度だけ呼び、戻った `ControlledSearchResult` 一件を表示へ渡す。比較用探索や再探索を行わない。
6. `comparison.format_move` / `format_score` で表示を作り、探索が返った後に実行条件と終了結果をまとめて標準出力へ出す。

## 契約・代表ケース・検出範囲

| 対象契約 | 代表ケースと独立期待値 | 検出したい誤り | 新テストと既存補完 |
| --- | --- | --- | --- |
| 必須引数・標準解析 | 四引数が揃った整数値。いずれか一つの不足、小数、未知引数は2。`--help`は0 | 深さ/予算の既定値混入、int以外の受理、未知引数の成功扱い | `test_parser_requires_explicit_values`、`test_parser_keeps_argparse_duplicate_and_abbreviation_rules`。argparse標準の同一オプション最終値と一意な省略形を確認 |
| 深さ・予算・SFEN境界 | 深さ0、負の目標、目標>上限、整数変換失敗、不正SFENは2。0/0と目標=上限は有効 | 独自の予算計算、0の時計なし化、探索前でない検査 | `test_prepare_inputs_rejects_invalid_depth_budget_and_sfen`、`test_main_invalid_inputs_do_not_start_search`。`test_time_management.py`は予算型/計算を補うが、CLIの入力境界は補わない |
| 入力失敗の副作用 | 上記不正入力でstdout空、時計・操作セット・探索呼出しなし | 不正入力後の部分実行、準備時間と探索時間の混同 | `test_main_invalid_inputs_do_not_start_search`。既存比較CLIテストのSFEN不正確認は新引数を検査しない |
| 直接予算の引渡し | 目標31ms・上限47msの異なる値と深さ4を使い、`SearchBudget(31, 47)`と4を確認 | 予算欄の入替、ms換算の混入、`calculate_search_budget`接続 | `test_search_uses_direct_budget_and_one_control`。SearchBudget自身の範囲検査は既存`test_time_management.py`が補う |
| 時計原点・依存順 | 固定時計123456789nsを、操作セット生成後・探索直前に一度だけ取得し、同一関数をSearchControlへ渡す | 開始時からの計時、原点の再取得、時計関数の不一致、操作準備を予算へ含める誤り | `test_search_uses_direct_budget_and_one_control`のイベント順・呼出し回数・引数同一性。`test_search_control.py`はSearchControl内部の期限境界を補う |
| 既存探索との接続 | 先手/後手局面で視点と深さを渡し、制御付き反復入口を一度呼ぶ | 停止なし入口・比較探索・誤った視点・複数回探索 | `test_search_uses_direct_budget_and_one_control`。`test_search_iterative_deepening_controlled.py`と`test_search_shogi_controlled.py`はコマンドを介さない探索内部を補う |
| COMPLETE / NO_LEGAL_MOVE | 完了記録の深さ・評価・訪問・累計を表示。合法手なしは選択手・記録なしで、記録項目の全行を出さない | 指定深さを実完了深さと混同、合法手なしを投了/詰み扱い、架空記録や訪問/累計だけの残存 | `test_format_complete_and_no_legal_move`。`test_search_controlled_result.py`と制御付き反復テストは状態データ契約を補う |
| STOPPED | 記録ありならその記録の手と値。記録なしなら予備手、評価なし、完了深さ行なし | 予備手へ評価0/深さ1を捏造、停止原因を目標/上限と断定 | `test_format_stopped_with_and_without_record`。既存結果型テストは値の組合せを補うが表示は検査しない |
| SUPPRESSED | 記録なし/あり両方で選択手なし。記録ありは記録項目だけ保持 | `last_completed`内の手の復活、投了への変換、記録の誤消去 | `test_format_suppressed_never_restores_move`。結果型テストは抑制状態の形を補うがコマンド表示は検査しない |
| 視点・手・評価 | 後手の局面と既存整形済み手/勝敗または符号付き評価を使う | 先手固定、符号反転、手の由来欠落 | `test_format_uses_existing_move_and_score_formatters`、`test_search_uses_gote_as_perspective`。`test_search_comparison.py`は共通整形自体を補う |
| 入力エラーと内部故障 | parser/入力ValueErrorは2。操作生成・時計・探索・整形・出力のValueErrorは伝播 | 広いValueError捕捉で内部故障を入力不正に変換 | `test_internal_value_errors_propagate`。旧CLIの同系統テストは範囲/配置が異なり、新入口固有境界を代替しない |
| Ctrl+C | 解析から表示までのKeyboardInterruptでstderr診断と130。返却前の選択手/記録を表示しない | 0/1で終了、STOPPEDへの誤変換、再探索/結果回収、診断漏れ | `test_keyboard_interrupt_returns_130_without_result_recovery`。単体注入の範囲に限定し、OS・配信タイミングの網羅は主張しない |
| モジュール入口 | ヘルプ0、入力不正2、玉だけ局面の0/0予算は正常終了0とSTOPPED/記録なし | `main`の値をSystemExitへ渡さない、実時間深さを固定期待 | `test_real_process_entrypoint`。既存`test_search_compare_iterative.py`は旧モジュールの入口のみを補う |

表示テストでは、設計で確定した行順も固定する。条件は `入力SFEN`、`評価視点`、`指定上限深さ`、`目標期間(ms)`、`上限期間(ms)`、結果は `終了状態`、`選択手`、`手の由来`、`完了記録` の順。記録ありの場合だけ `完了深さ`、`完了深さの評価`、`完了深さの訪問回数`、`反復累計（完了した深さまで）` の順で続く。NO_LEGAL_MOVEなど記録なしの場合、この四つの記録行すべてを出さない。

単独の新テストはコマンド境界の引数、引渡し、表示、例外を検出する。既存の `test_search_control.py`、`test_search_controlled_result.py`、`test_search_alpha_beta_controlled.py`、`test_search_shogi_controlled.py`、`test_search_iterative_deepening_controlled.py` は制御・結果・探索内部の補完であり、新CLI契約の代替ではない。`test_search_comparison.py`は既存整形、`test_search_compare_iterative.py`は比較コマンドの非変更を確認する。全体テストは結合回帰を確認するが、有限の局面・OS・スケジュールを全て証明しない。

## レビューフォーカス

1. **0msで合法手がある局面:** STOPPEDと合法予備手だけを表示し、深さ・評価・訪問・累計を作らない（タスク3・4）。
2. **完了記録が深さ2、指定上限が3の停止:** 選択手と評価・訪問・累計を同じ深さ2の記録から表示し、深さ3や未完了分を加えない（タスク3）。
3. **SUPPRESSEDで最後の完了記録あり:** 手は「なし」のまま、保持記録だけを示す（タスク3）。
4. **入力準備に遅延があり、時計値が一意:** 原点は操作セット後に一度だけ読み、同じ時計と制御を探索へ渡す（タスク2）。
5. **入力段階と探索段階のどちらからもValueError、任意段階のKeyboardInterrupt:** 入力のみ2、内部故障は伝播、中断は130で、別結果を作らない（タスク1・4）。

## 承認後の実装手順（この文書作成時は未実施）

### 共通のTDD・記録規律

- 各振る舞いについてテスト名・日本語docstring・独立期待値を先に決めてから実装する。
- 新規モジュールや対象関数を読み込めないエラーだけでRed完了としない。必要なら空の解析器や中立値を返す対象関数など、テストから正常に呼べるだけの骨格を用意し、戻り値・引数・出力の対象assertionが失敗することを確認する。既存実装の動作を包む箇所が初回Greenならその事実を記し、偽のRedを作らない。
- 各タスクのGreen後にRefactorの要否を確認し、結果と理由を記録する。レビュー指摘のCritical/Importantは修正後に該当検証と再レビューを行う。テストケース数や全体成功だけで検出力を判断しない。
- importを追加/変更した場合は `.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`、`.venv/bin/ruff check .` の順に実行し、差分を読む。unsafe修正、検査回避、hooksPath変更はしない。

個別テスト実行は `PYTHONPATH=tests .venv/bin/python -m unittest test_search_run_controlled_iterative.RunControlledIterativeTests.<test_name> -v`。新規テストクラスは `RunControlledIterativeTests(unittest.TestCase)` とする。

### タスク1：引数と入力を検査する

**ファイル:** 新規 `kaname_shogi/search/run_controlled_iterative.py`、新規 `tests/test_search_run_controlled_iterative.py`。

**消費:** `comparison.make_parser(description)`、`comparison.parse_position(sfen)`、`SearchBudget(target_ms, maximum_ms)`。

**生産:** `_make_parser() -> argparse.ArgumentParser`、`_prepare_inputs(sfen: str, max_depth: int, target_ms: int, maximum_ms: int) -> tuple[Position, SearchBudget]`。いずれもコマンド内の非公開処理とする。

- [x] **テスト:** `test_parser_requires_explicit_values` と `test_parser_keeps_argparse_duplicate_and_abbreviation_rules` を追加。四引数が全て必須、int変換、同じ引数は最後の値、一意な長い省略形をassertする。
- [x] **Red確認:** `_make_parser` が空の標準解析器を返すだけのimport可能な骨格でテストを実行し、必須引数や標準動作に関するassertionが失敗することを確認する。ImportErrorやテスト探索失敗だけはRedに数えない。
- [x] **最小実装:** 既存SFEN必須パーサーに深さ・二予算を追加する。
- [x] **Green確認:** `PYTHONPATH=tests .venv/bin/python -m unittest test_search_run_controlled_iterative.RunControlledIterativeTests.test_parser_requires_explicit_values test_search_run_controlled_iterative.RunControlledIterativeTests.test_parser_keeps_argparse_duplicate_and_abbreviation_rules -v` が成功する。
- [x] **テスト:** `test_prepare_inputs_rejects_invalid_depth_budget_and_sfen` を追加。深さ0、負予算、目標超過、SFEN不正は `assertRaises(ValueError)`、0/0、等値予算、目標31/上限47msは入力と独立した返却値assertで確認する。
- [x] **Red確認:** `_prepare_inputs` は中立値を返す骨格のまま、呼出し結果または例外型を確かめる対象assertionが失敗することを確認する。関数を読み込めないエラーをRedに数えない。
- [x] **最小実装:** 深さ1以上の検査、直接SearchBudget構築、既存SFEN解析へ委譲する入力準備を実装する。
- [x] **Green確認:** `PYTHONPATH=tests .venv/bin/python -m unittest test_search_run_controlled_iterative.RunControlledIterativeTests.test_parser_requires_explicit_values test_search_run_controlled_iterative.RunControlledIterativeTests.test_parser_keeps_argparse_duplicate_and_abbreviation_rules test_search_run_controlled_iterative.RunControlledIterativeTests.test_prepare_inputs_rejects_invalid_depth_budget_and_sfen -v` が成功する。
- [x] **Refactor・独立レビュー:** 入力補助処理の重複/例外範囲を確認し、Critical/Important/Minorと対応を実装記録へ記す。

### タスク2：原点と制御を一回の探索へ渡す

**ファイル:** `kaname_shogi/search/run_controlled_iterative.py`、`tests/test_search_run_controlled_iterative.py`。

**消費:** タスク1の入力準備、`shogi.make_controlled_operations(perspective)`、`SearchControl(budget, started_ns, now_ns=...)`、`iterative_deepening.search_controlled(node, max_depth, operations, control)`。

**生産:** `_run_search(position: Position, max_depth: int, budget: SearchBudget) -> ControlledSearchResult[Move]`。入力検査済みの一回探索を行う非公開処理。

- [ ] **テスト:** `test_search_uses_direct_budget_and_one_control` と `test_search_uses_gote_as_perspective` を追加する。前者は時計を固定値123456789nsに置き換え、イベント順を「操作セット作成→時計取得→探索呼出し」とassertする。`SearchBudget(31, 47)`、指定深さ4、同じ時計関数、同じSearchControl、探索一回をassertする。後者は後手SFENから `make_controlled_operations(Side.GOTE)` となること、予算・深さ・制御を引き渡すことをassertする。
- [ ] **Red確認:** import可能な骨格を使い、二テストを実行する。読み込みエラーではなく、時計回数/順序、後手視点、または探索へ渡す引数についての対象assertionが失敗することを確認する。
- [ ] **最小実装:** 開始側の `position.side_to_move` から制御操作を一度生成し、その後に一つの単調時計を原点として読み、同じ時計をSearchControlへ明示して一度の同期探索を呼ぶ。
- [ ] **Green確認:** `PYTHONPATH=tests .venv/bin/python -m unittest test_search_run_controlled_iterative.RunControlledIterativeTests.test_search_uses_direct_budget_and_one_control test_search_run_controlled_iterative.RunControlledIterativeTests.test_search_uses_gote_as_perspective -v` が成功する。
- [ ] **Refactor・独立レビュー:** 原点より前/後の仕事と制御再利用の範囲を読み直す。時計や探索のValueErrorを入力エラーへ包んでいないことを確認し、レビュー結論と対応を記録する。

### タスク3：四状態と表示項目を対応させる

**ファイル:** `kaname_shogi/search/run_controlled_iterative.py`、`tests/test_search_run_controlled_iterative.py`。

**消費:** タスク2の探索結果、`ControlledCompletion`、`ControlledSearchResult`、`IterationResult`、既存 `comparison.format_move` / `format_score`。

**生産:** `_format_result(sfen: str, position: Position, max_depth: int, budget: SearchBudget, result: ControlledSearchResult[Move]) -> str`。人向けの最終表示を作る非公開処理。

- [ ] **テスト:** `test_format_complete_and_no_legal_move` を追加。COMPLETEの記録ありは最後の記録深さ・評価・訪問・累計を表示し、条件/結果/記録の行が設計どおりの順序であることをassertする。NO_LEGAL_MOVEは手なし・記録なしとし、完了深さ・評価・訪問回数・反復累計の全行を出さず、投了/詰みを断定する行もないことをassertする。
- [ ] **テスト:** `test_format_stopped_with_and_without_record` を追加。記録なしは合法予備手・評価なしで四つの完了記録行すべてを出さず、記録ありは深さ2・評価1・訪問7・累計10の独立データを使い、それらを同じ深さ2から表示することをassertする。
- [ ] **テスト:** `test_format_suppressed_never_restores_move` を追加。last_completedに手がある結果でも選択手は「なし」、由来は該当なしとし、記録の有無だけに応じて記録項目を出すことをassertする。
- [ ] **テスト:** `test_format_uses_existing_move_and_score_formatters` を追加。後手の視点、既存 `format_move` の手表記と `format_score` の評価表記がそのまま実行条件/記録へ出ることをassertする。
- [ ] **Red確認:** 空文字列を返すだけの `_format_result` 骨格を使い、四つの表示テストで行順・状態ごとの手/記録・既存整形に関する対象assertionが失敗することを確認する。関数やテストの読み込みエラーだけはRedに数えない。
- [ ] **最小実装:** 状態ラベル・手の由来・完了記録の各組合せを承認済み表に対応させ、設計で定めた項目順を保つ。評価と手は既存整形へ委譲する。合法手なしを詰み/投了と断定せず、STOPPED理由を推測しない。
- [ ] **Green確認:** `PYTHONPATH=tests .venv/bin/python -m unittest test_search_run_controlled_iterative.RunControlledIterativeTests.test_format_complete_and_no_legal_move test_search_run_controlled_iterative.RunControlledIterativeTests.test_format_stopped_with_and_without_record test_search_run_controlled_iterative.RunControlledIterativeTests.test_format_suppressed_never_restores_move test_search_run_controlled_iterative.RunControlledIterativeTests.test_format_uses_existing_move_and_score_formatters -v` が成功する。
- [ ] **Refactor・独立レビュー:** 状態ごとに「選択手」と「完了記録」の情報源が混ざっていないこと、完了項目を架空に出していないことを確認し、レビュー結果を記録する。

### タスク4：main・例外境界・プロセス入口をつなぐ

**ファイル:** `kaname_shogi/search/run_controlled_iterative.py`、`tests/test_search_run_controlled_iterative.py`。

**消費:** タスク1〜3の非公開処理。**生産:** 公開 `main(argv: list[str] | None = None) -> int` と `if __name__ == "__main__": raise SystemExit(main())`。

- [ ] **テスト:** `test_main_invalid_inputs_do_not_start_search` と `test_main_help_skips_clock_and_search` を追加。引数解析中のargparse起因 `SystemExit(0)` と `SystemExit(2)` はその終了コードをmainの整数戻り値にし、入力値のValueErrorだけは診断付き2とする。入力不正ではstdout空・stderr診断・操作/時計/探索なし、ヘルプは0で時計/探索なしをassertする。
- [ ] **Red確認:** これらのテストでargparseの終了コード変換、入力ValueErrorの診断と終了値、不要な時計/探索呼出しに関する対象assertionが失敗することを確認する。
- [ ] **テスト:** `test_internal_value_errors_propagate` を追加。操作セット、時計、探索、整形、出力それぞれのValueErrorが入力不正2へ変換されず原因のまま伝わることをassertする。
- [ ] **テスト:** `test_keyboard_interrupt_returns_130_without_result_recovery` を追加。解析から出力までの代表境界でKeyboardInterruptを注入し、130・指定診断・再探索/再表示なしをassertする。出力途中のケースは部分文字列が残り得ることを許容し、完了結果としての再表示がないことを確認する。
- [ ] **Red確認:** import可能なmain骨格で両テストを実行し、内部ValueErrorの同一例外伝播、中断時の130・診断・結果回収なしに関する対象assertionが失敗することを確認する。関数呼出しやテスト探索の失敗だけはRedに数えない。
- [ ] **テスト:** `test_real_process_entrypoint` を追加。`sys.executable -m kaname_shogi.search.run_controlled_iterative` で `--help` は使用法を表示し0、SFEN不正は2、玉だけ局面の0/0予算は0・STOPPED・完了記録なしを確認する。実時間で深さを固定しない。
- [ ] **Red確認:** モジュールがimport可能でプロセスとして起動する骨格を用い、使用法/診断/結果の内容または終了値に関する対象assertionが失敗することを確認する。プロセス起動・モジュール読込み失敗だけはRedに数えない。
- [ ] **最小実装:** parser作成から通常出力までをKeyboardInterrupt捕捉範囲に置く。引数解析中に発生したargparse起因 `SystemExit` のコード0/2を戻り値にし、入力段階だけを2へ変換する。通常結果を一度表示し、通常の戻り値0/2/130を返す。公開 `main` の日本語docstringに引数・戻り値・標準出力/標準エラーの副作用・伝播する例外と前提条件・KeyboardInterruptの挙動・設計理由を記録する。
- [ ] **Green確認:** 専用テストファイル全体を実行し、出力と終了コードを確認する。
- [ ] **Refactor・独立レビュー:** mainの捕捉範囲とプロセス終了値への接続を再確認し、重大度別レビューと対応を実装記録へ記す。

## 全体の検証・完了条件（承認後のみ）

- [ ] `PYTHONPATH=tests .venv/bin/python -m unittest discover -s tests -p test_search_run_controlled_iterative.py -v` を実行する。
- [ ] `PYTHONPATH=tests .venv/bin/python -m unittest test_search_control test_search_controlled_result test_search_alpha_beta_controlled test_search_shogi_controlled test_search_iterative_deepening_controlled test_search_comparison test_search_compare test_search_compare_iterative test_time_management -v` と全体 `.venv/bin/python -m unittest discover -s tests -v` を実行し、既存制御・結果・整形・旧比較入口・予算契約を確認する。件数は合否基準にしない。
- [ ] 隔離コピーでリスクに見合う誤りを一件ずつ注入し、意図したassertionのFAIL、復元後の成功を確かめる。対象は予算値の入替/再計算、時計原点の前倒し・再取得、STOPPED記録なしの深さ1/評価0捏造、SUPPRESSED手復活、内部ValueErrorの2変換、main戻り値のSystemExit未接続。読込みエラーは検出成功に数えない。
- [ ] 文書・コード差分とRefactorの要否を確認し、変更後は該当検証を再実行する。
- [ ] Ruff import整理が必要なら `.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`、`.venv/bin/ruff check .` を行う。`git diff --check` と対象差分確認も行う。
- [ ] 新鮮な独立レビュアーへ承認済み設計・本計画・実差分・検証・未検証事項を渡す。Critical/Importantを修正して再検証・再レビューし、Minorの採否も学習記録に残す。
- [ ] 実施内容、実際のRed/Green、代表変異、既存テストの補完、独立レビュー、限界を学習記録へ記録する。学習記録・索引・再開案内を確認してから通常コミットする。main取り込みは別承認後に行う。

### 既存テストと今回の作業だけでは確認しない範囲

実時間性能・上限ms内の応答、すべてのSFEN/局面、すべてのOS/シグナル競合、実プロセスSIGINT配送と出力原子性、USIや通常対局との新方式競合、棋力・最適予算は保証しない。0msの実プロセス例は接続の代表例であり、時間性能試験ではない。設計レビューや文書検査、過去の探索部品テスト結果を今回の製品実測として扱わない。

## 実行方式の選択

主担当が `executing-plans` を使って順に実装する方式と、タスクごとに実装者を分ける方式を提示した。共有するコマンドモジュールとテストファイルへ変更が集中するため、順次実装を推奨し、本人は「順次実装（推奨）」を選択した。`using-git-worktrees` の確認に対し、本人は現在のcheckout内の作業ブランチを選択した。実装者は主担当が継続し、各タスクの独立レビューと全タスク後の新鮮な独立ブランチレビューを受ける。

## 計画レビュー・提示状態

初回の独立レビューはCritical 0 / Important 2 / Minor 2。argparseの終了コードとTDD順序の矛盾をImportantとして直し、公開mainのdocstring要件、記録なしで表示しない全項目、表示順のアサーションも追加した。二回目のレビューではそれらの反映を確認したうえで、表示群と例外境界群のRed確認が明示されていない点をImportant 1件として指摘された。各対象assertionのRed確認を最小実装前へ追記した。

最終の独立レビューはCritical 0 / Important 0 / Minor 0。SystemExit(0)/(2)と入力ValueErrorの境界、各振る舞いのRed順、表示契約、docstring、回帰コマンド、範囲と承認境界の維持を確認済み。レビューは読み取り専用で、コード・テスト・文書を変更せず、製品テストも実行していない。

計画全体の明示承認済み。本人は順次実装と現在のcheckout内の作業ブランチを選択済み。`codex/controlled-iterative-search-command` を `f8429f8` から作成し、計画用ワークスペースと共有インターフェースのプリフライトを完了した。Task 1のTDD・レビューを完了し、Task 2を次に始める。通常対局・USIへの新方式接続、予算式変更、時間保証は引き続き対象外。
