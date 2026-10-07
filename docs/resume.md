# 学習・開発の再開案内

## 現在地

第67回「SFEN局面変換」は、実装・独立レビュー・main統合・全326テスト・最終理解確認まで完了した。SFENの読込・正規化書出しとUSI `position sfen` 単独・指し手付き指定に対応している。手数は `SfenPosition` に保持し、JSON棋譜形式は変更していない。統合時のHEADは `8421492`。後続の文書コミットは `9036e2c` と `684d406` で、リモートへpushしていない。

本人は次テーマに第68回予定「ShogiHome画面へのSFEN貼り付け確認」を選び、新セッションの準備を依頼した。第68回の範囲・入力例・操作方法・期待表示は未合意で、ShogiHomeの画面操作も未承認。コード・テスト変更、実機確認は始めていない。テーマの選定だけでShogiHome操作の承認と扱わず、具体的な操作案を提示して明示承認を待つ。

引き継ぎ準備開始時は `/Users/oki2a24/kaname-shogi` の `main`、HEAD `684d406`、`origin/main` より8コミット先行、作業ツリーはクリーンだった。今回の引き継ぎコミット後の正確なHEAD・ahead数は、次セッションでGitコマンドを実行して確認する。コードの全326テストは `8421492` で成功し、その後は文書のみの変更でテストを再実行していない。

過去のShogiHome実機観察はmacOS版1.28.1だが、現在の版・画面・登録先・棋譜状態・稼働セッションは不明である。前回の画面状態を引き継いだとみなさず、実機操作の承認後に現物を確認する。[ShogiHome接続手順書](shogihome-connection-guide.md)と[接続スキル](../.agents/skills/shogihome-connection/SKILL.md)には、エンジンが `position startpos moves ...` のみ受け付けるという更新前の記述が残る。今回のテーマは画面貼り付けに限定し、エンジン接続・対局へ広げない。

## 確認記録

- [第67回学習記録](learning/67-sfen-position-conversion.md)：設計選択、実装、レビュー、テスト、本人回答と補足、未確認事項。
- [SFEN局面表記の確定知識](knowledge/sfen-position-notation.md)：現在のAPI、変換規則、検証範囲。
- [第68回予定テーマの引き継ぎ](handover-shogihome-sfen-paste.md)：選定理由、開始時Git状態、未合意事項、読む資料、再開用プロンプト。
- [次テーマ候補と選定履歴](next-topics.md)：第68回の選定と後続候補。
- [ShogiHome接続手順書](shogihome-connection-guide.md)と[接続スキル](../.agents/skills/shogihome-connection/SKILL.md)：画面操作を検討するときの停止条件と運用上の注意。

## 再開時に行うこと

まず次を実行して、現在の状態を過去の引き継ぎから推測せず確認する。

```sh
git status --short --branch
git log -3 --oneline
```

その後、[AGENTS.md](../AGENTS.md)、ルートの[README](../README.md)、[文書索引](README.md)、本書、[第68回予定テーマの引き継ぎ](handover-shogihome-sfen-paste.md)、[次テーマ候補](next-topics.md)、[プロジェクトの方向性](02-project-direction.md)を読む。続けて第67回学習記録とSFEN確定知識、ShogiHome接続手順書・スキルを読み、コード実装済みの事実と実機未確認の境界を確認する。

`superpowerssuperpowers:brainstorming` と `superpowerssuperpowers:roadmap-management` を使って対象・表現・確認方法を一問ずつ決める。実機操作の具体案を提示して明示承認を得るまでShogiHomeを操作しない。新しいセッションへ進むときは、本書内の再開用プロンプトを本人が入力する。
