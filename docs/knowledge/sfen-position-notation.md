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

## ShogiHome 1.28.1のSFEN貼り付けと手数の境界

第70回に公式ソースと第69回の既存ログを照合した。ShogiHome 1.28.1の[固定依存](https://github.com/sunfish-shogi/shogihome/blob/24960d39d0557e0109cb48e608d5e62a6cd48dd7/package-lock.json#L16416)はtsshogi 2.3.4である。

- [ShogiHomeのSFEN読込](https://github.com/sunfish-shogi/shogihome/blob/24960d39d0557e0109cb48e608d5e62a6cd48dd7/src/renderer/record/manager.ts#L229)は、`Position.newBySFEN`（局面データを生成する操作）の結果を `new Record(position)`（新しい棋譜データの生成）へ渡す。
- tsshogiの[局面読込](https://github.com/sunfish-shogi/tsshogi/blob/bec83166c011eb662ee963f04ddb3fe2eb584c99/src/position.ts#L605)は盤面・手番・持ち駒を保存し、入力の手数欄は検証するが保持しない。
- [棋譜生成](https://github.com/sunfish-shogi/tsshogi/blob/bec83166c011eb662ee963f04ddb3fe2eb584c99/src/record.ts#L436)は読み込んだ局面を開始局面とし、開始ノードの棋譜内手数を0にする。SFENの手数から過去の指し手履歴を生成するわけではない。
- [局面のSFEN生成](https://github.com/sunfish-shogi/tsshogi/blob/bec83166c011eb662ee963f04ddb3fe2eb584c99/src/position.ts#L586)の `sfen` は `getSFEN(1)` を呼ぶ。[棋譜のUSI生成](https://github.com/sunfish-shogi/tsshogi/blob/bec83166c011eb662ee963f04ddb3fe2eb584c99/src/record.ts#L1099)は開始局面の `sfen` を使用するため、手数欄は1になる。現在局面用の `Record.sfen` が棋譜内手数+1を指定する処理とは区別する。

この経路は、第69回で3手後の4欄SFEN `... w - 4` を貼り付けた後、ShogiHomeが `position sfen ... w - 1` を送った実測と一致する。盤面・手番・持ち駒が保たれたまま、入力手数は保持されない。新しい棋譜の「開始局面」は平手の初期配置を意味しない。

これは当該公式版の実装経路と一例のログの照合であり、作者の設計意図、当時の実行中アプリ内部状態、他版・他形式の手数保持は未確認である。kaname-shogiが受信後に探索状態へ `Position` だけを渡す処理とは別の境界である。調査の出典・本人回答・限界は[第70回学習記録](../learning/70-shogihome-sfen-move-number.md)を参照する。

## 関連資料

- [USI局面の再生](usi-position-replay.md)
- [USI一手表記](usi-move-notation.md)
- [棋譜・局面のメモリ内保存](29-game-record-and-position-save.md)

## 出典

- [The Universal Shogi Interface (USI), original description](https://hgm.nubati.net/usi.html) — SFEN欄とUSI `position` コマンド。
- [ShogiHome公式Issue #1115](https://github.com/sunfish-shogi/shogihome/issues/1115) — GUIへ貼り付けるSFENの手数欄省略。
- [YaneuraOu `position.cpp`](https://github.com/yaneurao/YaneuraOu/blob/master/source/position.cpp) — 別エンジンのSFEN読込実装。
- [cshogi `Engine.py`](https://github.com/TadaoYamaoka/cshogi/blob/master/cshogi/usi/Engine.py) — 別実装でのUSI position処理。
