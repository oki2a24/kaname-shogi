# 打ち歩詰め 実装計画

> **AIエージェントへの指示:** 実装前に `test-driven-development` を用い、振る舞いごとに Red を確認してから最小実装する。Green後はRefactorの要否を確認し、独立レビューと全検証を行う。

**目標:** `apply_drop` が、持ち歩で解除不能な王手をかける手を局面不変のまま拒否する。

**アーキテクチャ:** 公開APIは変えず、`movegen.py` の非公開操作に打ち歩詰め確認の有効・無効を閉じ込める。公開の駒打ちと合法手探索は有効、持ち歩試し打ち後の相手応手探索は無効にし、`apply_drop → is_checkmate → has_legal_move → apply_drop` の循環を断つ。

**技術スタック:** Python 3.9、標準ライブラリ `unittest`、Git。

**仕様 (Spec):** `docs/plans/2026-09-23-uchi-fuzume-design.md`

**グローバル制約 (Global Constraints):**

- 説明・学習記録・知識メモは日本語で書く。
- 公開インターフェースのdocstringには、引数・戻り値・副作用・前提条件と設計理由を記録する。
- テストメソッド名は英語とし、日本語docstringで振る舞いと検出したい誤りを説明する。
- 読み込みエラーではないRed、最小実装、Green、Refactor確認、独立レビューを順に行う。
- CriticalまたはImportantのレビュー指摘は、解消・再検証・再レビュー後に文書化する。
- コミットメッセージは日本語のConventional Commit形式にする。

---

## ファイル構成

- `kaname_shogi/movegen.py`: 非公開の駒打ち・合法手・詰み判定経路を追加し、公開操作を委譲する。
- `tests/test_movegen.py`: 打ち歩詰め、打ち不詰、対象外、玉なし、公開判定との接続をテストする。
- `README.md`: 実装済み規則の説明を更新する。
- `docs/knowledge/26-uchi-fuzume.md`: 一次資料、接続、対象外を記録する。
- `docs/learning/33-uchi-fuzume.md`: 設計、実施、レビュー、検証、理解確認を事実に基づき記録する。

### タスク1: 打ち歩詰めと、打ち歩詰めにならない歩打ちをRedで固定する

**ファイル:** `tests/test_movegen.py` に `UchiFuzumeTests` を追加する。

**消費:** `apply_drop(position, piece_type, destination) -> None`

**生産:** 歩打ちの受理・拒否を固定するテスト。

- [ ] 両玉を持つ「持ち歩を打つと詰む」局面ヘルパーを追加する。
- [ ] `test_rejects_pawn_drop_that_gives_unavoidable_check` を追加する。先手・後手を `subTest` で両方試し、先手は段が減る向き、後手は段が増える向きの歩打ちで `ValueError` と81マス・双方の持ち駒・手番の不変性を確認する。
- [ ] `python3 -m unittest tests.test_movegen.UchiFuzumeTests.test_rejects_pawn_drop_that_gives_unavoidable_check -v` を実行し、未実装により `ValueError not raised` となるRedを確認する。
- [ ] `test_allows_pawn_drop_when_king_can_capture_the_pawn` を追加する。後手玉が５一、先手玉が９九、先手が５二へ歩を打ち、後手玉が歩を取れる局面を使う。
- [ ] `test_allows_pawn_drop_without_check` を追加する。持ち歩を打っても相手玉を利かせない局面が受理されることを確認する。
- [ ] `test_allows_pawn_drop_when_king_can_escape` を追加する。後手番の局面を使い、玉が打った歩を取れなくても安全な逃げ先を持つ歩打ちが受理されることを確認する。
- [ ] `python3 -m unittest tests.test_movegen.UchiFuzumeTests -v` を実行し、打ち歩詰めにならない三種類の歩打ちは成功、打ち歩詰めの拒否だけが失敗することを確認する。

### タスク2: 循環しない内部経路を最小実装する

**ファイル:** `kaname_shogi/movegen.py`

**消費:** `_apply_drop_unchecked`、`_apply_if_king_safe`、既存の `apply_drop`、`has_legal_move`、`is_checkmate`。

**生産:** `_apply_drop(..., check_uchi_fuzume: bool)`、`_has_legal_move(..., check_uchi_fuzume: bool)`、`_is_checkmate(..., check_uchi_fuzume: bool)`。

- [ ] 非公開3操作を追加し、公開 `apply_drop`、`has_legal_move`、`is_checkmate` は既存シグネチャのまま有効設定で委譲する。
- [ ] `_apply_drop` は既存の自玉安全確認後、持ち歩かつ有効設定の場合だけ、試し局面で無効設定の `_is_checkmate` を呼ぶ。真なら `ValueError("打ち歩詰めはできません")`、偽なら本物を一度だけ適用する。
- [ ] `_is_checkmate` は既存の玉なし・非王手を `False` に保って `_has_legal_move` を呼ぶ。`_has_legal_move` の駒打ち候補は渡された設定をそのまま `_apply_drop` へ渡し、応手探索で打ち歩詰め確認を再開しない。
- [ ] 相手側が持ち歩を持つ局面で、打ち歩詰め確認用の `_has_legal_move(..., check_uchi_fuzume=False)` が駒打ち候補へ同じ `False` を渡すことを、`unittest.mock.patch` で `_apply_drop` の呼出し引数を記録して確認する。このテストは局面規則の代替ではなく、再入を断つ内部接続だけを固定する。
- [ ] `python3 -m unittest tests.test_movegen.UchiFuzumeTests -v` を実行してGreenを確認する。
- [ ] 既存の安全確認・未検証適用を重複させず、内部設定を公開APIへ漏らしていないかRefactor要否を確認する。
- [ ] `git add kaname_shogi/movegen.py tests/test_movegen.py` と `git commit -m "feat: 打ち歩詰めを拒否する"` を実行する。

### タスク3: 境界条件と公開判定の接続をTDDで確認する

**ファイル:** `tests/test_movegen.py`

**消費:** `apply_move`、`apply_drop`、`has_legal_move`、`is_checkmate`。

**生産:** 対象外・玉なし・合法手の契約。

- [ ] `test_allows_non_pawn_drop_that_gives_checkmate`、`test_allows_board_pawn_move_that_gives_checkmate`、`test_allows_pawn_drop_in_kingless_partial_position` を追加する。それぞれ日本語docstringで防ぐ誤りを記す。
- [ ] `test_does_not_count_pawn_drop_mate_as_legal_move` を追加する。局面ヘルパーの契約を「手番側は持ち歩を打つ以外の盤上移動・成り・別種類の駒打ちをできず、その歩打ちだけが打ち歩詰めとなる」と明記し、`has_legal_move` が `False` となることを確認する。
- [ ] 対象テストを一つずつ実行し、各Redが振る舞いのアサーション失敗であることを確認する。
- [ ] 歩だけの限定、玉なしの `False`、公開合法手探索の有効設定に不足があれば最小補正する。
- [ ] `python3 -m unittest tests.test_movegen.UchiFuzumeTests -v` を実行し、全Greenを確認する。
- [ ] Refactor要否を確認し、`git add kaname_shogi/movegen.py tests/test_movegen.py` と `git commit -m "test: 打ち歩詰めの境界条件を追加する"` を実行する。

### タスク4: 独立レビュー、全検証、文書化、取り込み準備

**ファイル:** `README.md`、`docs/knowledge/26-uchi-fuzume.md`、`docs/learning/33-uchi-fuzume.md`

- [ ] 設計仕様・実装差分・テストを照合する独立レビューを実施し、Critical・Important・Minorと対応を学習記録へ記す。CriticalまたはImportantがあれば、先に修正・再検証・再レビューする。
- [ ] READMEから「打ち歩詰め未実装」を除き、持ち歩だけを拒否する規則を記す。知識メモに一次資料、3操作の関係、循環回避、玉なし、対象外を記す。学習記録にRed/Green/Refactor、レビュー、検証を事実どおり記す。
- [ ] `python3 -m unittest discover -s tests -v`、`python3 -m kaname_shogi`、`git diff --check` を実行する。全テスト成功、CLI起動、差分チェック出力なしを確認する。
- [ ] `git add README.md docs/knowledge/26-uchi-fuzume.md docs/learning/33-uchi-fuzume.md` と `git commit -m "docs: 打ち歩詰めの学習記録を追加する"` を実行する。
- [ ] 作業ブランチ、レビュー結論、検証結果、未追跡ファイルを報告し、本人の承認まで `main` へ取り込まない。

## 計画の自己レビュー

- 設計仕様の対象範囲、三つの公開操作、循環回避、玉なしを各タスクへ対応付けた。
- Redは全て振る舞いのアサーション失敗を確認する手順である。
- Green、Refactor、独立レビュー、全検証、文書化、main取り込み承認を含めた。
- 変更ファイル、非公開インターフェース、コマンド、コミットメッセージを具体化した。
- TBD、TODO、未決定のプレースホルダは残していない。

## 実施状況

- タスク1〜3（Red、最小実装、Green、Refactor確認、境界条件テスト）を完了した。
- タスク4の独立レビュー、文書化、全検証を完了した。最終レビューの指摘はCritical・Important・Minorとも0件だった。
- 作業ブランチは `codex/uchi-fuzume`。`main` への取り込みは本人の選択を待っている。
