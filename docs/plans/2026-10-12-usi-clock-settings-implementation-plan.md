# USI時計受付・設定接続 実装計画

> **AIエージェントへの指示:** 実装には `executing-plans` または `subagent-driven-development` を使用する。2026-10-12、本人が「承認する」と回答し本計画を承認。計画作成時は提示まで。現在は本人の実装開始指示により手順を実行し、実績は末尾へ記録する。計画承認と実装開始指示、main取り込みの別承認を区別する。

**目標:** USI時計を検証し、現在局面の自分側時計と起動時に固定した設定を、既存の予算計算へ接続する。

**アーキテクチャ:** `usi_engine.py` に時計解析と先後選択の非公開境界を追加する。`main` が起動時に設定を読み、`run_usi_engine` へ注入する。時計なしはNone、時計ありは既存SearchBudgetで表し、今回は期間計算までを接続する。

**技術スタック:** Python 3.9、標準ライブラリのdataclasses・typing・unittest・unittest.mock。依存追加なし。

**仕様:** [承認済み全体設計](2026-10-11-clock-input-time-management-design.md)、[確認範囲](2026-10-12-clock-input-verification-review.md)、[既存部品の契約](../knowledge/time-budget.md)。本書のAPI・テスト案を含む計画内容は2026-10-12に本人承認済み。

**グローバル制約:**

- 説明・学習記録・知識メモは日本語で書く。
- 未決定の技術選択や将来の機能を先取りして複雑にしない。
- テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞い、続く本文に検出したい誤りや背景を書く。
- 公開インターフェースのdocstringに引数・戻り値・副作用・前提条件と設計理由を記録する。
- 式・設定の許容範囲・JSON方針・暫定値を維持する。main取り込みは別承認。

## 対象と段階の限界

対象は時計引数の検証、自分側時計の選択、起動時一回の設定読込と保持、既存予算計算の呼出し。今回の作業はこの実装の計画だけで、コード・テスト・設定変更、TDD、計測・対局・ShogiHome操作はしない。

将来この計画だけを実装しても、同期の合法手生成・choose_move・bestmove応答を維持する。予算は計算するが停止判定には使用しない。0予算でもこの段階では通常の有限比較を完了して返す。この暫定状態を「時間管理対応」「期限内応答」と呼ばない。全体設計の0予算で即停止要求・合法手未確保例外は、後続の探索制御を接続した段階で実現する。

単調時計・go読取時刻の取得、絶対期限、入力並行処理、停止要求、探索中断、予備手、候補評価・手選択の変更、応答抑制・故障回収は後続。現在のstop無視を今回拡張しない。CLI・将棋規則・起動ファイル・設定ファイル・既存time_management.pyは変更対象外。

## 現物とファイル構成

開始時点は2026-10-12、`/Users/oki2a24/kaname-shogi`、ブランチ `codex/usi-clock-plan-handoff`、HEAD `9ddc77f`、差分なし。別worktreeなし。Ruff 0.16.10はrequirements-dev.txtと一致、core.hooksPath=.githooks。

- 変更予定 `kaname_shogi/usi_engine.py`：時計解析、予算準備、設定注入、起動時診断。既存run_usi_engineの第3位置引数rngを維持する。
- 作成予定 `tests/test_usi_clock.py`：非公開時計解析と予算準備の契約。テスト内の固定設定は `TimeManagementConfig(20, Fraction(2), Fraction(3, 4), 2000)` とし、Git管理JSONから期待値を生成しない。
- 変更予定 `tests/test_usi_engine.py`：設定寿命・入口接続・実プロセスの不正時計診断。
- 変更予定 `tests/test_usi_engine_launcher.py`：別cwdと隔離コピー内の設定故障時の実行入口検証。
- 実装時の文書更新予定：README、`docs/knowledge/time-budget.md`、`docs/knowledge/usi-engine-response.md`、本計画、[学習記録](../learning/usi-clock-settings-implementation-plan.md)、再開案内。実装前には機能追加済みと更新しない。

## データと操作の案

すべて新規名は提案であり、現在存在するAPIと混同しない。

| 名前・シグネチャ | 日本語の意味・種類 | 契約 |
| --- | --- | --- |
| `_UsiClock` | USI時計データ | 非公開frozen dataclass、btime_ms:int、wtime_ms:int、byoyomi_ms:int。解析済み非負整数msのみを保持。生成元は下記パーサーに限定 |
| `_parse_go_clock(arguments: Sequence[str]) -> Optional[_UsiClock]` | go引数を解析する操作 | goを除くトークン列を受ける。副作用なし。不正/未対応はValueError。時計なしはNone |
| `_prepare_search_budget(clock: Optional[_UsiClock], side_to_move: Side, config: TimeManagementConfig) -> Optional[SearchBudget]` | 自分側時計を選び予算を準備する操作 | Noneなら計算せずNone。SENTEならbtime、GOTEならwtime。byoyomiと同じconfigを既存calculate_search_budgetへ渡す。時刻取得・入出力なし |
| `run_usi_engine(input_fn: Callable[[], str], output_fn: Callable[[str], None], rng: Optional[random.Random] = None, *, time_config: Optional[TimeManagementConfig] = None) -> None` | USIコマンドを処理する操作 | 既存位置引数を保持。注入設定があればファイルを読まない。省略時は最初の入力前に既存loaderで一回読む。今回追加するキーワード引数はテスト・mainからの注入境界 |
| `main() -> int` | 標準入出力を接続する操作 | 起動時に既存loaderで一回読みrunへ注入。設定ValueError/OSErrorはstderr診断・戻り値1、入力受付とUSI応答を開始しない。runのUSI ValueErrorも従来どおり診断・1 |

`Side` は先手・後手を区別する値（データ）。`SearchBudget` は目標・上限の期間データで、停止する操作ではない。`TimeManagementConfig` は不変の設定データ。起動時の所有者はmain、実行中はrunのローカル参照で保持し、局面状態・Difficulty設定とは分ける。runを直接呼ぶ利用者には省略時読込を用意し、代替の数値既定値は設けない。main→runでは二重読込しない。

## 時計解析の契約

既知の値付き項目はbtime・wtime・byoyomi・binc・winc。順序は任意。各項目は同値でも重複を拒否する。値は十進整数表記を整数msへ変換する。表記案は半角数字と任意の先頭符号（`+`/`-`）、先頭0を許し、変換後の負数を拒否する。`-0`は0。小数・指数・アンダースコア・非数値は拒否する。独自の最大値を設けず、floatを介さず標準intで変換し、処理系の安全制限は解除しない。この表記案も本計画のレビュー・承認対象。

1. 現行の未対応条件検査を解析境界へ移し、movetimeを追加。infinite/ponder/mate/depth/nodes/searchmoves/movetimeは値の有無を問わず未対応ValueError。
2. トークン列を順に調べ、未知トークンは一つずつ読み飛ばす。既知項目には直後の一トークンを値として要求し、欠落・別の項目名・未知語を値として読んだ場合は不正にする。未知語が先行しても後続の既知項目を見逃さない。
3. 五項目の重複・表記・負を検査。binc/wincは0のみ受理、正なら未対応ValueError。指定なしを加算0相当とし、加算値は時計データへ保存しない。
4. btime/wtime/byoyomiのどれもなければNone。binc/wincの0だけでもNone。いずれか時計項目があればbtime/wtime両方必須、byoyomi省略は0。

拒否理由には項目名と分類（重複、欠落、非整数、負、未対応、必須不足）を含める。全文一致へテストを固定せず、問題項目と理由を確認する。理由の優先順位は、未対応条件の検査を先行、残りは入力順、最後に必須不足を検査する。不正のgoではlegal_moves/choose_move/予算計算を開始せずbestmoveを出さない。

これは本プロジェクトの採用範囲であり、USI一般が加算やmovetimeを禁じるという意味ではない。[USI仕様](https://hgm.nubati.net/usi.html)はbtime/wtimeの先後とms、byoyomi、加算、movetime等を定義する。2026-10-12に再確認した。一般仕様の探索中入力要件は、この段階では未対応のまま。

## go受付順と後続への受渡し

runのgo分岐は、時計解析→現在局面のrequire_position→`position.side_to_move`で予算準備→既存の局内方針固定→legal_moves→choose_move→bestmoveの順。時計解析・予算準備が失敗した時は探索へ進めない。局面未設定は従来のValueError。局面の手番はSFENやmoves適用後の値を使い、対局開始時の先後・エンジン登録の名前・手数から推測しない。

予算準備の戻り値はgoごとのローカル `_search_budget` に保持し、今回の同期処理では参照しない。意図的な段階接続であることをコメント・公開docstring・利用案内へ明記する。観測用のコールバック、ログ、状態getter、将来用の探索コンテキストを追加しない。結合テストでは実操作をwrapしたspyで呼出しと戻り値を観測する。

後続ではこのOptional[SearchBudget]を探索制御へ渡す。Noneは時間停止なし、SearchBudget(0,0)は時間指定あり・即停止要求。値の真偽で判別せず `is None` を使う。次goでは再解析・再計算し、直前の時計・予算を流用しない。期間を絶対期限へ変換するのは後続責務で、go読取時刻を原点とする全体設計を維持し、計算後の時刻を原点に変更しない。

mainは設定読込だけを囲むtryでValueError/OSErrorをstderrの `USIエンジンエラー:` 接頭辞付き診断と1へ変換する。その後runを呼ぶtryでは従来のValueErrorだけを変換する。標準入力・出力のOSErrorを設定エラーと誤診断する広いcatchを作らない。run直接呼出しでは設定の例外を伝達し、出力しない。CLIへ読込を追加しない。

## 契約別の独立期待値と検出範囲

予算の期待値は既存関数の戻り値から作らず、承認済み式の手計算で固定する。既定のN=20、M=2、q=3/4、S=2000を維持。新規テストは入力の有無・先後・順序・符号・境界・連続goを反転させる。

| 契約 | 代表ケース・固定期待値 | 検出対象・既存補完 |
| --- | --- | --- |
| 時計なしと0 | 空、mystery、binc 0、winc 0、両加算0→None。btime 0 wtime 0→SearchBudget(0,0) | 0を未指定扱い、直前予算の流用。既存合法応答では区別不可 |
| 両時計必須 | btimeだけ、wtimeだけ、byoyomiだけ（0を含む）→ValueError | 不足を無制限扱い。新規で確認 |
| 自分側 | b=600000,w=120000,B=30000：先手(30000,60000)、後手(6000,12000) | 先手固定、相手時計、秒変換。同一盤面でSFEN手番を反転し手数17固定、moves 7g7fの後手でも確認 |
| 秒読み省略/0 | b=600000,w=0：後手、省略B→(0,0)、B=30000→(21000,28000) | 秒読み省略の補完漏れ、0残時間の誤判定 |
| 独自注入設定 | N=4,M=3/2,q=1/2,S=0、後手R=120000,B=30000→(30000,45000) | 既定設定へすり替え、注入の破棄。計算式自体は既存time_management検査が補完 |
| 値・重複 | 五項目それぞれの末尾欠落、直後が別キー、同値重複、-1、1.0、1e3、true、1_0→ValueError | 検査の部分適用。相手側時計も拒否する。正のbinc/wincも拒否 |
| 未知/順序 | mystery wtime 120000 extra btime 600000 byoyomi 30000と通常順が同値。mystery btime bad wtime 0→拒否 | 未知語で解析終了、未知語とともに既知キーを飛ばす誤り |
| 数値表記・大値 | +0、00、-0→0。+120000、00120000→120000。１２・١٢→ValueError。10^400の十進列を時計両側へ→値を保持 | float化、独自上限、記号の誤受理。全入力サイズの成功保証ではない |
| 設定寿命 | 入力受付前1回、usi/isready/複数go/usinewgameでも同一設定。注入時読込0回、別runは改めて読込 | go/新局で再読込、隠れた全プロセスキャッシュ。既存loaderのキャッシュなし検査を補完 |
| 起動エラー | 設定ValueError/OSError→stderrにパス・理由、stdout空、戻り値1、入力0回 | 黙った代替値、USI出力混入。実JSONの各型検査は既存テストを再利用 |
| 実入出力 | 不正時計→bestmoveなし、stderrに項目・理由、終了1。別cwdの起動→usi応答・終了0 | 関数mockだけでは確認できないmain/launcher伝達。既存flush・合法手・SFEN・三方針寿命を回帰再利用 |

## レビューフォーカス

1. 相手側だけ壊れていても拒否する（タスク1・3）。使う側だけ検査しない。
2. 未知語の前後にある既知項目の欠落/重複を見逃さない（タスク1）。
3. 連続goで時計なし・明示0・非0の区別を保つ（タスク2・3）。
4. 設定を複数go・usinewgameで読み直さず、別runには新しく読む（タスク3）。
5. 実起動で設定欠落/不正があってもusiokを先に送らず、元checkoutの設定をテストで壊さない（タスク3）。

## 承認後の実装手順（今回は実行しない）

各タスクは振る舞いごとにテスト追加→実行可能な境界で意図したRed確認→最小実装→Green→Refactor要否→独立レビューを行う。未定義APIのimportエラーだけをRed完了としない。既存処理で初回Greenならその事実を記録する。Critical/Importantは解消して再検証・再レビューする。

### タスク1：時計引数の厳密な解析

ファイル：usi_engine.py、作成test_usi_clock.py。消費：Sequence[str]。生産：_UsiClock、_parse_go_clock（上表のシグネチャ）。既存go分岐への接続はタスク3。

- [x] `test_parses_clock_and_omission`：通常/逆順/未知語混在に対して `(c.btime_ms,c.wtime_ms,c.byoyomi_ms)==(600000,120000,30000)`、省略Bは0をassertEqual。
- [x] `test_distinguishes_missing_clock_from_zero`：時計なし/加算0のみは `assertIsNone`、明示両0は `assertIsNotNone` と三欄0のassertEqual。
- [x] `test_rejects_invalid_known_fields`：上表の五項目ごとの不正・重複・必須不足をsubTestに列挙し `assertRaises(ValueError)`、項目/理由をassertIn。未知語直後の壊れた既知値と後続重複も含める。
- [x] `test_rejects_unsupported_go_parameters`：七種の未対応条件、正のbinc/wincを `assertRaises(ValueError)`。`test_accepts_integer_notation_and_large_values`：表記例0・+120000・00120000・10^400を固定整数へassertEqualし、全角数字１２・アラビア数字١٢はassertRaises(ValueError)。
- [x] `python3 -m unittest discover -s tests -p test_usi_clock.py -v` で各振る舞いのRed理由を確認し、最小実装後に失敗/エラー0のGreenを確認。
- [x] 隔離コピーで重複検査削除・片側必須検査削除・未知語で解析終了を個別注入。該当assertのFAILと復元後Greenを記録。元のcheckoutを誤り注入先にしない。
- [x] Refactor要否、独立レビュー、記録、品質検査を済ませ、対象だけステージして通常コミット。

### タスク2：自分側時計の選択と予算準備

ファイル：usi_engine.py、test_usi_clock.py。消費：_UsiClock、Side、既存TimeManagementConfig/calculate_search_budget。生産：_prepare_search_budget（上表）。既存runの変更はタスク3へまとめ、このタスクは純粋な準備操作を独立検証する。

- [x] `test_selects_budget_for_side_to_move`：上表の先後固定値と省略B/0残時間/独自設定をassertEqual。Noneでは計算spyの `assert_not_called()`、明示両0は `assertEqual(result, SearchBudget(0,0))`。
- [x] タスク1と同じ対象コマンドでRed→最小実装→Green。None・明示0・非0を連続して準備操作へ渡して各戻り値を確認する。
- [x] 隔離コピーへ自分側を先手固定、0をNone扱いを個別注入。単独検査のFAILと復元後Greenを記録。Refactor要否と独立レビュー、品質検査、記録、通常コミットを行う。

### タスク3：go接続・起動時読込・保持・エラー接続

ファイル：usi_engine.py、test_usi_engine.py、test_usi_engine_launcher.py。消費：既存 `load_time_management_config(path: Optional[Path]=None) -> TimeManagementConfig` とタスク1の_parse_go_clock、タスク2の_prepare_search_budget。生産：上表のtime_config注入引数を持つrun_usi_engine、mainの起動時一回読込、固定参照、stderr/終了1。新規CLI引数や環境設定は追加しない。

- [x] `test_go_prepares_budget_before_move_generation`：実際のprepareをwrapし、現在局面の手番と設定同一性、手計算予算、prepare→legal_moves→choose_moveの順序を確認。SFEN手番反転・同手数、moves適用後の後手を使う。
- [x] `test_each_go_uses_only_its_own_clock`：非0→時計なし→明示0→非0の連続goで戻り値が所定予算、None、SearchBudget(0,0)、所定予算になることをassertEqual。各goで通常bestmove一回を確認し、0で停止実装済みとは扱わない。
- [x] `test_invalid_go_never_starts_search`：有効positionの後に相手側不正・欠落・未対応条件を入れ `assertRaises(ValueError)`、legal_moves/choose_move/計算は `assert_not_called()`、outputs空を確認。局面なしの既存エラーも維持。
- [x] `test_run_loads_config_once_before_input`：loaderとinputの呼出し順を照合し、usi/isready/go/usinewgame/次position/go/quitでもloaderは `assert_called_once_with()`、prepareへ同一オブジェクトを渡す。明示注入時 `assert_not_called()`。別のrun呼出しには別設定を返すmock列を用い、二回目の結果と参照を確認。
- [x] `test_main_loads_and_injects_config_once`：mainの実処理を通し、読込一回とrunへのtime_config同一性を確認。run側の再読込も呼出し回数で検出する。
- [x] `test_main_rejects_invalid_or_unreadable_config_before_input`：loaderのValueError/OSErrorをそれぞれ注入し、`assertEqual(main(),1)`、stdout空、stderrに接頭辞/パス/理由、stdin未読・run未実行を確認。run直呼びでは同じ例外を伝達し出力しない。
- [x] `test_entrypoint_rejects_invalid_clock`：実プロセスで有効position後、不正時計/不足/正加算/movetimeを個別投入。終了1、bestmoveなし、stderrに項目・理由。診断全文には固定しない。
- [x] `test_launcher_loads_config_from_other_cwd`：絶対パスlauncherを一時cwdから起動しusi応答列一致、stderr空、終了0。`test_launcher_rejects_bad_config_before_usi`：tempへkaname_shogiパッケージ・launcher・configを配置した隔離コピーで、設定なし、不正JSON、キー欠落、不正UTF-8、設定先がディレクトリを個別検査。stdout空、stderrに対象パス/理由、終了1。元の設定を一時rename/書換えしない。権限依存chmodは使わずOSError伝達を関数テストでも確認する。
- [x] タスク3対象のRed→最小実装→Green。実プロセスには既存の有限timeoutとfinallyで回収する手順を使う。探索の時間保証を測る検査にはしない。
- [x] 隔離コピーでgoごと再読込、main注入の破棄（run再読込）、設定エラー時の正常終了への変更、go分岐のprepare呼出し削除を個別注入。意図したFAILと復元後Greenを記録。Refactor要否・独立レビューを完了し、品質検査・記録・通常コミット。既存合法手なしresign、局面保存、三方針の局内固定/次局継承、rng共有も回帰確認する。

### 終了検証・記録・統合ゲート

- [x] import追加・変更時 `.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`、`.venv/bin/ruff check .`、差分確認の順に実施。
- [x] `python3 -m unittest discover -s tests -p test_usi_clock.py -v`、同じ形式のtest_usi_engine.py・test_usi_engine_launcher.py・test_time_management.pyを実行し失敗/エラー0。全体 `python3 -m unittest discover -s tests -v` で回帰確認。
- [x] 将来の実装記録に契約・固定期待値・検出対象・単独/全体補完・未検証、実コマンドとRed/Green/誤り注入、Refactor判断、Critical/Important/Minorと対応を記す。
- [x] 利用案内を「時計検証・設定読込・予算計算まで接続、時間停止は未実装」と更新。文書の相対リンク/見出し、git diff --check、差分を確認し、独立最終レビュー後に対象だけステージ・通常コミット。フックを回避しない。
- [ ] 実装・検証・レビュー・記録がそろった時点で本人へ提示。main取り込みは別承認後、取り込み先検証を行う。最後の理解確認は一問だけ提示して回答を待つ。後続の探索制御を自動開始しない。

## 未検証・承認段階

今回の新規テスト案と誤り注入は一切未実施。既存374件成功は前テーマの結果で、今回の結果ではない。設定四欄・JSON精度・計算式の詳細は既存test_time_management.pyが補完するため重複再実装しない。既存合法応答テストだけでは今回の時計選択/設定寿命を保証しない。

期限比較、並行入力、停止中断、途中評価、一回応答の競合、故障回収、実時間安全性、係数の最適性、全OS、任意サイズ入力の資源耐性は後続または未保証。未実装の範囲を今回のテストで保証しない。

2026-10-12、本人が「承認する」と回答し本書の計画内容を明示承認。今回の依頼は計画提示までなので、承認後も実装開始指示を得るまでコード・テスト・設定変更やTDDへ進まない。Git保存・main取り込み・pushは今回実施しない。[学習・レビュー記録](../learning/usi-clock-settings-implementation-plan.md)を参照する。


## 実装開始後の現在状態

2026-10-12、本人「では実装を開始して下さい。適切なスキルを使い、進めて下さい」により実装開始。上記の「今回は実行しない」「未実施」「Git保存しない」等は計画作成時の履歴。時計解析・先後選択・起動時設定保持・goへの予算準備を実装し、全389件成功、Ruff成功、代表変異9種を検出。タスク1・2の保存bf3ca1b、計画保存d942386。タスク3・ブランチ全体の独立レビューは最終Critical/Important/Minor 0。タスク3と記録を9fd4f10へ保存し、最終全389件成功（6.185秒）。main取り込みは未承認・未実施。詳細は学習記録。


## main統合後の現在状態

2026-10-12、本人回答「1」によりローカルmainへの取り込みを承認。元ディレクトリ /Users/oki2a24/kaname-shogi で `git switch main`、`git merge --ff-only codex/usi-clock-plan-handoff` によりee3cac0から341c106へ早送り統合。作業ブランチ保持、別worktree・pushなし。Git書込みは権限昇格を使用し、自動承認レビューの拒否・フック回避なし。

取り込み先で `.venv/bin/python -m unittest discover -s tests -v` は389件成功（6.018秒）、`.venv/bin/ruff format --check .` は31ファイル整形済み、`.venv/bin/ruff check .` と `git diff --check` 成功。統合後は状態記録のみ更新し、コード変更なしのため全体テストを重複実行しない。上記のmain未承認・未実施は統合前の履歴。最後の理解確認は未回答で、終了ゲートは未完了のまま保持する。
