# 第50回：CLIコマンド解析の公開境界を設計し直す

## 目的

`kaname_shogi.cli.parse_command` が返すコマンド型を、先頭に `_` の付く内部名ではなく、
外部のPythonコードとテストが利用できる名前付き公開データ型として明確にする。

入力文法、保存・読込・投了・移動・駒打ちの公開動作、エラー文言、テスト件数は変えず、
第49回の駒名対応と将来の別機能は対象外とする。

設計は[設計仕様](../plans/2026-09-30-cli-command-parsing-public-boundary-design.md)、
実行手順は[実装計画](../plans/2026-09-30-cli-command-parsing-public-boundary.md)に記録した。

## 合意した設計

- `MoveCommand`、`DropCommand`、`ResignCommand`、`SaveCommand`、`LoadCommand` を
  `parse_command` の5つの公開戻り値型にする。
- `Command` はその5型のいずれかを表す公開の型別名にする。
- `cli.__all__` は `GameMode`、`choose_game_mode`、5公開型、`Command`、
  `parse_command`、`run_game` の10名を順序どおりに列挙する。
- `FORMAT_ERROR` と進行用の補助は公開APIに含めない。ただし例外として表示される
  `入力形式が正しくありません。` は既存どおり公開動作として維持する。
- 旧 `_MoveCommand` などの別名は残さない。同じ役割の型名を二重に残すと、どちらが
  正式な契約か曖昧になるためである。

各公開型は、解析済みの指示を表す凍結された**データ**である。`Square` は筋・段を、
`BasicPieceType` は基本駒種を表す値であり、いずれも操作ではない。実際に指す、打つ、
保存する、読み込む操作は、従来どおり `run_game` と `GameRecord` が担う。

## 実装内容

`cli.py` に10名の `__all__` を追加した。既存の5データクラスを、属性と
`frozen=True` を変えずに公開名へ一対一に改名し、5型の `Union` である `Command` を
追加した。

`parse_command` の戻り値注釈を `Command` にし、5つの戻り値生成、`_apply_command`、
`run_game` の型判定を公開型へ統一した。文字列の分割、引数数、成り記号、座標・駒名の
変換、形式エラー、保存・読込・投了・着手の処理順は変更していない。

既存の解析テスト5件の中で、移動・駒打ち・投了・保存・読込が対応する公開型になることと、
`__all__` の内容を確認するよう更新した。新しいテストメソッドは追加していない。

コード変更は次のコミットに記録した。

```text
bf90773 refactor: CLI解析コマンド型を公開する
```

## TDDとGreen-to-Green

テストを先に公開契約の期待値へ変更し、`CommandParsingTests` 5件を実行した。公開型と
`__all__` がまだ存在しないため、`AttributeError` が3件発生し、不正形式を確認する2件は
成功した。これは入力形式やテスト読込ではなく、公開契約が未実装であることを示すRedである。

最小実装後、解析テスト5件、CLIテスト37件、全テスト240件がすべて成功した。テスト
メソッド数はCLIが37件、全体が240件で変更していない。

静的確認では、旧5内部型名の定義・参照がないこと、`__all__` が設計どおりの10名であること、
5公開型と `Command` が存在することを確認した。

## Refactorの要否

追加Refactorは不要と判断した。公開型、`Command`、`__all__`、解析、進行分岐は、既存の
`cli.py` の小さい責務として読み取れる。共通基底クラス、タグ付き辞書、別モジュール化は、
今回必要のない抽象化や依存を増やすため行わない。

## 独立レビュー

`3e5adcc..bf90773` を対象に、別の読み取り専用レビュアーが設計・計画との整合性、
公開API10名、旧名不在、型・docstring、入力・進行・エラー文言不変、テスト件数、
不要な対象拡大を確認した。

- Critical：0件
- Important：0件
- Minor：0件
- 評価：マージ可能

追加修正は不要である。レビュー時点で未コミットだった実装計画の進捗チェックは、
レビュー対象のコードコミットには含めず、後続の文書記録として扱う。

## 検証

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v`：37件成功
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`：240件成功
- `rg -n '^    def test_' tests/test_cli.py | wc -l`：37
- `rg -n '^    def test_' tests | wc -l`：240
- 旧内部型名を検索：出力なし
- ASTによる `__all__`・公開型・`Command` の確認：成功

## 現在の状態

設計、実装計画、Red、最小実装、Green-to-Green、Refactor要否確認、独立レビュー、
学習記録をそろえた。`main` への取り込みと取り込み先検証は、本人の明示的な承認を待つ。

## 次回への問い

`main` への取り込みと取り込み先検証が終わった後、最後の理解確認を一問だけ出す。
