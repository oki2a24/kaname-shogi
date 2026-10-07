# 学習・開発の再開案内

## 現在地

第67回「SFEN局面変換」は、実装、独立レビュー、全体検証、`main` 統合、最終理解確認まで完了した。統合時の `main` HEAD は `8421492` で、統合後に全326テストが成功した。コードレビューの修正後指摘はCritical・Important・Minorともに0件。今回の変更をリモートへpushしていない。

SFENの読込・正規化書出し、USI `position sfen` 単独指定と `moves` 付き指定に対応した。省略手数は1として扱い、手数は `SfenPosition` に保持する。JSON棋譜形式は変更していない。最終理解確認で本人は「責任を分離を維持するため」と回答した。SFENをShogiHome画面へ貼り付ける操作や、ShogiHomeからSFEN局面を使った実エンジン対局は未確認である。

次テーマは未選定。候補と推薦理由は[次テーマ候補](next-topics.md)に記録した。本人がテーマを選ぶまで、新しい学習・実装へ進まない。

## 確認記録

- [第67回学習記録](learning/67-sfen-position-conversion.md)：設計選択、実装、レビュー、テスト、本人回答と補足、未確認事項。
- [第67回設計仕様](plans/2026-10-07-sfen-position-conversion-design.md)と[実装計画](plans/2026-10-07-sfen-position-conversion-implementation-plan.md)：承認された範囲と実施記録。
- [SFEN局面表記の確定知識](knowledge/sfen-position-notation.md)：現在のAPI、変換規則、検証範囲。
- [次テーマ候補](next-topics.md)：小さい順の候補、推薦、未選定状態。
- [ShogiHome接続手順書](shogihome-connection-guide.md)と[専用スキル](../.agents/skills/shogihome-connection/SKILL.md)：今後ShogiHomeを操作する場合の手順。

## 再開時に行うこと

現在状態は過去の記録から推測せず、次を実行して確認する。

```sh
git status --short --branch
git log -3 --oneline
```

その後、`README.md`、この案内、[文書索引](README.md)、[プロジェクトの方向性](02-project-direction.md)、[次テーマ候補](next-topics.md)を確認する。`8421492` はSFEN実装を `main` に統合した時点のコミットであり、現在のHEADは上記コマンドで確認する。

## 次に読むファイル

1. [AGENTS.md](../AGENTS.md)、ルートの[README](../README.md)、[文書索引](README.md)、本書、[次テーマ候補](next-topics.md)、[プロジェクトの方向性](02-project-direction.md)
2. 選んだ次テーマに対応する一次資料、確定知識、現行コード、関連テスト
3. ShogiHome実機操作を選ぶ場合は、[接続手順書](shogihome-connection-guide.md)と[専用スキル](../.agents/skills/shogihome-connection/SKILL.md)を確認し、範囲・手順・確認方法を決めてから明示承認を得る。

テーマの候補を選ぶまでは、次の学習・実装を始めない。
