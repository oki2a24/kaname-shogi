# 第38回：弱い自動指し手のための合法手列挙と一手選択 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 現在実装済みの規則に従う全合法手を固定順の不変データ列で返し、注入された乱数生成器でその中から一手を選ぶPython APIを追加する。

**アーキテクチャ:** `move.py` に中立な一手値を分離し、`movegen.py` は既存の `apply_move` / `apply_drop` を複製局面へ試して一覧を作る。選択器は局面とCLIに依存せず、列挙済みタプルと `random.Random` だけを受け取る。

**技術スタック:** Python 3.9標準ライブラリ（`dataclasses`、`typing`、`random`、`unittest`）

**仕様 (Spec):** [第38回設計仕様](2026-09-25-weak-move-selection-design.md)

**グローバル制約 (Global Constraints):**
- Python 3.9.6で動作し、外部パッケージを追加しない。
- 座標は既存の `Square(file, rank)` による筋・段を使い、内部添字を公開しない。
- 公開インターフェースのdocstringには引数・戻り値・副作用・前提条件・設計理由を日本語で記録する。
- テストメソッド名は英語、docstringは日本語とし、各振る舞いで明示的な失敗をRedとして確認してから最小実装する。
- 既存の `apply_move` / `apply_drop` の合法性規則を重複実装せず、試し指しには独立した `Position.copy()` を使う。
- CLIの入力、表示、対局進行は変更しない。
- USI・SFEN・JSON変換、終局理由の外部表現、評価・探索、人間対コンピュータCLIは実装しない。
- 実装は `main` ではなく `codex/weak-move-selection` ブランチで行い、mainへの取り込みはレビュー・記録・本人承認の後だけにする。

---

## ファイル構成

| ファイル | 責務 |
| --- | --- |
| `kaname_shogi/move.py`（新規） | `BoardMove`、`DropMove`、`Move` を局面を変えない中立な一手データとして定義する。 |
| `kaname_shogi/movegen.py` | `legal_moves`、内部の全列挙、`has_legal_move` の委譲、`choose_weak_move` を追加する。 |
| `tests/test_move.py`（新規） | 一手データの値・不変性を検証する。 |
| `tests/test_movegen.py` | 合法手一覧、固定順、既存規則との一致、選択器を検証する。 |
| `README.md` | 現在の到達点とPython APIの利用方法を更新する。 |
| `docs/learning/38-weak-move-selection.md`（新規） | 学習目的、確認問題、実装・検証・レビュー・振り返りを記録する。 |
| `docs/knowledge/31-weak-move-selection.md`（新規） | 公開API、列挙順、責務境界、将来への申し送りを記録する。 |

## タスク 0: 作業ブランチを作る

**ファイル:** 変更なし。

- [x] **ステップ 1: 現在の状態を確認する**

実行: `git status --short --branch` と `git branch --show-current`。

期待値：設計仕様・実装計画だけが未追跡で、通常ブランチにいないことを確認する。

- [x] **ステップ 2: 作業ブランチを作る**

実行: `git switch -c codex/weak-move-selection`

期待値：`codex/weak-move-selection` が現在ブランチになる。未追跡の設計文書は失わない。

## タスク 1: 中立な一手データを追加する

**ファイル:**
- 作成: `kaname_shogi/move.py`
- 作成: `tests/test_move.py`

**インターフェース (Interfaces):**
- 消費: `BasicPieceType`、`Square`
- 生産: `BoardMove(source: Square, destination: Square, promote: bool)`、`DropMove(piece_type: BasicPieceType, destination: Square)`、`Move = Union[BoardMove, DropMove]`

- [x] **ステップ 1: 失敗するデータ型テストを作成する**

`tests/test_move.py` では `try` / `except ModuleNotFoundError` と `_require_implementation()` を使い、読込エラーではなく明示的アサーションでRedにする。次をテストする。

```python
def test_board_move_keeps_values_and_is_immutable(self):
    """盤上移動は出発・到着・成り指定を変更不可の値として保持する。"""
    self._require_implementation()
    move = BoardMove(Square(7, 7), Square(7, 6), False)
    self.assertEqual(move.source, Square(7, 7))
    self.assertEqual(move.destination, Square(7, 6))
    self.assertFalse(move.promote)
    with self.assertRaises(FrozenInstanceError):
        move.promote = True
```

同じ形式で `DropMove(BasicPieceType.PAWN, Square(5, 5))` の値と不変性も確認する。

- [x] **ステップ 2: Redを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_move -v`

期待値：`_require_implementation()` の明示的失敗。

- [x] **ステップ 3: 最小の一手データを実装する**

`kaname_shogi/move.py` に `dataclass(frozen=True)` の `BoardMove` と `DropMove` を作る。Python 3.9互換のため `from typing import Union` を使い、`Move = Union[BoardMove, DropMove]` とする。各公開docstringには、値であり局面を変更しないこと、各属性、独立モジュールに置く理由を日本語で記す。

- [x] **ステップ 4: Greenを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_move -v`

期待値：一手データのテスト全件成功。

- [x] **ステップ 5: コミットする**

実行: `git add kaname_shogi/move.py tests/test_move.py && git commit -m "feat: 中立な指し手データを追加する"`

## タスク 2: 全合法手を固定順で列挙する

**ファイル:**
- 変更: `kaname_shogi/movegen.py:15-18, 412-471`
- 変更: `tests/test_movegen.py:2457-2575, 2881-2890`

**インターフェース (Interfaces):**
- 消費: `BoardMove`、`DropMove`、`Move`、`Position.copy()`、`apply_move`、`_apply_drop`
- 生産: `legal_moves(position: Position) -> Tuple[Move, ...]`、`has_legal_move(position: Position) -> bool`

- [x] **ステップ 1: 失敗する合法手一覧テストを作成する**

`tests/test_movegen.py` に `LegalMoveListTests` を追加する。未実装時は `hasattr(movegen, "legal_moves")` により明示的に失敗させる。盤上に両玉と先手の7七歩を置く局面で、次の固定順と局面不変性を確認する。

```python
expected = (
    BoardMove(Square(5, 9), Square(4, 8), False),
    BoardMove(Square(5, 9), Square(5, 8), False),
    BoardMove(Square(5, 9), Square(6, 8), False),
    BoardMove(Square(7, 7), Square(7, 6), False),
)
self.assertEqual(movegen.legal_moves(position), expected)
self.assertEqual(self._snapshot(position), before)
```

さらに、成り・不成の双方が可能な歩では不成が先になること、持ち歩の駒打ちは盤上移動の後かつ一一から九九の順になること、二歩・行き所のない駒・王手放置・打ち歩詰めを含めないこと、詰み局面は空タプルかつ `has_legal_move` が偽であることを追加する。既存の打ち歩詰め再帰回避テストは、内部の全列挙器で `check_uchi_fuzume=False` が伝播することを確認するよう更新する。

- [x] **ステップ 2: Redを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_movegen.LegalMoveListTests -v`

期待値：`legal_moves がまだ実装されていません` という明示的失敗。

- [x] **ステップ 3: 内部全列挙器と公開操作を実装する**

`movegen.py` に `Tuple` と一手型をimportする。既存の早期returnする `_has_legal_move` を、次の責務の `_legal_moves` に置き換える。

```python
def _legal_moves(position: Position, *, check_uchi_fuzume: bool) -> Tuple[Move, ...]:
    moves = []
    # file=1..9、rank=1..9、既存候補順、不成→成りで試す。
    # apply_move(position.copy(), ...) が成功した場合だけBoardMoveを追加する。
    # 飛・角・金・銀・桂・香・歩と全マスを試し、成功したDropMoveを後ろへ追加する。
    return tuple(moves)
```

盤上移動は `apply_move(position.copy(), ...)`、駒打ちは `_apply_drop(position.copy(), ..., check_uchi_fuzume=...)` に委譲する。`legal_moves` は真の打ち歩詰め検証で内部列挙を呼ぶ。`has_legal_move` は `return bool(legal_moves(position))` とし、`_is_checkmate` は再帰回避用の設定を保った内部列挙の空判定を使う。公開docstringに戻り値、固定順、局面不変性、規則再利用の理由を記す。

- [x] **ステップ 4: Greenを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_movegen.LegalMoveListTests tests.test_movegen.LegalMoveEnumerationTests tests.test_movegen.UchiFuzumeTests -v`

期待値：列挙、有無、詰み、打ち歩詰め再帰回避の対象テスト全件成功。

- [x] **ステップ 5: コミットする**

実行: `git add kaname_shogi/movegen.py tests/test_movegen.py && git commit -m "feat: 合法手を固定順で列挙する"`

## タスク 3: 弱いランダム一手選択を追加する

**ファイル:**
- 変更: `kaname_shogi/movegen.py:先頭import部とlegal_movesの直後`
- 変更: `tests/test_movegen.py:LegalMoveListTestsの後`

**インターフェース (Interfaces):**
- 消費: `Tuple[Move, ...]`、`random.Random`
- 生産: `choose_weak_move(moves: Tuple[Move, ...], rng: random.Random) -> Optional[Move]`

- [x] **ステップ 1: 失敗する選択器テストを作成する**

`WeakMoveSelectionTests` を追加し、未実装時は `hasattr(movegen, "choose_weak_move")` で明示的に失敗させる。次を確認する。

```python
moves = (
    BoardMove(Square(7, 7), Square(7, 6), False),
    DropMove(BasicPieceType.PAWN, Square(5, 5)),
)
first = movegen.choose_weak_move(moves, random.Random(20260925))
second = movegen.choose_weak_move(moves, random.Random(20260925))
self.assertIn(first, moves)
self.assertEqual(first, second)
```

空タプルでは `None`、選択前後で入力タプルが同じ、局面を引数に取らないことも確認する。

- [x] **ステップ 2: Redを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_movegen.WeakMoveSelectionTests -v`

期待値：`choose_weak_move がまだ実装されていません` という明示的失敗。

- [x] **ステップ 3: 最小の選択器を実装する**

`movegen.py` に `import random` を追加し、空なら `None`、それ以外は `rng.choice(moves)` を返す `choose_weak_move` を実装する。docstringには `legal_moves` 由来の一覧を渡す前提、局面・一手値を変えないこと、乱数生成器の状態だけを進めること、終局・投了を決めない理由を記す。

- [x] **ステップ 4: Greenを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_movegen.WeakMoveSelectionTests -v`

期待値：固定種、空一覧、入力不変性の対象テスト全件成功。

- [x] **ステップ 5: コミットする**

実行: `git add kaname_shogi/movegen.py tests/test_movegen.py && git commit -m "feat: 弱い自動指し手の一手選択を追加する"`

## タスク 4: Refactor判断と独立レビューを行う

**ファイル:** 必要な修正が見つかった場合だけ、実装・テストファイル。

- [x] **ステップ 1: Refactor要否を確認する**

`_legal_moves` と公開操作の責務、`has_legal_move` の委譲、打ち歩詰めの再帰回避、`move.py` と `game_record.py` の依存方向、公開docstringを確認する。修正が必要なら、対象振る舞いのRedから最小修正を行う。不要なら、その結論を学習記録に残す。

- [x] **ステップ 2: 独立レビューを依頼する**

`main` との差分について、仕様適合、Python 3.9互換性、合法性規則の重複、API責務、テスト、将来のUSIとの疎結合を確認する。Critical・Important・Minorを区別して記録する。

- [x] **ステップ 3: Critical・Importantを解消して再レビューする**

指摘があれば各項目でRed、最小修正、対象テスト、全体検証、再レビューを行う。なければ「なし」と記録する。

## タスク 5: ドキュメント更新と全検証を行う

**ファイル:**
- 変更: `README.md`
- 作成: `docs/learning/38-weak-move-selection.md`
- 作成: `docs/knowledge/31-weak-move-selection.md`
- 変更: `docs/plans/2026-09-25-weak-move-selection-design.md`
- 変更: `docs/plans/2026-09-25-weak-move-selection.md`

- [x] **ステップ 1: 記録を作成・更新する**

学習記録には目的、一次資料、確認問題1〜18と本人の回答・補足・合意、TDD、Refactor、独立レビュー、検証を記す。知識メモには一手データ、公開API、固定順、`None`、責務境界、USI・CLI・評価への申し送りを記す。READMEには実際のAPI利用例を加え、CLI未変更と未実装範囲を維持する。設計書と計画書には実行した事実だけを追記し、実施済みのチェックだけを完了へ更新する。

- [x] **ステップ 2: 全検証を実行する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`

実行: `printf 'move 7 7 7 6\nresign\n' | PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi`

実行: `git diff --check`

期待値：全テスト成功、CLIは先手の7六歩と後手投了・先手勝利を表示、差分チェックは出力なし。

- [x] **ステップ 3: ドキュメントをコミットする**

実行: `git add README.md docs/learning/38-weak-move-selection.md docs/knowledge/31-weak-move-selection.md docs/plans/2026-09-25-weak-move-selection-design.md docs/plans/2026-09-25-weak-move-selection.md && git commit -m "docs: 第38回の合法手列挙学習を記録する"`

## タスク 6: mainへの取り込み前後を確認する

**前提:** 全テスト成功、独立レビューでCritical・Importantが0件、記録の内容確認が完了し、本人の取り込み承認があること。

- [ ] **ステップ 1: 取り込み候補を確認する**

実行: `git status --short --branch && git log --oneline main..codex/weak-move-selection && git diff --check main...codex/weak-move-selection`

期待値：作業ブランチがクリーンで、取り込み対象と差分チェック結果を本人へ提示できる。

- [ ] **ステップ 2: 本人のmain取り込み承認を待つ**

承認前には `main` へ取り込まない。

- [ ] **ステップ 3: 承認後にmainで再検証する**

`git switch main`、`git merge --no-ff codex/weak-move-selection` の後、全テスト、CLIスモーク、`git diff --check`、`git status --short --branch` を実行する。期待値は、全検証成功とmain作業ツリーがクリーンであること。

## 自己レビュー

- 仕様の全要件（中立な一手データ、一覧、固定順、乱数注入、空一覧、再検証しない境界、有無判定の一致、CLI非変更、将来への申し送り）に対応するタスクを置いた。
- `TODO`、`TBD`、未定義の型・関数を残していない。`BoardMove`、`DropMove`、`Move`、`legal_moves`、`choose_weak_move` の型と責務はタスク間で一貫している。
- Redは新機能の存在を明示的アサーションで失敗させ、読込エラーだけを根拠にしない。
- 既存の打ち歩詰め再帰回避を内部全列挙器へ引き継ぐタスクとテスト更新を含めた。
