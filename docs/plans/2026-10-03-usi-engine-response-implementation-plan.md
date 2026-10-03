# USIエンジンとして一手を返す：実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 既存CLIから独立したUSI実行入口を追加し、通知された平手局面から合法な一手を選び、標準出力へ応答する。

**アーキテクチャ:** `kaname_shogi.usi_engine.run_usi_engine` が注入された一行入力・一行出力関数を使い、最新の `Position` をローカルに保持する。USI `position` は既存パーサーへ、`go` の手選択は既存の `legal_moves` / `choose_weak_move` / `format_usi_move` へ委譲する。`main()` が標準入出力、改行・flush、標準エラー診断を接続する。

**技術スタック:** Python 3.9.6、標準ライブラリ `unittest` / `subprocess` / `selectors` / `os` / `random` / `typing`、既存の `kaname_shogi.usi_move` / `usi_position` / `movegen`。

**仕様 (Spec):** [2026-10-03-usi-engine-response-design.md](2026-10-03-usi-engine-response-design.md)

**状態:** 2026-10-03に仕様と本計画が承認され、実装・レビュー・文書反映後の検証、学習記録・知識メモの本人確認、および作業ブランチへのコミットが完了した。`main` への取り込みと取り込み先検証は未実施。

**グローバル制約 (Global Constraints):**
- 設計仕様の「対象」に記載された範囲から拡張しない。特に次の契約をそのまま守る。
  - 「既存CLIから独立した `kaname_shogi.usi_engine` モジュールを追加する。」
  - 「`run_usi_engine` を同モジュールの公開関数とし、`python -m kaname_shogi.usi_engine` を起動入口とする。」
  - 「`position` は既存パーサーと同じ `position startpos moves <1手以上>` に限定する。」
  - 「通常の `go` では時計情報を使わず、合法手選択後すぐ一手を返す。認識済みの検索条件は、実装しないものを診断して終了する。」
  - 「入出力関数を注入可能にし、関数単位のテストと対話型サブプロセステストを自動化する。」
  - 「最新の `Position` を `run_usi_engine` のローカル状態として保持する。新しい `position` コマンドで置き換える。`usinewgame` では局面を未設定に戻す。」
  - 「コマンド型、独立したエンジン状態オブジェクト、履歴APIは今回設けない。」
  - 時計引数 `btime` / `wtime` / `binc` / `winc` / `byoyomi` / `movestogo` / `movetime` は選択・待機に使わず、認識済みの未対応検索引数 `searchmoves` / `depth` / `nodes` / `mate` / `infinite` / `ponder` は `ValueError` と標準エラー診断を経て終了する。
  - 「未知のコマンド」はUSI資料の扱いに沿って読み飛ばす。
  - 「`choose_weak_move` の戻り値が `None` の場合は `bestmove resign` を出力する。」
  - 「公開関数からの例外は実行入口で捕捉し、内容の分かる診断を標準エラーへ出し、非0で終了する。」
  - 「出力関数は各応答を改行付きで書き、直ちにflushする。標準出力にはUSI応答だけを出す。」
  - 「ShogiHome上での実対局、合法なエンジン応答に対するShogiHome挙動の実証」は今回行わない。
- テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞い、続く本文に検出したい誤りや背景を書く。
- 公開インターフェースのdocstringに引数・戻り値・副作用・前提条件と設計理由を日本語で記録する。
- 実装前に対象範囲・表現・確認方法を明確にし、Refactor判断後にCritical・Important・Minorを含む独立コードレビューを行う。
- CriticalまたはImportantのレビュー指摘は解消し、再検証・再レビューしてから記録とコミットへ進む。
- 学習記録・知識メモは内容を本人に確認してからGitへコミットする。
- テーマ実装、検証、独立レビュー、記録がそろうまで `main` へ取り込まない。
- コード・テスト変更は本計画への本人の明示的承認後にだけ開始する。

## レビューフォーカス

- `usinewgame` 後に局面がないまま `go` を受けても、前局の古い局面を再利用せず `ValueError` とする（`test_clears_position_when_usinewgame_received`）。
- `position` の未設定・不正入力は、誤った局面で手を返さず `ValueError` とする（`test_rejects_go_without_position`、`test_rejects_invalid_position_command`）。
- 合法手が空なら形式不正な `bestmove` や任意の手でなく `bestmove resign` を返す（`test_returns_resign_when_no_legal_moves`）。
- `searchmoves` を無視して制限外の手を返さず、認識済み未対応検索引数は診断して終了する（`test_rejects_unsupported_go_search_parameters`）。
- プロセス起動時に出力をflushし、標準出力をプロトコル専用に保ち、入力エラーを標準エラーへ出す（`test_entrypoint_flushes_protocol_and_bestmove`、`test_entrypoint_reports_invalid_position_on_stderr`）。

## ファイル構成

- 作成: `kaname_shogi/usi_engine.py` — USIコマンドループ、最新局面と乱数生成器の寿命、標準入出力を接続する起動入口。
- 作成: `tests/test_usi_engine.py` — 入出力関数を注入する機能テストと、起動入口を検証する対話型・エラーパスのサブプロセステスト。
- 作成: `docs/learning/57-usi-engine-response.md` — 本人の回答と補足、USI一次資料と実機観測の区別、TDD、Refactor、レビュー、検証、未解決事項を記録する。
- 作成: `docs/knowledge/usi-engine-response.md` — USI実行境界、状態、入出力、合法手応答、エラー契約を簡潔に記録する。
- 更新: `docs/plans/2026-10-03-usi-engine-response-design.md` — 実装・レビュー・検証の実績を、仕様と実績を分けて記録する。
- 更新: `docs/plans/2026-10-03-usi-engine-response-implementation-plan.md` — 実際に完了したステップと結果だけを記録する。
- 更新: `docs/README.md`、`docs/resume.md`、`docs/roadmap-usi-shogihome.md`、`docs/02-project-direction.md`、`README.md` — 現在テーマ・記録の参照先を必要な範囲で更新する。
- 変更しない: `kaname_shogi/cli.py`、`kaname_shogi/__main__.py`、`kaname_shogi/usi_move.py`、`kaname_shogi/usi_position.py`、`kaname_shogi/movegen.py`、`kaname_shogi/game_record.py`、`kaname_shogi/__init__.py`。既存CLIや既存の解析・合法手選択契約は変更せず利用する。

---

### Task 1: 注入可能なUSIコマンド処理を実装する

**ファイル:**
- 作成: `tests/test_usi_engine.py`
- 作成: `kaname_shogi/usi_engine.py`

**インターフェース (Interfaces):**
- 消費 (Consumes): `parse_usi_position(command: str) -> Position`、`legal_moves(position: Position) -> tuple[Move, ...]`、`choose_weak_move(moves, rng) -> Optional[Move]`、`format_usi_move(move: Move) -> str`。
- 生産 (Produces): `run_usi_engine(input_fn: Callable[[], str], output_fn: Callable[[str], None], rng: Optional[random.Random] = None) -> None`。入力関数は一行を返し、EOF時は `EOFError` を送出する。出力関数には改行なしの応答一行を渡す。未設定・不正局面、または未対応の既知検索引数は `ValueError` で呼び出し側へ伝える。

- [x] **ステップ1: 関数境界の振る舞いテストを作る**

`tests/test_usi_engine.py` に `UsiEngineFunctionTests` を作り、入力列から `EOFError` を送出する小さなテスト補助を用意する。各テストメソッド名は英語、日本語docstringは振る舞いと検出する誤りを説明する。

次のテストを作る。

1. `test_answers_usi_and_ready_in_order` — `usi`, `isready`, `quit` の入力に対し、出力が `id name kaname-shogi`、`id author kaname-shogi project`、`usiok`、`readyok` の順になることを確認する。
2. `test_ignores_setoption_gameover_and_unknown_commands` — `setoption`、`gameover lose`、未知コマンドに応答を出さず、処理を続けることを確認する。
3. `test_returns_legal_bestmove_from_replayed_position` — `position startpos moves 7g7f` の後に時計付き `go btime 591199 wtime 600000 byoyomi 30000` を渡す。応答が一つの `bestmove <token>` であり、`parse_usi_move(token)` が同じ局面の `legal_moves` に含まれることを確認する。
4. `test_returns_resign_when_no_legal_moves` — エンジンモジュール内の `legal_moves` を空タプルに差し替え、応答が `bestmove resign` となることを確認する。
5. `test_reuses_one_rng_across_go_and_usinewgame` — 起動時に作られる `random.Random` を一つに差し替え、二回の `go`（間に `usinewgame` と次の `position` を含む）が同じ生成器を使うことを確認する。
6. `test_clears_position_when_usinewgame_received` — `position`、`usinewgame`、`go` の順で入力し、古い局面を使わず `ValueError` になることを確認する。
7. `test_rejects_go_without_position` — 有効な `position` より前の `go` を `ValueError` とする。
8. `test_rejects_invalid_position_command` — `position startpos` や空の手順を通さず、既存パーサーの `ValueError` を伝える。
9. `test_rejects_unsupported_go_search_parameters` — 有効な局面後の `go searchmoves 7g7f`、`go depth 1`、`go nodes 1000`、`go mate 1`、`go infinite`、`go ponder` の各入力を `ValueError` とする。
10. `test_ignores_unknown_go_token` — 有効な局面後の `go mystery` は未知のトークンを無視し、合法な `bestmove` を返すことを確認する。
11. `test_stops_cleanly_on_quit_and_input_eof` — `quit` またはEOFで応答待ちを続けず正常終了することを確認する。

- [x] **ステップ2: 振る舞いのRedを確認する**

新モジュールがまだない状態でテストだけを実行し、まずimport失敗になることを確認する。その後、正しい名前・シグネチャで `run_usi_engine` が何もしない最小スタブを置き、同じテストを再実行する。期待する応答・例外アサーションがテスト本体で失敗することを確認する。import失敗だけをRed完了と扱わない。

実行:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine.UsiEngineFunctionTests -v
```

期待値: スタブに対する期待応答の不一致と、必要な `ValueError` が送出されない失敗が表示される。

- [x] **ステップ3: `run_usi_engine` を実装する**

`kaname_shogi/usi_engine.py` に上記シグネチャで関数を実装する。関数開始時に省略時の `random.Random` を一つ作り、`usinewgame` をまたいで使う。現在局面は未設定から開始し、`position` で置き換え、`usinewgame` でクリアする。USIコマンドは行単位に処理し、`usi` / `isready` の固定応答、`setoption` / `gameover` / 未知コマンドの無応答、`quit` / EOFの終了を行う。

通常の `go` では `Position` の有無を検査し、`searchmoves` / `depth` / `nodes` / `mate` / `infinite` / `ponder` を認識したら `ValueError` とする。未知のトークンは読み飛ばし、時計引数の値は使わず待たない。合法手列挙・選択・USI形式化は既存関数に委譲し、選択結果が `None` の場合は `bestmove resign` を出す。選択した手を内部局面へ適用しない。

公開docstringには引数、戻り値、副作用、EOFとValueErrorの境界、既存責務へ委譲する設計理由を日本語で記載する。

- [x] **ステップ4: 関数テストのGreenを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine.UsiEngineFunctionTests -v`

期待値: 11項目の振る舞いがすべて成功し、既存の `usi_position` / `movegen` / `usi_move` の契約を変更していない。

---

### Task 2: 標準入出力の実行入口とプロセス境界を作る

**ファイル:**
- 変更: `kaname_shogi/usi_engine.py`
- 変更: `tests/test_usi_engine.py`

**インターフェース (Interfaces):**
- 消費 (Consumes): タスク1の `run_usi_engine(input_fn, output_fn, rng=None)`。
- 生産 (Produces): `main() -> int` と `python -m kaname_shogi.usi_engine` のプロセス入口。正常終了は0、`ValueError` は標準エラー診断と非0終了にする。

- [x] **ステップ1: 実プロセスのテストを追加する**

`UsiEngineProcessTests` に次を追加する。

1. `test_entrypoint_flushes_protocol_and_bestmove` — `sys.executable -m kaname_shogi.usi_engine` を `Popen` で起動し、`usi` を送った後、終了させる前にID行2つと `usiok` を読む。続けて `isready` に `readyok`、時計付き `position` / `go` に合法な `bestmove` が返ることを読む。各行を短いタイムアウト付きで読み、改行・flushを確認する。`quit` 後に終了コード0、余分な標準出力なし、標準エラー空を確認する。
2. `test_entrypoint_reports_invalid_position_on_stderr` — 不正な `position` を標準入力へ渡すと、標準出力が空、標準エラーに診断があり、終了コードが非0となることを確認する。

対話テストはバイナリpipeを使い、`selectors.DefaultSelector` と `os.read` で到着済みデータをバッファし、改行がそろうまで有限時間待つ。これにより、flushされない応答や改行のない部分出力を、ブロックする `readline()` に頼らず検出する。タイムアウトやアサーション失敗時も `finally` で子プロセスを終了させる。

- [x] **ステップ2: 実行入口がない状態でプロセスの振る舞いRedを確認する**

テストはモジュール入口の追加前に実行する。`python -m` がUSI行を出さず正常終了する状態を観測し、期待する応答flushとエラー診断のアサーションが失敗することを確認する。

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine.UsiEngineProcessTests -v`

期待値: プロセス起動・import自体は成功するが、ID応答が読めないことと、エラー終了・stderr診断がないことをテスト本体が検出する。

- [x] **ステップ3: `main` とモジュール起動処理を実装する**

`main()` は標準入力の `readline()` がEOFを返した場合に `EOFError` として伝える入力関数、および応答一行を標準出力へ改行付きで書き `flush=True` で出す出力関数を作り、`run_usi_engine` に渡す。`ValueError` は標準エラーへ分かる診断を出し、1などの非0コードを返す。EOFと `quit` は0で終了する。`if __name__ == "__main__":` から `SystemExit(main())` を呼び出す。既存の `kaname_shogi.__main__` とCLI入口は変更しない。

- [x] **ステップ4: プロセステストのGreenを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine.UsiEngineProcessTests -v`

期待値: 対話プロセスが要求行への応答を終了前に返し、標準出力・標準エラー・終了コードの各アサーションが成功する。

---

### Task 3: Refactor判断、独立レビュー、記録と全体検証を行う

**ファイル:**
- 確認・必要時変更: `kaname_shogi/usi_engine.py`、`tests/test_usi_engine.py`
- 作成: `docs/learning/57-usi-engine-response.md`
- 作成: `docs/knowledge/usi-engine-response.md`
- 更新: 本計画、設計仕様、関連索引・現在地・ロードマップ

**インターフェース (Interfaces):**
- 消費 (Consumes): タスク1・2の公開関数、関数テスト、プロセステスト。
- 生産 (Produces): 承認済み範囲を満たし、独立レビュー・全体検証・学習／知識記録の確認を終えた作業ブランチ。

- [x] **ステップ1: Refactorの要否を判断する**

`usi_engine.py` のコマンド分岐、局面・乱数の寿命、標準入出力アダプターと、テストの補助処理の重複や過剰な抽象化を確認する。変更不要なら理由を計画と学習記録に残す。変更する場合は振る舞いを変えず、関数テストとプロセステストを再実行する。

実績: 処理責務とテスト補助は既に局所的だったため、構造を変えるRefactorは行わなかった。標準ライブラリのimport順だけを整え、専用13テストが成功した。

- [x] **ステップ2: 独立コードレビューを行い、指摘を解消する**

実装者と別のレビュアーが仕様・コード・テスト差分を確認し、Critical / Important / Minorを分類する。CriticalまたはImportantは解消し、同じテスト・全体検証を再実行した後に再レビューする。結果と対応を学習記録へ記す。

実績: 独立レビューはCritical 0、Important 0、Minor 0。任意の将来テスト案は学習記録へ記し、現在の機能欠陥ではないため追加修正はなかった。レビューで未判定とされた範囲の判断は計画の実行台帳に記録した。

- [x] **ステップ3: 専用テスト、全体テスト、差分を検証する**

実行:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
git diff --cached --check
```

期待値: 専用テストと全テストが成功し、差分検査で空白エラーがない。レビュー後にコードを修正した場合は、これらを再実行する。ShogiHome実対局を確認済みとは記録しない。

実績: 文書反映後に専用13/13件、全277/277件が成功した。`git diff --check` と `git diff --cached --check` も成功し、レビュー後の製品コード変更はなかった。

- [x] **ステップ4: 学習記録、確定知識、現在地文書を実績に合わせる**

学習記録では、本人の各回答とアシスタント補足、USI一次資料と第54回の使い捨てプローブ、第56回の通常手観測、今回自動テストで確認する挙動、ShogiHomeで未確認の挙動を分ける。TDD Red/Greenの実際の出力、Refactor判断、独立レビューのCritical / Important / Minor、検証結果、次回にコマンド型／独立状態APIを再検討する問いを記録する。知識メモには公開契約とエラー・状態境界のみを簡潔に記す。設計書・本計画には完了した手順だけを実績として反映する。

必要な参照更新は `docs/README.md`、`docs/resume.md`、`docs/roadmap-usi-shogihome.md`、`docs/02-project-direction.md`、`README.md` に限定し、第5項の実対局を未実施として保持する。学習記録と知識メモを本人へ提示して内容確認を得る。

`docs/next-topics.md` は第56回後に本テーマを選定した記録がすでにあり、内容は現在も正しい。新しい候補の選定は最終理解確認後に行うプロジェクト方針のため、今回は変更しない。

実績: 学習記録と知識メモ、README、索引、再開案内、ロードマップ、プロジェクト方向性を実績に合わせた。2026-10-03に本人が学習記録と確定知識を確認し、この内容で承認した。`docs/next-topics.md` は最終理解確認後の候補レビューに合わせて今回は変更していない。

- [x] **ステップ5: 確認済み記録と実装を作業ブランチにコミットする**

学習記録・知識メモの確認後、実装・テスト・計画・必要な索引更新をステージする。`git diff --cached --check` を確認し、日本語Conventional Commitとして `feat: USIエンジンが一手を返す` を作成する。`main` への取り込みは別の本人承認まで行わない。

実績: 承認済みの11ファイルをステージし、`git diff --cached --check` 成功後に `feat: USIエンジンが一手を返す` を作業ブランチへコミットした。`main` への取り込みは未実施。

---

## テーマ完了後のゲート

本テーマの実装・レビュー・記録と、本人が承認した方法での取り込み・取り込み先検証が終わった後に、最後の理解確認を一問だけ出す。本人の回答・補足を学習記録へ追記し、確認後に `docs/next-topics.md`、README、プロジェクト方向性を見直す。回答を得る前に次テーマの学習・実装へ進まない。

## 実行方法の提案

公開関数とプロセスアダプターは一つのモジュールで連続した責務を持つため、同一実装者がこのセッションで順にTDDを進めるネイティブ実行を推奨する。プロジェクト方針に従い、実装後のコードレビューは独立したレビュアーが行う。
