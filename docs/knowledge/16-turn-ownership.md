# 手番と駒の所有者

## 確定事項

- `Position.side_to_move` は、局面で次に指す側を表すデータである。
- `Piece.side` は、盤上のその駒を所有する側を表すデータである。
- `apply_move(position, source, destination)` は、出発駒が存在し、その `Piece.side` と `Position.side_to_move` が一致するときだけ移動を適用する。
- 所有者と手番が不一致なら `ValueError` とし、盤面と `side_to_move` を変更しない。
- `move_piece(board, source, destination)` は盤面専用の操作であり、手番も所有者照合も扱わない。

## 理由

将棋は先手・後手が交互に一手ずつ指し、同じ側が二手連続して指せない。局面の手番と駒の所有者を照合することで、この最小の規則を表現する。

## 出典

- [日本将棋連盟「将棋とは？」](https://www.shogi.or.jp/knowledge/about/)
- [日本将棋連盟「対局規則」第2条](https://www.shogi.or.jp/match/taikyoku_rules/)

## 関連資料

- [第23回：手番に合う駒だけを移動できること](../learning/23-turn-ownership.md)
- [第11回実装の設計：手番に合う駒だけを移動できること](../design/11-turn-ownership.md)
