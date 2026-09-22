# 持ち駒を打つ基本操作 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 手番側の持ち駒を空マスへ打ち、成功時に持ち駒と盤面と手番を一貫して更新する。

**アーキテクチャ:** `Hand` は持ち駒の枚数だけを変更する `remove` を提供する。局面を変更する `apply_drop` は、検証をすべて終えてから、手番側の `Hand`、`Board`、手番を順に更新する。盤上移動の `apply_move` は変更せず、出発マスのない駒打ちを別操作として保つ。

**技術スタック:** Python 3.9、標準ライブラリ `dataclasses`・`unittest`、外部依存なし。

**仕様 (Spec):** [持ち駒を打つ基本操作：仕様](2026-09-22-hand-drops-design.md)、[持ち駒を打つ操作の設計](../design/14-hand-drops.md)

**グローバル制約 (Global Constraints):**
- 二歩、行き所のない歩・香・桂、打ち歩詰め、成り、王手・合法手、CLI入力は扱わない。
- 持ち駒不足、占有マス、玉の指定は `ValueError` とし、盤面・先後双方の持ち駒・手番を変更しない。
- 公開インターフェースのdocstringには、引数・戻り値・副作用・前提条件と設計理由を日本語で記録する。
- テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞いを記す。

---

## ファイル構成

- `kaname_shogi/model.py`：持ち駒のデータ操作 `Hand.remove`。
- `tests/test_model.py`：`Hand.remove` の成功・拒否・不変性。
- `kaname_shogi/movegen.py`：局面操作 `apply_drop`。
- `tests/test_movegen.py`：先後双方の駒打ちと失敗時の局面不変性。
- `README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/learning/26-hand-drops.md`、`docs/knowledge/19-hand-drops.md`：実装・検証後の状態。

### タスク1：`Hand.remove` をTDDで追加する

**ファイル:**
- 変更: `tests/test_model.py:117-152`
- 変更: `kaname_shogi/model.py:107-146`

**インターフェース (Interfaces):**
- 消費 (Consumes): `Hand.add(piece_type: PieceType) -> None`、`Hand.count(piece_type: PieceType) -> int`。
- 生産 (Produces): `Hand.remove(piece_type: PieceType) -> None`。玉または0枚を `ValueError` で拒否し、失敗時は枚数を変えない。

- [ ] **ステップ1: 失敗するテストを作成**

`HandTests` に、歩を2枚加えて1枚取り除く成功、0枚の飛車の拒否、玉の拒否を追加する。各失敗後に歩・飛車の枚数が変わらないことも確認する。

```python
def test_remove_decreases_only_one_owned_piece_type(self):
    """持ち駒を1枚減らし、他の駒種の枚数を変えない。"""
    hand = model.Hand()
    hand.add(PieceType.PAWN)
    hand.add(PieceType.PAWN)
    hand.remove(PieceType.PAWN)
    self.assertEqual(hand.count(PieceType.PAWN), 1)
    self.assertEqual(hand.count(PieceType.ROOK), 0)

def test_remove_rejects_unowned_piece_and_king_without_changing_hand(self):
    """0枚の駒と玉を拒否し、持ち駒を変更しない。"""
    hand = model.Hand()
    hand.add(PieceType.PAWN)
    with self.assertRaises(ValueError):
        hand.remove(PieceType.ROOK)
    with self.assertRaises(ValueError):
        hand.remove(PieceType.KING)
    self.assertEqual(hand.count(PieceType.PAWN), 1)
    self.assertEqual(hand.count(PieceType.ROOK), 0)
```

- [ ] **ステップ2: テストが失敗することを確認するために実行**

実行: `python3 -m unittest discover -s tests -p 'test_model.py' -v`

期待値: `AttributeError: 'Hand' object has no attribute 'remove'` によるFAIL。テストモジュールの読み込みエラーではなく、未実装の振る舞いで失敗することを確認する。

- [ ] **ステップ3: 最小限の実装を作成**

`Hand.add` の直後に、既存の `_validate_piece_type` と `count` を利用する `remove` を追加する。枚数の確認を変更前に行う。

```python
def remove(self, piece_type: PieceType) -> None:
    self._validate_piece_type(piece_type)
    if self.count(piece_type) == 0:
        raise ValueError("指定した駒は持ち駒にありません")
    self._counts[piece_type] = self.count(piece_type) - 1
```

docstringには、引数、`None` の戻り値、0枚・玉の例外、成功時と失敗時の副作用、盤面・先後を扱わない理由を記す。

- [ ] **ステップ4: テストがパスすることを確認するために実行**

実行: `python3 -m unittest discover -s tests -p 'test_model.py' -v`

期待値: `HandTests` の全テストがPASS。

- [ ] **ステップ5: リファクタ要否を確認してコミット**

`add` と `remove` に必要な範囲を超える共通化がないか確認する。重複を減らすための補助関数が、枚数操作の理解をかえって難しくするなら追加しない。

```bash
git add kaname_shogi/model.py tests/test_model.py
git commit -m "feat: 持ち駒を減らす操作を追加"
```

### タスク2：`apply_drop` をTDDで追加する

**ファイル:**
- 変更: `tests/test_movegen.py:96-289`（`ApplyMoveTests` の後に `ApplyDropTests` を追加）
- 変更: `kaname_shogi/movegen.py:16-119`

**インターフェース (Interfaces):**
- 消費 (Consumes): `Hand.remove(piece_type: PieceType) -> None`、`Position.board`、`Position.sente_hand`、`Position.gote_hand`、`Position.side_to_move`。
- 生産 (Produces): `apply_drop(position: Position, piece_type: PieceType, destination: Square) -> None`。成功時は手番側の持ち駒を1枚減らし、空マスにその側の駒を置き、手番を交代する。

- [ ] **ステップ1: 失敗するテストを作成**

`ApplyDropTests` を追加する。先手・後手の両方が持ち歩を空の５五へ打つ成功と、持ち駒不足、先手駒の占有、後手駒の占有、玉の指定を検証する。失敗ケースは盤面81マス、手番、双方の全持ち駒枚数の事前値と事後値を比較する。

```python
def test_drops_hand_piece_to_empty_square_and_switches_turn(self):
    """手番側の持ち駒を空マスへ打ち、手番を交代する。"""
    for side, expected_turn in [(Side.SENTE, Side.GOTE),
                                (Side.GOTE, Side.SENTE)]:
        position = Position(Board(), side)
        hand = position.sente_hand if side == Side.SENTE else position.gote_hand
        hand.add(PieceType.PAWN)
        self._apply_drop(position, PieceType.PAWN, Square(5, 5))
        self.assertEqual(position.board.piece_at(Square(5, 5)),
                         Piece(PieceType.PAWN, side))
        self.assertEqual(hand.count(PieceType.PAWN), 0)
        self.assertEqual(position.side_to_move, expected_turn)
```

`_apply_drop` は `movegen.apply_drop` の存在を先にアサートして呼ぶ補助操作とする。拒否テストでは各ケースに `with self.assertRaises(ValueError):` を置く。

- [ ] **ステップ2: テストが失敗することを確認するために実行**

実行: `python3 -m unittest discover -s tests -p 'test_movegen.py' -v`

期待値: `apply_drop がまだ実装されていません` というアサーションによるFAIL。インポート時のエラーではなく、新しい局面操作がないことを示す失敗であることを確認する。

- [ ] **ステップ3: 最小限の実装を作成**

`movegen.py` の `apply_move` の後に `apply_drop` を追加し、`Piece` を import する。盤面・持ち駒・手番を変える前に、玉、到着先の占有、手番側の持ち駒を検証する。

```python
def apply_drop(position: Position, piece_type: PieceType,
               destination: Square) -> None:
    if piece_type == PieceType.KING:
        raise ValueError("玉は打てません")
    if position.board.piece_at(destination) is not None:
        raise ValueError("到着マスは空にしてください")
    hand = (position.sente_hand if position.side_to_move == Side.SENTE
            else position.gote_hand)
    hand.remove(piece_type)
    position.board.set_piece(destination,
                             Piece(piece_type, position.side_to_move))
    position.side_to_move = (Side.GOTE if position.side_to_move == Side.SENTE
                             else Side.SENTE)
```

docstringには、引数、`None` の戻り値、成功時に変更する局面状態、`ValueError` の条件と不変性、`apply_move` と分ける理由、今回扱わない規則を記す。

- [ ] **ステップ4: テストがパスすることを確認するために実行**

実行: `python3 -m unittest discover -s tests -p 'test_movegen.py' -v`

期待値: `ApplyDropTests` の全テストがPASS。

- [ ] **ステップ5: リファクタ要否を確認してコミット**

手番側の `Hand` を選ぶ処理を `apply_move` と共有するか検討する。短い条件式を別の非公開関数へ切り出すことで責務や学習上の理解が改善しなければ、共有化しない。

```bash
git add kaname_shogi/movegen.py tests/test_movegen.py
git commit -m "feat: 持ち駒を打つ操作を追加"
```

### タスク3：利用者向け文書を現在地へ更新し、全体を検証する

**ファイル:**
- 変更: `README.md`
- 変更: `docs/resume.md`
- 変更: `docs/next-topics.md`
- 変更: `docs/learning/26-hand-drops.md`
- 変更: `docs/knowledge/19-hand-drops.md`

**インターフェース (Interfaces):**
- 消費 (Consumes): `Hand.remove(piece_type: PieceType) -> None`、`apply_drop(position: Position, piece_type: PieceType, destination: Square) -> None`。
- 生産 (Produces): 実装済み範囲、実行方法、次テーマ、実測検証結果を正しく参照できる文書。

- [ ] **ステップ1: READMEを更新する**

現在の状態、テスト対象、コード例、文書リンクへ `apply_drop` を反映する。成功時の持ち駒減少・配置・手番交代と、持ち駒不足・占有マス・玉指定の不変な拒否を明記する。非対象の規則も明記する。

```python
position.sente_hand.add(PieceType.PAWN)
apply_drop(position, PieceType.PAWN, Square(5, 5))
# ５五は先手の歩、先手の持ち駒の歩は0枚、手番は後手
```

- [ ] **ステップ2: 再開・次テーマ・学習記録・知識メモを更新する**

`docs/resume.md` に今回の実装・実測結果・次の学習再開地点を追加する。`docs/next-topics.md` では今回の候補を完了状態にし、未実装の二歩・行き所のない駒などを次候補として残す。学習記録にはRed、Green、Refactor、レビュー、検証、実装後の理解確認を、実施済みの事実だけ記録する。知識メモは「実装予定」を実装済みの契約へ更新する。

- [ ] **ステップ3: 対象テスト、全テスト、CLI、差分を確認する**

実行:

```bash
python3 -m unittest discover -s tests -p 'test_model.py' -v
python3 -m unittest discover -s tests -p 'test_movegen.py' -v
python3 -m unittest discover -s tests -v
python3 -m kaname_shogi
git diff --check
```

期待値: 全コマンドが成功し、`git diff --check` は出力なし。CLIは既存どおり初期配置と先手の手番を表示して終了する。

- [ ] **ステップ4: 文書と最終検証結果をコミットする**

```bash
git add README.md docs/resume.md docs/next-topics.md \
  docs/learning/26-hand-drops.md docs/knowledge/19-hand-drops.md
git commit -m "docs: 記録 持ち駒を打つ実装"
```

- [ ] **ステップ5: 実装後の理解確認を一問だけ行う**

実装・検証・レビュー後、先手または後手の持ち駒と空マスへの打ちを問う確認問題を一問だけ出す。回答と補足を `docs/learning/26-hand-drops.md` に記録し、次テーマへ進む前に振り返りを確認する。
