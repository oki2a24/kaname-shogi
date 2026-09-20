# 玉の移動先候補 実装計画

> **AIエージェントへの指示:** この計画を実装する際は、タスクごとに`executing-plans`または`subagent-driven-development`スキルを起動して使用する。各ステップのチェックボックスで進捗を記録する。

**目標:** 玉の周囲8方向への移動先候補を、盤外・自駒を除外し、相手駒を含めて返す関数として追加する。

**アーキテクチャ:** `movegen.py`に玉専用の`king_move_candidates`を追加する。8方向を固定順で直接調べ、既存の駒関数との先行共通化は行わない。テストは`tests/test_movegen.py`の既存パターンに追加し、候補生成が盤面を変更しないことも確認する。

**技術スタック:** Python標準ライブラリ、`unittest`、既存の`Board`・`Piece`・`PieceType`・`Side`・`Square`。

**仕様 (Spec):** `docs/design/09-king-move-candidates.md`

**グローバル制約 (Global Constraints):**
- 説明・学習記録・知識メモは日本語で書く。
- テストメソッド名は英語とし、日本語docstringで確認する振る舞いと背景を書く。
- 座標は将棋の筋・段を基本とする。
- 実装は候補生成に限定し、王手・合法手判定・実際の移動・駒取り・持ち駒・成りを扱わない。
- 実装時は対象の振る舞いごとにRed → Green → Refactorで進める。

---

### タスク1: 玉の候補契約をテストで固定する

**ファイル:**
- 変更: `tests/test_movegen.py`
- 参照: `kaname_shogi/model.py`、`kaname_shogi/movegen.py`

**インターフェース:**
- 消費: `Board.set_piece(square, Piece(...))`、`Square(file, rank)`、`PieceType.KING`。
- 生産: `king_move_candidates(board, source)`が満たす期待値をテストで定義する。

- [ ] **ステップ1: 失敗するテストを作成**

  `KingMoveCandidatesTests`を追加し、次の振る舞いをテストする。

  - 空マスと玉以外の駒を`ValueError`として拒否する。
  - ５五の先手・後手の玉が、固定順 `[５四, ６四, ６五, ６六, ５六, ４六, ４五, ４四]`を返す。
  - １一では盤内の`[２一, ２二, １二]`だけを返す。
  - 自駒の到着先を除外し、相手駒の到着先を含める。
  - 候補計算後も81マスの内容が変わらず、`Position.side_to_move`にも依存しない。
  - 呼び出しごとに独立したリストを返す。

  テストメソッドは既存の英語命名規則に従い、日本語docstringで誤りの背景を説明する。

- [ ] **ステップ2: 対象テストが失敗することを確認**

  実行:

  ```sh
  python3 -m unittest tests.test_movegen.KingMoveCandidatesTests -v
  ```

  期待値: `movegen`に`king_move_candidates`がまだないため、テストのimportで失敗する。

- [ ] **ステップ3: テストの差分を確認してコミット**

  `git diff --check`を実行し、テストだけをコミットする。

  ```sh
  git add tests/test_movegen.py
  git commit -m "test: 玉候補の契約を追加"
  ```

### タスク2: 玉の候補生成を最小実装する

**ファイル:**
- 変更: `kaname_shogi/movegen.py`

**インターフェース:**
- 消費: `Board.piece_at(source)`、`PieceType.KING`、`Piece.side`。
- 生産: `king_move_candidates(board: Board, source: Square) -> list[Square]`。

- [ ] **ステップ1: 入力検証を追加**

  `source`の駒を取得し、空または`PieceType.KING`以外なら、既存関数と同じく`ValueError("出発マスには玉を指定してください")`を送出する。

- [ ] **ステップ2: 固定順の8方向を直接計算**

  次のオフセットをこの順で使用する。

  ```python
  offsets = ((0, -1), (-1, -1), (-1, 0), (-1, 1),
             (0, 1), (1, 1), (1, 0), (1, -1))
  ```

  各到着先について筋・段が`1 <= value <= 9`か確認し、盤内だけを`Square`にする。到着先の駒が自駒なら除外し、空または相手駒なら候補へ追加する。盤面への書き込みは行わない。

- [ ] **ステップ3: docstringを追加**

  引数、戻り値、`ValueError`、固定順、盤外・自駒・相手駒の扱い、盤面不変性、手番非依存、王手・合法手判定が対象外であることを日本語で記録する。`KING`は玉を表す駒種のデータ、`king_move_candidates`は候補を求める操作であることも記載する。

- [ ] **ステップ4: 玉のテストがGreenになることを確認**

  ```sh
  python3 -m unittest tests.test_movegen.KingMoveCandidatesTests -v
  ```

  期待値: 玉の全テストが成功する。

- [ ] **ステップ5: 実装をコミット**

  ```sh
  git diff --check
  git add kaname_shogi/movegen.py
  git commit -m "feat: 玉の移動先候補を追加"
  ```

### タスク3: 全体検証と文書更新

**ファイル:**
- 変更: `README.md`
- 変更: `docs/resume.md`
- 変更: `docs/learning/20-king-move-candidates.md`

**インターフェース:**
- 消費: `king_move_candidates`の確定した公開契約と、全テストの結果。
- 生産: 利用例、到達点、検証結果、未解決事項を反映した日本語文書。

- [ ] **ステップ1: READMEに玉を追記**

  現在の実装一覧、テスト説明、`king_move_candidates`の短い使用例、固定順、相手駒・盤面不変性、王手・合法手判定が対象外であることを既存の文体で追記する。

- [ ] **ステップ2: 学習記録と再開案内を事後結果で更新**

  学習記録の振り返りは本人の回答が得られた内容だけを記録し、実装後の検証結果を未実施の内容と混同しない。`docs/resume.md`には実装・レビュー・理解確認の完了状況と次のテーマを追記する。

- [ ] **ステップ3: 全検証を実行**

  ```sh
  python3 -m unittest discover -s tests -v
  python3 -m kaname_shogi
  git diff --check
  ```

  期待値: 全テスト成功、CLIが初期配置と先手表示で正常終了、差分検査成功。

- [ ] **ステップ4: 差分レビューとコミット**

  玉の範囲外（王手、合法手判定、実際の移動、成り）が混入していないこと、公開docstringとREADMEが実装と一致することを確認する。

  ```sh
  git status --short --branch
  git diff --check
  git add README.md docs/resume.md docs/learning/20-king-move-candidates.md
  git commit -m "docs: 玉候補の実装結果を記録"
  ```
