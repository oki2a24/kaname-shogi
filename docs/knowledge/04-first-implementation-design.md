# 第1回実装の設計：参照メモ

2026-09-13承認。[設計書](../design/01-board-and-initial-position.md)を仕様の参照先とし、ここには実装時に見返す決定事項をまとめる。[判断の背景](../learning/04-first-implementation-design.md)は学習記録を参照する。

## 決定事項

- Pythonと標準の `unittest` を使う。外部依存なしをREADMEに記載し、`requirements.txt` は作らない。
- パッケージは直下の `kaname_shogi/`。今回は `src/` を設けない。
- `Square(file, rank)` と `Piece(piece_type, side)` は `dataclass(frozen=True)`。
- `Side` と `PieceType` は列挙型。先後と基本8種類の駒を表す。
- `Board` は可変の9×9リスト、空マスは `None`。`Position` は可変で盤面と手番を保持する。
- 成り状態・持ち駒などは必要な回に追加する。
- 左下原点で `x = 9 - file`、`y = 9 - rank`、`cells[y][x]`。変換は `Square.to_indices()` に集約する。
- 初期配置生成は独立した盤面を返し、手番は先手。表示文字列の生成と標準出力を分ける。
- 初期配置の期待値を独立に用意し、空マスを含む全81マスを確認する。

## 混同しないこと

- `frozen=True` は内包リストまで不変にしない。型注釈は実行時検証ではない。[Python公式](https://docs.python.org/3/library/dataclasses.html)
- `src/` は配置用の外側のディレクトリ、`kaname_shogi` はパッケージ名である。[Python Packaging公式](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- 内部クラス名・座標系の一致はUSI互換の条件ではない。外部形式への変換を分離し、将来SFENに必要な持ち駒・手数などを追加する。[将棋所のUSI解説](https://shogidokoro2.stars.ne.jp/usi.html)

## 実装開始時に確認すること

使用可能なPythonバージョンを確認し、動作確認したバージョンをREADMEに記録する。このメモの作成時点では、コードは未実装である。
