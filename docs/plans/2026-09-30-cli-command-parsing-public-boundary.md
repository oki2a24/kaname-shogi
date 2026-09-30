# CLIコマンド解析の公開境界を設計し直す：実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** `parse_command` の解析済みコマンドを5つの名前付き公開データ型と `Command` 型別名で表し、CLIモジュールの公開APIを `__all__` で明記する。

**アーキテクチャ:** コマンド値オブジェクトは現在と同じ `cli.py` に置き、先頭の `_` を除いた公開名へ一対一に移行する。`Command` は5型の `Union` とし、文字列解析・対局進行・ファイル操作の責務分離は維持する。既存の解析テストを公開契約のテストへ置き換え、テストメソッドは追加しない。

**技術スタック:** Python 3.9標準ライブラリ（`dataclasses`、`typing`、`unittest`、`ast`、`subprocess`）、Git。

**仕様 (Spec):** [CLIコマンド解析の公開境界を設計し直す：設計仕様](2026-09-30-cli-command-parsing-public-boundary-design.md)

**グローバル制約 (Global Constraints):**

- 入力文法、保存・読込・投了・移動・駒打ちの公開動作、エラー文言、テスト件数を変更しない。
- 第49回で完了した駒名対応と、将来の別機能は扱わない。
- 公開型は `MoveCommand`、`DropCommand`、`ResignCommand`、`SaveCommand`、`LoadCommand` の5つとし、旧 `_MoveCommand` などの別名を残さない。
- `Command` は5公開型のいずれかを表す公開の型別名とする。
- `cli.__all__` は `GameMode`、`choose_game_mode`、5公開型、`Command`、`parse_command`、`run_game` の10名だけを順序どおりに含める。`FORMAT_ERROR` と内部補助は含めない。
- 各公開型は解析済みの指示を表す凍結データであり、局面やファイルを変更する操作ではない。属性、等価比較、凍結性は現行から変えない。
- `parse_command` は形式解析だけを担い、合法性判定・保存・読込の実行は既存の後段へ委譲する。
- `tests/test_cli.py` の37件と全体240件のテストメソッド数を維持する。
- 実装後はRefactor要否確認、独立コードレビュー、Critical・Important指摘の解消後の再検証・再レビュー、学習記録、本人承認後のmain取り込みと取り込み先検証を行う。

---

## ファイル構成

- 変更: `kaname_shogi/cli.py`
  - 公開API一覧、公開データ型、`Command`、`parse_command` の型注釈・docstring、内部の型参照を一貫して更新する。
- 変更: `tests/test_cli.py`
  - 既存5件の解析境界テストだけで、公開型・属性・`__all__` を確認する。テストメソッドは増減させない。
- 作成: `docs/learning/50-cli-command-parsing-public-boundary.md`
  - 実施内容、Green-to-Green、Refactor要否、独立レビュー、検証、main取り込み、最後の理解確認を、実施時点の事実として記録する。
- 更新: `docs/README.md`、`docs/roadmap-repository-foundation.md`、`docs/next-topics.md`、`docs/resume.md`
  - テーマ完了後にのみ、索引、ロードマップ、次テーマ候補、再開案内を実際の進行状況に合わせる。設計・実装完了前に完了扱いを記録しない。

### タスク1: 公開契約を先にテストで表す

進行状況: 完了

**ファイル:**

- 変更: `tests/test_cli.py:17-79`
- テスト: `tests/test_cli.py` の `CommandParsingTests` 5件

**インターフェース (Interfaces):**

- 消費 (Consumes): 現行の `cli.parse_command(text: str)`、現行の解析結果属性、`FORMAT_ERROR` の例外文言。
- 生産 (Produces): `cli.MoveCommand`、`cli.DropCommand`、`cli.ResignCommand`、`cli.SaveCommand`、`cli.LoadCommand`、`cli.Command`、`cli.__all__` という未実装の公開契約を要求する既存37件のCLIテスト。

- [x] **ステップ1: 既存の解析テストを公開型の期待値へ置き換える**

`test_parses_move_and_drop_with_halfwidth_or_fullwidth_input` に、既存の属性比較を残したまま次を加える。

```python
self.assertIsInstance(move, cli.MoveCommand)
self.assertIsInstance(promoted, cli.MoveCommand)
self.assertIsInstance(drop, cli.DropCommand)
```

`test_parses_resign_command` は次のように公開型を直接確認する。docstringには、投了の解析と公開API一覧を確認することを記す。

```python
command = cli.parse_command("resign")

self.assertEqual(cli.__all__, (
    "GameMode", "choose_game_mode", "MoveCommand", "DropCommand",
    "ResignCommand", "SaveCommand", "LoadCommand", "Command",
    "parse_command", "run_game",
))
self.assertIsInstance(command, cli.ResignCommand)
```

`test_parses_save_and_load_commands` は `getattr` による旧内部型の取得を削除し、次を使う。

```python
self.assertIsInstance(save, cli.SaveCommand)
self.assertEqual(save.path, "records/game.json")
self.assertIsInstance(load, cli.LoadCommand)
self.assertEqual(load.path, "/tmp/game.json")
```

不正形式を確認する既存2件は変更しない。新しい `test_` メソッド、入力例、期待エラー文言は追加・変更しない。

- [x] **ステップ2: 公開型がまだ存在しない理由でRedになることを確認する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.CommandParsingTests -v
```

期待値: `cli.MoveCommand` または `cli.ResignCommand` が未定義である `AttributeError` により失敗する。入力形式やテスト読み込みの失敗をRed完了と扱わず、公開契約が未実装であることが失敗理由であると確認する。

### タスク2: `cli.py` に唯一の公開コマンド契約を実装する

進行状況: 完了

**ファイル:**

- 変更: `kaname_shogi/cli.py:1-208, 321-334`
- テスト: `tests/test_cli.py` の `CommandParsingTests` 5件

**インターフェース (Interfaces):**

- 消費 (Consumes): タスク1の公開型・`__all__` の期待値、現行の `Square`、`BasicPieceType`、`GameRecord`。
- 生産 (Produces):
  - `MoveCommand(source: Square, destination: Square, promote: bool)`
  - `DropCommand(piece_type: BasicPieceType, destination: Square)`
  - `ResignCommand()`
  - `SaveCommand(path: str)`
  - `LoadCommand(path: str)`
  - `Command = Union[MoveCommand, DropCommand, ResignCommand, SaveCommand, LoadCommand]`
  - `parse_command(text: str) -> Command`

- [x] **ステップ1: 公開API一覧をモジュール先頭へ追加する**

import文の後、`FORMAT_ERROR` の前に次の順序のタプルを置く。

```python
__all__ = (
    "GameMode",
    "choose_game_mode",
    "MoveCommand",
    "DropCommand",
    "ResignCommand",
    "SaveCommand",
    "LoadCommand",
    "Command",
    "parse_command",
    "run_game",
)
```

`FORMAT_ERROR` と先頭が `_` の内部補助は追加しない。`__all__` は実行時の振る舞いを変えるための分岐ではなく、外部から利用してよい名前を列挙するモジュール定数である。

- [x] **ステップ2: 5データ型を公開名へ一対一に改名し、`Command` を定義する**

各 `@dataclass(frozen=True)` の属性・本体を変えず、クラス名だけを次のように変更する。

```python
@dataclass(frozen=True)
class MoveCommand:
    """盤上移動の入力を、合法性判定前の値として保持する。"""

    source: Square
    destination: Square
    promote: bool


Command = Union[MoveCommand, DropCommand, ResignCommand, SaveCommand,
                LoadCommand]
```

`Command` は5型の定義の後に置く。各公開型のdocstringには、引数・戻り値・副作用・
前提条件が該当しないことと、解析済みデータである設計理由を追記する。属性や
`frozen=True` を変更しない。

- [x] **ステップ3: 解析器と内部実行経路の型参照を公開名へそろえる**

`parse_command` のシグネチャを次に変更し、docstringの戻り値を「5つの公開型のいずれかの
`Command`」と明記する。

```python
def parse_command(text: str) -> Command:
```

5つの `return` は対応する公開型の生成へ変更する。`_apply_command` の引数は
`Union[MoveCommand, DropCommand]`、`isinstance` は `MoveCommand` にする。`run_game` の
保存・読込・投了の分岐も `SaveCommand`、`LoadCommand`、`ResignCommand` にする。

文字列の `split()`、引数数、`+`、座標・駒名の変換、`ValueError(FORMAT_ERROR)`、
保存・読込・投了・着手の分岐順と処理本体は変更しない。

- [x] **ステップ4: 解析境界テストがGreenになることを確認する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.CommandParsingTests -v
```

期待値: 5件成功、失敗0件。公開型、属性、`__all__`、既存の入力形式エラーが同時に確認できる。

- [x] **ステップ5: この実装単位をコミットする**

```sh
git add kaname_shogi/cli.py tests/test_cli.py
git commit -m "refactor: CLI解析コマンド型を公開する"
```

### タスク3: 振る舞い不変性、構造、レビューを確認して記録する

進行状況: 完了

**ファイル:**

- 変更: `docs/learning/50-cli-command-parsing-public-boundary.md`
- 更新: `docs/README.md`、`docs/roadmap-repository-foundation.md`、`docs/next-topics.md`、`docs/resume.md`（テーマの実際の完了段階に応じる）
- テスト: `tests/test_cli.py` の37件、`tests/` の全240件

**インターフェース (Interfaces):**

- 消費 (Consumes): タスク2の10名の `cli.__all__`、5公開型、`Command`、不変の入力・進行・エラー契約。
- 生産 (Produces): Green-to-Greenの検証記録、Refactor要否、独立レビュー結論、取り込み承認に必要な学習・案内文書。

- [x] **ステップ1: CLIテストと全テストを実行する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

期待値: 前者37件、後者240件がともに成功し、保存・読込・投了・移動・駒打ちと入力形式エラーの公開動作が不変である。

- [x] **ステップ2: テスト件数と公開境界を静的に確認する**

実行:

```sh
rg -n '^    def test_' tests/test_cli.py | wc -l
rg -n '^    def test_' tests | wc -l
rg -n '^class _(?:Move|Drop|Resign|Save|Load)Command|_(?:Move|Drop|Resign|Save|Load)Command' kaname_shogi tests
```

期待値: 最初は37、二つ目は240、三つ目は出力なし。さらに短い `ast` を用いた読み取り専用確認で、
`cli.__all__` が順序どおり10名、5公開型と `Command` が存在することを検査する。

- [x] **ステップ3: 差分と文書リンクを確認する**

実行:

```sh
git diff --check
```

期待値: 出力なし。更新文書に含まれる相対Markdownリンクは、既存のリンク検査方法で全件解決することを確認する。

- [x] **ステップ4: Refactor要否を判断する**

`cli.py` を読み直し、公開型、`Command`、`__all__`、解析、進行分岐の責務が一つの小さい
モジュール内で読み取れるかを確認する。入力文法の拡張、共通基底クラス、辞書形式、別モジュール化、
第49回の駒名対応の変更は、今回の目的を超えるため追加しない。判断理由を第50回の学習記録へ残す。

- [x] **ステップ5: 独立コードレビューを実施し、必要なら是正する**

レビュー対象を実装コミットと設計仕様からの差分に限定し、公開API10名、旧名不在、型・docstring、
入力・進行・エラー文言不変、テスト件数、不要な対象拡大を確認する。Critical・Important・Minorを
第50回の学習記録に記録する。CriticalまたはImportantがあれば修正し、ステップ1から再実行して
独立再レビューする。

- [x] **ステップ6: 実施記録と案内文書を更新してコミットする**

第50回の学習記録には、対象・非対象、実際の変更、Green-to-Green、Refactor要否、独立レビュー、
検証結果、未解決事項を記す。`docs/README.md`、ロードマップ、次テーマ候補、再開案内は、
実施済みの段階だけを更新する。

```sh
git add docs/learning/50-cli-command-parsing-public-boundary.md docs/README.md docs/roadmap-repository-foundation.md docs/next-topics.md docs/resume.md
git commit -m "docs: CLI解析公開境界の学習記録を追加する"
```

- [x] **ステップ7: main取り込み前の状態を報告し、本人の承認を待つ**

作業ブランチのコミット、検証結果、独立レビュー結果、未解決事項を本人へ提示する。`main` への
取り込みは本人の明示的な承認後にだけ行う。取り込み後は、取り込み先の全テスト、リンク検査、
`git diff --check` を再実行し、最後の理解確認を一問だけ出す。

## 計画の自己レビュー

- [x] 仕様の入力文法、公開動作、エラー文言、テスト件数、公開型、`Command`、`__all__`、旧名削除、対象外を、タスク1〜3のいずれかへ対応付けた。
- [x] 各型名、属性、戻り値注釈、`__all__` の10名と順序、検証コマンドを具体化した。
- [x] プレースホルダを使わず、Redの失敗理由を公開型未実装の `AttributeError` と明記した。
- [x] 実行コマンドはリポジトリ直下 `/Users/oki2a24/kaname-shogi` で実行できる形にした。
- [x] 新テスト追加ではなく既存5件を更新し、37件・240件を維持する手順にした。
