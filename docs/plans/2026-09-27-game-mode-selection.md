# 第41回 対局モードの選択 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: 実装時は `executing-plans` スキルを使用し、各ステップをチェックボックスで追跡する。

**目標:** 三つの対局形式を `run_game` と通常CLI起動時に選べるようにする。

**アーキテクチャ:** `cli.py` の公開 `GameMode` が先後ごとの担当を返し、局面の手番は既存の `Position.side_to_move` が管理する。一つの対局ループが、担当に応じて既存の人間入力または弱い自動手を実行する。

**技術スタック:** Python標準ライブラリ、`unittest`、既存の `GameRecord`、`legal_moves`、`choose_weak_move`。

**仕様 (Spec):** [設計書](2026-09-27-game-mode-selection-design.md)

**グローバル制約 (Global Constraints):**

- 成功手のたびに先後は交互に指す。`GameMode`は担当だけを決める。
- 三形式だけを実装し、`run_game()`の既定値は既存の人間先手・コンピュータ後手にする。
- 投了、EOF、Ctrl-C、詰み、合法手空一覧、メニュー選択は棋譜へ記録しない。
- 一局のコンピュータ手は一つの `random.Random` を共有し、人間手では消費しない。
- コンピュータ対コンピュータは詰み・合法手空一覧・Ctrl-Cだけで停止する。千日手、持将棋、手数上限は追加しない。
- 公開APIのdocstringは日本語で更新し、テスト名は英語、docstringは日本語にする。
- 実装は `codex/game-mode-selection` ブランチで行い、mainへの取り込みは本人承認後だけにする。

---

## ファイル構成

- `kaname_shogi/cli.py`: `GameMode`、担当判定、メニュー、共通進行・中断。
- `kaname_shogi/__main__.py`: メニューから `run_game` への入口。
- `tests/test_cli.py`: 三形式、メニュー、乱数、停止、表示、棋譜。
- `README.md`、`docs/02-project-direction.md`、`docs/next-topics.md`、`docs/resume.md`: 利用方法と到達点。
- `docs/learning/41-game-mode-selection.md`、`docs/knowledge/33-game-mode-selection.md`: 学習と確定知識。

### タスク1: 作業ブランチを作る

- [ ] `git status --short --branch` と `git log -1 --oneline` でmainの状態を記録する。
- [ ] `git switch -c codex/game-mode-selection` を実行し、ブランチ名を確認する。

### タスク2: `GameMode`と人間対人間をTDDで追加する

**変更:** `kaname_shogi/cli.py`、`tests/test_cli.py`

- [ ] 先手・後手の二入力が順番どおり `RecordedMove` となる失敗テストを書く。`run_game(mode=cli.GameMode.HUMAN_VS_HUMAN, ...)` を使い、3回目の入力EOFが記録されないことも確認する。
- [ ] 対象テストを実行し、`GameMode`未定義によるRedを確認する。
- [ ] `GameMode` を公開 `Enum` として実装する。値は `HUMAN_VS_HUMAN`、`HUMAN_VS_COMPUTER`、`COMPUTER_VS_COMPUTER`。`is_human_turn(side: Side) -> bool` は人間担当を返すデータ照会にする。
- [ ] `run_game` に `mode: GameMode = GameMode.HUMAN_VS_COMPUTER` を追加し、固定の先手人間判定を `mode.is_human_turn(position.side_to_move)` に置換する。docstringを更新する。
- [ ] 対象テストと既存の人間対コンピュータ・固定種再現テストを実行し、Greenと既定値互換を確認する。
- [ ] 人間対コンピュータを明示するテストで、先手の人間入力後に後手コンピュータが一手だけ選択・表示・記録し、同じ固定種・入力列では表示と`GameRecord`が再現されることを確認する。これは`mode=GameMode.HUMAN_VS_COMPUTER`を明示した場合と、`mode`を省略した既定値の両方で確認する。

### タスク3: 人間対コンピュータを明示指定でもTDDで保つ

**変更:** `tests/test_cli.py`。必要な場合だけ `kaname_shogi/cli.py`。

- [ ] `mode=GameMode.HUMAN_VS_COMPUTER`を明示して、先手の人間入力後に後手コンピュータが一手だけ選択・表示・記録する失敗テストを書く。同じ初期局面・入力列・固定種で、明示指定と`mode`省略の既定値が同じ`GameRecord.moves`と表示列を返すことも確認する。
- [ ] `GameMode`一般化前にテストを実行し、明示指定を受け取れないRedを確認する。タスク2後はテストがGreenになることを確認し、一般化により人間対コンピュータの担当・乱数・表示・棋譜が変わっていないことを確認する。
- [ ] 複数の人間手に続く複数の後手自動手で、一局につき一つの乱数生成器を再利用する既存テストを明示モードでも実行する。人間手が乱数を消費しないことと、駒打ちも`RecordedDrop`として残ることを確認する。

### タスク4: コンピュータ対コンピュータとCtrl-CをTDDで追加する

**変更:** `kaname_shogi/cli.py`、`tests/test_cli.py`

- [ ] 三回目の `choice` で `KeyboardInterrupt` を送る `random.Random` 派生テストダブルを使い、入力なしで先手・後手が各一手ずつ記録され、Ctrl-Cで勝者なし終了する失敗テストを書く。
- [ ] テストを実行し、自動手経路の `KeyboardInterrupt` が未捕捉でERRORになるRedを確認する。
- [ ] 対局ループ全体でEOFとCtrl-Cを一度だけ捕捉し、「入力を終了しました。」を表示して現在の `GameRecord` を返す最小実装をする。人間の形式・合法性エラー再入力と合法手空一覧の契約を維持する。
- [ ] 人間対人間で乱数を消費しない、コンピュータ対コンピュータの `RecordedDrop`、合法手空一覧で勝者なし、全形式のCtrl-Cを追加テストする。
- [ ] `python3 -m unittest -v tests.test_cli` を実行してGreenを確認する。

### タスク5: 起動メニューをTDDで追加する

**変更:** `kaname_shogi/cli.py`、`kaname_shogi/__main__.py`、`tests/test_cli.py`

- [ ] `choose_game_mode(input_fn=..., output_fn=...)` が番号1・2・3を三形式に対応し、無効番号で「エラー：対局形式を1〜3で選んでください。」を表示して再入力する失敗テストを書く。
- [ ] 対象テストを実行し、関数未定義のRedを確認する。
- [ ] メニュー関数を実装し、`__main__.py`が選択結果を `run_game(mode=...)` へ渡すようにする。入口のEOF/Ctrl-Cは対局を開始せず同じ中断文言で終了する。
- [ ] メニューテストをGreenにし、`printf '2\nmove 7 7 7 6\n' | python3 -m kaname_shogi` で通常CLIを確認する。

### タスク6: 全検証、Refactor確認、独立レビュー

- [ ] `python3 -m unittest discover -s tests -v` と `git diff --check` を実行する。
- [ ] 担当照会・メニュー・共通ループの責務を確認し、ループ複製、局面層への担当情報、将来モードの先取りがなければRefactor不要と判断する。
- [ ] 三形式を独立観点でレビューする。特に人間対コンピュータは、先手人間・後手コンピュータ、既定値互換、固定種再現、一手の表示・記録を確認する。あわせて手番交互性、終了、乱数、`GameRecord`、対象外規則を確認する。Critical/Importantがあれば、失敗テスト、最小修正、全再検証、再レビューを行う。

### タスク7: 記録、コミット、main取り込み

- [ ] 学習記録に第1〜7問の回答、TDDのRed/Green、レビューのCritical・Important・Minor、検証、振り返りを記録する。知識メモに規則とCLI設定の切り分け、三形式、乱数、終了・棋譜、既知制約を記録する。
- [ ] README等をメニュー・三形式・停止範囲・第41回後の現在地へ更新する。
- [ ] 全テスト、通常CLIスモーク、`git diff --check`、状態確認を再実行する。
- [ ] 設計書・計画書・実装・テスト・文書を `feat: 対局モードを選択できるようにする` でコミットする。
- [ ] ブランチ、コミット、レビュー、検証を示してmain取り込みの承認を求める。承認後に `git merge --no-ff codex/game-mode-selection -m "merge: 第41回の対局モード選択を取り込む"` を行い、mainで全検証する。
- [ ] 最後の理解確認を一問だけ出し、回答と補足を学習記録へ追記して日本語Conventional Commitで保存する。その後にだけ次候補を提示する。
