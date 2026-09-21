# 空マスへの移動適用 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、`executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックスを使用します。

**目標:** 空いている到着マスへ盤上の駒を移し、失敗時には盤面を変更しない `move_piece` を追加する。

**アーキテクチャ:** `Board` 単位の可変操作として `move_piece(board, source, destination)` を `movegen.py` に追加する。検証を完了してから `Board.set_piece` を2回呼び、候補生成・手番・駒取りなどを混ぜない。

**技術スタック:** Python標準ライブラリ、`unittest`、既存の `Board`・`Piece`・`Square`。

**仕様 (Spec):** `docs/design/10-empty-square-move-application.md`

**グローバル制約 (Global Constraints):**
- 指示・応答・学習記録・設計文書は日本語で記述する。
- 座標は将棋の筋・段を基本とし、数学のxyを公開インターフェースに導入しない。
- 公開インターフェースのdocstringに引数・戻り値・副作用・前提条件と設計理由を記録する。
- テストメソッド名は英語とし、日本語docstringで確認する振る舞いと背景を説明する。
- 今回は駒取り、持ち駒、成り、手番更新、王手、合法手判定、詰み、CLI入力、評価、探索を実装しない。
- 実装はTDDのRed → Green → Refactorで進める。

---

### タスク1：失敗する移動適用テストを追加

**ファイル:**
- 変更：`tests/test_movegen.py`
- 参照：`kaname_shogi/model.py`、`kaname_shogi/movegen.py`

**インターフェース:**
- 消費：`Board.set_piece(Square, Optional[Piece])`、`Board.piece_at(Square)`
- 生産：`move_piece(board, source, destination)` の期待仕様をテストで固定する。

- [x] 空の到着マスへの移動で出発マスが空になり、到着マスへ同じ `Piece` が置かれるテストを書く。
- [x] 空の出発マス、占有された到着マス、同一マスをそれぞれ `ValueError` とするテストを書く。
- [x] 各不正入力の前後で盤面81マスが一致するテストを書く。
- [x] テストを実行し、関数未実装による失敗であることを確認する。

実行：`python3 -m unittest tests.test_movegen -v`

### タスク2：最小実装でGreenにする

**ファイル:**
- 変更：`kaname_shogi/movegen.py`
- 変更：`tests/test_movegen.py`（必要なimportのみ）

**インターフェース:**
- 消費：タスク1の失敗テスト、`Board`、`Square`、`Piece`。
- 生産：`move_piece(board: Board, source: Square, destination: Square) -> None`。

- [x] `move_piece` の日本語docstringに引数、戻り値、副作用、前提条件、設計理由を記述する。
- [x] 検証を先に行い、出発マスの駒をローカル変数へ保存する。
- [x] 検証成功後だけ `source` を空にし、`destination` に保存した駒を置く。
- [x] 対象テストを実行し、Greenを確認する。
- [x] 全テストを実行し、既存の候補生成を壊していないことを確認する。

実行：`python3 -m unittest tests.test_movegen -v`

### タスク3：Refactorと文書の整合確認

**ファイル:**
- 変更：`kaname_shogi/movegen.py`
- 変更：`README.md`
- 変更：`docs/learning/21-empty-square-move-application.md`
- 変更：`docs/resume.md`

- [x] docstringとREADMEに、候補生成と移動適用の違いを記録する。
- [x] READMEに空マスへの移動適用の使用例と対象外範囲を追加する。
- [x] 学習記録に実装結果・検証結果・未解決事項を追記する。
- [x] `docs/resume.md` に現在の到達点と次回の理解確認を追記する。
- [x] `git diff --check` を実行する。
- [x] CLI `python3 -m kaname_shogi` を実行する。
- [x] 全テストを再実行する。
