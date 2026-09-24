# 棋譜・局面のファイル保存 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された subagent-driven-development スキル（推奨）または executing-plans スキルを起動して使用してください。ステップには追跡用のチェックボックスを使用します。

**目標:** GameRecord の開始局面と成功手を専用JSONへ保存し、読込時に既存の合法手適用で検証・再現できるようにする。

**アーキテクチャ:** 保存・読込の公開操作は記録の意味を持つ GameRecord に置く。JSON変換・値検証は同モジュール内の非公開ヘルパーに分け、読込は新しい GameRecord を構築して履歴を再適用する。CLIは変更しない。

**技術スタック:** Python 3.9、標準ライブラリ（json、pathlib、typing、tempfile、unittest）

**仕様 (Spec):** docs/plans/2026-09-24-game-record-file-save-design.md

**グローバル制約 (Global Constraints):**

- Python 3.9で動作し、外部パッケージを追加しない。
- JSONは専用の kaname-shogi-game-record-v1 形式とし、SFEN・USIは実装しない。
- 保存対象は開始局面（盤上駒・双方の持ち駒・手番）と成功した move / drop の履歴だけであり、現在局面は保存しない。
- GameRecord.save(path) と GameRecord.load(path) は明示的な呼び出し側だけが使い、CLIの自動保存・save / load コマンドは追加しない。
- 不正な保存内容・不正JSON・不合法な履歴は ValueError、ファイルの不存在・権限・入出力失敗は OSError とする。
- 読込失敗時は既存の GameRecord を変更しない。保存時はJSON値への全変換が終わるまで出力ファイルを開かない。
- 公開APIのdocstringには引数、戻り値、副作用、例外、前提条件と設計理由を日本語で記録する。
- テストメソッド名は英語にし、日本語docstringで振る舞いと検出したい誤りを説明する。
- 実装後は独立コードレビューを行い、Critical・Important・Minorと対応を学習記録へ残す。

---

## 確定するJSON形式

保存するJSONは次の形に固定する。キー順は読込条件にしないが、saveは ensure_ascii=False、indent=2、末尾改行付きで出力する。

~~~json
{
  "format": "kaname-shogi-game-record-v1",
  "initial_position": {
    "side_to_move": "SENTE",
    "pieces": [
      {"file": 7, "rank": 7, "piece_type": "PAWN", "side": "SENTE"}
    ],
    "hands": {
      "SENTE": {"PAWN": 1},
      "GOTE": {}
    }
  },
  "moves": [
    {
      "kind": "move",
      "source": {"file": 7, "rank": 7},
      "destination": {"file": 7, "rank": 6},
      "promote": false
    },
    {
      "kind": "drop",
      "piece_type": "PAWN",
      "destination": {"file": 5, "rank": 5}
    }
  ]
}
~~~

- format は文字列 kaname-shogi-game-record-v1 と完全一致しなければならない。
- side_to_move と盤上駒の side は SENTE または GOTE、盤上駒の piece_type は14種の PieceType.name、持ち駒と駒打ちの piece_type は玉以外7種の BasicPieceType.name とする。
- pieces は Square(file, rank) の昇順（筋、段）で出力する。各マスは高々1回だけ現れ、筋・段は type(value) is int かつ1〜9とする。
- hands は必ず先手・後手を持ち、各側は枚数が1以上の玉以外の基本駒種だけをキーに持つ。枚数は type(value) is int かつ1以上とする。保存で0枚は出力せず、読込では0枚・未知の駒種・玉を拒否する。
- moves の各要素は kind が move または drop。move は source、destination、promote（厳密にbool）だけ、drop は piece_type、destination だけを持つ。余分・不足キーは拒否する。
- 各オブジェクトは列挙したキーだけを持つ。boolを座標・枚数として受理しない。

## ファイル構成

- 変更: kaname_shogi/game_record.py — GameRecord.save / GameRecord.load、JSON変換・厳密なJSON値検証を追加する。
- 変更: tests/test_game_record.py — 一時ディレクトリを使う往復保存、JSON表現、読込失敗、既存記録の独立性を検証する。
- 変更: README.md — JSON保存・読込の最小使用例、CLIが自動保存しないこと、SFEN・USIが対象外であることを追記する。
- 作成: docs/learning/37-game-record-file-save.md — 一次資料、確認問題、設計、TDD、レビュー、検証、理解確認を記録する。
- 作成: docs/knowledge/30-game-record-file-save.md — 形式、保存対象、例外境界、対象外を参照用に記録する。

### タスク1: JSON保存の公開操作

**ファイル:**

- 変更: kaname_shogi/game_record.py:1-141
- テスト: tests/test_game_record.py:1-195

**インターフェース (Interfaces):**

- 消費 (Consumes): GameRecord.initial_position、GameRecord.moves、Position、Board.piece_at、Hand.count、Square、PieceType.name、BasicPieceType.name。
- 生産 (Produces): GameRecord.save(path: Union[str, Path]) -> None。開始局面と履歴だけを kaname-shogi-game-record-v1 のJSONへ書き出す。非公開 _record_to_payload(record) -> dict を生産する。

- [ ] **ステップ 1: 失敗する保存テストを作成**

tests/test_game_record.py に TemporaryDirectory、Path、json のimportを追加し、通常移動・成り・駒打ちを含む記録を保存するテストを追加する。getattr(record, "save", None) が None なら self.fail("GameRecordのJSON保存操作が未実装です") として、存在しないAPIによるERRORをRed完了と扱わない。

~~~python
def test_saves_initial_position_and_recorded_moves_as_json(self):
    """開始局面と成功手を固定文字列のJSONへ保存する。

    現在局面やEnumの内部番号を保存してしまう誤り、通常移動・成り・駒打ちの
    いずれかを履歴から落とす誤りを検出する。
    """
    board = Board()
    board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
    board.set_piece(Square(5, 1), Piece(PieceType.KING, Side.GOTE))
    board.set_piece(Square(2, 2), Piece(PieceType.PAWN, Side.SENTE))
    position = Position(board, Side.SENTE)
    position.sente_hand.add(BasicPieceType.PAWN)
    position.gote_hand.add(BasicPieceType.PAWN)
    record = GameRecord(position)
    record.apply_move(Square(2, 2), Square(2, 1), promote=True)
    record.apply_drop(BasicPieceType.PAWN, Square(4, 4))

    save = getattr(record, "save", None)
    self.assertIsNotNone(save, "GameRecordのJSON保存操作が未実装です")
    if save is None:
        return
    with TemporaryDirectory() as directory:
        path = Path(directory) / "record.json"
        save(path)
        payload = json.loads(path.read_text(encoding="utf-8"))

    self.assertEqual(payload["format"], "kaname-shogi-game-record-v1")
    self.assertEqual(payload["initial_position"]["side_to_move"], "SENTE")
    self.assertIn({"file": 2, "rank": 2, "piece_type": "PAWN",
                   "side": "SENTE"}, payload["initial_position"]["pieces"])
    self.assertEqual(payload["initial_position"]["hands"]["SENTE"],
                     {"PAWN": 1})
    self.assertEqual(payload["initial_position"]["hands"]["GOTE"],
                     {"PAWN": 1})
    self.assertEqual(payload["moves"], [
        {"kind": "move", "source": {"file": 2, "rank": 2},
         "destination": {"file": 2, "rank": 1}, "promote": True},
        {"kind": "drop", "piece_type": "PAWN",
         "destination": {"file": 4, "rank": 4}},
    ])
~~~

- [ ] **ステップ 2: テストが失敗することを確認するために実行**

実行: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_game_record.GameRecordTests.test_saves_initial_position_and_recorded_moves_as_json -v

期待値: AssertionError: GameRecordのJSON保存操作が未実装です でFAIL。import errorやattribute errorだけではRed完了にしない。

- [ ] **ステップ 3: 最小限の保存実装を作成**

game_record.py に json、Path、Union をimportし、次の公開操作と変換を追加する。盤面は筋1〜9、各筋の段1〜9の順に走査し、持ち駒は PAWN、LANCE、KNIGHT、SILVER、GOLD、BISHOP、ROOK の順に、1枚以上だけを出力する。

~~~python
def save(self, path: Union[str, Path]) -> None:
    """開始局面と成功手を専用JSONファイルへ保存する。"""
    payload = _record_to_payload(self)
    with Path(path).open("w", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")


def _record_to_payload(record: GameRecord) -> dict:
    return {
        "format": "kaname-shogi-game-record-v1",
        "initial_position": _position_to_payload(record.initial_position),
        "moves": [_move_to_payload(move) for move in record.moves],
    }
~~~

_position_to_payload は side_to_move.name、盤上駒の file / rank / piece_type.name / side.name、双方の hands を返す。_move_to_payload は RecordedMove なら kind: move、RecordedDrop なら kind: drop を返す。現在局面は参照も出力もしない。

- [ ] **ステップ 4: テストがパスすることを確認するために実行**

実行: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_game_record.GameRecordTests.test_saves_initial_position_and_recorded_moves_as_json -v

期待値: 1件PASS。

- [ ] **ステップ 5: コミット**

~~~bash
git add kaname_shogi/game_record.py tests/test_game_record.py
git commit -m "feat: 棋譜をJSONへ保存できるようにする"
~~~

### タスク2: JSON読込・再適用と形式検証

**ファイル:**

- 変更: kaname_shogi/game_record.py:1-141
- テスト: tests/test_game_record.py:1-195

**インターフェース (Interfaces):**

- 消費 (Consumes): GameRecord.save(path)、GameRecord(initial_position)、GameRecord.apply_move、GameRecord.apply_drop。
- 生産 (Produces): GameRecord.load(path: Union[str, Path]) -> GameRecord。正しいJSONを新しい独立記録に変換し、不正内容または不合法な履歴は ValueError、ファイルI/O失敗は OSError とする。

- [ ] **ステップ 1: 失敗する読込テストを作成**

次の3テストを追加する。load = getattr(GameRecord, "load", None) が None なら self.fail("GameRecordのJSON読込操作が未実装です") とし、読み込みエラーをRed扱いにしない。

~~~python
def test_loads_saved_record_and_replays_current_position(self):
    """保存済みの開始局面と履歴から独立した記録を再現する。

    現在局面をJSONから直接採用する誤り、返却記録が元の記録と可変状態を
    共有する誤りを検出する。
    """
    record = GameRecord(create_initial_position())
    record.apply_move(Square(7, 7), Square(7, 6))
    record.apply_move(Square(3, 3), Square(3, 4))
    with TemporaryDirectory() as directory:
        path = Path(directory) / "record.json"
        record.save(path)
        load = getattr(GameRecord, "load", None)
        self.assertIsNotNone(load, "GameRecordのJSON読込操作が未実装です")
        if load is None:
            return
        loaded = load(path)

    self.assertEqual(loaded.moves, record.moves)
    self.assertEqual(loaded.current_position.board.piece_at(Square(7, 6)),
                     Piece(PieceType.PAWN, Side.SENTE))
    loaded.apply_move(Square(7, 6), Square(7, 5))
    self.assertEqual(len(record.moves), 2)


def test_rejects_invalid_json_values_and_illegal_history(self):
    """形式不正または不合法な履歴のJSONをValueErrorで拒否する。"""
    invalid_payloads = (
        "{",
        json.dumps({"format": "wrong", "initial_position": {}, "moves": []}),
        json.dumps({"format": "kaname-shogi-game-record-v1",
                    "initial_position": {"side_to_move": "SENTE", "pieces": [],
                                         "hands": {"SENTE": {"KING": 1}, "GOTE": {}}},
                    "moves": []}),
        json.dumps({"format": "kaname-shogi-game-record-v1",
                    "initial_position": {"side_to_move": "SENTE", "pieces": [],
                                         "hands": {"SENTE": {}, "GOTE": {}}},
                    "moves": [{"kind": "move",
                               "source": {"file": 7, "rank": 7},
                               "destination": {"file": 7, "rank": 6},
                               "promote": False}]}),
    )
    load = getattr(GameRecord, "load", None)
    self.assertIsNotNone(load, "GameRecordのJSON読込操作が未実装です")
    if load is None:
        return
    with TemporaryDirectory() as directory:
        for index, text in enumerate(invalid_payloads):
            path = Path(directory) / f"invalid-{index}.json"
            path.write_text(text, encoding="utf-8")
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    load(path)


def test_propagates_missing_file_error_when_loading(self):
    """存在しない読込先はOSErrorとして通知する。"""
    load = getattr(GameRecord, "load", None)
    self.assertIsNotNone(load, "GameRecordのJSON読込操作が未実装です")
    if load is None:
        return
    with TemporaryDirectory() as directory:
        with self.assertRaises(FileNotFoundError):
            load(Path(directory) / "missing.json")
~~~

- [ ] **ステップ 2: テストが失敗することを確認するために実行**

実行: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_game_record.GameRecordTests.test_loads_saved_record_and_replays_current_position tests.test_game_record.GameRecordTests.test_rejects_invalid_json_values_and_illegal_history tests.test_game_record.GameRecordTests.test_propagates_missing_file_error_when_loading -v

期待値: 3件が AssertionError: GameRecordのJSON読込操作が未実装です でFAIL。

- [ ] **ステップ 3: 最小限の読込・検証実装を作成**

~~~python
@classmethod
def load(cls, path: Union[str, Path]) -> "GameRecord":
    """専用JSONを検証して、新しい対局記録として読み込む。"""
    with Path(path).open(encoding="utf-8") as source:
        payload = json.load(source)
    initial_position, moves = _payload_to_initial_position_and_moves(payload)
    record = cls(initial_position)
    for move in moves:
        if isinstance(move, RecordedMove):
            record.apply_move(move.source, move.destination,
                              promote=move.promote)
        else:
            record.apply_drop(move.piece_type, move.destination)
    return record
~~~

_payload_to_initial_position_and_moves と下位ヘルパーは、辞書・配列・キー集合・厳密型・固定文字列を検証して Position、RecordedMove、RecordedDrop を作る。盤上駒の重複マスは ValueError とし、Board.set_piece で検証済みの駒だけを置く。持ち駒は検証済みの枚数だけ Hand.add を繰り返す。履歴の不合法性は公開 apply_move / apply_drop に委譲するため、既存規則と二重実装しない。json.load の JSONDecodeError は ValueError のまま扱い、Path.open の OSError は捕捉・変換しない。

- [ ] **ステップ 4: テストがパスすることを確認するために実行**

実行: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_game_record.GameRecordTests.test_loads_saved_record_and_replays_current_position tests.test_game_record.GameRecordTests.test_rejects_invalid_json_values_and_illegal_history tests.test_game_record.GameRecordTests.test_propagates_missing_file_error_when_loading -v

期待値: 3件PASS。

- [ ] **ステップ 5: 境界テストとRefactor要否確認**

save が読み取り専用の記録を変更しないテスト、余分キー・重複マス・0枚の持ち駒・file: true・不正な promote を拒否するテスト、既存ファイルへの正常な上書き、親ディレクトリがない保存先の FileNotFoundError を追加する。

実行: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_game_record -v

期待値: GameRecordTestsの全件PASS。変換・検証の重複は公開APIを増やさない非公開ヘルパーへだけ抽出し、既存の合法手判定は複製しない。Refactorの有無と理由を学習記録へ残す。

- [ ] **ステップ 6: コミット**

~~~bash
git add kaname_shogi/game_record.py tests/test_game_record.py
git commit -m "feat: JSONの棋譜を読み込めるようにする"
~~~

### タスク3: 利用案内、回帰確認、学習記録

**ファイル:**

- 変更: README.md:8-70
- 作成: docs/learning/37-game-record-file-save.md
- 作成: docs/knowledge/30-game-record-file-save.md
- テスト: tests/test_game_record.py、tests/test_cli.py

**インターフェース (Interfaces):**

- 消費 (Consumes): GameRecord.save(path)、GameRecord.load(path)、run_game(...) -> GameRecord。
- 生産 (Produces): JSON保存・読込の利用方法と今回確定した参照メモ。CLIの入力仕様・終了条件を増やさない説明。

- [ ] **ステップ 1: READMEの利用例を更新する**

READMEの現在の状態と実行方法に次の最小例を追加し、CLIがファイルを自動保存しないこと、保存先を明示して呼び出すこと、SFEN・USIが対象外であることを明記する。このタスクは文書のみであり、保存・読込の振る舞いはタスク1・2の自動テストで先に確認済みである。

~~~python
from pathlib import Path
from kaname_shogi.game_record import GameRecord
from kaname_shogi.model import Square, create_initial_position

record = GameRecord(create_initial_position())
record.apply_move(Square(7, 7), Square(7, 6))
record.save(Path("game.json"))
loaded = GameRecord.load(Path("game.json"))
~~~

- [ ] **ステップ 2: 知識メモと学習記録を作成する**

docs/knowledge/30-game-record-file-save.md に形式名、保存対象、例外境界、CLI・SFEN・USIの対象外を短く記録する。docs/learning/37-game-record-file-save.md に一次資料、確認問題ごとの本人回答、設計承認、TDDの実行結果、Refactor判断、独立レビュー、検証結果、未解決事項を事実だけで記録する。最後の理解確認はmain取り込み後まで未回答として扱い、正解を書かない。

- [ ] **ステップ 3: 全自動検証を実行**

~~~bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_game_record tests.test_cli -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
~~~

期待値: 全テストPASS、git diff --checkは出力なし。CLIテストが全件成功して、CLIの自動保存・save / load コマンドが追加されていないことを回帰確認する。

- [ ] **ステップ 4: CLIスモークを実行**

~~~bash
printf 'move 7 7 7 6\nresign\n' | PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi
~~~

期待値: 初期局面、先手の7六歩後の局面、後手投了と先手勝利を表示して終了する。ファイル保存メッセージや追加入力待ちは表示しない。

- [ ] **ステップ 5: 独立コードレビューと再検証を行う**

実装差分を開始コミットと比較して独立レビューする。CriticalまたはImportantがあれば修正し、対象テスト・全テスト・git diff --checkを再実行して再レビューする。Critical・Important・Minorの件数、指摘、対応・見送り理由を学習記録へ残す。

- [ ] **ステップ 6: 文書をコミット**

~~~bash
git add README.md docs/learning/37-game-record-file-save.md docs/knowledge/30-game-record-file-save.md
git commit -m "docs: 第37回のファイル保存学習記録を追加する"
~~~

### タスク4: mainへの取り込みと最終確認

**ファイル:**

- 変更なし（取り込み後は main で文書の最後の理解確認だけを追記する）

**インターフェース (Interfaces):**

- 消費 (Consumes): 作業ブランチ codex/game-record-file-save の実装・テスト・レビュー・文書コミット。
- 生産 (Produces): main に取り込まれ、取り込み先で検証済みの第37回成果物。本人回答待ちの理解確認問題。

- [ ] **ステップ 1: 取り込み前の状態を提示して本人の承認を待つ**

作業ブランチ名、コミット一覧、独立レビュー結果、全検証結果、未解決事項を提示する。本人の明示的なmain取り込み承認までは、mainへマージしない。

- [ ] **ステップ 2: 承認後にmainへfast-forward取り込みを行う**

~~~bash
git switch main
git merge --ff-only codex/game-record-file-save
~~~

期待値: fast-forwardで取り込まれ、競合がない。競合またはfast-forward不能なら、状態を変更せず本人へ報告する。

- [ ] **ステップ 3: 取り込み先で全検証を再実行する**

~~~bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
printf 'move 7 7 7 6\nresign\n' | PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi
git diff --check
git status --short --branch
~~~

期待値: 全テストPASS、CLIスモーク成功、差分チェック出力なし、mainに未コミット変更なし。

- [ ] **ステップ 4: 最後の理解確認を一問だけ出して回答を待つ**

出題: 「なぜ読込時にJSONへ保存した現在局面をそのまま使わず、開始局面と成功手を既存の規則で再適用して現在局面を作るのか。」

本人の回答を待つ。未回答を正解として学習記録に書かない。

## 自己レビュー

- 仕様の保存形式、保存対象、例外境界、CLI・SFEN・USIの対象外はタスク1〜3に対応付けた。
- JSONのキー、厳密な型、固定文字列、順序、余分キーの扱いを具体化し、実装時に未決定を残していない。
- タスク1・2は振る舞いのRedを明示的なAssertionErrorで確認してから最小Greenへ進む。読み込みエラーだけをRedとは扱わない。
- 各Pythonコマンドはリポジトリ直下の標準unittest構成で実行可能である。
- main取り込み前の承認と、取り込み後の検証・理解確認を独立タスクにした。
