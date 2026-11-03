# 比較CLI性能改善の学習・実験記録

## 目標と適用範囲

比較CLIの確認比較と同条件の新規4,074局を、同一PC・4 workerで30分以内に完了する。目標条件と作業期限はルートの[GOAL.md](../../GOAL.md)、設計は[設計案](../plans/2026-11-03-comparison-cli-performance-design.md)、手順は[実装計画](../plans/2026-11-03-comparison-cli-performance-implementation-plan.md)を参照する。

計画承認後8時間が今回の作業期限。本人の回答待ちとアプリ停止で作業不能な時間だけを除外する。途中の性能改善や小標本から30分達成とは判定しない。

## 計画承認と期限開始

- 本人は[設計](../plans/2026-11-03-comparison-cli-performance-design.md)と[実装計画](../plans/2026-11-03-comparison-cli-performance-implementation-plan.md)を2026-11-03に明示承認した。
- 期限開始は2026-11-03 12:16:27 JST、終了予定は20:16:27 JST。計画提示12:08:38から承認受領12:16:27までの7分49秒は除外する。
- 承認後の状態再確認でbranch `codex/comparison-cli-performance`、HEAD `aa70d1d`、Python 3.15.2、Ruff 0.16.10、hooksPath `.githooks` を確認した。`ps` はOS権限で拒否されたためActivity MonitorのPython絞り込みとプロセスインスペクタを使い、確認した2件はいずれも比較CLIではないことを確かめた。
- 既存の未追跡比較成果物・保全物は保持する。コード・テスト・benchmarkは未着手。
- 元confirmationのconditions、summary、seed-list、局面ファイルを独立照合した。7局面×291組=2,037組・4,074局、schedule 4,074件、seed-list 2,037件、最大512手、4 worker、policy、positions SHAが一致し、局JSON 4,074件と未開始/故障/中断0を確認した。`elapsed_lower_bound=true` のため既存summaryの時間は総wall timeの基準にしない。
- 実験B0の42局fresh baselineは`/usr/bin/time -p`のwall 730.49秒、summary elapsed 729.772秒。全42局/21組完了、error・interruption・未開始・進行中0。外部wallと一手計時合計2,749.891秒の比は3.764で、worker間処理時間の重なりを見る粗い値である（OS CPU使用率ではない）。
- baseline42局すべてを元confirmationの位置・元組番号0/145/290・局順・方式別seedから突合し、初期SFEN、指し手列、終局理由、勝者（方式含む）が一致した。新runは`load_completed_comparison`で42局全てを合法再生し、summaryと条件も検証した。
- この部分集合は合計4,606成功手、平均109.7手/局で、元confirmationの530,714手/4,074局（130.3手/局）より短い。従って730.49秒を全量速度の推定値・達成判定へ外挿しない。profileは後続のB1で14局のみ収集し、時間値には使わない。

## 開始時の状態（2026-11-03、計画承認前）

- checkout: `/Users/oki2a24/kaname-shogi`、branch `codex/comparison-cli-performance`、開始HEAD `aa70d1deaec4c666839fb951aaba5a83a9f59b01`。branch作成前の `main` と `origin/main` は同じHEAD、追跡ファイル差分なし。
- 開始時の未追跡比較・保全物は保持し、編集・削除・移動・stageしていない。
- READMEが求めるPython 3.14以上の範囲で `.venv/bin/python` は3.15.2。固定Ruff 0.16.10、local hooksPath `.githooks`。
- 対象比較processは通常・拡張読み取り専用の確認で検出されなかった。
- 2026-11-02のsummaryは4,074/4,074局、2,037組完了、故障・中断など0。`elapsed_lower_bound=true`、`elapsed_ns=69063743406167`。再開前の停止時間が失われているため、下限約19時間11分であって総実時間の確定値ではない。
- `conditions.json` は7局面各291組、512手上限、baseline `material-piece-threat-v1`、candidate `material-piece-threat-value-v1`、4 worker、positions sha256 `256437ea5e0465f4e1ed777deecf091ef1745bbdbab6b70e805e88685b94ad61` を記録。元seed一覧は `data/comparison/runs/undefended-piece-value-comparison-confirmation-2026-11-02-seeds.json`。
- 一手計時は旧方式264,964手・計111,051.851秒・平均419.121ms、新方式265,750手・計158,786.204秒・平均597.502ms。合計時間はworker間で重なり、壁時計と同じではない。4 worker理想稼働の仮定で全量30分には約37.48倍の操作時間短縮が要るという難度の目安である。
- `run_game` の一手計時は合法手生成開始から選択終了まで。従って各policy計時だけでは棋譜更新・JSON保存・worker待機を説明しない。
- ソース調査では一手候補ごとに複製適用・詰み確認・評価を行う。M/U/Vは別々に呼ばれ、U/Vの内部で利き照会が繰り返される。これはprofile前の仮説である。
- 28局pilot 426.373秒は前回記録。今回の性能基準としては使わない。
- 計画用の読み取り専用seed照合では、7局面それぞれの元組番号0・145・290を選んだ21組すべてで、baseline/candidate seed値と先後割当の偶奇が保存済みconditionsと一致した（21/21）。対応する部分集合は42局。これはseed抽出方法の検算であり、対局実行・性能計測ではない。

計画は本人が2026-11-03 12:16:27 JSTに明示承認し、8時間期限が進行中。承認前は製品コード・テスト・benchmark出力を変更せず、profile/性能計測も開始していない。

## 実験記録

| # | 観測根拠/遅い処理 | 一つの仮説 | 期待効果・不変契約 | 測定・テスト | 結果/採否 |
| --- | --- | --- | --- | --- | --- |
| B1・2026-11-03 12:34 JST | 事前観測: B0で旧2,300手/候補2,306手、平均473.694/720.032ms。`is_square_attacked`が81マス走査する静的根拠はあったが費用寄与は未測定 | 元seedの各局面1組14局をcProfileし、最大費用と呼出回数を特定する | コード・評価・合法手・終局・seed・順序・rngを変更しない。計時値は速度値へ使わない | 14局の新規`run_game`をメモリ上で直列profileし、B0と指し手列/終局理由/勝者を全件照合 | 14/14局・1,549手一致。15,794,107,404 calls、cProfile総計1,988.146秒。上位は`is_square_attacked` 10,308,672回/累積1,385.185秒、`_move_candidates_for_piece` 156,972,383回/1,106.065秒、`evaluate_material_piece_threat_value` 192,688回/1,280.350秒、U価値balance 916.530秒、V balance 535.030秒、`is_piece_attacking_square` 53,929,209回/441.450秒。Square `__post_init__` 1,472,191,861回/累積635.166秒、`Board.piece_at` 1,905,996,369回/277.503秒。pstats: `/private/tmp/comparison-cli-performance-14-2026-11-03.pstats` | 原因特定に成功。計測は診断のみ。次はboard-wide scanが同じ81マスを都度`Square`生成する負担を検証 |
| B2・2026-11-03 13:16 JST | B1で`is_square_attacked`が10,308,672回/累積1,385.185秒。盤全81マスの反復、Square初期化1,472,191,861回/635.166秒を確認 | board-wide read scanで不変のSquareを事前生成したファイル優先タプルから再利用すると、毎セルの生成・座標検証負担が減る | 攻撃元の列挙順、攻撃結果、候補順、rng消費、合法手、終局、盤面不変と一手計時境界を維持 | `is_square_attacked`・`is_in_check`・`_find_king_square`だけを対象に変更。新test 3件と既存movegen/U/V群209件が通過。Ruff format/lint、`git diff --check`成功。B0と同じfresh 42局を4 workerで新出力へ実行し、wall458.47秒（summary457.945秒）、42/42局完了・checkmate42・error等0・`elapsed_lower_bound=false`。元run全42局と手順/終局理由/勝者が一致し、`load_completed_comparison`で42局合法再生。手計時合計1,718.103秒、wall比3.747。B0からwallを37.24%短縮。tmpコピーで走査Square再生成へ戻す変異は「82 not less than81」、キャッシュ81マスから末尾を除く変異は「80 !=81」の意図したassertion failure。初回mutation harnessは一度package rootを誤りImportErrorとなったため検出結果に含めず、package配置を直して上記2件を再実行 | 初回結果はSquare cacheとPiece生成ホイストの合わせ技候補として保持。単一仮説B2の採否・効果量には使わず、42局の部分benchmarkであり全量達成には使わない |
| B2分離再測定・2026-11-03 13:36 JST | B2独立レビューのImportant/Minorを修正。Piece生成頻度を元に戻したSquare cacheのみを比較 | B2変更前ticketのとおり、Square cacheだけでboard scanのSquare生成を除ける | seed/side/policy/合法手/順序/rng/終局・保存、42局・4 workerを維持 | 新規`comparison-cli-performance-42-square-only-2026-11-03`へfresh42局。外部wall500.30秒、summary499.759秒、42/42局・21組完了、checkmate42、error等0、`elapsed_lower_bound=false`。元42局全件と手順/終局理由/勝者一致、合法再生42。旧`is_in_check` 81-square loop変異で補強testが82生成を検出して失敗。正実装は関連216 test、Ruff、diff check成功。初回の関連test起動は`PYTHONPATH=tests`不足で補助module importに失敗し、正しい検索pathで再実行した。照合script初回も`PYTHONPATH=.`不足でpackage importに失敗し、再実行42/42成功 | B0の730.49秒より31.51%短い。Square cache単独の測定値は500.30秒。前回混在458.47秒より遅いが、約9%の差は両policyのmove timingにほぼ同率で表れており、環境変動とPiece-hoist効果をこの比較だけで分離できない。混在値をB2の採否根拠にしない |
| B2a・2026-11-03 13:45 JST・変更前 | `_find_king_square`の各探索で最大81個の`Piece(KING, side)`値を作る構造をコードで確認。B1 cProfileはPiece生成の費用を個別表示せず、効果は未測定 | board scan前に不変なPiece比較値を一個生成してloop内で再利用しても同じ玉マスを返し、割当を減らせる | 走査順、玉位置、局面・利き・候補順・rng・棋譜・終局・保存を維持。変更はsentinel生成位置だけ | 関連movegen/U/V test、Ruff、同じ42局・4 worker・seed・512手・profileなし・新出力。全棋譜照合。5%未満/悪化は棄却、10%以上短縮は単独変更として採用、5〜10%では効果断定せずB3へ進む。混在B2初回458.47秒は採否基準にしない | fresh42局は外部wall492.66秒、summary492.132秒、42/42局・21組完了、error等0。Square-only 500.30秒より1.53%短いが、事前基準5%未満のため効果を棄却し、sourceはSquare-only状態へ戻した。元確認比較との手順/終局理由/勝者一致42/42、合法再生42。照合script初回は`PYTHONPATH=.`不足でImportError、環境を補って再実行し42/42一致 |
| B3・2026-11-03 13:28 JST・変更前 | B1で`_move_candidates_for_piece`は156,972,383回/累積1,106.065秒、`is_piece_attacking_square`は53,929,209回/441.450秒。これらのAPIは真偽だけを調べるためにも全移動候補リストを生成している | source-targetの駒種幾何と途中遮蔽だけを直接判定すれば、同じ一手選択結果を保ちながら候補リストの反復生成を避けられる | 全14駒種・先後・成駒・長距離遮蔽・target占有・同一マス・ピンの幾何学的利き、局面無変更を維持する。合法手候補列挙や順序、rng、終局規則は変更しない | 既存候補生成を参照実装として、全source×targetを開局・全駒種配置・遮蔽局面で差分検査する。新しい個別target APIと`is_square_attacked`を対象に単独test、既存movegen/U/V群、代表変異、全体tests。profileなしfresh42をSquare cache単独の500.30秒と比較し、42棋譜も全件照合。15%以上改善・完全一致で保持、5%以内/悪化は棄却、5〜15%はSquare cache単独の500.30秒baselineとのノイズ差を記録 | 実験票を記録。test/code変更は未着手 |

## 検出力・範囲の記録

### B2の検出力・範囲（実験開始前）

- 対象契約: 攻撃照会・王手走査が全マスを同じファイル優先順で読む。キャッシュは不変な81個のSquare値だけで、盤面データを保持・共有しない。
- 検出したい誤り: 筋段順の取り違え・マス抜け/重複、走査中の81回のSquare再生成が残る、既存攻撃照会の真偽や先後を変える、元盤面を変更する。
- 独立期待値/代表ケース: マス列は`(1,1)…(1,9),(2,1)…(9,9)`で手計算できる。孤立した後手歩が一歩前の先手駒を攻撃する局面では真。既存movegenテストの全駒両側、長距離遮蔽、王、ピン、所有側占有マス、非変更ケースで意味論を補う。
- 単体範囲: 新しいSquareキャッシュと単純歩局面で構造上の生成削減を検出するtest。意味論は`test_movegen.py`の既存個別ケースと明示期待値で検出する。
- 全体範囲: 全ユニットテスト、Ruff、差分、42局の新規実行と旧42局の指し手列・終局理由・勝者全件照合を行う。
- 代表変異: キャッシュ順を入れ替える、1マスを除く、攻撃照会の正否/sideを反転、局面を変更する各変異で該当testのassertion failureを確認する。
- 未検証事項: 選択したscanのほかの`Square`生成、評価側の`is_piece_attacking_square`大量呼出し、保存・再開・analysis経路が変わらないことは全体/関連テストと42局比較を通すまで未検証。性能効果は42局wallまで未検証で、30分目標の達成は判定しない。

### B2レビュー指摘と分離再計測ticket（2026-11-03 13:34 JST）

- 独立レビューの結論: Criticalなし。Importantは`_find_king_square`内の`Piece(KING, side)`生成をloop外へ移す別最適化が混在し、B2のSquare再利用だけへ効果を帰属できない点。Minorは`is_in_check`の走査再生成testが途中returnで回帰を見逃しうる点。レビューはコード差分・計画・実験票を確認したが、コード・209 tests・Ruff・42局結果を再実行していない。
- Square cache単独の500.30秒と37.24%短縮は、合わせ技候補の結果として保持する。B2単独の性能効果としては扱わない。
- 次の実験仮説: 玉検索での`Piece`生成頻度を従来どおりへ戻したSquareキャッシュ単独状態を、B0/B2と同じ42局・seed・4 worker・profileなし・新出力で測る。旧出力は保持する。
- 不変契約: 盤走査順・攻撃結果・候補列挙・乱数消費・合法手・局面・終局・棋譜・保存形式、seedと計測境界を維持する。
- test補強: `is_in_check`用のテストでは、最後の走査マス(9,9)に置いた先手歩が(9,8)の後手玉を攻撃する。王探索をモックして攻撃元scanのみ計測し、旧81マスSquare生成への変異を追加する。test単体・既存209件・Ruff・42局棋譜全件照合・再レビューで採否を判断する。testとコードの変更は実験開始後に行う。

### B3の検出力・範囲（実験開始前）

- 対象契約: 既存`_move_candidates_for_piece`が返す候補集合へのtarget所属判定と、source-target幾何判定が一致する。利きは合法性ではなく現在の幾何学的候補であり、ピンされた駒も含む。
- 検出したい誤り: 歩・桂・銀・金相当の前後向き/成駒形状の取り違え、飛/角/香の経路遮蔽、馬/竜の複合移動漏れ、味方targetを攻撃しない誤り、target占有を途中遮蔽と誤認、source==targetを真とする誤り、局面変更。
- 独立期待値/代表ケース: 正式候補生成関数を参照値として使い、全14駒種×先後の駒を一つずつ置いた盤面でsourceと81targetを総当たりする。別に全駒種が両側へある盤面、長距離遮蔽と桂の飛越し、味方target・敵target・target空、王・ピンの配置を加える。candidate functionと直接判定は別コード経路なので集合所属の差分を直接測れる。
- 単体範囲: 新しいtarget boolean操作と`is_square_attacked`の全target差分test、盤面スナップショット。
- 全体範囲: `test_movegen.py`、U/V評価群、全ユニット、Ruff、42局fresh、42棋譜一致。合法手生成自体は変更しないため、CLI条件・保存・再開・analysisの関連pipeline testも実行する。
- 代表変異: 歩の進行方向または飛の遮蔽物チェックを反転して、意図したassertion failureを確認する。
- 未検証事項: 不正なPiece/Board値の扱いと新手続きへの例外伝播、全量のwall目標、正しさと独立レビューが終わるまで未検証。

## レビュー・振り返り・次回への問い

- 独立ビルダーチェック: GPT-6 Luna・maxが設計案と実装計画を読み `nothing important left`。重要な未回答事項なし。これは計画文書レビューであり、コードレビューではない。
- コード独立レビュー（B2、GPT-6 Luna・max）: Criticalなし。Importantは`_find_king_square`内の`Piece(KING, side)`生成をloop外へ移す別最適化が混在し、B2のSquare再利用だけへ効果を帰属できない点。Minorは`is_in_check`の走査再生成testが早期returnで回帰を見逃しうる点。B2分離再測定とtest補強を実施した。結果はwall500.30秒、42/42棋譜一致・合法再生、関連216 test・Ruff成功。B2aの単独Piece生成ホイストはwall492.66秒でSquare-only比1.53%改善、5%未満基準で棄却しSquare-only状態へ復帰した。GPT-6 Luna・maxによるコード再レビューはCritical/Important/MinorなしでB2を採用可と判断。コード・test・関連216件・Ruff・wall・42局照合は再レビュー側では再実行せず、記録と差分で確認。B2 Square-only実装と検証記録はcommit `8b510a99`で保存。
- 学習者の振り返り: 未聴取。
- 次回への問い: 繰り返す盤走査を減らす変更は、正しさを保ったまま42局wallと一手計時をどれだけ変えるか。残り時間の主要部分へ何倍の改善が必要か。
