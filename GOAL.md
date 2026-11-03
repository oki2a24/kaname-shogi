# 比較CLI性能目標

## 目標

比較CLIで、確認比較と同じ条件の新規4,074局を、同じPC・4 workerで実際に全局計算し、30分以内に完了する。保存済み棋譜の再利用、結果の埋め込み、局・手の省略、計測範囲の縮小は性能改善に数えない。目標値は自主的に緩和しない。

## 変えてはならない条件

- baseline `material-piece-threat-v1` と candidate `material-piece-threat-value-v1`。
- 7局面、局面ファイル `data/comparison/undefended-piece-value-positions-v1.json`、sha256 `256437ea5e0465f4e1ed777deecf091ef1745bbdbab6b70e805e88685b94ad61`。
- 各局面291組、計2,037組・4,074局。元seed一覧 `data/comparison/runs/undefended-piece-value-comparison-confirmation-2026-11-02-seeds.json` を使い、新しいseedへ置き換えない。
- 先後交換、方式ごとのseed、512手上限、4 worker。
- 評価式、候補順、同点時の扱いと乱数消費、合法手生成、詰み・千日手・その他の終局判定を維持する。
- 入力とseedが同じ場合、指し手列・終局理由・勝者を一致させる。保存・分析・再開機能も維持する。

## 作業開始と期限

- **計画承認:** 本人が2026-11-03 12:16:27 JSTに明示承認。
- **作業場所:** `/Users/oki2a24/kaname-shogi`
- **ブランチ:** `codex/comparison-cli-performance`
- **開始HEAD:** `aa70d1deaec4c666839fb951aaba5a83a9f59b01`（開始時の `main` と `origin/main` は一致）。
- **開始時刻:** 2026-11-03 12:16:27 JST。
- **終了予定:** 2026-11-03 20:16:27 JST。期限は延長しない。
- **承認待ちの除外時間:** 2026-11-03 12:08:38〜12:16:27 JST、7分49秒。計画承認前であり、8時間には含めない。
- **追加範囲承認待ち:** `tests/test_square_attacks.py`例外test 1件の更新許可を14:08頃〜14:10:50 JST頃に依頼した。許可依存の変更は保留したが、承認中も記録更新・確認など独立作業を継続し、全作業の停止はなかったため、追加の除外時間は0分。期限は20:16:27 JSTのまま。
- **環境:** CPython 3.15.2、Ruff 0.16.10、`core.hooksPath=.githooks`。開始時の作業ツリーには `docs/README.md`、`docs/resume.md` の変更と、GOAL・計画・学習記録・既存比較データ・保全アーカイブ等の未追跡物がある。これら開始前の変更・成果物は保持し、今回の対象だけを変更する。
- **実行中比較:** `ps` はOS権限で拒否された。2026-11-03 12:16〜12:17 JSTにActivity Monitorの全プロセスでPython名を確認し、表示された2件の実行ファイル・親プロセス・開いているファイルを調べた。1件はUI確認のosascript配下、もう1件はHermes環境とstate/logのみを開くプロセスであり、比較CLIではない。
- **保護対象:** 開始時の未追跡データ・保全アーカイブを保持し、既存比較成果物の保存先へ書き込まない。
- **元比較条件の再検算（2026-11-03 12:19 JST）:** conditions/summary/seed-list/局面ファイルを独立照合。7局面×291組=2,037組・4,074局、schedule 4,074件、seed-list 2,037件、最大512手、4 worker、両policy、位置SHA `256437ea5e0465f4e1ed777deecf091ef1745bbdbab6b70e805e88685b94ad61` が一致。保存済みrunは局JSON 4,074件、summary complete、未開始・故障・中断0。`elapsed_lower_bound=true` は確認済みで、基準wall timeには使わない。

## 既知の基準と現在の限界

2026-11-02の確認比較はsummary上で4,074局完了、2,037組、未開始・進行中・故障・中断0。`conditions.json` はprocess-pool 4 worker、512手上限、各局面291組を記録する。実行途中の停止後に再開したためsummaryは `elapsed_lower_bound=true`、`elapsed_ns=69063743406167`（下限69,063.743秒、約19時間11分）。これは確定した総実時間ではなく、厳密な性能基準に使わない。

同summaryの一手計時合計は旧方式111,051.851秒/264,964手（平均419.121ms）、新方式158,786.204秒/265,750手（平均597.502ms）。合計269,838.055秒はworker間で重なる各局の操作時間で、壁時計経過時間そのものではない。4 workerが理想的に稼働する仮定でも30分へ届くにはこの操作時間を約37.48倍短縮する必要があるという難度の目安に限り、達成推定には使わない。pilotの28局426.373秒は過去記録であり、今回の再現計測ではない。

ソースを読む限り、一手選択では合法手候補ごとに適用・詰み確認・評価が行われる。価値評価はM/U/Vを別操作として計算し、U/Vとも盤上の利きを繰り返し照会する。ここが支配的かどうかは未計測であり、最初の代表計測とprofileで確かめる。

計画前の読み取り専用照合では、各局面の元組番号0・145・290を選ぶ21組について、元seed値と先後割当の偶奇が全21組で一致することを確認した。対応する42局は同条件比較の部分benchmarkに使える。これは実際の対局実行・速度計測・達成判定ではない。

## 計測・採否の方針

- 反復用benchmarkは元seed一覧から各局面の組番号0・145・290を抜き出した42局とする。全7局面・両方式・先後交換・seed値を保ち、元の組番号の偶奇と先後割当が一致するように対応づける。これは根本処理の比較用で、全量達成判定には使わない。
- 各試行は4 workerで、別の未使用出力先に全局を実計算する。試行ログには観測した遅い処理、単一仮説、期待効果、維持する振る舞い、検証条件、変更・測定・採否を残す。
- profileは原因調査だけに使い、その計時を性能値にしない。代表benchmarkの壁時計時間はprofileなしで測る。
- 42局実行の外部壁時計とsummaryの一手計時合計を併記し、`一手計時合計 / 壁時計` をworkerごとの処理時間がどの程度重なったかを見る粗い稼働比として使う。これはOS CPU使用率ではない。壁時計との差が大きい場合はworker負荷の偏り・親側の投入/保存待ちを候補に加え、必要に応じて親CLIだけのcProfileも別出力で取る。
- 各改善候補は同じ42局の元結果と指し手列・終局理由・勝者を照合する。テスト、代表変異、全体テスト、独立レビューで重大な正しさの欠陥があれば採用しない。
- 正しさを満たした最速状態を作業ブランチ上で記録し、効果のない試行は理由とともに残す。新依存・大規模な構成変更が必要と判明した場合は、代替案と根拠を示し、別途承認を得るまで実装しない。
- 最終計測は別の未使用出力先で元seed一覧を全件使い、再開なしで新規4,074局を実行する。CLI起動から終了までの壁時計を測り、summaryの全局完了・故障等ゼロ・resumeでない状態も照合する。保存済み4,074局の各指し手列・終局理由・勝者とも照合する。

## 試行記録

| 日時 | 仮説・変更 | 代表/全量 | 壁時計 | 結果一致 | 採否 |
| --- | --- | ---: | ---: | --- | --- |
| 2026-11-03 12:20 JST・実験B0 | 旧summaryは各方式の候補選択に計269,838秒を記録（wall timeではない）。42局baselineで元seed再現と初回wall timeを得る | seed/position/side scheduleから作ったfresh 42局runは元の各棋譜と同じになり、wall測定はCLI全実行を含む | 変更なし。policy・合法手・終局・rng・保存挙動を維持し、42局を省略なく計算 | 42/42局完了、summary経過729.772秒、外部wall 730.49秒。手計時合計2,749.891秒/wall=3.764（粗いworker重なり指標）。元confirmation選択42局との手順・終局理由・勝者一致、全42棋譜の合法再生、error/interruption0。42局は一局当たり109.7手で、全量平均130.3手より短い。小標本から全量wallを宣言しない | baseline確立、変更なし |
| 2026-11-03 12:34 JST・実験B1 | B0ではpolicyごとに2,300手/2,306手、平均473.694ms/720.032ms。ソースには`is_square_attacked`の81マス走査と、候補評価時の複数回の利き照会があるが、寄与は未測定 | 14局cProfileが累積時間・呼出回数で支配操作を識別し、profile対象14局もB0棋譜と完全一致する | コード・評価式・合法手・終局・seed・順序は変更せず、profile計時は性能値へ使わない | 2026-11-03完了。1位置2局ずつ新規に`run_game`、14局・1,549手をprofile。14/14棋譜・終局理由・勝者一致。`is_square_attacked`: 10,308,672回/累積1,385.185秒、`_move_candidates_for_piece`: 156,972,383回/1,106.065秒、`is_piece_attacking_square`: 53,929,209回/441.450秒。`Square.__post_init__`: 1,472,191,861回/累積635.166秒、`Board.piece_at`: 1,905,996,369回/277.503秒。pstats `/private/tmp/comparison-cli-performance-14-2026-11-03.pstats`。累積時間は入れ子で重なる診断値であり、実性能値にしない | 原因を特定。最大の評価側費用は繰り返す利き判定と盤面走査 |
| 2026-11-03 13:16 JST・実験B2（初回、計測交絡あり） | B1で`is_square_attacked`が10,308,672回・累積1,385.185秒、各呼出しで81マスを走査。profile全体でSquare生成後検証が1,472,191,861回・累積635.166秒、`Board.piece_at`が1,905,996,369回 | `movegen.py`の攻撃照会・玉探索の盤面全走査で不変なSquareを都度生成せず、同じファイル優先順の事前生成タプルを再利用すれば、生成・検証・参照の負担が減る | 同じ81マス順、攻撃元候補、攻撃結果、合法手・指し手順・同点抽選・乱数消費・終局・棋譜・保存内容を維持。キャッシュは不変Square値のみで、盤面や履歴を共有しない | 新規出力`comparison-cli-performance-42-square-cache-2026-11-03`へ同じ42局・4 worker・512手・seed抜粋をprofileなしで実行。`/usr/bin/time -p` wall 458.47秒、summary 457.945秒、42/42局・21/21組完了、全件checkmate、error等0、`elapsed_lower_bound=false`。42局すべて元確認比較の対応棋譜と手順/終局理由/勝者が一致、合法再生42。手計時合計1,718.103秒、wallとの比3.747。B0から37.24%短縮、wall speedup 1.593倍。ただしレビューで`_find_king_square`の`Piece(KING, side)`生成もループ外へ移していたと判明し、Square再利用単独の効果に帰属できない。 | 合わせ技候補として検証済み最速状態に保持するが、B2単独仮説の完了・効果量としては扱わない。性能の全量推定には使わない |
| 2026-11-03 13:34 JST・B2分離再計測（変更前ticket） | 独立レビューで、B2コードに玉用`Piece`生成頻度を最大81回から1回へ変える別変更が混ざり、458.47秒に効果が混在していた。また`is_in_check`の再生成回帰テストは攻撃元が早期returnするため81未満の生成数でも通る可能性があると指摘された | `_find_king_square`内の`Piece`生成頻度を従来どおりに戻し、Squareキャッシュだけで同じ42局を再計測すればB2の効果を分離できる。王手scan testで攻撃元を最後の走査マスに置き、旧81回scanへの変異が確実に検出されるか確かめる | Squareタプルと走査順、従来の玉`Piece`生成頻度、利き・王手結果、棋譜・終局・乱数・保存を維持。ゲーム条件とseedはB0/B2同一 | 完了済み42局の出力は保持し、新規出力へ元seed抜粋・4 worker・profileなしで実計算。全42棋譜を旧比較と照合し、Ruff・関連209件・独立レビューを確認。採否は正しさと同条件wallで判断し、42局のみで30分達成は判定しない | 記録を追記済み。レビュー完了後にテスト補強・Piece生成位置の復元から開始 |
| 2026-11-03 13:45 JST・実験B2a（変更前ticket） | 差分確認で`_find_king_square`が各呼出しに最大81個の`Piece(KING, side)`比較値を生成する構造を確認。B1 cProfileにはPiece生成費用を独立に示す明瞭な項目がなく、実効果は不明 | 同じ不変Piece比較値をboard scan前に1回だけ生成して再利用しても玉検索の結果・返却順を保ち、割当を減らせる | 走査順・玉位置・局面・利き・候補順・乱数・棋譜・終局・保存を維持。変更はsentinel生成位置だけ | 既存movegen/U/V関連test、Ruff、同じ42局・4 worker・seed・512手・profileなし・別出力の全実測。全42棋譜を照合。5%未満/悪化なら棄却、10%以上短縮なら別変更として採用、5〜10%は効果を断定せずB3を優先。初回混在458.47秒は交絡と環境差を分けられず採否根拠にしない | 新規`comparison-cli-performance-42-king-value-hoist-2026-11-03`でwall492.66秒、summary492.132秒、42/42局・21組完了、error等0、全42棋譜一致・合法再生。Square-only 500.30秒比1.53%短縮で事前5%未満基準のため棄却し、sourceはSquare-onlyへ戻した |
| 2026-11-03 13:28 JST・実験B3開始前 | B1の`_move_candidates_for_piece`は156,972,383回/累積1,106.065秒、`is_piece_attacking_square`は53,929,209回/441.450秒。B2分離計測はSquare走査再利用のみで42局wall500.30秒、B0から31.51%短縮。初回の混在458.47秒はB2の基準値に使わない。候補一覧を作って真偽だけを調べる処理は残る。コード上`_move_candidates_for_piece`は呼出しごとに14項目dictを構築する | 既存候補一覧をmaterializeせず、駒種の幾何・遮蔽物から「このsourceからtargetへ利くか」だけを直接判定すれば、U/V・王手の繰返し候補生成が大幅に減る | 既存候補生成の集合と同じ幾何学的利き、source==target=false、同筋/斜線の遮蔽、先後方向、成駒、玉、同側占有target、ピン駒を維持。候補列挙順・乱数・合法手・局面・終局・保存結果は変えない。新しい盤面/履歴キャッシュは導入しない | `is_piece_attacking_square`を直接target判定へ変更し、`is_square_attacked`・`is_in_check`もこの同じ判定を使う。全14駒種×先後×81targetを既存候補生成の独立参照と差分照合し、中央/四隅・全面占有/遮蔽・空/敵味方占有target・ピン・盤面不変を含める。3つの利き照会が候補list生成を呼ばないassertion、`tests/test_piece_attack.py`の内部依存例外testを新helperの例外伝播testへ更新、単独testと既存movegen/U/V群、代表変異、Ruff、全体test後、同じ42局・4 workerのfresh runで全棋譜一致とwallを測る。15%以上短縮なら採用、5%以内/悪化は棄却、5〜15%はB2無変更baselineを新規出力で一度再測定してノイズ判定。B2分離sampleの9.205 moves/secに対し、元全量の実成功手数で30分以内に必要な速度は294.841 moves/sec、約32.03倍の追加改善が必要という粗い目安。B2分離版を全量へ線形換算した約13.15h、手数差を調整した約15.62hも推定であり、全量性能値にしない | 実験票を事前記録し、本人が14:04 JSTに`tests/test_piece_attack.py`の内部依存例外test1件の置換を承認。`tests/test_movegen.py`へ差分・候補生成回避testを追加。14種×先後×全targetの中央/四隅/全面占有差分testは候補参照と一致。候補list呼出しassertionは現コードで3回検出し意図どおりRed。製品コードは未変更 |
| 2026-11-03 14:08 JST・B3実装中間検証 | B3票の根拠どおり、真偽だけが必要な利き照会から候補生成を外す実装を反映。幾何判定は全駒種・先後・複数source・全81targetで既存候補集合と一致し、盤面不変も確認 | 中間マスの占有条件を反転する変異は遮蔽testで102件失敗。先後方向を反転する変異は幾何差分testで90件失敗。両変異は除去済み | 候補list回避、盤面無変更、target占有とピン、source==target、合法手生成順・rng・局面・終局は維持。例外伝播testは新helperへ更新する | 8関連moduleを実行し234件中233件成功、1件失敗。失敗は`tests/test_square_attacks.py`の1件で、旧`_move_candidates_for_piece`呼出しに結合した例外伝播testだった。2026-11-03 14:10 JSTに本人承認を得て同testのmock先だけを`_piece_attacks_target`へ更新した。承認済みの`tests/test_piece_attack.py`同様、他の変更は含めない。更新後に関連群・全体testを再実行する |

| 2026-11-03 14:11 JST・B3関連再実行 | 14:10に承認された`tests/test_square_attacks.py`の旧候補mock1件を直接helper例外testへ置換し、B3の承認範囲へ反映 | 同じ8関連moduleの234 testを再実行し、全駒種幾何・評価・例外伝播契約を確認 | Ruff format（対象ファイル）・Ruff check all・diff checkも完了 | 234件すべて成功、Ruff `All checks passed!`。fresh42計測・全体test・独立レビューは未実施 |
| 2026-11-03 14:16 JST・B3 2時間点検 | 実装仮説は候補一覧を作らない直接幾何判定。独立レビューはCritical/Important/Minorなしで、合法候補・順序・乱数・終局制御へ直接変更がないことを確認 | 選択した計算経路を候補集合の差分・候補関数非呼出し・完全test群・fresh42棋譜で確認する。性能改善率は測定後に判定 | 関連234 test、比較pipeline/result/resume/analyze60 test、全1080 test/92 moduleが成功。全体23.489秒。Ruff check、diff checkも成功 | B3 fresh42実行中（`comparison-cli-performance-42-direct-target-2026-11-03`、profileなし・4 worker）。wall・棋譜一致は完了後に記録。レビュー側は検証を再実行せず差分を確認 |
| 2026-11-03 14:17 JST・実験B3測定 | 14駒種の幾何を直接判定して、boolean利き照会の14項目dict・候補list生成と味方target用盤copyをなくす | Square-onlyに対し15%以上短縮、42局全件が元比較と一致し盤面・合法再生が保たれれば採用。5%以内は棄却、5〜15%はノイズ扱い | 4 worker、同じ21組/42局・元seed抜粋・位置/方式・先後・512手、profileなし、別新規出力で実計算。CLI起動〜終了wall171.41秒、summary170.949秒、42/42完了、elapsed_lower_bound=false、21/21組、checkmate42、未開始/進行中/故障/中断0。選択42局の手順・終局理由・勝者を全件照合、合法棋譜再生42/42 | Square-only 500.30秒より65.7%短縮（2.92倍）、B0 730.49秒より76.5%短縮（4.26倍）。実成功手4,606手/171.41秒=26.87手/秒。既存全量の実成功手530,714手から計算した目標速度は294.84手/秒で約10.97倍追加が必要というrough proxy。42局値から全量達成は推定しない。独立B3レビューはCritical/Important/Minorなし。B3を性能候補として採用し、次は更新後profileで残りのhot pathを確認する |
| 2026-11-03 14:18 JST・B3後診断profile票 | fresh42 B3は171.41秒まで短縮したが、26.87手/秒は目標proxy294.84手/秒の約1/10.97。旧B1 profileでは`_move_candidates_for_piece`・board scan・`Board.piece_at`が頻出したが、B3後の寄与は未測定 | B3後に同じ14局をメモリ内でcProfileし、候補生成負担が減った後に残る最大費用と回数を特定する。新しい速度変更はしない | B0の同一14棋譜に対して全手・理由・勝者を維持し、profileは性能値にしない。seed/position/policy/先後/合法手/RNG/終局は固定 | `/private/tmp/comparison-cli-performance-B3-14-2026-11-03.pstats`へprofileを保存。成功基準は14/14棋譜完全一致とpstats出力。累積時間は重複を明記し、変更hypothesisは上位caller/call count根拠で別途票を立てる |
| 2026-11-03 14:28 JST・B3後診断profile結果 | B3実装後の14局をcProfileして呼出しと時間順位を採取 | B0と同じ14局全ての結果が一致すれば診断結果を次ticketの根拠に使う | 14/14局・1,549手がB0の手順/理由/勝者/winner policyと一致。profile総計37億530万call/478.355 self seconds。これはwall速度値ではない | `_move_candidates_for_piece` 843,560回/累積8.052秒（B1の156,972,383回から約186倍減）。一方`is_square_attacked`は同じ10,308,672回/188.423秒、`Board.piece_at`は1,048,802,302回/138.655秒、`_piece_attacks_target`は159,822,813回/79.569秒、`Square.__post_init__`141,596,905回/64.289秒、`_find_king_square`1,762,509回/48.439秒。累積値は重複する診断値。pstats `/private/tmp/comparison-cli-performance-B3-14-2026-11-03.pstats` |
| 2026-11-03 14:29 JST・実験B4事前票 | B3は候補生成を大きく除いたが、10,308,672回の`is_square_attacked`が各81マス走査を継続し、関連する`piece_at`読込が10億回超。直接source-target helperは159m回呼ばれている | targetからの8方向rayで最初に見つかった駒と、8つの桂馬source候補だけを調べれば、ray上の遮蔽前にある攻撃候補だけを残しつつ全81マスscanを避けられる。rayの最初の駒が非攻撃駒なら、それより後ろのsliderは遮られ、攻撃にならない | 幾何的利き、ピンの扱い、target占有、source==target、8方向slider・香の向き・桂馬の飛越し、盤面無変更、bool結果を維持。合法手候補列挙・順序・乱数・評価・終局は変えない。`is_piece_attacking_square`は従来の単一source判定を維持 | 同じ`movegen.py`と承認済み`tests/test_movegen.py`内で変更。全駒種×先後×全target、複数の先頭blockerと奥のslider、桂source、敵味方占有、全board-wide queryを既存候補関数参照へ差分比較。ray stop・各方向を欠く代表変異でRed。関連234件＋比較60件、全体1080件、Ruff、独立レビュー後、B3同条件fresh42で15%以上短縮かつ42棋譜完全一致を採否基準。B3後の14局profileでは`is_square_attacked`に188.423累積秒、すべての`Board.piece_at`呼出しに138.655累積秒が記録されており（重複含む診断値）、この票の期待効果は無駄なsource scanを除くこと |
| 2026-11-03 14:30 JST・B4構造test Red | B4仮説を読取回数で検出するため、空盤中央targetの`is_square_attacked`呼出しに`piece_at`をpatchし、81未満の呼出しを要求 | target候補sourceへ絞る実装前は全盤を読むため、このtestは現在の`is_square_attacked`を失敗させる | 旧実装で予測どおり`piece_at.call_count == 81`となり「81 not less than 81」で失敗。B4の性能構造を検出するRedを確認。遮蔽fixtureは旧候補参照と現B3実装でpass | 結果はB4のtest根拠として保持し、製品コード未変更 |
| 2026-11-03 14:34 JST・B4実装とtest検出 | `is_square_attacked`・`is_in_check`をtarget起点8 ray最寄り駒+桂source候補へ変更。ray最寄りsourceの経路は既に空を確認済みのため、helperに明示的な前提flagを渡して二重path scanを避ける | すべての駒種・side・targetが旧候補参照と一致し、攻撃不能マスを全走査しない。ray stopと8方向の欠けを代表変異で検出する | 直接利き関連6 test Green。空盤中央queryで`piece_at`回数を40以下に制限（旧81回）。8方向を一つ外す変異で30失敗、ray stopを除く変異でSente/Gote各1件計2失敗。追加のray経路再読testは`True→False`変異で読取4回が7回となり失敗。変異は復元 | B4 fresh42・全体test・独立review後に採否を判断する |
| 2026-11-03 14:43 JST・B4検証・fresh42 | B4実装でtarget起点ray/桂sourceに探索を絞り、ray確認済み経路の再読も省く | B3と同じseed一覧・局面・方式・先後・512手・4 workerのfresh42で15%以上短縮し、全局結果も一致すれば採用 | `/usr/bin/time -p` wall134.95秒、summary134.558秒、42/42局・21/21組完了、checkmate42、error/interrupted/unstarted/in-flight 0、`elapsed_lower_bound=false`。条件はgit/source provenance以外一致。B3出力と全42局の初期局面・指し手列・終局理由・勝者/方式一致、合法再生42/42。成功手4,606 | B3の171.41秒より21.3%短縮（1.27倍）、Square-only B2の500.30秒より73.0%短縮、B0の730.49秒より81.5%短縮。34.13手/秒は部分sample値。全量既知成功手530,714からの必要速度294.84手/秒に対して約8.64倍不足し、全量所要時間の推定値にはしない。B4は検証済み最速候補として保持。4,074局は未実施 |
| 2026-11-03 14:44 JST・B4回帰検証と独立レビュー | B4実装後、関連test、pipeline契約、全体unit suiteを再確認し独立レビューを受ける | B3で変わっていないCLI/保存/再開/analysisと、全repo契約を維持し、Minor指摘も検出範囲へ反映する | comparison pipeline/result/resume/analyze60件成功。全体1083件/92 module/22.213秒成功。Ruff format・check、`git diff --check`成功。独立reviewはCritical/Importantなし。Minorは全体件数の記録が古い点で、以下の実行記録を1083件へ更新し解消 | B4のコード・test範囲をレビュー済み。fresh42結果と記録の採否反映後、B4をcommitする |
| 2026-11-03 14:45 JST・B4後診断profile票 | B4 fresh42は134.95秒、成功手4,606/34.13手/秒で、全量目標に必要な294.84手/秒との差は約8.64倍。B3 profileでは`is_square_attacked`10,308,672回/188.423累積秒と全盤source scanが大きかったが、B4後の寄与は未測定 | B4によるsource scan削減後、profile上位費用が攻撃照会以外へ移ったかをB0と同じ7位置×先後の14局cProfileで確認する | B0/B3診断profileの14棋譜に対し指し手・reason・winner side/policyを一致させる。seed/policy/position/side scheduleは固定。cProfile時間を速度指標にしない。製品コード・候補順・RNG・終局・保存は変更しない | `/private/tmp/comparison-cli-performance-B4-14-2026-11-03.pstats`へ保存。14/14完全一致とpstats出力を成功基準とし、呼出数・self/cumulativeで上位処理を選び、次の単一実験票の根拠にする |

## 進捗

- 基準との差: 正確な基準壁時計は未確定。保存済みsummaryの下限は目標より18時間41分以上長い。
- 最速実測候補: B4 target-ray版fresh42 wall134.95秒、42/42棋譜完全一致・合法再生42/42、独立reviewでCritical/Importantなし。目標とは別の部分標本であり、全量達成値ではない。過去候補はB3 171.41秒、B2 Square-only 500.30秒、B0 730.49秒。B2初回458.47秒は別変更が混ざるため単独効果に使わない。
- 進行中の作業（2026-11-03 14:44 JST、期限まで約5時間32分）: 検証済み最良実測はB4 fresh42の134.95秒。B3から21.3%短縮。条件はgit/source provenanceを除き一致し、同一42局のseed/先後/SFEN/全指し手/終局理由/勝者が一致、合法再生42/42。全体1083 test/92 module/22.213秒、comparison pipeline60 test、Ruff・diff check成功。ray経路read-count testを追加し、前提flagをfalseへ変えると期待4回に対して7回となる代表変異失敗を確認。独立レビューはCritical/Importantなし、Minorの古いtest件数記録を本更新で直した。1,083件で全体testは22.213秒。partial42の34.13手/秒と全量既知手数から必要な294.84手/秒には約8.64倍差が残る。B4をコード・検証済み最速候補として記録し、B4後14局profileで次の大きい処理を選ぶ。4,074 run未開始。期限20:16:27 JST。
- 失敗した試行・実行上の注意: B2のscan再利用test初稿は攻撃元が走査順の途中にあり、旧実装でも早期returnして生成回数閾値を通った。最後の走査マスから攻撃する歩へ置き換えた後、旧実装で2件の意図したassertion failureを確認。B2完成実装では対象3test成功。今回の関連testの直接module指定では`tests/`内補助moduleのimport pathがなく5件ImportErrorとなった。テスト失敗ではなく起動方法の誤りと判別し、指定runnerの全体実行をやり直して1083件成功。
- 次に試すこと: 14:45に記録したB4後diagnostic ticketどおり同じ14局をメモリ内cProfileし、ray最適化後の`is_square_attacked`、合法手候補生成、盤走査、Square/Move割当の寄与を呼出数とself/cumulativeで順位付けする。profileを性能値にせず、全14局の棋譜/理由/勝者をB3診断sampleと照合する。測定後に結果に基づく次の単一実験票を記録する。
- 期限点検: 開始2時間後・4時間後に、検証済み最良実測、30分目標との差、残る主要処理時間を照合する。現在の律速部分から残り全体を30分以内にするには何倍短縮が要るか再計算し、小幅改善の積み上げで届かないなら次の仮説を見直す（承認が要る範囲変更は止めて提示する）。最後の1時間は最良候補の検証・独立レビュー・記録を優先する。
- 期限で未達の場合: 期限到達時点の最速正しさ確認済み状態、実測、差、未完了作業、次の具体的な一手を記録して停止する。30分未満の新規全4,074局実測が確認できない限り達成にしない。
