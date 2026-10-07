# 第67回「SFEN局面変換」実装計画

> **AIエージェントへの指示:** REQUIRED-SUB-SKILL: 実装計画が本人承認された後に、選ばれた方法に応じて `executing-plans` または `subagent-driven-development` を使用する。承認前は実装・テスト変更・テスト実行を始めない。各ステップには追跡用チェックボックスを使う。

**状態:** 設計仕様・本実装計画は2026-10-07に本人承認済み。レビュー指摘への対応を含む実装、関連テスト、独立レビューを作業ブランチで完了した。本人の別途承認後、`feature/sfen-position-conversion` を `main` へfast-forward統合し、統合時の `main` HEAD `8421492` で全326テストが成功した。最終理解確認と回答記録も完了した。現在地の更新は本人が確認・承認し、`9036e2c` で文書コミット済み。pushは行っていない。

**目標:** `Position` とSFENの相互変換、SFENからのUSI局面設定、SFEN手数の保持を追加し、既存の局面モデルとJSON棋譜形式を保つ。

**アーキテクチャ:** `kaname_shogi.sfen` が `SfenPosition`（`Position` とSFENの手数を組にしたデータ）と読込・書出しを提供する。`parse_usi_position` は `startpos` または `sfen` を起点に既存の `GameRecord` で合法手を再生し、現在局面と手数を返す。エンジン状態は引き続き `.position` のみを保持し、SFENの変換はUSI境界に置く。

**技術スタック:** Python 3.9.6、標準ライブラリ、`unittest`、既存の `model` / `usi_move` / `game_record` / `usi_engine`。

**仕様 (Spec):** [第67回設計仕様](2026-10-07-sfen-position-conversion-design.md)

**グローバル制約 (Global Constraints):**
- SFENの読込・書出しの両方に対応する。
- USI局面指定は `position sfen <SFEN>` 単独と、`position sfen <SFEN> moves <指し手...>` の両方を受け付ける。
- 既存の `position startpos moves <指し手...>` は維持し、`startpos` 単独や `moves` の空列は新たに受け入れない。
- SFENの手数は読み込んだ値を保持して書き出しに反映する。SFENの後ろに指し手があれば、その数だけ手数を進める。
- 手数欄が省略されたSFENも受け付け、手数1として扱う。書き出しは手数欄を含む4項目にする。
- 手数は `Position` に追加せず、SFEN専用の結果データに保持する。
- 入力検証はSFENの構文と現在のモデルで表現可能な値までとし、局面の合法性・実戦到達可能性は検証しない。
- 任意の正の持ち駒枚数を内部モデルで表現し、枚数に比例した反復処理でUSI入力が止まらないよう `Hand.add_many` で一括加算する。
- エラーは理由を含む `ValueError` とし、一手変換・合法手適用の失敗には手数と入力トークンを添える。
- SFENとJSON棋譜は別形式とし、`kaname-shogi-game-record-v1` の構造を変更しない。
- ShogiHomeの実機操作・画面へのSFEN貼り付けは行わない。
- テストメソッド名は英語とし、日本語docstringに確認する振る舞いと検出したい誤りを記す。
- 公開インターフェースのdocstringは日本語で引数・戻り値・副作用・前提条件・設計理由を説明する。

## レビューフォーカス

- 手数欄なしは手数1となり、書出しで明示される（`test_defaults_missing_move_number_to_one_and_writes_it`）。
- 9段・各9マスでない盤面や不正な駒・手番・持ち駒・手数は、診断理由を持つ `ValueError` となる（`test_rejects_malformed_sfen_fields`）。
- 玉がない等の構文上表現できる局面は読み込め、合法性検査を誤って先取りしない（`test_accepts_composed_position_without_king`）。
- SFEN単独とSFENからの複数手再生は正しい盤面・手番・持ち駒を返し、手数を手の数だけ進める（`test_parses_sfen_without_moves`、`test_replays_moves_from_sfen_and_advances_move_number`）。
- SFENからの不正手・不合法手は手数と入力トークンが分かる `ValueError` になり、USIプロセスでは診断が標準エラーに出て標準出力へ混ざらない（既存の一手エラー・プロセステストとSFEN入口の追加テスト）。

---

## ファイル構成

- 作成: `kaname_shogi/sfen.py` — SFEN専用の局面データ、文字列解析、正規化書出しを定義する。
- 作成: `tests/test_sfen.py` — 初期局面、成駒、持ち駒、手数、省略手数、表現可能な局面、不正構文を検証する。
- 変更: `kaname_shogi/model.py` — `Hand.add_many` で検証済みの正の枚数を一括加算し、SFENの大きな枚数で反復回数が増えないようにする。
- 変更: `tests/test_model.py` — 一括加算の枚数、対象駒種、無効値での不変性を検証する。
- 変更: `kaname_shogi/usi_position.py` — `startpos` に加えてSFEN局面を受け、任意の既存合法手適用で再生する。
- 変更: `kaname_shogi/usi_engine.py` — USI解析結果の `.position` だけをエンジン状態へ渡す。
- 変更: `tests/test_usi_position.py` — 戻り値、SFEN単独、SFEN起点の再生、手数更新、エラーを確認する。
- 変更: `tests/test_usi_engine.py` — 戻り値接続と標準入出力プロセス経由のSFEN受信を確認する。
- 作成: `docs/knowledge/sfen-position-notation.md` — SFEN各欄と内部型の対応、手数、API、検証の境界を一次資料付きで記録する。
- 作成: `docs/learning/67-sfen-position-conversion.md` — 設計選択、学習要点、実装と実績、検証、Refactor、独立レビュー、未解決事項を記録する。最終理解確認の回答は本人が回答するまで記入しない。
- 更新: `docs/plans/2026-10-07-sfen-position-conversion-design.md` — 承認後の実施内容と設計からの差を記録する。
- 更新: この計画 — 実施した手順だけをチェックし、実績・検証・レビューを記録する。
- 更新時期を後段にする: `README.md`、`docs/02-project-direction.md`、`docs/next-topics.md`、`docs/roadmap-usi-shogihome.md`。作業ブランチで技術実装が終わった時点では完了扱いを先取りせず、`main` 統合後の検証と最終理解確認への本人回答を記録してから現在地を更新する。`docs/README.md` は作業ブランチの現在状態を索引に反映し、統合・理解確認後に完了状態へ更新する。
- 変更しない: `kaname_shogi/game_record.py`、既存のJSONスキーマ、ShogiHome設定・棋譜・ログ。`Position` に手数・履歴は追加しない。

## Task 0: 承認後に作業ブランチを開始する

- [x] **ステップ1: 現在状態を再確認し、専用ブランチを作る**

実装計画の明示承認後に `git status --short --branch`、`git rev-parse --short HEAD`、`git branch --list feature/sfen-position-conversion` を確認する。現在の基点 `0d1b9e6` と計画文書2件以外に予期しない変更がなく、同名ブランチがない場合だけ、`git switch -c feature/sfen-position-conversion` を実行する。状態が異なる場合は実装を開始せず相談する。`main` は更新しない。

## Task 1: SFEN局面の読込・書出しを追加する

**ファイル:**
- 作成: `kaname_shogi/sfen.py`
- 作成: `tests/test_sfen.py`

**インターフェース (Interfaces):**
- 消費: `Position`、`Board`、`Piece`、`PieceType`、`BasicPieceType`、`Hand`、`Side`、`Square`。
- 生産: `SfenPosition(position: Position, move_number: int)`、`parse_sfen(sfen: str) -> SfenPosition`、`format_sfen(sfen_position: SfenPosition) -> str`。`SfenPosition` は `Position` と1始まりのSFEN手数を持つデータで、`Position` 本体は変更しない。

- [x] **ステップ1: import可能なAPI骨組みを作る**

`SfenPosition` と二つの関数シグネチャを `kaname_shogi/sfen.py` に置き、テストがモジュール読込失敗で止まらない状態にする。二関数は意図的に不完全な固定結果を返し、SFENの解析や書出しロジックはまだ実装しない。

- [x] **ステップ2: 読込・書出しの振る舞いテストを書く**

`tests/test_sfen.py` に日本語docstring付きで次のテストを作る。

1. `test_parses_and_formats_initial_sfen` — `lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1` を解析し、平手初期局面と手数1を得て、同じ正規SFENを書き出す。
2. `test_round_trips_promoted_piece_hands_and_move_number` — `9/9/9/3+P5/9/9/9/9/K8 b 2RBGsnp 17` を解析し、`Square(6, 4)` の先手と金、先手の飛車2枚・角1枚・金1枚、後手の銀・桂・歩各1枚、手数17を確認し、同じ正規SFENを書き出す。
3. `test_defaults_missing_move_number_to_one_and_writes_it` — 初期SFENの手数欄を除いた3項目を受け付け、手数1と4項目の書出しを確認する。
4. `test_accepts_composed_position_without_king` — `9/9/9/9/9/9/9/9/9 w - 8` を受け付け、玉のない空盤面と後手番を保持する。
5. `test_rejects_malformed_sfen_fields` — 段不足 `9/9 b - 1`、段幅 `8/9/9/9/9/9/9/9/9 b - 1`、不明な駒 `X8/9/9/9/9/9/9/9/9 b - 1`、不正な成り `3+K5/9/9/9/9/9/9/9/9 b - 1` を検査する。さらに共通盤面 `9/9/9/9/9/9/9/9/9` に対する `x - 1`（不正な手番）、`b K 1`（持ち駒の玉）、`b 0P 1`（0枚指定）、`b - x`（非整数手数）、`b - 0`（0手数）を検査する。全て `ValueError` とし、メッセージから不正箇所が分かることを確認する。
6. `test_formatting_does_not_mutate_position` — 書出し前後の盤・手番・両手の枚数が同じであることを確認する。
7. `test_formats_hands_in_canonical_order` — 空盤面へ順不同で先手の歩・金・飛車、後手の歩・桂・銀を加え、`9/9/9/9/9/9/9/9/9 b RGPsnp 1` の順序で出力する。
- [x] **ステップ3: 振る舞いRedを確認する**

実行:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_sfen.py' -v
```

期待値: API骨組みは読み込まれ、上記テストが返却値の誤りまたは期待した `ValueError` が発生しないことを理由に失敗する。import・構文エラーだけをRed完了とは扱わない。

- [x] **ステップ4: `kaname_shogi/sfen.py` に最小の変換を実装する**

SFEN段を順に読み、行幅を9マスに展開し、`Board.set_piece(Square(file, rank), piece)` で配置する。手番・持ち駒・省略手数を `Position` と `SfenPosition` に変換する。逆変換では手番、段順、空きマス、成駒、`R,B,G,S,N,L,P` 順の持ち駒を正規化し、手数を必ず出力する。局面の駒数・玉・二歩・王手の合法性は検査に加えない。

- [x] **ステップ5: SFEN変換テストのGreenを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_sfen.py' -v`

期待値: 初期実装時のSFEN変換9テストがすべて成功する。

- [x] **ステップ6: SFEN変換を作業ブランチへコミットする**

作業ブランチ上で `kaname_shogi/sfen.py` と `tests/test_sfen.py` をステージし、`git diff --cached --check` を確認して `feat: SFEN局面の読込と書出しに対応する` でコミットする。

## Task 2: USIのSFEN局面指定をエンジンへ接続する

**ファイル:**
- 変更: `tests/test_usi_position.py`、`tests/test_usi_engine.py`
- 変更: `kaname_shogi/usi_position.py`、`kaname_shogi/usi_engine.py`

**インターフェース (Interfaces):**
- 消費: Task 1の `parse_sfen(sfen: str) -> SfenPosition` と `GameRecord`、`parse_usi_move`。
- 生産: `parse_usi_position(command: str) -> SfenPosition`。成功時に現在局面とSFENの1始まり手数を返す。`run_usi_engine` は戻り値の `.position` を `_UsiEngineState` へ設定する。

- [x] **ステップ1: SFEN起点のUSI局面・プロセステストを書く**

既存の通常手・成り・駒打ちテストを `SfenPosition.position` 参照へ更新し、次を追加する。

1. `test_parses_sfen_without_moves` — 平手SFENを単独指定し、局面と手数1を返す。
2. `test_replays_moves_from_sfen_and_advances_move_number` — 手数17の平手SFEN `lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 17` から `7g7f 3c3d` を適用し、手数19と両歩の位置・手番を確認する。
3. `test_replays_moves_from_sfen_without_move_number` — 手数欄を除いた同じ3項目のSFENから `7g7f` を適用し、既定手数1から2になることを確認する。
4. `test_replays_drop_using_sfen_hand` — `4k4/9/9/9/9/9/9/9/4K4 b P 17 moves P*5e` を受け、5五の先手歩、歩の持ち駒0枚、手番後手、手数18を確認する。
5. `test_rejects_sfen_with_empty_moves` — `position sfen lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1 moves` を `ValueError` にする。
6. `test_rejects_unsupported_or_malformed_position_commands` — 既存の `startpos` 文法を維持しながら、不正SFEN `position sfen 9/8 b - 1`、別コマンド、未知の基底指定を `ValueError` にする。
7. `UsiEngineProcessTests.test_entrypoint_accepts_sfen_position` — 実行入口へ平手SFEN単独指定、時間付き `go`、`quit` を送り、合法な `bestmove`、終了コード0、診断のないstderrを確認する。
8. `UsiEngineProcessTests.test_entrypoint_reports_invalid_sfen_position_on_stderr` — 不正SFEN `position sfen 9/8 b - 1` で標準出力へUSI応答を出さず、診断を標準エラーへ出して非0終了する。

テストメソッド名は英語とし、日本語docstringで確認内容と防ぎたい誤りを書く。`Position` と比較するために同じ値の別コピーを `assertEqual` するテストは作らず、局面の駒・手番・持ち駒を直接確認する。

- [x] **ステップ2: USI振る舞いRedを確認する**

実行:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_usi_position.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_usi_engine.py' -v
```

期待値: import/構文エラーではなく、SFENコマンドがまだ拒否されること、`SfenPosition` の戻り値契約がまだ満たされないこと、またはエンジンが `.position` を取り出さないことによる振る舞い失敗を確認する。

- [x] **ステップ3: `parse_usi_position` でSFENと指し手列を再生する**

`kaname_shogi/usi_position.py` で `position sfen` の後ろに3項目または4項目のSFENを識別し、任意の `moves` 区切りを処理する。SFEN単独なら解析結果を返す。指し手があれば `GameRecord(sfen_position.position)` から既存の一手解析・合法適用を順に使い、`SfenPosition(record.current_position, base_move_number + len(moves))` を返す。`position startpos moves ...` は従来の受け入れ条件を保ち、初期手数1から同じ結果型を作る。一手変換・合法適用の失敗は第何手とトークンを添えた `ValueError` にする。

- [x] **ステップ4: エンジン状態には盤面局面だけを渡す**

`kaname_shogi/usi_engine.py` の `position` 分岐で `parse_usi_position(command).position` を `replace_position` に渡す。検索処理、Difficulty、時計解釈、標準応答の責務は変更しない。

- [x] **ステップ5: USI局面・エンジンテストのGreenを確認する**

実行:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_usi_position.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_usi_engine.py' -v
```

期待値: SFEN単独・複数手再生・手数進行・既存の平手再生・合法手応答・不正入力stderrの各テストが成功する。ShogiHome実機互換を証明したとは扱わない。

- [x] **ステップ6: USI接続を作業ブランチへコミットする**

変更したUSI実装とテストをステージし、`git diff --cached --check` を確認して `feat: USI position sfenを受け付ける` でコミットする。

## Task 3: Refactor要否、独立レビュー、全体検証、記録を行う

**ファイル:**
- 確認・必要時変更: Task 1・2のコードとテスト
- 変更: `kaname_shogi/model.py`、`kaname_shogi/sfen.py` — レビュー指摘の大量枚数処理とASCII駒記号検証
- 変更: `tests/test_model.py`、`tests/test_sfen.py`、`tests/test_usi_position.py` — 修正前Red、修正後Green、SFEN起点の診断テスト
- 作成: `docs/knowledge/sfen-position-notation.md`、`docs/learning/67-sfen-position-conversion.md`
- 更新: `docs/knowledge/usi-position-replay.md` — `parse_usi_position` の戻り値とSFEN対応を反映
- 更新: 設計仕様、実装計画、`docs/README.md`

**インターフェース (Interfaces):**
- 消費: `SfenPosition`、SFEN変換API、SFEN対応済み `parse_usi_position` と `run_usi_engine`。
- 生産: 承認仕様を満たし、Critical / Important のレビュー指摘を解消し、記録と全テストを確認済みの作業ブランチ。

- [x] **ステップ1: Refactorの要否を確認する**

SFEN文字列変換、一手トークン変換、合法手適用、エンジン局面保持の責務が混ざっていないか確認する。重複や不要な抽象化がなければ追加変更をせず、その理由を学習記録へ残す。変更した場合は関連テストを再実行する。

- [x] **ステップ2: 独立したコードレビューを行う**

実装者とは別のレビュアーが承認仕様とコード・テスト差分を照合し、Critical / Important / Minorで指摘を分類する。初回レビューはCriticalなし、Important 1件（枚数比例の反復）、Minor 2件（ASCII以外の駒記号、SFEN起点手エラーの直接テスト不足）。ユーザー承認の計画更新後に一括加算・ASCII検査・直接テストを追加し、修正後レビューは指摘なし。CriticalまたはImportantが残る場合は修正、関連テストと全体テストの再実行、再レビューを行う。

- [x] **ステップ3: 関連・全体テストと差分を検証する**

実行:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_sfen.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_model.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_usi_position.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_usi_engine.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
```

期待値: 関連テストとREADME記載の全テストが終了コード0、差分検査に問題がない。実行結果と件数を記録し、ShogiHome画面や実機での互換性確認済みとは報告しない。

- [x] **ステップ4: 学習記録・知識メモ・設計実績を更新する**

確定知識にはAPIの引数・戻り値・副作用・前提条件、SFEN欄と内部表現の対応、正規化書出し、省略手数と検証範囲を一次資料付きで記す。学習記録には本人の選択とアシスタント補足を区別し、実装内容、TDD Red/Greenの理由、Refactor判断、レビュー、テスト結果、未確認事項を実施どおりに記録する。最終理解確認の回答は本人が回答するまで未記入とする。設計仕様と計画は承認・実績の状態に更新し、`docs/README.md` にリンクを追加する。

- [x] **ステップ5: 記録を本人に提示し、確認後にブランチへコミットする**

学習記録と知識メモを提示し、本人の内容確認を得る。確認後、残る関連文書を含む差分をステージし、`git diff --cached --check` と `git status --short --branch` を確認して `docs: 第67回SFEN局面変換を記録する` で作業ブランチへコミットする。未承認の `main` 統合やpushは行わない。

## Task 4: 明示承認後にmainへ統合・検証し、最終理解確認を行う

**ファイル:**
- 統合後に更新: `docs/learning/67-sfen-position-conversion.md`、`README.md`、`docs/02-project-direction.md`、`docs/next-topics.md`、`docs/roadmap-usi-shogihome.md`、`docs/README.md`、`docs/resume.md`

**インターフェース (Interfaces):**
- 消費: Task 3でレビュー・テスト・記録を終えた作業ブランチと本人の統合判断。
- 生産: 本人承認による統合、統合先での全体テスト、回答済み最終理解確認と次候補の案内。

- [x] **ステップ1: 統合選択を本人に提示して待つ**

実装ブランチの差分、レビュー結果、テスト結果、記録を提示した。本人はローカル `main` へのfast-forward統合を明示承認した。実装計画の承認とは別に統合判断を確認した。

- [x] **ステップ2: 統合が明示承認された場合だけmainへ反映する**

本人が統合を明示承認した。`main` と作業ツリーを確認しfast-forward可能だったため統合した。統合時の `main` HEAD は `8421492`。統合後に `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` を実行し、全326テストが成功した。

- [x] **ステップ3: 最終理解確認を一問だけ出す**

統合先の全体検証後に一問だけ尋ね、本人は「責任を分離を維持するため」と回答した。回答と補足は学習記録へ記録した。

- [x] **ステップ4: 回答後に学習記録と現在地を更新する**

本人の回答とアシスタント補足を分けて学習記録に追記し、`README.md`、`docs/02-project-direction.md`、`docs/next-topics.md`、`docs/roadmap-usi-shogihome.md`、`docs/README.md`、`docs/resume.md` の現在地と候補を更新した。本人が内容を確認・承認した。次テーマは未選定で、本人が選ぶまで新しい学習・実装を始めない。

- [x] **ステップ5: 内容確認後に現在地の記録をコミットする**

本人確認後に9文書を `9036e2c` で `main` にコミットした。コミット前に `git diff --check` と相対Markdownリンクの参照先を確認し、欠落がないことを確認した。pushは行っていない。

## 実行方法の提案

この計画はSFEN変換とUSI接続の2実装タスクを同じ型・手数契約で順に進め、最後に統合テストを行う。インターフェース依存があるため、このセッションで逐次実装する方法を推奨し、別担当者による独立コードレビューは最後に行う。
