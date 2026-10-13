# 学習・開発の再開案内

## 現在地


2026-10-13、直近テーマ「通常停止の再確認条件だけ」は条件作成・独立レビュー・本人承認後の直接USI一回・本人受け入れ・理解確認・main統合まで完了した。G2のShogiHome実機確認では4.516秒で合法な一応答を確認したが、探索中の通常 `stop` とその後の応答は未観測で、人間側切れ負けとなった。その後の直接USI観測では通常 `stop` 後の合法 `bestmove` 一件と終了コード0を確認した。ShogiHome経路は依然未検証。[G2実施記録](learning/clock-stop-real-check-conditions.md)、[直接USI条件・結果・学習記録](plans/2026-10-13-normal-stop-recheck-conditions.md)、[直接USI学習記録](learning/normal-stop-recheck-conditions.md)を参照。

前テーマ「ShogiHomeで通常停止を観測する条件だけ」は、条件案と実施開始の本人承認後に事前確認を行ったが、**画面操作による通常 `stop` の経路を確認できず、実施条件は成立しなかった**。探索・対局は開始していない。承認後に行った画面読み取りと固定版資料照合、未変更・未実施事項、本人の結論は[記録](learning/shogihome-normal-stop-conditions.md)、当初案は[条件案の履歴](plans/2026-10-13-shogihome-normal-stop-conditions.md)へ保存した。

直近テーマ「ShogiHomeの時計期限による停止」は、本人が条件案・実施開始と具体的設定変更/ログ採取/保全/再起動を承認し、一局・一goを実施した。2.316秒後に合法な `bestmove 3c2c` が返り40手目２三玉・人間手番を確認したが、外部stopは0件で時計期限停止は未観測。画面照合期限と起動数の条件にもずれがある。対局設定は、対象版の設定保存経路を確認した後に別途追加承認を得て一度の復帰対局で元値へ戻し、保存値とセッション0を画面確認した。本人は結果を受け入れ、最後の理解確認に回答した。記録はmainの `ae5d558` に取り込み済み。[実施・復帰・理解確認記録](learning/shogihome-clock-deadline-conditions.md)、[当初の承認条件](plans/2026-10-13-shogihome-clock-deadline-conditions.md)。

**現在のShogiHome状態は復帰済み。** 双方10分＋30秒、別時計OFF、エンジン時間切れありON、最大手数40を対局設定画面で確認。Difficulty Random、三種ログOFF、保全したbefore棋譜の開始局面、USI/CSAセッション0も確認した。観測結果の受け入れと最後の理解確認は済み。文書変更はmainの `ae5d558` に取り込み済み。次は[次テーマ候補](next-topics.md)から本人が選ぶまで新しい学習・実施を開始しない。

2026-10-13のテーマ完了時点は `/Users/oki2a24/kaname-shogi` のmain、HEAD `ae5d558`、origin/mainより28コミット先行、clean。コミットフックでRuff整形確認38ファイルと全検査が成功し、コミット後の差分検査も成功した。コード・テストは変更していない。次は[候補](next-topics.md)から本人が選ぶまで新しいテーマを始めない。

## 二手先読み設計の完了

設計記録 `3e3c4cf`、統合検証 `cd19b58`、最終回答と候補 `c41aaea` はmainにある。取り込み先の相対リンク先373件欠落0（見出しアンカー対象外）、差分、Ruff整形28ファイルとlintを確認済み。文書のみで全体テストは再実行していない。今回の準備の検証は[引き継ぎ](handover-two-ply-implementation-plan.md)へ記録する。数値比較の習得全般を確認済みとは扱わない。

## 前テーマの完了と履歴

文書整理 `bbc2619` と統合・検証記録 `6d3f7e4` は元のmainへ取り込み済み。リンク888件・履歴3本文一致・差分・Ruff整形28ファイルとlintが成功。文書のみで全体テストは再実行していない。最後の回答と補足は[整理記録](learning/documentation-chapter.md)。今回の準備の検証とGit状態は[引き継ぎ](handover-evaluation-next-stage.md)を参照する。
