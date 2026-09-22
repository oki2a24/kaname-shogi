# 行き所のない駒の駒打ち 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** `apply_drop` が、歩・香・桂を行き所のない段へ打つ操作を、局面を変えずに拒否できるようにする。

**アーキテクチャ:** `kaname_shogi/movegen.py` に、駒種・先後・段だけを読む非公開の判定操作を追加する。`apply_drop` は持ち駒を減らす前に判定し、該当時は `ValueError` とする。既存の `ApplyDropTests` に拒否と境界成功のテストを追加する。

**技術スタック:** Python 3.9.6、Python標準ライブラリの `unittest`

**仕様 (Spec):** `docs/plans/2026-09-22-no-legal-destination-drops-design.md`

**グローバル制約 (Global Constraints):**
- 歩・香・桂を打った直後に一度も進めない段へ打つ操作を拒否する。
- 二歩、打ち歩詰め、成り・不成、盤上の移動、王手・合法手、CLI入力は扱わない。
- `apply_drop(position, piece_type, destination)` の公開インターフェースは変えない。
- 失敗時は `ValueError` とし、盤面81マス、手番、双方の持ち駒を変更しない。
- テスト名は英語、docstringは日本語で、確認する振る舞いと検出する誤りを説明する。

---

## ファイル構成

- 変更: `tests/test_movegen.py` — 駒打ちの失敗と境界成功のテストを追加する。
- 変更: `kaname_shogi/movegen.py` — 判定操作と `apply_drop` の検証・docstringを追加する。
- 変更: `README.md` — 実装後の `apply_drop` の制限を反映する。
- 作成: `docs/knowledge/21-no-legal-destination-drops.md` — 確定規則と表現を記録する。
- 作成: `docs/learning/28-no-legal-destination-drops.md` — 学習、TDD、レビュー、理解確認を記録する。
- 変更: `docs/resume.md`、`docs/next-topics.md` — 完了後の到達点と次の候補を更新する。

### タスク1: Redテストを追加する

**ファイル:**
- 変更・テスト: `tests/test_movegen.py:292-440`

**インターフェース:**
- 消費: `movegen.apply_drop(position: Position, piece_type: PieceType, destination: Square) -> None`
- 生産: `test_rejects_piece_with_no_legal_destination_without_changing_position() -> None`
- 生産: `test_allows_piece_drop_just_before_no_legal_destination() -> None`

- [x] **ステップ 1: 失敗する拒否テストを作成**

`ApplyDropTests` に次を `subTest` で追加する。各ケースで手番側の持ち駒へ対象を1枚追加し、`ValueError` と `_assert_position_unchanged` による局面不変性を確認する。

```python
cases = (
    (Side.SENTE, PieceType.PAWN, 1),
    (Side.SENTE, PieceType.LANCE, 1),
    (Side.SENTE, PieceType.KNIGHT, 1),
    (Side.SENTE, PieceType.KNIGHT, 2),
    (Side.GOTE, PieceType.PAWN, 9),
    (Side.GOTE, PieceType.LANCE, 9),
    (Side.GOTE, PieceType.KNIGHT, 8),
    (Side.GOTE, PieceType.KNIGHT, 9),
)
```

docstringは「行き所のない段への歩・香・桂打ちを拒否し、局面を変更しない。」から始め、持ち駒の先行減算、盤面配置、手番交代の誤りを検出する目的を続ける。

- [x] **ステップ 2: 境界で成功するテストを作成**

先手の歩・香は二段、先手の桂は三段、後手の歩・香は八段、後手の桂は七段へ打つケースを追加する。各ケースで配置、対象持ち駒の0枚化、先後交代を確認する。

```python
cases = (
    (Side.SENTE, PieceType.PAWN, 2, Side.GOTE),
    (Side.SENTE, PieceType.LANCE, 2, Side.GOTE),
    (Side.SENTE, PieceType.KNIGHT, 3, Side.GOTE),
    (Side.GOTE, PieceType.PAWN, 8, Side.SENTE),
    (Side.GOTE, PieceType.LANCE, 8, Side.SENTE),
    (Side.GOTE, PieceType.KNIGHT, 7, Side.SENTE),
)
```

- [x] **ステップ 3: Redを実行して失敗理由を確認**

実行: `cd /Users/oki2a24/.codex/worktrees/2e7a/kaname-shogi && python3 -m unittest discover -s tests -p 'test_movegen.py' -v`

期待値: 新しい拒否テストだけが、禁止段へ配置できて `ValueError` が出ないため失敗する。読み込みエラーではなく、対象振る舞いの未実装による失敗を確認する。

- [x] **ステップ 4: Redの実結果を学習記録へ残す**

`docs/learning/28-no-legal-destination-drops.md` を作成し、失敗件数と実際の失敗理由だけを「Red」節へ記す。未実行の結果は書かない。

### タスク2: 最小実装とGreenを完了する

**ファイル:**
- 変更: `kaname_shogi/movegen.py:123-186`
- テスト: `tests/test_movegen.py:292-440`

**インターフェース:**
- 消費: `PieceType`、`Side`、`Position`、`Square`
- 生産: `_has_no_legal_destination(piece_type: PieceType, side: Side, rank: int) -> bool`

- [x] **ステップ 1: 非公開の判定操作を追加**

`_has_unpromoted_pawn_on_file` の直後に、次の契約の `_has_no_legal_destination` を追加する。

```python
def _has_no_legal_destination(piece_type: PieceType, side: Side,
                              rank: int) -> bool:
    """piece_typeをsideがrank段へ打ったとき行き所がなければTrueを返す。"""
    last_rank = 1 if side == Side.SENTE else 9
    if piece_type in (PieceType.PAWN, PieceType.LANCE):
        return rank == last_rank
    if piece_type == PieceType.KNIGHT:
        second_last_rank = 2 if side == Side.SENTE else 8
        return rank in (last_rank, second_last_rank)
    return False
```

docstringには、各引数、戻り値、状態を変更しないこと、盤面を読まない理由を既存の操作と同じ形式で詳記する。

- [x] **ステップ 2: `apply_drop` の検証とdocstringを更新**

二歩検証の直後、`hand.remove` の前に次を追加する。

```python
if _has_no_legal_destination(piece_type, position.side_to_move,
                             destination.rank):
    raise ValueError("行き所のない段へは打てません")
```

docstringの例外へ行き所のない歩・香・桂を加え、対象外一覧からそれらを削除する。

- [x] **ステップ 3: Greenを確認**

実行: `cd /Users/oki2a24/.codex/worktrees/2e7a/kaname-shogi && python3 -m unittest discover -s tests -p 'test_movegen.py' -v`

期待値: 新しい拒否・境界成功テストと既存の移動テストがすべて成功する。

- [x] **ステップ 4: 全体を検証してGreenをコミット**

実行: `python3 -m unittest discover -s tests -v`、`python3 -m kaname_shogi`、`git diff --check` を実行する。成功を確認した後、`git add kaname_shogi/movegen.py tests/test_movegen.py` と `git commit -m "feat: 行き所のない駒打ちを拒否する"` を実行する。

### タスク3: Refactor、独立レビュー、記録を完了する

**ファイル:**
- 必要なら変更: `kaname_shogi/movegen.py`、`tests/test_movegen.py`
- 変更: `README.md`、`docs/resume.md`、`docs/next-topics.md`
- 作成: `docs/knowledge/21-no-legal-destination-drops.md`、`docs/learning/28-no-legal-destination-drops.md`

**インターフェース:**
- 消費: `_has_no_legal_destination(piece_type: PieceType, side: Side, rank: int) -> bool`
- 消費: `apply_drop(position: Position, piece_type: PieceType, destination: Square) -> None`
- 生産: 第28回の学習・知識・再開記録とレビュー結論

- [ ] **ステップ 1: Refactorの要否を確認**

判定操作が行き所だけを返し、`apply_drop` が全検証後だけ局面を変える責務を保てているか確認する。必要な場合だけ最小の改善を行い、今回の範囲外の抽象化はしない。

- [ ] **ステップ 2: Refactor後に対象・全体を再検証**

対象の移動テスト、全テスト、CLI、`git diff --check` を実行する。期待値はすべて成功し、`git diff --check` は出力なし。

- [ ] **ステップ 3: 独立コードレビューを実施**

別のレビュー担当が仕様書・差分・対象テストを確認し、Critical・Important・Minorで結論を出す。CriticalまたはImportantがあれば、修正、対象・全体再検証、再レビューを終えてから記録する。Minorは対応の要否を判断し、対応時は対象テストを再実行する。

- [ ] **ステップ 4: 文書を実結果で更新して確認後にコミット**

知識メモに一次資料、禁止段、不変性、対象外を記録する。学習記録に本人回答と補足、Red/Green/Refactor/レビューの実際の結果を記録する。README・再開案内・次テーマ候補は、実装・検証・統合済みの事実だけを反映する。内容確認後に今回の文書だけをコミットする。

- [ ] **ステップ 5: mainへ取り込む前に本人の承認を得る**

作業用ブランチ名、レビュー結論、最終検証結果、変更内容を示し、本人の承認まで `main` へ取り込まない。承認後は実際の元ディレクトリと取り込み先を確認して統合し、取り込み先で全テスト、CLI、`git diff --check` を再実行する。
