# 実プロセスの新方式応答だけ

## 目的・範囲・承認

2026-10-11、本人が[引き継ぎ](../handover-usi-process-response.md)の再開用プロンプトを入力し、[承認済み計画タスク4](../plans/2026-10-10-two-ply-implementation-plan.md#タスク4usi設定と実応答)の実プロセス通知・新方式の合法bestmove・stdout診断混入防止だけを開始した。既存承認の部分実行であり、計画訂正なし。タスク5の三方式時間計測・性能・棋力・ShogiHomeは実施しない。main統合は別途本人承認を待つ。

開始HEAD `875b60a`、場所 `/Users/oki2a24/kaname-shogi`、ブランチ `codex/usi-process-response-handoff`、差分なし。Ruff 0.16.10と固定版、ローカルフック `.githooks` は一致。新規worktree・pushなし。以下は実施後の記録であり新規計画ではない。

## 対象契約と確認方法

事前に引き継ぎ・計画本文と既存ケースを照合した。対象の通知全文は既に更新済み。既存 `test_entrypoint_flushes_protocol_and_bestmove` はRandomで動いていたので、同じ `position startpos moves 7g7f` の送信前に `setoption name Difficulty value TwoPlyMaterial` を追加する。教材や待ち時間を変更しない。

| 振る舞い | 独立期待値・代表ケース | 検出したい誤り |
| --- | --- | --- |
| 実通知 | usi→id二行→三択option全文→usiok、isready→readyok | 新値欠落・通知順序の混入・flush/改行欠落 |
| 新値設定後の応答 | 7g7f後の後手番。bestmoveの二語をparseし、送った元局面の既存legal_movesへ含まれる | 不合法手・応答欠落・余分stdout |
| エラー診断 | 新値設定後、不正SFENと未対応startpos単独の各既存ケース。非0終了・stdout空・stderr診断 | 診断をstdoutへ出す |

実Python子プロセスを `sys.executable -m kaname_shogi.usi_engine` で起動し、cwdはテストファイルの親から求めるリポジトリ。PipeLineReaderは既存の一行2秒の有限待ちを使い、正常ケースはbestmove受信後にquitを送るため、プロセス終了によるまとめ出力では成功しない。終了待ち2秒とterminate/kill、ストリームcloseも既存を維持。合法性は選択結果や固定の一手から期待値を作らない。

## TDD・検出力・Refactor

- 基準全体362件成功を今回実行した。通知は既存成立であり、未実装Redと呼ばない。
- 正常pipeケースへ新値設定とdocstringの範囲説明を追加し、単独初回Green（1件、unittest全体1.068秒）。これは選択時間の個別測定ではない。
- 次に既存診断2ケースへ新値設定を追加し、2件初回Green。製品変更なし。既存成立なので不要な修正を行わない。
- Refactor要否を点検し、入力追加だけで既存後始末・期待値を再利用できるため不要と判断。
- 一時隔離コピーに製品とtestsを複写。テスト読込と子プロセスcwdが同じ隔離rootを参照することを確認し、元ツリーを動かす偽検証を避けた。各変異の後でソースを復元、キャッシュを除き、同じ対象を再実行し成功と本文一致を確認。元製品本文も一致。

| 隔離変異 | 観測したFAIL | 各復元 |
| --- | --- | --- |
| optionからTwoPlyMaterial欠落 | 通知全文assertEqual | 1件成功 |
| bestmoveを構文上有効な不合法手5e5dへ変更 | 元局面の合法手へのassertIn | 1件成功 |
| bestmove出力欠落 | 一行2秒のread_lineアサーション | 1件成功 |
| stdout.flush欠落 | 最初の通知のread_lineアサーション | 1件成功 |
| 応答改行欠落 | 最初の通知のread_lineアサーション | 1件成功 |
| bestmove後にdiagnostic行追加 | 終了後の余剰stdout空assertEqual | 1件成功 |
| 診断出力先をstdoutへ変更 | 不正position/SFENのstdout空assertEqual、2件FAIL | 2件成功 |

7変異はすべてアサーションFAIL、ERRORなし。注入した欠落による有限待ち失敗は、実際の深さ2処理の待ち超過とは区別する。復元後と通常検証では既存待ち超過なし、待ち延長・時間計測による待ち再決定・計画訂正は不要だった。

一時検証スクリプト `/tmp/check_usi_process_mutations.py`、初回 `/tmp/usi-process-first.log`、変異と復元 `/tmp/usi-process-<変異名>[-restored].log` は消える可能性があるため、結果は本表へ保存した。

## 検証・レビュー・保存

- `python3 -m unittest discover -s tests -v`：基準362件（4.686秒）、変更後362件（5.383秒）成功。件数増加なし。時間はテストスイートの表示であり性能比較ではない。
- `python3 -m unittest discover -s tests -p 'test_usi_engine*.py' -v`：31件成功。
- `.venv/bin/ruff format .`：28ファイル変更なし。`.venv/bin/ruff check .` と `git diff --check` 成功。import変更なし。
- 独立コードレビュー：Critical 0・Important 0・Minor 0、修正要求なし。レビュアーもUSI31件・7変異と各復元・元ソース一致・対象Ruff・差分を独立実測。全体362件はレビュアー未再実行。独立文書レビューもCritical 0・Important 0・Minor 0、修正要求なし。実行者・レビュアーとも対象6文書の相対リンク・見出し450件問題0と差分を確認。結果追記と再開案内への参照追加後の最終検査は451件問題0、Ruff整形28ファイル・lint・差分も成功。外部URL疎通は対象外。
- 指定項目の検証・独立レビュー・記録がそろい、結果追記後の最終検査を経て通常フック付きコミットへ保存する。mainは `3be8b7d` のまま、今回の変更と準備 `875b60a` は未統合。main取り込み・取り込み先検証・最後の理解確認は未実施。計画訂正・裁定・辞退したMinorなし。

## 検出範囲と未検証

今回単独は実標準入出力の通知、設定送信後の一局面の合法応答、正常時の余剰出力、不正局面の診断分離を確認する。合法性だけでRandom/Materialへの取り違えや最良手選択は検出しない。設定受け渡し・局中固定・未知値保持・実choose_moveと局面保存は既存USI関数テスト、探索の採点・視点・枝独立性はmovegenテストが補完する。

全局面・他乱数種・環境への一般性、実プロセスでのSFEN新方式応答・resign・局面保存、ランチャー新方式bestmoveは今回の単独検証では未確認。既存SFENプロセステストは未設定時の動作を引き続き確認する。タスク5・性能合否・棋力・ShogiHomeへ進んでいない。

## 要点・確認問題・振り返り・次への問い

`PipeLineReader` はpipeの一行を有限待ちで読むテスト補助データ型。`read_line` はその読み取り操作。`bestmove` は返した指し手であり、返答だけで局面へ適用する操作ではない。

最後の理解確認問題と本人回答・補足は、main取り込みの本人承認と取り込み先検証後に一問ずつ扱う。現在は未出題・未回答であり正解を記録しない。今回の振り返りは、既存実装が成立していても実プロセス境界の検出力を具体的な失敗と復元で確かめられたこと。次への問いは「終了前の返答をどう確かめたか」。後続テーマの選定はまだ行わない。
