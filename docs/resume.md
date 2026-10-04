# 学習・開発の再開案内

## 現在地

第58回「USIコマンド型・独立状態APIの導入要否を再検討する」は、実装・独立レビュー・学習記録・最終理解確認まで完了した。変更は2026-10-04に `main` へfast-forwardで取り込まれ、取り込み後の全281テストが成功した。USIコマンド行は文字列分岐を維持し、非公開 `_UsiEngineState` は `Position` または未設定の `None` だけを保持する。ShogiHomeでの実対局はロードマップ第5項に残っている。

第58回の内容と本人の回答は[学習記録](learning/58-usi-command-state-api-review.md)、現在のUSI契約は[確定知識](knowledge/usi-engine-response.md)、設計と実績は[設計仕様](plans/2026-10-04-usi-command-state-api-review-design.md)および[実装計画](plans/2026-10-04-usi-command-state-api-review-implementation-plan.md)にある。

## 次に行うこと

本人は次テーマにロードマップ第5項 **「ShogiHomeで平手対局する」** を選び、新しいセッションの準備を依頼した。選定理由、完了した前提、未確認の実機挙動、再開用プロンプトは[第59回の引き継ぎ](handover-usi-shogihome-gameplay.md)を参照する。人間がそのプロンプトを新しいセッションへ入力するまで、実対局の調査・学習・実装は始めない。

再開時は最初に `git status --short --branch` と `git log -3 --oneline` を実行し、作成時点の記録と現在のGit状態を区別する。ShogiHome実対局までの到達条件は[USI接続ロードマップ](roadmap-usi-shogihome.md)を参照する。

## 第59回を始めるとき

次の文を新しいセッションへ入力する。内容と開始時の資料は[第59回の引き継ぎ](handover-usi-shogihome-gameplay.md)にある。

> kaname-shogi の次テーマ「ShogiHomeで平手対局する」を始めてください。最初に `git status --short --branch` と `git log -3 --oneline` で現在状態を確認し、`AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/02-project-direction.md`、`docs/roadmap-usi-shogihome.md`、`docs/handover-usi-shogihome-gameplay.md`、第54〜58回の学習記録、USI関連の知識メモ・設計仕様・実装計画を読んでください。USI一次資料とShogiHome公式資料を確認し、第54回の使い捨てプローブで観測した一例、第55〜58回のローカル実装、未確認のShogiHome挙動を区別してください。`superpowerssuperpowers:brainstorming` を使い、一次資料と既存コードを確認してから設計を一問ずつ相談してください。実対局の範囲・手順・確認方法を設計案として提示し、明示的な承認を待ってください。コードやテストの変更が必要なら、実装計画を作成して提示し、承認前に変更しないでください。仕様や実機一例から未確認のコマンド要件を推測せず、ShogiHome上で `kaname-shogi` が合法な応手を返す通常の平手対局と終了を確認してください。
