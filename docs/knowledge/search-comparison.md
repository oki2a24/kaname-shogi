# 指定深さ探索と反復深化の開発用比較

## 利用方法

この文書は通常対局の一手選択とは別に、同一局面の全幅読みとαβ枝刈りを比較する開発用コマンドの仕様を説明する。対局ではRandom・Material・TwoPlyMaterialに加え、全幅最大4手とαβ枝刈り最大4手を選択できる。比較コマンドの結果をそのまま対局中の選択や棋力の保証とは扱わない。

```sh
.venv/bin/python -m kaname_shogi.search.compare --sfen "8k/9/9/9/9/9/9/9/K8 b - 1"
```

同一局面・既存の合法手生成順・二／三／四手で各方式を独立実行する。評価は開始側固定の駒得と詰み優先。勝ち・通常・負けを先に比較し、同点は最初の最善手を選ぶ。出力にはUSIと日本語の手を併記する。

## 比較の契約

全幅側は根の各候補の確定値を保持する。αβ側は根の確定値と一手を返し、省略枝の境界値を確定値として公開しない。比較は根評価一致と最善候補所属で成功。同点の別手は許容。手なしは双方の手なし・評価一致を確認する。

訪問は共通探索本体へ入るたび一回。開始・途中・末端と再訪を含む。合法手生成や王手確認内部の仮局面は除外。訪問回数は実行時間や全作業量と同じではない。

終端確認は深さ打切りより先。詰みは勝敗、詰みでない手なしは駒得で終了する。手なし開始局面の選択はなし、訪問1。千日手などの履歴終局は扱わない。

| 終了コード | 意味 |
| --- | --- |
| 0 | 全深さで比較成功。ヘルプも0 |
| 1 | 比較不一致。内部例外も通常1だが診断で区別 |
| 2 | 引数・SFEN入力の誤り |
| 130 | Ctrl+C中断 |

結果は標準出力、診断は標準エラー。各方式の完了行を逐次表示し、中断した方式は未完了。内部故障を入力誤りへ変換しない。

## 反復深化の比較

```sh
.venv/bin/python -m kaname_shogi.search.compare_iterative --sfen "8k/9/9/9/9/9/9/9/K8 b - 1"
```

深さ1〜4を順に探索する。各深さで、反復結果を保持→同じ深さの全幅→元の順序の単独αβ→比較表示の順。正しさは全幅との評価一致・最善候補所属で確認し、同点の別手を許容する。不一致でも次の深さを続け、最後に1を返す。

前回最善手は開始局面の先頭へ移すだけで、他候補の相対順・子局面の順序は保つ。同じ開始局面で一手を選ぶ間の再利用であり、実際に指した後の再利用ではない。優先なしは従来順序。不在の優先手は根の調査後、子へ進む前にValueError（深さ0・手なしでも照合）。

各深さの完了時に、深さ・既存SearchResult・累計をfrozenのIterationResultとして新規作成する。以前の記録は変更せず、最新の参照だけを切り替える。Pythonのyieldで結果を一件ずつ渡し、次の要求で次の探索を行う。上限検査は呼出し時で、boolを除く1以上の整数。ジェネレーター内の状態を保存する仕組みはPythonの言語機能であり、他言語では深さ・前回手・累計を明示保持するIterator等へ置き換えられる。

| 玉だけ局面の深さ | 単独αβ訪問 | 反復今回訪問 | 反復累計 |
| --- | --- | --- | --- |
| 1 | 4 | 4 | 4 |
| 2 | 9 | 9 | 13 |
| 3 | 29 | 29 | 42 |
| 4 | 64 | 64 | 106 |

2026-10-17の実測。全幅の確認用探索・単独αβ・中断反復の訪問は反復累計に加算しない。訪問回数削減は合格条件ではなく、改善しない例も正常である。

手なしは深さ1の完了記録を比較して終了し、0は「実行した比較がすべて一致」の意味となる。中断は130で不一致より優先。反復途中なら直前の完了結果を残し、確認用探索の途中なら「反復深化は深さNまで完了／深さNの比較は未完了」と分ける。完了前なら完了結果なし。内部故障は入力誤りへ変換しない。

## 構成と限界

`search/minimax.py` と `search/alpha_beta.py` が方式入口、`core.py` が共通探索、`contracts.py` と `result.py` がデータ、`shogi.py` が将棋接続、`compare.py` が指定深さ比較の入出力。反復管理は `iterative_deepening.py`、その比較入口は `compare_iterative.py`、入力・整形・一致判定の共通処理は `comparison.py`。評価の正本は `evaluation.py`、既存 `movegen.material_balance` の入口も維持。複製適用の公開操作 `movegen.position_after_move` は既存適用へ委譲する。

これらの比較コマンドは時間制御、置換表、定跡、新評価項目、対局方式の選択を含まない。対局接続の実装では `game_search` が新二方式を共通反復探索へ渡す。通常CLIとUSIは既存の時計予算・停止制御を使うが、CLIは自身の時計を管理し返却後に時間切れを判定し、USIはGUIから各goの時計を受ける。合法手が多い局面の全幅四手探索は長時間かかり得て、実応答時間・期限内の完了は保証しない。局面例・数値木・回帰の成功は棋力向上や全入力の証明ではない。OSからのSIGINT配送の実プロセス試験は未実施で、中断の捕捉と表示は操作境界で確認。

根拠と履歴：[承認済み設計](../plans/2026-10-17-engine-search-comparison-design.md)、[実装計画](../plans/2026-10-17-engine-search-comparison-implementation-plan.md)、[実装・学習記録](../learning/engine-improvement-stage-design.md)。

反復深化の根拠：[承認済み設計](../plans/2026-10-17-iterative-deepening-design.md)、[実装計画](../plans/2026-10-17-iterative-deepening-implementation-plan.md)、[学習・実装記録](../learning/iterative-deepening-design.md)。


## 制御付き探索入口との区別

2026-10-18に探索部品として `iterative_deepening.search_controlled` と `alpha_beta.search_controlled` を追加した。比較コマンドは従来の停止なし入口を使い続ける。停止なし反復は遅延取得で完了記録を一件ずつ渡し、手なしでも深さ1の記録を一件渡す。制御付き反復は準備を含めて同期実行し、最終終了結果を一件返す。準備の手なしは完了記録なしで終了する。

反復・再帰・優先手順序・完了累計の本体を共有する。準備と中断反復は累計に含めず、中断時は最新完了記録または予備手を使う。詳細は[探索停止](search-stop.md)、[承認済み設計](../plans/2026-10-18-iterative-deepening-stop-time-control-design.md)、[実装・検証記録](../learning/iterative-deepening-stop-time-control-implementation.md)を参照。比較コマンドに時計オプションはない。通常対局への接続仕様と検証範囲は[四手探索の接続設計](../plans/2026-10-19-four-ply-search-game-integration-design.md)と[実装・学習記録](../learning/four-ply-search-game-integration-plan.md)を参照する。

## 対局方式の比較とC1分析

`python -m kaname_shogi.compare_games` は開発用の一手選択方式を指定局面群で比較する。現在の方式名は `random`、`material`、`material-rook-mobility`、`two-ply-material`、`full-width-4`、`alpha-beta-4`。`material-rook-mobility` はB1全体（駒得と未成飛車の移動先候補数の合成、および一手詰み優先）を比較CLIの選択経路へ接続する。通常CLI・USIの選択肢には加えていない。

### 乱数種一覧と実行

```sh
python3 -m kaname_shogi.prepare_comparison_seeds \
  --positions data/comparison/c1-rook-mobility-positions-v1.json \
  --pairs-per-position 1 --purpose pilot --output /path/new-seeds.json

python3 -m kaname_shogi.compare_games \
  --baseline material --candidate material-rook-mobility \
  --positions data/comparison/c1-rook-mobility-positions-v1.json \
  --pairs-per-position 1 --seed-list /path/new-seeds.json \
  --max-plies 256 --output-dir /path/new-run

python3 -m kaname_shogi.analyze_comparison \
  --input-dir /path/new-run --output /path/new-analysis.json
```

準備CLIは局面群全体を検証した後、OS乱数源から128ビット種をbaseline/candidate用に各組一つずつ抽出し、`pilot` または `confirmation` と局面ファイルのSHA-256を含むJSONへ保存する。同じ数値の種が偶然重なっても引き直さない。出力は新規パス限定。比較CLIは `--seed` と `--seed-list` のどちらか一方を要求する。`--workers` は1〜4、既定値1で、2〜4はspawnプロセス並列を使う。種一覧実験では局面JSONのバイト列・順序・ID・局面ごとの組数を一覧と照合してから対局する。逐次の種一覧条件は `kaname-shogi-comparison-conditions-v2`、複数worker条件はv3とし、`execution` に `executor=process-pool` とworker数を保存する。`--seed` 実験は逐次conditions v1、並列conditions v3を使うが、現在の分析CLIは種一覧を保存したv2/v3だけを受け付けるため、これらの `--seed` 結果は分析できない。

予定の各組は同じ開始盤面・駒配置で二局を行い、方式の先後だけ交換する。二局内は同じ方式別種を保つ。棋譜・summaryを含む出力先は新規パスで、同じ一覧の再実行は再現性の確認であり、独立した追加標本ではない。時間・環境情報を含む全出力のバイト一致は期待しない。準備・比較・分析CLIのヘルプが引数の正本である。

通常のworker数1のsummaryはv1、2〜4はv2で `in_flight_games` を含む。再開後は逐次・並列ともsummary v3となり、`elapsed_lower_bound=true` を保存する。並列の進捗summaryは回収前の `in_flight_games` を示し、全worker回収後のsummaryだけが0となる。分析CLIは、seed-list形式のconditions v2+summary v1/v3、conditions v3+summary v2/v3を受け付け、予定・局ファイル・conditions SHA・summary件数を再照合する。`--seed`によるconditions v1/v3は形式上worker数を記録していても、seed-list専用の分析CLIでは読めない。並列summaryの `in_flight_games` が0でない途中成果物は分析しない。分析JSON v2は `elapsed_lower_bound` を含み、旧summary v1/v2ではfalse、再開summary v3の下限時間ではtrueを記録する。`--resume` は同じ出力先と条件を指定し、保存済みconditionsのsource_sha256、実行環境、方式、局面バイト列、seedまたはseed一覧、全予定、組数、手数上限、worker数を照合する。Git HEADやdirty状態の違いだけでは拒否しない。保存済みの完了局は保持し、中断・故障・欠落局だけを同じseedで開始局面からやり直す。局JSONは予定・条件ハッシュ・合法棋譜・終局を検証する。破損・予定外局・シンボリックリンクは拒否する。summaryが欠落・古い場合は局JSONから再構成する。同じ出力先への同時実行は `.comparison.lock` で拒否し、強制終了後のロックはPIDを人が確認するまで自動解除しない。Ctrl-Cは新規投入を止めて開始済みworkerを回収する。強制終了で保存されなかった局は次回に開始局面から再実行するため、その間の経過時間はsummaryに残らず、再開後の時間は下限として扱う。

### 分析と適用範囲

分析CLIが現在受け付けるのは、独立種一覧を保存した完了conditions v2/v3実験である。予定全件、局ファイル集合、execution条件、局ごとのconditions参照、乱数種、棋譜の合法再生と終局、summary再集計を照合する。通常時はv2 conditions+summary v1、v3+summary v2を組み合わせる。再開後はどちらの条件版もsummary v3を使え、下限時間フラグを含めて再集計する。`--seed` によるconditions v1/v3は、形式が条件とworker数を記録していても分析対象外である。欠落・余分・混在・未完了・不整合は分析前に拒否する。結果は入力と別の新規JSONへ保存する。旧conditions v1には今回の独立抽出前提を遡及適用しない。

#### 分析CLIの局単位再開

初回分析では、出力JSONの隣に `<output名>.checkpoint/` を作り、conditions・summary・予定・Pythonソースのfingerprintをmanifestに保存する。局ごとに元JSONのSHA-256と、最終集計に必要な終局・勝者・手数・方式別計時集計を、チェックサム付きの原子的JSONで保存する。棋譜本文と全手の計時配列は複製しない。局は `_load_game` による合法再生と予定・終局・計時照合が完了してからcheckpointに確定する。

Ctrl-Cでは終了コード130を返し、その時点までに完全検証された局だけを保持する。再開時は同じ `--input-dir` と `--output` に `--resume` を付ける。条件・summary・予定・ソースfingerprintが一致し、局checkpointの形式とチェックサムが正しいことを確認してから、保存済み局JSONの現在のSHA-256を照合する。一致した局は棋譜を再生せず、欠落局だけを通常どおり検証する。各局JSON bytesを読む必要はあるため、再開時間がディスク読込を含まずゼロになるわけではない。再構成した全局summaryを元summaryと照合し、候補方式視点の組得点と分析JSONを改めて計算する。このstoreは初回作成または再開時にmanifestを検証し、入力mapping・公開読込値から独立したdeep copyをcacheする。同じstore内の局ごとの保存・読込ではschedule全体を含むmanifestを繰り返しJSON解析しない。最終JSON保存後のcheckpoint削除がCtrl-Cで中断された場合も、完成済み結果を保存済みとして終了コード0を返し、同じ出力先へ再実行しない案内を出す。

最終JSONの新規保存が失敗・中断した場合はcheckpointを保持し、次回は全局再生なしで最終化を再試行できる。最終JSON保存後にcheckpoint削除だけが失敗した場合は、完成JSONを保ち警告して終了コード0とする。出力先が既にある状態では上書きしないため、この場合は完成JSONを確認し、同じ出力先へ再実行しない。チェックポイントの入力不一致・破損・予定外entryは終了コード2で拒否し、自動削除しない。内容を確認して進捗を破棄する判断をした場合だけ手動で削除する。

分析CLIの排他fileは `<output名>.lock` で、PIDとnonceを記録する。同じ出力先への並行実行を拒否する。強制終了後にlockが残った場合、PIDが動作中でないことを人が確認してから手動削除する。lockやcheckpointを自動で掃除しない。

局単位再開で検証するのは、CLIが作成した状態の入力一致と通常の偶発破損である。署名鍵のないローカルcheckpointの内容を人が書き換え、チェックサムも再計算した悪意ある変更、電源断後の永続性、任意OSのlock意味論、破損記憶媒体は保証しない。通常の成功結果を再生した小規模fixtureで新旧JSONの `analyzer` 識別を除く全項目と入力SHAの一致を確認する。実験本体の強さ判定を再実行する機能ではない。

候補方式の各局得点は勝ち `[1,1]`、負け `[0,0]`、通常千日手 `[1/2,1/2]`、手数上限の未決着と双方連続王手の未裁定 `[0,1]`。後二者を勝敗や0.5へ決め打ちせず下限・上限の両方へ残す。二局一組内の平均得点を一標本として組間を扱い、区間半径は `sqrt(log(40)/(2*n))`。95%の主区間は平均得点の下限から半径を引いた値と、上限平均に半径を足した値を `[0,1]` に切り詰める。確認比較は区間下端が0.5より大きい場合だけ改善支持、上端が0.5より小さい場合だけ悪化支持、それ以外は判断不能。50%は互角の境目であり、95%ではない。pilotは探索的集計だけで強さ判定をしない。

この区間は組間の独立抽出を仮定し、今回の6局面を均等に扱う一つの総合比較に限る。局面別・先後別は記述集計で、個別の95%保証を持たない。参照値2,035組は、未決着なし・真の得点率55%・検出力80%という仮定下でHoeffding不等式から得る十分条件であり、必要最小値でも棋力向上の保証でもない。未決着のある実験はその組数でも目標検出力を保証しない。時間上限・対局完了時間・局面群の実戦代表性・真の棋力差は別途未検証である。

分析・再開readerは、保存棋譜の `GameRecord.from_payload` で全手を既存の合法操作により検証・再生する。続く `_validate_and_replay` は計時・手番・方式・棋譜一致、各手の合法適用・反復・手数上限、末尾SFEN・終局・勝者照合を保持する。次の記録手がある中間局面では、その合法再生済みの一手を合法手存在の根拠にし、存在確認だけの全合法手列挙を省く。末尾は実際に列挙し、反復終局は従来どおり盤面終局判定を行わない。中断・故障局を読む局単位再開も同じreaderを使う。これは保存結果を読む処理の短縮で、対局実行側の探索・時計境界や通常CLI/USIの選択肢を変えない。実装の記録は[C1分析短時間化の学習記録](../learning/c1-analysis-performance-investigation.md)、承認仕様は[設計](../plans/2026-10-25-c1-analysis-legal-witness-design.md)を参照する。全4,080局の旧新版分析JSONは `analyzer` を除く全項目が一致した。統計判定は判断不能で、B1改善の根拠ではない。

終了コードは準備/分析CLIが正常0、引数・入力不正2、実行/保存故障1、Ctrl-C 130。比較CLIは既存の対局保存契約を使い、対局・保存故障1、入力不正2、Ctrl-C 130。設計と実装経緯は[C1承認済み設計](../plans/2026-10-24-c1-rook-mobility-evaluation-design.md)、[比較実装計画](../plans/2026-10-24-c1-rook-mobility-evaluation-implementation-plan.md)、[局単位再開計画](../plans/2026-10-25-c1-comparison-resume-plan.md)、[学習記録](../learning/c1-rook-mobility-evaluation.md)にある。
