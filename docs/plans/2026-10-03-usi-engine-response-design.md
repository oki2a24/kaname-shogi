# USIエンジンとして一手を返す：設計仕様

## 状態

2026-10-03、本人がチャット上の設計案を承認した。仕様書の内容確認は未完了であり、実装・テスト変更は開始していない。作業ブランチは `codex/usi-engine-response`。

## 目的

ShogiHomeで `kaname-shogi` と平手対局する大テーマの第4小テーマとして、既存の局面解析・合法手列挙・弱い一手選択をつなぎ、標準入出力でUSIの一手を返す境界を作る。既存の日本語CLIとは独立させ、プロトコル応答以外の表示を標準出力へ出さない。

## 根拠と確認済み範囲

### USI一次資料

[The Universal Shogi Interface](https://hgm.nubati.net/usi.html) は、USIの原案に将棋所の拡張を加えた説明である。同資料から、本テーマに関係する次の仕様を確認した。

- エンジンとGUIは標準入力・標準出力を使って一行単位で通信する。
- `usi` に対して、エンジンは `id name`、`id author`、`usiok` を返す。
- `isready` に対して `readyok` を返す。
- GUIが `position` で局面を指定し、`go` を送る。エンジンは探索結果として `bestmove` を返す。
- `go infinite` は `stop` を受けるまで探索を続けるモードである。
- 認識しないコマンドやトークンは読み飛ばす扱いが示されている。
- `bestmove resign` と `gameover` は将棋所系の拡張として記載されている。

本テーマでは、停止可能な探索を実装しないため `go infinite` と `go ponder` を通常の `go` として処理しない。`searchmoves`、`depth`、`nodes`、`mate` も検索条件の意味を実装しないため、これらの既知引数を含む `go` は未対応としてエラー終了する。USI資料が読み飛ばすよう示す未知のトークンは引き続き読み飛ばす。合法手がない場合の `bestmove resign` は、上記の拡張を選択して利用する設計である。

### ShogiHomeの使い捨てプローブでの観測

[第54回の学習記録](../learning/54-usi-shogihome-connection-scope.md)に、Mac版ShogiHome 1.28.1と使い捨てプローブで観測した一例を記録した。プローブが受けたコマンドと返答は次のとおり。

```text
usi
setoption name USI_Hash value 32
setoption name USI_Ponder value true
isready
usinewgame
position startpos moves 7g7f
go btime 591199 wtime 600000 byoyomi 30000
```

`usi` にはプローブが識別行と `usiok` を返し、`isready` には `readyok` を返した。`bestmove resign` の後にはShogiHomeが `gameover lose` と `quit` を送った。また、第56回には通常手だけからなる `position startpos moves ...` の複数手の例を記録した。

これらは特定バージョン・特定対局の観測であり、合法な `bestmove` を受けた場合のShogiHomeの応答、未観測の指し手形式、SFEN、エンジンを再利用する複数対局、先読み・停止系の挙動を確認したものではない。USI資料の一般説明と実機一例を、未確認のShogiHome要件の根拠として混同しない。

### 既存実装

- `kaname_shogi.usi_move.parse_usi_move` / `format_usi_move` は、一手表記と局面非依存の `Move` 値を相互変換する。
- `kaname_shogi.usi_position.parse_usi_position` は `position startpos moves <1手以上>` を解析し、合法適用した現在 `Position` を返す。
- `kaname_shogi.movegen.legal_moves(position)` は手番側の合法手を固定順のタプルで返す。
- `kaname_shogi.movegen.choose_weak_move(moves, rng)` は渡された乱数生成器で候補から一手を選び、候補が空なら `None` を返す。
- 既存の `python -m kaname_shogi` は対話型日本語CLIを起動するため、USIの標準出力と分離する。

## 合意した範囲

### 対象

- 既存CLIから独立した `kaname_shogi.usi_engine` モジュールを追加する。
- `run_usi_engine` を同モジュールの公開関数とし、`python -m kaname_shogi.usi_engine` を起動入口とする。
- 起動後の `usi`、`isready`、`setoption`、`usinewgame`、`position`、`go`、`gameover`、`quit` を扱う。
- `position` は既存パーサーと同じ `position startpos moves <1手以上>` に限定する。
- 通常の `go` では時計情報を使わず、合法手選択後すぐ一手を返す。認識済みの検索条件は、実装しないものを診断して終了する。
- 入出力関数を注入可能にし、関数単位のテストと対話型サブプロセステストを自動化する。
- 実対局とShogiHome固有の未確認挙動は後続のロードマップ第5項に残す。

### 対象外

- 既存CLIへのUSIループの追加や、既存CLIとの入出力混在。
- `position startpos` 単独、手順なし局面、`position sfen ...`、SFEN解析。
- `stop`、ponder、`go infinite`、`go ponder`、時間管理、探索。
- USIコマンドを表す独立したコマンド型や、`Position` 以外の独立状態API。
- ShogiHome上での実対局、合法なエンジン応答に対するShogiHome挙動の実証。

コマンドの種類や必要状態が今後増える場合、コマンド型・独立状態APIを導入した方が構造上適切になる可能性が高い。これは次回テーマで現状の拡張範囲を踏まえて再検討し、本テーマで先取りしない。

## 公開境界と処理設計

### 関数と状態

新しい `kaname_shogi.usi_engine` に次の公開関数を設ける。

```python
run_usi_engine(input_fn, output_fn, rng=None) -> None
```

- `input_fn` は一回につき一行を返す関数とする。行末はあってもなくてもよく、入力終了は `EOFError` で表す。
- `output_fn` はUSI応答を一行ずつ受け取る関数とする。渡す文字列に改行は含めない。
- `rng` は省略可能な乱数生成器である。省略時は `run_usi_engine` の開始時に一つ作り、その呼び出し中の全 `go` で共有する。`usinewgame` では作り直さない。テストでは固定seedの生成器を注入できる。
- 最新の `Position` を `run_usi_engine` のローカル状態として保持する。新しい `position` コマンドで置き換える。`usinewgame` では局面を未設定に戻す。
- コマンド型、独立したエンジン状態オブジェクト、履歴APIは今回設けない。

通常の `go` は、保持中の `Position` に対して既存処理を順に呼ぶ。

```text
legal_moves(position)
    → choose_weak_move(moves, rng)
    → format_usi_move(move)
    → bestmove <USI一手>
```

`choose_weak_move` の戻り値が `None` の場合は `bestmove resign` を出力する。選択した手をこの処理内で `Position` に適用しない。後続の局面はGUIから次の `position` として通知される境界とする。

### コマンド別の振る舞い

| 入力 | 処理・応答 |
| --- | --- |
| `usi` | `id name kaname-shogi`、`id author kaname-shogi project`、`usiok` をこの順に出力する。 |
| `isready` | `readyok` を出力する。 |
| `setoption ...` | 読み飛ばし、応答しない。設定項目を宣言する `option` 行も出さない。 |
| `usinewgame` | 保持中の `Position` をクリアする。乱数生成器は維持し、応答しない。 |
| `position startpos moves <1手以上>` | 既存の `parse_usi_position` を呼び、保持局面を返却値に置き換える。 |
| 通常の `go` | `position` で指定済みの局面から既存の合法手・選択・表記関数を使い、選択後すぐ `bestmove` を出す。 |
| 時計引数付き `go` | 時計に関するUSI引数 `btime` / `wtime` / `binc` / `winc` / `byoyomi` / `movestogo` / `movetime` は選択・待機に利用しない。第54回の実機観測で確認したのは `btime` / `wtime` / `byoyomi` のみであり、他の引数をShogiHomeが送るかは未確認。 |
| `go searchmoves ...` / `go depth ...` / `go nodes ...` / `go mate ...` | 検索条件を実装しないため `ValueError` にする。実行入口は診断を標準エラーへ出して処理を終了する。特に `searchmoves` の候補制限を無視して別の手を返さない。 |
| `go infinite` / `go ponder` | 停止・先読みの処理を実装しないため `ValueError` にする。実行入口は診断を標準エラーへ出して処理を終了する。 |
| 手番側の合法手がない `go` | `bestmove resign` を出力する。 |
| `gameover ...` | 読み飛ばし、応答しない。 |
| `quit` | 応答せず終了する。 |
| 未知のコマンド | USI資料の扱いに沿って読み飛ばす。 |
| 入力EOF | 静かに終了する。 |

通常の `go` より前に有効な `position` がない場合、または `position` が既存パーサーで拒否された場合は `ValueError` とする。`searchmoves` / `depth` / `nodes` / `mate` / `infinite` / `ponder` を含む未対応の `go` も同じく `ValueError` とする。公開関数からの例外は実行入口で捕捉し、内容の分かる診断を標準エラーへ出し、非0で終了する。エラー文言そのものは固定契約にしない。

### 標準入出力

`main()` は実際の標準入力・標準出力を `run_usi_engine` に接続する。出力関数は各応答を改行付きで書き、直ちにflushする。標準出力にはUSI応答だけを出す。診断は標準エラーへ出す。テストで注入する `output_fn` には、改行なしの応答一行を一回ずつ渡す。

## 確認方法

実装計画では以下を `unittest` で確認する具体的なテストへ分ける。

- 注入した入力・出力関数で `usi` と `isready` の応答内容・順序を確認する。
- `setoption`、`usinewgame`、未知コマンド、`gameover`、`quit`、EOFの無応答・終了の境界を確認する。
- `position` から `go` への既存処理の接続、時計値を待たずに返すこと、`bestmove` 表記を確認する。
- 空の合法手列に対する `bestmove resign` を確認する。
- run中に乱数生成器を共有し、`usinewgame` で再生成しないことを確認する。
- 未設定局面・不正局面、および `go searchmoves` / `go depth` / `go nodes` / `go mate` / `go infinite` / `go ponder` が `ValueError` となることを確認する。
- 対話型サブプロセスで実際の `python -m kaname_shogi.usi_engine` を起動し、応答を終了前に読み取れることからflushを確認する。標準出力にプロトコル以外が混ざらないこと、およびエラー診断が標準エラーへ出ることも確認する。
- 専用テスト、全 `unittest`、差分検査を行う。ShogiHome GUIでの実対局は行わない。

## 後続の記録

本書は設計仕様であり、個別テスト名・TDDのRed/Green手順・ファイルごとの作業順は別の実装計画に記載する。実装計画は本書の本人レビュー・承認後に作成して提示し、その計画への明示的承認前にコード・テストを変更しない。

実装完了後に、次の記録を実施内容と一致するよう更新または作成する。

- `docs/plans/2026-10-03-usi-engine-response-implementation-plan.md` — 承認済みの別文書として、TDD、Refactor判断、独立レビュー、検証手順を記録。
- `docs/learning/57-usi-engine-response.md` — 本人の回答と補足、USI仕様、実機観測と未確認範囲、設計判断、実装・テスト・レビュー・未解決事項を区別して記録。
- `docs/knowledge/usi-engine-response.md` — USI実行境界、入出力、状態、合法手応答、例外の確定知識を簡潔に記録。
- 関連するREADME、ドキュメント索引、ロードマップ、次回候補 — テーマ完了時に必要箇所を更新する。

## 参照

- [第54回：ShogiHome接続範囲と実機観測](../learning/54-usi-shogihome-connection-scope.md)
- [第55回：USI一手表記](../learning/55-usi-move-notation.md)
- [第56回：USI平手手順からの局面再現](../learning/56-usi-position-replay.md)
- [USI一手表記と内部の一手データ](../knowledge/usi-move-notation.md)
- [USI平手局面再現](../knowledge/usi-position-replay.md)
- [ShogiHome対局ロードマップ](../roadmap-usi-shogihome.md)
- [USI原案と将棋所系拡張の説明](https://hgm.nubati.net/usi.html)
