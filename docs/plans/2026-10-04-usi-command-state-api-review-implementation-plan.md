# 第58回「USIコマンド型・独立状態APIの導入要否を再検討する」実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキルまたは `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**状態:** 設計仕様、本実装計画、実績文書は本人が承認済み。実装・独立レビュー2回・専用17テスト・全体281テスト・最終理解確認が完了し、2026-10-04に `main` へfast-forwardで取り込み済み。取り込み後の全体281テストも成功。ShogiHome実対局はロードマップ第5項に残る。

**目標:** USIコマンド行の文字列分岐を保ったまま、最新 `Position` のライフサイクルだけを担う非公開 `_UsiEngineState` を導入し、既存のUSI応答を維持する。

**アーキテクチャ:** `_UsiEngineState` は未設定または最新の `Position` だけを保持し、置換・消去・取得を担う。`run_usi_engine` が引き続きコマンド行、乱数生成器、合法手選択、応答を扱い、`go` の局面を状態オブジェクトから取得する。

**技術スタック:** Python、標準ライブラリ、`unittest`。

**仕様 (Spec):** [第58回設計仕様](2026-10-04-usi-command-state-api-review-design.md)

**グローバル制約 (Global Constraints):**
- コマンド行を表す型は導入しない。`run_usi_engine` が文字列を分割し、現在の文字列分岐を維持する。
- 保持するのは最新の `Position` または未設定を示す `None` だけとする。
- `_UsiEngineState` は `usi_engine.py` 内に置き、package rootや他モジュールから再exportしない。
- 乱数生成器は `run_usi_engine` の実行中に一つ用意し、現在の `choose_weak_move(moves, rng)` へ渡す。
- `usinewgame` の後も同じ乱数生成器を使う。
- ShogiHome実機テストは行わず、ローカルの自動テストをGUI互換性の証拠として扱わない。

## レビューフォーカス (Review Focus)

- `position` より前の `go` は初期局面を暗黙に作らず `ValueError` となり、`bestmove` を出さないこと。
- `usinewgame` の後、次の `position` より前の `go` は前局面を再利用せず `ValueError` となること。
- 複数の `position` を受けた後の `go` は最後に受けた局面を使うこと。
- `usinewgame` をまたぐ複数の `go` でも、実行中の乱数生成器は同じ一つであること。
- 不正な `position` はプロトコル応答へ混ざらず、プロセス入口のstderr診断と非0終了の契約を保つこと。

---

## ファイル構成

- 変更: `kaname_shogi/usi_engine.py` — 非公開状態オブジェクトを定義し、既存のコマンド分岐から利用する。
- 変更: `tests/test_usi_engine.py` — 状態オブジェクトの契約とコマンドループとの接続を確認する。既存の関数・プロセステストは回帰確認に使う。
- 作成: `docs/learning/58-usi-command-state-api-review.md` — 本人の設計選択、実施内容、検証、独立レビュー、未解決事項を実績として記録する。
- 更新: `docs/knowledge/usi-engine-response.md` — USI実行中の局面保持方法と、乱数器の責務を現在の実装に合わせる。
- 更新: `docs/plans/2026-10-04-usi-command-state-api-review-design.md` — 設計仕様の承認状態を、現在の進行段階に合わせる。
- 更新: `docs/README.md` — 第58回の学習記録、設計仕様、実装計画を索引に加える。

`README.md`、`docs/02-project-direction.md`、`docs/next-topics.md`、`docs/resume.md`、ロードマップの現在地は、統合後の最終理解確認に本人が回答した後で見直す。ShogiHomeでの実対局やCLIの変更は行わない。

## Task 1: 非公開状態オブジェクトを追加してコマンド処理へ接続する

**ファイル:**
- 変更: `tests/test_usi_engine.py`
- 変更: `kaname_shogi/usi_engine.py`

**インターフェース (Interfaces):**
- 消費 (Consumes): `parse_usi_position(command: str) -> Position`、`legal_moves(position: Position)`、`choose_weak_move(moves, rng)`。
- 生産 (Produces): モジュール内だけの `_UsiEngineState()`、`replace_position(position: Position) -> None`、`clear_position() -> None`、`require_position() -> Position`。未設定時の `require_position` は現在の `go` と同じ `ValueError` を送出する。

- [x] **ステップ1: 状態オブジェクトの契約テストと最新局面の接続テストを書く**

`UsiEngineStateTests` に次の3テストを追加する。テスト用の `create_state()` 補助は `getattr(usi_engine, "_UsiEngineState", None)` が非 `None` であることを `assertIsNotNone` で確かめてから生成する。こうするとRed時もモジュールのimport失敗ではなく、期待する型がまだないというテスト内の明示的な失敗になる。

1. `test_requires_position_when_unset` — 新しい状態の `require_position()` が `ValueError` を送出する。
2. `test_replaces_position` — `replace_position(first)` の後は `first` を返し、`replace_position(latest)` の後は同一オブジェクト `latest` を返す。
3. `test_clears_position` — 設定済み状態を `clear_position()` した後の `require_position()` が `ValueError` を送出する。

加えて `UsiEngineFunctionTests.test_uses_most_recent_position_before_go` を作る。実際の `parse_usi_position` と `legal_moves` を記録用ラッパー越しに呼び、`position startpos moves 7g7f`、`position startpos moves 2g2f`、`go` の後で `legal_moves` が2回目の解析結果そのものを受け取ったことを `assertIs` で確認する。返答がその局面で合法な `bestmove` であることも確認する。`Position` の値比較では独立した `Board` を同値判定できないため、別途解析した局面との `assertEqual` は使わない。

テストメソッド名は英語とし、日本語docstringの先頭行に振る舞い、続く本文に検出したい誤りを書く。

- [x] **ステップ2: 新しい状態契約のRedを確認する**

実行:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine.UsiEngineStateTests -v
```

期待値: モジュールは読み込まれ、3つのテストが `_UsiEngineState` の未実装を示す `assertIsNotNone` の失敗になる。importや構文のエラーだけをRed完了とは扱わない。

- [x] **ステップ3: `kaname_shogi/usi_engine.py` に最小の `_UsiEngineState` を実装する**

`Position` を `.model` からimportし、`__init__(self) -> None` で `self._position: Optional[Position] = None` とする。`replace_position` は受け取った参照をそのまま保持し、`clear_position` は `None` に戻し、`require_position` は未設定時に既存と同じ `ValueError` を送出して設定済みなら保持参照を返す。コマンド解析、乱数、棋譜、合法手選択をこのクラスへ追加しない。

- [x] **ステップ4: 状態契約テストのGreenを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine.UsiEngineStateTests -v`

期待値: 未設定・置換・消去の3テストが成功する。

- [x] **ステップ5: `run_usi_engine` の局面変数を状態オブジェクトへ置き換える**

関数開始時に `_UsiEngineState()` を一つ作る。`position` は現在どおり `parse_usi_position(command)` を先に完了してから `replace_position` へ渡し、`usinewgame` は `clear_position` を呼ぶ。`go` は `require_position()` の戻り値を `legal_moves` へ渡す。`engine_rng` の生成位置・寿命と、その他の分岐・応答は変えない。

- [x] **ステップ6: 専用USIテストで接続と既存契約を確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine -v`

期待値: 状態テスト、新しい最新局面テスト、既存の関数・プロセステストがすべて成功する。未設定 `go`、`usinewgame` 後の消去、乱数器再利用、合法な一手、stdout/stderr、flush、終了コードの契約に差がない。

## Task 2: Refactor、独立レビュー、記録、全体検証を行う

**ファイル:**
- 確認・必要時変更: `kaname_shogi/usi_engine.py`、`tests/test_usi_engine.py`
- 作成: `docs/learning/58-usi-command-state-api-review.md`
- 更新: `docs/knowledge/usi-engine-response.md`、`docs/plans/2026-10-04-usi-command-state-api-review-design.md`、`docs/README.md`
- 更新: この実装計画（実際の変更、検証結果、未完了項目）

**インターフェース (Interfaces):**
- 消費 (Consumes): タスク1の非公開 `_UsiEngineState` と既存の `run_usi_engine`。
- 生産 (Produces): 設計仕様と一致し、Critical / Important の指摘を解消し、専用・全体テストと記録を確認済みの作業ブランチ。

- [x] **ステップ1: Refactorの要否を判断する**

状態クラスが局面ライフサイクルだけを担い、`run_usi_engine` にコマンド分岐と選択処理が残っていることを確認する。重複や不要な抽象化がなければ追加Refactorを行わず、その理由を学習記録へ書く。変更した場合はタスク1の専用テストを再実行する。

- [x] **ステップ2: 独立したコードレビューを受ける**

実装者とは別のレビュアーが、承認済み仕様とコード・テスト差分を確認し、Critical / Important / Minorを分類する。CriticalまたはImportantがあれば修正し、専用・全体テストを再実行して再レビューを受ける。指摘と対応、または指摘なしの結果を学習記録へ記す。

先行レビューと最終独立レビューの両方でCritical 0、Important 0、Minor 0、修正不要。最終レビューでは文書一式も照合し、専用17件・全体281件・差分確認の成功を再確認した。

- [x] **ステップ3: 確定知識と学習記録を実績に合わせて更新する**

`docs/knowledge/usi-engine-response.md` では「関数内で局面を保持する」を、非公開 `_UsiEngineState` が `Position` だけを保持する契約へ更新する。乱数器は引き続き `run_usi_engine` が保持し、状態オブジェクトに選択方式を含めないことも記す。学習記録には確認済みの設計選択、実際の変更、実行した検証、Refactor判断、独立レビュー、未確認事項を記録し、未回答の理解確認を回答済みと書かない。`docs/README.md` に第58回の記録と計画へのリンクを加える。

- [x] **ステップ4: 専用テスト・全体テスト・差分を検証する**

実行:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
```

期待値: 専用USIテストとREADMEに記載された全テストが成功し、`git diff --check` に出力がない。ShogiHomeのGUI互換性を示す結果として報告しない。

- [x] **ステップ5: 文書を提示して確認を待ち、承認後にコミットする**

学習記録・知識メモ・計画の差分、独立レビュー結果、テスト結果を本人へ提示し、文書内容の明示承認を得た。関連ファイルをステージし、`git diff --cached --check` と `git status --short --branch` で確認して作業ブランチへコミットする。

## この計画の後に残る承認ゲート

- 実装計画の明示承認後にのみコード・テスト変更を開始する。
- 実装・検証・レビュー・記録後、本人の選択「1. ローカルで `main` にマージする」を受け、2026-10-04にfast-forwardで統合した。
- 取り込み先の全体テスト281件が成功した。
- AGENTS.mdに従い、取り込み先検証後に最終理解確認を一問だけ行い、本人の回答とアシスタントの補足を学習記録へ記録した。続いて `docs/next-topics.md`、README、プロジェクトの方向性、再開案内を見直した。本人は次テーマとしてShogiHomeでの平手対局を選び、新しいセッションの準備を依頼した。次テーマの実作業は引き継ぎプロンプト入力後に始める。
- ShogiHomeでの実対局はロードマップ第5項の後続テーマとし、この計画では行わない。
