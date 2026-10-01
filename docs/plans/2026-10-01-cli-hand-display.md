# 対局中の持ち駒表示 実装計画

> **AIエージェントへの指示:** この計画をタスクごとに実装するには、`executing-plans` スキルを起動して使用してください。ステップには追跡用チェックボックスを使います。

**目標:** 既存の局面文字列に先手・後手双方の持ち駒を表示する。

**アーキテクチャ:** `render_position(position)` が既存の `Position.sente_hand` と `Position.gote_hand` を読み、先手視点の盤の上に後手、下に先手の持ち駒欄を加える。表示処理は `kaname_shogi/display.py` 内に閉じ、公開API、モデル、CLI進行処理は変更しない。

**技術スタック:** Python 3.9.6、標準ライブラリ `unittest`。

**仕様 (Spec):** [対局中の持ち駒表示 設計仕様](2026-10-01-cli-hand-display-design.md)

**グローバル制約 (Global Constraints):**
- 説明・学習記録・知識メモは日本語で書く。
- テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞い、続く本文に検出したい誤りや背景を書く。
- 表示関数は局面を変更せず、標準出力、色付け、入力操作も行わない。
- 入力文法、将棋規則、持ち駒の保持・更新モデル、保存形式、既存公開APIのシグネチャを変更しない。
- SFEN、USI、評価関数、探索、`_hand_counts` の重複整理を扱わない。

## レビューフォーカス

- 先後の持ち駒が逆の欄に出る局面でも、各 `Hand` が正しい側のラベルに表示されること。双方に異なる駒を持たせるテストで確認する。
- 複数の駒種を持つ局面でも、歩・香・桂・銀・金・角・飛の順序が保たれること。順序を逆転させて追加したテストデータで確認する。
- 枚数1と複数枚が正しく区別されること。1枚・2枚・3枚を含む出力を確認する。
- 双方が0枚の局面で空欄や誤った駒が出ず、「なし」と表示されること。初期局面と空の局面で確認する。
- 表示だけで局面の持ち駒が変化しないこと。表示前後の `Hand.count()` を比較する。

---

## ファイル構成

- 変更: `kaname_shogi/display.py` — `Hand` と `BasicPieceType` を読み、局面表示へ双方の持ち駒欄を追加する。
- 変更: `tests/test_display.py` — 全文期待値と持ち駒表示の振る舞いテストを追加する。
- 変更: `docs/learning/52-cli-hand-display.md` — 完了後、学習・合意・TDD・レビュー・検証・振り返りを事実に基づいて記録する。
- 作成: `docs/knowledge/16-cli-hand-display.md` — 確定した持ち駒表示の並び、空欄、枚数表記を参照メモにする。
- 変更: `docs/README.md` — 完了した学習回、知識メモ、仕様、実装計画への索引を加える。

## タスク1: 局面表示に持ち駒を追加する

**ファイル:**
- 変更: `tests/test_display.py`
- 変更: `kaname_shogi/display.py`

**インターフェース:**
- 消費: `Position.sente_hand` / `Position.gote_hand` は `Hand`、`Hand.count(piece_type: BasicPieceType) -> int` は枚数読み取り操作。
- 生産: 公開 `render_position(position: Position) -> str` は既存シグネチャのまま、双方の持ち駒欄を含む局面表示を返す。新しい公開APIは追加しない。

- [ ] **ステップ1: 失敗する表示テストを書く**

  `tests/test_display.py` の `EXPECTED` に、盤の前の `後手の持ち駒：なし` と盤の後の `先手の持ち駒：なし` を加える。次のテストを追加する。

  - `test_renders_sente_and_gote_hands_in_fixed_piece_order`: 先手に歩1・香2・金3・飛1、後手に桂2・銀1・角3を `Hand.add()` で設定し、各側の行がそれぞれ `先手の持ち駒：歩1、香2、金3、飛1` と `後手の持ち駒：桂2、銀1、角3` になることを確認する。テストデータは表示順と異なる順で追加する。
  - `test_renders_empty_hands_as_none`: 双方が0枚のとき両欄が `なし` となることを確認する。
  - `test_rendering_hands_does_not_change_position`: 表示前後で両 `Hand` の7駒種の枚数が変わらないことを確認する。

  テストメソッドには英語名と日本語docstringを付ける。モデル内部の `_counts` は参照しない。

- [ ] **ステップ2: 表示テストが仕様に沿って失敗することを確認する**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_display.py' -v`

  期待値: 新しい持ち駒の期待値に対し、現行 `render_position` が欄を出力しないため対象テストが失敗する。読み込みエラーや構文エラーではなく、持ち駒行の欠落による失敗であることを確認する。

- [ ] **ステップ3: `kaname_shogi/display.py` に持ち駒の整形を実装する**

  `BasicPieceType` と `Hand` をインポートし、歩・香・桂・銀・金・角・飛の固定順と日本語名を使って `Hand.count()` を読む。内部専用の `_render_hand(hand: Hand, side_label: str) -> str` で、0枚を `なし`、所持駒を枚数付きの `駒種枚数` として列挙する。`render_position` は後手欄を盤の直前、先手欄を盤の直後に加える。盤面・手番の既存順序と局面非変更を維持する。

- [ ] **ステップ4: 表示テストが成功することを確認する**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_display.py' -v`

  期待値: 表示テスト全件が成功し、初期局面の全文、双方のラベル・順序・枚数・0枚表記、局面非変更が確認できる。

- [ ] **ステップ5: Refactorの要否を確認する**

  表示処理に不要な抽象化や重複がないか、公開APIやモデルへ責務が漏れていないか確認する。不要ならその判断を学習記録へ残す。必要な修正があれば表示テストを再実行する。

## タスク2: 全体検証と独立レビューを行う

**ファイル:**
- 読み取り: `kaname_shogi/display.py`
- 読み取り: `tests/test_display.py`

**インターフェース:** タスク1で追加した `render_position(position: Position) -> str` とテストをレビュー対象にする。

- [ ] **ステップ1: 全 `unittest` を実行する**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`

  期待値: 既存機能を含む全テストが成功する。

- [ ] **ステップ2: CLIを起動して対局中の表示を手動確認する**

  実行: `python3 -m kaname_shogi`

  対局形式に人間対人間を選び、初期局面で盤上側に後手、盤下側に先手の「なし」が表示されることを確認する。続けて次の入力を行い、駒を取った後に先手の持ち駒表示が更新されることを確認してから `resign` で終了する。

  ```text
  1
  move 7 7 7 6
  move 7 3 7 4
  move 7 6 7 5
  move 3 3 3 4
  move 7 5 7 4
  resign
  ```

- [ ] **ステップ3: 差分形式を確認する**

  実行: `git diff --check`

  期待値: 空白エラーが報告されない。

- [ ] **ステップ4: 独立したコードレビューを受ける**

  実装差分について、設計仕様との整合、表示順と駒数、既存API・モデル・CLI境界、テスト品質をレビューし、Critical・Important・Minorの件数と対応を記録する。CriticalまたはImportantがあれば解消し、対象テスト・全テストを再実行してから再レビューする。

- [ ] **ステップ5: レビュー済みコードをコミットする**

  Critical・Importantの指摘が残っていないことを確認してから、日本語Conventional Commitで実装とテストを記録する。

  ```bash
  git add kaname_shogi/display.py tests/test_display.py
  git commit -m "feat: 対局中に双方の持ち駒を表示する"
  ```

## タスク3: 学習・知識・文書索引を完成する

**ファイル:**
- 作成: `docs/learning/52-cli-hand-display.md`
- 作成: `docs/knowledge/16-cli-hand-display.md`
- 変更: `docs/README.md`

**インターフェース:** 記録はタスク1の実際の差分とタスク2の実測結果だけを記載する。

- [ ] **ステップ1: 第52回学習記録を作成する**

  目的、一次資料、設計合意、本人の回答、TDDのRed/Green、変更内容、Refactor判断、独立レビュー結果、検証結果、未解決事項、振り返り、最後の理解確認問題を記録する。回答待ちの質問や未実施の操作を完了扱いにしない。

- [ ] **ステップ2: 確定した表示知識メモを作成する**

  表示側（後手が上・先手が下）、固定駒種順、0枚の `なし`、枚数の明記、表示責務と出典を簡潔に記録する。

- [ ] **ステップ3: 文書索引を更新する**

  `docs/README.md` に第52回の学習記録・知識メモ・設計仕様・実装計画を索引する。

- [ ] **ステップ4: 文書とリポジトリ状態を確認してコミットする**

  実行: `git diff --check`

  全ての新しい相対Markdownリンクが存在することと、学習記録が実際の実施内容・検証報告に一致することを確認してから、日本語Conventional Commitで記録をコミットする。

## 完了条件

- 設計仕様の双方の持ち駒表示を実装し、全テストが成功している。
- CLIを起動した手動確認で、初期局面と駒取り後の表示を確認している。
- Critical・Importantのレビュー指摘が残っていない。
- 第52回学習記録、知識メモ、文書索引、プロジェクト方向を更新している。
- 作業ブランチと元の作業ディレクトリでの取り込み状態を確認し、必要な取り込み承認を得る。
- 取り込み先で検証後、最後の理解確認を一問だけ出して回答を待つ。
- 回答と補足を学習記録へ追記してから、`docs/next-topics.md`、`README.md`、`docs/02-project-direction.md` を見直し、次の候補を示す。
