# CLIの駒名入出力対応を一つの定義から導く 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** `cli.py` の基本駒7種の表示用・入力用対応を、一つの順序付き定義から導き、CLIの既存振る舞いとテスト件数を保つ。

**アーキテクチャ:** `_DROP_PIECE_SPECS` に駒種と名称を一度だけ記述し、型→名称と名称→型の二つの辞書を導く。盤面表示・モデル・コマンド解析の公開境界は変更しない。

**技術スタック:** Python 3.9標準ライブラリ、`unittest`、Git。

**仕様 (Spec):** [設計仕様](2026-09-30-cli-piece-name-single-definition-design.md)

**グローバル制約 (Global Constraints):**

- 表示名、入力文法、入力可能な駒、順序、エラー文言、公開動作、テスト件数を変更しない。
- 共通定義は `cli.py` 内に限定し、`display.py` と `model.py` は変更しない。
- `parse_command` の公開境界は今回変更しない。次の予約テーマとして扱う。
- 既存テストの内容と期待値は変更しない。新しい振る舞いを追加しないため、Green-to-Greenで確認する。
- 実装は `codex/cli-piece-name-single-definition` で行い、コミットは日本語のConventional Commitにする。
- 実装後、Refactor要否確認、独立コードレビュー、記録、本人承認後のmain取り込みと取り込み先検証を行う。

---

## ファイル構成

| ファイル | 操作 | 責務 |
| --- | --- | --- |
| `kaname_shogi/cli.py` | 変更 | 駒打ちの正本と表示・入力向け派生辞書を定義する。 |
| `tests/test_cli.py` | 変更しない | 既存の`drop`解析、不正な王の拒否、CLI進行を保護する。 |
| `tests/test_display.py` | 変更しない | 盤面の基本駒・成駒・王玉の表示不変性を保護する。 |
| `docs/learning/49-cli-piece-name-single-definition.md` | 実装完了後に作成 | 合意、実際の変更、検証、レビュー、理解確認を記録する。 |

## タスク1: 変更前のGreen基準を確定する

**ファイル:**

- 変更: なし
- テスト: `tests/test_cli.py`、`tests/test_display.py`、テストスイート全体

**インターフェース (Interfaces):**

- 消費 (Consumes): 現在の `cli._PIECE_NAMES`、`parse_command(text: str)`、`_format_selected_move(move: Move)`。
- 生産 (Produces): 変更後と比較する対象別・全体の成功件数、テストメソッド数、現在の構造。

- [x] **ステップ1: 対象テストをGreenとして実行する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_display -v
```

期待値: どちらも `OK`。歩の解析、王の形式エラー、初期局面全文、成駒名、手番表示を含む既存テストが成功する。

- [x] **ステップ2: 全テストをGreenとして実行し、実測件数を記録する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

期待値: `OK`。実測のテスト総数を第49回学習記録の変更前基準として保存する。過去に記録された240件は参考情報であり、現在の実測値の代用にしない。

- [x] **ステップ3: テストメソッド数と変更前構造を静的に記録する**

実行:

```sh
rg -n '^    def test_' tests
rg -n -C 3 '_PIECE_NAMES|piece_types' kaname_shogi/cli.py
git status --short --branch
```

期待値: 後の同じ検索結果と比較できる。`cli.py` には `_PIECE_NAMES` と `parse_command` 内の手書き `piece_types` がそれぞれ一つある。

## タスク2: 一つの正本から二方向の対応を導く

**ファイル:**

- 変更: `kaname_shogi/cli.py` の `_LoadCommand` 直後から `parse_command` の駒打ち解析部
- テスト: 変更しない（既存の `tests/test_cli.py`、`tests/test_display.py`）

**インターフェース (Interfaces):**

- 消費 (Consumes): `BasicPieceType.PAWN` から `BasicPieceType.ROOK`、既存の `_format_selected_move` と `parse_command`。
- 生産 (Produces): `_DROP_PIECE_SPECS: tuple[tuple[BasicPieceType, str], ...]`、`_PIECE_NAMES: dict[BasicPieceType, str]`、`_PIECE_TYPES_BY_NAME: dict[str, BasicPieceType]`。既存の `parse_command(text: str)` の戻り値・例外は変えない。

- [x] **ステップ1: 駒打ち用の順序付き正本を追加する**

`_LoadCommand` の直後に、現在の順序を明記した次の値を置く。

```python
_DROP_PIECE_SPECS = (
    (BasicPieceType.PAWN, "歩"),
    (BasicPieceType.LANCE, "香"),
    (BasicPieceType.KNIGHT, "桂"),
    (BasicPieceType.SILVER, "銀"),
    (BasicPieceType.GOLD, "金"),
    (BasicPieceType.BISHOP, "角"),
    (BasicPieceType.ROOK, "飛"),
)
```

このタプルは、駒打ちで入力・表示する基本駒の表記対応を表すデータであることを、短いコメントまたはdocstring相当の説明で残す。新しい公開APIにはしない。

- [x] **ステップ2: 二つの派生辞書を共通定義から作る**

既存の手書き `_PIECE_NAMES` を次へ置き換え、その直後に逆引きを置く。

```python
_PIECE_NAMES = dict(_DROP_PIECE_SPECS)
_PIECE_TYPES_BY_NAME = {
    name: piece_type for piece_type, name in _DROP_PIECE_SPECS
}
```

これにより `_format_selected_move` は従来どおり `_PIECE_NAMES[move.piece_type]` を使え、外から見える表示を変更しない。

- [x] **ステップ3: `parse_command` の駒打ち解析を派生逆引きへ接続する**

`parse_command` にある手書き `piece_types` 辞書を削除し、既存の駒打ち分岐では次を使う。

```python
return _DropCommand(
    _PIECE_TYPES_BY_NAME[parts[1]],
    Square(int(parts[2]), int(parts[3])),
)
```

`KeyError` と `ValueError` を現在どおり `ValueError(FORMAT_ERROR)` へ変換する `except` 節は変更しない。したがって王や未知の駒名、座標不正時の例外型・文言を保つ。

- [x] **ステップ4: 構文と差分書式を確認する**

実行:

```sh
python3 -c 'import ast, pathlib; ast.parse(pathlib.Path("kaname_shogi/cli.py").read_text(encoding="utf-8"))'
git diff --check
git diff -- kaname_shogi/cli.py
```

期待値: 構文エラーと空白エラーがない。`py_compile` は実行環境のキャッシュ書込み権限で失敗するため、バイトコードを生成しない `ast.parse` で同じ構文解析を確認する。差分は正本、二つの派生辞書、逆引き参照への置換だけであり、`display.py`、`model.py`、テストには差分がない。

- [ ] **ステップ5: 構造整理のコード変更をコミットする**

実行:

```sh
git add kaname_shogi/cli.py
git commit -m 'refactor: CLI駒名対応を一つの定義から導く'
```

期待値: `cli.py` だけを含む日本語Conventional Commitが作られる。検証で問題が出た場合は、コミット前に最小限の修正を行い、Greenを再確認する。

## タスク3: 変更後のGreen-to-Greenと構造不変性を確認する

**ファイル:**

- 変更: なし
- テスト: `tests/test_cli.py`、`tests/test_display.py`、テストスイート全体

**インターフェース (Interfaces):**

- 消費 (Consumes): タスク1の変更前実測値、タスク2の `_DROP_PIECE_SPECS` と派生辞書。
- 生産 (Produces): 振る舞い・テスト件数・対象外ファイル不変性の検証結果。

- [x] **ステップ1: 対象テストと全テストを再実行する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_display -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

期待値: すべて `OK`。対象テストと全テストの実測件数がタスク1の変更前基準と一致する。

- [x] **ステップ2: 正本・派生・旧辞書除去を静的に確認する**

実行:

```sh
rg -n -C 2 '_DROP_PIECE_SPECS|_PIECE_NAMES|_PIECE_TYPES_BY_NAME|piece_types' kaname_shogi/cli.py
rg -n '^    def test_' tests
git diff main...HEAD -- kaname_shogi/display.py kaname_shogi/model.py tests
git diff --check
```

期待値: `_DROP_PIECE_SPECS` は一つ、二つの派生辞書はその定義を参照し、`parse_command` 内の `piece_types` は0件。テストメソッド数はタスク1と一致する。対象外の `display.py`、`model.py`、テストに作業ブランチ差分がなく、書式検査が成功する。

## タスク4: Refactor要否、独立レビュー、記録を完了する

**ファイル:**

- 作成: `docs/learning/49-cli-piece-name-single-definition.md`
- 変更: `docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/roadmap-repository-foundation.md`（完了時点の実際の状態に必要な範囲だけ）
- テスト: 変更しない

**インターフェース (Interfaces):**

- 消費 (Consumes): タスク3のGreen-to-Greenと静的確認、コード差分、設計仕様、実装計画。
- 生産 (Produces): Refactor要否、Critical・Important・Minorの独立レビュー結論、実施事実を記した学習記録、main取り込み前にレビュー可能なコミット。

- [x] **ステップ1: 追加Refactorの要否を判定する**

確認項目:

```text
正本は一つか。
表示と入力は正本から導かれるか。
駒打ち以外の責務や公開境界を増やしていないか。
```

期待値: 追加の抽象化、共有モジュール化、盤面表示との統合は不要と判断する。今回の正本はCLI駒打ちの基本駒7種に限られ、別責務を混ぜると対象範囲を越えるためである。

- [x] **ステップ2: コード差分を対象に独立レビューする**

実行:

```sh
git diff main...HEAD -- kaname_shogi/cli.py
```

レビューでは、正本の順序、二方向の導出、`KeyError` の形式エラー変換、公開動作不変、対象外ファイル不変、テスト件数不変を確認する。CriticalまたはImportantがあれば最小修正、再検証、再レビューを行う。

- [x] **ステップ3: 第49回の学習記録と現在案内を実施事実で更新する**

学習記録には、目的、承認済み設計、`BasicPieceType` がデータである説明、変更前後の実測テスト件数、静的確認、Refactor要否、独立レビュー結論、未解決事項を記録する。案内文書には、実際のブランチ、コミット、承認待ち、完了状態だけを書き、将来の行動を実施済みとして書かない。

- [x] **ステップ4: 文書と最終状態を検証して記録コミットを作る**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
git status --short --branch
git add docs
git commit -m 'docs: CLI駒名対応の学習記録を追加する'
```

期待値: 全テストはタスク1と同じ実測件数で `OK`、書式検査が成功し、文書の内容は実施済みの事実だけを表す。相対リンクを更新した場合は既存のリンク検査手順も実行する。mainへの取り込みは本人が明示的に承認するまで行わない。

## セルフレビュー

- [x] 仕様の対象、非対象、名称、配置、順序、エラー文言、公開動作、テスト件数の全要件をタスクへ対応付けた。
- [x] 新機能がないため、既存テストを変更せずGreen-to-Greenにする理由と実行順を明記した。
- [x] 未決定のプレースホルダーや、未定義の実装名を残していない。
- [x] `display.py`、`model.py`、次テーマの公開境界変更を範囲外として明記した。
