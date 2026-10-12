# 時計設定・時間配分 実装計画

> **AIエージェントへの指示:** 実装には `executing-plans` または `subagent-driven-development` を使用する。本人の明示承認前に実行しない。下記は計画作成時に将来手順として記載。2026-10-12、本人の実装開始依頼後の実績をチェックへ反映。

**目標:** 四設定を厳密に読み、承認済みの式から整数msの時間予算を返す小さい単位を作る。

**アーキテクチャ:** 予定する `kaname_shogi/time_management.py` に設定データ、予算データ、読込と純粋な計算操作を置く。USI入口からはまだ呼ばない。設定ファイルは承認後の実装で作成し、Git管理する。

**技術スタック:** Python 3.9、標準ライブラリのjson・decimal・fractions・pathlib・dataclasses・unittest。依存追加なし。

**仕様:** [承認済み全体設計](2026-10-11-clock-input-time-management-design.md)、[確認範囲](2026-10-12-clock-input-verification-review.md)。2026-10-12、本人が本計画案を承認。

**グローバル制約:**

- 説明・学習記録・知識メモは日本語で書く。
- 未決定の技術選択や将来の機能を先取りして複雑にしない。
- テストメソッド名は英語とし、日本語docstringの先頭行に確認する振る舞い、続く本文に検出したい誤りや背景を書く。
- 公開docstringに引数・戻り値・副作用・前提条件・設計理由を記載する。
- 承認済みの式・許容範囲・JSON方針・暫定値を維持する。main取り込みは別承認。

## 範囲と完了の意味

対象は設定データの検証、UTF-8 JSON読込、作業ディレクトリに依存しない既定パス、予算計算。USIコマンド解析、自分側時計の選択、起動入口接続、入力並行処理、探索中断、時計原点・期限判定、計測・対局は含めない。`usi_engine.py`、既存探索、既存テストは変更しない。

全体設計の「起動時一回読込・実行中固定」「欠落等でstderr診断・非0終了」は後続USI組込みの契約。今回は不変データと例外伝達までを作り、その外部動作を完成済みと呼ばない。CLIに設定読込を追加しない。

## データと操作の案

作成予定: `kaname_shogi/time_management.py`、`tests/test_time_management.py`、`config/time-management.json`。実装後の記録は今回の[学習記録](../learning/time-budget-implementation-plan.md)から案内する。

| 名前 | 日本語の意味・種類 | 契約 |
| --- | --- | --- |
| `TimeManagementConfig` | 時間設定データ | frozen dataclass。allocation_turns:int、maximum_multiplier:Fraction、byoyomi_target_ratio:Fraction、response_margin_ms:int。全引数必須、代替既定値なし |
| `SearchBudget` | 時間予算データ | frozen dataclass。target_ms:int、maximum_ms:int。0≤target_ms≤maximum_ms |
| `load_time_management_config(path: Optional[Path] = None) -> TimeManagementConfig` | 設定を読む操作 | Noneはモジュールの `Path(__file__).resolve().parents[1] / "config" / "time-management.json"`。明示パスはそのまま使用。読込以外の副作用・キャッシュなし |
| `calculate_search_budget(remaining_ms: int, byoyomi_ms: int, config: TimeManagementConfig) -> SearchBudget` | 時間予算を計算する操作 | 自分側の非負整数msを受ける。bool・負数・非整数をValueErrorで拒否。入出力・時刻取得・設定変更なし |

直接構築でも設定の範囲を `__post_init__` で検証する。整数欄は厳密なint（bool除外）、倍率・割合はFractionを受け、別型はValueError。SearchBudgetも型と大小関係を検証する。係数にfloatを直接渡すAPIにはしない。読込側がJSON整数/十進数をFractionに正規化する。

## JSONと精度

四項目だけを必須とし、次の暫定値を実装時にファイルへ保存する。未検証値で、安全・最適の保証ではない。

| キー | 許容範囲 | 暫定値 |
| --- | --- | --- |
| allocation_turns | 整数1以上 | 20 |
| maximum_multiplier | 有限数1超 | 2 |
| byoyomi_target_ratio | 有限数0超1未満 | 0.75 |
| response_margin_ms | 整数0以上 | 2000 |

`json.load(parse_float=Decimal, object_pairs_hook=重複検査操作, parse_constant=拒否操作)` を使う。整数欄はJSON整数表記を要求し、20.0や2e1は拒否。倍率/割合はJSON整数または十進数（指数表記を含む）を許し、文字列・bool・null・配列・objectは拒否する。トップレベルはobject。未知・欠落・重複（値が同一でも）を拒否。NaN/Infinity/-Infinity、コメント、末尾カンマ、余分な文書、不正UTF-8も拒否。

Decimalは十進文字列の保持と有限性確認にだけ使用し、有限値をFractionへ変換して比較・乗算する。Decimalの演算コンテキストやfloatを介さない。`floor(a*p/d)` は非負整数の `(a*p)//d` で計算する。桁数・倍率に独自上限を加えず、例えば1e400を有限数として扱う。Python処理系の資源限界は残り、無限の入力や資源枯渇への成功保証ではない。整数解析は処理系の標準intを使い、安全制限を解除しない。

構文・構造・値・文字コードの不正は理由の分かるValueError、読込不能はOSErrorを呼出し元へ伝える。既定値への置換なし。JSONDecodeErrorはValueErrorの一種として扱える。公開読込の診断には対象パスと不正キー/理由を含め、標準出力へ書かない。後続入口でこれらをstderrへ表示し非0終了する。MemoryError等を設定不正へ一括変換しない。

根拠: [JSON](https://docs.python.org/3.9/library/json.html)、[Decimal](https://docs.python.org/3.9/library/decimal.html)、[Fraction](https://docs.python.org/3.9/library/fractions.html)、[Path.resolve](https://docs.python.org/3.9/library/pathlib.html#pathlib.Path.resolve)。3.9系列公式資料は3.9.6以後の修正も含むため、その差を動作保証に流用しない。

## 式と独立期待値

R=remaining_ms、B=byoyomi_ms、N=allocation_turns、M=maximum_multiplier、q=byoyomi_target_ratio、S=response_margin_ms。すべて時間はms。

R>0: 基本目標=R//N、時計境界=max(0,R+B−S)、上限=min(floor(基本目標×M),時計境界)、目標=min(基本目標,上限)。

R=0: 上限=max(0,B−S)、目標=floor(上限×q)。分母Nは手番で減らさない。結果は期間であり、絶対期限・実際の応答時間ではない。

以下の値は式を手計算した固定期待値としてテストに記す。製品関数から期待値を作らない。

| 設定 | R / B | 目標 / 上限 | 検出対象 |
| --- | --- | --- | --- |
| 暫定 | 600000 / 30000 | 30000 / 60000 | 単位・通常配分 |
| 暫定 | 60000 / 30000 | 3000 / 6000 | 固定分母 |
| 暫定 | 10000 / 30000 | 500 / 1000 | 正の小残時間 |
| 暫定 | 1 / 30000 | 0 / 0 | 0切替を早める誤り |
| 暫定 | 0 / 30000 | 21000 / 28000 | 秒読み分岐 |
| 暫定 | 0 / 1999,2000,2001 | 0/0, 0/0, 0/1 | 余裕前後・切捨て |
| 暫定 | 0 / 0 | 0 / 0 | 両0 |
| 暫定 | 100 / 0 | 0 / 0 | 負の時計境界の抑制 |
| 暫定 | 100 / 1903 | 3 / 3 | 時計境界と目標の制限 |
| N=3,M=3/2,q=3/4,S=0 | 11 / 0 | 3 / 4 | 除算を先に切捨て、倍率積切捨て |
| N=1,M=2,q=29/100,S=0 | 0 / 100 | 29 / 100 | float丸めによる28への誤り |
| N=1,M=10^400,q=3/4,S=0 | 10 / 0 | 10 / 10 | 巨大有限倍率の乗算 |
| N=1,M=2,q=3/4,S=0 | 10^400 / 0 | 10^400 / 10^400 | 巨大時計のfloat変換 |

同じ設定オブジェクトへ同じR/Bを繰り返し渡して同じ予算になることも確認する。先後選択・時計なしのNone表現はこのAPIの責務に持ち込まない。

## レビューフォーカス

1. 重複キーの後勝ちを防ぐ（タスク1）。
2. 非有限値と巨大有限値を混同しない（タスク1・2）。
3. boolを整数として受け入れない（タスク1・2）。
4. 作業ディレクトリ変更で設定パスが変わらない（タスク1）。
5. 目標を上限へ制限し、余裕不足で負予算を返さない（タスク2）。

## 承認後の実装手順（今回は実行しない）

### タスク1: 設定データと厳密な読込

生産API: 上表のTimeManagementConfigとload_time_management_config。ファイル: time_management.py、test_time_management.py、config/time-management.json（すべて上記の完全な予定パス）。

- [x] 設定の受理・拒否を一振る舞いずつテスト化。`test_loads_provisional_config` は各欄が20、Fraction(2)、Fraction(3,4)、2000に一致することをassertEqual。`test_accepts_config_boundaries` はN=1、S=0、M=1.0000000000000000001、q=0.0000000000000000001および0.9999999999999999999を受理し正確なFractionと照合。1e400も受理。
- [x] `test_rejects_invalid_config` で各キーの欠落・重複、未知、トップレベル配列/null、各欄のbool/文字列/null/object/配列、N=0/-1/1.0、S=-1/0.0、M=1/0/-1、q=0/1/-1、非有限・不正JSONを個別subTestにしassertRaises(ValueError)。直接構築の不正も別に確認する。
- [x] `test_reports_config_read_errors` で一時ディレクトリの存在しないファイル・ディレクトリ指定はOSError、不正UTF-8はValueError。権限依存のchmod検査は避け、読込OSErrorをmockでも注入し伝達を確認する。パス/理由を例外文字列で照合。
- [x] `test_default_path_is_independent_of_cwd` は実装時のGit管理設定を別cwdから読み、四値一致を確認。明示パスは一時ファイルで別の合法値を読み、ファイル更新後の再呼出しは更新値になる（キャッシュなし）。既存返却データは変わらず、frozen違反はFrozenInstanceErrorになることを確認。
- [x] `python3 -m unittest discover -s tests -p test_time_management.py -v` でRed確認。未定義による読込エラーは準備段階だけであり、操作ごとに実行可能な最小境界を置いて、受理/拒否のアサーションが意図した理由で失敗することを確認する。
- [x] 契約に沿う最小実装と暫定設定を作り、同コマンドでGreen。独自制限・代替値・USI接続を足さない。
- [x] 重複検査の除去、bool検査の除去を隔離コピーへ個別注入し、該当アサーションのFAILと復元後Greenを確認。Refactor要否と独立レビューを記録し、Critical/Important解消後に品質検査・差分確認・ステージ・通常コミット。

### タスク2: 正確な予算計算

消費API: TimeManagementConfig。生産API: SearchBudgetとcalculate_search_budget。変更はtime_management.pyとtest_time_management.py。

- [x] `test_calculates_budget_examples` へ期待値表の各行をsubTestとして追加し、戻り値の二欄を固定整数とassertEqual。`test_keeps_allocation_turns_fixed` は複数回の呼出しと設定不変を確認する。
- [x] `test_rejects_invalid_clock_values` はR/Bそれぞれの-1、True、1.0、"1"、NoneをValueErrorと確認。SearchBudgetの負・逆転・bool・非整数も直接構築で検査する。
- [x] 個別にRed確認→最小実装→Green。読み込みエラーだけをRedにしない。計算に現在時刻や局面・先後・手番数カウンタを持ち込まない。
- [x] 隔離コピーへ、R=0分岐の無視、時計境界制限の除去、最終目標minの除去、除算の先行切捨て省略、割合積のfloat化を一つずつ注入。上表の該当ケースが意図したアサーションでFAILすること、復元後Greenを確認する。正常入力の計算呼出しでValueErrorが出た場合は `self.fail("正常入力で予算計算が例外になった")` へ変換する。最終目標min除去はSearchBudgetの不変条件による拒否をこのアサーションで検出し、他の値不一致による検出と区別して記録する。
- [x] Refactor要否確認と独立レビュー。Critical/Importantは解消して再検証・再レビュー。結果を学習記録へ残す。

### 終了検証と記録

- [x] import追加時に `.venv/bin/ruff check --select I --fix .`、続いて `.venv/bin/ruff format .`、`.venv/bin/ruff check .`、差分確認。
- [x] 対象テストと `python3 -m unittest discover -s tests -v` を実行し、終了コード0・失敗/エラー0を確認。回帰に含む既存USI合法応答・方針寿命・launcher・CLI・棋譜検査は、新規計算の検証を代替しない。
- [x] 記録へ契約/代表ケース/検出対象/既存補完/未検証、実コマンド・結果・Refactor判断・重大度別レビューを記す。JSON知識・利用案内は実装済みの範囲に限定し、USI時間管理が動くとは記載しない。文書リンクとgit diff --checkを確認してステージ・通常コミット。フックを回避しない。
- [ ] 実装・検証・レビュー・記録がそろったら提示。main取り込みは別承認を得てから行い、取り込み先で検証。最後の理解確認を一問出し回答を待つ。自動的にUSI組込みへ進まない。

## 検証範囲と残る限界

新規単独検査は設定と計算の契約を対象にする。既存テストは将棋規則・方針・通常USI応答の回帰を補完するが、新規係数・丸め・エラー拒否は補完しない。誤り注入は上記代表誤りに限定し全誤りへの検出証明ではない。

未検証として残すもの: 起動時一回読込とstderr/非0終了の実接続、自分側時計選択・USI解析、計時開始・期限比較、並行入力と故障回収、途中評価・探索停止、一回応答、実時間安全性、数値の最適性、全OS移植、任意サイズ入力の資源耐性。数値検査の成功から対局時の時間内応答を保証しない。

## 計画の承認段階

2026-10-12作成。今回は文書の作成・レビュー・提示まで。コード・テスト・設定は未変更、TDD未開始。提示後、本人が「承認する」と回答し計画内容を明示承認。今回の作業範囲は計画までのため、実装開始へ自動継続しない。レビュー結果と文書検証は[学習記録](../learning/time-budget-implementation-plan.md)へ記す。その後、本人が計画文書のGit保存を許可。作業ブランチへ保存し、main統合・pushは行わない。


## 実装結果

2026-10-12、本人の準備後実装開始の明示依頼を受け、タスク1・2を実装・検証・独立レビュー済み。新規12件/全体374件成功、代表変異7種を検出、最終レビューCritical/Important/Minorすべて0。最後の未完了項目はmain統合の別承認と取り込み先検証・理解確認。詳細は学習記録。上記の「今回は実行しない」等は計画作成時の範囲であり、その後の開始承認と実績は本節が現在状態。

2026-10-12、本人の選択「1」でmain統合を承認。1235931→3d01687へ早送り、取り込み先374件/Ruff/文書検証成功。上記のmain未統合・未承認は統合前の記録。残る未完了は最後の理解確認への本人回答とその記録。
