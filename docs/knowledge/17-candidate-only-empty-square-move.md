# 移動先候補に合う空マスへの移動：参照メモ

第24回で合意した、候補生成と局面への移動適用をつなぐ最小範囲を記録する。
学習の回答・出典・承認経緯は[第24回の学習記録](../learning/24-candidate-only-empty-square-move.md)、
実装上の責務と検証方針は[設計書](../design/12-candidate-only-empty-square-move.md)を参照する。

## 確定した範囲

- `apply_move(position, source, destination)` は、出発駒の所有者が手番と一致した後、
  その駒種の既存候補に `destination` が含まれるかを確認する。
- 今回受け付けるのは、既存候補に含まれる空マスだけである。
- 候補外は `ValueError` とし、盤面と手番を変更しない。
- 候補に含まれる相手駒のマスは駒取りの範囲なので、既存の `move_piece` により
  占有到着として拒否される。相手駒を取り除いたり持ち駒にしたりしない。
- `move_piece(board, source, destination)` は候補照合や手番を知らない盤面操作のままとする。
- 駒取り、持ち駒、成り、王手、合法手の確定、CLI入力は未実装である。

## 用語

- `PieceType` は駒種を表すデータである。
- 候補生成関数は、盤面と出発マスから移動先候補を求める操作である。
- `apply_move` は、盤面と手番を持つ `Position` を一手進める操作である。
