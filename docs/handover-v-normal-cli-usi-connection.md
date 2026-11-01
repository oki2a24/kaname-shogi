# 🔄 セッション引き継ぎ：V比較結果を通常CLI・USIへ接続

## 🎯 最終目標

Vの確認比較で改善が支持された候補 `10M+U+V` を、通常CLIとUSIの対局方式として選択できるようにする。既定方式を変えず、Random・Material・TwoPlyMaterial・FullWidth4・AlphaBeta4・既存の `10M+U` を残す。具体的な表示名、CLIで先手・後手に個別指定できるか、USI `Difficulty` の名前と局中固定の扱い、内部の一手選択経路は、まだ設計されていない。

## ✅ 完了した事項と「意思決定の背景」

- [済] Vの評価関数と `10M+U+V` 合成が実装済み。
  - **Why:** Vは、支えがある非玉駒が現在価値の低い相手非玉駒から利かれているとき、対象一枚につき1と数える評価である。合成式は `10M+U+V`。固定局面と一手選択の計数検証は完了している。
- [済] V0（`10M+U+0V`）とV1（`10M+U+1V`）は比較CLIに接続し、予備・確認比較と分析を完了した。
  - **Why:** 同じM/U、一手選択器、詰み優先を保ち、V係数だけを変えて比較した。確認は予備と独立した6局面・2040組/4080局で、95% Hoeffding区間は[0.505225, 0.567569]。下限は0.5を少し上回り、この事前固定条件の範囲で改善を支持した。一般局面の棋力向上までは示さない。
- [済] 比較専用のV0/V1は通常CLI・USIへ公開していない。
  - **Why:** 前テーマは比較CLI接続に限定し、通常CLI・USIへの接続を明示的に除外していた。今回の依頼は、その限定を遡って変更するものではなく、新しい接続テーマの選定である。現在の通常CLI/USIにはU方式 `10M+U` があるが、Vは含まれない。READMEはUSI `Difficulty` の `MaterialUndefendedPiece` を既存候補として案内し、V0/V1は比較CLI専用と記載している。
- [済] 本人は2026-11-01、V比較で改善が支持された候補を通常CLI・USIへ接続することを次テーマとして選んだ。
  - **背景:** 「通常CLIとUSIへの接続は終わっているか。未完了ならやりたい」と確認したため、現状を説明した上でこの接続テーマを選定した。選定理由はこの希望を越えて推測しない。
- [未] 今テーマの設計案・実装計画・TDD・実装・検証・独立レビューは未着手・未承認。
  - **重要:** `10M+U+V` を通常CLI/USIから選択できるようにするテーマ選定は済んだが、具体設計や実装を承認したわけではない。新セッションでbrainstormingを行い、設計と実装計画を提示して本人の明示承認を待つ。承認前にTDD・テスト変更・製品コード変更へ進まない。

## 🚧 現在の物理的状態

- **作業ディレクトリ:** `/private/tmp/kaname-shogi-main-integration-clone`
- **作業branch:** `codex/v-supported-threat-normal-cli-usi-connection`
- **開始時点:** GitHub `main` の `02f7612a8ac005dbfa79cb079f2ea93303496fd5` を起点にbranchを作成した。GitHubの先端は起点作成時に直接照合済み。handoff文書コミットを除き、このテーマのコード変更はない。
- **Git remote注意:** この標準cloneの `origin` は元checkout `/Users/oki2a24/kaname-shogi` を参照しているため、tracking ref `origin/main` は古い `7a389a52`。これをGitHubの最新mainとみなさない。GitHub mainは起点時点で `02f7612a` と直接確認した。
- **前テーマbranch:** `/Users/oki2a24/.codex/worktrees/undefended-piece-integration/kaname-shogi` の `codex/supported-lower-value-threat-comparison` は `7a389a52` でclean。比較実装の詳細を見る場合は読み取り専用で参照し、新テーマの作業場所にはしない。
- **保護する元checkout:** `/Users/oki2a24/kaname-shogi` はbranch `codex/c1-analysis-performance-investigation` で既存status 18件を保持している。checkoutの編集・切替・clean・reset・stashをしない。`.agents/tasks/`、`data/comparison/runs/`とC2保護4件も変更・削除・ステージしない。
- **直近の統合先検証:** V比較を含むmainでは `PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_tests_parallel.py` が1031件・84モジュール・25.565秒で成功。Ruff 0.16.10、format、check、hooksも成功した。文書のみの後続コミットでは全体テストを再実行せず、hooks・`git diff --check`・Markdown相対リンク検査が成功した。
- **関係する実装ファイル:** `kaname_shogi/material_piece_threat.py`、`kaname_shogi/cli.py`、`kaname_shogi/usi_engine.py`。関連テスト候補は `tests/test_supported_piece_threat.py`、`tests/test_piece_threat_selection.py`、`tests/test_cli.py`、`tests/test_usi_engine.py` とU既存接続テスト。次セッションではファイル現物を読み、変更境界を確定する。

## 📝 次の具体的なアクション

1. 新セッションで指定ディレクトリへ移動し、`git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`、`git rev-parse main`、`git rev-parse HEAD`を順に実行し、branchと現物を照合する。
2. `AGENTS.md`、`docs/resume.md`、本handoff、Vの知識・設計・実装計画・比較結果、既存U通常CLI/USI設計・実装計画、README、現行コードとテストを読む。
3. 未確定事項をbrainstormingで明確にする。特に、CLIの方式選択とCVCでの先後別設定、USI option名・値・局中固定、既存 `10M+U` との関係、既定Randomの維持、探索深さ別の接続範囲を決める。比較専用V0/V1を通常モードへそのまま公開するかどうかも、意図を確認して設計する。
4. 設計案と実装計画を作成・提示し、本人の明示承認を待つ。計画承認と新セッション再開確認前にTDDを始めない。
5. 承認後は `~/.codex/observations/test-driven-development.md` と `docs/knowledge/test-coverage-review.md` を参照し、対象振る舞いごとにassertion Redを確認してから最小実装する。U通常CLI/USI接続時に制御付き探索経路の追加接続が必要だった経験を参照し、登録表示だけで終えない。
6. Refactor要否確認後に独立レビューを行う。Critical/Importantがあれば修正・再検証・再レビューし、文書更新・Ruff・対象/全体テスト・差分検査を記録する。今回の新テーマのmain統合・pushは別途本人承認を得る。
7. 新テーマ完了後も、主線の「次の非駒得評価項目を選び学ぶ」は未完了のまま次テーマ候補へ残す。ShogiHomeでのU実践も、遠隔PCへアクセス可能との本人連絡後に再提案する保留帰還目標である。

## 💬 再開用プロンプト

> `/private/tmp/kaname-shogi-main-integration-clone` のbranch `codex/v-supported-threat-normal-cli-usi-connection` で、V比較結果を通常CLI・USIへ接続するテーマを始めます。まず `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`、`git rev-parse main`、`git rev-parse HEAD` をこの順で実行し、`AGENTS.md`、`docs/resume.md`、`docs/handover-v-normal-cli-usi-connection.md` と関連資料を現物照合してください。V比較結果は事前固定6局面・一手選択・指定条件の範囲で改善を支持しましたが、一般局面の棋力向上を示すものではありません。Vは比較CLIには接続済みですが、通常CLI・USIには未接続です。既存U通常CLI/USI接続を参考に、CLI選択/CVC先後別設定、USI `Difficulty`、探索経路、既定動作維持を調べてbrainstormingで設計範囲を明らかにし、設計案・実装計画を提示して明示承認を待ってください。承認前はTDD・テスト変更・コード変更を開始しないでください。元の `/Users/oki2a24/kaname-shogi` の作業状態と `.agents/tasks/`、`data/comparison/runs/`・C2保護4件は変更しないでください。main統合・pushは別途承認を待ってください。
