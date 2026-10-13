# Session Handoff: ShogiHomeで通常停止を観測する条件だけ

2026-10-13作成。本人は次テーマ「ShogiHomeで通常停止を観測する条件だけ」を選び、新セッションの準備を依頼した。これは開始時点の背景と物理状態の記録である。新セッション開始時にはGit状態と対象文書を再確認し、この記録を現在の実測や実施承認と混同しない。

## 最終目標

直接USIプロセスでは、探索中と推定できるCPU活動を観測した後に通常 `stop` を送り、合法な `bestmove` 一件と正常終了を一度確認し、本人が受け入れた。次は、その停止応答がShogiHomeからの実際の対局経路でどう観測できるかを調べ、**ShogiHomeで通常停止を一度観測するための条件案だけ**を具体化・独立レビューして本人へ提示する。

特に、ユーザーは前テーマの理解確認で「stopの場合はその後対局が続く可能性があるから」と回答した。通常 `stop` で返った合法手をShogiHomeが棋譜・盤面へ反映し、対局を続けられる経路なのかを中心に調べる。対局中断、時計切れ、解析中断が同じUSI `stop` を送ると決めつけず、どの画面操作が何を送るかをShogiHome公式資料と現行仕様から見分ける。

条件案には少なくとも、候補局面と選定根拠、探索を停止前に自然完了させないための考え方、合意する時計と操作、通常 `stop` の送信および一回の合法応答・対局継続のログ/画面証拠、有限の待機・終了条件、異常時の停止・棋譜保全・設定復帰、本人が結果を判断する材料、未検証事項を含める。画面操作が通常停止を送るか証明できない場合は未確定と明示し、別の操作や停止方法を推測で提案しない。

このテーマは条件作成・レビュー・提示まで。条件提示後は本人の明示承認を待つ。実施開始は別承認、main取り込みも別承認である。今回はShogiHome等の実機操作、エンジン起動、設定変更、ログ採取、計測、対局、コード・テスト・設定変更を行わない。

## 完了した事項と意思決定の背景

### 直近のShogiHome確認で通常停止が未達だった理由

- 2026-10-13の前テーマでは、ShogiHome 1.28.2のG2でC1 SFEN、TwoPlyMaterial、`go btime 0 wtime 0 byoyomi 8000` を使い、目標4,500ms/上限6,000msの実施条件で `bestmove 6f5g+` が4.516秒後に返った。合法性と棋譜への反映は確認した。
- エンジン応答後に予定していた通常停止操作が間に合わず、人間側が8秒の秒読みで切れ負けとなった。探索中の通常 `stop` 送信と、その後の応答は確認できなかった。これは通常停止の成功でもエンジンの秒読み超過でもなく、操作が間に合わなかったことによる未達である。
- G2のSFEN、持ち時間、秒読み、目標・上限、操作手順、起動数、再試行方針を今回の条件へ自動流用しない。過去の計画と記録は経緯確認に使うだけで、新条件の根拠は現行仕様・現行資料と今回の目的から改めて示す。

### 前テーマの直接USI観測と、方式を選んだ理由

- 2026-10-13、リポジトリルートから `python3 -m kaname_shogi.usi_engine` を一度起動し、C2 SFEN・TwoPlyMaterial・時計引数なし `go` を使った。標準入出力とflush時刻、一時制御役が記録したPIDのmacOS `proc_pidinfo(..., PROC_PIDTASKINFO, ...)` 累積CPU時間を観察した。
- 標準出力応答がない間にCPU時間が連続増加した後、約1.510秒で通常 `stop` を一度送り、約7.842ms後に合法な `bestmove 3b3a` が一件返った。1秒の重複観察窓に追加応答はなく、`quit` 後は終了コード0、標準エラーは空だった。CPU時間の増加はプロセス活動の補助証拠であり、探索関数が実行中だったことの完全な証明ではない。
- 一時合法手照合は作業ディレクトリに起因するimport path不足で失敗した。その失敗イベントと暫定判定を削除せず残し、リポジトリルートから読み取り専用の独立照合をして合法性を確かめた。エンジンは再起動・再試行していない。
- Terminal/Codex画面の取得はUI制御側の安全制限で拒否され、画像はない。JSONL時系列と合法手照合による受け入れを本人が認めた。これは直接USIでの一例に限り、ShogiHome上の実通信・時計期限停止・他局面は証明しない。
- 直接USIを使ったのは、直前の小テーマが「実エントリポイントのプロセスへUSI `stop` を送った後の応答」の切り分けだったためである。ShogiHomeの中断操作は対局終了の経路になり得て、時計切れにはGUI時計・エンジン内期限停止が関係し、解析中断は `go infinite` の経路となる。これらを混ぜずに直接プロセスの一例を観測した。今回の選定は、その方法で未確認のShogiHomeホスト経路を次の独立課題として扱うためであり、以前の直接USI方法をShogiHome上の確認とみなさない。
- 学習確認で本人は「stopの場合はその後対局が続く可能性があるから」と回答した。補足として、通常 `stop` は探索を止めて応答を返し、その合法手を受け取った呼び出し側が次の局面を渡せば対局を続けられるが、`stop` 自体が自動で対局を進めるわけではない。`quit` はプロセス終了なので一回応答を確認する代用にならない。この本人回答と補足は前テーマの[学習記録](learning/normal-stop-recheck-conditions.md)にもある。

### 現行実装・検査で確かめるべき境界

- 現行のUSI仕様では、通常 `stop` は未送信応答を抑制せず、合法な一手または手なし確定時の応答を一回返す。`quit`・EOF・`gameover` は保留応答を抑制する終端として区別される。時計期限停止と通常 `stop` も、どちらが停止要求を起こしたかを分ける。
- 既存検査の探索初期検索では、`tests/test_search_control.py` が停止制御、`tests/test_usi_concurrency.py` が同期された制御下の並行入力・応答、`tests/test_usi_process_concurrency.py` がプロセス境界と実探索ラッパーを対象にしている。`test_real_search_wrapper_receives_stop` は開始通知後に自然完了する競合もあり、実探索中に停止が届いたことを毎回保証する検査ではない。新セッションでは該当関数の現行本文、他の入口検査、ドキュメント更新後の差を再確認する。
- これらのリポジトリ検査はShogiHomeの画面操作、ShogiHomeが実際に送るコマンド、棋譜への反映、画面上の対局継続を立証しない。次セッションは検査範囲を読み合わせるだけで、検査・コードを変更・実行しない。

## 現在の物理的状態

- 作業場所は `/Users/oki2a24/kaname-shogi`。準備開始時に `git status --short --branch` は `## main...origin/main [ahead 26]`、`git log -5 --oneline` の先頭は `53b09a1 docs: 通常停止確認の完了と次候補を記録`、作業ツリーはcleanだった。
- 準備開始時の `.venv/bin/ruff --version` は `ruff 0.16.10`、`git config --local --get core.hooksPath` は `.githooks`。この文書一式のコミット後はmainがさらに進んでいるため、新セッションで状態を必ず再取得する。
- この準備で更新するものは本引き継ぎ、`docs/resume.md`、`docs/next-topics.md`、`docs/README.md` のみ。コード、テスト、設定、ShogiHomeの実画面・棋譜・設定・ログには触れていない。新テーマの調査・条件案作成もまだ始めていない。
- 前テーマの条件・レビュー・直接USI結果・本人受け入れは [計画と条件](plans/2026-10-13-normal-stop-recheck-conditions.md)、[学習・実施記録](learning/normal-stop-recheck-conditions.md)、[旧引き継ぎ](handover-normal-stop-recheck-conditions.md) にある。ログと補助証拠は `/private/tmp/kaname-normal-stop-20261013-081727JST/`。これらは過去の経緯であり、今のShogiHome状態や今回の実施条件ではない。
- 直近G2条件・物理復帰・証拠については [前テーマ記録](learning/clock-stop-real-check-conditions.md)、[G2条件](plans/2026-10-12-clock-stop-real-check-conditions.md)、[その開始時引き継ぎ](handover-normal-stop-recheck-conditions.md) を読む。前回見た画面・ShogiHomeの版・登録先・棋譜・時計・ログ設定が今も同じとは推定しない。
- 条件設計のための操作範囲は [ShogiHome接続手順書](shogihome-connection-guide.md) と [ShogiHome接続スキル](../.agents/skills/shogihome-connection/SKILL.md)を基準にする。公式資料へのリンクも同手順書にある。画面・対局・ログ設定への操作承認はこの準備に含まれない。

## 引き継ぎ文書のレビューと検証（2026-10-13）

- 独立レビューはCritical 0、Important 0、Minor 0。本人の回答と補足、次テーマの焦点、過去条件を自動採用しない指示、条件提示・実施開始・main取り込みの承認境界に不整合がないことを確認した。
- 本引き継ぎ、再開案内、次テーマ一覧、文書索引のローカル参照487件を照合し、欠落は0件。差分の `git diff --check` も成功した。
- 文書のみの準備でコードやテスト設計を変更していないため、テストは実行していない。ShogiHome操作・エンジン起動・設定変更・ログ採取・計測・対局も行っていない。

## 次の具体的なアクション

1. 作業場所を `/Users/oki2a24/kaname-shogi` にし、次の4コマンドをこの順で実行する。結果はこの記録の準備時点と区別する。
   - `git status --short --branch`
   - `git log -3 --oneline`
   - `.venv/bin/ruff --version`
   - `git config --local --get core.hooksPath`
2. `AGENTS.md`、`README.md`、`docs/documentation-guide.md`、`docs/resume.md`、`docs/next-topics.md`、本書を読み、前テーマの[直接USI条件と結果](plans/2026-10-13-normal-stop-recheck-conditions.md)、[学習記録](learning/normal-stop-recheck-conditions.md)、[G2未達記録](learning/clock-stop-real-check-conditions.md)を読む。
3. 時計・停止の現行契約として `docs/knowledge/usi-engine-response.md`、`docs/knowledge/search-stop.md`、`docs/knowledge/time-budget.md`、`docs/knowledge/usi-shogihome-gameplay.md`、`docs/knowledge/test-coverage-review.md` を読む。停止関連の既存テストを列挙して実コードと検出対象を確認する（少なくとも `tests/test_search_control.py`、`tests/test_usi_concurrency.py`、`tests/test_usi_process_concurrency.py`）。各テストがShogiHomeのホスト経路について証明すること・しないことを分ける。
4. [接続手順書](shogihome-connection-guide.md)、[接続スキル](../.agents/skills/shogihome-connection/SKILL.md)と、そこから参照されるShogiHome公式資料のうち停止・対局操作に関係する内容を読み、UI操作とUSIコマンドの対応が資料で確認できるかを調べる。現行の画面名・コマンドを知らないまま推測しない。資料に明記がなければ、操作と送信コマンドの対応は未検証事項として残す。今回の作業では画面を開かない。
5. 候補局面・先後・時計・操作タイミング・ログと画面の証拠・成功/未達の判定・有限の待機/終了・棋譜保全/設定復帰・本人の判断方法・未検証事項を条件案にする。通常 `stop` 後の応答がShogiHomeの盤と棋譜に反映され、ゲームを続けられることが狙いに含まれるかを明示する。対局中断・時計切れ・解析中断を同じ経路と決めつけない。
6. 具体的な時計値、局面、起動数、再試行、打切り値は今回の条件案のために根拠と限界を提示して再評価する。C1/C2やG2の数値、直接USIの一回で使ったC2、500ms/2秒等、前回の条件や上限を自動採用しない。実施操作が不明または復帰不能なら、より安全な手順を推測で足さず、案の限界と確認が必要な点を示す。
7. 条件案を独立レビューし、Critical/Important/Minorと対応を記録する。文書差分・相対リンクを確認した後に案を本人へ提示する。今回は提示で止まり、本人の明示承認を待つ。実施開始とmain取り込みはそれぞれ別承認。学習確認をする場合は一問だけ出して回答を待つ。

## 再開用プロンプト

> `/Users/oki2a24/kaname-shogi` で、選定済みテーマ「ShogiHomeで通常停止を観測する条件だけ」を開始してください。最初に `git status --short --branch`、`git log -3 --oneline`、`.venv/bin/ruff --version`、`git config --local --get core.hooksPath` をこの順で実行してください。`AGENTS.md`、`README.md`、`docs/documentation-guide.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/handover-shogihome-normal-stop-conditions.md` と、同引き継ぎに列挙した現行仕様・検査範囲・ShogiHome資料を読み、USI通常 `stop` の現行契約、既存テストが証明する範囲、ShogiHomeの操作とUSIコマンドの対応を照合してください。前回のShogiHome G2では合法な一応答は4.516秒で返りましたが、探索中の通常 `stop` とその後の応答は観測できず、人間側切れ負けで終了しました。その後、直接USIプロセスでは通常 `stop` 後の合法な一応答と正常終了を一度確認して本人が受け入れましたが、ShogiHome経路は未検証です。通常 `stop` では返った合法手をShogiHomeが棋譜・盤面に反映し、対局が続く可能性がある点を中心に、候補局面、時計、操作、ログ/画面の証拠、有限の終了・復帰条件、本人の判断方法、未検証事項だけを条件案へ具体化し、独立レビューと文書検証後に提示してください。対局中断・時計切れ・解析中断を同じ停止経路と決めつけず、画面操作が通常 `stop` を送ると資料から確認できない場合は未確定と明記してください。前回の局面・時計・上限値・起動数・再試行条件は今回の実施条件として自動採用しないでください。学習確認は一問ずつ進めてください。今回は条件作成・レビュー・提示までです。コード・テスト・設定変更、エンジン起動、ShogiHome等の実機操作、ログ採取、計測・対局は行わず、条件提示後に本人の明示承認を待ってください。実施開始とmain取り込みも別承認です。`
