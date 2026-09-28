# 第46回：コードとユニットテストの構造レビュー

## 目的

`kaname_shogi/` と `tests/` の全14ファイルを読み、次の観点で現在の構造を説明できる状態にする。

- 本体モジュールの責務、公開インターフェース候補、依存方向
- テストの主対象と、併せて保護するモジュール境界
- テストの性質と、境界テストであることの判別しやすさ
- テストから内部実装への直接依存
- 重複の種類と、共通化する場合・しない場合の影響
- 保守上の懸念、現時点で変更不要と判断する根拠、別テーマ候補

今回は構造の調査と記録だけを行う。コード、テスト、公開動作、棋譜JSON形式は変更しない。

設計と実行手順は、次を参照する。

- [設計仕様](../plans/2026-09-28-code-and-unit-test-structure-review-design.md)
- [実装計画](../plans/2026-09-28-code-and-unit-test-structure-review.md)

## 開始時の状態と確認資料

セッション開始時に、過去の引き継ぎを現在状態とみなさず、次を実行して確認した。

```text
$ git status --short --branch
## main...origin/main [ahead 1]

$ git log -3 --oneline
83fb183 docs: 構造レビューの引き継ぎを作成する
04b07e6 docs: 第45回の理解確認を記録する
9cc861c merge: 古い文書記述是正を取り込む
```

その後、目的が分かる作業ブランチ `codex/code-and-unit-test-structure-review` を作成した。設計仕様と実装計画はそれぞれ本人の明示的な承認を得てから次へ進んだ。

開始時に確認した案内・方針文書は次のとおりである。

- `AGENTS.md`
- `README.md`
- `docs/README.md`
- `docs/resume.md`
- `docs/handover-code-and-unit-test-structure-review.md`
- `docs/roadmap-repository-foundation.md`
- `docs/learning/45-stale-document-correction.md`

調査対象は、本体8ファイルとテスト6ファイルの合計14ファイル、7,036行である。

- `kaname_shogi/__init__.py`
- `kaname_shogi/__main__.py`
- `kaname_shogi/cli.py`
- `kaname_shogi/display.py`
- `kaname_shogi/game_record.py`
- `kaname_shogi/model.py`
- `kaname_shogi/move.py`
- `kaname_shogi/movegen.py`
- `tests/test_cli.py`
- `tests/test_display.py`
- `tests/test_game_record.py`
- `tests/test_model.py`
- `tests/test_move.py`
- `tests/test_movegen.py`

## 調査方法

1. 本体8ファイルを起点に、責務、先頭が `_` でない名前、docstring、READMEでの説明、他モジュールからの利用、import方向を照合した。
2. テスト6ファイルの全240テストを、主に検証するモジュールと、併せて保護する境界へ逆引きした。
3. テストの性質を「単体中心」「結合的」「限定的なCLI E2E／スモーク」に分けた。
4. ファイル名、クラス名、テスト名、docstringのどこまで読めば境界テストだと分かるかを確認した。
5. 先頭が `_` の内部名をテストが直接参照する箇所を検索し、公開操作だけで代替できるか、実装変更で壊れることを許容できるかを個別に判断した。
6. 重複を「保守上の重複」「境界をまたぐ類似準備」「意図的に独立させた期待値」に分けた。

依存方向は循環していない。概略は次のとおりである。

```text
model
├── move
├── display
├── movegen ── move
│   └── game_record
└── cli ── display / game_record / move / movegen
    └── __main__
```

## モジュールの責務・公開インターフェースとテスト対応

「公開候補」は、単に先頭が `_` でないという意味だけではない。docstring、README、他モジュールからの利用を合わせて、現在の利用者が呼び出し得る境界として整理した。`__all__` は定義されていない。

| 本体モジュール | 主な責務 | 公開候補 | 主な依存先 | 主なテスト | 併せて保護する境界 | テストの性質 | 判別しやすさ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `kaname_shogi/__init__.py` | パッケージとして認識させる空ファイル | なし。パッケージ直下に明示的な公開APIを再公開していない | なし | 直接対応するテストなし | 各テストのimport成功がパッケージ成立を間接的に保護する | 単体中心の各テストによる間接保護 | 専用テストがないため表を見ないと対応は分かりにくいが、空ファイルに固有動作はない |
| `kaname_shogi/__main__.py` | `python -m kaname_shogi` の実行入口。モード選択と対局開始をつなぎ、EOF・割り込みを正常終了にする | モジュールとして呼ぶ関数はなく、モジュール実行そのものが外部境界 | `cli` | `tests/test_display.py` の `DisplayTests.test_cli_exits_from_game_mode_menu_on_eof` | Pythonのモジュール実行、標準入力、プロセス終了コード、`cli.choose_game_mode` | 限定的なCLI E2E／スモーク | テストメソッド名ではCLI境界と分かるが、`test_display.py` と `DisplayTests` への配置からは分かりにくい |
| `kaname_shogi/model.py` | 手番、駒種、マス、駒、持ち駒、盤、局面、初期局面という中核データと不変条件を表す | `Side`、`PieceType`、`BasicPieceType`、`Square`、`Piece`、`Hand`、`Board`、`Position`、`create_initial_position` | 標準ライブラリのみ | `tests/test_model.py` の `SquareTests`、`BoardTests`、`HandTests`、`PositionHandTests`、`InitialPositionTests` | `move`、`movegen`、`game_record`、`display`、`cli` が共有するデータ契約 | 単体中心 | ファイル名・クラス名から主対象が明確。境界保護は利用側テストまで読むと分かる |
| `kaname_shogi/move.py` | 盤上移動と駒打ちを、副作用を持たない不変な指し手データとして表す | `BoardMove`、`DropMove`、型別名 `Move` | `model` | `tests/test_move.py` の `MoveDataTests` | `movegen.legal_moves` の戻り値と `cli` のコンピュータ着手処理 | 単体中心 | ファイル名・クラス名から主対象が明確。利用境界は `test_movegen.py` と `test_cli.py` で保護される |
| `kaname_shogi/movegen.py` | 駒別移動候補、着手・駒打ちの適用、王手・合法手・詰み・終局判定、合法手列挙、弱い手の選択を担う | `move_piece`、`is_in_check`、`apply_move`、`apply_drop`、`legal_moves`、`choose_weak_move`、`has_legal_move`、`is_checkmate`、`is_game_over`、各駒の `*_move_candidates` | `model`、`move` | `tests/test_movegen.py` の全21クラス | `model` の局面更新契約、`move` の指し手表現、`game_record` の記録前検証、`cli` の対局進行 | 単体中心。ただし実際の `Position` と `Move` を使うためモジュール境界も併せて保護する | ファイル名・クラス名・テスト名から機能群は明確。公開操作と内部補助の境界は末尾の打ち歩詰めテストまで読まないと分かりにくい |
| `kaname_shogi/game_record.py` | 初期局面と着手履歴を保持し、適用、任意手数への再現、JSON保存・読込を行う | `RecordedMove`、`RecordedDrop`、`GameRecord` とその公開メソッド | `model`、`movegen` | `tests/test_game_record.py` の `GameRecordTests` | `movegen` による合法性判定、`model` のコピー独立性、ファイルシステムとJSON形式 | 結合的 | ファイル名・クラス名から主対象は明確。実物の `movegen` とファイル入出力を使う境界もテスト名とdocstringから判別できる |
| `kaname_shogi/display.py` | 局面を日本語の文字列へ描画する純粋な表示変換 | `render_position` | `model` | `tests/test_display.py` の先頭3テスト | `model` の駒種・手番・盤面表現、`cli` の表示出力 | 単体中心 | `DisplayTests` と先頭3テストは明確。ただし同じクラス内のCLIプロセステストは表示責務との区別がつきにくい |
| `kaname_shogi/cli.py` | コマンド解析、対局モード選択、人間・コンピュータの手番進行、表示、保存・読込、終了通知を調停する | `GameMode`、`choose_game_mode`、`parse_command`、`run_game` | `display`、`game_record`、`model`、`move`、`movegen` | `tests/test_cli.py` の `CommandParsingTests`、`GameModeMenuTests`、`GameplayTests` | 入出力関数、乱数、`GameRecord`、合法手生成・詰み判定・表示の協調 | 結合的 | クラス分割により解析・メニュー・進行は明確。`parse_command` が内部コマンド型を返す境界だけは、型定義とテスト本文を読まないと分からない |

クラス内部を含む主な公開操作も確認した。`model` では `Square.to_index`、`Piece.base_piece_type`、`Piece.is_promoted`、`Hand.count`・`add`・`remove`・`copy`、`Board.piece_at`・`set_piece`・`copy`、`Position.copy` が利用境界である。`game_record` では `GameRecord.moves`・`current_position`・`initial_position`、`position_at`、`save`、`load`、`apply_move`、`apply_drop` が公開操作である。

`movegen` の「各駒の `*_move_candidates`」は、`king_move_candidates`、`knight_move_candidates`、`bishop_move_candidates`、`rook_move_candidates`、`lance_move_candidates`、`silver_move_candidates`、`gold_move_candidates`、`pro_pawn_move_candidates`、`pro_lance_move_candidates`、`pro_knight_move_candidates`、`pro_silver_move_candidates`、`pawn_move_candidates`、`horse_move_candidates`、`dragon_move_candidates` を指す。これらは対応する駒別テストから直接利用されるため、現時点では公開候補として扱う。

テスト側から逆引きすると、6ファイルはすべて表の主対象または境界へ対応している。

| テストファイル | テスト数 | 主対象 | 併せて保護する主な境界 |
| --- | ---: | --- | --- |
| `tests/test_model.py` | 25 | `model` | 中核データのコピー独立性と不変条件 |
| `tests/test_move.py` | 2 | `move` | `model` の値を保持する不変な指し手データ契約 |
| `tests/test_movegen.py` | 158 | `movegen` | `model` の局面更新、`move` の列挙結果、打ち歩詰め判定内の再帰境界 |
| `tests/test_game_record.py` | 14 | `game_record` | `movegen` の合法性判定、JSON・ファイル入出力 |
| `tests/test_display.py` | 4 | 先頭3件は `display`、末尾1件は `__main__` | `model` の表示契約と、実プロセスでのCLI起動・終了 |
| `tests/test_cli.py` | 37 | `cli` | `display`、`game_record`、`move`、`movegen`、入力・出力・乱数の協調 |

全テストクラスの逆引きは次のとおりである。

- `tests/test_model.py`: `SquareTests`、`BoardTests`、`HandTests`、`PositionHandTests`、`InitialPositionTests` は、それぞれ `model` の同名データと初期局面を主対象にする。
- `tests/test_move.py`: `MoveDataTests` は `move` の2種類の不変な指し手データを主対象にする。
- `tests/test_movegen.py`: `PromotedMinorMoveCandidateTests`、`HorseMoveCandidateTests`、`DragonMoveCandidateTests`、`KingMoveCandidatesTests`、`KnightMoveCandidatesTests`、`BishopMoveCandidatesTests`、`RookMoveCandidatesTests`、`LanceMoveCandidatesTests`、`SilverMoveCandidatesTests`、`GoldMoveCandidatesTests`、`PawnMoveCandidatesTests` は駒別候補生成、`CheckDetectionTests` は王手判定、`MovePieceTests` は低水準の盤更新、`ApplyMoveTests` と `ApplyDropTests` は局面への合法な適用、`LegalMoveTests` は王の安全を含む合法性、`LegalMoveListTests` と `LegalMoveEnumerationTests` は合法手列挙、`WeakMoveSelectionTests` は弱い手の選択、`CheckmateAndGameEndTests` は詰み・終局、`UchiFuzumeTests` は打ち歩詰めと内部再帰境界を主対象にする。
- `tests/test_game_record.py`: `GameRecordTests` は `game_record` の記録、再生、コピー独立性、保存・読込を主対象にする。
- `tests/test_display.py`: `DisplayTests` の先頭3件は `display`、末尾1件だけは `__main__` の限定的な実行境界を主対象にする。
- `tests/test_cli.py`: `CommandParsingTests`、`GameModeMenuTests`、`GameplayTests` は、それぞれ `cli` の解析、モード選択、対局調停を主対象にする。

## テストから内部実装への依存

検索で確認できた直接依存は次の4分類である。CLIコマンド型への依存は、同じ公開候補 `parse_command` の戻り値境界として3型を一つにまとめた。

| テスト側の参照 | 直接確認していること | 公開操作だけでの代替 | 変更耐性の評価 |
| --- | --- | --- | --- |
| `tests/test_cli.py` → `cli._ResignCommand`、文字列による `cli._SaveCommand`・`cli._LoadCommand` の取得 | `parse_command` が投了・保存・読込を対応する内部コマンド型として解釈し、保存・読込パスを保持すること | `run_game` に3操作を入力すれば最終結果は確認できるが、解析結果を他のコマンドから区別する失敗原因が遠くなる | `parse_command` は公開候補なのに戻り値型が内部名であり、テストだけの問題ではなく公開境界が曖昧。現状は小さい解析器を直接診断する価値があるが、3型いずれの改名・統合でも壊れる |
| `tests/test_movegen.py` → `_apply_drop_unchecked` | 打ち歩詰め検査を行わない駒打ち後の局面を作り、詰み形そのものを確認すること | 公開 `apply_drop` は対象の打ち歩詰めを拒否するため、同じ中間局面を作る用途には使えない。盤と持ち駒を手作業で変えると、別の実装詳細をテスト側で複製する | 打ち歩詰めの分解診断として許容する。ただし内部の段階分けを変更すると壊れる、意図的なホワイトボックステストである |
| `tests/test_movegen.py` → `_apply_drop` | 再帰時に `check_uchi_fuzume=False` を渡した経路を起動すること | 公開 `apply_drop` では常に通常経路から始まり、再帰ガードの引数伝播だけを切り離して確認できない | 無限再帰を防ぐ境界を直接保護するため、現構造では許容する。ガード方式を変える場合は、公開動作が同じでもテストを同時に見直す必要がある |
| `tests/test_movegen.py` → `_has_legal_move` | 上記の再帰経路で合法手探索が終了し、期待結果を返すこと | 公開 `has_legal_move` は通常の打ち歩詰め検査を有効にするため、内部再帰の停止条件だけは指定できない | `_apply_drop` と同じ意図的なホワイトボックステスト。対象3関数は一組の内部プロトコルとして結合している |

内部名への直接依存を一律に禁止する必要はない。打ち歩詰めの3参照は、公開結果だけでは「再帰ガードが効いた」ことと「偶然同じ結果になった」ことを区別しにくいため、局所的な実装依存を受け入れている。一方、`_ResignCommand`、`_SaveCommand`、`_LoadCommand` は公開候補 `parse_command` の戻り値に内部型が現れる設計なので、将来CLIコマンドを拡張するときに境界を先に決め直す余地がある。

## 重複の分類と評価

### 保守上の重複

- `tests/test_movegen.py` では、盤面、持ち駒、手番をタプル化する `_snapshot` が `LegalMoveTests`、`LegalMoveListTests`、`LegalMoveEnumerationTests`、`CheckmateAndGameEndTests`、`UchiFuzumeTests` に同形で置かれている。同じスナップショット項目を増減すると5か所の追従が必要になる。ファイル内のテスト補助へ集約すれば変更箇所を減らせるが、各テストクラスだけ読んだときの自己完結性は少し下がる。
- 同ファイルの `ApplyMoveTests` と `ApplyDropTests` には、持ち駒数を写す `_hand_counts` が重複する。対象は2か所で短く、今すぐ共通化する利益は小さい。
- `cli.py` の表示用 `_PIECE_NAMES` と `parse_command` 内の入力用 `piece_types` は、日本語駒名と型の対応を両方向に保持する。現在は対象が基本駒7種に固定され、入出力テストもあるため変更漏れは検出できるが、駒名表記を変える場合は両方を確認する必要がある。

### 境界をまたぐ類似準備

- `tests/test_cli.py` と `tests/test_movegen.py` は、それぞれ詰み局面を準備する。形は類似するが、前者はCLIが詰み前後で入力・出力を止める境界、後者は合法手と詰み判定そのものを検証する。共有fixtureにすると片方の変更が他方の前提を暗黙に変えるため、現時点では独立させる。
- `tests/test_game_record.py` と `tests/test_cli.py` は実際の `GameRecord` と着手適用を使う。これは重複というより、記録単体とアプリケーション調停という異なる境界から同じ契約を守っている。

### 意図的に独立させた期待値

- `tests/test_model.py` の初期配置81マスは、`create_initial_position` と同じ生成手順を再利用せず、期待する盤面を独立に列挙している。冗長でも実装側の並べ間違いを検出できる。
- `tests/test_display.py` の初期局面全文は、描画実装から期待文字列を組み立てず、利用者が見る完成形を固定している。
- `tests/test_movegen.py` の移動候補順、合法手順、駒打ち順の期待値は、候補生成器や列挙器を使って期待値を作っていない。弱い手の乱数再現性が順序に依存するため、独立した順序期待値を維持する意味がある。
- `move.py` の `BoardMove`・`DropMove` と `game_record.py` の `RecordedMove`・`RecordedDrop` は形が似るが、前者は合法手選択に使う中立なデータ、後者は適用済み履歴である。責務を分ける意図がdocstringにあり、現時点で統合しない。
- `movegen.py` の角・馬、飛車・竜、金・成小駒などには方向走査や占有判定の類似がある。一部は金相当の内部補助で共有済みだが、駒ごとの規則を明示することは学習目的に合う。抽象化を増やすと個々の駒の規則を追う距離が延びるため、変更頻度が上がるまでは現在形を保つ。

## 保守上の懸念

| 対象 | 観察した事実 | 起こり得る変更漏れ | 現在の保護 |
| --- | --- | --- | --- |
| CLIプロセス境界テストの配置 | `__main__.py` を実プロセスで確認する1件が `test_display.py` の `DisplayTests` にある | 入口や終了処理を変更する人が `test_cli.py` だけを探し、このテストを見落とす | テスト名とdocstringは目的を説明し、全テスト実行では検出できる |
| `parse_command` の境界 | 公開候補の関数が `_MoveCommand` など内部型を返し、テストも `_ResignCommand`、`_SaveCommand`、`_LoadCommand` の型名を直接参照する | 内部型の整理が利用可能な戻り値契約の変更になるか判断しづらい | 解析テストと対局進行テストの両方が現在動作を保護する |
| `movegen.py` と `test_movegen.py` の責務密度 | 本体は候補生成、適用、合法性、終局、手選択を持ち、テストは158件・21クラスで一ファイルに集まる | 一つの変更で読む範囲が広くなり、内部補助の変更影響や境界テストの位置を見落としやすい | 機能別テストクラスと詳細な日本語docstringにより、振る舞い単位では検索できる |
| 打ち歩詰めの内部プロトコル | 3つの内部関数と `check_uchi_fuzume` 引数が再帰停止を協調して担う | 内部分割や引数伝播を変えたとき、無限再帰または規則の検査漏れが起こり得る | `UchiFuzumeTests` が公開動作と内部ガードの両方を意図的に確認する |
| `test_movegen.py` のスナップショット補助 | 同形の `_snapshot` が5クラスにある | 状態比較へ項目を足す場合、更新漏れでクラスごとの検出範囲がずれる | 現在の各ヘルパーは盤・持ち駒・手番をすべて比較している |
| CLIの駒名対応 | 出力辞書と入力辞書が別々に定義される | 表記追加・変更時に片方向だけ直す可能性がある | コマンド解析と表示を含むCLIテストが両方向を個別に保護する |

## 変更不要の箇所と根拠

- 空の `__init__.py` に再公開APIを追加しない。現在はライブラリではなく小さなアプリケーションであり、利用箇所は各モジュールから明示的にimportしている。安定したパッケージ直下APIを先に約束する必要がない。
- `game_record.py` の履歴管理とJSON永続化を分割しない。保存形式は一つで、読み書きは `GameRecord` の状態復元という同じ変更理由にまとまり、14テストが成功・失敗・不正入力・再生を一続きで保護している。別形式が必要になる前に抽象層を足すのは先取りになる。
- `test_cli.py` を「単体テストではない」という理由だけで細分化しない。CLIの責務は複数モジュールの調停であり、実際の `GameRecord` と差し替え可能な入出力・乱数を組み合わせる結合的テストが適している。3クラスで解析、メニュー、進行も区切られている。
- テストの期待値を本体ヘルパーから生成しない。重複を減らしても同じ誤りを期待値へ写す危険が増すため、`test_model.py` の初期配置、`test_display.py` の表示全文、`test_movegen.py` の候補順・合法手順は、それぞれ本体実装から独立させる。
- 駒別候補生成を一つの汎用方向テーブルへ全面統合しない。現在の明示的な実装は、各駒の規則を説明できることを優先するプロジェクト目的に合い、駒別テストが対応している。
- 打ち歩詰めの内部参照テストを公開APIだけに置き換えない。現在の再帰ガードは誤ると停止性に影響し、公開結果だけよりも失敗位置を限定できる。ただし内部設計を変える別テーマでは同時に見直す。
- 本格的な対局E2Eを追加しない。実プロセスの入口は限定的なスモークテストで確認し、対局進行は注入可能な入力・出力・乱数を使う `test_cli.py` が決定的に保護している。現時点で実プロセスを通す重い重複を増やす根拠がない。

## 別テーマにする小リファクタリング候補

優先順は、読者が境界を発見しやすくする小さい変更から並べた。いずれも今回は実装しない。

1. **CLI実行入口のスモークテストを専用の配置へ移す**
   - 対象: `tests/test_display.py` の `test_cli_exits_from_game_mode_menu_on_eof`
   - 解消したい懸念: `__main__.py` の境界テストが表示テストに見えること
   - 制約: テスト内容と公開動作を変えず、例えば `tests/test_cli_entrypoint.py` のように目的が一目で分かる配置・クラス名にする
   - 確認: 全240テストと、移動した実プロセステスト
2. **`test_movegen.py` の局面スナップショット補助をファイル内で一つにする**
   - 対象: 5クラスの同形 `_snapshot`
   - 解消したい懸念: 比較対象を変える際の5か所更新
   - 制約: 期待値は本体実装から生成せず、テスト間で共有するのは状態の読み取り方法だけにする
   - 確認: `tests.test_movegen` 全158テスト
3. **CLIコマンド解析の公開境界を設計し直す**
   - 対象: `parse_command` と5つの内部コマンド型
   - 解消したい懸念: 公開候補が内部型を返し、利用者とテストが依存してよい契約が曖昧なこと
   - 制約: 入力文法、対局中の動作、表示を変えない。型を公開するか、解析自体を内部化するかは別テーマの設計で決める
   - 確認: `CommandParsingTests` と `GameplayTests`
4. **CLIの駒名入出力対応を一つの定義から導く**
   - 対象: `_PIECE_NAMES` と `parse_command` 内の `piece_types`
   - 解消したい懸念: 表記変更時の片方向更新漏れ
   - 制約: 表示名、入力可能な駒、順序、エラー文言を変えない
   - 確認: コマンド解析、駒打ち、コンピュータ着手表示の既存テスト

`movegen.py` の分割は、候補生成・局面適用・合法性・終局・手選択という境界候補がある。しかし複数ファイルの公開関係と内部再帰を設計し直すため「小リファクタリング」ではない。まず上記の小さい候補を別テーマとして検討し、実際の変更頻度や学習上の区切りが必要になった時点で、分割そのものを独立した設計テーマにする。

## Refactorの要否

今回のGREENは、対応表、保守上の懸念、変更不要の根拠、必要なら別テーマにする候補を記録することである。調査により候補は見つかったが、現在の振る舞いの誤りや、今回中に直さなければ調査結果が成立しないCritical・Important相当の問題は確認していない。

したがって、今回の変更は文書記録だけとし、コード・テストのリファクタリングは行わない。候補を実施する場合は、一回一テーマで設計、承認、振る舞い不変の検証を改めて行う。

## 独立レビュー

最終文書差分を別レビュアーが読み取り専用で確認した初回結果は、Critical 0件、Important 3件、Minor 1件だった。

- Important: CLI内部依存の調査から `_SaveCommand` と `_LoadCommand` が漏れていた。`_ResignCommand` と合わせた一分類として表、懸念、再開案内を修正した。
- Important: ロードマップで、独立レビュー、main取り込み、取り込み先検証、理解確認より前にテーマ3を完了扱いしていた。進行中へ戻し、実装計画の状態更新指示も修正した。
- Important: 文書索引だけが検証を未完了としていた。検証済みで、独立レビュー以降が未完了という現在状態へ修正した。
- Minor: 変更不要の根拠で期待値の所属が曖昧だった。初期配置、表示全文、候補・合法手順の各テストファイルを明記した。

Critical・Importantを修正し、リンク・書式・不変性を再検証して独立再レビューを行った。再レビュー結果はCritical 0件、Important 1件、Minor 1件だった。

- Important: 実装計画のタスク5とタスク6で、ロードマップを完了へ変える条件が矛盾していた。main取り込み、取り込み先検証、最後の理解確認後という条件へ統一した。
- Minor: 初回レビュー済み・指摘反映済みという状態が、索引、ロードマップ、検証節の一部に反映されていなかった。再レビュー指摘への対応済み・再々レビュー待ちという現在状態へ統一した。

再レビューのCritical・Importantを修正し、リンク・書式・不変性を再検証して独立再々レビューを行った。最終結果はCritical 0件、Important 0件、Minor 0件で、作業ブランチのテーマコミットへ進行可能と判断された。mainへの取り込みは本人の承認後に行う。

## 検証

2026-09-28に、次を確認した。

- ASTによる定義一覧との照合で、8モジュールの先頭が `_` でないクラス・関数と、6テストファイルの全 `unittest.TestCase` クラスに記録漏れなし。
- 対応表と逆引き表に本体8ファイル、テスト6ファイル、主対象、併せて保護する境界、性質、判別しやすさを記録済み。
- 更新対象6文書の相対Markdownリンク194件を検査し、不足なし。
- `git diff --check` 成功。
- `git diff --exit-code main...HEAD -- kaname_shogi tests` と `git diff --exit-code -- kaname_shogi tests` が成功し、コード・テスト差分なし。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` は全240テスト成功（`Ran 240 tests in 0.517s`、`OK`）。
- 独立再々レビュー結果の反映後、`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests` を再実行し、全240テスト成功（`Ran 240 tests in 0.486s`、`OK`）。相対リンク194件、書式、コード・テスト不変性も再確認して成功した。

初回独立レビュー、再レビュー、指摘対応後の独立再々レビューは、この検証結果を現在情報へ反映した文書差分を対象に実施済みである。

## 振り返り

- ファイル名を一対一対応させるだけでは、`game_record` と `movegen`、`cli` と複数モジュールのような本来の境界保護が見えない。「主対象」と「併せて保護する境界」を分けると、重複に見えるテストの役割を説明できた。
- 「境界テスト」という種類を追加するだけでは発見性は上がらない。ファイル名・クラス名・テスト名・docstringのどこで意図が分かるかまで見ることで、`__main__.py` のスモークテスト配置を具体的な懸念として切り出せた。
- 内部実装への依存は、弱いテストの印ではなく、失敗位置や停止性を直接守るために選ぶ場合もある。公開動作だけで代替できるかと、内部変更で壊れる費用を対にして判断する必要がある。

## 次回への問い

### 最後の理解確認

問題：あるテストが一つのモジュールの動作だけでなく複数モジュールの境界も守っている場合、なぜ「テストファイルと本体モジュールを一対一に対応付ける」だけでは不十分で、主対象、併せて保護する境界、さらに名前や配置から意図を判別しやすいかを分けて記録する必要があるか。

本人の回答：境界は複数のファイルが関わり、その関わり方は複雑なため

アシスタントの補足：その通り。境界では複数モジュールの契約と協調が一つの振る舞いを作るため、一対一対応だけでは、どの接続を壊したときにどのテストが検出するかが見えない。主対象と併せて保護する境界を分ければテストの役割を説明でき、名前や配置からの判別しやすさも記録すれば、将来その境界を変更する人が必要なテストを発見しやすくなる。

## main取り込みと取り込み先検証

本人はローカルでmainへマージする方法を選んだ。`codex/code-and-unit-test-structure-review` はmainの `83fb183` から分岐していることを確認し、リモートからの更新がないことを確認した後、mainを `ee06635` へfast-forwardした。

mainで次を確認した。

- 全ユニットテスト：240件成功、失敗0件（`Ran 240 tests in 0.591s`、`OK`）。
- 更新対象6文書の相対リンク194件：すべて解決。
- `git diff --check`：出力なし。
- `83fb183..HEAD` の `kaname_shogi/` と `tests/`：差分なし。
- 取り込み直後の作業ツリー：クリーン。

検証成功後、取り込み済みの `codex/code-and-unit-test-structure-review` ブランチを削除した。

## 未解決事項

- 別テーマ候補のどれを次に選ぶかは未決定である。今回の結果とプロジェクト全体の候補を小さい順で提示し、本人が選ぶまで新テーマへ進まない。
- `movegen.py` の将来の分割境界は未決定である。現時点では分割を前提にしない。
