# ShogiHomeで通常停止を観測する条件の整理

2026-10-13。同日の会話と実際の事前確認を事後記録する。[条件案](../plans/2026-10-13-shogihome-normal-stop-conditions.md)。

## 目的と結論

通常対局の画面操作からUSI `stop` を送り、合法な応答を棋譜・盤面へ反映して対局が続く経路の条件を作成した。**画面操作による通常 `stop` の経路を確認できず、実施条件は成立しなかった。** 該当操作がすべての版・画面に存在しないと証明した意味ではない。エンジン故障やUSI通常停止の失敗を観測した結果でもない。

直接USIで確認した通常停止後の一応答は、ShogiHome経路の証明にはならない。G2では合法応答を4.516秒で確認したが、探索中の通常 `stop` とその後の応答を観測せず、人間側切れ負けとなった。過去の履歴は[開始時引き継ぎ](../handover-shogihome-normal-stop-conditions.md)から辿る。

## 本人の指示とアシスタントの対応

本人は条件案提示後に「承認する。実施開始して下さい」と指示した。条件案は、通常対局の操作と `stop` の対応を資料から確認できなければ `go` を開始しないと定めていた。承認後は既に起動していたShogiHomeの画面と設定を読み取り、公式v1.28.2ソースを照合した。設定画面はキャンセルで閉じた。

本人は背景と選択肢の説明を求めた。アシスタントは、画面操作による通常停止、対局中断、時計期限による停止を説明し、今回を条件不成立として記録し、ShogiHome時計期限による停止を別テーマにすることを推薦した。本人の選択は次のとおり。

> 今回のテーマを「画面操作による通常 `stop` の経路を確認できず、実施条件は成立しなかった」と記録し、次に時計期限による停止を別テーマとして条件作成する、とします

これは結論の記録と次テーマの条件作成の指示であり、新条件の実施開始やmain取り込みの承認ではない。理解確認問題はまだ出しておらず、回答・習得済みとして記録しない。

## 資料で確認した区別

- v1.28.2の「対局中断」は `store.stopGame()`、通常対局では `gameManager.stop()` を呼び、`end(INTERRUPT)` に進む。終局通知はプレイヤーの `gameover()` を呼ぶ。
- USIプレイヤーの `stop()` は `usiStop`、`gameover()` は `usiGameover`、`close()` は `usiQuit` に対応する。対局中断を単独の通常 `stop` 操作と扱わない。実際の通信列は今回採取していない。
- エンジンの時間切れが無効の場合、ShogiHomeの時計期限処理は `player.stop()` を呼んで対局を継続する分岐を持つ。これは時計起点の別経路。
- 「解析中断」は `store.stopAnalysis()` の別ハンドラ。公式Wikiの検討機能用「停止」も通常対局の停止操作へ流用しない。

固定版公式資料：[画面操作](https://github.com/sunfish-shogi/shogihome/blob/v1.28.2/src/renderer/view/main/ControlPane.vue)、[ストア](https://github.com/sunfish-shogi/shogihome/blob/v1.28.2/src/renderer/store/index.ts#L761)、[時計期限・対局中断](https://github.com/sunfish-shogi/shogihome/blob/v1.28.2/src/renderer/game/game.ts#L469)、[終局通知](https://github.com/sunfish-shogi/shogihome/blob/v1.28.2/src/renderer/game/game.ts#L614)、[USIプレイヤー](https://github.com/sunfish-shogi/shogihome/blob/v1.28.2/src/renderer/players/usi.ts#L237)。固定タグの実装確認と、インストール済みアプリの実通信・内部状態の観測を区別する。

## 事前確認した実機状態と限界

当時の画面はShogiHome 1.28.2、`/private/tmp/kaname-clock-stop-G2-restart-20261013-cca2681/before-G2.kif` の開始局面。監視表示はUSIエンジン0、CSAサーバー0。登録先は `/Users/oki2a24/kaname-shogi/kaname-shogi-usi`、Ponder OFF、Difficulty Random、Hash 32。アプリ・USI・CSAログはOFF。設定反映に再起動が必要と表示された。これらはその時の読み取りであり、次の実施時に再確認する。

エンジン起動、対局、ログ採取、計測、設定保存・変更、棋譜の変更・保存、コード・テスト変更は行わなかった。条件案作成段階には実機操作を行わず、読み取り操作は実施開始承認後に行った。main取り込みは未承認・未実施。作業開始HEADは `3144003`、mainはorigin/mainより27コミット先行。文書変更は未コミット。

## レビューと文書検証

当初条件案は独立レビューの初回Important 2件・Minor 1件へ対応し、再レビューでCritical 0・Important 0・Minor 0。詳細は条件案に保持する。今回の結論記録・次テーマ案のレビューと文書検証は次テーマ案に記録する。実装変更がないためテストは実行せず、過去のテスト成功を今回の結果にしない。

## 次回への問い

ShogiHomeの時計期限より前にエンジン自身が期限停止して応答した場合、どの経路を観測したと言えるか。これは未回答の学習候補であり、回答を求めた記録ではない。[次テーマの条件案](../plans/2026-10-13-shogihome-clock-deadline-conditions.md)。

## 後日の資料再照合による限定（2026-10-13）

上の「終局通知はプレイヤーのgameoverを呼ぶ」は、勝敗変換結果がある場合に限る。v1.28.2の変換関数はINTERRUPTにnullを返すため、対局中断ではgameoverを送らず、closeからquitへ進む。現行安定版v1.29.1も同じ分岐を確認した。[今回の一次資料・条件案](../plans/2026-10-13-shogihome-interruption-conditions.md)。これは資料読取りの訂正であり、当時または現在の実通信を観測した意味ではない。上の当時の記録は履歴として保持する。
