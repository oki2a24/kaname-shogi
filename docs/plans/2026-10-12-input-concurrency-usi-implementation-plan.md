# 入力並行処理・USI接続 実装計画

> **AIエージェントへの指示:** 2026-10-12、本人「承認する」により本計画を承認済み。実装開始指示待ち。本人の実装開始指示までコード・テスト・設定変更、TDD、実装を始めない。実装時は `executing-plans` または本人が選ぶ `subagent-driven-development` を使用する。main取り込みは別承認。

**目標:** 完成済み探索停止部品をUSIへ接続し、探索中入力、停止・抑制、一回応答、故障通知、入力待機解除と担当回収を実現する。

**アーキテクチャ:** 現在スレッドを主担当、入力を一つの読取りスレッド、各goを一つの探索スレッドとする。命令・故障・担当終了はQueueで主担当へ通知し、入力確定と送信・抑制を共通Lockで順序付ける。macOSの標準入力は内部終了pipeと同時に待ち、部分行でも中断できる。

**技術スタック:** Python 3.9、標準ライブラリのみ（threading、queue、selectors、os、codecs、io、time、dataclasses、unittest）。依存追加・Python更新なし。

**仕様:** [承認済み全体設計](2026-10-11-clock-input-time-management-design.md)、[確認範囲と追加合意](2026-10-12-clock-input-verification-review.md)、[探索部品の引渡し](2026-10-12-search-stop-implementation-plan.md#後続の入力並行処理usi接続への引き渡し)、[時計接続](2026-10-12-usi-clock-settings-implementation-plan.md)。全体設計の変更ではなく具体化案。以下の入力API追加・Queue/pipe/API選択も今回の計画承認対象。

**グローバル制約:**

- 「説明・学習記録・知識メモは日本語で書く。」
- 「未決定の技術選択や将来の機能を先取りして複雑にしない。」
- 「テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞い、続く本文に検出したい誤りや背景を書く。」
- 「将来の開発・保守で判断を思い出せるよう、公開インターフェースのdocstringに引数・戻り値・副作用・前提条件と設計理由を記録する。処理を変えたら説明も更新する。」
- 四設定・整数精度・時計受付・設定寿命・Difficulty三方式・局内固定・次局継承・未知値保持・乱数器の実行内共有を維持する。
- CLI、将棋規則、探索評価、JSON、起動スクリプト、Ruff設定は変更対象外。計測・対局・係数調整は別テーマ。

## 現物と対象ファイル

2026-10-12、`/Users/oki2a24/kaname-shogi`、ブランチ `codex/input-concurrency-plan-handoff`、開始HEAD `06e288a`、差分なし。Ruff 0.16.10はrequirements-dev.txtと一致、hooksPathは.githooks。別worktreeなし。この計画段階は文書のみ、コミット・push・main取り込みなし。

現在runは同期入力→時計解析・予算準備→legal_moves→choose_move→送信。SearchControl/search_moveは完成しているが未接続。過去の425件成功は今回の検証実績ではない。

| 実装時のファイル | 責務・範囲 |
| --- | --- |
| 変更 `kaname_shogi/usi_engine.py` | 非公開の入力源、通知・共有状態、主担当・探索担当・起動回収、共通出力同期、main診断。既存時計パーサー・予算準備・局面状態を再利用 |
| 作成 `tests/test_usi_concurrency.py` | 制御可能な入力・探索・出力で競合順序、故障、回収、読取り原点を確認 |
| 作成 `tests/test_usi_input.py` | 実pipeと読取り担当で部分行・行分割・終了通知・資源回収を確認 |
| 変更 `tests/test_usi_engine.py` | 既存関数テストの同期点と監視境界を移行、実プロセスの受付・flush・終了を補強 |
| 必要時変更 `tests/test_usi_engine_launcher.py` | 別cwd起動・設定故障の回帰。起動方法は維持 |
| 文書 | 本計画・学習記録・USI知識・README・再開案内・索引。機能表示は接続検証後に更新 |

search_control.py、movegen.py、time_management.pyとそのテストは原則変更せず回帰で利用。部品契約の欠陥が見つかった場合は接続の都合で変更せず、理由・影響を提示し計画変更の承認を得る。

## データ・操作と所有者（新規名は提案）

| API・型 | 日本語の意味・契約 |
| --- | --- |
| `_InputLine(text: str, read_ns: int)` | 完成行と読取り原点の不変データ。主担当が時刻を上書きしない |
| `_InputEnded` / `_WorkerFailed(worker: str, error: BaseException)` / `_SearchFinished(context)` | EOF、担当故障、探索担当終了の通知データ。通常の探索中断と区別する |
| `_StdinLineSource(stream: TextIO)` | macOS用入力源データ。呼出し元の標準入力を所有・closeしない。自前の終了通知pipeとselectorを所有 |
| `read_line() -> _InputLine` | 入力源の操作。完成行を返し、EOFはEOFError、内部終了は非公開 `_InputCancelled` 例外。読取り・復号故障は例外のまま通知担当へ渡す |
| `cancel() -> None` / `close() -> None` | 内部通知による待機解除／入力担当回収後の自前資源解放操作。反復可能。closeは入力担当の実行中に呼ばない |
| `_SearchContext` | 一goの状態データ。独立Position、固定policy、SearchControl、Thread参照、応答抑制、送信完了、終了状態、故障を保持。予備手・完了候補はsearch_move内部が所有し重複保持しない |
| `_run_session(read_line: Callable[[], _InputLine], output_fn: Callable[[str], None], rng: random.Random, config: TimeManagementConfig, cancel_input: Callable[[], None]) -> None` | 主担当の操作。Queue受信・入力確定・起動・回収を行う非公開共通入口。終了時は両担当を回収してから返す／故障を再送出する |
| `_search_and_respond(context: _SearchContext, output_fn: Callable[[str], None], rng: random.Random, lock: Lock, events: Queue) -> None` | 探索と最終応答の操作。search_moveを一回呼び、同じLock内で抑制再確認・一回送信・送信完了を確定。必ず終了通知を送る |
| `run_usi_engine(input_fn, output_fn, rng=None, *, time_config=None, cancel_input_fn=None) -> None` | 既存位置引数・time_configを保持する公開操作。入力関数の返却直後にmonotonic_nsを記録して_InputLineへ包む。新キーワードcancel_input_fnは入力待機解除操作 |

公開runの互換性は引数・一行入出力・設定寿命を保つが、探索と入力の時系列は変わる。有限なScriptedInputはcancel省略可（何もしない解除関数）。待機する入力関数は、別スレッドからのcancelで必ず返る／EOFErrorにできるものを渡すことを新しい前提としてdocstringに明記する。任意のブロッキングCallableを強制停止できるとはしない。mainは公開runの文字列アダプターを経ず、時刻付き入力源を_run_sessionへ渡す。mainの既存テストの監視先はこの実境界へ移す。

時間設定は担当起動前に一回読み、mainから渡す。runの省略時のみ既存loaderを一回呼ぶ。乱数器は一実行で共有し、前担当回収後にしか次担当へ渡さない。主担当だけが保存局面とDifficulty設定・局内固定を変更する。

## 入力待機・完成行・原点

標準入力fdとos.pipe()の読取り端をselectors.DefaultSelectorへ登録する。標準入力の元blocking属性を保存しos.set_blocking(fd, False)とし、終了後に復元する。TextIOWrapper.readlineとos.readを混用しない。mainでは入力を先読みせず、起動設定確認後にこの入力源を作る。実fdがない入力は公開runの注入境界を利用する。

os.read(fd, 4096)で到着分を取り、BlockingIOErrorは次の待機へ戻る。各read後に通知も確認し、連続入力でも内部終了を後回しにしない。標準入力と終了通知の両方がreadyなら終了通知を優先し、蓄積済み未配送行・部分行を破棄する。cancelは専用の状態同期で一回だけ非blocking通知pipeへ書き、反復でpipe満杯待ちを作らない。closeは登録解除後にselectorと自前pipe両端を閉じ、借用stdinの属性を復元する。

復号はstream.encoding/stream.errors（未設定時はUTF-8/strict）によるincremental decoderを用い、io.IncrementalNewlineDecoderで従来テキスト入力のLF/CRLF/CRを扱う。分割された多バイト文字・CRLFを保留する。文字列splitlinesではなく正規化後のLFで完成行を切り出す。各完成行を確定した直後のmonotonic_nsを保存し、複数行を一readで得ても配送時に時刻を取り直さない。CRのみで終わる入力は次バイトまたはEOFで確定する。EOFではdecoderをfinal化し、改行なし末尾行があれば一回配送してからEOF通知。復号失敗は読取り故障。

go原点はこの完成行読取り時刻。受渡し・前担当回収・解析・Position.copy・探索起動を含める。GUI送信から読取りまで、先行positionの処理時間は含めない。時計なしNoneとSearchBudget(0,0)を区別し、整数nsのままSearchControlへ渡す。新しい上限値・float換算は追加しない。

macOSの標準入力pipeを主要対象とする。端末・通常ファイルもselector登録の可否と失敗診断を確認するが、全入力デバイスの動作保証はしない。Linux/Windowsへの移植時にはfd同時待機、非blocking読取り、復号・改行、終了通知・回収・属性復元を再点検する。この対象OS・前提・移植点を該当docstringにも書く。

## 共通同期と状態遷移

Queueは通知の共通受渡し場所。入力担当は規則・局面を解析せず行/EOF/故障を通知する。入力の「読取り」と「確定」は別で、確定は主担当がQueueから取り出し共通Lock内で現在状態と命令を照合した時点。単なるQueue投入を抑制確定と呼ばない。最終送信も同じLockで順序付ける。

各goは時計解析→局面要求→予算準備→局内方針固定→独立Position.copy→新SearchControl→context登録→Thread.startの順。原点は読取り時刻。登録から起動まで主担当が責任を持ち、起動失敗は故障として抑制・終了へ進める。active登録はLock内、start・copy・joinはLock外。主担当は処理中に次命令を確定しない。入力担当はその間も受け付ける。

| 入力確定時の状態・入力 | 動作 |
| --- | --- |
| idleのstop | 無視。次goへ持ち越さない |
| 探索/送信未完了のstop | control.request_stop()、正常のbestmoveを待つ。反復しても一回 |
| quit / EOF | context抑制＋request_stop(suppress_response=True)、入力待機解除、探索・入力回収、正常終了 |
| gameover | 同じ抑制で探索回収後に受付継続。保存局面・方針寿命は従来どおり、usinewgameに代えない |
| 探索/送信未完了のposition/go/usinewgame | 入力エラー確定と抑制を同じLock内で行い、回収後ValueError。stderr・終了1 |
| 探索中isready / usi | 主担当がreadyok／既存識別・option・usiokを行単位Lockで送信、探索継続 |
| 探索中setoption / 未知・空行 | 設定受付（局内方針不変）／無視。探索継続 |
| 送信完了後・担当未回収の次命令 | 正常命令を拒否せずLock外で前担当join後に処理。次goの原点は既読時刻 |

探索担当はsearch_move(position, policy, rng, control)を一回呼ぶ。SUPPRESSEDなら送らない。INTERRUPTEDは合法手、COMPLETEのNoneだけresign。共通Lock下でcontext抑制とcontrolのSUPPRESSを再確認し、送信済みでなければoutput_fnを呼ぶ。戻って初めてsent=True。mainのoutput_fnは改行writeとflushが戻るまで一回の送信として扱う。上限/stopを送信抑制へ読み替えない。

ロック順序は共通Lock→SearchControl専用Lock。逆順・join中の共通Lock保持は禁止。出力関数に入力処理やエンジンへの再入をさせない。usiの複数行はそれぞれ一行単位の同期で混線を防ぐ。送信中Lockを保持するため、出力自体が詰まる場合に入力確定や終了が遅れる限界は残る。

## 故障・回収

入力・探索担当は境界でBaseExceptionを捕捉して_WorkerFailedをQueueへ送り、finallyで終了を通知する。通常SUPPRESSED・INTERRUPTEDは故障にしない。探索担当の故障は送信前なら共通Lock下で抑制も確定し、入力がなくても主担当を起こす。送信失敗はsent=Falseのまま、再送しない。主担当自身の解析・起動・出力故障も同じ終了処理へ入る。

終了処理は（1）共通Lock内で抑制・終了フラグ・停止要求、（2）Lock外で入力源cancel、（3）起動済み探索担当join、（4）入力担当join、（5）入力源closeと標準入力属性復元、（6）元の原因を再送出／正常終了。各後片付けの例外を記録して残りの後片付けも試みる。解除不能な注入入力は公開runの前提違反であり回収保証外。daemon化やスレッド放棄で済ませない。初期化途中・Thread.start失敗では実際に起動した担当と取得した資源だけ片付ける。gameoverは探索だけ回収し、入力源は維持する。

終了通知を受けてもjoinを省略しない。送信完了とThread終了は別で、_SearchFinishedの受信・join後にactive参照を消す。故障が後片付け中に重なっても正常終了に上書きせず最初の原因を保持し、後続の回収失敗も診断へ添える。KeyboardInterruptは回収後に再送出し、その他の担当・入出力故障はmainでstderr診断・終了1。設定故障は従来どおり担当起動前に終了1。stdoutへ診断や独自の探索開始通知は加えない。

## レビューフォーカスと契約別検証

個人観察と[検出力点検](../knowledge/test-coverage-review.md)を適用する。期待値はLockで作った順序・固定原点・固定手・既存の合法性契約から決め、製品出力から期待値を生成しない。

| 優先する失敗モード・契約 | 代表ケース／独立期待値／検出対象 | 所有タスク・補完・未検証 |
| --- | --- | --- |
| 抑制後の送信 | search_move返却後を止めquit確定→送信0、送信完了→quit確定なら1。EOF/gameover/入力エラーも同様 | 2・3。送信直前再確認除去を検出。部品テストだけでは補完不可 |
| 無言GUIで故障後残留 | 探索例外・出力例外・start失敗、入力は無言/部分行。次入力なしで終了1・全担当非生存 | 1・3・4。通知欠落・読取り再待機・daemon放棄を検出。厳密な終了秒数保証ではない |
| 回収中の相互待ち | 送信済みworkerを終了直前で止め次goを読む。join前Lock解放、前担当終了後だけ次start | 2・3。共通Lock下join・重複担当を検出。OS全順序は未検証 |
| 原点の遅れ | goを100nsで読み、配送/回収後の現在時刻を進める。SearchControlへ100を渡し期限が既に到達 | 1・2。起動時刻への置換検出。既存制御テストで整数期限計算を補完 |
| 旧テスト移行による契約喪失 | 三方式・局内固定/次局継承・未知値保持・rng同一性・保存局面と両持駒・先後時計・None/0/非0 | 2・4。sleep待ちへの置換や監視削除を避ける。探索評価は既存探索テストが補完 |

## 実装タスク（すべて承認後、未実施）

**検査自体の回収規則:** 停止不能な非daemon担当を生み得るケース（部分行取消、故障後終了、共通Lockとの相互待ち、起動途中回収）と、それらの変異実験は、関数テスト・実pipeテストを含め親監視付き子プロセスで実行する。親は有限時間で結果またはタイムアウトを検出し、finallyでterminate→kill→waitして回収する。子の有限joinによるassertion FAILだけではPython終了時の待機を防げないため、同一unittestプロセスへ停止不能スレッドを残さない。正常側では子の結果に全担当非生存・資源閉鎖を含め、親による強制終了を製品の正常回収成功と数えない。

### タスク1：中断可能な行読取り

ファイル：usi_engine.py / 新test_usi_input.py。生産：_InputLine、_InputCancelled、_StdinLineSourceの上記3操作。単独で実pipe入力を確認できる単位。

- [ ] `test_partial_line_is_cancelled_without_more_input`：部分バイトだけ投入しcancel、読取りthreadを有限joinして非生存、行配送0をassert。
- [ ] `test_lines_keep_read_timestamps`：一readの複数行を制御時計100/101で確定、主担当配送を遅らせてもread_nsが100/101のまま。
- [ ] `test_split_encoding_newlines_and_eof_tail`：UTF-8分割、LF/CRLF/CRの分割、空行、改行なし末尾、空EOFで既存readline相当の順序と一回EOFをassert。不正復号は故障。
- [ ] `test_cancel_closes_owned_resources_and_restores_flags`：無言入力・初期化途中例外・反復cancel/close、通知pipe/selector閉鎖とstdin生存・blocking属性復元をassert。readエラーも終了通知経路を通す。
- [ ] 実行 `.venv/bin/python -m unittest discover -s tests -p 'test_usi_input.py' -v`。先に実行可能な停止不能の境界で意図したアサーションFAILを確認する。importエラーだけはRedとしない。
- [ ] 計画の入力操作を最小実装し同コマンド成功確認。固定sleepで入力状態を推測せず、読み取り待機/部分蓄積の同期点をテスト側で制御する。
- [ ] Refactor要否・独立レビュー・検出範囲を学習記録へ残し、Ruffと差分確認後に通常コミット。

### タスク2：入力と探索の接続・一回応答

ファイル：usi_engine.py / 新test_usi_concurrency.py / test_usi_engine.py。消費：タスク1の_InputLine、既存SearchControl/search_move。生産：_SearchContext、_run_session、_search_and_respond、cancel_input_fn付きrun。

- [ ] `test_go_uses_read_origin_and_new_context`：read_ns=100をassert、コピーは保存局面と別参照で内容同一、goごと制御別参照、rngは同一。None/0/非0を連続応答の後に進め、先後時計を固定予算と照合。
- [ ] `test_search_results_send_once_or_suppress`：固定合法手のCOMPLETE/INTERRUPTEDは各1、COMPLETE/Noneはresign1、SUPPRESSEDは0。自然完了/stop/上限競合とstop反復でも1。
- [ ] `test_commands_during_search`：探索開始Eventで止め、isready/usiの応答・setoption次局反映・未知無視・idle stop無視をassert。探索中position/go/usinewgameは各ValueError、送信0。
- [ ] `test_input_confirmation_orders_suppression_and_send`：送信前Lock取得と入力確定の両順序を作り、quit/EOF/gameover/不正入力の送信0/送信済み1をassert。合法手未確保中も抑制要求を渡す。
- [ ] `test_next_command_waits_for_previous_worker`：送信済み・終了前の同期点で次position/go/usinewgameを受け、正常処理、最大探索担当数1、後続go原点維持をassert。後片付けが同じLockを使っても終了できる。
- [ ] `.venv/bin/python -m unittest discover -s tests -p 'test_usi_concurrency.py' -v`で各振る舞いのRedを確認し、接続を最小実装してGreen。既存USI通常応答テストも同期点を移行し成功確認。
- [ ] Refactor要否・独立レビュー後、Ruff・対象回帰・記録を揃え通常コミット。入力と探索の責務を同じモジュール内で分け、無関係な公開APIは増やさない。

### タスク3：故障通知・終了回収・main

ファイル：usi_engine.py / test_usi_concurrency.py / test_usi_input.py / test_usi_engine.py。消費：タスク2のsession/context、タスク1のcancel/close。生産：全終了経路の回収とstderr/終了コード。

- [ ] `test_worker_failure_wakes_idle_input`：探索・読取り・出力の例外、探索start失敗を別々に注入。無言/部分行入力で有限回収、全担当非生存、送信失敗時sent=False・再送0、原因保持をassert。
- [ ] `test_shutdown_and_gameover_have_distinct_lifetimes`：quit/EOFは正常終了・抑制、入力不正/故障は異常、gameoverは抑制回収後isready・次goに応答。次探索へ抑制を持ち越さない。
- [ ] `test_partial_startup_cleanup_and_primary_error`：入力担当start失敗、入力源構築途中失敗、主担当出力失敗、後片付けの追加失敗で、取得済み資源だけ解放し主原因を失わないことをassert。
- [ ] 対象2モジュールとtest_usi_engineを実行し振る舞いのFAILを確認、最小の共通finally/故障通知/main診断を実装し成功確認。設定読込は入力源構築前、run直接呼出しの例外伝達は維持。
- [ ] Refactor要否・独立レビュー後、Ruff・回帰・記録を揃え通常コミット。

### タスク4：既存テスト移行・実プロセス接続確認・最終記録

ファイル：test_usi_engine.py / 必要時test_usi_engine_launcher.py / 文書。消費：接続済み入口。生産：関数・実pipe・実プロセスを区別した裏付け。

- [ ] ScriptedInputを使う通常応答ケースは出力bestmoveのEvent/Conditionを待ってから次go・quit・EOFへ進む入力補助へ移行する。待機する補助にはcancelを必ず用意し、finallyで解除・有限join。goなしの有限入力は従来補助を残す。
- [ ] choose_move/legal_movesへのpatchはsearch_moveへ移す。固定SearchResultの境界テストと実search_moveの合法応答テストを区別し、実評価・元局面保存の教材を維持。時計順序はprepare→copy/control→search開始を観測。不正goはsearchと予算計算未呼出しを維持。
- [ ] `test_entrypoint_accepts_sfen_position`のgo直後quitを、reader.read_lineで合法bestmove確認後quitへ移行。他の即EOF/連続goも同じ観点で点検。期限を短くしただけで旧通常応答契約を緩めない。
- [ ] 実入口プロセスで三方式の合法bestmove・改行/flush・stdout診断分離・終了0/不正1、0予算の合法予備手または手なしresign、時計なしstopの受付を確認する。
- [ ] 探索中stop/readyok/quit/EOF/gameoverと故障時の入力解除は、子プロセス内で実sessionと実stdin入力源を使い、テスト専用bootstrapからsearch_moveをEventで停止する。別の継承pipeで「探索開始」を親へ知らせ、その後命令を送る。stdoutには試験通知を加えない。製品入口の実探索ケースとは分けて記録し、このbootstrap検証だけを実探索中stopの一般保証と呼ばない。
- [ ] 実探索の開始/停止部品接続は、探索開始を通知するラッパーが実search_moveを呼ぶ子プロセスでも一系列確認する。速く完了したケースを探索中stop成功と数えず、制御付きbootstrapの結果と区別する。
- [ ] 全プロセスは有限read/waitとfinallyのterminate→kill→waitで検査失敗時も回収する。部分行中故障、複数行、末尾行は実pipe入力テストで補完。無出力は回収後のstdout残量でassertし、sleep中に何も来なかったことだけで判断しない。
- [ ] 代表変異を隔離コピーで実行：原点を探索起動時へ置換、送信前抑制確認除去、sent確定を出力前へ移動、joinを共通Lock内へ移動、内部通知無視。停止不能になり得る変異は上記の親監視付き子プロセスで実行する。期待したassertion FAILまたは親の有限待ちFAIL（読み込みエラー除外）と復元後成功を記録する。
- [ ] `.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`、`.venv/bin/ruff check .`、差分確認、`.venv/bin/python -m unittest discover -s tests -v`を実行。契約別の単独検出と既存全体による補完を整理する。
- [ ] 最終独立レビューへ契約・代表ケース・検出対象・補完・未検証を渡し、Critical/Importantを解消して再検証・再レビュー。知識・READMEの未接続表示は実績に沿って更新し文書リンクも確認、通常コミット。main統合は本人の別承認待ち。

## 限界と承認後の進め方

固定sleepで競合を推測せず明示同期を使うが、有限テストで全競合・全局面・全OSを証明しない。出力待ち・単一処理・OS遅延・合法手未確保の通常停止例外による超過リスクは維持する。係数の最適性・厳密な期限内応答・ShogiHome互換性・対局安全性はこの実装検証から主張しない。

今回の文書検証・レビュー結果は[学習記録](../learning/input-concurrency-usi-plan.md)へ記す。承認済みでも本計画を実施済みにしない。計画の明示承認後も実装開始指示を待ち、実装・統合・最後の理解確認を別段階として進める。
