# 反復深化と既存時間制御の接続 実装計画

> **AIエージェントへの指示:** 明示承認後に `executing-plans` を使用してこのセッションの主担当が段階的に実装する案。各段階のRefactor要否確認後に `requesting-code-review` で独立レビューを行う。実装の委任はこの計画の前提にしない。

**目標:** 中断時に合法予備手または最新の完了結果を返す、時間制御付き反復深化の探索部品を追加する。

**アーキテクチャ:** 既存SearchControlと予算計算をそのまま使う。合法手生成の目標確認と初手保護を分離し、将棋接続部で完了／中断の別型へ変換する。指定深さの再帰と反復管理は既存入口と共有し、停止なしAPIの契約を保つ。

**技術スタック:** Python標準ライブラリ・unittest・Ruff 0.16.10。現行READMEはPython 3.14以上、今回の `.venv` は3.15.0、Ruff targetはpy314。Python移行やRuff設定変更は行わない。

**仕様:** [承認済み設計](2026-10-18-iterative-deepening-stop-time-control-design.md)。[設計学習・独立レビュー](../learning/iterative-deepening-stop-time-control-design.md)と合わせて読む。

**グローバル制約（設計から抜粋）:**

- 「Random（最弱・既定）、一手駒得、現行二手先読みを維持する。」
- 「通常対局・USI・CLIへの新方式接続、比較コマンドへの時計オプション追加、予算式や設定値変更、時間保証、性能・棋力向上は対象外。」
- 「中断は戻り値で伝える。完了と中断を別の型で表し、戻り値をそのユニオン型とする。共通の親クラスは設けない。」
- 「想定外の例外は原因を保って呼出し元へ伝え、保持手を返して成功扱いにしない。」
- 「開始時刻や制御を深さごとに作り直さない。」
- 「訪問累計は従来どおり完了反復の和。予備手確保・中断反復・比較用探索は含めない。」
- 「共有本体へ渡すところで既存の操作を成功結果として扱い、停止なしの公開戻り値へ中断型を追加しない。」

## 承認段階と進捗

2026-10-18、計画作成の依頼を受領。本人「承認する。段階的な実装を進めて」により本計画も**明示承認済み**。以下は承認した実施手順。実際のRed/Green・初回Green・レビュー・変異の結果は[学習・実施記録](../learning/iterative-deepening-stop-time-control-implementation.md)へ分けて記録した。main取り込みは別承認。

- [x] 開始時Git・引き継ぎ・設計・コード・テストの照合。
- [x] 契約・対象ファイル・検証を対応付けた計画草案作成。
- [x] 独立計画レビューと必要な修正。初回Minor 1を補強し、再確認で未解決Critical/Important/Minorすべて0。
- [x] 本人による計画の明示承認（2026-10-18）。
- [x] タスク1〜5のTDD・検証・各段階の独立レビュー。
- [x] 全体レビュー・記録・通常コミット。
- [x] main取り込みの別承認と取り込み先検証。
- [x] 最後の理解確認一問への回答・補足の記録（初回補足と再確認を含む）。

開始HEAD `6418379`、cleanなmain（origin/mainより4コミット先）から、同じディレクトリ `/Users/oki2a24/kaname-shogi` に作業ブランチ `codex/iterative-deepening-stop-time-control-implementation` を作成。別worktreeなし。過去の513件成功等は今回の実測ではない。

## レビューフォーカス

1. 最初の合法手が打ち歩で、その合法性確認中に停止する：下位へ通常停止保護を伝え、抑制は中断する（タスク2・4）。
2. 深さ3で前回と違う暫定最善手を得てから中断する：深さ2の手・評価・累計を一組で保持する（タスク5）。
3. 根の最終確認直前と完了確定直後で通常停止する：前者だけ未完了、後者は記録を保持する（タスク3・5）。
4. 準備や再帰の戻り値が契約に反する：未確定を投了へ変換せず、prepareのSTOPは契約違反として拒否する（タスク1・5）。
5. 停止なし入口から共有本体を通る：遅延取得・例外・優先手順序・全幅のroot_scores・訪問数が変わらない（タスク3・5）。

## ファイルと共通化の境界

| ファイル | 変更責務 |
| --- | --- |
| `kaname_shogi/search/result.py` | 不変なSearchInterrupted・ControlledCompletion・ControlledSearchResultと構築時検査 |
| `kaname_shogi/search/contracts.py` | PreparedRoot・AdvancedNode・ControlledSearchOperations |
| `kaname_shogi/movegen.py` | 停止可能な公開3操作とMoveApplicationResult。既存非公開本体を共用 |
| `kaname_shogi/search/core.py` | 一つの再帰本体で完了／中断を処理。旧操作を成功値へ適合 |
| `kaname_shogi/search/alpha_beta.py` | 制御付きの指定深さ入口を追加 |
| `kaname_shogi/search/shogi.py` | 将棋用制御付き操作セットと型変換 |
| `kaname_shogi/search/iterative_deepening.py` | 共通反復、初回準備、四状態の最終結果 |
| `tests/test_search_controlled_result.py`（新規） | 新データの組合せ・不変性 |
| `tests/test_search_movegen.py` | 公開境界と既存三方式の回帰 |
| `tests/test_search_alpha_beta_controlled.py`（新規） | 数値木で再帰中断と確認点 |
| `tests/test_search_shogi_controlled.py`（新規） | 将棋接続と非破壊・先後・打ち歩詰め |
| `tests/test_search_iterative_deepening_controlled.py`（新規） | 準備・期限・結果保持・確定境界 |
| `tests/search_tree_support.py` | 必要な制御付き操作の薄い適合と数値木。探索アルゴリズムは実装しない |

既存 `test_search_control.py`、`test_search_alpha_beta.py`、`test_search_minimax.py`、`test_search_iterative_deepening.py`、`test_search_shogi.py`、比較・USI・CLIテストを回帰に使う。既存テストを新構造へ合わせるだけの弱体化はしない。`search_control.py`、`time_management.py`、設定、USI・CLI・比較入口の製品変更は予定しない。

## 共通の実行規律（承認後のみ）

各タスク内でも振る舞いを一つずつ進める。以下は承認前に定めた規律で、承認後に実行した。

1. 指定したテスト名・独立期待値のアサーションを書く。新APIの読込みに必要な宣言だけを先に置く場合も、実装済みと扱わない。
2. 対象テストを実行し、期待した振る舞いのアサーションがFAILすることと理由を記録する。ImportError・SyntaxError・単なる未定義名だけでRed完了としない。
3. 対象の最小実装を行い、同じテストが成功することを確認する。既存処理の公開化で初回からGreenならその事実を記録し、偽のRedを作らず、代表変異で検出力を補う。
4. import変更時は `.venv/bin/ruff check --select I --fix .`、続いて `.venv/bin/ruff format .`、`.venv/bin/ruff check .`、差分確認、指定の回帰検証。
5. Refactorの要否を検討し、変更した場合は関連検証を再実行。変更不要の場合も理由を記録する。
6. 新鮮な独立レビュアーへ対話履歴を渡さず、契約・差分・検証・未検証を渡す。Critical/Importantは修正・再検証・再レビューし、Minorも採否と理由を記録する。
7. 学習記録へ実績を追記し、`git diff --check`、差分確認後、対象ファイルを明示してステージし通常コミット。フックを回避しない。各段階でmainへは取り込まない。

個別実行は `PYTHONPATH=tests .venv/bin/python -m unittest <module>.<class>.<test> -v`。各タスクの回帰は以下のdiscoverコマンドを使う。新規テストのクラス名は各ファイルの責務に合わせ、表中のメソッド名を使う。日本語docstringに振る舞いと検出対象を書く。

## タスク1：完了と中断を区別するデータ契約

**ファイル:** result.py、contracts.py、新規test_search_controlled_result.py。

**消費:** `SearchSignal`、既存 `Score`・`SearchResult[M]`・`IterationResult[M]`・`NodeInspection[M]`。

**生産（すべてデータ、操作ではない）:**

- `SearchInterrupted(reason: SearchSignal)`：STOP/SUPPRESSだけ許可。評価・手・訪問数の欄や評価取得メソッドなし。
- `ControlledCompletion`：COMPLETE / NO_LEGAL_MOVE / STOPPED / SUPPRESSED。
- `ControlledSearchResult[M](completion: ControlledCompletion, move: M | None, last_completed: IterationResult[M] | None)`。
- `PreparedRoot[M](move: M | None)`：最初の合法手または手なし確定。
- `AdvancedNode[N](node: N)`：正常適用した次局面。
- `ControlledSearchOperations[N,M](prepare, inspect, advance, evaluate)`。Callableの引数・戻り値は設計の対応表をそのまま採用：prepare(N, SearchControl)→PreparedRoot[M] | SearchInterrupted、inspect(N, SearchControl)→NodeInspection[M] | SearchInterrupted、advance(N,M,SearchControl)→AdvancedNode[N] | SearchInterrupted、evaluate(N)→Score。

全新データをfrozenとする。resultはcontractsをimportせず循環を避ける。外側結果は未知状態・不正な記録型・四状態の不整合をValueErrorで拒否する。COMPLETEの手と記録内の手はともに非Noneで一致、STOPPEDは手必須で記録ありなら一致、NO_LEGAL_MOVEは両方None、SUPPRESSEDは手None。合法性と上限深さの一致は探索側で検証し、データ型へ局面や上限を持ち込まない。

| テスト名 | 独立期待値・主アサーション |
| --- | --- |
| `test_interruption_accepts_only_stop_or_suppress` | STOP/SUPPRESSでreason一致。CONTINUE・None・文字列は `assertRaises(ValueError)` |
| `test_interruption_has_no_evaluation_and_is_frozen` | `assertFalse(hasattr(value, "score"))`、move・visited_nodesもなし。reason代入はFrozenInstanceError |
| `test_four_completion_states_and_invalid_combinations` | 記録 `IterationResult(2, SearchResult((0,1),"B",7,None),10)` を用い四状態の有効例を構築。不一致手A、COMPLETEの欠落記録・手なし記録、STOPPEDのNone手、NO_LEGAL_MOVEの手または記録、SUPPRESSEDの手、未知状態、不正記録型を個別拒否 |
| `test_success_wrappers_and_operations_are_immutable` | PreparedRoot(None)/PreparedRoot("A")、AdvancedNode(node)の値と同一性。操作セット・終了結果も欄への再代入を拒否 |

- [x] 上表の契約ごとのRed→最小実装→Greenを確認。単純宣言・既存再利用の初回Greenは実施記録で区別。
- [x] `.venv/bin/python -m unittest discover -s tests -p 'test_search_controlled_result.py' -v` が失敗0。
- [x] Refactor点検・独立レビュー・記録・通常コミット。

## タスク2：合法手生成と適用の公開境界

**ファイル:** movegen.py、test_search_movegen.py。

**消費:** 既存 `_legal_moves_controlled`、`_has_legal_move_controlled`、`_apply_drop_controlled`、`_position_after_move_controlled` とSearchControl。

**生産（操作）:**

- `legal_moves_controlled(position: Position, *, control: SearchControl, include_target: bool=False, protect_first_legal: bool=False) -> LegalMovesResult`
- `first_legal_move_controlled(position: Position, *, control: SearchControl, protect_first_legal: bool=False) -> LegalMovesResult`
- `position_after_move_controlled(position: Position, move: Move, *, control: SearchControl) -> MoveApplicationResult`
- `MoveApplicationResult(completed: bool, position: Position | None)`（不変データ）：TrueならPosition、FalseならNoneだけ許可。不正組合せと非boolはValueError。

共通生成本体へ `include_target=False` を追加する。既存root指定は維持し、目標は `root or include_target`、根の保護は `(root or protect_first_legal) and not moves` として最初の確保までに限定する。下位の合法性調査へ渡す保護は、その一手を確定する間維持する。公開全生成はroot=False、打ち歩詰め確認True。最初の取得は `_first_only=True` の同じ本体を利用し、完了時0/1手、追加候補を調べない。適用は既存の対を公開データへ包むだけで規則をコピーしない。

| テスト名 | ケースと主アサーション／検出対象 |
| --- | --- |
| `test_public_generation_separates_target_and_protection` | 予算(10,20)・now=10ms、include_target=Falseで全生成完了、Trueで未完了。開始stopで保護Falseは空の未完了、Trueは先頭合法手確保後に未完了。`moves == (BoardMove(Square(2,7),Square(2,6),False),)`／目標と保護の再結合・全探索保護を検出 |
| `test_first_legal_finishes_without_later_trials` | 二歩教材の先頭だけ返し、7筋候補の適用呼出しなし。空盤はTrue/()。0予算と開始stopでも保護ありなら同じ確定結果 |
| `test_public_first_protection_reaches_pawn_defense` | 既存uchi(side)教材の先後・合法歩打ち／打ち歩詰めを対照。根候補を歩打ちに絞る既存操作境界を利用し、実際の防御調査でstop／抑制。通常stopでは合法手確保または手なし確定、抑制では `completed is False`。元盤面・両持駒・手番不変 |
| `test_public_application_returns_only_complete_position` | 盤上手・成り・打ちの成功は独立Position。実適用途中のstop／抑制はFalse/None。未知手TypeError・違法手ValueError・故障はそのまま |
| `test_application_result_rejects_inconsistent_state` | True/None、False/Position、1/Position、True/不正型を拒否、frozen確認 |

- [x] 公開境界の上表を一件ずつRed/既存初回Greenの区別→最小実装→Green。
- [x] `.venv/bin/python -m unittest discover -s tests -p 'test_search_movegen.py' -v`。既存root・通常三方式の停止・抽選契約も失敗0。
- [x] Refactor点検・独立レビュー・記録・通常コミット。

## タスク3：指定深さ探索の共有本体へ中断を伝播

**ファイル:** core.py、alpha_beta.py、新規test_search_alpha_beta_controlled.py、必要なsearch_tree_support.py。

**消費:** タスク1の型とSearchControl。

**生産:** `alpha_beta.search_controlled(node, depth, operations: ControlledSearchOperations[N,M], control: SearchControl, *, preferred_move=None) -> SearchResult[M] | SearchInterrupted`。

内部は `core._search(node, depth, operations, control: SearchControl | None, *, pruning, preferred_move=None)` に再帰を一つだけ置く。旧 `core.search` は停止なし操作を成功値へ適合しcontrol=Noneで呼ぶ。制御付き `core.search_controlled` は同じ本体を呼ぶ。旧公開戻り値はSearchResultのままとし、停止なし経路に中断が来ない前提を内部で確認する。制御なしのために新SearchControlや時計を生成しない。

再帰の返却は `tuple[Score, M | None] | SearchInterrupted`。調査前後、適用前後、評価前後、子からの復帰後、根の結果生成直前で確認する。全て目標False・保護False。中断を先に判別して直ちに伝播し、比較・best更新・候補継続をしない。優先手は調査完了後だけ照合。枝刈りは完了、root_scoresは全幅だけ、visitsの既存定義を維持。prepareはこの入口では呼ばない。

| テスト名 | ケースと主アサーション |
| --- | --- |
| `test_controlled_search_matches_hand_calculated_tree` | two_level([3,5],[-2,10])で `(score,move,visits)==((0,3),"A",6)`、root_scores=None。最小側・同点・深さ0・終端優先も既存の独立数値で対照 |
| `test_inspect_advance_and_recursive_interrupt_propagate` | STOP/SUPPRESSを調査・適用・孫から返す。最大/最小節点、先頭/中間/末尾候補を小木で代表化。`assertIs(result, interruption)`、後続inspect/advance/evaluate履歴なし。中断を比較する誤りを検出 |
| `test_stop_at_each_operation_boundary` | 実SearchControlと操作ラッパーで開始前、調査後、適用後、評価後、子復帰後にstop。適用前・評価前・根最終確認だけは確認点を識別する制御テストダブルで狙い撃ち。期待はSearchInterrupted(STOP)、未実行操作の履歴なし。単なる最終手一致だけにしない |
| `test_target_is_ignored_but_maximum_stops_inside_depth` | 10/20ms、評価操作で時計を10msへ進めても完了。20ms直前は完了、一致・直後は中断。sleepなし |
| `test_preferred_move_validation_waits_for_completed_inspection` | 不在優先手でも調査中断なら中断、調査完了なら深さ0/終端もValueError。既存順序を変更しない |
| `test_depth_validation_precedes_operations` | -1/True/1.5/NoneをValueError、操作履歴空。0は有効 |
| `test_faults_are_not_converted_to_interruption` | inspect・advance・evaluate・now_nsから同じRuntimeErrorインスタンスを送出、`assertIs(caught.exception, error)`。ValueErrorとKeyboardInterruptも代表経路で伝播 |

- [x] 上表の契約ごとのRed→最小実装→Greenを確認。
- [x] `.venv/bin/python -m unittest discover -s tests -p 'test_search_alpha_beta*.py' -v`、同じコマンドのpatternを `test_search_minimax.py` にして既存全幅も失敗0。
- [x] Refactor点検・独立レビュー・記録・通常コミット。

## タスク4：将棋操作の制御付き適合

**ファイル:** shogi.py、新規test_search_shogi_controlled.py。

**消費:** タスク1・2の公開型／操作、既存評価・王手確認。

**生産:** `make_controlled_operations(perspective: Side) -> ControlledSearchOperations[Position, Move]`（操作）。

prepareはfirst_legal_move_controlledへ保護True、inspectはlegal_moves_controlledへ目標False・保護False、advanceはposition_after_move_controlledへ同じ制御を渡す。完了なら対応する成功型、未完了なら `control.check()` で抑制を再確認しSUPPRESSなら抑制、それ以外はSTOPとして返す（未完了を継続へ戻さない）。評価と詰みの開始側視点の決定を旧セットと共有する小さな内部補助にまとめる。手があるとき王手の再調査をせず、手なしは既存の勝敗／通常点規則。prepareのSTOP契約違反検出は外側タスク5が行う。

| テスト名 | ケースと主アサーション |
| --- | --- |
| `test_prepare_protects_only_first_legal_acquisition` | 開始stop・0予算で確定先頭手、空盤ならPreparedRoot(None)、抑制ならSearchInterrupted(SUPPRESS)。後続inspectには保護なし |
| `test_incomplete_generation_and_application_keep_reason` | 空/一件の未完了一覧ともNodeInspectionにせずSTOP。適用未完了はAdvancedNodeにしない。再確認時の抑制はSUPPRESS、再確認CONTINUEの模擬でもSTOP |
| `test_controlled_shogi_preserves_scores_and_positions` | KINGS先後の評価0、RECAPTUREの開始側13と逆側-13、既存手順15/-15/3、成り12、歩打ち1、詰み±1区分。元局面と両持駒・手番のsnapshot不変、二つの適用結果を相互変更して独立性を確認 |
| `test_public_pawn_defense_interruption_reaches_adapter` | タスク2の実下位調査でのstop／抑制をprepare/inspect/advanceへ接続し、未完了を手なしや合法な子へ変換しない。先後で確認 |
| `test_adapter_passes_same_control_and_faults` | 全操作で `assertIs(received_control, supplied_control)`。生成・適用・評価の故障の同一例外を保持 |

- [x] 上表を一件ずつRed→最小実装→Green。
- [x] `.venv/bin/python -m unittest discover -s tests -p 'test_search_shogi*.py' -v` が失敗0。
- [x] Refactor点検・独立レビュー・記録・通常コミット。

## タスク5：反復の共有と最終結果の選択

**ファイル:** iterative_deepening.py、新規test_search_iterative_deepening_controlled.py、必要なsearch_tree_support.py。

**消費:** タスク1・3・4。

**生産:** `search_controlled(node, max_depth: int, operations: ControlledSearchOperations[N,M], control: SearchControl) -> ControlledSearchResult[M]`（同期操作）。

旧searchの上限検査を `_validate_max_depth(max_depth: int) -> None` へ共有。反復本体 `_iterations(max_depth, search_depth, before_depth)` は深さ・前回手・完了累計を所有し、IterationResultまたは中断を一件ずつ渡す内部iteratorとする。search_depth(depth, preferred)→SearchResult | SearchInterrupted、before_depth()→SearchInterrupted | None。一深さ完了後だけ累計・優先手を更新。旧入口は停止しないbefore_depthと旧alpha_beta.searchを渡し、遅延取得と手なし一件を維持。新入口は同じ制御で目標を確認するbefore_depthとalpha_beta.search_controlledを渡す。外側の準備・終了選択を共通反復へ混ぜない。

新入口の順序：上限検査→prepare一回→手なし/抑制の分岐→反復を消費→終了結果。prepareのSTOPはValueErrorで契約違反とする。根の完了確認はタスク3が担当し、返った完了値を反復記録へ確定する間に通常停止で取消さない。準備が手ありなのに正深さの根完了手がNoneなら操作セットの不整合としてValueError。どの終了経路でも返却前に抑制を再確認し、抑制なら手なしへ上書きする。既に抑制理由を受け取った場合は再確認で抑制を解除しない。

### 数値木と独立期待値

深さ1はA=5/B=3。深さ2はA=min(1,-2)=-2、B=min(2,1)=1でB。各深さ訪問3/7、累計10。深さ2の葉にさらに子を付け、深さ3では先にB枝の値0を完了、続くA枝の値9を得た後、根最終確認で中断する。深さ3を停止なしで完了させた対照はA=9。途中のAと前回Bが異なるので上書きを検出できる。深さ2時点の節点は静的値を使わせ、深さ3の子は終端値にする。

| テスト名 | ケースと主アサーション |
| --- | --- |
| `test_zero_budget_and_initial_stop_return_fallback` | 深さ1呼出しなし、STOPPED/"A"/None。prepareは一回。時計なしなら完了する対照 |
| `test_no_legal_move_has_no_iteration_record` | prepare(None)でNO_LEGAL_MOVE/None/None、反復なし。抑制中断はSUPPRESSED、手なしと区別 |
| `test_rejects_invalid_depth_before_prepare` | 0/-1/True/False/1.5/NoneでValueError、prepare履歴空 |
| `test_preparation_stop_is_contract_error` | prepareがSearchInterrupted(STOP)ならValueError、予備手返却/投了にしない |
| `test_incomplete_deeper_search_keeps_latest_record` | 上記深さ3中断：`(r.completion,r.move,r.last_completed.depth,r.last_completed.result.score,r.last_completed.total_visited_nodes)==(STOPPED,"B",2,(0,1),10)`。抑制版は手None、記録は同じ。中断を早いA枝途中にも注入して同じ保持を確認 |
| `test_target_stops_next_depth_without_discarding_current` | 10/20ms、深さ2途中で10ms到達→深さ2完了B/累計10、深さ3未開始。開始直前の目標-1ns/一致/+1nsと上限-1ns/一致/+1nsを対照化 |
| `test_protection_does_not_restart_and_control_is_reused` | 深さ2の最初のinspect開始時にstop→深さ1の記録保持。実将棋接続でも公開生成へ `protect_first_legal=False` が渡ることと、stop後は最初の候補適用も起きない履歴を確認する。記録保持だけでは調査後チェックに隠れる保護再開を検出できないため、この二つを併せて検査する。全深さ・準備・子で同じ制御。非0原点1秒で期限1.010/1.020秒を維持 |
| `test_final_boundary_distinguishes_stop_and_suppression` | 最終評価後/根最終確認時の停止は未完了。実alpha_betaの完了返却直後にラッパーで通常stop→上限深さならCOMPLETE、さらに深さが残ればSTOPPED、記録保持。同位置または最終返却確認で抑制→SUPPRESSED/None、記録保持。手なし終了の返却直前抑制も確認 |
| `test_searches_do_not_share_control_fallback_or_records` | 第一探索停止、別局面・別制御で第二探索完了。さらに第一の操作内から独立した第二探索を呼び状態混在を検出。手・累計・記録の同一性/不変性を検査 |
| `test_faults_after_completed_depth_remain_faults` | 深さ2まで完了後のprepare以外の各操作・時計故障は例外のまま。開始時prepare故障も同一例外。保持手へのフォールバックで隠さない |
| `test_controlled_shogi_and_legacy_stream_regressions` | 実将棋KINGS先後・成り・打ち・駒取り・終端を小深さで接続。制御なし相当の完了結果を旧入口と比較し、手計算期待値も併用。準備訪問を加算しない。旧遅延取得・優先手受渡し・不変性テストを維持 |

- [x] 表の契約ごとのRed→最小実装→Greenを確認。
- [x] `.venv/bin/python -m unittest discover -s tests -p 'test_search_iterative_deepening*.py' -v` が失敗0。
- [x] `.venv/bin/python -m unittest discover -s tests -p 'test_search*.py' -v` で共有本体・比較・停止の回帰を確認。
- [x] Refactor点検・独立レビュー・記録・通常コミット。

## 検出力・全体レビュー・完了手順

[点検方針](../knowledge/test-coverage-review.md)と `~/.codex/observations/test-driven-development.md` に従い、次の代表変異を隔離コピーで一つずつ試す。作業ブランチの製品コードを変異状態でコミットしない。元のチェックアウトの `.venv/bin/python` を絶対パスで使い、cwd/PYTHONPATHが隔離コピーを指すことを確認する。

| 代表変異 | 対応テストと単独で期待する検出 |
| --- | --- |
| 深さ内でも目標を適用 | タスク3/5の目標中到達が完了せずFAIL |
| 期限の>=を>へ変更 | タスク3/5の期限一致が中断せずFAIL。既存test_search_controlも補完 |
| 初手保護を深さごとに再開、または下位へ渡さない | タスク5の深さ2停止後の候補適用禁止履歴・保護False指定、タスク2/4の歩打ち防御保護がFAIL |
| 中断を空一覧／正常適用へ変換 | タスク3/4の中断型・後続未実行アサーションがFAIL |
| 根の最終確認を削除 | タスク3/5の最終確認だけを狙った停止が完了してFAIL |
| 中断反復の手を採用／訪問を累計へ加算 | タスク5のB・深さ2・評価1・累計10の一組がFAIL |
| 返却直前の抑制確認を削除 | タスク5の完了後／手なし後抑制で手または状態が違いFAIL |

変異ごとに変更箇所・コマンド・意図したFAIL・復元後成功を学習記録へ残す。単独で検出しなければ既存全体が補完するかを区別し、必要な補強と限界を記録。非公開関数の呼出し回数への過度な固定を避け、実操作境界で起こせない最終確認等にだけ制御ダブルを使う。二つの探索方式の結果一致だけを独立期待値としない。

- [x] 代表変異と復元検証を実施。
- [x] `.venv/bin/ruff format --check .`、`.venv/bin/ruff check .`、`git diff --check` を確認。
- [x] `.venv/bin/python -m unittest discover -s tests -v` の全体回帰を実行。三方式・USI・CLIの既存契約も含め、今回の件数と失敗数を記録。
- [x] ブランチ全体を新鮮な独立レビュアーがレビュー。Critical/Important解消と再検証・再レビュー後に文書更新へ進む。
- [x] 学習記録に実変更・設計からの差異・検証・Refactor・各重大度と対応・未解決事項を記録。READMEは部品追加の利用境界だけ、knowledge/search-stop.md・search-comparison.mdは旧入口と新入口の契約を区別して更新。索引・resumeを同期。
- [x] 文書リンク・見出し・差分確認後に通常コミット。mainへ未取り込みであることと作業場所を提示し、別承認を待つ。
- [x] main承認後に元ディレクトリへ統合し、取り込み先でRuff・全体回帰・文書検査。
- [x] 最後の理解確認を一問ずつ出し、初回回答・補足・再確認回答を記録した。

未検証に残すもの：厳密な期限内応答、実時間性能、全局面・全OS・全スケジュール、USIへ新方式を接続した競合、実機対局、棋力、最適予算。注入時計の成功は時間保証ではない。計画レビューは製品検証ではなく、上記の実行実績は承認後に初めて記録する。

## 実行結果と残件（2026-10-18）

タスク1〜5を順に実装・検証・独立レビューし、ca59b63・8d4ced6・73a0264・db31d03・30fe837に保存。最終全体546件31.419秒OK、Ruff整形確認63ファイルとcheck成功。代表変異11件は隔離コピーで意図したassert FAIL・復元後成功。各段階のMinor補強と最終ブランチ全体レビューの結論は学習記録を正本とする。

本人の別承認「yes」後にmainへ80e3db0まで統合し、取り込み先で全体546件30.083秒OK、Ruff・文書検査成功。作業ブランチ削除済み。最後の理解確認は初回補足後の再確認回答を記録して完了。次テーマは本人の選択待ち。検証の時点と履歴は学習記録を参照。
