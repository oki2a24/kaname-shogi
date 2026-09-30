# 第49回：CLIの駒名入出力対応を一つの定義から導く

## 目的

`kaname_shogi/cli.py` で別々に定義されていた、駒打ちの基本駒7種の
`BasicPieceType` と日本語名の対応を、一つの定義から表示・入力の両方向へ導く構造に整理する。表示名、入力文法、入力可能な駒、順序、エラー文言、公開動作、テスト件数は変更しない。

設計は[設計仕様](../plans/2026-09-30-cli-piece-name-single-definition-design.md)、手順は[実装計画](../plans/2026-09-30-cli-piece-name-single-definition.md)に記録した。

## 合意した設計

- `cli.py` 内に、順序付きの `_DROP_PIECE_SPECS` を置く。
- 各要素は、駒種を表すデータ `BasicPieceType` と日本語名の組である。これは駒を打つ操作ではなく、CLI用表記の対応を表すデータである。
- 順序は歩・香・桂・銀・金・角・飛のままにする。
- `_PIECE_NAMES`（型から名称）と `_PIECE_TYPES_BY_NAME`（名称から型）を、`_DROP_PIECE_SPECS` からモジュール定数として導く。
- `display.py` の14種の盤面表示、`model.py`、テスト、次の「CLIコマンド解析の公開境界を設計し直す」テーマは対象外とする。

## 変更内容

`cli.py` に `_DROP_PIECE_SPECS` を追加し、従来の手書き `_PIECE_NAMES` を `dict(_DROP_PIECE_SPECS)` に置き換えた。逆引きの `_PIECE_TYPES_BY_NAME` も同じ正本から導き、`parse_command` の駒打ち解析で使っていたローカルの `piece_types` 辞書を削除した。

これにより、コンピュータの駒打ち表示は従来どおり `_PIECE_NAMES` を使い、入力解析は同じ正本由来の逆引きを使う。`KeyError` と `ValueError` を `ValueError("入力形式が正しくありません。")` へ変換する既存の境界は変更していない。

コード変更は次のコミットに記録した。

```text
35559d3 refactor: CLI駒名対応を一つの定義から導く
```

## Green-to-Greenの確認

変更前と変更後の双方で、次を確認した。

- `tests.test_cli`：37件成功
- `tests.test_display`：3件成功
- 全テスト：240件成功
- テストメソッド数：240件

静的確認では、`_DROP_PIECE_SPECS` が1件、二つの派生辞書が正本を参照すること、`parse_command` 内の旧 `piece_types` が0件であることを確認した。作業ブランチ上で `display.py`、`model.py`、テストに差分はなく、`git diff --check` も成功した。

計画に記載した `py_compile` は、実行環境のPythonがワークスペース外の `com.apple.python` キャッシュへバイトコードを書こうとして権限拒否になった。構文エラーではなくキャッシュ書込みの失敗であることを確認し、ファイルを変更しない `ast.parse` に置き換えて `cli.py` の構文解析成功を確認した。

## Refactorの要否

追加Refactorは不要と判断した。正本、表示用派生、入力用派生、利用箇所が `cli.py` 内の小さい責務単位に収まっている。共有モジュール化や `display.py` との統合は、成駒・王玉の表示という別責務を混ぜ、今回の対象範囲を広げるため行わない。

## 独立レビュー

`main` の `fff0d80` からコード変更コミット `35559d3` までを対象に、読み取り専用の独立レビューを行った。

- Critical：0件
- Important：0件
- Minor：0件
- 結論：マージ可能

レビューでは、正本から二方向へ導く構造、入力形式エラーへの既存変換、コンピュータの駒打ち表示、対象外ファイル不変、書式検査を確認した。追加修正はない。

## 現在の状態

設計、実装計画、コード変更、Green-to-Green、Refactor要否確認、独立レビュー、学習記録をそろえた。main取り込みと取り込み先検証は、本人の明示的な承認待ちである。取り込み後に、最後の理解確認を一問だけ出し、本人の回答を待つ。
