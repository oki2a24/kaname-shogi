# 学習・開発の再開案内

## 現在地

第64回「承認済み難易度選択設計を実装する」は、実装、レビュー、記録、`main` への取り込み、取り込み先の検証、最終理解確認まで完了した。現在の作業先は `main`。実装コミットは `082a802`、開始時の引き継ぎコミット `859742d` も `main` に含まれる。ローカルの `main` には未pushのコミットがあり、作業ツリーは再開時に確認する。

全体検証 `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` は、実装ブランチと取り込み後の `main` でそれぞれ305テストが成功した。独立レビュー再確認はCritical・Important・Minorがすべて0件。学習記録・知識メモの確認も完了した。

一様ランダムは最弱・既定値として維持される。CLIはコンピュータ参加対局の開始前に方針を選び、USIは `Difficulty` comboの `Random` / `Material` を使う。駒得評価は谷川浩司さんの参考値を用いて合法手一手後の盤上・持ち駒合計差を比べる。玉将を除外し、取った成駒は基本駒の持ち駒値へ戻し、同点はランダムに選ぶ。

第65回「ShogiHomeでDifficulty設定を確認する」は、実機観察と最終理解確認まで完了した。ShogiHome 1.28.1の設定画面に `Random` / `Material` が表示され、MaterialがUSI `setoption` で送信されることを確認した。Randomは画面で選択されていたが、既定値と同じため明示的な `setoption` はログで確認できなかった。指し手を進めていないため、Material時の着手の違いは未確認。DifficultyはRandom、USI通信ログは開始前と同じOFFへ復帰し、監視欄はUSI 0件・CSA 0件。観察範囲と最終理解確認は[第65回学習記録](learning/65-shogihome-difficulty-verification.md)を参照する。

第66回「ShogiHomeでMaterialの着手への影響を確認する」は、主題の実機観察と最終理解確認まで完了した。同じ7手局面でRandomは初手☖９四歩、Materialは初手☖８八角成（角を取る）を選び、USI通信でも設定値と着手を確認した。この一局ずつの観察から、この局面でMaterialが駒得を選ぶ挙動を確認できた。両局とも10分＋30秒の先手切れ負けだったが、本人は正常終局を主題の条件にしないと明確にしたため再試行はしない。対局後にアプリ/USI/CSAログOFF・INFO、Difficulty Random、Ponder OFF、稼働セッション0件を確認した。USIログは当初の想定より広く全体を読んだ。Macのロック解除後、まだ作成されていないログファイルを開こうとしたエラー表示を閉じ、開始局面と稼働セッション0件を再確認した。片付けで設定、棋譜、ログファイルは変更していない。観察結果と未確認事項は[第66回学習記録](learning/66-shogihome-material-move-effect.md)に記録した。

本人は第67回のテーマに「SFEN局面変換」を選び、新しいセッションの準備を依頼した。引き継ぎ準備開始時は `main` の `0e4c048` がHEADで、そこから第66回記録・索引・方向性の更新とSFEN引き継ぎを文書コミットにまとめた。新しいセッションでは `git status --short --branch` と `git log -3 --oneline` を実行し、コミット後の実際の状態を照合する。第67回の範囲・表現・確認方法は未合意であり、再開用プロンプトが本人から入力されるまで学習・実装を始めない。[第67回予定テーマの引き継ぎ](handover-sfen-position-conversion.md)を参照する。

## 確認記録

- [第64回学習記録](learning/64-weakest-mode-difficulty-selection-implementation.md)：最終理解確認の本人回答と補足を記録。
- [第65回学習記録](learning/65-shogihome-difficulty-verification.md)：ShogiHome画面とUSIログの観察結果、本人回答と補足を記録。
- [第66回学習記録](learning/66-shogihome-material-move-effect.md)：設計合意、主題の実機観察、時間切れの記録、設定復帰、未確認事項を記録。
- [第67回予定テーマの引き継ぎ](handover-sfen-position-conversion.md)：SFEN局面変換の選定理由、開始時Git基点、未決事項、読む資料、再開用プロンプト。
- [第64回の実装計画](plans/2026-10-05-weakest-mode-difficulty-selection-implementation-plan.md)：TDD、Refactor、独立レビュー、取り込み先検証の実績。
- [承認済み設計](plans/2026-10-05-weakest-mode-difficulty-selection-design.md)、[一手選択の知識](knowledge/31-weak-move-selection.md)、[USI応答の知識](knowledge/usi-engine-response.md)。
- 第65回は本人が合意した範囲で実機確認済み。操作前の別途承認を得て、確認用の棋譜は本人承認後に破棄した。確認時の画面・ログと設定復帰の詳細は[第65回学習記録](learning/65-shogihome-difficulty-verification.md)を参照する。

## 再開時に行うこと

現在状態は過去の記録から推測せず、次を実行して確認する。

```sh
git status --short --branch
git log -3 --oneline
```

その後、第66回の結果を[学習記録](learning/66-shogihome-material-move-effect.md)で確認し、第67回「SFEN局面変換」の開始条件と再開用プロンプトを[引き継ぎ](handover-sfen-position-conversion.md)で確認する。引き継ぎ文書はテーマ開始時点の履歴であり、現在のGit状態は必ずコマンドで確かめる。

## 次に読むファイル

1. [AGENTS.md](../AGENTS.md)、[README](../README.md)、[文書索引](README.md)、この案内、[次テーマ候補](next-topics.md)、[プロジェクト方向性](02-project-direction.md)、[第67回予定テーマの引き継ぎ](handover-sfen-position-conversion.md)、[第66回学習記録](learning/66-shogihome-material-move-effect.md)
2. [USIエンジン応答の知識](knowledge/usi-engine-response.md)、[USI平手局面コマンド再生の知識](knowledge/usi-position-replay.md)、`kaname_shogi/model.py`、`kaname_shogi/usi_position.py`、`tests/test_usi_position.py`
3. [USI接続ロードマップ](roadmap-usi-shogihome.md)、第55回[USI一手表記の知識](knowledge/usi-move-notation.md)、第56回[USI平手局面再生の学習記録](learning/56-usi-position-replay.md)を確認する。USI一次資料は第67回の引き継ぎに記載する。

新しいセッションでは、引き継ぎ内の再開用プロンプトを本人が入力してから次テーマを始める。プロンプトを入力しただけではShogiHome実機操作の承認にならない。
