# 比較CLIの性能改善 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画を実行する前に `superpowerssuperpowers:executing-plans` を適用する。チェックボックスで実績を追跡する。

**目標:** 同一PC・4 worker・元条件とseedを維持した新規4,074局を30分以内に完了する。

**アーキテクチャ:** 現行Pythonの比較CLIを、新しい出力先で実際に計算する。代表42局のprofileで支配処理を特定してから、一度に一つの仮説だけをテスト先行で変更する。変更前後のseed一致結果、保存/再開/分析契約、全体回帰、独立レビューを確認してから新規全量実測する。

**技術スタック:** CPython 3.15.2（READMEのPython 3.14以上）、既存標準ライブラリ、既存 `ProcessPoolExecutor`、`unittest`、Ruff 0.16.10。新しい依存は導入しない。

**仕様 (Spec):** [性能改善の設計案](2026-11-03-comparison-cli-performance-design.md)。

## グローバル制約 (Global Constraints)

- 比較対象policy、評価式、合法手・詰み・千日手・その他終局、seed、7局面・SHA、2,037組/4,074局、先後交換、512手上限、4 workerを維持する。
- 同じ入力・seedで指し手列、終局理由、勝者を変えない。候補順、同点時の選択、乱数消費順を維持する。
- 保存、analysis、`--resume`、source fingerprint、ロック契約を維持する。
- 新規実出力先の全計算時間だけを性能目標に使い、既存局の再利用・結果埋込・局/手/計時の省略をしない。
- 作業は同じcheckoutの `codex/comparison-cli-performance` 上で行う。mainへの統合・pushは本計画に含めない。
- 承認時に開始時刻と8時間後の終了予定を `GOAL.md` へAsia/Tokyoで記録する。承認待ちは期限から除き、その時間を記録する。2時間・4時間で検証済み最良実測、目標差、残る主要処理時間を照合し、現在の律速部分を目標内にするための必要倍率を再計算する。小幅改善の積み上げでは届かないなら仮説を見直し、計画外の大規模変更は別途承認を得る。最後の1時間は検証・レビュー・記録を優先する。
- 未追跡比較成果物、`.antigravity/tasks/`、保全アーカイブなど開始時にある既存データを変更・移動・削除・ステージしない。
- Python変更ではimport整理、整形、lint、差分確認、対象テストを行う。フックを迂回しない。

## レビューフォーカス (Review Focus)

1. 候補順・同点処理・乱数抽選回数が変わるとき、固定seedの後続棋譜まで一致しなくなる。各方針の一手と全42局結果を旧runと比較する。
2. 攻撃集合の共有や高速化が、王・ピンされた駒・成駒・遮蔽・敵味方マスで既存の幾何学的利きと食い違う。既存公開利きAPIとの独立照合を行う。
3. 盤面適用の省略が、移動・成り・捕獲・打ち・自玉安全・打ち歩詰め・持ち駒更新を弱める。合法な候補と不正な入力の両方を検査する。
4. 共有キャッシュが異なる盤面・持ち駒・先後・履歴の値を返す。状態依存を列挙し、別枝・遷移前後・先後反転・状態不変を直接検査する。
5. 新規全量計測が保存済み結果を読み込む、resumeする、または一部局だけ実行する。空の専用出力先、元seed全件、条件JSON、summary、局JSON全件を照合する。

## タスク

### Task 1: 環境・基準・42局benchmarkの再現

**ファイル:** `GOAL.md`、`docs/learning/comparison-cli-performance.md`、元seed一覧と局面ファイル（読み取りのみ）。profile用一時runnerとbenchmark成果物は `/private/tmp` または新規の比較出力先に置き、既存runを変更しない。

- [x] **ステップ1: 承認後の開始状態を記録する。** 2026-11-03 12:16:27 JST開始、20:16:27 JST終了予定。承認待ち7分49秒を除外。branch/HEAD、固定Ruff/hooks/Python、seed/局面SHAを再確認し、Activity Monitorで比較CLI不在を確認した（`ps`はOS権限で拒否）。
- [x] **ステップ2: 元confirmation条件を独立に検算する。** 7局面、各291組、2,037組・4,074局、512手、4 worker、policy、元seed一覧の全件を検査した。seed一覧と局面は読み取りのみで、新しいseedは生成していない。
- [x] **ステップ3: 新規の固定42局baselineを作る。** 各局面の元組番号0・145・290を抽出し、seed値、baseline/candidate割当、元と同じ先後割当を保つseed-listを作った。元runの条件に合わせた4 worker比較を未使用ディレクトリへ実行し、profileなしのCLI起動から終了までwall 730.49秒を記録した。

  実行形は以下のとおり。seed-listは既存confirmation seedの抜粋を別ファイルに作り、出力先は開始前に未使用と確認する。`time` の実時間とsummaryを両方記録する。

  ```sh
  time PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m kaname_shogi.compare_games \
    --baseline material-piece-threat-v1 \
    --candidate material-piece-threat-value-v1 \
    --positions data/comparison/undefended-piece-value-positions-v1.json \
    --pairs-per-position 3 \
    --seed-list /private/tmp/comparison-cli-performance-42-seeds.json \
    --max-plies 512 --workers 4 \
    --output-dir data/comparison/runs/comparison-cli-performance-42-baseline-2026-11-03
  ```

  計画段階の読み取り専用照合では、21組すべてで元seedと先後割当の偶奇が一致することを確認済み。baseline完了後はsummaryの一手計時合計と外部壁時計も記録し、その比をworker処理時間の重なり方の粗い指標として見る。これはOS CPU使用率ではなく、並列の偏りや親側処理の測定を考えるための手掛かりに限定する。
- [x] **ステップ4: baseline出力を旧保存結果へ突合する。** 位置ID、元組番号、局順、side/policy、方式別seedで対応づけ、42局の指し手列、終局理由、勝者がすべて一致することを確認した。出力条件・42局/21組完了・合法再生・未開始/故障/中断0も照合した。
- [x] **ステップ5: 代表局のprofileを取る。** 元seedの最初の組を使い、7局面×2先後交換の14局をメモリ上で新規実行し、標準ライブラリcProfileで集計した。14局・1,549手すべてB0の指し手列・終局理由・勝者と一致。全15,794,107,404 call/1,988.146秒のprofileで、`is_square_attacked`は10,308,672回/累積1,385.185秒、`_move_candidates_for_piece`は156,972,383回/1,106.065秒、`is_piece_attacking_square`は53,929,209回/441.450秒、Square `__post_init__`は1,472,191,861回/635.166秒。累積時間は入れ子で重なる診断値であり、性能比較には使わない。pstatsは `/private/tmp/comparison-cli-performance-14-2026-11-03.pstats`。必要に応じた親CLI profileは後続のwall差から判断する。

### Task 2: 一つのホットパス仮説をTDDで改善

**対象ファイル:** profile結果に基づき、必要な既存コードと対応テストだけを選ぶ。現時点の候補は `kaname_shogi/one_ply_selection.py`、`kaname_shogi/movegen.py`、`kaname_shogi/undefended_piece_value.py`、`kaname_shogi/supported_piece_threat.py`、`kaname_shogi/material_piece_threat_value.py` と、既存の `tests/test_one_ply_selection.py`、`tests/test_movegen.py`、`tests/test_undefended_piece_value.py`、`tests/test_supported_piece_threat.py`、`tests/test_material_piece_threat_value.py`、`tests/test_piece_threat_selection.py`。profileが示さない候補へは着手しない。これらの範囲外が必要なら計画変更を先に承認してもらう。

- [x] **ステップ1: `GOAL.md` に実験票を先に作る。** 実験B2として、B1の根拠、事前生成した不変Squareタプルをboard-wide scanで再利用する一つの仮説、維持する振る舞い、42局での採否基準、対象テスト・全量テスト・代表変異をコード変更前に記録した。
- [x] **ステップ2: profileで選んだ契約のテストを追加する。** `tests/test_movegen.py`へSquareタプルの81マス順、is_square_attackedのboard scan、玉探索/王手scanの再利用を確認する3 testを追加した。変更前、最初の盤面では攻撃元が走査途中にあり生成回数テストは通ってしまったため、最後の走査マスから利く歩へ移し、キャッシュ不存在と81セル再生成のassertion Redを確認した。
- [x] **ステップ3: Redを確認し、最小変更する。** `movegen.py`の`is_square_attacked`、`_find_king_square`、`is_in_check`を事前生成したfile-major tupleで走査した。実際の差分では`_find_king_square`内の`Piece(KING, side)`生成もループ外へ移していたことが独立レビューで判明した。この追加変更を分離し、B2を単一仮説の実験として再計測する。合法候補・選択・rng・局面更新・終局のコードは変更していない。
- [x] **ステップ4: 単独テストGreenと検出力を確認する。** 対象3 testと既存movegen/U/V関連を計209件実行し成功。Temporary copyでboard scanの再生成を再導入した変異はcall-count assertion、キャッシュから最後のマスを除いた変異は長さassertionが意図どおり失敗した。最初のcopy起動はpackage root設定を誤ってImportErrorとなったため検出結果に数えず、正しい一時packageで再実行した。
- [x] **ステップ5: 静的検査と42局新規benchmarkを行う。** Ruff format、Ruff check、`git diff --check`、対象test216件を通過。初回42局実測458.47秒はSquare cacheとPiece生成ホイストが混在していたため、Square-only状態でfresh再測定しwall500.30秒、summary499.759秒、42/42局の指し手列・終局理由・勝者一致、合法再生42件、error等0を確認した。B2aとしてPiece生成ホイストだけを追加した測定は492.66秒（Square-only比1.53%改善）で、事前の5%基準未満のため棄却し、Square-onlyへ戻した。

  比較CLI引数と条件はTask 1の例と同じにし、各実験で新しい `--output-dir`（例: `comparison-cli-performance-42-trial-001-2026-11-03`）を使う。比較時間は `time` の実時間で取り、profileを付けない。
- [x] **ステップ6: 採否を記録する。** Square cache単独のwall500.30秒はB0から31.51%短縮、42/42棋譜一致と関連testを通過したためB2として採用する。初回混在458.47秒は単一仮説の効果量として扱わない。B2aのPieceホイスト単独版は1.53%改善で採用基準5%未満のため棄却した。どの42局結果も全量達成判定には使わない。
- [x] **ステップ7: 独立レビューと最速状態の保存を行う。** 初回レビューのImportant（Piece生成ホイスト交絡）とMinor（王手scan testの早期return）を是正し、再レビューでCritical/Important/Minorなし。Square-only変更を採用し、B2aは棄却。Refactor要否を確認し、レビュー済みコード・test・試行記録だけをstageしてこのtopic branchにcommitする。比較出力や開始時からある未追跡物はstageしない。

### Task 3: 保存・分析・再開契約、全体テスト、独立レビュー

**対象:** `kaname_shogi/compare_games.py`、`comparison.py`、`comparison_io.py`、`comparison_result_io.py`、`comparison_resume.py`、`analyze_comparison.py` と `tests/test_comparison_pipeline.py`、`tests/test_comparison_result_io.py`、`tests/test_comparison_resume.py`、`tests/test_analyze_comparison.py` の既存契約。Task 2の変更に合わせて対象を絞り、関係しない回帰テストは無用に重ねない。

- [ ] **ステップ1: 比較pipeline/結果reader/再開/analysisの関連テストを実行する。** 条件・出力・原子的保存・summary・既存局保持・再開・合法棋譜照合の該当契約を確認する。
- [ ] **ステップ2: テスト検出範囲を記録する。** `.codex/observations/test-driven-development.md` と `docs/knowledge/test-coverage-review.md` に従い、対象契約、検出したい誤り、代表ケース、単独と全体の検出範囲、未検証事項を `docs/learning/comparison-cli-performance.md` へ記録する。
- [ ] **ステップ3: Pythonユニットテスト全体を実行する。** `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/run_tests_parallel.py` を実行し、全発見モジュールの件数と所要を記録する。逐次実行は共有状態/順序依存を調べる場合またはランナー変更時に限る。
- [ ] **ステップ4: Refactor要否を判断して独立レビューを受ける。** Critical/Important/Minorを学習記録へ残す。Critical/Importantがあれば修正、全体検証、独立再レビューを行う。
- [ ] **ステップ5: 実施記録を保存する。** 承認済み計画との差分、全体検証、独立レビューの結論を文書へ反映し、計画対象ファイルだけをstageしてcommitする。mainへの統合・pushは行わない。

### Task 4: 最速状態を固定し、新規4,074局を計測

- [ ] **ステップ1: 8時間の残りと見込時間を照合する。** 8時間期限・最後の1時間の検証時間を確保できる場合のみ全量runを開始する。期限までに終わらない見込みなら起動せず、期限で未達保存する。
- [ ] **ステップ2: fresh run条件を再確認する。** 完了比較processなし、指定4 worker、元conditions/seed/positions hash一致、max-plies512、2,037組、空かつ未使用の新しい出力先、`--resume` なしを二重確認する。
- [ ] **ステップ3: 同条件4,074局を実行し壁時計を測る。** CLIプロセス起動から終了コード取得まで、外部の `time` 実時間を記録する。全局が新規計算される実行のみ有効とする。

  ```sh
  time PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m kaname_shogi.compare_games \
    --baseline material-piece-threat-v1 \
    --candidate material-piece-threat-value-v1 \
    --positions data/comparison/undefended-piece-value-positions-v1.json \
    --pairs-per-position 291 \
    --seed-list data/comparison/runs/undefended-piece-value-comparison-confirmation-2026-11-02-seeds.json \
    --max-plies 512 --workers 4 \
    --output-dir data/comparison/runs/comparison-cli-performance-4074-2026-11-03-v1
  ```

  実行前に出力先が存在しないことを確認する。存在する場合は別の新規名を選び、条件は変えない。
- [ ] **ステップ4: 完了条件と結果を全件照合する。** 4,074局完了、2,037組、未開始/進行中/故障/中断0、実時間30分以下を確認し、元の各局と指し手列・終局理由・勝者を突合する。summaryがresume由来のelapsed lower boundでないことを確認する。
- [ ] **ステップ5: 記録・レビュー差分を完了する。** GOALに最良実測/目標差/短縮率/条件/実行状態を記録する。学習記録に全仮説、成功・棄却、測定境界、テスト範囲、独立レビューを記す。索引・再開案内・計画実績を整え、リンクと差分を確認する。

## 計画上の停止条件

計画承認後にtimerを開始する。本人回答・承認待ちとアプリ停止による作業不能時間は開始・終了・理由をGOALへ記録して8時間から除く。2時間/4時間点検で目標距離と主要残時間を再計算する。プロフィール・42局計測から30分へ向けた次の一手が見込める限り続ける。対象条件を変える、結果が一致しないまま速さを採用する、あるいは追加技術・大規模再構成に切り替える場合は停止し、根拠付きの計画変更承認を得る。

## 実行状態

- 計画: 本人が2026-11-03 12:16:27 JSTに明示承認。
- Task 1: ステップ1〜5完了。14局profileとB0棋譜一致を確認。
- Task 2: Square-only B2を関連216 test、変異Red、fresh42局wall500.30秒、42/42棋譜一致・合法再生で検証。B2a Pieceホイスト単独版はwall492.66秒（1.53%）で棄却し、Square-onlyへ戻した。独立再レビューはCritical/Important/Minorなしで採用可。Refactor要否確認済み。B2変更・記録をcommitした。B3票は候補リストを避ける直接target判定として記録済み。
- Task 3〜4: 未着手。
- 現在のbranch: `codex/comparison-cli-performance`、開始HEAD `aa70d1d`。
