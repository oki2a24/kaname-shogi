# 終局理由の拡張 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** CLIで手番側の `resign` を受け付け、投了側と勝者を表示して局面を変えずに対局を終了する。

**アーキテクチャ:** `cli.py` の入力指示に投了を表す内部データを追加する。`run_game` は詰みを入力前に確認し、投了は入力イベントとして終了させる。局面から判定する `movegen.is_game_over` は詰みだけを返す既存責務を維持する。

**技術スタック:** Python 3.9、標準ライブラリ `dataclasses`・`typing`・`unittest`・`unittest.mock`、Git。

**仕様 (Spec):** `docs/plans/2026-09-23-game-end-reasons-design.md`

**グローバル制約 (Global Constraints):**

- 説明・学習記録・知識メモは日本語で書く。
- 公開インターフェースのdocstringには、引数・戻り値・副作用・前提条件と設計理由を記録する。
- テストメソッド名は英語とし、日本語docstringで振る舞いと検出したい誤りを説明する。
- 読み込みエラーではないRed、最小実装、Green、Refactor確認、独立レビューを順に行う。
- CriticalまたはImportantのレビュー指摘は、解消・再検証・再レビュー後に文書化する。
- コミットメッセージは日本語のConventional Commit形式にする。
- 投了は半角ASCIIの `resign` だけを受け付け、投了側と相手の勝利を表示する。
- 詰みは入力前に優先判定し、EOF/Ctrl-Cは投了・勝敗にせず正常終了する。
- 承認前にコード・テストを変更しない。作業は `codex/game-end-reasons` で行い、mainへの取り込みは全検証と本人承認後に限る。

---

## ファイル構成

- 変更 `kaname_shogi/cli.py`: 投了の内部指示、解析、投了表示、対局終了を追加する。
- 変更 `tests/test_cli.py`: 投了の解析、形式エラー、先後の投了、詰み・EOF/Ctrl-Cの維持を検証する。
- 変更 `README.md`: `resign` の入力形式、投了時の表示、対象外の終局理由を更新する。
- 作成 `docs/knowledge/28-game-end-reasons.md`: 詰みと投了の区別、CLIの確定仕様、一次資料を参照メモにする。
- 作成 `docs/learning/35-game-end-reasons.md`: 質問回答、設計承認、TDD、レビュー、検証、最後の理解確認を事実に基づいて記録する。
- 変更 `docs/plans/2026-09-23-game-end-reasons.md`: 実施済みのチェックと実際の結果を更新する。

## タスク1: 投了入力と終局進行をTDDで追加する

**ファイル:**
- 変更: `tests/test_cli.py`
- 変更: `kaname_shogi/cli.py`

**インターフェース (Interfaces):**
- 消費: `parse_command(text: str)`、`run_game(*, input_fn: Callable[[], str] = input, output_fn: Callable[[str], None] = print)`、`Position.side_to_move`
- 生産: `_ResignCommand`、`_resignation_message(side_to_move: Side) -> str`、投了を扱う拡張済み `parse_command` と `run_game`

- [x] **ステップ1: 失敗する解析・進行テストを作成する**

  `tests/test_cli.py` に、`resign` が移動や駒打ちと区別できる指示を返すテスト、`resign now` と `ｒｅｓｉｇｎ` を形式エラーにするテストを追加する。さらに、初期局面で先手が投了するテストと、先手の一手の後に後手が投了するテストを追加する。各進行テストは、正しい終了文言、入力回数、開始局面または一手後局面が投了で変更されないことを確認する。

  ```python
  def test_parses_resign_command(self):
      """resignを、局面を変更しない投了指示へ変換する。"""
      command = cli.parse_command("resign")

      self.assertIsInstance(command, cli._ResignCommand)


  def test_stops_when_sente_resigns(self):
      """先手が投了すると、局面を変えず後手の勝ちを表示して終了する。"""
      inputs = ScriptedInput(["resign"])
      outputs = []

      cli.run_game(input_fn=inputs, output_fn=outputs.append)

      self.assertEqual(inputs.calls, 1)
      self.assertIn("先手が投了しました。後手の勝ちです。", outputs)
  ```

  既存の詰み・EOF・Ctrl-Cテストには、投了文言が含まれないことも追加する。

- [x] **ステップ2: 読み込みエラー以外のRedを確認する**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v`

  期待値: 現時点では `resign` が `ValueError("入力形式が正しくありません。")` となるため、投了解析と投了進行のアサーションが失敗する。既存テストは成功し、新しいテストの失敗理由が機能未実装であることを確認する。

- [x] **ステップ3: 最小実装を追加する**

  `cli.py` に空の凍結データクラス `_ResignCommand` を追加し、`parse_command` の返り値Unionへ含める。`parts == ["resign"]` のときだけこれを返し、他の形式は既存どおり `FORMAT_ERROR` にする。

  ```python
  @dataclass(frozen=True)
  class _ResignCommand:
      """投了の入力を、局面を変更しない終局指示として保持する。"""


  def _resignation_message(side_to_move: Side) -> str:
      loser_name = "先手" if side_to_move == Side.SENTE else "後手"
      winner_name = "後手" if side_to_move == Side.SENTE else "先手"
      return f"{loser_name}が投了しました。{winner_name}の勝ちです。"
  ```

  `run_game` で入力解析後、`_ResignCommand` なら `_resignation_message(position.side_to_move)` を出力して戻る。`_apply_command` は盤上移動・駒打ちだけを受け取るように保つ。`run_game` と `parse_command` のdocstringを、投了の入力・局面不変・詰み優先・EOF/Ctrl-Cとの差が分かる内容へ更新する。

- [x] **ステップ4: Greenを確認する**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v`

  期待値: 新旧のCLIテストが全て成功する。先後の投了は正しい勝者を表示し、既存の詰み・EOF・Ctrl-Cの挙動は変わらない。

- [x] **ステップ5: Refactor要否を確認し、対象変更をコミットする**

  `parse_command` が文字列解析だけ、`_resignation_message` が表示文字列作成だけ、`run_game` が進行だけを担い、投了判定を `movegen.py` や `Position` へ広げていないことを確認する。抽出が不要なら、その理由を学習記録へ残す。

  ```sh
  git add kaname_shogi/cli.py tests/test_cli.py
  git commit -m "feat: CLIで投了による終局を扱う"
  ```

## タスク2: 独立レビュー、記録、全検証、取り込み準備を行う

**ファイル:**
- 変更: `README.md`
- 作成: `docs/knowledge/28-game-end-reasons.md`
- 作成: `docs/learning/35-game-end-reasons.md`
- 変更: `docs/plans/2026-09-23-game-end-reasons.md`

**インターフェース (Interfaces):**
- 消費: タスク1のCLI挙動、設計仕様、一次資料、テスト結果、独立レビュー結果
- 生産: 利用者向けの入力説明、確定知識、実施事実を記した学習記録、更新済み実装計画

- [x] **ステップ1: 独立コードレビューを実施する**

  設計仕様と実装差分を渡した独立レビュアーに、`resign` の厳密な形式、先後の勝者表示、局面不変、詰み優先、EOF/Ctrl-Cとの差、docstring、既存挙動への回帰を確認させる。Critical・Important・Minorを区別して記録する。CriticalまたはImportantがあれば、先に修正し、対象テスト・全テストを再実行して再レビューする。

- [x] **ステップ2: 利用者向け・学習用文書を更新する**

  READMEのCLI入力説明に `resign` と投了時の終了文言を加え、詰みと投了を扱い、他の終局理由は未実装と記す。知識メモには、公式規則、局面判定と入力イベントの区別、EOF/Ctrl-Cとの差を記す。学習記録には、4つの確認問題の本人の回答、設計承認、Red/Greenの実結果、Refactor判断、レビュー結論、検証結果を、実施済みの事実だけで記す。

- [x] **ステップ3: 全検証を実行する**

  ```sh
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
  printf 'resign\n' | PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi
  git diff --check
  git status --short --branch
  ```

  期待値: 全テストが成功し、実CLIは初期局面の後に先手投了・後手勝ちを表示して終了する。差分チェックは出力なしとする。

- [x] **ステップ4: 記録をコミットし、mainへの取り込み承認を求める**

  ```sh
  git add README.md docs/knowledge/28-game-end-reasons.md \
      docs/learning/35-game-end-reasons.md \
      docs/plans/2026-09-23-game-end-reasons.md
  git commit -m "docs: 投了による終局の学習記録を追加する"
  ```

  作業ブランチのコミット、レビュー結論、検証結果を報告し、本人の明示承認を受けるまでmainへ取り込まない。承認後はmainで全テスト、実CLI、差分チェックを再実行する。最後に理解確認を一問だけ出し、本人の回答と補足を学習記録へ追記してコミットする。

## 計画の自己レビュー

- 仕様の入力形式、投了側・勝者表示、局面不変、詰み優先、EOF/Ctrl-Cとの差をタスク1へ対応付けた。
- Red、最小実装、Green、Refactor、独立レビュー、全検証、記録、main取り込み承認を順に記した。
- 将来の終局結果型や局面履歴を先取りせず、`cli.py` と `tests/test_cli.py` だけをコード変更対象にした。
- 実行コマンドと期待される失敗・成功理由を具体化し、未決定のプレースホルダを残していない。
