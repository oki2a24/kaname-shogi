# 第36回：棋譜・局面の保存 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** CLI対局の成功手と現在局面をメモリ上で保持し、開始局面から任意の手数までの局面を再現できるようにする。

**アーキテクチャ:** 新しい `GameRecord` が開始局面・現在局面・不変の指し手値を保持し、既存の `apply_move` / `apply_drop` に合法性判定を委譲する。`Position` に履歴を混在させず、CLIは記録を経由して対局を進め、終了時に記録を返す。

**技術スタック:** Python 3、標準ライブラリ（`dataclasses`、`typing`、`unittest`）

**仕様 (Spec):** [第36回：棋譜・局面の保存 設計仕様](2026-09-23-game-record-and-position-save-design.md)

**グローバル制約 (Global Constraints):**

- 説明・学習記録・知識メモは日本語で書く。
- 公開インターフェースのdocstringに引数・戻り値・副作用・前提条件と設計理由を記録する。
- 英語の型名やメソッド名は、日本語の意味と「データか操作か」を併せて説明する。
- テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞い、続く本文に検出したい誤りや背景を書く。
- 実装対象は開始局面、成功した盤上移動・駒打ちの履歴、現在局面、任意手数の局面再現だけとする。
- ファイル保存・読み込み、時間、CLIの履歴表示・保存コマンド、投了・EOF・Ctrl-Cの履歴化、千日手、SFEN、USIは実装しない。
- 合法な `move` / `drop` が成功した直後だけ記録を更新し、失敗時は開始局面・現在局面・履歴を変更しない。
- `run_game` は記録を作成して使い、詰み・投了・EOF・Ctrl-Cのいずれで終わっても記録を返す。
- コミットメッセージは日本語のConventional Commitにする。

---

## ファイル構成

| ファイル | 責務 |
| --- | --- |
| `kaname_shogi/game_record.py` | 局面を変更する既存操作を使い、開始局面・現在局面・成功手を一貫して保持・再現する。 |
| `tests/test_game_record.py` | `GameRecord` の履歴、失敗時不変性、複製独立性、局面再現を単体で確認する。 |
| `kaname_shogi/cli.py` | CLIの盤上移動・駒打ちを記録へ委譲し、終了時に記録を返す。 |
| `tests/test_cli.py` | CLIの戻り値の記録内容と、既存の投了・EOF等の進行を確認する。 |
| `docs/learning/36-game-record-and-position-save.md` | 一次資料、確認問題、設計、TDD、レビュー、検証、理解確認を記録する。 |
| `docs/knowledge/29-game-record-and-position-save.md` | 保存対象・不変条件・今回の対象外を簡潔に参照可能にする。 |
| `README.md` / `docs/02-project-direction.md` / `docs/next-topics.md` / `docs/resume.md` | 実装完了後の到達点・次候補・再開案内を更新する。 |

## タスク1：対局記録の履歴と更新

**ファイル:**

- 作成: `tests/test_game_record.py`
- 作成: `kaname_shogi/game_record.py`

**インターフェース (Interfaces):**

- 消費 (Consumes): `Position.copy() -> Position`、`apply_move(position, source, destination, *, promote=False) -> None`、`apply_drop(position, piece_type, destination) -> None`
- 生産 (Produces): `RecordedMove`、`RecordedDrop`、`GameRecord(initial_position: Position)`、`GameRecord.apply_move(source: Square, destination: Square, *, promote: bool = False) -> None`、`GameRecord.apply_drop(piece_type: BasicPieceType, destination: Square) -> None`、`GameRecord.moves -> tuple[RecordedMove | RecordedDrop, ...]`

- [x] **ステップ1: 失敗する対局記録テストを作成**

`tests/test_game_record.py` に、初期局面から先手の７七歩→７六歩、後手の３三歩→３四歩を記録し、順番・値・現在手番を確認するテストを書く。持ち駒を追加した小局面では歩打ちも成功させ、`RecordedDrop` が履歴へ追加されることを確認する。さらに不正な移動の後、履歴と現在局面が変わらないことを確認する。

```python
record = GameRecord(create_initial_position())
record.apply_move(Square(7, 7), Square(7, 6))
record.apply_move(Square(3, 3), Square(3, 4))

self.assertEqual(record.moves, (
    RecordedMove(Square(7, 7), Square(7, 6), False),
    RecordedMove(Square(3, 3), Square(3, 4), False),
))
self.assertEqual(record.current_position.side_to_move, Side.SENTE)
```

- [x] **ステップ2: Redを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_game_record -v`

期待値: テスト側で未実装モジュールを捕捉し、テスト収集時の読み込みエラーではなく「GameRecordの対局記録機能が未実装です」というAssertionErrorで3件が失敗する。読み込みエラーだけを機能のRedとは扱わない。

- [x] **ステップ3: 最小の対局記録実装を作成**

`kaname_shogi/game_record.py` に凍結データクラス `RecordedMove` と `RecordedDrop`、可変の `GameRecord` を実装する。コンストラクタは開始局面を複製し、現在局面も別の複製として保持する。各適用操作は既存の局面操作を現在局面へ先に実行し、成功後だけ履歴リストへ該当値を追加する。

```python
@dataclass(frozen=True)
class RecordedMove:
    """盤上移動の履歴を表す不変のデータ。"""
    source: Square
    destination: Square
    promote: bool


class GameRecord:
    def apply_move(self, source: Square, destination: Square,
                   *, promote: bool = False) -> None:
        apply_move(self._current_position, source, destination,
                   promote=promote)
        self._moves.append(RecordedMove(source, destination, promote))
```

公開プロパティ `moves` は変更できないタプルを返す。全公開インターフェースのdocstringに、引数・戻り値・副作用・例外・開始局面からの経過を保持する理由を日本語で記す。

- [x] **ステップ4: Greenを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_game_record -v`

期待値: タスク1で追加した、成功手だけが順序どおり履歴化され、失敗時に履歴・現在局面が不変であるテストがすべてPASSする。

- [ ] **ステップ5: タスク1をコミットする**

```bash
git add kaname_shogi/game_record.py tests/test_game_record.py
git commit -m "feat: 対局記録に指し手履歴を追加する"
```

## タスク2：局面複製の独立性と任意手数の再現

**ファイル:**

- 変更: `tests/test_game_record.py`
- 変更: `kaname_shogi/game_record.py`

**インターフェース (Interfaces):**

- 消費 (Consumes): タスク1の `GameRecord`、`RecordedMove`、`RecordedDrop`
- 生産 (Produces): `GameRecord.initial_position -> Position`、`GameRecord.current_position -> Position`、`GameRecord.position_at(move_count: int) -> Position`

- [x] **ステップ1: 失敗する再現・複製テストを作成**

開始局面と現在局面のプロパティで受け取った局面を手動変更しても、記録から再取得した局面が変わらないことを確認する。2手の履歴で `position_at(0)`、`position_at(1)`、`position_at(2)` を比較し、各時点の駒位置・手番を確認する。`-1` と履歴長より大きい値が `ValueError` となることも確認する。

```python
first_position = record.position_at(1)
self.assertEqual(first_position.board.piece_at(Square(7, 6)),
                 Piece(PieceType.PAWN, Side.SENTE))
self.assertEqual(first_position.side_to_move, Side.GOTE)

with self.assertRaisesRegex(ValueError, "手数"):
    record.position_at(3)
```

- [x] **ステップ2: Redを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_game_record -v`

期待値: `initial_position`、`current_position`、`position_at` が未実装である、または複製を返さず再現範囲を検証しないため、新しい振る舞いテストがFAILする。

- [x] **ステップ3: 最小の再現・複製実装を追加する**

局面プロパティは内部局面の `copy()` を返す。`position_at` は手数の型を `int` とし、`0 <= move_count <= len(self._moves)` を満たさなければ「手数」を含む `ValueError` を送出する。開始局面の複製から履歴を先頭順に適用し、型により盤上移動・駒打ちを分岐して適用する。

```python
def position_at(self, move_count: int) -> Position:
    if type(move_count) is not int or not 0 <= move_count <= len(self._moves):
        raise ValueError("手数は履歴の範囲で指定してください")
    position = self._initial_position.copy()
    for move in self._moves[:move_count]:
        if isinstance(move, RecordedMove):
            apply_move(position, move.source, move.destination,
                       promote=move.promote)
        else:
            apply_drop(position, move.piece_type, move.destination)
    return position
```

`current_position` は再現結果を毎回計算せず、成功時に更新済みの内部局面の複製を返す。これにより、現在表示の責務と任意手数再現の学習目的を分ける。

- [x] **ステップ4: Greenを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_game_record -v`

期待値: タスク1・2の全テストがPASSし、外部から返された局面の変更が記録に影響せず、任意手数の局面が開始局面から再現される。

- [x] **ステップ5: Refactor要否を確認してコミットする**

履歴の再適用分岐は `position_at` にだけ存在し、現在局面更新は盤上移動・駒打ちの公開操作がそれぞれ異なるため、今回の抽出は行わない。公開APIを増やさず、処理の責務も分かれていることを学習記録へ残す。

```bash
git add kaname_shogi/game_record.py tests/test_game_record.py
git commit -m "feat: 対局記録から局面を再現する"
```

## タスク3：CLIからの記録利用と戻り値

**ファイル:**

- 変更: `tests/test_cli.py`
- 変更: `kaname_shogi/cli.py`

**インターフェース (Interfaces):**

- 消費 (Consumes): `GameRecord(initial_position: Position)`、`GameRecord.current_position -> Position`、`GameRecord.apply_move(...) -> None`、`GameRecord.apply_drop(...) -> None`
- 生産 (Produces): `run_game(*, input_fn: Callable[[], str] = input, output_fn: Callable[[str], None] = print) -> GameRecord`

- [x] **ステップ1: 失敗するCLI記録テストを作成**

既存のゲーム進行テストで `run_game` の戻り値を受け取り、2手の `move` の後にEOFとなった記録の履歴と現在局面を確認する。投了時の戻り値は空の履歴で、開始局面と同じ局面を再現できることを確認する。駒打ちテストでは戻り値の履歴が `RecordedDrop` となることを確認する。

```python
record = cli.run_game(input_fn=ScriptedInput([
    "move 7 7 7 6", "move 3 3 3 4",
]), output_fn=outputs.append)

self.assertEqual(len(record.moves), 2)
self.assertEqual(record.current_position.side_to_move, Side.SENTE)
```

- [x] **ステップ2: Redを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v`

期待値: 既存の `run_game` は `None` を返すため、戻り値の `moves` を確認する新しいテストが属性不足としてFAILする。既存テストはこの時点で維持される。

- [x] **ステップ3: 最小のCLI接続を実装する**

`cli.py` で `GameRecord` をインポートし、初期局面から一度だけ作る。`_apply_command` は `Position` ではなく `GameRecord` を受け、対応する記録操作を呼ぶ。`run_game` の表示・詰み判定・投了表示には `record.current_position` を使い、すべての終了分岐で同じ `record` を返す。

```python
record = GameRecord(create_initial_position())
while True:
    position = record.current_position
    if is_game_over(position):
        output_fn(_checkmate_message(position.side_to_move))
        return record
    # ...
```

`run_game` と `_apply_command` のdocstringを更新し、戻り値が対局記録であること、投了・EOF・Ctrl-Cは履歴に含めないことを明記する。入力形式、エラーメッセージ、投了・詰みの優先順位を変更しない。

- [x] **ステップ4: Greenを確認する**

実行: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v`

期待値: 新規の戻り値テストと既存のCLIテストがすべてPASSし、形式・合法性エラー、投了、詰み、EOF、Ctrl-Cの既存表示が維持される。

- [x] **ステップ5: タスク3をコミットする**

```bash
git add kaname_shogi/cli.py tests/test_cli.py
git commit -m "feat: CLIから対局記録を返す"
```

## タスク4：全体確認、独立レビュー、記録

**ファイル:**

- 作成: `docs/learning/36-game-record-and-position-save.md`
- 作成: `docs/knowledge/29-game-record-and-position-save.md`
- 変更: `README.md`
- 変更: `docs/02-project-direction.md`
- 変更: `docs/next-topics.md`
- 変更: `docs/resume.md`

**インターフェース (Interfaces):**

- 消費 (Consumes): タスク1〜3の実装、ユーザーの確認問題への回答、実行済みの検証・レビュー結果
- 生産 (Produces): 学習記録、知識メモ、更新済みの到達点と次テーマ候補

- [x] **ステップ1: 対象・全体・実CLIを検証する**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_game_record -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
printf 'move 7 7 7 6\nresign\n' | PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi
git diff --check
```

期待値: 新規・既存の全テストがPASSし、実CLIは先手の７六後に後手投了を表示して終了し、差分チェックは出力なし。

- [x] **ステップ2: 独立コードレビューを実施する**

仕様書、実装、テスト、`git diff` を実装時の判断から独立して確認した。初回レビューはCritical 0件、Important 0件、Minor 1件で、境界テストを追加した。再レビューはCritical 0件、Important 0件、Minor 3件でマージ可と評価された。残ったMinorは追加の回帰テスト候補として採否理由を学習記録へ残す。

- [x] **ステップ3: 学習記録と知識メモを作成・更新する**

一次資料の出典、全5問の本人回答と補足、承認日、実際のTDDのRed/Green/Refactor、レビュー結果、検証コマンドと実測結果、対象外、次回候補を日本語で記録する。実施していない手順を実施済みと書かない。

- [x] **ステップ4: 文書を確認してコミットする**

```bash
git add README.md docs/02-project-direction.md docs/learning/36-game-record-and-position-save.md docs/knowledge/29-game-record-and-position-save.md docs/next-topics.md docs/resume.md
git diff --cached --check
git commit -m "docs: 第36回の学習記録を追加する"
```

- [ ] **ステップ5: mainへの取り込み前に承認を求める**

作業ブランチ、コミット一覧、レビュー結論、全検証の実測結果、取り込み予定を提示し、本人の明示承認を待つ。承認前に `main` を変更しない。

- [ ] **ステップ6: 承認後にmainへ取り込み、取り込み先で再検証する**

```bash
git switch main
git merge --ff-only codex/game-record-and-position-save
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git status --short --branch
```

期待値: `main` が作業ブランチの変更をfast-forwardで取り込み、全テストがPASSし、追跡対象の未コミット変更がない。

- [ ] **ステップ7: 最後の理解確認を一問だけ出し、回答を記録する**

質問例: 「なぜ現在局面だけを保存するのではなく、開始局面と成功手の履歴から `position_at` で再現できるようにしたのか。」本人の回答を待ち、補足とともに学習記録へ追記して日本語のConventional Commitでコミットする。その後に次テーマ候補を小さい順で提示し、本人が選ぶまで新しい学習・実装を開始しない。

## 計画の自己レビュー

- 仕様の保存対象、更新時機、再現範囲、CLIとの関係、SFEN/USI除外を全タスクへ対応付けた。
- `TBD`、`TODO`、未定義の作業名を置かず、公開型・メソッド・検証コマンドを明記した。
- タスク2以降が使う `GameRecord`・履歴値・プロパティをタスク1で定義し、CLIが使うインターフェースをタスク3で明記した。
- 検証コマンドはプロジェクトの標準ライブラリ構成と既存のテスト実行方法に合わせた。
