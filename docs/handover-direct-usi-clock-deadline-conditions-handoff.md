# 引き継ぎ：直接USIで時計期限停止を確認する条件だけ

## 最終目標

選定済みの次テーマ「直接USIで時計期限停止を確認する条件だけ」を、新しいセッションで条件作成から始める。時計引数付きUSI `go` に対して、エンジン内部の時間予算・期限判定が探索を止める経路を、ホストが送る明示的な通常 `stop` と区別して観測する実施条件を設計する。

今回行う範囲は、現行仕様・実装・既存検査の照合、条件案作成、独立レビュー、文書検証、本人への提示まで。実施の承認、エンジン起動・時計計測・ログ採取、コードやテストの変更・実行、ShogiHome操作は含まない。条件案の承認後に実施開始を別途承認してもらい、mainへの取り込みも別承認とする。

## 完了事項と判断の背景

### 直近のShogiHome時計期限確認

- 本人は「ShogiHomeの時計期限による停止の条件だけ」を選び、条件案、実施開始、具体的設定変更・ログ採取・棋譜保全・再起動を承認した。
- ShogiHome 1.28.2の一局・一探索で、時計引数付き `go btime 600000 wtime 0 byoyomi 5000` の送信後2.316秒に合法な `bestmove 3c2c` が返り、盤面と棋譜に反映された。ログ上のShogiHome発 `stop` は0件であり、時計期限停止は観測できなかった。
- 受信後の画面照合期限と起動数条件にも計画との差があった。ログON期間は設定照会2件と対局1件で、ログOFF中を含む全起動数は確定していない。失敗・未達を成功扱いにしない。
- 試行設定を対局開始なしで保存する画面経路がないことを対象版資料で確認した後、別途本人承認を得た一度の復帰対局を初期局面で開始し、人間の着手前に即時中断した。保全した元棋譜を開き直し、時計・最大手数・Difficulty・ログ設定とUSI/CSAセッション0を画面で確認した。復帰対局の通信ログはOFFのため取得していない。
- 本人は今回の結果を受け入れた。理解確認で本人は「stop を送る前に bestmove が返ってくる場合があるため」と回答し、合法手の返却だけではstopの観測にならないと確認した。
- 学習・計画・索引等はmainの `ae5d558` と `9b51d43` に記録済み。結果・未達・復帰・本人回答は `docs/learning/shogihome-clock-deadline-conditions.md` にある。

### 以前に確認した直接USIの通常 `stop`

- `docs/plans/2026-10-13-normal-stop-recheck-conditions.md` の一回観測では、実エントリポイント `python3 -m kaname_shogi.usi_engine` を起動し、時計引数なしの `go` を実行してから明示的な `stop` を送った。OS CPU時間の連続増加中に送信し、合法 `bestmove 3b3a` 一件、重複なし、終了コード0を確認した。
- 本人はその直接プロセスの通常 `stop` 観測として受け入れた。この証拠は時計引数による内部期限停止を確認したことにはならない。
- 通常 `stop`、USI時計期限による内部停止、ShogiHomeの「対局中断」、時計切れ、解析中断は別の操作・経路として扱う。ログに明示 `stop` がないことを、実装上の内部期限停止の証拠に読み替えない。

### この順序を選ぶ理由

時計付き探索の期限停止がまだ実測されていない一方、明示stopの直接USI応答とShogiHome接続の通常応答は別々に確認済みである。時計期限の直接USI条件を設計すれば、GUI時計や画面操作が送るコマンドとの混同を避け、`go` の時計引数から内部予算・停止までの境界に対象を絞れる。条件作成の段階では、止まる時計値や応答時間を先に仮定せず、現行契約と検査範囲から候補を組み立てる。

## 現在の物理状態

- リポジトリ: `/Users/oki2a24/kaname-shogi`
- 新セッション用作業ブランチ: `codex/direct-usi-clock-deadline-conditions-handoff`
- 分岐元mainのHEAD: `9b51d43`（`docs: finalize ShogiHome clock stop record`）。分岐直前にmainは `origin/main` より29コミット先行し、cleanだった（2026-10-13確認）。
- 分岐前の環境確認: `.venv/bin/ruff --version` は `ruff 0.16.10`、`git config --local --get core.hooksPath` は `.githooks`。
- mainには `ae5d558` と `9b51d43` があり、前テーマの受け入れ結果・理解確認・復帰・文書検証が記録済み。この引き継ぎブランチはmainへ未統合であり、統合承認も得ていない。
- コード・テスト・設定の変更はなく、ShogiHomeの現物操作もしていない。引き継ぎ文書4ファイルは専用ブランチにコミット済み（初回コミット `f85d727`）。通常フックはRuff整形確認38ファイルと基本検査に成功。文書リンク検証は4ファイル・490件で欠落0件、`git diff --check` 成功。独立レビュー初回はCritical 0・Important 0・Minor 2で指摘を反映し、最終レビューはCritical 0・Important 0・Minor 0。mainへの取り込みはしていない。新セッションではここに書いた状態を盲信せず、指定コマンドで現物を確認する。
- 作成・更新対象: `docs/handover-direct-usi-clock-deadline-conditions-handoff.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/README.md`。

## 次セッションで読む資料と照合範囲

最初に本引き継ぎ、`AGENTS.md`、`README.md`、`docs/documentation-guide.md`、`docs/resume.md`、`docs/next-topics.md` を読む。次に次の契約・実装・検査を現行HEADと照合する。

- 契約メモ: `docs/knowledge/time-budget.md`、`docs/knowledge/search-stop.md`、`docs/knowledge/usi-engine-response.md`。
- 実装: `kaname_shogi/time_management.py`、`kaname_shogi/search_control.py`、`kaname_shogi/usi_engine.py`、必要であれば実際の探索処理。
- 既存検査: `tests/test_time_management.py`、`tests/test_usi_clock.py`、`tests/test_search_control.py`、`tests/test_usi_concurrency.py`、`tests/test_usi_process_concurrency.py`、`tests/test_search_movegen.py`、`tests/test_usi_engine_launcher.py`。
- 既存検査の点検では、どの契約・誤りを検出するか、代表ケース、個別テストと全体の範囲、今回の条件案でも未検証の点を記す。テスト成功件数だけで十分性を決めない。
- 開発・テスト設計の点検に必要な場合は `~/.codex/observations/test-driven-development.md` と `docs/knowledge/test-coverage-review.md` を読む。次テーマは条件作成だけなので、テストを実行・追加・変更しない。
- 過去の根拠: `docs/learning/shogihome-clock-deadline-conditions.md`、`docs/plans/2026-10-13-shogihome-clock-deadline-conditions.md`、`docs/learning/normal-stop-recheck-conditions.md`、`docs/plans/2026-10-13-normal-stop-recheck-conditions.md`。

## 条件案で決めること

時計予算仕様と既存検査の検出範囲を照合してから、候補局面・方針・時計引数、明示 `stop` を送らないことを確認する証拠、送信・受信・プロセス状態の記録方法、合法な `bestmove` と終了の照合、有限の待ち時間・中断・復帰、本人の判断方法、未検証事項を具体化する。

前回のShogiHome局面、時計値、上限、起動数、再試行条件を自動採用しない。時計値や時間上限は現行仕様・局面候補・観測目的から新しく提案し、どの意味の期限を試すのか区別する。外部 `stop` が混ざる条件を内部期限停止の観測としない。

## まだ行っていないこと

- 直接USIの時計期限停止を確認する条件案は未作成。独立レビューも未実施。
- エンジン起動、`go`、時計計測、ログ・画面採取、対局、ShogiHome操作は新テーマでは一切始めていない。
- コード、テスト、JSON設定、ShogiHome設定の変更もしていない。テストは実行していない。
- 条件案の提示後の本人承認、実施開始、main取り込みはそれぞれ未取得。

## 次の具体的な行動

1. 本人が下記プロンプトを新セッションへ入力した後、指定順でGit状態、Ruff、hooksPathを確認する。
2. 引き継ぎと現行案内を読み、契約・実装・テストを現在のファイルと照合する。
3. 時計期限停止の条件案だけを作る。計測・実行・テストはしない。
4. 独立レビュー、Critical/Important/Minorの対応、相対リンク・差分検証を行い、条件案を本人へ提示する。
5. 条件案の明示承認を待つ。実施開始とmain取り込みは別々に承認を待つ。

## 再開用プロンプト

このプロンプトを次のCodexセッションに本人が入力する。入力前に新テーマの調査・学習・実施を始めない。

> `/Users/oki2a24/kaname-shogi` のブランチ `codex/direct-usi-clock-deadline-conditions-handoff` で、選定済みテーマ「直接USIで時計期限停止を確認する条件だけ」を開始してください。最初に `git status --short --branch`、`git log -3 --oneline`、`.venv/bin/ruff --version`、`git config --local --get core.hooksPath` をこの順で実行してください。作業ツリーの現物を正とし、`docs/handover-direct-usi-clock-deadline-conditions-handoff.md`、`AGENTS.md`、`README.md`、`docs/documentation-guide.md`、`docs/resume.md`、`docs/next-topics.md` を読み、引き継ぎに列挙した現行仕様・実装・テスト範囲を照合してください。時計引数付きUSI `go` によるエンジン内部期限停止を、ホストが送る通常 `stop` と区別して観測する実施条件案だけを作成してください。既存検査が確認する契約と誤り、代表局面・時計条件、送受信・プロセスの証拠、合法応答と終了、有限の停止・復帰条件、本人の判断方法、未検証事項を明確にしてください。前回のShogiHome局面・時計値・上限・起動数・再試行条件は自動採用せず、今回はコード・テスト・設定の変更やテスト実行、エンジン起動、時計計測、ログ採取、実機操作を行わないでください。独立レビューと文書検証後に条件案を提示し、本人の明示承認を待ってください。条件案承認後の実施開始とmain取り込みも別承認です。学習確認は一問ずつ進めてください。`
