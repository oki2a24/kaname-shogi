# 学習・開発の再開案内

## 現在地

2026-10-11更新。選定テーマ「40手目の長考理由を調べる範囲の設計だけ」について、限定読取り調査、ローカル計測、ShogiHomeでの40手上限／41手上限比較まで本人の段階ごとの承認を得て実施した。最後の比較は2組・4応答で終了。40手条件では2回とも応答後に `gameover draw`、41手条件では応答後に局が継続した。応答時間は40手条件が30.141秒・29.700秒、41手条件が29.488秒・29.578秒で、平均差は約0.388秒。この少数回から長考原因は判定できず、「40手の設定が長考の原因」という仮説は未検証のまま。詳細と限界は[実施記録](learning/long-think-scope-design.md)に保存する。

- 場所 `/Users/oki2a24/kaname-shogi`、後片付け開始HEAD `cb8a283`、ブランチ `codex/long-think-scope-handoff`。実績整理は同ブランチ上で行い、今回のmain取り込み・push・新規worktreeはない。main統合には別途本人承認が必要。
- 上限比較では `TwoPlyMaterial`、`USI_Hash=32`、Ponder OFFの下で、4回とも同じ39手分の `position` と同じ `go btime 600000 wtime 600000 byoyomi 30000` を使った。エンジン起動はUSIオプション確認2回と比較4回の計6回で、起動上限を使い切った。予定した3組のうち2組を行い、第3組は実施していない。検証用棋譜は本人の許可により破棄し、元の対象棋譜は変更していない。USIログは `/Users/oki2a24/Library/Logs/electron-shogi/usi-20261011_165821.log`。
- 比較後にShogiHomeを再起動し、Difficulty Random、Ponder OFF、USI・CSA・アプリログOFF、ログレベルINFO、USI/CSAセッション0を確認した。製品コード・テスト・設定ファイルの変更はない。
- 読取り調査では上限設定そのものがエンジンへ届く直接経路は見つからなかった。本人が別途承認したローカル確認では、同じ局面の履歴再生と探索応答を分けて計測した。履歴形式の `position→readyok` は中央値7.486 ms長く、フェンス後の `go→bestmove` は両形式とも約28秒。過去ログの計時区間への正確な寄与と40手上限による長考の因果は未確定。[ローカル計測結果](learning/long-think-scope-design.md#承認後の一回ローカル計測)
- 先行ローカル計測には、有効測定6回に対して子プロセスを7回起動した上限・停止条件からの未承認逸脱がある。A/B比較の6起動とは別の記録として[学習記録](learning/long-think-scope-design.md)に残している。
- 比較実績・仮説の切り分け・文書検証は[実施記録](learning/long-think-scope-design.md#承認後の40手上限比較2026-10-11事後記録)を参照する。記録は作業ブランチ上にあり、main取り込み・pushはしていない。
- 前テーマはmain統合・取り込み先検証・最後の理解確認まで完了。[実績](learning/two-ply-final-check.md)にある本人の待ち時間許容判断と、他局面・秒読み後の未保証を維持する。
- 次テーマは未選定。本人がテーマを選ぶまで、新しい学習・調査・計測・実装は開始しない。

## 次に読む資料

[調査範囲と結果](plans/2026-10-11-long-think-scope-design.md)、[今回の実施記録](learning/long-think-scope-design.md)。開始時点の背景・証拠パスは[引き継ぎ](handover-long-think-scope.md)に保存。

## 二手先読み設計の完了

設計記録 `3e3c4cf`、統合検証 `cd19b58`、最終回答と候補 `c41aaea` はmainにある。取り込み先の相対リンク先373件欠落0（見出しアンカー対象外）、差分、Ruff整形28ファイルとlintを確認済み。文書のみで全体テストは再実行していない。今回の準備の検証は[引き継ぎ](handover-two-ply-implementation-plan.md)へ記録する。数値比較の習得全般を確認済みとは扱わない。

## 前テーマの完了と履歴

文書整理 `bbc2619` と統合・検証記録 `6d3f7e4` は元のmainへ取り込み済み。リンク888件・履歴3本文一致・差分・Ruff整形28ファイルとlintが成功。文書のみで全体テストは再実行していない。最後の回答と補足は[整理記録](learning/documentation-chapter.md)。今回の準備の検証とGit状態は[引き継ぎ](handover-evaluation-next-stage.md)を参照する。
