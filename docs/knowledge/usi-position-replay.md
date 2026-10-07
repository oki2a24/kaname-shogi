# USI局面コマンドからの局面再生

`position` コマンドから開始局面を得て、指定されたUSI指し手を順に適用する方法を記録する。SFEN欄と手数の詳しい対応は[SFEN局面表記の知識メモ](sfen-position-notation.md)を参照。

## API

`kaname_shogi.usi_position.parse_usi_position(command: str) -> SfenPosition` は、次のいずれかの全文を受け取る。

- `position startpos moves <move1> ... <moveN>`
- `position sfen <SFEN>`
- `position sfen <SFEN> moves <move1> ... <moveN>`

成功時は、現在の `Position` と1始まりの手数を持つ `SfenPosition` を返す。`startpos` は手数1から始まる。SFENの手数を指定した場合はその値を保持し、`moves` の手を適用した数だけ進める。SFENの手数欄を省略した場合は1とする。`startpos` は従来どおり `moves` と1手以上を必要とし、SFENでも `moves` を書いた場合は1手以上を必要とする。

## 責務

- `parse_usi_move(text)` は一手トークンを `BoardMove` または `DropMove` に変換する。盤面の合法性は判定しない。
- `parse_usi_position(command)` は `position` 文法とSFEN欄を解析し、各トークンの変換を `parse_usi_move` に委譲する。
- `GameRecord.apply_move` / `apply_drop` が現在局面に対する合法手適用を担う。
- 戻り値の `SfenPosition.position` は盤面・手番・持ち駒を表す。`SfenPosition.move_number` は入力SFEN由来またはUSI手順から数えた手数で、局面履歴は含まない。
- USIエンジン状態が保持するのは引き続き `.position` のみ。

文法エラー、一手変換失敗、不合法手はいずれも `ValueError`。一手に起因する場合、メッセージには手順内の手数とトークン、原因が含まれる。

## 出典

- [USI原案](https://hgm.nubati.net/usi.html) — `position [sfen ... | startpos] moves ...` の形式。
- [ShogiHome公式Issue #1115](https://github.com/sunfish-shogi/shogihome/issues/1115) — GUIへ貼り付けるSFENで手数欄を省略できる件。USI通信の欄省略の根拠とは区別する。
