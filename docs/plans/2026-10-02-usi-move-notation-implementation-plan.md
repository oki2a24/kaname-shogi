# USI指し手表記と内部の一手の対応：実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには `executing-plans` スキルを使用する。各ステップには追跡用チェックボックスを使う。

## 状態

2026-10-02に作成し、同日本人が承認した。codex/usi-move-notation ブランチで実行中。

**目標:** USIの一手トークンと `BoardMove` / `DropMove` を双方向に変換する純粋関数を追加する。

**アーキテクチャ:** `kaname_shogi.usi_move` に解析・形式化関数を置き、中立な既存値型をそのまま使う。文字列文法と値の型契約だけを検証し、局面依存の合法性は扱わない。`unittest` の専用テストで各表記と失敗条件を確認する。

**技術スタック:** Python標準ライブラリ、`unittest`、既存の `kaname_shogi.move` / `kaname_shogi.model`。

**仕様 (Spec):** [2026-10-02-usi-move-notation-design.md](2026-10-02-usi-move-notation-design.md)

**グローバル制約 (Global Constraints):**
- 「変換APIはUSI専用モジュールで公開し、Move の値型はUSIに依存させない。」
- 「不正な一手表記と表記できない Move 値は ValueError とする。」
- 「玉打ち表記は変換時に拒否する。」
- 「両関数は入力値と出力値だけを扱う純粋な変換操作で、局面・持ち駒・手番を変更しない。」
- 「kaname_shogi.usi_move から直接importできる公開名とする。kaname_shogi.__init__ からは再exportしない。」
- 「position コマンド全体の解析、startpos / sfen の局面解釈、複数手の局面再現」は対象外。
- 「指し手の局面適用、合法手判定、手番・持ち駒・盤面の検証」は対象外。
- 確認には標準ライブラリ `unittest` を使い、`tests/test_usi_move.py` と全テストを実行する。
- 公開関数のdocstringには引数・戻り値・副作用・前提条件と設計理由を日本語で記す。テストメソッド名は英語、日本語docstringで検証する振る舞いと背景を説明する。

## レビューフォーカス (Review Focus)

- コマンド接頭辞、前後空白、余分な文字を一手トークンとして受け取った場合、`ValueError` になること（`test_parse_rejects_malformed_tokens`）。
- 筋・段の境界が取り違えられず、`1a` と `9i` がそれぞれ `Square(1, 1)` と `Square(9, 9)` になること（`test_parse_maps_edge_squares_without_legality_check`）。
- 持ち駒にできない玉の打ち表記が `ValueError` になること（`test_parse_rejects_king_drop`）。
- 構成型でもフィールドの型契約に反する値をUSI表記へ誤変換せず、`ValueError` にすること（`test_format_rejects_invalid_move_fields`）。
- 局面を受け取らない解析が駒の動きや局面合法性を誤って判定しないこと（構文上の座標対 `1a9i` を解析できる同じ境界テストで確認する）。

## ファイル構成

- 作成: `kaname_shogi/usi_move.py` — USI一手トークンの解析・形式化と、その公開関数の契約を定義する。
- 作成: `tests/test_usi_move.py` — USI表記とMove値の対応、往復、拒否条件を標準ライブラリで検証する。
- 作成: `docs/knowledge/usi-move-notation.md` — 後続のposition処理とbestmove出力で再利用する表記・座標の対応を一次資料付きで記録する。
- 更新: `docs/learning/55-usi-move-notation.md` — 実装、Red/Green、検証、リファクタ要否、独立レビュー、未解決事項を記録する。
- 更新: `docs/plans/2026-10-02-usi-move-notation-design.md` — 本人の承認状態を記録する。
- 変更しない: `kaname_shogi/move.py`、`kaname_shogi/model.py`、`kaname_shogi/__init__.py`、`tests/test_move.py`。USI依存を値型へ持ち込まず、既存の値型テストを変換テストと混ぜない。

## 実装タスク

各TDDサイクルでは、先に振る舞いテストを書き、対象テストを実行して期待値との差によるRedを確認してから最小実装を加える。初回にモジュール読み込みエラーが起きても、それだけを振る舞いのRed完了とは扱わない。必要なら関数名を持つ仮の足場を置き、テストが値の不一致で失敗する状態を確認する。

## Task 1: 盤上移動の解析

**ファイル:**
- 作成: `tests/test_usi_move.py`
- 作成: `kaname_shogi/usi_move.py`

**インターフェース (Interfaces):**
- 生産: `parse_usi_move(text: str) -> Move`。このタスクでは盤上移動の通常・成り表記を解析する。
- 生産: 後続タスク用に `format_usi_move(move: Move) -> str` の関数名もモジュールに置く。実装前の仮実装は、形式化テストが値の不一致を示す段階で置き換える。

- [x] **ステップ1: 盤上移動の振る舞いテストを先に作成する**

`UsiMoveParseTests` に次のテストを追加する。各テストメソッド名は英語、日本語docstringに確認する振る舞いと誤りの背景を書く。

| テスト | 入力 | 期待値 |
| --- | --- | --- |
| `test_parse_board_move_without_promotion` | `7g7f` | `BoardMove(Square(7, 7), Square(7, 6), False)` |
| `test_parse_board_move_with_promotion` | `8h2b+` | `BoardMove(Square(8, 8), Square(2, 2), True)` |
| `test_parse_maps_edge_squares_without_legality_check` | `1a9i` | `BoardMove(Square(1, 1), Square(9, 9), False)` |

`test_parse_rejects_malformed_tokens` は `""`、`"7g7"`、`"7g7f++"`、`" 7g7f"`、`"7g7f "`、`"position startpos moves 7g7f"`、`"0g7f"`、`"10g7f"`、`"7j7f"`、`"7g7F"`、`"p*5e"`、`"X*5e"`、`"*P5e"`、`"P+*5e"`、`"P*5e+"` を `subTest` と `assertRaises(ValueError)` で確認する。玉打ちはタスク2の専用テストで確認する。

- [x] **ステップ2: 値の不一致によるRedを確認する**

実行: `python3 -m unittest tests.test_usi_move.UsiMoveParseTests -v`

モジュール未作成によるimportエラーだけでは振る舞いのRedとしない。テストを書いた後、`kaname_shogi/usi_move.py` に `parse_usi_move` と `format_usi_move` が `None` を返す一時的な足場を置いて同じコマンドを再実行する。期待値と `None` の不一致、および不正入力で `ValueError` が起きない失敗を確認する。

- [x] **ステップ3: 盤上移動の解析を実装する**

`kaname_shogi/usi_move.py` に公開関数 `parse_usi_move(text: str) -> Move` と必要最小限の内部処理を実装する。USIの数字を `Square.file`、段字を1〜9の `Square.rank` に対応させ、末尾 `+` の有無だけを `promote` に反映する。`1a9i` を解析できるままにし、駒の移動規則は導入しない。docstringには引数・戻り値・副作用・前提条件・局面合法性を判定しない設計理由を日本語で記す。

- [x] **ステップ4: 盤上移動テストのGreenを確認する**

実行: `python3 -m unittest tests.test_usi_move.UsiMoveParseTests -v`

期待値: 通常移動、成り、境界座標、不正トークンの各テストがPASS。

## Task 2: 駒打ちの解析

**ファイル:**
- 変更: `tests/test_usi_move.py`
- 変更: `kaname_shogi/usi_move.py`

**インターフェース (Interfaces):**
- 消費: `parse_usi_move(text: str) -> Move`。
- 生産: 7種類の駒打ち表記を `DropMove(BasicPieceType, Square)` に変換する。

- [x] **ステップ1: 7種の対応と玉打ち拒否のテストを作成する**

`test_parse_drop_move_for_each_hand_piece` で次の表記をすべて `Square(5, 5)` への対応値と照合する。

| 入力 | 期待する駒種 |
| --- | --- |
| `P*5e` | `BasicPieceType.PAWN` |
| `L*5e` | `BasicPieceType.LANCE` |
| `N*5e` | `BasicPieceType.KNIGHT` |
| `S*5e` | `BasicPieceType.SILVER` |
| `G*5e` | `BasicPieceType.GOLD` |
| `B*5e` | `BasicPieceType.BISHOP` |
| `R*5e` | `BasicPieceType.ROOK` |

`test_parse_rejects_king_drop` は `K*5e` に `ValueError` を期待する。

- [x] **ステップ2: 対象テストのRedを確認する**

実行: `python3 -m unittest tests.test_usi_move.UsiMoveParseTests -v`

期待値: 7種の有効な打ち表記が `DropMove` と一致せず失敗する。玉打ち拒否テストはタスク1の一般的な不正形式拒否により既にPASSしていてよい。

- [x] **ステップ3: 駒打ち表記を解析する**

`parse_usi_move` の既存分岐に、USI大文字記号と7種の `BasicPieceType` の対応を追加する。`K` や未知の記号を対応表へ加えず、`ValueError` にする。

- [x] **ステップ4: 駒打ちテストのGreenを確認する**

実行: `python3 -m unittest tests.test_usi_move.UsiMoveParseTests -v`

期待値: 盤上移動と7種の駒打ちがPASSし、玉打ちテストも `ValueError` を確認してPASS。

## Task 3: Move値のUSI形式化と往復

**ファイル:**
- 変更: `tests/test_usi_move.py`
- 変更: `kaname_shogi/usi_move.py`

**インターフェース (Interfaces):**
- 消費: `parse_usi_move(text: str) -> Move`。
- 生産: `format_usi_move(move: Move) -> str`。`BoardMove` は4文字または末尾 `+` を含む5文字、`DropMove` は駒記号・`*`・座標の表記を返す。

- [x] **ステップ1: 盤上・駒打ちの出力と往復テストを作成する**

`test_format_board_move_with_and_without_promotion` で `7g7f`、`8h2b+`、境界座標を含む `1a9i` の値から同じ表記を期待する。`test_format_drop_move_for_each_hand_piece` でタスク2の7種を `P*5e` などへ対応させる。`test_parse_and_format_round_trip` で通常移動、成り、境界座標、7種の打ちについて `format_usi_move(parse_usi_move(token)) == token` を確認する。

同じテスト追加で、`test_format_rejects_non_move_values` は未対応オブジェクトを、`test_format_rejects_invalid_move_fields` は `BoardMove("1a", Square(1, 2), False)`、`BoardMove(Square(1, 1), Square(1, 2), 1)`、`DropMove("P", Square(5, 5))`、`DropMove(BasicPieceType.KING, Square(5, 5))` を `ValueError` として確認する。例外メッセージは固定しない。

- [x] **ステップ2: 形式化のRedを確認する**

実行: `python3 -m unittest tests.test_usi_move.UsiMoveFormatTests -v`

期待値: 未実装の形式化関数の結果が期待するUSIトークンと一致せず失敗し、不正な値も `ValueError` にならず失敗する。

- [x] **ステップ3: USI形式化を実装する**

`kaname_shogi/usi_move.py` に公開関数 `format_usi_move(move: Move) -> str` を実装し、`BoardMove` と `DropMove` の型で表記を分ける。数字・段文字と成り記号、駒種記号・`*` の順は設計仕様の対応に従う。局面や持ち駒を参照しない。docstringには引数・戻り値・副作用・前提条件・局面を参照しない設計理由を日本語で記す。

- [x] **ステップ4: 出力と往復のGreenを確認する**

実行: `python3 -m unittest tests.test_usi_move.UsiMoveFormatTests -v`

期待値: 盤上移動、成り、7種の駒打ち、各種往復テストがPASS。

## Task 4: Refactor確認、全体検証、記録、独立レビュー

**ファイル:**
- 変更: `kaname_shogi/usi_move.py`
- 変更: `tests/test_usi_move.py`
- 作成: `docs/knowledge/usi-move-notation.md`
- 変更: `docs/learning/55-usi-move-notation.md`
- 変更: `docs/plans/2026-10-02-usi-move-notation-design.md`

**インターフェース (Interfaces):**
- 消費: 完成した解析・形式化関数と専用テスト。
- 生産: 検証・レビュー結果・学習記録・参照用知識メモを含むレビュー可能な差分。

- [x] **ステップ1: Refactorの要否を確認する**

重複や責務の混在があれば、APIとUSI対応を変えず小さく整理し、なければ「不要」と学習記録へ記す。変更した場合は専用テストを再実行する。

- [x] **ステップ2: 独立コードレビューを行い、指摘を解消する**

製品コードとテストの差分を、実装者とは別のレビュー視点で確認し、Critical / Important / Minorを分類する。CriticalまたはImportantがあれば修正テストのRed、最小修正、Green、全体テスト、再レビューを行う。結論と対応は学習記録の実装結果を確定する段階で記録する。

- [x] **ステップ3: 個別・全体テストと差分検査を実行する**

実行:

```bash
python3 -m unittest tests.test_usi_move -v
python3 -m unittest discover -s tests -v
git diff --check
```

期待値: 専用テストと全テストが終了コード0で通り、`git diff --check` に問題がない。Critical / Important修正がある場合は修正後に再実行する。ShogiHome接続や実機対局は行わない。

- [x] **ステップ4: 知識メモと学習記録を更新する**

`docs/knowledge/usi-move-notation.md` に一手文法、座標対応、7種の駒打ち記号、純粋な一手変換と局面合法性の境界、USI一次資料へのリンクを記録する。学習記録には実際のテストコマンドと結果、Red/Green、Refactor判断、未実施の実機接続、独立レビューのCritical / Important / Minorと対応を記す。計画や結果を実施前に実施済みと書かない。

- [x] **ステップ5: 記録内容を確認してから日本語のConventional Commitを作成する**

学習記録と知識メモを本人に提示して内容確認を受けてから、レビュー済みの実装・テスト・文書をステージし、`git diff --cached --check` でステージ済みの全ファイルを確認して作業ブランチにコミットする。候補メッセージ: `feat: USI指し手表記と一手データを相互変換する`。mainへの取り込みはこの計画に含めない。

- [x] **ステップ6: 最後の理解確認を一問行い、回答を記録する**

検証・レビュー・記録・コミット後、USI座標または盤上移動と駒打ちの対応について一問だけ出し、回答を待つ。回答と補足を区別して学習記録へ追記し、その記録変更は本人の確認後に別の日本語Conventional Commitで記録する。次テーマの提案はこの回答記録後に行う。

## 実行方法の確認

計画は1つの新規モジュール、1つの専用テスト、逐次依存する3つのTDDサイクルで構成される。実装はこのセッションで行い、タスク実装をサブエージェントへ委譲しない。`AGENTS.md` の独立レビュー要件を満たすため、Task 4では別のレビュアーによるコードレビューを一度行う。
