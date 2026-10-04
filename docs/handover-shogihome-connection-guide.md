# 🔄 Session Handoff: ShogiHome接続手順書を作成する（第62回予定）

## 🎯 最終目標 (Ultimate Goal)

- ShogiHomeへ `kaname-shogi` を接続して対局・観察するとき、毎回の画面状態を確認しながら迷わず進められる、再利用可能な手順書を作る。
- 主な読み手は、後のセッションでShogiHomeの操作を依頼される人間とAIアシスタント。特に、アシスタントが登録エンジン・棋譜カーソル・Ponder・USIログの状態を取り違えず、既存の登録を活用して接続できることを重視する。
- ShogiHomeの全機能やUSI全コマンドを説明する文書にはしない。通常の対局接続、必要な場合のUSIログ取得、終了後の確認と設定復帰を、実機で分かった範囲から整理する。

## ✅ 完了した事項と「意思決定の背景」 (Done & Why)

- [済] 第61回「ShogiHome自動投了時のUSI通信を確認する」の実機観察・理解確認を実施した。
  - **Why:** 第60回の棋譜と画面では自動投了終局を確認したが、USI通信ログがなく、最終応答文字列と終局経路は未確認だったため。
  - **Crucial:** 第61回のsid=2では、ShogiHomeが37手の `position` と `go` を送り、エンジンが `bestmove resign` を返した。その後ShogiHomeが `gameover lose` と `quit` を送り、エンジンプロセスが終了した。これは当該実機観察一例であり、他局面・他バージョンで同じ通信になる必須要件と一般化しない。
  - sid=2を含む30行のUSIログ原本は `/Users/oki2a24/Library/Logs/electron-shogi/usi-20261004_201234.log`。学習記録の転記は原本と完全一致することを確認済み。
  - 学習記録は [第61回学習記録](learning/61-shogihome-auto-resign-logs.md) を参照。ユーザーの理解確認回答は `bestmove resign` と `gameover lose`。補足として `quit` は後続する別の終了要求であることを記録した。
- [済] 第61回で、登録済みランチャーとPonderをShogiHome上で再確認した。
  - **Crucial:** 登録先は `/Users/oki2a24/kaname-shogi/kaname-shogi-usi`、PonderはOFF。対象セッションのログにも `setoption name USI_Ponder value false` が記録された。次のセッションで設定が維持されていると決めつけず、現物を確認する。
  - このパスは過去に使われていたアーカイブ済みworktree内のランチャーが `ENOENT` となった後、メインの作業ディレクトリへ登録し直したもの。将来のworktree切替・移動後にはShogiHomeが引き続き正しい作業ツリーを指すか確認が必要。
- [済] 第60回の棋譜を保存し、37手だけの試行用棋譜を作り、第61回の結果棋譜とログを残した。
  - 第60回の元棋譜全体: `/private/tmp/kaname-shogi-60-full-record-with-resign-20261004.kif`
  - 37手の試行用棋譜: `/private/tmp/kaname-shogi-60-37-ply-replay-20261004.kif`
  - 第61回結果棋譜: `/private/tmp/kaname-shogi-61-observed-result-20261004.kif`
  - 結果棋譜の主変化は37手と38手目「投了」、別変化には初回に中断した試行の「1 中断」がある。初回に棋譜の37手目を明示選択せず開始したところ人間側の時計が動いたため中断し、画面で37手目を選択したと確かめてから対象局面で再試行した。
- [済] USIログ設定は観察中だけONにし、最後にOFFへ戻して再起動後も確認した。監視画面では対局後に稼働中USIエンジン0件を確認した。手動でプロンプトへUSIコマンドは送っていない。
- [選定済み] ユーザーは次テーマを **「ShogiHome接続手順書を作成する」** と選び、新しいセッションの準備を依頼した。
  - **Why:** 第61回を実施して、登録先の古いworktree、Ponder、USIログの再起動要件、KIFを開いた後の手数選択など、接続前後に画面で確かめる項目が複数あり、セッションごとの記憶に頼ると操作を誤りやすいと分かった。再利用できる確認表を用意すれば、次の実対局・通信観察を短く正確に始められる。
  - **Crucial:** ユーザーの目的は「ShogiHome につなぐ手順を、依頼時にアシスタントが迷わず一度で実行できるようにする」こと。手順書の保存先・対象とする起動パターン・UI確認をどこまで固定するかはまだ合意していない。候補パスや章構成を決めつけず、次のセッションで設計対話を行う。

## 📚 次のセッションで使う一次資料と既存資料

- ShogiHome公式 [エンジン登録手順](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E7%99%BB%E9%8C%B2%E6%89%8B%E9%A0%86): エンジン設定で追加し、実行ファイルを選択して保存する手順。読込済みエンジンは「保存して閉じる」まで永続化されない旨も記載されている。
- ShogiHome公式 [スクリプト・インタプリタ型エンジンの注意](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%B7%E3%82%A7%E3%83%AB%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%97%E3%83%88%E3%82%84%E3%82%A4%E3%83%B3%E3%82%BF%E3%83%97%E3%83%AA%E3%82%BF%E5%9E%8B%E8%A8%80%E8%AA%9E%E3%81%A7%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E3%82%92%E5%AE%9F%E8%A1%8C%E3%81%97%E3%81%9F%E3%81%84%E6%96%B9%E3%81%B8): macOS/Linuxで必要なシバンと実行権限の説明。
- ShogiHome公式 [開発者向け機能](https://github.com/sunfish-shogi/shogihome/wiki/%E9%96%8B%E7%99%BA%E8%80%85%E5%90%91%E3%81%91%E6%A9%9F%E8%83%BD%E3%81%AE%E4%BD%BF%E3%81%84%E6%96%B9): ログ設定は既定で無効、設定変更後の再起動が必要。ログ種別ごとに別ファイルとなり、アプリ起動ごとに新しいログとなる。ログフォルダーをメニューから開ける。監視は生きたセッションの確認、プロンプトは履歴確認や手入力に使えるが、対局中の誤った手入力は予期しない動作を起こしうる。
- ShogiHome公式 [基本的な操作方法](https://github.com/sunfish-shogi/shogihome/wiki/%E5%9F%BA%E6%9C%AC%E7%9A%84%E3%81%AA%E6%93%8D%E4%BD%9C%E6%96%B9%E6%B3%95): ファイルメニューから棋譜の読み込み・保存ができる。
- リポジトリ内: `AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/02-project-direction.md`、本ファイル、`docs/learning/61-shogihome-auto-resign-logs.md`、`docs/knowledge/usi-shogihome-gameplay.md`、`docs/knowledge/usi-engine-response.md`、`docs/roadmap-usi-shogihome.md`、`kaname-shogi-usi`。

## 🚧 現在の物理的状態 (Physical Anchor)

- **作業ディレクトリ:** `/Users/oki2a24/kaname-shogi`
- **最終確認Git状態:** `main`、`origin/main` より6コミット先行。HEADは `1429e34 第60回のShogiHome試用を引き継ぐ`。次セッションで必ず `git status --short --branch` と `git log -3 --oneline` を取り直す。
- **作業ツリー:** 初回状態から存在する未コミットの変更に、今回の第61回記録、確定知識の更新、本引き継ぎ・`docs/resume.md` 等の更新が加わっている。2026-10-04の最後の `git status --short --branch` は以下のとおり。次セッションでは必ず取り直し、現在の出力を正とする。コード・テストに変更はない。
  ```text
  ## main...origin/main [ahead 6]
   M README.md
   M docs/02-project-direction.md
   M docs/README.md
   M docs/knowledge/usi-shogihome-gameplay.md
   M docs/next-topics.md
   M docs/resume.md
   M docs/roadmap-usi-shogihome.md
  ?? docs/handover-shogihome-auto-resign-logs.md
  ?? docs/handover-shogihome-connection-guide.md
  ?? docs/learning/60-shogihome-son-trial.md
  ?? docs/learning/61-shogihome-auto-resign-logs.md
  ```
- **ブランチ制約:** `main` 以外で作業する方針だが、この環境では `.git` 内のrefを書けず、過去にも記録用ブランチ作成ができなかった。未コミットの文書差分を保持し、勝手にリセット・stash・上書きしない。コミットも `.git` の書き込み可否と文書レビュー後に扱う。
- **第61回の記録確認:** USIログ30行の本文一致、結果KIFの主変化38行（37手と投了）および別変化「1 中断」を確認した。第61回はコード・テスト変更がないため、テストは実行していない。
- **ShogiHomeの最後に確認した状態:** Mac版1.28.1。`kaname-shogi` の登録パスは `/Users/oki2a24/kaname-shogi/kaname-shogi-usi`、Ponder OFF、USIログ設定OFF（OFFへ戻してアプリを再起動した後にも確認）。UI上の現在状態は次セッションで再確認する。
- **ファイル所在:** 生ログはShogiHomeログフォルダー `/Users/oki2a24/Library/Logs/electron-shogi/usi-20261004_201234.log`。第60回元棋譜、試行用37手KIF、第61回結果KIFは `/private/tmp/` にあり、一時ファイルとして扱う。必要なログ原本は削除しない。
- **学習記録:** `docs/learning/61-shogihome-auto-resign-logs.md` に本人回答と補足を追記済み。記録内容のユーザー確認・Gitコミットはまだ済んでいない。

## 📝 次の具体的なアクション (Next Steps)

1. 新しいセッションで最初に `git status --short --branch` と `git log -3 --oneline` を実行し、上記の作成時点の状態と区別する。
2. `AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/02-project-direction.md`、本ファイル、`docs/learning/61-shogihome-auto-resign-logs.md`、ShogiHome/USI知識メモ、ロードマップ、`kaname-shogi-usi` を選んで読む。
3. ShogiHome公式資料を再確認する。公式資料の内容は変わり得るため、1.28.1の実機で見たメニュー名・現在設定と分けて記録する。
4. `superpowerssuperpowers:brainstorming` を使い、手順書の目的はすでに確認済み（アシスタントが依頼時に迷わず接続を一度で行えること）。保存場所、通常接続とログ付き観察をどう分けるか、KIF再現時の保護・カーソル確認、復帰手順など未決定の点を一問ずつ相談する。
5. 手順書の対象範囲・構成・確認方法を具体案として提示し、明示承認前に手順書ファイルの作成・修正へ進まない。既存経験だけで確認できる事項と、次回アプリで再確認が必要なUIを分ける。
6. 合意後、再利用手順を作成する。少なくとも、(a) アプリ・登録エンジン・起動可能な正規パス・Ponderの事前確認、(b) 未保存棋譜の保護と対象局面の明示、(c) ローカル対局の開始、(d) ログ取得が目的の場合だけUSIログを有効化して再起動し、原本を開く手順、(e) 監視画面とプロンプトを補助に限定する方法、(f) 対局後のセッション終了確認と設定復帰、(g) 失敗時に手動USIコマンドや推測で状態を変えず停止する条件、を範囲候補として検討する。何を入れるかは相談・承認後に確定する。
7. 実機操作が追加で必要なら、変更・対局の具体案を先に提示して明示承認を待つ。コード・テスト変更が必要だと判明した場合は独立した実装計画を作り、承認前は変更しない。
8. 作成後は出典リンク、版差の注記、記録との整合性、文書差分を確認し、結果・未解決事項を学習記録へ記録する。実施していない接続確認や承認を記録しない。
9. 文書を本人が確認した後にコミットを扱う。第61回記録と既存未コミット文書を混同せず、作業ツリーの差分を保全する。

## 💬 再開用プロンプト (Resumption Prompt)

> kaname-shogi の次テーマ「ShogiHome接続手順書を作成する」を始めてください。新しいセッションの最初に `/Users/oki2a24/kaname-shogi` で `git status --short --branch` と `git log -3 --oneline` を実行し、現在の未コミット差分を過去の引き継ぎ記載と区別してください。`AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/02-project-direction.md`、この引き継ぎ、`docs/learning/61-shogihome-auto-resign-logs.md`、`docs/knowledge/usi-shogihome-gameplay.md`、`docs/knowledge/usi-engine-response.md`、`docs/roadmap-usi-shogihome.md`、`kaname-shogi-usi` を読み、ShogiHome公式のエンジン登録・スクリプト起動・ログ・基本操作の一次資料も再確認してください。ユーザーの目的は、ShogiHomeへの接続を依頼したときアシスタントが迷わず一度で進められる再利用手順書を作ることです。第61回の実例では、登録ランチャー `/Users/oki2a24/kaname-shogi/kaname-shogi-usi`、Ponder OFF、USIログ有効化後の再起動、37手KIFの対象手を明示選択する確認がありました。最初にBrainstormingで未決定の保存場所・手順書の範囲・確認方法を一問ずつ相談し、具体的な手順書案を明示提示して承認を待ってください。承認前に手順書を作成・編集せず、実機設定変更や対局を追加で行う必要がある場合も具体案を示して明示承認を待ってください。今回のUSI通信を他の対局の必須要件と一般化せず、`docs/learning/61-shogihome-auto-resign-logs.md` の本人回答は `bestmove resign` と `gameover lose`、`quit` はその後の別コマンドという補足も維持してください。コード・テスト変更は必要性が分かった場合に別計画と承認を得てから検討してください。`
