# USIエンジンの一手応答

## 境界

`kaname_shogi.usi_engine.run_usi_engine(input_fn, output_fn, rng=None)` は、注入された一行入出力関数でUSIコマンドを処理する。入力関数は入力EOF時に `EOFError` を送出し、出力関数には改行なしの応答一行を渡す。標準入出力へ接続する入口は `python3 -m kaname_shogi.usi_engine`。既存の日本語CLIとは分離している。

## 局面と一手

- `position` は `position startpos moves <1手以上>` のみ対応し、`parse_usi_position` が再現した最新 `Position` を関数内に保持する。
- 次の `position` で保持局面を置き換え、`usinewgame` で未設定へ戻す。`usinewgame` をまたいでも一回の実行の乱数生成器は再利用する。
- `go` は `legal_moves(position)` → `choose_weak_move(moves, rng)` → `format_usi_move(move)` の順に既存処理へ委譲し、`bestmove <一手>` を返す。選択手は内部局面へ適用しない。
- 合法手がない場合は `bestmove resign` を返す。

## コマンドとエラー

- `usi` は `id name kaname-shogi`、`id author kaname-shogi project`、`usiok` を順に出力し、`isready` は `readyok` を出力する。
- `setoption`、`gameover`、未知コマンド、未知の `go` トークンは応答せず読み飛ばす。
- 時計引数は使わず、`go` を受けると合法手選択後すぐ応答する。
- `searchmoves`、`depth`、`nodes`、`mate`、`infinite`、`ponder` は未対応として `ValueError`。有効な `position` がない `go` と、対応外・不正な `position` も `ValueError`。
- 実行入口は `ValueError` をstderrに診断し、非0で終了する。USI応答だけをstdoutに書き、各行をflushする。
- `quit` と入力EOFは正常終了する。

このメモは実装済みのローカル契約を示す。ShogiHomeへ登録した実対局や、合法な `bestmove` を受けたShogiHomeの挙動はまだ実証していない。コマンド型や独立状態APIは今回設けず、他のUSIコマンドへ広げるテーマで構造を再検討する。
