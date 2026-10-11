# 次テーマへの引き継ぎ：USIへの三方式の通知・受付だけ

## 最終目標と選定理由

2026-10-11、本人は「USIへの三方式の通知・受付だけ。新セッションの準備して」と依頼した。対象は[承認済み計画](plans/2026-10-10-two-ply-implementation-plan.md#タスク4usi設定と実応答)タスク4の先頭2項目のみ。CLIで選んだ方針を対局へ渡す学習を終え、同じ方針データをUSIの設定から渡す小さい段階へ進むため推薦し、本人が選定した。

今回は準備のみ。本人が下の再開用プロンプトを新セッションへ入力するまで、USIの学習・テスト変更・TDD・製品変更を開始しない。既存計画の対象範囲は承認済みで再承認不要。新規実装計画ではなく再開手順であり、計画訂正が必要なら案を提示し本人の明示承認を待つ。

## 完了事項と意思決定の背景

内部の二手比較（タスク1・2）はmain統合・理解確認まで完了。CLI三択（タスク3）も前テーマでmainへ取り込み、取り込み先358件・Ruff整形28ファイル・lint・差分成功を確認した。実装 `9d52530`、統合記録 `4659f34`、最後の回答と完了 `de357be` はmain保存済み。独立コード・文書レビュー各Critical 0・Important 0・Minor 0、未解消指摘なし。

CLIは1→RANDOM、2→MATERIAL、3→TWO_PLY_MATERIAL、空入力→RANDOM。表示はランダム・一手駒得・二手先読み（駒得）。公開シグネチャと内部値を保ち、入口・run_gameの製品変更は不要だった。表示と3未対応、無効入力エラーの不足はアサーションRed→最小修正→Green。空入力・未指定・受け渡し等の初回Greenは既存成立として区別し、隔離6変異でFAIL（ERRORなし）・各復元1件成功を確認した。複数自動手にわたる固定は今回の単独テストで直接確認していない。性能・棋力・USI対応をCLIテストで証明したとは扱わない。

main取り込みは本人の「ok」を受け `6f70ec8` → `9d52530` へfast-forward（準備 `007b318` を含む）。初回Git操作はsandbox書込制限で失敗したため、承認済み操作を権限付きで再実行した。失敗後の作業ブランチテストをmain検証へ流用せず、取り込み後にmain上358件を再実行して成功を確認した。新規worktreeなし。

最後の確認は「CLIで3を選ぶと二手先読みと既定ランダムのどちらか」。本人回答「二手先読み」。正解と確認し、選んだ方針が対局へ渡り、ランダムは空入力・未指定時の既定値と補足した。具体例の理解確認であり探索全般の習得とは扱わない。[本人回答と完了記録](learning/cli-three-policies.md#最後の理解確認への回答とテーマ完了2026-10-11)に保存した。回答文書5件の独立レビュー各重大度0、リンク416件問題0・Ruff・差分成功。回答記録は文書のみで全体テスト再実行なし。

回答後README・方向性・候補を見直し、タスク4先頭2項目のみ（推薦）とタスク4全体を小さい順に提示した。本人は前者を選んだ。今回の選定で局中固定・未知値・実応答やタスク5まで開始してよいとは解釈しない。

## 対象契約・表現・確認方法

承認済みタスク4の先頭2項目をそのまま使う。

1. `usi` に対する通知を `option name Difficulty type combo default Random var Random var Material var TwoPlyMaterial` とする。通知欠落を対象アサーションのRedで確認して追加する。`usiok` より前の通知、既定Randomと旧二値を維持する。
2. `test_accepts_two_ply_material_case_insensitively`：`TwoPlyMaterial` と大小混在の値をそれぞれ設定し、position→goで既存spy境界へ `MoveSelectionPolicy.TWO_PLY_MATERIAL` が渡ることを確認する。辞書へ小文字キー `twoplymaterial` を追加する。初回Redは既定RANDOMへ留まる等の方針不一致で確認し、読み込みエラーをRed完了としない。

`MoveSelectionPolicy` は方針データ、`run_usi_engine` はコマンドを受け応答する操作、`choose_move` は方針に従い手を選ぶ操作。既存公開シグネチャ `run_usi_engine(input_fn, output_fn, rng=None) -> None` と選択入口を維持する。設定のUSI値は合意済みの `TwoPlyMaterial`。旧Materialの一手限定の意味は変えない。

期待値は合意した通知全文と方針値から直接記述し、製品辞書を使って生成しない。検出対象は新値通知欠落・旧値/既定値の破壊・usiok後の通知・新値受付漏れ・大小混在だけ受付漏れ・MATERIAL/RANDOMへの取り違え・選択境界への受け渡し欠落。各値の確認は新しいエンジン実行を使い、先の有効設定が残って混在値の未受付を隠さないようにする。

既存テストがRandom/Material、無設定、未知値、局中固定等を補完する。通知全文の既存期待値は `tests/test_usi_engine.py` 153・184・594行付近の3箇所にある。新通知による期待値の更新は先頭項目の整合に含まれるが、実プロセスで新方式を選んで応答を検証する後続項目まで実施済みとしない。基準と現物を次回再確認する。

未検証・対象外：新値の局中固定と次局継承、新値後の未知値保持、新方式の実選択・局面保存・手なしresign、新値の実プロセスbestmove、ShogiHome操作、時間・棋力測定。タスク4全体完了と記録しない。後続へ自動継続せず、main取り込みは別途本人承認を得る。

## 現在の物理的状態

- ディレクトリ `/Users/oki2a24/kaname-shogi`。準備開始main HEAD `de357be`、清潔。今回の実測でmainとorigin/mainは同じ状態（前回のahead8とは異なる。今回アシスタントがpushしたものではない）。次回も現物を優先する。
- 準備ブランチ `codex/usi-three-policies-handoff` を作成。今回main統合・push・新規worktreeなし。文書のみ準備。
- Ruff 0.16.10と固定版一致、ローカルフック `.githooks` を実測。次回不足・不一致はREADMEのセットアップ手順で解消する。
- `kaname_shogi/usi_engine.py`：値辞書12行、設定状態79行、usi通知105行、設定受付111行、最初のgoで局中方針を確定134行、選択呼出し137行付近。現行辞書・通知はRandom/Materialだけ。
- `tests/test_usi_engine.py`：spy操作121行、通知テスト136行、旧Material受付207行、大小混在225行、旧未知値244行、実pipe通知594行付近。
- 必読：AGENTS.md、README、docs/documentation-guide.md、docs/02-project-direction.md、docs/next-topics.md、承認済み計画タスク4先頭2項目、docs/plans/2026-10-10-evaluation-next-stage-design.md、docs/learning/cli-three-policies.md、docs/knowledge/usi-engine-response.md、docs/knowledge/31-weak-move-selection.md、docs/knowledge/test-coverage-review.md、`/Users/oki2a24/.codex/observations/test-driven-development.md`。
- 補助台帳 `.superpowers/sdd/2026-10-10-two-ply-implementation-plan/progress.md` は部分実施の履歴で、恒久記録・現在Gitを優先する。task-startは日本語見出し非対応だったため計画本文を直接読む。補助ツール都合で計画を訂正しない。
- CLIの一時ログ `/tmp/cli-main-merged-full.log`、変異 `/tmp/check_cli_mutations.py`、リンク検査 `/tmp/check_leaf_doc_links.py` は消える可能性あり。恒久結論は学習記録にある。

## 次の具体的な行動

1. 指定ディレクトリで `git status --short --branch`、`git log -4 --oneline`、`.venv/bin/ruff --version`、`git config --local --get core.hooksPath` を実行。準備コミットと文書レビュー完了を照合する。
2. 必読・コード現物を照合し、範囲をタスク4先頭2項目に固定。契約・独立期待値・検出対象・既存補完・未検証を確認。計画訂正が必要なら案を提示し明示承認を待つ。
3. using-superpowers、roadmap-management、実行スキル、TDD・完了前検証・独立レビューを適用。main以外で現在の基準テストを実行し、過去の358件を現在結果へ流用しない。
4. 通知、受付を一振る舞いずつテスト→意図したアサーションRed→最小実装→Green→Refactor要否の順で確認。既存成立の初回Greenは区別し、必要な隔離誤り注入で対象FAILと復元成功を確認。前の有効設定による偽Greenに注意する。
5. `python3 -m unittest discover -s tests -p 'test_usi_engine*.py' -v` と全体回帰、Ruff・差分・独立レビューを実施。Critical/Importantは解消・再検証・再レビュー。記録・知識・案内は今回実施した範囲だけ更新し、リンク確認後に通常コミット。新方式の実応答・ShogiHome確認を実施済みとしない。
6. main取り込みは別途本人承認。取り込み後の検証と一問の理解確認・回答記録を終えてから次候補を提示。タスク4残りや時間計測へ自動継続しない。

## 再開用プロンプト

> `/Users/oki2a24/kaname-shogi` で「USIへの三方式の通知・受付だけ」を再開してください。Git状態、AGENTS.md、docs/resume.md、docs/handover-usi-three-policies.mdを確認し、「次の具体的な行動」に従ってください。対象は承認済み計画タスク4の先頭2項目のみです。TwoPlyMaterialの通知と、大文字小文字を区別しない受付・方針受け渡しを振る舞いごとにTDDで確認してください。初回Greenなら検出力と復元を確認し、前の有効設定で未受付が隠れないようにしてください。計画訂正は明示承認を待ち、局中固定・未知値保持・実応答・性能測定へ自動継続せず、main取り込みは別途本人承認を得てください。

## 今回準備の検証・保存状態

文書のみの準備。USIテスト変更・TDD・誤り注入・製品変更・全体テスト再実行なし。変更5文書の相対リンク・見出し410件問題0、Ruff整形28ファイル・lint・差分検査成功。独立文書レビューはCritical 0・Important 0・Minor 1（CLI統合時点の「今回」が準備と紛らわしい）。「前テーマで」へ修正して時点を明確にした。結果追記後に最終検査し、通常コミットへ保存する。今回の準備のmain統合・pushなし。
