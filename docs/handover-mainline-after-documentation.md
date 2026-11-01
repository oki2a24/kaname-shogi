# セッション引き継ぎ：文書整理後に主線へ戻る

作成日：2026-11-01。本人は文書整理の最後の理解確認後、候補1「主線に戻る」を選択した。これは「次の非駒得評価項目を一つ選び、学び、設計する」という主線への復帰であり、具体的な評価項目の選定・設計・実装計画・実装の承認ではない。選定理由は聞いていないため推測しない。

## 最終目標と再開の範囲

駒得以外の評価を一項目ずつ育てる主線に戻り、現行評価と候補を照合した後、本人が次に学ぶ具体的な一項目を選ぶ。候補ごとの重複、独立期待値、代表局面、測定可能な改善仮説と限界を考え、必要な確認は一度に一問ずつ行い、本人の回答・選択を待つ。角の可動性、成りに近づく進行度、選んだ重要マスへの利き、「駒の働き・活性度」はいずれも選定済みではない。A番号は予約しない。

項目選択後は日本将棋連盟などの一次資料を優先して学習し、現行コードを照合し、設計案と具体的な実施計画を提示する。計画を文書化・提示した後は本人の明示承認を待ち、承認前にTDD・製品コード・テスト変更・実装へ進まない。開発・テスト設計へ入る場合は `~/.codex/observations/test-driven-development.md` と `docs/knowledge/test-coverage-review.md` を確認する。

## 背景と完了事項

- A1/B1の飛車可動性はC1比較を2回行い、いずれも指定条件では改善・悪化を判断できず一旦区切った。A2/B2/C2の玉周辺安全度はC2の登録4局面・指定条件で悪化を支持した。一般棋力の結論ではない。
- Uは実装・比較・通常CLI/USI接続まで完了。Vは通常CLI候補7とUSI `MaterialSupportedPieceThreat` に接続済みで、固定6局面・一手選択・指定条件で改善を支持したが、一般局面への棋力向上は示さない。U/Vの詳細と本人の回答は[Uの記録](learning/undefended-piece-coordination-evaluation.md)、[Vの記録](learning/supported-piece-lower-value-threat.md)を参照。
- 文書整理では入口と現行知識を照合し、[文書整理スキル](../.agents/skills/documentation-maintenance/SKILL.md)と[文書更新ガイド](documentation-guide.md)を整えた。本人は最後の確認に「どちらか一方の確認だけでは不足だから」と回答。リンク先の存在と内容の現行性は別々に確認する補足を[学習記録](learning/workspace-knowledge-consolidation.md#最後の理解確認2026-11-01)へ保存した。
- 文書整理は本人の依頼によりmainへ統合し、GitHubへpush済み。統合先の全体テストは1039件・84モジュール・25.282秒、Ruff整形・lint・差分確認が成功した。これは前テーマの実測であり、次テーマの検証結果ではない。
- 本人は「今後ワークツリーを使わない」「作業は `/Users/oki2a24/kaname-shogi`、開発は同じディレクトリの作業ブランチ」を指定した。既存worktreeは保護物を保存し、本人の例外承認後に削除した。[退避経緯](learning/workspace-knowledge-consolidation.md)とGit状態を参照。
- ShogiHomeでのU候補実践は、遠隔PCへアクセス可能と本人が知らせた後に条件を再提案する保留帰還目標。アクセス可能の連絡自体も対局実施の承認ではない。
- 通常CLIで選択できる方式を将来追加・変更する場合、別指定がなければCVCを2局以上、可能な限り先後を入れ替えて完局し、開始前表示・双方の実着手・終局を確認する。少数局の勝敗を棋力の根拠にしない。

## 物理状態と保護対象

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`。引き継ぎ作成branch：`codex/next-evaluation-after-docs`。別worktreeや別cloneを作らない。
- 作成開始時のmain・HEAD・ローカル `origin/main` は `9b72404ea7880216e61d4aaff970cff1c51c2a12`。この数値は開始時点であり、再開時は現物を測る。GitHubの現在値は必要な場合に直接確認し、推測しない。
- 未追跡 `.antigravity/tasks/`、既存 `.venv.backup-*`、`data/comparison/runs/` のC1比較データ、`migration-preservation-2026-11-01/`、`worktree-preservation-2026-11-01/` は保持する。C2保護4件と `.agents/tasks/` を含む旧worktreeの退避tarは `worktree-preservation-2026-11-01/b2-main-integration.tar` にあり、移動・削除・上書き・一括ステージしない。
- 旧[引き継ぎ](handover-mainline-next-evaluation-item.md)の `/private/tmp/kaname-shogi-main-integration-clone` とそのbranch・Git状態は作成時の履歴で、現在の作業場所ではない。旧cloneは本人承認後に退避・削除した。
- main統合とpushは、それぞれ本人の別途承認を待つ。

## 次セッションでの行動

1. 次のプロンプトを受け取ったら、指定ディレクトリで `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`、`git rev-parse main`、`git rev-parse HEAD`、`git worktree list` を順に実行する。`AGENTS.md`、[再開案内](resume.md)、本書を現物と照合する。
2. [次テーマ候補](next-topics.md)、[非駒得評価ロードマップ](roadmap-non-material-position-evaluation.md)、[プロジェクトの方向性](02-project-direction.md)、README、[文書索引](README.md)、現行の評価コード・関連テスト・知識メモを必要な範囲で確認する。文書整理スキルの自動発見が新セッションで確認できた場合は結果を区別して記録する。これは本主線と別にテーマを始める許可ではない。
3. `superpowerssuperpowers:brainstorming` を使い、具体的な評価項目を本人が選ぶまで対話する。前セッションで提示した候補表は比較の出発点であり、決定済みの設計や改善実績と扱わない。
4. 選択後、一次資料に基づき一項目を学び、代表局面・独立期待値・既存評価との重複・改善仮説・検証方法を設計する。実装計画を提示して承認待ちとし、承認前に実装しない。

## 再開用プロンプト

> `/Users/oki2a24/kaname-shogi` の `codex/next-evaluation-after-docs` で、主線「次の非駒得評価項目を一つ選び、学び、設計する」を再開します。まず `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`、`git rev-parse main`、`git rev-parse HEAD`、`git worktree list` を順に実行し、`AGENTS.md`、`docs/resume.md`、`docs/handover-mainline-after-documentation.md` と現物を照合してください。本人は主線へ戻ることを選びましたが、具体的な評価項目は未選定です。`docs/next-topics.md`、`docs/roadmap-non-material-position-evaluation.md`、`docs/02-project-direction.md`、README、`docs/README.md`、現行の評価コード・関連テスト・知識メモを確認してください。`superpowerssuperpowers:brainstorming` を使い、既存評価との重複、独立期待値、代表局面、測定可能な改善仮説を比較し、確認は一問ずつ行って本人の選択を待ってください。候補を選定済みと扱わず、A番号も予約しないでください。選定後は一次資料に基づき学習・設計し、実施計画を提示して明示承認を待ってください。承認前にTDD、製品コード・テスト変更、実装を始めないでください。ShogiHomeでのU候補実践はアクセス可能との本人連絡後に再提案する保留目標です。作業はこのディレクトリ内のブランチで行い、別worktreeや別cloneは使いません。未追跡の比較データ、`.agents/tasks/`、C2保護4件と退避アーカイブは変更しないでください。main統合とpushはそれぞれ別途承認を待ちます。すべて日本語で進めてください。
