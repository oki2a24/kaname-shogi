# 学習・開発の再開案内

第36回「棋譜・局面の保存」は実装・検証・独立レビュー・main取り込み・最後の理解確認まで完了した。次テーマとして第37回「棋譜・局面のファイル保存」を選定し、新しいセッションで始める準備を完了した。

## テーマ間のセッション再開手順

次テーマを選んだら、アシスタントが引き継ぎ文書とこのファイルに再開用プロンプトを記録する。その後、人間が再開用プロンプトを新しいセッションへ入力する。入力を受け取る前に、アシスタントは次テーマの一次資料確認・確認問題・設計・実装を開始しない。人間の入力を起点に、現在のGit状態と記録を確認してから次テーマを始める。

実装計画を文書として作成・更新した場合も、内容を提示して本人の明示承認を待つ。承認前にTDD、コード・テスト変更、実装を開始しない。

最終整理：2026-09-23。恒常的な運用方針はルートのAGENTS.mdを参照する。現在はmainで第36回の実装・レビュー・検証・取り込み・理解確認を完了している。第37回のファイル形式・保存対象・読込時の扱いは未決定であり、新しいセッションで一次資料を確認し、確認問題を一問ずつ行って設計合意してから実装する。

## 現在の到達点

玉・歩・金・銀・桂・香・飛車・角について、盤上の駒の所有者に応じた移動先候補を計算できる。`PieceType` は盤上14種、`BasicPieceType` は持ち駒8種を表し、`Piece` は不変値である。`Position` は盤面、手番、先手・後手の持ち駒を持ち、`Board.copy()`・`Hand.copy()`・`Position.copy()` は試し指し用に独立複製を返す。

`apply_move(position, source, destination, *, promote=False)` は、手番の駒だけを既存候補へ移動できる。成り・強制成り・駒取りを扱い、相手玉を取る操作を拒否する。`apply_drop(position, piece_type, destination)` は、持ち駒を空マスへ打ち、玉の指定、持ち駒不足、二歩、行き所のない歩・香・桂、自玉の王手放置を拒否する。いずれも失敗時に盤面・持ち駒・手番を変更しない。

`is_in_check(board, side)` は指定側の玉への相手の利きを読み取る。`has_legal_move(position)` は盤上移動、不成・成り、玉以外の持ち駒打ちを複製局面で試し、現在実装済みの規則で合法手があるかを返す。`is_checkmate(position)` は手番側の玉が盤上にあり、王手を受け、合法手がないときだけ真を返す。`is_game_over(position)` は今回、詰みだけを終局とする。

`GameRecord` は開始局面、成功した `move` / `drop` の履歴、現在局面を保持する。`position_at` は開始局面から任意手数を再適用し、公開局面は独立複製を返す。CLIは詰み・投了・EOF・Ctrl-Cで対局記録を返す。ファイル保存、千日手、持将棋、入玉、時間切れ、反則勝敗、評価、探索、USI/SFENは未実装である。

## 直近までの記録

- 第31回で王手判定と、盤上移動・駒打ちの自玉安全確認を実装した。
- 第32回で全候補を複製局面に適用する `has_legal_move`、王手かつ合法手なしの `is_checkmate`、詰みだけを終局とする `is_game_over` を実装した。
- 第32回は独立レビューで、王手駒取りのテストが逃げでも通る Important を発見した。玉の逃げを塞いだ王手駒取りと、玉以外の駒による王手駒取りを追加して解消し、再レビューは Critical・Important・Minor なしだった。
- `main` 取り込み後に186件のテスト、CLI起動、複数手の標準入力による人間同士のCLI対局確認、差分チェックを成功させ、最後の理解確認の回答と補足を記録した。
- 第36回で対局記録と任意手数の局面再現を追加し、全199件のテスト、CLIスモーク、差分チェック、独立レビューを成功させた。

## 次に行うこと

1. `docs/handover-game-record-file-save.md` の再開手順に従い、現在の状態を確認する。
2. 第37回の一次資料確認と確認問題を開始する。設計承認前にはコード・テストを変更しない。

## 第37回の再開用プロンプト

```text
kaname-shogiの第37回「棋譜・局面のファイル保存」を新しいセッションで始めてください。最初にAGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/02-project-direction.md、docs/learning/36-game-record-and-position-save.md、docs/knowledge/29-game-record-and-position-save.md、docs/handover-game-record-file-save.md、kaname_shogi/game_record.py、kaname_shogi/cli.py、kaname_shogi/model.py、tests/test_game_record.py、tests/test_cli.pyを読み、git status --short --branchで現在の状態を確認してください。日本将棋連盟などの一次資料で棋譜・記録に関係する規則を確認し、ファイル形式、保存対象、保存・読込の時機、エラー時の扱い、CLIとの関係、SFEN/USIの扱いを、確認問題として一度に一問ずつ出して私の回答を待ちながら合意してください。設計合意と設計承認までコードやテストを書かないでください。承認後にTDD、独立レビュー、全検証、学習記録、mainへの取り込みを行い、最後に理解確認を一問だけ出してください。コミットメッセージは日本語のConventional Commitにしてください。
```

## 第36回で参照した再開用プロンプト（履歴）

```text
kaname-shogiの第36回「棋譜・局面の保存」を新しいセッションで始めてください。最初にAGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/02-project-direction.md、docs/learning/35-game-end-reasons.md、docs/knowledge/28-game-end-reasons.md、docs/handover-game-record-and-position-save.md、kaname_shogi/cli.py、kaname_shogi/model.py、kaname_shogi/movegen.py、tests/test_cli.pyを読み、git status --short --branchで現在の状態を確認してください。日本将棋連盟などの一次資料で棋譜・記録に関係する規則を確認し、保存対象、保存時機、再現範囲、CLIとの関係、SFEN/USIの扱いを、確認問題として一度に一問ずつ出して私の回答を待ちながら合意してください。設計合意と設計承認までコードやテストを書かないでください。承認後にTDD、独立レビュー、全検証、学習記録、mainへの取り込みを行い、最後に理解確認を一問だけ出してください。コミットメッセージは日本語のConventional Commitにしてください。
```

## 実行場所とコマンド

```sh
cd /Users/oki2a24/kaname-shogi
python3 -m unittest discover -s tests -v
python3 -m kaname_shogi
```

過去の成功記録を今回実行済みとは扱わない。別の作業ツリーを選ぶ場合は、実際のパスと元のmainとの関係を確認する。
