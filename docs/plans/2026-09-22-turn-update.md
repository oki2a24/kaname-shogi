# 手番更新 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、`executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 空マスへの移動に成功したときだけ、可変の `Position` の手番を先手・後手で交代する `apply_move` を追加する。

**アーキテクチャ:** 盤面だけを変更する既存の `move_piece(board, source, destination)` は残す。新しい `apply_move(position, source, destination)` はまず `move_piece(position.board, ...)` を呼び、成功後にのみ `Position.side_to_move` を交代する。既存操作が `ValueError` を送出すれば、手番更新には進まない。

**技術スタック:** Python 3.9標準ライブラリ、`unittest`、既存の `Board`・`Position`・`Piece`・`Square`。

**仕様 (Spec):** `docs/plans/2026-09-22-turn-update-design.md`

**グローバル制約 (Global Constraints):**
- 指示・応答・学習記録・設計文書は日本語で記述する。
- 座標は将棋の筋・段を基本とし、数学のxyを公開インターフェースに導入しない。
- 公開インターフェースのdocstringに引数・戻り値・副作用・前提条件と設計理由を記録する。
- テストメソッド名は英語とし、日本語docstringで確認する振る舞いと背景を説明する。
- `Board` は盤面だけを保持し、`Position` は盤面と手番を保持する責務分離を維持する。
- `move_piece` は盤面だけを変更する既存の公開操作として残す。
- 手番と出発駒の所有者が一致するかは検証しない。
- 駒取り、持ち駒、成り・不成、移動方向、候補生成結果、王手、合法手判定、詰み、CLI入力、評価、探索、不変な局面への変更を実装しない。
- 実装はTDDのRed → Green → Refactorで進める。

---

### タスク1: `apply_move` の失敗するテストを追加する

**ファイル:**
- 変更: `tests/test_movegen.py`
- 参照: `kaname_shogi/model.py`、`kaname_shogi/movegen.py`

**インターフェース (Interfaces):**
- 消費: `Board.set_piece(square, piece)`、`Board.piece_at(square)`、`Position(board, side_to_move)`、`movegen` モジュール。
- 生産: `apply_move(position: Position, source: Square, destination: Square) -> None` の振る舞いを固定する `ApplyMoveTests`。

- [ ] **ステップ1: 未実装を振る舞いの失敗として扱う補助メソッドを追加する**

```python
class ApplyMoveTests(unittest.TestCase):
    def _apply_move(self, position, source, destination):
        """局面への移動適用関数を取得し、未実装をテスト失敗として扱う。"""
        self.assertTrue(hasattr(movegen, "apply_move"),
                        "apply_move がまだ実装されていません")
        return movegen.apply_move(position, source, destination)
```

- [ ] **ステップ2: 成功時の盤面更新と先後両方向の手番交代をテストする**

```python
for initial_turn, expected_turn in [(Side.SENTE, Side.GOTE),
                                    (Side.GOTE, Side.SENTE)]:
    board = Board()
    source, destination = Square(5, 5), Square(5, 4)
    piece = Piece(PieceType.PAWN, Side.SENTE)
    board.set_piece(source, piece)
    position = Position(board, initial_turn)
    self.assertIsNone(self._apply_move(position, source, destination))
    self.assertIsNone(position.board.piece_at(source))
    self.assertEqual(position.board.piece_at(destination), piece)
    self.assertEqual(position.side_to_move, expected_turn)
```

テストメソッド名は `test_moves_piece_and_switches_turn_after_success` とし、日本語docstringで盤面だけの更新や交代方向の誤りを検出する目的を記録する。

- [ ] **ステップ3: 三種類の失敗時に盤面81マスと手番が不変であることをテストする**

空の出発マス、占有された到着マス、同一マスを `subTest` で検査する。同一マスのケースでは、出発・到着の共通マスに駒を置いてから同じ `Square` を渡す。空の出発マスでは盤を空のままにし、占有された到着マスでは出発と到着へ別の駒を置く。各ケースで移動前後の81マスをリストとして比較し、`Position(board, Side.SENTE)` の `side_to_move` が `Side.SENTE` のままであることを確認する。テストメソッド名は `test_rejects_invalid_move_without_changing_board_or_turn` とする。

- [ ] **ステップ4: 所有者一致を検証しないことをテストする**

```python
board = Board()
source, destination = Square(5, 5), Square(5, 4)
piece = Piece(PieceType.PAWN, Side.GOTE)
board.set_piece(source, piece)
position = Position(board, Side.SENTE)

self._apply_move(position, source, destination)

self.assertEqual(position.board.piece_at(destination), piece)
self.assertEqual(position.side_to_move, Side.GOTE)
```

テストメソッド名は `test_does_not_require_moving_piece_to_match_turn` とし、日本語docstringで今回の範囲へ所有者検証を混ぜないことを説明する。

- [ ] **ステップ5: Redを確認する**

実行: `python3 -m unittest tests.test_movegen.ApplyMoveTests -v`

期待値: 追加したテストは `apply_move がまだ実装されていません` により失敗する。読み込みエラーではなく、未実装の振る舞いによる失敗であることを確認する。

### タスク2: `apply_move` を最小実装してGreenにする

**ファイル:**
- 変更: `kaname_shogi/movegen.py`
- 変更: `tests/test_movegen.py`（タスク1のテストに必要なimportだけ）

**インターフェース (Interfaces):**
- 消費: タスク1の `ApplyMoveTests`、`move_piece(board, source, destination)`、`Position`、`Side`。
- 生産: `apply_move(position: Position, source: Square, destination: Square) -> None`。

- [ ] **ステップ1: `Position` をimportし、`move_piece` の直後に最小実装を追加する**

```python
def apply_move(position: Position, source: Square, destination: Square) -> None:
    """空の到着マスへの移動と手番交代を、渡された局面へ適用する。

    引数:
        position: 変更対象の盤面と手番を持つ可変の局面。
        source: 移動元の筋・段を表すSquare。
        destination: 移動先の筋・段を表すSquare。

    戻り値:
        なし（None）。成功時だけposition.boardとposition.side_to_moveを変更する。

    例外:
        ValueError: move_pieceが拒否する空の出発マス、占有された到着マス、
            または同一マスの場合。失敗時は盤面と手番を変更しない。

    盤面移動はmove_pieceへ委譲し、成功後だけ手番を交代することで、
    Boardの配置責務とPositionの局面責務を分ける。今回は移動方向、
    出発駒の所有者と手番の一致、駒取り、成り、王手、合法手を検証しない。
    """
    move_piece(position.board, source, destination)
    if position.side_to_move == Side.SENTE:
        position.side_to_move = Side.GOTE
    else:
        position.side_to_move = Side.SENTE
```

- [ ] **ステップ2: 対象テストをGreenで確認する**

実行: `python3 -m unittest tests.test_movegen.ApplyMoveTests -v`

期待値: `ApplyMoveTests` の全テストが成功する。

- [ ] **ステップ3: 既存テストを含む全テストを実行する**

実行: `python3 -m unittest discover -s tests -v`

期待値: 既存の候補生成、初期配置、CLI、空マスへの移動適用と、新しい手番更新のテストがすべて成功する。

### タスク3: Refactorと文書を整合させる

**ファイル:**
- 変更: `kaname_shogi/movegen.py`
- 変更: `README.md`
- 変更: `docs/learning/22-turn-update.md`
- 変更: `docs/resume.md`
- 変更: `docs/plans/2026-09-22-turn-update.md`

**インターフェース (Interfaces):**
- 消費: タスク2の `apply_move(position, source, destination)` と成功・失敗時のテスト結果。
- 生産: 責務・対象外範囲・実装結果・再開位置を説明する更新済み文書。

- [ ] **ステップ1: Refactorの要否を判断する**

`apply_move` は `move_piece` に盤面移動を委譲し、手番交代だけを追加する。`Side` の2値は明示的な条件分岐で交代しているため、今回の範囲では共通化や抽象化を追加しない。変更不要なら、この判断を学習記録へ残す。

- [ ] **ステップ2: READMEへ使用例と対象外範囲を追加する**

```python
from kaname_shogi.model import Square, create_initial_position
from kaname_shogi.movegen import apply_move

position = create_initial_position()
apply_move(position, Square(7, 7), Square(7, 6))
# position.side_to_move は Side.GOTE
```

`move_piece` は盤面専用、`apply_move` は成功時だけ手番を交代すること、出発駒の所有者との一致を検証しないこと、今回扱わない規則を記録する。

- [ ] **ステップ3: 学習記録と再開案内を更新する**

第22回へ実装結果、Red→Green→Refactorの実測結果、検証、レビュー、将来の課題を追記する。`docs/resume.md` の到達点と次のテーマを更新し、理解確認が完了するまで駒取り・持ち駒・成りへ進まないことを記録する。

- [ ] **ステップ4: 文書とコードの整合性、最終検証、コミット準備を確認する**

実行: `rg -n "apply_move|move_piece|手番" README.md docs/resume.md docs/learning/22-turn-update.md kaname_shogi/movegen.py`

実行: `python3 -m unittest discover -s tests -v`

実行: `python3 -m kaname_shogi`

実行: `git diff --check`

実行: `git diff --stat`

期待値: 全テストとCLIが成功し、空白エラーがなく、説明が一貫する。

- [ ] **ステップ5: 検証・レビュー後に今回の変更をコミットする**

実行: `git add README.md docs/learning/22-turn-update.md docs/resume.md docs/plans/2026-09-22-turn-update.md kaname_shogi/movegen.py tests/test_movegen.py`

実行: `git commit -m "feat: 手番更新を追加"`

コミット前に、ステージ済み差分へ未承認・無関係なファイルを含めないことを確認する。
