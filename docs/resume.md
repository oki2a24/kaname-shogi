# 学習・開発の再開案内

## 現在地

第58回「USIコマンド型・独立状態APIの導入要否を再検討する」は、実装・独立レビュー・学習記録・最終理解確認まで完了した。変更は2026-10-04に `main` へfast-forwardで取り込まれ、取り込み後の全281テストが成功した。USIコマンド行は文字列分岐を維持し、非公開 `_UsiEngineState` は `Position` または未設定の `None` だけを保持する。

第59回「ShogiHomeで平手対局する」は、実装・検証・ShogiHome 1.28.1での限定対局まで進み、2026-10-04に `codex/shogihome-gameplay` のコミット `d7046c6` を元の `/Users/oki2a24/kaname-shogi` の `main` へfast-forwardで取り込んだ。人間先手の７六歩に対して `kaname-shogi` が４四歩、人間の２六歩に対して９二飛を返し、ShogiHomeの盤面・棋譜へ反映された。人間の投了後、画面に「対局終了（投了）」が表示され、棋譜にも投了が記録された。取り込み先の全283テストと独立コードレビューの再確認も成功した。

第59回の最終理解確認への本人の回答とアシスタントの補足を[学習記録](learning/59-shogihome-even-game.md)へ記録した。第60回「息子によるShogiHome試用」は2026-10-04に実施し、平手・息子先手で19手、エンジンの18応手を棋譜上で確認した。約3手のチェックポイントでユーザーが続行を伝えた。対局終盤には息子が「最初鳥から端角で来て、角の頭を狙ったところあたりから少し良くなった。」と自発的に述べた。最後は息子が投了操作をしておらず、エンジン側の番で「対局終了（投了）」となった。最終理解確認では、第54回と異なり今回は開始から終局まで対局し、投了をエンジンが行ったことが違いだと回答した。補足を[第60回学習記録](learning/60-shogihome-son-trial.md)へ記録した。

第59・60回の根拠と未確認事項は[第59回学習記録](learning/59-shogihome-even-game.md)、[第60回学習記録](learning/60-shogihome-son-trial.md)、[ShogiHome対局知識](knowledge/usi-shogihome-gameplay.md)を参照する。USI通信ログは有効にしていないため、ShogiHomeが第60回に実際に送信したコマンド列や最終応答のUSI文字列、時計動作は未確認である。

第61回「ShogiHome自動投了時のUSI通信を確認する」では、37手の局面からShogiHomeが送った `position` と `go` に対し、エンジンが `bestmove resign` を返し、その後ShogiHomeが `gameover lose`、`quit` を送る一例を実機ログで確認した。第54回の使い捨てプローブ、第55〜58回のローカル実装・テスト、第59回の通常応手と人間投了、第60回の画面・棋譜だけの自動投了とは証拠を分けて記録した。第61回の理解確認への本人回答とアシスタント補足は[学習記録](learning/61-shogihome-auto-resign-logs.md)に記録済みである。コード・テスト変更はなく、テストも実行していない。USIログ設定はOFFへ戻して再起動し、登録ランチャー `/Users/oki2a24/kaname-shogi/kaname-shogi-usi` とPonder OFFをShogiHome上で確認した。通信ログ原本とKIFの所在は次テーマの引き継ぎに記録する。

現在は `main`（最終確認時点で `origin/main` より6コミット先行、HEAD `1429e34`）で文書の未コミット変更がある。コード・テストに変更はない。`.git` 内のrefを書けず作業ブランチを作成できなかった過去の制約がある。再開時の `git status --short --branch` と `git log -3 --oneline` を必ず取り直し、文書の内容確認後にコミットを扱う。本人は次テーマとして「ShogiHome接続手順書を作成する」を選び、新しいセッションを依頼した。

## 第59回を始めた際の資料

再開時には `git status --short --branch` と `git log -3 --oneline` を確認し、作成時点の引き継ぎと現在の状態を区別した。第59回の再開依頼文は[引き継ぎ](handover-usi-shogihome-gameplay.md)に保存されている。一次資料は[USI原案](https://hgm.nubati.net/usi.html)と[ShogiHome公式資料](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E7%99%BB%E9%8C%B2%E6%89%8B%E9%A0%86)を参照する。

## 次テーマを始める手順

本人は「ShogiHome接続手順書を作成する」を次テーマに選び、新しいセッションの準備を依頼した。選定理由、完了事項、物理状態、次に読む資料、未決定の設計点、再開用プロンプトは[引き継ぎ](handover-shogihome-connection-guide.md)に記録する。第61回学習記録と既存文書は未コミットである。本人が再開用プロンプトを新しいセッションへ入力するまで、接続手順書の調査・作成を開始しない。
