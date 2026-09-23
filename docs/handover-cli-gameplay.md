# 🔄 Session Handoff: CLIでの指し手入力と対局進行

## 🎯 最終目標

- CLIから筋・段などの指し手を入力し、現在局面へ合法手を適用して表示する。
- 詰みや既存の終局条件に達したら入力を停止する、最小の対局進行を作る。
- 入力形式、エラー時の再入力、終局時の表示と停止範囲を学びながら合意し、TDDで実装する。

## ✅ 完了した事項と意思決定の背景

- [済] 第33回「打ち歩詰め」を完了した。
  - **Why:** 第32回で詰み判定が使えるようになったため、既存の駒打ちへ持ち歩限定の反則判定を追加した。
  - `apply_drop` は持ち歩による解除不能な王手だけを拒否し、打ち歩詰めでない歩打ち、歩以外の駒打ち、盤上の歩の移動、玉なし部分局面は既存契約どおり扱う。
  - 公開APIを変えず、内部の `check_uchi_fuzume` フラグで、打ち歩詰め確認の再入だけを無効にした。二歩、行き所のない駒、自玉の王手放置は応手探索でも有効に保つ。
- [済] 設計・実装・独立レビュー・文書化を完了した。
  - 独立レビューは最終的にCritical・Important・Minorとも0件だった。
- [済] `main` へローカルマージし、取り込み先で検証した。

## 🚧 現在の物理的状態

- **作業ディレクトリ:** `/Users/oki2a24/kaname-shogi`
- **ブランチ:** `main`
- **Git状態:** `main...origin/main [ahead 19]`。未追跡の `.antigravity/` は計画ツール生成物であり、今回の成果物として追加しない。
- **直近コミット:** `75181c9 docs: 次回テーマを対局進行へ更新する`
- **直近の成功コマンド:** `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q`（177件成功）、`python3 -m kaname_shogi`、`git diff --check`
- **実装開始前に読むファイル:** `AGENTS.md`、`README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/02-project-direction.md`、`docs/learning/33-uchi-fuzume.md`、`docs/knowledge/26-uchi-fuzume.md`、`kaname_shogi/model.py`、`kaname_shogi/movegen.py`、`kaname_shogi/display.py`、`tests/test_movegen.py`
- **未決定:** CLIの入力表現、エラー時の再入力方針、入力できる手の範囲、終局表示、EOF・Ctrl-Cの扱い。先取りして決めない。

## 📝 次の具体的なアクション

1. 上記ファイルを読み、`git status --short --branch` と現在のテストを確認する。
2. 日本将棋連盟などの一次資料で、対局の着手・終局・反則に関係するCLI設計上の事実を確認する。
3. 確認問題を一問ずつ出し、本人の回答を待つ。
4. 入力形式、合法手適用、エラー再入力、終局停止の対象範囲を設計書と実装計画にまとめ、本人の明示承認を待つ。
5. 承認後にTDDでテストを先に追加し、Red、最小実装、Green、Refactor確認、独立レビュー、全検証を行う。

## 💬 再開用プロンプト

```text
kaname-shogiの第34回「CLIでの指し手入力と対局進行」を始めてください。
最初にAGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/02-project-direction.md、docs/learning/33-uchi-fuzume.md、docs/knowledge/26-uchi-fuzume.md、kaname_shogi/model.py、kaname_shogi/movegen.py、kaname_shogi/display.py、tests/test_movegen.py、docs/handover-cli-gameplay.mdを読み、git status --short --branchで現在の状態を確認してください。
日本将棋連盟などの一次資料で、CLIの入力と対局進行に関係する着手・終局・反則の規則を確認し、確認問題を一度に一問だけ出して私の回答を待ってください。入力形式、合法手適用、エラー時の再入力、終局時の停止範囲を設計で合意するまでコードやテストを書かないでください。設計承認後にTDDで実装し、独立レビューと全検証を行い、最後の理解確認を一問出して回答と補足を記録してください。コミットメッセージは日本語のConventional Commitにしてください。
```
