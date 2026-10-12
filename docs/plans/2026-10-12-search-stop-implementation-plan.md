# 探索停止・途中結果 実装計画

> **AIエージェントへの指示:** 本計画は2026-10-12に本人承認済み。今回は作成・独立レビュー・提示まで。本人の実装開始指示を得るまで、コード・テスト・設定変更、TDD、実装を開始しない。実装時は `executing-plans` または本人が選ぶ `subagent-driven-development` を使用し、チェックボックスで実績を追跡する。main取り込みは別承認。

**目標:** 計算済みの期間とgo読取り時刻から探索を協調停止し、評価完了候補または合法な予備手を返す、独立検証可能な探索部品を作る。

**アーキテクチャ:** `search_control.py` が期限と外部停止要求を扱い、`movegen.py` が中断可能な規則確認・候補評価・最終選択を扱う。従来の公開APIは停止なしの完了契約を保ち、規則・評価の実処理を共有する。今回の実装範囲案は部品までで、USIへの接続は入力並行処理・送信同期・担当回収をそろえる後続計画に分離する。

**技術スタック:** Python 3.9、標準ライブラリのdataclasses・enum・typing・time・threading・unittest・unittest.mock。依存追加なし。

**仕様:** [承認済み全体設計](2026-10-11-clock-input-time-management-design.md)、[確認範囲点検](2026-10-12-clock-input-verification-review.md)、[既存時計接続](2026-10-12-usi-clock-settings-implementation-plan.md)、[予算契約](../knowledge/time-budget.md)。全体設計の承認と本計画の承認を区別する。

**グローバル制約:**

- 「未決定の技術選択や将来の機能を先取りして複雑にしない。」
- 「説明・学習記録・知識メモは日本語で書く。」
- 「テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞い、続く本文に検出したい誤りや背景を書く。」
- 「将来の開発・保守で判断を思い出せるよう、公開インターフェースのdocstringに引数・戻り値・副作用・前提条件と設計理由を記録する。処理を変えたら説明も更新する。」
- 既存の時計解析・設定寿命・四設定・式・精度・暫定値を維持する。CLIの三方式と規則・評価・合法手順序も維持する。

## 範囲と切り出し判断

現在の `run_usi_engine` は同期入力・同期探索で、予算を計算するが停止には使わない。この計画を実装しただけでは、USIの時計付きgoやstopで探索は止まらない。0予算時の「返す手」の契約は今回の探索部品で検証し、実際の `bestmove` 送信は後続接続で検証する。部品完成をUSI時間管理対応と表示しない。

対象は期限判定、通常停止と抑制付き停止の区別、中断伝播、根の予備手確保、完了候補の保持、三方式の結果選択、0予算・時計なしの区別。範囲を切り出すため、単調時刻と停止要求を注入可能な部品にする。同期USIへ期限だけを先に接続する暫定方式は採らない。入力中のquit等を扱えず、承認済み全体設計の抑制・回収契約を満たせないため。

対象外は入力スレッド、探索スレッドの起動・回収、標準入力待機解除、共通受渡し場所、応答の同期・一回送信・flush・故障診断、実プロセスでの探索中入力、計測・対局・最適化・Python更新。これらは削除せず、末尾の後続接続に引き渡す。現在も今回も実時間安全性は未保証。

## 現物・予定ファイル・所有者

2026-10-12開始時：`/Users/oki2a24/kaname-shogi`、`codex/search-stop-plan-handoff`、HEAD `07d8aad`、差分なし。Ruff 0.16.10は固定版一致、core.hooksPathは `.githooks`。同じ作業ディレクトリを使い、別worktreeなし。今回は下記の計画・学習記録と入口文書だけを更新する。

| 将来のファイル | 責務・変更範囲 |
| --- | --- |
| 作成 `kaname_shogi/search_control.py` | SearchControl・SearchSignal。期間から期限への変換、停止要求と判定。movegen/USIをimportしない |
| 変更 `kaname_shogi/movegen.py` | 現在の `_apply_drop`、`_legal_moves`、`_has_legal_move`、`_is_checkmate`、`_position_after_move`、`_two_ply_score`、`choose_move` 周辺に制御付き共通内部境界を作る。規則や点数表は変えない |
| 作成 `tests/test_search_control.py` | 時刻・境界・停止要求の状態遷移 |
| 作成 `tests/test_search_movegen.py` | 中断伝播、予備手、完了候補、0予算、停止なし互換性 |
| 変更が必要な場合のみ `tests/test_movegen.py` | 公開契約の回帰を維持。内部patchの結合箇所を変える場合は検出対象を保ち、理由を記録 |
| 実装時の文書 | 本計画、[学習記録](../learning/search-stop-implementation-plan.md)、新しい探索部品の知識メモ、再開案内・索引。READMEは部品追加とUSI未接続を区別して必要部分だけ更新 |

予備手・評価完了候補は `search_move` の一呼出しのローカル状態として探索担当だけが所有する。制御部品は結果を書き換えない。後続のUSI `SearchContext`（一探索の状態データ）は制御と最終結果を保持し、送信状態・担当寿命を管理する。今回、未使用のUSIコンテキストは作らない。

## データと操作の具体案

下記はすべて新規APIの提案。Python 3.9に合わせOptionalを使い、名前付き結果はfrozen dataclassとする。

| 名前・シグネチャ | 意味と契約 |
| --- | --- |
| `SearchSignal` | 継続/通常停止/抑制付き停止の状態データ。Enumの `CONTINUE` / `STOP` / `SUPPRESS` |
| `SearchControl(budget: Optional[SearchBudget], started_ns: int, *, now_ns: Callable[[], int] = time.monotonic_ns)` | 一探索の制御データと確認操作。読取り済み原点を受け、構築時刻へ置き換えない。started_nsは整数（bool拒否）、負は許す。型違反はValueError。now_nsは同じ単調時計に由来する整数nsを返す関数を前提とする。時計の絶対原点に意味を持たせない |
| `request_stop(*, suppress_response: bool = False) -> None` | 同じ制御に停止要求を記録する操作。反復可。抑制は一度立ったら戻らず、後から通常stopを受けても解除しない |
| `check(*, include_target: bool = False, protect_first_legal: bool = False) -> SearchSignal` | 確認操作。SUPPRESS最優先。予備手確保の保護区間なら通常停止を保留。それ以外は要求済みstop、上限到達、include_target時の目標到達でSTOP。その他CONTINUE |
| `LegalMovesResult(completed: bool, moves: tuple[Move, ...])` | 合法手生成結果データ。中断時も合法と確定した接頭部分だけ使える。空かどうかと完了を別に扱う |
| `HasLegalMoveResult(completed: bool, value: Optional[bool])` | 手あり確認の結果データ。中断はvalue=None。Trueは合法手を一つ確認、Falseは全調査完了の場合だけ |
| `CheckmateResult(completed: bool, value: Optional[bool])` | 詰み判定結果データ。中断はvalue=None。王手でない/玉なしの確定Falseを含む |
| `_ApplicationResult(completed: bool)` | 試し指し・試し打ちの適用結果データ。通常の不合法は従来のValueError、中断はcompleted=False。中断時は渡された局面を変更しない |
| `CandidateEvaluation(completed: bool, score: Optional[tuple[int, int]])` | 一候補の評価結果データ。中断はscore=None。Materialの点も `(0, 駒得差)` へ包み、二手方式の勝ち(1,0)/通常(0,点)/負け(-1,0)の比較を維持 |
| `SearchCompletion` / `SearchResult(completion: SearchCompletion, move: Optional[Move])` | 最終結果データ。Enumは `COMPLETE` / `INTERRUPTED` / `SUPPRESSED`。COMPLETEのNoneだけが全調査による合法手なし。INTERRUPTEDは合法手必須。SUPPRESSEDはmove=Noneで、手なしの意味ではない |
| `search_move(position: Position, policy: MoveSelectionPolicy, rng: random.Random, control: SearchControl) -> SearchResult` | 根の合法手生成から最終選択まで行う操作。局面不変、抽選時だけrngを進める。入出力・設定読込・スレッド生成なし。呼出しごとに予備手・評価済み候補を新規作成 |

`Move` は盤上移動または駒打ちの一手データ、`Position` は局面データ、`MoveSelectionPolicy` は選び方のデータ。`search_move` は手を選ぶ操作であり、選んだ手を元局面に指す操作ではない。

SearchControlは短い専用Lockで停止・抑制フラグの書込み/読取りを同期する。時計関数呼出し・探索・出力・joinの間は保持しない。タイマースレッドは作らず確認点で現在時刻を読む。専用Lockは後続の送信同期Lockを代替しない。部品の結果返却後に抑制要求が確定する競合は、後続の送信前再確認と共通Lockで処理する。

期限は `started_ns + budget.target_ms * 1_000_000` と上限版をPython整数で保存し、現在時刻との `>=` で判定する。floatや秒への変換を挟まない。Noneなら期限なし、SearchBudget(0,0)なら最初の確認から通常停止対象。巨大予算にも独自上限を設けず、有限例で資源耐性は保証しない。

## 中断可能な内部境界

`movegen.py` 内で次の操作を定義する。control=Noneは停止なし。公開 `legal_moves / has_legal_move / is_checkmate / choose_move / apply_drop` のシグネチャ・戻り値・不合法時の例外・入力局面保存を維持する。内部結果を公開戻り値へ読み替えるのは、停止なしで完了した場合だけ。既存 `_apply_drop` 等は共通内部処理の通常完了側を使い、規則・評価のコピーを別に作らない。

| 操作 | シグネチャ・責務 |
| --- | --- |
| 合法生成 | `_legal_moves_controlled(position: Position, *, check_uchi_fuzume: bool, control: Optional[SearchControl], root: bool = False, protect_first_legal: bool = False) -> LegalMovesResult` |
| 手あり | `_has_legal_move_controlled(position: Position, *, check_uchi_fuzume: bool, control: Optional[SearchControl], protect_first_legal: bool = False) -> HasLegalMoveResult` |
| 詰み | `_is_checkmate_controlled(position: Position, *, check_uchi_fuzume: bool, control: Optional[SearchControl], protect_first_legal: bool = False) -> CheckmateResult` |
| 駒打ち | `_apply_drop_controlled(position: Position, piece_type: BasicPieceType, destination: Square, *, check_uchi_fuzume: bool, control: Optional[SearchControl], protect_first_legal: bool = False) -> _ApplicationResult`。試行局面で安全/打ち歩詰め確認を完了後にだけpositionへ適用 |
| 一手適用 | `_position_after_move_controlled(position: Position, move: Move, *, control: Optional[SearchControl]) -> tuple[_ApplicationResult, Optional[Position]]`。未知手型TypeError/不合法ValueErrorは隠さない。中断は局面None |
| 二手評価 | `_two_ply_score_controlled(after_move: Position, perspective: Side, *, control: Optional[SearchControl]) -> CandidateEvaluation` |
| 候補評価 | `_evaluate_candidate(position: Position, move: Move, policy: MoveSelectionPolicy, *, control: Optional[SearchControl]) -> CandidateEvaluation`。Material/TwoPlyMaterialを扱う。Randomには呼ばない |

盤上の出発マス・移動先・成り選択、駒打ち種・打ち先の各反復の区切りと、下位処理復帰後に確認する。根の生成中だけinclude_target=Trueを使う。根で予備手がまだない間はprotect_first_legal=Trueを下位の合法判定まで引き継ぐ。最初の合法手確定後には解除し、次の確認で通常停止する。保護は根の一手を合法と確認するための呼出し鎖に限り、候補評価・相手応手へは渡さない。

打ち歩詰めの経路は `_legal_moves_controlled → _apply_drop_controlled → _is_checkmate_controlled → _has_legal_move_controlled → _legal_moves_controlled(check_uchi_fuzume=False)`。内側はroot=Falseのため目標停止しない。保護されていない内側で上限/stop/抑制による中断があれば、真偽未確定をそのまま上へ伝え、その歩打ちを一覧へ追加しない。保護中でもSUPPRESSは保留しない。不合法ValueErrorを無視する現在の列挙規則で、中断を不合法扱いして次の手へ進まない。

手あり確認は最初の合法手を見つければTrueが確定する。手なし・詰みTrue・二手評価の最悪値には必要な全調査の完了が要る。制御付き操作の下位中断を空一覧/False/0点へ変換しない。一回の複製、利き計算、静的採点自体を強制切断しない。

## 返す手の決定と完了境界

1. 根生成が中断したら、抑制ならSUPPRESSED。通常停止で確認済み手があれば、その最初の手でINTERRUPTED。未確保なら通常停止を保留し、合法手一つまたは全調査による手なし確定まで続ける。
2. 根生成が完了し空ならCOMPLETE/None。根生成完了と目標到達が重なり、手があるなら新候補評価を始めず予備手を返す。
3. Randomは根生成完了後の停止確認がCONTINUEなら全合法手から一回抽選してCOMPLETE。停止なら予備手を返し抽選しない。
4. 駒得方式は各候補開始前にinclude_target=True、評価中はFalseで確認する。目標だけなら評価中候補を続け、上限/stop/抑制なら中断する。
5. 候補は一手適用・必要な詰み判定・全応手の評価・復帰後の停止確認まで終えて初めて評価済みへ追加する。最後の静的採点が終わっても、その復帰後確認で上限/stopが観測された候補は未完了として捨てる。目標だけなら追加できる。これを評価完了の境界としてテストで固定する。
6. 目標/上限/stopで終了するときは、評価済み候補の最高同点だけから一回抽選。評価済み0件なら予備手を返し抽選しない。全候補完了はCOMPLETE、未着手/中断候補が残ればINTERRUPTED。SUPPRESSなら結果の手を渡さず抽選しない。

最終抽選直前にも抑制を確認する。直後の要求は後続送信担当が再確認する。制御部品のcheck/結果生成はUSI送信と原子的ではないため、今回だけで一回応答や抑制競合の解決済みとはしない。通常完了が早い場合は目標時刻まで待たない。

## 契約・独立期待値・検出範囲

個人観察 `~/.codex/observations/test-driven-development.md` と[点検手順](../knowledge/test-coverage-review.md)を適用する。時計は制御値、選択は手計算の点と記録する抽選器で期待値を作る。製品の戻り値を期待値として再利用するだけの検査にしない。

| 契約 | 代表ケースと固定期待値 | 検出対象・既存補完 |
| --- | --- | --- |
| 原点・単位・境界 | 原点1,000,000,000ns、予算(10,20)ms。目標1,010,000,000ns、上限1,020,000,000nsの各−1/一致/+1。目標ではinclude_target時だけSTOP、上限では常にSTOP | 起動時原点、ms換算漏れ、`>`、目標と上限混同。既存計算は期間のみ補完 |
| 受渡し遅延・巨大値 | 構築/最初のcheckが原点+21msなら最初からSTOP。予算(10^400,10^400)でも整数で期限判定 | 原点再取得、float overflow、独自上限。標準入力の実原点取得は後続 |
| 時計なし・0・保護 | Noneで任意の前進時刻はCONTINUE、(0,0)はSTOP。0でも保護中CONTINUE、抑制後SUPPRESS。別制御はCONTINUE | 0をNone扱い、保護の過大適用、古い停止残留。既存時計解析は入力側の区別を補完 |
| 根予備手 | 玉なし教材で先手歩を２七/７七に置く。通常生成順A=２七→２六、B=７七→７六。0/開始前stopならAだけを確保して返す。空盤はCOMPLETE/None | 未確保の空を投了、全一覧生成継続、生成順変更。通常順は既存LegalMoveListTestsが補完 |
| 生成途中 | 盤上/成り/駒打ちの各区切り、合法確定前/後に制御要求。返す一覧は手書きで特定した確定手のみ。抑制は未確保中でも中断 | 不合法/未確定手の追加、反復内確認漏れ。既存合法規則が通常側を補完 |
| 打ち歩詰め・詰み | UchiFuzumeTestsの先後両教材を参照して局面を組み立てる。内側防御確認を中断→value=None/歩打ち未追加。通常完了の合法/打ち歩詰め拒否と対照 | 中断をFalse化して歩打ち採用、再帰時フラグ喪失。既存打ち歩詰めだけでは中断を検出不可 |
| 完了候補のみ | 合法なA/B/Cに評価完了値(0,3)/(0,7)、Cの途中仮点(0,99)を与える選択境界検査→B。同点(0,7)/(0,7)と低点候補→抽選引数は同点二手だけ、呼出し1回 | 途中点採用、先頭/末尾だけ保持、全候補抽選、二重抽選。実評価は次行で別検証 |
| 実評価の中断 | 下記の取り返し教材・詰み教材を先後反転。応手先頭/中間/末尾、詰み判定内部で中断→CandidateEvaluation(False,None)。無停止はMaterial歩取り(0,7)/安全手(0,5)、TwoPly歩取り(0,-23)/安全手(0,5)、詰み勝ち(1,0)/負け(-1,0) | 部分min採用、下位未確定の点化、開始側固定。既存二手深さ・詰み・枝独立性が通常完了を補完 |
| 目標と上限 | A完了後B評価中に目標→B完了を保持、C未開始。B採点復帰前の上限/stop→Bを捨てA。A未完了なら予備手 | 目標で評価途中破棄、上限で継続、完了境界の誤り |
| 三方式・局面寿命 | Random全完了は全手一回抽選、中断はAで抽選0。三方式の中断前後で全81マス/両持駒/手番一致。次呼出しは新制御とローカル結果 | ランダム部分抽選、局面破壊、前回結果流用。既存局面保存/乱数器共有を補完 |
| 故障と抑制 | 採点RuntimeError、未知手TypeError、不合法ValueErrorは通常中断へ変換せず伝達。stop→suppress→stopで抑制を維持 | 故障を投了/予備手へ隠蔽、抑制解除。故障通知・出力失敗は後続 |

選択境界の固定点テストだけで実評価の正しさを主張しない。停止点は実操作をwrapして要求/時刻を変更し、実際の合法判定・中断伝播・評価を通す。sleepや「checkを何回呼んだら停止」という総回数だけへ依存しない。

取り返し教材は先手玉９九・飛５五、後手玉１一・金５三・歩５四、持駒なし。歩取り５五→５四では一手後15+1−9=7点、金に取り返されると1−(15+9)=-23点、安全手５五→４五では15−(9+1)=5点。後手版は全筋段を10から引き所属を交換し、開始側視点で同じ固定点とする。詰み教材は既存 `TwoPlyMaterialSelectionTests._mate_priority_position` の全駒配置を参照し、飛５三→５二の直後を勝ち(1,0)、反対側を開始視点にした一手後相当局面の全応手評価を負け(-1,0)とする。非詰み手なしは玉なし空盤に開始側持ち歩7枚・相手手番を設定し、固定値(0,7)とする。テストクラスのprivate helperを実行コードからimportせず、教材の配置をテスト内へ明示する。

## レビューフォーカス

1. 0予算で最初の合法手も見つからない局面：全調査の手なし確定と抑制中断を区別する（タスク2・4）。
2. 打ち歩詰め内部で通常停止から抑制へ切り替わる：保護中でも止め、未確定歩打ちを使わない（タスク2・4）。
3. 目標0・上限1msの予算：根生成では目標停止、評価中では上限までの区別を守る（タスク1・3・4）。
4. 最後の応手採点から戻る際に上限到達：その候補を完了に昇格させず、以前の完了候補を返す（タスク3・4）。
5. 返却直前の抑制と故障：抑制時の手なしを投了に変換しない。結果返却後の競合は後続送信同期の責務と明示する（タスク4・後続接続）。

## 承認後の実装手順（今回は全て未実行）

各タスク内で振る舞いごとにテスト作成→実行可能な境界で意図したアサーションのRed→最小実装→Green→Refactor要否確認→独立レビューを行う。import失敗だけをRed完了としない。既存共通処理で初回Greenならその事実を区別する。Critical/Importantは解消・再検証・再レビュー後に記録・コミットへ進む。

### タスク1：期限と停止要求

ファイル：作成search_control.py / test_search_control.py。消費：既存Optional[SearchBudget]と読取り済み整数ns。生産：上表のSearchControl、SearchSignal。

- [x] `test_deadline_boundaries`：上表の直前/一致/直後に `assertEqual(control.check(include_target=...), expected_signal)`。`test_uses_received_origin`：21msの遅延後でもSTOP。`test_preserves_large_integer_budget`：10^400msで期限直前CONTINUE/一致STOP。
- [x] `test_validates_origin_type_without_restricting_sign`：started_nsにTrue/False/1.0/文字列/Noneを渡し `assertRaises(ValueError)`。原点-1,000,000,000ns、予算(10,20)msでは目標-990,000,000nsの直前CONTINUE/一致STOPを `check(include_target=True)` で確認し、負数を拒否する誤りも検出する。
- [x] `test_distinguishes_no_budget_and_zero`、`test_protects_only_ordinary_stop`：None/0/目標0上限1を固定期待値へassertEqual。`test_suppression_is_monotonic`：stop→suppress→stop後は保護の有無によらずSUPPRESS。`test_new_control_does_not_inherit_stop`：別インスタンスはCONTINUE。
- [x] `.venv/bin/python -m unittest discover -s tests -p test_search_control.py -v` を実行し、境界・0・抑制について期待したRed理由を記録する。
- [x] 上表のシグネチャで最小実装し、同コマンドの失敗/エラー0を確認。偽時計はテスト内の整数値で、実時間を待たない。
- [x] 隔離コピーで `>=` を `>`、ms→nsを1000倍、原点を構築時へ変更、抑制を通常stopで解除する誤りを個別注入。対応assertのFAILと復元後Greenを記録。
- [x] Refactor要否・独立レビュー・品質検査・記録を済ませ、対象だけ通常コミット。

### タスク2：合法手・手あり・詰み・適用の中断伝播

ファイル：movegen.py / 作成test_search_movegen.py、必要ならtest_movegen.py。消費：タスク1のSearchControl.check。生産：上表のLegalMovesResult / HasLegalMoveResult / CheckmateResult / _ApplicationResultと各controlled操作。一手適用操作もここで用意する。

- [x] `test_root_generation_stops_after_first_legal_move`：上表の二歩教材、0予算で `assertEqual(result.moves,(A,))`、`assertFalse(result.completed)`。空盤では `assertTrue(result.completed)` と空一覧。生成途中の盤上手・成り・駒打ちに対し `test_keeps_only_confirmed_moves` で手書き期待タプルと照合する。
- [x] `test_suppression_breaks_first_move_protection`：最初の合法判定中に抑制→completed=False、未確定手なし。`test_uchi_fuzume_interrupt_is_not_legality`：先後教材の内側防御生成へstop/抑制を投入し、中断結果と歩打ち未追加をassert。保護あり通常stopは合法/違法確定まで続き、抑制は中断する対照も検査。
- [x] `test_checkmate_and_move_existence_keep_unknown`：中断は `assertIsNone(value)`、完了側はTrue/False。王手なし・玉なしは完了False。`test_interrupted_application_preserves_position`：適用中断時は全局面snapshot一致、戻り局面None。未知手TypeError/不合法ValueErrorの伝達もassertRaises。
- [x] `.venv/bin/python -m unittest discover -s tests -p test_search_movegen.py -v` で各契約のRedを確認。共通規則へ制御付き境界を設け、従来APIは停止なしで共有する最小実装後にGreenを確認。
- [x] `.venv/bin/python -m unittest discover -s tests -p test_movegen.py -v` で既存順序・成り・駒取り・駒打ち・打ち歩詰め・保存の通常完了契約を回帰確認。
- [x] 隔離コピーで中断を空の完了一覧へ変換、内側中断を詰みFalseへ変換、保護をSUPPRESSにも適用、成り/駒打ち反復の停止確認を削除する誤りを注入。意図したFAILと復元後Greenを確認し、Refactor要否・独立レビュー・品質検査・記録・通常コミット。

### タスク3：候補評価の完了単位

ファイル：movegen.py / test_search_movegen.py、必要ならtest_movegen.py。消費：タスク2の制御付き一手適用・詰み・合法生成。生産：CandidateEvaluation、_evaluate_candidate、_two_ply_score_controlled。従来choose_moveの通常評価を同じ内部処理へ委譲し、公開契約を維持する。

- [x] `test_target_allows_current_candidate_to_finish`：評価開始後に目標だけ到達→ `assertTrue(result.completed)` と独立固定score。`test_maximum_or_stop_discards_candidate`：復帰後確認で上限/stop→ `assertFalse(result.completed)`、`assertIsNone(result.score)`。目標0/上限1msの制御を候補操作へ直接渡す対照を含む。
- [x] `test_reply_and_mate_interrupt_propagate`：実二手教材の応手先頭/中間/末尾と詰み判定内部で停止し、未完了/Noneをassert。`test_completed_scores_preserve_policy_and_perspective`：先後反転・通常/詰み勝ち/詰み負け/非詰み手なしを固定点と比較。既存教材の設定と手計算をテスト本文に記し、製品採点から期待値を作らない。
- [x] 対象test_search_movegen.pyでRed→最小実装→Green。test_movegen.pyで既存の同点抽選・勝敗順・二手境界・枝独立性・不合法例外を回帰確認。
- [x] 隔離コピーで応手中断時の部分minを採用、最後の復帰後確認を削除、下位詰み中断を通常点へ変換する誤りを個別注入。FAIL/復元Green、Refactor要否、独立レビュー、品質検査、記録、通常コミット。

### タスク4：根探索と途中結果の最終選択

ファイル：movegen.py / test_search_movegen.py。消費：タスク1〜3。生産：SearchCompletion、SearchResult、search_move。USI呼出し先は変更しない。

- [x] `test_zero_budget_returns_fallback_or_confirmed_no_moves`：三方式×先後反転の最初の合法手を手書きで特定し `assertEqual(result.move,A)`、INTERRUPTED、抽選0回。空盤はCOMPLETE/None。`test_suppressed_search_has_no_response_move`：保護中もSUPPRESSED/None、抽選0回。
- [x] `test_root_target_stops_generation_but_reply_target_does_not`：根生成の目標到達→予備手。評価中の下位応手生成は目標では止めず完了。`test_target_prevents_next_candidate`：B評価中目標→B保持/C評価未呼出し。`test_maximum_discards_active_candidate`：B中断→A保持。
- [x] `test_selects_only_completed_best_candidates`：上表のA/B完了・C途中99点→抽選引数 `(B,)`、同点対照は最高同点二手のみ、`assertEqual(choice.call_count,1)`。完了0ならAと抽選0。候補順を反転しても途中候補を選ばない。
- [x] `test_random_complete_and_interrupted_selection`：全完了は全合法手タプルへ一回choice、中断は最初の手へ抽選0。`test_finishes_without_waiting_for_target`：偽時計が期限前でもCOMPLETEを返す。`test_new_search_preserves_position_and_does_not_reuse_result`：三方式/中断点ごとの81マス・両持駒・手番一致、連続呼出しで結果と停止状態を継承しない。
- [x] `test_search_propagates_unexpected_errors`：実評価の例外を `assertRaises(RuntimeError)`、不合法/未知型は既存TypeError/ValueErrorで確認。投了や予備手へ変換しない。
- [x] test_search_movegen.pyの各振る舞いでRed→最小実装→Green。隔離コピーで途中候補を追加、予備手を常に優先、Random中断時の部分抽選、下位応手へ根保護を適用、0を期限なし扱いする誤りを個別注入し、意図したFAIL/復元Greenを記録。
- [x] 全体 `.venv/bin/python -m unittest discover -s tests -v`、import変更時の `.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`、`.venv/bin/ruff check .`、差分確認、必要な再検証を行う。Refactor要否・独立最終レビュー・文書リンク検証・git diff --check・実績記録後に通常コミット。フック回避なし。

## 後続の入力並行処理・USI接続への引き渡し

ここは依存契約の一覧であり、入力API・通信路・スレッド実装の計画を今回追加承認するものではない。

| 後続担当 | 今回から受け取る/維持する契約 | 後続で必須の確認 |
| --- | --- | --- |
| 入力読取り担当 | go行を読み取った時点のmonotonic_nsを渡す。同じ時計の現在時刻をSearchControlへ注入 | 主担当受渡し・前担当回収・解析・複製・生成が予算へ含まれること。macOSの中断可能読取り、部分入力/複数行/末尾行、内部終了通知と回収。他OS移植点の明記 |
| 主担当 | 時計解析→局面要求→予算準備、局内方針固定の既存契約を保持。goごとに新制御・独立局面を探索担当へ渡す | stopはrequest_stop()、quit/EOF/gameover/入力エラー/故障はsuppress_response=True。idle stop無視、探索中isready/usi/setoption/未知入力、探索中position/go/usinewgameのエラー契約 |
| 探索担当 | search_moveの最終結果を受け、一回のbestmove送信を担当。INTERRUPTEDの合法手とCOMPLETE/Noneを使う | SUPPRESSED/Noneをresignへ変換しない。送信直前に共通Lock内で抑制を再確認し、入力確定/送信/完了を同順序で扱う。出力失敗は送信完了にしない |
| 回収・故障処理 | 部品の例外は故障として通知し、通常中断と区別する | joinは共通Lock外、送信完了後の正常次命令は前担当回収後に処理。回収前に新探索を起動しない。入力待ちを内部通知で解除し担当/通信路を回収 |
| USIテスト移行 | 既存ScriptedInputはgo後すぐquit/EOFを返すため非同期後の抑制契約に合わせ順序を作る | 通常応答を待ってからquit/EOF、意図した抑制は送信前に確定。固定sleepに頼らず同期点と有限回収待ちを使用。実プロセスのstop/readyok/一回応答/flush/終了確認を追加 |

後続接続まで実USIの0予算応答は従来の通常比較のまま。接続後は0予算を即通常停止要求とし、合法予備手または全調査の手なしを一回応答する。全体設計の合法手未確保例外と期限超過リスクは維持する。

## 検証・記録・承認ゲート

新規テスト、TDD、誤り注入、実時間計測、対局は今回一切未実施。既存389件成功は前テーマの取り込み先実績であり今回の結果ではない。今回の文書検証と独立レビューは[学習記録](../learning/search-stop-implementation-plan.md)へ実施後に記す。

実装時は各契約のRed/Green・変異名と失敗理由・復元・単独/全体補完・Refactor要否・Critical/Important/Minorと対応を記録する。部品の検証から標準入力受付・一回送信・スレッド回収・全競合・全OS・厳密な期限内応答・係数最適性を保証しない。

本書をレビュー後に提示し、本人の明示承認を待つ。計画承認だけで実装開始へ自動継続しない。main統合は別承認。計画作成だけの現段階ではGitコミット・push・main取り込みを行わない。

## 一次資料

2026-10-12に再確認。単調時計を整数nsで扱う技術的根拠は [Python 3.9 time](https://docs.python.org/3.9/library/time.html#time.monotonic_ns)、フラグ同期は [threading Lock](https://docs.python.org/3.9/library/threading.html#lock-objects)。探索中入力とstop/bestmoveの一般要件は [USI仕様](https://hgm.nubati.net/usi.html)。本プロジェクトの目標/上限・予備手・抑制方針をUSI一般の規定と混同しない。

## 計画内容の承認

2026-10-12、計画提示後の本人回答「**承認数r**」を、文脈上「承認する」の入力誤記として受け取り、本計画への明示承認として記録した。API・実装範囲・検証案・入力並行処理との後続接続を含む計画内容の承認。上記の未承認・承認待ち表現は提示前の段階の記述。今回の依頼は計画提示までなので実装開始へ自動継続せず、開始指示を待つ。main取り込みは別承認。コード・テスト・設定変更、TDD、コミット・push・main取り込みは未実施。

## 実装開始後の状態

2026-10-12、本人の実装開始指示により手順を開始。上記の「今回は計画だけ」「未実行」「開始指示待ち」「コミットなし」は計画作成時の履歴。実績と裁定は学習記録へ追記する。main取り込みは別承認。


## 実装・最終レビューの実績（2026-10-12）

本人の開始指示後、上記4タスクを実装・検証・独立レビュー。全425件成功、Ruff成功、文書リンク497件・見出し14件欠落0、差分検査成功。最終独立レビューはCritical/Important/Minor全0。手ありの早期確定には共通生成のprivate `_first_only` を追加した。実績・Red/Green・変異の補強・裁定・未検証範囲は[学習記録](../learning/search-stop-implementation-plan.md)、確定仕様は[知識メモ](../knowledge/search-stop.md)へ記録した。

元の作業ディレクトリの作業ブランチへ9b317ccとして保存済み。main統合の承認・取り込み先検証・最後の理解確認は未実施。USI接続・計測・対局は今回実施していない。


## main取り込みの実績（2026-10-12）

本人の選択肢1によりローカルmainへの統合を承認。元ディレクトリで3ddd7c5から522614cへfast-forward統合した。取り込み先で全425件成功、Ruff整形34ファイル・lint成功、相対リンク499件・見出し14件欠落0、差分検査成功。最後の理解確認は未回答。USI接続・push・計測・対局は行っていない。
