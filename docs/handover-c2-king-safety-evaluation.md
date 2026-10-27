# 引き継ぎ：C2 安全度を接続して比較評価する

作成日：2026-10-28。これはC2の学習・設計を始める前の記録である。再開時はGitと入口文書を実物に照合し、ここにある過去の検証値を現在の検証として扱わない。

## 最終目標

主線「駒得以外の局面評価を一項目ずつ育てる」のC2として、B2で実装した玉周辺安全度評価を、本人と合意した範囲・比較方法でエンジンへ接続し、対照版との比較評価を行うための学習・調査・設計から始める。ロードマップ上は、CLI/USI接続・確認、反復対局、必要に応じたShogiHome実践、結果・採否・未確認事項の記録がC段階の成果である。

本人は2026-10-28に「C2：安全度を接続して比較評価する」を次テーマとして選んだ。本人が選定理由の詳細を述べたわけではない。C2はB2後の主線への直接の帰還目標であり、B2で作った評価を比較可能な経路へ接続する段階である。選定は、接続先・比較条件・具体案・実装計画・実装・長時間比較の実施を承認したことを意味しない。学習と現状調査から開始し、対象範囲と確認方法を具体化する。

## 完了した事項と判断の背景

### 主線とC1の位置づけ

- A1/B1では、駒得以外の項目として飛車だけの可動性を学び、設計・実装した。
- C1の初回比較と独立追試は別々に実施され、いずれも95%区間が50%を含む結果となった。本人は「判断不能」で一旦区切り、追加比較を現在予定していない。これはB1の効果がないという証明ではない。
- P1・千日手・P2およびC1に付随した比較/分析CLIの補助改善は完了済み。過去の実験手順や結果は各学習記録にあり、C2へ自動で流用・追加しない。

### A2/B2の安全度定義

B2の製品実装は `a75a0466` からmainへfast-forward統合され、統合先検証後にorigin/mainへpush済みである。承認済み設計と実績は次を参照する。

- [A2/B2学習・実施記録](learning/king-safety-design.md)
- [玉周辺安全度の確定知識](knowledge/king-safety-evaluation.md)
- [承認済み設計](plans/2026-10-28-king-safety-design.md)
- [実装計画と実績](plans/2026-10-28-king-safety-implementation-plan.md)

現在の評価部品は `kaname_shogi/king_safety.py`、`kaname_shogi/material_king_safety.py` にあり、既存の `kaname_shogi/one_ply_selection.py` へ評価操作を注入する構造である。関連テストは `tests/test_king_safety.py`、`tests/test_material_king_safety.py`、`tests/test_king_safety_selection.py`。

設計上の契約は以下の通り。

- 玉自身を除く盤内隣接マスについて、現在の相手の利きがある異なるマスを危険マス数 `D` として数える。合法な逃げ先数、詰み、将来の駒打ちは数えない。
- 指定側Pと相手Qについて `S(P) = D(Q) - D(P)`、合成評価は `E(P) = 10 × M(P) + S(P)`。`M` は既存の駒得差。仮の重み10対1で、棋力上の妥当性は未確認。
- 両側の玉は正確に一枚ずつ必要。詰みは新評価の通常点で作らず、既存の一手選択が通常点より優先する。
- 一手選択へ評価を注入する部品までは実装済みだが、通常対局CLI・USI・比較CLIへ公開されていない。
- 指標の限界として、利きの集中、合法性、玉を動かした後の射線、安全性や勝敗の保証を表さない。

最後の理解確認で本人は「少なくとも先手玉の周囲に後手の利きが２つ以上ある状態」と回答した。補足として、`S=-2` は先手の危険マス数が後手よりちょうど2多いことを表し、後手の危険マス数は0以上なので先手の危険マス数は少なくとも2となる。利きの数ではなく、異なる危険マスの差である点も記録済み。

## C2で未決定の事項と範囲境界

まだC2の学習記録・設計書・実装計画は作成・承認されていない。次セッションで現行コードと既存C1接続・比較方式を調べ、少なくとも以下を決める必要がある。

- どの利用経路（CLI、USI、比較CLI、またはその一部）へ、どの評価版をどう選択可能にするか。
- 対照版と候補版、先後の割当、開始局面/棋譜の扱い、千日手・未決着・停止の扱い、反復数と判定基準。
- 接続の振る舞いを確認する独立期待値とテスト検出範囲、短時間の確認方法、長時間実験を本人が端末で行うための手順。
- 結果が判断不能、差あり、または実験不成立の場合に何を結論できるか。

これらは調査・設計の論点であり、回答を先取りしない。通常CLIのSFEN入出力と飛車可動性バージョン2は別候補として保留し、C2へ自動追加しない。二手/四手探索への新評価適用、評価係数の最適化、C2を超える性能改善も自動追加しない。長時間の比較・分析CLIは本人が端末で実行し、アシスタントは起動・監視しない。main統合とpushは別途承認を得る。

## 開始時の物理状態

引き継ぎ準備開始時（2026-10-28）の指定checkoutは `/Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi`。`git status --short --branch` は `## main...origin/main`、`git log -3 --oneline --decorate` の先頭は `452ab55a` (`HEAD -> main, origin/main, origin/HEAD`) で、`git branch --show-current` は `main`、`git rev-parse origin/main` は `452ab55ab0ee1569b46a0c1dddd2a7dd9af0f6d4` だった。C2開始時は必ずコマンドを再実行し、この文書作成後のコミットを含む現物と照合する。

B2実装ブランチ `codex/a2-king-safety-design` は `a75a0466` で、mainへの統合済み。C2の設計・実装用作業ブランチはまだ選定・作成していない。C2を開始するときは、AGENTS.mdに従いmainではなく目的の分かる作業ブランチを使う。

元の `/Users/oki2a24/kaname-shogi` は `codex/c1-analysis-performance-investigation` 上で、次の保持物があった。

```text
 M docs/README.md
 M docs/learning/c1-rook-mobility-evaluation.md
 M docs/resume.md
?? .antigravity/tasks/
?? .venv.backup-2026-10-22/
?? .venv.backup-2026-10-25-broken-python-3150/
?? data/comparison/runs/c1-rook-mobility-confirmation-2026-10-25-analysis-legal-witness.json
?? data/comparison/runs/c1-rook-mobility-confirmation-2026-10-25-analysis.json
?? data/comparison/runs/c1-rook-mobility-confirmation-2026-10-25/
?? data/comparison/runs/c1-rook-mobility-follow-up-confirmation-2026-10-26-analysis-legal-witness.json
?? data/comparison/runs/c1-rook-mobility-follow-up-confirmation-2026-10-26-analysis.json
?? data/comparison/runs/c1-rook-mobility-follow-up-confirmation-2026-10-26-seeds.json
?? data/comparison/runs/c1-rook-mobility-follow-up-confirmation-2026-10-26/
?? data/comparison/runs/c1-rook-mobility-follow-up-pilot-2026-10-26-seeds.json
?? data/comparison/runs/c1-rook-mobility-follow-up-pilot-2026-10-26/
?? docs/plans/2026-10-26-analysis-cli-resume-design.md
?? docs/plans/2026-10-26-analysis-cli-resume-implementation-plan.md
?? docs/plans/2026-10-26-c1-rook-mobility-follow-up-comparison-design.md
```

これは引き継ぎ準備時の記録であり、C2開始時にも `/Users/oki2a24/kaname-shogi` を確認すること。これらはユーザーの保持物なので、clean/reset/切替・削除・上書きしない。C2作業に必要なファイルは現main checkoutを基準に読む。

main統合checkoutには `.venv` がなく、`core.hooksPath` は `.githooks`。開発再開時の必須確認は `.venv/bin/ruff --version` と `requirements-dev.txt` 固定版との一致、ローカルフックである。B2統合検証時に使った環境は `/Users/oki2a24/.codex/worktrees/c1-analysis-speedup/kaname-shogi/.venv`（Python 3.15.2、Ruff 0.16.10）だった。以前の一時リンクでランチャーテストと全体テストを成功させたが、C2開始時の環境状態を保証しない。`scripts/setup_dev.py` は別Git worktreeを直接セットアップ対象にできないことをその時点で確認しているため、環境準備が必要ならREADMEの手順と現在の実体を再確認し、元checkoutの環境や内容を変更しない。

## 直近の検証・未検証

これはB2統合時の記録であり、C2の検証結果ではない。

- 統合先の全体テスト：`PYTHONDONTWRITEBYTECODE=1 /Users/oki2a24/.codex/worktrees/c1-analysis-speedup/kaname-shogi/.venv/bin/python3 scripts/run_tests_parallel.py`。928件・62モジュールが25.003秒で成功。
- Ruff format `--check`、Ruff check、`git diff --check` 成功。
- 統合前、統合checkoutに `.venv` がない状態ではUSI起動テスト3件がランチャーのPython不在で失敗した。既存環境への一時リンクで該当8件を再確認し、全体も成功。リンクは除去済み。
- B2最終独立レビュー Critical 0 / Important 0 / Minor 0。C2設計・接続・比較はレビューも検証も未実施。

次セッションで製品変更を行う場合、個人の `~/.codex/observations/test-driven-development.md` と `docs/knowledge/test-coverage-review.md` を読み、環境/Ruff/フックを再確認し、その作業環境で製品変更前の全体ベースラインを実行する。B2の928件成功をC2作業のベースラインとして流用しない。長時間比較・分析は本人が実行する。

## 次に読む資料と具体的な進め方

開始時に `AGENTS.md`、`docs/resume.md`、本書を照合し、`git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current` を実行する。続けて以下を必要な順に読む。

1. `docs/next-topics.md`、`docs/roadmap-non-material-position-evaluation.md`、`docs/02-project-direction.md` で主線とC2の位置を再確認する。
2. `docs/knowledge/king-safety-evaluation.md`、`docs/learning/king-safety-design.md`、承認済みB2設計・実装計画で評価の現行契約・限界を確認する。
3. `docs/README.md` から既存比較設計・C1の学習記録・接続/実験CLIの関連知識を選び、READMEとコード (`kaname_shogi/`、`tests/`) の現行契約を調査する。C1の方式は比較材料であって、C2へ自動適用される承認仕様ではない。
4. C2の学習・調査で候補経路と対照条件を比較し、独立期待値・検出したい誤り・代表ケース・単独/全体の検出範囲・未検証事項を定める。ここでは実装案の範囲を提示する。
5. 必要な計画文書を作成・自己確認し、内容を本人へ提示する。明示承認を得る前にTDD、コード/テスト変更、実装へ進まない。
6. 承認後に初めて実装・試験・レビューへ進む。振る舞いごとにassert失敗の理由を確認し、既存部品で初回GreenとなるケースをRedと偽らない。最小実装、Green、Refactor要否確認後に独立レビューし、Critical/Importantを解消して記録する。

## 再開用プロンプト

> `/Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi` で主線C2「安全度を接続して比較評価する」を始めます。最初に `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current` を実行し、AGENTS.md、docs/resume.md、本引き継ぎと現物を照合してください。B2はmainへ統合・push済みで、玉周辺安全度評価は既存の一手選択へ注入できる部品として存在しますが、C2の学習・調査・設計・実装は未着手です。docs/knowledge/king-safety-evaluation.md、docs/learning/king-safety-design.md、承認済みB2設計・実装計画、主線ロードマップ、C1の接続・比較記録と現行コードを調べ、C2の対象経路・対照条件・独立期待値・確認方法を学習・設計してください。個人の ~/.codex/observations/test-driven-development.md と docs/knowledge/test-coverage-review.md を読み、実装へ進む場合は環境/Ruff固定版/ローカルフックと製品変更前ベースラインを新たに確認してください。計画を文書として提示し、明示承認前にTDD・コード・テスト変更・実装を始めないでください。通常CLIのSFEN入出力、飛車可動性バージョン2、二手/四手への適用を自動追加しないでください。長時間の比較・分析CLIは私が端末で実行します。main統合とpushは別途承認を得てください。元の /Users/oki2a24/kaname-shogi は未コミット文書・比較データを保持しているためclean/reset/切替しないでください。すべて日本語で進めてください。
