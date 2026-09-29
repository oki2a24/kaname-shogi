# CLI実行入口のスモークテスト配置を明確にする 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** `tests/test_display.py` にあるCLI実行入口の実プロセステスト1件を専用ファイルへ移し、名前と配置から限定的なE2E／スモークテストだと判別できるようにする。

**アーキテクチャ:** 表示変換を確認する `DisplayTests` と、`python -m kaname_shogi` の外部プロセス境界を確認する `CliEntrypointSmokeTests` を別ファイルへ分離する。対象テストの処理と期待値は変えず、テスト構造と説明だけを責務に合わせる。本体コード、公開動作、テスト件数は変更しない。

**技術スタック:** Python 3.9.6、標準ライブラリ `unittest`・`subprocess`・`pathlib`、Git、Markdown

**仕様 (Spec):** `docs/plans/2026-09-29-cli-entrypoint-smoke-test-placement-design.md`

**グローバル制約 (Global Constraints):**
- 対象は `DisplayTests.test_cli_exits_from_game_mode_menu_on_eof` 1件の配置と、それを囲むファイル名・クラス名・モジュールdocstringに限る。
- テストメソッド名、日本語docstring、`subprocess.run` の引数、作業ディレクトリ計算、入力、文字コード、終了コード・標準出力・標準エラーの期待値を変更しない。
- `kaname_shogi/` の本体コード、公開動作、出力文言、全240件というテスト総数を変更しない。
- 新しい補助関数、fixture、モック、本格的な対局E2Eを追加しない。
- `tests/test_movegen.py` と、その局面スナップショット補助には触れない。
- 計画承認前にテスト移動、既存文書更新、TDD／Refactor作業を開始しない。
- 計画承認後、タスク1へ入る前に `superpowerssuperpowers:test-driven-development` を起動し、既存テストを移すリファクタリングに適用する手順を確認する。
- 実装後はRefactor要否を確認し、独立レビューでCritical・Important・Minorを記録する。CriticalまたはImportantがあれば修正、再検証、再レビューする。
- コミットメッセージは日本語のConventional Commitとする。

---

## ファイル構成

- 作成: `tests/test_cli_entrypoint.py`
  - `python -m kaname_shogi` を実プロセスで起動する限定的なスモークテスト1件だけを保持する。
- 変更: `tests/test_display.py:1-6,65-83`
  - CLI用importと実プロセステストを外し、表示変換テスト3件だけを保持する。
- 作成: `docs/learning/47-cli-entrypoint-smoke-test-placement.md`
  - 合意、実装、検証、Refactor判断、独立レビュー、振り返り、理解確認を記録する。
- 変更: `docs/README.md:35-41,47-89`
  - 現在の作業入口と第47回の索引を現在状態へ合わせる。
- 変更: `docs/roadmap-repository-foundation.md:44-48`
  - テーマ4のうち今回扱う小リファクタリングの進行・完了条件と参照先を記録する。
- 変更: `docs/resume.md:1-48`
  - 作業中は現在のブランチ・完了事項・次の承認ゲート、完了後は次テーマ選定待ちの状態へ更新する。
- 条件付き変更: `docs/next-topics.md`
  - main取り込み後の理解確認と候補再評価を終え、本人が次テーマを選んだ場合だけ、その結果を追記する。

`docs/knowledge/` は変更しない。今回確定するのは将棋規則や本体の実装契約ではなく、テストの配置方針だからである。

### タスク1: 移動前の基準状態を固定する

**ファイル:**
- 読取: `tests/test_display.py:1-83`
- 読取: `kaname_shogi/__main__.py:1-10`
- 記録先: `docs/learning/47-cli-entrypoint-smoke-test-placement.md`（タスク4で作成）

**インターフェース (Interfaces):**
- 消費 (Consumes): `DisplayTests.test_cli_exits_from_game_mode_menu_on_eof` と `python -m kaname_shogi` の現在の公開動作。
- 生産 (Produces): 移動後との比較に使う、対象テスト1件の成功結果と全体のテスト数。

- [x] **ステップ1: 作業ブランチと差分を確認する**

実行:

```sh
git status --short --branch
git log -3 --oneline
git diff --check
```

期待値: ブランチは `codex/cli-entrypoint-smoke-test-placement`。設計・計画コミット以外に未記録の変更がなく、`git diff --check` は出力なし。

- [x] **ステップ2: 対象テストを現在の配置で個別実行する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_display.DisplayTests.test_cli_exits_from_game_mode_menu_on_eof -v
```

期待値: 1件成功し、`Ran 1 test` と `OK` を表示する。2026-09-29の計画作成時にも同じコマンドが1件成功することを確認済み。

- [x] **ステップ3: 全テストの基準件数を確認する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

期待値: 240件成功し、失敗・エラーがない。

### タスク2: CLI実行入口のテストを専用配置へ移す

**ファイル:**
- 作成: `tests/test_cli_entrypoint.py`
- 変更: `tests/test_display.py:1-6,65-83`
- テスト: `tests/test_cli_entrypoint.py`
- テスト: `tests/test_display.py`

**インターフェース (Interfaces):**
- 消費 (Consumes): Pythonモジュール実行 `python -m kaname_shogi`、標準入力EOF、標準出力、標準エラー、プロセス終了コード。
- 生産 (Produces): `CliEntrypointSmokeTests.test_cli_exits_from_game_mode_menu_on_eof`。引数はなく、成功時の戻り値は `None`、副作用は子プロセスの起動だけである。

- [x] **ステップ1: 新しいテストファイルを作成する**

`tests/test_cli_entrypoint.py` を次の内容で作成する。既存メソッドは、クラスのインデント位置を除いてそのまま移す。

```python
"""CLI実行入口の実プロセス境界を限定的なスモークテストで確認する。"""

from pathlib import Path
import subprocess
import sys
import unittest


class CliEntrypointSmokeTests(unittest.TestCase):
    def test_cli_exits_from_game_mode_menu_on_eof(self):
        """CLIは対局形式メニューでEOFなら、対局を始めず終了する。

        実プロセスで起動し、入口のメニュー・入力終了・対局開始前に盤面を表示しない
        ことを確認する。
        """
        result = subprocess.run(
            [sys.executable, "-m", "kaname_shogi"],
            cwd=Path(__file__).resolve().parents[1],
            input="", capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "対局形式を選んでください（1: 人間対人間、2: 人間対コンピュータ、"
            "3: コンピュータ対コンピュータ）:\n"
            "入力を終了しました。\n",
        )
        self.assertEqual(result.stderr, "")
```

- [x] **ステップ2: 表示テストからCLI境界だけを取り除く**

`tests/test_display.py` で次を行う。

```python
"""表示の筋段・所有者・手番・成駒名の誤りを検出する。"""

import unittest
```

- 先頭のモジュールdocstringを上記へ変更する。
- `from pathlib import Path`、`import subprocess`、`import sys` を削除する。
- `DisplayTests.test_cli_exits_from_game_mode_menu_on_eof` 全体を削除する。
- `EXPECTED` と残る3テストは変更しない。

- [x] **ステップ3: 新しい配置の対象テストを個別実行する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli_entrypoint.CliEntrypointSmokeTests.test_cli_exits_from_game_mode_menu_on_eof -v
```

期待値: 1件成功し、移動前と同じ日本語docstring、`Ran 1 test`、`OK` を表示する。

- [x] **ステップ4: 表示テストだけを実行する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_display.DisplayTests -v
```

期待値: 表示テスト3件が成功し、CLI実行入口テストはこのクラスに現れない。

- [x] **ステップ5: 移動前後の意味差分を確認する**

実行:

```sh
git diff --word-diff=plain -- tests/test_display.py
git diff --no-index --word-diff=plain /dev/null tests/test_cli_entrypoint.py
git diff --exit-code -- kaname_shogi
```

期待値: 1件のテスト本文は新ファイルへ移り、変更はファイル・クラス・モジュールdocstring・importの配置だけである。未追跡の新規ファイルを表示する2番目のコマンドは差分があるため終了コード1、本体コードを確認する3番目のコマンドは出力なし、終了コード0。

### タスク3: 全検証、Refactor判断、独立レビューを行う

**ファイル:**
- 検査: `tests/test_cli_entrypoint.py`
- 検査: `tests/test_display.py`
- 不変確認: `kaname_shogi/`
- 記録先: `docs/learning/47-cli-entrypoint-smoke-test-placement.md`（タスク4で作成）

**インターフェース (Interfaces):**
- 消費 (Consumes): タスク2のテスト構造差分。
- 生産 (Produces): 全240件の成功結果、Refactor不要または追加変更の判断、Critical・Important・Minorの独立レビュー結論。

- [x] **ステップ1: 全テストを実行する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

期待値: 240件成功し、失敗・エラーがない。`CliEntrypointSmokeTests` の1件と `DisplayTests` の3件が別クラスとして表示される。

- [x] **ステップ2: Refactorの要否を確認する**

確認事項:

- 新規ファイルが1件の実プロセステストだけを保持している。
- `test_display.py` が表示責務だけを保持している。
- 対象テストを共通化する新しい抽象が増えていない。
- 本体コード、公開動作、テスト件数が変わっていない。

期待値: 設計どおりの最小移動なら追加Refactorは不要。必要と判断した場合は、理由と変更範囲を本人へ提示し、承認された範囲以外へ広げない。

- [x] **ステップ3: 独立レビューを依頼する**

`superpowerssuperpowers:requesting-code-review` を使い、設計仕様、実装計画、`main` との差分、タスク1・2の検証結果を渡す。レビュー対象はテスト配置と振る舞い不変性であり、次をCritical・Important・Minorで判定してもらう。

- 対象テストの確認内容が移動前後で変わっていないか。
- ファイル名・クラス名・テスト名からCLI実行入口の限定的なスモークテストだと分かるか。
- 表示テストに不要なCLI用importや説明が残っていないか。
- 本体コードや対象外テストに変更がないか。

- [x] **ステップ4: 指摘へ対応する**

CriticalまたはImportantがある場合は、その原因に限定して修正し、タスク2の個別テスト、タスク3の全テスト、差分検査を再実行して再レビューを依頼する。Minorは、学習目的・YAGNI・今回の範囲に照らして対応または見送り理由を決める。

期待値: 最終レビューでCritical 0件、Important 0件。Minorの件数、内容、対応または見送り理由が確定している。

### タスク4: 実施内容と現在状態を文書へ記録する

**ファイル:**
- 作成: `docs/learning/47-cli-entrypoint-smoke-test-placement.md`
- 変更: `docs/README.md`
- 変更: `docs/roadmap-repository-foundation.md`
- 変更: `docs/resume.md`

**インターフェース (Interfaces):**
- 消費 (Consumes): 承認済み設計、実装計画、タスク1〜3の実績、独立レビュー結果。
- 生産 (Produces): 第47回の学習・実施記録と、作業ブランチ上の現在状態を指す文書入口。

- [x] **ステップ1: 第47回学習記録を作成する**

`docs/learning/47-cli-entrypoint-smoke-test-placement.md` に次の見出しと確定した実績を書く。

```markdown
# 第47回：CLI実行入口のスモークテスト配置を明確にする

## 目的
## 開始時の状態と確認資料
## 設計で合意したこと
## 移動前の基準確認
## 実装した変更
## Greenの確認
## Refactorの要否
## 独立レビュー
## 検証
## 振り返り
## 最後の理解確認
## main取り込みと取り込み先検証
## 未解決事項
```

実行していない検証、未回答の理解確認、未承認のmain取り込みを完了扱いしない。理解確認欄には問題だけを用意し、本人の回答前に正解として記録しない。

- [x] **ステップ2: 文書索引に第47回を追加する**

`docs/README.md` の現在の作業入口を実装済み・レビュー済み・main取り込み待ちの状態へ合わせ、テーマ表へ次の対応を追加する。

```text
CLI実行入口のスモークテスト配置を明確にする（第47回）
学習記録: learning/47-cli-entrypoint-smoke-test-placement.md
設計仕様: plans/2026-09-29-cli-entrypoint-smoke-test-placement-design.md
実装計画: plans/2026-09-29-cli-entrypoint-smoke-test-placement.md
引き継ぎ: handover-cli-entrypoint-smoke-test-placement.md
```

確定知識は追加しないため、該当列は `—` とする。

- [x] **ステップ3: ロードマップと再開案内を更新する**

`docs/roadmap-repository-foundation.md` のテーマ4へ、設計・計画・実装・検証・レビューの現在状態と3文書へのリンクを追記する。この時点では、main取り込みと理解確認が未完了ならテーマ4全体を完了扱いしない。

`docs/resume.md` は、ブランチ名、現在HEAD、完了した検証、独立レビュー結果、未実施のmain取り込み・理解確認、再開時に読む設計・計画・学習記録を現在値として記す。

- [x] **ステップ4: 文書と差分を検証する**

更新文書の相対Markdownリンクを、次の一時スクリプトで検査する。

```sh
python3 - <<'PY'
import re
from pathlib import Path

sources = [
    Path("docs/README.md"),
    Path("docs/resume.md"),
    Path("docs/roadmap-repository-foundation.md"),
    Path("docs/learning/47-cli-entrypoint-smoke-test-placement.md"),
    Path("docs/plans/2026-09-29-cli-entrypoint-smoke-test-placement-design.md"),
    Path("docs/plans/2026-09-29-cli-entrypoint-smoke-test-placement.md"),
]
missing = []
checked_count = 0
for source in sources:
    targets = re.findall(r"(?<!!)\[[^]]+\]\(([^)]+)\)",
                         source.read_text(encoding="utf-8"))
    checked_count += len(targets)
    for target in targets:
        path_text = target.split("#", 1)[0]
        if not path_text or "://" in path_text or path_text.startswith("mailto:"):
            continue
        resolved = (source.parent / path_text).resolve()
        if not resolved.exists():
            missing.append(f"{source}: {target}")
if missing:
    raise SystemExit("\n".join(missing))
print(f"相対リンク{checked_count}件を検査しました")
PY
```

期待値: 不足リンクを表示せず、検査件数を表示して終了コード0。

続けて次を実行する。

実行:

```sh
git diff --check
git diff --exit-code main...HEAD -- kaname_shogi
git diff --exit-code -- kaname_shogi
git status --short --branch
```

期待値: 書式エラーなし、本体コード差分なし、相対リンクの不足なし。差分は承認済み設計、計画、テスト配置、学習記録、索引、ロードマップ、再開案内に限定される。

- [x] **ステップ5: テーマ変更をコミットする**

実行:

```sh
git add tests/test_display.py tests/test_cli_entrypoint.py docs/learning/47-cli-entrypoint-smoke-test-placement.md docs/README.md docs/roadmap-repository-foundation.md docs/resume.md
git diff --cached --check
git commit -m "test: CLI入口スモークテストを専用配置へ移す"
```

期待値: 日本語のConventional Commitが1件作成され、作業ツリーがクリーンになる。

### タスク5: main取り込み、理解確認、次テーマ選定へ引き渡す

**ファイル:**
- 更新: `docs/learning/47-cli-entrypoint-smoke-test-placement.md`
- 更新: `docs/roadmap-repository-foundation.md`
- 更新: `docs/README.md`
- 更新: `docs/resume.md`
- 条件付き更新: `docs/next-topics.md`

**インターフェース (Interfaces):**
- 消費 (Consumes): レビュー・検証済みの作業ブランチと本人のmain取り込み承認、最後の理解確認への本人の回答。
- 生産 (Produces): main上で検証済みの完了テーマ、回答と補足を含む第47回記録、本人が選ぶ次テーマへの入口。

- [ ] **ステップ1: main取り込みの承認を待つ**

作業ブランチのコミット、検証結果、独立レビュー結果、mainとの差分を提示し、本人が取り込み方法を明示的に承認するまで停止する。

- [ ] **ステップ2: 承認された方法でmainへ取り込む**

既定案は、リモート更新と分岐元を確認したうえでのローカルfast-forwardである。実行直前に現在の `main` とリモート差分を再確認し、状態が変わっていれば停止して本人へ報告する。

- [ ] **ステップ3: 取り込み先で再検証する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli_entrypoint.CliEntrypointSmokeTests.test_cli_exits_from_game_mode_menu_on_eof -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_display.DisplayTests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
git status --short --branch
```

更新文書の相対Markdownリンクは次でも再検査する。

```sh
python3 - <<'PY'
import re
from pathlib import Path

sources = [
    Path("docs/README.md"),
    Path("docs/resume.md"),
    Path("docs/roadmap-repository-foundation.md"),
    Path("docs/learning/47-cli-entrypoint-smoke-test-placement.md"),
    Path("docs/plans/2026-09-29-cli-entrypoint-smoke-test-placement-design.md"),
    Path("docs/plans/2026-09-29-cli-entrypoint-smoke-test-placement.md"),
]
missing = []
checked_count = 0
for source in sources:
    targets = re.findall(r"(?<!!)\[[^]]+\]\(([^)]+)\)",
                         source.read_text(encoding="utf-8"))
    checked_count += len(targets)
    for target in targets:
        path_text = target.split("#", 1)[0]
        if not path_text or "://" in path_text or path_text.startswith("mailto:"):
            continue
        resolved = (source.parent / path_text).resolve()
        if not resolved.exists():
            missing.append(f"{source}: {target}")
if missing:
    raise SystemExit("\n".join(missing))
print(f"相対リンク{checked_count}件を検査しました")
PY
```

期待値: 対象1件、表示3件、全240件が成功し、リンク・書式に問題がなく、取り込み直後の作業ツリーがクリーンである。

- [ ] **ステップ4: 最後の理解確認を一問だけ出す**

次を問い、本人の回答を待つ。

```text
今回、テストメソッドの内容を変えず、ファイル名とクラス名を変えるだけで保守性が上がるのはなぜでしょうか。
```

回答前に補足や正解を記録しない。

- [ ] **ステップ5: 回答、補足、完了状態を記録する**

本人の回答とアシスタントの補足を区別して第47回学習記録へ追記する。ロードマップ、文書索引、再開案内を、main取り込み・取り込み先検証・理解確認まで完了した現在状態へ更新する。

- [ ] **ステップ6: 次テーマ候補を再評価する**

`docs/next-topics.md`、README、`docs/02-project-direction.md` を見直し、小さい順の候補と推薦理由を本人へ示す。既に予定されている「`test_movegen.py` の局面スナップショット補助を一つにする」も現在の状態に照らして再評価し、本人が次テーマを選ぶまで開始しない。

- [ ] **ステップ7: 最終記録をコミットする**

本人の回答と次テーマ選定に応じて更新した文書だけをステージし、リンク・書式を再検査して、次の日本語Conventional Commitで記録する。

```sh
git commit -m "docs: 第47回の理解確認と完了を記録する"
```

新しいセッションで次テーマを始めることを本人が選んだ場合は、その時点で `superpowerssuperpowers:session-handoff` を使い、別途引き継ぎ文書と再開用プロンプトを作成する。引き継ぎ文書は、完了記録とは分けた日本語Conventional Commitで記録する。

## 実行時の停止条件

- 実装計画の明示的な承認が得られていない。
- 対象テストの処理または期待値を変える必要が生じた。
- `kaname_shogi/` の本体コード変更が必要になった。
- 全テスト数が240件から変わった理由を説明できない。
- CriticalまたはImportantのレビュー指摘が未解消である。
- mainまたはリモートが設計開始時から予期せず更新されている。
- 次テーマを始めるための本人の選定または新セッション移行の意思が未確認である。
