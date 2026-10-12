# Session Handoff: 時計・停止接続後の実機確認条件だけを決める

2026-10-12作成。新セッション開始時の背景と物理状態を保存する。現在の操作条件・実測値は再開時に現物と照合する。この引き継ぎは実機操作の手順書ではない。

## 最終目標

本人が選定した「時計・停止接続後の実機確認条件だけを決める」を新セッションで開始する。完成した入力並行処理・時計・探索停止の検証範囲と、GUI実通信や時間内応答の未検証範囲を分け、実機で何を確認し、どの条件で止め、何をもって判断するかを具体案にする。今回は条件の作成・レビュー・提示まで。実機操作・計測・対局・ログ採取・設定変更・コードやテスト変更は含めない。本人が新セッションへ再開プロンプトを入力するまで、このテーマの学習・条件検討を始めない。

## 完了した事項と意思決定の背景

### 入力並行処理・USI接続

- 承認済み全体設計から接続計画を作成・独立レビューし、本人「承認する」、続いて「実装開始して下さい」により実装した。計画承認・実装開始・main取り込みを別段階で扱った。
- main/current threadが命令を管理し、一入力threadと各goの一探索threadをQueueで接続する。入力完成行の読取り時刻と、共通Lock内での入力確定は別。読取り原点から受渡し・前担当回収・解析・複製・起動も予算へ含めるため、整数nsをそのまま渡す。
- macOSの標準入力と内部終了pipeをselectorで待ち、nonblocking read・逐次復号を使う。単にreadlineを別threadへ移すだけでは無言/部分行入力中の故障後に回収できないため。借用stdinを閉じず属性復元、自前pipe/selectorを解放する。
- 各goでPosition.copy・新SearchControl、同一実行のrngを共有する。既存三方式、時計受付、局内固定・次局継承・未知値保持・時間設定一回読込を維持。探索はsearch_move一回だけで、予備手や候補をUSI側へ重複所有しない。
- stopは通常停止、quit/EOF/gameover/禁止入力・故障は未送信応答を抑制。送信直前にも共通Lock内で再確認する。COMPLETE/Noneだけresign、SUPPRESSEDは無応答。write/flush完了後にsentを確定し、失敗時は再送しない。
- sentとthread終了は別。次go前に共通Lock外で前担当joinを待つ。gameoverは探索だけを回収して入力継続。故障はQueueで主担当を起こし、入力取消・探索/入力join・入力源解放を行う。後片付け故障でも残る解放を試み、主原因と追加原因を診断する。
- CLIの従来選択処理、探索評価・JSON・係数・起動スクリプト・Ruff設定は変えていない。厳密な期限内応答、全競合・全OS、接続後のShogiHome実対局安全性は未保証。

### 検証・レビューで得た根拠と限界

- TDDで旧同期処理に対する探索中受付・抑制・原点のFAIL、故障通知の欠落による有限親タイムアウトFAILなどを確認した。新たな追加ケースの初回Greenと未実装Redを区別して[実施記録](learning/input-concurrency-usi-plan.md)へ残した。子テストの初回SyntaxErrorはRedから除外。
- 通常応答の既存テストはbestmove Event後に次go/quit/EOFを渡す取消可能入力へ移行し、監視先をsearch_moveへ変更した。実探索の盤面・両持駒保存、時計・設定寿命の旧契約を維持した。
- 制御付きbootstrapは実session・実stdin入力源と別の継承pipeによる探索開始通知を使う。探索中readyok/stop/quit/EOF/gameover、無言/部分行での探索故障終了1を確認。実入口の三方式×時計なし/0予算、改行flush・stdout/stderr分離、通常ファイル/ptyも確認した。実search_moveを呼ぶ開始通知ラッパーのstop系列は自然完了先行もあり得るので、一般の探索中停止の証明とはしない。
- 隔離変異で原点起動時刻化・抑制再確認除去・sent前倒しをassertion FAIL、共通Lock内join・内部通知無視を有限親タイムアウトFAILで検出。最初のjoin変異は生存したためjoin呼出Eventを追加し再検出した。停止不能な子も親のterminate→kill→waitで回収し、強制回収を製品正常終了成功と数えない。
- 最終独立レビューImportant1件は、session故障と入力源close複数故障が重なると後続診断が漏れる点。再現FAIL後に入れ子診断を修正し全体回帰・独立再レビュー済み。コードと全ブランチパッケージの結論Critical/Important/Minor全0。最上位モデルのレビュー起動は利用上限で失敗し、代替独立レビュアーで確認した。自己レビューだけで済ませていない。
- 全OS/入力デバイス/局面/スケジュール、厳密期限、対局安全性は追加の実機・負荷確認が必要という裁定。誤って保証した場合のコストは停止不能や時間切れ。OS故障下の完全資源解放ではなく、残る解放を試みる契約。

### 統合と理解確認

本人「１」によりローカルmainへa9159d4までfast-forward統合。git pull --ff-onlyはAlready up to date。mainで全456件成功（9.817秒）、Ruff38ファイル整形済み・lint成功。統合記録54fb871、回答と次候補fe4371dをmainへ保存済み。取り込み済み作業ブランチは通常削除した。pushなし。

最後の問い「bestmove送信後も次go前にjoinする理由」へ本人「処理プロセスを完了させるため」。アシスタントは要点を認め、正確にはスレッドであり、終了処理を待って探索担当重複・rng同時使用を防ぐと補足した。本人回答と補足は記録済み。前テーマに未回答の理解確認はない。

### 次テーマの選定

小さい順に①時計・停止接続後の実機確認条件だけ、②Python更新の影響調査・移行案だけ、③三方式の構成調査だけを提示。完成した接続に直結し、実機の確認対象・終了条件を小さく定められるため①を推薦。本人「時計・停止接続後の実機確認条件だけを決める。新セッションの準備して」により①を選定した。Python更新・構成調査は保留。具体的な局面・時計・操作・ログ範囲・採否基準はまだ未決定。

## 現在の物理的状態

- 作業場所：`/Users/oki2a24/kaname-shogi`。別worktreeなし。
- 引き継ぎ準備開始HEAD：`fe4371d`。その時点でmain、差分なし、origin/mainより18コミット先行。
- 準備ブランチ：`codex/clock-stop-real-check-conditions-handoff`。mainのfe4371dから作成。今回の準備文書だけを保存し、準備ブランチはmain未統合。前テーマの実装はmainへ取り込み済み。
- Ruff：`.venv/bin/ruff --version` → `ruff 0.16.10`、固定版一致。hooks：`git config --local --get core.hooksPath` → `.githooks`。
- 直近の全体成功：main/a9159d4で `.venv/bin/python -m unittest discover -s tests -v` →456件、9.817秒。`.venv/bin/ruff format --check .` →38ファイル整形済み、`.venv/bin/ruff check .` →成功。準備文書の検証とは時点を区別する。
- 直近の文書成功：fe4371d保存前、変更6文書の相対リンク511件・見出し12件欠落0、git diff --check成功。通常コミットのフック成功。
- 現在のコード故障・未解決Critical/Important：なし。今回の準備ではコード・テスト・設定変更、エンジン起動・アプリ操作・計測・対局なし。
- 未検証：接続後の実機通信、時間内応答、係数妥当性、全OS/全競合。以前のShogiHome 1.28.2平手一例・最大約28.4秒は過去の旧接続時の観察であり、新接続の保証に使わない。
- タスクリスト：前テーマは実装/統合/検証/理解確認完了。次テーマは選定済み・新セッション開始待ち、条件未作成・未承認。実施は今回範囲外。

## 次の具体的なアクション

1. 以下の再開プロンプトを本人が新セッションへ入力する。アシスタントが新チャットを自動作成・送信して先に着手しない。
2. 指定4コマンドとAGENTS/README/文書ガイド/resume/本書で物理状態を照合し、上記の結果を現在の結果と同一視しない。
3. 次の現行資料を読む。操作条件の根拠は現行の手順書・仕様・知識・公式資料とする。過去ログ・学習・引き継ぎは背景と検証範囲の理解に使い、実機操作条件の補完に使わない。
   - [全体設計](plans/2026-10-11-clock-input-time-management-design.md)、[確認範囲](plans/2026-10-12-clock-input-verification-review.md)
   - [接続計画](plans/2026-10-12-input-concurrency-usi-implementation-plan.md)、[接続仕様](knowledge/usi-engine-response.md)、[探索停止](knowledge/search-stop.md)、[時間予算](knowledge/time-budget.md)
   - [実装・検証記録](learning/input-concurrency-usi-plan.md)、`tests/test_usi_process_concurrency.py`（実入口と制御bootstrapの範囲）、`tests/test_usi_concurrency.py`、`kaname_shogi/usi_engine.py`
   - [ShogiHome接続手順書](shogihome-connection-guide.md)、[ShogiHomeスキル](../.agents/skills/shogihome-connection/SKILL.md)、[接続知識](knowledge/usi-shogihome-gameplay.md)
   - [検出力点検](knowledge/test-coverage-review.md)、`~/.codex/observations/test-driven-development.md`
4. 準備中にShogiHomeスキルの適用範囲を確認したところ「エンジンは時計引数を時間管理に使わず」という旧前提が残っている。現行USI仕様の接続済みと一致しない。この準備では修正・実機操作せず、次セッションで関連現行資料との不一致を確認し、条件案の根拠へ古い前提を混ぜない。必要な文書整合の対象はその時点で明示する。
5. 適切な設計・レビュー用スキルを使い、確認対象、代表ケース、ログ等の観測方法、終了条件、時間内応答と使用感の判断範囲、未検証を条件案へ具体化する。具体値を過去の10分+30秒等から自動採用しない。学習・不明点は一問ずつ本人の回答を待つ。
6. 条件案を文書化・レビュー・提示し、本人の明示承認を待つ。実機操作・測定・対局・設定変更・ログ採取は開始しない。実施とmain取り込みも別承認とする。

## 再開用プロンプト

```text
/Users/oki2a24/kaname-shogi で、選定済みテーマ「時計・停止接続後の実機確認条件だけを決める」を開始してください。

最初に git status --short --branch、git log -3 --oneline、.venv/bin/ruff --version、git config --local --get core.hooksPath を実行してください。

AGENTS.md、README.md、docs/documentation-guide.md、docs/resume.md、docs/handover-clock-stop-real-check-conditions.md を読み、指定資料と現在の物理状態を確認してください。

main統合済みの時計・探索停止・入力並行処理の仕様と、実入口・制御bootstrap・実探索ラッパーの検証範囲を照合し、実機で確認する対象・局面と時計・操作・観測方法・終了条件・本人の判断方法・未検証事項を条件案へ具体化してください。ShogiHome手順書・スキルの旧時計前提と現行仕様の不一致も確認してください。過去の実測条件を今回の操作条件として自動採用しないでください。学習は一問ずつ進め、適切なスキルを使用してください。

今回は条件作成・レビュー・提示までです。コード・テスト・設定変更、エンジン起動、ShogiHome等の実機操作、ログ採取、計測・対局・係数調整は始めず、条件提示後に本人の明示承認を待ってください。実施開始とmain取り込みも別承認です。
```

## 引き継ぎ準備の検証

この節は文書の作成・入口更新後に実施結果を記す。前テーマ456件成功を今回の準備の新たなテスト実行とは扱わない。コード・実行手順の変更を含まない準備なので全体テストは再実行せず、差分・相対リンク・見出し・現在地整合と通常保存を確認する。

準備5文書の相対リンク472件・見出し11件欠落0、git diff --check成功。独立レビューはCritical/Important/Minor全0、参照先と物理状態・承認段階・旧前提注意の整合を確認した。レビュアーも新条件検討・実機操作・テスト再実行はしていない。通常コミットで保存し、実ハッシュとcleanは保存後に確認する。
