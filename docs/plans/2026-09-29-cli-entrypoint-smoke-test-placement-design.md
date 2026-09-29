# CLI実行入口のスモークテスト配置を明確にする：設計仕様

作成日：2026-09-29
設計承認日：2026-09-29

## 目的

`tests/test_display.py` に置かれている
`test_cli_exits_from_game_mode_menu_on_eof` を、名前と配置から
`python -m kaname_shogi` の実行入口を確認する限定的なE2E／スモークテストだと
一目で分かる構造にする。

今回のGREENは、表示の単体テストとCLI実行入口の実プロセステストを分離し、
ファイル名、クラス名、テスト名からそれぞれの主対象を判別できることである。
テストの振る舞い、公開動作、本体コード、テスト件数は変更しない。

## 現在の問題

対象テストは、実プロセスで次の境界を確認している。

- `python -m kaname_shogi` によるモジュール実行
- 対局形式メニューの標準出力
- 標準入力がEOFになった場合の正常終了
- 終了コードが0であること
- 対局開始前なので盤面を表示しないこと
- 標準エラーが空であること

テストメソッド名とdocstringから確認内容は分かるが、現在は
`tests/test_display.py` の `DisplayTests` にあり、表示変換のテストに見える。
そのため、`kaname_shogi/__main__.py` の実行入口を変更する人が、対応する
実プロセステストを配置から発見しにくい。

## 対象範囲

次の最小変更だけを行う。

1. `tests/test_display.py` から
   `test_cli_exits_from_game_mode_menu_on_eof` を取り出す。
2. `tests/test_cli_entrypoint.py` を新設する。
3. 新規ファイルに `CliEntrypointSmokeTests` を定義し、対象テストを移す。
4. `Path`、`subprocess`、`sys` のimportを対象テストとともに新規ファイルへ移す。
5. `tests/test_display.py` のモジュールdocstringを、残る表示テスト3件の責務に
   合う説明へ更新する。
6. 新規ファイルのモジュールdocstringに、CLI実行入口を実プロセスで確認する
   限定的なスモークテストであることを記す。

次は対象外とする。

- `kaname_shogi/__main__.py`、`kaname_shogi/cli.py`、その他の本体コードの変更
- テスト対象となる公開動作や出力文言の変更
- 本格的な対局E2Eの追加
- 新しい補助関数、fixture、モックの導入
- `tests/test_movegen.py` の局面スナップショット補助の共通化
- CLI機能、将棋規則、保存形式の変更

## 配置と命名

移動後の構造は次のとおりとする。

```text
tests/test_display.py
└── DisplayTests
    ├── test_renders_all_promoted_piece_names
    ├── test_initial_position_matches_full_display
    └── test_turn_label_follows_position

tests/test_cli_entrypoint.py
└── CliEntrypointSmokeTests
    └── test_cli_exits_from_game_mode_menu_on_eof
```

`test_cli_entrypoint.py` は主対象がCLI実行入口であること、
`CliEntrypointSmokeTests` は実プロセスを使う限定的なスモークテストであること、
テストメソッド名はEOF時に確認する具体的な振る舞いを示す。

`tests/test_cli.py` には移さない。同ファイルの37件は、差し替え可能な入力・出力・
乱数を使ってCLIの解析、モード選択、対局調停を確認する結合的テストである。
実プロセスを起動する1件を専用ファイルへ分けることで、異なるテスト境界を
配置から区別できる。

`tests/test_main.py` という名前も採用しない。`__main__.py` との対応は示せるが、
CLIの実行入口と限定的なスモークテストという性質が
`test_cli_entrypoint.py` より伝わりにくいためである。

## 既存テストの意図を保つ方法

対象テストでは、次を変更せず移動する。

- テストメソッド名
- 日本語docstring
- `subprocess.run` のコマンドと引数
- `Path(__file__).resolve().parents[1]` による作業ディレクトリ
- 空文字列を渡す標準入力
- 標準出力と標準エラーの取得方法
- UTF-8の文字コード指定
- 終了コード、標準出力、標準エラーの期待値

新規ファイルも `tests/` 直下に置くため、既存の作業ディレクトリ計算は引き続き
リポジトリ直下を指す。テスト本体を共通化・抽象化せず、どの外部境界を
通して何を確認するかを一つのメソッドから直接読める形を保つ。

移動によるテストの削除や追加は行わず、全テスト数は240件のままとする。

## 記録形式

- 本設計仕様には、対象範囲、配置と命名、判断理由、意図の保存方法、
  検証方法、承認ゲートを記録する。
- `docs/plans/2026-09-29-cli-entrypoint-smoke-test-placement.md` には、
  承認済み設計を実行する具体的な手順と検証コマンドを記録する。
- `docs/learning/47-cli-entrypoint-smoke-test-placement.md` には、本人の回答、
  実際の変更、Red・Green・Refactorの確認、検証結果、独立レビュー、振り返り、
  最後の理解確認を記録する。
- 完了段階で `docs/README.md`、`docs/roadmap-repository-foundation.md`、
  `docs/resume.md` を現在状態へ合わせる。
- `docs/next-topics.md` は、最後の理解確認後に次テーマ候補を見直す段階で更新する。
  予定されている `test_movegen.py` のテーマ自体は今回開始しない。

## 検証方法

次を順に確認する。

1. 移動前に既存配置の対象テスト1件を個別実行し、成功する基準状態を記録する。
2. 移動後に新しい配置の対象テスト1件を個別実行し、同じ振る舞いで成功することを
   確認する。
3. `tests/test_display.py` に残る表示テスト3件が成功することを確認する。
4. 全テストを実行し、240件のまま全件成功することを確認する。
5. 差分で、対象テストのdocstring、実行条件、期待値が変わっていないことを確認する。
6. `kaname_shogi/` に差分がなく、本体コードを変更していないことを確認する。
7. 更新文書の相対Markdownリンクがすべて解決することを確認する。
8. `git diff --check` が成功することを確認する。
9. Refactor要否を記録した後、独立レビューでCritical・Important・Minorを判定する。
10. CriticalまたはImportantがあれば修正し、再検証・再レビューする。
11. 本人の承認後に `main` へ取り込み、取り込み先でも全テストと必要な文書検査を
    再実行する。

今回は既存の正常なテストを責務に合う場所へ移すため、新しい失敗ケースは追加しない。
振る舞いのRedを作るために一時的な読み込みエラーを起こすこともしない。移動前後の
同一成功結果と差分検査を、振る舞い不変の根拠とする。

## 承認ゲート

この設計仕様を作業ブランチへ記録して自己レビューし、日本語の
Conventional Commitでコミットした後、本人のレビューと明示的な承認を待つ。

設計文書の承認後に `superpowerssuperpowers:writing-plans` を使って実装計画を
文書化し、コミットして再び本人の明示的な承認を待つ。実装計画の承認前には、
対象テストの移動、既存文書の更新、TDD／Refactor作業を開始しない。
