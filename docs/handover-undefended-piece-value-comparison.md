# 引き継ぎ：支えのない被攻撃駒の価値を比較CLIで比較する

> **この文書の時点:** 本文と再開用プロンプトは、比較設計・実施計画の承認前に作成した開始時の記録である。2026-11-02に本人は「組得点＋固定局面の作用確認」を選び、その後設計・実施計画を承認してworker 4での実施を指示した。現在の作業状態・残件は[再開案内](resume.md)と[学習記録](learning/undefended-piece-value.md)を正本とする。このページ内の「明示承認待ち」「承認前に開始しない」という文言は作成時点の履歴であり、現在の指示ではない。

## 最終目標

駒得以外の局面評価を一項目ずつ学び、設計・実装・比較して育てる主線を続ける。本人が2026-11-02に選んだ次テーマは、既に実装済みの「支えのない被攻撃駒の価値」を比較CLIへ接続し、従来方式と比較評価すること。今回の選定はテーマの選択であり、比較設計・実施計画・実装開始・対局実行への承認ではない。

## 完了事項と意思決定の背景

- [完了] 前テーマの「支えのない被攻撃駒の価値を評価へ反映する」は、集計・合成と既存一手選択器への注入まで実装済みで、`main` へ統合・`origin/main` へpush済み。
  - 対象は相手の利きがあり、味方の支えがない盤上非玉駒。攻撃元の数にかかわらず対象一枚の参考価値を一度だけ数え、成駒は現在の参考価値を使う。
  - 今回の合成評価は `10 × M（駒得）+ 1 × 支えのない被攻撃駒の価値合計差 + V（支えあり低価値駒脅威の枚数差）`。旧U（支えのない被攻撃駒の枚数差）は加算せず、価値合計差へ置き換える。今回の項に新しい略号は割り当てていない。
  - `kaname_shogi/material_piece_threat_value.py` の `evaluate_material_piece_threat_value` が合成し、`kaname_shogi/undefended_piece_value.py` が価値合計と差を計算する。CLI・USI・比較CLIにはまだ接続していない。
- [完了] 代表局面での計算・一手選択器注入を検証し、独立レビュー最終判定はCritical 0 / Important 0 / Minor 0。
  - `python3 scripts/run_tests_parallel.py` はmain統合後に1,054テスト・87モジュール・24.711秒で成功。
  - 独立期待値を使った8種類の誤り注入は専用assertionで検出した。これらは固定条件の検査で、一般棋力の改善を示さない。
- [完了] 統合後の最後の理解確認に、本人は「-14。2枚から狙われていても一回計算するのみ」と回答した。相手側の歩1から自分側の飛車15を引くため `1 − 15 = −14`。回答と補足は `docs/learning/undefended-piece-value.md` に記録済み。
- [選定済み] 本人は次候補の1「今回の評価を比較CLIへ接続して比較する」を選んだ。選定理由は聞いていないため推測しない。
  - 推薦理由として提示したのは、今回の項目が実装されたため、次に旧方式 `10 × M + U + V` と新方式 `10 × M + 1 × 価値合計差 + V` を同条件で比べるのが、改善仮説を直接確かめる主線の次段階だからである。これはアシスタントの推薦理由で、本人の選定理由とは区別する。
- [選択済み] 2026-11-02、本人は比較指標の範囲として「組得点＋固定局面の作用確認」を選んだ。対局中の捕獲状況は追加指標に含めない。この範囲選択は設計案・実施計画案全体の承認ではない。
- [提案済み] 比較条件・局面群・方式名・試行数・統計方法を記した[設計案](plans/2026-11-02-undefended-piece-value-comparison-design.md)と[実施計画案](plans/2026-11-02-undefended-piece-value-comparison-implementation-plan.md)を用意した。旧U/Vの比較条件は自動流用せず、組得点と固定局面の作用確認を分け、一般局面での棋力向上を結論しない。両案とも本人の明示承認待ち。
- `M` は駒得、`U` は旧方式の支えのない被攻撃駒の枚数差、`V` は支えあり低価値駒脅威の枚数差と、日本語の意味を必ず添える。
- ShogiHomeでのU候補実践はPCへアクセス可能との本人連絡後に再提案する保留目標。角の可動性は本人希望で後回し。A番号は割り当てない。

## 現在の物理的状態

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`。
- 次テーマ用ブランチ：`codex/undefended-piece-value-comparison`。`main` / `origin/main` の `9a44a277` から、同じリポジトリ内で作成した。追加worktree・別cloneは使わない。引き継ぎ・選定記録はこのブランチにだけコミットする。次テーマのmain統合とpushは未実施で、それぞれ別途本人承認を待つ。再開時に実際のHEAD・ブランチ・作業ツリーを確認する。
- このブランチには比較設計案・実施計画案と現在地文書を記録した。製品コード・テスト・比較CLI・局面・seed・対局条件は変更していない。
- 最新の製品検証はmain統合後の全1,054テスト・87モジュール・24.711秒。今回の変更は文書のみで、文書変更後の製品テストは再実行していない。
- `main` と `origin/main` は引き継ぎ作成開始時点で `9a44a277`。次テーマの実装・比較・統合・pushは未着手であり、main統合とpushはそれぞれ別途本人承認を待つ。
- 保護対象を変更しない。`.agents/tasks/`、未追跡比較データ、C2保護4件、`migration-preservation-2026-11-01/` と `worktree-preservation-2026-11-01/` の退避物は保持する。現在のstatusには `.antigravity/tasks/`、複数の `.venv.backup-*`、C1比較データと上記退避ディレクトリが未追跡で表示されている。

## 次の具体的な行動

1. セッション開始時に `/Users/oki2a24/kaname-shogi` で次を順に実行し、引き継ぎ記述と現物を照合する：
   - `git status --short --branch`
   - `git log -3 --oneline --decorate`
   - `git branch --show-current`
   - `git rev-parse main`
   - `git rev-parse HEAD`
   - `git worktree list`
   その後、開発環境の準備に進む前に `.venv/bin/ruff --version`、`git config --local --get core.hooksPath`、`.venv/bin/python --version` を確認する。不足・不一致時はREADMEの手順を使い、グローバル設定を変えない。
2. `AGENTS.md`、`docs/resume.md`、本書、`docs/next-topics.md`、`docs/roadmap-non-material-position-evaluation.md`、`docs/README.md`、`README.md`、`docs/02-project-direction.md` を確認する。前テーマの統合で利用可能なCLI/USI機能や長期方針を変更していないが、比較CLIの利用方法・現行仕様はREADMEと現行コードで再確認する。
3. `docs/knowledge/undefended-piece-value.md`、`docs/learning/undefended-piece-value.md`、承認済みの `docs/plans/2026-11-02-undefended-piece-value-design.md` と `docs/plans/2026-11-02-undefended-piece-value-implementation-plan.md` を読み、現在の評価式と未検証事項を確認する。
4. `kaname_shogi/comparison.py` と比較関連モジュールの実在する比較CLI入口・方針選択・評価注入経路を調べ、関連コードとテストを現物で特定する。現時点で見つかっている入口・関連契約は `kaname_shogi/material_piece_threat_value.py`、`kaname_shogi/material_undefended_piece.py`、`kaname_shogi/material_piece_threat.py`、`kaname_shogi/supported_piece_threat.py`、`tests/test_piece_threat_comparison_policy.py`、`tests/test_piece_threat_comparison_pipeline.py`、`tests/test_undefended_piece_comparison_positions.py`、`tests/test_undefended_piece_comparison_pipeline.py`。ファイルの役割と接続可否は再開時のコードで確認し直す。
5. `docs/plans/2026-11-02-undefended-piece-value-comparison-design.md` と `docs/plans/2026-11-02-undefended-piece-value-comparison-implementation-plan.md` を本人と確認する。比較指標の範囲は本人が「組得点＋固定局面の作用確認」と選択済みで、対局中の捕獲状況は追加しない。
6. 設計案・実施計画案全体について本人の明示承認を待つ。承認前にTDD、製品コード・テスト変更、局面・seed作成、比較CLI接続、対局実行を始めない。main統合とpushは各々別途承認を待つ。

## 再開用プロンプト

> `/Users/oki2a24/kaname-shogi` の `codex/undefended-piece-value-comparison` で、本人が選んだ「支えのない被攻撃駒の価値を比較CLIへ接続して比較する」を再開してください。最初に `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`、`git rev-parse main`、`git rev-parse HEAD`、`git worktree list` を順に実行し、`AGENTS.md`、`docs/resume.md`、この引き継ぎと現物を照合してください。続いて `.venv/bin/ruff --version`、`git config --local --get core.hooksPath`、`.venv/bin/python --version` を確認し、不足時はREADMEの手順に従ってください。本人は比較指標の範囲として「組得点＋固定局面の作用確認」を選択済みで、対局中の捕獲状況は追加指標に含めません。`README.md`、`docs/README.md`、`docs/next-topics.md`、`docs/roadmap-non-material-position-evaluation.md`、前テーマの知識・学習・承認済み設計計画、比較CLIの現行コード・関連テスト・比較知識メモを確認してください。[比較設計案](plans/2026-11-02-undefended-piece-value-comparison-design.md)と[実施計画案](plans/2026-11-02-undefended-piece-value-comparison-implementation-plan.md)を読み、質問は一問ずつにして、未解決の設計判断があれば確認してください。以前のU/V比較条件は自動流用しません。保護対象の未追跡比較データ、`.agents/tasks/`、C2保護4件と退避アーカイブを変更しないでください。別worktree・別cloneを使わず、このディレクトリ内のブランチで作業してください。両案の明示承認を待ち、承認前にTDD、製品コード・テスト変更、局面・seed作成、実装、比較実行を始めないでください。A番号を予約しないでください。ShogiHomeでのU候補実践はPCアクセス可能との本人連絡後に再提案する保留目標です。main統合とpushはそれぞれ別途承認を待ってください。`
