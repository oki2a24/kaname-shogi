# 移動先候補に合う空マスへの移動 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** `apply_move` が、手番に合う出発駒の既存候補に含まれる空マスだけへ移動を適用するようにする。

**アーキテクチャ:** `movegen.py` に非公開の候補選択ヘルパーを追加し、盤上の `PieceType` から既存の8種類の候補生成関数を選ぶ。`apply_move` は所有者・手番を照合した後、盤面変更前に候補照合を行い、成功時だけ既存の `move_piece` と手番交代へ進む。`move_piece` の盤面専用の責務と公開APIは変えない。

**技術スタック:** Python 3.9、標準ライブラリ `unittest`、dataclasses、Enum。

**仕様 (Spec):** `docs/design/12-candidate-only-empty-square-move.md`

**グローバル制約 (Global Constraints):**
- 既存の移動先候補に含まれる「空マス」への移動だけを扱う。
- 駒取り、持ち駒、成り、王手、合法手の確定、CLI入力は扱わない。
- テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞い、続く本文に検出したい誤りや背景を書く。
- 公開インターフェースのdocstringには引数・戻り値・副作用・前提条件と設計理由を記録する。
- 機能ごとに、振る舞いを確認する失敗テスト、最小実装、成功確認、Refactorの要否確認を行う。読み込みエラーだけでRed確認を完了と扱わない。

---

## ファイル構成

- `kaname_shogi/movegen.py`：駒種から既存候補関数を選ぶ非公開ヘルパーと、候補照合後に局面を変更する `apply_move` を置く。
- `tests/test_movegen.py`：候補内の空マスの成功、候補外の局面不変、先後の歩の成功を確認する。
- `README.md`：`apply_move` の候補照合、空マス限定、対象外を利用者向けに説明する。
- `docs/resume.md`、`docs/next-topics.md`：第24回完了後の到達点と次の候補を更新する。
- `docs/learning/24-candidate-only-empty-square-move.md`：実際のRed・Green・Refactor・検証・レビュー・理解確認を記録する。
- `docs/knowledge/17-candidate-only-empty-square-move.md`：確定した参照知識を維持する。

### タスク1: 候補内・候補外の局面適用をテストで固定する（完了）

**ファイル:**
- 変更: `tests/test_movegen.py:96-172`（`ApplyMoveTests`）

**インターフェース (Interfaces):**
- 消費 (Consumes): `movegen.apply_move(position: Position, source: Square, destination: Square) -> None`、`Board`、`Piece`、`PieceType`、`Position`、`Side`、`Square`。
- 生産 (Produces): 候補内の空マスだけを適用し、候補外を局面不変で拒否する `apply_move` のテスト契約。

- [x] **ステップ 1: 失敗するテストを作成する**

`ApplyMoveTests` に次の2メソッドを追加する。全8駒種の到着先は、空の５五から各既存候補関数が返す座標を直接記す。候補外テストは先後の歩について反対向きの空マスを指定する。

```python
def test_moves_each_piece_to_an_empty_candidate_and_switches_turn(self):
    """各駒種は候補内の空マスへ移動し、成功後に手番を交代する。

    駒種から候補関数を選び忘れる誤りや、候補照合後に手番を交代しない誤りを検出する。
    """
    cases = [
        (PieceType.KING, Square(5, 4)), (PieceType.ROOK, Square(4, 5)),
        (PieceType.BISHOP, Square(4, 4)), (PieceType.GOLD, Square(5, 4)),
        (PieceType.SILVER, Square(5, 4)), (PieceType.KNIGHT, Square(4, 3)),
        (PieceType.LANCE, Square(5, 4)), (PieceType.PAWN, Square(5, 4)),
    ]
    for piece_type, destination in cases:
        board = Board()
        source = Square(5, 5)
        piece = Piece(piece_type, Side.SENTE)
        board.set_piece(source, piece)
        position = Position(board, Side.SENTE)
        with self.subTest(piece_type=piece_type):
            self.assertIsNone(self._apply_move(position, source, destination))
            self.assertIsNone(board.piece_at(source))
            self.assertEqual(board.piece_at(destination), piece)
            self.assertEqual(position.side_to_move, Side.GOTE)

def test_rejects_empty_destination_outside_piece_candidates_without_changing_position(self):
    """候補外の空マスを拒否し、盤面と手番を変更しない。

    空いているだけの任意のマスへ動かしてしまう誤りを、先後の歩の反対向きで検出する。
    """
    source = Square(5, 5)
    squares = [Square(file, rank) for file in range(1, 10) for rank in range(1, 10)]
    for side, destination in [(Side.SENTE, Square(5, 6)), (Side.GOTE, Square(5, 4))]:
        board = Board()
        board.set_piece(source, Piece(PieceType.PAWN, side))
        position = Position(board, side)
        before = [board.piece_at(square) for square in squares]
        with self.subTest(side=side):
            with self.assertRaises(ValueError):
                self._apply_move(position, source, destination)
            self.assertEqual([board.piece_at(square) for square in squares], before)
            self.assertEqual(position.side_to_move, side)
```

既存の `test_moves_piece_and_switches_turn_after_success` は後手の歩の到着先を、先手と同じ５四ではなく後手の前方である５六へ変更する。

```python
destination = Square(5, 4) if initial_turn == Side.SENTE else Square(5, 6)
```

- [x] **ステップ 2: 振る舞い上のRedを確認する**

実行: `python3 -m unittest discover -s tests -p 'test_movegen.py' -v`

期待値: `test_rejects_empty_destination_outside_piece_candidates_without_changing_position` が、候補外の空マスでも `ValueError` が送出されないため `AssertionError: ValueError not raised` で失敗する。これは読み込みエラーではなく、実際の `apply_move` が任意の空マスを受け入れる振る舞いによる失敗である。

### タスク2: 候補照合を最小実装する（完了）

**ファイル:**
- 変更: `kaname_shogi/movegen.py:15-80`
- テスト: `tests/test_movegen.py:96-172`

**インターフェース (Interfaces):**
- 消費 (Consumes): `Board`、`Square`、盤上の `Piece.piece_type`、および8種類の `*_move_candidates(board, source) -> list[Square]`。
- 生産 (Produces): `_move_candidates_for_piece(board: Board, source: Square) -> list[Square]` と、候補内の空マスだけを適用する既存シグネチャの `apply_move(position: Position, source: Square, destination: Square) -> None`。

- [x] **ステップ 1: 非公開ヘルパーを `apply_move` の直前に追加する**

盤上の駒がない場合は `ValueError` を送出し、駒種ごとに既存関数を選ぶ。

```python
def _move_candidates_for_piece(board: Board, source: Square) -> list[Square]:
    piece = board.piece_at(source)
    if piece is None:
        raise ValueError("出発マスに駒がありません")
    candidate_functions = {
        PieceType.KING: king_move_candidates, PieceType.ROOK: rook_move_candidates,
        PieceType.BISHOP: bishop_move_candidates, PieceType.GOLD: gold_move_candidates,
        PieceType.SILVER: silver_move_candidates, PieceType.KNIGHT: knight_move_candidates,
        PieceType.LANCE: lance_move_candidates, PieceType.PAWN: pawn_move_candidates,
    }
    return candidate_functions[piece.piece_type](board, source)
```

- [x] **ステップ 2: `apply_move` に候補照合を追加し、docstringを更新する**

所有者と手番の照合の後、駒が存在する場合だけ候補を求める。`destination` が候補外なら、`move_piece` の前に `ValueError` を送出する。候補内なら既存の盤面移動と手番交代をそのまま使う。

```python
piece = position.board.piece_at(source)
if piece is not None and piece.side != position.side_to_move:
    raise ValueError("手番と出発駒の所有者が一致しません")
if piece is not None and destination not in _move_candidates_for_piece(position.board, source):
    raise ValueError("到着マスは出発駒の移動先候補に含まれません")

move_piece(position.board, source, destination)
```

docstringには、候補内の空マスだけを対象にすること、候補に含まれる相手駒のマスは駒取り未実装のため `move_piece` が拒否すること、候補外・既存不正時に局面を変更しないことを記載する。

- [x] **ステップ 3: 対象テストのGreenを確認する**

実行: `python3 -m unittest discover -s tests -p 'test_movegen.py' -v`

期待値: `ApplyMoveTests` を含む `test_movegen.py` の全テストが成功する。候補外は `ValueError` となり、候補内の空マスだけが移動する。

- [x] **ステップ 4: 全テストとCLIを確認する**

実行: `python3 -m unittest discover -s tests -v`

実行: `python3 -m kaname_shogi`

実行: `git diff --check`

期待値: 全テスト、CLI、差分形式の検査が成功する。

- [x] **ステップ 5: Refactorの要否を確認する**

候補関数の選択は非公開ヘルパーにだけ置く。各候補生成関数の共通化、`move_piece` への候補照合の移動、駒取り実装は行わない。重複した駒種選択や読みにくい処理がないことを確認し、不要ならコードを変えずにその判断を学習記録へ残す。

### タスク3: 利用者向け記録を更新し、レビュー・コミットする（完了）

**ファイル:**
- 変更: `README.md`
- 変更: `docs/resume.md`
- 変更: `docs/next-topics.md`
- 変更: `docs/learning/24-candidate-only-empty-square-move.md`
- 変更: `docs/knowledge/17-candidate-only-empty-square-move.md`
- 作成: `docs/plans/2026-09-22-candidate-only-empty-square-move.md`
- テスト: `tests/test_movegen.py`

**インターフェース (Interfaces):**
- 消費 (Consumes): タスク2で確定した `apply_move` の契約と、実行済みの検証結果。
- 生産 (Produces): 現在の範囲、実施経過、未解決事項、次テーマを正確に示す学習・参照文書。

- [x] **ステップ 1: READMEと再開文書を実装結果に更新する**

READMEの `apply_move` の説明を、手番と所有者に加えて「既存候補に含まれる空マスだけ」を照合する契約に更新する。候補に含まれる相手駒のマスへの駒取りは対象外であることを明記する。`docs/resume.md` と `docs/next-topics.md` は任意の空マスへ動けるという古い到達点を削除し、候補外を拒否する現在地と、次候補の駒取り・持ち駒の前提を記録する。

- [x] **ステップ 2: 実際に行ったTDD・検証・レビューを学習記録へ追記する**

`docs/learning/24-candidate-only-empty-square-move.md` に、実際に観測したRedの失敗理由、Greenの最小実装、Refactorの判断、対象・全体テスト、CLI、差分検査、コードレビュー結果を事実として追記する。未実施の理解確認は記録しない。

- [x] **ステップ 3: 変更をセルフレビューする**

実行: `git diff --check`

確認内容: 設計書の範囲外である駒取り・持ち駒・成り・王手・CLI入力を追加していないこと、`move_piece` が候補照合と手番更新を知らないこと、失敗時の局面不変をテストしていること、公開docstringとREADMEが実装契約と一致すること。

- [x] **ステップ 4: 変更をコミットする**

実行: `git add README.md docs/resume.md docs/next-topics.md docs/learning/24-candidate-only-empty-square-move.md docs/knowledge/17-candidate-only-empty-square-move.md docs/design/12-candidate-only-empty-square-move.md docs/plans/2026-09-22-candidate-only-empty-square-move.md kaname_shogi/movegen.py tests/test_movegen.py`

実行: `git commit -m "feat: 移動先候補を局面移動へ適用"`

期待値: 第24回の設計、実装、テスト、記録が単一コミットに含まれる。

## 計画セルフレビュー

- [x] 仕様の候補照合、空マス限定、局面不変、既存責務の維持、対象外を各タスクに対応付けた。
- [x] 未確定事項を残すプレースホルダーを含めない。
- [x] `_move_candidates_for_piece`、`apply_move`、各既存候補関数の名前と型を整合させた。
- [x] テストとCLIのコマンドはリポジトリ直下で実行する既存コマンドを使う。
