# 学習・開発の再開案内

## 現在地

2026-10-14、本人の明示承認に基づき、Python移行を作業ブランチ `codex/python-315-migration` 上で実施し、追加承認後にmainへ統合した。Homebrew CPython 3.15.0をこのcloneの `.venv` に使い、Python 3.14.8を最低対応境界として検証した。Ruff 0.16.10と `core.hooksPath=.githooks` は維持。既存のPython 3.9仮想環境は `/private/tmp/kaname-shogi-venv-python39-20261014` へ退避して保持している。主な変更、実施した検証、独立レビュー、main統合後の検証、制約と復帰方法は[実装計画と事後結果](plans/2026-10-14-python-315-migration-implementation-plan.md)、回答・判断・実施経緯は[学習記録](learning/python-upgrade-impact.md)を参照する。

Ruff `target-version` は `py314`。`scripts/setup_dev.py` はホストと既存 `.venv` の双方でPython 3.14以上を確認し、ShogiHome用ランチャーはclone内 `.venv/bin/python` を使う。CPython 3.14.8と3.15.0で全テストを実行し、Ruffの整形検査・lintも通過した。LinuxとShogiHome GUIからの実接続・対局は未検証。二手先読みと時計は「学習・実装テーマとしては完了。ShogiHome実機挙動と一般的な時間保証は未確認のまま」。

mainへの統合、取り込み先検証、最後の理解確認と回答記録は完了した。Python移行テーマは完了し、次テーマは未選定である。[候補と推薦理由](next-topics.md)から本人が選ぶまで、新しい学習・実装を開始しない。移行時の開始状態は[開始時点の引き継ぎ](handover-python-upgrade-impact.md)に履歴として残す。

前テーマ「ShogiHomeの『対局中断』経路を資料から整理する条件だけ」は、資料整理・実機観測・結果受け入れ・復帰・理解確認まで記録してmainへ統合済み。探索中断は未達、秒読み30秒への復帰は完了。二手先読みと時計の学習・実装テーマは完了扱いだが、ShogiHome実機挙動と一般的な時間保証は未確認のまま。詳細は[実施記録](learning/shogihome-interruption-conditions.md)。

## 二手先読み設計の完了

設計記録 `3e3c4cf`、統合検証 `cd19b58`、最終回答と候補 `c41aaea` はmainにある。取り込み先の相対リンク先373件欠落0（見出しアンカー対象外）、差分、Ruff整形28ファイルとlintを確認済み。文書のみで全体テストは再実行していない。今回の準備の検証は[引き継ぎ](handover-two-ply-implementation-plan.md)へ記録する。数値比較の習得全般を確認済みとは扱わない。

## 前テーマの完了と履歴

文書整理 `bbc2619` と統合・検証記録 `6d3f7e4` は元のmainへ取り込み済み。リンク888件・履歴3本文一致・差分・Ruff整形28ファイルとlintが成功。文書のみで全体テストは再実行していない。最後の回答と補足は[整理記録](learning/documentation-chapter.md)。今回の準備の検証とGit状態は[引き継ぎ](handover-evaluation-next-stage.md)を参照する。
