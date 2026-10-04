# 🔄 Session Handoff: 息子によるShogiHome試用（第60回予定）

## 🎯 最終目標 (Ultimate Goal)

- 息子がShogiHomeの画面から人間側として指し、弱い将棋エンジン `kaname-shogi` がUSIエンジンとして応じる対局を試す。
- プロジェクトの目的である「息子と将棋を通じて成長を共有する」ことに向け、ShogiHomeの盤面操作が分かりやすいか、ランダムな弱い応手でも試してみる価値があるかを本人の体験から知る。
- これは強さの測定や息子による開発作業ではない。既存エンジンを人間が実際に操作して試すテーマである。

## ✅ 完了した事項と「意思決定の背景」 (Done & Why)

- [済] 第59回「ShogiHomeで平手対局する」を完了した。
  - **Why:** 人間が先手、`kaname-shogi` が後手の平手対局をMac版ShogiHome 1.28.1で行い、以前は未確認だった通常の合法応手と終局を確かめるため。
  - **Crucial:** 棋譜・画面には人の７六歩、エンジンの４四歩、人の２六歩、エンジンの９二飛が順に表示された。人が投了すると「対局終了（投了）」が表示され、棋譜にも投了が記録された。棋譜ファイルへの保存・書き出しはしていない。
- [済] 第59回の実装・レビュー・統合・検証を完了した。
  - **Why:** ShogiHomeから起動可能な実行入口が必要だったため、承認済み計画で `kaname-shogi-usi` とランチャーテストを追加した。独立レビュー初回のImportant（`main()` の終了コードがランチャーへ伝わらない）をテスト追加で検出・修正し、再レビューではCritical 0、Important 0となった。
  - **Crucial:** 実装コミット `d7046c6` を `main` へfast-forward統合し、取り込み先で `python3 -m unittest discover -s tests -v` を実行して全283件成功を確認した。その後の変更は記録文書のみで、コード・テストは変えていない。
- [済] 次テーマ「息子によるShogiHome試用」を選定した。
  - **Why:** 技術的にエンジンがShogiHome上で応じて終了できることを確認した後は、強さを先に上げるより、本来の利用者がGUIで指せるかを試す順序がプロジェクトの目的に合うため。
  - **Crucial:** 本人は「ShogiHomeで人間が指し、`kaname-shogi`（弱い将棋エンジン）が応じる」という意味でよいと確認した。選んだのはテーマであり、対局の長さ、先後、終了方法、感想の聞き方、棋譜保存などの詳細はまだ合意していない。
- [済] 証拠の範囲を分けて記録した。
  - **第54回:** 使い捨てプローブが `position startpos moves 7g7f` と時間付き `go` の一例を受け、`bestmove resign`、`gameover lose`、`quit` を観測しただけである。`kaname-shogi` の合法応手をShogiHomeが受け入れた証拠ではない。
  - **第55〜58回:** USI一手変換、平手の手順再現、合法手応答、局面状態管理をローカル実装・テストで確認した。これらだけではGUI実対局の成立を示さない。
  - **第59回:** ShogiHome 1.28.1上で通常応手2回と投了終了を目視・棋譜表示で確認した。通信ログは取っていないので、送受信された全コマンドやPonder設定による通信差は未確認である。
- [済] 実機で使った設定に留意点がある。
  - **Why:** ローカルの [USIエンジン応答メモ](knowledge/usi-engine-response.md)では `go ponder` を未対応として拒否する。第59回はShogiHomeの設定画面に `USI_Ponder` が既定ONと表示されたため、PonderをOFFにして対局した。
  - **Crucial:** 第59回の通信ログはOFFであり、ShogiHomeが実際にどのコマンドを送ったか、OFF設定が送信内容をどう変えたかは観測していない。新セッションでは設定を改めて確認し、未確認のコマンドを推測で要件化しない。
- [済] 登録ランチャーのパスに注意が必要だと確認した。
  - **Why:** 第59回は作業ワークツリーにあるランチャーをShogiHomeへ登録したが、そのワークツリーは成果統合後にアーカイブした。
  - **Crucial:** 2026-10-04の引き継ぎ準備時、旧パス `/Users/oki2a24/.codex/worktrees/shogihome-gameplay/kaname-shogi/kaname-shogi-usi` は存在せず、安定したmain側の `/Users/oki2a24/kaname-shogi/kaname-shogi-usi` は実行可能ファイルとして存在した。ShogiHomeの登録設定が旧パスのままかは未確認なので、新セッションで画面を確認し、必要ならmain側ランチャーを登録し直す。設定を変更する前に実状態を確認する。

## 🚧 現在の物理的状態 (Physical Anchor)

- **作業ディレクトリ:** `/Users/oki2a24/kaname-shogi`
- **引き継ぎ準備開始時のGit状態:** `main`、HEAD `0aaee12 第59回の理解確認と次テーマ候補を記録する`、`origin/main` より5コミット先行、作業ツリーclean。今回の引き継ぎ準備が関連文書を更新・コミットするため、これは作成開始時の記録であり、新セッションの現在状態ではない。新セッションでは必ず `git status --short --branch` と `git log -3 --oneline` を実行する。
- **作業ワークツリー:** `/Users/oki2a24/.codex/worktrees/shogihome-gameplay/kaname-shogi` はCodexでアーカイブ済み。テーマ成果は元のmainへ統合済み。
- **安定したUSIランチャー:** `/Users/oki2a24/kaname-shogi/kaname-shogi-usi`。引き継ぎ準備時に実行可能ファイルとして確認した。
- **直近の成功検証:** 2026-10-04、`main` 統合後に `python3 -m unittest discover -s tests -v` を実行し、283件成功。以後のコード・テスト変更はない。新テーマがGUIの人間試用のみなら、ソーステストを目的なく繰り返さない。
- **直近の実機結果:** ShogiHome 1.28.1で平手、人間先手・エンジン後手。２回の合法応手と人の投了による終了を確認。対局設定は持ち時間10分+30秒が画面既定、Ponder OFF。時計精度は評価していない。
- **未確認のアプリ状態:** 引き継ぎ準備中にShogiHomeの登録一覧や現在の画面は再確認していない。保存済み登録がアーカイブ済み旧パスを指す可能性がある。アプリの起動状態、棋譜の保存状態、エンジン設定の現状も新セッションで確認する。
- **Snapshot:**
  - [x] 第59回実対局、独立レビュー、main統合、全283テスト、理解確認
  - [x] 第60回予定テーマ「息子によるShogiHome試用」を本人が選定
  - [x] 引き継ぎ準備前のmain側ランチャー存在確認と旧作業ワークツリーのアーカイブ確認
  - [x] 引き継ぎ文書・再開案内の作成とGitコミット
  - [ ] 人間が以下の再開用プロンプトを新しいセッションへ入力
  - [ ] 新セッションでGit・文書・一次資料・既存コード・ShogiHomeの実状態を確認
  - [ ] 試用の範囲・手順・確認方法を一問ずつ相談し、設計案の明示承認を得る
  - [ ] 承認後に息子によるShogiHome試用を行い、体験と結果を記録

## 📚 次に読むファイル

新セッションでは、まず現在のGit状態を確認してから、以下を読む。引き継ぎに書かれた状態は作成時点の記録であり、最新状態は必ず実際に確認する。

1. `/Users/oki2a24/kaname-shogi/AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/02-project-direction.md`。
2. この引き継ぎ、`docs/learning/59-shogihome-even-game.md`、`docs/knowledge/usi-shogihome-gameplay.md`、`docs/knowledge/usi-engine-response.md`、`docs/roadmap-usi-shogihome.md`。
3. `kaname-shogi-usi`、`kaname_shogi/usi_engine.py`、USI関連テストを読み、現行mainの起動方法・未対応事項を確認する。
4. [USI原案](https://hgm.nubati.net/usi.html)、[ShogiHome公式エンジン登録手順](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E7%99%BB%E9%8C%B2%E6%89%8B%E9%A0%86)、[ShogiHome公式のエンジン機能操作方法](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E3%82%92%E4%BD%BF%E3%81%86%E6%A9%9F%E8%83%BD%E3%81%AE%E6%93%8D%E4%BD%9C%E6%96%B9%E6%B3%95)を、現行の内容として確認する。
5. ShogiHomeの実際の版・エンジン登録パス・Ponder設定・記録状態を画面で確認する。旧作業ワークツリーのパスは既に存在しない。人間の試用開始前に、必要なら実行可能なmainランチャーへ登録先を直す。

## 📝 次の具体的なアクション (Next Steps)

1. 人間が次の再開用プロンプトを新しいセッションへ入力する。入力前に第60回の調査・試用を開始しない。
2. 新しいセッションで `git status --short --branch` と `git log -3 --oneline` を実行する。引き継ぎ文書のコミット後の状態を現物で確かめる。
3. 上記ファイル、USI一次資料、ShogiHome公式資料、既存コード・テストを確認する。第54回の使い捨てプローブ、第55〜58回のローカル実装、第59回のShogiHome実対局を明確に分ける。
4. `superpowerssuperpowers:brainstorming` を使用する。本人の意図を一問ずつ確認し、少なくとも参加タイミング、先後、試用の長さ・終了、操作の分かりやすさや弱い応手の受け止め方をどう確認するかを設計する。息子への連絡はせず、本人が実際に試用できる環境を準備する。
5. 実対局の範囲・手順・確認方法の案を示し、ShogiHomeで試用する前に明示承認を待つ。エンジンの起動・Ponder設定など実機状態も設計と承認の対象に含める。
6. コードまたはテスト変更が必要と分かった場合は、対象範囲・表現・検証を含む実装計画を作り、提示して明示承認を得るまで変更しない。変更が不要なら実機試用を中心に進める。
7. 実施後は観察した事実と本人・息子の感想を分けて記録する。試していない指し手・コマンド・時計機能を確認済みと扱わない。

## 💬 再開用プロンプト (Resumption Prompt)

> kaname-shogi の次テーマ「息子によるShogiHome試用」（第60回予定）を始めてください。最初に `git status --short --branch` と `git log -3 --oneline` で現在状態を確認し、`AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/02-project-direction.md`、この引き継ぎ、`docs/learning/59-shogihome-even-game.md`、`docs/knowledge/usi-shogihome-gameplay.md`、`docs/knowledge/usi-engine-response.md`、`docs/roadmap-usi-shogihome.md` を読んでください。USI一次資料とShogiHome公式資料、既存のランチャー・USIエンジン・関連テストを確認してください。第54回の使い捨てプローブで観測した `bestmove resign` の一例、第55〜58回のローカル実装、第59回にShogiHomeで確認した合法応手と投了終了、今回未確認の挙動を区別してください。次テーマの意図は息子がShogiHomeの画面から人間として指し、`kaname-shogi` が応じる試用です。先後・試用時間・終わり方・感想の確認方法は未決定なので、`superpowerssuperpowers:brainstorming` を使って一問ずつ相談し、試用の範囲・手順・確認方法の案を示して明示承認を待ってください。ShogiHomeの登録ランチャーはアーカイブ済み作業ワークツリーを指している可能性があります。旧パスの存在を前提にせず、実際の登録先を確認し、必要なら `/Users/oki2a24/kaname-shogi/kaname-shogi-usi` を使える状態に整えてください。Ponder設定も再確認してください。実機一例やUSI仕様から未確認のコマンド要件を推測しないでください。コードやテストの変更が必要なら実装計画を作成して提示し、承認前に変更しないでください。
