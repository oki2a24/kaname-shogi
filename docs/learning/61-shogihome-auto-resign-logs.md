# 第61回：ShogiHome自動投了時のUSI通信を確認する

## 目的

第60回の37手をShogiHomeで再現し、エンジンの手番で自動的に投了終局した際、ShogiHomeと `kaname-shogi` の間で実際に記録されたUSI通信を確認する。画面・棋譜で見た結果、USIログの実通信、ローカル実装の既知動作を分けて記録する。

## 資料と証拠の範囲

- [USI一次資料](https://hgm.nubati.net/usi.html)は、USIコマンドと応答の意味を確認するために使う。資料にあるコマンド説明から、この局面でShogiHomeが送るべき未確認コマンドや、コマンド順序の必須要件を推測しない。
- [ShogiHome公式「開発者向け機能の使い方」](https://github.com/sunfish-shogi/shogihome/wiki/%E9%96%8B%E7%99%BA%E8%80%85%E5%90%91%E3%81%91%E6%A9%9F%E8%83%BD%E3%81%AE%E4%BD%BF%E3%81%84%E6%96%B9)でログ設定・ログファイルの扱いを確認した。[基本操作](https://github.com/sunfish-shogi/shogihome/wiki/%E5%9F%BA%E6%9C%AC%E7%9A%84%E3%81%AA%E6%93%8D%E4%BD%9C%E6%96%B9%E6%B3%95)と[ファイル形式](https://github.com/sunfish-shogi/shogihome/wiki/%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E5%BD%A2%E5%BC%8F%E3%81%AE%E7%A8%AE%E9%A1%9E)は、KIFの保存・読み込み方法を確認する資料であり、棋譜末尾から対局を再開できることの根拠にはしない。
- 第54回の使い捨てプローブは、`bestmove resign` と、その後の `gameover lose` / `quit` を観測した一例で、通常対局ではない。第55〜58回はローカル実装・テスト、第59回は通常応手と人間の投了である。
- 第60回は人間の19手とエンジンの18応手の後、エンジン側の手番で自動投了終局した画面・棋譜だったが、USI通信ログがなく最終応答文字列は未確認だった。本回の実測ログが得られる前に、現行コードの動作を第60回の実通信として扱わない。

## 合意した観察方法

ユーザーと一問ずつ相談し、観察計画の明示承認後に実施した。

- USIログファイルを主証拠とし、監視画面・プロンプト履歴は読み取り専用の補助とする。手動コマンドは送らない。
- ShogiHome 1.28.1上で登録ランチャーとPonderを確認する。USIログ設定の初期値を記録し、観察後に同じ値へ戻す。
- 現在未保存だった第60回棋譜をShogiHomeの「ファイル」→「棋譜を名前を付けて保存」から一時KIFに保存して保全する。
- 保存した棋譜を元に、38手目の「投了」と終了日時を除いた37手の一時KIFを用意する。ShogiHomeの通常操作で読み込み、棋譜カーソルを明示的に37手目へ移動してから、ローカル対局の開始局面を「現在の局面」にする。
- KIF末尾からの対局再開が画面操作でできない場合は、未確認コマンドを使わず停止する。コード・テスト変更が必要なら実装計画を提示して別途承認を待つ。

## 登録・設定と試行経路

- ShogiHomeは1.28.1。登録エンジンのランチャーは `/Users/oki2a24/kaname-shogi/kaname-shogi-usi` で、予定していたパスと一致した。
- 登録エンジン設定の `USI_Ponder` はOFF。対局設定でもPonder OFFを確認した。
- 開発者向け設定のUSI通信ログは観察前OFF、アプリログとCSAログもOFFだった。USI通信ログだけをONにして保存・再起動し、再起動後の設定値ONを確認した。観察後に初期値OFFへ戻して再起動し、OFFへ戻ったことも確認した。
- 元の画面は未保存の第60回棋譜で、37手に続いて「38 投了」が表示されていた。これを `/private/tmp/kaname-shogi-60-full-record-with-resign-20261004.kif` に保存した。
- 試行用KIFは `/private/tmp/kaname-shogi-60-37-ply-replay-20261004.kif`。初回は棋譜の37手目を明示選択せずに対局を開始したところ、先手（人）の時計が動いたため、その試行は対象局面として扱わず中断した。sid=1に `position` と `go` がないこともログで確認した。本譜へ戻って「37 ☗４一金」を選択したことを画面で確認してから、改めて「現在の局面」で開始した。
- 正しい末尾局面からの試行はShogiHome画面に「対局終了（投了）」を表示し、結果棋譜の主変化は1〜37手に続いて「38 投了」となった。結果棋譜を `/private/tmp/kaname-shogi-61-observed-result-20261004.kif` に保存した。同ファイルには別変化 `変化：1手` と `1 中断` も記録されており、主変化と区別した。

## 実際のUSIログ（2026-10-04）

原本は `/Users/oki2a24/Library/Logs/electron-shogi/usi-20261004_201234.log` にある。以下はファイル全体を転記したもので、`>` と `<` の方向表記も原文のまま残す。sid=1は開始局面のまま始めた誤った試行、sid=2は棋譜の37手目を選んで開始した観察対象である。

```text
[2026-10-04T20:17:07.266] [INFO] usi - sid=1: launch: /Users/oki2a24/kaname-shogi/kaname-shogi-usi
[2026-10-04T20:17:07.267] [INFO] usi - sid=1: > usi
[2026-10-04T20:17:07.309] [INFO] usi - sid=1: < id name kaname-shogi
[2026-10-04T20:17:07.310] [INFO] usi - sid=1: < id author kaname-shogi project
[2026-10-04T20:17:07.310] [INFO] usi - sid=1: < usiok
[2026-10-04T20:17:07.310] [INFO] usi - sid=1: > setoption name USI_Hash value 32
[2026-10-04T20:17:07.310] [INFO] usi - sid=1: > setoption name USI_Ponder value false
[2026-10-04T20:17:07.312] [INFO] usi - sid=1: > isready
[2026-10-04T20:17:07.321] [INFO] usi - sid=1: < readyok
[2026-10-04T20:17:07.321] [INFO] usi - sid=1: > usinewgame
[2026-10-04T20:18:40.401] [INFO] usi - sid=1: quit USI engine
[2026-10-04T20:18:40.402] [INFO] usi - sid=1: > quit
[2026-10-04T20:18:40.410] [INFO] usi - sid=1: engine process closed: close=0 signal=null
[2026-10-04T20:20:21.826] [INFO] usi - sid=2: launch: /Users/oki2a24/kaname-shogi/kaname-shogi-usi
[2026-10-04T20:20:21.827] [INFO] usi - sid=2: > usi
[2026-10-04T20:20:21.873] [INFO] usi - sid=2: < id name kaname-shogi
[2026-10-04T20:20:21.873] [INFO] usi - sid=2: < id author kaname-shogi project
[2026-10-04T20:20:21.873] [INFO] usi - sid=2: < usiok
[2026-10-04T20:20:21.873] [INFO] usi - sid=2: > setoption name USI_Hash value 32
[2026-10-04T20:20:21.873] [INFO] usi - sid=2: > setoption name USI_Ponder value false
[2026-10-04T20:20:21.874] [INFO] usi - sid=2: > isready
[2026-10-04T20:20:21.874] [INFO] usi - sid=2: < readyok
[2026-10-04T20:20:21.875] [INFO] usi - sid=2: > usinewgame
[2026-10-04T20:20:21.887] [INFO] usi - sid=2: > position startpos moves 2g2f 1c1d 2f2e 2b1c 3i4h 3a4b 1g1f 7a6b 1f1e 8b9b 1e1d 1c5g 4h5g P*1e 1i1e 9c9d 1d1c+ 9b9c 2e2d 1a1c 1e1c+ 8c8d 2d2c+ P*1b 1c1b 6a7a 1b2a 5a5b 2a2b 7a7b 2b3b 4b5a 3b4a 3c3d 4a5a 5b4b G*4a
[2026-10-04T20:20:21.887] [INFO] usi - sid=2: > go btime 600000 wtime 600000 byoyomi 30000
[2026-10-04T20:20:21.901] [INFO] usi - sid=2: < bestmove resign
[2026-10-04T20:20:21.902] [INFO] usi - sid=2: > gameover lose
[2026-10-04T20:20:21.902] [INFO] usi - sid=2: quit USI engine
[2026-10-04T20:20:21.902] [INFO] usi - sid=2: > quit
[2026-10-04T20:20:21.906] [INFO] usi - sid=2: engine process closed: close=0 signal=null
```

### ログから確認できること

- sid=1はエンジン起動・初期化の往復後に `quit` したが、`position` と `go` は記録されていない。これは37手目後の観察対象ではない。
- sid=2では `position startpos moves ... G*4a` の後に `go` が送られ、エンジンは `< bestmove resign` を返した。その後、この実例ではShogiHomeが `> gameover lose` を送って `> quit` を送り、エンジンプロセスは `close=0 signal=null` で終了した。
- USI一次資料には `bestmove resign`、`gameover`、`quit` の説明がある。今回確認したのはこの局面の実際の順序であり、全対局に対して同じ後続順序を必須要件とはしない。
- ログはUSIエンジンプロセスの起動から終了までを記録する。ShogiHomeアプリ自体の起動ログを有効化したわけではない。

## 画面・棋譜・監視の照合

- 試行対象のKIF主変化は1〜37手を含み、37手目は `☗４一金`。正しいカーソル位置からの対局開始直後、画面に「対局終了（投了）」が出て、主変化に「38 投了」が追加された。実ログに通常の指し手ではなく `bestmove resign` が記録されたことと対応する。結果KIFにある別変化の `1 中断` は初回試行の記録として主変化と区別した。
- 終局後のShogiHome監視画面・監視ウィンドウは「稼働中のUSIエンジンはありません」と表示した。
- セッションが短く、終了後の監視にはコマンド履歴が残らなかった。閉じたエンジンのプロンプト履歴も確認できず、手動でコマンドは送っていない。USIログ原本を通信の主証拠とする。

## 学んだこと

- 第60回では画面・棋譜で確認できた自動投了を、本回は実通信で照合できた。このsid=2ではエンジンが実際に `bestmove resign` を返し、ShogiHomeから続けて `gameover lose`、`quit` が送られた。
- KIFを開いただけでは棋譜末尾が開始局面に選ばれているとは限らない。盤面・棋譜カーソルを明示確認してから「現在の局面」で開始すると、37手目後の位置を再現できた。
- 第54回のプローブと本回では同じ種類の終局通信が観測されたが、第54回は一回限りのプローブ、本回は37手の棋譜を使ったShogiHome対局である。第60回の実通信が後から分かったことにしてはならない。
- 登録ランチャーとPonderは想定どおりだった。ログ設定は初期値OFF、観察中のみON、終了後にOFFへ復帰した。

## 実装・テスト・レビュー

実機の通信観察がテーマで、コード・テスト変更は不要だった。変更しておらず、テスト実行・コードレビューも行っていない。

## 理解確認

### 質問

sid=2でエンジンが返した最終応答と、その後ShogiHomeが送ったゲーム結果通知・終了要求は、それぞれどの文字列でしたか。

### 本人の回答

sid=2でエンジンが返した応答：`bestmove resign`。
その後ShogiHomeが送ったゲーム結果通知・終了要求：`gameover lose`。

### アシスタントの補足

ログでは `gameover lose` はゲーム結果通知で、その後に `quit` が別の終了要求として送られている。本人の回答では `gameover lose` を挙げており、終了要求の `quit` はこの補足で区別した。

## 振り返りと次回への問い

開始局面を誤って選んだ試行を一度中断し、37手目の選択を画面で確かめ直したことで、意図した位置からの実通信を記録できた。第54回・第60回の記録と異なり、本回は受信した応答文字列まで確定した。ログ原本はShogiHomeのログフォルダーに残し、設定を元の値へ戻した。

次回への問い：エンジンが投了したとき、ShogiHomeの通信上の勝敗通知と棋譜の「投了」がどう対応するかを、他の終局結果と区別して説明できるか。
