# 第37回「棋譜・局面のファイル保存」引き継ぎ

## 最終目標

第36回でメモリ上に保持できるようになった `GameRecord`（棋譜・局面の記録）を、プログラム終了後にも残せるファイルとして保存し、読み込んで局面・手順を再現できるようにする。

ただし、ファイル形式、保存対象、読込エラー時の扱い、CLIからの操作、SFEN・USIとの関係は未決定である。次セッションで一次資料を確認し、確認問題を一問ずつ行ってから設計合意する。

## 完了したことと背景

第36回「棋譜・局面の保存」は完了している。`GameRecord` は開始局面、成功した盤上移動・駒打ちの履歴、現在局面をメモリ上で保持し、`position_at(move_count)` で任意の手数直後の局面を再現する。CLIは対局終了時にこの記録を返す。

最後の理解確認では、開始局面と成功手の履歴を保存する理由を「棋譜として再現できる様にするため」と回答した。今回のテーマは、その再現可能な記録をプロセス終了後にも扱えるようにする、最小の次の段階として選定した。SFEN・USI・時間記録は第36回では対象外であり、今回も先取りしない。

## 物理的な状態

- 作業ディレクトリ: `/Users/oki2a24/kaname-shogi`
- 取り込み先: `main`
- 引き継ぎ作成前の状態: `## main...origin/main [ahead 17]`、作業ツリーはクリーン
- 直近の第36回完了コミット: `ffd706b docs: 第36回の理解確認を記録する`
- 引き継ぎ文書のコミット後は ahead 数が変わるため、再開時には必ず実際の状態を確認する。

直近の検証結果（第36回を `main` へ取り込んだ後）:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
199 tests passed

printf 'move 7 7 7 6\nresign\n' | PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi
```

後者では初期局面、`7六`、`後手が投了しました。先手の勝ちです。` が表示された。`git diff --check` も成功している。

## 再開時に読むもの

次セッションの最初に、以下を読み、現在状態を確認する。

1. `AGENTS.md`
2. `README.md`
3. `docs/resume.md`
4. `docs/next-topics.md`
5. `docs/02-project-direction.md`
6. `docs/learning/36-game-record-and-position-save.md`
7. `docs/knowledge/29-game-record-and-position-save.md`
8. `docs/handover-game-record-file-save.md`
9. `kaname_shogi/game_record.py`
10. `kaname_shogi/cli.py`
11. `kaname_shogi/model.py`
12. `tests/test_game_record.py`
13. `tests/test_cli.py`

続けて、`git status --short --branch` を実行する。過去の記録にある状態・テスト結果を現在と同一と決めつけない。

## 次に行うこと

1. 日本将棋連盟などの一次資料で、棋譜・対局記録に関係する規則を確認する。
2. ファイル形式、保存対象、保存・読込の時機、エラー時の扱い、CLIとの関係、SFEN・USIの扱いを、確認問題として一度に一問ずつ出し、本人の回答を待って合意する。
3. 合意した対象範囲・表現・確認方法を設計書または実装計画に記録し、本人の設計承認・仕様書承認を待つ。
4. 承認後にのみ、作業用ブランチでTDD（実際の振る舞いのRed、最小のGreen、Refactor要否確認）を行う。
5. 独立レビュー、全検証、学習記録・知識メモ、本人承認後の `main` 取り込みと取り込み先での検証を行う。
6. 最後に理解確認を一問だけ出し、回答を待つ。

## 再開用プロンプト

新しいセッションで、次の文をそのまま入力する。

```text
kaname-shogiの第37回「棋譜・局面のファイル保存」を新しいセッションで始めてください。最初にAGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/02-project-direction.md、docs/learning/36-game-record-and-position-save.md、docs/knowledge/29-game-record-and-position-save.md、docs/handover-game-record-file-save.md、kaname_shogi/game_record.py、kaname_shogi/cli.py、kaname_shogi/model.py、tests/test_game_record.py、tests/test_cli.pyを読み、git status --short --branchで現在の状態を確認してください。日本将棋連盟などの一次資料で棋譜・記録に関係する規則を確認し、ファイル形式、保存対象、保存・読込の時機、エラー時の扱い、CLIとの関係、SFEN/USIの扱いを、確認問題として一度に一問ずつ出して私の回答を待ちながら合意してください。設計合意と設計承認までコードやテストを書かないでください。承認後にTDD、独立レビュー、全検証、学習記録、mainへの取り込みを行い、最後に理解確認を一問だけ出してください。コミットメッセージは日本語のConventional Commitにしてください。
```
