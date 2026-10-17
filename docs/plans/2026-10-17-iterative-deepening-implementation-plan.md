# 反復深化と開発用比較 実装計画

> **AIエージェントへの指示:** 承認後の実行では、本人が選んだ方式に応じて `executing-plans` または `subagent-driven-development` スキルを使用する。以下のチェックボックスは実行記録であり、計画作成時には完了にしない。

**目標:** 各深さの完了結果を保持する反復深化と、正しさ・訪問回数を観察する開発用コマンドを追加する。

**アーキテクチャ:** 既存αβの根だけに優先手を指定し、反復処理は深さと完了記録を管理する。比較の共通処理を取り出し、新旧コマンドの実行順と中断状態は各入口に保つ。

**技術スタック:** リポジトリ既定のPython 3.15、標準ライブラリのdataclasses・argparse・unittest、固定版Ruff 0.16.10。依存追加なし。

**仕様:** [承認済み設計](2026-10-17-iterative-deepening-design.md)。2026-10-17、草案全体の確認依頼に本人が「yes」と回答。**本計画は未承認、実行方法も未選択。**

**グローバル制約:**

- Random（最弱・既定）、一手駒得、現行二手先読みは選択肢に残す。
- 時間制御、通常対局・USIへの接続、実際の着手後の再利用、置換表、途中局面の手順序変更、評価改良は対象外。
- SOLID・DRYの希望に沿い、反復の段取り、指定深さ探索、比較入出力を分離する。再帰探索は既存の共有本体を使い、将来機能のためのクラス階層や汎用設定基盤は追加しない。
- 上限4を一か所で管理し反復処理へ渡す。現在は深さ指定オプションを追加しないが、将来その入力を接続しやすくする。
- 計画承認前にTDD・コード・テスト変更を行わない。main統合は別途本人承認を得る。
- 日本語docstringに契約・副作用・理由を記す。テスト名は英語、docstring先頭行は確認する振る舞い、本文は検出対象を書く。

## レビューフォーカス

仕様を具体的な検証へ落とす際に追加点検する5条件。対応テストは各タスクへ含める。

1. 二つの反復を交互に取得しても前回手と累計が混ざらない（タスク2）。
2. 深さ0・終端に不在の優先手を指定しても、早期returnで検査をすり抜けない（タスク1）。
3. 優先手が先頭/末尾、または根が最小側でも、残りの順序と正しい最善手を保つ（タスク1）。
4. 不一致を出した後で中断したら130となり、不一致の証拠を消さない（タスク4）。
5. 一度渡した完了記録を保持して次へ進めても値が変わらず、操作内の例外も入力誤りへ隠されない（タスク2・4）。

## ファイルと正確な境界

パスはリポジトリルートからの相対表記。作業場所は `/Users/oki2a24/kaname-shogi`、ブランチは `codex/iterative-deepening-design` を継続する案。別worktreeは作らない。

| ファイル | 変更 |
| --- | --- |
| `kaname_shogi/search/core.py`, `alpha_beta.py` | 省略可能な根の優先手 |
| `kaname_shogi/search/result.py` | frozenの完了記録 |
| `kaname_shogi/search/iterative_deepening.py` | 新規、遅延取得する反復 |
| `kaname_shogi/search/comparison.py` | 新規、入力・整形・判定の共通化 |
| `kaname_shogi/search/compare.py` | 既存動作を保って共通処理へ委譲 |
| `kaname_shogi/search/compare_iterative.py` | 新規、上限4の比較入口 |
| `tests/test_search_alpha_beta.py` | 優先手の契約を追加 |
| `tests/test_search_iterative_deepening.py` | 新規、反復と記録の契約 |
| `tests/test_search_comparison.py` | 新規、共通入力・整形・判定 |
| `tests/test_search_compare_iterative.py` | 新規、新コマンドの順序・出力・例外 |
| `tests/test_search_compare.py`, `tests/test_search_shogi.py` | 既存回帰。必要な場合のみ共通化に合わせて参照先を調整 |
| `tests/search_tree_support.py` | 必要な独立数値木のみ追加。製品の結果から期待値を計算しない |
| `docs/learning/iterative-deepening-design.md`, `docs/resume.md` | 実行・検証・レビュー・承認の記録 |
| `docs/knowledge/search-comparison.md`, `README.md`, `docs/README.md` | 実装後の使い方・制約・参照先 |

## 共通の実行規律

各タスクの振る舞いを一つずつ、失敗テスト→振る舞いのFAIL確認→最小実装→成功→Refactor要否の順で進める。新規モジュールのImportErrorだけでRed完了としない。最小の宣言が必要なら、実装前の足場であることを記録し、期待値との不一致を改めて確認する。既存処理の抽出は初回Greenとなり得るため、Redを捏造しない。

各タスクの完了点で変更範囲とRefactor要否を記録する。選択した実行方式で必要な独立レビューを実施し、少なくともブランチ全体の最終レビューを必須とする。Critical/Importantは修正・再検証・再レビュー後に文書更新とコミットへ進む。Minorも対応または理由を記録する。

Python変更時の順序は、import変更があれば `.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`、`.venv/bin/ruff check .`、差分確認、対象テスト、ステージ、コミット。フックを回避しない。計画ではこの共通手順を各タスクから参照する。

## タスク1：根の優先手を既存αβへ追加

**消費:** `SearchOperations[N, M]`、`SearchResult[M]`、既存の数値木。

**生産:**

- `alpha_beta.search[N, M](node: N, depth: int, operations: SearchOperations[N, M], *, preferred_move: M | None = None) -> SearchResult[M]`
- `core.search`にも同じキーワード引数を追加。既存の必須キーワード`pruning: bool`は維持。

- [ ] `tests/test_search_alpha_beta.py`へ下記のテストを一つずつ追加する。
  - `test_preferred_move_reorders_only_root`：深さ2、根A/B/C/Dの全葉を同値にし優先C。訪問ラベルはroot,C,C0,A,A0,B,B0,D,D0（各枝の子は一つ）。子に複数候補を置く別例ではX/Y/Zの相対順も確認。入力のchildrenは元のまま。
  - `test_preferred_move_at_first_last_and_minimizing_root`：先頭A、末尾D、最小根での優先をsubTest。候補を欠落させず同点は優先手になる。
  - `test_invalid_preferred_move_checks_root_before_children`：不在手を深さ0/2と終端で指定しValueError、根inspect一回、advanceゼロ。深さ0の合法指定は評価のみでmove=None。
  - `test_preferred_move_preserves_exact_best_at_equal_bound`：既存の境界同値の木の根順をB/Aにして優先A。期待値はscore=(0,3), move=A, visits=6。
- [ ] 対象テストを実行して意図した振る舞いのFAILを確認する。
- [ ] 根のinspect直後に優先手を照合する。候補列を局所的に並べ替え、再帰へ優先手を伝播しない。終端・深さ0のreturnより前に照合し、二重inspectを避ける。
- [ ] 下記を成功させ、既存のmax/min枝刈りと同点の検証が残っていることを確認する。

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_search_alpha_beta.py' -v
.venv/bin/python -m unittest discover -s tests -p 'test_search_minimax.py' -v
```

主要アサーションの形：

```python
self.assertEqual(result.move, "C")
self.assertEqual(seen, ["root", "C", "C0", "A", "A0", "B", "B0", "D", "D0"])
self.assertEqual(root.children, original_children)
```

- [ ] 共通手順で整形・検証し、Refactor要否を記録する。

## タスク2：完了記録と反復の入口

**消費:** タスク1の`alpha_beta.search`。

**生産:**

- `IterationResult[M](depth: int, result: SearchResult[M], total_visited_nodes: int)`：frozen dataclass。
- `iterative_deepening.search[N, M](node: N, max_depth: int, operations: SearchOperations[N, M]) -> Iterator[IterationResult[M]]`。

- [ ] `tests/test_search_iterative_deepening.py`へ順にテストを追加する。
  - `test_completed_depth_changes_best_and_accumulates`：設計のA=5/B=3、深い葉A=[1,−2]/B=[2,1]を使い下記の値を確認。
  - `test_stream_is_lazy_and_validates_limit_immediately`：search呼出しだけではseen空。不正0/−1/1.5/True/FalseはnextせずValueError。next一回で深さ1まで。上限1は次のnextでStopIteration。
  - `test_previous_best_is_passed_to_next_depth`：実αβへのラッパーで優先指定None→A→Bを観察する。固定Aや二回前の手を渡す誤りを検出。
  - `test_records_are_immutable_and_streams_independent`：過去記録の値不変、フィールド代入はFrozenInstanceError、内包resultの同一性、別の二ストリームを交互取得して深さ・累計の独立を確認。
  - `test_terminal_yields_once`：詰み(-1,0)と非詰み手なし(0,3)を別々に確認。上限4でもdepth=1,move=None,visits=1,total=1の一件のみ。
  - `test_interruption_keeps_previous_record`：深さ3の操作でKeyboardInterruptを発生させ、取得済み深さ2の記録不変・深さ3記録なし。ValueErrorを投げる操作もそのまま伝播。
- [ ] 各テストの振る舞いのFAILを確認する。
- [ ] 呼出し時の上限検査と内部ジェネレーターを分離する。各回のαβ完了後に新規記録を生成し、`yield`する。手なしならその記録の後に終了。状態をモジュール変数や共有リストへ置かない。
- [ ] `yield`にPython固有の状態保持と他言語でのIterator等への置換を説明する日本語コメントを付ける。
- [ ] 次のアサーションと対象テストを成功させる。

```python
self.assertEqual(
    [(r.depth, r.result.move, r.result.score, r.result.visited_nodes,
      r.total_visited_nodes) for r in records],
    [(1, "A", (0, 5), 3, 3), (2, "B", (0, 1), 7, 10)],
)
self.assertIs(record.result, returned_alpha_beta_result)
```

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_search_iterative_deepening.py' -v
```

- [ ] 共通手順で整形・検証し、Refactor要否を記録する。

## タスク3：比較共通処理の抽出

**消費:** 既存のSFEN変換・Move・Position・Score・SearchResult。

**生産（comparison.py）:**

- `make_parser(description: str) -> argparse.ArgumentParser`：requiredな`--sfen`のみを共通登録。
- `parse_position(sfen: str) -> Position`：`parse_sfen(sfen).position`へ委譲し、ValueErrorを変換しない。
- `format_move(move: Move | None) -> str`、`format_score(score: Score) -> str`。
- `best_moves(full: SearchResult[Move]) -> tuple[Move, ...]`。
- `results_match(full: SearchResult[Move], pruned: SearchResult[Move]) -> bool`。

- [ ] 共通処理のテストを`tests/test_search_comparison.py`へ用意する。`test_input_and_format_contracts`でSFEN・後手・不正入力、`test_match_accepts_ties_rejects_wrong_score_or_move`で既存比較テストの独立値を再利用。期待値例：`format_score((0,-2)) == '−2'`、`format_move(None) == 'なし'`、同点別手はTrue、低い手はFalse。
- [ ] 抽出前の既存比較テストを実行し基準を確認する。新しい入口が未存在な段階の読み込みエラーと、抽出処理の初回Greenを区別して記録する。
- [ ] 共通関数を移し、既存compareはimportして使う。`compare.format_move`と`compare.results_match`の参照を維持する。parse_argsのSystemExitとSFEN変換のValueErrorは各main内の小さい範囲で処理する。
- [ ] 下記を成功させ、旧深さ2/3/4、行形式、終了コード、入力例外と内部例外の境界が変わらないことを確認する。

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_search_comparison.py' -v
.venv/bin/python -m unittest discover -s tests -p 'test_search_compare.py' -v
```

- [ ] 共通手順で整形・検証し、Refactor要否を記録する。

## タスク4：反復深化の開発用比較コマンド

**消費:** タスク2のストリーム、タスク3の共通関数、minimax/alpha_betaの既存探索。

**生産:** `compare_iterative.main(argv: list[str] | None = None) -> int`、同モジュールの`DEFAULT_MAX_DEPTH = 4`、`python -m`入口。

- [ ] `tests/test_search_compare_iterative.py`へ以下を一つずつ追加し、各振る舞いのFAILを確認する。
  - `test_order_and_three_counts`：反復結果取得→全幅→単独αβ→次取得のイベント順。反復visits=3,7、total=3,10、単独visits=3,7、全幅visitsを異なる値に置き、累計混入を見分ける。実探索の数値木検証とモックの段取り検証を分ける。
  - `test_mismatch_continues`：深さ2だけ不一致、深さ4まで実行して1、全深さ成功を出さない。
  - `test_interrupt_during_iteration`：深さ1途中なら完了なし、深さ3途中なら完了2・作業3未完了、累計は完了分。
  - `test_interrupt_during_reference_search`：深さ3の反復結果を渡した後、全幅/単独αβそれぞれで中断し、反復完了3・比較未完了3を表示、130。
  - `test_mismatch_then_interrupt`：不一致表示を残し130、後続探索なし。
  - `test_terminal_compares_only_depth_one`：手なしでも全幅・単独αβの深さ1比較を行い、手なし終了、全4深さ完了の誤表示なし。
  - `test_input_and_internal_errors`：SFEN不正・引数欠落・未知の--depthは2で探索ゼロ、helpは0、各探索段階のValueErrorは内部例外として伝播。
  - `test_real_process_entrypoint`：玉だけSFENの先手/後手、手なし、invalid、helpを実プロセスで確認。旧コマンドと同様にタイムアウトを設定し、実SIGINT試験とは区別する。
- [ ] mainを実装する。最後の反復完了記録、最後の比較完了深さ、現在の作業段階、不一致の有無を別に管理する。取得直後に記録を保持し、確認用探索の前に失わない状態にする。
- [ ] 表示は深さ・反復評価・USIと日本語の手・比較・単独訪問・反復今回・反復累計の列とする。累計の見出しは「反復累計（完了した深さまで）」、中断診断は「反復深化：深さNまで完了」「深さNの比較：未完了」を含める。未完了反復の訪問数を総費用として表示しない。
- [ ] 正常一致0、不一致1、入力2、中断130を返し、末尾で`raise SystemExit(main())`を使う。中断は不一致より優先。内部ValueErrorは広く捕捉しない。
- [ ] 代表アサーションと対象テストを成功させる。

```python
self.assertEqual(code, 130)
self.assertIn("反復深化：深さ3まで完了", err)
self.assertIn("深さ3の比較：未完了", err)
self.assertNotIn("全深さで比較成功", out)
```

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_search_compare_iterative.py' -v
```

- [ ] 共通手順で整形・検証し、Refactor要否を記録する。

## タスク5：全体検証・検出力・独立レビュー・記録

- [ ] `tests/test_search_shogi.py`の既存例（先後・駒取り・成り・打ち・詰み・手なし・元局面不変）を再利用し、反復入口と全幅の同深さ一致を`tests/test_search_iterative_deepening.py`で確認する。全幅一致のみを正しさの根拠にしない。
- [ ] 対象と全体を実行し、実際の件数・結果を記録する。過去490件を流用しない。

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_search_*.py' -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m kaname_shogi.search.compare_iterative --sfen '8k/9/9/9/9/9/9/9/K8 b - 1'
```

- [ ] 隔離コピーで代表的誤りを一つずつ入れる：根優先を無視、子まで並べ替え、累計を今回分で置換、前回最善手を固定、中断時の完了記録を破棄。意図したアサーションのFAILと復元後成功を確認する。単独では検出できない誤りを全体検出と混同しない。読み込みエラーは検出成功に数えない。
- [ ] Refactor要否をブランチ全体で確認する。新しい独立レビュアーへ設計・差分・契約/ケース/検出対象/補完/未検証を渡す。Critical/Importantを解消して再検証・再レビューする。Minorも扱いを記録する。
- [ ] 実測値・実際の変更・Red/Green・誤り注入・Refactor・各重大度のレビュー結果を学習記録へ保存する。知識メモとREADMEへ新コマンドと累計の意味・未接続の制約を追記し、索引・現在地を更新する。
- [ ] 文書リンク・差分を確認し、対象ファイルだけステージしてコミットする。未レビューの変更をコミット完了扱いにしない。
- [ ] 本人へ成果とmainへの取り込み案を提示して承認を待つ。承認後にmainへ取り込み、取り込み先で同じ影響範囲の検証を実施する。
- [ ] 最後の理解確認を一問出し、本人回答と補足を記録してからテーマ完了・次候補の整理へ進む。

## 計画の自己点検と現状

2026-10-17、既存のcore/alpha_beta/compare/result/contracts/shogiと数値木・比較テストを読み、シグネチャ・既存参照・検証コマンドを照合した。仕様のデータ、順序、中断、イミュータブル、入力境界、共有範囲はタスク1〜4、回帰・検出力・レビュー・記録はタスク5に対応する。

本計画内のテスト名・アサーション・コマンドは将来の実施内容であり、未実行。製品・テストファイルは変更していない。現在行うのは文書の自己点検とリンク・差分検査のみ。実装計画の独立レビューは未実施。OSのSIGINT配送、棋力、全局面での速度、通常対局接続は未検証のまま残す。

実行方法は、私自身がこのセッションで順に実装し最後に独立レビューする方式を推薦する。各タスクが前の公開契約に依存するため。タスクごとに別エージェントが実装・レビューする方式も選べる。本人の計画承認と実行方式の選択後に開始する。
