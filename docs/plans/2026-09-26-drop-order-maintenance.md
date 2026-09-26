# 第40回 駒打ち順の保守改善 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** `legal_moves` の駒打ち順を `BasicPieceType` の反復順から切り離し、飛・角・金・銀・桂・香・歩の公開順を全駒種・全打ち先で検証する。

**アーキテクチャ:** `movegen.py` にモジュール非公開の順序定数を追加し、非公開の合法手列挙器がその定数だけを反復する。全種類の持ち駒を持つ空盤面で一覧全体と局面不変性を確認し、`movegen` 内の `BasicPieceType` の反復順をテスト中だけ入れ替えても公開順が変わらないことを確認する。

**技術スタック:** Python 3.9標準ライブラリ、`unittest`、`unittest.mock`

**仕様 (Spec):** `docs/plans/2026-09-26-drop-order-maintenance-design.md`

**グローバル制約 (Global Constraints):**
- `BasicPieceType` の定義、宣言順、列挙値、持ち駒・成駒復元での役割は変更しない。
- 盤上移動の順、成り・不成の順、駒打ち先の走査順、合法性の判定、CLIの動作、乱数選択器のインターフェースは変更しない。
- 駒打ち順は将棋規則ではなく、`legal_moves` の再現可能な公開API契約として保つ。
- 新規・変更テストには、日本語docstringで確認する振る舞いと検出したい誤りを記録する。
- 変更は `codex/drop-order-maintenance` ブランチで行い、本人の承認前にmainへ取り込まない。

---

### タスク1: 駒打ち順の独立性を失敗するテストで表す

**ファイル:**
- 変更: `tests/test_movegen.py:2459-2548`（`LegalMoveListTests`）

**インターフェース (Interfaces):**
- 消費: `legal_moves(position) -> Tuple[Move, ...]`、`DropMove(piece_type, destination)`、既存の局面スナップショット。
- 生産: 先手・後手の全7駒種・全打ち先、局面不変性、`BasicPieceType`反復順からの独立性を確認するテスト。

- [x] **ステップ1: 期待する駒打ち順とテスト局面の補助を追加する**

  実装側の定数を参照しない期待順をテストへ置く。空盤面の手番側に飛・角・金・銀・桂・香・歩を各1枚加える。期待値は駒種ごとに筋1から9、各筋の段1から9を走査し、先手は歩・香の一段と桂の一・二段、後手は歩・香の九段と桂の八・九段を除外する。

```python
_DROP_ORDER = (BasicPieceType.ROOK, BasicPieceType.BISHOP,
               BasicPieceType.GOLD, BasicPieceType.SILVER,
               BasicPieceType.KNIGHT, BasicPieceType.LANCE,
               BasicPieceType.PAWN)

def _position_with_all_drops(self, side):
    position = Position(Board(), side)
    hand = position.sente_hand if side == Side.SENTE else position.gote_hand
    for piece_type in self._DROP_ORDER:
        hand.add(piece_type)
    return position

def _expected_drops(self, side):
    excluded_ranks = {
        BasicPieceType.PAWN: {1} if side == Side.SENTE else {9},
        BasicPieceType.LANCE: {1} if side == Side.SENTE else {9},
        BasicPieceType.KNIGHT: {1, 2} if side == Side.SENTE else {8, 9},
    }
    return tuple(DropMove(piece_type, Square(file, rank))
                 for piece_type in self._DROP_ORDER
                 for file in range(1, 10)
                 for rank in range(1, 10)
                 if rank not in excluded_ranks.get(piece_type, set()))
```

- [x] **ステップ2: 反復順を入れ替える失敗テストを追加する**

  `unittest.mock.patch.object` で `movegen.BasicPieceType` だけを、歩から始まる別順序で反復するテスト用オブジェクトへ一時的に置き換える。各属性値は本物の`BasicPieceType`を使うため、持ち駒・合法性規則は変えない。現実装は直接反復するため、最初の`DropMove`が飛でなく歩となり、一覧全体との比較が`AssertionError`で失敗する。

```python
from unittest.mock import patch

class _ReorderedBasicPieceTypes:
    KING = BasicPieceType.KING
    ROOK = BasicPieceType.ROOK
    BISHOP = BasicPieceType.BISHOP
    GOLD = BasicPieceType.GOLD
    SILVER = BasicPieceType.SILVER
    KNIGHT = BasicPieceType.KNIGHT
    LANCE = BasicPieceType.LANCE
    PAWN = BasicPieceType.PAWN

    def __iter__(self):
        return iter((self.KING, self.PAWN, self.LANCE, self.KNIGHT,
                     self.SILVER, self.GOLD, self.BISHOP, self.ROOK))

def test_drop_order_does_not_follow_basic_piece_type_iteration(self):
    """駒打ち順はBasicPieceTypeの反復順に依存しない。"""
    position = self._position_with_all_drops(Side.SENTE)
    before = self._snapshot(position)
    with patch.object(movegen, "BasicPieceType", _ReorderedBasicPieceTypes()):
        self.assertEqual(movegen.legal_moves(position),
                         self._expected_drops(Side.SENTE))
    self.assertEqual(self._snapshot(position), before)
```

- [x] **ステップ3: Redを確認する**

  `python3 -m unittest -v tests.test_movegen.LegalMoveListTests.test_drop_order_does_not_follow_basic_piece_type_iteration` を実行する。読み込みエラーではなく、公開順の独立性が未実装である`AssertionError`を確認する。

### タスク2: 非公開順序定数による最小実装と全件確認

**ファイル:**
- 変更: `kaname_shogi/movegen.py:414-478`
- 変更: `tests/test_movegen.py:2459-2548`

**インターフェース (Interfaces):**
- 消費: タスク1の期待順、テスト局面、独立性テスト。
- 生産: `_DROP_PIECE_TYPES: Tuple[BasicPieceType, ...]` と、それを使う `_legal_moves(position, *, check_uchi_fuzume) -> Tuple[Move, ...]`。

- [x] **ステップ1: モジュール非公開の順序定数を追加する**

```python
_DROP_PIECE_TYPES = (BasicPieceType.ROOK, BasicPieceType.BISHOP,
                     BasicPieceType.GOLD, BasicPieceType.SILVER,
                     BasicPieceType.KNIGHT, BasicPieceType.LANCE,
                     BasicPieceType.PAWN)
```

- [x] **ステップ2: 駒打ち列挙を最小変更する**

  `_legal_moves` の`for piece_type in BasicPieceType`と玉除外分岐を、`for piece_type in _DROP_PIECE_TYPES`へ置き換える。打ち先の筋・段ループ、試し打ち、例外時の継続、`DropMove`追加は変えない。

- [x] **ステップ3: 先手・後手の全件順序テストを追加する**

  全期待値との一致、一覧前後の局面不変性、行き所のない段の除外を先手・後手ごとに確認する。期待値は実装の`_DROP_PIECE_TYPES`を参照しない。

```python
def test_returns_all_drops_in_fixed_order_for_each_side(self):
    """全持ち駒の駒打ちを先後別の固定順で返し、局面を変更しない。"""
    for side in Side:
        with self.subTest(side=side):
            position = self._position_with_all_drops(side)
            before = self._snapshot(position)
            self.assertEqual(movegen.legal_moves(position),
                             self._expected_drops(side))
            self.assertEqual(self._snapshot(position), before)
```

- [x] **ステップ4: Greenを確認する**

  `python3 -m unittest -v tests.test_movegen.LegalMoveListTests` を実行する。既存テストと、新しい独立性・先後全件・不変性テストがすべてPASSすることを確認する。

- [x] **ステップ5: Refactor要否を確認して対象テストを再実行する**

  順序定数以外の共通化、`BasicPieceType`変更、打ち先走査変更は不要と判断する。対象テストを再実行する。

- [x] **ステップ6: 作業ブランチへコミットする**

  `git add kaname_shogi/movegen.py tests/test_movegen.py` の後、`git commit -m "refactor: 駒打ち順を明示定数で固定する"` を実行する。

### タスク3: 独立レビュー・全検証・記録

**ファイル:**
- 作成: `docs/learning/40-drop-order-maintenance.md`
- 作成: `docs/knowledge/32-drop-order-maintenance.md`
- 参照: `docs/plans/2026-09-26-drop-order-maintenance-design.md`
- 参照: `docs/plans/2026-09-26-drop-order-maintenance.md`

**インターフェース (Interfaces):**
- 消費: タスク2のコードとテスト、設計書、実装計画。
- 生産: レビュー結論、検証結果、対象範囲、確認問題と回答を記録した学習記録・知識メモ。

- [x] **ステップ1: 独立コードレビューを行う**

  公開順の明示性、`BasicPieceType`からの独立性、玉の除外、先後の全駒種・全打ち先、行き所のない段、局面不変性、二歩・自玉の安全・打ち歩詰め、docstring、不要な公開APIを確認する。CriticalまたはImportantがあれば修正、再検証、再レビューする。

- [x] **ステップ2: 全検証を実行する**

  `python3 -m unittest discover -s tests -v`、`printf 'move 7 7 7 6\\n' | python3 -m kaname_shogi`、`git diff --check` を実行する。全テストPASS、CLIスモークで後手の自動手・次の入力案内・EOF終了、差分検査の成功を確認する。

- [x] **ステップ3: 学習記録と知識メモを作成・コミットする**

  学習記録には一次資料との切り分け、確認問題と本人の回答・補足、合意、TDDのRed/Green、Refactor要否、独立レビュー、全検証、main取り込み結果、最後の理解確認を時系列で記録する。知識メモには順序定数の責務、`BasicPieceType`との分離、公開APIの再現性、対象外を記録する。`git commit -m "docs: 第40回の駒打ち順保守改善を記録する"` を使う。

- [x] **ステップ4: mainへの取り込み承認を本人へ求める**

  作業ブランチの変更、レビュー結論、検証結果、作業ディレクトリと取り込み先を示し、`main`への取り込みを本人が明示承認するまで待つ。

- [x] **ステップ5: 承認後にmainへ取り込み、mainで再検証する**

  `git switch main`、`git merge --no-ff codex/drop-order-maintenance -m "merge: 駒打ち順保守改善を取り込む"` の後、全テスト、CLIスモーク、`git diff --check`をmain上で再実行する。

- [ ] **ステップ6: 最後の理解確認を一問だけ出す**

  main取り込みと再検証後だけ、「`BasicPieceType`の定義順と`_DROP_PIECE_TYPES`を分けたことで、固定種の乱数を使う弱いコンピュータの再現性をどう守れるか」を尋ねる。本人の回答と補足を学習記録へ追記してコミットする。
