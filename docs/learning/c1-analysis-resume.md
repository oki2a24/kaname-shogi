# C1分析CLIの局単位再開機能

## 目的と開始状態

C1確認比較の分析CLIは4,080局の棋譜を全件検証するため長時間を要した。ユーザーは分析CLIの途中終了・再開機能を希望し、再開単位は局単位を選んだ。分析CLI・比較CLIの実データ実行は人間が端末から行う方針を確認し、この実装では4,080局の本番入力を起動しない。

本人は局単位チェックポイントの設計と実装計画全体を承認した。対象は分析CLIの初回保存、完了局の再利用、入力・条件不一致の拒否、summary再集計、ロック、最終保存再試行である。対局CLIの高速化、並列化、局途中再開、通常CLIのSFEN入出力、飛車可動性バージョン2、B1強さの再判定は含めない。

作業は `/Users/oki2a24/.codex/worktrees/c1-analysis-resume/kaname-shogi` の `codex/c1-analysis-resume` で行った。開始基点は確認済みの分析reader短縮branch `codex/c1-analysis-legal-witness` の `6fd2dba`。元checkout `/Users/oki2a24/kaname-shogi` の未コミットC1記録・実験データ、および `docs/resume.md` は変更していない。mainへの統合は未承認・未実施。

## 設計・実装

- 初回分析は出力JSONの隣にmanifestと検証済み局の小さなsummaryをチェックサム付きで保存する。
- 再開では条件・summary・schedule・ソース指紋・局JSON SHA-256を照合し、既に検証済みの局は合法再生せず、未完了局だけを検証する。全局summaryを元summaryと再集計照合し、pair scoreと分析JSONは再導出する。
- 同じ出力先の重複実行はPID/nonceのexclusive lockで拒否する。lockやcheckpointの残骸は自動削除しない。
- 最終分析JSONの保存が失敗・中断した場合はcheckpointを保持する。完成JSONの保存後、checkpoint cleanupだけが失敗・中断した場合は完成結果を成功扱いで保持し、同じ出力先へ再実行しない案内を出す。
- レビュー対応で、lock作成直後の `fstat` 失敗・割込みでもFDと空lockのcleanupを試みるようにした。closeが失敗した場合は元の割込みを保ちつつ診断を出す。manifestはcreate/resumeで検証・保持し、局ごとの保存・読込でschedule全体を繰り返しJSON解析しない。
- 勝者情報を含む合法な一手詰みfixtureを先後交換し、キャッシュから `winner_side` と `winner_policy` を復元した後、候補勝ち・候補負けと二局平均0.5を確認する。

## TDD・検出力・確認範囲

主要な独立fixtureは二局一組で、期待値は比較writerや完成分析JSONからコピーせず手書きで設定している。単独のテストは、局保存前後の割込み、再開時の再生回数、conditions/summary/局JSONの不一致、破損・予定外entry・symlink、summary不一致、source fingerprint変更、出力の上書き防止、ロック、勝者先後の復元を対象とする。局単位テストは保存形式とFD/lock境界、CLIテストは終了コード・output/checkpoint状態、readerテストは合法棋譜・summary・pair scoreを検出する。全体テストは既存機能への回帰を確認する。

追加した境界テストでは、次のRedを確認してから実装修正した。

- `fstat` の `OSError` は例外を包まず漏らし、`KeyboardInterrupt` では空lockが残り、どちらもFD cleanupできていなかった。
- per-game `save_game`・`load_game`・`completed_game_ids` はmanifestを計4回再解析していた。
- manifest atomic write中の `KeyboardInterrupt` は部分checkpoint rootを残していた。
- 最終JSON保存後のcheckpoint削除中断は、完成JSONがあるのに終了コード130と `--resume` 案内を返していた。
- lock cleanup時の非EBADF close失敗を黙って無視していた。追加テストではstderr診断がないことで失敗した。
- source fingerprint変更の専用テストは、追加前にstatus 0でoutputを作り、期待status 2に対してRedだった。
- cache分離テストは浅いcacheで元schedule変更を反映してしまい、完了局を予定外として誤拒否するRedだった。deepcopyでcacheと入力・公開戻り値を分離してGreenになった。
- `mkdir()` がrootを作った直後に割り込みを注入すると空rootが残るRedだった。例外時に作成先directoryを掃除するようにしGreenになった。

最終化前の4つの代表変異は隔離した `/tmp` コピーで実施した。局入力SHA比較を無効化すると変更済み完了局を拒否するassertionが失敗し、summary比較を無効化するとsummary mismatch拒否が失敗した。局検証前に2局目のcheckpointを保存すると割込みテストが完了2局と誤認して失敗し、cached局も再生する変異では再利用テストが重複checkpointを作るため失敗した。各変異は作業worktreeへ残していない。

2026-10-26の最終コード変更後の検証では、`.venv/bin/python -m unittest tests.test_analysis_resume tests.test_analyze_comparison tests.test_comparison_result_io -v` が62件で成功し、`.venv/bin/python scripts/run_tests_parallel.py` が58モジュール894件で成功した（27.163秒）。Ruffのimport検査、format check、全体checkも診断なし。format書込みは対象ファイル一件で権限エラーになったため、Ruffの差分を手動反映し、最終 `format --check` で108ファイル整形済みを確認した。文書リンクは6文書で相対リンク欠落0。`git diff --check` も成功した。変更は2026-10-26に `0fcb157` (`feat: 分析CLIの局単位再開を完成`) として作業branchへコミットし、hookのformat/checkも成功した。CI・実データ分析は起動していない。

## 独立レビュー

最初の最終レビューはCritical 0、Important 0、Minor 1だった。close errorを区別せずFD残存の可能性を診断できない点は、追加Redテスト後に `EBADF` とその他を区別し、cleanupを両方試し、割込み中もstderrへ診断するよう修正した。続く独立再レビューはCritical 0、Important 0、Minor 2。1件はfstat前に外部から同じlock pathを空fileへ差し替える狭い競合で、fstat前にはfd inodeが得られず自動削除の完全な所有判定ができないため、コードdocstringと本節で保証対象外として明記した。もう1件はmanifestの入れ子mappingが入力・公開戻り値と共有される点で、TDD Redを確認し、deepcopyでキャッシュ・入力・戻り値を分離した。さらにroot mkdir直後の割込みで部分checkpointが残るMinorは、専用テストをRed→Greenにしてcleanupを追加した。最終再レビューではCritical/Importantの新規指摘なし。残る制約は、lock pathへの外部差し替えと、CLIが排他lock中に利用者がcheckpoint filesystemを直接編集する状況を保証しないこと。

## 未検証・限界

- 二局の小規模fixtureは状態遷移・得点復元の契約を確認するが、任意件数や4,080局の実行時間を保証しない。
- 実端末Ctrl-C、プロセス強制終了、電源断後の永続性、複数OSのlock意味論、記憶媒体故障は検証していない。
- ローカルcheckpointのチェックサムは偶発的破損検出であり、内容とchecksumを両方書き換える悪意ある編集への署名保証ではない。fstat前に外部プロセスが排他作成した空lockを同じpathへ差し替える競合も対象外とする。
- この機能は分析処理の再開性を改善する。C1の候補方式が強くなったかどうかを示すものではない。

## 実装branchのGit状態（2026-10-26時点）

実装計画のTask 1〜3は `2618104`, `96f1f87`, `4a63943`、Task 4の機能・利用資料・設計・学習記録は `0fcb157` として `/Users/oki2a24/.codex/worktrees/c1-analysis-resume/kaname-shogi` の `codex/c1-analysis-resume` にコミット済み。mainまたは元checkoutへの取り込みは別承認を待つ。

## main起点の候補での再検証（2026-10-27）

現在のmain `ba03ee9` には分析reader短時間化・比較CLIの合法手判定早期終了が統合済みだが、分析CLI再開機能は含まれていなかった。再開機能の5コミットだけをmain起点branch `codex/c1-analysis-resume-integration`（`/Users/oki2a24/.codex/worktrees/c1-analysis-speedup/kaname-shogi`）へ適用し、既存reader短縮と一緒に検証している。元checkout `/Users/oki2a24/kaname-shogi` の未コミット記録・実験データは操作していない。

統合候補レビューで、最終JSONの保存直後やlock解除中の割込みが完成結果を終了コード130として扱い、再実行不能にする可能性が指摘された。出力JSONが今回のpayloadと一致する場合は完成扱いにしてcheckpoint後処理へ進め、lock解除の割込みは診断して終了状態を変えないようにした。追加TDDでは「writerの完全保存直後に割込み」と「lock解除中の割込み」が変更前に終了コード130でRed、修正後Green。再レビューで指摘されたbool/整数のJSON値同一視も、`False` と `0` の変異でRedを確認し、既存の型厳密比較 `_json_values_equal` を使う修正でGreenにした。レビューMinorの索引漏れは `docs/README.md` に設計・計画・学習記録の行を追加して解消した。

main起点候補の最終コード変更後、関連 `.venv/bin/python -m unittest -q tests.test_analysis_resume tests.test_analyze_comparison tests.test_comparison_result_io` は65件で成功し、全体 `python3 scripts/run_tests_parallel.py` は58モジュール898件・22.218秒で成功した。Ruffのimport整理・整形・全体checkと `git diff --check` も成功。README・索引・設計・計画・知識・学習記録の6文書でローカルリンク692件、欠落0件を確認し、索引からの再開仕様見出しリンクも存在する。最終独立再レビューはCritical 0、Important 0、Minor 2。1件（レビュー・リンク確認未実施という一時的な記録）はこの追記で解消し、もう1件（部分JSONの書込と削除がともに失敗するI/O障害後は、残存出力を人が確認して処置する）は既存の新規限定保存方針に沿う未検証限界として保持する。実端末Ctrl-C・プロセス強制終了・記憶媒体故障は未検証。4,080局の実分析や比較は起動していない。C1強さ判定「判断不能」と、分析CLI再開機能のmain統合状態は別事項である。

## main統合と取り込み先検証（2026-10-27）

本人の「分析CLIの局単位再開機能もマージしたい」という指示を受け、統合候補 `codex/c1-analysis-resume-integration` をローカルmainへfast-forwardした。mainは `ba03ee9` から `441345e` へ進み、再開機能・そのレビュー修正・利用資料を取り込んだ。統合に使ったworktreeは `/Users/oki2a24/.codex/worktrees/c1-analysis-speedup/kaname-shogi`。元の `/Users/oki2a24/kaname-shogi` はbranch `codex/c1-analysis-performance-investigation` の未コミット記録・実験データを保持し、変更していない。pushはしていない。

取り込み先mainで `.venv/bin/python -m unittest -q tests.test_analysis_resume tests.test_analyze_comparison tests.test_comparison_result_io` が65件、`python3 scripts/run_tests_parallel.py` が58モジュール898件・22.530秒で成功した。`.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`（108ファイル変更なし）、`.venv/bin/ruff check .`、`git diff --check` も成功。main統合後の状態更新後に9文書のローカルリンク808件を確認し、欠落0件。索引からの分析CLI再開仕様見出しリンクも存在する。文書のみの追記のため製品テストは再実行していない。実データ分析・比較は実行していない。C1の棋力改善判定が「判断不能」であることと、分析CLIの中断・再開機能がmainに統合されたことは別の結論である。

## 最後の理解確認（2026-10-27）

質問：分析CLI再開機能のmain統合によって、C1の棋力判定も変わったと言えるか。

本人の回答：「言えない。」

補足：その理解で正しい。分析CLI再開は検証済み棋譜の中断・再開を扱い、候補方式の指し手選択や対局成績を変える機能ではない。初回確認比較と独立追試の区間が50%を含むため、C1の判定は引き続き「判断不能」である。本人の追加質問への確認では、C1の比較接続コード `material-rook-mobility` は現在のmainに含まれている。比較方式の登録は[比較CLIの案内](../../README.md)と[比較・分析の知識メモ](../knowledge/search-comparison.md)にあり、C1実装コミット `42fc9e9` は現在のmainの祖先である。局単位再開の統合コミット `441345e` は別の補助機能で、統合後もC1の強さ判定は変わらない。

## 脇道の完了確認と主線A2への帰還選定（2026-10-27）

本人は「脇道は全て完了？そうなら本筋に戻りましょう」と述べた。照合した結果、着手済みのC1補助作業（比較CLI局単位再開、分析CLI短時間化、比較CLI局内高速化、分析CLI局単位再開）はローカルmainへの統合と統合先検証まで完了している。C1の強さ比較も完了したが、結果は「判断不能」であり、改善または悪化が確認されたという意味ではない。通常CLIのSFEN入出力と飛車可動性バージョン2は、将来候補として保留された未着手項目で、現在の作業の未完了事項とは区別する。

本人の「本筋に戻りましょう」をロードマップ上の次の主線A2「次の駒得以外の評価項目を一つ選ぶ」の選定として記録する。選んだのはA2というテーマであり、具体的な評価項目、設計、実装はまだ選定・承認していない。新しいセッションで学習・候補比較から始める。現在の作業場所、Git状態、読む資料、再開プロンプトは[A2引き継ぎ](../handover-a2-non-material-position-evaluation.md)に記録する。
