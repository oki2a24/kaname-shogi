# 詰み・終局判定 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 現在実装済みの規則で合法手を全候補から試し、詰みと詰みによる最小の終局を局面を変更せずに判定できるようにする。

**アーキテクチャ:** `movegen.py` に、既存の候補生成と `apply_move`・`apply_drop` を再利用する `has_legal_move` を追加する。`is_checkmate` は王手かつ合法手なし、`is_game_over` は今回に限り詰みと同じ結果を返す。新しい指し手データ型は導入しない。

**技術スタック:** Python 3.9、標準ライブラリ `unittest`

**仕様 (Spec):** `docs/plans/2026-09-23-checkmate-and-game-end-design.md`

**グローバル制約 (Global Constraints):**
- 説明・学習記録・知識メモは日本語で書く。
- 公開インターフェースのdocstringに引数・戻り値・副作用・前提条件と設計理由を記録する。
- テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞い、続く本文に検出したい誤りや背景を書く。
- 実装前に各振る舞いのテストを追加し、機能欠如を理由とする失敗を確認してから最小実装を行う。
- 今回の終局は詰みだけとし、打ち歩詰め、投了、千日手、持将棋、入玉、時間切れ、反則勝敗、CLI入力、履歴、評価、探索、USI/SFENは扱わない。
- 玉がない部分局面と、王手ではない合法手なし局面は詰み・終局ではない。

---

### タスク1: 全候補を試す合法手の有無

**ファイル:**
- 変更: `tests/test_movegen.py`
- 変更: `kaname_shogi/movegen.py`

**インターフェース (Interfaces):**
- 消費: `Position.copy() -> Position`、`_move_candidates_for_piece(board, source) -> list[Square]`、`apply_move(position, source, destination, *, promote=False) -> None`、`apply_drop(position, piece_type, destination) -> None`
- 生産: `has_legal_move(position: Position) -> bool`

- [ ] **ステップ 1: 失敗するテストを作成**

`LegalMoveEnumerationTests` を `tests/test_movegen.py` に追加し、盤上の一手、持ち駒を打つ一手、成りでのみ王手を防げる一手、全候補が既存規則で拒否される局面を検証する。各テストで判定前後の盤面81マス・双方の持ち駒・手番を比較する。

```python
def test_finds_a_legal_drop_without_changing_position(self):
    """持ち駒を打つ一手があれば合法手ありと判定し、局面を変更しない。"""
    position = Position(Board(), Side.SENTE)
    position.sente_hand.add(BasicPieceType.GOLD)
    before = self._snapshot(position)

    self.assertTrue(hasattr(movegen, "has_legal_move"),
                    "has_legal_move がまだ実装されていません")
    self.assertTrue(movegen.has_legal_move(position))
    self.assertEqual(self._snapshot(position), before)
```

- [ ] **ステップ 2: テストが失敗することを確認するために実行**

実行: `python3 -m unittest tests.test_movegen.LegalMoveEnumerationTests -v`

期待値: `movegen.has_legal_move` が未実装であるため、`AttributeError` ではなく、テストの `hasattr` による明示的なアサーション失敗となる。盤上移動・駒打ち・成りの各経路を同一の欠如で失敗させず、最初のテストごとに失敗理由を読む。

- [ ] **ステップ 3: 最小限の実装を作成**

`movegen.py` に、手番側の盤上駒・既存候補・成りの二指定・玉以外の持ち駒種・全81マスを走査し、各試行の複製局面へ既存公開操作を適用する実装を追加する。`ValueError` だけを候補不成立として捕捉する。

```python
def has_legal_move(position: Position) -> bool:
    for source in _all_squares():
        piece = position.board.piece_at(source)
        if piece is not None and piece.side == position.side_to_move:
            for destination in _move_candidates_for_piece(position.board, source):
                for promote in (False, True):
                    try:
                        apply_move(position.copy(), source, destination,
                                   promote=promote)
                        return True
                    except ValueError:
                        pass
    # 玉以外の各持ち駒と全マスについても同様に apply_drop を試す。
    return False
```

- [ ] **ステップ 4: テストがパスすることを確認するために実行**

実行: `python3 -m unittest tests.test_movegen.LegalMoveEnumerationTests -v`

期待値: 追加した各テストが成功し、テストした全経路で元の局面が不変である。

- [ ] **ステップ 5: コミット**

```bash
git add kaname_shogi/movegen.py tests/test_movegen.py
git commit -m "feat: 合法手の有無を判定する"
```

### タスク2: 詰みと最小の終局判定

**ファイル:**
- 変更: `tests/test_movegen.py`
- 変更: `kaname_shogi/movegen.py`

**インターフェース (Interfaces):**
- 消費: `is_in_check(board: Board, side: Side) -> bool`、`has_legal_move(position: Position) -> bool`
- 生産: `is_checkmate(position: Position) -> bool`、`is_game_over(position: Position) -> bool`

- [ ] **ステップ 1: 失敗するテストを作成**

`CheckmateAndGameEndTests` を追加し、詰み、玉の退避・王手駒の取得・盤上合い駒・持ち駒合い駒で防げる王手、非王手、玉なし部分局面を検証する。`is_game_over` は詰みで真、他で偽であることを確認する。各操作の局面不変性を確認する。

```python
def test_checkmate_and_game_over_are_true_when_checked_king_has_no_legal_move(self):
    """王手を受けた玉に防ぐ合法手がなければ、詰みと終局を返す。"""
    position = self._position_with_a_mated_sente_king()
    before = self._snapshot(position)

    self.assertTrue(hasattr(movegen, "is_checkmate"),
                    "is_checkmate がまだ実装されていません")
    self.assertTrue(hasattr(movegen, "is_game_over"),
                    "is_game_over がまだ実装されていません")
    self.assertTrue(movegen.is_checkmate(position))
    self.assertTrue(movegen.is_game_over(position))
    self.assertEqual(self._snapshot(position), before)
```

- [ ] **ステップ 2: テストが失敗することを確認するために実行**

実行: `python3 -m unittest tests.test_movegen.CheckmateAndGameEndTests -v`

期待値: `is_checkmate` と `is_game_over` が未実装であるため、最初の詰みテストが明示的な未実装アサーションで失敗する。局面構成の誤りやテスト読込エラーではないことを確認する。

- [ ] **ステップ 3: 最小限の実装を作成**

`is_checkmate` は手番側の玉がない、または王手でない場合に `False` を返し、それ以外では `not has_legal_move(position)` を返す。`is_game_over` は `is_checkmate(position)` の結果を返す。両方のdocstringへ引数、戻り値、副作用、部分局面、詰みだけを終局とする理由を記す。

```python
def is_checkmate(position: Position) -> bool:
    side = position.side_to_move
    if _find_king_square(position.board, side) is None:
        return False
    return is_in_check(position.board, side) and not has_legal_move(position)


def is_game_over(position: Position) -> bool:
    return is_checkmate(position)
```

- [ ] **ステップ 4: テストがパスすることを確認するために実行**

実行: `python3 -m unittest tests.test_movegen.CheckmateAndGameEndTests -v`

期待値: 詰み、詰みでない王手、非王手、玉なし、局面不変性の全テストが成功する。

- [ ] **ステップ 5: コミット**

```bash
git add kaname_shogi/movegen.py tests/test_movegen.py
git commit -m "feat: 詰みと終局を判定する"
```

### タスク3: 文書化・全体検証・学習記録

**ファイル:**
- 変更: `README.md`
- 作成: `docs/knowledge/25-checkmate-and-game-end.md`
- 作成: `docs/learning/32-checkmate-and-game-end.md`
- 変更: `docs/next-topics.md`

**インターフェース (Interfaces):**
- 消費: 実装済みの `has_legal_move(position)`、`is_checkmate(position)`、`is_game_over(position)`
- 生産: 第32回の学習記録、参照メモ、READMEの現状説明、次テーマ候補

- [ ] **ステップ 1: 実装済みの公開契約を文書へ反映する**

READMEに三つの判定操作と、詰みだけを終局とする今回の範囲、打ち歩詰めなどの対象外を記す。知識メモに一次資料のリンク、詰みの二条件、玉なし部分局面、全候補の試行を記す。

- [ ] **ステップ 2: 実装・レビュー・検証の事実を学習記録へ記す**

学習記録に目的、確認問題と本人の回答・補足、設計合意、Redの実際の失敗理由、Green、Refactor判断、独立レビューのCritical・Important・Minor、実際に実行した検証結果、最後の理解確認を追記する。最後の理解確認は、main取り込み後の検証が済んでから一問だけ出し、回答を待って追記する。

- [ ] **ステップ 3: 全体検証を実行する**

実行:

```bash
python3 -m unittest discover -s tests -v
python3 -m kaname_shogi
git diff --check
```

期待値: 全テスト成功、CLIは初期局面を表示して終了、`git diff --check` は出力なし。

- [ ] **ステップ 4: コミット**

```bash
git add README.md docs/knowledge/25-checkmate-and-game-end.md \
  docs/learning/32-checkmate-and-game-end.md docs/next-topics.md
git commit -m "docs: 詰み・終局判定の学習記録を追加する"
```

## 計画の自己レビュー

- 仕様の公開操作、全候補の試行、成り、持ち駒、玉なし、終局範囲をタスク1・2で対応付けた。
- 各実装タスクを、失敗テスト、失敗確認、最小実装、成功確認、コミットへ分けた。
- 実際に使うファイル、関数、テストコマンド、コミットメッセージを明記した。
- 未決定の要件や実装を先送りするプレースホルダは残していない。
