# 飛車可動性と差し替え可能な一手選択 実装計画

> **AIエージェントへの指示:** この計画の実装には `superpowerssuperpowers:executing-plans` を使用する。本人はネイティブ実行を選択済み。各タスクの追跡にはチェックボックスを用いる。

**目標:** 既存方式を維持し、飛車可動性の計数・重み付き評価・一手選択を別ファイルに分けた再利用可能な部品を作る。

**アーキテクチャ:** 飛車可動性は盤面と指定側から整数の差を返す。合成評価は設定データから重みを受け、一手選択は渡された評価操作で通常点を計算する。新規3ファイルを一方向に依存させ、既存movegenや共有駒得評価へ新方式の依存を逆流させない。

**技術スタック:** リポジトリの現行Python 3.14以上、標準unittest、固定Ruff0.16.10。新規依存なし。

**仕様:** [本人承認済み設計](2026-10-24-rook-mobility-design.md)、[学習・追加希望](../learning/rook-mobility-design.md)。2026-10-24、本人は設計全体と本計画を承認し、今回のロジックを別ファイルにして抜き差ししやすくすることを希望した。実装方式はネイティブ実行を選択した。

## グローバル制約

- 指定側をP、その相手をQとし、通常評価 E(P) = 10 × M(P) + R(P) − R(Q)。既存の駒得尺度は変更しない。
- 対象は盤上の未成飛車のみ。相手駒のマスを含めて止まり、味方駒のマスを含めず止まる。成り・不成で同じマスを二重計上しない。
- 竜・持ち飛の可動性は0。共通候補は飛車ごとに数える。自玉の王手確認・移動先の安全性を候補数に含めない。
- 合法な候補を独立した複製へ一手適用し、開始側視点を保つ。一手詰みの勝ち区分は通常整数より常に上。最高同点だけ一回抽選する。
- 重みは名前のある設定値にまとめる。.env・外部設定・設定UIを追加しない。
- CLI/USI/比較CLI公開、既存方針enumの追加、二手・四手への適用、既存方式の置換、通常CLIのSFEN入出力は含めない。
- 公開操作のdocstringは日本語で引数・戻り値・副作用・前提・設計理由を記す。型名はデータ、関数名は操作として説明する。テスト名は英語、日本語docstringに振る舞いと検出対象を書く。
- 各振る舞いでRedの理由を確認して最小実装・Green・Refactor要否確認・独立レビュー。Critical/Importantは解消後に再検証・再レビューする。
- import変更時は `.venv/bin/ruff check --select I --fix .`、続いて `.venv/bin/ruff format .`、`.venv/bin/ruff check .`、差分確認・相応のテスト・ステージ・通常コミット。フック回避なし。
- 全体テストは `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py`。テスト除外・skip・filterによる短縮はしない。逐次は共有状態・順序依存・並列差の診断時に併用する。

## レビューフォーカス

以下は基本例だけでは漏れる可能性がある条件。所有タスクのテストへ含める。

1. 後手開始で自分・相手双方に飛車があり、相手手番への更新後も開始側で採点する（Task 1・3）。
2. 駒打ち・成り・成駒取りで盤上と持ち駒の境界が変わる（Task 2・3）。
3. 別の評価関数へ差し替えても一手選択・詰み優先が働き、飛車評価へ隠れて依存しない（Task 3）。
4. 巨大な通常評価や後手側の詰みでも、通常点が勝ち区分を上回らない（Task 3）。
5. 複数候補の評価後も元局面・持ち駒・候補が保たれ、評価関数の故障が隠されない（Task 3）。

## ファイル構成と差し替え境界

| ファイル | 責務 |
| --- | --- |
| 新規 `kaname_shogi/rook_mobility.py` | 盤上の未成飛車の候補マス数を数え、指定側−相手側の差を返す |
| 新規 `kaname_shogi/material_rook_mobility.py` | 不変の重みデータと駒得・可動性の合成評価 |
| 新規 `kaname_shogi/one_ply_selection.py` | 通常評価操作を引数で受け、既存の複製適用・詰み判定・乱数で一手選択 |
| 新規 `tests/test_rook_mobility.py` | 計数・対象・視点・遮蔽・読み取り契約 |
| 新規 `tests/test_material_rook_mobility.py` | 固定期待値・尺度・重み・手種後の評価 |
| 新規 `tests/test_one_ply_selection.py` | 実局面での選択・評価差替・詰み・境界・独立性 |
| 更新 `docs/learning/rook-mobility-design.md` 等 | 実績・レビュー・検出範囲・現在地 |

依存は `rook_mobility → model, movegen`、`material_rook_mobility → model, evaluation, rook_mobility`、`one_ply_selection → model, move, movegen`。one_ply_selectionは新しい合成評価をimportしない。既存製品ファイルは変更しない予定。循環参照や既存の全面分割を避ける。

差し替えはCallable一つで行い、汎用エンジン登録機構・継承階層・プラグイン基盤は作らない。別評価を選ぶときは引数を替え、重み変更時は `functools.partial` など標準機能で束ねる。他の将棋ソフトへ持ち出す場合は、このリポジトリのPosition/Board等への依存を相手側に合わせる必要がある。無変更での外部移植までは保証しない。

## 共通の実施手順

作業ディレクトリは `/Users/oki2a24/kaname-shogi`、現在の文書ブランチは `codex/a1-rook-mobility-design`。実装はB1として本人選定後に作業ブランチで行う。main統合・pushは別途承認。既存未追跡2ディレクトリは保持・ステージしない。

各タスクでは下記の具体ケースを一度に全部実装せず、振る舞いごとに小さくRed→最小実装→Greenを繰り返す。新モジュール不在によるImportErrorだけをRedの証拠にせず、最小の宣言後、返値等のアサーションが仕様上の理由で失敗することを確認する。既存処理で初回から成功する例は既存Greenと記録する。

各タスクのRefactor要否確認後は、変更の有無にかかわらず独立レビューし、結果を学習記録へ残す。コミットは当該タスクのファイルと記録だけを明示的にステージする。

### Task 1：飛車可動性の読み取り部品

**ファイル:** 新規 `kaname_shogi/rook_mobility.py`、`tests/test_rook_mobility.py`。

**消費:** `rook_move_candidates(board: Board, source: Square) -> list[Square]`、`Board.piece_at(square)`、駒種・所属。

**生産:** `rook_mobility_balance(position: Position, perspective: Side) -> int`。盤上81マスで未成飛車だけの候補数を先後別に合算し、指定側−相手側を返す読み取り操作。手番・持ち駒は計数に使わない。

- [x] **1. 失敗するテストを作る。** SFENは `parse_sfen(...).position` で用意。下表の各値は手計算、視点は明記がなければ先手。

| テスト名 | 固定配置・期待するassertEqual等 |
| --- | --- |
| `test_counts_blocked_and_open_rook` | A=`8k/9/9/9/4R4/9/4P4/9/K8 b - 1` は13、Bは歩を４七（段文字列`5P3`）へ替えて16 |
| `test_counts_edges_without_center_bonus` | 先手飛だけの玉なし部分局面で５五・１五・１一・９九は各16 |
| `test_sums_each_rook_without_deduplicating` | 同じ側の飛車１一・９九、他なし：それぞれ16、合計32。共通の１九・９一を除かない |
| `test_subtracts_opponent_and_ignores_turn` | `p7r/9/8P/9/4R4/9/4P4/9/9 b - 1`。先手飛５五と歩５七、後手飛１一と歩１三に加え、後手歩９一が後手飛車の横候補を一つ塞ぐため先手13・後手9・差＋4、後手視点−4。手番だけ変更しても同値 |
| `test_uses_piece_side_after_rotation` | 上例を180度回転して所属交換：先手視点−4、後手視点＋4 |
| `test_excludes_dragon_and_hand_rook` | 先手飛５五のみ16、竜へ替えると0、盤上なし持ち飛のみ0、飛車なし0 |
| `test_counts_all_blocking_directions` | 飛車５五から２マス先の５三/５七/３五/７五へ、歩を一つずつ置く独立局面を検査。味方歩なら各13、相手歩なら各14。相手玉を一方向へ置いた場合も14 |
| `test_counts_pinned_and_unsafe_destinations` | 先手玉５九・先手飛５八・後手飛５一：双方15、差0。先手飛の横移動は合法でなくても候補に含む。先手飛５五・後手角３三のみなら差16で、角の利く５一も候補に含む |
| `test_preserves_position` | 計数前後のSFEN・手番・双方持ち駒が同一 |

危険先の固定例は先手飛５五・後手角３三とする。角は５一に利き、５一は飛車の候補。５一を含む候補数16を期待する。このテストで「５一の包含」を既存候補操作の固定期待値として確認し、集計値16と合わせて安全先限定の誤りを検出する。

中心例のアサーション（A/Bは上表の固定SFENから構築する）：

```python
self.assertEqual(rook_mobility_balance(a, Side.SENTE), 13)
self.assertEqual(rook_mobility_balance(b, Side.SENTE), 16)
self.assertEqual(rook_mobility_balance(a, Side.GOTE), -13)
```

- [x] **2. Redを確認。** `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p test_rook_mobility.py -v`。各対象振る舞いのassert失敗を記録する。
- [x] **3. 最小実装。** 上記シグネチャを実装。候補の再実装やlegal_moves呼出はしない。
- [x] **4. Green・Refactor・独立レビュー。** 同コマンド成功を確認。既存の飛車候補テスト（`test_movegen.RookMoveCandidatesTests`）が盤端・遮蔽を補完する一方、先後集計・対象選別・手番非依存は今回固有と点検する。
- [x] **5. 品質検査・コミット。** 共通のRuff手順、差分確認、学習記録を更新し、当該2ファイルと記録だけをステージして通常コミット。

**GREEN条件:** 全固定値・読み取り契約が成功し、独立レビューのCritical/Importantが0。

### Task 2：重み付き合成評価

**ファイル:** 新規 `kaname_shogi/material_rook_mobility.py`、`tests/test_material_rook_mobility.py`。

**消費:** Task 1の `rook_mobility_balance`、`evaluation.material_balance(position, perspective)`。

**生産:**

- `@dataclass(frozen=True) class RookMobilityWeights`：設定データ。`material: int = 10`、`mobility: int = 1`。bool等の非int、material≤0、mobility<0はValueError（計画でのアシスタント判断）。mobility=0を許し、比較時に項目を外せる。
- `evaluate_material_rook_mobility(position: Position, perspective: Side, *, weights: RookMobilityWeights = RookMobilityWeights()) -> int`：通常点を返す読み取り操作。詰み・探索・乱数は扱わない。既定値は不変データなので共有してよい。

- [x] **1. 失敗するテストを作る。** 下記の独立期待値を使う。

| テスト名 | アサーション |
| --- | --- |
| `test_combines_material_and_mobility` | Task 1のA/Bは173/176。後手視点−173/−176。元局面不変 |
| `test_accepts_named_weights` | A、重みmaterial=2・mobility=3で16×2＋13×3＝71。mobility=0なら32。既定の再評価は173のまま |
| `test_validates_immutable_weights` | 既定(10,1)。material=0/−1/True/1.5、mobility=−1/True/1.5をValueError。フィールド代入はFrozenInstanceError |
| `test_values_promotion_and_hand_boundary` | 玉なし５五飛のみ166、５五竜のみ170、持ち飛1枚のみ150。５四飛→５三の不成166と成170。持ち飛を５五へ打った後166、元は150 |
| `test_scores_capture_after_demoting_piece` | 先手飛５五・後手竜５四のみ。５五飛→５四で竜を取り、先手持ち飛が1枚：駒得30、盤上飛16で316。元局面の持ち駒は0のまま |

中心例のアサーション：

```python
self.assertEqual(evaluate_material_rook_mobility(a, Side.SENTE), 173)
self.assertEqual(evaluate_material_rook_mobility(b, Side.SENTE), 176)
self.assertEqual(
    evaluate_material_rook_mobility(
        a, Side.SENTE, weights=RookMobilityWeights(material=2, mobility=3)
    ),
    71,
)
```

- [x] **2. Redを確認。** `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p test_material_rook_mobility.py -v`。初期ImportError以外のassert失敗を確認する。
- [x] **3. 最小実装。** 設定クラスと合成操作のみ。係数はフィールドから読み、式へ10/1を重複して埋め込まない。
- [x] **4. Green・Refactor・独立レビュー。** 同コマンドとTask 1を確認。既存駒得テストは駒価値・持ち駒復元を補完、今回は係数・新項目と手種後の接続を検証する。
- [x] **5. 品質検査・コミット。** 共通Ruff手順と記録更新後、当該2ファイルと記録を通常コミット。

**GREEN条件:** 既定/別重み・成り/打ち/取り・視点・不変性が成功、Critical/Importantが0。

### Task 3：評価を差し替え可能な一手選択

**ファイル:** 新規 `kaname_shogi/one_ply_selection.py`、`tests/test_one_ply_selection.py`。

**消費:** `position_after_move(position: Position, move: Move) -> Position`、`is_checkmate(position: Position) -> bool`、呼出元から渡された通常評価操作。

**生産:** `choose_one_ply_move(position: Position, moves: tuple[Move, ...], rng: random.Random, *, evaluate: Callable[[Position, Side], int]) -> Move | None`。

evaluateは読み取り専用・整数を返す・開始側視点に従うという呼出契約。実行時の型検査や独自例外階層は増やさない。通常点のみを担当し、詰み優先は選択側が維持する。候補なしは評価・適用・詰み確認・抽選をせずNone。各候補を複製へ適用し、詰みなら(1,0)、それ以外は(0,evaluate(after,perspective))で比較。最高同点だけ元の順序で集め、一回choiceする。呼出側の評価例外・不正候補の既存例外は伝播する。

- [x] **1. 失敗するテストを作る。** 下記のassertを仕様として固定する。

| テスト名 | アサーション |
| --- | --- |
| `test_prefers_open_rook_from_equal_material` | Task 1のAで候補(５七歩→５六,５五飛→４五)、新評価では後者。静的値は172/176。候補を逆順でも後者。180度回転・所属交換・後手開始でも対応手 |
| `test_swaps_evaluator_without_changing_selector` | 同じ二候補で既存material_balanceを渡すと16/16で両手がchoiceの引数になる。新評価なら後者のみ。Spyで適用後局面と開始側が一回ずつ渡ることを確認 |
| `test_selects_best_ties_once` | 玉なし先手飛５五で候補５四・４五、両方166。choice呼出は一回で元順タプル。候補に低い手を加え、低い手は混入しない |
| `test_compares_negative_scores_without_clamping` | 注入評価が候補A−8/B−3を返すとB。任意の整数評価へ差し替えられることを、盤面から識別する固定関数で確認 |
| `test_mate_outranks_unbounded_normal_score` | 実詰み局面は下記。候補の詰み/通常を既存操作で確認し、通常評価が10**30でも詰み候補。先後両方、候補順両方。詰み候補には通常評価を呼ばない |
| `test_empty_candidates_have_no_effects` | 空候補はNone、rng.choice/evaluate/position_after_move/is_checkmateを呼ばない |
| `test_noncheck_no_reply_uses_evaluator` | 玉なし先手飛５五、候補５四だけ。相手は合法手なしだが非詰みで、evaluateは一回・先手視点で呼ばれ、通常選択される |
| `test_preserves_source_and_branches` | 歩取り・成り・駒打ちを含む別々の固定局面で元局面と各結果を確認し、複数の歩打ち候補では評価器から一枝を変更して他枝と元局面への漏れを確認。異種の捕獲・成り・打ちを兄弟候補とする組合せは直接確認しない |
| `test_propagates_failures` | 評価操作のRuntimeError、未知候補型のTypeError、既存適用が拒否する不合法候補のValueErrorを伝播。抽選しない |

詰みの固定配置：先手玉９九、先手飛５三、先手金４三、後手玉５一、後手歩４一・６一・４二・６二。候補は５三飛→５二（詰み）と５三飛→６三（通常）。後手ケースは180度回転・所属交換。期待詰みは５二飛を金４三が支え、後手玉の退路を後手歩が塞ぐことから独立に説明する。実局面と注入評価を組み合わせ、勝ち区分と任意整数の大小を確認する。同点の複数詰みは、この局面での５二飛成/不成を両候補としてchoiceへ両方渡す別ケースを作る。

低い候補混入の固定例はTask 1のAで５五飛→４五と５五飛→６五（各176）、５七歩→５六（172）を用いる。成り・打ち・取りの枝独立性はTask 2の固定例を基に、同じ開始局面で選べる別の候補を追加して確認する。移動後の局面は共有せず、一候補評価で盤面を変更するテスト用観測は別枝・元局面への漏れ検出に限定する（製品のevaluate契約は読み取り専用）。

中心例のアサーション（blocked/openedは上表の５七歩→５六/５五飛→４五）：

```python
self.assertEqual(
    choose_one_ply_move(
        a, (blocked, opened), rng, evaluate=evaluate_material_rook_mobility
    ),
    opened,
)
# 別ケースではchoiceを観測し、既存material_balanceなら両候補が同点。
choice.assert_called_once_with((blocked, opened))
```

このchoiceのアサーションは、material_balanceへ差し替えた別呼出だけを対象にする。新評価呼出と同じmock履歴へ混ぜない。

- [x] **2. Redを確認。** `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p test_one_ply_selection.py -v`。返値・choice引数・区分・視点のassert失敗を記録する。
- [x] **3. 最小実装。** 上記シグネチャの選択操作のみ。movegenの既存choose_moveやenumは編集しない。合成評価のimportなし。
- [x] **4. Green・Refactor・独立レビュー。** 同コマンド成功。差替で新評価への隠れた依存がないこと、詰み確認の防御探索以外の応手読みを追加していないことをレビューする。
- [x] **5. 品質検査・コミット。** 共通Ruff手順・記録更新後に当該2ファイルと記録を通常コミット。

**GREEN条件:** 実局面での選択・評価差替・詰み順序・境界・不変性・故障伝播が成功、Critical/Importantが0。

### Task 4：検出力点検・全体回帰・実施記録

**ファイル:** 上記6製品/テストファイル、学習記録、知識メモ新規 `docs/knowledge/rook-mobility-evaluation.md`、設計/本計画、`docs/02-project-direction.md`、再開案内・索引・ロードマップ・次テーマ候補。製品のCLI/USI機能説明は変わらないためルートREADMEは原則変更しない。

**消費:** Task 1〜3の公開操作と検証結果。**生産:** B1部品の検証証拠とレビュー・未検証範囲。C1公開済みとは記録しない。

- [x] **1. 契約ごとの点検。** 対象/独立期待値/検出対象/専用と関連の補完/未検証を学習記録へ整理する。
- [x] **2. 代表変異の検出力確認。** /private/tmp内の隔離コピー等で実施し、元ブランチの製品を汚さない。下表の意図したassert FAILと復元後成功を確認する。構文/import失敗は検出成功ではない。

| 変異 | 直接検出するテスト |
| --- | --- |
| 相手候補数を引かず足す | Task 1の双方非零＋4/−4 |
| 飛車を最初の一枚だけ数える | Task 1の二枚32 |
| 竜を含める | Task 1の竜0・Task 2の170 |
| 係数10を1にする | Task 2の173/176 |
| 開始側でなく適用後手番で採点 | Task 3の先後二候補選択 |
| 勝ち区分を通常評価へ落とす | Task 3の実詰み対10**30 |
| 注入された別評価を無視して既定の合成評価へ固定 | Task 3のmaterial_balance差替時のchoice引数 |

- [x] **3. 品質検査と全体テスト。** `.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`、`.venv/bin/ruff check .`、`git diff --check`、`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py`。全モジュール成功・失敗/skipなしを確認。件数・時間は今回の実測のみ記録し、過去705件を予告値にしない。
- [x] **4. 独立ブランチレビュー。** Refactor要否・専用/関連/全体・変異・文書を渡し、Critical/Important/Minorを記録。Critical/Importantは解消後、影響範囲を再検証・再レビューする。最終レビューはCritical 0 / Important 0で追加指摘なし。Task 3のMinor 1は混在する兄弟候補の直接検査がない範囲上の残件として学習記録へ残した。
- [x] **5. 文書検証・記録コミット。** 相対リンク・アンカーを確認し、未実施は未実施と明記。変更ファイルのみステージし通常コミット。
- [x] **6. 統合承認と取り込み先検証。** 本人の明示承認を受け `41910f4` からローカルmainへfast-forwardし、統合先 `06453c9` で全体テスト729件・48モジュール（14.634秒）、Ruff import整理・整形（90ファイル変更なし）・全体検査、`git diff --check`、8文書のリンク790件・アンカー5件（欠落0）を確認した。
- [x] **7. 最後の理解確認。** 統合後に一問だけ提示した。本人は「飛車の移動可能先マスを数え、先手から後手を引く定義」と回答し、未成飛車の候補先マスを数えて自玉の安全を確認した合法手数とは異なる点を補足として学習記録へ区別して残した。

**GREEN条件:** 今回の全体回帰・品質検査・代表変異・最終独立レビューがそろい、未検証とC1への帰還目標が記録される。実装完了とmain統合・C1公開・棋力確認を区別する。

## 計画作成時点の照合とセルフレビュー

- 既存API・import方向・テスト配置・通常ランナー・Ruff版/フックを読み取りで確認した。
- 既存操作を一時実行し、A候補13/M16、B候補16/M16、５七歩→５六と５五飛→４五の合法性・候補数12/16・非詰みを確認した。新評価・新選択・テストファイルは作成していない。
- Task 1＝可動性契約、Task 2＝重みと駒得合成、Task 3＝差替・一手選択、Task 4＝検出力/回帰/レビュー/記録と対応づけた。
- APIの引数型は全タスクでPosition/Side/Move/intに統一。重み付き操作は既定値で二引数Callableとして渡せる。特殊重みはpartialで指定できる。
- レビューフォーカス5件を所有タスクへ割り当てた。今は設計・計画の読み取り確認であり、将来の独立コードレビュー・実テストの代替ではない。
- セルフレビューでピン局面の双方候補数を15/15へ訂正した。また、詰み比較の通常候補に当初考えた９九玉→９八は相手詰みが継続するため不適切だった。既存操作による一時照合で、５三飛→６三と後手鏡像は合法・非詰み、５二飛成/不成と後手鏡像は合法・詰みと確認して固定した。新テスト実行や新実装の検証ではない。
- 専用コマンドは標準discoverで新規モジュールを指定する形式。実行時のパス・Python・テスト名を再確認し、期待されるassert失敗/成功を記録する。製品テストは承認前のため未実行。

本人は本計画を承認し、ネイティブ実行を選択した。Task 1はRed/Green、Refactor要否、独立レビュー、品質検査、記録を完了し、9テスト成功後に `8f39c9b` として通常コミットした。Task 2はbehavioral Redを確認後、設定と合成操作を実装した。専用5、Task 1の9、既存評価2テスト、全Ruff検査が成功し、独立レビューはCritical 0 / Important 0 / Minor 0。記録を含めて `e9a3d45` として通常コミットした。Task 3はRed/GreenとRuff検査、専用10・Task 1の9・Task 2の5・既存評価2の成功を確認。独立レビューはCritical 0 / Important 0 / Minor 1で、異種兄弟枝同士の相互干渉が直接未検証との指摘を、範囲内の軽微な残件として記録した。実装・テスト・記録を `bc6651b` として通常コミットした。Task 4では7代表変異を隔離コピー上で意図したassertion failureとして確認し、全体テスト729件/48モジュールが14.591秒で成功した。Ruffと差分検査も成功。差分 `41910f4..bc6651b` の独立コードレビューはCritical 0 / Important 0 / Minor 1で、同じ枝組合せの未検証を記録した。最終文書レビューもCritical 0 / Important 0で追加指摘なし。独立したリンク検査は790件・アンカー5件で欠落0、独立全体テストは729件・48モジュールが14.602秒で成功した。変異実行の再確認は行わず、7対象テスト名と検出契約を照合した。Task 4の検証・レビュー・記録を完了した。本人の明示承認を受けて `41910f4` からmainへfast-forwardし、統合先 `06453c9` で全体テスト729件・48モジュール（14.634秒）、Ruff、差分、文書リンク790件・アンカー5件（欠落0）を確認した。最後の理解確認では本人が飛車の移動候補先マスを数えて先手から後手を引くと回答し、正確な範囲と合法手数との違いを補足として学習記録へ残した。
