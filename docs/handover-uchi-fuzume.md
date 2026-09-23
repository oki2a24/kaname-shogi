# 第33回「打ち歩詰め」引き継ぎ

作成日：2026-09-23

## 最終目標

持ち歩を打った直後に相手玉を詰ませる「打ち歩詰め」を反則として拒否する最小実装を、将棋の一次資料に基づいて学び、説明できる形で追加する。歩以外の駒打ち、盤上の歩の移動による詰み、投了・千日手・持将棋・入玉などの終局規則、CLI入力は対象に含めない。

## 次テーマを選んだ理由

- 第32回で `is_checkmate(position)` が「王手を受け、合法手がない」ことを判定できるようになった。打ち歩詰めは、この結果を持ち歩の打ちにだけ結び付ける次の小さな規則である。
- 既存の `apply_drop` は二歩、行き所のない段、自玉の安全を検証済みであり、持ち歩を打つ経路を増やさずに反則を追加できる可能性がある。
- CLI対局進行や終局理由全体を先取りせず、歩を打つ操作の一条件に限定できる。

## 完了した事項と意思決定の背景

- [済] 盤面、持ち駒、局面、先後、14種の盤上駒と8種の持ち駒を表現した。
  - **Why:** 盤上の成駒と持ち駒へ戻る基本駒種を混同せず、各規則の対象を型で分けるためである。
- [済] `apply_move` と `apply_drop` は、複製局面で自玉の安全を確認してから本物の局面を変更する。
  - **Why:** 王手放置や王手へ移動する手を、失敗時に盤面・持ち駒・手番を変えずに拒否するためである。
- [済] `has_legal_move(position)`、`is_checkmate(position)`、`is_game_over(position)` を追加した。
  - **Why:** 打ち歩詰めでは「歩を打った結果、相手番が詰みか」を確認する土台が必要だった。詰みは王手かつ合法手なしに限定し、玉がない部分局面は偽とした。
- [済] 第32回は `main` へマージ済みで、168件の単体テスト、CLI起動、差分チェックを `main` 上で成功させた。
  - **Why:** 次テーマの前に、終局判定の実装・レビュー・理解確認を取り込み先で完結させるプロジェクト方針に従うためである。
- [済] 打ち歩詰めを次テーマに選定した。
  - **Why:** `apply_drop` の未実装規則を一つだけ埋め、詰み判定を実際の反則判定へ使う、依存関係が明確な次の段階だからである。

## 重要な既存仕様と注意点

- `apply_drop(position, piece_type, destination)` は成功時に本物の局面を変更し、手番を交代する。失敗時は `ValueError` を送出し、局面を変更しない。
- `has_legal_move` は `apply_move` と `apply_drop` を使って候補を試す。打ち歩詰めを `apply_drop` に入れる場合、`has_legal_move` からの呼び出しと詰み判定の循環をどう避けるかを設計で明示する必要がある。
- 打ち歩詰めは、持ち歩を打つ手そのものの反則である。盤上の歩が指して詰ませる手、歩以外の駒を打って詰ませる手は今回の禁止対象ではない。
- 現在の詰み判定は教育用の部分局面を扱い、手番側の玉がない局面を `False` とする。打ち歩詰めの試験局面で両方の玉を置くか、部分局面の扱いをどこまで許すかを設計で確認する。
- 第32回で「実装計画の作成後は本人の明示承認を待つ」規則を `AGENTS.md` に追加した。今回も、確認問題、対象範囲、設計承認の前にコード・テストを書かない。

## 現在の物理的状態

- **作業ディレクトリ:** `/Users/oki2a24/kaname-shogi`
- **ブランチ:** `main`
- **Git状態:** この引き継ぎ文書を作る直前は `main...origin/main [ahead 8]`、作業ツリーは変更なし。引き継ぎ文書をコミットした後に、必ず現在の状態を再確認する。
- **直前のHEAD:** `030d107 docs: 第32回の理解確認と次候補を記録する`
- **主要実装:** `kaname_shogi/model.py`、`kaname_shogi/movegen.py`
- **主要テスト:** `tests/test_model.py`、`tests/test_movegen.py`
- **直近の成功コマンド:** `python3 -m unittest discover -s tests`（168件成功）、`python3 -m kaname_shogi`、`git diff --check HEAD^ HEAD`。
- **未検証・未実装:** 第33回の一次資料確認、確認問題、設計、TDD、レビュー、テスト、コードはまだ開始していない。

## 次に読むファイル

1. `AGENTS.md`
2. `README.md`
3. `docs/resume.md`
4. `docs/next-topics.md`
5. `docs/learning/32-checkmate-and-game-end.md`
6. `docs/knowledge/25-checkmate-and-game-end.md`
7. `docs/02-project-direction.md`
8. `kaname_shogi/model.py`
9. `kaname_shogi/movegen.py`
10. `kaname_shogi/display.py`
11. `tests/test_movegen.py`
12. `docs/handover-uchi-fuzume.md`

## 次の具体的なアクション

1. 上記のファイルを読み、`git status --short --branch` で現時点の物理状態を確認する。過去の検証記録を今回の状態と同一視しない。
2. 日本将棋連盟などの一次資料で、打ち歩詰めが禁止される対象と、反則時の扱いを確認する。
3. 確認問題を一度に一問だけ出し、本人の回答を待つ。
4. 対象範囲、`apply_drop` と `is_checkmate` の関係、循環を避ける方法、玉なし部分局面、試験局面の表現を設計で合意する。
5. 設計文書を提示したら、本人の明示承認を待つ。承認前にテスト・コードを書かない。
6. 承認後はTDDのRed → Green → Refactor、独立レビュー、全検証、main取り込み、最後の理解確認の順に進める。

## 再開用プロンプト

```text
kaname-shogiの第33回「打ち歩詰め」を始めてください。
最初にAGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/learning/32-checkmate-and-game-end.md、docs/knowledge/25-checkmate-and-game-end.md、docs/02-project-direction.md、kaname_shogi/model.py、kaname_shogi/movegen.py、kaname_shogi/display.py、tests/test_movegen.py、docs/handover-uchi-fuzume.mdを読み、git status --short --branchで現在の状態を確認してください。
日本将棋連盟などの一次資料で打ち歩詰めの規則を確認し、確認問題を一度に一問だけ出して私の回答を待ってください。設計承認前にコードやテストを書かないでください。打ち歩詰めの対象範囲、`apply_drop`・`has_legal_move`・`is_checkmate` の関係、循環を避ける方法、玉なし部分局面の扱いを設計で合意してからTDDで実装してください。実装後は独立レビューと全検証を行い、最後の理解確認を一問出して回答と補足を記録してください。コミットメッセージは日本語のConventional Commitにしてください。
```
