# kaname-shogi

`kaname-shogi` は、将棋のルールを学びながら、ゼロから少しずつ育てていく自作の将棋プログラムです。

最初の目標は、コマンドラインで動く、ごく弱くても自分で理解できるプログラムを作ることです。将来的には、探索による強化、USI対応、将棋GUIとの対局へと段階的に進むことを考えています。

強さだけを急ぐのではなく、将棋とプログラムの両方を理解しながら育てます。息子と将棋を通じて成長を共有できるものにすることも、このプロジェクトの大切な目的です。

## 現在の状態

初期配置のCLI表示と、玉・歩・金・銀・桂・香・飛車・角の移動先候補を求める関数を実装しました。CLIは平手の初期配置と「手番：先手」を表示して終了します。候補計算は盤面を変更せず、実際の駒の移動や対局はまだできません。

実行・テストともにPython標準ライブラリのみを使用します。外部パッケージのインストールは不要で、`requirements.txt` は作成していません。

## 実行方法

動作確認環境：macOS、Python 3.9.6。リポジトリ直下で実行します。

```sh
python3 -m kaname_shogi
```

盤は先手視点で、左から9〜1筋、上から一〜九段です。`+` は先手、`-` は後手、`・` は空マスを表します。日本語を表示できる等幅フォントの端末を想定しています。

## テスト

```sh
python3 -m unittest discover -s tests -v
```

座標の検証、駒の不変性、盤面の独立性、初期配置の全81マス・枚数・手番、CLI表示、歩・金・銀・桂・香・飛車・角の候補の向き・盤外・占有・盤面不変性を確認します。

`-v` を付けると、英語のテストメソッド名に続けて、日本語のdocstringの先頭行が表示されます。テスト名は検索・個別実行に使える英語のまま、確認する振る舞いと検出したい誤りは日本語のdocstringで説明しています。

## コードを読むとき

歩の候補をPythonから調べる例です。リポジトリ直下でPythonを起動して実行できます。

```python
from kaname_shogi.model import Square, create_initial_position
from kaname_shogi.movegen import pawn_move_candidates

position = create_initial_position()
print(pawn_move_candidates(position.board, Square(7, 7)))
# [Square(file=7, rank=6)]
```

先後は出発マスの歩が持つ所有者から読み取ります。候補なしは `[]`、出発マスが空または歩以外なら `ValueError` です。成りや王手などを検証していないため、戻り値は合法手の確定ではありません。

金は `gold_move_candidates(board, source)` で調べます。先後は盤上の金から読み、盤外・自駒を除いた0〜6候補を固定順で返します。出発点が空または金以外なら `ValueError` です。

```python
from kaname_shogi.movegen import gold_move_candidates

print(gold_move_candidates(position.board, Square(6, 9)))
# [Square(file=6, rank=8), Square(file=7, rank=8), Square(file=5, rank=8)]
```

公開する型・関数・メソッドのdocstringには、引数・戻り値・変更する状態・前提条件と、その設計を選んだ背景を記録します。将来の保守では、仕様を変える際にdocstringも更新してください。判断の詳しい経緯は設計書と学習記録を参照できます。

銀は `silver_move_candidates(board, source)` で調べます。先後は盤上の銀から読み、盤外・自駒を除いた0〜5候補を固定順で返します。出発点が空または銀以外なら `ValueError` です。成銀や成りの選択は扱いません。

```python
from kaname_shogi.movegen import silver_move_candidates

print(silver_move_candidates(position.board, Square(7, 9)))
# [Square(file=7, rank=8), Square(file=6, rank=8)]
```

桂馬は `knight_move_candidates(board, source)` で調べます。knightは桂馬、
move_candidatesは移動先候補を求める操作です。盤上の桂馬の所有者から前方を決め、
右前（筋−1）・左前（筋＋1）の順に、段を2つ進んだ盤内のマスを最大2個返します。
桂馬は途中の駒を飛び越えられます。自駒のある到着先は除外し、相手駒のある到着先は
含めます。候補なしは `[]`、出発点が空または桂馬以外なら `ValueError` です。

```python
from kaname_shogi.model import Board, Piece, PieceType, Side, Square
from kaname_shogi.movegen import knight_move_candidates

board = Board()
board.set_piece(Square(5, 5), Piece(PieceType.KNIGHT, Side.SENTE))
print(knight_move_candidates(board, Square(5, 5)))
# [Square(file=4, rank=3), Square(file=6, rank=3)]
```

候補計算では盤面を変更せず、`Position.side_to_move`にも制限されません。成桂・成り、
行き所のない桂の合法性、駒取り、実際の移動、王手、合法手の確定、持ち駒は対象外です。

香は `lance_move_candidates(board, source)` で調べます。lanceは香、move_candidatesは移動先候補を求める操作です。Boardは盤面のデータ、Squareは筋・段を持つマスの値です。盤上の香の所有者から前方を決め、同じ筋の候補を近い順に0〜8個返します。自駒の手前、または最初の相手駒のマスで止まり、駒を飛び越しません。候補なしは `[]`、出発点が空または香以外なら `ValueError` です。盤面は変更せず、成りや合法手の確定は扱いません。

```python
from kaname_shogi.model import Board, Piece, PieceType, Side, Square
from kaname_shogi.movegen import lance_move_candidates

board = Board()
board.set_piece(Square(5, 5), Piece(PieceType.LANCE, Side.SENTE))
board.set_piece(Square(5, 3), Piece(PieceType.PAWN, Side.GOTE))
print(lance_move_candidates(board, Square(5, 5)))
# [Square(file=5, rank=4), Square(file=5, rank=3)]
```

５三は相手の歩を取る移動の候補ですが、この計算では香は５五、歩は５三に残ります。

飛車は `rook_move_candidates(board, source)` で調べます。rookは飛車、move_candidatesは移動先候補を求める操作です。右・左・前・後ろの順に各方向を近い順で走査し、空マスと最初の相手駒のマスを候補に含めます。自駒のマスとその先は含めません。先後は出発マスの飛車から読み、手番には制限されません。出発点が空または飛車以外なら `ValueError` です。

```python
from kaname_shogi.movegen import rook_move_candidates

print(rook_move_candidates(board, Square(5, 5)))
# [Square(file=4, rank=5), Square(file=3, rank=5), ...,
#  Square(file=5, rank=6), Square(file=5, rank=7), ...]
```

候補計算では飛車や他の駒を動かしたり取ったりしません。成り、王手、合法手の確定は扱いません。

角は `bishop_move_candidates(board, source)` で調べます。bishopは角、move_candidatesは移動先候補を求める操作です。右前・左前・右後ろ・左後ろの順に各方向を近い順で走査し、空マスと最初の相手駒のマスを候補に含めます。自駒のマスとその先は含めません。先後は出発マスの角から読み、手番には制限されません。出発点が空または角以外なら `ValueError` です。

```python
from kaname_shogi.movegen import bishop_move_candidates

print(bishop_move_candidates(board, Square(5, 5)))
# [Square(file=4, rank=4), Square(file=3, rank=3), ...,
#  Square(file=6, rank=6), Square(file=7, rank=7), ...]
```

候補計算では角や他の駒を動かしたり取ったりしません。成り、馬の縦横1マス、王手、合法手の確定は扱いません。

## 文書

- [第20回：玉の移動先候補](docs/learning/20-king-move-candidates.md)
- [玉の移動先候補の設計](docs/design/09-king-move-candidates.md)
- [玉の移動先候補の実装計画](docs/plans/2026-09-20-king-move-candidates.md)

- [学習・開発の再開案内](docs/resume.md)
- [プロジェクトの背景](docs/01-project-background.md)
- [プロジェクトの方向性](docs/02-project-direction.md)
- [第1回実装の設計](docs/design/01-board-and-initial-position.md)
- [第4回：実装設計と判断の背景](docs/learning/04-first-implementation-design.md)
- [第1回実装の設計：参照メモ](docs/knowledge/04-first-implementation-design.md)
- [第5回：初期配置CLIの実装と検証](docs/learning/05-initial-position-implementation.md)
- [第6回：歩の移動候補](docs/learning/06-pawn-move-candidates.md)
- [歩の移動先候補：実装用メモ](docs/knowledge/06-pawn-move-candidates.md)
- [第2回実装の設計：歩の移動先候補](docs/design/02-pawn-move-candidates.md)
- [第7回：歩の候補生成の設計と実装](docs/learning/07-pawn-candidates-implementation.md)
- [第8回：金の移動先候補](docs/learning/08-gold-move-candidates.md)
- [金の移動先候補：参照メモ](docs/knowledge/08-gold-move-candidates.md)

- [第3回実装の設計：金の移動先候補](docs/design/03-gold-move-candidates.md)
- [第9回：金の候補生成の設計と実装](docs/learning/09-gold-candidates-implementation.md)
- [第10回：銀の移動先候補](docs/learning/10-silver-move-candidates.md)
- [銀の移動先候補：参照メモ](docs/knowledge/10-silver-move-candidates.md)
- [第4回実装の設計：銀の移動先候補](docs/design/04-silver-move-candidates.md)
- [第11回：銀の候補生成の設計と実装](docs/learning/11-silver-candidates-implementation.md)
- [第18回：桂馬の移動先候補](docs/learning/18-knight-move-candidates.md)
- [桂馬の移動先候補：参照メモ](docs/knowledge/15-knight-move-candidates.md)
- [第8回実装の設計：桂馬の移動先候補](docs/design/08-knight-move-candidates.md)
- [第19回：桂馬の候補生成の実装](docs/learning/19-knight-candidates-implementation.md)

- [第12回：香の移動先候補](docs/learning/12-lance-move-candidates.md)
- [香の移動先候補：参照メモ](docs/knowledge/12-lance-move-candidates.md)
- [第5回実装の設計：香の移動先候補](docs/design/05-lance-move-candidates.md)
- [第13回：香の候補生成の設計と実装](docs/learning/13-lance-candidates-implementation.md)
- [第14回：飛車の移動先候補](docs/learning/14-rook-move-candidates.md)
- [飛車の移動先候補：参照メモ](docs/knowledge/13-rook-move-candidates.md)
- [第6回実装の設計：飛車の移動先候補](docs/design/06-rook-move-candidates.md)
- [第15回：飛車の候補生成の実装](docs/learning/15-rook-candidates-implementation.md)
- [第16回：角の移動先候補](docs/learning/16-bishop-move-candidates.md)
- [角の移動先候補：参照メモ](docs/knowledge/14-bishop-move-candidates.md)
- [第7回実装の設計：角の移動先候補](docs/design/07-bishop-move-candidates.md)
- [角の移動先候補 実装計画](docs/plans/2026-09-19-bishop-move-candidates.md)
- [桂馬の移動先候補 実装計画](docs/plans/2026-09-20-knight-move-candidates.md)

## 名前について

`Kaname` は、息子の名前「要」に由来します。「全体を支える大切なところ」という意味も、このプロジェクトが少しずつ積み上がっていく姿に重なります。

## ライセンス

未定です。公開の形や利用範囲を考える段階で決めます。
