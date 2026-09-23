# 学習・開発の再開案内

第33回「打ち歩詰め」は完了し、次テーマは第34回「CLIでの指し手入力と対局進行」に決定している。詳細な引き継ぎは[第34回引き継ぎ](handover-cli-gameplay.md)を参照する。

## テーマ間のセッション再開手順

次テーマを選んだら、アシスタントが引き継ぎ文書とこのファイルに再開用プロンプトを記録する。その後、人間が再開用プロンプトを新しいセッションへ入力する。入力を受け取る前に、アシスタントは次テーマの一次資料確認・確認問題・設計・実装を開始しない。人間の入力を起点に、現在のGit状態と記録を確認してから次テーマを始める。

実装計画を文書として作成・更新した場合も、内容を提示して本人の明示承認を待つ。承認前にTDD、コード・テスト変更、実装を開始しない。

最終整理：2026-09-23。恒常的な運用方針はルートのAGENTS.mdを参照する。現在はmainで第33回まで完了し、第34回を新しいセッションで開始する準備ができている。

## 現在の到達点

玉・歩・金・銀・桂・香・飛車・角について、盤上の駒の所有者に応じた移動先候補を計算できる。`PieceType` は盤上14種、`BasicPieceType` は持ち駒8種を表し、`Piece` は不変値である。`Position` は盤面、手番、先手・後手の持ち駒を持ち、`Board.copy()`・`Hand.copy()`・`Position.copy()` は試し指し用に独立複製を返す。

`apply_move(position, source, destination, *, promote=False)` は、手番の駒だけを既存候補へ移動できる。成り・強制成り・駒取りを扱い、相手玉を取る操作を拒否する。`apply_drop(position, piece_type, destination)` は、持ち駒を空マスへ打ち、玉の指定、持ち駒不足、二歩、行き所のない歩・香・桂、自玉の王手放置を拒否する。いずれも失敗時に盤面・持ち駒・手番を変更しない。

`is_in_check(board, side)` は指定側の玉への相手の利きを読み取る。`has_legal_move(position)` は盤上移動、不成・成り、玉以外の持ち駒打ちを複製局面で試し、現在実装済みの規則で合法手があるかを返す。`is_checkmate(position)` は手番側の玉が盤上にあり、王手を受け、合法手がないときだけ真を返す。`is_game_over(position)` は今回、詰みだけを終局とする。

投了、千日手、持将棋、入玉、CLI入力、履歴、評価、探索、USI/SFENは未実装である。打ち歩詰めは持ち歩による解除不能な王手を拒否する。

## 直近までの記録

- 第31回で王手判定と、盤上移動・駒打ちの自玉安全確認を実装した。
- 第32回で全候補を複製局面に適用する `has_legal_move`、王手かつ合法手なしの `is_checkmate`、詰みだけを終局とする `is_game_over` を実装した。
- 第32回は独立レビューで、王手駒取りのテストが逃げでも通る Important を発見した。玉の逃げを塞いだ王手駒取りと、玉以外の駒による王手駒取りを追加して解消し、再レビューは Critical・Important・Minor なしだった。
- `main` 取り込み後に177件のテスト、CLI起動、差分チェックを成功させ、最後の理解確認の回答と補足を記録した。

## 次に行うこと

1. [第34回引き継ぎ](handover-cli-gameplay.md)に従って現在の状態と一次資料を確認する。
2. CLIの入力形式、合法手適用、エラー時の再入力、終局時の停止範囲について確認問題を一問ずつ進める。
3. 設計と実装計画を本人の明示承認までに確定し、承認前にコードやテストを変更しない。

## 第34回の再開用プロンプト

```text
kaname-shogiの第34回「CLIでの指し手入力と対局進行」を始めてください。
最初にAGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/02-project-direction.md、docs/learning/33-uchi-fuzume.md、docs/knowledge/26-uchi-fuzume.md、kaname_shogi/model.py、kaname_shogi/movegen.py、kaname_shogi/display.py、tests/test_movegen.py、docs/handover-cli-gameplay.mdを読み、git status --short --branchで現在の状態を確認してください。
日本将棋連盟などの一次資料で、CLIの入力と対局進行に関係する着手・終局・反則の規則を確認し、確認問題を一度に一問だけ出して私の回答を待ってください。入力形式、合法手適用、エラー時の再入力、終局時の停止範囲を設計で合意するまでコードやテストを書かないでください。設計承認後にTDDで実装し、独立レビューと全検証を行い、最後の理解確認を一問出して回答と補足を記録してください。コミットメッセージは日本語のConventional Commitにしてください。
```

## 実行場所とコマンド

```sh
cd /Users/oki2a24/kaname-shogi
python3 -m unittest discover -s tests -v
python3 -m kaname_shogi
```

過去の成功記録を今回実行済みとは扱わない。別の作業ツリーを選ぶ場合は、実際のパスと元のmainとの関係を確認する。
