# USI平手手順からの局面再現：実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画を実装するには `executing-plans` スキルを使用する。各ステップには追跡用チェックボックスを使う。

## 状態

2026-10-02に作成し、同日本人がこのセッションでのTDD実装と最後の独立レビューを含めて承認した。作業ブランチ `codex/usi-position-replay` で実行中。

**目標:** `position startpos moves ...` の合法な指し手列を再生し、最後の局面を `Position` として返すUSI APIを追加する。

**アーキテクチャ:** `kaname_shogi.usi_position.parse_usi_position` がコマンド文法を確認し、各一手トークンを既存の `parse_usi_move` へ渡す。`GameRecord` の合法手適用で平手初期局面から順に再生し、独立コピーである `current_position` を返す。履歴は戻り値に含めず、呼び出し側は必要なら元のコマンドや別の `GameRecord` を保持する。

**技術スタック:** Python標準ライブラリ、`unittest`、既存の `kaname_shogi.usi_move` / `game_record` / `model`。

**仕様 (Spec):** [2026-10-02-usi-position-replay-design.md](2026-10-02-usi-position-replay-design.md)

**グローバル制約 (Global Constraints):**
- 「完全な `position startpos moves <move1> ... <moveN>` コマンドを受け付ける。」
- 「`moves` と1手以上の指し手を必須にする。」
- 「既存の `parse_usi_move` が扱う通常移動・成り・7種類の駒打ちを、複数手順の各トークンとして利用する。」
- 「平手初期局面から手順を順番に合法適用し、最後の `Position` を返す。」
- 「文法エラー、指し手変換失敗、不合法手は `ValueError` とし、原因が分かるメッセージを付ける。」
- 「返却値 `Position` への指し手履歴の追加」は対象外。
- 「`position sfen ...` とSFEN解析」は対象外。
- Move値型、`Position`、`GameRecord`、`movegen`、`kaname_shogi.__init__` は変更しない。
- テストメソッド名は英語とし、日本語docstringに振る舞いと検出する誤りを書く。公開関数のdocstringは引数・戻り値・副作用・前提条件・設計理由を日本語で説明する。
- ShogiHome実機で未観測の成り・駒打ち・SFEN・不正手順の挙動を推測または実証済みと記録しない。

## レビューフォーカス

- `position startpos` と空の `moves` は平手初期局面だけを返さず、`ValueError` にする（`test_rejects_position_without_moves`）。
- SFEN、異なるコマンド接頭辞、手順のない不正コマンドを `ValueError` にする（`test_rejects_unsupported_or_malformed_position_commands`）。
- 不正な一手トークンを `ValueError` にし、原因の手をメッセージで特定できるようにする（`test_rejects_unparseable_move_token`）。
- 表記として読めても局面で不合法な手を合法適用扱いせず、手順を示す `ValueError` にする（`test_rejects_illegal_move`）。
- 成りと捕獲後の駒打ちを含む手順で、盤上の駒・持ち駒・手番を正しく再現する（`test_replays_promoting_move_from_startpos`、`test_replays_captured_pawn_drop_from_startpos`）。

## ファイル構成

- 作成: `tests/test_usi_position.py` — コマンド構文、通常手の複数手再現、成り、駒打ち、変換失敗、不合法手を `unittest` で確認する。
- 作成: `kaname_shogi/usi_position.py` — USI `position` コマンドの構文確認と合法手順の局面再生を担当する公開関数を定義する。
- 作成: `docs/knowledge/usi-position-replay.md` — 確定したAPI、合法性委譲、履歴の返却境界、エラーを一次資料付きで簡潔に記録する。
- 作成: `docs/learning/56-usi-position-replay.md` — 本人の回答、USI資料、実機観測、TDD、実装、検証、Refactor判断、独立レビュー、未解決事項を記録する。
- 更新: `docs/plans/2026-10-02-usi-position-replay-design.md` — 実装結果と計画・実績の差、最終状態を記録する。
- 更新: `docs/plans/2026-10-02-usi-position-replay-implementation-plan.md` — 実際に完了した手順だけチェックし、計画と実績の差を記録する。
- 変更しない: `kaname_shogi/usi_move.py`、`kaname_shogi/move.py`、`kaname_shogi/model.py`、`kaname_shogi/game_record.py`、`kaname_shogi/movegen.py`、`kaname_shogi/__init__.py`、`tests/test_usi_move.py`、`tests/test_game_record.py`。既存の一手変換・合法適用・履歴責務を再利用する。

## Task 1: コマンドから合法な現在局面を再現する

**ファイル:**
- 作成: `tests/test_usi_position.py`
- 作成: `kaname_shogi/usi_position.py`

**インターフェース (Interfaces):**
- 消費: `parse_usi_move(text: str) -> Move`、`create_initial_position() -> Position`、`GameRecord(initial_position)`、`GameRecord.apply_move(source, destination, *, promote=False)`、`GameRecord.apply_drop(piece_type, destination)`。
- 生産: `parse_usi_position(command: str) -> Position`。成功時は平手初期局面へ1手以上を順番に合法適用した独立 `Position` を返す。文法・一手変換・局面適用の失敗は原因が分かる `ValueError` とする。

- [x] **ステップ1: 全振る舞いのテストを先に作成する**

`tests/test_usi_position.py` に `unittest.TestCase` を作り、各テストメソッドは英語、日本語docstringは確認する振る舞いを先頭に置き、続けて検出したい誤りを記す。

1. `test_replays_multiple_ordinary_moves_from_startpos` は `position startpos moves 7g7f 3c3d 2g2f` を読み、返り値が `Position` であること、`Square(7, 6)` に先手歩、`Square(3, 4)` に後手歩、`Square(2, 6)` に先手歩があり、手番が `Side.GOTE` であることを確認する。
2. `test_replays_promoting_move_from_startpos` は `position startpos moves 7g7f 3c3d 7f7e 3d3e 7e7d 3e3f 7d7c+` を読み、`Square(7, 3)` が先手の `PieceType.PRO_PAWN`、手番が `Side.GOTE` であることを確認する。
3. `test_replays_captured_pawn_drop_from_startpos` は `position startpos moves 1g1f 1c1d 1f1e 1d1e 1i1h 4c4d 1h1e 4d4e P*1d` を読み、`Square(1, 4)` に先手歩、`Square(1, 5)` に先手香、先手の持ち歩が0枚、手番が `Side.GOTE` であることを確認する。
4. `test_rejects_position_without_moves` は `position startpos` と `position startpos moves` を `ValueError` として拒否することを確認する。
5. `test_rejects_unsupported_or_malformed_position_commands` は `position sfen ...`、別の接頭辞、不足または余分な構文トークンを `ValueError` として拒否することを確認する。
6. `test_rejects_unparseable_move_token` は `position startpos moves 7g7` を `ValueError` とし、エラーメッセージに問題のトークン `7g7` が含まれることを確認する。メッセージ全文は固定しない。
7. `test_rejects_illegal_move` は `position startpos moves 7g7e` を `ValueError` とし、エラーメッセージに問題のトークン `7g7e` が含まれることを確認する。

- [x] **ステップ2: importエラーではない振る舞いのRedを確認する**

テスト作成後に `kaname_shogi/usi_position.py` を作り、正しい関数シグネチャで `None` を返す一時的な仮実装を置く。次を実行し、合法手の期待 `Position` と `None` の不一致、および不正・不合法入力で `ValueError` が送出されない失敗を確認する。

実行: `python3 -m unittest tests.test_usi_position -v`

期待値: テストモジュールの読み込みエラーだけでなく、テスト本体の期待値・例外アサーションが失敗する。

- [x] **ステップ3: `parse_usi_position` を実装する**

`kaname_shogi/usi_position.py` に `parse_usi_position(command: str) -> Position` を実装する。コマンドを空白区切りで読み、先頭が `position`、次が `startpos`、次が `moves` であり、その後に1手以上あることを検査する。`position startpos` 単独、空の手順、SFENその他の形式は `ValueError` にする。

新しい平手 `GameRecord(create_initial_position())` を作り、各トークンを既存の `parse_usi_move` で読み取る。`BoardMove` は `apply_move`、`DropMove` は `apply_drop` へ渡す。文字列変換または局面適用の `ValueError` は問題の手のトークンを含む `ValueError` として伝え、原因例外を連鎖する。全手成功後に `record.current_position` を返す。USI固有の文法・履歴を `Move` や `Position` の型へ持ち込まない。

公開docstringには引数・戻り値・副作用・前提条件と、USI解析を値型および合法手適用から組み合わせる設計理由を日本語で記す。

- [x] **ステップ4: 対象テストのGreenを確認する**

実行: `python3 -m unittest tests.test_usi_position -v`

期待値: 通常手・成り・駒打ちを含む合法手順が期待する局面になり、文法・変換・合法性エラーが `ValueError` としてPASSする。

## Task 2: Refactor、独立レビュー、検証、記録

**ファイル:**
- 変更: `kaname_shogi/usi_position.py`
- 変更: `tests/test_usi_position.py`
- 作成: `docs/knowledge/usi-position-replay.md`
- 作成: `docs/learning/56-usi-position-replay.md`
- 更新: `docs/plans/2026-10-02-usi-position-replay-design.md`
- 更新: `docs/plans/2026-10-02-usi-position-replay-implementation-plan.md`

**インターフェース (Interfaces):**
- 消費: タスク1の公開関数と全対象テスト。
- 生産: 独立レビュー、全体検証、本人確認済みの学習・知識記録を含むレビュー可能なブランチ差分。

- [x] **ステップ1: Refactorの要否を判断する**

責務の重複、分かりにくい分岐、不要な状態を `usi_position.py` と専用テストで確認する。変更不要なら理由とともに不要と記録する。変更する場合は振る舞いを変えず、専用テストを再実行する。

- [x] **ステップ2: 独立コードレビューを受け、指摘を解消する**

実装者とは別のレビュアーが設計仕様と差分を確認し、Critical / Important / Minor に分類する。Critical・Important・Minorはいずれもなし。後続手で失敗した際の診断を守る任意テストの提案は、現行仕様を満たす必須修正ではないため保留する。結論と対応を学習記録へ残す。

- [x] **ステップ3: 専用・全体テストと差分検査を実行する**

実行:

```bash
python3 -m unittest tests.test_usi_position -v
python3 -m unittest discover -s tests -v
git diff --check
git diff --cached --check
```

期待値: すべて終了コード0で完了し、差分検査で問題がない。レビュー指摘を修正した場合は修正後にすべて再実行する。ShogiHome実機で未観測の成り・駒打ち・SFEN・不正手順の挙動を確認済みとは扱わない。

実績: レビュー後の専用テストは7件、全体は264件でいずれも成功。`git diff --check` と `git diff --cached --check` も終了コード0。実機未観測の挙動は主張していない。

- [x] **ステップ4: 学習記録・知識メモ・設計状態を更新する**

`docs/learning/56-usi-position-replay.md` に目的、設計判断、本人の回答とアシスタントの補足、USI一次資料の根拠、第54回から増えた実機観測とその限界、TDDのRed/Green、Refactor判断、独立レビューのCritical / Important / Minor、検証結果、未解決事項を実施どおりに記す。

`docs/knowledge/usi-position-replay.md` にAPI契約、`parse_usi_move`・`GameRecord` との責務関係、返却 `Position` に履歴が含まれないこと、`ValueError` の範囲、USI資料を簡潔に記す。設計仕様と計画は実施状態へ更新し、未実施の手順を完了扱いしない。

実績: 4文書を作成・更新した。学習記録では本人回答と補足、実機観測の限界、TDD結果、Refactor判断、独立レビュー、検証、未解決事項を区別して記載した。記録内容は本人の確認前であり、コミットしていない。

- [ ] **ステップ5: 記録を本人に提示し、確認後に日本語Conventional Commitを作成する**

学習記録・知識メモの内容を提示して本人の確認を得る。その後、実装・テスト・レビュー済み文書をステージし、`git diff --cached --check` を確認して作業ブランチへコミットする。候補メッセージ: `feat: USI平手手順から局面を再現する`。mainへの取り込みは含めない。

- [ ] **ステップ6: 最後の理解確認を一問出し、回答を記録する**

テーマ完了後、USI一手解析と合法局面適用の責務境界、または返却 `Position` と履歴の関係について一問だけ出し、回答を待つ。本人の回答と補足を区別して学習記録へ追記し、内容確認後に記録を日本語Conventional Commitで保存する。回答記録後にだけ次テーマ・方向性を見直す。

## 実行方法の提案

この計画は1つの公開関数、1つの専用テスト、既存の一手変換・合法手適用・GameRecordを順に使う小さな変更である。そのため、実装はこのセッションで逐次進め、最後に別のレビュアーが差分を独立確認する方法を推奨する。サブエージェント駆動で各実装単位を委譲する必要はない。
