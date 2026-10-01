# CLIの `help` 表示 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 人間が対局中に `help` を入力して5種類のコマンド書式と短い説明を確認し、局面を変えず同じ手番で入力を続けられるようにする。

**アーキテクチャ:** `HelpCommand` を既存の公開コマンド解析境界へ追加し、`run_game` が固定ヘルプ文を `output_fn` へ一度渡して入力ループを続ける。既存コマンドの文法・動作は維持し、READMEと学習記録に利用方法と実施結果を記録する。

**技術スタック:** Python 3.9.6、標準ライブラリ `unittest`。

**仕様 (Spec):** [CLIの `help` 表示 設計仕様](2026-10-01-cli-help-display-design.md)

**グローバル制約 (Global Constraints):**
- 入力文法、将棋規則、保存形式、既存5コマンドの公開動作を変更しない。
- `HelpCommand` は解析済み指示を表す公開データ型とし、局面を変更しない。
- ヘルプ表示後は同じ人間手番で入力を続ける。
- 毎回の入力案内文を変更しない。
- 既存の標準ライブラリだけを使用する。
- 実装計画の承認前に作業ブランチ、TDD、コード・テスト・既存文書の変更を始めない。
- 目的が分かる作業ブランチで実装し、日本語のConventional Commitを使う。

## レビューフォーカス

1. `help` の後に着手したとき、help自体が棋譜へ混入せず、同じ人間手番から手が適用されること。
2. `help` の後にEOFになっても、開始局面・空の記録を返し投了・勝敗表示をしないこと。
3. `help` 以外の大文字表記や余分な引数は、既存の形式エラー動作を維持すること。
4. ヘルプ文が保存後の継続、読込後の再開、空白なしパス、全角数字の案内を誤らないこと。
5. 既存入力案内、5コマンドの解析・進行、終局後に入力しない動作を変えないこと。

---

## ファイル構成

- 変更 `kaname_shogi/cli.py`: 公開 `HelpCommand`、解析、公開型別名・`__all__`、ヘルプ文、対局ループの表示・継続を追加する。
- 変更 `tests/test_cli.py`: `help` 解析、公開API、表示文、同じ手番・不変状態での継続を検証する。
- 変更 `README.md`: 対局中の `help` 入力と表示内容をCLI操作に追記する。
- 作成 `docs/learning/51-cli-help-display.md`: 目的、設計、確認問題と回答、TDD、実装、Refactor判断、独立レビュー、検証、振り返り、次回への問いを記録する。未回答の確認問題を正解として記録しない。

## タスク1: 公開解析と対局中ヘルプ表示

**ファイル:**
- 変更: `tests/test_cli.py`
- 変更: `kaname_shogi/cli.py`
- 変更: `README.md`
- 作成: `docs/learning/51-cli-help-display.md`

**インターフェース:**
- 消費: `Command` は既存5公開コマンド型のUnion、`parse_command(text: str) -> Command` はCLI入力を解析、`run_game(..., mode: GameMode) -> GameRecord` は対局を進行する。
- 生産: `HelpCommand` は引数なしの凍結データ型。`Command` は6コマンド型のUnion。`parse_command("help") -> HelpCommand`。`cli.__all__` は既存10名の順序を保ち、`HelpCommand` を加える。

- [ ] **ステップ1: `help` の解析・公開APIテストを追加する**

`CommandParsingTests` に `test_parses_help_command` を追加する。`cli.parse_command("help")` が `cli.HelpCommand()` と等しいこと、`HelpCommand` が `cli.__all__` の `LoadCommand` と `Command` の間に含まれ、既存10名の順序が維持されることを確認する。また `help now` と `HELP` は既存の形式エラーになることを確認する。

- [ ] **ステップ2: 解析テストを実行してRed理由を確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.CommandParsingTests.test_parses_help_command -v`
期待値: `HelpCommand` が未定義、または `help` が形式エラーとなり、追加した振る舞いが未実装であることを示す失敗。テスト読込エラーだけの場合はRed確認としない。

- [ ] **ステップ3: ヘルプ後の進行テストを追加する**

`GameplayTests` に `test_help_displays_commands_and_reprompts_same_turn` と `test_help_preserves_record_when_input_ends` を追加する。前者は人間対人間モードで `help`、先手の合法手 `move 7 7 7 6`、後手の `resign` を順に入力し、出力に5コマンドの書式と短い説明、`+`、全角数字、パス制約、save/load後の進行説明が含まれることを検証する。入力呼び出しが3回、棋譜に記録される手がmove一手だけ、局面がその手だけ進み、help直後に再入力案内が出ることを検証する。後者は `help` の後にEOFを返し、投了や勝敗を追加せず、開始局面と空の棋譜を保つことを検証する。

- [ ] **ステップ4: 進行テストを実行してRed理由を確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.GameplayTests.test_help_displays_commands_and_reprompts_same_turn tests.test_cli.GameplayTests.test_help_preserves_record_when_input_ends -v`
期待値: `help` が解析できず、追加した入力・表示・継続の振る舞いが未実装であることを示す失敗。例外によるテスト中断も未実装の失敗として記録し、構文・importエラーだけでRedを済ませない。

- [ ] **ステップ5: `cli.py` に最小実装を追加する**

`HelpCommand` を引数なしの `@dataclass(frozen=True)` として定義し、公開データ型のdocstring方針に従って意味・副作用なし・表示操作との境界を日本語で説明する。`Command` と `__all__` に追加し、`parse_command` が単独の `help` を返すようにする。追加引数は既存形式エラーにする。

`_HELP_TEXT` をモジュール内部の固定文字列として定義し、5コマンドの構文と説明を改行で連結する。`run_game` は `HelpCommand` を受けたらこの文字列を `output_fn` に一度渡して `continue` する。記録・局面を変更せず、従来の入力案内は変えない。

- [ ] **ステップ6: 追加テストをGreenにする**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.CommandParsingTests.test_parses_help_command tests.test_cli.GameplayTests.test_help_displays_commands_and_reprompts_same_turn tests.test_cli.GameplayTests.test_help_preserves_record_when_input_ends -v`
期待値: 3件の追加テストが成功する。

- [ ] **ステップ7: CLIテスト全体で互換性を確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v`
期待値: `tests/test_cli.py` の全テスト成功。既存コマンドのエラー文言と進行テストに失敗がない。

- [ ] **ステップ8: READMEに使い方を追加する**

READMEのCLI操作へ `help` を追加し、対局中に書式一覧を表示して同じ手番で続けられることを記す。記載は `_HELP_TEXT` と一致させ、既存コマンドの説明を変更しない。

- [ ] **ステップ9: 学習記録に実施内容を記録する**

`docs/learning/51-cli-help-display.md` に設計仕様へのリンク、本人の確認回答とアシスタント補足の区別、テストごとのRed理由、Green結果、実変更、Refactor要否、独立レビューのCritical・Important・Minorと対応、検証結果、未解決事項、振り返り、次回への問いを記録する。確認問題は一問だけ提示し、本人の回答前に回答欄を正解で埋めない。

- [ ] **ステップ10: 全テストと差分を検証する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
```

期待値: 全ユニットテスト成功、`git diff --check` に出力なし。CLIテスト件数と全テスト件数を数え、README・学習記録・設計仕様への相対リンクを検査する。

- [ ] **ステップ11: Refactorの要否を確認し独立レビューを実施する**

追加抽象化の必要性を確認し、変更有無と判断理由を学習記録へ記す。その後、変更差分を独立してレビューし、Critical・Important・Minorを分類する。CriticalまたはImportantがあれば修正し、テストとレビューを再実施してから記録・コミットへ進む。

- [ ] **ステップ12: 日本語Conventional Commitを作成する**

テーマの実装・検証・レビュー・記録が揃った後、内容を確認して関連ファイルをコミットする。例: `feat: CLIにhelp表示を追加する`。計画承認前にはこのステップを実行しない。

## テーマ完了時の手順

1. 設計・実装・検証・レビュー・学習記録が揃ったら、本人の承認を得てから元ディレクトリの `main` へ取り込む。
2. 取り込み先で全テストと文書リンクを検証する。
3. 最後の理解確認を一問だけ提示して回答を待ち、本人の回答と補足を学習記録へ追記する。
4. その後に `docs/next-topics.md`、README、プロジェクト方向性を見直し、次候補を提示する。
