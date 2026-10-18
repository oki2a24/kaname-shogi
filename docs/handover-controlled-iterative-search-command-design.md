# 引き継ぎ：時間制御付き反復を試す開発用コマンドの学習・設計

## 最終目標と今回の選定範囲

2026-10-18、本人が次候補の「2」を選び、「時間制御付き反復を試す開発用コマンドを設計する」を次テーマに選定した。実装済みの探索部品を、小さいSFEN局面で人が追える入口につなぐための学習・設計までを扱う。

推薦理由は、既存部品の予算・深さ・終了状態・完了結果を確認する方法を整理し、通常対局の設定・通信・並行処理まで一度に広げず、理解できる小さな段階で進められるため。今回の選定は具体的なコマンド仕様の承認ではなく、実装計画や実装への承認でもない。

本人から現セッション継続の希望はないため、新セッションで始める。本人が本書の再開プロンプトを新セッションへ入力するまで、次テーマの学習・一次資料調査・設計・実装計画・TDD・コードやテスト変更を始めない。現セッションでは引き継ぎの作成・保存まで。

## 完了事項と意思決定の背景

前テーマは「承認済み設計から実装計画を作り、計画の明示承認後に段階的に実装・検証・独立レビューまで進める」。本人が計画を明示承認し、5段階を実装した。別承認「yes」でmainへ取り込み、取り込み先検証と最後の理解確認も完了した。

- 初回準備で生成順の合法予備手だけを確保する。通常停止の保護は最初の合法手の確定または手なし確定までで、打ち歩詰めの下位防御調査にも渡す。抑制は保護しない。深さごとに保護を再開しない。
- 同じSearchControlと時計原点を準備・全深さ・子へ渡す。目標は次の深さを始める直前だけ、上限・通常停止・抑制は深さ内部でも確認する。予算式と設定は変更していない。
- 深さの完了は最後の評価後と根の最終確認まで通過して確定する。未完了の手・点・訪問数で前回完了記録を上書きしない。累計は完了反復だけ。
- 内部の中断はSearchInterrupted（中断データ）で返し、完了型とのユニオンとする。共通親クラスや仮の評価は設けない。専用例外による中断案は、本人との前段の検討で採らなかった。故障は例外で原因を保って伝える。
- 最終ControlledSearchResult（終了結果データ）はCOMPLETE / NO_LEGAL_MOVE / STOPPED / SUPPRESSED。通常停止なら最新完了手または予備手、抑制なら手なし。完了記録自体は抑制時も保持できる。
- 旧反復入口は一件ずつ完了記録を渡す遅延取得、新入口は同期で最終結果一件。準備で手なしなら新入口は完了記録なし、旧入口は深さ1の記録一件という違いがある。再帰と反復の本体は共有した。
- Random（最弱・既定）、一手駒得、現行二手先読みを維持。新方式は通常対局・USI・CLIの方針へ未接続。比較コマンドも停止なし入口のまま。

最後の理解確認では本人が最初に「返す手と保持する完了記録は深さ2」と答えた。抑制では手なし・記録は深さ2と補足し、「記録があっても手を返さない理由」の再確認に「Ctrl+Cなどの終了のため」と回答した。終了などで応答不要という趣旨を確認してテーマを完了した。Ctrl+Cがどの停止経路になるかは呼出し側次第で、全入口で同じ抑制と決めつけない。

詳しい採否・初回回答・補足・TDD・レビュー・検証の履歴は[前テーマの学習・実施記録](learning/iterative-deepening-stop-time-control-implementation.md)へ保存済み。

## 現在の物理的状態

- 作業場所：`/Users/oki2a24/kaname-shogi`、main。引き継ぎ作成開始HEADは `605b0a3`、clean、origin/mainより14コミット先。直前は0be1c7a、04de2ae。引き継ぎ保存後のHEAD・差分・aheadは次セッションで再取得する。
- 実装：ca59b63（データ）、8d4ced6（将棋公開境界）、73a0264（共有再帰）、db31d03（将棋接続）、30fe837（共有反復）。最終記録80e3db0までmainへ統合、統合記録04de2ae、理解確認と候補記録605b0a3。
- 今回の作業ブランチcodex/iterative-deepening-stop-time-control-implementationは統合・検証後に通常削除した。pushしていない。
- 今回の作業で別worktreeを作成・利用していない。今回 `git worktree list` では、元ディレクトリ以外に既存4件（2e7a、9c92、cedb、usi-move-notation-record）を確認した。別テーマの既存worktreeであり、未変更・未整理。前テーマの「別worktreeなし」は今回の作業で追加利用なしの意味として扱い、リポジトリ全体に存在しないと推測しない。
- Ruff0.16.10はrequirements-dev.txtと一致、ローカルhooksPath=.githooksを引き継ぎ作成時に確認した。新セッションで再確認する。
- 取り込み先80e3db0の直近製品検証：`.venv/bin/python -m unittest discover -s tests -v` は546件30.083秒OK。Ruff format --checkは63ファイル変更不要、check成功。統合後のコード・テスト変更なし。今回は引き継ぎ文書のみのため製品テストを再実行していない。
- 各段階とブランチ全体の独立レビューを実施。最終Critical 0・Important 0・Minor 0。代表変異11件の単独assert FAILと復元後成功も確認済み。有限の確認を全局面の証明とは扱わない。
- 補助スクリプト・変異ログは一時ディレクトリに保存した履歴であり、新セッションで存在するとは限らない。計画専用の一時台帳とレビューパッケージは整理済み。正本はGit内の設計・計画・学習記録。
- 新テーマの設計・計画・実装は未開始。時間内応答・実時間性能・全局面/OS/スケジュール・新方式USI競合・実機対局・棋力・最適予算は未検証。

## 次に読む資料と現物

1. AGENTS.md、[再開案内](resume.md)、本書を現在のGit状態と照合する。
2. [文書索引](README.md)、[次候補と本人選定](next-topics.md)、ルートREADMEの開発用探索比較・制約、docs/02-project-direction.md。
3. docs/knowledge/search-stop.md、time-budget.md、search-comparison.md。既存の時間予算・中断データ・比較入口の責務を区別する。
4. docs/plans/2026-10-18-iterative-deepening-stop-time-control-design.md、同implementation-plan.md、docs/learning/iterative-deepening-stop-time-control-implementation.md。合意済みの探索部品契約は土台とし、コマンド仕様まで承認済みと解釈しない。
5. kaname_shogi/search/iterative_deepening.py:75（制御付き反復入口）、alpha_beta.py:28、shogi.py:73、result.py:43以降、contracts.py。SearchControlとSearchBudgetはsearch_control.py、time_management.py。
6. kaname_shogi/search/compare_iterative.py:41（既存コマンド）、comparison.py（SFEN入力・手/評価表示）、compare.py。既存のKeyboardInterrupt→終了130は比較コマンドの契約であり、新入口へそのまま採用済みとはしない。
7. tests/test_search_iterative_deepening_controlled.py、test_search_alpha_beta_controlled.py、test_search_shogi_controlled.py、test_search_controlled_result.py、test_search_compare_iterative.py、test_search_comparison.py、test_search_control.py。設計の期待値や既存契約の補完を調べるときに読む。
8. ~/.codex/observations/test-driven-development.md、docs/knowledge/test-coverage-review.md、docs/documentation-guide.md。新セッションの関連スキルを現物から確認する。

## 次の具体的な行動と未決定事項

1. 最初に `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current` を実行する。過去の546件成功やHEADを現在の実測へ流用しない。
2. 開発環境と引き継ぎ・現物を照合し、brainstorming等の適用を確認して学習・設計を始める。確認問題は一問ずつ出し、本人回答を待つ。
3. 小さいSFEN局面、予算・上限深さの指定、終了状態・完了深さ・選択手等の表示に必要な契約を本人と明確にする。これらは候補の観点であって、引数名・表示形式・既定値の承認ではない。
4. 既存比較コマンドの拡張か別入口か、比較探索を同時に行うか、予算を直接指定するか、Ctrl+Cや通常停止/抑制の扱い、標準出力/標準エラー、終了コード、手なし/記録なし表示、入力不正と故障の区別は未決定。学習・一次資料・既存境界を踏まえて設計する。特に単一threadでKeyboardInterruptを捕捉するだけで最新結果を取得できるとは決めつけない。
5. 設計全体を独立レビューし本人へ提示して承認を待つ。承認後も今回の範囲は学習・設計まで。実装計画、TDD、コード・テスト変更、通常対局・USIへの接続に自動移行しない。

## 再開用プロンプト

> `/Users/oki2a24/kaname-shogi` で、選定済みテーマ「時間制御付き反復を試す開発用コマンドの学習・設計」を新しいセッションで始めます。
>
> まず `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current` を実行し、`AGENTS.md`、`docs/resume.md`、`docs/handover-controlled-iterative-search-command-design.md` を現物と照合してください。案内に沿って既存の探索部品・比較コマンド・知識・設計・テストを読んでください。
>
> 今回は学習・設計・独立設計レビュー・設計提示までです。実装計画・TDD・コードやテスト変更は始めず、確認問題は一問ずつ出して回答を待ってください。予算・深さ・終了状態・完了記録等の指定と表示を、既存部品の責務を保って検討してください。コマンド構成やCtrl+Cの扱いは未決定です。
>
> Random（最弱・既定）、一手駒得、現行二手先読みを維持し、通常対局・USIへの新方式接続、予算式変更、時間保証は対象外にしてください。過去の検証結果を現在の実測と扱わず、設計全体は独立レビュー後に提示して明示承認を待ってください。
