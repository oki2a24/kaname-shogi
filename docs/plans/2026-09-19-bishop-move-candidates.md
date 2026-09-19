# 角の移動先候補 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画をタスクごとに実装するには、移植された `subagent-driven-development` スキル（推奨）または `executing-plans` スキルを起動して使用してください。ステップには追跡用のチェックボックス (`- [ ]`) を使用します。

**目標:** 成る前の角について、盤面を変更せず、斜め4方向の移動先候補を固定順で返す操作を追加する。

**アーキテクチャ:** 既存の `kaname_shogi.movegen` に角専用の公開関数を追加する。方向順「右前 → 左前 → 右後ろ → 左後ろ」で各方向を近い順に走査し、飛車との共通ヘルパーは作らない。

**技術スタック:** Python 3.9.6、標準ライブラリ、`unittest`。

**仕様 (Spec):** `docs/design/07-bishop-move-candidates.md`

**グローバル制約 (Global Constraints):**
- 説明・記録は日本語で書く。
- Python標準ライブラリとunittestのみを使用する。
- 座標は将棋の筋・段を基本とする。
- 候補生成は盤面を変更せず、手番・成り・王手・合法手判定を扱わない。
- 角と飛車の処理は今回共通化せず、角専用関数として実装する。
- TDDはRed → Green → Refactorで進め、各段階の実施結果を正確に記録する。

---

## 変更ファイル

- 変更：`tests/test_movegen.py` — `BishopMoveCandidatesTests` と角の振る舞いのテストを追加。
- 変更：`kaname_shogi/movegen.py` — `bishop_move_candidates(board: Board, source: Square) -> list[Square]` と日本語docstringを追加。
- 変更：`README.md` — 角の公開関数、候補順、占有条件、対象外を追記。
- 作成：`docs/learning/17-bishop-candidates-implementation.md` — 実際のRed・Green・Refactor、検証、レビュー、理解確認を記録。

## 実装タスク

### タスク1：基準確認と入力契約のRed

**ファイル:** `tests/test_movegen.py`

- [ ] 既存テストを実行し、角追加前の基準テスト数と成功を確認する。
- [ ] `BishopMoveCandidatesTests` に、空マスの出発点を拒否するテストを追加する。

```python
def test_empty_source_is_rejected(self):
    """空の出発マスを角候補の計算対象として受け付けない。

    候補なしと呼び出しの誤りを区別するValueErrorの契約を確認する。
    """
    with self.assertRaises(ValueError):
        bishop_move_candidates(Board(), Square(5, 5))
```

- [ ] 角以外の全駒種を拒否するテストを追加する。テストメソッド名は英語、日本語docstringとする。
- [ ] 関数未定義によるImportErrorと、関数定義後にValueErrorが出ない振る舞いのRedを区別して記録する。

### タスク2：斜め4方向の最小Green

**ファイル:** `tests/test_movegen.py`, `kaname_shogi/movegen.py`

- [ ] ５五の先手・後手の角を開いた盤面に置き、次の順で16候補を期待するテストを追加する。

```python
expected = (
    [Square(file, rank) for file, rank in [(4, 4), (3, 3), (2, 2), (1, 1)]]
    + [Square(file, rank) for file, rank in [(6, 4), (7, 3), (8, 2), (9, 1)]]
    + [Square(file, rank) for file, rank in [(4, 6), (3, 7), (2, 8), (1, 9)]]
    + [Square(file, rank) for file, rank in [(6, 6), (7, 7), (8, 8), (9, 9)]]
)
```

- [ ] `movegen.py` に出発点の角検証、先後に応じた前後の段増減、4方向の筋・段増減、方向ごとの走査、空マスの追加を最小実装する。
- [ ] 公開docstringに引数、戻り値、新しいリスト、`ValueError`、盤面不変、方向順、対象外の範囲を記載する。
- [ ] 対象テストを実行し、Greenを確認する。

### タスク3：停止条件と境界の確認

**ファイル:** `tests/test_movegen.py`, `kaname_shogi/movegen.py`

- [ ] 各方向の自駒の手前で止まり、自駒とその先を含めないテストを追加する。
- [ ] 各方向の最初の相手駒を最後の候補に含め、その先を含めないテストを追加する。
- [ ] 一方向が自駒で塞がっても残り3方向を調べるテストを追加する。
- [ ] 四隅の候補を先後両方で確認し、盤外のマスを含めないテストを追加する。
- [ ] 停止条件または境界のテストを、実装前に実行してRedを確認する。読み込みエラーだけを振る舞いのRedとは扱わない。
- [ ] 空マス追加、相手駒追加後の停止、自駒での停止、盤外での停止を最小実装で満たす。
- [ ] 対象テストを実行し、Greenを確認する。

### タスク4：契約の検証とRefactor

**ファイル:** `tests/test_movegen.py`, `kaname_shogi/movegen.py`

- [ ] 候補計算前後で盤上の全81マスが同じであることを確認するテストを追加する。
- [ ] 呼び出しごとに独立したリストを返すテストを追加する。
- [ ] `Position.side_to_move` を変更しても、出発駒の所有者から前後を計算し、手番を変更しないテストを追加する。
- [ ] 全テストを実行する。

```sh
python3 -m unittest discover -s tests -v
```

- [ ] Green後に、方向データ、走査処理、変数名、公開docstringの読みやすさを点検する。
- [ ] 角専用関数という設計を維持し、飛車との共通化は行わない。変更が必要な場合だけ再テストする。

### タスク5：文書・README・CLI・レビュー

**ファイル:** `README.md`, `docs/learning/17-bishop-candidates-implementation.md`

- [ ] READMEに `bishop_move_candidates` の意味、方向順、先後の前後、相手駒・自駒の扱い、対象外を日本語で追記する。
- [ ] 実際に行ったRed・Green・Refactor、変更内容、検証結果、レビュー結果、未解決事項を実装後の学習記録へ記録する。
- [ ] コードを示した理解確認を一問ずつ行い、本人の回答と補足を区別して記録する。回答前に正解を記録しない。
- [ ] CLIを実行する。

```sh
python3 -m kaname_shogi
```

- [ ] 差分と文書リンクを確認する。

```sh
git diff --check
```

- [ ] 読み取り専用レビューで、斜め方向の筋・段、先後、候補順、停止条件、盤面不変、docstringとREADMEの整合を確認する。
- [ ] 学習・設計・実装・検証・レビューの変更を確認してコミットする。
