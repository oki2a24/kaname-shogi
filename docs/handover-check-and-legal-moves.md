# 第31回「王手と合法手判定」引き継ぎ

作成日：2026-09-23

## 最終目標

成駒を含む移動候補から、相手玉への利き（王手）を検出し、自分の玉を王手にさらす手を合法手から除外する。打ち歩詰めやCLI入力は、このテーマの範囲を確認してから別テーマへ分ける。

## 完了した事項と背景

- [済] 第30回「成駒の移動」をmainへ取り込んだ。
  - と金・成香・成桂・成銀は金と同じ6方向の候補を返す。
  - 馬は角の長距離移動と縦横1マス、竜は飛車の長距離移動と斜め1マスを返す。
  - `apply_move` は成駒自身の候補で移動し、移動後も成駒を保持する。
  - 成駒を取ったときは `base_piece_type` で基本駒種に戻して持ち駒へ加える。
- [済] 第30回の一次資料確認、6問の理解確認、設計承認、TDD実装、独立レビュー、最後の理解確認、学習記録を完了した。
  - 独立レビューはCritical 0、Important 0、Minor 1。Minorの先手だけの成駒移動テストへ後手ケースを追加して対応した。
- [済] 全139テスト、CLI、`git diff --check`をmain上で再検証した。
- [済] ユーザーは次テーマを「王手と合法手判定」に選択した。

## 物理的状態

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`
- ブランチ：`main`
- Git状態：`main...origin/main [ahead 9]`、作業ツリー変更なし（再開時に必ず確認する）。
- 第30回の主要コミット：`2e35bf1`（馬・竜候補）、`cfdbae2`（成駒局面移動）、`a47c271`（後手テスト）、`a25cccf`（学習記録）、`2c229a6`（最終確認記録）。
- 直近の成功コマンド：`python3 -m unittest discover -s tests -v`（139件成功）、`python3 -m kaname_shogi`、`git diff --check`。
- 現在は第31回のコード・テスト・設計をまだ開始していない。次セッションでは一次資料と既存コードを先に確認する。

## 次に読むファイル

1. `AGENTS.md`
2. `README.md`
3. `docs/resume.md`
4. `docs/next-topics.md`
5. `docs/learning/30-promoted-piece-movement.md`
6. `docs/knowledge/23-promoted-piece-movement.md`
7. `docs/02-project-direction.md`
8. `kaname_shogi/model.py`
9. `kaname_shogi/movegen.py`
10. `kaname_shogi/display.py` と `tests/test_movegen.py`

## 次の具体的なアクション

1. 上記ファイルを読み、`git status --short --branch`を実行する。
2. 日本将棋連盟などの一次資料で、王手・玉の安全・合法手の規則を確認する。
3. 確認問題は一度に一問だけ出し、回答を待つ。
4. 設計承認前にコード・テストを書かない。
5. 実装範囲を「王手の検出」から始めるか、「王手検出＋王手放置の合法手除外」まで含めるかを設計で明確にする。

## 再開用プロンプト

```text
kaname-shogiの第31回「王手と合法手判定」を始めてください。
最初にAGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/learning/30-promoted-piece-movement.md、docs/knowledge/23-promoted-piece-movement.md、docs/02-project-direction.md、kaname_shogi/model.py、kaname_shogi/movegen.py、kaname_shogi/display.py、tests/test_movegen.pyを読み、git status --short --branchで現在の状態を確認してください。
日本将棋連盟などの一次資料で王手・合法手の規則を確認し、確認問題を一度に一問だけ出して私の回答を待ってください。設計承認前にコードやテストを書かないでください。実装後は最後の理解確認を一問行い、回答と補足を記録してから次テーマ候補を示してください。
コミットメッセージは日本語のConventional Commitにしてください。
```
