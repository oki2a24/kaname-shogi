# 探索停止・途中結果の実装計画だけ：新セッションへの引き継ぎ

2026-10-12作成。準備時点の記録であり、次回はGitと現物を再確認する。

## 最終目標と選定範囲

本人：「探索停止・途中結果の実装計画だけ。新セッションの準備して」。計算済み時間予算を探索で使う境界に集中し、小さく処理の理由を理解するために推薦した候補1を選定した。次回は承認済み全体設計の期限判定、探索中断、途中結果、0予算時の応答を、具体的な実装単位・契約・検証へ落とす。入力並行処理との依存と後続接続を明示する。全体設計を無断変更せず、切り出し可能性も現物に照らして確認する。

今回は引き継ぎ準備のみ。新テーマの学習・調査・計画作成は未開始。人間が末尾のプロンプトを新セッションへ入力してから始める。次回も計画作成・独立レビュー・提示までとし、提示後に本人の明示承認を待つ。テーマ選定は具体案承認・実装開始承認ではない。main取り込みも別承認。

コード・テスト・設定変更、TDD、探索停止・入力並行処理の実装、実時間計測・対局・ShogiHome操作、最適化・棋力比較、Python更新を開始しない。章番号・学習回番号は付けない。

## 完了事項と意思決定の背景

- 時計設定読込・時間予算計算に続き、USI時計受付・設定接続を完了。本人の計画承認と実装開始指示、TDD、検出力点検、独立レビュー、main統合承認、取り込み先検証、最後の理解確認まで実施した。
- 時計解析/自分側予算準備bf3ca1b、USI接続9fd4f10、完了記録341c106をmainへ早送り統合。統合記録513dab0、回答と補足486d1d4、理解確認完了と候補3ddd7c5もmainにある。
- 時計引数検証、自分側時計選択、起動時設定一回読込と実行中保持、goごとの予算準備までを接続した。時間停止は未実装。予算0でも現在の探索を完了して応答する。時計なしはNone、明示0はSearchBudget(0,0)という区別を保持する。
- 最後の本人回答は最初「はい。その接続は今回自走したため。」。アシスタントは予算計算と探索停止の違いを補足し、正解扱いしなかった。再確認「計算した時間予算を使って探索を止める処理は実装済みか」への本人回答「未実装。」を確認して理解確認を完了した。
- 狭い入力接続を先に完成させた理由は、入力検証・設定寿命と探索制御を分けて理解するため。今回の選定も停止・途中結果の境界に集中するためで、後半全体の同時実装を承認したものではない。
- 約28.4秒の応答は一例の許容判断。他局面・秒読み後の安全性は未保証。40手上限が長考原因という仮説も未検証。
- 前テーマの補助task-startは日本語見出し解析に非対応だったため、手動概要/台帳で補完。仕様変更なし。補助一時ワークスペースは永久記録後に削除済み。最終レビュー担当の一度の利用上限停止は別担当の独立レビューで補完した。

## 現物と維持する契約

- `kaname_shogi/usi_engine.py`：_parse_go_clockは時計の検証操作、_prepare_search_budgetは現在手番から予算を準備する操作。run_usi_engineは同期入力・同期探索のまま。goで解析→局面確認→予算準備→方針固定→合法手→選択→応答。計算結果_search_budgetは停止には未使用。
- btime/wtime両必須、byoyomi省略0、非負整数ms、重複/不正/欠落拒否。binc/wincは0のみ受付、加算0だけなら時計なし。未知トークンを一つずつ無視して既知項目は検査。movetime/infinite/ponder/mate/depth/nodes/searchmovesは未対応エラー。
- 先手はbtime、後手はwtime。現在局面の手番を使い、手数から推測しない。時計はgoごとに独立。設定は明示注入でき、省略時は入力前一回読み、同一run中は新局でも固定。mainは設定不正・読込不能をstderr診断し終了1。設定ファイル・time_management.py・CLI・launcher自体は前テーマで変更していない。
- `kaname_shogi/time_management.py`：TimeManagementConfigは設定データ、SearchBudgetは期間の予算データ（target_ms/maximum_ms）。calculate_search_budgetは計算操作で、時刻取得・絶対期限・先後選択を行わない。JSON四欄/精度/式/暫定値は維持。詳細はknowledge/time-budget.mdを参照し、今回の計画で無断再設計しない。
- 承認済み全体設計はgo読取時刻を単調時計の原点とし、主担当への受渡し・回収待ち等も計時。主担当は現在スレッド、入力/探索は別スレッド。予備手・完了評価・抑制付き停止・故障通知・入力待機解除・回収について既存設計を読む。今回はその範囲から停止・途中結果の計画を切り出し、並行入力との境界を明示する。

## 現在の物理状態・検証の限界

- 場所 /Users/oki2a24/kaname-shogi。準備開始main、HEAD 3ddd7c5、差分なし。準備ブランチcodex/search-stop-plan-handoffへ同じ場所で切替。別worktreeなし。この準備文書はmain未統合。保存コミットは次回ログで確認する。
- 開始時origin/mainより2コミット先というローカル表示を実測。以前のahead59とは異なるため、過去の表示やpushなしを現在のリモート同期状態の証明に使わない。この引き継ぎ準備でpushは行わない。
- Ruff 0.16.10、core.hooksPath=.githooks。固定版一致。既存動作確認環境Python 3.9.6。
- main取り込み先で `.venv/bin/python -m unittest discover -s tests -v` は389件成功（6.018秒、新規15/既存374）。Ruff format --checkは31ファイル整形済み、check成功。今回の準備では文書のみのため全体テストを再実行しない。
- 前テーマは隔離コピーの代表変異9種を検出。重複、必須時計、未知語で打切り、先手固定、0をNone扱い、go再読込、main注入破棄、設定エラー成功終了、prepare省略。最終errorsなし。全入力の証明ではない。
- 最終実装・記録・統合・理解確認記録の独立レビューはCritical/Important/Minor 0。停止・期限内応答・競合・係数最適性・全OS/任意サイズの資源耐性は未保証。
- Git書込みはindex.lockの権限制約に対し承認範囲の権限昇格を使用。自動承認レビュー拒否・フック回避なし。
- Snapshot：前テーマ完了、次テーマ選定済み、引き継ぎ準備のみ。新テーマ計画・学習・実装は人間の新セッション入力待ち。

## 次の具体的アクションと読む資料

1. 指定場所でgit status --short --branch、git log -3 --oneline、.venv/bin/ruff --version、git config --local --get core.hooksPathを実行する。
2. AGENTS.md、README.md、docs/documentation-guide.md、docs/resume.md、本書、docs/next-topics.md、docs/02-project-direction.mdを読む。
3. docs/plans/2026-10-11-clock-input-time-management-design.md、docs/plans/2026-10-12-clock-input-verification-review.md、docs/plans/2026-10-12-usi-clock-settings-implementation-plan.md、docs/learning/usi-clock-settings-implementation-plan.md、docs/knowledge/time-budget.md、docs/knowledge/usi-engine-response.mdを読む。
4. ~/.codex/observations/test-driven-development.md、docs/knowledge/test-coverage-review.mdを読み、対象契約・検出したい誤り・独立期待値・既存補完・未検証を点検する。
5. kaname_shogi/usi_engine.py、kaname_shogi/time_management.py、kaname_shogi/movegen.py（MoveSelectionPolicyは方針データ、choose_moveは手選択操作）、tests/test_usi_clock.py、tests/test_usi_engine.py、tests/test_usi_engine_launcher.py、tests/test_time_management.pyを読み取り照合する。必要な一次資料は公式資料を優先し、適用スキルを確認する。
6. 学習は一問ずつ本人回答を待つ。停止・途中結果・0予算の範囲、API、所有者、期限原点、依存境界、例外、検証を計画化して独立レビュー後提示する。明示承認前に実装/TDDへ進まない。

## 再開用プロンプト

```text
/Users/oki2a24/kaname-shogi で、選定済みテーマ「探索停止・途中結果の実装計画だけ」を開始してください。
最初に git status --short --branch、git log -3 --oneline、.venv/bin/ruff --version、git config --local --get core.hooksPath を実行してください。
AGENTS.md、README.md、docs/documentation-guide.md、docs/resume.md、docs/handover-search-stop-implementation-plan.md を読み、指定資料と現在の物理状態を確認してください。
USI時計受付・設定保持・予算計算への接続はmain統合・取り込み先検証・理解確認まで完了しています。探索停止は未実装です。承認済み全体設計の期限判定、探索中断、途中結果、0予算時の応答だけを実装計画へ具体化し、入力並行処理との依存・後続接続を明記してください。既存の時計受付・設定・計算契約を維持してください。
~/.codex/observations/test-driven-development.md と docs/knowledge/test-coverage-review.md を参照し、契約・独立期待値・検出対象・既存補完・未検証を記載してください。学習は一問ずつ回答を待ってください。
今回は計画作成・レビュー・提示までです。コード・テスト・設定変更、TDD、探索停止・入力並行処理の実装、計測・対局・ShogiHome操作は始めず、計画提示後に本人の明示承認を待ってください。main取り込みも別承認です。
```

## 準備文書の確認

対象5文書の相対ファイルリンク444件欠落0（見出しアンカー対象外）、再開用プロンプト見出し存在、git diff --check成功。独立レビューのMinor 1件（旧選定待ち表現）を再開入力待ちへ修正し、再レビュー最終Critical 0・Important 0・Minor 0。文書のみのため全体テストは再実行せず、既存389件の結果と区別する。準備ブランチへ通常コミットし、人間の新セッション入力を待つ。
