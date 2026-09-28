# コードとユニットテストの構造レビュー 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** `kaname_shogi/` と `tests/` の全14ファイルを構造面からレビューし、モジュールとテストの対応、保守上の懸念、変更不要の根拠、別テーマ候補を第46回学習記録へ残す。

**アーキテクチャ:** 本体モジュールを起点に責務・公開候補・依存方向を整理し、テスト側から主対象、保護する境界、テストの性質、内部実装への依存を逆引きして漏れを確認する。コードとテストは変更せず、結果は一つの学習記録へ集約し、現在情報を持つ索引・ロードマップ・再開案内だけを最小限更新する。

**技術スタック:** Python 3.9、標準ライブラリの `unittest`、Markdown、Git、`rg`、POSIXシェル。

**仕様 (Spec):** `docs/plans/2026-09-28-code-and-unit-test-structure-review-design.md`

**グローバル制約 (Global Constraints):**

- 対象は現在存在する `kaname_shogi/` の8ファイルと `tests/` の6ファイルである。
- `kaname_shogi/__init__.py` と `kaname_shogi/__main__.py` も対象に含める。
- コード、テスト、公開動作、JSON形式を変更しない。
- 設定ファイル、過去の設計書の内容監査、将棋ルールの正否、性能測定、新機能は対象外とする。
- テストは「主に検証するモジュール」と「併せて保護する境界」を分けて記録する。
- テストの性質は「単体中心」「結合的」「限定的なCLI E2E／スモーク」のいずれかで記録する。
- 境界テストだと名前や配置から判別しにくい場合は、今回変更せず、保守上の懸念または別テーマ候補として記録する。
- 公開インターフェースは、先頭が `_` でない名前、docstring、README、他モジュールからの利用実績を合わせて判断する。
- 先頭が `_` の名前をテストが直接参照する場合は、理由と変更耐性への影響を個別に評価する。
- 重複は「保守上の重複」「境界をまたぐ類似準備」「意図的に独立させた期待値」に分ける。
- リファクタリング候補が見つかっても実装せず、別テーマ候補として記録する。
- 具体的な調査結果は `docs/learning/46-code-and-unit-test-structure-review.md` に集約し、設計仕様や本計画へ重複させない。
- コミットメッセージは日本語のConventional Commitにする。
- `main` への取り込みは、テーマの記録・検証・独立レビューがそろった後、本人の承認を得てから行う。

---

## ファイル構成

| ファイル | 役割 | 操作 |
| --- | --- | --- |
| `docs/learning/46-code-and-unit-test-structure-review.md` | 対応表、内部依存、重複、懸念、変更不要の根拠、別テーマ候補、検証、レビュー、振り返りを一元記録する | 作成 |
| `docs/README.md` | 第46回と設計仕様・実装計画・学習記録への索引を追加する | 変更 |
| `docs/roadmap-repository-foundation.md` | テーマ3の進行と完了結果、成果物への参照を記録する | 変更 |
| `docs/resume.md` | 現在の作業ブランチ、承認状態、完了事項、残作業を示す | 変更 |
| `docs/plans/2026-09-28-code-and-unit-test-structure-review.md` | 調査、記録、検証、レビューの実行手順と実績チェックを保持する | 作成・進捗更新 |

変更しないファイル:

- `kaname_shogi/` と `tests/` 以下の全14ファイル。
- 既存の学習記録、知識メモ、設計仕様、実装計画、引き継ぎ。ただし上記で明示した現在情報の3文書と、本計画の進捗チェックは除く。
- ルートの `README.md`。今回のレビューでは利用方法や現在の機能を変更しないためである。

## タスク1: 実行条件と調査対象を固定する

**ファイル:**

- 参照: `docs/plans/2026-09-28-code-and-unit-test-structure-review-design.md`
- 参照: `kaname_shogi/` の全8ファイル
- 参照: `tests/` の全6ファイル
- 進捗更新: `docs/plans/2026-09-28-code-and-unit-test-structure-review.md`

**インターフェース (Interfaces):**

- 消費 (Consumes): 承認済み設計仕様、本人による本計画の承認、現在のGit状態。
- 生産 (Produces): 全14ファイルの固定一覧、変更前のコード・テスト不変性、調査に使う事実一覧。

- [ ] **ステップ1: 計画承認と作業状態を確認する**

実行:

```sh
git status --short --branch
git log -3 --oneline
```

期待値: ブランチは `codex/code-and-unit-test-structure-review`。設計仕様と本計画以外に未承認の差分がなく、本人の計画承認が会話に記録されている。

- [ ] **ステップ2: 対象ファイル一覧と行数を再取得する**

実行:

```sh
rg --files kaname_shogi tests
wc -l kaname_shogi/*.py tests/*.py
```

期待値: `kaname_shogi/` 8ファイル、`tests/` 6ファイルの合計14ファイルが得られる。実行時に増減があれば、調査を止めて設計範囲への影響を本人へ確認する。

- [ ] **ステップ3: コードとテストに差分がないことを確認する**

実行:

```sh
git diff --exit-code main...HEAD -- kaname_shogi tests
git diff --exit-code -- kaname_shogi tests
```

期待値: どちらも出力なし、終了コード0。設計開始後にコードとテストを変更していない。

- [ ] **ステップ4: 責務・公開候補・依存・テスト構造の機械的な一覧を取得する**

実行:

```sh
rg -n '^from \.|^import ' kaname_shogi
rg -n '^class |^def |^    def ' kaname_shogi
rg -n '^from kaname_shogi|^import kaname_shogi' tests
rg -n '^class |^    def test_|^    def _' tests
rg -n 'movegen\._|cli\._|game_record\._|model\._|display\._' tests
```

期待値: 設計時に確認した依存、公開候補、テストクラス、内部名への直接参照を再現できる。検索結果を結論そのものにはせず、各ファイル本文と照合するための一覧として使う。

## タスク2: モジュール責務とテスト対応表を作成する

**ファイル:**

- 作成: `docs/learning/46-code-and-unit-test-structure-review.md`
- 参照: `kaname_shogi/__init__.py`
- 参照: `kaname_shogi/__main__.py`
- 参照: `kaname_shogi/cli.py`
- 参照: `kaname_shogi/display.py`
- 参照: `kaname_shogi/game_record.py`
- 参照: `kaname_shogi/model.py`
- 参照: `kaname_shogi/move.py`
- 参照: `kaname_shogi/movegen.py`
- 参照: `tests/test_cli.py`
- 参照: `tests/test_display.py`
- 参照: `tests/test_game_record.py`
- 参照: `tests/test_model.py`
- 参照: `tests/test_move.py`
- 参照: `tests/test_movegen.py`

**インターフェース (Interfaces):**

- 消費 (Consumes): タスク1の全14ファイル一覧、本文読解、import・定義・テストクラス一覧。
- 生産 (Produces): 8本体モジュールの責務・公開候補・依存先と、6テストファイルの主対象・境界・性質・判別しやすさを結ぶ対応表。

- [ ] **ステップ1: 第46回学習記録の事実部分を作成する**

次の見出しを作る。

```markdown
# 第46回：コードとユニットテストの構造レビュー

## 目的
## 開始時の状態と確認資料
## 調査方法
## モジュールの責務・公開インターフェースとテスト対応
## テストから内部実装への依存
## 重複の分類と評価
## 保守上の懸念
## 変更不要の箇所と根拠
## 別テーマにする小リファクタリング候補
## Refactorの要否
## 独立レビュー
## 検証
## 振り返り
## 次回への問い
## 未解決事項
```

開始時のGit状態と確認資料は実際に確認した事実だけを記録し、過去の引き継ぎにある状態と混同しない。

- [ ] **ステップ2: 8モジュールの責務と公開候補を表へ記録する**

表は次の列を使い、本体8ファイルを一行ずつ記録する。

```markdown
| 本体モジュール | 主な責務 | 公開候補 | 主な依存先 | 主なテスト | 併せて保護する境界 | テストの性質 | 判別しやすさ |
| --- | --- | --- | --- | --- | --- | --- | --- |
```

`__init__.py` は空である事実と、パッケージ直下の明示的な公開APIを定義していないことを記す。`__main__.py` は実行入口として、`test_display.py` の実プロセステストとの副次対応を記す。公開候補は、先頭が `_` でないことだけで確定せず、docstring、README、他モジュールからの利用と照合する。

- [ ] **ステップ3: 6テストファイルから対応表を逆引きする**

各テストファイルの全テストクラスを、表の「主なテスト」または「併せて保護する境界」のいずれかへ対応付ける。単体中心、結合的、限定的なCLI E2E／スモークを区別し、境界テストの意図がファイル名・クラス名・メソッド名・docstringのどこまで読めば分かるかを「判別しやすさ」へ記録する。

- [ ] **ステップ4: 対象ファイルの網羅性を確認する**

実行:

```sh
rg -n 'kaname_shogi/(__init__|__main__|cli|display|game_record|model|move|movegen)\.py|tests/test_(cli|display|game_record|model|move|movegen)\.py' docs/learning/46-code-and-unit-test-structure-review.md
```

期待値: 全14ファイルが、対象説明または対応表に明示される。ファイル名をまとめて省略している箇所は、読者が一対一で照合できる表現へ直す。

## タスク3: 内部依存、重複、懸念、変更不要の根拠を記録する

**ファイル:**

- 変更: `docs/learning/46-code-and-unit-test-structure-review.md`
- 参照: `kaname_shogi/` と `tests/` の全14ファイル

**インターフェース (Interfaces):**

- 消費 (Consumes): タスク2の対応表、内部名参照の検索結果、本文から確認した変更理由。
- 生産 (Produces): 内部依存の個別評価、重複の3分類、根拠付きの懸念・変更不要・別テーマ候補。

- [ ] **ステップ1: テストから内部実装への直接依存を個別評価する**

少なくとも、次を検索結果と本文で確認する。

- `tests/test_cli.py` から `cli._ResignCommand` などの内部コマンド型への依存。
- `tests/test_movegen.py` から `_apply_drop_unchecked`、`_apply_drop`、`_has_legal_move` への依存。

各依存について、「何を直接確認するためか」「公開操作だけでは同じ誤りを検出できるか」「内部構造の変更でテストが壊れることを許容する理由があるか」を記録する。内部参照をすべて問題扱いせず、必要性と変更耐性を分けて評価する。

- [ ] **ステップ2: 重複を3分類する**

少なくとも、次を確認する。

- `tests/test_movegen.py` 内の局面スナップショット用ヘルパーの重複。
- `tests/test_cli.py` と `tests/test_movegen.py` にある詰み局面準備の類似。
- 初期配置、候補順、合法手順など、実装と独立して保持する期待値。
- 本体の駒別候補生成にある方向走査・占有判定の類似と、学習上の明示性を維持する理由。

各項目を「保守上の重複」「境界をまたぐ類似準備」「意図的に独立させた期待値」のいずれかへ分類し、共通化する場合としない場合の影響を短く記す。

- [ ] **ステップ3: 保守上の懸念と変更不要の根拠を対にして記録する**

懸念ごとに対象、観察した事実、起こり得る変更漏れ、現在のテストによる保護を記す。ファイルの長さだけで分割を結論にせず、責務数、変更理由、内部結合、対応テストを根拠にする。

変更不要の項目には、現在の規模、公開境界、テストの独立性、学習目的のいずれが根拠かを明記する。「問題が見つからなかった」だけで済ませない。

- [ ] **ステップ4: 別テーマ候補を小さく切り出す**

候補がある場合は、一候補につき一つの責務境界または一つのテスト構造に限定し、対象、解消したい懸念、振る舞いを変えない制約、確認に使える既存テストを記す。候補がない観点は「候補なし」と根拠を記す。候補の実装手順や未選定の将来機能は先取りしない。

- [ ] **ステップ5: Refactor要否を記録する**

今回のGREENを満たすために同一テーマ内のリファクタリングが必要かを判断する。設計仕様どおり、候補が見つかっても今回実装しないため、「今回の変更は文書記録のみ」「コード・テストのリファクタリングは別テーマ」と明記する。

## タスク4: 調査記録の完全性を自己照合する

**ファイル:**

- 変更: `docs/learning/46-code-and-unit-test-structure-review.md`
- 進捗更新: `docs/plans/2026-09-28-code-and-unit-test-structure-review.md`
- 参照: `docs/plans/2026-09-28-code-and-unit-test-structure-review-design.md`

**インターフェース (Interfaces):**

- 消費 (Consumes): タスク2・3の調査記録、承認済み設計仕様、全14ファイル。
- 生産 (Produces): GREEN条件の各項目を満たし、現在情報へ反映できる調査記録の草案。

- [ ] **ステップ1: 設計仕様と調査記録を照合する**

次を一項目ずつ確認する。

- 全14ファイルが対象に含まれる。
- 8モジュールの責務、公開候補、依存先が記録される。
- 主対象と併せて保護する境界が分かれる。
- テストの性質と境界テストの判別しやすさが記録される。
- 内部実装への直接依存が個別評価される。
- 重複が3分類される。
- 保守上の懸念、変更不要の根拠、別テーマ候補が記録される。

- [ ] **ステップ2: コードとテストが未変更であることを確認する**

実行:

```sh
git diff --exit-code main...HEAD -- kaname_shogi tests
git diff --exit-code -- kaname_shogi tests
```

期待値: どちらも出力なし、終了コード0。

- [ ] **ステップ3: 公開候補と内部参照を検索結果へ再照合する**

タスク1ステップ4の定義一覧・内部名参照一覧と、第46回学習記録の対応表・内部依存節を一行ずつ照合する。検索に現れた名前を省略する場合は、同じ分類へまとめられる根拠を記録する。独立レビュー結果はまだ記入しない。

## タスク5: 現在情報の文書を最小更新する

**ファイル:**

- 変更: `docs/README.md`
- 変更: `docs/roadmap-repository-foundation.md`
- 変更: `docs/resume.md`
- 変更: `docs/learning/46-code-and-unit-test-structure-review.md`

**インターフェース (Interfaces):**

- 消費 (Consumes): タスク4で自己照合した調査結果、設計仕様、本計画。
- 生産 (Produces): 第46回と成果物へ到達でき、テーマ3の実際の進行・完了状態を示す現在情報。

- [ ] **ステップ1: 文書索引へ第45回と第46回を反映する**

`docs/README.md` のテーマ・学習回別索引に、既に完了している第45回「古い文書記述の是正」と、今回の第46回「コードとユニットテストの構造レビュー」を追加する。第46回の行から、学習記録、設計仕様、本計画へ到達できるようにする。確定知識と引き継ぎは、該当する実在文書がある場合だけリンクし、なければ `—` とする。

- [ ] **ステップ2: ロードマップのテーマ3を実績どおり更新する**

`docs/roadmap-repository-foundation.md` のテーマ3に、設計仕様、本計画、第46回学習記録への参照を追加する。この時点では進行中とし、対応表、懸念、変更不要の根拠、別テーマ候補を記録中であることを短く記す。完了への変更は、タスク6の検証と独立レビューが成功した後に行う。テーマ4以降は、今回実際に記録した候補の存在以上に具体化しない。

- [ ] **ステップ3: 再開案内を現在状態へ更新する**

`docs/resume.md` に、作業ブランチ、設計・計画承認、構造レビュー記録、検証、独立レビューの実施状況を実績どおり記す。未完了のmain取り込み、取り込み先検証、最後の理解確認があれば明確に残す。次テーマは本人が選ぶまで決定済みと書かない。

- [ ] **ステップ4: 振り返りと次回への問いを記録する**

第46回学習記録へ、構造レビューで理解した責務境界、今後の変更時に対応表をどう使うか、未解決事項を記す。本人がまだ回答していない確認問題を、正解または回答済みとして記録しない。

## タスク6: 最終検証、独立レビュー、テーマコミットを行う

**ファイル:**

- 検証: `docs/learning/46-code-and-unit-test-structure-review.md`
- 検証: `docs/README.md`
- 検証: `docs/roadmap-repository-foundation.md`
- 検証: `docs/resume.md`
- 検証・進捗更新: `docs/plans/2026-09-28-code-and-unit-test-structure-review.md`

**インターフェース (Interfaces):**

- 消費 (Consumes): タスク1〜5の調査結果と文書更新。
- 生産 (Produces): リンク・書式・非コード差分・全テストの成功証拠、Critical・Important・Minorの結論、日本語Conventional Commit。

- [ ] **ステップ1: 更新文書の相対Markdownリンクを検査する**

リポジトリ直下で次を実行する。

```sh
python3 - <<'PY'
import re
from pathlib import Path

sources = [
    Path("docs/README.md"),
    Path("docs/resume.md"),
    Path("docs/roadmap-repository-foundation.md"),
    Path("docs/learning/46-code-and-unit-test-structure-review.md"),
    Path("docs/plans/2026-09-28-code-and-unit-test-structure-review-design.md"),
    Path("docs/plans/2026-09-28-code-and-unit-test-structure-review.md"),
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

- [ ] **ステップ2: 書式とコード・テスト不変性を検査する**

実行:

```sh
git diff --check
git diff --exit-code main...HEAD -- kaname_shogi tests
git diff --exit-code -- kaname_shogi tests
```

期待値: すべて出力なし、終了コード0。

- [ ] **ステップ3: 既存全ユニットテストを実行する**

実行:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

期待値: 全テストが成功する。件数は実行結果を第46回学習記録へ記載し、過去の240件を現在値として先に記入しない。

- [ ] **ステップ4: 検証結果と完了状態を文書へ反映する**

`docs/roadmap-repository-foundation.md` のテーマ3を完了へ変更し、対応表、懸念、変更不要の根拠、別テーマ候補を記録したことを短く記す。`docs/resume.md` と第46回学習記録へも、実行したテスト件数、リンク検査、コード・テスト差分なしを実績どおり反映する。レビュー結果はまだ記入しない。

- [ ] **ステップ5: 反映後のリンク・書式・不変性を再検証する**

ステップ1とステップ2を再実行する。期待値は同じく、不足リンク、書式エラー、コード・テスト差分がないこと。

- [ ] **ステップ6: 最終差分全体の独立レビューを依頼する**

`superpowerssuperpowers:requesting-code-review` を使い、承認済み設計仕様、本計画、全14ファイル、第46回学習記録、索引、ロードマップ、再開案内の最終差分を別のレビュアーに読み取り専用で確認させる。次を必須観点とする。

- 対応表の事実誤認と欠落。
- 公開候補と内部実装の分類。
- 境界テストの性質と判別しやすさ。
- 重複分類と、変更不要または別テーマ候補の根拠。
- 索引・ロードマップ・再開案内と実際の進行状態の一致。
- 今回の範囲を越えた提案や、コード変更の混入。

Critical・Important・Minorを分け、指摘なしの区分も0件と明記させる。

- [ ] **ステップ7: レビュー指摘へ対応して再検証・再レビューする**

CriticalまたはImportantがあれば、事実・根拠・分類・現在情報を最小限修正する。設計範囲を広げる必要がある場合は作業を止め、本人の承認を得て本計画を更新する。修正後はステップ1、2、5、6を再実行する。Minorは対応するか、見送る理由を記録する。

各区分の件数、指摘内容、対応、再レビューの有無を第46回学習記録へ実績どおり記録する。レビュー結果を記録した後、ステップ1とステップ2を再実行する。レビュー前に結果を予測して書かない。

- [ ] **ステップ8: 最終差分と計画の実績を照合する**

実行:

```sh
git status --short
git diff --stat
git diff -- docs/learning/46-code-and-unit-test-structure-review.md docs/README.md docs/roadmap-repository-foundation.md docs/resume.md docs/plans/2026-09-28-code-and-unit-test-structure-review.md
```

期待値: 変更は計画で明示した文書だけで、調査結果、レビュー結果、検証結果、未完了事項が実績どおり記録される。本計画のチェックボックスは完了したステップだけ `[x]` である。

- [ ] **ステップ9: テーマ一式をコミットする**

実行:

```sh
git add docs/README.md docs/resume.md docs/roadmap-repository-foundation.md docs/learning/46-code-and-unit-test-structure-review.md docs/plans/2026-09-28-code-and-unit-test-structure-review.md
git diff --cached --check
git commit -m "docs: コードとテストの構造レビューを記録する"
```

期待値: 作業ブランチに、レビュー済みの調査結果、現在情報、実績更新済み計画を含む日本語Conventional Commitが作成される。設計仕様は既存コミット `978f7a4` に保持される。`main` への取り込みは本人の承認前に行わない。

## 計画の自己レビュー

- 設計仕様の対象範囲、判定基準、対応表、内部依存、重複分類、懸念、変更不要の根拠、別テーマ候補、検証、独立レビューをタスク1〜6へ対応付けた。
- 全14ファイルの明示、テスト側からの逆引き、内部名参照の検索を含め、記録漏れを検出できるようにした。
- コードとテストを変更しないため、TDDのRed・Greenを形式的に適用せず、全ファイル照合、差分検査、全既存テストをGREENの確認手段にした。
- 未確定の将来機能やリファクタリング実装を含めず、候補は別テーマへ分離した。
- コマンドは `/Users/oki2a24/kaname-shogi` を作業ディレクトリとして実行する。
