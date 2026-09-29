# `test_movegen.py` の局面スナップショット補助を一つにする 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** `tests/test_movegen.py` の5クラスにある同形の局面スナップショット補助を、比較対象を変えずに一つのファイル内補助へ整理する。

**アーキテクチャ:** `LegalMoveTests` の直前に、`Position` の盤面・先後の持ち駒・手番を比較用タプルとして読む `_position_snapshot(position)` を置く。5クラスの `_snapshot` は削除し、既存の不変性確認箇所を共通補助の直接呼び出しへ置換する。期待値、局面準備、テストメソッド、本体コードは変更しない。

**技術スタック:** Python 3.9、標準ライブラリ `unittest`、Git

**仕様 (Spec):** `docs/plans/2026-09-29-movegen-position-snapshot-helper-design.md`

**グローバル制約 (Global Constraints):**
- 共有するのは盤面81マス、先後の玉を除く基本持ち駒7種、手番という局面状態の読み取り方法だけにする。
- 比較対象、その順序、期待値、局面準備、テストメソッド、テスト件数を変更しない。
- `kaname_shogi/` 以下の本体コード、公開動作、`_hand_counts` の重複、`movegen.py` の分割を変更しない。
- テストの期待値を本体実装や本体ヘルパーから生成しない。
- `_position_snapshot` はファイル内限定のテスト補助とし、局面を変更しないことを日本語docstringで説明する。
- 日本語のConventional Commitを用いる。
- 予約済みのCLIの2テーマは開始しない。

---

## ファイル構成

- 変更: `tests/test_movegen.py:334-3060` — `_position_snapshot` の追加、5つの同形
  `_snapshot` の削除、各呼び出しの置換だけを行う。
- 作成: `docs/learning/48-movegen-position-snapshot-helper.md` — 合意、実変更、
  Green-to-Green、Refactor要否、独立レビュー、検証、理解確認を記録する。
- 変更: `docs/README.md`、`docs/resume.md`、`docs/roadmap-repository-foundation.md` —
  テーマ完了後の現在状態と索引を更新する。
- 変更候補: `docs/next-topics.md` — 最後の理解確認後、本人が選定した場合だけ次テーマの
  状態を更新する。

### タスク1: 局面状態を読む補助を一つに整理する

**ファイル:**
- 変更: `tests/test_movegen.py:334-3060`
- テスト: `tests/test_movegen.py` の `LegalMoveTests`、`LegalMoveListTests`、
  `LegalMoveEnumerationTests`、`CheckmateAndGameEndTests`、`UchiFuzumeTests`

**インターフェース (Interfaces):**
- 消費 (Consumes): `Position.board.piece_at(square)`、`Position.sente_hand.count(piece_type)`、
  `Position.gote_hand.count(piece_type)`、`Position.side_to_move`。
- 生産 (Produces): `_position_snapshot(position)`。盤面81マス、先手の基本持ち駒7種、
  後手の基本持ち駒7種、手番をこの順に持つ比較用タプルを返し、`position` を変更しない。

- [ ] **ステップ1: 変更前のGreen基準を記録する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_movegen -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

期待値: 前者は158件、後者は現在の全テスト件数がともに成功する。これは既存の
正常テストを構造整理するGreen-to-Greenの変更前基準であり、故意のRedは作らない。

- [ ] **ステップ2: 共通補助を追加する**

`LegalMoveTests` の直前に、次のテスト補助を追加する。

```python
def _position_snapshot(position):
    """局面の盤面81マス・先後の基本持ち駒・手番を比較用タプルとして読む。

    盤面、先手の玉を除く基本持ち駒7種、後手の同7種、手番の順に返す。
    局面は変更しない。
    """
    squares = [Square(file, rank)
               for file in range(1, 10) for rank in range(1, 10)]
    piece_types = [piece_type for piece_type in BasicPieceType
                   if piece_type != BasicPieceType.KING]
    return (
        tuple(position.board.piece_at(square) for square in squares),
        tuple(position.sente_hand.count(piece_type)
              for piece_type in piece_types),
        tuple(position.gote_hand.count(piece_type)
              for piece_type in piece_types),
        position.side_to_move,
    )
```

- [ ] **ステップ3: 5クラスの同形補助と呼び出しを置換する**

各クラスの `_snapshot` 定義を削除する。各テストにある次の呼び出しを、同じ引数と
比較タイミングのまま `_position_snapshot(position)` に置換する。

```python
# 変更前
before = self._snapshot(position)
self.assertEqual(self._snapshot(position), before)

# 変更後
before = _position_snapshot(position)
self.assertEqual(_position_snapshot(position), before)
```

局面を作るコード、`movegen` を呼ぶコード、`assertEqual` の右辺、既存テストの
docstringは変更しない。

- [ ] **ステップ4: 構造と対象外差分を静的に確認する**

実行:

```sh
rg -n 'def _position_snapshot|def _snapshot|_position_snapshot\(' tests/test_movegen.py
git diff --check
git diff --exit-code -- kaname_shogi
git diff -- tests/test_movegen.py
```

期待値: `_position_snapshot` の定義は1件、旧 `def _snapshot` は0件、5クラスの
局面不変性確認は共通補助を直接呼ぶ。`git diff --check` と本体差分なしの検査は成功し、
最後の差分では補助の集約以外に期待値やテストメソッドを変えていないことを確認する。

- [ ] **ステップ5: 変更後のGreenを確認する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_movegen -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

期待値: 変更前と同じく対象158件と全テストが成功し、テスト総数も変わらない。

- [ ] **ステップ6: Refactor要否を判断し、独立レビューを依頼する**

新しい基底クラス、fixture、別ファイルへの分割、型注釈の追加は行わない。状態の読み取りを
一か所へ集約した時点で目的を満たすため、追加Refactorの不要性を第48回学習記録へ記録する。
その後、変更差分を読み取り専用の独立レビューへ渡し、Critical・Important・Minorを
分類する。CriticalまたはImportantがあれば、指摘を解消してステップ4と5を再実行し、
再レビューする。

- [ ] **ステップ7: テスト変更をコミットする**

```sh
git add tests/test_movegen.py
git commit -m "test: 局面スナップショット補助を一つにする"
```

期待値: テスト補助の構造整理だけを含む日本語Conventional Commitが作成される。

### タスク2: 実施記録とテーマ完了の案内を更新する

**ファイル:**
- 作成: `docs/learning/48-movegen-position-snapshot-helper.md`
- 変更: `docs/README.md`
- 変更: `docs/resume.md`
- 変更: `docs/roadmap-repository-foundation.md`
- 変更候補: `docs/next-topics.md`

**インターフェース (Interfaces):**
- 消費 (Consumes): タスク1の実際の差分、テスト結果、Refactor要否、独立レビュー結果、
  本人の理解確認の回答。
- 生産 (Produces): 第48回の学習記録と、完了状態を示す索引・再開案内・ロードマップ。

- [ ] **ステップ1: 第48回の学習記録を作成する**

記録には、目的、設計・計画へのリンク、開始時の現在Git状態、本人が合意した
対象範囲・補助名・配置・docstring・Green-to-Green・記録形式、実際の差分、
変更前後のテスト結果、静的確認、Refactor要否、独立レビューのCritical・Important・Minor、
未解決事項を記す。実施していない承認、レビュー、検証は完了扱いで書かない。

- [ ] **ステップ2: 完了時の案内文書を更新する**

`docs/README.md` のテーマ索引へ第48回、設計仕様、実装計画を追加する。
`docs/resume.md` と `docs/roadmap-repository-foundation.md` は、実際のmain取り込み、
取り込み先検証、最後の理解確認が済むまで、正しい進行状態だけを記す。
最後の理解確認後に本人が次テーマを選んだ場合だけ、`docs/next-topics.md` をその選定結果へ
更新する。

- [ ] **ステップ3: 文書検査と最終レビューを行う**

実行:

```sh
git diff --check
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

更新したMarkdownの相対リンクを検査し、全テストと書式検査が成功することを確認する。
文書差分も含めて独立レビューを行い、CriticalまたはImportantがあれば修正、再検証、
再レビューする。

- [ ] **ステップ4: 記録をコミットし、main取り込みの承認を待つ**

```sh
git add docs
git commit -m "docs: 局面スナップショット補助整理を記録する"
```

期待値: 実施済みの事実だけを含む記録コミットが作成される。mainへの取り込みは、
テーマの実装、検証、レビュー、記録がそろった後に本人の明示承認を受けてから行う。

## 計画の自己レビュー

- [x] 仕様の対象5クラス、共通化する値、対象外、docstring、意図の保持、Green-to-Green、
  記録、承認ゲートのすべてに対応するタスクがある。
- [x] `TBD`、`TODO`、未記入の手順を含まない。
- [x] `_position_snapshot(position)` の名前、引数、戻り値の順序をタスク全体で統一した。
- [x] 記載した`unittest`、`rg`、`git diff`、`git add`、`git commit`のコマンドは、
  リポジトリ直下で実行する。

## 実行前の承認ゲート

この計画を日本語のConventional Commitで記録した後、本人へ計画内容を提示する。
本人の明示的な承認を受けるまで、`tests/test_movegen.py`、既存文書、本体コードを
変更しない。承認後にだけ、タスク1の変更前Green基準確認から開始する。
