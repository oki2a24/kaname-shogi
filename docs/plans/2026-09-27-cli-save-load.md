# 第42回「CLIでの明示的な保存・読込」実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: 実装時には `executing-plans` スキルを起動し、各ステップをチェックボックスで追跡する。

**目標:** CLI対局中に `save <path>` と `load <path>` を受け付け、既存JSON棋譜を明示的に保存・再開できるようにする。

**アーキテクチャ:** `GameRecord` は既存のJSON変換・検証・再適用を変更せず担う。`cli.py` は保存・読込を表す入力値を解析し、対局ループでファイル操作、成功表示、失敗時の再入力、読込成功時の記録置換を担う。

**技術スタック:** Python 3.9標準ライブラリ、`unittest`、`pathlib.Path`、既存の `GameRecord`。

**仕様 (Spec):** `docs/plans/2026-09-27-cli-save-load-design.md`

**グローバル制約 (Global Constraints):**

- 人間担当の手番で、半角ASCIIの `save <path>` と `load <path>` を受け付ける。
- `<path>` は空白を含まない一語とし、相対・絶対パスを受け付ける。親ディレクトリは自動作成しない。
- `GameRecord` とJSON保存形式は変更しない。
- 失敗した保存・読込は局面・手番・履歴を変更せず、同じ人間手番で再入力する。
- `load` 成功時だけ記録を完全に置き換え、局面を表示して読込後の担当に従う。保存・読込・終了イベント・エラーは履歴に残さない。
- 詰み、投了、EOF、Ctrl-C、コンピュータの合法手空一覧は既存動作を保ち、終了後には入力を受け付けない。自動保存は追加しない。
- 公開APIのdocstringとテストの日本語docstringはプロジェクト方針に従って更新する。

---

## ファイル構成

- `kaname_shogi/cli.py`: コマンド値、入力解析、対局進行を変更する。
- `tests/test_cli.py`: 解析、保存、読込、失敗時再入力、終了境界、履歴置換を検証する。
- `README.md`: CLI利用方法を更新する。
- `docs/learning/42-cli-save-load.md`: 学習・TDD・レビュー・検証を記録する。
- `docs/knowledge/30-game-record-file-save.md`: `GameRecord` とCLIの責務境界を追記する。
- `docs/02-project-direction.md`: 第42回完了時点を追記する。
- `docs/next-topics.md`、`docs/resume.md`: 最後の理解確認への本人回答後だけ更新する。

`kaname_shogi/game_record.py` は変更しない。

### タスク1: 保存・読込入力を解析する

**ファイル:** `tests/test_cli.py: CommandParsingTests`、`kaname_shogi/cli.py: parse_command`

**生産するインターフェース:** `_SaveCommand(path: str)` と `_LoadCommand(path: str)`。いずれもファイル操作をしない不変データ。

- [x] **ステップ1: 失敗するテストを追加する**

```python
def test_parses_save_and_load_commands(self):
    """save/loadの一語パスを、ファイル操作前の指示へ変換する。"""
    save = cli.parse_command("save records/game.json")
    load = cli.parse_command("load /tmp/game.json")
    self.assertIsInstance(save, cli._SaveCommand)
    self.assertEqual(save.path, "records/game.json")
    self.assertIsInstance(load, cli._LoadCommand)
    self.assertEqual(load.path, "/tmp/game.json")
```

`"save"`、`"load"`、`"save a b"`、`"load a b"` を入力形式エラーとして拒否するテストも追加する。

- [x] **ステップ2: Redを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.CommandParsingTests -v`

期待値: コマンド値が未定義、または`save`/`load`が形式エラーとなりFAILする。読み込みエラーだけではないことを確認する。

- [x] **ステップ3: 最小実装を加える**

`cli.py`に不変の`_SaveCommand`と`_LoadCommand`を追加し、`parse_command`が`parts == ["save", path]`または`parts == ["load", path]`のときだけ対応するコマンド値を返すようにする。戻り値型注釈・docstringを更新し、ここに`Path`変換、ファイル操作、JSON検証は追加しない。

- [x] **ステップ4: Greenを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.CommandParsingTests -v`

期待値: 追加した解析テストを含めてPASSする。

- [x] **ステップ5: コミットする**

実行: `git add kaname_shogi/cli.py tests/test_cli.py && git commit -m "feat: CLIの保存読込入力を解析する"`

### タスク2: CLI進行で保存・読込する

**ファイル:** `tests/test_cli.py: GameplayTests`、`kaname_shogi/cli.py: run_game`

**消費するインターフェース:** `_SaveCommand.path`、`_LoadCommand.path`、`GameRecord.save(path)`、`GameRecord.load(path) -> GameRecord`。

**生産するインターフェース:** `run_game(...) -> GameRecord` は、`load` 成功時には読込済み記録を返し、その後の成功手をその末尾へ追加する。失敗時には元の記録を返す。

- [x] **ステップ1: 失敗する対局進行テストを追加する**

一時ディレクトリを使い、次の4件を追加する。保存成功後は同じ人間手番で入力を受け直すこと、後手番の記録をloadすると局面表示後にコンピュータが指すこと、load失敗後の`move`だけが元記録へ入ること、親ディレクトリがないsave失敗後も同じ手番で`move`できることを確認する。

```python
def test_save_keeps_position_and_reprompts_same_human_turn(self):
    """save成功後は記録を変えず、同じ人間手番で入力を受け直す。"""

def test_load_replaces_record_displays_position_and_continues_by_loaded_turn(self):
    """load成功後は記録を置換して局面を表示し、読込後の手番で進める。"""

def test_reprompts_without_replacing_record_after_load_error(self):
    """load失敗は元の記録を保ち、同じ人間手番で再入力する。"""

def test_reprompts_after_save_file_error_without_changing_record(self):
    """save失敗は記録を保ち、同じ人間手番で再入力する。"""
```

既存の開始時詰みテストへ`save ignored.json`を与え、入力回数0のまま終局することも確認する。

- [x] **ステップ2: Redを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.GameplayTests -v`

期待値: 保存・読込分岐がないため追加テストがFAILする。

- [x] **ステップ3: 最小実装を加える**

`run_game`の人間入力分岐で指し手適用より先に`_SaveCommand`を`record.save(command.path)`へ、`_LoadCommand`を`record = GameRecord.load(command.path)`へ委譲する。成功表示はそれぞれ「棋譜を保存しました。」「棋譜を読み込みました。」とする。load成功時は`render_position(record.current_position)`を表示して`continue`する。`ValueError`と`OSError`を既存と同じ`エラー：`表示・再入力へ含め、EOF/Ctrl-Cの外側処理を変えない。`run_game`のdocstringを副作用、失敗時不変性、読込後の表示と担当切替まで更新する。

- [x] **ステップ4: Greenを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v`

期待値: 追加・既存のCLIテストがすべてPASSし、保存後の同一手番、読込後の置換・表示・担当切替、失敗時再入力を確認できる。

- [x] **ステップ5: コミットする**

実行: `git add kaname_shogi/cli.py tests/test_cli.py && git commit -m "feat: CLIで棋譜を保存読込する"`

### タスク3: Refactor判断、レビュー、文書、全検証

**ファイル:** `README.md`、`docs/knowledge/30-game-record-file-save.md`、`docs/learning/42-cli-save-load.md`、`docs/02-project-direction.md`

- [x] **ステップ1: Refactorの要否を判断して検証する**

保存・読込分岐が入力解析・局面適用・終了処理の境界を壊していないか確認する。重複がなければ「不要」と学習記録へ残す。必要なら公開API・表示文言を変えない最小の抽出を行う。実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v`。期待値: PASS。

- [x] **ステップ2: 独立レビューを実施する**

Criticalは「読込失敗で既存記録を破壊しないか」、Importantは「load後の表示・手番・担当が一致するか」「保存・読込・終了を履歴へ混入させないか」、Minorは「docstring、エラー文、テスト説明が方針に合うか」を確認する。CriticalまたはImportantがあれば修正、CLI全テスト、再レビューを行い、最終結論と対応を学習記録へ残す。

- [x] **ステップ3: 利用文書と学習記録を更新する**

READMEに入力形式、相対・絶対パス、親ディレクトリ非作成、成功後の進行、失敗時再入力、終了後に不可、JSON形式不変を追記する。知識メモに保存形式は`GameRecord`、文字列入力・表示・再入力・置換はCLIという境界を追記する。学習記録に目的、一次資料、確認問題と回答、承認、TDD、Refactor、レビュー、検証、未解決事項を残す。未回答の理解確認は回答済みにしない。

- [x] **ステップ4: 全検証とCLIスモークを実行する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`、`printf '1\\nsave /private/tmp/kaname-shogi-cli-save-load.json\\nmove 7 7 7 6\\nresign\\n' | PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi`、`git diff --check`。

期待値: 全テストPASS、スモークでは形式選択・保存成功・指し手・投了終了を確認し、`git diff --check`は出力なし。

- [ ] **ステップ5: 文書をコミットする**

実行: `git add README.md docs/knowledge/30-game-record-file-save.md docs/learning/42-cli-save-load.md docs/02-project-direction.md && git commit -m "docs: 第42回の学習と利用方法を記録する"`

### タスク4: main取り込みと最後の理解確認

- [x] **ステップ1: 取り込み前に本人の承認を得る**

`git status --short --branch`、作業ブランチから`main`への差分、全検証、最終レビュー（Critical/Important 0件）を提示する。本人の明示的承認まで取り込まない。

- [x] **ステップ2: 承認後にmainへ取り込み、mainで再検証する**

実行: `git switch main`、`git merge --no-ff <実際の作業ブランチ名> -m "merge: 第42回のCLI保存読込を取り込む"`、`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q`、`git diff --check`、`git status --short --branch`。

期待値: `main`で全テストPASS、`git diff --check`は出力なし、作業ツリーはクリーン。

- [ ] **ステップ3: 理解確認を一問だけ出す**

質問: 「なぜ `load` は既存の `GameRecord` を少しずつ書き換えるのではなく、読込が完全に成功した後に新しい `GameRecord` と置き換えるのか。」本人の回答を待ち、回答前に次テーマを開始しない。

- [ ] **ステップ4: 本人回答後に記録と次候補を更新する**

本人回答と補足を学習記録へ区別して追記する。README、`docs/02-project-direction.md`、`docs/next-topics.md`、`docs/resume.md`を見直して更新し、必要な文書を`docs: 第42回の理解確認を記録する`としてコミットする。

## 計画の自己レビュー

- 仕様の全要件を、タスク1（形式）、タスク2（進行・失敗・終了）、タスク3（レビュー・文書・検証）、タスク4（取り込み・理解確認）に対応付けた。
- `GameRecord`不変更、load成功時だけの置換、失敗時不変性、履歴範囲、終了状態を明記した。
- 型名と既存APIの参照は一貫し、未決定の実装プレースホルダは含まない。
