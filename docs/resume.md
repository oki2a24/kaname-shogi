# 学習・開発の再開案内

## 現在地

第64回「承認済み難易度選択設計を実装する」は、実装、レビュー、記録、`main` への取り込み、取り込み先の検証、最終理解確認まで完了した。現在の作業先は `main`。実装コミットは `082a802`、開始時の引き継ぎコミット `859742d` も `main` に含まれる。ローカルの `main` には未pushのコミットがあり、作業ツリーは再開時に確認する。

全体検証 `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` は、実装ブランチと取り込み後の `main` でそれぞれ305テストが成功した。独立レビュー再確認はCritical・Important・Minorがすべて0件。学習記録・知識メモの確認も完了した。

一様ランダムは最弱・既定値として維持される。CLIはコンピュータ参加対局の開始前に方針を選び、USIは `Difficulty` comboの `Random` / `Material` を使う。駒得評価は谷川浩司さんの参考値を用いて合法手一手後の盤上・持ち駒合計差を比べる。玉将を除外し、取った成駒は基本駒の持ち駒値へ戻し、同点はランダムに選ぶ。

第65回「ShogiHomeでDifficulty設定を確認する」は、実機観察と最終理解確認まで完了した。ShogiHome 1.28.1の設定画面に `Random` / `Material` が表示され、MaterialがUSI `setoption` で送信されることを確認した。Randomは画面で選択されていたが、既定値と同じため明示的な `setoption` はログで確認できなかった。指し手を進めていないため、Material時の着手の違いは未確認。DifficultyはRandom、USI通信ログは開始前と同じOFFへ復帰し、監視欄はUSI 0件・CSA 0件。観察範囲と最終理解確認は[第65回学習記録](learning/65-shogihome-difficulty-verification.md)を参照する。

本人は第66回予定テーマに「ShogiHomeでMaterialの着手への影響を確認する」を選び、新しいセッションの準備を依頼した。Random・Materialの両方で終局まで進み正常終了も確認したいという希望があるが、具体的な比較局面、対局手順、時計、終局条件、棋譜・ログ採取は未合意。希望をそのまま実行範囲と扱わず、次のセッションで一問ずつ設計する。実機操作の前に手順を提示し、別途明示承認を得る。[第66回予定テーマの引き継ぎ](handover-shogihome-material-move-effect.md)を参照。

## 確認記録

- [第64回学習記録](learning/64-weakest-mode-difficulty-selection-implementation.md)：最終理解確認の本人回答と補足を記録。
- [第65回学習記録](learning/65-shogihome-difficulty-verification.md)：ShogiHome画面とUSIログの観察結果、本人回答と補足を記録。
- [第64回の実装計画](plans/2026-10-05-weakest-mode-difficulty-selection-implementation-plan.md)：TDD、Refactor、独立レビュー、取り込み先検証の実績。
- [承認済み設計](plans/2026-10-05-weakest-mode-difficulty-selection-design.md)、[一手選択の知識](knowledge/31-weak-move-selection.md)、[USI応答の知識](knowledge/usi-engine-response.md)。
- 第65回は本人が合意した範囲で実機確認済み。操作前の別途承認を得て、確認用の棋譜は本人承認後に破棄した。確認時の画面・ログと設定復帰の詳細は[第65回学習記録](learning/65-shogihome-difficulty-verification.md)を参照する。

## 再開時に行うこと

現在状態は過去の記録から推測せず、次を実行して確認する。

```sh
git status --short --branch
git log -3 --oneline
```

その後、第66回予定テーマの開始条件を[引き継ぎ](handover-shogihome-material-move-effect.md)で確認する。引き継ぎ文書は対応テーマ開始時点の履歴であり、現在のGit状態を示すものではない。

## 次に読むファイル

1. [AGENTS.md](../AGENTS.md)、[README](../README.md)、[文書索引](README.md)、この案内、[次テーマ候補](next-topics.md)、[プロジェクト方向性](02-project-direction.md)、[第65回学習記録](learning/65-shogihome-difficulty-verification.md)、[第66回予定テーマの引き継ぎ](handover-shogihome-material-move-effect.md)
2. [ShogiHome接続スキル](../.agents/skills/shogihome-connection/SKILL.md)、[ShogiHome接続手順書](shogihome-connection-guide.md)、[USIエンジン応答の知識](knowledge/usi-engine-response.md)
3. 第64回からの経緯が必要なら[学習記録](learning/64-weakest-mode-difficulty-selection-implementation.md)と[承認済み設計](plans/2026-10-05-weakest-mode-difficulty-selection-design.md)

新しいセッションでは、引き継ぎ内の再開用プロンプトを本人が入力してから次テーマを始める。プロンプトを入力しただけではShogiHome実機操作の承認にならない。
