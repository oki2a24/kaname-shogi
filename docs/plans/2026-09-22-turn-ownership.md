# 手番に合う駒だけを移動できること 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** `apply_move` が手番と所有者の一致する駒だけを移動し、不一致なら局面を変更せず拒否する。

**アーキテクチャ:** 手番を知らない `move_piece` は変更せず、局面を扱う `apply_move` が出発駒の `Piece.side` と `Position.side_to_move` を照合する。不一致は盤面移動の前に `ValueError` とし、一致した場合だけ既存の盤面移動と手番交代を行う。

**技術スタック:** Python 3.9.6、Python標準ライブラリ `unittest`、Git。

**仕様 (Spec):** `docs/design/11-turn-ownership.md`

**グローバル制約 (Global Constraints):**
- 指示・応答・記録はすべて日本語で行う。
- 座標は将棋の筋・段を基本とし、公開インターフェースに数学のxyを導入しない。
- 公開インターフェースのdocstringには、引数・戻り値・副作用・前提条件と設計理由を記録する。
- テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞い、続く本文に検出したい誤りや背景を書く。
- 機能追加では振る舞いごとに、失敗理由を確認するRed、最小実装のGreen、Refactor要否の確認を行う。読み込みエラーだけをRedの成功と扱わない。
- 外部パッケージは追加せず、検証は `python3 -m unittest discover -s tests -v` で行う。
- 駒取り、持ち駒、成り、移動方向、王手、合法手判定、CLI入力、評価、探索を今回の範囲に含めない。

---

## ファイル構成

- 変更: `tests/test_movegen.py` — `ApplyMoveTests` で、所有者不一致の拒否・局面不変性と、一致時の成功を検証する。
- 変更: `kaname_shogi/movegen.py` — `apply_move` の開始時に所有者と手番を照合し、公開docstringを契約に合わせる。
- 変更: `README.md` — `apply_move` の利用条件と未実装範囲を現在の契約に更新する。
- 変更: `docs/learning/23-turn-ownership.md` — 実施したRed・Green・Refactor・検証結果を追記する。
- 変更: `docs/resume.md` — 現在の到達点と次のテーマ候補を更新する。
- 作成: `docs/handover-<next-topic>.md` — 完了時点で次テーマが決まった場合だけ、再開時に必要な状態と未実装範囲を引き継ぐ。次テーマが未決定なら作成しない。

### タスク1: 所有者照合付きの局面移動（完了）

**ファイル:**
- 変更: `tests/test_movegen.py: ApplyMoveTests`
- 変更: `kaname_shogi/movegen.py: apply_move`
- 変更: `README.md: 現在の状態とapply_moveの説明`
- 変更: `docs/learning/23-turn-ownership.md: 実装・検証記録`
- 変更: `docs/resume.md: 現在の到達点と次に行うこと`

**インターフェース (Interfaces):**
- 消費 (Consumes): `Position(board: Board, side_to_move: Side)`、`Piece(piece_type: PieceType, side: Side)`、`move_piece(board: Board, source: Square, destination: Square) -> None`。
- 生産 (Produces): `apply_move(position: Position, source: Square, destination: Square) -> None`。手番と出発駒の所有者が一致し、到着マスが空なら盤面を変更して手番を交代する。不一致なら `ValueError` を送出し、盤面と手番を変更しない。

- [x] **ステップ1: 所有者不一致を拒否する失敗テストへ置き換える**

`ApplyMoveTests.test_does_not_require_moving_piece_to_match_turn` を、先手番で後手の駒、後手番で先手の駒を指定する二つのケースへ置き換える。各ケースで全81マスと手番を保存し、`ValueError` 後に同一であることを確認する。

```python
def test_rejects_piece_owned_by_the_other_side_without_changing_position(self):
    """手番と所有者が異なる駒を拒否し、局面を変更しない。

    後手の駒を先手番で、先手の駒を後手番で動かしてしまう二手指しと、
    例外時の盤面または手番の部分変更を検出する。
    """
    source, destination = Square(5, 5), Square(5, 4)
    for turn, piece_side in [(Side.SENTE, Side.GOTE), (Side.GOTE, Side.SENTE)]:
        board = Board()
        piece = Piece(PieceType.PAWN, piece_side)
        board.set_piece(source, piece)
        position = Position(board, turn)
        before_board = [board.piece_at(Square(file, rank))
                        for file in range(1, 10) for rank in range(1, 10)]
        with self.subTest(turn=turn, piece_side=piece_side):
            with self.assertRaises(ValueError):
                self._apply_move(position, source, destination)
            self.assertEqual(
                [board.piece_at(Square(file, rank))
                 for file in range(1, 10) for rank in range(1, 10)],
                before_board,
            )
            self.assertEqual(position.side_to_move, turn)
```

同時に既存の成功テストを、手番と同じ所有者の歩を置く形へ更新する。

```python
for initial_turn, expected_turn in [(Side.SENTE, Side.GOTE), (Side.GOTE, Side.SENTE)]:
    piece = Piece(PieceType.PAWN, initial_turn)
```

- [x] **ステップ2: 失敗することを確認する**

実行: `python3 -m unittest tests.test_movegen.ApplyMoveTests.test_rejects_piece_owned_by_the_other_side_without_changing_position -v`

期待値: 二つの所有者不一致ケースで `AssertionError: ValueError not raised` となりFAILする。`apply_move` 自体は存在するため、読み込みエラーや未実装関数による失敗ではない。

- [x] **ステップ3: `apply_move` に最小の所有者照合を加える**

`move_piece` を変更せず、`apply_move` の先頭で出発駒を読む。駒が存在し、所有者と手番が異なる場合だけ盤面変更前に `ValueError` を送出する。空の出発マスは既存の `move_piece` に委譲し、同一マス・占有到着マスを含む既存の拒否処理も維持する。

```python
piece = position.board.piece_at(source)
if piece is not None and piece.side != position.side_to_move:
    raise ValueError("手番と出発駒の所有者が一致しません")

move_piece(position.board, source, destination)
```

`apply_move` のdocstringを更新し、所有者不一致の `ValueError`、不一致時の局面不変性、所有者照合を `apply_move` に置く責務分離、今回扱わない移動方向などを記載する。

- [x] **ステップ4: 対象テストが成功することを確認する**

実行: `python3 -m unittest tests.test_movegen.ApplyMoveTests -v`

期待値: `ApplyMoveTests` の全テストがPASSし、先後両方の一致時は成功、不一致時と従来の不正移動時は盤面・手番が不変である。

- [x] **ステップ5: 全テスト、CLI、差分形式を検証する**

実行: `python3 -m unittest discover -s tests -v`

期待値: 全テストがPASSする。

実行: `python3 -m kaname_shogi`

期待値: 初期配置と「手番：先手」を表示して正常終了する。

実行: `git diff --check`

期待値: 出力なしで成功する。

- [x] **ステップ6: Refactor要否を確認し、利用者向け記録を更新する**

`apply_move` の追加処理が、所有者照合と既存の盤面移動委譲・手番交代だけになっていることを確認する。今回の範囲に寄与しない共通化、候補生成との統合、`Position` や `Piece` の型変更は行わない。

READMEの `apply_move` 節を、手番と出発駒の所有者が一致する場合にだけ成功する契約へ更新する。第23回の学習記録には、実際のRed失敗理由、Green、Refactorの結論、実行した検証コマンドと結果だけを追記する。`docs/resume.md` は現在の到達点、参照資料、次の再開手順を実際の完了状態に合わせる。次テーマが決まった場合だけ、その合意内容を引き継ぎ文書に記録する。

- [x] **ステップ7: 実装と記録をコミットする**

```bash
git add kaname_shogi/movegen.py tests/test_movegen.py README.md \
  docs/learning/23-turn-ownership.md docs/resume.md
git commit -m "feat: 手番と駒の所有者を照合"
```

期待値: 所有者照合の実装、テスト、説明・学習記録が同じコミットに含まれる。次テーマの引き継ぎ文書を作成した場合は、同じコミットへ明示的に追加する。

## 計画の自己レビュー

- [x] 仕様の一致: 所有者照合、成功時の盤面移動・手番交代、不一致時と既存不正時の不変性、対象外の規則をすべてタスク1に対応付けた。
- [x] プレースホルダ: 未記入の実装内容や曖昧な代替指示を含めない。
- [x] 型と名称: 現在の `Position`、`Piece`、`Side`、`Square`、`move_piece`、`apply_move` の名称とシグネチャに一致する。
- [x] コマンド: プロジェクトが使用している `unittest` とCLI起動コマンドを指定し、外部依存を追加しない。
