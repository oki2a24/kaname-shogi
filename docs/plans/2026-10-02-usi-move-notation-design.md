# USI指し手表記と内部の一手の対応：設計仕様

## 状態

会話内の設計案は2026-10-02に本人が承認した。本書は仕様書としてのレビュー待ちであり、実装の承認や実装計画の承認を表さない。製品コードとテストは未変更。

## 目的

ShogiHomeで平手対局する大テーマの第2小テーマとして、USIの一手トークンと既存の中立な一手データ Move を対応づける。後続テーマで position の指し手履歴を読み込み、合法な手を bestmove として返す土台にする。

USIの形式は一次資料で確認する。第54回の実機観測 position startpos moves 7g7f は一例として扱い、通常移動・成り・駒打ちの規則全体は一次資料を根拠にする。

## 合意した範囲

### 対象

- 通常の盤上移動、成りを伴う盤上移動、駒打ちのUSI一手トークンを Move 値へ変換する。
- BoardMove / DropMove の値をUSI一手トークンへ変換する。
- 盤上の筋・段、成り指定、駒種記号を既存の Square / BasicPieceType に対応づける。
- 不正な一手表記と表記できない Move 値は ValueError とする。
- 玉打ち表記は変換時に拒否する。
- 変換APIはUSI専用モジュールで公開し、Move の値型はUSIに依存させない。
- 単体テストで表記の種類、座標境界、往復変換、不正入力を確認する。

### 対象外

- position コマンド全体の解析、startpos / sfen の局面解釈、複数手の局面再現
- 指し手の局面適用、合法手判定、手番・持ち駒・盤面の検証
- USI標準入出力ループ、go / bestmove の通信、ShogiHome上の実対局
- CLIの move / drop 入力形式、棋譜保存形式、SFENの変換
- 検索・評価・手の選択

## 根拠と既存データ

- 将棋所の説明は、筋を1〜9、段をa〜iで表し、1段をaとする。通常移動は出発マスと到着マスの連結、成りは末尾の +、駒打ちは大文字の駒記号・*・打ち先である。
- USI原案も座標例として 1a を右上、9i を左下とし、通常移動、成り、駒打ちの各表記を示している。持ち駒欄に現れる駒種は飛・角・金・銀・桂・香・歩の7種で、玉は含まれない。
- 第54回にShogiHomeから届いた実機例は position startpos moves 7g7f である。この実機例は一次資料の一般書式とは別の証拠として記録する。
- kaname_shogi.model.Square(file, rank) は筋と段をそれぞれ1〜9で保持する不変の値である。file=1は右端、rank=1は上端。
- kaname_shogi.model.BasicPieceType は基本駒種8種類を表す列挙値である。玉は持ち駒にならない。Hand は持ち駒の枚数を保持する可変データ、movegen.apply_drop は局面へ駒打ちを適用する操作であり、どちらも玉を拒否する。
- kaname_shogi.move.BoardMove は source / destination / promote を持つ不変の盤上移動データである。DropMove は piece_type / destination を持つ不変の駒打ちデータである。Move は両者をまとめる型別名である。どの型も局面を変更しない。

## 表記と内部値の対応

### 座標

USIのマスは筋の数字と段の英字を連結する。マス表記の数字を Square.file に、a〜i の文字を rank 1〜9 に対応させる。

| USI段 | 内部の段 |
| --- | ---: |
| a | 1 |
| b | 2 |
| c | 3 |
| d | 4 |
| e | 5 |
| f | 6 |
| g | 7 |
| h | 8 |
| i | 9 |

例：7g は Square(7, 7)、7f は Square(7, 6)。したがってUSIの 7g7f は BoardMove(Square(7, 7), Square(7, 6), promote=False) に対応する。1a と 9i はそれぞれ Square(1, 1) と Square(9, 9)。

### 盤上移動と成り

通常移動は出発マスと到着マスの二つを続けて書く。末尾に + があれば BoardMove.promote=True、なければ False とする。例として 7g7f は不成指定の通常移動、8h2b+ は成りを指定した盤上移動である。

BoardMove には移動する駒種と局面が含まれない。この変換では、移動先、駒の動き、所有者、成れる駒かどうか、成りを選べる局面かどうかを判定しない。局面依存の判定は後続の指し手適用・USI局面処理側の責務とする。

### 駒打ち

USIの駒打ちは、基本駒種の大文字記号、*、打ち先のマスを続けて書く。次の7種を対応させる。

| USI記号 | 内部データ | 日本語名 |
| --- | --- | --- |
| P | BasicPieceType.PAWN | 歩 |
| L | BasicPieceType.LANCE | 香 |
| N | BasicPieceType.KNIGHT | 桂 |
| S | BasicPieceType.SILVER | 銀 |
| G | BasicPieceType.GOLD | 金 |
| B | BasicPieceType.BISHOP | 角 |
| R | BasicPieceType.ROOK | 飛 |

例：P*5e は DropMove(BasicPieceType.PAWN, Square(5, 5)) に対応する。玉を示す K*... は対応する DropMove にできないため ValueError とする。駒を実際に持っているか、打ち先が空か、二歩や行き所のない駒でないか、自玉が安全か、打ち歩詰めでないかは確認しない。

## APIと依存関係

新しい kaname_shogi.usi_move モジュールに次の名前付き関数を設ける。

- parse_usi_move(text: str) -> Move
- format_usi_move(move: Move) -> str

parse_usi_move は単独のUSI一手トークンを読み、BoardMove または DropMove を返す。format_usi_move はそのいずれかの値を一手トークンへ変換する。両関数は入力値と出力値だけを扱う純粋な変換操作で、局面・持ち駒・手番を変更しない。

入力関数は一手トークンだけを受け取る。position などのコマンド接頭辞や複数手列、周囲の空白はこの関数の対象に含めず、不正形式として扱う。記号の大小文字はUSI表記どおりに扱う。

kaname_shogi.usi_move から直接importできる公開名とする。kaname_shogi.__init__ からは再exportしない。BoardMove / DropMove の公開データや Square / BasicPieceType にUSI固有の属性・変換メソッドを追加せず、値型の中立性を保つ。

不正なトークン、未対応の駒記号、玉打ち、形式化できない値は ValueError とする。例外メッセージの文言は公開契約に含めず、利用者が例外型で失敗を判定できるようにする。format_usi_move は Move の二つの構成型と、各フィールドが型の契約を満たす値を受け取る。構成型以外、盤上座標が Square でない値、promote が bool でない値、玉を含む打ち駒種など、USI表記へ変換できない値は ValueError とする。

## 確認方法

新しい tests/test_usi_move.py に標準ライブラリ unittest の単体テストを追加する。

- 通常移動をUSI表記とBoardMoveの間で確認する。
- 成り指定の末尾 + と promote 値の対応を確認する。
- 7種の駒打ち記号をそれぞれ確認する。
- 1a と 9i を含む境界座標の読取と出力を確認する。
- 各表記種別について parse_usi_move と format_usi_move の往復対応を確認する。
- 空文字、長さ不足・余分な文字、筋0 / 10、段a〜i以外、誤った大小文字、未知の駒記号、* と + の位置違い、玉打ちを ValueError として確認する。
- format_usi_move に渡された未対応オブジェクトや型契約に反する値が ValueError になることを確認する。

既存の tests/test_move.py はBoardMove / DropMoveそのものの値と不変性を検証しているため変更せず、USI変換の責務は専用テストへ分ける。個別テスト、全テスト、差分検査を行う。ShogiHomeとの結合確認は後続テーマで行う。

実装時に予定する確認コマンド：

    python3 -m unittest tests.test_usi_move -v
    python3 -m unittest discover -s tests -v
    git diff --check

## 記録と承認手順

- 学習経緯、USI資料の要点、本人が選んだ範囲、実装・検証結果、独立レビュー、未解決事項は docs/learning/55-usi-move-notation.md に記録する。
- USI表記と内部値の確定対応を参照メモにする価値がある場合、docs/knowledge/ に別途短い知識メモを追加する。
- この設計仕様書のレビューと承認後に、実装手順・TDDのRed/Green・検証・レビュー方法を含む実装計画を作成して提示する。実装計画への明示的な承認後にのみ、テスト・製品コードを変更する。
- 実装完了後はRefactor要否を確認し、独立コードレビューを行い、Critical / Important / Minorの結論を学習記録へ残す。
- 学習記録・知識メモは内容を提示・確認してから日本語のConventional Commitで記録する。

## 参照資料

- [将棋所：USIプロトコルとは](https://shogidokoro2.stars.ne.jp/usi.html) — マスの表記、指し手表記、コマンドとの関係を確認した。
- [The Universal Shogi Interface (USI), original description](https://hgm.nubati.net/usi.html) — USI原案の座標、通常移動・成り・駒打ち、持ち駒の駒種を確認した。
- [第54回学習記録](../learning/54-usi-shogihome-connection-scope.md) — ShogiHomeで観測した position startpos moves 7g7f の証拠。
- [ShogiHome対局ロードマップ](../roadmap-usi-shogihome.md) — 第2小テーマの範囲と後続テーマ。
- [move.py](../../kaname_shogi/move.py)、[model.py](../../kaname_shogi/model.py) — 既存の値型と座標境界。
