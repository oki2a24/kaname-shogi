# USI新値後の未知値保持

## 目的・承認範囲と開始状態

2026-10-11、本人の再開指示により[引き継ぎ](../handover-usi-invalid-value.md)を現物と照合し、[承認済み計画タスク4](../plans/2026-10-10-two-ply-implementation-plan.md#タスク4usi設定と実応答)の `test_invalid_value_preserves_two_ply_setting` 1項目のみ実施した。計画訂正なし。

場所 `/Users/oki2a24/kaname-shogi`、ブランチ `codex/usi-invalid-value-handoff`、開始HEAD `b1d8777`、差分なし。Ruff 0.16.10・固定版とローカルフック `.githooks` の一致を確認。現在の基準全体360件成功。新規worktree・push・main取り込みなし。

## 要点・契約・実際の変更

`MoveSelectionPolicy` は選択方針データ、`configured_policy` は最新の有効設定データ。`run_usi_engine` はコマンド処理の操作、`choose_move` は手を選ぶ操作である。

指定1メソッドを追加。各subTestでエンジンを新しく実行し、次の独立期待値と選択呼び出し1回を確認する。期待値を製品辞書から生成しない。

| 設定入力 | 最初のgoへ渡す方針 |
| --- | --- |
| TwoPlyMaterial → Strong | TWO_PLY_MATERIAL |
| 無設定 | RANDOM |
| Random | RANDOM |
| Material | MATERIAL |

各入力後に既存対応形式 `position startpos moves 7g7f`、go、quitを送る。未知値を最初のgoより前に送り、局内固定が設定消失を隠す偽成功を防ぐ。既存spyで選択境界だけを置換し、設定受付・状態処理・局面再現・合法手列挙は実際に動かす。

## TDD・検出力と復元

単独実行：`PYTHONPATH=tests python3 -m unittest test_usi_engine.UsiEngineFunctionTests.test_invalid_value_preserves_two_ply_setting -v`。

まず新値→未知値のケースだけを追加して初回有効Greenを確認し、続いて計画指定の無設定・旧値を加えてGreenを確認した。既存の既知値判定が未知値で設定を更新しないため、製品変更は不要。未実装Red→製品修正とは扱わない。Refactorも不要、import変更なし。

隔離コピーへの誤り注入を実行し、次の8変異すべてで対象アサーションFAIL、ERRORなし、各復元後単独1件成功・ソース一致を確認した。元作業ツリーの製品コードへ注入していない。

| 誤り | 検出箇所 |
| --- | --- |
| 未知値でRandomへ戻す | 新値後の方針比較 |
| 未知値でMaterialへ取り違える | 新値後の方針比較 |
| 新値後だけ設定を消す | 新値後の方針比較 |
| 未知値を方針データとして受理する | 新値後の方針比較 |
| 選択境界へRANDOMを渡す | 新値・Materialの方針比較 |
| 選択呼び出し欠落 | 呼び出し数0≠1 |
| 無設定の既定値をMaterialへ変える | 無設定の方針比較 |
| 旧MaterialをRandomへ変える | Materialの方針比較 |

一時スクリプト `/tmp/check_usi_invalid_mutations.py` と `/tmp/usi-invalid-mutation-1.log`〜`8.log` は消える可能性があるため、結果を本書に残す。

## 回帰・範囲・未検証

- USI関連：`python3 -m unittest discover -s tests -p 'test_usi_engine*.py' -v`、30件成功。
- 全体：`python3 -m unittest discover -s tests -v`、361件成功。
- `.venv/bin/ruff format .` は28ファイル変更なし、`.venv/bin/ruff check .` と `git diff --check` 成功。

代表例は未知値Strongを新値直後・最初go前に送る1系列。無設定と旧2値は同メソッドの対照例である。設定の寿命と独立した先後・駒種の組合せや不要な全未知文字列を追加しない。有限例を全入力への証明としない。

単独で上表の誤りを検出する。明示Randomを無視する誤りは既定RANDOMと結果が同じで、この対照例だけでは識別しない。既存テストにも有効値から明示Randomへ戻す固有ケースはなく、この切替は未検証として残す（今回の計画指定は旧値が従来値を返すassertであり、範囲を拡張しない）。旧Material後の未知値保持・不正値のみ・未知名、通知、新値大小混在、局中固定・次局継承は既存テストが補完する。

新方式の実選択・局面保存・手なしresign・実プロセスbestmove・性能・棋力・ShogiHomeは今回対象外・未検証。全体回帰に既存プロセステストを含むことを、新方式の実応答完了と扱わない。タスク4全体は未完了。

## 独立レビュー・保存状態

独立コード・文書レビューは各Critical 0・Important 0・Minor 0、修正要求・未解消指摘・辞退Minorなし。レビュアーも単独1件・USI30件・隔離8変異のアサーションFAILと各復元成功・ソース一致を再実行した。基準360件・全体361件はログ確認のみで、全体回帰とRuffはレビューでは再実行していない。実行者とレビュアーが変更4文書の相対リンク・見出し406件問題0と差分検査成功を確認した。結果追記後のリンク406件・Ruff整形確認28ファイル・lint・差分検査も成功し、通常フック付きコミットへ保存した。初回Git保存操作はサンドボックスでindex.lock作成を拒否されたため、許可された権限付き再実行で通常フックを通した。検査回避なし。main取り込みは別途本人承認を待つ。取り込み先検証と最後の理解確認は未実施。

## 確認問題・回答・振り返り・次回への問い

最後の理解確認は取り込み先検証後に一問だけ出す。未出題・未回答。

振り返り：未知値を局内固定前に送ることで、最新設定を保つ処理を直接確認できた。初回Greenを未実装Redと区別し、隔離誤り注入と復元で検出力を確認した。

次回への問い：指定1項目をmainへ取り込むか。承認後は取り込み先検証と理解確認へ進み、実応答・性能へ自動継続しない。
