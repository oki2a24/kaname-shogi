# 千日手ルール実装計画

> 状態：2026-10-22、本人が「承認する」と明示承認。実施内容・検証・レビュー結果は本計画末尾の実施記録と[学習記録](../learning/repetition-rule-design.md)に残す。
>
> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。各ステップには進捗確認用チェックボックスを使用します。

**目標:** 全履歴から通常千日手と連続王手を判定し、通常CLIで選択された4回目の続行・打開後再出現・終局表示を実現する。

**アーキテクチャ:** `GameRecord` に開始局面からの一回再生APIを加え、新しい `RepetitionTracker` が同一局面キーと実着手の王手履歴から結果を返す。通常CLIは合法手適用後と棋譜読込後にこの部品を更新し、終局時に表示して一局を終了する。既存の棋譜v1形式は維持する。

**技術スタック:** Python 3.9互換の標準ライブラリ、既存の `unittest`、既存の `Position`・`GameRecord`・`movegen.is_in_check`。

**仕様 (Spec):** [千日手ルール設計案](2026-10-22-repetition-rule-design.md)（本人が2026-10-22に本計画とともに明示承認）

## グローバル制約 (Global Constraints)

- すべての説明・docstring・学習記録は日本語で書き、テストメソッド名は英語、docstringは日本語とする。
- 公開する型・操作のdocstringに引数・戻り値・副作用・前提条件と設計理由を記録する。
- 指示・応答は日本語で行う。Python 3.9互換を維持し、依存ライブラリを追加しない。
- 座標の説明は筋・段を基本とし、xyを内部座標への要望と解釈しない。
- 既存棋譜v1の保存形式を維持する。千日手結果欄・自動保存は追加しない。
- 通常CLIのSFEN入出力、USI接続、探索反復、早期合意操作、比較CLI接続は今回の対象外。比較CLIは後続P2の計画で同じ判定部品を利用する。
- 未決定の将来機能を先取りしない。mainで実装せず、承認後に `codex/repetition-rule` の作業ブランチで行う。
- 実装変更ごとに、対象契約のRed、最小実装、Green、Refactor要否を確認する。読み込みエラーだけではRedと数えない。
- テスト点検は `docs/knowledge/test-coverage-review.md` と `~/.codex/observations/test-driven-development.md` の検出力・範囲方針に従う。
- Python変更時はプロジェクト手順どおりimport整列・format・ruff check・差分確認・変更に見合うテストを行う。独立レビューでCritical/Importantがあれば修正・再検証・再レビューする。

## レビューフォーカス (Review Focus)

1. 盤面のみ一致して手番または双方の持ち駒が異なる場合、千日手にせず対局を続ける。
2. 保存棋譜の4回目で連続王手をした側が負け、4回目が通常千日手ならCLIを終了せず続行案内を出す。
3. 通常4回目の後に同一局面が戻ったとき、5回目を直近の出現2〜5回目の区間で判定し、最初の区間だけを見る誤りを避ける。
4. 読込履歴の終端ですでに千日手成立なら次の入力を受け付けず、合法手が失敗した場合に履歴・反復状態を進めない。
5. コンピュータ探索の仮想局面、無効な入力、棋譜外の局面を実対局履歴へ混ぜず、既存保存形式へ結果欄を誤追加しない。

---

## 実行前提

- この計画と設計案は2026-10-22に本人が明示承認した。開始HEADは `1b69147`、開始ブランチは `main`。実装は隔離した作業ブランチ `codex/repetition-rule` で行った。mainへの取り込みは別途本人承認を得る。
- TDDの各段階は該当する標準 `unittest` を実行する。テストメソッド名と日本語docstringはプロジェクト方針に合わせる。
- `tests/test_game_record.py` と `tests/test_cli.py` の既存構造を確認し、過度な共通化や新しいテスト基盤を追加しない。
- 下記のコマンドは承認後の実行予定であり、計画作成時には実行していない。

### タスク 1: GameRecordの一回履歴再生

**ファイル:**

- 変更: `kaname_shogi/game_record.py`
- テスト: `tests/test_game_record.py`

**インターフェース:**

- 生産: `GameRecord.iter_positions(self) -> Iterator[Position]`。開始局面と各成功手後の独立複製を順番に返す。
- 消費: 既存の `initial_position`、`moves`、`apply_move`、`apply_drop` と同じ合法手適用操作。

- [x] **ステップ1: 失敗するテストを作成**

  `test_iter_positions_includes_initial_and_each_successful_move` で、開始局面と複数の盤上移動・駒打ち後の順序、最終値を手書き期待値と照合する。`test_iter_positions_returns_independent_snapshots` で返却値を変更しても棋譜と後続値が変わらないこと、`test_iter_positions_does_not_mutate_record` で現在局面・成功手数の維持を確認する。

- [x] **ステップ2: 対象テストを実行して意図した失敗を確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_game_record.py' -v`

  期待値: 新しい操作がないため、属性エラーまたは未実装による失敗。読込・importエラーだけの場合はRed完了と扱わない。

- [x] **ステップ3: GameRecord.iter_positions() を実装**

  `Iterator` を使い、内部の開始局面コピーを一度だけ進める。開始局面と各手後に別々の `Position.copy()` をyieldし、盤上移動・駒打ちは `GameRecord.position_at()` / `from_payload()` と同じ既存適用操作へ委譲する。

- [x] **ステップ4: 対象テストが成功することを確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_game_record.py' -v`

  期待値: 対象モジュール全件PASS。

- [x] **ステップ5: Task 1の変更を確認**

  実行: `.venv/bin/ruff format kaname_shogi/game_record.py tests/test_game_record.py`、`.venv/bin/ruff check kaname_shogi/game_record.py tests/test_game_record.py`、`git diff --check`、`git diff`。

  期待値: 整形・静的検査・差分検査が成功し、Task 1の変更範囲を確認する。コミットは全体レビュー後にまとめる。

### タスク 2: 同一局面・出現窓・連続王手の判定部品

**ファイル:**

- 作成: `kaname_shogi/repetition.py`
- 作成: `tests/test_repetition.py`

**インターフェース:**

- 消費: Task 1の `GameRecord.iter_positions()`、既存 `Position`、`Side`、`Board.piece_at()`、`Hand.count()`、`movegen.is_in_check()`。
- 生産: `RepetitionOutcomeKind`、不変データ `RepetitionOutcome(kind, losing_side=None)`、`RepetitionTracker(initial_position)`、`RepetitionTracker.add_position(position) -> RepetitionOutcome`、`RepetitionTracker.from_positions(positions) -> RepetitionTracker`、読み取り値 `current_outcome`。状態には、双方が連続王手に該当する未裁定を表す `UNRESOLVED_DOUBLE_PERPETUAL_CHECK` も含める。
- `from_positions` は空入力を `ValueError` にし、先頭を初期局面、残りを一手後の局面として再生する。終局の後に局面が続けば `ValueError` にする。

- [x] **ステップ1: 失敗するテストを作成**

  `test_repetition_key_includes_board_hands_and_turn` で盤上駒1枚、双方の持ち駒の各1枚、手番を一つずつ変えた局面を別キーにする。通常循環は玉と飛車だけの初期局面（先手玉9九、先手飛車4九、後手玉5一）とし、手順 `4i4h, 5a6a, 4h4i, 6a5a` を3回実行して、開始局面を含む同一局面の総出現回数を4回にする。`test_fourth_ordinary_occurrence_continues` は4回目を続行、`test_fifth_occurrence_ends_as_repetition` は同じ循環をもう1回実行して総出現5回目で通常千日手を確認する。`test_fourth_occurrence_of_continuous_check_loses` は手順 `4i5i, 5a4a, 5i4i, 4a5a` を3回実行し、4回目で先手連続王手負けを確認する。後手側への固定誤りを検出するため、同じ条件を手番と配置を反転した`test_fourth_occurrence_of_gote_continuous_check_loses`でも確認する。`test_fifth_occurrence_checks_latest_four_occurrences` は非王手循環を1回、続けてこの王手循環を3回実行し、4回目は続行・5回目は先手負けを確認する。`test_both_sides_continuous_check_returns_unresolved` は判定用の王手履歴を制御して両側該当を通常千日手や片側負けへ誤分類しないこと、`test_add_position_after_terminal_raises` と `test_from_positions_rejects_moves_after_terminal` は終局後の履歴追加・読込を拒否すること、`test_from_positions_reconstructs_outcome` は棋譜履歴再生後の状態を照合する。

- [x] **ステップ2: 対象テストを実行して意図した失敗を確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_repetition.py' -v`

  期待値: 新しい型・操作がないため対象の振る舞いで失敗。テストデータの不正な局面構築だけで失敗する場合はRedに数えない。

- [x] **ステップ3: kaname_shogi/repetition.py に判定部品を実装**

  キーは81マスの駒種・所有者、両手の7種枚数、手番の完全な値とする。出現位置は各キーの最新4件を保持し、各実着手後に「移動側・王手有無」を保存する。出現4件の間で一方の全着手が王手ならその側の負け、通常4回目は続行、通常4回目後の再出現では最新4件の間を調べて連続王手または通常千日手を返す。双方が条件を満たす場合は `UNRESOLVED_DOUBLE_PERPETUAL_CHECK` を返す。`is_in_check` には直後の局面で手番側を渡し、その側が王手中なら直前の手番側を王手側とする。

- [x] **ステップ4: 対象テストが成功することを確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_repetition.py' -v`

  期待値: 対象モジュール全件PASS。代表的な同一性差分と、最初の窓・直近の窓を個別に照合する。

- [x] **ステップ5: Task 2の変更を確認**

  実行: `.venv/bin/ruff format kaname_shogi/repetition.py tests/test_repetition.py`、`.venv/bin/ruff check kaname_shogi/repetition.py tests/test_repetition.py`、`git diff --check`、`git diff`。

  期待値: 整形・静的検査・差分検査が成功し、Task 2の変更範囲を確認する。コミットは全体レビュー後にまとめる。

### タスク 3: 通常CLIの実着手と終局表示

**ファイル:**

- 変更: `kaname_shogi/cli.py`
- テスト: `tests/test_cli.py`
- テスト: `tests/test_repetition.py`（必要な場合は境界単位テストのみ）

**インターフェース:**

- 消費: Task 2の `RepetitionTracker` と `RepetitionOutcome`。人間手 `GameRecord.apply_move/apply_drop`、自動手 `_apply_selected_move`。
- 生産: 通常CLIの人間同士・人間対コンピュータ・コンピュータ同士で、成功手後だけ反復状態を一度更新し、終局表示後に `GameRecord` を返す。

- [x] **ステップ1: 失敗するCLIテストを作成**

  `test_fourfold_ordinary_position_displays_continuation_and_accepts_move` で4回目に即終了せず次の合法入力を受け付けることを確認する。`test_computer_vs_computer_repetition_stops_after_fifth_occurrence` で5回目に通常千日手を表示し後続入力を読まないこと、`test_perpetual_check_repetition_displays_checker_loss` で王手側と勝者を逆にしないこと、両側該当なら未裁定表示で勝者を作らないことを確認する。`test_invalid_move_does_not_advance_repetition_history` で不正手の再入力中に履歴数が増えないことを確認する。機械対局経路にも同じ判定部品が接続されることを確認する。

- [x] **ステップ2: 対象テストを実行して意図した失敗を確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_cli.py' -v`

  期待値: 千日手時の表示・終了がまだないことによる振る舞いの失敗。テストの入力不足や読み込み失敗だけでRed完了としない。

- [x] **ステップ3: cli.py の成功手境界へ追跡を接続**

  人間の合法入力とコンピュータの合法手が `GameRecord` に適用された後で一度だけ `add_position()` を呼ぶ。両経路の表示文言を設計案どおりに固定する。探索開始・探索中・抑制・時間切れ・失敗手では追加しない。通常千日手・連続王手負け・双方連続王手の未裁定結果で当該ゲームループを終了する。

- [x] **ステップ4: 対象CLIテストが成功することを確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_cli.py' -v`

  期待値: 対象モジュール全件PASS。既存の投了・詰み・読込・時計経路の期待値を壊さない。

- [x] **ステップ5: Task 3の変更を確認**

  実行: `.venv/bin/ruff format kaname_shogi/cli.py tests/test_cli.py`、`.venv/bin/ruff check kaname_shogi/cli.py tests/test_cli.py`、`git diff --check`、`git diff`。

  期待値: 整形・静的検査・差分検査が成功し、Task 3の変更範囲を確認する。コミットは全体レビュー後にまとめる。

### タスク 4: 読込時の履歴再構成

**ファイル:**

- 変更: `kaname_shogi/cli.py`
- テスト: `tests/test_cli.py`

**インターフェース:**

- 消費: Task 1の `GameRecord.iter_positions()`、Task 2の `RepetitionTracker.from_positions()` と `current_outcome`。
- 生産: `load` 成功後に保存全履歴から状態を再構築し、終端が千日手成立なら次の入力を受けず終了。既存v1ペイロードは変えない。

- [x] **ステップ1: 失敗する読込テストを作成**

  `test_loading_record_rebuilds_repetition_history` で4回目通常千日手の途中保存を読んでも続行できること、`test_loading_record_at_repetition_end_does_not_accept_move` で終局位置で保存された棋譜を読んだとき再入力へ進まないこと、`test_loading_post_terminal_record_preserves_current_session` で終局後の指し手を含む過去棋譜を拒否し読込前の棋譜・時計を保つことを確認する。`test_saved_payload_has_no_repetition_result_field` で既存v1キーだけが保存されることを確認する。

- [x] **ステップ2: 対象テストを実行して意図した失敗を確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_cli.py' -v`

  期待値: 読込後にトラッカーを再構築しないことによる状態不一致の失敗。

- [x] **ステップ3: 読込経路を実装**

  読み込んだ候補セッションの全位置を一回再生して候補トラッカーを作る。再構成が成功した後にだけ棋譜・時計・トラッカーをまとめて置き換える。読込終端が終局なら千日手結果を表示して終了し、4回目の通常千日手なら継続できる状態を保つ。履歴の途中に終局があり後続手も保存されている場合は、読込前の棋譜・時計を保って読込を拒否する。比較CLIの別集計方針は変更しない。

- [x] **ステップ4: 読込・保存テストが成功することを確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_cli.py' -v` と `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_game_record.py' -v`

  期待値: 両対象モジュール全件PASS。通常開始、読込再開、終局読込の状態が期待どおり。

- [x] **ステップ5: Task 4の変更を確認**

  実行: `.venv/bin/ruff format kaname_shogi/cli.py tests/test_cli.py`、`.venv/bin/ruff check kaname_shogi/cli.py tests/test_cli.py`、`git diff --check`、`git diff`。

  期待値: 整形・静的検査・差分検査が成功し、Task 4の変更範囲を確認する。コミットは全体レビュー後にまとめる。

### タスク 5: 全体確認と独立レビュー

**ファイル:**

- 対象: Task 1〜4の変更すべて
- 文書: `README.md`、`docs/README.md`、`docs/resume.md`、`docs/learning/repetition-rule-design.md`
- 確認: `docs/knowledge/test-coverage-review.md` とTDD観測メモ

**インターフェース:**

- 消費: 各タスクで追加したテスト・実装と、承認済み設計。
- 生産: 全体検証結果、Critical/Important/Minor別の独立レビュー記録、未検証範囲と修正結果、内容確認済みの文書更新と最終コミット。

- [x] **ステップ1: 変更ファイル全体の検査**

  実行: `.venv/bin/ruff format --check .`、`.venv/bin/ruff check .`、`git diff --check`。

  期待値: すべて成功。import変更がある場合は個別確認の上で `.venv/bin/ruff check --select I --fix .` を行ってから再整形・再検査する。

- [x] **ステップ2: 全ユニットテストを実行**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_tests_parallel.py`

  期待値: 発見された全テストが成功。必要な場合だけ共有状態・順序依存を逐次 `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` で診断する。

- [x] **ステップ3: 代表誤りと検出範囲を照合**

  キー項目の欠落、4回目で早期終了、4回目で連続王手負けを見逃す、5回目で古い窓を使う、王手側と敗者を逆にする、読込後履歴の消失、失敗手の履歴混入、保存形式の不用意な変更、両側連続王手を勝敗へ誤変換する問題を点検する。各テストの独立期待値、単独・全体での検出範囲、未検証事項を学習記録に記録する。

- [x] **ステップ4: Refactor要否を確認して独立レビュー**

  新鮮な視点で差分をレビューし、Critical/Important/Minorを分ける。CriticalまたはImportantがあれば修正、関連テスト・全体検証、独立再レビューを繰り返す。レビュー記録は学習記録に追記し、フック成功だけをレビュー代わりにしない。

- [ ] **ステップ5: 文書を更新し、内容確認後に実装をコミット**

  独立レビューと修正後の検証結果に基づき、実際の変更・検証・レビュー・制限を設計案と照合する。README・索引・再開案内・学習記録を更新し、相対リンクと差分を確認してから、対象ファイルをステージして作業ブランチにコミットする。mainへの取り込みは別途本人承認を得る。本人の最終理解確認は取り込み先の検証後に一問だけ行い、その回答を待つ。

## セルフレビュー

- 設計案の要件はタスク1（線形履歴再生）、タスク2（同一性と反復区間）、タスク3（実着手と結果表示）、タスク4（読込再構築と保存形式維持）、タスク5（全体検査とレビュー）へ対応付けた。
- 公開型・操作名・戻り値は後続タスクで一致させた。設計案と実装計画は2026-10-22に本人が明示承認し、Task 1〜4を実施した。
- レビューフォーカス5件をタスク別テストへ対応させた。変異検査、実時間性能、探索履歴、USI、早期合意はこの計画の検証対象に含めない。両側が同時に連続王手となる場合は資料に裁定がないため、別結果として扱うテストを計画し、通常千日手や片側負けへ推測で変換しない。
- 計画作成時点では製品テストを実行していない。その後の実行結果とレビュー記録は、実施結果欄と学習記録に追記する。

## 実施結果（2026-10-22）

- Task 1〜4を承認済み範囲で実装。作業ブランチは `codex/repetition-rule`、worktreeは `/Users/oki2a24/.codex/worktrees/repetition-rule/kaname-shogi`。通常CLIの人間対人間・人間対コンピュータ・コンピュータ対コンピュータを対象にし、比較CLI・USI・探索・通常CLI SFEN・早期合意・自動指し直しは接続していない。既存棋譜v1の項目も維持した。
- 全体コマンド `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py` は661件・42モジュールが15.013秒で成功。対象モジュールは `test_game_record.py` 19/19、`test_repetition.py` 11/11、`test_cli.py` 58/58、`test_cli_time_control.py` 18/18。Python 3.9文法解析も成功。
- `.venv/bin/ruff format --check .` は78ファイル整形済み、`.venv/bin/ruff check .` と `git diff --check` は成功。Ruff二コマンドを共有キャッシュへ同時実行した際の一時ファイル作成失敗後、コマンドごとに異なる `RUFF_CACHE_DIR` を指定して順番に再実行し成功した。
- 独立した隔離変異7件（手番キー除外、敗者先手固定、古い判定窓、共有スナップショット、読込履歴リセット、不正手の履歴加算、盤上配置位置の無視）は、各対応テストの期待アサーションで失敗した。位置キーから盤上配置を無視する変異は `test_repetition_key_includes_board_hands_and_turn` 単独で確認し、読み込みエラーは検出成功に数えていない。
- Refactor確認では、責任ごとの実装がまとまっており、追加抽象化の利益を示す重複がないため構造変更をしなかった。検出範囲、代表ケース、単独/全体の補完、未検証事項は[学習記録](../learning/repetition-rule-design.md)に記録した。
- 初回独立レビューの文書Important指摘をREADME・索引・承認記録で修正し、配置位置テストを補強した。最終独立レビューはCritical 0 / Important 0 / Minor 2。Minorは昇格状態・複数枚の持ち駒差を個別検査するテストと、load失敗後の追跡器保持を振る舞いで検査するテストで、学習記録へDeferredとして記録した。main取り込みは別承認である。
