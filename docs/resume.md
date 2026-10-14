# 学習・開発の再開案内

## 現在地

2026-10-14、「三つの選択方式の構成調査だけ」を実施し、[構成調査記録](learning/three-policy-architecture.md)へ結果を記録した。本人は現状維持を確認し、次のレベルの将棋エンジンでは方式別ファイル分離を希望した。今回の調査テーマは完了。次テーマは未選定で、「次のレベル」の範囲や分割境界も未決定。コード・設定・テスト変更、テスト実行、リファクタリング、分割、実装計画の承認は行っていない。開始時点と調査範囲は[引き継ぎ](handover-three-policy-architecture.md)を参照する。Python移行の変更・検証・独立レビュー・統合は[実装計画と事後結果](plans/2026-10-14-python-315-migration-implementation-plan.md)、回答と判断の経緯は[学習記録](learning/python-upgrade-impact.md)を参照する。

次テーマは本人の選定待ち。Ruff `target-version` は `py314`、実測したPythonは3.14.8と3.15.0。LinuxとShogiHome GUIからの実接続・対局は未検証。二手先読みと時計は「学習・実装テーマとしては完了。ShogiHome実機挙動と一般的な時間保証は未確認のまま」。

今回の選定理由と候補履歴は[次テーマ候補](next-topics.md)、Python移行開始時の背景は[開始時点の引き継ぎ](handover-python-upgrade-impact.md)にある。

前テーマ「ShogiHomeの『対局中断』経路を資料から整理する条件だけ」は、資料整理・実機観測・結果受け入れ・復帰・理解確認まで記録してmainへ統合済み。探索中断は未達、秒読み30秒への復帰は完了。二手先読みと時計の学習・実装テーマは完了扱いだが、ShogiHome実機挙動と一般的な時間保証は未確認のまま。詳細は[実施記録](learning/shogihome-interruption-conditions.md)。

## 二手先読み設計の完了

設計記録 `3e3c4cf`、統合検証 `cd19b58`、最終回答と候補 `c41aaea` はmainにある。取り込み先の相対リンク先373件欠落0（見出しアンカー対象外）、差分、Ruff整形28ファイルとlintを確認済み。文書のみで全体テストは再実行していない。今回の準備の検証は[引き継ぎ](handover-two-ply-implementation-plan.md)へ記録する。数値比較の習得全般を確認済みとは扱わない。

## 前テーマの完了と履歴

文書整理 `bbc2619` と統合・検証記録 `6d3f7e4` は元のmainへ取り込み済み。リンク888件・履歴3本文一致・差分・Ruff整形28ファイルとlintが成功。文書のみで全体テストは再実行していない。最後の回答と補足は[整理記録](learning/documentation-chapter.md)。今回の準備の検証とGit状態は[引き継ぎ](handover-evaluation-next-stage.md)を参照する。
