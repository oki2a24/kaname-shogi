# 🔄 Session Handoff: CLIで読込失敗時の表示と状態保持を一回観察する

## 🎯 最終目標 (Ultimate Goal)

- 新しいセッションで通常CLIを実際に起動し、時計つきセッションの「不正な棋譜・妥当な時計」と「妥当な棋譜・不正な時計」を一例ずつ読み込む。
- `load`失敗時に端末へ実際に出たエラーと、その後に同じ人間手番へ戻る様子を記録する。**実際の端末出力を会話にもコードブロックで示す。予想した文言を実出力として提示しない。**
- 失敗前後に保存したセッションJSONを比較し、棋譜・時計が保持されたかを確認する。
- 観察と学習記録までを対象とし、製品コード・テスト・設定・承認済み設計を変更しない。実装へ進まない。
- 最後に確認問題を一問だけ出し、本人の回答を待つ。本人回答とアシスタント補足を分けて記録し、未回答を完了としない。

## ✅ 完了した事項と「意思決定の背景」 (Done & Why)

- [済] 前テーマ「読込失敗時に棋譜と時計を保つ理由を固定例で確認する」は、紙上照合と最後の確認問題への回答まで完了した。[学習記録](learning/cli-record-load-failure.md)に固定例、本人回答、補足がある。
  - 本人回答:「不正なまま受け入れるとゲームが成立しない可能性があるため」
  - 補足では、棋譜と時計を一つのセッションとして検証・置換する理由、および時計のない旧v1棋譜をコンピュータ対局の起動時条件から補う成功経路を記録した。
- [済] 今回の候補1「CLIで読込失敗時の表示と状態保持を一回観察する」を本人が選定した。
  - 本人からの条件:「実際にどんな出力となるかを見せること」
  - 選定理由は尋ねていないため、本人の動機として推測しない。
- [済] 開始前にGit状態、Ruff固定版、ローカルhooksPath、再開案内、直近テーマの記録、README・知識メモ・承認済み設計の関係箇所を照合した。

## 📍 物理的な作業状態 (Physical Anchor)

引き継ぎ準備開始時の現物は次のとおり。新セッションでは必ず現在値を再確認し、この記録を現物より優先しない。

```text
$ git status --short --branch
## main...origin/main [ahead 3]
?? .antigravity/tasks/

$ git log -3 --oneline --decorate
27b660e (HEAD -> main) docs: record CLI load failure study
a39ef7b docs: prepare record load failure learning handoff
9d2f499 docs: record clocked CLI save-load observation

$ git branch --show-current
main

$ .venv/bin/ruff --version
ruff 0.16.10

$ git config --local --get core.hooksPath
.githooks
```

`requirements-dev.txt`の固定値は`ruff==0.16.10`で一致した。`.antigravity/tasks/`は今回も変更しない。引き継ぎ文書の更新コミット後は、`main`が`origin/main`より4コミット先となる想定。次セッションではGitの現物を再確認する。

## 🧭 次に行うこと (Next Steps)

1. 新セッションで最初に`git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`を実行し、[AGENTS.md](../AGENTS.md)、[docs/resume.md](resume.md)、本引き継ぎの記録を現物と照合する。Ruff固定版とローカルhooksPathも確認する。
2. [README](../README.md)のCLI起動・対局・保存/読込、[通常対局CLIの知識メモ](knowledge/32-human-vs-computer-cli.md)、[棋譜保存の知識メモ](knowledge/30-game-record-file-save.md)、[承認済みCLI時計設計](plans/2026-10-20-cli-search-time-control-design.md)の読込失敗・時計検証・旧v1互換を読み直す。[前テーマの学習記録](learning/cli-record-load-failure.md)で採用済みの固定値も照合する。
3. 一時ファイルを使い、実際のCLIを人間対コンピュータ・ランダム方式で起動する。10分・30秒を設定し、先手人間の入力中にする。固定状態には、二手後に先手人間の番となる時計つき棋譜を使う。以前の観察時に作成した`/tmp/kaname-shogi-clocked-roundtrip-before.json`が存在し、棋譜・時計を確認できれば再利用する。無い場合は既存のCLI形式に従う有効な一時fixtureを用意する。リポジトリ内の製品ファイルは変更しない。
4. 各失敗例の直前と直後に`save <path>`で一時JSONを保存する。次の二候補を`load`する。
   - **不正な棋譜・妥当な時計:** 先手7七→7六、後手3三→3四、先手7六→7四（歩の二マス移動で不合法）。時計は初期`600000ms`、秒読み`30000ms`、先手`590000000000ns`、後手`580000000000ns`。
   - **妥当な棋譜・不正な時計:** 先手7七→7六、後手3三→3四の二手で、先手人間番となる棋譜。時計の先手残りを`true`、後手残りを`580000000000ns`にする。boolは時計値の整数条件に違反する。
5. PTY等で取得した実際のCLI出力から、入力した`load`、エラー文、盤面・履歴の表示、同じ人間手番へ戻ったことが分かる範囲を、文言を整えずに保存する。最終応答でも2ケースそれぞれの実出力をコードブロックでユーザーに示す。表示が長い場合は、開始・失敗・復帰が連続して分かる実際の範囲を切り出し、省略箇所を明記する。
6. 前後JSONを比較し、棋譜・時計が失敗前の状態と一致するかを確認する。旧`kaname-shogi-game-record-v1`の時計なし成功経路は、失敗ケースと混ぜず、今回の観察に必要なときだけ別の成功例として扱う。
7. 一回の観察結果・実出力・終了状態・本人の確認回答/補足を`docs/learning/`へ記録し、`docs/README.md`のテーマ行を更新する。最後の確認問題は一問だけ出す。本人の回答が届くまでは未完了として扱う。

### 読み直す資料

- [ルートREADME](../README.md)
- [CLI進行と時計](knowledge/32-human-vs-computer-cli.md)
- [棋譜ファイル保存](knowledge/30-game-record-file-save.md)
- [承認済みCLI時計設計](plans/2026-10-20-cli-search-time-control-design.md)
- [前テーマの固定例・本人回答・補足](learning/cli-record-load-failure.md)
- [文書更新ガイド](documentation-guide.md)

## ⚠️ 制約と未確認事項 (Constraints & Open Questions)

- 選定テーマは実動作の観察と学習記録まで。コード、テスト、設定、承認済み設計の変更や実装計画の作成へ進まない。
- 自動テスト・テストスイートを実行しない。通常CLIを人が操作する一回の観察として扱う。
- 端末で実測した文言だけを実出力として示す。エラー文、盤面、時計表示、入力プロンプトの見え方は設計文書から推定しない。
- `save`による前後比較は観察資料であり、保存・読込の時間を時計から差し引かない契約は知識メモで確認する。値の一致はこの実行例に限る。
- 時計のない旧v1棋譜は時計つき形式の読込失敗と別経路。コンピュータ対局では起動時条件から時計を作る既存の成功経路として扱い、不正時計からの補完と混同しない。
- `.antigravity/tasks/`は引き続き触らない。新セッション開始時に現在状態を再確認する。

## 💬 再開用プロンプト (Resumption Prompt)

```text
/Users/oki2a24/kaname-shogi で、選定済みテーマ「CLIで読込失敗時の表示と状態保持を一回観察する」を始めます。
最初に `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current` を実行し、AGENTS.md、docs/resume.md、docs/handover-cli-record-load-failure-observation.mdを現在の状態と照合してください。Ruff固定版とローカルhooksPathも確認してください。
README.mdのCLI起動・対局・保存/読込手順、docs/knowledge/32-human-vs-computer-cli.md、docs/knowledge/30-game-record-file-save.md、docs/plans/2026-10-20-cli-search-time-control-design.mdの読込失敗・時計検証・旧v1互換の関係箇所を読み直してください。前テーマのdocs/learning/cli-record-load-failure.mdにある固定値も照合してください。
通常CLIを人間対コンピュータ・ランダム方式・10分・30秒で起動し、二手後に先手人間番となる時計つきセッションを基準状態にしてください。各失敗例の前後で一時ファイルへsaveし、次の二例を一回ずつloadしてください。
1. 不正な棋譜・妥当な時計: 先手7七→7六、後手3三→3四、先手7六→7四。時計は初期600000ms、秒読み30000ms、先手590000000000ns、後手580000000000ns。
2. 妥当な棋譜・不正な時計: 先手7七→7六、後手3三→3四。先手残り時計をtrue、後手を580000000000nsにする。
`load`失敗時の実際の端末出力（load入力、エラー、盤面・履歴の表示、同じ人間手番への復帰が分かる範囲）をそのまま採取し、最終応答にも2ケース分の実出力をコードブロックで必ず見せてください。予想した文言を実出力として書かず、長い出力を切り出す場合は省略箇所を明記してください。前後JSONの棋譜・時計も比較してください。
このテーマは観察と学習記録までです。製品コード・テスト・設定・承認済み設計を変更せず、実装へ進まないでください。自動テストも実行しないでください。最後の確認問題は一問だけ出して私の回答を待ち、本人回答と補足を分けて記録し、未回答を完了扱いにしないでください。
```
