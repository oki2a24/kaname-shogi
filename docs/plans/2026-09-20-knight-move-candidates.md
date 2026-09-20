# 桂馬の移動先候補 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 盤上の桂馬について、先後・盤外・到着先の占有を考慮した移動先候補を、盤面を変更せず返す`knight_move_candidates`を追加する。

**アーキテクチャ:** 既存の`kaname_shogi.movegen`に桂馬専用の公開関数を追加し、`tests/test_movegen.py`に入力契約・候補順・飛び越し・占有・境界・不変性のテストを追加する。桂馬は走査駒ではないため、方向ごとのループや他の駒との共通化は行わず、2つの到着先を方向データから直接判定する。

**技術スタック:** Python 3.9.6、標準ライブラリ、`unittest`。

**仕様 (Spec):** `docs/design/08-knight-move-candidates.md`

**グローバル制約 (Global Constraints):**
- 説明・学習記録・知識メモは日本語で書く。
- 英語の型名やメソッド名は、日本語の意味と「データか操作か」を併せて説明する。
- テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞い、続く本文に検出したい誤りや背景を書く。
- 実装は成桂、成り・不成、行き所のない桂の合法性、実際の移動、駒取り、持ち駒、王手、合法手判定、手番による合法手の確定、他の駒との処理共有を扱わない。
- 候補生成は盤面を変更せず、`Position.side_to_move`で候補を制限しない。
- 候補順は右前（筋−1）・左前（筋＋1）とする。

---

### タスク1：桂馬の入力契約と候補順のRedテスト

**ファイル:**
- 変更: `tests/test_movegen.py`

**インターフェース:**
- 消費: `Board`、`Piece`、`PieceType.KNIGHT`、`Side`、`Square`。
- 生産: `knight_move_candidates(board, source)`に対する失敗する振る舞いテスト。

- [x] **ステップ1: テストを追加**

`KnightMoveCandidatesTests`を追加し、空の出発マスと桂馬以外の全駒種で`ValueError`を期待する。さらに、５五の先手・後手の開いた盤面について、先手は`[Square(4, 3), Square(6, 3)]`、後手は`[Square(4, 7), Square(6, 7)]`を期待する。テストメソッド名は英語、日本語docstringで確認内容と検出対象を説明する。

```python
class KnightMoveCandidatesTests(unittest.TestCase):
    def test_empty_source_is_rejected(self):
        """空の出発マスを桂馬候補の計算対象として受け付けない。

        候補なしと呼び出しの誤りを区別するValueErrorの契約を確認する。
        """
        with self.assertRaises(ValueError):
            knight_move_candidates(Board(), Square(5, 5))

    def test_open_board_returns_right_front_then_left_front(self):
        """５五の桂馬は右前、左前の順に候補を返す。

        先後の段方向、筋の増減、固定順の誤りを検出する。
        """
        board = Board()
        board.set_piece(Square(5, 5), Piece(PieceType.KNIGHT, Side.SENTE))
        self.assertEqual(knight_move_candidates(board, Square(5, 5)),
                         [Square(4, 3), Square(6, 3)])
```

- [x] **ステップ2: Redを確認**

実行: `python3 -m unittest tests.test_movegen.KnightMoveCandidatesTests -v`

期待値: `movegen`に関数がまだないため、importまたは属性解決で失敗する。これは準備段階の失敗として扱い、関数未定義だけで振る舞いのRed完了とはみなさない。

- [x] **ステップ3: 関数を最小実装**

`kaname_shogi/movegen.py`に関数名だけを公開し、出発マスの駒を調べる。空または`PieceType.KNIGHT`以外なら、既存関数と同じく`ValueError`を送出する。開いた盤面の期待値を満たすため、先後で`forward = -2`または`2`を選び、方向データ`((-1, forward), (1, forward))`を使って盤内候補を作る。自駒判定は次タスクで追加する。

```python
def knight_move_candidates(board: Board, source: Square) -> list[Square]:
    """出発マスの桂馬について、移動先候補を返す。"""
    piece = board.piece_at(source)
    if piece is None or piece.piece_type != PieceType.KNIGHT:
        raise ValueError("出発マスには桂馬を指定してください")
    forward = -2 if piece.side == Side.SENTE else 2
    candidates = []
    for file_delta in (-1, 1):
        target = Square(source.file + file_delta, source.rank + forward)
        if 1 <= target.file <= 9 and 1 <= target.rank <= 9:
            candidates.append(target)
    return candidates
```

- [x] **ステップ4: 入力契約と開いた盤面を確認**

実行: `python3 -m unittest tests.test_movegen.KnightMoveCandidatesTests -v`

期待値: 追加した入力契約と先後・候補順のテストが成功する。

- [x] **ステップ5: コミット**

```bash
git add tests/test_movegen.py kaname_shogi/movegen.py
git commit -m "test: 桂馬候補の入力契約と方向を追加"
```

### タスク2：飛び越し・占有・盤外のGreenテストと最小修正

**ファイル:**
- 変更: `tests/test_movegen.py`
- 変更: `kaname_shogi/movegen.py`

**インターフェース:**
- 消費: タスク1の`knight_move_candidates(board, source)`。
- 生産: 途中の駒を無視し、到着先の自駒だけを除外する候補生成。

- [x] **ステップ1: 振る舞いテストを追加**

先手５五の到着先４三・６三の途中に駒を置いても両方が候補になるテスト、自駒を一方の到着先に置くと他方だけになるテスト、相手駒を一方の到着先に置くとそのマスを含むテスト、１二・９二などから盤外候補を除外するテストを追加する。盤外テストでは先手と後手の両方を含める。

```python
    def test_intermediate_pieces_do_not_block_candidates(self):
        """途中のマスに駒があっても桂馬は到着先を候補にする。

        途中のマスを走査して候補を誤って止める実装を検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.KNIGHT, Side.SENTE))
        board.set_piece(Square(4, 4), Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(6, 4), Piece(PieceType.PAWN, Side.GOTE))
        self.assertEqual(knight_move_candidates(board, source),
                         [Square(4, 3), Square(6, 3)])

    def test_own_destination_is_excluded_but_opponent_destination_is_included(self):
        """自駒の到着先を除外し、相手駒の到着先を含める。

        到着先の所有者判定の欠落や、相手駒まで除外する誤りを検出する。
        """
        board = Board()
        source = Square(5, 5)
        board.set_piece(source, Piece(PieceType.KNIGHT, Side.SENTE))
        board.set_piece(Square(4, 3), Piece(PieceType.PAWN, Side.SENTE))
        board.set_piece(Square(6, 3), Piece(PieceType.PAWN, Side.GOTE))
        self.assertEqual(knight_move_candidates(board, source), [Square(6, 3)])
```

- [x] **ステップ2: 振る舞いのRedを確認**

実行: `python3 -m unittest tests.test_movegen.KnightMoveCandidatesTests -v`

期待値: 自駒を除外できない、または相手駒・途中の駒を誤って扱うため、追加テストの少なくとも一つが失敗する。

- [x] **ステップ3: 最小実装を修正**

各到着先を作った後、盤内であることを確認する。盤内なら`board.piece_at(target)`を調べ、駒があり、所有者が出発駒と同じ場合だけ候補追加をスキップする。途中のマスは参照しない。相手駒は候補へ追加し、盤面から除去しない。

```python
        if not (1 <= target.file <= 9 and 1 <= target.rank <= 9):
            continue
        occupant = board.piece_at(target)
        if occupant is not None and occupant.side == piece.side:
            continue
        candidates.append(target)
```

- [x] **ステップ4: 対象テストを確認**

実行: `python3 -m unittest tests.test_movegen.KnightMoveCandidatesTests -v`

期待値: 桂馬クラスの全テストが成功する。

- [x] **ステップ5: コミット**

```bash
git add tests/test_movegen.py kaname_shogi/movegen.py
git commit -m "feat: 桂馬の移動先候補を追加"
```

### タスク3：契約docstring・不変性テスト・既存資料の更新

**ファイル:**
- 変更: `kaname_shogi/movegen.py`
- 変更: `tests/test_movegen.py`
- 変更: `README.md`
- 変更: `docs/resume.md`
- 変更: `docs/learning/18-knight-move-candidates.md`
- 変更: `docs/knowledge/15-knight-move-candidates.md`

**インターフェース:**
- 消費: Greenになった`knight_move_candidates(board, source)`。
- 生産: 保守に必要な公開docstring、READMEの使用例、再開案内、実装記録。

- [x] **ステップ1: 不変性とリスト独立性のテストを追加**

候補計算の前後で81マスが同一であること、`Position.side_to_move`を変えても候補と手番が変わらないこと、返却リストを変更しても次回結果へ波及しないことを既存の角テストと同じ形式で追加する。

- [x] **ステップ2: 不変性テストを確認**

実行: `python3 -m unittest tests.test_movegen.KnightMoveCandidatesTests -v`

期待値: 不変性・手番独立性・リスト独立性を含む桂馬テストが成功する。

- [x] **ステップ3: 公開docstringを完成**

`movegen.py`の関数docstringに引数、戻り値、`ValueError`、先後の段方向、右前・左前の順、盤外・自駒・相手駒、盤面不変、手番非依存、対象外を記載する。`KNIGHT`が桂馬を表す駒種のデータであり、`move_candidates`が候補を求める操作であることも明記する。

- [x] **ステップ4: READMEを更新**

現在の駒一覧とテスト説明に桂馬を追加し、`knight_move_candidates`の短い使用例、候補順、飛び越し、占有条件、盤面不変、対象外を日本語で追記する。

- [x] **ステップ5: 実装記録と再開案内を更新**

`docs/learning/19-knight-candidates-implementation.md`を新規作成し、TDDのRed→Green→Refactor、変更内容、検証結果、レビュー、実装後の理解確認、未解決事項を実際の結果に基づいて記録する。理解確認は本人の回答前に正解を記録しない。`docs/resume.md`には桂馬の完了状態と次のテーマを、実際のコミットと検証結果を確認してから追記する。

- [x] **ステップ6: 全体検証**

実行:

```bash
python3 -m unittest discover -s tests -v
python3 -m kaname_shogi
git diff --check
```

期待値: 全テスト成功、CLIが初期配置と手番を表示して正常終了、差分検査成功。過去のテスト件数を再利用せず、今回の実行結果を記録する。

- [x] **ステップ7: レビュー前の確認とコミット**

変更差分を読み、桂馬の候補順、筋・段、先後、飛び越し、占有、不変性、docstring、README、学習記録、再開案内が設計書と一致することを確認する。

```bash
git add kaname_shogi/movegen.py tests/test_movegen.py README.md docs/resume.md docs/learning/19-knight-candidates-implementation.md
git commit -m "docs: 桂馬候補の実装記録を追加"
```
