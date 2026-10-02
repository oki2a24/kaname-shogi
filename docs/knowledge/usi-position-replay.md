# USI平手局面コマンドの再生

`position startpos moves ...` から、指し手を順に合法適用した現在局面を得る方法を記録する。

## API

`kaname_shogi.usi_position.parse_usi_position(command: str) -> Position` は、完全な `position startpos moves <move1> ... <moveN>` コマンドを受け取り、手順を再生した独立 `Position` を返す。`moves` と1手以上の指し手が必須で、`position startpos` 単独や `position sfen ...` は対象外である。

## 責務

- `parse_usi_move(text)` は一手トークンを `BoardMove` または `DropMove` に変換する。盤面の合法性は判定しない。
- `parse_usi_position(command)` は `position` 文法を確認し、各トークンの変換を `parse_usi_move` に委譲する。
- `GameRecord.apply_move` / `apply_drop` が現在局面に対する合法手適用を担う。
- 戻り値の `Position` は盤面・手番・持ち駒であり、指し手履歴を含まない。必要な呼び出し側は入力コマンドまたは別の `GameRecord` を保持する。

文法エラー、一手変換失敗、不合法手はいずれも `ValueError`。一手に起因する場合、メッセージには手数とトークンが含まれる。USIの位置コマンド文法については [USI原案](https://hgm.nubati.net/usi.html) と[将棋所の説明](https://shogidokoro2.stars.ne.jp/usi.html)を参照。
\n