# 第55回「USIの指し手表記と内部の一手の対応」開始時点の引き継ぎ

## 最終目標

手元のMacのShogiHomeデスクトップ版から `kaname-shogi` を使い、平手で人間と対局できるようにする。ロードマップはこの到達点を小テーマに分けている。第54回ではShogiHomeとUSIの接続範囲を実機確認し、本人は第2小テーマとしてUSI指し手表記と内部の一手の対応を選んだ。ShogiHomeから `kaname-shogi` を実際に起動し、合法手で複数手対局するのは後続の第5テーマである。

## 選定理由と判断背景

本人は、CLIの `move` / `drop` の文字入力より既存GUIから盤面を指す方が家族で早く遊べると考え、ShogiHomeを使う大テーマを選んだ。第54回の実機観測では、ShogiHomeが初手後の履歴にUSI表記 `7g7f` を送り、次に時間情報付き `go` を送ることが確認できた。既存の一手データと外部表記との境界を先に整理すれば、局面再現や標準入出力の対局ループと混ぜずに学べる。

今回選んだのはロードマップ第2小テーマ「USIの指し手表記を内部の一手と対応させる」。USI文字列と `BoardMove` / `DropMove` の対応を調べる。第54回で観測したのは通常の盤上移動 `7g7f` だけなので、成りや駒打ちなどの対応は一次資料で確かめ、本人と対象範囲を設計する。USIから内部型への変換だけにするか、内部型からUSI表記へ戻す方向も含めるか、不正な文字列の扱いをどうするかは未決定である。

## 第54回で完了した事項

- ShogiHome 1.28.1をMac上で起動し、実行可能な単一Pythonスクリプトをエンジン登録できることを確認した。プローブには絶対シバン `#!/usr/bin/python3` と実行権限を付けた。登録・準備では同じスクリプトが複数回起動したため、実エンジンは複数回の起動・終了要求に対応する必要がある。
- 平手、先手人間、後手プローブ、10分＋30秒で、ShogiHomeとプローブ双方のログを照合した。通信順は次のとおり（`>` はShogiHomeからエンジン、`<` はエンジンからShogiHome）。

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

- `usinewgame` は人間の初手前に送られた。初手後の局面・思考通知は `position startpos moves 7g7f` と時間付き `go`。時間値はミリ秒で、先手の消費分を引いた値だった。オプションを宣言しないプローブにも `USI_Hash=32` と `USI_Ponder=true` が送られた。
- プローブの投了応答後に `gameover lose` と `quit` が届いた。合法手応答、複数手の往復、SFEN、先読み・停止系は確認していない。
- 初回の短時間設定では対局準備中に人間の時間切れとなり、局面通知と `go` は送信されなかった。通信範囲の判断には使わず、10分＋30秒の再試行を観測対象にした。
- 後片付けとして「KanameShogiProbe」登録を削除し、USI通信ログを無効にして再起動した。再起動後、エンジン一覧が空で、ログ設定がオフであることを確認した。一時プローブとそのログは削除済み。ShogiHomeの公式ログは保持している。
- 製品コード・テストは変更していない。文書の `git diff --check`、7文書の行末・空白・相対リンク検査が成功した。第54回の経緯と本人回答は[第54回学習記録](learning/54-usi-shogihome-connection-scope.md)、より広い順序は[USI接続ロードマップ](roadmap-usi-shogihome.md)を参照する。

## 一次資料

- [将棋所：USIプロトコルとは](https://shogidokoro2.stars.ne.jp/usi.html)：盤上移動、成り、駒打ちを含むUSI指し手文字列の書式を次セッションで再確認する。
- [ShogiHome公式案内](https://sunfish-shogi.github.io/shogihome/)、[エンジン登録手順](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E7%99%BB%E9%8C%B2%E6%89%8B%E9%A0%86)：今回の実機接続先と登録確認の背景。
- [ShogiHome開発者向け機能](https://github.com/sunfish-shogi/shogihome/wiki/%E9%96%8B%E7%99%BA%E8%80%85%E5%90%91%E3%81%91%E6%A9%9F%E8%83%BD%E3%81%AE%E4%BD%BF%E3%81%84%E6%96%B9)：第54回の実機USIログ取得手順。

ShogiHomeの実機観測は第54回で完了し、引き継ぎ後はUSIの文字列表現そのものを将棋所の一次資料で確認する。

## 現在分かっている内部表現

- `kaname_shogi/move.py` の `BoardMove` は変更不可の盤上移動データで、`source`、`destination`、`promote` を持つ。局面へ移動を適用する操作ではない。
- 同じファイルの `DropMove` は変更不可の駒打ちデータで、`piece_type` と `destination` を持つ。`Move` は `BoardMove` または `DropMove` の和集合型である。
- `kaname_shogi/model.py` の `Square(file, rank)` は筋・段の値で、双方1〜9。筋は先手視点で右端が1、左端が9、段は上端が1、下端が9。
- `BasicPieceType` には玉を含む8種があるが、玉は持ち駒にならない。USIの駒打ち表記からどの基本駒種を作るかは、仕様と型の範囲を照合して設計する。
- これらは調査時点の既存データ境界であり、新しいパーサー・フォーマッターや公開APIを追加する合意ではない。

## 対象境界と未決事項

このテーマでは、一次資料を根拠にして、USI指し手文字列と既存の一手データをどう対応づけるかを決める。通常の移動、成りの指定、駒打ちをどの範囲で扱うか、変換方向、エラー表現、公開APIにするか内部処理にするか、テスト境界と記録方法は新セッションで一問ずつ確認する。

以下は後続テーマに残す。

- `position startpos moves ...` 全体の読み取りと、複数手を局面へ再適用する処理。
- `position sfen` の読取、任意局面変換。
- `go`、合法手選択、`bestmove`、USIコマンドループ、標準入出力。
- ShogiHomeで `kaname-shogi` を登録して実際に応手を返す結合確認。

第54回でShogiHomeが送った `7g7f` は実機例であるが、座標の対応規則、成り・打ち表記の文法、往復変換はUSI一次資料で改めて確認する。`7g7f` 一例だけから完全な変換仕様を推測しない。

## 開始時の物理状態

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`
- 実機：macOS 27.0.1 (`arm64`)、ShogiHome 1.28.1、Python `/usr/bin/python3` 3.9.6、エンジン起動タイムアウト10秒。
- 引き継ぎ準備開始時ブランチ：`codex/usi-shogihome-connection-scope`
- 引き継ぎ準備開始時HEAD：`41b69a4 docs: ShogiHome対局ロードマップと引き継ぎを記録する`
- 準備開始時点では、第54回の記録・関連文書が同ブランチ上で未コミットだった。本人確認を経て、この引き継ぎを含む文書一式を日本語のConventional Commitで記録する段取りだった。再開時はGitコマンドで実際の状態を確認する。
- 新セッションの開始時点はここに書いた値と異なる場合がある。実際の `git status --short --branch` と `git log -3 --oneline` を必ず取り直す。
- ShogiHome 1.28.1はMac上で再起動済み。現在エンジン登録は空で、USI通信ログはオフ。`/private/tmp/kaname-shogi-usi-probe-20261002.py` と `.log` は削除済み。
- 保持した実機ログ：`/Users/oki2a24/Library/Logs/electron-shogi/usi-20261002_100920.log`。
- 引き継ぎ準備後の2026-10-02に `git diff --check` と8文書の行末・空白・相対リンク検査が成功した。プロジェクトテストは実行していない。

## 次の具体的な手順

1. 新セッションの最初に `git status --short --branch` と `git log -3 --oneline` を実行し、ここにある物理状態の記述と照合する。
2. `AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、本書、`docs/roadmap-usi-shogihome.md`、`docs/learning/54-usi-shogihome-connection-scope.md`、`docs/02-project-direction.md` を読む。
3. `kaname_shogi/move.py` と `kaname_shogi/model.py` の該当する値型、`tests/test_move.py` の既存テストを確認する。必要に応じて一手の生成・適用との責務境界を `movegen.py` で読む。
4. `superpowerssuperpowers:brainstorming` を使う。今回の希望テーマと既存型の説明を最初の文脈として共有した上で、対象範囲、変換の向き、表現、エラー、検証、記録方法を一問ずつ確認する。
5. 将棋所のUSI一次資料を開き、盤上移動・成り・駒打ちの文字列表現と座標を確かめる。第54回のShogiHome実機例 `7g7f` と矛盾しないか確認し、出典リンクを設計記録に残す。
6. 対象範囲・表現・テストと検証方法の設計案を提示して、明示的な承認を待つ。承認前にコード・テスト・既存文書を変更しない。独立した実装計画を作る場合は、その計画への明示的な承認も別途待つ。
7. 実装が承認された場合に限り、目的が分かる作業ブランチで、合意範囲の変換だけを扱う。TDD、レビュー、検証、学習記録をプロジェクト方針に従って行う。局面再現やUSI対局ループを先取りしない。

## 再開用プロンプト

> kaname-shogi の第55回テーマ「USIの指し手表記と内部の一手の対応」を始めてください。最初に `git status --short --branch` と `git log -3 --oneline` で現在状態を確認し、`AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/handover-usi-move-notation.md`、`docs/roadmap-usi-shogihome.md`、`docs/learning/54-usi-shogihome-connection-scope.md`、`docs/02-project-direction.md` を読んでください。`kaname_shogi/move.py` の `BoardMove` / `DropMove` と `kaname_shogi/model.py` の `Square` / `BasicPieceType`、既存の `tests/test_move.py` も確認してください。ShogiHomeで `kaname-shogi` と平手対局する大テーマの第2小テーマとして、USI指し手表記と既存の一手データの対応を調べます。第54回で確認した実機例は `position startpos moves 7g7f` です。USI一次資料で通常移動・成り・駒打ちの文法と座標を確認し、実機の一例から未確認の仕様を推測しないでください。今回の対象に変換の向き、エラー表現、公開境界、確認方法を含めるかは未決定です。`superpowerssuperpowers:brainstorming` を使い、対象範囲・表現・検証・記録方法を一問ずつ確認した後、設計案を提示して明示的な承認を待ってください。承認前に指し手変換、局面再現、対局ループの実装やテスト変更を始めないでください。計画書を作る場合も、計画への明示的な承認を待ってください。実装する場合は目的が分かる作業ブランチで進め、TDD、独立レビュー、検証、日本語のConventional Commitなど `AGENTS.md` の方針に従ってください。ユーザーが選んだのはUSI表記と内部の一手の対応を調べるテーマであり、変換方向や実装方式はまだ合意していません。
