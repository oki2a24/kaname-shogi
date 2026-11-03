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

**対象ファイル:** profile結果に基づき、必要な既存コードと対応テストだけを選ぶ。現時点の候補は `kaname_shogi/one_ply_selection.py`、`kaname_shogi/movegen.py`、`kaname_shogi/undefended_piece_value.py`、`kaname_shogi/supported_piece_threat.py`、`kaname_shogi/material_piece_threat_value.py` と、既存の `tests/test_one_ply_selection.py`、`tests/test_movegen.py`、`tests/test_piece_attack.py`、`tests/test_undefended_piece_value.py`、`tests/test_supported_piece_threat.py`、`tests/test_material_piece_threat_value.py`、`tests/test_piece_threat_selection.py`。profileが示さない候補へは着手しない。これらの範囲外が必要なら計画変更を先に承認してもらう。


**計画変更（本人承認・2026-11-03 14:04 JST）:** B3のsource-target直接利き判定に伴い、`tests/test_piece_attack.py`を対象へ追加する。同ファイルの`test_candidate_error_propagates`は非公開の`_move_candidates_for_piece`呼出しに結合しているため、新しい内部直接判定helperからの例外伝播を検証するテストへ置換する。この1テスト以外の同ファイル変更、公開API、CLI、データ形式の変更は含めない。

**計画変更（本人承認・2026-11-03 14:10 JST）:** 関連test実行で`tests/test_square_attacks.py::test_preserves_board_on_success_and_failure`も旧`_move_candidates_for_piece`呼出しを前提とすることが判明した。テストの失敗を解消するため、この1件の例外mockだけを`_piece_attacks_target`へ更新する。関係のない同ファイル変更は含めない。

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

- [x] **ステップ1: 比較pipeline/結果reader/再開/analysisの関連テストを実行する。** 条件・出力・原子的保存・summary・既存局保持・再開・合法棋譜照合の該当契約を確認する。pipeline/result/resume/analyze 60件成功。後続の全体runnerにも関連契約を含む。
- [x] **ステップ2: テスト検出範囲を記録する。** `.codex/observations/test-driven-development.md` と `docs/knowledge/test-coverage-review.md` に従い、対象契約、検出したい誤り、代表ケース、単独と全体の検出範囲、未検証事項を `docs/learning/comparison-cli-performance.md` へ記録する。B2/B3/B4/B8について代表変異と未検証範囲を学習記録へ保存した。
- [x] **ステップ3: Pythonユニットテスト全体を実行する。** `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/run_tests_parallel.py` を実行し、全発見モジュールの件数と所要を記録する。逐次実行は共有状態/順序依存を調べる場合またはランナー変更時に限る。B8時点で1,088件/92 module/21.018秒成功。
- [x] **ステップ4: Refactor要否を判断して独立レビューを受ける。** Critical/Important/Minorを学習記録へ残す。B8のRefactorは不要と判断し、独立review Critical/Important/Minor 0/0/0。reviewerはtest・benchmarkを再実行していない。
- [x] **ステップ5: 実施記録を保存する。** 承認済み計画との差分、全体検証、独立レビューの結論を文書へ反映し、承認済みのコード・test・4文書だけをstageしてcommitした（`d911cc16`）。全体1091 tests/92 modules・19.383秒、Ruff、diff check、文書54リンクの存在を確認。mainへの統合・pushは行っていない。

### Task 4: 最速状態を固定し、新規4,074局を計測

- [x] **ステップ1: 8時間の残りと見込時間を照合する。** 2026-11-03 19:28 JST時点で期限まで約48分。B17 fresh42のwall84.79秒からの単純な局数比例は全量約2時間超となるが、小規模runからの推定であり性能実測としては扱わない。残り時間内の完了見込みを得られないため、全量runを起動しない。
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

- 計画: 本人が2026-11-03 12:16:27 JSTに明示承認。作業期限は20:16:27 JST。
- Task 1: 条件・seed・positions hashを照合。B0 fresh42 baselineと14局の初回profileを取得し、B0棋譜との一致を確認。
- Task 2: B2 Square-only 500.30秒、B3 direct-target 171.41秒、B4 target-ray 134.95秒をそれぞれ42/42棋譜一致・合法再生で確認。B2コードは`8b510a99`、B3は`f1fd3544`にcommit済み。B5 source candidate scan 132.32秒（2.0%）とB7 movegen Square cache 117.68秒（B6比2.15%）は性能差が採用基準未満で棄却。B6局所occupancy map 120.27秒を保持し、B8ではU/VのSquare構築をcached tuple参照へ変更。B8関連250 test、全体1,088 test/92 module/21.018秒、Ruff、独立review Critical/Important/Minor 0/0/0、fresh42 wall95.55秒、42/42棋譜一致・合法再生で確認。B9は内部の合法手適用案を関連214件・全体1,090件・Ruff・独立review 0/0/0・fresh42で検証したが、97.66秒でB8より2.2%遅く棄却し、B9コード/testを戻してB8を維持。B8変更・記録のcommitは未実施。
- Task 3: pipeline/result/resume/analyze 60件成功。B8後のB9全体test1,090/92 module・23.117秒、Ruff成功。B9独立reviewは初回Minor指摘をtest補強・drop mutationで解消し、再確認Critical/Important/Minor 0/0/0。B9を採用しない理由と失敗からの注意を学習記録へ記載した。最終stage/commitと記録照合は未完了。
- Task 4: B8後profileとB9〜B15のfresh42で根本処理を調査。B9合法適用fast pathは97.66秒でB8比2.2%遅く棄却。B10既知相手玉helperは初回85.64秒/repeat85.21秒、42/42棋譜一致・合法再生、review0/0/0で最速採用候補。B11 82.89秒（2.7%）、B12 84.51秒（0.8%）、B14 83.51秒（2.0%）は棄却。B15は80.27/82.23秒、fresh42平均81.25秒（4.65%）でB10より速い傾向だったが、5%棄却線との反復判定で不採用としてcode/testを戻した。全fresh42は42/42棋譜一致・合法再生。B10更新profileは14/14棋譜一致。`is_square_attacked`10.31m/56.687累積秒、U呼出し6.58m/35.587秒、V source候補34.0m/20.044秒。これら診断値はwall推定でない。B16案はU/Vに対象別攻撃情報を一回計算して一時handoffする協調変更で、複数moduleをまたぐ。計画変更の必要性・代替・検証範囲を次節に記し、本人の明示承認待ち。全4,074局未開始。現在18:06、期限20:16:27、残り約2時間10分。最後1時間は検証/review/記録を優先。
- 現在のbranch: `codex/comparison-cli-performance`、開始HEAD `aa70d1d`。main統合・pushは範囲外。

### 計画変更B16（18:20:55 JST承認・実施・棄却）

**観測根拠:** B13 profileはtarget-centricな攻撃判定に`is_square_attacked`10.31m回/56.687 cumulative秒、Vの`_target_source_candidates`34.0m/20.044秒と`is_piece_attacking_square`15.58m/16.630秒を示した。B15ではUの攻撃/支え2 ray queryを1回へまとめたが、同条件fresh42二計測の単純平均は81.25秒、B10比4.65%で5%棄却線に届かなかった。profile累積値はwall予測として用いず、U/V間の重複したtarget/source処理を一度にまとめる仮説を提案する。

**提案範囲:** `movegen.py`に、指定した占有target群から各targetの8方向ray先頭駒と桂sourceを一度ずつ読み、各sourceがtargetへ幾何学的に利くかを既存`_piece_attacks_target`で一度判定し、`target index -> (target Piece, tuple[(source Piece, attacks_target)])`の局所snapshotを返す内部操作を追加する。ray先頭駒はintervening-clearを真、桂sourceは既定の遮蔽判定で扱う。`material_piece_threat_value.py`はM計算後にこのsnapshotを一度作り、U/V専用の内部集計へ同じsnapshotを渡す。`undefended_piece_value.py`は同じsideへの攻撃と支えの有無を、`supported_piece_threat.py`は同side supportと相手のstrict-lower-value attackをsnapshotから計算する。各公開単独APIの引数・戻り値は保つ。単独のbalance APIは一回のsnapshotを両sideの集計で共有し、片sideだけの公開APIは一回snapshotを作る。旧M+V方式のV balanceも、この単独balance経路から一回のsnapshotを使う。対象候補は `movegen.py`, `material_piece_threat_value.py`, `undefended_piece_value.py`, `supported_piece_threat.py` と、それぞれの既存test moduleのみ。新しいmodule・依存・永続cache・Board内部配列への直接アクセスは加えない。

**既存の呼び出し経路と構造への影響:** 現在の合成評価`evaluate_material_piece_threat_value`はMを計算した後、Uのbalance、Vのbalanceを別々に呼ぶ。Uは各対象駒について相手の利きと味方の支えを`is_square_attacked`へ別々に尋ね、視点・反対側の集計でも同じ盤を再走査する。Vは先手・後手のcountを別々に計算し、各countで盤面を読み、対象候補ごとにray/桂sourceと幾何学的な利きを調べる。提案後は複合評価からU/Vの非公開集計helperへ一時snapshotを渡す経路が加わり、両者の内部実装が共通記録を読む。単独で使う既存公開関数は引数・戻り値を変えず、その場でsnapshotを用意して従来どおり使えるようにする。旧方式側の`material_piece_threat.py`もV balanceを利用するため、公開V関数の内部更新によって旧方式でも単独用snapshotを作る。よって両方式の実行時間に影響し得るが、Vの得点と方式の条件は変えず、fresh42を両方式込みで測る。内部モジュール間の依存と局所データの受け渡しは増えるが、`Position`/`Board`のデータ構造、M/U/Vの意味と重み、合法手生成、探索・終局、CLI、棋譜・conditions・summaryの保存形式、再開・分析の流れは変えない。速度上の反対仮説として、現在の`is_square_attacked`は最初の該当攻撃で早期returnし、Vも支えと低価値攻撃がそろうと対象走査を打ち切る。先に全sourceの幾何学判定を作るsnapshotは、現在なら短絡して省ける判定まで行って遅くなる可能性がある。さらに毎評価で一時tuple等を割り当てる。これらの費用が削減分を上回れば、正確性を満たしてもB16を棄却してB10へ戻す。採否は両方式を含む同条件fresh42の実時間と完全照合で決める。

**維持条件:** 幾何学的利き、ピンを除外しない意味、ray遮蔽、target上の駒、桂の飛越し、成駒、先後、U対象/価値/符号、Vのsupportとstrict lower-value attacker、例外伝播、局面不変、評価値、候補順/RNG、終局、同seedの棋譜、保存/再開/analysisを変えない。snapshotはひとつの評価呼出しだけで生存し、局面更新後に再利用しない。

**検証案:** 実装前に独立source-reference testとsnapshot未実装のassertion Redを確認。実装後は全駒種/先後/遮蔽/成駒/target占有を含む代表boardでtarget/source記録と従来の個別公開API結果を独立照合し、両U/V値・例外・盤面/手番/持ち駒のsnapshotを比較する。誤ったsource共有、ray clear誤設定、strict-lower-valueの境界を代表mutationで検出。関連/full test・Ruff・diff・独立review後、profileなしfresh42をB10 seed/conditions・4 worker・新出力で計測し、42/42の棋譜・終局・勝者/合法再生を照合する。15%以上改善はreview後に保持、5%以内は棄却、5〜15%は残り期限に余裕がある場合だけ同コードを一度反復する。新しい全量4,074局は期限内の見込時間と最後の1時間を確保できる場合のみ判断する。

**代替案:** (a) B10を維持し、残り期限を独立review・正しさ確認・記録へ使う。(b) 計画変更をしない。承認済みscope内であってもB11/B12/B14/B15と同じ小幅変更は同じ測定根拠のまま繰り返さない。攻撃snapshotのallocation costが削減分を越えた場合はこの案を棄却し、B10へ戻す。

**承認状態（2026-11-03 18:20:55 JST）:** 本人は既存構造への具体的な影響とsnapshotの意味を確認した上で、B16範囲を明示承認した。snapshotは一評価中だけメモリ上に作り、同じ局面で決定的な内容を持ち、盤面・ファイルを変更しない。一回の複合M+U+V評価でU/Vが共有し、単独balanceは一回だけ作って両side集計へ使う。承認対象は`movegen.py`、`material_piece_threat_value.py`、`undefended_piece_value.py`、`supported_piece_threat.py`と各対応既存test。8時間期限は20:16:27 JSTのまま、追加除外は0分。TDDを開始する。


**実施結果・採否:** B16初回fresh42 wall80.86秒、同コードrepeat79.56秒、平均80.21秒でB10 85.21秒比5.87%短縮。42/42棋譜/終局/勝者一致・合法再生、各run lower_bound=false。関連262件/full1100件、Ruff成功、独立review Critical/Important/Minor 0/0/0。事前採用線15%未達のためB16 runtime/test変更を除去。rollback fresh42は97.00秒で棋譜42/42一致だがsource hashがB10既知値と異なるため、byte-identicalなB10復元は未確認。詳細なmutation・失敗した試行・suite結果は[学習記録](../learning/comparison-cli-performance.md)を参照。


### 計画変更案B17（2026-11-03 18:52 JST改訂、19:04:34 JST承認）

**観測根拠:** B16の先行全件snapshotはfresh42平均80.21秒、B10の85.21秒比5.87%短縮に留まり、15%採用線を満たさなかった。snapshotはU/Vの早期return・Vのtarget走査short-circuitを外す設計だった。rollback fresh42は97.00秒でB10と同じ棋譜を42/42返したがsource fingerprintが異なる。B10保存patchとHEADからの再構成はsource hash 0899e4c2…でB10記録c58bbfe…と一致せず、Gitのunreachable 16 commits/228 root treesにもhash一致はなかった。B17案のため7開始局面で既存U・Vを個別計測したところ、Uはgeometry query 1,249回、Vは997回、同じ(source,target)の重複候補は996回だった。これは開始局面だけのquery-countで、全局・wall速度の予測ではない。 B10-14 cProfileでも_piece_attacks_targetは37,347,155回/19.204 cumulative秒、うちis_piece_attacking_square callerが15,578,731回/8.781秒、_is_target_attacked_by_side callerが21,768,424回/10.423秒だった。cProfile累積秒はwall予測に使わず、source-target共有候補が多い処理を特定する根拠にだけ使う。

**仮説:** 合成M+U+V評価の同じ不変盤面について、Uのtarget-centric reverse-ray経路とVのsource-candidate経路が共に要求した幾何判定(source,target)のbooleanを、一回のevaluation内で遅延記録して再利用する。7つの開始局面では独立呼出し計2,246件中996件のV queryがUと同じpairを参照した。dict lookup/割当が節約を打ち消す可能性は残るため、実時間で検証する。

**提案範囲と内部経路:** movegen.pyに、board・同じsource Piece・source Square・target Square・一時dict・clear-path証明を受けるprivate geometry helperを置く。keyは(source,target)。cache missでは既存_piece_attacks_targetを呼び、正常return後にだけboolを保存して、例外はそのまま伝える。Uの_is_target_attacked_by_sideとVのsource candidate判定を、複合評価から渡された同じdictを使うprivate helperへ接続する。ray先頭から来たUのclear-path=Trueはray走査が中間空きを証明した場合だけ許し、V側の通常判定と同じ幾何結果となる。material_piece_threat_value.pyは一回のM+U+V評価だけでdictを作り、undefended_piece_value.pyとsupported_piece_threat.pyのprivate集計へ渡す。公開単独APIと旧M+V経路は変更しない。cacheは同じ不変Boardを使う同期評価呼出しの間だけ存在し、別Board/evaluationへ持ち越さない。永続cache、module-global、新module、新依存、Board内部配列参照なし。対象はmovegen.py、material_piece_threat_value.py、undefended_piece_value.py、supported_piece_threat.pyと各既存testのみ。

**維持条件:** U/Vの独立API、評価値・符号・strict value比較、幾何学的利き・遮蔽・成駒・ピン、例外伝播、局面不変、候補手列挙・乱数消費順、終局・棋譜・保存/再開/analysisを変えない。同じ入力/seedの指し手列・終局理由・勝者を一致させる。key省略、誤ったclear-path証明、例外保存、別評価や別盤面へのcache再利用を防ぐ。

**TDD・検出力確認:** 実装前に、(1)同じsource/target二回目がgeometry query一回、(2)別sourceまたはtargetは共有しない、(3)query例外をcacheしない、(4)実測7開始局面でU/Vが重なるsource-target queryを一回にできる、(5)短絡した未到達candidateを先行計算しない、(6)複合評価内だけ共有し単独公開APIは従来経路を通る、を直接検査するtestを追加し、未実装/未共有時のassertion Redを確認する。実装後は独立な従来public API referenceでU/V/複合評価値を照合し、board/手番/持ち駒の前後stateを比較する。想定test名: test_same_source_target_reuses_geometry, test_different_source_or_target_does_not_share, test_failed_geometry_is_not_cached, test_unreached_candidates_remain_unevaluated, test_composite_evaluation_shares_geometry_cache. Mutationはkey target欠落、例外保存、ray clear誤設定、eager化、U/V辞書分離、evaluation間再利用を検出する。局所/関連/full tests、Ruff import sort/format/check、diff、独立Critical/Important/Minor reviewを行う。

**実測と採否:** 元のseed/position/side schedule・方式・512手・4 workerのfresh42を新規出力で実計算し、current rollback(97.00秒、sha f5f6…)とB10歴史値85.21秒(sha c58bb…)の双方に対しconditions差、棋譜42/42、合法再生、終局理由、winner/policyを照合する。fresh42の初回wallがB10歴史値より15%以上短縮（72.43秒以下）なら同コードでもう一度fresh42を実行して平均で採否を判断する。初回が5〜15%短縮でもrepeatは一回だけとし、2-run平均が72.43秒以下の場合のみ採用候補とする。5%以内は棄却し、最後の1時間前にrepeatまで完了できない場合は採用せず検証/記録を優先。少数局で4,074局30分達成とはしない。全量計測は残り時間に実際に完了する見込みがある場合だけ開始する。未達ならB17 runtime/test変更を外す。

**代替案:** B17を行わず、B10相当状態との差分復元調査と検証だけを続ける。B17の実時間が閾値に届かなければコード/testを戻す。B16 snapshotやB11/B12/B14/B15の小幅変更を根拠なく再試行しない。

**承認状態（2026-11-03 19:04:34 JST）:** 本人から「ゴールに沿っているなら承認」と回答を受領した。B17は比較条件・棋力・信頼性を変えずsource-targetの重複geometryだけを削る案で、fresh42の採用線を歴史的B10比15%以上に保ち、最終目標4,074局/30分を緩めないため、条件に合致すると判断して明示承認として扱う。B17のTDDを開始する。元の作業期限20:16:27 JSTは変更せず、独立作業を継続したため承認待ち除外0分。

**実施結果・採否（2026-11-03 19:17 JST）:** 実装前のcache契約4件は未実装helperへのassertionで失敗し、合成評価のRedは公開U/V個別queryで3 unique pairsのところ実装前に5 callsとなることを検出した。実装後、関連232件、全体1098件/92 modules、Ruff check/format・差分検査が成功。5代表mutation（source key欠落、target key欠落、False再計算、ray clear proof欠落、U/V別辞書）はそれぞれ意図したassertionで検出。独立review初回Critical 0・Important 0・Minor 1（従来module alias存在を固定するtest不足）。U/V alias同一性testとalias削除変異の検出を追加し、再reviewでCritical/Important/Minor 0/0/0。

新規出力`comparison-cli-performance-42-B17-lazy-geometry-cache-2026-11-03`で既存21 seed組を再利用入力として全42局を新規計算（棋譜自体は再利用せず）。wall84.79秒、summary84.400539833秒、42/42局・21/21組、成功手4606、詰み42、error/interrupted/unstarted/in-flight 0、`elapsed_lower_bound=false`。歴史的B10 fresh42 repeat 85.21秒との比較では0.49%短縮だけで、事前5%棄却線内、15%採用線にも届かず。B10との差はconditionsの`source_sha256`のみ。seed/side/position schedule、開始局面、moves、終局reason、winner side/policyが42/42一致し、合法再生42/42。測定ぶれを超える根拠がないためrepeatは行わず、計画どおりB17 runtime/test差分を除去した。B17 source fingerprintは`f116cf293cd7070f276edea858d7a8077d56241c35fb4356359e236a7425b81d`。30分目標は未達、4,074局は未計測。


### 計画変更B18（2026-11-03 19:34 JST、本人の選択委任を受けて決定）

**観測根拠:** B10-14 cProfileで`Square.__post_init__`が55,286,947回/24.635累積秒、その中の`any` generatorが9.923秒。累積profile時間は入れ子を含む診断値でwall予測ではない。fresh42はB17 84.79秒でもB10 85.21秒比0.49%に留まり、必要proxy速度へ約5.43倍不足する。局所Square検証だけでは目標を満たさないが、構造が単純で既存データ契約に触れず、短時間で棄却できるため候補を選んだ。

**仮説と対象:** `Square.__post_init__`のtuple/generator/`any`をfileとrankの明示的な型・範囲条件へ置き換えると、同じ無効値を拒否したまま、Squareを大量生成する探索時のgenerator評価・一時tuple割当を減らせる。対象は`kaname_shogi/model.py`と`tests/test_model.py`だけ。dataclass field、constructor、repr、equality/hash、`Square.to_index`、Board内部表現、既存APIは変えない。

**維持条件・検出力:** file/rankの1〜9境界、bool・float・文字列・Noneを拒否する現行契約、同じValueError型/message、正常Squareの不変性・座標順・indexを維持する。製品コード変更前に、`builtins.any`がSquare検証経路で呼ばれない構造testを足し、現実装ではSquare生成という成功振る舞いに対する意図したRedを確認する。既存の不正座標testとvalid boundary/index/immutability testを利用し、tuple/generator/anyを復活する変異、型条件を落とす変異、境界条件を誤る変異を意図したassertionで検出する。単独/関連/full suite、Ruff import sort/format/check、diff、独立review C/I/Mを実施する。

**実測と採否:** 元のB10 seed/position/side schedule・2方式・512手・4 workerのfresh42を未使用出力先へ全局新規計算する。conditions・seed・初期局面・moves・終局reason・winner/policyを42/42照合し、合法再生42/42を確認する。15%以上は強い採用効果、5%以内/悪化は棄却、5〜15%は同コードで一度repeatする。repeat後、2-run平均で5%以上短縮し、各runの条件・42/42棋譜・合法再生が一致すれば、fastest correct状態として保持して次の仮説へ進む。15%未満の保持は作業完了や目標達成を意味しない。全4,074局/30分はfresh42で代用しない。小標本の単純線形投影は実測値と称さず、期限内に完了見込みがない全量runは開始しない。

**計画判断:** 2026-11-03 19:33 JST、本人は候補選択の質問を避け「ゴールに沿って進めて」と指示した。これは技術候補の選択をアシスタントへ委ねる明示指示として受け取り、profile根拠と影響の小ささから上記B18を選択した。追加承認待ちはなく、元の作業期限20:16:27 JSTは変えない。開始前ソースfingerprintは`f5f6b0ca96e6b489752579502c5dcf3313283be2369db8994f76865ba7b326be`。

**実施結果・採否（2026-11-03 19:41 JST）:** 検証generatorを直接条件式へ変えたfresh42はwall77.36秒/summary77.019177250秒、反復はwall78.05秒/summary77.711795333秒。各42/42局、21組、4606成功手、詰み42、error等0、lower_bound=false。2-run平均wall77.705秒はB10 repeat85.21秒より8.8%短い。同コードrun同士の差は0.9%、既知B8同コード差4.4%より小さい。両runはB10と`git`/`source_sha256`のprovenanceのみ異なり、seed/side/schedule、初期局面、moves/reason/winner side/policy42/42一致、legal replay42/42。既存の採用済みB10もB8同コード2-run平均より8.6%短い状態で保持した先例と一致するため、B18を次の改善の基盤として保持する判断へ更新した。これは中間の再現可能な改善であり、30分目標未達・全4,074局未計測。

**検出力・review:** `test_square_validation_does_not_call_any`は未実装時にSquare生成でmock assertion failureを確認。rank上限を10へ広げる変異は不正座標testの`rank=10` assertionで失敗、ValueError文言変更変異は16 subtestsでregex assertion failure。修正後model module28件と全体1092件/92 modules/18.305秒成功、Ruff import sort/format/check・diff check成功。独立レビューは初回Critical0/Important0/Minor1（文言をtest固定していない）、`assertRaisesRegex`で補強後の再reviewはCritical/Important/Minor 0/0/0。reviewerはtestを再実行していない。

### 計画変更B19（2026-11-03 19:44 JST、候補選択を本人から委任）

**観測根拠:** B10-14の並列cProfileで`Square.to_index`は406,836,055 calls/16.442 cumulative seconds。値は重複する累積profileでありwall予測ではない。B18はfresh42を2回新規実行し平均wall77.705秒、B10 fresh42 repeat85.21秒比8.8%短縮したが、30分目標に必要なproxy速度までは約4.97倍不足する。Squareのdata representationやBoardの格納方式を変える案は等値・hash・メモリ・参照経路へ影響が広く、期限内の確認時間を要するため今回は選ばない。

**仮説と対象:** 現行`Square.to_index`の`(file - 1) * 9 + (rank - 1)`は整数演算を4個実行する。等価式`file * 9 + rank - 10`は算術演算を3個に減らせるため、数億回の呼出し経路で時間を削る可能性がある。対象を`kaname_shogi/model.py`と`tests/test_model.py`に限定する。Squareのfields・constructor・validation・repr・equality/hash、index順、Board格納、候補順、乱数、局面・合法手・棋譜・保存/再開は変更しない。

**テスト契約・検出力:** 81マスを筋優先・段昇順に列挙したとき、`to_index`が0〜80の連番へ各座標を一意に対応させる契約を明示する。既存の「集合が0〜80」というtestだけでは任意の座標入替を検出できないため、列挙順から独立に期待indexを作り、81件すべてを対応づけるtestを先に追加する。これは動作を増やす変更ではないので、現実装でGreenとなる理由を記録し、off-by-one式変異でそのassertionがRedとなることを確かめる。既存の四隅・７六、不正座標/型、immutability、Board初期配置testが補完する。局所test・全体suite・Ruff・diff・独立review C/I/Mを行う。

**fresh42測定・採否:** B18の2-run平均wall77.705秒を比較値とし、元と同じseed/局面/side/policy/512手/4 worker、別の新規出力先で全42局を新規計算する。初回が5%未満の改善なら測定差内として棄却し、5%以上改善なら期限内に同コードを一度再実行し、平均5%以上かつconditions・42/42棋譜・reason/winner・合法再生が一致した場合にだけ保持候補とする。15%以上は強い改善として記録する。初回または平均が5%未満なら元の式へ戻す。全量4074局はfresh42から達成とせず、期限内に実完了見込みがないため開始しない。

**計画判断:** 2026-11-03 19:44 JST、本人から候補選択は人間へ尋ねずゴールに沿って進めるよう明示された。profile上で頻出し、公開データ表現を変えない単一の算術式を選び、上記の限定範囲でTDD・測定・検証を進める。作業開始12:16:27 JSTおよび終了期限20:16:27 JSTを維持し、承認待ち除外時間は0分。

**B19実施結果・採否（2026-11-03 19:50 JST）:** 全81座標対応testは現式でGreen。式の減算を1つ増やすoff-by-one mutationを入れると81 subtests全てが期待値assertionで失敗し、test検出を確認した。候補式`file * 9 + rank - 10`へ一時変更したfresh42は新規出力`comparison-cli-performance-42-B19-to-index-arithmetic-2026-11-03`、CLI起動〜終了wall79.44秒、summary79.104882750秒。42/42局・21/21組・4,606成功手・checkmate42、error/interrupted/unstarted/in-flight0、`elapsed_lower_bound=false`。B18 repeat77.705秒平均より2.2%遅く、5%採用線未達のためrepeatせず候補式をrollback。B19側conditions差は`source_sha256`のみ、開始局面/seed/side/policy/schedule/moves/reason/winner42/42一致、legal replay42/42。独立review C/I/M0/0/0。全体suiteはrollback後1093 tests/92 modules/18.576秒成功。B18のsource fingerprint `32e3686d734e8ebbce9ca78414c4771a842324497b071a6d52174d5c2d77efdc`へ復帰した。B19で明示化した全81 file-major index mapping testは既存の集合0〜80 testが検出しない座標置換誤りを防ぐため保持し、これは性能改善の主張ではない。

### 計画変更B20（2026-11-03 19:51 JST、本人の候補選択委任に基づく）

**観測根拠:** B10-14 aggregate profileで`Board.piece_at`は404,499,935 calls/53.201 cumulative seconds、`Square.to_index`は406,836,055 calls/16.442 cumulative seconds、`Square.__post_init__`は55,286,947 calls/24.635 cumulative seconds。いずれも並列profileの重複累積値でwall時間の予測には使わない。呼出し回数はSquare生成の約7.3倍で、検証済みB18 fresh42平均77.705秒から必要proxyに約4.97倍不足する。

**仮説と範囲:** Squareの筋・段は生成後に変更できない。検証を通過したSquareの`__post_init__`で、その筋・段だけから決まるfile-major indexを非dataclass/private属性へ一度だけ記録し、`to_index()`は保存した整数を返すと、高頻度の4演算とPython method-body実行を減らせる可能性がある。新しい永続cacheやglobal cacheではなく、各不変Square値の寿命だけに閉じる。対象は`kaname_shogi/model.py`と`tests/test_model.py`。コンストラクタ引数、宣言済みdataclass fields、repr、等値・hash、表示、既存API、0〜80 mapping、Board cells、評価式、候補列挙・乱数、局面・合法手・棋譜・終局・保存/再開は変えない。cache依存がfile/rankだけであることを、Squareのstrict validationとfrozen contractに基づいて確認する。余分なinstance-dict entryと初期化費用が利益を上回るriskも測定対象とする。

**TDD・検出力:** 先に`to_index`がprivate computed indexを使い、cacheがdataclass fieldを増やさず、repr/equality/hashとimmutabilityを保つtestを追加する。未実装ではprivate index欠落の対象assertionでRed。既存の全81 file-major mapping testで添字変異を検出する。既存の四隅・７六、invalid coordinate/type、Square immutable、Board初期配置testが補完する。明示的なoff-by-one cache式・declared dataclass fieldへの変異・cache値のstale化などが意図したassertionで失敗するか確認。model suite、full suite、Ruff・diff、独立C/I/M review後にfresh42を計測する。

**fresh42測定・採否:** 4 workers、同じseed-list sha `82b5a5f5...`、7局面/21組/42局、両方式・先後・512手で全局を新規計算。別出力先へ保存し、B18の2-run平均77.705秒と比較する。5%以上短縮した場合のみ同コードfresh42を一度repeatし、平均5%以上短縮かつ条件/初期局面/moves/reason/winner/policy/合法再生42/42なら保持候補とする。5%未満・同等・悪化ならcacheを外しB18へ戻す。余分なinstance stateの影響を含む実時間で判定し、42局から全量達成を宣言しない。

**計画判断:** 本人は候補選択で人間へ質問せず、ゴールに沿って進めるよう指示している。上記のhot path頻度を根拠に、公開Square/Board APIと永続形式を変えず不変座標だけを使う限定案を選択した。作業開始12:16:27 JST・期限20:16:27 JSTを維持し、追加承認待ちによる除外時間なし。

**B20実施結果・採否（2026-11-03 19:56 JST）:** B20 pre-code Redはcacheなしで`_index`期待値59に対してNoneとなるassertion failure。`(file - 1) * 9 + (rank - 1) + 1`の変異は81座標mapping testで81件すべて失敗。候補コードの5,000,000回呼出しmicrobenchmark 5回では既存method body median0.1345秒に対し属性読出しmedian0.0915秒、1.47倍だったが、Square生成時の追加dict entry/演算を含むゲーム計測とは異なる。fresh42新規出力`comparison-cli-performance-42-B20-cached-square-index-2026-11-03`はwall75.86秒/summary75.519626958秒、42/42局・21組・4,606手・checkmate42・error等0・lower_bound=false。B18 repeat条件との差はsource_sha256のみ、seed/side/schedule/初期局面/moves/reason/winner/policy42/42一致、legal replay42/42。B18平均77.705秒より2.37%短いが5%線および観測済み実行差の範囲内であり、repeatせず棄却。runtime cacheとB20専用testを除去し、B18 runtimeへrollback。独立reviewはCritical0/Important0/Minor1（to_indexがcacheを読むことをtest固定していない）。この不足を検出するtestを一時作成したが、閾値未達で候補をrollbackしたため未採用・未実行。詳細は学習記録。

### 計画変更B21（2026-11-03 19:56 JST、候補選択は本人から委任）

**観測根拠:** Board.piece_at 404,499,935 calls/53.201 cumulative secondsとSquare.to_index406,836,055 calls/16.442 secondsの大半が同じ高頻度読み取り経路と見られる。B20はto_index内部の算術を属性取得へ置き換えたがfresh42は2.37%しか短縮しなかった。method call自体をBoardの最頻読取から外す案が異なる部分を狙う。cProfileはwall予測に用いない。

**仮説と範囲:** `Board.piece_at(square)`内で、検証済みSquareの同じfile-major formulaを直接使い、`Square.to_index()`の追加Python呼出しを省けばBoard readを速められる可能性がある。対象は`kaname_shogi/model.py`と`tests/test_model.py`。Boardの内部list・公開piece_at/set_piece契約・Square.to_index・index order・Square equality/hash/immutability・評価値・合法手・move order/RNG・終局・棋譜・保存/再開は維持する。既存の「添字変換をSquareへ集約」の設計には例外を一つ設け、Boardのprofile済みread hotspotだけで式をinlineするため、理由をBoard.piece_at docstring/commentへ説明する。mapping consistency testがSquare.to_index/set_pieceとのズレを検出する。

**TDD・検出力:** 81 Square全てに異なる隣接駒patternをset_pieceで置き、Square.to_indexを例外mockにして全マスpiece_atを読むtestを先に追加。現実装は既存method呼出し時のassertionでRed。変更後は全81のPiece identityが一致する。off-by-one formula mutationで読み取り期待値のassertion失敗、Square.to_index呼出しへの回帰をmockで検出する。既存の空盤、特定マスだけ変更、clear、初期配置、全81 index mapping testと関連/full suiteで補完。Ruff、diff、独立C/I/M review後にfresh42を実測。

**fresh42測定・採否:** B18平均77.705秒、新しい出力先、同じ42 seed sha/7局面/21組/両方式/先後/512手/4 workersで全42局を新規計算。初回5%未満は棄却・rollback、5%以上は同コードを一度repeatし、2-run平均5%以上かつ条件・42/42棋譜/終局・勝者・合法再生一致なら保持候補。15%以上は強い効果として記録。全量実行・達成判定へは置き換えない。

**計画判断:** 本人は「このてのことを人間に聞くことは禁止する。ゴールに沿って進めて」と明示し、候補選択を委任した。B20の範囲を最小化しても必要proxyに約4.97倍不足するため、profileで実測された最頻read pathからmethod-call overheadを狙うB21を選択。8時間期限20:16:27 JSTを維持し、追加承認待ち除外0分。

**B21実施結果・採否（2026-11-03 20:01 JST）:** 初期Redは現Board.piece_atからSquare.to_indexを呼び、mock assertionで全81座標失敗。off-by-one formula mutationは80 assertion failure + index81範囲外1 errorとなり、ずれを検出した。testの初稿はRuff B905 zip(strict=)で止まったため、Python 3.9互換を守ってenumerate + index参照に直した。実装後testは全座標のPiece identityとto_index非呼出しを確認。Ruff import sort/format/check成功。B21 fresh42は新規出力`comparison-cli-performance-42-B21-inline-board-read-2026-11-03` wall74.94秒/summary74.592958500秒、42/42局・21組・4,606手・checkmate42・error等0・lower_bound=false。B18 repeatとsource_sha256以外条件差なし、開始局面/seed/side/schedule/moves/reason/winner/policy42/42一致、legal replay42/42。B18 mean77.705秒より3.56%短いだけで、事前5%線と既知B8同コードばらつき4.4%を超えないためrepeatせず棄却。runtimeと専用testをrollback。実装中はmodel30 test/full1094 tests/92 modules/17.959秒成功。独立レビューC/I/M0/0/0。rollback後はB18 + B19全81 index mapping coverageのみへ戻し、model29 test/full1093 tests/92 modules/18.325秒成功。最終source fingerprintがB18 `32e3686d...`と一致することを確認。
