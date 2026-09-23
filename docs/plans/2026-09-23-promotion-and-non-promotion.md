# 成り・不成の基礎 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキルまたは `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 盤上の成駒を14種で表現し、成り・不成・強制成りと、成駒を基本駒種として持ち駒へ戻す駒取りを局面へ適用する。

**アーキテクチャ:** `PieceType`を盤上14種へ拡張し、持ち駒8種を`BasicPieceType`へ分離する。`Piece`は不変のまま、基本駒種への復元と成駒判定を公開する。`apply_move`はキーワード専用の`promote`を受け、検証後に成駒の新しい値を置く。

**技術スタック:** Python 3.9+、標準ライブラリ（`dataclasses`、`enum`、`unittest`）、外部依存なし。

**仕様 (Spec):** `docs/plans/2026-09-23-promotion-and-non-promotion-design.md`

**グローバル制約 (Global Constraints):**

- 実装は`/Users/oki2a24/kaname-shogi`の`codex/promotion-and-non-promotion`ブランチで行う。mainへの取り込みは、実装・検証・Refactor後の独立レビュー・学習記録がそろい、本人の承認を得た後だけ行う。
- 公開インターフェースのdocstringは日本語で、引数・戻り値・副作用・前提条件・設計理由を記す。成駒は定義箇所で日本語名を併記する。
- テスト名は英語、docstringは日本語とする。振る舞いごとに読み込みエラーではないRed、最小実装、Green、Refactor要否確認を行う。失敗時は盤面81マス、手番、双方の持ち駒を変更しない。
- 成駒の移動先候補と成駒の移動、王手・詰み・合法手、打ち歩詰め、CLI入力、USI/SFEN、履歴、評価、探索は実装しない。
- 実装後は対象テスト、全テスト、CLI、`git diff --check`を実行する。Refactor後に独立コードレビューを行い、Critical・Importantは解消後に再検証・再レビューする。

---

## ファイル構成

| ファイル | 責務 |
| --- | --- |
| `kaname_shogi/model.py` | 盤上14種、持ち駒8種、成駒復元、成駒判定、持ち駒の型境界。 |
| `kaname_shogi/movegen.py` | 成り・強制成り、成駒取り、二歩、駒打ち。 |
| `tests/test_model.py` | 駒種、復元、不変性、持ち駒の型境界。 |
| `tests/test_movegen.py` | 成り、不成、強制成り、不変性、成駒取り、二歩。 |
| `README.md`、`docs/knowledge/22-promotion-and-non-promotion.md`、`docs/learning/29-promotion-and-non-promotion.md` | 利用者向け説明、確定知識、実施記録。 |

### タスク1: ブランチ準備と型分離

**ファイル:** `kaname_shogi/model.py`、`kaname_shogi/movegen.py`、`tests/test_model.py`、`tests/test_movegen.py`

**生産するインターフェース:** `BasicPieceType`、14値の`PieceType`、`Piece.base_piece_type: BasicPieceType`、`Piece.is_promoted: bool`、`Hand.{count,add,remove}(BasicPieceType)`。

- [ ] **ステップ1: ブランチを作る**

実行: `git switch -c codex/promotion-and-non-promotion`。続けて`git status --short --branch`を実行し、新ブランチかつ未コミット変更なしを確認する。

- [ ] **ステップ2: 失敗するモデルテストと型移行テストを書く**

`Piece(PieceType.PRO_PAWN, Side.SENTE)`の`base_piece_type`が`BasicPieceType.PAWN`、`is_promoted`が真であるテストを加える。全成駒6種の復元、`Hand.add(PieceType.PRO_PAWN)`の`ValueError`と不変性を確認する。既存のHand・駒打ちテストは`BasicPieceType`へ移行する。

- [ ] **ステップ3: Redを確認する**

実行: `python3 -m unittest tests.test_model -v`。`PRO_PAWN`、`BasicPieceType`、または読み取り値の未実装による振る舞い上の失敗を確認する。読み込みエラーはRedと扱わない。

- [ ] **ステップ4: 最小実装を加える**

`PieceType`に`PRO_PAWN`（と金）、`PRO_LANCE`（成香）、`PRO_KNIGHT`（成桂）、`PRO_SILVER`（成銀）、`HORSE`（馬）、`DRAGON`（竜）を加える。`BasicPieceType`には未成8種だけを置く。`Piece.base_piece_type`は成駒6種の対応表と同名未成駒の変換で返し、`is_promoted`は対応表のキーで判定する。`Hand`は`BasicPieceType`以外を拒否する。

- [ ] **ステップ5: Greenとコミットを確認する**

実行: `python3 -m unittest tests.test_model tests.test_movegen -v`。成功後、対象4ファイルを`feat: 盤上駒種と持ち駒種を分離`としてコミットする。

### タスク2: 成り・不成と強制成りを適用する

**ファイル:** `kaname_shogi/movegen.py`、`tests/test_movegen.py`

**生産するインターフェース:** `apply_move(position: Position, source: Square, destination: Square, *, promote: bool = False) -> None`。

- [ ] **ステップ1: 失敗する成りテストを書く**

先後双方について、敵陣へ入る任意成り、不成、移動前だけ敵陣の成り、歩・香・桂の強制成り、玉・金・成駒・敵陣外での成り指定を追加する。成駒を出発駒にした移動も拒否する。拒否時には盤面・手番・双方の持ち駒の不変性を確認する。

- [ ] **ステップ2: Redを確認する**

実行: `python3 -m unittest tests.test_movegen.ApplyMoveTests -v`。`promote`未対応または強制成りの未拒否による失敗を確認する。

- [ ] **ステップ3: 最小実装を加える**

`_is_enemy_camp(side, rank)`は先手の一〜三段、後手の七〜九段を返す。`_can_promote(piece, source, destination)`は未成の飛・角・銀・桂・香・歩で、出発または到着が敵陣のときだけ真とする。`_must_promote(piece, destination)`は先手の歩・香の一段、桂の一・二段と、後手の歩・香の九段、桂の八・九段で真とする。`apply_move`は全検証後にだけ更新し、`promote=True`は未成→成駒の対応表で新しい`Piece`を置く。成駒は候補関数へ渡す前に拒否する。

- [ ] **ステップ4: Greenとコミットを確認する**

実行: `python3 -m unittest tests.test_movegen.ApplyMoveTests -v`。成功後、2ファイルを`feat: 成りと強制成りを適用する`としてコミットする。

### タスク3: 成駒取りと二歩の境界を固定する

**ファイル:** `kaname_shogi/movegen.py`、`tests/test_movegen.py`

**生産するインターフェース:** `apply_drop(position: Position, piece_type: BasicPieceType, destination: Square) -> None`。成駒取りは`target_piece.base_piece_type`を持ち駒へ加える。

- [ ] **ステップ1: 失敗する境界テストを書く**

と金・成香・成桂・成銀・馬・竜の各駒取りで、歩・香・桂・銀・角・飛が持ち駒へ増えることを確認する。同じ筋にと金だけがある場合、`BasicPieceType.PAWN`を打てることも確認する。

- [ ] **ステップ2: Redを確認する**

実行: `python3 -m unittest tests.test_movegen.ApplyMoveTests tests.test_movegen.ApplyDropTests -v`。成駒が基本駒種へ戻らない、または二歩がと金を数える失敗を確認する。

- [ ] **ステップ3: 最小実装を加える**

駒取りは`hand.add(target_piece.base_piece_type)`を使う。`apply_drop`は`BasicPieceType`と同名の未成`PieceType`を置く。二歩の走査は`PieceType.PAWN`だけを数え、`PRO_PAWN`を除外する。

- [ ] **ステップ4: Greenとコミットを確認する**

実行: `python3 -m unittest tests.test_movegen.ApplyMoveTests tests.test_movegen.ApplyDropTests -v`。成功後、2ファイルを`feat: 成駒を基本駒種として持ち駒へ戻す`としてコミットする。

### タスク4: Refactor、検証、独立レビュー、記録

**ファイル:** 実装・テスト4ファイル、`README.md`、`docs/knowledge/22-promotion-and-non-promotion.md`、`docs/learning/29-promotion-and-non-promotion.md`

- [ ] **ステップ1: Refactor要否を確認する**

対応表の重複、判定と局面変更の混在、公開docstringの不一致を確認する。必要なら対応表を一つの非公開操作へ集約するが、候補生成の再構成はしない。

- [ ] **ステップ2: 全検証を実行する**

`python3 -m unittest discover -s tests -v`、`python3 -m kaname_shogi`、`git diff --check main...HEAD`、`git status --short --branch`を順に実行する。全テスト成功、CLIの初期局面表示、差分検査出力なし、新ブランチを確認する。

- [ ] **ステップ3: 独立コードレビューを実施する**

敵陣の先後・出発・到着判定、強制成りの不変性、成駒取り、と金の二歩除外、成駒の未成扱い拒否、二つの駒種の混用を確認する。Critical・Important・Minorと対応を記録し、CriticalまたはImportantは修正・再検証・再レビューする。

- [ ] **ステップ4: README・知識・学習記録を更新してコミットする**

READMEには14種/8種の区別、`promote`、成駒取り、成駒移動が未実装であることを記す。知識メモには一次資料、敵陣、任意成り・不成・強制成り、復元と二歩を記す。学習記録には確認問題6問、承認済み設計、実際のRed/Green/検証/レビュー結果だけを記す。全ファイルを`docs: 成り・不成の学習を記録`としてコミットし、mainへの取り込みは本人の承認を待つ。
