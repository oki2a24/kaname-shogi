# 通常対局CLIの探索時間制御 実装計画

> **AIエージェントへの指示:** 2026-10-20に実装開始指示を受け、本計画の順で作業した。チェックボックスはその実施状態を示す。**計画全体は本人承認済み。main取り込みと取り込み先検証は完了し、最後の理解確認が残っている。**

**目標:** 通常CLIの五方式をUSIと同じ制御付き探索へ接続し、CLI対局管理層で時計・返却後判定・表示・保存読込を担う。

**アーキテクチャ:** 共通探索・予算・制御は現物をそのまま使う。時計の値と更新を`cli_clock.py`、棋譜と時計の保存を`cli_session.py`、対話と着手を既存`cli.py`へ配置する。既存棋譜の辞書変換・検証再生だけを公開操作へ分ける。

**技術スタック:** 現行READMEのPython 3.14以上、標準ライブラリ、unittest、固定Ruff 0.16.10。依存追加なし。古い個人方針中のPython 3.9という記述を現行実行環境の要件に置き換えない。

**仕様:** [承認済み設計全体](2026-10-20-cli-search-time-control-design.md)。本人回答・撤回・承認は[設計学習記録](../learning/cli-search-time-control-design.md)。本計画はその実装順・公開名・検証を具体化し、2026-10-20にAPIの具体化・手順・検証方法を含む全文について本人の「yes」により承認された。

**グローバル制約:**

- 「コンピュータ手には事前の詰み確認・全合法手生成を挟まず、USIと同じ制御付き入口を使う。合法手なしの正常結果は投了とする。」
- 「現行USI向け戻り値にない完了深さ・手の由来は表示しない。」
- 「USIの製品経路・時計予算式・停止確認点・設定値・結果型を変更する提案は含めない。」
- 「人間側の時計、加算時間、先読み、探索中の入力受付、時計なしの選択、時間切れ判定を無効にする設定は今回追加しない。」
- 「終局理由は成功した指し手の履歴へ混ぜない。」
- 訪問回数・過去の約5分から原因・時間・予算を推定しない。実時間で完了深さや期限内応答を固定期待しない。
- 日本語docstringに引数・戻り値・副作用・前提・理由を記す。テスト名は英語、docstring先頭は日本語の振る舞い、本文は検出対象。

## レビューフォーカス

1. 時計つき保存の読込途中で棋譜だけが置換される事故 → Task 5の不正clock・不合法履歴・I/O失敗後の再保存で双方の保持を確認。
2. 端数を丸めて時間切れ境界を誤る事故 → Task 1/4で1ns前・一致・後、相手時計と次手の秒読みを確認。
3. 全手番共通の事前詰み判定が残り無制御の待ち時間が復活 → Task 3でコンピュータ手の禁止呼出しを検出し、人間手番の判定を確認。
4. 読込後に起動初期値を失い、旧棋譜へ直前の時計設定を流用 → Task 5で異なる時計つき→旧v1の連続読込を確認。
5. 探索・時計のValueErrorを入力エラーや時間切れへ変換 → Task 3/4で同一例外の伝播とCtrl+C/EOFの終了を別確認。

## 計画作成時の開始状態と実施済み作業

計画作成時の開始HEADは`f3a05b8`、作業場所は`/Users/oki2a24/kaname-shogi`、作業ブランチは`codex/cli-search-time-control-plan`。別worktreeなし。開始時mainはorigin/mainより5コミット先行し、未追跡`.antigravity/tasks/`だけがあった。保持しステージしない。

計画作成時点では計画・独立レビュー・文書検証・提示だけを行い、製品コード・テスト・設定・承認済み設計を変更しなかった。その後、本人から実装開始指示を受け、本計画の各Taskと検証を実施した。作業ブランチへの反映は完了後に記録する。mainへの取り込み・pushは行わない。

## ファイルと境界・構築者判断

| ファイル | 責務 |
| --- | --- |
| `kaname_shogi/cli_clock.py`（新規） | 初期条件・先後残りnsの不変データ、入力条件の検証、経過更新・時間切れ計算。I/O・探索なし |
| `kaname_shogi/cli_session.py`（新規） | 棋譜と任意の時計の値、形式判別・保存読込。モード・方針・予算設定を保持しない |
| `kaname_shogi/game_record.py` | `to_payload`/`from_payload`を公開し既存save/loadも委譲。既存v1検証・再生本体を共有 |
| `kaname_shogi/cli.py` | 時計入力、手番分岐、計時・予算接続・結果優先順・日本語表示、保存読込後の状態確定 |
| `kaname_shogi/__main__.py` | モード→方針→時計の入力、コンピュータ参加時のみ設定一回読込、設定故障stderr/終了1 |
| `tests/test_cli_clock.py`・`tests/test_cli_session.py`（新規） | 時計と保存単独契約 |
| `tests/test_cli_time_control.py`（新規） | CLI接続・状態・時間・例外・表示・読込統合 |
| `tests/test_game_record.py`・`test_cli.py`・`test_cli_entrypoint.py` | 公開境界と既存CLI契約の維持・承認済み変更への更新 |

USIとの差分：新しい二モジュールはGUIに相当するCLI管理責務。USIへ移植せず、USIの非公開予算準備関数を輸入しない。同じ公開`calculate_search_budget`を呼ぶ。棋譜公開境界は設計承認内であり、USI・共通探索のAPIは拡張しない。

公開名と直接呼出しの具体化（今回の計画全体承認に含む）：

- `CliClockSettings(initial_time_ms: int, byoyomi_ms: int)`：初期条件を表す不変データ。非負整数、bool不可、同時0不可。
- `CliClock(settings: CliClockSettings, sente_remaining_ns: int, gote_remaining_ns: int)`：現在時計の不変データ。残りは0以上、初期ms×1000000以下。
- `CliClock.start(settings: CliClockSettings) -> CliClock`、`remaining_ns(side: Side) -> int`、`after_turn(side: Side, elapsed_ns: int) -> CliClock`、`is_expired(side: Side, elapsed_ns: int) -> bool`：生成・参照・更新・判定の操作。更新と判定は**同じ開始時計**に対して行う。経過は非負整数、bool不可、違反はValueError。絶対時刻の負値は禁止しない。
- `CliSession(record: GameRecord, clock: CliClock | None)`：保存単位のデータ。`save(path: str | Path) -> None`、`load(path: str | Path) -> CliSession`はファイル操作。旧v1のloadはclock=Noneを返す。旧棋譜への初期時計補完はCLI側で行う。
- `GameRecord.to_payload(self) -> dict`、`GameRecord.from_payload(cls, payload: object) -> GameRecord`：独立辞書への変換と、既存検証・合法再生を行う操作。公開辞書は内部可変状態と共有しない。
- `choose_clock_settings(*, input_fn: Callable[[], str] = input, output_fn: Callable[[str], None] = print) -> CliClockSettings`を`cli.py`へ追加し`__all__`にも載せる。不正なら理由を表示し二欄の入力をやり直す。
- `run_game`の既存キーワード・戻り値GameRecordは維持し、キーワード専用`clock_settings: CliClockSettings | None = None`、`time_config: TimeManagementConfig | None = None`、`now_ns: Callable[[], int] = time.monotonic_ns`を追加する。直接呼出しでコンピュータ参加かつ初期条件省略なら10分/30秒、設定省略なら一回loaderを呼ぶ。対話入力は追加しない。人間同士では時計・loader・時計入力を要求しない。注入設定は読み直さず、故障は呼出し元へ伝える。
- 実入口mainは方針→時計入力→loader→run_gameの順。mainが既に読んだtime_configを渡す。設定読込のValueError/OSErrorだけを狭い境界でstderr診断・終了1へ変換し、探索の故障を同じ境界で捕捉しない。

旧直接呼出しの引数・戻り値互換性は維持するが、コンピュータ参加時に時計制御・JSON読込が加わる動作変更は本機能の目的。旧`choose_move`への接続・無制御の深さ4固定完了を互換性として維持しない。

## 全タスク共通の実行規律

各タスク内で振る舞いごとに順番に行い、一度に全テストを足してRedを一括扱いしない。

- [x] 対象テストを作る／必要な既存期待値だけ更新する。既存公開名でimportできる状態を整え、対象アサーションの失敗理由を読む。未実装名のimport失敗だけをRedとしない。既存処理で初回Greenなら回帰保護として区別する。
- [x] 指定の単独コマンドを実行し、対象契約に由来するRedを記録する。
- [x] 最小実装後、同コマンドのGreenと関連回帰を確認する。
- [x] Refactor要否を確認し、実施した場合は再検証する。変更しない判断も記録する。
- [x] 下表の代表変異を隔離コピーで確認する。意図したアサーションFAIL・復元後成功を記録し、import失敗を数えない。製品作業ツリーへ変異を残さない。
- [x] 独立レビューへ契約・代表例・誤り・単独/全体の補完・未検証を渡す。Critical/Important解消後に再検証・再レビューし、全重大度と対応を学習記録へ残す。
- [x] import変更なら`.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`、`.venv/bin/ruff check .`、差分確認、対象テスト、明示ファイルだけステージ、通常フックでコミットする。コミット文言は各タスクの案。検査を迂回しない。

## Task 1：時計の値・更新・境界

**ファイル:** 新規`kaname_shogi/cli_clock.py`・`tests/test_cli_clock.py`。

**消費:** Side。**生産:** 上記CliClockSettings/CliClockの全操作。秒読みの残量・絶対原点をデータへ持ち込まない。

- [x] `test_rejects_invalid_clock_values`：設定・各残りへbool/負/小数/文字列、同時0、初期超過を入れてValueError。残り0・初期上限、初期0/秒読み30000は受理。
- [x] `test_updates_only_moving_side_without_carrying_byoyomi`：先手5000000000ns・後手3000000000ns、秒読み30000ms、先手経過20000000000nsで先手0・後手3000000000・秒読み30000。次の先手経過29999999999nsは時間内。先後反転も確認。
- [x] `test_preserves_submillisecond_remainders`：開始1000001nsから1nsを二回引き999999ns。msへ往復しない。
- [x] `test_expiry_includes_exact_nanosecond_boundary`：開始5秒＋30秒に34999999999/35000000000/35000000001nsを与えFalse/True/True。残り0・秒読み0を持つ有効な保存時計でも経過0でTrue。
- [x] `test_rejects_negative_elapsed_without_mutation`：経過-1はValueError、元時計不変。
- [x] Red→最小実装→Green：`.venv/bin/python -m unittest discover -s tests -p 'test_cli_clock.py' -v`。成功は全ケースOK。
- [x] 共通規律・独立レビュー後、`feat: add CLI clock state and expiry rules`としてコミット。

## Task 2：既存v1辞書公開と時計つき保存単位

**ファイル:** `game_record.py`・`tests/test_game_record.py`、新規`cli_session.py`・`tests/test_cli_session.py`。

**消費:** Task 1の時計型、既存v1変換・検証・合法再生。**生産:** GameRecord公開二操作とCliSession.save/load。

- [x] `test_public_payload_matches_literal_v1_and_replays_independently`：保存→読込の往復だけで期待値を作らない。既存テストの成り/駒打ちを含む手書きv1辞書とto_payloadを比較し、手書き辞書から再生した局面・履歴・独立性を確認。辞書を変えても記録を変えない。
- [x] `test_public_payload_rejects_illegal_history`：手書き不合法履歴と不正入れ子をfrom_payloadでも拒否。既存save/loadが同じ公開本体へ委譲することをspyで確認し、既存API・v1構造を維持。
- [x] `test_session_payload_contains_only_record_and_four_clock_values`：外側キーはformat/game_record/clock、形式名はkaname-shogi-cli-session-v1。clockはinitial_time_ms/byoyomi_ms/sente_remaining_ns/gote_remaining_nsのみ。先後123456789/987654321ns、初期600000ms・秒読み30000msを手書きJSONから読んで保存と照合。時計なしは従来v1、旧v1読込はclock=None。
- [x] `test_session_rejects_malformed_envelope_without_legacy_fallback`：外側/clockの未知・不足、null、配列、不正format、各欄のbool・負・float・文字列・上限超過・同時0、壊れたJSON・文字コード・不合法棋譜を拒否。新形式clock欠落/nullを旧v1へ落とさない。既存v1本体の許容範囲を独自に厳格化しない。
- [x] `test_session_propagates_io_error`：存在しない読込先・保存親なしをOSError。操作で元棋譜/時計は不変。原子的ファイル置換の新保証はしない。
- [x] Red→共有本体を公開操作へ移す最小実装→Green：`.venv/bin/python -m unittest discover -s tests -p 'test_game_record.py' -v`と同じ形式の`test_cli_session.py`。
- [x] 共通規律・独立レビュー後、`feat: expose record payloads and save CLI clocks`としてコミット。

## Task 3：五方式の制御付き一手と対局時計

**ファイル:** `cli.py`・新規`tests/test_cli_time_control.py`・既存`tests/test_cli.py`。

**消費:** Task 1の時計、`calculate_search_budget(remaining_ms, byoyomi_ms, config) -> SearchBudget`、`SearchControl(budget, started_ns, now_ns=now_ns)`、`game_search.search_move(position, policy, rng, control) -> SearchResult`。

**生産:** 拡張run_game。一手内部は`_run_computer_turn(record, rng, output_fn, move_selection_policy, clock, time_config, now_ns) -> tuple[CliClock, bool]`へ変更。boolは続行可否。時計は返却後に更新され、recordは着手の場合だけ変更する。

- [x] `test_five_policies_call_controlled_adapter_once_without_uncontrolled_prework`：五方式×先後でsearch_moveの同一公開入口・方針・共有rng・新controlを確認。コンピュータ手でcliのis_game_over/旧choose_move/全合法生成を呼ぶと失敗するspyを置き、人間手番のis_game_overは維持。旧シンボル削除後も再導入を検出できるよう禁止元のmovegen側も監視する。
- [x] `test_origin_precedes_budget_and_search_position_and_return_is_immediate`：イベント列は開始表示→開始時計→予算→探索用current_position複製→探索→返却時計→整形/出力/適用。担当判定用の局面取得と探索用取得を区別する。予算・複製で偽時計を進め、同じ原点・時計をcontrolが使用することを確認。実時間sleepなし。
- [x] `test_budget_receives_side_clock_in_ms_but_keeps_ns`：先後で600000ms/120000ms、秒読み30000ms、固定設定20/2/3÷4/2000で期待予算30000/60000、6000/12000。999999ns残りは渡す値0msで21000/28000、1000000nsなら1msで0/0。calculate呼出し引数と手計算予算、保持nsの双方を別にassertする。予算Noneを渡さない。
- [x] `test_each_turn_owns_new_control_and_keeps_rng_policy_config`：二手以上の先後自動手でcontrol別個、rng/方針/configは同一。停止要求を一手目へ付けても二手目へ継承しない。
- [x] `test_result_priority_suppression_expiry_resignation_and_move`：SUPPRESSEDは時間内外とも無着手・無勝敗、非抑制の手あり/なしは時間切れ優先、時間内COMPLETE/Noneは投了、COMPLETE/手・INTERRUPTED/手は返却手を一回適用し再探索しない。時間切れ後は指した手として表示しない。成功履歴だけが増える。
- [x] `test_human_checkmate_and_clock_are_preserved`：人間手番の既存詰みとコンピュータ手後の人間詰みを維持、人間入力・盤面表示・適用で偽時計を進めてもコンピュータ計時区間へ入らない。
- [x] `test_search_and_clock_failures_propagate`：探索のValueError/RuntimeError/OSErrorと時計例外・逆行で故障を正常結果へ変えない。同一例外は同一性もassert。逆行はValueError。Ctrl+C/EOFは別テストで既存正常終了。
- [x] 既存test_cliのchoose_move監視をsearch_moveへ更新。コンピュータ合法手なしを勝敗不明とする旧2テストは投了期待へ変更。新二方式の無制御search監視はsearch_controlledへ移し、固定偽時計でのみ深さ1→4の再開を確認。人間詰み・入力・rng・成り/駒打ち・履歴の既存保証は削らない。
- [x] 既存`test_new_modes_remain_fixed_for_game`と`test_each_new_mode_restarts_at_depth_one_on_each_computer_turn`は、コンピュータ手で呼ばなくなる`is_game_over(False, False, True)`を終了条件にしない。小さい玉だけ局面・固定時計で二回は本物の制御付き探索を呼び、三回目のCLI探索入口でKeyboardInterruptを発生させるラッパーへ移す。アダプター呼出しは終了用を含め3回、完了した探索と成功履歴は2回と区別し、二手分の方針・新control・深さ再開を検証する。
- [x] 既存`test_stops_after_a_move_gives_checkmate`は人間が後手コンピュータを詰ませるケースなので、後手のCOMPLETE/Noneによる「後手が投了しました。先手の勝ちです。」へ期待を変更する。人間手番で詰みを検出する既存ケースと、新規のコンピュータ着手後の人間詰みケースは詰み表示を維持する。
- [x] 既存`test_records_computer_drop_move`は`cli.legal_moves`の固定返却をやめ、CLIの探索入口から`SearchResult(COMPLETE, DropMove(歩, 5五))`を返す差替えへ移す。既存の駒打ち表示・履歴・盤上の駒のassertを維持する。既存テスト全体で残る旧入口差替えも検索し、禁止APIの足場をテスト都合で残さない。
- [x] Red→最小接続→Green：`.venv/bin/python -m unittest discover -s tests -p 'test_cli_time_control.py' -v`、`test_cli.py`も同形式。初回Greenとなる既存共通探索テストと今回のRedを区別する。
- [x] 共通規律・独立レビュー後、`feat: connect CLI turns to controlled game search`としてコミット。

## Task 4：時計入力・設定寿命・表示・実入口

**ファイル:** `cli.py`・`__main__.py`・`tests/test_cli_time_control.py`・`tests/test_cli.py`・`tests/test_cli_entrypoint.py`。

**消費:** Task 3のrun_game、既存loader。**生産:** choose_clock_settingsと実入口の設定寿命・診断・表示契約。

- [x] `test_clock_menu_defaults_units_and_retries`：空/空=600000/30000ms、0/30、10/0、0/0拒否後の再入力、前後空白・先頭0、全角数字・符号・小数・指数・文字を拒否。二欄をやり直すことと確定前に対局しないことをassert。
- [x] `test_main_prompts_and_loads_config_only_for_computer`：全モード、方針→時計→loader→run_gameの順、渡す設定と時計の同一性、loader一回、人間同士は全て不要。run_game直接呼出しも省略時一回/注入時0回を確認。複数手・読込後も再読込なし。
- [x] `test_config_failure_is_stderr_exit_one_before_game`：loaderのValueError/OSErrorはstderrに理由・終了1、run_game未呼出し。探索故障をmainが設定失敗扱いしない。EOF/Ctrl+Cはメニュー・時計入力・人間入力・探索・出力から起こし「入力を終了しました。」、無着手（適用前ケース）、再探索なし。出力途中や適用途中の原子性は保証しない。
- [x] `test_time_and_completion_display_matches_fixed_values`：固定経過1234567890nsは1.234秒、更新後598766msは09:58.766、秒読み30秒。COMPLETEは完了、INTERRUPTEDは通常停止、着手情報の後に盤面。60分超、1ms未満、先後ラベルも確認。完了深さ・評価・手の由来・停止原因断定が出ない。
- [x] `test_terminal_display_has_no_played_move`：固定時計で時間切れ文言・時計、投了文言・時計、抑制文言を区別。思考中表示は原点より前に各手一回。表示に起因する時計進行は次手へ持ち越して減算しない。
- [x] 実入口テスト入力を`2\n\n\n\nresign\n`へ更新し、モード→方針→時計二欄→初期盤面の順を確認。人間同士`1\nresign\n`は時計欄なし、時計入力途中EOFも終了0。実探索の時間/深さを期待するスモークは作らない。
- [x] Red→最小実装→Green：Task 3の二コマンドと`.venv/bin/python -m unittest discover -s tests -p 'test_cli_entrypoint.py' -v`。stderr故障は注入テストで検証し、同梱設定ファイルを壊さない。
- [x] 共通規律・独立レビュー後、`feat: add CLI clock setup and result display`としてコミット。

## Task 5：対局の保存読込への接続と全体確認

**ファイル:** `cli.py`・`tests/test_cli_time_control.py`・`tests/test_cli.py`、README・関連知識メモ・本計画・今回学習記録・docs/resume.md・docs/README.md。

**消費:** Task 2のCliSession.save/loadとTask 3/4の起動初期条件・現在時計。**生産:** 人間手番の既存save/load窓口で、棋譜と時計を一緒に確定する動作。

- [x] `test_load_commits_record_and_clock_together_or_preserves_both`：一時sessionを完全検証後に置換。不正clock・不合法履歴・壊れたJSON・I/O失敗後に同手番で再保存し、元棋譜/時計両方と比較。出力だけで状態保持を判断しない。
- [x] `test_clocked_then_legacy_load_uses_original_startup_settings`：起動10分/30秒→異なる5分/10秒の時計つき→旧v1で10分/30秒の双方初期値。旧棋譜補完メッセージをassert。予算JSON・モード・方式は固定。
- [x] `test_preserves_clock_in_human_game_and_legacy_without_clock`：同じ人間同士対局内で時計つき読込→人間手→外側形式保存→旧v1読込→時計なしv1保存を確認。新規棋譜も時計なしv1。コンピュータ参加の旧v1は起動条件から双方生成。
- [x] `test_loaded_computer_side_uses_its_saved_remainder`：後手手番の時計つきを人間対コンピュータで読込、保存された後手残りから予算、先手不変、返却後に一手を記録。コンピュータ同士は先後異なる残りをTask 3で確認し、探索中保存対話を追加しない。
- [x] `test_save_excludes_idle_time_and_preserves_error_state`：save/load/入力中に偽時計を進めても減算しない。保存失敗は同手番へ戻り棋譜/時計不変、着手確定後の保存に成功履歴と更新時計が揃う。終了イベント・制御・原点・予算係数が保存されない。
- [x] Red→最小統合→Green：CLI・時計/保存/棋譜の対象単独コマンド。全体検証と独立ブランチレビューを下記ゲートで実施。
- [x] READMEのCLI時計設定・保存互換・通常停止と時間切れ・未保証を実態に合わせ、search-stop/time-budgetのCLI接続状況も履歴を保持して更新。USIの実装済み記録と承認済み設計は維持。
- [x] 共通規律と最終独立レビュー後の指摘対応・再確認を完了（Critical 0 / Important 0 / Minor 0）。
- [x] `feat: integrate CLI session persistence and document clocks`として通常フック付きでコミット。本人の別承認前にmainへ統合しない。

## 検出力・独立期待値・補完範囲の対応

製品の出力から期待値を作らず、手書きの時刻・辞書・結果から期待値を決めた。[検出力点検](../knowledge/test-coverage-review.md)と`~/.codex/observations/test-driven-development.md`に沿った個別テスト・既存全体による補完・未検証範囲の結果は[実施記録](../learning/cli-search-time-control-plan.md)に残す。

| 契約/所有Task | 代表例・独立期待値 | 代表変異と意図するFAIL | 既存全体による補完と単独の限界 |
| --- | --- | --- | --- |
| 単位・更新/1,3 | 1000001−1−1=999999ns、先後反転、5秒消費20秒後0＋秒読み30 | msへ往復、相手減算、秒読み残量持越し → 時計数値assert | test_time_managementの手計算は式を補完するがCLI端数/所有側は確認しない |
| 時間切れ/1,3,4 | 35秒の±1ns、予算上限1秒超過かつ対局35秒未満なら着手 | >=を>へ、予算期限を勝敗へ転用 → 境界/履歴/表示assert | test_search_controlの期限包含は制御だけ。対局負け判定は新規が担当 |
| 制御接続/3 | 五方式、先後、準備遅延、二手で新control | 原点を局面複製後へ、旧入口再使用、control再利用 → イベント/呼出し/同一性assert | test_game_searchの旧三方式委譲・新方式の結果変換/実探索、test_usi_four_plyの同一制御を再利用。CLI原点は新規が担当 |
| 優先順・故障/3,4 | 抑制×時間内外、手あり/なし×時間内外、例外同一性 | 抑制を投了、着手を時計判定より先行、ValueError握潰し → 無履歴/無勝敗/伝播assert | USI結果/抑制競合テストは通信側だけ。CLI着手可否は新規が担当 |
| 入力・寿命/4 | 空欄、0/0、不正表記、人間同士、注入、省略、読込後 | 毎手loader、失敗時既定値へ → call_count/終了コードassert | test_time_managementはloader不正値/パス、既存entrypointはプロセス窓口。新しい入力順は新規が担当 |
| 表示/4 | 1.234秒、09:58.766、60分超、通常停止 | 四捨五入、架空深さ、指し手表示復活 → 固定文字列/非出力assert | 既存render/CLI表記が盤面・指し手を補完。出力原子性は未検証 |
| 公開棋譜・保存/2,5 | 手書きv1・外側JSON、異なる先後ns、clock null、連続読込 | clock不正を旧形式化、棋譜先行置換、起動条件上書き → 再保存payloadassert | test_game_recordの入れ子不正/合法再生/コピー、test_cliの読込失敗時保持を補完。往復だけでは共通の誤りを検出できない |

変異は各行の現実的な代表を選び、全候補を機械的に増やさない。複数アサーションが同じ誤りを検出した場合も、どの単独テストと既存全体が検出したかを記録する。重要な想定誤りがすり抜けたらケースを補強し再確認する。

## 全体検証と終了ゲート

- [x] `.venv/bin/python --version`、Ruff固定版・hooksPathとGit状態を確認する。
- [x] 関連回帰：`test_game_search.py`、`test_time_management.py`、`test_search_control.py`、`test_usi_clock.py`、`test_usi_four_ply.py`を実行。USI時計なし/0・抑制送信競合と共通探索は既存全体で補完する。
- [x] `.venv/bin/python -m unittest discover -s tests -v`で全体OK、`.venv/bin/ruff format --check .`・`.venv/bin/ruff check .`成功、`git diff --check`成功。過去件数は合格条件にしない。変更を伴う失敗は理由を調べ、単なる期待値削除で通さない。
- [x] 対象契約と変異結果・Refactor要否・未検証範囲・USIとの差分を渡し、独立ブランチレビュー。Critical/Important解消・再検証・再レビュー後、全重大度と対応を学習記録へ。
- [x] 文書相対リンクと作業ブランチ差分を確認し、結果を記録する。
- [x] 作業ブランチの具体的差分を本人へ提示し、main取込みについて別承認を待つ。
- [x] 別承認を受け、`codex/cli-search-time-control-plan`をmainへfast-forward統合した。統合後に全623テストと文書・Ruff検査を再確認した。
- [ ] 取り込み先検証後、最後の理解確認は一問だけ提示し回答を待つ。未回答を正解・完了としない。次テーマを自動開始しない。

未検証として残すもの：実時間性能・期限内応答・特定深さの実時間完了・全局面/OS/割込み/競合順・任意サイズ入力の成功・出力や保存ファイルの原子性・ShogiHome実機互換性・棋力。単一処理やOS待ちを強制切断しない。実時間観察が後で必要なら条件・測定対象を別途定め、今回の固定時計契約テストを性能測定と呼ばない。

## 計画作成チェック

- [x] 承認済み設計・本人回答・現物を照合し、撤回済み事項を復活させない。
- [x] 各設計要件をTask 1〜5と検証表へ対応付け、型名・操作・依存順・既存期待値の変更を記す。
- [x] 独立期待値・代表誤り・既存全体の補完・未検証を区別する。
- [x] 独立レビュー・指摘対応・再確認結果（初回0/1/0、対応後0/0/0）を[今回の学習記録](../learning/cli-search-time-control-plan.md)へ保存する。
- [x] 計画全体を提示し、2026-10-20に本人の明示承認「yes」を受領。実装開始指示は別途受領済み。
