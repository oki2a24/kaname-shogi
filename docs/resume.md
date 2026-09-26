# 学習・開発の再開案内

第38回「弱い自動指し手のための合法手列挙と一手選択」は、実装・検証・独立レビュー・main取り込み・最後の理解確認まで完了した。本人は次テーマとして第39回「人間対コンピュータのCLI進行」を選定し、新しいセッションで開始することを希望した。このファイルと引き継ぎ文書の更新・コミットが済むまで、次テーマの一次資料確認、確認問題、設計、実装を開始しない。

## テーマ間のセッション再開手順

新しいセッションでは、まず現在のGit状態と指定文書を確認する。過去の引き継ぎにあるコミット、作業ツリー、テスト結果は、現在と同一だと決めつけない。

確認問題は一度に一問だけ出して本人の回答を待つ。対象範囲・表現・確認方法を設計書に記録して提示し、本人の明示的な承認を得るまでコード・テストを変更しない。承認後は、作業ブランチでTDD、Refactor要否確認、独立レビュー、全検証、記録、本人承認後のmain取り込みとmain側の再検証を行う。

最終整理：2026-09-26。恒常的な運用方針はルートの `AGENTS.md` を参照する。

## 現在の到達点

盤面、駒、持ち駒、手番、成り、駒取り、二歩、行き所のない駒、王手放置、打ち歩詰め、詰み、投了を、現在の学習範囲で扱える。CLIは先手・後手とも人が `move` / `drop` / `resign` を入力する対局を進め、終了時に `GameRecord` を返す。

第38回で、局面を変更しない `BoardMove`、`DropMove`、`Move` を追加した。`legal_moves(position)` は既存規則に従う全合法手を固定順タプルで返し、`choose_weak_move(moves, rng)` は注入された `random.Random` により一覧から一様に一手を選ぶ。空一覧の `None` は選択不能だけを表し、詰み・投了・勝敗を決めない。

人間対コンピュータの手番、乱数生成器の寿命、表示時機、`None` と終局判定の関係、CLI開始方法は未決定である。評価、探索、USI、SFEN、CLI保存読込、千日手、持将棋、入玉、時間切れ、反則勝敗も未実装である。

## 第39回でまず行うこと

1. `docs/handover-human-vs-computer-cli.md` と再開用プロンプトに従い、現在の状態と第38回の記録を確認する。
2. 一次資料を確認し、人間対コンピュータCLIの最小範囲について、確認問題を一問ずつ開始する。
3. 設計承認前は、コード・テストを変更しない。

## 第39回の再開用プロンプト

```text
kaname-shogiの第39回「人間対コンピュータのCLI進行」を新しいセッションで始めてください。最初にAGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/02-project-direction.md、docs/learning/38-weak-move-selection.md、docs/knowledge/31-weak-move-selection.md、docs/handover-human-vs-computer-cli.md、docs/plans/2026-09-25-weak-move-selection-design.md、kaname_shogi/cli.py、kaname_shogi/move.py、kaname_shogi/movegen.py、kaname_shogi/game_record.py、tests/test_cli.py、tests/test_movegen.pyを読み、git status --short --branchで現在の状態を確認してください。日本将棋連盟などの一次資料で対局の手番交代・投了・終局に関係する必要最小限の規則を確認し、人間対コンピュータCLIの対象範囲を確認問題として一度に一問ずつ出して私の回答を待ちながら合意してください。少なくともコンピュータ担当の先後、CLI開始方法、乱数生成器の生成・寿命、人間入力と自動手の表示時機、合法手なし・投了・EOF/Ctrl-Cの責務、GameRecordへの記録を確認してください。設計合意と設計書承認までコードやテストを書かないでください。承認後に作業ブランチでTDD、独立レビュー、全検証、学習記録、mainへの取り込みを行い、最後に理解確認を一問だけ出してください。コミットメッセージは日本語のConventional Commitにしてください。
```

## 実行場所と最初の確認コマンド

```sh
cd /Users/oki2a24/kaname-shogi
git status --short --branch
python3 -m unittest discover -s tests -v
```

過去の成功記録を今回実行済みとは扱わない。別の作業ツリーを選ぶ場合は、実際の絶対パスと元の `main` との関係を確認する。
