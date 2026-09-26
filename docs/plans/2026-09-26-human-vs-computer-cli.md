# 第39回：人間対コンピュータのCLI進行 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 既定CLIを、人間が先手、弱いコンピュータが後手を担当する一局進行へ変更する。

**アーキテクチャ:** `cli.run_game` は担当手番の非公開境界で人間入力と自動手を分ける。コンピュータは既存の `legal_moves` と `choose_weak_move` を使い、選んだ手を既存の `GameRecord` 経由で適用する。通常実行では一局に一個だけ乱数生成器を作り、テストでは注入する。

**技術スタック:** Python 3.9.6以上、Python標準ライブラリ（`random`、`unittest`、`unittest.mock`）。

**仕様 (Spec):** `docs/plans/2026-09-26-human-vs-computer-cli-design.md`

**グローバル制約 (Global Constraints):**

- 説明・学習記録・知識メモは日本語で書く。
- 公開インターフェースのdocstringには引数・戻り値・副作用・前提条件と設計理由を記録する。
- テストメソッド名は英語とし、日本語docstringで振る舞いと背景を説明する。
- 人間は先手、コンピュータは後手を担当し、`python3 -m kaname_shogi` はこの既定で開始する。
- 乱数生成器は一局につき一個だけ使用し、テストでは固定種の `random.Random` を注入する。
- `GameRecord` とJSON保存形式へ担当者情報・終局理由を追加しない。成功した盤上移動・駒打ちだけを記録する。
- `None` は選択不能だけを表し、投了・勝敗とは解釈しない。EOF/Ctrl-Cは勝敗にしない入力中断とする。
- 千日手、持将棋、入玉、時間、反則勝敗、手合い選択用のCLI引数、対局者クラスは追加しない。

---

## 変更対象

| ファイル | 責務 |
| --- | --- |
| `kaname_shogi/cli.py` | 担当判定、自動手の表示・適用、注入可能な一局用乱数生成器、人間・コンピュータの交互進行。 |
| `tests/test_cli.py` | 自動手、表示順、乱数再現性、履歴、終局・中断の振る舞い。 |
| `README.md` | 人間対コンピュータの実行方法・入力・表示・未実装範囲。 |
| `docs/learning/39-human-vs-computer-cli.md` | 合意、TDD、Refactor、レビュー、検証、理解確認の実測記録。 |
| `docs/knowledge/32-human-vs-computer-cli.md` | 確定したCLI進行の参照メモ。 |
| `docs/02-project-direction.md`、`docs/next-topics.md`、`docs/resume.md` | main取り込み後の到達点と次候補。 |

## タスク1：自動手のCLI進行をTDDで追加する

**ファイル:**

- 変更: `tests/test_cli.py:54-286`
- 変更: `kaname_shogi/cli.py:1-170`

**インターフェース:**

- 消費: `legal_moves(position) -> tuple[Move, ...]`、`choose_weak_move(moves, rng) -> Move | None`、`GameRecord.apply_move`、`GameRecord.apply_drop`。
- 生産: `run_game(*, input_fn=input, output_fn=print, rng: Optional[random.Random] = None) -> GameRecord`。

- [x] **ステップ1: 失敗するテストを追加する**

`tests/test_cli.py`に、自動手・表示順・固定種の再現性・盤上移動と駒打ちの記録・投了/EOF/Ctrl-C・合法手空一覧の個別テストを追加する。核となるテストは次の形にする。

```python
def test_human_sente_move_is_followed_by_one_computer_gote_move(self):
    """先手の成功手の後に、後手のコンピュータが一手だけ指す。

    後手入力を要求するまま残る誤りと、同じ側が続けて指す誤りを検出する。
    """
    inputs = ScriptedInput(["move 7 7 7 6"])
    outputs = []
    record = cli.run_game(input_fn=inputs, output_fn=outputs.append,
                          rng=random.Random(20260926))
    self.assertEqual(inputs.calls, 2)
    self.assertEqual(len(record.moves), 2)
    self.assertEqual(record.moves[0], RecordedMove(Square(7, 7),
                                                    Square(7, 6), False))
    self.assertEqual(record.current_position.side_to_move, Side.SENTE)
    self.assertTrue(any(line.startswith("後手の指し手: ") for line in outputs))
```

- [x] **ステップ2: Redを振る舞いとして確認する**

実行: `python3 -m unittest tests.test_cli -v`

期待値: 追加テストは、まだ`run_game`に`rng`引数と自動手分岐がないためFAILする。読み込みエラーだけでなく、期待する進行または出力との差を確認する。

- [x] **ステップ3: 最小実装を追加する**

`cli.py`へ`random`、`Optional`、`BoardMove`、`DropMove`、`Move`、`legal_moves`、`choose_weak_move`を読み込む。`rng`未指定時だけ`run_game`開始時に一個生成する。担当判定を一つの非公開操作に置く。コンピュータ担当では空の合法手一覧を先に処理し、空でなければ一手を表示して適用し、盤面を表示する。

```python
def _apply_selected_move(record: GameRecord, move: Move) -> None:
    if isinstance(move, BoardMove):
        record.apply_move(move.source, move.destination, promote=move.promote)
        return
    record.apply_drop(move.piece_type, move.destination)
```

盤上移動は`move <筋> <段> <筋> <段> [ + ]`、駒打ちは`drop <駒名> <筋> <段>`として`後手の指し手: `の後に適用前表示する。既存の人間入力・例外・再入力経路を維持し、`run_game`のdocstringを更新する。

- [x] **ステップ4: Greenを確認する**

実行: `python3 -m unittest tests.test_cli -v`

期待値: 既存テストと新規テストがすべてPASSする。

- [x] **ステップ5: Refactorの要否を確認する**

盤面表示・終局判定・`GameRecord`適用の重複、担当判定の散在、docstringとの不一致を確認する。変更した場合は対象テストを再実行する。

- [x] **ステップ6: コミットする**

実行: `git add kaname_shogi/cli.py tests/test_cli.py && git commit -m 'feat: 人間対コンピュータのCLI進行を追加'`

## タスク2：案内と学習記録を実測に基づいて更新する

**ファイル:**

- 変更: `README.md:7-110`
- 作成: `docs/learning/39-human-vs-computer-cli.md`
- 作成: `docs/knowledge/32-human-vs-computer-cli.md`

- [x] **ステップ1: 現行案内との差を確認する**

実行: `rg -n '人間同士|人間対コンピュータ|後手の指し手|GameRecord|EOF|Ctrl-C' README.md`

期待値: READMEが人間同士の説明のままであることを確認する。

- [x] **ステップ2: 実測済みの事実だけを文書へ記録する**

READMEを人間先手・コンピュータ後手向けへ更新する。`move`、`drop`、`resign`、表示順、EOF/Ctrl-C、乱数による弱い手、未実装範囲を説明する。学習記録には確認問題ごとの本人回答と補足、実施済みのRed/Green、Refactor、レビュー、検証だけを追記する。知識メモには担当境界、乱数寿命、`None`と終局の分離、記録範囲を記す。

- [x] **ステップ3: 文書の正確性を確認する**

実行: `rg -n '人間対コンピュータ|人間は先手|コンピュータは後手|後手の指し手|勝敗にしない' README.md docs/learning/39-human-vs-computer-cli.md docs/knowledge/32-human-vs-computer-cli.md`

期待値: 実装済みの契約が記録され、未実施事項を完了扱いしていない。

- [ ] **ステップ4: コミットする**

実行: `git add README.md docs/learning/39-human-vs-computer-cli.md docs/knowledge/32-human-vs-computer-cli.md && git commit -m 'docs: 人間対コンピュータCLIの利用方法を記録'`

## タスク3：全検証、独立レビュー、main取り込みを完了する

**ファイル:**

- 変更: `docs/learning/39-human-vs-computer-cli.md`
- 変更: `docs/02-project-direction.md`、`docs/next-topics.md`、`docs/resume.md`

- [x] **ステップ1: 全検証とCLIスモークを実行する**

実行: `python3 -m unittest discover -s tests -v`、`printf 'move 7 7 7 6\\n' | python3 -m kaname_shogi`、`git diff --check`

期待値: 全テストがPASSし、CLIは先手入力後に後手の自動手と次の先手入力案内を表示する。

- [x] **ステップ2: 独立レビューを実施する**

手番交代、乱数の一局単位の寿命、表示順、`None`の誤解釈、`GameRecord`、EOF/Ctrl-C、docstring、既存挙動の回帰を別視点で確認する。Critical・Important・Minorを明示し、CriticalまたはImportantがあれば修正、再検証、再レビューする。結果を学習記録へ追記する。

- [ ] **ステップ3: 実測済みの完了文書をコミットする**

main取り込み前には学習記録へ検証・レビュー結果を追記し、main取り込み後の事実は取り込み・main再検証後に`docs/02-project-direction.md`、`docs/next-topics.md`、`docs/resume.md`へ記録する。

実行: `git add docs/learning/39-human-vs-computer-cli.md docs/02-project-direction.md docs/next-topics.md docs/resume.md && git commit -m 'docs: 第39回の検証結果と次の候補を記録'`

- [ ] **ステップ4: main取り込みの本人承認を求める**

作業ブランチ、コミット、検証結果、独立レビュー、未解決事項を提示する。本人の明示承認前にmainへ取り込まない。

- [ ] **ステップ5: 承認後にmainへ取り込み、再検証する**

実行: `git switch main && git merge --no-ff codex/human-vs-computer-cli && python3 -m unittest discover -s tests -v && git status --short --branch`

期待値: `/Users/oki2a24/kaname-shogi`のmainに変更が取り込まれ、全テストがPASSする。

- [ ] **ステップ6: 最後の理解確認問題を一問だけ出す**

main側の再検証後に、`None`と終局の責務を分けた理由を問う一問だけを出し、本人の回答を待つ。回答と補足は受け取ってから学習記録へ追記し、次テーマの候補はその後にだけ示す。

## 計画の自己レビュー

- 仕様書の担当、起動、乱数、表示、合法手空一覧、投了、EOF/Ctrl-C、`GameRecord`を各タスクへ対応付けた。
- コードTDD、文書、全検証、独立レビュー、本人承認後のmain取り込み、最後の一問を明確に分けた。
- プレースホルダや未定の操作は残していない。全コマンドは`/Users/oki2a24/kaname-shogi`で実行する。
