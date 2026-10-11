# 二手選択で例外を隠さず伝える確認

## 目的・範囲・開始状態

2026-10-11、本人の再開依頼に従い、[開始時引き継ぎ](../handover-two-ply-invalid-move-errors.md)の「次の具体的な行動」を実施した。対象は[承認済み計画](../plans/2026-10-10-two-ply-implementation-plan.md)タスク2の `test_does_not_hide_invalid_move_errors` 1項目のみ。未知型のTypeErrorと不合法な盤上移動のValueErrorが、公開選択操作から呼び出し側へ伝わることを確認する。計画の訂正・追加は不要だった。

場所 `/Users/oki2a24/kaname-shogi`、ブランチ `codex/two-ply-invalid-move-errors-handoff`、開始HEAD `a827caa`、変更なしを実測。mainは `1e1bbd8`、準備 `a827caa` はmain未取り込み。Ruff 0.16.10は固定版と一致、ローカルフック `.githooks` を確認。新規worktree・pushなし。基準全体355件は今回新たに実行して成功し、前テーマの実績を流用していない。

## 表現・対象契約・確認方法

`MoveSelectionPolicy` は選択方針データ、`TWO_PLY_MATERIAL` は二手先読み方針の値。`Position` は局面データ、`Square` は筋・段を表すマスの値、`BoardMove` は盤上移動データであり、移動を実行する操作ではない。`choose_move` は公開の一手選択操作、`_position_after_move` は複製へ一手を適用する非公開操作、`apply_move` は盤上移動を局面へ適用する操作。`TypeError` は扱えない型、`ValueError` は扱える型の不正な値・移動を伝える例外である。

実装前に、既存計画の入力・期待する例外型・検出対象を明確にした。通常の入口へ合法手を渡す前提は維持し、誤入力を通常の選択結果へ変えない契約だけを扱う。

| 代表入力 | 独立した期待 | 検出したい誤り |
| --- | --- | --- |
| 空盤・先手番、非空候補 `(object(),)` | 対応しない一手型なのでTypeError | 型の誤りを握り潰してランダム選択・Noneへ変える |
| 空盤・先手番、非空候補に５五→５四の不成BoardMove | 出発マスが空なのでValueError | 不合法移動を握り潰してランダム選択・Noneへ変える |

各ケースで新しい局面と乱数器を用意し、公開 `choose_move` へ二手方針を渡す。`subTest` でケースを分け、各 `assertRaises` で例外型を確認する。期待値は製品の返値や採点から作らず、承認済み例外契約と空の出発マスという教材の性質から決めた。

- 既存補完：`ApplyMoveTests.test_rejects_invalid_move_without_changing_board_or_turn` は空出発・自駒のある到着・同一マス等と状態保全を扱う。既存二手比較テストは正常候補の比較、空候補テストはNone・非抽選、既存ランダム選択テストは委譲を扱う。今回それらすべてへ誤り注入したとは扱わない。
- 未検証：不合法な駒打ち、全種類の不合法盤上移動、応手内部の例外、合法・不正候補の混在や候補位置、後手固有の誤りは今回の単独例では保証しない。例外の同一オブジェクト・文言、誤入力時の状態保全・非抽選もこのテストでは確認しない。任意の握り潰しに対する完全な証明ではない。枝独立性・二手境界は別項目として残す。

## 実際の変更・初回結果・Refactor判断

`tests/test_movegen.py` の指定1メソッドのみを追加した。import変更なし。初回有効実行は1件成功（Green）で、未実装Redではない。既存の二手選択が候補を `_position_after_move` へ渡し、未知型をTypeErrorとして送出し、`apply_move` のValueErrorも捕捉せず伝えるため成立した。

既存の製品実装で契約が成立しており、製品変更は不要。二つの小さいケースを1メソッド内で表せるためRefactorも不要と判断した。

## 隔離した誤り注入・各復元

製品パッケージと対象テストを一時ディレクトリへコピーし、公開入口の二手方針分岐へ次の例外捕捉を一つずつ注入した。元の製品コードは変更していない。

| 変異 | 意図した失敗 | 各復元後 |
| --- | --- | --- |
| TypeErrorを捕捉して既存ランダム選択へ切替 | TypeErrorケースの `assertRaises` が `TypeError not raised` でFAIL | 単独1件成功 |
| TypeErrorを捕捉してNoneを返す | TypeErrorケースの `assertRaises` が `TypeError not raised` でFAIL | 単独1件成功 |
| ValueErrorを捕捉して既存ランダム選択へ切替 | ValueErrorケースの `assertRaises` が `ValueError not raised` でFAIL | 単独1件成功 |
| ValueErrorを捕捉してNoneを返す | ValueErrorケースの `assertRaises` が `ValueError not raised` でFAIL | 単独1件成功 |

隔離基準1件成功を確認してから実施した。各変異では `FAILED (failures=1)` と対象の例外未送出を照合し、ERROR・読み込み失敗を検出成功に数えていない。各回で製品ファイルを原文へ復元し、キャッシュを除去して再実行した。終了後に元の製品ファイルの無変更も照合した。一時スクリプト `/tmp/check_invalid_move_mutations.py` と `/tmp/invalid-move-*.log` は消える可能性があるため、結論は本書へ保存する。

## 検証・独立レビュー

- 基準：`python3 -m unittest discover -s tests -v` → 355件成功。
- 単独：`python3 -m unittest discover -s tests -p test_movegen.py -k test_does_not_hide_invalid_move_errors -v` → 1件成功（2 subTest）。
- 対象：`python3 -m unittest discover -s tests -p test_movegen.py -v` → 183件成功。
- 全体：`python3 -m unittest discover -s tests -v` → 356件成功。
- `.venv/bin/ruff format .` → 28ファイル変更なし、`.venv/bin/ruff check .` と `git diff --check` 成功。

`requesting-code-review` に従い、履歴を渡さない独立レビュアーへ、指定差分・承認済み仕様と計画・契約／代表ケース／検出対象／既存補完／未検証を渡した。Critical 0・Important 0・Minor 0、修正指摘なし。レビュアーは単独1件、対象ファイルのRuff両検査、差分検査、隔離4変異の対象FAIL・各復元成功を再実測した。対象183件・全体356件はログで照合し、レビュアー自身は再実行していない。

判断辞退リストは上記の未検証事項と、ブランチ全体の完成度・統合可否。今回の小さい契約範囲を広げず未検証として残し、統合可否は本人の別途承認と取り込み先検証で判断する。これらを保証済みとは扱わない。独立文書レビューはCritical 0・Important 0・Minor 0、修正指摘なし。レビュアーは実行ログ・Git状態・現在欄と履歴の区別・未承認／未出題／未回答を照合し、相対リンク・見出し389件問題0と差分検査成功を再実測した。本人発言全文と今後の統合・理解確認・後続全体の判定は対象外。結果追記後の最終差分は実行者が確認する。文書追記のみのため、全体テストを再実行せず今回の356件成功を実績とする。結果追記後に同じ4文書のリンク・Ruff両検査・差分と製品無変更を確認し、内容を確認した5ファイルを通常フック付きでコミットする。

`finishing-a-development-branch` に従い、通常チェックアウトでmain `1e1bbd8` が共通祖先と確認した。本人の指定どおり作業ブランチを保持し、main取り込みは別途承認を待つ。計画訂正と未解消の指摘はない。README・知識メモ・方向性は製品仕様・利用面が変わらないため変更不要。引き継ぎは開始時の履歴として保持し、学習記録・索引・再開案内・次候補の現在欄を更新する。

## 確認問題・本人回答・振り返り・次回への問い

main統合は別途本人承認待ちで、未実施。取り込み先検証・最後の理解確認も未実施。確認問題はまだ出題しておらず、本人回答も未取得である。指定1項目のテスト検証と、テーマ全体の完了を区別する。

振り返り：既存実装で成立する例外契約へ不要な製品変更を加えず、握り潰しの代表的な4種類を対象アサーションで検出できた。例外がないことを正常結果と誤解しないための境界を、小さい2ケースで確認した。

次回への問い：未知型や不合法な盤上移動で、例外を伝える代わりにランダム選択やNoneを返すと、呼び出し側は何を見分けにくくなるか。これは論点の記録で、まだ出題していない。本人承認でmainへ取り込み、取り込み先検証後に最後の理解確認を一問だけ出す。タスク2全体は未完了で、枝独立性・二手境界、CLI／USI三択等へ自動継続しない。
