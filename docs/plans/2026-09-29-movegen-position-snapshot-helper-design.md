# `test_movegen.py` の局面スナップショット補助を一つにする：設計仕様

作成日：2026-09-29
設計承認日：2026-09-29

## 目的

`tests/test_movegen.py` の `LegalMoveTests`、`LegalMoveListTests`、
`LegalMoveEnumerationTests`、`CheckmateAndGameEndTests`、`UchiFuzumeTests` に
同形で置かれている `_snapshot` を、ファイル内のテスト補助一つへ整理する。

今回のGREENは、局面不変性を確認する既存テストの比較対象と検出範囲を変えず、
局面状態を読み取る処理の更新箇所を一つにすることである。本体コード、公開動作、
期待値、テスト件数は変更しない。

## 現在の問題

5クラスの `_snapshot` はすべて、可変の `Position`（局面データ）から次の値を同じ順で
タプルへ読み取っている。

1. 盤面81マスの駒
2. 先手の、玉を除く基本持ち駒7種の枚数
3. 後手の、玉を除く基本持ち駒7種の枚数
4. 手番

比較項目を将来増減する場合、5か所すべてへ同じ変更が必要になる。更新漏れがあると、
局面不変性の検出範囲がクラスごとにずれる。

## 対象範囲

次の最小変更だけを行う。

1. `LegalMoveTests` の直前に、ファイル内限定の `_position_snapshot(position)` を置く。
2. 5クラスの `_snapshot` を削除する。
3. 各クラスから `_position_snapshot(position)` を直接呼ぶようにする。

次は対象外とする。

- `kaname_shogi/` 以下の本体コードと公開動作
- テストの期待値、局面準備、比較対象、テストメソッド、テスト件数
- `ApplyMoveTests` と `ApplyDropTests` の `_hand_counts`
- `movegen.py` の分割や抽象化
- CLIの駒名入出力対応、CLIコマンド解析の公開境界
- 将棋規則、保存形式、テスト用基底クラスやfixtureの追加

## 配置・命名・docstring

`_position_snapshot` は最初に使う `LegalMoveTests` の直前に置く。前半の駒移動候補・
王手判定のテストに関係しない、局面不変性用のテスト補助だと近接した配置から分かる。

名前の `position` は盤面、先後の持ち駒、手番を持つ可変の局面データ `Position` を指す。
`snapshot` はその状態を比較用の変更不能なタプルとして写す値であり、局面を指す・置く
操作ではない。

docstringには、盤面81マス、先手持ち駒、後手持ち駒、手番をこの順で読み、持ち駒は
玉を除く基本駒7種を `BasicPieceType` の列挙順で読むこと、局面を変更しないことを
日本語で明記する。

## 既存テストの意図を保つ方法

5クラスは共通補助を直接呼び、中継する同名メソッドや共通基底クラスは作らない。
これにより、状態を読む実装は一つだけになる。

各クラスの責務は、次の既存のクラス名と各テストメソッドの日本語docstringで保つ。

- `LegalMoveTests`：自玉を王手にさらさない合法性
- `LegalMoveListTests`：全合法手の列挙
- `LegalMoveEnumerationTests`：合法手の有無と弱い一手選択
- `CheckmateAndGameEndTests`：詰みと終局
- `UchiFuzumeTests`：打ち歩詰めと内部再帰境界

共通化するのは局面状態の読み取りだけであり、各テストが作る局面、呼ぶ操作、期待する
結果、比較するタイミングは変えない。期待値を `movegen` の実装や本体ヘルパーから
生成しないため、実装側と同じ誤りを期待値へ写さない独立性も保つ。

## Green-to-Greenの確認方法

実装前後で、次を同じ条件で実行する。

1. `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_movegen -v` を実行し、
   対象158件が成功することを確認する。
2. `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` を実行し、
   全テストの件数と成功結果を確認する。
3. 差分と静的確認で、`_position_snapshot` が1定義だけで、5クラスが直接使い、
   旧 `_snapshot` が残っていないことを確認する。
4. 差分で `kaname_shogi/` に変更がないこと、テストメソッドと期待値が変わらないことを
   確認する。

今回は既存テストの構造整理であり、新しい振る舞いを作らない。したがって、故意に
既存テストを失敗させるRedは作らず、変更前後の同一成功結果と差分確認を
Green-to-Greenの根拠とする。

## 記録形式

- 本設計仕様には、対象範囲、配置・命名、比較対象、意図の保存、Green-to-Greenの
  根拠、承認ゲートを記録する。
- `docs/plans/2026-09-29-movegen-position-snapshot-helper.md` には、承認済み設計を
  実行する具体的な手順と検証方法を記録する。
- `docs/learning/48-movegen-position-snapshot-helper.md` には、本人の回答、実際の変更、
  Green-to-Green、Refactor要否、独立レビュー、検証、最後の理解確認を記録する。
- 完了段階で `docs/README.md`、`docs/roadmap-repository-foundation.md`、
  `docs/resume.md` を現在状態へ更新する。`docs/next-topics.md` は、最後の理解確認後に
  次テーマを見直す段階で更新する。

## 承認ゲート

本設計仕様を自己レビューし、日本語のConventional Commitでコミットした後、本人の
レビューと明示的な承認を待つ。

仕様書の承認後に `superpowerssuperpowers:writing-plans` を使って実装計画を文書化する。
実装計画をコミットして提示し、本人の明示的な承認を受けるまで、対象テスト、既存文書、
本体コードを変更せず、TDD／Refactor作業を開始しない。
