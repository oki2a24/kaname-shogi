# 空候補で抽選しないことを確認する

## 目的・承認・開始時の状態

2026-10-11、本人の開始指示により、[承認済み計画](../plans/2026-10-10-two-ply-implementation-plan.md)タスク2の `test_empty_candidates_do_not_draw` 1項目だけを実施した。[開始時の引き継ぎ](../handover-two-ply-empty-candidates.md)と現物を照合し、既存承認の範囲内で進めた。計画変更なし。以下は実施記録であり新しい計画ではない。

場所は `/Users/oki2a24/kaname-shogi`。開始HEAD `228045c`、準備ブランチ `codex/two-ply-empty-candidates-handoff`、変更なし。同じ場所に `codex/two-ply-empty-candidates` を作成した。通常のGit書込みはサンドボックスの権限制限で失敗し、許可された実行で解消した。新規worktreeなし。mainは `d7b62ce` で、準備コミットも未取り込み。

Ruff 0.16.10は固定版と一致し、ローカルフックは `.githooks`。現行基準の全体352件成功を新たに確認した。using-superpowers、roadmap-management、executing-plans、TDD、完了前検証、独立レビューを適用した。補助台帳はタスク2全体を完了扱いにせず保持する。

## 要点・契約・代表ケース

`MoveSelectionPolicy` は方針データ、`TWO_PLY_MATERIAL` は二手先読みの方針値。`Position` は局面データ、`Board` は盤面データ、`Side.SENTE` は先手を表す値。`choose_move` は一手を選ぶ操作、`choice` は抽選する操作である。

空盤の先手局面と、候補を含まないタプルデータ `moves=()` を公開入口へ渡す。独立した期待値は仕様で決まる `None` と抽選呼出し0回であり、製品処理から算出しない。`None` は選択できる一手なしで、選択操作自体が投了・詰み・勝敗を決める意味ではない。局面から合法手がなくなる規則や、途中の応手なしの採点とは区別する。

実際の `choose_move` を実行し、渡す `random.Random` の `choice` だけを実処理ラップして呼出しを観測する。採点・選択処理の置換はない。[テスト点検手順](../knowledge/test-coverage-review.md)と個人知見 `~/.codex/observations/test-driven-development.md` を適用した。

- 単独の検出対象：空候補でNone以外を返す誤り、不要な抽選。戻り値は `assertIsNone(selected)`、非抽選は `choice.assert_not_called()` で確認する。
- 既存テストによる補完：公開入口のRANDOM／MATERIAL空候補と、弱い選択器単体の空候補は既存テストが担う。今回、新方針の同じ境界を補完した。
- 未検証：公開入口と非公開二手選択操作の二重ガードを個別に検証していない。片方を削除しても他方で契約が保たれるなら、検出しないこと自体は不具合の見逃しとは限らない。後手・別局面全般、`choice`以外の乱数操作、詰み・投了・勝敗、途中の応手なし、枝独立性・探索深さ・例外などは今回の保証外。後続テーマへ進まない。

## 初回実行・隔離誤り注入・Refactor

テストは1メソッドだけ追加し、初回有効実行は既存実装でGreen。未実装Redとは呼ばない。公開入口の空候補ガードが既に契約を満たすため、製品変更は不要。import変更なし。短い1メソッドで契約を明示でき、Refactorも不要と判断した。

製品とテストを一時ディレクトリへコピーし、公開入口の空候補分岐に次の誤りを一つずつ注入した。作業ツリーの製品は変更していない。

| 変異 | 対象アサーションのFAIL | 各復元後 |
| --- | --- | --- |
| `return None` を `return moves` へ変更 | `assertIsNone`：空タプルはNoneではない | 成功 |
| `rng.choice((None,))` を行ってからNoneを返す | `assert_not_called`：choiceが1回呼ばれる | 成功 |

2変異とも対象アサーションFAILであり、読み込みエラー・例外を検出成功と数えていない。不要抽選の変異は、空列抽選のIndexErrorで停止せず非抽選アサーションまで到達させるため、Noneを含むタプルを渡した。実際に空タプルを抽選する誤りは、実処理ラップによりIndexErrorでテストが失敗するが、その例外を今回のアサーションFAIL実績には含めていない。

実験スクリプト `/tmp/check_empty_mutations.py`、ログ `/tmp/empty-*.log` は一時成果物。恒久的な結果は本書へ保存する。すべての誤実装を検出する証明とは扱わない。

## 検証・独立レビュー

- 基準：`python3 -m unittest discover -s tests -v` → 352件成功。
- 単独：`python3 -m unittest discover -s tests -p test_movegen.py -k test_empty_candidates_do_not_draw -v` → 1件成功。
- 対象：`python3 -m unittest discover -s tests -p test_movegen.py -v` → 180件成功。
- 全体：`python3 -m unittest discover -s tests -v` → 353件成功。
- `.venv/bin/ruff format .` → 28ファイル変更なし。`.venv/bin/ruff format --check .`、`.venv/bin/ruff check .`、`git diff --check` 成功。
- `requesting-code-review` に従い履歴を引き継がないレビュアーへ契約・代表例・検出対象・補完・未検証を渡した。独立コードレビューはCritical 0・Important 0・Minor 0、対応不要。レビュアーも隔離2変異と各復元、単独1件・対象180件・Ruff・差分検査を再実行した。全体353件は実装者の実測。

変更4文書の相対リンク・見出し375件問題0。独立文書レビューはCritical 0・Important 0・Minor 0、対応不要。レビュアーもリンク375件・Ruff整形確認28ファイル・lint・差分検査を再実行した。追記後も同じ検査を確認し、内容確認済みの5ファイルを通常フック付きでコミットする。`finishing-a-development-branch` に従い通常チェックアウトとmain未取り込みを確認した。main統合は別途本人承認を待つ。利用可能な方式・製品仕様・長期方針は変わらないため、ルートREADME・知識メモ・方向性・承認済み計画は変更しない。

## 確認問題・回答・振り返り・次回への問い

実装コミット時点ではmain統合の承認・取り込み先検証・最後の理解確認は未実施だった。確認問題は取り込み先検証後に一問だけ出し、本人の回答を待つ方針とした。本人回答は未取得であり、正解やテーマ全体の完了とは記録しない。後の統合は次節へ記録する。

振り返り：戻り値と副作用の有無を別のアサーションで観測し、既存実装を変更せずに代表的な2つの誤りを検出できた。公開契約と内部二重ガードの検証を区別した。

次回への問い：空候補のNone・非抽選が、投了・詰み・勝敗の判定を意味しない理由を本人の言葉で説明できるか。残りのタスク2、CLI／USI三択、性能・棋力測定、Python更新・構成再検討には自動継続しない。

## main統合・取り込み先検証・理解確認待ち

2026-10-11、mainへ取り込んでよいかという確認に、本人は「ok」と回答し承認した。元の作業ディレクトリ `/Users/oki2a24/kaname-shogi` のmainを `d7b62ce` から `3a98991` へ `git merge --ff-only codex/two-ply-empty-candidates` で統合した。準備 `228045c` と指定テスト・記録 `3a98991` を取り込み済み。pushなし。

取り込み先mainで `python3 -m unittest discover -s tests -v` は353件成功。Ruff整形確認28ファイル・lint、取り込み6文書の相対リンク・見出し385件問題0、差分検査も成功。統合記録の追記は文書のみで、全体テストは再実行せず、直前の取り込み先353件を検証実績とする。

最後の理解確認問題：二手先読みの選択操作へ空候補 `moves=()` を渡すと、戻り値と抽選呼出しはどうなり、その結果だけで「投了した」と判断できるか。

本人回答は未取得。回答とアシスタント補足は、回答確認後に分けて追記する。テーマ全体の理解確認完了とは扱わない。次候補の見直しは回答確認後とし、後続テーマを開始しない。

統合記録の独立文書レビューはCritical 0・Important 0・Minor 0、対応不要。レビュアーはmain履歴と取り込み先ログを照合し、追記後の相対リンク・見出し386件問題0、Ruff整形確認28ファイル・lint・差分検査を再確認した。内容確認後、統合記録4文書をmainへ通常コミットする。
