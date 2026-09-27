# 文書ナビゲーションの最小改善 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** `README.md` を人間向けの簡潔な第一入口にし、`docs/README.md` をテーマ・学習回別の単一索引として新設して、人間とAIが目的に合う文書だけを選んで読めるようにする。

**アーキテクチャ:** ルートの `README.md` は現在の概要・利用方法・主要入口だけを持ち、`docs/README.md` が文書種別の説明、現在進行中の入口、テーマ別の横断索引を一元的に持つ。既存文書の配置と意味は変えず、相対リンクで既存資料を結び、進行中の細かな状態は `docs/resume.md` と現在の実装計画へ委譲する。

**技術スタック:** Markdown、Git、Python 3.9標準ライブラリ（読み取り専用の相対リンク検査）。

**仕様 (Spec):** `docs/plans/2026-09-27-repository-document-navigation-design.md`

**グローバル制約 (Global Constraints):**

- 人間向けの第一入口は `README.md`、詳細文書を選ぶ単一索引は `docs/README.md` とする。AIは `AGENTS.md`、`README.md`、`docs/resume.md`、現在の実装計画、現在のGit状態で再開し、引き継ぎはテーマ開始時点の背景として読む。
- `docs/README.md` は、すべての文書を最初から読む一覧ではなく、現在の使い方、作業再開、確定仕様、判断経緯、設計・実装という目的に合う資料を選ぶ入口とする。
- テーマ別索引はファイル番号ではなくテーマ・学習回を主軸にし、学習記録、知識メモ、設計仕様、実装計画、引き継ぎを横断してたどれるようにする。
- 存在しない文書種別にはリンクを作らず `—` と表示する。
- `docs/design/` は初期設計の履歴、`docs/plans/*-design.md` は現在方式の設計仕様として説明し、今後の設計仕様は後者へ置く。
- 知識メモ番号 `32` の重複は改名せず、題名とテーマで識別する。
- 既存文書の移動・改名・削除、古い内容の意味を変える是正、文書索引の自動生成、コード・テスト・将棋規則・CLI動作・JSON保存形式の変更は行わない。
- READMEから情報を外す前に、同じ役割の情報へ `docs/README.md` から到達できることを確認する。別文書に存在しない情報は機械的に削除しない。
- `docs/resume.md` は現在の再開入口として実際の進行状況へ更新し、現役テーマの引き継ぎ文書はテーマ開始時点の物理状態を残す履歴として変更しない。
- コミットメッセージは日本語のConventional Commitとし、実装・検証・独立レビュー・学習記録がそろうまでテーマの変更をコミットしない。
- 実装は作成済みの `codex/document-navigation` ブランチで行い、本人の明示的承認前にはこの計画書以外を変更しない。

---

## ファイル構成

- 作成: `docs/README.md`
  - 文書の選択方法、文書種別の責務、現在進行中の入口、テーマ・学習回別の横断索引、例外、更新規則を一元管理する。
- 変更: `README.md`
  - プロジェクト概要、現在できることと主な未対応事項、実行方法、CLI操作、テスト、主要文書、名前、ライセンスだけを持つ人間向け入口にする。
- 作成: `docs/learning/44-document-navigation.md`
  - 設計承認、計画承認、実施内容、READMEから外した情報の参照先、検証、独立レビュー、振り返り、最後の理解確認を記録する。
- 変更: `docs/roadmap-repository-foundation.md`
  - 実装開始時にテーマ2を進行中とし、完了時に検証・学習記録・索引への参照を添えて完了へ更新する。
- 変更: `docs/resume.md`
  - 着手前の再開指示を、現在の作業ブランチ、承認済み計画、実施済み事項、未完了手順を確認する再開入口へ更新する。
- 条件付き変更: `docs/next-topics.md`、新しい `docs/handover-<topic>.md`
  - 第44回の最後の理解確認への本人回答後、次テーマが選ばれ、新しいセッションで始める場合だけ更新する。ナビゲーション実装中は変更しない。

変更しないファイル:

- `kaname_shogi/` と `tests/` 以下の全ファイル。
- 既存の `docs/learning/`、`docs/knowledge/`、`docs/design/`、`docs/plans/`、`docs/handover-*.md`。ただし上記で明示したロードマップと、テーマ完了後に条件を満たした再開文書は除く。
- `docs/02-project-direction.md` の古い「未決定事項」など、今回の入口改善と無関係な内容。

## `docs/README.md` の具体的な構成

1. **この索引の使い方**
   - 全文書を順番に読むためではなく、目的に合う最小限の資料を選ぶ入口だと明記する。
2. **目的別の読み方**
   - 現在の使い方: ルート `README.md`。
   - 作業再開: `AGENTS.md`、ルート `README.md`、`docs/resume.md`、現在の実装計画、現在のGit状態。引き継ぎはテーマ開始時点の背景として読む。
   - 現在の確定仕様: 該当する `docs/knowledge/`。
   - 判断経緯: 該当する `docs/learning/`。
   - 実装: 承認済み設計仕様、実装計画、関連コード、関連テスト。
3. **文書種別の役割**
   - 仕様書の「文書種別の責務」と同じ区分で、役割、読み手、読むタイミング、更新契機、現在情報か履歴情報かを表にする。
4. **現在進行中の入口**
   - `resume.md`、現在の実装計画、`roadmap-repository-foundation.md` を現在の入口として示す。
   - `handover-repository-foundation-document-navigation.md` を含む `handover-*.md` は対応テーマ開始時点の情報を残す履歴であり、現在のGit状態や次の行動を示さないと説明する。
5. **テーマ・学習回別索引**
   - 列は「テーマ」「学習記録」「確定知識」「設計仕様」「実装計画」「引き継ぎ」とする。
   - 次のテーマ群をこの順で載せ、各列には実在する関連文書だけを相対リンクで記す。
     1. 将棋の全体像（第1回）
     2. 駒の動きと成り（第2回）
     3. 初期配置と盤上の座標（第3回）
     4. 初期実装の設計と初期配置CLI（第4〜5回）
     5. 歩の移動先候補（第6〜7回）
     6. 金の移動先候補（第8〜9回）
     7. 銀の移動先候補（第10〜11回）
     8. 香の移動先候補（第12〜13回）
     9. 飛車の移動先候補（第14〜15回）
     10. 角の移動先候補（第16〜17回）
     11. 桂馬の移動先候補（第18〜19回）
     12. 玉の移動先候補（第20回）
     13. 空マスへの移動適用（第21回）
     14. 手番更新（第22回）
     15. 手番と駒の所有者（第23回）
     16. 候補内の空マスへの移動（第24回）
     17. 駒取りと持ち駒（第25回）
     18. 持ち駒を打つ（第26回）
     19. 二歩（第27回）
     20. 行き所のない駒（第28回）
     21. 成り・不成（第29回）
     22. 成駒の移動（第30回）
     23. 王手と合法手判定（第31回）
     24. 詰み・終局判定（第32回）
     25. 打ち歩詰め（第33回）
     26. CLIでの指し手入力と対局進行（第34回）
     27. 終局理由の拡張（第35回）
     28. 棋譜・局面のメモリ内保存（第36回）
     29. 棋譜・局面のJSONファイル保存（第37回）
     30. 弱い自動指し手（第38回）
     31. 人間対コンピュータのCLI進行（第39回）
     32. 駒打ち順の保守（第40回）
     33. 対局モードの選択（第41回）
     34. CLIでの明示的な保存・読込（第42回）
     35. 文書構成の棚卸しと入口設計（第43回）
     36. 文書ナビゲーションの最小改善（第44回）
6. **例外と履歴の読み方**
   - `docs/design/` と `docs/plans/*-design.md` の役割差、知識メモ番号 `32` の重複、`docs/superpowers/plans/2026-09-13-initial-position.md` が初期計画の履歴であることを説明する。
7. **更新規則**
   - 各テーマ完了時に該当行とリンクを更新し、進行中の細かな状態は `resume.md` と現在の実装計画に置く。

## `README.md` から外す情報の参照先

| READMEの現行内容 | READMEでの扱い | 索引から到達させる既存資料 |
| --- | --- | --- |
| 第32〜42回の累積的な実装履歴 | 現在できることの短い要約へ統合 | 各回の `docs/learning/32-*.md`〜`42-*.md` と対応する知識メモ |
| `GameRecord.save` / `load` のPython使用例と形式詳細 | CLI利用に必要な短い説明だけ残す | `knowledge/30-game-record-file-save.md`、第37回・第42回の学習・設計・計画 |
| `legal_moves` / `choose_weak_move` のPython使用例 | 現在できることへ要約 | `knowledge/31-weak-move-selection.md`、第38回の学習・設計・計画 |
| 歩・金・銀・桂・香・飛・角のAPI使用例 | 削除し、テーマ別索引へ委譲 | 対応する `knowledge/06`、`08`、`10`、`12`〜`15` と学習・設計・計画 |
| 未分類の長い文書リンク一覧 | 削除し、単一索引へのリンクへ置換 | 新規 `docs/README.md` |
| 公開APIのdocstring方針 | READMEの利用者向け中心責務から外す | `AGENTS.md` と関連する設計・学習記録 |

CLIコマンド、保存・読込の利用制約、テストコマンド、主な未対応事項、名前、ライセンスはREADMEに残す。

### タスク1: 実装開始条件と文書インベントリを固定する

**ファイル:** `docs/roadmap-repository-foundation.md`

**インターフェース (Interfaces):**

- 消費 (Consumes): 承認済み仕様 `docs/plans/2026-09-27-repository-document-navigation-design.md`、本計画、現在のGit状態。
- 生産 (Produces): テーマ2が進行中であることを示すロードマップ状態と、索引へ載せる実在ファイル一覧。

- [x] **ステップ1: 本人の計画承認と作業ブランチを確認する**

実行:

```sh
git status --short --branch
```

期待値: ブランチは `codex/document-navigation`。本計画書以外に未承認の差分がない。本人の明示的承認が会話に記録されている。

- [x] **ステップ2: コード・テストを含む変更前の基準を記録する**

実行:

```sh
git diff --name-only main...HEAD
git status --short
rg --files docs/learning docs/knowledge docs/design docs/plans | sort
```

期待値: 実装開始前の差分と文書インベントリを把握できる。索引では、この時点で実在するファイルだけをリンク対象にする。

- [x] **ステップ3: ロードマップのテーマ2を進行中へ更新する**

`docs/roadmap-repository-foundation.md` のテーマ2見出しを「進行中」にし、開始日 `2026-09-27` と、本計画 `plans/2026-09-27-repository-document-navigation.md` へのリンクを加える。GREEN条件、対象外、テーマ3以降の内容は変えない。

- [x] **ステップ4: 差分を確認する**

実行:

```sh
git diff -- docs/roadmap-repository-foundation.md
git diff --check
```

期待値: テーマ2の状態と計画リンクだけが変わり、空白エラーはない。

### タスク2: テーマ・学習回別の単一索引を作成する

**ファイル:** 作成 `docs/README.md`

**インターフェース (Interfaces):**

- 消費 (Consumes): 仕様の文書種別責務、AI向け選択的読解、実在する既存文書の相対パス。
- 生産 (Produces): ルートREADMEからリンクされる単一索引 `docs/README.md`。目的別入口と36テーマ群の横断リンクを提供する。

- [x] **ステップ1: 索引の骨格と選択的な読み方を書く**

「この索引の使い方」「目的別の読み方」「文書種別の役割」「現在進行中の入口」を、上の具体的な構成どおりに作る。過去のGit状態やテスト件数を現在情報として転記しない。

- [x] **ステップ2: 36テーマ群の横断索引を書く**

各行にテーマ名と学習回を明記し、実在する学習記録、知識メモ、設計仕様、実装計画、引き継ぎだけを相対リンクで記す。対応文書がない列は `—` とし、番号が重複する知識メモは題名で区別する。

- [x] **ステップ3: 例外説明と更新規則を書く**

初期設計と現在方式の設計仕様の配置差、知識メモ番号 `32` の重複、初期計画の保存場所、再開案内と開始時点の引き継ぎの違い、各テーマ完了時の索引更新を明記する。

- [x] **ステップ4: 索引内の相対リンクを検査する**

リポジトリ直下で次を実行する。外部URLとページ内リンクは除外し、Markdownの相対リンク先が実在することを確認する。

```sh
python3 - <<'PY'
import re
from pathlib import Path

sources = [Path("docs/README.md")]
missing = []
for source in sources:
    for target in re.findall(r"(?<!!)\[[^]]+\]\(([^)]+)\)", source.read_text()):
        path_text = target.split("#", 1)[0]
        if not path_text or "://" in path_text or path_text.startswith("mailto:"):
            continue
        resolved = (source.parent / path_text).resolve()
        if not resolved.exists():
            missing.append(f"{source}: {target}")
if missing:
    raise SystemExit("\n".join(missing))
print("docs/README.md: すべての相対リンクが解決しました")
PY
```

期待値: `docs/README.md: すべての相対リンクが解決しました` と表示される。

- [x] **ステップ5: 索引の網羅性を照合する**

実行:

```sh
rg -n '^# ' docs/learning docs/knowledge docs/design docs/plans docs/handover-*.md | sort
rg -n '第([1-9]|[1-3][0-9]|4[0-4])回' docs/README.md
```

期待値: 第1〜44回がテーマ群のいずれかに現れ、既存の知識メモ、設計、計画、引き継ぎの対応先を確認できる。存在しない対応文書へのリンクはない。

### タスク3: READMEを人間向けの簡潔な第一入口へ整理する

**ファイル:** 変更 `README.md`

**インターフェース (Interfaces):**

- 消費 (Consumes): 新規 `docs/README.md`、現在のCLI利用方法、テストコマンド、現在できることと主な未対応事項。
- 生産 (Produces): 初めて訪れた人が目的、実行、CLI操作、テスト、詳細文書へ順に到達できるルート `README.md`。

- [x] **ステップ1: READMEの章立てを仕様どおりに絞る**

章を「プロジェクト概要」「現在できることと主な未対応事項」「実行方法」「CLI操作」「テスト」「文書案内」「名前」「ライセンス」にする。プロジェクトの学習目的と息子と成長を共有する目的は保持する。

- [x] **ステップ2: 現在できることとCLI利用方法を短く統合する**

初期配置、3対局形式、盤上移動、成り、駒取り、駒打ち、王手・詰み・打ち歩詰め、投了、棋譜のメモリ保持、明示的なJSON保存・読込、弱いランダム指し手を要約する。`move`、`drop`、`resign`、`save`、`load` の入力例、パスは空白なしの一語、親ディレクトリ非作成、保存・読込失敗時は同じ手番で再入力する点を残す。

- [x] **ステップ3: 詳細説明を索引へ委譲する**

「READMEから外す情報の参照先」の表に従い、累積履歴、Python API例、未分類リンク一覧を除く。情報を除くたびに、新規索引から対応する既存資料へ到達できることを確認する。

- [x] **ステップ4: 必要最小限の入口リンクを置く**

文書案内には、`docs/README.md`、`docs/01-project-background.md`、`docs/02-project-direction.md`、`docs/resume.md` の4入口だけを置く。個別の学習記録、知識メモ、設計、計画へのリンクは `docs/README.md` へ集約する。

- [x] **ステップ5: README単体の到達性を点検する**

READMEだけを上から読み、実行コマンド、全5種の人間入力、テストコマンド、詳細文書、再開案内へ到達できることを確認する。

実行:

```sh
rg -n 'python3 -m kaname_shogi|move |drop |resign|save |load |python3 -m unittest|docs/README.md|docs/01-project-background.md|docs/02-project-direction.md|docs/resume.md' README.md
```

期待値: 必須の利用情報と4入口がすべて見つかる。個別APIの長い使用例と未分類文書一覧は残っていない。

### タスク4: 変更範囲と全相対リンクを検証する

**ファイル:** `README.md`、`docs/README.md`、`docs/resume.md`、`docs/roadmap-repository-foundation.md`

**インターフェース (Interfaces):**

- 消費 (Consumes): タスク1〜3の文書差分。
- 生産 (Produces): 対象外ファイルの不変性、リンク解決、現在情報と履歴情報の区別を示す検証結果。

- [x] **ステップ1: 変更ファイルが許可範囲内か確認する**

実行:

```sh
git status --short
git diff --name-only
git diff --stat
```

期待値: この時点の変更は計画書、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/roadmap-repository-foundation.md` だけで、`kaname_shogi/` と `tests/` に差分がない。

- [x] **ステップ2: READMEと索引の全相対リンクを検査する**

```sh
python3 - <<'PY'
import re
from pathlib import Path

sources = [Path("README.md"), Path("docs/README.md")]
missing = []
for source in sources:
    for target in re.findall(r"(?<!!)\[[^]]+\]\(([^)]+)\)", source.read_text()):
        path_text = target.split("#", 1)[0]
        if not path_text or "://" in path_text or path_text.startswith("mailto:"):
            continue
        resolved = (source.parent / path_text).resolve()
        if not resolved.exists():
            missing.append(f"{source}: {target}")
if missing:
    raise SystemExit("\n".join(missing))
print("README.md と docs/README.md: すべての相対リンクが解決しました")
PY
```

期待値: すべての相対リンクが解決した旨が表示される。

- [x] **ステップ3: 現在情報と履歴情報の表現を点検する**

`docs/README.md` の現在進行中の入口が `docs/resume.md`、現在の実装計画、ロードマップを指すこと、すべての引き継ぎをテーマ開始時点の情報と説明していること、過去のHEAD・先行コミット数・テスト件数を現在値として記していないことを確認する。

- [x] **ステップ4: コードとテストに差分がないことを機械的に確認する**

実行:

```sh
git diff --exit-code -- kaname_shogi tests
```

期待値: 出力なし、終了コード0。

- [x] **ステップ5: Markdown差分の基本検査を行う**

実行:

```sh
git diff --check
```

期待値: 出力なし。

### タスク5: Refactor要否確認と独立レビューを行う

**ファイル:** `README.md`、`docs/README.md`、`docs/resume.md`、`docs/roadmap-repository-foundation.md`

**インターフェース (Interfaces):**

- 消費 (Consumes): 検証済みの文書差分と承認済み設計。
- 生産 (Produces): Critical・Important・Minorに分類した独立レビュー結果、必要な修正、再検証結果。

- [x] **ステップ1: 追加の構造整理が必要か判断する**

索引が一つに集約され、READMEと責務が重複していないかを確認する。既存文書の移動、ディレクトリ別索引、自動生成、古い内容の是正がなくても目標を満たすならRefactor不要と判断する。必要な場合も承認済み範囲内の見出し・表・リンク整理だけに限る。

- [x] **ステップ2: `requesting-code-review` を使って独立レビューを依頼する**

レビュー対象は `main...HEAD` と未コミット差分、仕様書、本計画とする。次を重点確認する。

- Critical: 相対リンク切れ、現役と履歴の誤認、現在情報と時点情報の混同、対象外のコード・テスト・既存文書の意味変更。
- Important: 第1〜44回または主要テーマの欠落、READMEから利用方法・テスト・主要入口が失われること、READMEから外した情報へ索引から到達できないこと、単一索引とREADMEの責務重複。
- Minor: 見出し順、表記ゆれ、冗長さ、表の読みやすさ、Markdownの体裁。

- [x] **ステップ3: レビュー指摘へ対応する**

CriticalまたはImportantがあれば承認済み範囲内で修正し、タスク4の全検証を再実行してから再レビューする。初回レビューで確認された再開情報の矛盾は、本人の追加承認に基づき `docs/resume.md` を現在状態へ更新し、引き継ぎをテーマ開始時点の記録と索引上で明示して解消する。Minorは対応するか、対応しない理由を明示する。最終的にCritical・Importantが0件になるまで次へ進まない。

- [x] **ステップ4: 最終レビュー結果を一時記録する**

Critical・Important・Minorの件数、各指摘、対応、再レビュー結果を、次タスクで `docs/learning/44-document-navigation.md` へ正確に転記できる形で整理する。実施していないレビューや検証を完了扱いにしない。

### タスク6: 学習記録とmain取り込み待ち状態を記録し、コミットする

**ファイル:** 作成 `docs/learning/44-document-navigation.md`、変更 `docs/roadmap-repository-foundation.md`、`docs/README.md`

**インターフェース (Interfaces):**

- 消費 (Consumes): 実際の差分、リンク検査出力、Refactor判断、独立レビュー結果。
- 生産 (Produces): 第44回の事実に基づく学習記録、main取り込み待ちを示すロードマップと索引行、レビュー済みコミット。

- [x] **ステップ1: 第44回学習記録を作成する**

次の節をこの順で書く。

1. 目的と対象外。
2. 開始時のGit状態と読んだ資料。
3. 第43回から引き継いだ承認済み設計。
4. 計画承認日と実装範囲。
5. `docs/README.md` の構成とREADME簡潔化の判断。
6. READMEから外した情報と既存参照先の対応。
7. Refactor要否。
8. 独立レビューのCritical・Important・Minor、対応、再レビュー。
9. リンク検査、変更範囲検査、`git diff --check` の実測結果。
10. 未解決事項。
11. 最後の理解確認。質問だけを記し、本人の回答前は「未回答」とする。

最後の理解確認の質問は次の一問とする。

> AIが特定テーマの現在仕様を調べるとき、なぜREADMEや過去の学習記録をすべて読むのではなく、`docs/README.md` から該当する知識メモを選び、判断理由が必要な場合だけ学習記録へ進むのか。

- [x] **ステップ2: ロードマップと索引をmain取り込み待ち状態へ更新する**

`docs/roadmap-repository-foundation.md` のテーマ2を「実装・レビュー完了、main取り込み待ち」にし、実施日、`README.md`、`docs/README.md`、`docs/learning/44-document-navigation.md`、リンク検査と独立レビューの結論を記す。`docs/README.md` の第44回行もmain取り込み待ちへ更新する。main取り込み、取り込み先検証、最後の理解確認が終わるまで、テーマ全体を完了扱いにしない。次テーマは本人が選ぶまで確定しない。

- [x] **ステップ3: 最終検証を実行する**

タスク4の相対リンク検査と次を実行する。

```sh
git diff --exit-code -- kaname_shogi tests
git diff --check
git status --short --branch
```

期待値: コード・テストの差分なし、相対リンク切れなし、空白エラーなし、変更対象は計画で許可したMarkdownだけ。

コードとテストを変更しないため、ユニットテストは原則として実行しない。文書変更が実行コマンドやCLI仕様と食い違う疑いがレビューで生じた場合だけ、確認対象を明記して既存テストを実行し、その理由と結果を学習記録へ残す。

- [x] **ステップ4: レビュー済み文書をコミットする**

実行:

```sh
git add README.md docs/README.md docs/resume.md docs/roadmap-repository-foundation.md docs/learning/44-document-navigation.md docs/plans/2026-09-27-repository-document-navigation.md
git diff --cached --check
git diff --cached --stat
git commit -m "docs: 文書ナビゲーションを整理する"
```

期待値: 日本語のConventional Commitで、レビュー・検証・学習記録がそろった文書変更だけがコミットされる。

### タスク7: main取り込み、取り込み先検証、最後の理解確認を行う

**ファイル:** 条件付きで `docs/learning/44-document-navigation.md`、`docs/next-topics.md`、`docs/resume.md`、新しい引き継ぎ文書

**インターフェース (Interfaces):**

- 消費 (Consumes): レビュー済み作業ブランチ、本人の取り込み承認、最後の理解確認への本人回答、本人が選ぶ次テーマ。
- 生産 (Produces): `main` へ取り込まれた文書ナビゲーション、第44回の本人回答、必要に応じた次セッションの引き継ぎ。

- [x] **ステップ1: main取り込み前の承認を得る**

実行:

```sh
git status --short --branch
git log --oneline main..HEAD
git diff --stat main...HEAD
git diff --check main...HEAD
```

作業ブランチ、変更ファイル、リンク検査、独立レビューの最終結論、コード・テスト差分なしを提示する。本人の明示的承認までmainへ取り込まない。

- [x] **ステップ2: 承認後にmainへ取り込み、取り込み先で再検証する**

実行:

```sh
git switch main
git merge --no-ff codex/document-navigation -m "merge: 文書ナビゲーション改善を取り込む"
git diff --exit-code HEAD^1..HEAD -- kaname_shogi tests
git diff --check HEAD^1..HEAD
git status --short --branch
```

READMEと索引の相対リンク検査もmainで再実行する。期待値: コード・テスト差分なし、リンク切れなし、空白エラーなし、作業ツリーはクリーン。

- [x] **ステップ3: 最後の理解確認を一問だけ出す**

タスク6で記録した一問だけを提示し、本人の回答を待つ。回答前に次テーマの学習・実装へ進まない。

- [x] **ステップ4: 本人の回答と補足、テーマ完了を記録する**

本人の回答とアシスタントの補足を区別して `docs/learning/44-document-navigation.md` へ追記し、未回答を正解として記録しない。`docs/roadmap-repository-foundation.md` のテーマ2を完了にし、`docs/README.md` の第44回行を完了テーマの履歴表現へ、`docs/resume.md` を次テーマ未選定の現在状態へ更新する。内容確認後、次でコミットする。

```sh
git add docs/learning/44-document-navigation.md docs/roadmap-repository-foundation.md docs/README.md docs/resume.md
git diff --cached --check
git commit -m "docs: 第44回の理解確認を記録する"
```

- [ ] **ステップ5: 次テーマ候補を示し、選択を待つ**

`docs/next-topics.md`、README、`docs/02-project-direction.md`、ロードマップを読み直し、候補を小さい順に示して推薦理由を説明する。本人が次テーマを選ぶまで、`docs/next-topics.md`、`docs/resume.md`、引き継ぎ文書を更新せず、新テーマを開始しない。

- [ ] **ステップ6: 次テーマを新しいセッションで始める場合だけ引き継ぐ**

本人が次テーマを選び新しいセッションを希望した場合、`session-handoff` スキルを使い、`docs/next-topics.md`、`docs/resume.md`、`docs/handover-<topic>.md` を更新する。選定理由、完了事項と背景、現在のGit状態、作業ディレクトリ、直近の検証、次に読むファイル、再開用プロンプトを記録し、内容確認後に日本語のConventional Commitでコミットする。

## 計画の自己レビュー

- 仕様の各要件を、タスク2（単一索引）、タスク3（人間向けREADME）、タスク4（リンク・変更範囲検査）、タスク5（独立レビュー）、タスク6（学習記録・完了状態）、タスク7（main取り込み・理解確認）へ対応付けた。
- 既存文書の移動・改名・削除、古い内容の是正、コード・テスト変更、自動生成を含めていない。
- `docs/README.md` の36テーマ群、READMEから外す情報の参照先、変更ファイル、コミットメッセージ、検証コマンドを具体化し、曖昧な実装プレースホルダーを残していない。
- 現在の再開案内と開始時点の引き継ぎ、現在情報と時点情報、確定知識と判断経緯の区別をレビュー基準に含めた。
- 計画承認前は本計画書以外を変更せず、実装開始、独立レビュー、コミット、main取り込み、最後の理解確認の承認境界を分離した。
