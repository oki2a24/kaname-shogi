# 引き継ぎ：時計なし旧v1棋譜の通常CLI読込と起動時計補完を観察する

## 最終目標

時計のない旧`kaname-shogi-game-record-v1`を通常CLIで一度読み込み、コンピュータ対局の起動時計条件から時計が補われる成功経路を、実際の表示と保存JSONで確認する。対象は一回の手動観察と学習記録まで。製品コード・テスト・設定・承認済み設計を変更せず、自動テストも実行しない。

このテーマの後は、本人が指定した順序どおり、ShogiHomeで全幅最大4手とαβ最大4手を実践検証する。今回の観察と最後の理解確認が完了する前に、後続テーマを始めない。

## 完了した事項と選定理由

- [済] CLI時計の設計・実装テーマはTask 1〜5、検証、独立レビュー、main統合、取り込み先検証、最後の理解確認まで完了している。[実施記録](learning/cli-search-time-control-plan.md)によると、当時の全体テスト623件、Ruff検査も成功した。
- [済] 時計つき保存・再読込の成功経路を一回観察し、棋譜と時計のJSONを照合した。[学習記録](learning/cli-clocked-record-roundtrip.md)
- [済] 読込失敗時の不正棋譜・不正時計を一例ずつ通常CLIで観察し、実出力と前後JSON一致を記録した。[学習記録](learning/cli-record-load-failure-observation.md)
- [未] 時計なし旧v1の成功読込は、設計・知識資料では確認したが、通常CLIではまだ実行していない。
- [選定理由] 本人は「CLIの時計機能は2をやれば完了ですか？そうであれば2とします。その後1」と指定した。候補2は現在計画されているCLI時計機能の最後の観察であり、完了すれば予定済みのCLI観察が揃う。ただし、全局面・全OS・実時間性能を証明する意味ではない。
- [次の順序] 今回の後に行うShogiHome検証も本人が順序指定済み。時間管理テーマから四手探索の元の主線へ戻る。

## 開始時の資料と事実

- 元の主線は、開発用の全幅・αβ比較から両方式のCLI/USI対局接続へ進み、その後ShogiHome実機で両方式を実践検証すること。最後の実機検証だけが未確認。
- CLI時計は、両方式の対局接続後に派生した補助テーマ。時計つき保存・読込と失敗保持の観察は済み、時計なし旧v1成功経路の観察が残っていた。
- 旧v1は時計つき`kaname-shogi-cli-session-v1`とは別形式。コンピュータ対局中に旧v1を読むと、CLI起動時の初期時計条件から先後の時計を作る仕様である。時計つき形式の失敗検証と混ぜない。
- 次テーマ選定時に作ったロードマップと現在の順序は[次テーマ一覧](next-topics.md)、再開時の状態は[再開案内](resume.md)を参照する。

## 物理的な作業状態

この引き継ぎ作成前、2026-10-21に確認した状態：

```text
$ git status --short --branch
## main...origin/main [ahead 1]
 M AGENTS.md
 M docs/02-project-direction.md
 M docs/documentation-guide.md
 M docs/next-topics.md
 M docs/resume.md
?? .antigravity/tasks/

$ git log -3 --oneline --decorate
0eadcac (HEAD -> main) docs: record CLI load failure observation answer
0500be8 (origin/main, origin/HEAD) docs: prepare CLI load failure observation handoff
27b660e docs: record CLI load failure study

$ git branch --show-current
main
```

これは引き継ぎ更新前のスナップショット。次セッションでは必ずGitの現在値を読み直し、この記録から推定しない。`.antigravity/tasks/`は既存の未追跡物で、この作業で変更しない。

## 次の具体的な行動

1. 新セッションで`git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`を実行し、`AGENTS.md`、`docs/resume.md`、本引き継ぎと照合する。`.venv/bin/ruff --version`と`git config --local --get core.hooksPath`も確認する。
2. [README](../README.md)のCLI起動・対局・時計・`save`/`load`、[通常対局CLIの知識](knowledge/32-human-vs-computer-cli.md)、[棋譜保存の知識](knowledge/30-game-record-file-save.md)、[承認済みCLI時計設計](plans/2026-10-20-cli-search-time-control-design.md)の旧v1互換と時計補完箇所、[時計つき成功観察](learning/cli-clocked-record-roundtrip.md)、[読込失敗観察](learning/cli-record-load-failure-observation.md)、ロードマップを読む。
3. リポジトリ外の一時領域に、正しい`kaname-shogi-game-record-v1`形式で、先手7七→7六・後手3三→3四の二手を持つ有効な棋譜JSONを用意する。時計のキーを含めず、内側の棋譜形式が旧v1であることを確認する。既存の一時ファイルが残っているとは仮定せず、保存形式は知識メモと既存実例から確認する。
4. `python3 -m kaname_shogi`で通常CLIを起動し、人間対コンピュータ・ランダム方式・10分・30秒を選ぶ。先手人間の手番で`load <旧v1ファイル>`を一回実行する。
5. 実際の端末から`load`入力、成功時の表示、読込後の盤面・二手の履歴、先手人間へ進んだことが分かる範囲を未整形で採取する。表示文言を設計資料から予測して書かない。読み込んだ直後に一時パスへ`save`し、保存JSONの棋譜・時計全体を確認する。
6. 起動条件から先後の時計が補われたかをJSONの実値と表示の両方で確認する。時計なし旧v1の中身と、時計つきCLIセッション形式へ保存された後の内容を区別して記録する。保存データは観察時の証拠であり、実行前に期待した文言を実出力として扱わない。
7. 一回の実行条件、端末出力、前後または読込前後のJSON比較、確認できたことと限界を`docs/learning/`へ記録し、`docs/README.md`を更新する。最後の理解確認を一問だけ出し、本人の回答を待つ。本人回答と補足を分けて記録するまで未完了扱いにする。
8. 最後の理解確認の記録後、本人指定済みの次テーマ「ShogiHomeで全幅最大4手・αβ最大4手を実践検証する」への引き継ぎを整える。ShogiHome操作前に`.agents/skills/shogihome-connection/SKILL.md`と`docs/shogihome-connection-guide.md`を確認し、画面・登録先・時計・停止条件を現在状態と照合する。

## 読み直す資料

- [ルートREADME](../README.md)
- [CLI進行と時計](knowledge/32-human-vs-computer-cli.md)
- [棋譜ファイル保存](knowledge/30-game-record-file-save.md)
- [承認済みCLI時計設計](plans/2026-10-20-cli-search-time-control-design.md)
- [時計つき成功観察](learning/cli-clocked-record-roundtrip.md)
- [不正入力の失敗観察](learning/cli-record-load-failure-observation.md)
- [学習ロードマップ・選定状況](next-topics.md)
- [文書更新ガイド](documentation-guide.md)

## 制約と未確認事項

- 旧v1読込の成功経路を一回観察する。コード、テスト、設定、承認済み設計、実装計画は変更しない。
- 自動テスト・テストスイートは実行しない。
- 端末表示は実測した文言・結果だけを記録する。長い出力を切る場合は省略箇所を明記する。
- 起動時計補完を一つのCLI条件で確認する結果であり、全局面・全OS・実時間応答・棋力を保証しない。
- `.antigravity/tasks/`は変更しない。
- 今回の理解確認が終わるまでShogiHomeの次テーマを開始しない。

## 再開用プロンプト

```text
/Users/oki2a24/kaname-shogi で、選定済みテーマ「時計のない旧v1棋譜を通常CLIで読み、起動時計の補完を一回観察する」を始めます。
最初に `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current` を実行し、AGENTS.md、docs/resume.md、docs/handover-cli-legacy-v1-clock-completion-observation.mdを現在の状態と照合してください。Ruff固定版とローカルhooksPathも確認してください。
README.mdのCLI起動・対局・時計・save/load、docs/knowledge/32-human-vs-computer-cli.md、docs/knowledge/30-game-record-file-save.md、docs/plans/2026-10-20-cli-search-time-control-design.mdの旧v1互換・時計補完箇所、docs/learning/cli-clocked-record-roundtrip.md、docs/learning/cli-record-load-failure-observation.md、docs/next-topics.mdの学習ロードマップを読み直してください。
リポジトリ外の一時領域に、有効な旧 kaname-shogi-game-record-v1（先手7七→7六、後手3三→3四、時計フィールドなし）を用意してください。通常CLIを人間対コンピュータ・ランダム方式・10分・30秒で起動し、先手人間の手番でこの旧v1を一回loadしてください。成功時の実端末出力、盤面・二手の履歴・先手人間への復帰を採取し、直後に一時JSONへsaveして棋譜と補われた時計を照合してください。文言を予想で補わず、長い出力を切る場合は省略箇所を明記してください。
このテーマは一回の実機観察と学習記録までです。製品コード・テスト・設定・承認済み設計・実装計画を変更せず、自動テストも実行しないでください。観察結果・JSON・限界をdocs/learning/へ記録し、docs/README.mdを更新してください。最後の確認問題は一問だけ出し、本人回答と補足を分けて記録し、回答前に完了扱いしないでください。
この後のテーマは本人指定済みの「ShogiHomeで全幅最大4手・αβ最大4手を実践検証する」です。今回の記録と理解確認が済むまでは開始しないでください。
```
