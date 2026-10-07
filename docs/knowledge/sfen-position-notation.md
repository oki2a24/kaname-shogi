# SFEN局面表記と内部型の対応

SFEN文字列と `Position` の変換、USIの `position sfen`、手数と棋譜の境界を記録する。

## SFENの欄

SFENは盤面、手番、持ち駒、手数を空白で区切る。盤面は1段目から9段目へ、各段は9筋から1筋へ並べ、連続した空きマスを数字にまとめる。駒記号の大文字は先手、小文字は後手を表し、成駒は `+` を付ける。持ち駒欄は飛・角・金・銀・桂・香・歩をそれぞれ `R, B, G, S, N, L, P` で表す。枚数1は省略し、2枚以上は駒記号の前に枚数を置く。手番は先手 `b`、後手 `w`、持ち駒なしは `-`。

標準的なSFEN欄の説明とUSIの `position [sfen ... | startpos] moves ...` は[USI原案](https://hgm.nubati.net/usi.html)を参照する。

## 読み込み・書き出しAPI

- `parse_sfen(sfen: str) -> SfenPosition` は3欄または4欄のSFENを読み込む。4欄目がある場合は正の整数として保持し、省略時は手数1とする。
- `format_sfen(sfen_position: SfenPosition) -> str` は盤面と持ち駒を正規化し、手数欄を含む4欄で返す。
- `SfenPosition(position: Position, move_number: int)` はSFENの局面と1始まり手数を組にしたデータ。`Position` は盤面・手番・先後の持ち駒を保持し、手数や履歴は持たない。

盤面は `Board` と `Piece`、手番は `Side`、持ち駒は `Hand`、座標は筋・段を表す `Square` に対応する。SFENの盤面は段順と筋順を変換して `Board.set_piece(Square(file, rank), piece)` に配置する。書き出し時の持ち駒順は先手、後手それぞれ `R, B, G, S, N, L, P`。

3欄SFENを受け付けて手数1にするのは、このプロジェクトの互換方針である。ShogiHomeのSFEN貼り付けで手数欄を省略できる挙動は[公式リポジトリのIssue #1115](https://github.com/sunfish-shogi/shogihome/issues/1115)で確認した。これはGUI貼り付けの記録であり、ShogiHomeがUSI通信で3欄を送る根拠ではない。

## 入力検証の境界

読込時は盤面の段数・幅、空きマス数、ASCII駒記号、成り記号、手番、持ち駒記号と枚数、手数の構文を検査する。入力できる値がモデルで表現可能かも検査する。エラーは不正箇所が分かる `ValueError`。

玉の有無、駒の総数、二歩、王手状態、実戦での到達可能性などは検査しない。したがって、玉のない詰将棋用の局面や、通常の将棋では起こらない駒総数でも、現在の `Position` / `Hand` で表現可能なら読み込む。玉を持ち駒にするなど、内部モデルで表現できない値は拒否する。

## 持ち駒の一括加算

`Hand.add_many(piece_type: BasicPieceType, count: int) -> None` は、玉以外の基本駒種へ正の整数枚数を加える操作である。駒種と枚数を検証してから内部カウントを一度更新し、失敗時は持ち駒を変更しない。`bool` は `int` のサブクラスだが枚数としては受け付けない。

SFENの持ち駒数は合法性検査の対象ではない。`add_many` により大きな枚数もモデルへ取り込め、枚数に比例した `Hand.add` の反復でUSI入力処理が止まることを避ける。SFEN変換側から `Hand._counts` を直接変更しない。

## USI・棋譜との境界

- `parse_usi_position(command: str) -> SfenPosition` は既存の `position startpos moves ...` に加えて、`position sfen <SFEN>` と `position sfen <SFEN> moves <指し手...>` を扱う。`moves` があれば指し手を既存の一手変換・合法手適用へ渡し、SFEN手数へ適用手数を加える。
- `position startpos` は手数1から数える。
- エンジン状態が保持するのは引き続き `Position` だけであり、SFEN手数はUSI入力時の結果データに留める。
- SFENは一局面のスナップショットであり、履歴を持つ `GameRecord` や `kaname-shogi-game-record-v1` JSON棋譜とは別形式である。JSONの保存形式は変更しない。

## 関連資料

- [USI局面の再生](usi-position-replay.md)
- [USI一手表記](usi-move-notation.md)
- [棋譜・局面のメモリ内保存](29-game-record-and-position-save.md)

## 出典

- [The Universal Shogi Interface (USI), original description](https://hgm.nubati.net/usi.html) — SFEN欄とUSI `position` コマンド。
- [ShogiHome公式Issue #1115](https://github.com/sunfish-shogi/shogihome/issues/1115) — GUIへ貼り付けるSFENの手数欄省略。
- [YaneuraOu `position.cpp`](https://github.com/yaneurao/YaneuraOu/blob/master/source/position.cpp) — 別エンジンのSFEN読込実装。
- [cshogi `Engine.py`](https://github.com/TadaoYamaoka/cshogi/blob/master/cshogi/usi/Engine.py) — 別実装でのUSI position処理。
