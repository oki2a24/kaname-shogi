# kaname-shogi

`kaname-shogi` は、将棋のルールを学びながら、ゼロから少しずつ育てていく自作の将棋プログラムです。

最初の目標は、コマンドラインで動く、ごく弱くても自分で理解できるプログラムを作ることです。将来的には、探索による強化、USI対応、将棋GUIとの対局へと段階的に進むことを考えています。

強さだけを急ぐのではなく、将棋とプログラムの両方を理解しながら育てます。息子と将棋を通じて成長を共有できるものにすることも、このプロジェクトの大切な目的です。

## 現在の状態

初期配置のCLI表示と、未成駒・成駒を含む14種の移動先候補を求める関数、空マスへの移動適用、手番に合う駒だけの局面移動、候補内の相手駒を取って持ち駒へ加える処理、持ち駒を打つ処理を実装しました。盤上の駒種は未成8種と成駒6種の14種を`PieceType`で表し、持ち駒は基本駒種8種の`BasicPieceType`で表します。`Board.copy()`・`Hand.copy()`・`Position.copy()` は可変状態を共有しない複製を返します。CLIは平手の初期配置を表示し、`move 7 7 7 6` のような盤上移動または `drop 歩 5 5` のような駒打ちを受け付けます。形式・合法性エラーは理由を表示して同じ手番で再入力し、詰みなら勝者を表示して停止します。候補計算は盤面を変更せず、`move_piece(board, source, destination)` は検証成功時に盤面を変更します。`is_in_check(board, side)` は指定側の玉が相手駒の候補に入るかを判定します。`apply_move(position, source, destination, *, promote=False)` は出発駒の所有者、既存候補、成り、駒取りを検証した後、複製局面で試し指しし、自玉が相手の利きに残る場合は `ValueError` で拒否します。`promote=True` は移動元または移動先が敵陣のときだけ成りとして新しい成駒を置き、歩・香・桂が行き所を失う移動では成りを強制します。成駒は固有の移動候補で移動し、駒取りでは基本駒種へ戻して指した側の持ち駒へ加えます。`apply_drop(position, piece_type, destination)` も複製局面で試し打ちし、自玉が相手の利きに残る場合、または持ち歩で相手玉へ解除不能な王手をかける場合は拒否します。持ち駒不足、占有マス、玉の指定、二歩、歩・香・桂を行き所のない段へ打つ操作も `ValueError` で拒否し、局面を変更しません。王手・詰み・打ち歩詰めの検出を扱います。

第32回で `has_legal_move(position)`、`is_checkmate(position)`、`is_game_over(position)` を追加しました。手番側の全ての盤上移動・成り・駒打ちを複製局面で試し、現在実装済みの規則で一つでも指せる手があるかを判定します。第33回では打ち歩詰めとなる歩打ちを合法手から除外しました。第34回ではCLIの入力解析と対局進行を追加しました。`move` / `drop` と成りの `+` は半角で、区切りと筋段は半角・全角の空白・数字を受け付けます（実装はPythonの`str.split()`を使うため、その他のUnicode空白も区切りになります）。詰みは「手番側が王手を受け、合法手がない」場合だけ、終局は今回の最小範囲では詰みだけを返します。玉がない部分局面は詰み・終局とも `False` です。投了、千日手、持将棋、入玉、時間、反則勝敗、USI/SFENはまだ扱いません。

実行・テストともにPython標準ライブラリのみを使用します。外部パッケージのインストールは不要で、`requirements.txt` は作成していません。

## 実行方法

動作確認環境：macOS、Python 3.9.6。リポジトリ直下で実行します。

```sh
python3 -m kaname_shogi
```

盤は先手視点で、左から9〜1筋、上から一〜九段です。`+` は先手、`-` は後手、`・` は空マスを表します。日本語を表示できる等幅フォントの端末を想定しています。

## 人間同士でCLI対局をする

リポジトリ直下で次のコマンドを実行すると、初期局面から対局を開始できます。

```sh
python3 -m kaname_shogi
```

先手・後手を担当する人が、表示された入力待ちに交互に指し手を入力します。盤上の駒を動かすときは、出発マスと到着マスを筋・段で指定します。

```text
move <出発筋> <出発段> <到着筋> <到着段>
move <出発筋> <出発段> <到着筋> <到着段> +
```

最後の `+` は成りを指定します。例えば、先手の初手は次のように入力します。

```text
move 7 7 7 6
```

持ち駒を打つときは、駒名と打ち先を指定します。

```text
drop <歩|香|桂|銀|金|角|飛> <筋> <段>
```

例えば、歩を５五へ打つ場合は次のように入力します。

```text
drop 歩 5 5
```

区切りと筋・段には半角・全角の空白・数字を使えます。形式または合法性に誤りがある場合は理由を表示し、同じ手番で再入力を求めます。詰みになると勝者を表示して入力を停止します。投了、千日手、持将棋、時間切れなどはまだ扱いません。

入力を終える場合は `Ctrl-D`（EOF）または `Ctrl-C` を入力してください。「入力を終了しました。」と表示して正常終了します。

## テスト

```sh
python3 -m unittest discover -s tests -v
```

座標の検証、駒の不変性、盤面と持ち駒の独立性、局面複製、初期配置の全81マス・枚数・手番、CLI表示、入力解析、全角入力、合法手の再入力、詰み停止、EOF/Ctrl-C、14種の候補の向き・盤外・占有・盤面不変性、王手の全駒種・先後・遮蔽・桂馬・隣接玉・玉なし、局面移動時の所有者照合、駒取り、玉取り拒否、持ち駒の減算、王手放置、自玉の利きへの移動、合い駒、空マスへの駒打ち、二歩、駒打ち失敗時の不変性を確認します。

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

空いている到着マスへの駒の移動は `move_piece(board, source, destination)` で適用します。出発マスの駒を空にし、到着マスへ同じ駒を置きます。出発マスが空、到着マスが占有、出発と到着が同じ場合は `ValueError` となり、盤面は変更されません。移動方向の検証、駒取り、手番更新、成り、王手、合法手判定は対象外です。

```python
from kaname_shogi.model import Square
from kaname_shogi.movegen import move_piece

move_piece(position.board, Square(7, 7), Square(7, 6))
```

手番も含めて局面を進めるときは、`apply_move(position, source, destination, *, promote=False)` を使います。出発駒の所有者と`position.side_to_move`が一致し、既存の移動先候補に含まれる到着マスへ、成り・駒取りを含む移動を試し指しします。試し指し後に自玉が相手の利きに残る場合、`ValueError`となり、盤面・手番・双方の持ち駒は変更されません。安全なら本物の局面へ一度だけ適用し、手番を交代します。`promote=True` は移動元または移動先が敵陣にある歩・香・桂・銀・角・飛でだけ指定でき、歩・香・桂が行き所を失う移動では強制されます。成駒は固有の候補で移動し、成駒種を保ちます。候補に含まれる相手の玉以外の駒を取る場合、取った駒は基本駒種へ戻して指した側の持ち駒に加えます。玉を取ろうとした場合、所有者と手番が違う場合、候補外、成れない成り指定、強制成りでの不成、空の出発マス、自駒のある到着マス、同一マスも`ValueError`となります。詰みと打ち歩詰めは別の範囲です。

```python
from kaname_shogi.model import Square, create_initial_position
from kaname_shogi.movegen import apply_move

position = create_initial_position()
apply_move(position, Square(7, 7), Square(7, 6), promote=False)
# position.side_to_move は Side.GOTE
```

持ち駒を打つときは `apply_drop(position, piece_type, destination)` を使います。`piece_type` は打つ基本駒種というデータ、`destination` は打ち先の筋・段を表す `Square` の値です。成功時は手番側の `Hand` から1枚減り、その側の駒が空マスへ置かれて手番が交代します。玉の指定、0枚の持ち駒、先手・後手いずれかの駒で占有されたマス、二歩、歩・香・桂を行き所のない段へ打つ操作、持ち歩による打ち歩詰めは `ValueError` となり、盤面・手番・双方の持ち駒を変更しません。

```python
from kaname_shogi.model import BasicPieceType, Square, create_initial_position
from kaname_shogi.movegen import apply_drop

position = create_initial_position()
position.sente_hand.add(BasicPieceType.PAWN)
apply_drop(position, BasicPieceType.PAWN, Square(5, 5))
# ５五は先手の歩、先手の持ち駒の歩は0枚、手番は後手
```

打ち歩詰めは持ち歩で解除不能な王手をかける操作だけを拒否します。盤上の歩の移動や歩以外の駒打ちによる詰みは対象外です。駒打ち後に自玉が王手になる手も拒否します。

角は `bishop_move_candidates(board, source)` で調べます。bishopは角、move_candidatesは移動先候補を求める操作です。右前・左前・右後ろ・左後ろの順に各方向を近い順で走査し、空マスと最初の相手駒のマスを候補に含めます。自駒のマスとその先は含めません。先後は出発マスの角から読み、手番には制限されません。出発点が空または角以外なら `ValueError` です。

```python
from kaname_shogi.movegen import bishop_move_candidates

print(bishop_move_candidates(board, Square(5, 5)))
# [Square(file=4, rank=4), Square(file=3, rank=3), ...,
#  Square(file=6, rank=6), Square(file=7, rank=7), ...]
```

候補計算では角や他の駒を動かしたり取ったりしません。成り、馬の縦横1マス、王手、合法手の確定は扱いません。

## 文書

- [第27回：二歩](docs/learning/27-nifu.md)
- [二歩：参照メモ](docs/knowledge/20-nifu.md)
- [二歩の設計](docs/design/15-nifu.md)
- [二歩の実装計画](docs/plans/2026-09-22-nifu.md)

- [第28回：行き所のない駒](docs/learning/28-no-legal-destination-drops.md)
- [行き所のない駒：参照メモ](docs/knowledge/21-no-legal-destination-drops.md)
- [第29回：成り・不成の基礎](docs/learning/29-promotion-and-non-promotion.md)
- [成り・不成の基礎：参照メモ](docs/knowledge/22-promotion-and-non-promotion.md)
- [第30回：成駒の移動](docs/learning/30-promoted-piece-movement.md)
- [成駒の移動：参照メモ](docs/knowledge/23-promoted-piece-movement.md)
- [第31回：王手と合法手判定](docs/learning/31-check-and-legal-moves.md)
- [王手と合法手判定：参照メモ](docs/knowledge/24-check-and-legal-moves.md)
- [王手と合法手判定の設計仕様](docs/plans/2026-09-23-check-and-legal-moves-design.md)
- [王手と合法手判定の実装計画](docs/plans/2026-09-23-check-and-legal-moves.md)
- [第32回：詰み・終局判定](docs/learning/32-checkmate-and-game-end.md)
- [詰み・終局判定：参照メモ](docs/knowledge/25-checkmate-and-game-end.md)
- [詰み・終局判定の設計仕様](docs/plans/2026-09-23-checkmate-and-game-end-design.md)
- [詰み・終局判定の実装計画](docs/plans/2026-09-23-checkmate-and-game-end.md)
- [第34回：CLIでの指し手入力と対局進行](docs/learning/34-cli-gameplay.md)
- [CLIでの指し手入力と対局進行：参照メモ](docs/knowledge/27-cli-gameplay.md)
- [CLIでの指し手入力と対局進行の設計仕様](docs/plans/2026-09-23-cli-gameplay-design.md)
- [CLIでの指し手入力と対局進行の実装計画](docs/plans/2026-09-23-cli-gameplay.md)
- [行き所のない駒の設計](docs/plans/2026-09-22-no-legal-destination-drops-design.md)
- [行き所のない駒の実装計画](docs/plans/2026-09-22-no-legal-destination-drops.md)

- [第26回：持ち駒を打つ基本操作と打ち場所の制限](docs/learning/26-hand-drops.md)
- [持ち駒を打つ：参照メモ](docs/knowledge/19-hand-drops.md)
- [持ち駒を打つ操作の設計](docs/design/14-hand-drops.md)
- [持ち駒を打つ基本操作の実装計画](docs/plans/2026-09-22-hand-drops.md)

- [第25回：駒取りと持ち駒の基礎](docs/learning/25-capture-and-hands.md)
- [駒取りと持ち駒：参照メモ](docs/knowledge/18-capture-and-hands.md)
- [駒取りと持ち駒の設計](docs/design/13-capture-and-hands.md)
- [駒取りと持ち駒の実装計画](docs/plans/2026-09-22-capture-and-hands.md)

- [第24回：移動先候補に合う空マスへだけ移動できること](docs/learning/24-candidate-only-empty-square-move.md)
- [移動先候補に合う空マスへの移動：参照メモ](docs/knowledge/17-candidate-only-empty-square-move.md)
- [移動先候補に合う空マスへの移動の設計](docs/design/12-candidate-only-empty-square-move.md)
- [移動先候補に合う空マスへの移動の実装計画](docs/plans/2026-09-22-candidate-only-empty-square-move.md)
- [第23回：手番に合う駒だけを移動できること](docs/learning/23-turn-ownership.md)
- [手番と駒の所有者：参照メモ](docs/knowledge/16-turn-ownership.md)
- [手番と駒の所有者の設計](docs/design/11-turn-ownership.md)
- [手番と駒の所有者の実装計画](docs/plans/2026-09-22-turn-ownership.md)

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
