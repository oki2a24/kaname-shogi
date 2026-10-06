# 第65回：ShogiHomeでDifficulty設定を確認する

## 目的

第64回に実装したUSI `Difficulty` の `Random` / `Material` がShogiHomeの設定画面に表示され、選択値がエンジンへ送られるかを実機で確認する。指し手は進めず、USI通信ログを根拠にする。コード・テストの変更やテスト実行は行わない。

## 参照した現行資料

- [USIエンジン応答の知識メモ](../knowledge/usi-engine-response.md)
- [ShogiHome接続手順書](../shogihome-connection-guide.md)
- [ShogiHome接続スキル](../../.agents/skills/shogihome-connection/SKILL.md)

## 合意した範囲と方法

- ShogiHomeの設定画面で `Difficulty` と選択肢 `Random` / `Material` を確認する。
- 各値を選んだ状態で、平手・人間先手・`kaname-shogi` 後手のローカル対局を一度ずつ開始する。指し手を進めず、USI通信ログを確認したら人間が投了する。
- 時計に「時間制限なし」が見つからなければ、画面に表示された10分＋30秒を変更せず使う。実際の開始前にこの条件を確認し、本人の了承を得た。
- 既存の未保存棋譜はダウンロードフォルダへ別名保存する。確認用棋譜は保存しない。USIログだけを一時的に有効化し、採取後は開始前の設定へ戻す。
- ShogiHome画面の操作は、この計画と手順を提示した後、本人の明示承認を得てから行った。

## 実機で確認したこと

- ShogiHomeはmacOS版 1.28.1。エンジン名 `kaname-shogi` の登録先は `/Users/oki2a24/kaname-shogi/kaname-shogi-usi` と一致した。エンジン設定では `USI_Ponder` が `OFF`、`Difficulty` の選択肢に `Random` と `Material` が表示された。
- 開始時のDifficultyは `Random`。アプリログとCSAログはOFF、USI通信ログもOFF、ログレベルはINFOだった。USI通信ログだけをONにして保存し、ShogiHomeを終了するメニュー操作後にアプリを再取得した。
- もともと画面に開いていた未保存棋譜は、本人の依頼に従って `/Users/oki2a24/Downloads/ShogiHome_2026-10-06_投了譜.kif` へ保存した。開始局面に戻った後に、各確認用対局を行った。
- 2局とも人間が先手、エンジンが後手、平手、持ち時間10分・秒読み30秒で開始した。自動保存はOFFで、指し手は進めず、人間が「投了」を選んだ。監視画面で対象セッションが `quitCompleted` となり、稼働中USIセッションが0件になった。
- 確認用対局の未保存棋譜は保存せず、本人の個別承認を得てShogiHomeの「初期化」で破棄した。ダウンロードへ保存した既存棋譜はその後開かず、変更していない。

## USIログの観察

確認したログは `~/Library/Logs/electron-shogi/usi-20261006_190236.log`。Consoleで開いて読み取り、共有・削除・外部送信はしていない。

| セッション | ShogiHome上の値 | ログで確認した通信 | 結果 |
| --- | --- | --- | --- |
| SID 1 | `Random` | `usi` に対してDifficulty optionを通知。`usiok` の後は `USI_Hash` と `USI_Ponder` の設定、`isready`、`readyok`、`usinewgame`。`setoption name Difficulty value Random` は記録されなかった。投了後は `gameover win`、別コマンドとして `quit`。 | 画面でRandomが選択されていたことは確認。Randomはエンジンの既定値でもあるため、明示的なRandom送信はこのログでは確認できない。 |
| SID 3 | `Material` | `usi` / option通知 / `usiok` の後に `setoption name Difficulty value Material`、`USI_Hash`、`USI_Ponder`、`isready`、`readyok`、`usinewgame`。投了後は `gameover win`、別コマンドとして `quit`。 | Materialの設定値がエンジンへ送信されたことを確認。 |

SID 2では設定画面を確認していた時間帯にエンジンが起動し、option通知と `usiok` の後、対局開始に至らず `quit` した。画面の設定読込に伴う起動かどうかはログだけでは断定できないため、用途不明の補助セッションとして記録する。

投了による終局では、今回のログは `gameover win` の後に `quit` した。これは人間側の投了に対応する観察であり、エンジンが `bestmove resign` を返す場合の通信とは区別する。

## 復帰と終了状態

- `Difficulty` を元の `Random` に戻して保存した。画面で読み直した値も `Random` だった。
- USI通信ログをOFFに戻して保存した。ShogiHomeの終了・再取得後に開発者向け設定を確認し、アプリログOFF、USIログOFF、CSAログOFF、INFOを確認した。
- 復帰後のエンジン設定でも `Random`、`USI_Ponder OFF`、登録先 `/Users/oki2a24/kaname-shogi/kaname-shogi-usi` を確認した。監視欄はUSI 0件、CSA 0件だった。
- ShogiHomeのウィンドウは空の開始局面で開いている。確認用棋譜は残していない。

## 未確認事項と限界

- `Random` は既定値と同じため、今回のUSIログから `setoption name Difficulty value Random` の明示送信を確認できなかった。画面の選択値と既定値適用を越えて、明示コマンド送信まで確認したとは言わない。
- 指し手を進めていないため、`Material` 選択時の実際の候補手・着手が `Random` と異なることは確認していない。今回確認したのはShogiHome画面での表示と、Material値のUSI送信である。
- SID 2の起動理由は不明。2回の指定対局とは区別して記録した。
- USIログは今回の観察範囲だけを読み取った。ログファイル自体はユーザーのローカルに残る。
- コード・テストは変更せず、テストも実行していない。

## 振り返り

画面に値が表示されることと、エンジンへ値が送信されることは別の確認事項だった。Materialでは設定画面の選択とUSIログの `setoption` が一致した。Randomでは画面上の選択は確認できたが、既定値と同じため明示的な送信行がなく、ログで確認できる範囲に差が残った。

## 最終理解確認

### 質問

ShogiHomeの設定画面で `Random` が選ばれ、USIログに `Difficulty` の選択肢が通知されている一方、`setoption name Difficulty value Random` がない場合、今回どこまで確認でき、何は未確認のままですか。

### 本人の回答

> Random は画面上で選択されていました
> 指し手を進めていないため、Material の実際の着手への影響は未確認

### アシスタントの補足

どちらも観察範囲に沿った回答である。Randomについては、画面での選択は確認できたが、既定値と同じだったため `setoption name Difficulty value Random` の明示送信はログで確認できていない。MaterialについてはUSIログへの値の送信を確認した一方、指し手を進めていないので実際の着手への影響は未確認である。

## 次回への問い

Materialを選んだときの実際の着手への影響を確かめるなら、RandomとMaterialをどの同一局面から一手ずつ比較するとよいか。
