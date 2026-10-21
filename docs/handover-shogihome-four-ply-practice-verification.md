# 引き継ぎ：ShogiHomeで全幅最大4手・αβ最大4手を実践検証する

## 最終目標

元の探索強化主線へ戻り、ShogiHomeでこのリポジトリのエンジンを使い、`FullWidth4`（全幅最大4手）と`AlphaBeta4`（αβ枝刈り最大4手）の両方を実際に選んで対局応答を観察する。選んだ設定・盤面・時計の条件で確認できた動作を記録し、全局面の正しさ、期限内応答、棋力向上へ一般化しない。

この引き継ぎは実機操作の記録ではない。次セッションで現画面と合意条件を確認し、ShogiHome接続スキル・手順書の停止条件に沿って進める。

## 完了した事項と次テーマ選定の背景

- [済] 開発用比較で全幅読みとαβ枝刈りの二・三・四手を比較し、評価・最善候補・訪問回数を確認した。
- [済] 両方式を通常CLIとUSIの対局方式へ接続し、実装・検証・独立レビュー・main統合・取り込み先検証・最後の理解確認まで完了した。[実装記録](learning/four-ply-search-game-integration-plan.md)と[承認済み実装計画](plans/2026-10-19-four-ply-search-game-integration-implementation-plan.md)を参照する。
- [未確認の帰還目標] ShogiHomeで両方式を実際に選ぶ確認が残っている。`docs/02-project-direction.md`はこれを元の探索強化主線の帰還目標としている。[学習ロードマップ](next-topics.md)にも主線と補助テーマの関係を記録している。
- [完了した補助テーマ] CLI時計の設計・実装と計画済み観察を完了した。最後の時計なし旧v1観察では、2026-10-21にランダム方式・10分・30秒の通常CLIで旧v1を一度読み、端末の時計補完表示と直後の保存JSONを照合した。本人回答とアシスタント補足を[学習記録](learning/cli-legacy-v1-clock-completion-observation.md)へ記録済み。これはShogiHomeでの次テーマとは別のCLI観察である。
- [選定] 本人は、旧v1観察の後に「ShogiHomeで全幅最大4手・αβ最大4手を実践検証する」と指定した。これから両方式を確認する順序は本人の指定済みで、未着手の追加テーマを選び直す必要はない。

## 対象範囲と保留条件

- 対象はShogiHome上で`FullWidth4`と`AlphaBeta4`をそれぞれ選び、実際の応答を観察すること。別の方式、コード修正、テスト追加、時間制御の設計変更へ広げない。
- どの開始局面・先後・時計・対局数・終了方法を使うか、USIログを採るかは、この記録ではまだ決めていない。次セッションで依頼と現画面を照合し、未決条件を一問ずつ具体化する。過去の10分＋30秒や他のShogiHome実測値を既定・推奨条件として流用しない。
- `docs/shogihome-connection-guide.md`の通常対局手順に従う。新規平手対局では人間先手・エンジン後手とし、エンジンに初手から指させない。別の開始局面を使う場合は、開始局面・手番・棋譜保全・時計・終了方法を明確にして手順書の対象条件を満たす。
- ShogiHomeの版、現在画面、エンジン登録パスとこのチェックアウト内の`kaname-shogi-usi`の実在・実行可能性、`USI_Ponder`、監視タブ上の稼働中セッション、未保存棋譜を開始時に確認する。食い違い・不明・保全されていない棋譜があれば推測で続けず止まる。
- 登録先・Ponder・ログ等のアプリに残る設定変更は、変更前の値と具体的な変更・影響を示し、本人の明示承認を得る。USIログ採取は依頼・合意がない限り行わない。ShogiHomeのプロンプト欄へUSIコマンドを手入力しない。
- 依頼した範囲の実対局を終えたら、実際に選ばれた設定と応答、画面・棋譜・ログで観察できた証拠、終了・設定復帰の有無を分けて記録する。一回の実機条件を全局面・全OS・期限内応答・棋力の保証にしない。
- 学習記録に条件・手順・実測・未確認事項を残し、最後の理解確認を一問だけ出す。次のテーマは本人が指定済みだが、ここに記した範囲の実機確認と理解確認を終える前に、さらに後続の学習・実装へ進まない。

## 次セッションで最初に読む資料

1. `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`を実行し、現在値とこの引き継ぎ作成時点を区別する。
2. `AGENTS.md`、`docs/resume.md`、本書、`docs/next-topics.md`冒頭の学習ロードマップ、`README.md`のUSI・ShogiHome案内、`docs/02-project-direction.md`を読み、主線・現在地・未確認目標を照合する。
3. [接続スキル](../.agents/skills/shogihome-connection/SKILL.md)と[ShogiHome接続手順書](shogihome-connection-guide.md)を操作前に読む。操作条件は現在の画面・手順書・現行の知識メモ・公式資料から確認し、過去の学習記録や引き継ぎを現在の画面条件に使わない。
4. [現行USI応答知識](knowledge/usi-engine-response.md)、[探索停止知識](knowledge/search-stop.md)、[時間予算知識](knowledge/time-budget.md)、[ShogiHome対局知識](knowledge/usi-shogihome-gameplay.md)、[承認済み対局接続計画](plans/2026-10-19-four-ply-search-game-integration-implementation-plan.md)を確認する。以前のテスト成功・画面・アプリ版・登録先を今回の実測として扱わない。
5. `docs/learning/cli-legacy-v1-clock-completion-observation.md`は直前の補助テーマ完了の背景として参照する。CLIの成功表示や時計値をShogiHomeの動作証拠へ転用しない。

## 現在の物理的な作業状態

旧v1観察を始めた時点のHEADは`f850f01`、ブランチは`main`、`origin/main`より2コミット先行し、未追跡`.antigravity/tasks/`があった。旧v1観察の学習記録、文書索引、再開案内、ロードマップ、今回の引き継ぎを一緒に更新している。次セッションでは開始時の現Git状態を再取得し、この引き継ぎ作成時点の記録と区別する。

直近の手動確認は`python3 -m kaname_shogi`による通常CLIの一回観察で、終了コード0。開始時のRuffは固定版`0.16.10`と一致し、`core.hooksPath=.githooks`。`git diff --check`と今回の学習記録内の相対リンク確認は成功した。自動テストは実行していない。ShogiHomeの画面確認・エンジン起動・対局・ログ採取はこの引き継ぎ準備では行っていない。

## 再開用プロンプト

```text
/Users/oki2a24/kaname-shogi で、本人指定済みテーマ「ShogiHomeで全幅最大4手・αβ最大4手を実践検証する」を始めます。
まず `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current` を実行し、AGENTS.md、docs/resume.md、docs/handover-shogihome-four-ply-practice-verification.md と現在の状態を照合してください。引き継ぎ記載のGit状態は履歴であり、開始時の実測を優先してください。
`docs/next-topics.md`冒頭の学習ロードマップ、README.mdのUSI/ShogiHome案内、docs/02-project-direction.md、承認済みの全幅4手・αβ対局接続計画と実施記録、現行のUSI応答・探索停止・時間予算・ShogiHome対局の知識を読み、元の主線と未確認の帰還目標を照合してください。
ShogiHomeを操作する前に `.agents/skills/shogihome-connection/SKILL.md` と `docs/shogihome-connection-guide.md` を読み、現在の画面・版・登録先・チェックアウト内の `kaname-shogi-usi`・USI_Ponder・監視タブの稼働セッション・未保存棋譜を実状態で確認してください。過去の画面・登録パス・時計条件を現在値として使わないでください。
確認対象は ShogiHomeで `FullWidth4` と `AlphaBeta4` をそれぞれ選んだ場合の実際の応答です。開始局面・先後・持ち時間/秒読み・対局数・終了方法・USIログ採取の要否で未決の条件があれば、接続スキルと手順書に従って必要なことを一問ずつ具体化してください。10分＋30秒などの過去の値を推奨・既定として流用しないでください。
開始前に画面上の設定と依頼条件を一致させ、通常平手なら人間先手・エンジン後手としてください。登録先やPonder等の永続設定変更、ログ採取が必要なら、変更前の値・変更内容・影響を示して別途明示承認を待ってください。盤面・手番・時計・稼働状態に不一致がある場合は、指し手やコマンドを送らず停止してください。USIコマンドをShogiHomeのプロンプト欄へ直接入力しないでください。
合意された範囲だけを観察し、実際に選んだ方式・画面上の応答・対局結果・証拠・終了状態・設定復帰・限界を記録してください。観察後に最後の理解確認を一問だけ出し、本人回答を待ちます。コード・テスト・設定変更へ広げず、自動テストも実行しないでください。
```
