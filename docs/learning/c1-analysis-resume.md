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

## Git状態・次の段階

実装計画のTask 1〜3は `2618104`, `96f1f87`, `4a63943`、Task 4の機能・利用資料・設計・学習記録は `0fcb157` として `/Users/oki2a24/.codex/worktrees/c1-analysis-resume/kaname-shogi` の `codex/c1-analysis-resume` にコミット済み。mainまたは元checkoutへの取り込みは別承認を待つ。
