# 学習・開発の再開案内

## 現在地

第67回「SFEN局面変換」は実装・独立レビュー・main統合・全326テスト・最終理解確認まで完了した。第68回「ShogiHome画面へのSFEN貼り付け確認」では、ShogiHome 1.28.1の画面へ同じ3手後局面の4欄SFENと3欄SFENを貼り付け、どちらも盤面・後手番・持ち駒なしが期待どおり表示された。最終画面は3欄局面の未保存新規棋譜。ShogiHomeから `kaname-shogi` へのUSI `position sfen` 送信・エンジン応答は未確認である。本人の理解確認回答も記録した。

次テーマは未選定。候補と推薦理由は[次テーマ候補](next-topics.md)に記録した。本人が選ぶまで新しい学習・実機操作・実装へ進まない。

再開準備開始時は `/Users/oki2a24/kaname-shogi` の `main`、HEAD `684d406`、作業ツリーはクリーンだった。第68回の引き継ぎコミット後、文書草案を更新する前のHEADは `5ad3a4d` で `origin/main` と同じだった。現在は第68回記録等の文書変更が未コミットであり、内容確認・承認後にコミットする。コードとテストは変更しておらず、今回テストを実行していない。第67回の全326テストは `8421492` 時点の結果である。

第68回の画面観察時はShogiHome 1.28.1、USIエンジン0、CSAサーバー0だった。現在の画面状態は将来の再開時に推測せず現物確認する。[ShogiHome接続手順書](shogihome-connection-guide.md)と[接続スキル](../.agents/skills/shogihome-connection/SKILL.md)には `position startpos moves ...` のみ対応するという古い記述が残る。これは今回確認したGUI貼り付けとは別のエンジン通信上の未確認事項である。

## 確認記録

- [第67回学習記録](learning/67-sfen-position-conversion.md)：設計選択、実装、レビュー、テスト、本人回答と補足、未確認事項。
- [SFEN局面表記の確定知識](knowledge/sfen-position-notation.md)：現在のAPI、変換規則、検証範囲。
- [第68回学習記録](learning/68-shogihome-sfen-paste.md)：4欄・3欄SFENの画面貼り付け結果、未確認事項、本人回答と補足。
- [第68回予定テーマの引き継ぎ](handover-shogihome-sfen-paste.md)：開始時のGit状態と、開始前計画・実施結果。
- [次テーマ候補と選定履歴](next-topics.md)：第68回の選定と後続候補。
- [ShogiHome接続手順書](shogihome-connection-guide.md)と[接続スキル](../.agents/skills/shogihome-connection/SKILL.md)：画面操作を検討するときの停止条件と運用上の注意。

## 再開時に行うこと

まず次を実行して、現在の状態を過去の引き継ぎから推測せず確認する。

```sh
git status --short --branch
git log -3 --oneline
```

その後、[AGENTS.md](../AGENTS.md)、ルートの[README](../README.md)、[文書索引](README.md)、本書、第68回学習記録、[次テーマ候補](next-topics.md)、[プロジェクトの方向性](02-project-direction.md)、[SFEN確定知識](knowledge/sfen-position-notation.md)、ShogiHome接続手順書・スキル・ロードマップを読む。画面貼り付け確認とUSIエンジン連携の未確認境界を保つ。

第68回の記録草案は未コミットである。本人の確認・承認後に文書をコミットする。次テーマは本人が選ぶまで開始せず、ShogiHome操作が含まれる場合は接続手順書・専用スキルを読み、具体案を提示して明示承認を得る。
