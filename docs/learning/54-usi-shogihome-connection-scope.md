# 第54回：ShogiHomeとUSIの接続範囲を確定する

## 目的

手元のMacのShogiHomeデスクトップ版から、将来 `kaname-shogi` と平手対局するために必要なUSIコマンド、Pythonスクリプトの起動・登録条件、通信の観測方法を確認する。USIの指し手変換、局面再現、対局ループは実装しない。

## 開始時の状態

2026-10-02に `git status --short --branch` と `git log -3 --oneline` を確認した。開始時は `main...origin/main` で作業ツリーは clean、HEADは `41b69a4 docs: ShogiHome対局ロードマップと引き継ぎを記録する` だった。承認済みの文書記録を `codex/usi-shogihome-connection-scope` ブランチで行う。

ユーザーが公式の `ShogiHome-1.28.1-universal.dmg` からインストールし、起動・終了できることを確認済みだった。ユーザーはShogiHomeの起動操作を許可した。最初の調査時はアプリが終了していたため、USIログを有効にしてから再起動し、設定が保持されたことを確認した。

## 対象・調査方法・記録方法の合意

- 対象は公式資料、Mac上のShogiHome 1.28.1の起動・エンジン登録、平手対局での実通信とする。
- 一次資料を基準にし、Mac上で使い捨てのUSIプローブを登録する。プローブは受信行を `/private/tmp` のログへ記録し、初期化コマンドへの応答と `go` に対する `bestmove resign` だけを返す。
- 実機のUSI通信ログとプローブ側ログを照合する。ユーザーが指定した第54回学習記録、ShogiHomeロードマップ、文書索引へ根拠付きで記録する。
- 指し手変換や対局ループを含む製品コード・テストの変更は行わない。

## 環境

- ShogiHome：1.28.1。ユーザーが `ShogiHome-1.28.1-universal.dmg` から導入し、起動できることを確認した版。
- macOS：27.0.1、Apple Silicon (`arm64`)。
- Python：`/usr/bin/python3`、Python 3.9.6。
- ShogiHomeのアプリ設定で確認したエンジン起動タイムアウト：10秒。

## 一次資料

- [将棋所：USIプロトコルとは](https://shogidokoro2.stars.ne.jp/usi.html)：標準入出力上の行コマンド、初期化、局面・思考、終局通知を確認した。
- [ShogiHome公式案内](https://sunfish-shogi.github.io/shogihome/)：PC版、macOS配布、バージョン一覧を確認した。調査日には最新版として1.29.0、安定版として1.28.1が案内されていた。
- [ShogiHomeのインストール手順](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB%E6%89%8B%E9%A0%86)：Macでは `-mac.zip` 内のDMGを開き、ShogiHomeをApplicationsへ移す手順を確認した。
- [ShogiHomeのエンジン登録手順](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E7%99%BB%E9%8C%B2%E6%89%8B%E9%A0%86)：エンジン設定から追加し、実行ファイルを選び、用途を選択して「保存して閉じる」手順を確認した。起動が遅い場合は起動待ち時間を延ばせる。
- [シェルスクリプトやインタプリタ型言語の起動条件](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%B7%E3%82%A7%E3%83%AB%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%97%E3%83%88%E3%82%84%E3%82%A4%E3%83%B3%E3%82%BF%E3%83%97%E3%83%AA%E3%82%BF%E5%9E%8B%E8%A8%80%E8%AA%9E%E3%81%A7%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E3%82%92%E5%AE%9F%E8%A1%8C%E3%81%97%E3%81%9F%E3%81%84%E6%96%B9%E3%81%B8)：macOS/Linuxでは正しいシバンと実行権限が必要で、`/usr/bin/env` を使う場合はGUI起動時のPATHに注意する。
- [開発者向け機能：ログ・起動タイムアウト・監視](https://github.com/sunfish-shogi/shogihome/wiki/%E9%96%8B%E7%99%BA%E8%80%85%E5%90%91%E3%81%91%E6%A9%9F%E8%83%BD%E3%81%AE%E4%BD%BF%E3%81%84%E6%96%B9)：ログは初期状態で無効、設定変更後の再起動が必要。macOSでは `~/Library/Logs/{app name}/` に出力し、デバッグメニューからUSIログを開ける。監視タブではUSIセッションを確認できる。

## 実機で確認した登録・起動条件

1. ShogiHomeの「エンジン設定」から「追加」を押し、`.py` ファイルを選ぶと、アプリはそのファイルを実行して `usi` による識別を行った。
2. プローブは `#!/usr/bin/python3` のシバンと実行権限 `-rwxr-xr-x` を持つ単一ファイルだった。ShogiHomeのファイル選択画面で直接指定でき、表示名 `KanameShogiProbe` で登録された。
3. 用途は「対局」のみを選び、「保存して閉じる」で登録を保存した。ローカル対局の後手候補に表示され、平手・先手人間・後手プローブで開始できた。
4. 登録・準備中に同じスクリプトの別プロセスが複数回起動した。したがって、1プロセスの起動だけを想定せず、毎回 `usi` に応答して終了要求 `quit` で閉じられる必要がある。
5. プローブは絶対シバンを使ったため、ShogiHomeのGUIプロセスが引き継ぐPATHに依存しなかった。ShogiHomeがエンジンへ渡す作業ディレクトリや環境変数の全体は観測していない。実際の `kaname-shogi` 起動方法は、実エンジンを登録するテーマで改めて確認する。
6. エンジン起動タイムアウト設定は10秒だった。今回のプローブは期限内に `usiok` を返した。実際のエンジン初期化がこの設定を超える場合は、アプリ設定で待ち時間を延ばす必要がある。

## 通信ログを有効にする方法と実行条件

USI通信ログは、アプリ設定の「開発者向け」で「USI通信ログを出力」を有効にして保存し、ShogiHomeを再起動すると出力された。今回、アプリメニュー「デバッグ」→「ログファイル」→「USI通信ログを開く」からログを確認できた。ログは `~/Library/Logs/electron-shogi/usi-20261002_100920.log` に生成された。ShogiHome公式資料によれば、ログは起動単位で新しいファイルとなり、該当ログが最初に出力されるまでファイルは作られない。

プローブ側では受信行を `/private/tmp/kaname-shogi-usi-probe-20261002.log` に保存し、応答行も記録した。次の一覧の `>` はShogiHomeからエンジン、`<` はエンジンからShogiHomeを表す。

## 実通信の観測結果

初回は対局設定の初期値 `00:00+30`（持ち時間なし、秒読み30秒）を使ってしまい、準備中に先手が時間切れとなった。その試行では局面通知と `go` は送られず、ShogiHomeは `gameover win` と `quit` を送った。通信範囲の判定には使わず、次の試行では先手・後手双方を10分＋30秒に設定した。

成功した試行は平手、先手人間、後手プローブ、棋譜自動保存オフ、10分＋30秒、連続対局1局だった。ShogiHome実機ログとプローブログの両方で、次の順序を確認した。

```text
> usi
< id name KanameShogiProbe
< id author Codex
< usiok
> setoption name USI_Hash value 32
> setoption name USI_Ponder value true
> isready
< readyok
> usinewgame
> position startpos moves 7g7f
> go btime 591199 wtime 600000 byoyomi 30000
< bestmove resign
> gameover lose
> quit
```

先手が平手初期局面から７六歩を指した後、ShogiHomeは `position startpos moves 7g7f` を送り、初期局面からその時点までの指し手履歴を `moves` の後ろに付けた。時間値はミリ秒で、先手の残り時間が `btime 591199`、後手の残り時間が `wtime 600000`、秒読みが `byoyomi 30000` だった。プローブが `bestmove resign` を返すとShogiHomeは対局を終え、エンジン敗北の `gameover lose`、続けて `quit` を送った。

ShogiHomeはこの実行で、プローブが `option` 行を一つも宣言していないにもかかわらず、対局開始時に `USI_Hash=32` と `USI_Ponder=true` を送った。設定値は実機の初期値だった。最初の接続範囲では、これらの `setoption` 行を受け取っても対局を停止せず処理できる必要がある。今回は値を変更しないプローブが行を受信して無視し、問題なく `isready` へ進んだ。

## 接続範囲の判断

最初のShogiHome対局へ向け、次のコマンドを実装設計の対象にする。

- 起動・初期化：`usi` → `id name` / `id author` / `usiok`、`setoption` の受信、`isready` → `readyok`、`usinewgame`。
- 局面と探索：平手では `position startpos moves ...` を読み、`go`（今回の既定時間設定では `btime` / `wtime` / `byoyomi` を伴う）を受け、合法な指し手を `bestmove <move>` で返す。
- 終了：少なくとも今回確認した `bestmove resign`、`gameover [win|lose|draw]`、`quit` を扱う。
- 通信：標準入出力の1行単位テキストとし、エンジンからの応答は改行を付けてflushする。標準出力へUSI以外の表示を混ぜない。

このテーマではコマンド実装、USI文字列と内部手の変換、局面適用、対局ループ、合法手の `bestmove` は変更していない。ロードマップ上の既存順序を維持し、指し手変換、`position` からの局面再現、USIエンジン応答をそれぞれ後続テーマで扱う。

## 未確認事項

- プローブが合法な `bestmove <move>` を返して盤面へ適用されること。今回のプローブは投了だけを返したため、合法手応答の結合確認は実施していない。
- 人間とエンジンの通常手を複数回往復した場合の `position` が全指し手履歴を含むこと。将棋所の説明では初期局面から全指し手を並べるが、今回実機で見たのは1手後まで。
- `position sfen`、駒落ち、`binc` / `winc`、`go ponder`、`stop`、`ponderhit`、連続対局や複数プロセスでの並行対局。
- ShogiHomeが登録スクリプトへ渡す作業ディレクトリ、PATHなどの環境変数。
- `kaname-shogi` の既存ランダム合法手選択をUSIから使い、実際の応手までGUIで確認すること。これは後続の接続テーマで扱う。

## 変更・検証

このテーマでは製品コードとテストを変更せず、プロジェクトのテストは実行しない。実機のShogiHome通信ログと独立したプローブ側受信ログを照合し、USIコマンドの向きと順序を確認した。ロードマップ・文書索引の差分、相対リンク、引用元と記述の整合性、行末・`git diff --check` は文書更新後に確認する。

ShogiHomeの後片付けは2026-10-02に実施した。エンジン管理で「KanameShogiProbe」を削除して保存し、アプリ設定の「USI通信ログを出力」をオフにして保存した後、ShogiHomeを終了・再起動した。再起動後にエンジン一覧が空であること、USI通信ログ設定がオフのままであることを画面で確認した。`/private/tmp/kaname-shogi-usi-probe-20261002.py` と `/private/tmp/kaname-shogi-usi-probe-20261002.log` は削除済み。通信記録の根拠としてShogiHome公式ログ `~/Library/Logs/electron-shogi/usi-20261002_100920.log` は保持した。

## 最後の理解確認

### 問題

今回の観測では、人間の初手後にShogiHomeがエンジンへ送った局面・思考コマンドは何で、投了応答後に何を送ったでしょうか。`setoption` の観測値も含めて説明してください。

### 本人の回答

人間の初手後
> usinewgame
> position startpos moves 7g7f
> go btime 591199 wtime 600000 byoyomi 30000

投了応答後
> gameover lose
> quit

### アシスタントの補足

- 回答は投了後の終了通知を正しく挙げている。人間の初手後に届いた局面・思考コマンドは `position startpos moves 7g7f` と `go btime 591199 wtime 600000 byoyomi 30000`。
- 時系列は、`usinewgame` が人間の初手前、初期化の `isready` / `readyok` の後に送られ、その後に人間が７六歩を指して `position` と `go` が送られた。
- 対局開始時には `setoption name USI_Hash value 32` と `setoption name USI_Ponder value true` も送られた。プローブは `bestmove resign` を返し、その後ShogiHomeが `gameover lose` と `quit` を送った。
- 以上は実機ログに基づく補足で、本人の回答を置き換えない。

## 振り返り

公式USIの一般形だけでは、実際のGUIが初期値としてどのオプションを送るか、Pythonファイルの登録時に何度起動するか、どの時間値で `go` を送るかは分からない。ShogiHomeの公式説明と実機ログを併用したことで、最初の平手対局に必要な外枠と、後続の確認へ残す境界を分けられた。

## 次回への問い

本人は次のテーマとして「USIの指し手表記と内部の一手の対応」を選んだ。これはShogiHomeで `kaname-shogi` と平手対局する大テーマの第2小テーマである。新しいセッションでは[開始時点の引き継ぎ](../handover-usi-move-notation.md)を読み、一次資料と現在の内部型を確認してから、対象範囲・表現・確認方法を一問ずつ決める。設計案への明示的な承認前にコードやテストを変更しない。
