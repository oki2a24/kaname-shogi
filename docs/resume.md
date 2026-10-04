# 学習・開発の再開案内

## 現在地

第58回「USIコマンド型・独立状態APIの導入要否を再検討する」は、実装・独立レビュー・学習記録・最終理解確認まで完了した。変更は2026-10-04に `main` へfast-forwardで取り込まれ、取り込み後の全281テストが成功した。USIコマンド行は文字列分岐を維持し、非公開 `_UsiEngineState` は `Position` または未設定の `None` だけを保持する。

第59回「ShogiHomeで平手対局する」は、実装・検証・ShogiHome 1.28.1での限定対局まで進み、2026-10-04に `codex/shogihome-gameplay` のコミット `d7046c6` を元の `/Users/oki2a24/kaname-shogi` の `main` へfast-forwardで取り込んだ。人間先手の７六歩に対して `kaname-shogi` が４四歩、人間の２六歩に対して９二飛を返し、ShogiHomeの盤面・棋譜へ反映された。人間の投了後、画面に「対局終了（投了）」が表示され、棋譜にも投了が記録された。取り込み先の全283テストと独立コードレビューの再確認も成功した。

第59回の最終理解確認への本人の回答とアシスタントの補足を[学習記録](learning/59-shogihome-even-game.md)へ記録した。次テーマとして本人は **「息子によるShogiHome試用」** を選び、「息子がShogiHomeの画面から人間として指し、`kaname-shogi` が応じる」意味だと確認した。先後・試用の長さ・終了方法・感想の確認方法はまだ決めていない。テーマは選定済みだが、実対局の範囲・手順・確認方法を新しいセッションで設計し、試用前に明示承認を得る。

第59回の根拠と未確認事項は[学習記録](learning/59-shogihome-even-game.md)、限定対局で確かめた事実は[知識メモ](knowledge/usi-shogihome-gameplay.md)、変更・検証の手順は[実装計画](plans/2026-10-04-shogihome-gameplay-implementation-plan.md)を参照する。USI通信ログは有効にしていないため、ShogiHomeが今回実際に送信したコマンド列や時計動作は未確認である。

第60回予定テーマの開始手順と再開用プロンプトは[引き継ぎ](handover-son-shogihome-trial.md)に記録した。第59回は作業ワークツリーのランチャーを登録していたが、そのワークツリーはアーカイブ済みで旧ランチャーパスは存在しない。安定した `/Users/oki2a24/kaname-shogi/kaname-shogi-usi` は存在するため、新セッションでShogiHomeの登録先とPonder設定を実際に確認する。

## 第59回を始めた際の資料

再開時には `git status --short --branch` と `git log -3 --oneline` を確認し、作成時点の引き継ぎと現在の状態を区別した。第59回の再開依頼文は[引き継ぎ](handover-usi-shogihome-gameplay.md)に保存されている。一次資料は[USI原案](https://hgm.nubati.net/usi.html)と[ShogiHome公式資料](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E7%99%BB%E9%8C%B2%E6%89%8B%E9%A0%86)を参照する。

## 第60回予定テーマを始めるとき

新しいセッションでは、まずGit状態を確認し、[第60回予定テーマの引き継ぎ](handover-son-shogihome-trial.md)と現在の記録を読む。USI一次資料、ShogiHome公式資料、現行コード・テスト、実際のShogiHome登録状態を確認した後、`superpowerssuperpowers:brainstorming` で試用の範囲を一問ずつ相談する。実機で試す前に範囲・手順・確認方法の明示承認を得る。コード・テスト変更が必要なら、先に実装計画を作成して明示承認を得る。
