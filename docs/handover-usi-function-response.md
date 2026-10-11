# 次テーマへの引き継ぎ：関数境界での実応答だけ

## 最終目標と選定理由

2026-10-11、本人は「関数境界での実応答だけ。新セッションの準備して」と選定した。対象は[承認済み計画タスク4](plans/2026-10-10-two-ply-implementation-plan.md#タスク4usi設定と実応答)の `test_two_ply_bestmove_is_legal_and_preserves_position` 1項目のみ。設定spyで方針が届く確認から、実際の選択による応答へ一段進めるため推薦した。

今回は文書準備のみ。本人が再開用プロンプトを新セッションへ入力するまで、次テーマの学習・テスト変更・誤り注入・実装を開始しない。既存承認済み計画の部分再開であり再承認不要。本書は新規実装計画ではない。計画訂正が必要なら具体案を提示して明示承認を待つ。main取り込みは別途本人承認を得る。実プロセス応答・性能・棋力・ShogiHomeへ自動継続しない。

## 完了事項と意思決定の背景

内部二手比較と詰み・境界・枝独立性、CLI三択、USI三択通知・受付、局中固定・次局継承はmain統合・検証・理解確認済み。直前は新値後の未知値保持1項目だけを実施した。

- `test_invalid_value_preserves_two_ply_setting` を追加。TwoPlyMaterial→Strong→最初goはTWO_PLY_MATERIAL、無設定とRandomはRANDOM、MaterialはMATERIAL。各ケースを新しいエンジン実行にし、呼び出し1回も確認した。期待値は製品辞書から生成しない。
- 初回Green。既知値だけ設定更新する既存処理が成立しており、製品変更・Refactor不要。未実装Red→製品修正とは扱わない。
- 隔離8変異（未知値でRandomへ戻す・Materialへ取り違え・新値後だけ消去・未知値を方針データとして受理・選択へRANDOMを渡す・呼び出し欠落・無設定既定値破壊・旧Material受付破壊）は全てアサーションFAIL、ERRORなし、各復元1件成功・ソース一致。
- USI30件・全体361件・Ruff整形28ファイル・lint・差分成功。独立コード・文書レビュー各Critical 0・Important 0・Minor 0。レビュアーも単独・USI30・8変異と各復元を再実行。実装保存 `d407f20`。
- 本人「ok」で元ディレクトリmainを `12a6d74` → `d407f20` へfast-forward（準備 `b1d8777` 含む）。取り込み先全体361件・Ruff・差分成功。統合記録 `8baa34c`。統合文書のMinor 1件（次候補の古い承認待ち表記）は修正・再レビューで残件0。
- 最後の問題はTwoPlyMaterial→Strong。本人最初「random」は誤答として残し、直前有効設定を保持すると補足。Material→Strongの再確認へ本人「`Material`」で正解。回答・完了・候補は `5afc2a4`。具体例の再確認であり探索全般の習得ではない。

詳細は[前テーマの実施記録](learning/usi-invalid-value.md)。明示Randomへ有効値から戻す切替は、既定値と同じ結果の対照例では検出せず未検証として残した。今回へ自動追加しない。初回保存操作のindex.lock作成はサンドボックスで拒否され、許可された権限付き再実行で通常フックを通した。検査回避なし。未解消失敗・レビュー指摘なし。タスク4全体は未完了。

## 対象契約・表現・確認方法

計画の指定1項目をそのまま再開する。教材のSFENを既存書出し操作で作り、新値設定とposition、go二回を送る。実選択を使い、両bestmoveをparseして元局面のlegal_movesに含まれること、同じ局面が渡ることを確認する。手なし局面では新方式のbestmove resignも確認する。全合法手から４五飛だけが一意に選ばれるとは扱わない。

教材は先手番、先手９九玉・５五飛、後手１一玉・５三金・５四歩、持ち駒なし、他は空マス。[承認済み設計](plans/2026-10-10-evaluation-next-stage-design.md)に理由がある。二候補限定の４五飛選択を、今回の全合法手での固定期待値へ流用しない。

`Position` は盤面・手番・持ち駒を表すデータ、`SfenPosition` は局面と手数のデータ。`format_sfen` はSFENへ書き出す操作、`run_usi_engine` はコマンド処理の操作、`choose_move` は手を選ぶ操作、`parse_usi_move` は応答の指し手をデータへ読む操作である。設定だけのspyに置き換えて実選択を省略しない。観測のため包む場合も実処理を呼ぶ。

振る舞いごとに契約・独立期待値・検出対象・代表ケースを確認してTDDを行う。初回Greenなら既存成立と記録し、不要な製品変更をせず、隔離誤り注入で意図したアサーションFAILと各復元成功を確認する。読み込みERRORをRedに数えない。単独が検出する誤りと既存テストの補完を区別し、実応答の合法性確認だけを方針選択全般の証明と呼ばない。教材・観測方法・手なし表現の具体化で計画訂正が必要と判明した場合は明示承認を待つ。

実プロセスpipe・ランチャーの新方式bestmove・時間計測・性能合否・棋力・ShogiHomeは対象外。全体回帰の既存プロセステスト成功を、新方式のプロセス実応答完了と扱わない。

## 現在の物理的状態

- 場所 `/Users/oki2a24/kaname-shogi`。準備開始main `5afc2a4`、差分なし、origin/mainより12コミット先を確認。pushなし。
- 準備ブランチ `codex/usi-function-response-handoff` を作成。新規worktreeなし。今回準備のmain取り込みなし。
- Ruff 0.16.10と固定版、ローカルフック `.githooks` の一致を確認。
- `kaname_shogi/usi_engine.py`：run_usi_engine 40行、設定受付117行、go処理125行、実選択138行、bestmove出力142行付近。
- `tests/test_usi_engine.py`：既存spy121行、今回までの未知値263行、合法bestmove確認407行、局面参照確認434行、既存resign確認471行付近。指定新テスト未追加。
- `kaname_shogi/sfen.py`：SfenPosition 53行、format_sfen 110行。`tests/test_movegen.py`：教材ヘルパー4338行付近。行番号は次回現物で再確認する。
- 必読：AGENTS.md、README、docs/documentation-guide.md、docs/resume.md、本書、承認済み計画・設計、docs/learning/usi-invalid-value.md、docs/knowledge/usi-engine-response.md、docs/knowledge/test-coverage-review.md、`/Users/oki2a24/.codex/observations/test-driven-development.md`。
- 補助台帳 `.superpowers/sdd/2026-10-10-two-ply-implementation-plan/progress.md` は部分実施履歴。恒久記録と現物を優先する。task-startの日本語見出し非対応は既知で、本文を直接照合しツール都合の計画訂正をしない。
- 直近の全体成功は取り込み先の361件（`/tmp/usi-invalid-main.log`）。今回準備では全体再実行なし。一時ファイルは消える可能性がある。次回は現在の基準を実行する。

## 次の具体的な行動

1. 指定ディレクトリで `git status --short --branch`、`git log -4 --oneline`、`.venv/bin/ruff --version`、`git config --local --get core.hooksPath` を実行し現物と照合。不一致はREADME手順で解消する。
2. 必読とコードを読み、指定1項目だけに固定。教材、実選択、両bestmoveの合法性、局面保存、手なしresignの契約・確認方法・既存補完・未検証を照合。計画訂正が必要なら明示承認を待つ。
3. using-superpowers・roadmap-management・実行スキル・TDD・完了前検証・独立レビューを適用し、main以外で基準全体テストを実行。前回361件を今回へ流用しない。
4. 指定テストを振る舞いごとに追加し、失敗理由確認→最小実装→成功→Refactor要否を確認。初回Greenなら検出力と復元を確認する。
5. USI関連・全体回帰・Ruff・差分・独立レビューを実施。Critical/Importantは解消・再検証・再レビュー後、今回の範囲だけ記録・入口更新・リンク検査・通常コミット。タスク4全体完了としない。
6. main取り込みは別途本人承認を待つ。取り込み先検証後、最後の理解確認を一問ずつ行い本人回答を待って記録。本人が次テーマを選ぶまで後続へ進まない。

## 再開用プロンプト

> `/Users/oki2a24/kaname-shogi` で「関数境界での実応答だけ」を再開してください。Git状態、AGENTS.md、docs/resume.md、docs/handover-usi-function-response.mdを確認し、「次の具体的な行動」に従ってください。対象は承認済み計画タスク4の test_two_ply_bestmove_is_legal_and_preserves_position 1項目のみです。実選択を使い、go二回の合法bestmove・局面保存・新方式の手なしresignを確認してください。振る舞いごとにTDDを行い、初回Greenなら検出力と復元を確認してください。計画訂正は明示承認を待ち、実プロセス応答・性能測定へ自動継続せず、main取り込みは別途本人承認を得てください。

## 今回準備の検証・保存状態

文書準備のみ。新テーマの学習・テスト変更・誤り注入・製品変更・全体テスト再実行なし。文書レビュー・リンク・Ruff・差分を確認し、結果追記後に通常コミットへ保存する。

準備5文書の相対リンク・見出し415件問題0、Ruff整形確認28ファイル・lint・差分成功。独立文書レビューはCritical 0・Important 0・Minor 0、修正要求なし。レビュアーもリンク415件・差分成功を再確認し、全体テスト・Ruffは再実行していない。結果追記後に最終検査し、通常コミットへ保存する。準備のmain統合・pushなし。
