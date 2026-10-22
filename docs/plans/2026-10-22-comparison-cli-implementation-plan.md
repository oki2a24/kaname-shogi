# 比較CLI 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 承認済みの比較設計に従い、同一ソース内の二方式を指定局面・組数・手数上限で対局させ、条件・局ごとの記録・記述集計を専用CLIから保存する。

**アーキテクチャ:** `comparison.py` に比較条件・予定・一局進行・集計、`comparison_io.py` に局面セット検証とJSON/ファイル境界、`compare_games.py` に専用CLI接続を置く。既存の `GameRecord`、`MoveSelectionPolicy`、`game_search.choose_move`、`RepetitionTracker` を利用し、通常CLI・USIには接続しない。

**技術スタック:** Python 3.9互換、標準ライブラリ、`unittest`、既存の将棋局面・探索・棋譜API。

**仕様 (Spec):** [承認済み比較設計](2026-10-21-engine-comparison-design.md)、[確定済み千日手知識](../knowledge/repetition-rule.md)、[千日手設計](2026-10-22-repetition-rule-design.md)

このP2は補助テーマの実装であり、完了・確認後は主線の最初の評価項目A1へ戻る。A1の評価要素や実装範囲はこの計画では先取りしない。

## グローバル制約 (Global Constraints)

- 専用の比較CLIを作り、通常対局メニューへ設定を追加しない。
- 比較する五方式は `random`、`material`、`two-ply-material`、`full-width-4`、`alpha-beta-4` とし、既存の深さ・評価・同点選択を変えない。
- 各引数を必須とし、未知引数・不正入力・全局面の不正を対局開始前に拒否する。出力先は既存なら拒否する。
- 一組は同じ開始局面で二局を行い、二局目は方式の先後だけを交換する。盤面・駒の所属は反転しない。
- 開始局面履歴は比較開始位置を一回目として作り、準備手順を比較対局の千日手履歴・手数・計時に含めない。
- 一局ごとに独立した `GameRecord`、`RepetitionTracker`、方式ごとの乱数生成器を使う。
- `RepetitionTracker.add_position()` は成功した実着手の確定後に一度だけ呼ぶ。探索局面・失敗手を履歴へ加えない。
- `FOURFOLD_CONTINUE` は継続であり終局にしない。5回目の出現による `REPETITION` は勝者なしで終了する。通常千日手の指し直し・再戦は開始しない。
- `PERPETUAL_CHECK_LOSS` は負け側と反対側を勝敗に算入する。`UNRESOLVED_DOUBLE_PERPETUAL_CHECK` から勝者を作らない。
- 終局確認は千日手・連続王手、合法手なし、手数上限の順とし、手数上限ちょうどの実着手後にも千日手APIを評価する。
- 計時は `time.monotonic_ns` を使い、当該局面の合法手生成直前から選択操作の返却までとする。
- JSONを再解析の正本とし、各局の記録を集計より先に原子的に保存する。通常Ctrl-Cは保存後130、故障・保存失敗は1、入力不正は2、全局完了・保存成功は0。
- 統計による棋力判定、自動採用、Elo、SPRT、信頼区間、勝率・0.5点換算・引き分け数を実装しない。
- 通常CLI・USIの仕様や接続、通常CLIのSFEN入出力、自動再戦、自動再試行、並列対局、外部エンジン、持将棋・入玉の独自裁定を変更・追加しない。
- 英語の公開型・操作名は日本語の意味とデータか操作かをdocstringで説明する。テストメソッド名は英語、日本語docstringを付ける。
- 既存の Python 3.9互換性を保ち、依存パッケージと Ruff ルールを追加しない。

## 承認済みの仕様調整

千日手APIは双方の連続王手を `UNRESOLVED_DOUBLE_PERPETUAL_CHECK` として返す。一方、承認済み比較設計の終了理由表・summaryには専用識別子と件数がなく、`repetition` は通常千日手の件数として定義されている。双方連続王手を通常千日手へ加えると結果分類を誤り、勝敗へ加えると確定APIに反する。

**調整内容:** 局ごとの終了理由 `unresolved_double_perpetual_check` とsummaryの同名件数を追加する。勝者はnullとし、`repetition` 件数・基準勝ち・候補勝ちへ加えない。これは実装済みAPIの未裁定結果をJSON・画面で失わず表すための最小追加である。新しい裁定・再戦・得点換算は導入しない。

本人は2026-10-23に計画全体とこの出力契約の拡張を明示承認した。双方連続王手の未裁定を独立した終局理由・集計件数にし、勝者・通常千日手・勝敗件数へ変換しないことを確定仕様として実装する。

## ファイル構成

- 作成: `kaname_shogi/comparison.py` — 不変の比較データ、予定生成、一局進行、終局理由、記述集計。
- 作成: `kaname_shogi/comparison_io.py` — JSON厳密検証、開始局面の合法再生、環境情報・指紋、JSON変換と原子的保存。
- 作成: `kaname_shogi/compare_games.py` — argparse入口、標準出力/標準エラー、Ctrl-C・例外・終了コード境界。
- 作成: `data/comparison/start-positions-v1.json` — 承認設計の動作確認用4局面。
- 作成: `tests/test_comparison.py` — 予定、対局、千日手境界、終局理由、集計。
- 作成: `tests/test_comparison_io.py` — 入力・JSON・指紋・原子的保存。
- 作成: `tests/test_compare_games.py` — 引数・表示・終了コード・専用入口。
- 変更: `docs/README.md`、`README.md`、`docs/resume.md`、`docs/learning/engine-comparison-design.md` — 完了後の実際の範囲・検証・レビュー・限界を反映する。READMEは実行可能な利用案内を加える段階で更新。

## 公開データ・操作契約案

`comparison.py` が提供する。

- `ComparisonPosition(position_id: str, setup_moves: tuple[str, ...], rationale: str, start_position: Position, start_sfen: str, initial_move_number: int)` は局面セットの一項目データ。`start_position` は合法手順再生後、`start_sfen` はその正規化表記。
- `ComparisonConfig(baseline: MoveSelectionPolicy, candidate: MoveSelectionPolicy, positions: tuple[ComparisonPosition, ...], pairs_per_position: int, seed: int, max_plies: int, output_dir: Path, positions_path: Path, positions_json: bytes)` は検証済み条件データ。入力ファイルを実験開始後に変更されても条件JSONへ読込時点の内容を保存できるよう、引数の元パスと読込バイト列を保持する。
- `ScheduledGame(game_id: str, position_id: str, pair_number: int, game_number_in_pair: int, baseline_side: Side, candidate_side: Side, baseline_seed: int, candidate_seed: int)` は一局の予定データ。組番号 `q = position_index * K + repetition_index`、方式別種は `S+2*q` / `S+2*q+1`。
- `GameResult(schedule: ScheduledGame, start_sfen: str, initial_move_number: int, record: GameRecord, reason: GameEndReason, winner_side: Side | None, winner_policy: MoveSelectionPolicy | None, plies: int, move_times_ns: tuple[MoveTiming, ...], unfinished_calculation_ns: int | None, error: str | None)` は局の確定結果データ。`record` は失敗していない成功手のみを持つ。
- `GameEndReason` は `checkmate`、`no_legal_move`、`perpetual_check_loss`、`repetition`、`unresolved_double_perpetual_check`、`ply_limit`、`interrupted`、`error` を表す列挙値。
- `BatchStatus` は `running` / `complete` / `interrupted` / `error` のバッチ状態を表す列挙値。
- `MoveTiming(ply: int, side: Side, policy: MoveSelectionPolicy, move: Move, elapsed_ns: int)` は成功手一つの計時データ。
- `run_game(schedule: ScheduledGame, position: ComparisonPosition, config: ComparisonConfig, *, clock_ns: Callable[[], int] = time.monotonic_ns) -> GameResult` は独立した一局を進行する操作。
- `make_schedule(config: ComparisonConfig) -> tuple[ScheduledGame, ...]` は全局の決定的予定を作る操作。
- `summarize(config: ComparisonConfig, results: Sequence[GameResult], *, batch_status: BatchStatus, unstarted_games: int, elapsed_ns: int) -> dict[str, object]` は定義済み件数と方式別計時のsummary JSONデータを作る操作。

`comparison_io.py` が提供する。

- `load_positions(path: Path) -> tuple[ComparisonPosition, ...]` は局面セット全体を厳密検証する操作。
- `load_config(argv: Sequence[str]) -> ComparisonConfig` はCLI引数と局面全件を検証し、出力先作成前の条件データを作る操作。
- `conditions_payload(config: ComparisonConfig, schedule: Sequence[ScheduledGame], *, source_root: Path) -> dict[str, object]`、`game_payload(result: GameResult, config: ComparisonConfig, *, conditions_sha256: str)`、`summary_payload(summary: Mapping[str, object])` はそれぞれJSON値へ変換する操作。`source_root` はリポジトリルート。
- `atomic_write_json(path: Path, payload: Mapping[str, object]) -> None` は同一ディレクトリ一時ファイルから置換する操作。
- 条件JSON、局JSON、summary JSONの厳密なキーは各タスクでテスト内の独立期待値として固定し、承認設計の必須情報を落とさない。

**確定したJSONキー:** 条件JSONは `format`、`baseline`、`candidate`、`positions_file`、`positions_sha256`、`positions`（各 `id/setup_moves/rationale/start_sfen/initial_move_number`）、`pairs_per_position`、`seed`、`max_plies`、`schedule`（各 `game_id/position_id/pair_number/game_number_in_pair/baseline_side/candidate_side/baseline_seed/candidate_seed`）、`timing`（単調時計と計測境界）、`clock`（時計制御なしのnull）、`repetition`、`git`（`head/dirty/diagnostic`）、`runtime`、`source_sha256` を持つ。局JSONは `format`、`conditions_sha256`、予定8キー、`baseline`、`candidate`、`start_sfen`、`initial_move_number`、`plies`、`reason`、`winner_side`、`winner_policy`、`record`、`move_times`、`unfinished_calculation`、`error` を持つ。既存棋譜v1は変更せず埋め込む。summary JSONは `format`、`status`、`planned_games`、`started_games`、`ended_games`、`unstarted_games`、`completed_pairs`、`partial_pairs`、8種類の排他的な `results`、`perpetual_check_losses`（敗者側別・終局件数とは別枠）、`by_position`（`started_games/results`）、`by_side`（先後別の生 `games/wins/losses/no_winner` 件数）、`move_time_by_policy`（全5方式の `successful_moves/total_ns/average_ns/max_ns`）、`elapsed_ns`、`statistical_decision`（未実施のnull）を持つ。方式別平均は合計ns÷成功手数で、成功手数0なら平均と最大はnull。summaryは勝率や統計的判定を出さない。局識別子は `game-000001` 形式とし、ディレクトリ内で一意にする。このネスト・キー・null可否・型をTask 3のテスト期待値へ固定した。

`compare_games.py` は `main(argv: Sequence[str] | None = None) -> int` を提供し、`python3 -m kaname_shogi.compare_games` で実行可能にする。

## レビューフォーカス (Review Focus)

1. 4回目通常出現後に打開して5回目へ至る局：4回目は続行し、直近4出現で判定された5回目だけが千日手終局となり、再戦を始めない。
2. 千日手が `max_plies` ちょうどで成立する局：上限による未決着より千日手を優先し、通常千日手は勝者なしの別件数にする。
3. 片側または双方が連続王手の局：片側負けは相手の方式の勝ち、双方未裁定は勝者なし・通常千日手とは別件数にする。
4. 後半局面に不正な準備手順または不正なJSONキーがある実験：出力先を作らず、一局も開始しない。
5. 探索・局ファイル保存・summary保存中の例外またはCtrl-C：確定手・確定局だけを保存し、勝敗や完了局数へ未完了局を混ぜず、指定終了コードを返す。

## タスク 1: 条件・開始局面セット・対局予定の入力契約

**ファイル:** `kaname_shogi/comparison_io.py`、`kaname_shogi/comparison.py`、`data/comparison/start-positions-v1.json`、`tests/test_comparison_io.py`、`tests/test_comparison.py`。

**消費:** `MoveSelectionPolicy`、`create_initial_position()`、`parse_usi_move()`、`GameRecord.apply_move/apply_drop`、`format_sfen()`、`RepetitionTracker`。

**生産:** 上記 `ComparisonPosition`、`ComparisonConfig`、`ScheduledGame`、`load_positions()`、`load_config()`、`make_schedule()`。

**検出範囲・未検証:** 専用テストは全入力の厳密性、全局面の遅延失敗、同一局面正規化、開始位置と準備履歴の境界、予定順・先後・種の算式を検出する。関連テストはUSI手解析・合法手適用・SFEN変換の規則を補完し、全体テストは既存入口とのimport回帰を検出する。実際の全局面空間、Unicode/特殊ファイルシステム差、OS間のファイル名・パス差は未検証。

- [x] **ステップ1: 独立期待値を持つ入力・予定テストを作成**

  局面セット4件のID、準備手順、理由、生成SFENを設計値と照合する。全件を検証し、未知キー・欠落キー・重複JSONキー・未知format・空配列・重複ID・盤面持ち駒手番を正規化した同一局面・不正な最後の準備手・準備中終局を個別拒否する。`type(x) is int` でないJSON整数欄（真偽値を含む）、0以下の組数/手数、負種、同一方式、未知方式、既存出力先、未知CLIオプションも拒否する期待を明記する。エラー全件について出力先が存在しないことを検査する。

  予定は局面2件・K=2の8局について手書きの `q`、順序、基準/候補の先後交換、種 `S+2q` と `S+2q+1` を照合する。後手番開始局面でも方式の担当だけを交換し、局面・駒所有を反転しないことを確認する。

- [x] **ステップ2: 対象テストを実行して仕様上の失敗を確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_comparison_io.py' -v` と `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_comparison.py' -v`

  期待値: 未実装データ・操作による対象振る舞いの失敗。テスト自体のimport/構文失敗はRedとして数えない。

- [x] **ステップ3: 入力・予定データを実装**

  重複キー検出付きJSON object hookを使う。準備手順は平手初期局面から既存 `parse_usi_move` と `GameRecord` で再生し、比較開始位置に新しい `RepetitionTracker` を作って準備中終局と開始時合法手なしを拒否する。比較履歴へ準備履歴を持ち込まない。局面同一性は盤面・両手・手番の完全値で検査する。全CLI引数・全局面検証が終わるまで出力先を作らない。予定順と乱数式は設計どおり固定する。

- [x] **ステップ4: 対象テストを再実行**

  実行: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_comparison_io.py' -v` と `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_comparison.py' -v`

  期待値: この2モジュール全件PASS。全局面検証失敗前の副作用なし、独立予定値、先後交換を照合。

- [x] **ステップ5: Refactor要否と差分を確認**

  実行: `.venv/bin/ruff format kaname_shogi/comparison.py kaname_shogi/comparison_io.py tests/test_comparison.py tests/test_comparison_io.py`、`.venv/bin/ruff check kaname_shogi/comparison.py kaname_shogi/comparison_io.py tests/test_comparison.py tests/test_comparison_io.py`、`git diff --check`、`git diff`。

  期待値: 整形・check・差分確認成功。入力検証と予定生成の責務が混線していないか確認。

## タスク 2: 一局進行と千日手・終局・計時境界

**ファイル:** `kaname_shogi/comparison.py`、`tests/test_comparison.py`。

**消費:** Task 1の `ComparisonConfig` / `ComparisonPosition` / `ScheduledGame`、`GameRecord`、`legal_moves()`、`game_search.choose_move()`、`RepetitionTracker.add_position()`、`RepetitionOutcomeKind`。

**生産:** `GameEndReason`、`MoveTiming`、`GameResult`、`run_game()`。

**検出範囲・未検証:** 専用テストは一局内の手確定、四回目/五回目境界、終局優先順位、敗者視点、乱数・履歴の局間独立、時間計測境界を検出する。関連テストは合法手生成・GameRecord・千日手判定・既存五方式の内部挙動を補完し、全体テストは既存対局やUSIの回帰を検出する。探索方式自体の全局面での正しさ、実時間応答、時計のOS精度、実対局の棋力は未検証。

- [x] **ステップ1: 対局状態遷移テストを作成**

  固定された偽探索で各終局理由を作り、独立した局面・履歴・結果から勝者と手数を照合する。先手詰み/後手詰みまたは手なしを反転し勝者視点固定を検出する。通常循環を4回出現させた時点では `FOURFOLD_CONTINUE` のまま次手を探索し、打開を挟んだ5回目だけ `REPETITION`・勝者なし・再戦なしとする。王手循環の4回目と5回目について、`PERPETUAL_CHECK_LOSS.losing_side` の反対側方式だけを勝ちとし、王手側を勝者にする誤りを検出する。双方連続王手を専用理由の未裁定・勝者なし・通常千日手とは別件数に保つ。`max_plies=1` と、千日手が上限ちょうどに成立する対局で優先順位を照合する。

  局間で前局の手・反復tracker・乱数状態が次局へ漏れないこと、方式ごとに同じ専用乱数を割り当て、相手の乱数消費が他方へ影響しないことを確認する。探索が非空候補からNoneまたは候補外手を返す、探索例外、適用失敗では未確定手を棋譜・反復・成功手数へ加えず、後続局へ進めないことを確認する。偽単調時計で合法手生成前から選択返却までだけを含め、適用・判定・保存を含めないこと、時計逆行を故障にすることを検査する。

- [x] **ステップ2: 対象テストで意図した失敗を確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_comparison.py' -v`

  期待値: 一局操作未実装または振る舞い不一致による失敗。千日手API読み込み失敗だけでRedとしない。

- [x] **ステップ3: `run_game()` と状態データを実装**

  成功手の適用を一時局面で準備して検証後に確定し、確定局面を一度だけtrackerへ渡す。開始時・成功手後は反復終局→合法手なし→手数上限の順で確認する。`FOURFOLD_CONTINUE` は継続、`REPETITION` は勝者なし、`PERPETUAL_CHECK_LOSS` は敗者の反対側の勝者、双方連続王手は勝者なしにする。各局に独立 `GameRecord` / `RepetitionTracker` / 方式別 `random.Random` を作る。一手時間は全合法手生成の直前から `choose_move` の返却までを計測する。未完了計算時間は成功手計時と分離する。

- [x] **ステップ4: 一局テストを再実行**

  実行: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_comparison.py' -v`

  期待値: 対象モジュール全件PASS。千日手の4→5境界、上限優先順位、勝者、成功手だけの記録を個別に確認。

- [x] **ステップ5: Refactor要否と差分を確認**

  実行: `.venv/bin/ruff format kaname_shogi/comparison.py tests/test_comparison.py`、`.venv/bin/ruff check kaname_shogi/comparison.py tests/test_comparison.py`、`git diff --check`、`git diff`。

  期待値: 検査成功。API結果から比較結果への変換に通常千日手・連続王手・未裁定の混同がない。

## タスク 3: JSON記録・原子的保存・集計

**ファイル:** `kaname_shogi/comparison_io.py`、`kaname_shogi/comparison.py`、`tests/test_comparison_io.py`、`tests/test_comparison.py`。

**消費:** Task 1の条件・予定、Task 2の `GameResult`、`GameRecord.to_payload()`、標準 `hashlib`・`platform`・`sys`。

**生産:** `conditions_payload()`、`game_payload()`、`summary_payload()`、`summarize()`、`atomic_write_json()`。

**検出範囲・未検証:** 専用テストはJSON契約・ハッシュの正規化・勝者と排他理由・集計恒等式・保存失敗時の既存ファイル保持を検出する。関連テストは既存棋譜v1の形と再読込可能性を補完し、全体テストは標準ライブラリ利用や既存保存境界との回帰を検出する。複数ファイルをまたぐトランザクション、強制終了・電源断・媒体障害後の復旧は未検証であり保証しない。

- [x] **ステップ1: 記録・集計の独立期待値テストを作成**

  条件JSONはフォーマット版、全引数、入力局面セット内容とSHA-256、生成開始SFEN、予定ID/担当/種、計時境界、時計なし、千日手方針、Git HEAD/変更有無、Python/OS/機器、`.py` ソース指紋をキー単位で固定する。ソース指紋は `kaname_shogi` 以下の全 `.py` をPOSIX相対パスのUTF-8バイト列で辞書順に並べ、各ファイルについて4バイト符号なしbig-endianのパス長、パス、8バイト符号なしbig-endianの内容長、内容を連結してSHA-256へ渡す。途中の区切りを省く、絶対パスで環境依存にする、未追跡Pythonを落とす誤りを検出する。Git情報不能ならnullと診断、dirtyフラグありならHEADのみで内容が復元できると主張しない。

  局JSONは条件SHA、予定ID、両方式の先後、開始SFEN/由来手数、成功手数、終了理由、勝者の先後と方式、既存棋譜v1、各成功手の手番/方式/USI手/時間ns、未完了計算・故障情報を検査する。JSONの勝者は詰み・合法手なし・連続王手負けだけに存在し、通常千日手・手数上限・中断・故障・未裁定ではnullであることを確認する。

  手書き結果群から予定/開始/理由別終了/未実行/完了組/片局組/方式別成功手数・合計・平均・最大を計算し、全理由の合計=開始局数、連続王手内訳の非二重加算、0手平均=nullを検査する。千日手件数と未裁定件数を混同しない。局面別・先後別に全体値へ照合できる。勝率等が出力されないことも確認する。

  `atomic_write_json()` について成功・置換・書込/置換失敗時に確定済みファイルを保ち、一時ファイルを後始末する契約を検査する。局保存がsummaryより先であり、保存失敗を成功へ見せない。

- [x] **ステップ2: 対象テストで仕様上の失敗を確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_comparison_io.py' -v` と `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_comparison.py' -v`

  期待値: JSON変換・集計・保存の未実装振る舞いによる失敗。

- [x] **ステップ3: 保存値・集計・原子的書込を実装**

  条件・局・summaryを純粋な辞書変換にする。局棋譜には `GameRecord.to_payload()` を埋め込み、既存v1を拡張しない。各JSONを同じ出力先内の一時ファイルへ書いて置換し、局結果を先に確定してから保存済み局ファイル相当の結果でsummaryを作り直す。平均は成功手数0ならnull。排他的な終了理由は相互排他的に数え、perpetual-check内訳を勝敗と別枠にする。

- [x] **ステップ4: JSON・集計テストを再実行**

  実行: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_comparison_io.py' -v` と `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_comparison.py' -v`

  期待値: 両対象全件PASS。変換値・集計値は手書き期待と一致し、保存失敗の既存記録保持を確認。

- [x] **ステップ5: Refactor要否と差分を確認**

  実行: Ruff format/check、`git diff --check`、`git diff`。

  期待値: 検査成功。JSON変換とファイル副作用、集計と勝敗判定の責務境界を確認。

## タスク 4: 専用CLI・バッチ停止・画面表示

**ファイル:** `kaname_shogi/compare_games.py`、`tests/test_compare_games.py`。

**消費:** Task 1の `load_config()` / `make_schedule()`、Task 2の `run_game()`、Task 3のpayload変換・保存・集計。

**生産:** `python3 -m kaname_shogi.compare_games` の実行入口、`main(argv: Sequence[str] | None = None) -> int`。

**検出範囲・未検証:** 専用テストは引数から保存までの接続、終了コード、進行中/局間の中断、局保存とsummary更新の順を検出する。関連テストはJSON・一局操作を補完し、全体テストと実プロセス試行はモジュール入口・CLI引数伝播・実際の出力ファイルを検出する。全OSのCtrl-C配送、強制SIGKILL、非常に長い対局やディスク満杯の全状況は未検証。

- [x] **ステップ1: CLI境界テストを作成**

  正常な小実験で conditions を最初に一度保存し、開始済み各局の `game-NNNNNN.json` を個別保存し、最後に `summary.json` を保存する順序を検査する。未知/不正引数では出力先未作成・対局呼出し0、出力先既存では拒否する。各局後にsummaryを更新し、Ctrl-Cを局開始前、局進行中、二局間で発生させ、開始数・中断局の有無・未実行数・130を独立期待値と照合する。例外・局保存失敗・summary保存失敗では1、入力エラーでは2、全局保存完了は0を検査し、保存失敗時に成功文を出さない。通常千日手は再戦しないこと、終了画面は固定深さ/時計なし・反復棋譜の独立証拠限界・統計判定未実施を伝えることを確認する。

- [x] **ステップ2: 対象テストで振る舞いの失敗を確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_compare_games.py' -v`

  期待値: 専用CLI入口・停止境界の振る舞いによる失敗。

- [x] **ステップ3: CLI接続を実装**

  argparse検証、条件保存、予定順の逐次実行、局ファイル確定、summary更新、短い日本語表示を接続する。`KeyboardInterrupt` は局進行操作の境界で捕捉し、確定済み履歴で中断局を記録する。処理故障は後続局を始めず、保存可能な状態と診断を残す。`__main__.py` や通常CLIには選択肢を追加しない。

- [x] **ステップ4: CLI境界と実プロセスを確認**

  実行: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p 'test_compare_games.py' -v`、一時ディレクトリ上で `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m kaname_shogi.compare_games --help` と設計済みの小さい成功/入力不正例。

  期待値: 対象テスト全件PASS、help・終了コード・JSON副作用が専用プロセスから一致。

- [x] **ステップ5: Refactor要否と差分を確認**

  実行: Ruff format/check、`git diff --check`、`git diff`。

  期待値: 検査成功。引数検証、対局規則、保存処理がCLI内へ重複していない。

  実績: CLI専用テスト11件、比較状態/JSON関連テスト33件がPASS。実プロセスでhelp=0、未知引数=2、4局面×1組・1手上限の8局成功=0を確認し、conditions・局別8 JSON・完了summaryを検査。Ruff format/checkと`git diff --check`が成功。独立レビューで局間の局面参照時の割込み捕捉不足が見つかり、再現テストのRed確認後にバッチループ全体で捕捉する修正を行った。

## タスク 5: 全体検証・検出力点検・独立レビュー・記録

**ファイル:** Task 1〜4の全製品コード・テスト、`data/comparison/start-positions-v1.json`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/learning/engine-comparison-design.md`。

**消費:** 承認済み比較設計・未裁定識別子拡張、Task 1〜4の実装とテスト。

**生産:** 完全な比較CLI、全体検証、独立レビュー記録と実績・未検証事項。

**検出範囲・未検証:** 専用テスト群と代表変異で比較固有の対象契約を確認し、関連既存モジュールで再利用境界を、全体テストで統合回帰を確認する。個々の有限ケースから全入力の正しさ・棋力改善・統計的独立性を証明しない。未検証事項は直前の一覧を実績と照合して更新する。

- [x] **ステップ1: 対象契約・範囲・外部副作用をレビュー**

  開始前入力検証、組み順・先後/種、局の初期履歴、成功手境界、4回目継続/5回目直近窓、上限同時成立、連続王手の敗者、双方未裁定、時計境界、終了理由排他性、棋譜v1維持、保存順/原子性、Ctrl-C/故障時状態を比較設計と照合する。通常CLI・USI・通常CLI SFEN・統計判断・自動再戦/再試行へ差分がないことも確認する。

- [x] **ステップ2: 誤りを隔離注入して意図した検査を確認**

  少なくとも、4回目で終了、5回目に古い窓を利用、通常千日手を勝敗化、連続王手敗者を反転、双方未裁定を通常千日手/勝敗へ変換、手数上限を実際の終局より先にする、先後を交換しない、種を誤割当、未確定手を記録、summaryへ未実行局を計上、保存失敗を成功表示の代表変異を隔離して実行する。各ケースで狙ったアサーションがFAILし、変異復元後PASSすることを記録する。単独テストで検出しない項目と全体テストで補完するものを分ける。

- [x] **ステップ3: Ruff・関連・全体検証を実行**

  実行: `.venv/bin/ruff format --check .`、`.venv/bin/ruff check .`、`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py`、`git diff --check`。失敗時のみ関連する逐次診断を使う。

  期待値: 新規三モジュールの専用テスト、依存する既存テスト、全テストが成功。数字は実測を記録し、過去の検証値を今回へ流用しない。

  実績: `.venv/bin/ruff format .` は84ファイル変更なし、`.venv/bin/ruff check .` と`git diff --check`は成功。`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py`は705件・45モジュールが14.705秒で成功。CLI専用11件、比較/JSON関連33件も成功。別の一時コピーへ11種類の代表変異を注入し、すべて狙ったテストのAssertionErrorによるFAILを確認した。元作業ツリーは変異に使用していない。

- [x] **ステップ4: Refactor要否の後に独立コードレビューを行う**

  Critical / Important / Minor を記録する。CriticalまたはImportantがあれば修正し、専用・関連・全体検証を再実行して再レビューする。Minorは対応または理由付きDeferredとする。フック成功を独立レビューの代わりにしない。

  実績: 初回レビューはCritical 0 / Important 1 / Minor 0。局間の予定局取得・局面参照中にCtrl-Cが来るとループ外へ漏れる指摘に対して、局面ID参照時の割込みテストを追加した。修正前は想定したテストがAssertionErrorでFAILし、バッチループ全体のKeyboardInterrupt捕捉後はCLI専用11件と全体705件がPASSした。独立した再レビューはCritical 0 / Important 0 / Minor 0。

- [x] **ステップ5: 利用・設計・実績文書を更新する**

  READMEに新コマンドの現行利用法と動作確認用途・棋力判定ではない限界を記す。索引・再開案内・P1学習記録へ実際の変更、テスト設計の検出範囲、代表変異、専用/関連/全体結果、レビュー重大度と対応、未検証事項を記録する。相対リンクと `git diff --check` を確認する。main統合は別承認の後とする。

  実績: READMEへ専用CLIの必須引数、組・先後、深さ/時計、千日手、JSON出力、終了コードと証拠限界を追加した。文書索引・再開案内・P1学習記録に計画承認、変更、検出範囲、全体検証、11代表変異、レビューの初回指摘と解消、未検証事項を記録した。変更した5文書の685相対リンク先を確認し欠落なし。`.venv/bin/ruff format --check .`（84ファイル）、`.venv/bin/ruff check .`、`git diff --check` が成功した。別途の本人承認後、2026-10-23に `e595f8e` から実装コミット `3adbd23` をローカルmainへfast-forward統合した。統合先で全体705件・45モジュール（14.548秒）、Ruff format確認84ファイル、Ruff check、`git diff --check` が成功。pushなし。最後の理解確認は未実施で、回答待ち。

## 期待する検出範囲と未検証事項

- **専用テスト:** 入力/予定、比較状態機械、千日手境界、保存/集計、CLI終了コードの比較固有契約と代表誤りを検出する。
- **関連既存テスト:** 合法手適用、SFEN表現、棋譜v1、五方式の既存探索・手選択、千日手API内部を再実装せず契約境界で利用できることを補完する。
- **全体テスト:** import/入口/既存機能との回帰とモジュール相互作用を確認する。全入力への証明とはしない。
- **代表変異:** 別個の実験でアサーションのFAILを確かめ、読み込みエラーだけを検出成功としない。
- **未検証:** 全局面・全棋譜・全OS/Python配布形態、強制終了・電源断時の複数ファイル完全性、実時間応答保証、将棋棋力の改善、独立標本性、統計的有意性・必要対局数、外部/別Git版エンジン、通常CLI SFEN、USI接続。

## セルフレビュー

- 設計要件を、入力/予定（Task 1）、一局状態機械（Task 2）、記録/集計（Task 3）、バッチ入口（Task 4）、横断確認・レビュー・文書（Task 5）へ割り当てた。
- 千日手API実契約の継続・4回目・5回目直近窓・連続王手負け・双方未裁定を、終局・勝敗・専用集計へ接続した。未裁定の新識別子と集計欄は承認済み設計にない追加であることを計画で区別し、本人の明示承認後に確定仕様として実装した。
- 通常CLI SFEN入出力、通常CLI/USI変更、統計判定、自動再戦/再試行を除外した。
- 各タスクに対象契約、独立期待値、想定誤り、専用/関連/全体の範囲、未検証事項を実装時に記録する手順を置いた。ケース数の多さを十分性と同一視しない。
- コマンドはリポジトリルートで実行する。計画作成時に製品テストを実行していない。
