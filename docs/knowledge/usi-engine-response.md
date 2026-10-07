# USIエンジンの一手応答

更新日：2026-10-07

## 境界

`kaname_shogi.usi_engine.run_usi_engine(input_fn, output_fn, rng=None)` は注入された一行入出力関数でUSIコマンドを処理する。入力関数はEOF時に `EOFError` を送出し、出力関数には改行なしの応答一行を渡す。標準入出力の入口は `python3 -m kaname_shogi.usi_engine`。日本語CLIとは分離している。

## 局面と一手

- `position` は `position startpos moves <1手以上>` のみ対応し、`parse_usi_position` が再現した最新 `Position` を非公開 `_UsiEngineState` が保持する。状態オブジェクトは `Position` または未設定の `None` だけを持つ。
- `replace_position` は局面を置き換え、`clear_position` は未設定へ戻し、`require_position` は局面を返すか未設定時に `ValueError` を送出する。設定値、棋譜、合法手選択、乱数器はこの状態オブジェクトへ入れない。
- `legal_moves(position)` が合法手を列挙し、共通の `choose_move(position, moves, policy, rng)` が方針別に一手を選び、`format_usi_move` が表記する。選択した手はUSIエンジン内のPositionへ適用しない。
- 合法手がない場合は `bestmove resign` を返す。

## Difficulty option と局ごとの方針

`usi` には次のcombo行を `usiok` より前に出す。

```text
option name Difficulty type combo default Random var Random var Material
```

`setoption name Difficulty value Random` は一様ランダム、`value Material` は一手後の駒得比較を選ぶ。設定がない場合は `Random`。USI仕様に従い、受信時のoption名と値は大文字小文字を区別せずに比較する。[USI仕様 §5.3 `setoption`](https://hgm.nubati.net/usi.html)はnameとvalueをcase-insensitiveとしている。未知の設定名は読み飛ばし、既知の `Difficulty` に不正値が届いた場合は最後の有効値を保つ。

設定値は `run_usi_engine` 内で `_UsiEngineState` と別に保持する。局の最初の `go` で有効値を局内方針として固定するため、後から届いた `setoption` は現在局の後続 `go` には影響しない。`usinewgame` は局面を消し、局内固定だけを解除して、設定値を次局へ残す。乱数器も設定・局面状態と別にし、一回のエンジン実行中で共有する。

## コマンドとエラー

- `usi` はid行、Difficulty option行、`usiok`を順に返し、`isready` は `readyok` を返す。
- `gameover`、未知コマンド、未知の `go` トークンは応答せず読み飛ばす。
- 時計引数は使わず、`go` を受けると合法手選択後すぐ応答する。
- `searchmoves`、`depth`、`nodes`、`mate`、`infinite`、`ponder` は未対応として `ValueError`。有効なpositionがない `go` と、対応外・不正なpositionも `ValueError`。
- 実行入口は `ValueError` をstderrへ診断し、非0で終了する。USI応答だけをstdoutに書き、各行をflushする。
- `quit` と入力EOFは正常終了する。

## コマンド行の表現

コマンド行は `split()` と既存の文字列分岐で扱う。USIコマンド型や公開状態APIは設けない。非公開状態クラスを独立モジュールやpackage rootから再exportしない。

第59〜62回にShogiHome 1.28.1で平手対局・観察を行った記録は[ShogiHome対局の知識メモ](usi-shogihome-gameplay.md)を参照する。第65回はDifficulty選択画面とMaterial設定のUSI送信を確認し、第66回は同じ7手局面でRandomの☖９四歩、Materialの☖８八角成を実機観察し、両方の設定と着手をUSIログで確認した。これは一局面・各設定一局の実例であり、他局面に対する一般性は示さない。詳細は[第66回学習記録](../learning/66-shogihome-material-move-effect.md)を参照する。
