# C1：飛車可動性の接続・比較評価 実装計画

> **AIエージェントへの指示:** この計画の実行には `executing-plans` スキルを使用する。2026-10-24、本人は計画全体を明示承認し、私が順に実装する方法と現在のディレクトリで作業ブランチを使う方法を選んだ。作業ブランチは `codex/c1-rook-mobility-evaluation`。下記のチェックリストと進捗台帳を使い、承認済み範囲を順に実行する。

**目標:** 比較CLIで現行一手駒得とB1を再現可能な予定で対局させ、保存結果を分析し、C1内で強さと採否を判断できるようにする。

**アーキテクチャ:** B1部品を共通の一手選択境界へ接続し、準備・比較・分析の三入口を同じ保存契約で結ぶ。乱数種データと統計計算をI/Oから分離し、既存の合法手・棋譜・千日手操作を再利用する。三入口は同じ実験を完成させる従属した工程のため、一計画で扱う。

**技術スタック:** Python標準ライブラリ、unittest、既存の将棋部品、固定版Ruff。外部統計ライブラリを追加しない。

**仕様:** [本人承認済み設計](2026-10-24-c1-rook-mobility-evaluation-design.md)。2026-10-24、本人は設計全体に「yes」、本実装計画全体に「承認する」と回答した。経緯は[学習記録](../learning/c1-rook-mobility-evaluation.md)。

## グローバル制約

- 比較CLIからB1を選択できるようにする。通常CLI・USIへの公開は今回行わない。
- 通常CLIのSFEN入出力、可動性バージョン2は追加しない。
- B1部品の重み・候補生成・詰み判定・乱数の契約を変更せず再利用する。
- 予備比較と確認比較は別の乱数種一覧を用い、成績を混ぜない。
- 確認比較は固定組数で予定分を実行し、途中の勝ち越しを理由に打ち切らない。
- 同じ一覧での再実行を新たな強さの証拠として加算しない。
- 改善支持でも自動採用・通常CLI/USI公開・main統合はしない。
- Python 3.9への影響を点検し、新規モジュールは必要な遅延型注釈を用いる。日本語docstringに引数・戻り値・副作用・前提と理由を記す。
- [検出力と範囲の点検](../knowledge/test-coverage-review.md)と `~/.codex/observations/test-driven-development.md` を適用する。

## レビューフォーカス

1. 入力一覧に同じ種の値が偶然重複した場合も、独立抽出のモデルを変える除外・再抽出をしない（タスク2）。
2. JSONのbool・重複キー・非有限数・128ビットの境界を黙認せず、出力作成前に拒否する（タスク2/3/5）。
3. 棋譜は合法でも通常千日手の終了後へ続いていたら、分析で最初の終局との不一致を拒否する（タスク5）。
4. 一方の局だけ別実験へ差し替えたものや、古いsummaryは、成績を黙って計算せず拒否する（タスク5）。
5. CI端点が50％ちょうど、pilot、未裁定、片組しかない結果を、改善支持へ変換しない（タスク4/5）。

## 実行前の場所・承認・共通サイクル

基準の作業場所は `/Users/oki2a24/kaname-shogi`。計画作成時はmain、HEAD `5f136d5`、origin/mainより15コミット先行。今回の文書変更と、以前からの `.antigravity/tasks/`・`.venv.backup-2026-10-22/` を区別し、後二者はステージしない。

- [x] 計画承認後、本人は実行方法としてこのセッションで私が順に実装する方法を選んだ。六タスクの共有データ契約が多いため、タスクごとのゲートを適用し、最後に独立レビューを行う。
- [x] `using-git-worktrees` の手順で既存隔離環境を確認した。このタスクに添付された作業ツリーはなかった。本人は別作業ツリーでなく現在のディレクトリを選んだ。
- [x] 元ディレクトリ `/Users/oki2a24/kaname-shogi` で `git switch -c codex/c1-rook-mobility-evaluation` を実行した。未追跡 `.antigravity/tasks/` と `.venv.backup-2026-10-22/` を含む既存作業物を保持する。
- [x] 実行先のGit状態・直近履歴・branch、`.venv/bin/ruff --version`、`git config --local --get core.hooksPath` を確認した。branch作成時点のHEADは `5f136d5`、Ruffは `0.16.10`、hooksPathは `.githooks`。2026-10-24に `python3 scripts/run_tests_parallel.py` を実行し、729件・48モジュールが14.830秒で成功した。

タスクごとに下記のサイクルを守る。新規モジュールのimportエラーを振る舞いのRedとは数えず、最小のAPI骨格を用意した後に契約アサーションが失敗することを確認する。既存処理の初回Greenは特性確認として区別する。

1. 各テストの日本語docstringに契約・検出対象・独立期待値の根拠を書く。
2. 振る舞いを一つずつRed確認→最小実装→Green→Refactor要否確認する。
3. タスク固有と既存回帰の検出範囲・未検証を記録する。
4. import変更時は `.venv/bin/ruff check --select I --fix .`、続いて `.venv/bin/ruff format .`、`.venv/bin/ruff check .`、差分確認、見合うテストを実行する。
5. Refactor要否確認後の独立コードレビューを行い、Critical/Importantは解消・再検証・再レビューする。タスク単位のコミットを行う場合もこの条件を満たしてから、対象ファイルのみステージして通常のフック付きコミットを行う。全体レビューはタスク6でも行う。

## ファイルと依存関係

| ファイル | 責務 |
| --- | --- |
| 変更 `kaname_shogi/movegen.py`、`game_search.py` | 方式データ追加とB1への一手選択接続 |
| 新規 `kaname_shogi/comparison_artifact_io.py` | 厳密なJSON読取と上書きしない新規成果物保存 |
| 新規 `kaname_shogi/comparison_seeds.py` | 乱数種データ・生成・検証・JSON変換。将棋対局やファイルI/Oをしない |
| 新規 `kaname_shogi/prepare_comparison_seeds.py` | 乱数種準備CLI |
| 変更 `kaname_shogi/comparison.py`、`comparison_io.py`、`compare_games.py` | 一覧の読込、予定生成、v2条件保存、既存実行との接続 |
| 新規 `kaname_shogi/comparison_analysis.py` | 得点上下限・二局一組の集約・Hoeffding計算 |
| 新規 `kaname_shogi/comparison_result_io.py` | 保存実験の読取・合法再生・条件/集計の照合、分析JSON変換 |
| 新規 `kaname_shogi/analyze_comparison.py` | 分析CLI |
| 新規 `data/comparison/c1-rook-mobility-positions-v1.json` | 合意済み6局面。既存starter-v1は改変しない |

依存は `artifact_io ← seeds ← comparison ← result_io` とし、analysisはcomparisonの終了理由・方式データを読む。準備CLIはseedsと既存局面読取を使い、分析CLIはresult_ioとanalysisを使う。result_ioから比較実行CLIを呼ばない。

## 共通データ・保存形式

新規型・操作名の英語は以下の日本語の意味で説明する。すべて後続タスクが使う正確な契約とする。

- `PairSeeds`：一組の種を持つ変更不可データ。フィールドは `position_id: str, repetition_index: int, baseline_seed: int, candidate_seed: int`。
- `SeedPlan`：乱数種一覧の変更不可データ。`purpose: str, positions_sha256: str, position_ids: tuple[str, ...], pairs_per_position: int, pairs: tuple[PairSeeds, ...]`。sourceはos、bitsは128の固定契約でJSONに記録する。
- 既存 `ComparisonConfig.seed` は `int | None` とし、末尾に既定Noneの `seed_plan: SeedPlan | None, seed_list_json: bytes | None, seed_list_path: Path | None` を追加する。旧呼出しは修正なしで成立し、seedか一覧のちょうど一方を持つ。
- `PairScore`：一組の候補得点区間データ。`lower: Fraction, upper: Fraction`。各端点は0〜1。
- `ScoreAnalysis`：計算結果データ。`pairs: int, lower_mean: Fraction, upper_mean: Fraction, radius: float, lower: float, upper: float, decision: str`。信頼水準0.95は名前付き定数。
- `LoadedComparison`：検証済み保存実験データ。`config: ComparisonConfig, schedule: tuple[ScheduledGame, ...], results: tuple[GameResult, ...], purpose: str, conditions_sha256: str, artifact_hashes: tuple[tuple[str, str], ...], elapsed_ns: int`。

乱数種JSONの厳密なトップキーは `format, purpose, positions_sha256, position_ids, pairs_per_position, source, bits, pairs`。formatは `kaname-shogi-comparison-seeds-v1`、sourceは `os`、bitsは128。pairsの各項目のキーはPairSeedsの4フィールドと同名。順序は局面順→反復0始まり。種はbool以外の整数で `0 <= seed < 2**128`。種の値の偶然の重複は許すが、局面・反復の重複や順序違いは拒否する。

一覧実験のconditionsは `kaname-shogi-comparison-conditions-v2`。既存v1の項目に、読込時の正確な局面JSON文字列 `positions_json`、`randomization`、`policy_parameters` を追加する。seedはnull。randomizationのキーは `purpose, source, bits, seed_list_sha256, seed_list_json`。seed_list_jsonも読込時の正確なUTF-8文字列で、SHA-256は保存した文字列をUTF-8へ戻したバイト列に対して照合する。policy_parametersはbaseline/candidateの辞書でB1だけ `{material: 10, mobility: 1, mate_priority: true}`、既存方式は空辞書。scheduleの各種とも一致させる。

旧 `--seed` はv1条件を維持する。game/summaryと内部棋譜v1の既存構造を変えず、方式名としてB1を追加する。旧五方式の実験の方式別計時キーは従来の五方式を維持し、B1を使う実験にだけB1キーを加える。

分析JSON形式は `kaname-shogi-comparison-analysis-v1`。トップキーは `format, inputs, analyzer, purpose, baseline, candidate, assumptions, confidence_level, method, planned_games, completed_pairs, counts, score, by_position, by_side, move_time_by_policy, elapsed_ns`。inputsにconditionsと全局・summaryのファイル名とSHA-256、analyzerに分析ソース/Git/Pythonの識別を保存する。scoreは `lower_mean, upper_mean, radius, lower, upper, decision`。比率はJSON有限数、countsとby_position/by_sideに勝敗・千日手・上限・双方未裁定を残す。methodは `hoeffding-paired-bounds-v1`。分析のsource識別は実験時との一致を必須にしない。

### タスク 1：B1の実接続と6局面

**変更:** `kaname_shogi/movegen.py`、`game_search.py`、`comparison.py`、`comparison_io.py`。**作成:** 上記6局面JSON。**テスト:** `tests/test_game_search.py`、`test_comparison_io.py`、`test_compare_games.py`。既存CLI/USIのテストで公開範囲も回帰確認する。

**消費:** `choose_one_ply_move(position, moves, rng, *, evaluate)`、`evaluate_material_rook_mobility(position, perspective, *, weights=...)`。
**生産:** `MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY`、方式名 `material-rook-mobility`。既存 `game_search.choose_move` のシグネチャを変えず接続する。

- [x] 二候補の差1点・先後反転・最高同点抽選・空候補・詰み優先の接続確認を追加する。弱点例の+1/−1は新接続経路でも保持する。旧MATERIALの挙動は変えない。
- [x] 全合法手での独立期待集合を検査する。玉９九/１一、先手飛５八・歩５七、持ち駒なしでは、最大点176、最高集合は `５八飛→{１八,２八,３八,４八,６八,７八,８八}` の7手。全て非詰み。手計算では飛車16マス、駒得16で176。抽選器へ渡す集合をこの固定集合と比較し、結果が集合内、抽選一回、元局面不変を確認する。先後対称版も扱う。
- [x] 失敗を `unittest discover -s tests -p 'test_game_search.py' -v` 等で確認し、入口と名前変換の最小実装後にGreenを確認する。上記全合法手集合は計画作成時に既存部品で照合済みで、期待集合を製品評価から生成しない。
- [x] 6局面JSONはstarter-v1の4項目を内容保持して複写し、設計の20/26手局面を追加する。IDは `developed-before-exchanges` / `developed-after-exchanges`、セットIDは `c1-rook-mobility-v1`。手計算の6/6と8/8、駒得0、固定SFEN、合法手数41/54を確認する。
- [x] 旧五方式の予定・集計、CLIメニューとUSIの選択肢が従来どおりであることを確認し、共通サイクルを完了する。

主要テスト名は `test_b1_dispatch_preserves_full_best_set`。上記配置を作り、抽選器に渡された候補を記録するテスト用オブジェクトで `self.assertEqual(set(rng.seen), expected_moves)` と `self.assertEqual(rng.calls, 1)` を確認する。expected_movesは上記の7手を直接記述し、製品の採点で組み立てない。

### タスク 2：乱数種一覧と準備CLI

**作成:** `comparison_artifact_io.py`、`comparison_seeds.py`、`prepare_comparison_seeds.py`。**変更:** `comparison_io.py` の既存局面読取に公開のバイト列入口を設ける。**テスト:** 新規 `tests/test_comparison_seeds.py`、`test_prepare_comparison_seeds.py`。

**生産する操作:**

```text
comparison_artifact_io.decode_object(raw: bytes, *, context: str) -> dict[str, object]
comparison_artifact_io.write_new_json(path: Path, payload: Mapping[str, object]) -> None
comparison_seeds.generate_seed_plan(position_ids: tuple[str, ...], positions_sha256: str,
    pairs_per_position: int, purpose: str, *, randbits: Callable[[int], int] = secrets.randbits) -> SeedPlan
comparison_seeds.parse_seed_plan(raw: bytes) -> SeedPlan
comparison_seeds.seed_plan_payload(plan: SeedPlan) -> dict[str, object]
comparison_seeds.validate_seed_plan(plan: SeedPlan, *, position_ids: tuple[str, ...],
    positions_sha256: str, pairs_per_position: int) -> None
comparison_io.positions_from_bytes(raw: bytes) -> tuple[ComparisonPosition, ...]
prepare_comparison_seeds.main(argv: Sequence[str] | None = None) -> int
```

既存の `_positions_from_bytes` は互換ラッパーを保ち、`load_positions` と新公開入口は同じ実処理を使う。JSONの重複キー拒否は共通decode_objectへ寄せ、既存呼出しの診断内容を保つ。decode_objectはUTF-8、トップオブジェクト、全階層の重複キー・NaN/Infinityを拒否する。

- [x] 2局面各2組、固定乱数源11〜18で、8回のrandbits(128)呼出しと4組の正確な列を期待するテストを追加し、振る舞いのRedを確認する。
- [x] 同じ種が8回出ても4組をそのまま保存する、bool/負/2**128は拒否、0と2**128−1は許可、欠落/未知キー/重複組/順序違いを拒否するテストを一つずつRed→最小実装→Greenにする。
- [x] CLI引数を設計どおり `--positions --pairs-per-position --purpose --output` とする。全局面の合法準備を検証してから抽出する。出力はJSONをメモリ上で直列化後、排他的な新規作成で保存する。同名ファイル・存在しない親・ディレクトリを拒否し、既存データを上書きしない。
- [x] 実行中の保存失敗・Ctrl-C、入力不正時の抽出/出力未実施、実プロセスでの一局面一組生成を確認する。正常0・入力不正2・実行保存失敗1・通常中断130を固定する。乱数源の独立性の証明はテスト対象外。
- [x] `unittest discover -s tests -p 'test_*comparison_seeds.py' -v` でタスク固有テストを実行し、既存入力テストも回帰確認して共通サイクルを完了する。

主要テスト名は `test_generates_four_pairs_from_eight_fixed_draws`。生成結果の各行を4フィールドのタプルへ変換し、`self.assertEqual(rows, [("a", 0, 11, 12), ("a", 1, 13, 14), ("b", 0, 15, 16), ("b", 1, 17, 18)])` と比較する。`write_new_json` は保存失敗時に自身が作成した途中ファイルを可能なら除去し、除去失敗も診断する。既存ファイルは削除しない。

### タスク 3：比較CLIでの一覧入力とv2条件保存

**変更:** `comparison.py`、`comparison_io.py`、`compare_games.py`。**テスト:** `test_comparison.py`、`test_comparison_io.py`、`test_compare_games.py`。

**消費:** タスク2のSeedPlanとJSON操作。**生産:** 既存 `load_config(argv) -> ComparisonConfig`、`make_schedule(config) -> tuple[ScheduledGame, ...]`、`conditions_payload(config, schedule, *, source_root) -> dict[str, object]` の一覧対応。既存引数の呼出し互換を維持する。

- [x] 既存--seed、一覧、両方指定、どちらもなしの4分岐を検査する。両方/なしは出力作成・対局前に拒否。局面内容を同じIDのまま変えた場合もSHA-256不一致で拒否する。
- [x] 2局面各2組を手書きの種列で予定8局へ照合し、先後担当・第一局の交互割当て・一組内の種維持・盤面非反転を確認する。最後の組だけ欠落/重複/不正種の場合も開始しない。
- [x] Red後にConfigの末尾フィールドを追加し、旧式と一覧の予定生成を分岐する。一覧は読込済み値だけを使う。
- [x] conditions v2の正確なpositions_json/seed_list_json、各ハッシュ・purpose・全schedule・B1重みを保存し、外部入力ファイルを後で変更しても保存値が変わらないことを確認する。旧--seedのv1条件と旧五方式の計時キーは変更しない。
- [x] 短い実プロセス実行でB1の名前・条件v2・二局の予定と保存・出力先既存拒否を確認する。この短い実行の成績で棋力を判断しない。
- [x] 三つの既存テストモジュールを個別実行し、保存失敗・中断・終局優先の回帰も含めて共通サイクルを完了する。

主要テスト名は `test_seed_list_keeps_policy_seeds_across_swapped_games`。タスク2の4組を使い、`self.assertEqual([(g.baseline_seed, g.candidate_seed) for g in games], [(11,12),(11,12),(13,14),(13,14),(15,16),(15,16),(17,18),(17,18)])`。先後担当の期待列も独立に固定する。

### タスク 4：得点上下限とHoeffding計算

**作成:** `comparison_analysis.py`、`tests/test_comparison_analysis.py`。

**消費:** `GameEndReason`、`MoveSelectionPolicy`。**生産:** PairScore、ScoreAnalysisと次の操作。

```text
game_score_bounds(reason: GameEndReason, winner_policy: MoveSelectionPolicy | None,
    candidate: MoveSelectionPolicy) -> tuple[Fraction, Fraction]
make_pair_score(bounds: tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction]]) -> PairScore
analyze_scores(pairs: Sequence[PairScore], *, purpose: str) -> ScoreAnalysis
decide_interval(lower: float, upper: float, *, purpose: str) -> str
reference_pair_count() -> int
```

Fractionは整数の比を表すデータで、得点合計を正確に保つ。平方根・自然対数とJSON表示段階で有限floatへ変換する。判定は丸め前の値で行い、表示用丸めで結論を変えない。

- [x] 勝ち[1,1]、負け[0,0]、通常千日手[1/2,1/2]、上限と双方未裁定[0,1]、中断/故障の拒否をそれぞれRed→最小実装→Greenにする。
- [x] 勝ち＋千日手の一組はPairScore(3/4,3/4)、上限＋負けは(0,1/2)とする。例えばこの二組全体はLbar=3/8、Ubar=5/8。勝者の先後を逆にしても候補方式視点で得点を決める。
- [x] 固定期待値のテスト例を実装する（計算元として製品関数を呼ばない）。

```python
def test_hoeffding_radius_and_reference_count(self):
    scores = [PairScore(Fraction(1), Fraction(1))] * 100
    self.assertAlmostEqual(analyze_scores(scores, purpose="confirmation").radius,
                           0.13581015157406195)
    self.assertEqual(reference_pair_count(), 2035)

def test_boundary_and_pilot_do_not_claim_improvement(self):
    self.assertEqual(decide_interval(0.5, 0.7, purpose="confirmation"), "inconclusive")
    self.assertEqual(decide_interval(0.6, 0.7, purpose="pilot"), "exploratory")
```

- [x] n=0、不正purpose、不正範囲・端点順・非有限値を拒否する。確認比較のlower>0.5だけimproved、upper<0.5だけworsened、それ以外inconclusive。pilotはexploratory。100組・2035組の幅を独立計算と照合する。
- [x] 区間は `[max(0,Lbar−e), min(1,Ubar＋e)]`、eは `sqrt(log(40)/(2*n))`。参考組数は `floor((sqrt(log(40))+sqrt(log(5)))**2/(2*0.05**2))+1`。独立性や検出力の統計仮定はユニットテストで実証したと扱わない。
- [x] 固有テストを実行して共通サイクルを完了する。

### タスク 5：保存結果の検証と分析CLI

**作成:** `comparison_result_io.py`、`analyze_comparison.py`、`tests/test_comparison_result_io.py`、`test_analyze_comparison.py`。**変更:** `comparison.py` の終局理由変換を再利用できる境界へ抽出する。

**消費:** タスク2のJSON操作、タスク3のv2保存、タスク4の得点計算、既存 `GameRecord.from_payload` と `RepetitionTracker`。
**生産:**

```text
comparison.repetition_terminal(outcome: RepetitionOutcome) -> tuple[GameEndReason, Side | None] | None
comparison.board_terminal(position: Position, *, has_legal_moves: bool, plies: int,
    max_plies: int) -> tuple[GameEndReason, Side | None] | None
comparison_result_io.load_completed_comparison(input_dir: Path) -> LoadedComparison
comparison_result_io.analysis_payload(loaded: LoadedComparison, analysis: ScoreAnalysis,
    *, source_root: Path) -> dict[str, object]
analyze_comparison.main(argv: Sequence[str] | None = None) -> int
```

repetition_terminalを先に、board_terminalを後に評価する。後者は合法手なし→上限の順。比較実行で既に求めた合法手の有無を渡し、合法手生成を重複させず計時境界を保つ。

- [x] 手書き期待値の小さな完了結果で読取・候補視点集計・ハッシュ照合のRedを作る。新writerで生成した値を唯一の期待値にはしない。
- [x] conditions v2の厳密キー・有限値・入れ子、保存局面JSONと一覧のハッシュ、各予定・方式・種・開始SFENの一致を検証する。`game-*.json` の集合は予定と完全一致を求め、別名の分析成果物は局として数えない。入力ディレクトリ外へ向ける任意のファイル参照は受け取らず、予定IDから局ファイル名を構成する。
- [x] GameRecordで合法再生し、比較開始局面・棋譜手数・各手と計時の対応を照合する。履歴を開始局面から追い、途中で既に終局していた記録、理由/勝者/上限の矛盾、unfinished_calculationがある完了局を拒否する。終局ロジック抽出の旧テスト初回Greenは特性確認とし、新readerの振る舞いRedと区別する。
- [x] summaryはstatus=complete、全予定実行・全組完了・未実行0・中断/故障0を求める。局結果から既存summarizeで再集計し、件数・先後・計時等と一致を確認する。elapsed_nsは有限非負整数として読み、実行当時の壁時計を再計測しない。未決着・双方未裁定は完了局として扱い、得点上下限を保つ。
- [x] 片局欠落、余分な局、別conditionsの一局、偽summary、合法だが早期千日手後へ続く記録、旧v1条件の各ケースを拒否する。旧v1は独立抽出前提の分析へ自動移行しない。
- [x] `--input-dir --output` のCLIを接続し、新規analysis JSONと日本語表示を保存する。判断不能とpilotの正常保存は終了0、入力不正2、実行保存失敗1、通常中断130。既存outputは上書きせず、元実験の保存値を変えない。
- [x] 局面別・先後別は記述集計とし、総合一回の主判定だけに95％の前提を付ける。分析時のコード識別は現在のものを別記し、当時のソースと違うだけでは拒否しない。形式やルールが未対応なら拒否する。
- [x] 固有二モジュールと既存比較三モジュールを実行し、共通サイクルを完了する。

主要テスト名は `test_rejects_one_game_from_another_experiment`。正常な手書きfixtureの一局のconditions参照だけを変更し、`with self.assertRaises(ValueError): load_completed_comparison(input_dir)` を確認する。`test_validates_result_before_creating_analysis_output` では同fixtureでCLI終了2と `self.assertFalse(output.exists())` を確認する。分析時ソースの識別は既存 `comparison_io._source_sha256` と `_git_metadata` を再利用し、同じ算出処理を複製しない。

### タスク 6：実接続・検出力点検・文書・予備比較

**変更:** `README.md`、`docs/knowledge/search-comparison.md`、C1設計/学習/計画、`docs/resume.md`、`docs/README.md`、`docs/next-topics.md`、ロードマップ。**必要な確認:** 既存テストと新規テストへ接続ケースを追加する。

- [x] 準備→比較→分析の実プロセス一連を小さな条件で実行し、purpose保持、入力拒否、保存条件/得点の対応を確認する。同じ種一覧で再実行し、時間・実行環境の変動欄を除く予定・棋譜・終了理由・勝敗の一致を確認する。
- [x] 隔離コピーで代表誤りを一つずつ入れ、狙ったassertion failureと復元後Greenを記録する。候補はB1をMATERIALへ誤配線、評価視点を先手固定、組内で方式の種を交換、未知結果を0.5へ固定、nを局数へ変更、片局欠落を許可、条件ハッシュ照合を省略。全てを毎回増殖させず、関連テストと固有テストの補完を記録する。import失敗や構文失敗を検出成功にしない。
- [x] Refactor要否確認後の独立コードレビューでCritical/Important/Minorと対応を記録する。初回レビューはCritical 0・Important 0・Minor 1。`comparison_io.load_config` が `Path.exists()` で出力先を調べるため、dangling symlinkを見逃し、mkdir失敗を入力不正2ではなく実行保存失敗1にする指摘だった。CLIの公開動作テストを追加し、旧実装で終了1となるRed、`os.path.lexists()`への変更後に終了2となるGreenを確認した。リンクが残り、対局が始まらないことも同じテストで確認した。最終独立レビューはCritical 0・Important 0・Minor 0で、修正を確認した。レビュアーはテストを実行していない。
- [x] Ruff整理・format/check、`git diff --check`、`python3 scripts/run_tests_parallel.py`、文書リンク確認を実施した。Ruff三工程は成功、全体795件・55モジュールは17.518秒で成功、9文書807相対リンク・8見出しリンクは欠落0件。順序依存・並列差やランナー変更はないため逐次全体を追加しない。Python 3.9の実行互換は未検証として残す。
- [x] 3コマンドの使用法・引数・形式・終了コード・分析の仮定と限界をREADME/知識へ、実績・承認・回答・レビューを学習記録へ保存した。
- [x] 内容確認後、C1対象31ファイルのみ通常コミット `42fc9e9`（`feat: 比較CLIで飛車可動性を評価する`）へ保存した。main統合は別の本人承認後に行い、取り込み先で検証する。
- [x] 実装・検証済みのソースをコミット `42fc9e9` で固定後、6局面×各1組・max-plies256・purpose pilotの乱数種一覧を作成して予備比較を行った。実コマンドと絶対パスを事前案内し、seed JSON・出力ディレクトリ・analysis JSONの新規性を確認した。比較CLIは12/12局を完了し、analysis JSONを保存した。乱数種、conditions、12局の結果、summary、分析JSON、実測・限界・未決事項は学習記録とともにコミットする。

```text
python3 -m kaname_shogi.prepare_comparison_seeds --positions data/comparison/c1-rook-mobility-positions-v1.json --pairs-per-position 1 --purpose pilot --output <新規の予備比較乱数種JSON>
python3 -m kaname_shogi.compare_games --baseline material --candidate material-rook-mobility --positions data/comparison/c1-rook-mobility-positions-v1.json --pairs-per-position 1 --seed-list <同JSON> --max-plies 256 --output-dir <新規出力ディレクトリ>
python3 -m kaname_shogi.analyze_comparison --input-dir <同ディレクトリ> --output <新規分析JSON>
```

- [x] 全12局が完了した後、251.999秒の比較時間、6組それぞれの手選択計時合計、未決着5/12局、具体棋譜例を説明した。均等配分の参考4,080局へ単純比例すると約23.8時間だが、局ごとのばらつきと256手上限到達5局があるため粗い見積もりである。未決着が多く、未決着なしを前提にした目標検出力は保証できない。
- [ ] **本人の選択を待つ。** 確認比較の組数・手数上限・実行予算は未承認。pilot結果と時間見積もりを踏まえ条件を確定し、新しいpurpose confirmationの乱数種一覧を作って予定分を実行する。予算不足または未決着率のため目標検出力を満たせない場合は、限界と変更案を説明して本人が選ぶ。
- [ ] 確認比較の結果と不確かさ、処理時間、弱点、適用範囲を提示して本人の採否を待つ。判断不能を強化失敗の証明へ言い換えず、同じ確認結果を見ながら追加局を継ぎ足して固定標本の判定を繰り返さない。追加比較は別計画として本人が選ぶ。

## 計画のセルフレビューと未検証

仕様の接続・小局面・一覧準備・旧方式互換・保存・分析・予備/確認の各要件をタスク1〜6に割り当てた。型名と利用箇所、予定の算式、比率の尺度、失敗時の保存、上記レビューフォーカスの各テストを照合する。2026-10-24にセルフレビューを実施し、要件のタスク割当て、型と操作名の一致、6件のタスク境界、5件のレビューフォーカスのテスト対応、数式の数値を確認した。新規コマンドは未実装のため実行できず、既存コマンドの形とパスを読み取り確認した。新コマンド実行確認は各実装タスクのGreen後に行う。

計画作成時点ではコード・テスト・製品用局面データ・対局結果は未作成だった。後続の実装・検証実績は上記タスクと学習記録を参照する。未検証はOS乱数源の独立性、全入力と全OSの挙動、実応答時間上限、真の棋力差、局面群の実戦代表性、確認比較の最終条件。計画承認はこれらの成功を認定するものではない。
