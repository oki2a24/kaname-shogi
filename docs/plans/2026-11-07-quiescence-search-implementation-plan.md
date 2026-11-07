# 静止探索部品と小局面診断の実装計画

> **AIエージェントへの指示** この計画をタスクごとに実装するには`executing-plans`または`subagent-driven-development`スキルを使用し、以下のチェックボックスで追跡する。本人は2026-11-07に計画全体を承認済み。製品コード・テストの変更は承認後に開始する。

**目標** 同じ時計予算の下で、現行αβ最大4手と静止探索追加2手・4手を小局面から診断できるようにする。

**アーキテクチャ** 共通探索の末端に任意の追加探索操作を接続し、将棋固有の静止探索は専用モジュールへ置く。合法手生成・非破壊遷移・駒得・反復深化・時計予算は既存部品を利用する。診断用コマンドが3方式の一回探索と計測表示を担当する。

**技術スタック** 現行READMEのPython 3.14以上、標準ライブラリ、unittest、固定Ruff 0.16.10。今回環境はPython 3.15.2。

**仕様** [承認済み設計](2026-11-07-quiescence-search-design.md)。設計全体承認後に作成し、本人が2026-11-07に全体承認した実装計画。作業先は`/Users/oki2a24/kaname-shogi`、ブランチ`codex/quiescence-search-design`。

## グローバル制約

- 対話・説明・docstring・学習記録は日本語。英語の型はデータか操作かを説明する。公開インターフェースに引数・戻り値・副作用・前提と理由を記す。
- 既存入口は追加末端操作なしを既定とし、通常のevaluateは採点操作のままにする。
- 通常探索は最大4手、駒得評価と現行時間配分を使う。王手なしの追加候補は合法な駒取り、王手中は合法な回避手。
- 追加上限は2手・4手、王手回避も一手として減らす。上限王手中は詰み確定以外を未完了にする。
- 同じ停止制御を末端まで使い、抑制を優先し、未完了反復の手や評価を採用しない。合法予備手と最後の完了反復を利用する。
- 既存worktree・cloneを増やさず同じcheckoutで進める。main統合とpushは本人の別承認を待つ。
- 計画承認後も、各振る舞いのRed理由、最小実装、Green、Refactorの要否、独立レビュー、記録を順に行う。読み込みエラーだけでRed完了としない。
- import変更時に`.venv/bin/ruff check --select I --fix .`、続いてformat、check、差分確認、関連テスト。通常の全体は`.venv/bin/python3 scripts/run_tests_parallel.py`。検査を回避しない。
- 今回の成果は探索部品と診断入口。対局候補接続・長時間比較は後続設計の対象。

## レビューフォーカス

1. 上限で王手中の枝が一つだけ現れる場合も、反復全体が未完了となり旧完了手へ戻る（Task 1・3）。
2. 後手開始でもstand patの最大・最小と詰み優先が反転し、捕獲を強制しない（Task 2）。
3. 上限到達と同時の停止・抑制で抑制が最優先となり、共有停止要求を汚さない（Task 1〜3）。
4. 合駒・逃げだけの王手回避、捕獲成り・不成、駒取りを伴わない成りの区別（Task 2）。
5. 診断コマンドが未完了訪問数を落とさず、故障を入力エラーや通常停止へ変換しない（Task 4）。

## 型と接続の具体化

以下の名前は計画で具体化した提案。実装中に契約変更が必要なら先に理由を説明して計画を更新する。

- `search/result.py`に不変データ`QuiescenceLimit`を追加する。値・手を持たない専用の未完了マーカー。`ControlledCompletion.QUIESCENCE_LIMIT`は追加上限未完了を示し、結果の手は最後の完了反復か合法予備手と一致する。抑制時は既存のSUPPRESSEDと手なしを優先する。
- `ControlledSearchOperations[N, M]`の末尾に既定Noneの`search_leaf`を追加する。型は`Callable[[N, NodeInspection[M], Score | None, Score | None, SearchControl], Score | SearchInterrupted | QuiescenceLimit] | None`。順に局面、調査済み情報、下限、上限、停止制御を受ける操作。準備・調査・評価の既存位置引数を維持する。
- 共通探索は終端判定を先にし、深さ0で`search_leaf`があればそこへ委譲する。なければ既存evaluate。追加操作を使う呼出しは制御付き探索とし、None制御での追加操作呼出しは入力不正として扱う。Scoreの開始側視点と境界はそのまま渡す。
- `search/diagnostics.py`に可変計数データ`SearchCounters(normal_nodes: int = 0, quiescence_calls: int = 0)`を置く。診断以外はNoneとして計測を任意にする。正常・中断を問わず実際に局面調査へ入った回数を計数する。停止確認で調査前に返ったものは含めない。根の予備手準備や合法手生成内部の再帰は計数外。
- `shogi.make_controlled_operations(perspective: Side, *, counters: SearchCounters | None = None)`に任意の通常調査計数を加える。初期prepareは計数しない。静止探索内部では計数なしの基礎操作を使い、quiescence_callsで別計数する。
- `quiescence.search(position: Position, inspected: NodeInspection[Move], remaining: int, lower: Score | None, upper: Score | None, control: SearchControl, operations: ControlledSearchOperations[Position, Move], *, counters: SearchCounters | None = None) -> Score | SearchInterrupted | QuiescenceLimit`を追加する。既に調査した根の合法手と終端評価を受け取り、根の合法手生成を重複しない。子では基礎操作のinspectを使う。操作は入力を変更しない。
- `shogi.make_quiescence_operations(perspective: Side, additional_depth: int, *, counters: SearchCounters | None = None) -> ControlledSearchOperations[Position, Move]`が上記をsearch_leafへ接続する。追加深さはboolを除く非負整数。診断の選択値は2・4に限定し、内部の0は境界検証に使う。
- `iterative_deepening.search_controlled`に既定Noneの`on_iteration: Callable[[int, IterationResult[M] | SearchInterrupted | QuiescenceLimit], None] | None`を追加する。各開始した反復の終了直後に一度だけ観測し、表示や再探索はしない。反復開始前の時間停止では架空の反復記録を作らない。観測中の例外は故障として伝える。抑制確認は最終結果確定時にも行う。

## Task 1　末端操作と未完了結果を既存探索へ接続する

**変更ファイル** `search/result.py`、`search/contracts.py`、`search/core.py`、`search/alpha_beta.py`、`search/minimax.py`（型注釈が必要な範囲）、`search/iterative_deepening.py`。

**テスト** `tests/test_search_quiescence_boundary.py`を新規作成。既存の制御付き結果・αβ・minimax・反復深化テストを併用する。将棋に依存しない小さい手作り木を使う。

- [x] A/Bの独立評価木で既定B・追加末端ありA `(0, 4)` をαβ・minimax双方で確認。終端葉にはhookを呼ばない。非None下限・上限と同一SearchControlの受渡しも検証。
- [x] 新しい型を参照するテスト外枠を作り、読み込みエラーではなく、未接続時に期待手Aを得られないAssertionErrorを確認してから最小実装。
- [x] `QuiescenceLimit`を両固定深さ方式・反復へ伝播。深さ2はB枝を完了した後にA枝だけを未完了にし、状態・完了深さ1・前回評価`(0, 5)`・前回手Bを保持。予備手Aと区別する。`SearchInterrupted`と上限未完了を同じ理由へ潰さない。
- [x] 制御付きテスト木で初回未完了は合法予備手A、上限結果は共有停止状態を変えない、返却境界の抑制は手を隠すことを確認。時計は時刻0を返す制御を使用。
- [x] マーカーの不変・値/手なし、終端優先、既定Noneの旧結果、観測の完了/通常中断/上限未完了の回数と順序、開始前停止での非呼出し、例外伝播を確認。
- [x] 関連46テスト成功。Refactor不要と判断。独立レビュー2回でCritical 0・最終Important 0。初回Importantのケース不足を修正し、上限境界とテスト説明も補強。全体1,115 tests/93 modules成功。整形・check・差分確認後、学習記録へ追記してコミット。

Task 1の主要なassertの形は次のとおり。`baseline`と`extended`は本文のA/B木を深さ1で探索した結果、`limited`は深さ2の枝だけを未完了にする反復結果である。

```python
self.assertEqual(baseline.move, "B")
self.assertEqual(extended.move, "A")
self.assertEqual(extended.score, (0, 4))
self.assertEqual(limited.completion, ControlledCompletion.QUIESCENCE_LIMIT)
self.assertEqual(limited.last_completed.depth, 1)
self.assertEqual(limited.move, limited.last_completed.result.move)
self.assertEqual(suppressed.completion, ControlledCompletion.SUPPRESSED)
self.assertIsNone(suppressed.move)
```

## Task 2　将棋の静止探索と計数を実装する

**作成** `kaname_shogi/search/quiescence.py`、`kaname_shogi/search/diagnostics.py`、`tests/test_search_quiescence.py`。
**変更** `kaname_shogi/search/shogi.py`。

**消費・生産** 上記のsearch_leaf契約とQuiescenceLimitを消費し、quiescence.search、make_quiescence_operations、任意のSearchCountersを提供する。

- [x] 既存の`tests/test_search_shogi.py`のKINGS・MATE・RECAPTUREと盤面構築方法を読む。実盤面の小さい捕獲例を構成し、合法手を一覧で照合して、期待する手順・終端・駒得をテスト内へ明記する。説明用の角8・飛車10を製品の駒価値として流用せず、現行の参考点数で手計算する。
- [x] 振る舞いごとにテストを作りassertion failureを確認し、最小実装で通す。対象は、取り返しで損するのでstand patを選ぶ、別マスの捕獲、二手後に得が消える、最大側・最小側の反転、捕獲成り・不成、非捕獲成りを除くこと。`score == 手計算値`をassertし、単なる「基準より良い」では済ませない。
- [x] 王手回避が玉移動だけ・合駒だけ・捕獲だけの各小局面を作る。手番反転も確認する。上限0・王手中で回避ありはQuiescenceLimit、上限0でも詰みは詰みScore、王手なし上限0は終端確認後の静的評価を期待する。
- [x] 既存合法手・局面遷移を利用して、候補の判別を`isinstance(move, BoardMove)`と`position.board.piece_at(move.destination)`によって行う。王手中は候補を捕獲へ絞らない。上限は遷移ごとに減らす。
- [x] prepare・調査・遷移・再帰の前後で停止契約を検査する。偽時計と停止要求で時間中断／抑制／上限を個別に検出し、同時なら抑制を優先する。全合法手生成の途中の中断も伝える。
- [x] 入力の盤面・持ち駒のスナップショットが一致すること、異なる順序で兄弟枝を調べても評価が一致することを確認する。小局面の全探索した静止木とαβ版の評価一致を期待値の補完に使う。
- [x] 計数の独立期待値は手作り木・操作呼出し回数で確認する。通常末端と静止入口は両計数に現れうると明記し、合計を異なる局面数と呼ばない。計数なしの結果も同じであることを確認する。
- [x] `PYTHONPATH=tests .venv/bin/python3 -m unittest test_search_quiescence test_search_shogi test_search_shogi_controlled -v`を実行。Refactorの要否、独立レビュー、学習記録、整形・検査後に当該変更をコミットする。

既存RECAPTURE教材の局所値は、開始13、`5e5d`後15、`5c5d`後−15、`4e5d`後3である。合法手を照合して、この値を境界ケースに再利用する。たとえば最初の捕獲後の局面に追加上限0を与え、王手なしを確認した上で次のassertを置く。追加探索全体の最善値は、この一本の手順だけから推定せず全候補を点検して別に決める。

```python
self.assertEqual(raw_ops.evaluate(after_first_capture), (0, 15))
self.assertEqual(qsearch_at_zero, (0, 15))
self.assertIsInstance(checked_nonmate_at_zero, QuiescenceLimit)
self.assertEqual(mated_at_zero, (-1, 0))  # 開始側が詰まされている教材
self.assertEqual(snapshot(position), before_snapshot)
```

## Task 3　反復深化を通した3方式と中断結果を検証する

**変更** `tests/test_search_quiescence_boundary.py`、`tests/test_search_quiescence.py`。必要最小限の既存接続修正のみ。

**消費** `iterative_deepening.search_controlled(position, 4, operations, control, on_iteration=...)`。基準はmake_controlled_operations、候補はmake_quiescence_operationsの2・4。

- [x] 同じ実局面で、基準／2／4の手・評価・完了反復を比較する。差が出る例と、差が出ない玉だけの例を両方用意する。通常深さ1・2・3にも末端探索が適用され、4手完了まで待って追加するだけの実装を検出する。
- [x] QuiescenceLimitで最後の完了反復へ戻る実局面を作り、結果由来と観測記録をassertする。未完了をCOMPLETEと誤報する変異を検出する。追加深さ0を使い、初回反復が未完了の実局面で完了反復がないことも直接検査する。
- [x] 完了反復の累計と全反復の実計数を区別する。手作り木で通常調査の反復差分3・5、累計8を操作呼出し回数と照合する。実局面では未完了反復分も含む計数を検証し、未完了計数を落とす誤りを変異で検出する。
- [x] 呼出し例外を上限未完了や通常停止へ変換しないことを確認する。既存game_search・USI・CLIは既定経路で従来の結果型を受け取ることを関連テストで確認する。
- [x] `PYTHONPATH=tests .venv/bin/python3 -m unittest test_search_quiescence_boundary test_search_quiescence test_game_search test_search_iterative_deepening_controlled test_cli test_usi_engine -v`。Refactor確認、独立レビュー、記録、整形・検査後にコミットする。

## Task 4　一局面の診断コマンドと利用案内を追加する

**作成** `kaname_shogi/search/diagnose_quiescence.py`、`tests/test_search_diagnose_quiescence.py`。
**変更** READMEの開発用入口、文書索引、学習記録、再開案内。既存診断のSFEN解析・手／評価表示を再利用する。

**公開入口** `main(argv: list[str] | None = None) -> int`。`--sfen`、`--variant {baseline,q2,q4}`、`--remaining-ms`、`--byoyomi-ms`を必須とする。通常上限深さは4で固定。時計設定の読込と予算計算は既存公開操作へ委譲する。

**内部境界** `_prepare_inputs(sfen: str, variant: str, remaining_ms: int, byoyomi_ms: int, config: TimeManagementConfig) -> tuple[Position, SearchBudget]`、`_run_search(position: Position, variant: str, budget: SearchBudget, *, now_ns: Callable[[], int] = time.monotonic_ns) -> DiagnosticResult`。DiagnosticResultは同ファイルの不変データで、制御付き結果・経過ns・各反復の計数差分と結果・全体計数を保持する。操作セット構築後から予備手準備・反復・観測記録保存まで計時し、結果文字列の整形とstdoutは計時外。

- [x] パーサの必須・負数・bool相当の直接呼出し・未知variant・不正SFEN・不正時計設定をテストし、入力失敗2／正常0／SIGINT130の契約を固定する。設定故障はstderrと非0にし、内部探索のValueError等は入力エラー境界で握りつぶさない。
- [x] 基準の実探索結果を既存反復深化と一致させ、候補2／4の接続が正しい値で一回呼ばれることを確認する。偽時計で経過ns、抑制・追加上限・停止・完了・合法手なしの表示、手の由来と完了記録なしをassertする。
- [x] 日本語表示は「方式」「目標期間(ms)」「上限期間(ms)」「消費時間(ms)」「終了状態」「選択手」「手の由来」「完了した通常深さ」「各反復の通常調査回数」「各反復の静止探索呼出し回数」「全体の各計数」を含む。追加上限未完了を時間切れ負けと表示しない。
- [x] 実プロセスで玉だけのSFEN `8k/9/9/9/9/9/9/9/K8 b - 1` を3方式各1回、`--remaining-ms 600000 --byoyomi-ms 30000`で実行する。同じ3方式を残り0・秒読み30000でも各1回実行する。6プロセス全て深さ4完了。各プロセスの外側タイムアウト90秒内、終了コード0。
- [x] Task 2で用意した捕獲小局面から1例を固定し、同じ2時計条件・3方式を各1回だけ実行した。6プロセス全て90秒以内・終了コード0。q2は深さ1・2完了後に深さ3の静止探索上限、baselineとq4は深さ4完了。時間・計数の実測は学習記録に記載した。
- [x] `PYTHONPATH=tests .venv/bin/python3 -m unittest test_search_diagnose_quiescence test_search_run_controlled_iterative -v`は29件成功。Ruff import整理・format・check、`git diff --check`、全体1,152 tests/95 modulesが27.914秒で成功。
- [x] 代表変異としてstand patの候補除外、min側でmax使用、王手回避を捕獲限定、上限を一手早める、未完了を完了扱い、中断反復の計数記録を省く変異を隔離コピーで一件ずつ試し、各対象assertion failureを確認した。変異は全て一時コピーだけに置き、製品ソースは変更していない。
- [x] Refactorの要否を確認後、独立した最終コードレビューを行いCritical・Important・Minorと対応を学習記録へ残す。Critical／Importantは解消して再検証・再レビューする。Refactor不要、Critical 0・Important 0・Minor 0。
- [x] 知識メモは追加不要と判断した。README・索引・学習記録・再開案内を更新し、文書リンク・差分確認後にコミットした。
- [ ] main統合は別途承認後に行い、取り込み先検証と最後の理解確認を実施する。今回の実装範囲には含めず、次の判断待ち。

## 実施前の点検と未検証範囲

- 実装着手時にGit状態・HEAD・Python・Ruff固定版・hooksPathを再照合する。既存未追跡保護物を保持する。製品変更前の全体baselineを一回取得する。
- 各TaskのRed理由、Green結果、Refactor判断、レビュー結果を記録する。実装は`executing-plans`でインライン実行し、各Task後は`requesting-code-review`の新鮮なサブエージェントによる独立レビューを行う。これはリポジトリ方針のTaskごとの独立レビュー要件を満たすための実行方式。
- 単独の小局面テストは具体的な誤実装の検出を担い、既存の探索・合法手・USI・CLIテスト全体は旧経路と基本契約を補完する。件数や全体成功だけで十分としない。
- 棋力、10分30秒の一局全体、秒読み中の連続実戦、ShogiHome実機、任意局面の時間内応答、全OS、探索木内部の千日手判定は今回の成果だけでは未検証。静止探索の循環は追加手数上限と共有停止制御で有限化する。
- 実装前baselineとして`.venv/bin/python3 scripts/run_tests_parallel.py`を2026-11-07に実行し、1,101 tests/92 modulesが19.556秒で成功。製品コード・テストの変更前に取得した。
