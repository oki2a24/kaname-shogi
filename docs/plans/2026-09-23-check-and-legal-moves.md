# 王手と合法手判定 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 王手を検出し、盤上移動と駒打ちで自玉を相手の利きに残す手を拒否する。

**アーキテクチャ:** 可変の盤面・持ち駒・局面を独立に複製する。既存の候補生成を利用した `is_in_check` を追加し、公開の局面適用は複製局面への試し指しを通過した場合だけ本物へ反映する。実際の局面変更は非公開操作へ集め、試し指しの再帰を避ける。

**技術スタック:** Python 3.9+、標準ライブラリ `unittest`、Git。

**仕様 (Spec):** `docs/plans/2026-09-23-check-and-legal-moves-design.md`

**グローバル制約 (Global Constraints):**
- 説明・公開インターフェースのdocstring・学習記録・知識メモは日本語で書く。
- `Square` と `Piece` は変更不可の値であり、`Board`、`Hand`、`Position` は可変状態である。
- 試し指し用の複製と本物の局面で可変状態を共有しない。
- 成り、駒取り、二歩、行き所のない駒、手番交代、失敗時不変の既存契約を維持する。
- 打ち歩詰め、詰み・終局判定、合法手の全列挙、CLI入力、履歴、評価、探索は実装しない。
- テストメソッド名は英語、docstringは日本語とし、読み込みエラーではなく対象の振る舞いによりRedを確認する。
- コミットメッセージは日本語のConventional Commit形式にする。

---

## ファイル構成

- `kaname_shogi/model.py`: `Board.copy`、`Hand.copy`、`Position.copy` を提供する。
- `kaname_shogi/movegen.py`: `is_in_check` と試し指しによる合法性確認を提供する。
- `tests/test_model.py`: 複製と独立性を確認する。
- `tests/test_movegen.py`: 王手検出と移動・駒打ちの合法性を確認する。
- `README.md`、`docs/knowledge/24-check-and-legal-moves.md`、`docs/learning/31-check-and-legal-moves.md`、`docs/next-topics.md`: 到達点・規則・学習経緯を記録する。

### タスク1: 独立した局面複製

**ファイル:**
- 変更: `kaname_shogi/model.py: Hand、Board、Position`
- テスト: `tests/test_model.py`

**インターフェース (Interfaces):**
- 消費: `Board.piece_at(square) -> Optional[Piece]`、`Hand.count(piece_type) -> int`。
- 生産: `Hand.copy() -> Hand`、`Board.copy() -> Board`、`Position.copy() -> Position`。

- [x] **ステップ1: 失敗するテストを作成**

`Hand.copy`、`Board.copy`、`Position.copy` をそれぞれ直接確認するテストを `tests/test_model.py` に追加する。`Position.copy` の複製先では、盤上の先手歩、先手の持ち歩、後手の持ち角、手番を変更し、元の局面の全てが変わらないことを確認する。

```python
clone = position.copy()
clone.board.set_piece(Square(5, 5), None)
clone.sente_hand.remove(BasicPieceType.PAWN)
clone.gote_hand.remove(BasicPieceType.BISHOP)
clone.side_to_move = Side.GOTE
self.assertEqual(position.board.piece_at(Square(5, 5)), piece)
self.assertEqual(position.sente_hand.count(BasicPieceType.PAWN), 1)
self.assertEqual(position.gote_hand.count(BasicPieceType.BISHOP), 1)
self.assertEqual(position.side_to_move, Side.SENTE)
```

- [x] **ステップ2: Redを確認するために実行**

実行: `python3 -m unittest tests.test_model -v`

期待値: 新しいテストが `AttributeError: 'Position' object has no attribute 'copy'` により失敗する。テストモジュールの読み込みエラーではなく、未実装の振る舞いを確認する。

- [x] **ステップ3: 最小実装を追加**

`Hand.copy` は新しい内部枚数辞書、`Board.copy` は新しい81マスの内部リストを持つ複製を返す。`Position.copy` は両者を使い、同じ手番を持つ新しい局面を返す。

```python
def copy(self) -> "Position":
    return Position(self.board.copy(), self.side_to_move,
                    self.sente_hand.copy(), self.gote_hand.copy())
```

各docstringに、元を変更しないことと、可変状態を共有しない設計理由を記載する。

- [x] **ステップ4: Greenと回帰を確認するために実行**

実行: `python3 -m unittest tests.test_model -v`

期待値: 新しい複製テストを含むモデルテストが全件成功する。

- [x] **ステップ5: Refactor要否を確認する**

コピー処理が既存の状態カプセル化を保つことを確認する。内部状態を外部公開する変更はしない。

- [x] **ステップ6: コミット**

実行: `git add kaname_shogi/model.py tests/test_model.py && git commit -m "feat: 局面の独立複製を追加"`

### タスク2: 王手の読み取り

**ファイル:**
- 変更: `kaname_shogi/movegen.py: _move_candidates_for_piece の後`
- テスト: `tests/test_movegen.py`

**インターフェース (Interfaces):**
- 消費: `_move_candidates_for_piece(board, source) -> list[Square]`、`Board.piece_at(square) -> Optional[Piece]`、`Piece.side`。
- 生産: `is_in_check(board: Board, side: Side) -> bool`。

- [ ] **ステップ1: 失敗するテストを作成**

`PieceType` 全14種類と攻撃側の先後を表にし、指定側の玉を各駒種の移動候補へ置いたとき `True` となる表駆動テストを `tests/test_movegen.py` に追加する。表には玉、飛、角、金、銀、桂、香、歩、と金、成香、成桂、成銀、馬、竜を含める。各ケースでは両方の玉を盤上へ置き、攻撃対象ではない側を指定すると `False` であることも確認する。

飛・角・香・馬・竜は、攻撃駒と玉の間に攻撃側・防御側のいずれの駒があっても `False`、玉が最初に到達する相手駒なら `True` となる遮蔽表を追加する。桂馬は中間マスに駒を置いても `True` である表を追加する。隣接する両玉の相互の利き、玉のない部分局面での `False`、複数の攻撃駒がある局面と全攻撃線を遮った局面も確認する。

王手・非王手・玉なしの各例で、`is_in_check` 呼出し前後の全81マスを比較し、盤面を変更しないことを確認する。手番を持たない操作であることを示すため、`Position` を用いる例では `side_to_move` も変わらないことを確認する。

```python
for piece_type, attacker, king_square in cases:
    board = Board()
    board.set_piece(king_square, Piece(PieceType.KING, defender))
    board.set_piece(Square(5, 5), Piece(piece_type, attacker))
    with self.subTest(piece_type=piece_type, attacker=attacker):
        self.assertTrue(movegen.is_in_check(board, defender))
```

- [ ] **ステップ2: Redを確認するために実行**

実行: `python3 -m unittest tests.test_movegen -v`

期待値: 新しいテストが `AttributeError: module 'kaname_shogi.movegen' has no attribute 'is_in_check'` により失敗する。

- [ ] **ステップ3: 最小実装を追加**

盤の全81マスから指定側の玉を探す。玉がなければ `False` を返す。玉があれば相手側の各駒の既存候補に玉マスが含まれるときだけ `True` を返す。補助操作は非公開で盤面を変更しない。公開関数のdocstringに、部分局面での扱いと既存候補を利用する理由を記載する。

```python
def is_in_check(board: Board, side: Side) -> bool:
    king_square = _find_king_square(board, side)
    if king_square is None:
        return False
    return any(king_square in _move_candidates_for_piece(board, source)
               for source in _squares_with_side(board, _opposite_side(side)))
```

- [ ] **ステップ4: Greenと回帰を確認するために実行**

実行: `python3 -m unittest tests.test_movegen -v`

期待値: 新しい王手検出テストと既存テストが全件成功する。

- [ ] **ステップ5: Refactor要否を確認する**

複数駒で同じ玉を攻撃する局面と、複数の攻撃線をすべて遮った局面の決定的テストで、盤の走査順・候補順が真偽に影響しないことを確認する。全駒候補生成の再構成はしない。

- [ ] **ステップ6: コミット**

実行: `git add kaname_shogi/movegen.py tests/test_movegen.py && git commit -m "feat: 王手判定を追加"`

### タスク3: 盤上移動と駒打ちの合法性

**ファイル:**
- 変更: `kaname_shogi/movegen.py: apply_move、apply_drop`
- テスト: `tests/test_movegen.py`

**インターフェース (Interfaces):**
- 消費: `Position.copy() -> Position`、`is_in_check(board, side) -> bool`、既存の移動・駒打ち規則。
- 生産: 自玉が王手となる指し手を `ValueError` で拒否する `apply_move(position, source, destination, *, promote=False) -> None` と `apply_drop(position, piece_type, destination) -> None`。

- [ ] **ステップ1: 失敗するテストを作成**

王手放置、相手の利きへの玉移動、遮蔽を外す移動を拒否し、各拒否で盤面81マス・先後双方の持ち駒・手番が不変であるテストを追加する。玉の退避、王手駒の取得、飛車・角・香への合い駒、駒打ちでの合い駒を許可するテストも追加する。桂馬への合い駒と、王手放置の駒打ちは拒否する。

```python
with self.assertRaisesRegex(ValueError, "王手"):
    movegen.apply_move(position, Square(4, 7), Square(4, 6))
with self.assertRaisesRegex(ValueError, "王手"):
    movegen.apply_move(position, Square(5, 9), Square(5, 8))
with self.assertRaisesRegex(ValueError, "王手"):
    movegen.apply_move(position, Square(5, 7), Square(4, 6))
```

- [ ] **ステップ2: Redを確認するために実行**

実行: `python3 -m unittest tests.test_movegen -v`

期待値: 新しい拒否テストが `ValueError not raised` で失敗する。既存テストの読み込みエラーではなく、未実装の合法性判定を確認する。

- [ ] **ステップ3: 最小実装を追加**

既存の局面変更本体を `_apply_move_unchecked` と `_apply_drop_unchecked` へ移す。公開操作は複製局面へ非公開操作を適用し、指す前の手番側の玉を `is_in_check` で調べ、安全なら本物にも同じ非公開操作を一度だけ適用する。

```python
def _apply_if_king_safe(position: Position, apply_unchecked) -> None:
    side = position.side_to_move
    trial = position.copy()
    apply_unchecked(trial)
    if is_in_check(trial.board, side):
        raise ValueError("自玉が王手になる手は指せません")
    apply_unchecked(position)
```

公開操作のdocstringを、試し指し、拒否条件、副作用に合わせて更新する。既存の `ValueError` 条件と順序を保つ。

- [ ] **ステップ4: Greenと回帰を確認するために実行**

実行: `python3 -m unittest tests.test_movegen -v && python3 -m unittest discover -s tests -v`

期待値: 新しい合法手テストと既存の全テストが成功する。

- [ ] **ステップ5: Refactor要否を確認する**

移動と駒打ちの共通する試し指しだけを小さな非公開操作へまとめ、成り・駒取り・二歩の個別規則を過度に共通化しない。各失敗経路で本物の局面を変更しないことを確認する。

- [ ] **ステップ6: コミット**

実行: `git add kaname_shogi/movegen.py tests/test_movegen.py && git commit -m "feat: 自玉を守る合法手判定を追加"`

### タスク4: 文書化、統合検証、独立レビュー

**ファイル:**
- 変更: `README.md`、`docs/knowledge/24-check-and-legal-moves.md`、`docs/learning/31-check-and-legal-moves.md`、`docs/next-topics.md`
- 確認: `kaname_shogi/model.py`、`kaname_shogi/movegen.py`、`tests/test_model.py`、`tests/test_movegen.py`

**インターフェース (Interfaces):**
- 消費: 実装済みの複製・王手判定・合法手判定、テスト実行結果、コードレビュー結果。
- 生産: 到達点、規則根拠、設計判断、検証・レビュー結果、最後の理解確認を区別して残す日本語文書。

- [ ] **ステップ1: 確定知識と学習記録を作成**

一次資料リンクを添え、王手、王手放置、相手の利きへの玉移動、合い駒、独立複製の理由を知識メモへ記録する。第1〜第4問の本人の回答と補足、設計合意、Red・Green・Refactor、検証、レビューを学習記録へ区別して記録する。最後の理解確認はmain取り込み後に一問だけ出し、回答前に正解として記録しない。

- [ ] **ステップ2: READMEと次テーマ候補を更新**

READMEの現在の状態と公開操作説明を更新する。最後の理解確認の回答と補足を記録した後にだけ次テーマ候補を見直し、打ち歩詰めを小さい順の候補として示す。

- [ ] **ステップ3: 統合検証を実行**

実行: `python3 -m unittest discover -s tests -v`

実行: `python3 -m kaname_shogi`

実行: `git diff --check`

実行: `git status --short --branch`

期待値: 全テスト成功、CLIが初期配置と手番を表示して終了、`git diff --check` は出力なし。結果を学習記録へ記載する。

- [ ] **ステップ4: 独立コードレビューを実行して記録する**

変更済みの実装とテストを独立に確認し、Critical・Important・Minorの結論と対応を学習記録へ残す。CriticalまたはImportantがあれば修正し、タスク3の検証と再レビューを行う。レビュー後の結論がマージ可能であることを確認する。

- [ ] **ステップ5: 文書と検証記録をコミット**

実行: `git add README.md docs/knowledge/24-check-and-legal-moves.md docs/learning/31-check-and-legal-moves.md docs/next-topics.md && git commit -m "docs: 王手と合法手判定の学習記録を追加"`

## 計画の自己レビュー

- 仕様の複製、王手検出、盤上移動・駒打ちの合法性、失敗時不変、対象外をタスク1〜3に対応付けた。
- 各タスクに具体的なファイル、インターフェース、Red、Green、検証、Refactor、コミットを示した。
- Python標準ライブラリの `unittest` 実行コマンドを使用し、存在しない `pytest` を前提にしていない。
- 「TBD」「TODO」「詳細を記入」などの未確定な指示を含めない。
