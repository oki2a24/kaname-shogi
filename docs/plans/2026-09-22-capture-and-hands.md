# 駒取りと持ち駒の基礎 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、`subagent-driven-development` または `executing-plans` スキルを使用し、チェックボックスを更新する。

**目標:** 候補に含まれる相手駒を取ると、指した側の持ち駒へその基本駒種を1枚加え、成功時だけ手番を交代する。

**アーキテクチャ:** `model.py` に持ち駒枚数を扱う可変 `Hand` を追加し、`Position` が先手・後手それぞれの `Hand` を保持する。`apply_move` は空到着では既存 `move_piece` へ委譲し、相手駒の到着では盤面更新と持ち駒加算を行う。

**技術スタック:** Python 3.9+、標準ライブラリ `dataclasses`・`unittest`、外部依存なし。

**仕様 (Spec):** [第13回実装の設計：駒取りと持ち駒の基礎](../design/13-capture-and-hands.md)

**グローバル制約 (Global Constraints):**
- 日本語のdocstringに引数・戻り値・副作用・前提条件・設計理由を記す。座標は `Square(file, rank)` の筋・段で扱う。
- 振る舞いごとにRedの失敗理由を確認してから最小実装、Green、Refactor要否確認を行う。読み込みエラーをRedと扱わない。
- `apply_move` の失敗時は盤面・手番・双方の持ち駒を変更しない。
- 持ち駒を打つ、成り・不成、成駒を取ったときの復元、王手・詰み・合法手、履歴、CLI入力、評価、探索は実装しない。
- 玉取りは `ValueError` で拒否し、玉を持ち駒へ加えない。
- 実装後は対象テスト、全テスト、CLI、`git diff --check` を実行・確認してからコミットする。

---

## ファイル構成

| ファイル | 役割 |
| --- | --- |
| `kaname_shogi/model.py` | `Hand` と、先後の持ち駒を持つ `Position`。 |
| `kaname_shogi/movegen.py` | 駒取りを含む `apply_move`。 |
| `tests/test_model.py` | `Hand` の枚数・玉拒否・局面間の独立性。 |
| `tests/test_movegen.py` | 先後の駒取り成功と失敗時の局面不変。 |
| `docs/knowledge/18-capture-and-hands.md` | 確定知識。 |
| `docs/learning/25-capture-and-hands.md` | 学習・実装・検証記録。 |
| `README.md`、`docs/resume.md`、`docs/next-topics.md` | 現在地と次テーマ。 |

### タスク1: 持ち駒データと局面の保持

**状態:** 完了

**ファイル:**
- 変更: `kaname_shogi/model.py:1-170`
- 変更: `tests/test_model.py:1-180`

**インターフェース:**
- 生産: `Hand()`、`Hand.count(piece_type: PieceType) -> int`、`Hand.add(piece_type: PieceType) -> None`、`Position.sente_hand: Hand`、`Position.gote_hand: Hand`。

- [x] **ステップ 1: 失敗するモデルテストを作成**

`tests/test_model.py` のimportへ `Hand` と `Position` を追加し、次を加える。各docstringには検出したい共有・玉取りの誤りを日本語で説明する。

```python
class HandTests(unittest.TestCase):
    def test_counts_start_at_zero_and_add_changes_only_one_piece_type(self):
        """新しい持ち駒は0枚で、追加した駒種だけを1枚増やす。"""
        hand = Hand()
        self.assertEqual(hand.count(PieceType.PAWN), 0)
        self.assertEqual(hand.count(PieceType.ROOK), 0)
        hand.add(PieceType.PAWN)
        self.assertEqual(hand.count(PieceType.PAWN), 1)
        self.assertEqual(hand.count(PieceType.ROOK), 0)

    def test_king_is_rejected_without_changing_hand(self):
        """玉は持ち駒に加えられず、失敗後も枚数を変えない。"""
        hand = Hand()
        with self.assertRaises(ValueError):
            hand.add(PieceType.KING)
        self.assertEqual(hand.count(PieceType.PAWN), 0)


class PositionHandTests(unittest.TestCase):
    def test_positions_and_sides_have_independent_hands(self):
        """先後と別局面の持ち駒は互いに独立している。"""
        first, second = Position(Board(), Side.SENTE), Position(Board(), Side.SENTE)
        first.sente_hand.add(PieceType.PAWN)
        first.gote_hand.add(PieceType.ROOK)
        self.assertEqual(first.gote_hand.count(PieceType.PAWN), 0)
        self.assertEqual(second.sente_hand.count(PieceType.PAWN), 0)
        self.assertEqual(second.gote_hand.count(PieceType.ROOK), 0)
```

- [x] **ステップ 2: Redを確認**

実行: `python3 -m unittest discover -s tests -p 'test_model.py' -v`

期待値: `Hand` または `Position.sente_hand` が未実装で失敗する。テストの構文・読み込みではなく、未実装の公開APIが理由であることを確認する。

- [x] **ステップ 3: 最小実装を追加**

`dataclasses` のimportに `field` を加え、`Piece` の後ろに次の `Hand` を追加する。公開要素のdocstringには、`Hand` は一方の持ち駒データ、`count` は読取操作、`add` は加算操作、先後は持たないことを記す。

```python
@dataclass
class Hand:
    _counts: dict[PieceType, int] = field(default_factory=dict, init=False, repr=False)

    def _validate_piece_type(self, piece_type: PieceType) -> None:
        if piece_type == PieceType.KING:
            raise ValueError("玉は持ち駒にできません")

    def count(self, piece_type: PieceType) -> int:
        self._validate_piece_type(piece_type)
        return self._counts.get(piece_type, 0)

    def add(self, piece_type: PieceType) -> None:
        self._validate_piece_type(piece_type)
        self._counts[piece_type] = self.count(piece_type) + 1
```

`Position` を `board`、`side_to_move`、`sente_hand: Hand = field(default_factory=Hand)`、`gote_hand: Hand = field(default_factory=Hand)` の4フィールドにする。`create_initial_position()` は `Position(board, Side.SENTE)` のままとし、既定値で空の持ち駒を得る。

- [x] **ステップ 4: Greenを確認**

実行: `python3 -m unittest discover -s tests -p 'test_model.py' -v`

期待値: 新しい `HandTests` と `PositionHandTests` を含む全テストが成功する。

- [x] **ステップ 5: Refactor要否を確認してコミット**

持ち駒を打つ削除操作や不変化を先取りせず、`Hand` が枚数の読取・加算だけを持つことを確認する。

実行: `git add kaname_shogi/model.py tests/test_model.py && git commit -m "feat: 持ち駒を局面に保持"`

### タスク2: 駒取りを含む局面移動

**状態:** 完了

**ファイル:**
- 変更: `kaname_shogi/movegen.py:1-115`
- 変更: `tests/test_movegen.py:96-225`

**インターフェース:**
- 消費: `Position.sente_hand`、`Position.gote_hand`、`Hand.add(piece_type: PieceType) -> None`。
- 生産: `apply_move(position: Position, source: Square, destination: Square) -> None`。空マス移動と相手駒の駒取りを成功時に適用し、失敗時は局面を変更しない。

- [x] **ステップ 1: 駒取りの失敗テストを作成**

`ApplyMoveTests` に次を追加する。既存の候補外・所有者不一致・空出発・同一マスの失敗テストへも、先後双方の持ち駒が0枚のままという検証を加える。

```python
def test_captures_opponent_pawn_adds_hand_and_switches_turn(self):
    """候補内の相手歩を取り、指した側の持ち駒へ歩を1枚加える。"""
    cases = [(Side.SENTE, Square(5, 5), Square(5, 4), Side.GOTE),
             (Side.GOTE, Square(5, 5), Square(5, 6), Side.SENTE)]
    for side, source, destination, expected_turn in cases:
        board = Board()
        board.set_piece(source, Piece(PieceType.PAWN, side))
        board.set_piece(destination, Piece(PieceType.PAWN, expected_turn))
        position = Position(board, side)
        self._apply_move(position, source, destination)
        hand = position.sente_hand if side == Side.SENTE else position.gote_hand
        self.assertIsNone(board.piece_at(source))
        self.assertEqual(board.piece_at(destination), Piece(PieceType.PAWN, side))
        self.assertEqual(hand.count(PieceType.PAWN), 1)
        self.assertEqual(position.side_to_move, expected_turn)

def test_rejects_capture_of_king_without_changing_position(self):
    """相手玉を取る移動を拒否し、局面のどの状態も変更しない。"""
    board = Board()
    source, destination = Square(5, 5), Square(5, 4)
    board.set_piece(source, Piece(PieceType.PAWN, Side.SENTE))
    board.set_piece(destination, Piece(PieceType.KING, Side.GOTE))
    position = Position(board, Side.SENTE)
    before = [board.piece_at(Square(file, rank)) for file in range(1, 10) for rank in range(1, 10)]
    with self.assertRaises(ValueError):
        self._apply_move(position, source, destination)
    self.assertEqual([board.piece_at(Square(file, rank)) for file in range(1, 10) for rank in range(1, 10)], before)
    self.assertEqual(position.side_to_move, Side.SENTE)
    self.assertEqual(position.sente_hand.count(PieceType.PAWN), 0)
```

- [x] **ステップ 2: 振る舞い上のRedを確認**

実行: `python3 -m unittest discover -s tests -p 'test_movegen.py' -v`

期待値: 駒取り成功は既存の `move_piece` が占有到着を拒否するため `ValueError` で失敗し、玉取り拒否は未実装のため失敗する。読み込みエラーではないことを確認する。

- [x] **ステップ 3: `apply_move` の最小分岐を実装**

既存の手番・候補照合の後に到着駒を読む。空なら既存 `move_piece` を呼ぶ。相手駒なら玉を拒否し、手番側の `Hand` を選んで盤面更新と持ち駒加算を行う。`move_piece` は変更しない。

```python
target_piece = position.board.piece_at(destination)
if target_piece is None:
    move_piece(position.board, source, destination)
else:
    if target_piece.piece_type == PieceType.KING:
        raise ValueError("玉は取れません")
    hand = position.sente_hand if position.side_to_move == Side.SENTE else position.gote_hand
    position.board.set_piece(source, None)
    position.board.set_piece(destination, piece)
    hand.add(target_piece.piece_type)
```

`apply_move` のdocstringを、相手駒を取る成功条件、玉取り拒否、失敗時に持ち駒も不変である契約へ更新する。

- [x] **ステップ 4: Greenを確認**

実行: `python3 -m unittest discover -s tests -p 'test_movegen.py' -v`

期待値: 新しい先後の駒取り、玉取り拒否、既存の空マス移動・候補外拒否・手番照合を含む全テストが成功する。

- [x] **ステップ 5: Refactor要否を確認してコミット**

`apply_move` が局面規則、`move_piece` が空マスへの盤面操作という責務分離を保つことを確認する。駒打ち・成り・王手判定を加えない。

実行: `git add kaname_shogi/movegen.py tests/test_movegen.py && git commit -m "feat: 駒取りで持ち駒を加える"`

### タスク3: 記録と全体検証

**ファイル:**
- 作成: `docs/knowledge/18-capture-and-hands.md`、`docs/learning/25-capture-and-hands.md`
- 変更: `README.md`、`docs/resume.md`、`docs/next-topics.md`

**インターフェース:**
- 消費: 実測したRed・Green・Refactor・検証結果。
- 生産: 確定知識、学習記録、次回の開始点。

- [x] **ステップ 1: 全体検証を実行して事実を収集**

実行: `python3 -m unittest discover -s tests -v && python3 -m kaname_shogi && git diff --check`

期待値: 全テスト成功、CLIが初期配置を表示して終了、`git diff --check` は出力なし。失敗時は記録・コミットの前に対象範囲内で修正する。

- [x] **ステップ 2: 文書を更新**

`docs/knowledge/18-capture-and-hands.md` に、駒取り・持ち駒・盤上にないこと・玉を持ち駒にしないこと・対象外と、日本将棋連盟「駒の動かし方」へのリンクを記す。`docs/learning/25-capture-and-hands.md` に今回の質問と回答、設計合意、Red・Green・Refactor・検証・レビューの実測結果を書く。`README.md`、`docs/resume.md`、`docs/next-topics.md` を実装済み範囲と「持ち駒を打つ操作と打ち場所の制限」が次候補である現在地へ更新する。未実施のレビュー・回答・検証を完了として記録しない。

- [x] **ステップ 3: 文書を含めて再検証し、コミット**

実行: `python3 -m unittest discover -s tests -v && python3 -m kaname_shogi && git diff --check && git status --short`

期待値: 全テストとCLIが成功し、`git diff --check` は出力なし。既存の未追跡 `.antigravity/` は変更・追加・コミットしない。

実行: `git add README.md docs/knowledge/18-capture-and-hands.md docs/learning/25-capture-and-hands.md docs/resume.md docs/next-topics.md && git commit -m "docs: 駒取りと持ち駒の実装を記録"`

## 完了条件

- `Hand` は玉以外の駒種の枚数だけを扱い、先後を記憶しない。
- `Position` は独立した `sente_hand` と `gote_hand` を持ち、既存の2引数コンストラクタを維持する。
- `apply_move` は候補内の相手駒を取り、手番側の持ち駒を1枚増やし、成功後だけ手番を交代する。
- 玉取りを含む失敗経路で、盤面・手番・双方の持ち駒が不変である。
- 持ち駒を打つ、成り、王手・合法手判定を実装していない。
