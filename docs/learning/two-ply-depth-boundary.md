# 二手で駒得探索を止める確認

## 目的・合意・開始状態

2026-10-11、本人の再開指示により、[承認済み計画](../plans/2026-10-10-two-ply-implementation-plan.md)タスク2の `test_stops_material_scoring_at_two_plies` 1項目のみ実施した。[開始時引き継ぎ](../handover-two-ply-depth-boundary.md)の次の具体的な行動に従った。計画訂正なし。後続開始とmain統合の承認は含まない。

場所は `/Users/oki2a24/kaname-shogi`、ブランチは `codex/two-ply-depth-boundary-handoff`、開始HEAD `14cd76a`。作業ツリーは清潔で、前テーマ回答・準備の独立文書レビューと通常コミットは保存済みだった。Ruff 0.16.10と固定版、ローカルフック `.githooks` の一致を確認した。新規worktree・pushなし。

using-superpowers、roadmap-management、executing-plans、test-driven-development、verification-before-completion、requesting-code-reviewを適用。[テスト点検](../knowledge/test-coverage-review.md)と個人知見を確認した。対象契約・表現・確認方法は承認済み計画どおりで、新規計画は作成していない。

## 要点・参照の作り方・変更

教材は先手９九玉・５五飛、後手１一玉・５三金・５四歩、持ち駒なし。候補は５四飛と４五飛。Positionは局面データ、BoardMove・DropMoveは一手データ、Squareはマスの値。apply_move・apply_dropは一手を適用する操作、legal_movesは合法手を列挙する操作、material_balanceは駒得差を求める操作である。

テスト側で候補を複製へ一度直接適用し、全合法応手をさらに各複製へ一度直接適用する。探索用の `_position_after_move`・`_two_ply_score` や採点結果から期待局面を作らない。既存の `_position_snapshot` で盤面81マス・双方の基本持ち駒7種の枚数・手番を保存する。各候補後と各応手後が詰みでないこと、応手が非空であることを確認する。

公開choose_moveを実行中だけmaterial_balanceと公開legal_movesを実処理ラップし、呼出時点の全状態を保存する。assertCountEqualで採点局面を全二手後参照と、公開応手生成局面を全一手後参照と照合する。順序に依存せず出現回数も確認する。詰み判定内部は `_has_legal_move` を使うため公開手生成の観測に含まない。手番一致だけを深さの証拠にしない。

指定1メソッド追加後の初回有効実行はGreen（単独1件）。未実装Redではない。既存の固定二段階処理が契約を満たすため製品変更は不要。Refactorも既存スナップショットと教材を再利用でき、今回必要なしと判断した。

## 隔離誤り注入と検出範囲

`/tmp/check_depth_mutations.py` で製品とテストの隔離コピーを作り、隔離基準1件成功後、次の変異を一つずつ注入した。

| 変異 | 検出結果 | 復元 |
| --- | --- | --- |
| 応手後でなく一手後を採点 | 採点局面照合FAIL | 単独1件成功 |
| 葉からさらに一手適用し三手後を採点 | 採点局面照合FAIL | 単独1件成功 |
| 葉からさらに二手適用し四手後を採点 | 採点局面照合FAIL | 単独1件成功 |
| 二手後から不要な公開合法手生成 | 生成局面照合FAIL | 単独1件成功 |
| 各二手後を余分に一回採点 | 採点回数照合FAIL | 単独1件成功 |
| 最初の応手のみ読む | 採点局面・回数照合FAIL | 単独1件成功 |

各回のFAILED (failures=1)とassertCountEqualのFAIL、復元OKを確認し、ERRORを検出成功に数えていない。キャッシュを除去して各復元を再実行し、元の製品ファイル無変更も照合した。ログ `/tmp/depth-*.log` は一時物であり、恒久結論は本書へ保存する。

今回単独で確認するのは教材二候補の採点と公開応手生成の境界である。四手後は開始手番と一致しても全状態比較で検出する。既存通常比較・詰み・手なし・例外等のテストは選択・採点・共通適用処理を補完する。後手反転や他教材、全手種・複数枝の独立性、私的操作だけで余分な手を試して結果を破棄する実装、CLI／USI、時間・棋力は未検証。有限例を全入力への証明とは扱わない。

## 検証・独立レビュー

開始時に全体テストを実行しOKを確認したが、そのログを隔離単独の同名ログで上書きしてしまった。開始時件数の証拠として流用せず、追加後の以下の保存ログを検証根拠とする。

- 単独 `python3 -m unittest discover -s tests -p test_movegen.py -k test_stops_material_scoring_at_two_plies -v`：1件成功。
- 対象 `python3 -m unittest discover -s tests -p test_movegen.py -v`：184件成功（`/tmp/depth-target.log`）。
- 全体 `python3 -m unittest discover -s tests -v`：357件成功（`/tmp/depth-full.log`）。
- `.venv/bin/ruff format .`：テスト1ファイル整形、27ファイル変更なし。`.venv/bin/ruff check .`・`git diff --check` 成功。import変更なし。

独立コードレビューはCritical 0・Important 0・Minor 0、修正指摘なし。履歴なしのレビュアーが単独1件を再実行し、6変異と各復元ログ・スクリプト、契約・参照の独立性・補完・未検証を照合した。レビュアーが全体回帰や変異自体を再実行したとは扱わない。独立文書レビューもCritical 0・Important 0・Minor 0、修正指摘なし。レビュアーは4文書と差分・実行ログの整合、未検証・未承認・未回答の区別を確認し、相対リンク・見出し393件問題0と差分検査を再実測した。結果反映後の最終差分・リンク・Ruffは実行者が確認する。文書だけの追記後に全体テストは再実行せず、上記357件を実績とする。判断辞退は上記の未検証範囲と、後続全体の完成度・統合可否であり、保証済みにはしない。

## 確認問題・振り返り・次回への問い

main統合は別途本人承認待ちで未実施。取り込み先検証と最後の理解確認は未実施で、本人回答なし。確認問題はまだ出題しない。

振り返り：製品を変更せず、全状態と出現回数で固定二手境界の代表的な誤りを検出できた。手番だけでは四手後も同じになるため、状態全体の参照が役立つ。

次回への問いとして「採点時の手番が開始側と同じという確認だけでは、なぜ二手で止まることを十分に確認できないか」を記録する。出題は本人承認によるmain統合・取り込み先検証後に一問だけ行う。枝独立性やCLI／USIへ自動継続しない。

finishing-a-development-branchを適用し、mainとの共通祖先 `d7775f3` を確認した。本人指定どおり作業ブランチを保持し、内容確認後にテストと4文書を通常フック付きコミットへ保存する。main統合・pushはしない。README・知識・方向性は製品仕様と利用面が変わらず変更不要。

## main統合・取り込み先検証

2026-10-11、main取り込みの承認依頼に本人は「ok」と回答した。元の作業ディレクトリ `/Users/oki2a24/kaname-shogi` で `git switch main`、`git merge --ff-only codex/two-ply-depth-boundary-handoff` を実行し、mainを `d7775f3` から `4a2fb20` へ進めた。準備 `14cd76a` と指定項目 `4a2fb20` はmain取り込み済み。push・新規worktree・ブランチ削除なし。

取り込み先で `python3 -m unittest discover -s tests -v` は357件成功（`/tmp/depth-main-full.log`）。Ruff 0.16.10・フック `.githooks` は一致、Ruff整形28ファイル・lint・差分検査成功。取り込み6文書の相対リンク・見出し403件問題0。この統合記録は文書のみで、全体テストを再実行せず上記のmain実績を根拠とする。

最後の理解確認問題：採点時の手番が開始側と同じという確認だけでは、なぜ二手で止まることを十分に確認できないでしょうか。

統合記録の保存後に一問だけ出題する。現時点では未出題・本人回答未取得。main統合・取り込み先検証まで完了し、最後の理解確認は未完了。後続へ自動継続しない。統合記録の独立文書レビューはCritical 0・Important 0・Minor 0、指摘なし。レビュアーはGit現物・取り込み先357件のログ・Ruffとフック・差分・6文書リンク403件問題0・未出題／未回答を確認した。結果反映後の最終差分と同じ検証を実行者が確認し、4文書を通常コミットする。
