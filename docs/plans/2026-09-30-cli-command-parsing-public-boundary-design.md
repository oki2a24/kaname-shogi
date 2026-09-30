# CLIコマンド解析の公開境界を設計し直す：設計仕様

## 目的

`kaname_shogi.cli.parse_command` が返す解析済みコマンドを、外部のPythonコードと
テストが型名・属性で利用できる正式な公開データ契約として明確にする。

このテーマはCLI解析器の公開・内部境界を整理するリファクタリングである。入力文法、
保存・読込・投了・移動・駒打ちの公開動作、エラー文言、テスト件数を変更せず、
第49回で完了した駒名対応と将来の別機能は扱わない。

## 対象と非対象

### 対象

- `cli.py` の `_MoveCommand`、`_DropCommand`、`_ResignCommand`、`_SaveCommand`、
  `_LoadCommand` の公開名への移行
- 上記5型のいずれかを表す公開の型別名 `Command`
- `parse_command` の戻り値注釈とdocstring
- `cli.__all__` によるCLIモジュールの公開API一覧
- `tests/test_cli.py` の解析テストが公開型と公開APIを検証するようにする変更

### 非対象

- `move`、`drop`、`resign`、`save`、`load` の文法、受理する全角・半角の空白・数字、
  駒名、成り記号、パスの規則
- 保存・読込・投了・移動・駒打ちの進行、局面・手番・履歴の変更規則
- `ValueError` と文言 `入力形式が正しくありません。`、保存・読込失敗時の表示
- 第49回で完了した `_DROP_PIECE_SPECS` と駒名の入出力対応
- 将棋規則、JSON形式、CLIコマンドの追加、`help`、SFEN、USI、評価関数
- テストメソッド数、CLIテスト数、全テスト数

## 公開データ契約

次の5つを、凍結したデータクラスとして公開する。これらは解析済みの入力を表す
**データ**であり、局面を変える「指す」「打つ」「保存する」といった操作ではない。
操作の実行は従来どおり `run_game`、`GameRecord`、その内部補助が担う。

| 公開型 | 保持する値 | 意味 |
| --- | --- | --- |
| `MoveCommand` | `source: Square`、`destination: Square`、`promote: bool` | 盤上移動の指示 |
| `DropCommand` | `piece_type: BasicPieceType`、`destination: Square` | 駒打ちの指示 |
| `ResignCommand` | なし | 投了の指示 |
| `SaveCommand` | `path: str` | 保存先を表す指示 |
| `LoadCommand` | `path: str` | 読込元を表す指示 |

`Square` は将棋盤の筋・段を表す値、`BasicPieceType` は基本駒種を表す値であり、
どちらも操作ではない。5型の属性、等価比較、凍結性は現行のデータクラスから変えない。

`Command` は上の5型のいずれかを表す公開の型別名とする。`parse_command` の戻り値は
`Command` と明記する。これにより利用者は、解析結果全体を一つの名前で注釈できる一方、
実行時には各公開型で指示の種類と属性を判別できる。

旧 `_MoveCommand` などの名前は残さない。同じ役割に公開名と内部名を併存させると、
どちらが契約なのかが再び曖昧になるためである。

## CLIモジュールの公開API

`cli.__all__` を次の名前だけからなる順序付きの公開API一覧として定義する。

```python
(
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

`GameMode`、`choose_game_mode`、`run_game` は従来から先頭に `_` を付けず外部利用が可能な
名前であるため、今回の一覧にも含める。`FORMAT_ERROR` は例外文言をモジュール内で共有する
内部定数として `__all__` に含めない。例外から得られる文言そのものは、これまでどおり
公開動作として維持する。`_apply_command`、`_apply_selected_move`、`_run_computer_turn` などの
内部補助も含めない。

## 解析と進行の境界

`parse_command` は文字列の形式を検査し、上記の公開データへ変換するだけである。候補手、
手番、二歩などの合法性は既存どおり後段へ委譲し、保存・読込も解析時には実行しない。

`run_game` と `_apply_command` は、旧内部型名ではなく公開型で分岐・型注釈を行う。これは
内部の実行経路を新しい公開契約へ合わせるだけであり、分岐順、呼び出す `GameRecord` の
操作、表示、例外処理を変えない。

## 既存テストの意図と互換性

`CommandParsingTests` の5件は、現在の解析器を直接診断する境界テストとして維持する。

- 移動・駒打ちのテストは、全角・半角入力を正しい公開型と属性へ変換することを確認する。
- 投了、保存、読込のテストは、それぞれ対応する公開型とパスを確認する。
- 不正な保存・読込とその他の不正形式のテストは、例外型・エラー文言を確認する。

この既存5件の中で、5公開型と `__all__` を検証するように期待値を置き換え・補強する。
新しいテストメソッドは追加せず、37件のCLIテストと全体のテスト件数を維持する。
進行テスト32件は、解析結果を実行して保存・読込・投了・移動・駒打ちの公開動作を守る
役割を、そのまま維持する。

旧名が非公開であっても現在のテストが直接参照していることは、今回明示的に移行する対象で
ある。公開型へ置き換えるため、外部利用者が依存すべき型名は一意になる。

## 確認方法

振る舞いの追加ではないため、TDDのRed-GreenではなくGreen-to-Greenで確認する。
変更前後に次を比較・実行する。

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v`：37件
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`：全240件
- `rg -n '^    def test_' tests/test_cli.py | wc -l`：37件、および全テストメソッド数：240件
- ASTまたは同等の静的確認：`__all__` が設計どおりの10名だけを列挙し、5公開型と
  `Command` が存在し、旧5内部型の定義・参照が残らないこと
- `git diff --check`
- 更新文書の相対Markdownリンク検査

実装後はRefactor要否を確認し、変更の有無にかかわらず独立コードレビューを実施する。
CriticalまたはImportantがあれば修正、再検証、再レビューを行う。

## 記録と承認の順序

実装は `/Users/oki2a24/kaname-shogi` の
`codex/cli-command-parsing-public-boundary` ブランチで行う。設計仕様、実装計画、
第50回の学習記録を分ける。将棋規則や保存形式の確定知識は増えないため、
`docs/knowledge/` は更新しない。

この設計仕様を自己レビューしてコミットした後、本人の仕様書レビュー承認を待つ。その後に
`writing-plans` スキルで実装計画を作成し、計画を提示して本人の明示的な承認を待つ。
その承認前にコード、テスト、既存文書の変更、TDD、実装を開始しない。
