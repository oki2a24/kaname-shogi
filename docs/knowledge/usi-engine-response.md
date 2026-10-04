# USIエンジンの一手応答

## 境界

`kaname_shogi.usi_engine.run_usi_engine(input_fn, output_fn, rng=None)` は、注入された一行入出力関数でUSIコマンドを処理する。入力関数は入力EOF時に `EOFError` を送出し、出力関数には改行なしの応答一行を渡す。標準入出力へ接続する入口は `python3 -m kaname_shogi.usi_engine`。既存の日本語CLIとは分離している。

## 局面と一手

- `position` は `position startpos moves <1手以上>` のみ対応し、`parse_usi_position` が再現した最新 `Position` を `usi_engine.py` 内の非公開 `_UsiEngineState` が保持する。状態オブジェクトは `Position` または未設定の `None` だけを持つ。
- 状態オブジェクトの `replace_position` は新しい局面を保持し、`clear_position` は未設定へ戻し、`require_position` は局面を返すか未設定時に `ValueError` を送出する。コマンド解析・棋譜・合法手選択・乱数器は保持しない。
- 次の `position` で保持局面を置き換え、`usinewgame` で未設定へ戻す。乱数生成器は `run_usi_engine` の実行中に選択処理側で保持し、`usinewgame` をまたいでも再利用する。
- `go` は `legal_moves(position)` → `choose_weak_move(moves, rng)` → `format_usi_move(move)` の順に既存処理へ委譲し、`bestmove <一手>` を返す。選択手は内部局面へ適用しない。
- 合法手がない場合は `bestmove resign` を返す。

## コマンドとエラー

- `usi` は `id name kaname-shogi`、`id author kaname-shogi project`、`usiok` を順に出力し、`isready` は `readyok` を出力する。
- `setoption`、`gameover`、未知コマンド、未知の `go` トークンは応答せず読み飛ばす。
- 時計引数は使わず、`go` を受けると合法手選択後すぐ応答する。
- `searchmoves`、`depth`、`nodes`、`mate`、`infinite`、`ponder` は未対応として `ValueError`。有効な `position` がない `go` と、対応外・不正な `position` も `ValueError`。
- 実行入口は `ValueError` をstderrに診断し、非0で終了する。USI応答だけをstdoutに書き、各行をflushする。
- `quit` と入力EOFは正常終了する。

## コマンド行の表現

コマンド行は `split()` と既存の文字列分岐で扱う。USIコマンド型や公開状態APIは設けない。非公開状態クラスを独立モジュールやpackage rootから再exportしない。

このメモは実装済みのローカル契約を示す。第59回ではShogiHome 1.28.1で短い平手対局を行い、2回の合法な `bestmove` が盤面・棋譜へ反映され、投了で終了することを別途確認した。通信ログを取得していないため、今回ShogiHomeが送信したコマンド列や他の機能の互換性は未確認である。詳細は[ShogiHome対局の知識メモ](usi-shogihome-gameplay.md)を参照する。追加のコマンドや強いエンジンの選択境界は、具体的な要件ができた時点で別に設計する。
