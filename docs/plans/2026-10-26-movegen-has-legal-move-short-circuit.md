# 合法手有無判定を最初の合法手で終える実装計画

> **AIエージェントへの指示:** この計画を実行するときは `superpowerssuperpowers:executing-plans` スキルを使用する。各段階を順番に進め、チェックボックスを更新する。本人の計画全体への明示承認前にテスト・コードを変更しない。

**目標:** `_has_legal_move` が全合法手を列挙せず、最初の合法手が見つかった時点で真を返すようにし、同じ局面・seed・条件で指し手列と対局結果を変えずに詰み判定の時間を減らす。

**アーキテクチャ:** 合法手一覧の既存生成器 `_legal_moves_controlled` を `_first_only=True`、`control=None` で呼び、戻った一手タプルの有無を真偽値にする。合法手の列挙順・合法性規則・打ち歩詰め確認の設定は既存処理に委ね、公開APIや比較条件は変えない。

**技術スタック:** Python 3.9互換、標準 `unittest`、一時スクリプトの `time.perf_counter`。

**仕様 (Spec):** [局内高速化の計測設計・実測](2026-10-26-c1-comparison-game-internal-speedup-design.md)、[学習記録](../learning/c1-comparison-game-internal-speedup.md)

状態: 2026-10-26に本人が全体承認。実装・検証・独立レビュー・記録を完了し、このブランチへコミットする。main統合は対象外。

## グローバル制約 (Global Constraints)

- 変更前後で同じ局面・乱数種・比較条件の指し手列、成功手数、終局理由、勝者を一致させる。
- `_has_legal_move(position, check_uchi_fuzume=...)` は、指定された現行規則に合法手が一つ以上あるときだけ `True`、ないとき `False` を返す。
- `check_uchi_fuzume` をそのまま伝播し、打ち歩詰め確認中の再帰境界を保つ。
- 合法手一覧 `legal_moves` の全列挙・固定順・公開契約は変更しない。
- 盤面、手番、双方の持ち駒を変更しない。
- 依存関係、評価式、比較CLI条件、並列worker数、通常対局CLI、USIを変更しない。
- 本計画の明示承認まではTDD、コード変更、テスト変更を開始しない。

## レビューフォーカス (Review Focus)

1. 合法手がある局面で、誤って常に `False` を返したり、合法手の発見を見落としたりしない。
2. 合法手がない局面で、全候補を調べ終える前に `True` を返さない。
3. 盤上の手だけでなく、既存規則上の合法な駒打ちも「手あり」と判定する。
4. 打ち歩詰め確認時に `check_uchi_fuzume=False` が失われ、再帰・誤判定が起きない。
5. 候補手の試行で元の局面を変更しない。

## 対象ファイル

- 変更: `kaname_shogi/movegen.py` の `_has_legal_move` とそのdocstring。
- 変更: `tests/test_movegen.py` の `LegalMoveEnumerationTests` に、早期終了経路を確認するテストを追加。
- 更新: 本計画、`docs/plans/2026-10-26-c1-comparison-game-internal-speedup-design.md`、`docs/learning/c1-comparison-game-internal-speedup.md`、`docs/resume.md`、`docs/README.md` に承認・実装・検証・レビューの事実を記録。

## 作業場所

計画作成時の作業場所は `/Users/oki2a24/.codex/worktrees/c1-analysis-resume/kaname-shogi`、ブランチは `codex/c1-analysis-resume`、HEADは `cf3d1a9`。2026-10-26に全体承認を受け、同じ隔離worktreeで `codex/movegen-has-legal-move-short-circuit` を作成した。実装・検証・独立レビューを完了。main統合はしない。

## 契約とテスト検出範囲

| 契約 | 代表ケース | 検出したい誤り | 検出範囲 |
| --- | --- | --- | --- |
| 手があるなら真 | 新しい `test_uses_first_only_search_when_a_board_move_exists`、`CheckmateAndGameEndTests.test_returns_false_when_king_can_escape_check` | 常にFalse、first-onlyを指定しない | 専用テストと詰み判定関連テスト |
| 手がなければ偽 | `CheckmateAndGameEndTests.test_returns_true_for_checked_king_with_no_legal_move` | 合法手なしを手ありとする | 詰み判定関連テストと全体テスト |
| 合法な駒打ちも手として扱う | `CheckmateAndGameEndTests.test_returns_false_when_hand_piece_can_interpose` | 盤上移動だけを調べる | 詰み判定関連テストと全体テスト |
| 打ち歩詰め確認の設定を保つ | `test_reply_search_disables_nested_uchi_fuzume_check` | Falseを失い公開の打ち歩詰め確認へ再入する | `UchiFuzumeTests` と全体テスト |
| 元局面を変更しない | 新しい早期終了テストのsnapshot、既存の盤上手・駒打ちテスト | 試し指し・試し打ちを元局面へ漏らす | 合法手有無・詰み判定関連テスト |
| 対局の指し手列と結果を変えない | 固定6局の保存済みJSONとの全手順・終局照合 | 同seed再生の挙動変化 | この6局のみ。全局面・全seedの証明ではない |

## タスク 1: 合法手有無判定の早期終了

**ファイル:**
- 変更: `kaname_shogi/movegen.py:466-474`
- 変更: `tests/test_movegen.py` の `LegalMoveEnumerationTests`
- 更新: 上記の設計・学習・再開案内文書

**インターフェース:**
- 消費: `_legal_moves_controlled(position, *, check_uchi_fuzume, control=None, _first_only=True) -> LegalMovesResult`。`_first_only=True` は一手目を得た時点で `completed=True` とその一手を返し、合法手がない場合は全候補を調べた後に空タプルを返す既存経路。
- 生産: `_has_legal_move(position, *, check_uchi_fuzume: bool) -> bool`。探索制御の中断はなく、結果は常に確定した真偽値。

- [x] **変更前の短い基準計測**

  TDD変更前に、`data/comparison/runs/c1-rook-mobility-pilot-512-2026-10-24/` の保存済み6予定・seedを一時スクリプトから `comparison.run_game` で各1回再生した。`time.perf_counter` の通常wall合計は164.437秒、各手の `elapsed_ns` 合計は143.252秒。6局すべてで全指し手列・終局理由・勝者などが保存済み結果と一致し、conditions・summary・局JSON・局面セットのSHA-256も計測前後で一致した。結果ディレクトリへの書き込みはない。

- [x] **RED: 盤上に複数の合法手がある局面で早期終了経路を要求するテストを追加**

  `LegalMoveEnumerationTests` に `test_uses_first_only_search_when_a_board_move_exists` を追加する。先手玉・後手玉と複数の合法手を持つ局面を作り、`_legal_moves_controlled` を `unittest.mock.patch.object(..., wraps=...)` で観測しながら `_has_legal_move(position, check_uchi_fuzume=True)` を呼ぶ。真を返すこと、呼出し前後で局面snapshotが同じこと、`self.assertIs(search.call_args.kwargs.get("_first_only"), True)` をassertする。旧経路では値が `None` となり、テスト本体のassertionで失敗する。

- [x] **Verify RED: 旧経路で振る舞いの失敗を確認**

  実行: `PYTHONPATH=tests .venv/bin/python -m unittest test_movegen.LegalMoveEnumerationTests.test_uses_first_only_search_when_a_board_move_exists -v`

  期待値: テスト本体は実行され、現在の `_first_only=False` で失敗する。import・属性エラーや読み込みエラーはRedとして数えない。

- [x] **GREEN: `_has_legal_move` を既存first-only経路へ接続**

  `kaname_shogi/movegen.py` の `_has_legal_move` で `_legal_moves_controlled` を `check_uchi_fuzume`、`control=None`、`_first_only=True` で呼び、返された `moves` の有無を返す。公開の `legal_moves` に戻らない。docstringを実際の早期終了方式と打ち歩詰め確認境界に合わせる。

- [x] **Verify GREEN: 新テストと合法手有無の既存契約を確認**

  実行: `PYTHONPATH=tests .venv/bin/python -m unittest test_movegen.LegalMoveEnumerationTests -v` と `PYTHONPATH=tests .venv/bin/python -m unittest test_movegen.CheckmateAndGameEndTests -v`

  期待値: 合法手有無、詰み／非詰み、盤上手・持ち駒合いのテストが両クラスで全件PASS。続けて打ち歩詰めフラグ伝播を確認するため `PYTHONPATH=tests .venv/bin/python -m unittest test_movegen.UchiFuzumeTests.test_reply_search_disables_nested_uchi_fuzume_check -v` を実行しPASS。

- [x] **検出力を確認: 独立した誤実装を一時コピーで注入**

  一時worktreeまたは一時コピーで、(a) `_first_only=True` をFalseにする、(b) `_has_legal_move` を常にFalseにする、の2変異を一つずつ適用する。両方とも新しい `test_uses_first_only_search_when_a_board_move_exists` が、(a) は `_first_only` assertion、(b) は戻り値のassertionでFAILすることを確認し、実ソースを復元した後にPASSさせる。エラー終了を検出成功として扱わない。

- [x] **REFACTOR要否を確認**

  既存の `LegalMovesResult` と first-only生成器で十分であること、重複探索経路・新しい型・公開APIが不要であることを確認した。追加のRefactorは行わない。

- [x] **性能・同値性を固定6局で検証**

  変更前と同じ6予定・seed（`game-000001`、`000003`、`000005`、`000007`、`000009`、`000011`）を一時スクリプトで各1回再生した。schedule・方式別seed・先後・開始SFEN・全指し手列・成功手数・終局理由・勝者・error値が保存済みJSONと6局すべて一致し、conditions、6局JSON、summary、局面セットのSHA-256も不変だった。変更前は通常wall 164.437秒・各手`elapsed_ns`合計143.252秒、変更後は100.908秒・79.319秒。各一回の測定なのでこの6局での観測値として記録し、速度倍率を一般化しない。cProfileの変更後再実行は行わなかった。

- [x] **全体検証・独立レビュー**

  `.venv/bin/ruff format .`（1ファイル再整形）、`.venv/bin/ruff check .`（成功）、`python3 scripts/run_tests_parallel.py`（895件・58モジュール、21.427秒）、`git diff --check`（成功）。独立レビューはCritical 0・Important 0・Minor 1。Minorは学習記録の現状表現が古いという指摘で、計測時点の履歴と現在状態を分けるよう修正済み。コード修正指摘はなかった。

- [x] **記録を確認してコミット**

  承認と実装結果、TDD Red/Green、誤り注入、確認コマンドと実測結果、レビュー、未検証事項を学習記録へ記載した。`docs/resume.md` と `docs/README.md` の現在地・索引を更新し、相対Markdownリンク692件と差分を確認した。この計画を含む変更一式を現在の作業ブランチへコミットする。mainへの統合は対象外で、別途本人の承認を待つ。

## 検出範囲と未検証事項

- テストは合法手あり／なし、盤上手／駒打ち、局面不変、打ち歩詰め確認フラグ、および早期終了指定を確認する。詰み判定クラスと既存探索・比較テスト全体が、その接続先の回帰を補う。
- 固定6局の再生は同seedでの指し手列と結果が一致するかを確認する代表例であり、全局面・全seedに対する証明ではない。
- 変更前後の時間比較は6局を各一回だけ実行するため、実比較CLI全体の高速化倍率、4,080局の所要時間、全OS・Python版での効果は未検証である。既存cProfile値は候補選定の根拠であり、変更後速度の証拠として使わない。
- 4,080局の本番確認比較と分析CLIは実行しない。長時間比較は本人が端末から実行する既定を保つ。

## 所要時間の目安

前回の6局cProfileは約10分7秒だったが、今回はprofileを再実行しなかった。変更前再生は164.437秒、変更後は100.908秒で、二回合計265.345秒（約4分25秒）。変更前後一回ずつの値であり、全比較への一般化はしない。全体テストは変更前894件/58モジュール・22.290秒、変更後895件/58モジュール・21.427秒だった。4,080局の比較は実行していない。
