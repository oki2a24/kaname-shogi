# USI一手表記と内部の一手データ

USIの一手トークンと `kaname_shogi.move` の `BoardMove` / `DropMove` の対応を記録する。ここでの変換は文字列表記と値の対応であり、局面への適用や合法性判定ではない。

## 座標

USI座標は筋の数字1〜9と段の小文字a〜iを続けて書く。右上が `1a`、左下が `9i`。内部では数字を `Square.file`、段をa=1〜i=9の `Square.rank` に対応させる。

例：`7g` は `Square(7, 7)`、`7f` は `Square(7, 6)`。したがって `7g7f` は `BoardMove(Square(7, 7), Square(7, 6), promote=False)` となる。

## 一手の表記

- 盤上移動は出発座標と到着座標を続ける。成る手は末尾に `+` を付け、内部の `BoardMove.promote` を `True` にする。
- 駒打ちは大文字の駒記号、`*`、打ち先座標を続ける。対応する駒種は `P`=歩、`L`=香、`N`=桂、`S`=銀、`G`=金、`B`=角、`R`=飛。
- このプロジェクトではUSIの持ち駒7種と内部モデルに合わせ、玉打ち表記を拒否する。

## 責務境界

`kaname_shogi.usi_move.parse_usi_move` と `format_usi_move` がUSI一手表記と既存Move値を相互変換する。Move値型はUSIに依存しない。変換は駒の動き、成りの可否、所有者、持ち駒の有無、打ち先、二歩、王手や打ち歩詰めを検査しない。局面処理側で別途扱う。

## 出典

- [将棋所：USIプロトコルとは](https://shogidokoro2.stars.ne.jp/usi.html) — 座標、盤上移動、成り、駒打ちの表記。
- [The Universal Shogi Interface (USI), original description](https://hgm.nubati.net/usi.html) — `1a` / `9i` の座標例、指し手表記、持ち駒欄の7駒種。
- 玉打ち拒否と変換の責務境界は、USI資料の記述に加え、本プロジェクトの内部モデルと合意した設計に基づく。
