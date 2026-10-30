# 支えのない狙われた駒の評価 実装計画

> **AIエージェントへの指示:** この計画の実施には `superpowerssuperpowers:executing-plans` または `superpowerssuperpowers:subagent-driven-development` を使用する。各ステップをチェックボックスで追跡し、AGENTS.mdが求める各タスクのRefactor要否確認後の独立レビューと、最終レビューを実施する。

**目標:** 相手の利きがあり味方の支えがない非玉駒を一枚ずつ数え、駒得と10対1で合成し、既存の一手選択器へ注入できる部品として実装・確認する。

**アーキテクチャ:** 新規 `undefended_piece` が公開利き操作を呼びC/Uを集計する。新規 `material_undefended_piece` が既存MとUを名前付き重みで合成する。既存 `choose_one_ply_move` にEを渡して接続を確認する。

**技術スタック:** Python 3.14以上、標準unittest、固定Ruff 0.16.10。新規依存なし。環境の現在値は実装開始時に改めて確認する。

**仕様:** [本人承認済み設計](2026-10-30-undefended-piece-evaluation-design.md)、[学習・回答記録](../learning/undefended-piece-coordination-evaluation.md)。2026-10-30、本人は設計全体へ「YES」と回答した。本人は2026-10-30に本計画全体と推薦したネイティブ方式を承認した。A段階の最後の理解確認と回答記録は完了し、本人はB段階へ進むことを選択済み。実装は次セッションから開始し、現時点で全Task未着手。

## グローバル制約

- 盤上の非玉13駒種を対象とし、玉は対象外だが攻撃元・支え役に含める。成駒は成った後の動きとする。
- 相手の利きが一つ以上、味方の支えが0の駒を一枚につき1とする。複数攻撃元も一枚は1、支えが一つでもあれば0。
- 現在の盤面の駒の動き方と遮蔽を使い、ピン駒を攻撃元・支え役に含む。合法な捕獲・取り返しの判定をしない。
- Cは手番・持ち駒に依存せず、盤面・手番・双方持ち駒を変更しない。対象自身を支え役に含めない。
- `U(P)=C(Q)-C(P)`、`E(P)=material*M(P)+undefended*U(P)`。既定10/1。Mは既存駒得の盤上・持ち駒を含む定義を用いる。
- 有効なBoard・Piece・Sideを前提に静的評価は玉なしの部分局面も受け付ける。合法性・総駒数・玉枚数の検査を追加しない。
- 重みは凍結dataclassで、materialは1以上、undefendedは0以上の整数。bool・floatを拒否。0でもUを計算する。
- 既存 `movegen.is_square_attacked` を公開操作として再利用する。既存一手選択器・既存方式の実装や評価の指定を変更しない。
- BはC/U・重み・合成Eと既存一手選択器への注入確認まで。CLI/USI・比較CLIへの公開、列挙値、保存形式、二手・四手への適用はC以降の別設計。
- 通常CLIのSFEN入出力、飛車可動性バージョン2、玉周辺安全度の合成、時間制御・千日手の変更は含めない。
- 英語名は日本語の意味とデータか操作かを説明する。公開docstringは引数・戻り値・副作用・前提・設計理由を記す。駒名は日本語を併記する。
- テストメソッド名は英語、日本語docstringの先頭行に振る舞い、本文に検出したい誤り・背景を記す。
- 振る舞いごとにassertionの失敗理由を確認して最小実装→成功確認→Refactor要否確認→独立レビュー。ImportErrorやAttributeErrorのみを振る舞いのRedとしない。
- Critical/Importantは解消し、再検証・独立再レビューを経てコミットする。通常フックを回避せず、unsafe修正を一括適用しない。
- 元の `/Users/oki2a24/kaname-shogi` の未コミット文書・比較データと、指定worktreeのC2未追跡成果物4件を保護する。clean/reset/切替・削除・上書き・一括ステージを元checkoutへ行わない。
- 長時間の比較・分析CLIは本人が端末で実行する。

## レビューフォーカス

基本例では見逃しやすい条件と、所有タスクの直接検査を示す。

1. 味方占有の対象へ届く支えを正しく検出し、対象自身を支えとしない（Task 1の四組合せ）。
2. ピンされた攻撃元・支え役、玉による攻撃・支え、玉自身の対象除外を区別する（Task 1）。
3. 成駒を対象に含み、成った後に追加された動きで支えを検出する（Task 1）。
4. 両側非零・不等を両視点と先後反転で評価し、符号・片側欠落を防ぐ（Task 1・2）。
5. 仮重み0でUの計算経路を維持し、注入後も一手詰み・候補枝の独立性と既存方式を保つ（Task 2・3）。

## 作業場所・開始前確認・共通サイクル

計画作成時の指定worktreeは `/Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi`。
2026-10-30確認時はmain・HEAD bf826066・origin/mainより20先行。現在地・未コミット文書は再確認する。
指定worktreeのmainに記録用文書案があり、C2の種一覧、worker 1中断出力、worker 4出力、分析結果は未追跡で保持中。
元checkoutへの取り込みはされていない。既存のC2結果を新規実測に流用しない。

- [x] 2026-10-30、本人が本計画全体と推薦したネイティブ方式を承認。
- [x] 2026-10-30、A段階の最後の理解確認を実施。本人回答`a`は正解A。回答と補足を学習記録へ記録した。
- [x] 2026-10-30、本人がB段階へ進むことを選択し、所定の引き継ぎを作成。新セッションから開始する。
- [x] 2026-10-30、指定worktreeでGit三コマンドを実行し、文書差分とC2成果物4件を確認した。
- [x] 2026-10-30、同名branchが存在せず指定worktreeが対象と確認後、そこで`codex/undefended-piece-evaluation`を作成・checkoutした。元checkoutは変更していない。
- [x] 2026-10-30にPython 3.15.2、requirements-dev.txt・`.venv/bin/ruff`のRuff 0.16.10、hook `.githooks`を照合済み。README条件内で、セットアップ再実行は不要。
- [x] 2026-10-30、製品変更前baseline`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py`は943件・67モジュール・21.826秒で成功。以後、製品コード・テスト変更なし。
- [x] 2026-10-30、承認済み設計・計画・学習記録・現在地・引き継ぎ文書を対象限定で通常のフック付きコミットへ記録。C2成果物4件は含めていない。
- [ ] 各TaskのRed→最小実装→Greenを振る舞い単位で繰り返す。Refactorの有無を確認し、独立レビューの重大度・対応・再確認を記録する。全体の最終独立レビューも行う。
- [ ] import追加・変更後は `.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`、`.venv/bin/ruff check .`、差分確認、変更に見合うテストの順。テスト0件を成功と扱わない。
- [ ] 各Taskの対象ファイルのみ `git add` で明示し、`git diff --cached --check` とステージ内容を確認して通常の `git commit` を行う。まとめた記録や知識メモは実施事実に応じて更新する。

実行方式の提案：**ネイティブ方式**で実行セッションの担当者が各Taskを実装し、各TaskのRefactor要否確認後に別の独立レビューを受ける。Task間で集計→合成→注入の依存があり、既存共通部品を変更しない範囲を小さく確認しやすいため。本人は推薦案のネイティブ方式を承認した。Taskごとに実装者とレビュー担当を分ける方式へ変更する場合は本人の希望を確認する。いずれも各Task・最終の独立レビューを省略しない。

## ファイル・依存方向

| ファイル | 責務 |
| --- | --- |
| `kaname_shogi/undefended_piece.py` | 新規。C/Uの公開読み取り操作と、公開利き判定の利用 |
| `kaname_shogi/material_undefended_piece.py` | 新規。不変重み、既存MとUの合成E |
| `tests/undefended_piece_support.py` | 新規。手書きの固定局面・左右反転・状態保存のテスト支援。テスト以外の生成基盤は作らない |
| `tests/test_undefended_piece.py` | 新規。C/U、玉・成駒・ピン・遮蔽・状態不変 |
| `tests/test_material_undefended_piece.py` | 新規。重みの検証・固定合成値・重み0の経路 |
| `tests/test_undefended_piece_selection.py` | 新規。既存一手選択器への新評価注入と既存の共通契約 |
| `docs/learning/undefended-piece-coordination-evaluation.md`、本計画 | 各Taskの実施・失敗理由・検証・Refactor・レビューと限界 |
| `docs/knowledge/undefended-piece-evaluation.md` | 実装完了後、確定した操作・条件・限界を記録 |
| `docs/README.md`、`docs/resume.md`等 | 現在地・知識メモへの参照。未接続の方式を利用可能と書かない |

依存は `material_undefended_piece` → `evaluation` と `undefended_piece`、`undefended_piece` → `model` と `movegen`。
既存 `movegen`・`evaluation`・`one_ply_selection` から新評価を逆輸入しない。

## 共通フィクスチャと独立期待値

`tests/undefended_piece_support.py` に `position(*pieces, side_to_move=Side.SENTE)` を用意する。
各要素は `(PieceType, Side, Square)`。新しい `Board` に `set_piece` し `Position` を返す。
`design_case(name)` は次の固定駒を手で置く。期待値は対象実装から生成しない。
`rotate_and_swap(pieces)` は各筋・段を `10-値`、所属を反転する。`snapshot(position)` は81マス・手番・両持ち駒の玉を除く7基本駒種の枚数を記録する。 テストからの読込は `from undefended_piece_support import ...` とする。標準discoverと並列ランナーはどちらもtestsディレクトリを探索パスに入れる。

共通：先手玉９九・桂５五、後手王１一。A=先手金４七・後手歩５四、B=先手金４六・後手歩５四、C=先手金４七・後手歩５三、D=先手金４六・後手歩５三。
それぞれ先手Cは1/0/0/0、後手Cは0、先手Uは-1/0/0/0、Mは14、既定Eは139/140/140/140。
Dは「攻撃なし・支えあり」で、A/B/Cと合わせ条件の四組合せを分ける。

双方非零：先手玉９九・桂５五・桂３五・金４七・歩７五、後手王１一・歩５四・歩３四・桂７四。
先手C=2・後手C=1、先手U=-1・後手U=+1、先手M=14・E=139、後手E=-139。
これらは[承認済み設計](2026-10-30-undefended-piece-evaluation-design.md)の手計算と今回追加したDを使う。
静的部分局面の実戦到達性は対象外。一手候補の合法性・非詰みはTask 3で別に確認する。

## Task 1：攻撃され支えのない盤上駒の枚数と差

**ファイル:** 作成 `kaname_shogi/undefended_piece.py`、`tests/undefended_piece_support.py`、`tests/test_undefended_piece.py`。
**消費:** `is_square_attacked(board: Board, target: Square, attacking_side: Side) -> bool`、`Position`、`Side`、`PieceType`、`Square`。
**生産:** `attacked_undefended_piece_count(position: Position, side: Side) -> int`、`attacked_undefended_piece_balance(position: Position, perspective: Side) -> int`。

- [ ] **1. 四組合せと両視点のテストを作成する。** `design_case` と双方非零の固定盤を使い、以下の独立値をassertする。13種や特殊条件は後続の振る舞いごとに追加する。

```python
for name, expected_c, expected_u in (("A", 1, -1), ("B", 0, 0), ("C", 0, 0), ("D", 0, 0)):
    position = design_case(name)
    self.assertEqual(attacked_undefended_piece_count(position, Side.SENTE), expected_c)
    self.assertEqual(attacked_undefended_piece_count(position, Side.GOTE), 0)
    self.assertEqual(attacked_undefended_piece_balance(position, Side.SENTE), expected_u)
    self.assertEqual(attacked_undefended_piece_balance(position, Side.GOTE), -expected_u)
```

- [ ] **2. Redを確認する。** 新公開操作が存在しない読込失敗は記録するがRed完了としない。必要なら公開シグネチャを備えた一時の0スタブだけを置き、Aで `1 != 0` 等の意図したassertion failureを確認する。実行: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p test_undefended_piece.py -v`。
- [ ] **3. 最小実装しGreenを確認する。** 一側ごとのCを走査する内部操作へ公開2操作を委譲する。対象非玉駒だけに敵の利きと味方の支えを公開利き操作で照会し、C(Q)-C(P)を返す。上記コマンドで実テストが発見され、終了0・OKを確認する。
- [ ] **4. 次の独立固定例を振る舞いごとに追加し、その都度Red理由→最小実装→Greenを記録する。** すでに満たす既存利きの接続・入力境界は初回Greenと記録し、未実装のRedと混同しない。

| テスト名 | 正確な固定例・期待値・検出対象 |
| --- | --- |
| `test_counts_four_attack_defense_combinations` | A/B/C/Dの先手C=1/0/0/0、後手C=0。AND/NOT・支え欠落・攻撃なしを誤計上する変異を検出 |
| `test_counts_multiple_attackers_and_defenders_once` | Aに後手角７三を追加して先手C=1。Bに先手金６六を追加して先手C=0。複数攻撃元の加算・支え一枚の無視を検出。追加駒自身も盤面全体で数える |
| `test_handles_both_sides_and_rotated_perspectives` | 上記双方非零例でC先手2・後手1、U先手-1・後手+1。180度回転し所属交換後のC先手1・後手2、U先手+1・後手-1。片側無視・符号反転を検出 |
| `test_includes_every_non_king_target_type` | 玉なし盤で先手の各13非玉駒を５五、後手歩を５四に置く。各場合C先手=1。成駒の対象除外や飛車だけ対象の誤りを検出。駒種と日本語名をテスト定義で併記 |
| `test_promoted_support_uses_current_movement` | 先手桂５五・後手歩５四。先手と金４六ならC先手0、未成歩４六なら1。先手馬４五なら0、角４五なら1。先手竜４四なら0、飛車４四なら1。成駒の金移動・馬の直交一歩・竜の斜め一歩の漏れを検出 |
| `test_excludes_king_as_target_but_uses_king_attacks` | 玉の枚数検査を前提としない部分盤で、先手玉５五・後手歩５四はC先手0。先手桂５五・後手王５四はC先手1。先手桂５五・先手玉４六・後手歩５四はC先手0。対象玉混入、攻撃玉・支え玉の除外を検出 |
| `test_counts_pinned_attacker_and_pinned_defender` | 攻撃側ピン：先手玉１九・飛５九・桂４四、後手王５一・金５三ではC先手1、C後手1。支え側ピン：先手玉５九・金５七・桂４六、後手王１一・飛５一・歩４五ではC先手1（金のみ）・C後手0。合法手への置換、ピン支えの除外を検出 |
| `test_sliding_blocker_preserves_support_boundary` | 先手桂５五、後手歩５四、先手飛５八。５七が空なら飛車が５五を支えC先手0。５七に先手桂を置くと射線が遮られC先手1。遮蔽物の貫通を検出。遮蔽駒自身が攻撃されないことも確認 |
| `test_turn_hands_empty_and_immutability` | Aの手番変更・両側持ち歩追加で先手C=1・後手C=0・先手U=-1は不変、盤・手番・持ち駒snapshotも呼出し前後で一致。空盤と玉だけの盤はC/U=0。手番依存・持ち駒混入・不要な玉検査・副作用を検出 |
| `test_propagates_attack_probe_errors` | 新モジュール側の `is_square_attacked` を例外送出に差替え、同じ例外を伝播しsnapshot不変。例外隠蔽を検出 |

- [ ] **5. 専用・関連検査を実行する。** 上記専用コマンド、および `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p test_square_attacks.py -v` を実行し、それぞれ発見件数とOKを確認。既存利きの全14駒種・対象占有・遮蔽検査を補完として利用し、集計固有のテストを省かない。
- [ ] **6. Refactor要否確認・独立レビュー・共通品質検査・限定コミット。** Critical/Importantは解消して再検証・再レビュー。記録に実際のRed/Greenと検出範囲を残す。

**GREEN条件:** C/Uの固定値、四条件、玉・全13種・成駒の動き・ピン・遮蔽・状態保持、既存利き関連検査が成功し、独立レビューのCritical/Importantが0。

## Task 2：駒得と新しい差の重み付き合成

**ファイル:** 作成 `kaname_shogi/material_undefended_piece.py`、`tests/test_material_undefended_piece.py`。
**消費:** Task 1の `attacked_undefended_piece_balance(position, perspective) -> int` と `evaluation.material_balance(position, perspective) -> int`。
**生産:** 凍結設定データ `UndefendedPieceWeights(material: int = 10, undefended: int = 1)`、`evaluate_material_undefended_piece(position: Position, perspective: Side, *, weights: UndefendedPieceWeights = 既定設定) -> int`。

- [ ] **1. 独立値と別重みの失敗するテストを作る。** A/B/Cと双方非零のE先手=139/140/140/139、後手=-139/-140/-140/-139をassertする。Aで `UndefendedPieceWeights(material=2, undefended=3)` は25、`material=2, undefended=0` は28。変更後の既定評価A=139を再確認する。
- [ ] **2. Redを確認する。** 読込エラーだけなら、正確な公開シグネチャ・凍結設定を備える一時の0戻り値スタブを作り、Aで `139 != 0` のassertion failureを確認する。実行: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p test_material_undefended_piece.py -v`。
- [ ] **3. 最小実装してGreenを確認する。** 既存MとTask 1のUを取得し `material*M + undefended*U` を返す。上記専用コマンドの件数とOKを確認する。
- [ ] **4. 次の振る舞いを各々追加し、Red/Greenまたは初回Greenとその理由を記録する。**

| テスト名 | 固定値・検出対象 |
| --- | --- |
| `test_combines_independent_expected_values` | A/B/C/双方非零の両視点で上記E。符号・係数・駒得だけへの固定を検出 |
| `test_validates_frozen_named_weights` | 既定10/1、material 0/-1/True/1.5、undefended -1/True/1.5でValueError、undefended 0は許容。代入はFrozenInstanceError。型・境界・変更可能の誤りを検出 |
| `test_custom_weights_and_zero_use_same_path` | Aで(2,3)=25、(2,0)=28、再度既定139。モジュール内U操作をMockで包み、undefended=0でも一回呼ばれることを確認。係数直書き・既定変更・0でUを省略する誤りを検出 |
| `test_hand_turn_and_missing_kings` | 玉なし盤のA相当でも139。Aに先手の持ち歩を1枚追加でM=15・U=-1・E=149、手番だけ変更してもE同じ。盤・手番・持ち駒snapshot不変。玉必須化・持ち駒のU混入を検出 |
| `test_propagates_balance_errors_without_mutation` | U操作の例外を伝播し、盤面・手番・持ち駒が不変。0重みも含め例外隠蔽を検出 |

- [ ] **5. 専用・関連検査。** 上記専用コマンド、Task 1の専用コマンド、`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p test_evaluation.py -v` を実行。件数とOKを確認する。
- [ ] **6. Refactor要否確認・独立レビュー・品質検査・限定コミット。** Critical/Importantは解消して再検証・再レビューし、独立期待値と検出範囲を記録する。

**GREEN条件:** 独立E・逆視点・重み境界・0経路・持ち駒と玉なし・例外/副作用、および関連検査が成功し、独立レビューのCritical/Importantが0。

## Task 3：既存一手選択器への注入と既存契約

**ファイル:** 作成 `tests/test_undefended_piece_selection.py`。必要なら支援操作を `tests/undefended_piece_support.py` に追加。既存選択器・方式の製品コードは変更しない。
**消費:** `choose_one_ply_move(position, moves, rng, *, evaluate)`、Task 2の評価操作、既存 `legal_moves`・`position_after_move`・`is_checkmate`。
**生産:** 新評価を渡したときの独立期待値と、旧評価を渡したときの選択器の挙動を確認する自動検査。

- [ ] **1. 設計Aから二候補を作る。** `BoardMove(Square(4,7), Square(4,6), False)` と `BoardMove(Square(4,7), Square(3,7), False)` が `legal_moves(position)` にあり、いずれも `is_checkmate(position_after_move(...))` がFalseとassertする。一手後のM=14/14、U=0/-1、E=140/139をassertする。
- [ ] **2. 接続期待値をテストする。** 先手・180度回転した後手で両候補の順序を反転しても新評価の選択は支えを作る手。後手の対応手は６三金→６四金（支えあり）・６三金→７三金（支えなし）。`material_balance` を同じ選択器へ注入すると両手同点で、注入乱数器の `choice` が元の候補タプルを一回受ける。新評価の重み0でも同じ同点・一回抽選を確認する。
- [ ] **3. 既存選択器の初回Greenと新たな振る舞いを区別する。** Task 2完了後の上記注入は既存の選択器によって初回Greenの可能性があり、その事実を記録する。Task 1/2で新評価の振る舞いを未実装Redで確認済みなら、接続検査に失敗を捏造しない。失敗なら原因を分析し、既存方式を変更する前に本計画の範囲を再確認する。
- [ ] **4. 既存共通契約の補完を確認する。** 既存 `tests/test_one_ply_selection.py` と `tests/test_king_safety_selection.py` を読み、詰み優先・同点・空候補・例外・成り/捕獲/打ちの異種兄弟枝の独立性に対応する既存検査名を記録する。今回のテスト支援に `mate_case(perspective)` を追加する。先手例は先手玉９九・飛５三・金４三、後手王５一・歩４一/６一/４二/６二。詰み手は５三飛→５二飛、通常手は５三飛→６三飛。後手例は配置を180度回転して所属を交換し、詰み手５七飛→５八飛、通常手５七飛→４七飛とする。既存テストの非公開補助をimportしない。両手の合法性、詰み手のみ `is_checkmate=True` を確認し、新評価の通常点に `10**30` を足しても詰み手が選ばれ、評価が通常枝だけに一回呼ばれ、元局面snapshot不変であることを候補順両方でassertする。既存の異種枝検査で検出できる契約と、新評価が読み取りであることをTask 1/2で直接検査した範囲を区別する。
- [ ] **5. 専用・関連検査。** `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p test_undefended_piece_selection.py -v`、同様のdiscoverで `test_one_ply_selection.py` と `test_king_safety_selection.py` を実行し、各々の発見件数とOKを確認する。
- [ ] **6. Refactor要否確認・独立レビュー・品質検査・限定コミット。** 新評価を受け渡すテスト以外に既存方式を変更していないか、`git diff` と明示ファイル一覧で確認する。Critical/Importantは解消し再検証・再レビューする。

**GREEN条件:** 両手番・候補順の新評価選択、同一選択器の駒得/重み0同点、一手詰み優先、既存共通契約の補完が成功し、独立レビューのCritical/Importantが0。

## 代表的な誤りの検出・全体確認・文書

- [ ] **1. 隔離コピーで以下の代表変異を一つずつ入れる。** `/private/tmp` の一時ディレクトリへ現時点の `kaname_shogi` と `tests` を複写し、指定worktreeの `.venv/bin/python3` を絶対パスで使ってコピー内から対象unittestを実行する。C2成果物・`.git`・元checkoutをコピーしない。各変異で指定assertionの失敗を確認し、ファイルを新たに複写し直して復元後に同じ検査が成功することを記録。import/構文エラーを検出成功としない。

| 代表変異 | 意図した失敗を確認する検査 |
| --- | --- |
| 味方の支え確認を無視して攻撃ありを数える | Task 1の四組合せBで先手C=0、成駒支え例 |
| 敵と味方の利き照会を逆にする | Task 1の四組合せAで先手C=1 |
| 対象駒から玉を除外しない | Task 1の攻撃された玉のC先手=0 |
| Uを `C(P)-C(Q)` に逆転 | Task 1双方非零の先手U=-1・後手U=+1 |
| 成駒の支えを未成駒の動きで扱う | Task 1のと金・馬・竜の支え例 |
| 合成時にU係数を既定2にする | Task 2のAのE=139 |
| 重み0ならU操作を呼ばずに駒得を返す | Task 2の重み0でのU操作呼出し確認 |

- [ ] **2. 最終検証。** import整理が必要なら実施後、`.venv/bin/ruff format .`、`.venv/bin/ruff check .`、`git diff --check`、専用3モジュール、関連の利き・駒得・一手選択、`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py` を実行。新たな失敗・変更がなければ全体を理由なく繰り返さない。
- [ ] **3. 最終独立レビュー。** 全差分について契約・手計算例・検出対象・既存検査の補完・未検証事項・Refactor判断・各Taskのレビューを渡す。Critical/Importantを修正した場合、影響する検査とレビューをやり直す。重大度と対応を記録する。
- [ ] **4. 知識・学習・入口を更新。** 実装した契約・限界を `docs/knowledge/undefended-piece-evaluation.md`、実際のRed/Green・代表変異・全体結果・レビュー結果を学習記録・本計画へ、現在地と索引を `docs/resume.md`・`docs/README.md` 等へ記録する。リンク・差分を確認し、実測していない棋力・全局面・速度を証明済みとしない。
- [ ] **5. 差分を限定して通常コミット。** C2の4成果物と元checkoutを保持し、明示された対象のみステージする。main統合と元checkoutへの取り込みは別途本人承認を得てから行い、取り込み先で検証する。

**GREEN条件:** 代表変異の狙った失敗と復元成功、専用・関連・全体検査、Ruff、文書点検、独立最終レビューでCritical/Important 0、記録・通常コミットまで完了。棋力、意図的な駒捨て、交換の連鎖、全盤面、最適重み、実時間性能は未検証。

## 計画の自己点検

仕様の各条件をTask 1/2/3または最終確認へ対応づけ、公開シグネチャと依存方向を統一した。
テスト期待値は手書き盤面から定め、既存利き検査・選択器検査による補完と新規接続検査を区別した。
上記レビューフォーカス5項目は各所有Taskの検査へ対応する。
実行コマンドは既存のunittest・並列ランナー方式に合わせた計画であり、計画作成時に製品テストを実行した結果ではない。 独立レビューの初回Minor 1は既存テスト非公開補助への依存で、固定局面を新規テスト支援に明記し、discoverと並列ランナーでの読込方法を明示して修正した。 再確認はCritical 0 / Important 0 / Minor 0で、静的な名前解決と先後反転の不整合なし。実際の合法性・詰み判定はTask 3の実行時に確認する。
