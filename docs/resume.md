# 学習・開発の再開案内

第37回「棋譜・局面のファイル保存」は実装・検証・独立レビュー・main取り込み・最後の理解確認まで完了した。最初の目標との距離を見直した結果、次テーマは第38回「弱い自動指し手のための合法手列挙と一手選択」として選定済みである。新しいセッションで始める準備を完了した。

## テーマ間のセッション再開手順

次テーマを選んだら、アシスタントが引き継ぎ文書とこのファイルに再開用プロンプトを記録する。その後、人間が再開用プロンプトを新しいセッションへ入力する。入力を受け取る前に、アシスタントは次テーマの一次資料確認・確認問題・設計・実装を開始しない。人間の入力を起点に、現在のGit状態と記録を確認してから次テーマを始める。

実装計画を文書として作成・更新した場合も、内容を提示して本人の明示承認を待つ。承認前にTDD、コード・テスト変更、実装を開始しない。

最終整理：2026-09-24。恒常的な運用方針はルートのAGENTS.mdを参照する。

## 現在の到達点

玉・歩・金・銀・桂・香・飛車・角について、盤上の駒の所有者に応じた移動先候補を計算できる。`PieceType` は盤上14種、`BasicPieceType` は持ち駒8種を表し、`Piece` は不変値である。`Position` は盤面、手番、先手・後手の持ち駒を持ち、`Board.copy()`・`Hand.copy()`・`Position.copy()` は試し指し用に独立複製を返す。

`apply_move(position, source, destination, *, promote=False)` は、手番の駒だけを既存候補へ移動できる。成り・強制成り・駒取りを扱い、相手玉を取る操作を拒否する。`apply_drop(position, piece_type, destination)` は、持ち駒を空マスへ打ち、玉の指定、持ち駒不足、二歩、行き所のない歩・香・桂、自玉の王手放置、打ち歩詰めを拒否する。いずれも失敗時に盤面・持ち駒・手番を変更しない。

`has_legal_move(position)` は盤上移動、不成・成り、玉以外の持ち駒打ちを複製局面で試し、現在実装済みの規則で合法手があるかを返す。`is_checkmate(position)` は手番側の玉が盤上にあり、王手を受け、合法手がないときだけ真を返す。`is_game_over(position)` は詰みだけを終局とする。

`GameRecord` は開始局面、成功した `move` / `drop` の履歴、現在局面を保持する。`position_at` は開始局面から任意手数を再適用し、公開局面は独立複製を返す。`GameRecord.save(path)` / `GameRecord.load(path)` は専用JSONへ開始局面と成功手を保存・読込し、既存の合法手適用で現在局面を再現する。CLIは詰み・投了・EOF・Ctrl-Cで対局記録を返すが、先手・後手とも人が入力する。コンピュータの一手選択、CLIの保存読込、SFEN、USI、評価、探索、千日手、持将棋、入玉、時間切れ、反則勝敗は未実装である。

## 直近までの記録

- 第32回で、盤上移動・成り・駒打ちを既存規則で試して合法手の有無を返す `has_legal_move`、詰み、終局判定を実装した。
- 第34回で、先手・後手とも人が入力するCLI対局ループを実装した。
- 第36回で、開始局面と成功手の履歴を `GameRecord` に分離して保持し、任意手数の局面を再現できるようにした。
- 第37回で、専用JSONへ棋譜を保存・読込し、206件のテスト、CLIスモーク、差分チェック、独立レビュー、main取り込みを完了した。
- 第37回の理解確認後、最初の目標が「弱くても息子と対戦できる将棋ソフト」であることを再確認した。SFENやCLI保存読込を先に進めるのでなく、次は合法手を列挙して弱い自動指し手が一手を選ぶ基盤を扱うことを本人が選定した。

## 次に行うこと

1. `docs/handover-weak-move-selection.md` の再開手順に従い、現在の状態を確認する。
2. 第38回の一次資料確認と確認問題を開始する。設計承認前にはコード・テストを変更しない。

## 第38回の再開用プロンプト

```text
kaname-shogiの第38回「弱い自動指し手のための合法手列挙と一手選択」を新しいセッションで始めてください。最初にAGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/02-project-direction.md、docs/learning/32-checkmate-and-game-end.md、docs/learning/37-game-record-file-save.md、docs/knowledge/25-checkmate-and-game-end.md、docs/handover-weak-move-selection.md、kaname_shogi/model.py、kaname_shogi/movegen.py、kaname_shogi/cli.py、tests/test_movegen.py、tests/test_cli.pyを読み、git status --short --branchで現在の状態を確認してください。日本将棋連盟などの一次資料で合法手・成り・駒打ちに関係する規則を確認し、合法手の公開表現、盤上移動と駒打ちの扱い、列挙順、一手選択の規則、合法手がない局面の扱い、CLIとの境界を、確認問題として一度に一問ずつ出して私の回答を待ちながら合意してください。設計合意と設計承認までコードやテストを書かないでください。承認後にTDD、独立レビュー、全検証、学習記録、mainへの取り込みを行い、最後に理解確認を一問だけ出してください。コミットメッセージは日本語のConventional Commitにしてください。
```

## 実行場所とコマンド

```sh
cd /Users/oki2a24/kaname-shogi
python3 -m unittest discover -s tests -v
python3 -m kaname_shogi
```

過去の成功記録を今回実行済みとは扱わない。別の作業ツリーを選ぶ場合は、実際のパスと元のmainとの関係を確認する。
