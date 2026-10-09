# kaname-shogi

## プロジェクト概要

`kaname-shogi` は、将棋のルールを学びながら、ゼロから少しずつ育てていく自作の将棋プログラムです。

最初の目標は、コマンドラインで動く、ごく弱くても自分で理解できるプログラムを作ることです。強さだけを急がず、将棋とプログラムの両方を理解しながら育てます。息子と将棋を通じて成長を共有できるものにすることも、このプロジェクトの大切な目的です。

最初の目標は達成しました。第54回ではMac版ShogiHome 1.28.1と使い捨てプローブ間のUSI通信を実機確認し、第55〜58回ではUSI一手表記、局面再現、合法な一手応答、コマンド状態を実装・検討しました。全281テストと独立レビュー2回を確認して `main` に取り込み済みです。第59回はShogiHome 1.28.1で通常応手2回と人間の投了による終了を確認し、2026-10-04に `main` へ取り込んで全283テストが成功しました。

第60回では息子が平手の先手として19手を指し、`kaname-shogi` の18応手がShogiHomeの棋譜に記録されました。第61回はその37手局面を再現し、ShogiHome 1.28.1のUSI通信ログから今回の一例としてエンジンの `bestmove resign` と後続するShogiHomeの `gameover lose`、`quit` を確認しました。この一例を全対局の必須要件とは扱いません。第62回では人間向けの[ShogiHome接続手順書](docs/shogihome-connection-guide.md)と、このリポジトリで発見できる[接続用Codexスキル](.agents/skills/shogihome-connection/SKILL.md)を整え、ShogiHome 1.28.1で通常対局を一局だけ実証しました。先手の７六歩にエンジンが５二金右で応じたこと、投了後にエンジンが終了したことを画面で確認しています。USIログは採取していません。詳細は[第60回学習記録](docs/learning/60-shogihome-son-trial.md)、[第61回学習記録](docs/learning/61-shogihome-auto-resign-logs.md)、[第62回学習記録](docs/learning/62-shogihome-connection-guide.md)、[次テーマ候補](docs/next-topics.md)、[ShogiHome対局の確定知識](docs/knowledge/usi-shogihome-gameplay.md)、[USI接続ロードマップ](docs/roadmap-usi-shogihome.md)、現在地は[再開案内](docs/resume.md)を参照してください。

第63回では、CLIとShogiHomeの両方で難易度を選べる設計を承認しました。第64回ではその設計に基づき、一様ランダムを最弱・既定値として保ちながら、谷川浩司さんの参考値を使う一手後の駒得評価を実装しました。CLIは対局開始前に選び、USIは `Difficulty` optionで指定します。2026-10-05に `main` へ取り込み、取り込み先で全305テストが成功しました。第65回ではShogiHome 1.28.1のDifficulty画面とMaterial設定のUSI送信を確認しました。第66回では同じ7手局面でRandomが☖９四歩、Materialが☖８八角成を選ぶ一例を観察し、USIログでも両方のDifficulty値と着手を確認しました。この結果から、この局面ではMaterialが駒得を選んだと結論できますが、他局面での一般性までは示しません。両局は先手の切れ負けで終わりましたが、正常終局は主題ではないため再試行しません。第67回ではSFENの読込・書出しとUSI `position sfen` を実装し、独立レビュー、全326テスト、`main` 統合後の全体テスト、最終理解確認まで完了しました。第68回ではShogiHome画面へのSFEN貼り付け、第69回ではShogiHome 1.28.1からの `position sfen` 送信と合法な一手応答を一局面で確認しました。第70回では入力手数4が送信時1になる経路を公式ソースと照合し、第71回では接続用スキルを現行化しました。詳細は[第66回学習記録](docs/learning/66-shogihome-material-move-effect.md)、[第67回学習記録](docs/learning/67-sfen-position-conversion.md)、[SFEN局面表記の知識メモ](docs/knowledge/sfen-position-notation.md)、[次テーマ候補と選定履歴](docs/next-topics.md)、[第69回の実測記録](docs/learning/69-shogihome-sfen-engine.md)、[第70回の調査記録](docs/learning/70-shogihome-sfen-move-number.md)、[第71回のスキル保守記録](docs/learning/71-shogihome-connection-skill-update.md)、[再開案内](docs/resume.md)、[第65回学習記録](docs/learning/65-shogihome-difficulty-verification.md)、実装記録は[第64回学習記録](docs/learning/64-weakest-mode-difficulty-selection-implementation.md)、仕様は[難易度選択設計](docs/plans/2026-10-05-weakest-mode-difficulty-selection-design.md)、実装計画は[第64回実装計画](docs/plans/2026-10-05-weakest-mode-difficulty-selection-implementation-plan.md)を参照してください。

## 現在できることと主な未対応事項

第68回ではShogiHome 1.28.1の画面に3手後局面の4欄・3欄SFENを貼り付け、盤面・後手番・持ち駒なしの表示を確認しました。第69回では同じ4欄SFENの一局面から、USIログの `position sfen`・時間付き `go`・`bestmove 9a9b` と、盤面・棋譜への後手の合法手の反映を確認しました。画面への貼り付けと、エンジンへの送信・応答は別の確認です。

入力SFENの手数4は送信時1になりました。第70回に照合した公式ShogiHome 1.28.1と固定依存tsshogi 2.3.4では、局面読込で入力手数を保持せず、読み込んだ局面を新しい棋譜の開始局面としてUSI生成時に手数1を付けます。盤面・手番・持ち駒は保たれ、平手初期配置へ戻る意味ではありません。現行仕様と公式ソースへの参照は[SFEN知識](docs/knowledge/sfen-position-notation.md)、実測・調査の履歴は[第69回](docs/learning/69-shogihome-sfen-engine.md)・[第70回](docs/learning/70-shogihome-sfen-move-number.md)、現在の作業状況は[再開案内](docs/resume.md)を参照してください。

平手の初期配置から、次の3形式で対局できます。

1. 人間対人間
2. 人間対コンピュータ（先手が人間、後手がコンピュータ）
3. コンピュータ対コンピュータ

盤上移動、成り・不成、駒取り、持ち駒、駒打ち、二歩、行き所のない駒、王手、自玉を王手にさらす手の禁止、詰み、打ち歩詰め、投了を扱います。コンピュータは対局ごとに「最弱（一様ランダム）」か「駒得を考える」を選べます。未指定時は最弱です。駒得方針は各合法手を一手だけ適用した後、盤上と持ち駒の参考点数差を比較し、最高点の手から同点ランダムで選びます。探索はしません。

対局中の成功手はメモリ上の棋譜へ記録されます。人間の手番では、開始局面と指し手履歴を専用JSON形式へ明示的に保存し、後から読み込んで再開できます。

対局中の局面表示では、盤の上に後手、下に先手の持ち駒を表示します。持ち駒がない場合は「なし」、ある場合は駒名と枚数を確認できます。

ライブラリには、USI一手トークンと内部の一手データの相互変換、平手の `position startpos moves <1手以上>` からの局面再現、SFENの読込・正規化書出し、USI `position sfen <SFEN>` 単独または `moves <1手以上>` 付きの局面再現、USIコマンドから合法な一手を返す専用エンジン入口があります。`position startpos` 単独は未対応です。手数欄のないSFENは手数1として読み込み、書出しには手数欄を含めます。SFEN読込は構文と内部モデルでの表現可能性を検査しますが、駒総数や実戦での到達可能性などの局面の合法性は検査しません。USIエンジンは `Difficulty` comboに `Random` と `Material` を通知し、設定がない場合は `Random` を使います。ShogiHome 1.28.1では第59〜62回に平手対局・観察を行い、息子の対局では18回のエンジン応答、第61回では自動投了時の通信ログ1例、第62回では７六歩への５二金右の応答を画面で確認しました。第65回はDifficulty画面とMaterial送信、第66回はRandom/Materialの設定送信と実際の初手を確認しました。第66回の一局ずつの観察では、Materialが角を取る手を選びました。ShogiHome画面へのSFEN貼り付けは第68回で確認済みです。SFEN局面の送信と一手応答は第69回に一例確認しました。対応範囲は[SFEN知識](docs/knowledge/sfen-position-notation.md)と[USI応答知識](docs/knowledge/usi-engine-response.md)、操作条件は[接続手順書](docs/shogihome-connection-guide.md)と[専用スキル](.agents/skills/shogihome-connection/SKILL.md)を参照してください。

千日手、持将棋、入玉、時間管理、反則勝敗、複数手を読む探索や強さの保証、自動保存はまだ扱いません。駒得方針は一手後だけの評価です。ShogiHomeとの確認はMac版1.28.1の平手対局と、SFEN局面での一手応答の一例です。第75回では２手後SFENから２六歩を追加し、SFEN付き指し手履歴の送信と５二金右の合法応答を一局面で確認しました（[第75回学習記録](docs/learning/75-shogihome-sfen-moves-verification.md)）。他版・全局面・他の指し手履歴の実機互換性は未確認です。自動投了時の通信ログは37手局面からの一例です。Materialが駒を取る手を選ぶ実例は一つ確認しましたが、他局面でも駒得を選ぶ一般性、長い探索の有無、時計動作や他の終局・コマンドの互換性は未確認です。コンピュータ対コンピュータには手数上限がなく、詰み、合法手なし、または `Ctrl-C` で停止します。

実行と単体テストにはPython標準ライブラリだけを使います。開発時の整形・静的検査には、プロジェクト内の仮想環境へRuffを導入します。

## 実行方法

動作確認環境はmacOS、Python 3.9.6です。リポジトリ直下で次を実行します。

```sh
python3 -m kaname_shogi
```

起動後に対局形式を1〜3から選びます。コンピュータが参加する形式では続けて方針を選びます。空入力で「最弱（一様ランダム）」、`2` で「駒得を考える」を選べます。人間対人間では方針を尋ねません。選択は一局中固定です。盤は先手視点で、左から9〜1筋、上から一〜九段です。`+` は先手、`-` は後手、`・` は空マスを表します。日本語を表示できる等幅フォントの端末を想定しています。

USIエンジンを標準入出力で起動する場合は、専用の実行入口を使います。

```sh
python3 -m kaname_shogi.usi_engine
```

この入口はUSIコマンドを読み、応答を標準出力へ返します。ShogiHomeで利用する場合は、リポジトリ直下の `kaname-shogi-usi` を実行ファイルとして登録します。第59回に2回、第60回に18回の応答が棋譜へ表示されました。第60回の自動投了時に実際に送られたUSI応答はログ未取得のため未確認です。

## CLI操作

人間の手番では、次のコマンドを入力できます。

対局中に `help` と入力すると、コマンドの書式と短い説明を表示します。表示後は同じ手番で入力を続けられます。

```text
help
```

表示される操作は、盤上の駒を動かす `move <出発筋> <出発段> <到着筋> <到着段> [+]`、持ち駒を打つ `drop <歩|香|桂|銀|金|角|飛> <筋> <段>`、`resign`、`save <path>`、`load <path>` です。`+` は成りを指定し、筋・段には全角数字も使えます。パスは空白を含まない一語です。保存成功後は同じ手番を続け、読込成功後は読み込んだ局面から再開します。

### 盤上の駒を動かす

```text
move <出発筋> <出発段> <到着筋> <到着段>
move <出発筋> <出発段> <到着筋> <到着段> +
```

最後の `+` は成りを指定します。例えば、先手の歩を７七から７六へ動かす入力は次のとおりです。

```text
move 7 7 7 6
```

### 持ち駒を打つ

```text
drop <歩|香|桂|銀|金|角|飛> <筋> <段>
```

例えば、歩を５五へ打つ入力は次のとおりです。

```text
drop 歩 5 5
```

### 投了する

```text
resign
```

投了した側の相手を勝者として表示し、局面と棋譜の指し手履歴を変更せずに終了します。コンピュータは投了しません。

### 棋譜を保存・読込する

```text
save records/game.json
load records/game.json
```

パスは空白を含まない一語で、相対パスと絶対パスを指定できます。保存先の親ディレクトリは自動作成しません。保存成功後は同じ手番を続け、読込成功後は読み込んだ局面を表示して、その局面の手番から続けます。

保存・読込の失敗、入力形式の誤り、不合法手は理由を表示し、局面・手番・履歴を変更せず、同じ人間手番で再入力を求めます。詰み、投了、EOF、`Ctrl-C` などで対局が終了した後は入力を受け付けません。

操作語と成りの `+` は半角です。区切りと筋・段には半角・全角の空白・数字を使えます。実装はPythonの `str.split()` を使うため、その他のUnicode空白も区切りになります。

## テスト

リポジトリ直下で次を実行します。

```sh
python3 -m unittest discover -s tests -v
```

テストメソッド名は検索や個別実行に使える英語とし、日本語docstringで確認する振る舞いと検出したい誤りを説明しています。`-v` を付けると、その日本語説明も表示されます。

## 別PCでの開発環境セットアップ

Python 3.9以上（`venv`・`pip`を利用可能な環境）、Git、初回パッケージ取得用のインターネット接続が必要です。セットアップはmacOS/Linux向けです。実測環境はmacOS・Python 3.9.6で、LinuxとWindowsネイティブは未実測です。Windowsと別Git worktreeへの導入は今回の対応範囲に含みません。

```sh
python3 --version
git --version
git clone https://github.com/oki2a24/kaname-shogi.git
cd kaname-shogi
python3 scripts/setup_dev.py
.venv/bin/ruff format --check .
.venv/bin/ruff check .
python3 -m unittest discover -s tests -v
```

すでにcloneしている場合は、そのリポジトリへ移動してセットアップコマンドから実行します。スクリプトは `.venv` の作成、`requirements-dev.txt` に固定したRuffの導入、バージョン確認、`git config --local core.hooksPath .githooks` を行います。グローバルのPython環境やGit設定は変更しません。既存フックとの競合は上書きせず停止します。依存関係の取得に失敗した場合も、フックを新たに有効化しません。

`.venv` とローカルGit設定はcloneで引き継がれません。PCごと・cloneごとに実行してください。`.venv` を別PCへコピーせず、同じ手順で作成します。セットアップは再実行可能で、依存関係の固定版が更新されたときも再実行します。

### 日常の整形・検査とコミット

```sh
.venv/bin/ruff format .
.venv/bin/ruff check .
git diff
python3 -m unittest discover -s tests -v
# 内容を確認して対象をgit addし、git commitする
```

Ruffの対象はPythonファイルです。行長88・Python 3.9を対象とし、リンターは `E4,E7,E9,F` だけを有効にしています。基本的な誤りを確認する設定であり、型検査や将棋ルールの正しさの保証ではありません。

通常の `git commit` では、**ステージした全Pythonファイルと設定**を一時領域へ複写し、整形とリンターの両検査を実行します。未ステージの変更と未追跡ファイルは検査に混ぜません。失敗するとコミットが止まるので、修正・差分確認・再ステージしてから再試行してください。フックは自動修正や再ステージ、パッケージ取得を行いません。Pythonファイルや設定のシンボリックリンクは拒否します。Gitの `--no-verify` で回避する運用は採用しません。

フック設定と固定版の確認：

```sh
git config --local --get core.hooksPath
.venv/bin/ruff --version
```

期待値は `.githooks` と `ruff 0.16.10` です。フックの検査は単体テスト・レビューの代わりにはなりません。

### 手動構築と環境の再作成

スクリプトが行う主要な操作は次のとおりです。既存フックがある場合は、統合方法を決めてから設定してください。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/ruff --version
git config --local core.hooksPath .githooks
```

Python更新やディレクトリ移動で `.venv` が動かなくなった場合は、使用中の仮想環境を終了し、`.venv` を削除せず別名へ退避してセットアップを再実行してください。退避先は既存の名前と重複させないでください。スクリプトは壊れた環境や既存ファイルを自動削除しません。Linuxで `venv`・`pip` がない場合は、利用するPython配布元の手順で用意してから再実行してください。

設計理由・検証・レビューは[開発環境整備の記録](docs/learning/ruff-local-quality-gate.md)、実装計画は[Ruff導入計画](docs/plans/2026-10-09-ruff-local-quality-gate.md)を参照してください。

## 文書案内

- [文書索引：目的・テーマ・学習回から資料を選ぶ](docs/README.md)
- [ShogiHomeへの接続手順：通常対局・KIF再開・USIログ](docs/shogihome-connection-guide.md)
- [プロジェクトの背景](docs/01-project-background.md)
- [プロジェクトの方向性](docs/02-project-direction.md)
- [学習・開発の再開案内](docs/resume.md)

## 名前について

`Kaname` は、息子の名前「要」に由来します。「全体を支える大切なところ」という意味も、このプロジェクトが少しずつ積み上がっていく姿に重なります。

## ライセンス

未定です。公開の形や利用範囲を考える段階で決めます。
