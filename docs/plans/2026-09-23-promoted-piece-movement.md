# 成駒の移動 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 6種類の成駒の候補を計算し、既存の `apply_move` で成駒を移動・取得できるようにする。

**アーキテクチャ:** 金相当の4成駒は、駒種検証を行う公開関数と共通の非公開候補計算を分ける。馬・竜は既存の角・飛車の長い移動に、追加の1マス候補を組み合わせる。候補の振り分け表を拡張し、既存の局面適用を再利用する。

**技術スタック:** Python 3.9.6、標準ライブラリ `unittest`、Git。

**仕様 (Spec):** `docs/plans/2026-09-23-promoted-piece-movement-design.md`

**グローバル制約 (Global Constraints):**
- 説明・学習記録・知識メモは日本語で書く。
- 公開インターフェースのdocstringに引数・戻り値・副作用・前提条件と設計理由を記録する。
- テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞いを書く。
- 候補生成は盤面・手番・持ち駒を変更せず、王手を考慮した合法手の確定ではない。
- 王手・詰み・合法手、打ち歩詰め、成り直し、CLI入力、履歴、評価、探索を実装しない。
- 実装はRed → Green → Refactorの順に行い、振る舞いごとにRedの失敗理由を確認する。

---

## ファイル構成

- `tests/test_movegen.py`: 成駒候補と局面移動の振る舞いを固定する。
- `kaname_shogi/movegen.py`: 候補関数、共通処理、`apply_move`の振り分けを実装する。
- `docs/learning/30-promoted-piece-movement.md`: 学習・TDD・レビュー・検証を記録する。
- `docs/knowledge/23-promoted-piece-movement.md`: 規則と表現の参照メモを記録する。
- `README.md`、`docs/next-topics.md`、`docs/resume.md`: 到達点と次の候補を更新する。

### タスク1: 金相当の4成駒の候補生成

**ファイル:** `tests/test_movegen.py`、`kaname_shogi/movegen.py`

**生産する公開操作:**

```python
def pro_pawn_move_candidates(board: Board, source: Square) -> list[Square]: ...
def pro_lance_move_candidates(board: Board, source: Square) -> list[Square]: ...
def pro_knight_move_candidates(board: Board, source: Square) -> list[Square]: ...
def pro_silver_move_candidates(board: Board, source: Square) -> list[Square]: ...
```

- [ ] 先後の各成駒を5五へ置き、金と同じ6候補、相手駒を含むこと、自駒・盤外を除くこと、盤面不変性を確認する失敗テストを追加する。
- [ ] `python3 -m unittest tests.test_movegen.PromotedMinorMoveCandidateTests -v` を実行し、未実装関数による `ImportError` または `AttributeError` のRedを確認する。
- [ ] 駒種検証後に金と同じ方向を返す非公開操作を追加し、各公開関数が委譲する最小実装と日本語docstringを追加する。
- [ ] 同じコマンドを実行し、追加したテストがPASSすることを確認する。
- [ ] `git add kaname_shogi/movegen.py tests/test_movegen.py && git commit -m "feat: add gold-like promoted move candidates"` を実行する。

### タスク2: 馬・竜の候補生成

**ファイル:** `tests/test_movegen.py`、`kaname_shogi/movegen.py`

**生産する公開操作:**

```python
def horse_move_candidates(board: Board, source: Square) -> list[Square]: ...
def dragon_move_candidates(board: Board, source: Square) -> list[Square]: ...
```

- [ ] 馬の斜め長距離＋縦横1マス、竜の縦横長距離＋斜め1マスについて、遮蔽、自駒・相手駒、盤端、盤面不変性を確認する失敗テストを追加する。
- [ ] `python3 -m unittest tests.test_movegen.HorseMoveCandidateTests tests.test_movegen.DragonMoveCandidateTests -v` を実行し、関数未実装によるRedを確認する。
- [ ] 既存の角・飛車と同じ停止規則で長い移動を追加し、馬は上・右・下・左、竜は右上・左上・右下・左下の1マスを追加する。
- [ ] 同じコマンドを実行し、追加したテストがPASSすることを確認する。
- [ ] `git add kaname_shogi/movegen.py tests/test_movegen.py && git commit -m "feat: add horse and dragon move candidates"` を実行する。

### タスク3: 成駒の局面移動

**ファイル:** `tests/test_movegen.py` の`ApplyMoveTests`、`kaname_shogi/movegen.py`

**消費する操作:** タスク1・2の6候補関数と `apply_move(position, source, destination, *, promote=False) -> None`。

- [ ] 「成駒を拒否する」既存テストを、6成駒が候補内の空マスへ同じ駒種のまま移動し手番を交代する失敗テストへ置換する。成駒が未成駒・成駒を取る場合、取得駒が基本駒種として持ち駒に加わることと、候補外・相手玉・`promote=True`では局面不変であることも追加する。
- [ ] `python3 -m unittest tests.test_movegen.ApplyMoveTests -v` を実行し、候補表に成駒がないため正常移動が `ValueError` となる振る舞い上のRedを確認する。
- [ ] `_move_candidates_for_piece` の対応表へ6成駒を追加し、`apply_move`の成駒一律拒否だけを外す。`promote=True`は既存の `_can_promote` により引き続き拒否する。
- [ ] 同じコマンドを実行し、成駒移動・取得・不変性を含むテストがPASSすることを確認する。
- [ ] 重複が公開関数の規則を読みにくくしていないかRefactorの要否を確認し、必要なら非公開の1マス候補操作だけを抽出して再テストする。
- [ ] `git add kaname_shogi/movegen.py tests/test_movegen.py && git commit -m "feat: allow promoted piece moves"` を実行する。

### タスク4: 統合検証・記録・独立レビュー

**ファイル:** `docs/learning/30-promoted-piece-movement.md`、`docs/knowledge/23-promoted-piece-movement.md`、`README.md`、`docs/next-topics.md`、`docs/resume.md`

- [ ] `python3 -m unittest discover -s tests -v`、`python3 -m kaname_shogi`、`git diff --check` を実行し、全テスト成功・CLI正常終了・差分検査無出力を確認する。
- [ ] `requesting-code-review` スキルを起動して独立レビューを行い、Critical・Important・Minorと対応を決める。CriticalまたはImportantなら修正、再検証、再レビューを行う。
- [ ] 第1〜6問の本人の回答と補足、一次資料、設計合意、実際のRed/Green/Refactor、レビュー、検証を学習記録へ記す。知識メモには6成駒の動きと`apply_move`接続だけを記す。
- [ ] README・次候補・再開案内を実装済み状態へ更新し、記録を確認後にコミットする。
- [ ] `git status --short --branch` と `git log --oneline main..HEAD` で取り込み対象を確認し、本人の承認までmainへ取り込まない。
