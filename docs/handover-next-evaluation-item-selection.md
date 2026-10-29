# 引き継ぎ：次の非駒得評価項目を選ぶ

作成日：2026-10-29。本人はC2完了後の候補1「次の評価項目を一つ選ぶ（主線）」を選定した。これは次の評価項目を選ぶ学習段階の選定であり、評価項目そのもの、具体設計、実装計画、製品変更を承認したものではない。再開時は現Git状態と入口文書を照合し、この選択の続きを始める。

## 最終目標

主線「駒得以外の局面評価を一項目ずつ育てる」に従い、既存の選択可能な動作を保ちながら、次に学ぶ評価項目を一つ選び、測定可能な改善仮説・独立期待値・検証範囲を持つA段階へ進む。今回選定されたのは評価項目を選ぶテーマまでであり、実際に扱う項目は未選定である。「A3」という番号や順序も予約しない。

## 完了した事項と意思決定の背景

### 主線の位置

- 補助P1（比較設計）、千日手、P2（比較CLI）は完了済み。
- 主線A1/B1（飛車可動性）は完了。C1の比較結果は判断不能で一旦区切った。
- A2/B2（玉周辺安全度）は完了。続くC2「安全度を接続して比較評価する」も、比較CLIだけを対象に接続・確認比較・統計分析まで完了した。
- C2の確認比較は登録4局面を各509組、計2,036組・4,072局で行い、95%得点区間 `[0.227, 0.305]`、判定「悪化を支持」だった。この結論は登録4局面と今回の探索条件に限る。通常CLI/USI、全局面の棋力、悪化原因は示さない。安全度重み1の候補は通常対局方式へ接続されておらず、選択1はこれを採用済みと扱わず次の評価項目へ進む選択である。
- 最後の理解確認に本人は「棋力向上していないといえる。」と回答した。補足では、比較対象となった4局面・今回の条件で悪化を支持することと、エンジン全体の棋力やレーティングまでは判断できないことを区別して記録した。

### 本人の今回の選択

2026-10-29、本人は次テーマ候補1「次の評価項目を一つ選ぶ（主線・推薦）」を選んだ。選定理由は尋ねていないため推測しない。実際の評価項目は、ロードマップの候補プールと現行評価を調べ、重複加点にならないかを見たうえで本人と選ぶ。候補には駒の働き・活性度、可動性、利きの広がり、駒の連携、配置・進行度がある。これらは入口であり、採用順や実装予定ではない。

通常CLIのSFEN入出力、飛車可動性バージョン2、二手・四手探索への新評価適用は別候補・別判断であり、今回の選択に含まれない。長時間の比較・分析CLIは本人が端末で実行する。pushは承認されていない。

## 現在の物理状態

- 主な作業worktree：`/Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi`。
- handoff文書の作成直前（2026-10-29）の状態は `main`、HEAD `eed74a35`、`origin/main` は `cdd46519808564584c6f77507319c4d8df6edacd`、ローカルmainは18コミット先行。以下のhandoff・入口文書をコミットするため、次セッションでは必ず最新状態を取り直すこと。
- C2統合コミットは `6ddeae78`。C2ブランチ `codex/c2-king-safety-evaluation` はそのコミットに残る。C2後の記録コミットは `6711ed3a`、`59d166f3`、`eed74a35`。
- 未追跡の本人作成データは保持する。特に次の4項目は追加・移動・削除・上書き・一括ステージしない。

  ```text
  data/comparison/runs/c2-king-safety-confirmation-2026-10-28-seeds.json
  data/comparison/runs/c2-king-safety-confirmation-2026-10-28/
  data/comparison/runs/c2-king-safety-confirmation-2026-10-28-workers-4/
  data/comparison/runs/c2-king-safety-confirmation-2026-10-28-workers-4-analysis.json
  ```

  worker 4 directoryには4,074ファイル（4,072局、条件、summary）がある。worker 1の中断出力とworker 4の完了結果を混ぜず、既存比較や分析CLIを再実行しない。
- 元の `/Users/oki2a24/kaname-shogi` は `codex/c1-analysis-performance-investigation`、HEAD `14e7210b` で未コミット文書・比較データを保持している。そこではブランチ切替、clean、reset、削除、上書き、C2 checkoutを行わない。今回のmain統合は別worktreeにあり、元checkoutのworking treeへC2を適用していない。
- C2統合後の製品検証は全943テスト・67モジュールが成功し、Ruff整形・checkと差分検査も成功。以後の変更は文書のみで、通常Gitフックを通過している。C2の結果・検証の詳細は[学習記録](learning/c2-king-safety-evaluation.md)、現行状態は[再開案内](resume.md)を参照する。
- 実装やテスト変更へ進む場合は、その時点で個人の `~/.codex/observations/test-driven-development.md` と `docs/knowledge/test-coverage-review.md` を読み、Python環境、Ruff固定版、ローカルフックを確認して、製品変更前baselineを新たに取る。C2のテスト数・baselineを新テーマの実績として流用しない。

## 次の具体的な行動

1. 再開時に次のGitコマンドを指定worktreeで実行し、出力をこの記録と照合する。

   ```sh
   git status --short --branch
   git log -3 --oneline --decorate
   git branch --show-current
   ```

2. `AGENTS.md`、`docs/resume.md`、本書を現物と照合する。元checkoutの状態は読み取り専用で確認し、手を加えない。
3. `docs/next-topics.md` 冒頭、`docs/roadmap-non-material-position-evaluation.md`、`docs/02-project-direction.md` とREADMEを読み、次の評価項目を選ぶ主線上の位置を確認する。
4. ロードマップの評価項目候補と現行評価・知識メモを調べ、各候補の独立期待値、駒得や既存項目との重複、測定可能な局面、対象外・未検証を比較する。本人の回答を一問ずつ待ってから候補を絞り、本人が実際の評価項目を選ぶまで先回りしない。
5. 選ばれた項目について学習・調査を行い、範囲・独立期待値・確認方法を文書にする。設計と実装計画を提示し、明示承認を得るまではTDD・コード・テスト変更・実装を始めない。
6. 将来コード変更が承認された場合のみ、TDD観察記録・テスト範囲レビュー・環境確認・baselineを新規に行う。通常の実装・検証・独立レビュー・記録後のmain統合も別途承認を得る。pushは別途承認がない限り行わない。

## 再開用プロンプト

> `/Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi` で、主線の次の非駒得評価項目を一つ選ぶ段階を始めます。最初に `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current` を実行し、`AGENTS.md`、`docs/resume.md`、本引き継ぎと現物を照合してください。本人は2026-10-29に次テーマ候補1「次の評価項目を一つ選ぶ（主線）」を選びましたが、評価項目そのもの、選定理由、設計、実装は未決定・未承認です。次のテーマ選定を理由として推測せず、`docs/next-topics.md`冒頭、`docs/roadmap-non-material-position-evaluation.md`、`docs/02-project-direction.md`、README、評価項目候補プールと現行コードを調べ、既存評価との重複・独立期待値・検証可能な範囲を整理してください。確認事項は一問ずつ尋ね、本人の回答を待ってから進めてください。次の評価項目を本人が選ぶまで選定を確定しないでください。通常CLIのSFEN入出力、飛車可動性バージョン2、二手/四手への適用を自動追加しないでください。設計と実装計画を提示し、明示承認前にTDD・コード・テスト変更・実装を始めないでください。実装へ進む場合は個人の `~/.codex/observations/test-driven-development.md` と `docs/knowledge/test-coverage-review.md`、環境・Ruff固定版・ローカルフック・新しい製品変更前baselineを確認してください。長時間比較・分析CLIは私が端末で実行します。C2比較成果物を保持し、元の `/Users/oki2a24/kaname-shogi` は未コミット文書・比較データがあるのでclean/reset/切替・削除・上書きをしないでください。C2は別worktreeのローカルmainに統合済みですが、origin/mainへpushしていません。すべて日本語で進めてください。
