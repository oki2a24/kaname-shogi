# 承認済みCLI設計から実装計画を作る

## 目的と範囲

2026-10-20開始。本人の指定により、[承認済み設計](../plans/2026-10-20-cli-search-time-control-design.md)から実装計画を作成・独立レビュー・提示する。製品コード・テスト・設定・承認済み設計を変更せず、TDD・実装へ進まない。今回の選定や過去の設計承認を計画承認と扱わず、計画承認後も別の実装指示を待つ。

## 開始時の照合

指定された三コマンドを最初に実行した。作業場所は`/Users/oki2a24/kaname-shogi`、main、HEAD `f3a05b8`、origin/mainより5コミット先行。直近3件はf3a05b8・2e9a11d・ae828e5。追跡ファイル変更なし、未追跡`.antigravity/tasks/`あり。引き継ぎ準備開始時2e9a11dの後に引き継ぎ記録コミットが加わった状態で、矛盾はない。

Ruffは`ruff 0.16.10`、requirements-dev.txtの固定`ruff==0.16.10`と一致。ローカル`core.hooksPath`は`.githooks`。セットアップの再実行は不要だった。作業用`codex/cli-search-time-control-plan`を同じディレクトリに作成した。最初はsandboxの.git書込制限で失敗し、同じコマンドを許可された権限で実行して作成した。別worktreeは作成していない。mainへの取り込み・pushは行わない。既存未追跡ディレクトリは保持する。

## 参照と具体化

AGENTS.md、docs/resume.md、[開始時引き継ぎ](../handover-cli-search-time-control-plan.md)、文書ガイド・索引、承認済み設計と本人回答・撤回合意、READMEの通常CLI/USI/開発用入口、方向性、search-stop/time-budget/usi-engine-responseを参照した。現物cli.py・__main__.py・game_search.py・game_record.py・time_management.py・search_control.pyとusi_engine.pyの予算/制御接続、およびCLI・棋譜・探索接続・予算・制御・USI時計/四手の関連テストを読み取り確認した。製品テストは実行していない。

using-superpowers、writing-plans、roadmap-management、requesting-code-review、verification-before-completionを適用。個人観察`~/.codex/observations/test-driven-development.md`と[検出力点検](../knowledge/test-coverage-review.md)に従い、契約・具体的誤り・独立期待値・代表ケース・単独と既存全体の補完・未検証を計画へ対応付けた。

[計画全体](../plans/2026-10-20-cli-search-time-control-implementation-plan.md)は時計、棋譜公開境界と保存単位、五方式の制御付き接続、入力/表示/実入口、保存読込統合の5段階。初期条件・時計値の型、公開操作名、run_game直接呼出しの互換性と既定値、テスト移行を、設計から委任された細部として具体化した。作成時点では未承認案だった。下記の本人承認後も実装済みAPIではない。

USIとの共通部は同じsearch_move・loader・予算計算・SearchControl・結果型。CLIで追加する時計値の保持・返却後判定・保存は対局管理責務。CLI専用二モジュールはその責務を分けるものでUSIへ変更を加える判断ではない。コンピュータ手の事前詰み/全合法生成、完了深さ/手の由来表示を復活させない。ShogiHome固定版の100ms周期/イベント順まで同じにする計画でもない。

## 独立レビューと検証

初回の独立レビューはCritical 0 / Important 1 / Minor 0。ImportantはTask 3の既存テスト移行不足。現物で妥当性を確認し、receiving-code-reviewに従い次を計画へ追加した。

- コンピュータ手番のis_game_overを終了条件にしていた新二方式テストを、固定時計で二手の実探索＋三回目のCLI探索入口でCtrl+Cへ移行する。終了用の呼出しと二回の完了を区別する。
- 人間がコンピュータを詰ませた既存テストはCOMPLETE/Noneによる投了表示へ移行し、人間手番の詰み表示と区別する。
- 既存のコンピュータ駒打ちテストは全合法手生成差替えからSearchResult返却へ移し、表示・履歴・盤面の保証を維持する。

計画・本記録・再開案内・索引の独立再確認はCritical 0 / Important 0 / Minor 0、計画全体を提示可能との結論。読み取り専用の文書と現物比較であり、製品テスト・コード変更・変異注入はしていない。将来手順に書いたRed/Green・変異注入・製品回帰は今回の実績ではない。

文書4件について相対リンク先587件、末尾空白・最終改行を検査し問題0、git diff --check成功。開始HEADから製品コード・テスト・設定・承認済み設計の差分なしも確認した。文書だけの作業のため製品テストを実行せず、過去の成功を今回の結果へ流用していない。提示時点では計画内容が未承認だったため、文書を未コミットで提示した。

## 計画全体への本人承認

独立レビュー・指摘対応・再確認と文書検証後、計画全文へのリンクと5段階の順序、契約と検証の対応、USIとの差分、未実施事項を提示した。

承認確認：「全文に記載したAPIの具体化・手順・検証方法を含め、この計画全体を承認しますか？」

本人回答：`yes`

2026-10-20、これを計画全体の明示承認として記録する。TDD・実装開始・main取り込みへの承認とは扱わない。承認段階更新の独立点検もCritical 0 / Important 0 / Minor 0。文書4件の相対リンク先588件・末尾空白・最終改行とgit diff --checkを確認した。作業ブランチへ文書をコミットし、実装開始は別の指示を待つ。今回、確認問題はまだ出しておらず、回答を推測していない。

今回の振り返り：共通探索の内部契約は既存検証を再利用できるが、CLIの原点・時計更新・着手可否・保存状態の同時置換は接続固有の確認が必要。次回への問いは、実装へ進む場合にどの実行方法を選ぶか。未決のまま実装開始と扱わない。
