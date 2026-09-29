# 第47回：CLI実行入口のスモークテスト配置を明確にする

## 目的

`tests/test_display.py` にある `test_cli_exits_from_game_mode_menu_on_eof` を、
表示変換の単体テストではなく、`python -m kaname_shogi` の実行入口を確認する
限定的なCLI E2E／スモークテストだと、名前と配置から一目で分かる構造へ整理する。
テストの振る舞い、公開動作、本体コード、全240件というテスト総数は変更しない。

設計は [設計仕様](../plans/2026-09-29-cli-entrypoint-smoke-test-placement-design.md)、
手順は [実装計画](../plans/2026-09-29-cli-entrypoint-smoke-test-placement.md) に記録した。

## 開始時の状態と確認資料

開始時に現在値を確認した。

```text
$ git status --short --branch
## codex/cli-entrypoint-smoke-test-placement

$ git log -3 --oneline
ca41aa2 docs: CLI入口スモークテスト配置の実装計画を作成する
60062a0 docs: CLI入口スモークテスト配置を設計する
36a23b8 docs: CLI入口テスト整理の引き継ぎを作成する
```

確認資料は `AGENTS.md`、README、文書索引、再開案内、次テーマ候補、引き継ぎ、
ロードマップ、第46回学習記録・設計仕様、`tests/test_display.py`、
`kaname_shogi/__main__.py`、`kaname_shogi/cli.py` である。

設計承認後に `codex/cli-entrypoint-smoke-test-placement` ブランチを作成し、
設計仕様と実装計画を本人の承認後に記録した。

## 設計で合意したこと

- 移動先は `tests/test_cli_entrypoint.py` とする。
- クラス名は `CliEntrypointSmokeTests` とする。
- メソッド名 `test_cli_exits_from_game_mode_menu_on_eof` は維持する。
- 対象テストのdocstring、`subprocess.run` の引数、作業ディレクトリ、入力、
  UTF-8指定、終了コード・標準出力・標準エラーの期待値を維持する。
- `tests/test_display.py` は表示テスト3件と表示用importだけにする。
- 本体コード、公開動作、本格的な対局E2E、`test_movegen.py` は対象外とする。
- 設計仕様、実装計画、学習記録を分離し、個別テスト・全テスト・差分・リンク・
  書式・独立レビューを確認する。

### 選択肢の比較

`tests/test_cli.py` へ追加するとCLI関連のテストを集約できるが、注入した入出力を
使う結合テストの中に実プロセス境界が埋もれる。`tests/test_main.py` へ移すと
`__main__.py` との対応は示せるが、スモークテストの性質が弱い。
専用ファイルとクラスを採用すると、実行入口・実プロセス・限定的な確認という
責務を配置から発見できる。

## 移動前の基準確認

2026-09-29、移動前の配置で次を実行した。

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_display.DisplayTests.test_cli_exits_from_game_mode_menu_on_eof -v
Ran 1 test in 0.032s
OK
```

同時点の全テストも実行し、`Ran 240 tests in 0.581s`、`OK` だった。

## 実装した変更

`tests/test_display.py` から対象テストと `Path`、`subprocess`、`sys` のimportを
取り出し、新設した `tests/test_cli_entrypoint.py` の
`CliEntrypointSmokeTests` へ移した。表示側のモジュールdocstringは、表示の筋段、
所有者、手番、成駒名の誤りを検出する説明へ整理した。

テスト本体のASTを移動前の `HEAD:tests/test_display.py` と移動後の新ファイルで
比較し、`ast.dump(..., include_attributes=False)` が一致することを確認した。
したがって、実行するプロセス、入力、期待する出力、終了コード、標準エラーの
検証は変わっていない。

テスト移動は次のコミットへ記録した。

```text
f0431c8 test: CLI入口スモークテストを専用配置へ移す
```

## Greenの確認

移動後に次を実行した。

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli_entrypoint.CliEntrypointSmokeTests.test_cli_exits_from_game_mode_menu_on_eof -v
Ran 1 test in 0.032s
OK

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_display.DisplayTests -v
Ran 3 tests in 0.000s
OK

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
Ran 240 tests in 0.577s
OK
```

`kaname_shogi/` には差分がなく、対象テスト・表示テスト・全テストが成功した。

## Refactorの要否

追加のRefactorは不要と判断した。新規ファイルは実プロセステスト1件だけを持ち、
表示ファイルは表示テスト3件だけを持つ。新しいfixture、モック、補助関数、抽象化を
追加せず、責務境界だけを明確にできているためである。

今回のTDD適用は、新しい振る舞いを作るRed-Greenではなく、既存テストを移す
Green-to-Greenのリファクタリングとした。移動前の既存テスト1件と全240件の成功を
基準にし、移動後の同じAST、対象1件、表示3件、全240件の成功を比較した。計画と
この判断は本人の承認を得ている。

## 独立レビュー

`ca41aa2..f0431c8` を対象に読み取り専用の独立コードレビューを実施した。

### 強み

- 対象テストのdocstring、実行条件、期待値を保ったまま専用ファイルへ移している。
- `test_cli_entrypoint.py` と `CliEntrypointSmokeTests` からCLI実行入口の限定的な
  スモークテストだと分かる。
- `test_display.py` からCLI用importを除去し、表示責務へ整理している。
- 本体コードと対象外テストを変更していない。

### 結論

- Critical：0件
- Important：0件
- Minor：0件
- マージ可能：Yes

レビュー結果に基づく追加修正はない。次は学習記録と現在状態の文書を更新し、
main取り込みの承認を待つ。

## 検証

- 移動前の対象テスト1件：成功
- 移動後の対象テスト1件：成功
- 表示テスト3件：成功
- 全240件：成功
- 移動前後の対象テストAST：一致
- `kaname_shogi/` の差分：なし
- `git diff --check`：成功

文書の相対リンク、ロードマップ・索引・再開案内の作業中状態は、次の記録段階で
検査する。mainへの取り込みと取り込み先検証はまだ行っていない。

## 振り返り

テストの振る舞いが正しくても、表示テストのファイルとクラスに実プロセス境界を
置くと、`__main__.py` の変更時に必要なテストを探しにくい。テスト名だけでなく、
ファイル名とクラス名に主対象とテストの性質を表す語を置くことで、テストを探す
経路自体を短くできることを確認した。

## 最後の理解確認

### 問題

今回、テストメソッドの内容を変えず、ファイル名とクラス名を変えるだけで保守性が
上がるのはなぜでしょうか。

本人の回答：人間とAIにとってわかりやすくなったため

アシスタントの補足：その通り。ファイル名とクラス名が、CLI実行入口の限定的な
スモークテストという主対象と性質を示すため、人間にもAIにも実装を読む前に目的と
確認場所が分かる。`__main__.py` を変更するときに関連テストを見落としにくくなり、
表示テストと実プロセステストの失敗原因も切り分けやすくなる。

## main取り込みと取り込み先検証

本人の明示的な承認を得て、`codex/cli-entrypoint-smoke-test-placement` を `main` へ
fast-forwardで取り込んだ。取り込み後の `main` のHEADは `729f974` である。

取り込み先で次を実行した。

```text
対象スモークテスト：1件成功
表示テスト：3件成功
全テスト：240件成功（Ran 240 tests in 0.509s、OK）
相対リンク：199件を検査し、不足なし
git diff --check：成功
作業ツリー：クリーン
```

取り込み先でも `kaname_shogi/` に変更はなく、テスト配置の変更が公開動作へ影響
していないことを確認した。

## 未解決事項

今回のテーマ内に未解決事項はない。

## 次テーマの選定

README、プロジェクトの方向性、`docs/next-topics.md` を見直した。本人は、第46回の
構造レビューから残る3件を「構造整理の残り」という順番付きの大きなまとまりとして
予約し、実装は別テーマ・別承認で一つずつ進めることを選んだ。

1. `test_movegen.py` の局面スナップショット補助を一つにする。
2. CLIの駒名入出力対応を一つの定義から導く。
3. CLIコマンド解析の公開境界を設計し直す。

次の新しいセッションでは1件目だけを開始する。2件目と3件目は順番を予約しただけで、
前のテーマが完了するまで設計・実装を開始しない。
