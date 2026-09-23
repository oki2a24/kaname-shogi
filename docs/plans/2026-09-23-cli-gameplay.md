# CLIでの指し手入力と対局進行 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 筋・段の文字列入力から既存の合法手を局面へ適用し、エラー時の再入力と詰みによるCLI停止を行う。

**アーキテクチャ:** `cli.py` に入力解析と対局進行を置き、`__main__.py` は起動だけを担う。`cli.py` は解析した移動を既存の `apply_move` / `apply_drop` へ一度だけ渡し、合法性を重複実装しない。`render_position` は成駒6種を表示できるようにして、成り後も同じ表示経路を使う。

**技術スタック:** Python 3.9、標準ライブラリ `dataclasses`・`typing`・`unittest`、Git。

**仕様 (Spec):** `docs/plans/2026-09-23-cli-gameplay-design.md`

**グローバル制約 (Global Constraints):**

- 説明・学習記録・知識メモは日本語で書く。
- 公開インターフェースのdocstringには、引数・戻り値・副作用・前提条件と設計理由を記録する。
- テストメソッド名は英語とし、日本語docstringで振る舞いと検出したい誤りを説明する。
- 読み込みエラーではないRed、最小実装、Green、Refactor確認、独立レビューを順に行う。
- CriticalまたはImportantのレビュー指摘は、解消・再検証・再レビュー後に文書化する。
- コミットメッセージは日本語のConventional Commit形式にする。
- `move` / `drop` と `+` は半角ASCIIだけを受け付ける。区切りは半角・全角スペース、筋段は半角・全角数字を受け付ける。
- `ValueError` による形式・合法性エラーは局面を変えず、同じ手番で再入力する。終局は詰みだけ、EOF/Ctrl-Cは勝敗にせず正常終了する。

---

## ファイル構成

- 作成 `kaname_shogi/cli.py`: 文字列を内部の移動・駒打ち指示へ変換し、表示・入力・適用・停止を進行する。
- 変更 `kaname_shogi/__main__.py`: `run_game()` を起動するだけにする。
- 変更 `kaname_shogi/display.py`: 成駒6種の表示名を追加する。
- 作成 `tests/test_cli.py`: 解析、進行、再入力、詰み停止、EOF/Ctrl-Cを単体テストする。
- 変更 `tests/test_display.py`: 成駒表示と、EOFで終了する実CLIの出力を検証する。
- 変更 `README.md`: 実行方法と入力形式、今回の終局・対象外を更新する。
- 作成 `docs/knowledge/27-cli-gameplay.md`: 確定した入力・進行・規則との関係を参照メモにする。
- 作成 `docs/learning/34-cli-gameplay.md`: 質問回答、設計、Red/Green、レビュー、検証、最後の理解確認を事実に基づき記録する。

## タスク1: 入力解析のRedを固定する

**ファイル:**
- 作成: `tests/test_cli.py`

**インターフェース:**
- 消費: `BasicPieceType`、`Square`
- 生産: `parse_command(text: str) -> _MoveCommand | _DropCommand`

- [x] **ステップ1: 解析用の失敗するテストを作成する**

  `tests/test_cli.py` に `CommandParsingTests` を追加する。移動、成り、駒打ちを比較できる
  よう、返り値の属性（`source`、`destination`、`promote`、`piece_type`）を読む。

  ```python
  def test_parses_move_and_drop_with_halfwidth_or_fullwidth_input(self):
      """半角・全角の座標と空白を、移動・駒打ちの指示へ変換する。"""
      move = cli.parse_command("move　７　７　７　６")
      promoted = cli.parse_command("move 2 2 2 1 +")
      drop = cli.parse_command("drop　歩　５　５")

      self.assertEqual((move.source, move.destination, move.promote),
                       (Square(7, 7), Square(7, 6), False))
      self.assertEqual((promoted.source, promoted.destination,
                        promoted.promote),
                       (Square(2, 2), Square(2, 1), True))
      self.assertEqual((drop.piece_type, drop.destination),
                       (BasicPieceType.PAWN, Square(5, 5)))
  ```

  空行、`ｍｏｖｅ 7 7 7 6`、`move 7 7 7 6 ＋`、未知の駒名、引数の過不足、盤外座標が
  `ValueError("入力形式が正しくありません。")` になるパラメタ化テストも追加する。

- [x] **ステップ2: Redを確認する**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.CommandParsingTests -v`

  期待値: テスト作成後、`cli.py` には `parse_command` が常に `None` を返すだけの最小の
  仮実装を置いて読み込みを通す。続けて同じコマンドを実行し、`None` に `source` がないという
  アサーション経路の失敗を確認する。モジュール未作成による読み込みエラーだけではRed完了としない。

- [x] **ステップ3: 最小の解析実装を追加する**

  `kaname_shogi/cli.py` に、内部の凍結dataclass `_MoveCommand` と `_DropCommand`、
  公開 `parse_command` を追加する。`text.split()` で半角・全角スペースを区切り、`int()`
  で半角・全角数字を読む。すべての形式失敗を同じ利用者向けメッセージへ正規化する。

  ```python
  @dataclass(frozen=True)
  class _MoveCommand:
      source: Square
      destination: Square
      promote: bool


  def parse_command(text: str) -> Union[_MoveCommand, _DropCommand]:
      parts = text.split()
      if parts[:1] == ["move"] and len(parts) in (5, 6):
          if len(parts) == 6 and parts[5] != "+":
              raise ValueError("入力形式が正しくありません。")
          try:
              return _MoveCommand(Square(int(parts[1]), int(parts[2])),
                                  Square(int(parts[3]), int(parts[4])),
                                  len(parts) == 6)
          except ValueError as error:
              raise ValueError("入力形式が正しくありません。") from error
      piece_types = {"歩": BasicPieceType.PAWN,
                     "香": BasicPieceType.LANCE,
                     "桂": BasicPieceType.KNIGHT,
                     "銀": BasicPieceType.SILVER,
                     "金": BasicPieceType.GOLD,
                     "角": BasicPieceType.BISHOP,
                     "飛": BasicPieceType.ROOK}
      if parts[:1] == ["drop"] and len(parts) == 4:
          try:
              return _DropCommand(piece_types[parts[1]],
                                  Square(int(parts[2]), int(parts[3])))
          except (KeyError, ValueError) as error:
              raise ValueError("入力形式が正しくありません。") from error
      raise ValueError("入力形式が正しくありません。")
  ```

  `parse_command` のdocstringに、引数、返り値、局面を変更しない副作用、受け付ける書式、
  この層で合法性を判定しない理由を記載する。

- [x] **ステップ4: Greenを確認する**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.CommandParsingTests -v`

  期待値: 全テストが成功する。

- [x] **ステップ5: Refactor要否を確認しコミットする**

  駒名対応と座標作成で形式エラーを一貫して返し、`Square` の検証を重複していないことを
  確認する。追加抽出が不要ならその判断を学習記録へ残す。

  ```sh
  git add kaname_shogi/cli.py tests/test_cli.py
  git commit -m "feat: CLI指し手入力を解析する"
  ```

## タスク2: 成駒を表示できるRed/Greenを完了する

**ファイル:**
- 変更: `kaname_shogi/display.py`
- 変更: `tests/test_display.py`

**インターフェース:**
- 消費: `render_position(position: Position) -> str`
- 生産: 成駒を含む局面にも例外なく表示文字列を返す `render_position`

- [x] **ステップ1: 成駒表示の失敗するテストを作成する**

  6種の成駒を空の盤へ置いた局面を作り、表示文字列に `+と`、`+成香`、`+成桂`、
  `+成銀`、`+馬`、`+竜` が含まれることを確認するテストを追加する。

  ```python
  def test_renders_all_promoted_piece_names(self):
      """成駒6種を含む局面を、KeyErrorにせず名称付きで表示する。"""
      position = Position(Board(), Side.SENTE)
      for square, piece_type in promoted_pieces:
          position.board.set_piece(square, Piece(piece_type, Side.SENTE))

      rendered = render_position(position)

      for name in ("と", "成香", "成桂", "成銀", "馬", "竜"):
          self.assertIn("+" + name, rendered)
  ```

- [x] **ステップ2: Redを確認する**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_display.DisplayTests.test_renders_all_promoted_piece_names -v`

  期待値: 現在の `names` 辞書に成駒がなく、`KeyError` による失敗となる。

- [x] **ステップ3: 最小の表示実装を追加する**

  `display.py` の `names` に成駒6種の表示名を加え、`render_position` のdocstringの
  「基本8種類」前提を14種対応へ更新する。マス幅の整列は既存の文字列連結方式を保ち、
  表示専用の別経路を作らない。

  ```python
  names = {
      PieceType.PRO_PAWN: "と", PieceType.PRO_LANCE: "成香",
      PieceType.PRO_KNIGHT: "成桂", PieceType.PRO_SILVER: "成銀",
      PieceType.HORSE: "馬", PieceType.DRAGON: "竜",
      # 既存の未成駒名も維持する。
  }
  ```

- [x] **ステップ4: Greenを確認する**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_display.DisplayTests -v`

  期待値: 成駒表示テストと既存表示テストが全て成功する。

- [x] **ステップ5: Refactor要否を確認しコミットする**

  玉・王の既存分岐を維持し、14種の盤上駒名が一つの対応表で完結していることを確認する。

  ```sh
  git add kaname_shogi/display.py tests/test_display.py
  git commit -m "fix: CLI表示で成駒を描画する"
  ```

## タスク3: 対局進行・再入力・停止のRed/Greenを完了する

**ファイル:**
- 変更: `kaname_shogi/cli.py`
- 変更: `kaname_shogi/__main__.py`
- 変更: `tests/test_cli.py`
- 変更: `tests/test_display.py`

**インターフェース:**
- 消費: `parse_command(text: str)`、`apply_move`、`apply_drop`、`is_game_over`、`render_position`
- 生産: `run_game(*, input_fn: Callable[[], str] = input, output_fn: Callable[[str], None] = print) -> None`

- [x] **ステップ1: 進行の失敗するテストを作成する**

  `tests/test_cli.py` に、値を順番に返す `ScriptedInput` と出力文字列を蓄積する
  `outputs.append` を用意する。以下を個別テストにする。

  ```python
  def test_reprompts_after_format_and_legality_errors(self):
      """形式エラーと二歩の拒否後も、同じ手番で合法手を受け付ける。"""
      outputs = []
      inputs = ScriptedInput(["move 7", "move 7 7 7 8",
                              "move 7 7 7 6", "move 3 3 3 4"])

      cli.run_game(input_fn=inputs, output_fn=outputs.append)

      self.assertIn("エラー：入力形式が正しくありません。", outputs)
      self.assertIn("手番：後手", outputs)
      self.assertIn("手番：先手", outputs)
  ```

  上記では、形式エラー、先手歩を後退させる合法性エラーの後に、先手の７七→７六、
  後手の３三→３四を受け付ける。
  このほか、持ち駒を持つ局面を `unittest.mock.patch` で初期局面生成に渡し、`drop 歩 5 5`
  が `apply_drop` を通じて反映されるテストを追加する。EOF、`KeyboardInterrupt`、初期時点の
  詰み、先手が５三→５二と指して後手を詰ませる局面を同じ方法で作り、それぞれ終了
  メッセージまたは `詰みです。先手の勝ちです。` と、余分に入力を読まないことを確認する。

- [x] **ステップ2: Redを確認する**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.GameplayTests -v`

  期待値: `run_game` が未実装、または入力を一度表示して終了する現在の挙動では、再入力・
  終局停止・中断メッセージのアサーションが失敗する。読み込みエラーだけではRed完了としない。

- [x] **ステップ3: 最小の進行実装を追加する**

  `run_game` は初期局面を作って `render_position` を出力し、各周回で
  `指し手を入力してください（例: move 7 7 7 6）:` を出力してから `input_fn()` を呼ぶ。
  解析結果の種類で既存操作を一度だけ呼び、`ValueError` を `エラー：<理由>` にして再入力する。
  成功時には局面を表示し、`is_game_over` が真なら反対側の勝者を出力してreturnする。

  ```python
  def run_game(*, input_fn=input, output_fn=print) -> None:
      position = create_initial_position()
      output_fn(render_position(position))
      while True:
          if is_game_over(position):
              output_fn(_checkmate_message(position.side_to_move))
              return
          output_fn("指し手を入力してください（例: move 7 7 7 6）:")
          try:
              command = parse_command(input_fn())
              _apply_command(position, command)
          except (EOFError, KeyboardInterrupt):
              output_fn("入力を終了しました。")
              return
          except ValueError as error:
              output_fn("エラー：" + str(error))
              continue
          output_fn(render_position(position))
  ```

  `run_game` のdocstringに、引数、戻り値、開始局面と出力という副作用、詰みだけを終局と
  する前提、例外を端末へ出さず再入力・終了へ変換する理由を記す。`__main__.py` は
  `from .cli import run_game` と `run_game()` だけに変更する。

- [x] **ステップ4: Greenを確認する**

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.GameplayTests -v`

  期待値: 移動・駒打ち、形式エラー・合法性エラーの再入力、詰み、EOF、Ctrl-Cの全テストが成功する。

- [x] **ステップ5: 実プロセスのCLIを更新して確認する**

  `tests/test_display.py` の既存CLIテストを、空の標準入力を渡してEOF終了を確認する形に
  更新する。初期局面、入力案内、`入力を終了しました。`、stderrなし、終了コード0を
  固定する。

  実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_display.DisplayTests.test_cli_starts_game_and_exits_on_eof -v`

  期待値: 実プロセスでも入力待ちが残らず、定めた文言で成功する。

- [x] **ステップ6: Refactor要否を確認しコミットする**

  形式解析と適用を分け、合法手規則をCLIへ重複させず、終了・エラー文言を一箇所へ保てて
  いることを確認する。

  ```sh
  git add kaname_shogi/cli.py kaname_shogi/__main__.py \
      tests/test_cli.py tests/test_display.py
  git commit -m "feat: CLIで対局を進行する"
  ```

## タスク4: 独立レビュー、全検証、記録、取り込み準備を完了する

**ファイル:**
- 変更: `README.md`
- 作成: `docs/knowledge/27-cli-gameplay.md`
- 作成: `docs/learning/34-cli-gameplay.md`
- 変更: `docs/plans/2026-09-23-cli-gameplay.md`

- [ ] **ステップ1: 独立コードレビューを実施する**

  設計仕様、差分、各テストを照合して、入力の曖昧さ、局面不変性、終局後の入力、成駒表示、
  EOF/Ctrl-C、公開docstringをレビューする。Critical・Important・Minorを分けて
  `docs/learning/34-cli-gameplay.md` に記録する。CriticalまたはImportantがあれば、先に
  修正し、対象・全テストを再実行して再レビューする。

- [ ] **ステップ2: 文書を更新する**

  READMEの「CLIは初期配置を表示して終了」を、入力形式、エラー再入力、詰み停止、
  EOF/Ctrl-C、未実装の終局理由へ更新する。知識メモには、日本将棋連盟の規則と、学習用CLIが
  反則勝敗ではなく入力エラーとして再入力する判断、全角入力、既存APIとの接続を記す。
  学習記録には、本人の各確認問題と回答、設計承認、Redの実際の失敗、Green、Refactor、
  レビュー、検証を、実施した順に記録する。

- [ ] **ステップ3: 全検証を実行する**

  ```sh
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
  printf '' | PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi
  git diff --check
  git status --short --branch
  ```

  期待値: 全テスト成功、CLIが初期局面と終了メッセージを表示して終了、差分チェックは出力なし。
  `.antigravity/` は生成物として未追跡のまま保ち、コミット対象にしない。

- [ ] **ステップ4: 記録をコミットし、取り込み承認を求める**

  ```sh
  git add README.md docs/knowledge/27-cli-gameplay.md \
      docs/learning/34-cli-gameplay.md docs/plans/2026-09-23-cli-gameplay.md
  git commit -m "docs: CLI対局進行の学習記録を追加する"
  ```

  作業ブランチの全コミット、レビュー結論、検証結果、未追跡ファイルを報告する。本人が
  承認するまで `main` へ取り込まない。取り込み後は `main` で全テストとCLI起動を再検証し、
  最後の理解確認を一問だけ出して回答と補足を記録する。

## 計画の自己レビュー

- 設計仕様の入力形式、再入力、詰み停止、EOF/Ctrl-C、成駒表示、対象外を全タスクへ対応付けた。
- 各実装タスクに、振る舞いのRed、最小実装、Green、Refactor確認、コミットを含めた。
- 後続タスクが使う関数名・引数・戻り値を各インターフェース節に固定した。
- 全コマンドはリポジトリ直下で実行でき、外部依存を追加しない。
- 未決定のプレースホルダを残していない。
