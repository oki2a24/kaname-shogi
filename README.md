# kaname-shogi

`kaname-shogi` は、将棋のルールを学びながら、ゼロから少しずつ育てていく自作の将棋プログラムです。

最初の目標は、コマンドラインで動く、ごく弱くても自分で理解できるプログラムを作ることです。将来的には、探索による強化、USI対応、将棋GUIとの対局へと段階的に進むことを考えています。

強さだけを急ぐのではなく、将棋とプログラムの両方を理解しながら育てます。息子と将棋を通じて成長を共有できるものにすることも、このプロジェクトの大切な目的です。

## 現在の状態

初期配置のCLI表示と、歩・金・銀の移動先候補を求める関数を実装しました。CLIは平手の初期配置と「手番：先手」を表示して終了します。候補計算は盤面を変更せず、実際の駒の移動や対局はまだできません。

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

座標の検証、駒の不変性、盤面の独立性、初期配置の全81マス・枚数・手番、CLI表示、歩・金・銀の候補の向き・盤外・占有・盤面不変性を確認します。

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

## 文書

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

## 名前について

`Kaname` は、息子の名前「要」に由来します。「全体を支える大切なところ」という意味も、このプロジェクトが少しずつ積み上がっていく姿に重なります。

## ライセンス

未定です。公開の形や利用範囲を考える段階で決めます。
