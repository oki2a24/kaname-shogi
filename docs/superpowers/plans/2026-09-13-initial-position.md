# 初期配置CLIの実装計画

> 実行担当者向け：`superpowerssuperpowers:executing-plans` を使い、このタスク内で順番に実行する。チェックボックスで進捗を記録する。

**目的：** 筋・段で扱う初期配置と先手の手番をCLIに表示する。

**構成：** `model.py` が値・盤・局面を保持し、`display.py` が表示文字列を生成する。`__main__.py` だけが標準出力を行う。内部の81マスの添字は `Square.to_index()` に集約する。

**技術：** Python標準ライブラリ、dataclasses、Enum、unittest。実行環境はPython 3.9.6。

**仕様：** [承認済み設計](../../design/01-board-and-initial-position.md)

## 共通の制約

- 説明・文書・コメントは日本語。
- 外部依存と `requirements.txt` は追加しない。
- `Square`・`Piece` は不変、`Board`・`Position` は可変。
- 筋・段は1〜9の整数。真偽値・非整数・範囲外は `ValueError`。
- 駒の移動・成り・持ち駒・合法手・探索・USI・SFENを追加しない。
- 全マスを筋・段で検証し、保存順とは独立した期待配置を用意する。
- 既存の隔離作業ツリーを使用する。実装前のテストは存在しない。

## 手順1：値と盤面

作成：`kaname_shogi/__init__.py`（空）、`kaname_shogi/model.py`、`tests/test_model.py`、`.gitignore`。

公開する型と操作：

```python
Square(file: int, rank: int)
Square.to_index() -> int
Side.SENTE / Side.GOTE
PieceType.KING / ROOK / BISHOP / GOLD / SILVER / KNIGHT / LANCE / PAWN
Piece(piece_type: PieceType, side: Side)
Board()
Board.piece_at(square: Square) -> Optional[Piece]
Board.set_piece(square: Square, piece: Optional[Piece]) -> None
```

- [x] `unittest.TestCase` で四隅と７六の変換、不正な座標、不変性、空盤、配置と取得、盤面の独立性を先に検証する。

```python
self.assertEqual(Square(7, 6).to_index(), 59)
self.assertEqual(Square(9, 9).to_index(), 80)
with self.assertRaises(ValueError):
    Square(True, 1)
board = Board()
piece = Piece(PieceType.PAWN, Side.SENTE)
board.set_piece(Square(7, 6), piece)
self.assertEqual(board.piece_at(Square(7, 6)), piece)
self.assertIsNone(Board().piece_at(Square(7, 6)))
```

- [x] `python3 -m unittest discover -s tests -v` を実行し、対象の型が未実装であるため失敗することを確認する。
- [x] 以下の方針で最小実装を行う。`Side`・`PieceType` は列挙値、`Square`・`Piece` は凍結dataclass。`Board` は内部に81個の `None` を保持する。

```python
if any(type(value) is not int or not 1 <= value <= 9
       for value in (self.file, self.rank)):
    raise ValueError("筋・段は1〜9の整数で指定してください")
# Square.to_index
return (self.file - 1) * 9 + (self.rank - 1)
# Board.__init__
self._cells: list[Optional[Piece]] = [None] * 81
# Board.piece_at / set_piece
return self._cells[square.to_index()]
self._cells[square.to_index()] = piece
```

- [x] 同コマンドで成功を確認し、差分を確認してコミットする。`.gitignore` は `__pycache__/` と `*.py[cod]` を除外する。

## 手順2：初期局面

変更：`kaname_shogi/model.py`、`tests/test_model.py`。

公開する操作：`Position(board: Board, side_to_move: Side)` と `create_initial_position() -> Position`。手順1の `Board.set_piece()` を使う。

- [x] 表示の並びで独立した期待配置を作り、全81マスを比較する。各側20枚、歩9枚、玉1枚と先手の手番を検証する。生成した二つの盤面の一方を書き換え、他方が変わらないことも確認する。

```python
# 行は一〜九、各行は９筋〜１筋。大文字が先手、小文字が後手。
rows = (
    "lnsgkgsnl", ".r.....b.", "ppppppppp",
    ".........", ".........", ".........",
    "PPPPPPPPP", ".B.....R.", "LNSGKGSNL",
)
self.assertEqual(create_initial_position().side_to_move, Side.SENTE)
```

- [x] 全テストを実行し、初期局面の生成が未実装で失敗することを確認する。
- [x] 可変dataclassの `Position` を追加する。歩は先手七段・後手三段に置く。最奥段は筋1〜9に香・桂・銀・金・玉・金・銀・桂・香を配置する。飛角は明示する。

```python
board.set_piece(Square(8, 8), Piece(PieceType.BISHOP, Side.SENTE))
board.set_piece(Square(2, 8), Piece(PieceType.ROOK, Side.SENTE))
board.set_piece(Square(8, 2), Piece(PieceType.ROOK, Side.GOTE))
board.set_piece(Square(2, 2), Piece(PieceType.BISHOP, Side.GOTE))
return Position(board, Side.SENTE)
```

- [x] 全テストの成功と差分を確認してコミットする。

## 手順3：CLI表示と利用文書

作成：`kaname_shogi/display.py`、`kaname_shogi/__main__.py`、`tests/test_display.py`。
変更：`README.md`。学習記録と参照メモに実装時の確認結果を追記する。

公開する操作：`render_position(position: Position) -> str`。盤面の参照は `position.board.piece_at(Square(file, rank))` のみを使う。

- [x] 初期配置の全文を固定した期待文字列と照合するテストを書く。後手の手番表示も確認する。`subprocess.run` でCLIの終了コード・標準出力・標準エラーを確認する。

```python
self.assertEqual(render_position(create_initial_position()), EXPECTED)
result = subprocess.run(
    [sys.executable, "-m", "kaname_shogi"],
    capture_output=True, text=True, check=False,
)
self.assertEqual(result.returncode, 0, result.stderr)
self.assertEqual(result.stdout, EXPECTED + "\n")
self.assertEqual(result.stderr, "")
```

- [x] テストを実行し、表示処理とCLIが未実装で失敗することを確認する。
- [x] 表示を実装する。１セルは通常の日本語等幅端末で4桁相当とし、駒は `+歩 `、空は ` ・ `、列見出しは ` 9  ` の形に揃える。段を一→九、筋を9→1で走査する。

```python
lines = [f"手番：{side_name}", "+：先手、-：後手", ""]
lines.append("   " + "".join(f" {file}  " for file in range(9, 0, -1)).rstrip())
for rank, label in enumerate("一二三四五六七八九", start=1):
    # 各駒を先後記号と日本語名に変換し、空は「 ・ 」とする。
    lines.append((label + " " + "".join(cells)).rstrip())
return "\n".join(lines)
```

`KING` は先手が王・後手が玉、それ以外は飛・角・金・銀・桂・香・歩。文字列生成は標準出力を行わない。CLIは以下の処理に限定する。

```python
from .display import render_position
from .model import create_initial_position

if __name__ == "__main__":
    print(render_position(create_initial_position()))
```

- [x] 全テストと `python3 -m kaname_shogi` を実行し、正常終了と表示を確認する。
- [x] READMEにPython 3.9.6での動作確認、起動・テストコマンド、実装済みの範囲を記録する。学習記録は実装で確認した事実を記録し、利用者の未回答の問題に回答を創作しない。
- [x] 設計との照合・リンク確認・`git diff --check` を行い、コミットする。マージ・公開は行わず、結果を報告する。

## 計画の自己確認

設計の座標・不変性・独立性は手順1、全81マス・枚数・手番は手順2、全文表示・CLIは手順3で確認する。`Optional[Piece]` を使い、Python 3.9.6で実行可能にする。関数名と筋段の意味は全手順で共通とする。
