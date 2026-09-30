# プロジェクトの方向性にある基盤整理の完了状態：実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** `docs/02-project-direction.md` の現在情報を、リポジトリ基盤整理の完了と次テーマ未選定の状態へ一致させる。

**アーキテクチャ:** 「最初のゴール」節の1文だけを置換し、過去の見直し節と長期方針を履歴・将来像として保つ。コード・テスト・他の現在情報文書は変更しない。

**技術スタック:** Markdown、Git、Python 3.9標準ライブラリ、unittest。

**仕様 (Spec):** [プロジェクトの方向性にある基盤整理の完了状態：設計仕様](2026-09-30-project-direction-foundation-completion-design.md)

**グローバル制約 (Global Constraints):**

- 変更対象は `docs/02-project-direction.md` の「最初のゴール」節にある現在情報の1文だけとする。
- 基盤整理が完了し、次テーマが未選定である現在状態を表す。
- 将来のSFEN・USI・探索・評価の方針、過去の見直し節、コード、テスト、CLI動作、将棋規則、保存形式は変更しない。
- 相対Markdownリンク、`git diff --check`、全ユニットテストを確認する。
- mainへの取り込みは本人の明示的な承認後にだけ行う。

---

## ファイル構成

- 変更: `docs/02-project-direction.md`
  - 最初のCLI到達点と基盤整理の完了、次テーマ未選定を表す現在情報へ置換する。
- 変更しない: `kaname_shogi/`、`tests/`、`docs/next-topics.md`、`docs/resume.md`、`docs/roadmap-repository-foundation.md`
  - これらはすでに基盤整理完了・次テーマ未選定の情報を持つか、今回の1文是正の対象外である。

### タスク1: 現在情報を最小限に是正する

**ファイル:**

- 変更: `docs/02-project-direction.md:15`
- テスト: `tests/` の全240件

**インターフェース (Interfaces):**

- 消費 (Consumes): 第42回で最初のCLI到達点が完了した事実、第43〜50回で基盤整理が完了した事実、次テーマ未選定の現在状態。
- 生産 (Produces): 「最初のゴール」節における正確な現在情報。

- [ ] **ステップ1: 対象の現在情報を置換する**

次の2文を、設計仕様で合意した1文へ置き換える。

```markdown
この最初のゴールは、第42回までに達成しました。現在は、次の機能追加の前にリポジトリ基盤を整理する小テーマを進めています。
```

置換後:

```markdown
第42回までに最初の到達点を完了し、その後のリポジトリ基盤整理も完了した。現在は、次テーマを選ぶ前の段階にある。
```

「段階的な発展の見通し」以降の節、コード、テスト、他の文書には触れない。

- [ ] **ステップ2: 差分範囲と書式を確認する**

実行:

```sh
git diff --check
git diff -- docs/02-project-direction.md
git diff --exit-code -- kaname_shogi tests
```

期待値: 書式エラーなし。`docs/02-project-direction.md` の対象1文だけが変わり、
`kaname_shogi/` と `tests/` の差分はない。

- [ ] **ステップ3: 相対リンクと全ユニットテストを確認する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q
```

期待値: 全240件が成功する。Python標準ライブラリの読み取り専用スクリプトで
`docs/02-project-direction.md` の相対Markdownリンクも確認し、不足を0件とする。

- [ ] **ステップ4: Refactor要否と独立レビューを確認する**

1文の現在情報がロードマップ・再開案内・次テーマ候補と一致するかを確認する。見出しの再構成、
過去の履歴の更新、文書移動は不要と記録する。読み取り専用の独立レビューでCritical・Important・Minorを
確認し、CriticalまたはImportantがあれば是正、再検証、再レビューを行う。

- [ ] **ステップ5: 是正内容をコミットし、main取り込みの承認を待つ**

```sh
git add docs/02-project-direction.md
git commit -m "docs: 基盤整理完了の現在地を是正する"
```

検証結果と独立レビュー結果を本人へ提示し、mainへの取り込みは明示承認後に行う。

## 計画の自己レビュー

- [x] 変更対象を1文に限定し、非対象の文書・コード・テストを明記した。
- [x] 置換前後の文面、差分確認、リンク確認、全テスト、独立レビューを具体化した。
- [x] プレースホルダを残さず、実行コマンドをリポジトリ直下で使える形にした。
