# 支えのない被攻撃駒の価値を反映する 実装計画

> **AIエージェントへの指示:** タスクごとの実行には `superpowerssuperpowers:executing-plans` または `superpowerssuperpowers:subagent-driven-development` を、本人が選ぶ実行方式に従って使用する。本計画の明示承認前はTDD・製品コード・テスト変更・実装を始めない。追跡用チェックボックスは実施証拠がある場合だけ更新する。

**状態:** 2026-11-02作成。設計全体・本計画・実装開始、推奨されたネイティブ方式を本人の「YES」で承認済み。Task 1〜3の実装・テスト・レビュー・記録が完了し、topic branchへのコミット待ち。main統合・pushは別途承認待ち。

**目標:** 支えのない被攻撃駒の価値合計差を実装し、従来の枚数差を置き換えた通常評価を既存の一手選択器へ渡して検証する。

**アーキテクチャ:** 新しい集計モジュールと合成モジュールを追加し、既存の駒価値・利き・V（支えあり低価値駒脅威）・一手選択を再利用する。従来U（支えのない被攻撃駒の枚数差）と公開済み方式を変更しない。今回は旧集計部品の抽象化を先取りせず、既存契約と新集計の一致を固定例で確認する。

**技術スタック:** 現行READMEのPython 3.14以上、標準ライブラリ、unittest、固定版Ruff。新しい依存パッケージなし。

**仕様:** [本人承認済み設計](2026-11-02-undefended-piece-value-design.md)。実行者は[学習と合意](../learning/undefended-piece-value.md)も読む。

## グローバル制約

- 対象は玉以外。未成駒と成駒の全13駒種を含む。
- 攻撃元が複数でも対象一枚は一度だけ加える。
- 玉は対象外だが、攻撃元・支え役には含む。
- 持ち駒は対象・攻撃元・支え役にせず、手番は参照しない。
- 利き・遮蔽・ピンの扱いは既存 `is_square_attacked` と同じ。
- 価値の唯一の定義元は既存 `piece_reference_value`。価値表を複製しない。
- 成駒を元の価値へ戻さない。玉の架空の価値を設けない。
- 玉なし部分局面を受け付ける。入力の盤面・持ち駒・手番を変更せず、依存操作の例外を伝播する。
- 一手詰みを通常点より優先し、開始側視点、候補ごとの独立複製、同点最高からの抽選を維持する。
- 作業先は `/Users/oki2a24/kaname-shogi`、branchは `codex/next-evaluation-after-docs`。別worktree・cloneを使わない。
- 未追跡比較データ、`.agents/tasks/`、C2保護4件と退避アーカイブを変更しない。main統合とpushはそれぞれ別途承認。
- ShogiHomeでのU候補実践はアクセス可能との本人連絡後に再提案する保留目標。
- 説明・docstringは日本語。M（駒得）・U（支えのない被攻撃駒の枚数差）・V（支えあり低価値駒脅威）には意味を添える。英語の公開名はデータか操作かを説明する。
- 公開操作のdocstringに引数・戻り値・副作用・前提・例外・設計理由を記す。テスト名は英語、日本語docstringに振る舞いと検出対象を記す。
- 比較CLI接続・比較実行、通常CLI・USI公開、二手・四手探索への適用は本計画の対象外。後続で従来10M+U+Vと今回版を比較する方針は維持する。

## レビューフォーカス

設計だけでは具体ケースが未確定だったリスクを以下で補い、担当タスクで検査する。

1. 両側に異なる価値の対象がある場合も双方を集計し、差の符号を正しくする（Task 1、E局面）。
2. 全13駒種と玉対象除外を分け、成駒を元の価値へ戻さず、玉の価値照会もしない（Task 1、駒種別検査）。
3. 支えを付けた際、価値合計から外れて既存Vへ移る動作を正しく合成する（Task 2、C局面）。
4. 係数0でも依存操作を一度呼び、例外と入力不変性を保つ（Task 2、依存先差替検査）。
5. 新評価を渡しても一手詰みを巨大な通常点より優先し、先後や候補順に依存しない（Task 3、既存mate_caseの接続検査）。

## ファイル構成と公開インターフェース

| ファイル | 役割 |
| --- | --- |
| 新規 `kaname_shogi/undefended_piece_value.py` | 対象価値合計と視点差の読み取り操作 |
| 新規 `kaname_shogi/material_piece_threat_value.py` | 新しい名前付き重みデータと合成操作 |
| 新規 `tests/undefended_piece_value_support.py` | 座標で作るA〜E局面。期待値を製品関数から生成しない |
| 新規 `tests/test_undefended_piece_value.py` | 集計契約・境界・反転・不変性 |
| 新規 `tests/test_material_piece_threat_value.py` | 合成・重み・委譲・従来との差 |
| 新規 `tests/test_undefended_piece_value_selection.py` | 新評価注入と一手選択への接続 |
| 新規 `docs/knowledge/undefended-piece-value.md` | 実装後の確定契約と限界。未実装時には作らない |
| 更新 `docs/learning/undefended-piece-value.md`、本計画、`docs/resume.md`、`docs/README.md` | 実測・レビュー・承認段階・参照先 |

### Task 1が提供する読み取り操作

```python
attacked_undefended_piece_value(position: Position, side: Side) -> int
attacked_undefended_piece_value_balance(position: Position, perspective: Side) -> int
```

前者は指定側の非負の価値合計、後者は相手側合計−指定側合計。`value` は価値を表す語だが、この関数名全体は集計する操作。型や値データの名称ではない。

### Task 2が提供するデータと操作

```python
@dataclass(frozen=True)
class PieceThreatValueWeights:
    material: int = 10
    undefended_value: int = 1
    supported_threat: int = 1

evaluate_material_piece_threat_value(
    position: Position,
    perspective: Side,
    *,
    weights: PieceThreatValueWeights = _DEFAULT_PIECE_THREAT_VALUE_WEIGHTS,
) -> int
```

`PieceThreatValueWeights` は合成の重みを保持する設定データ、`evaluate_material_piece_threat_value` は局面を採点する読み取り操作。式は `weights.material * M + weights.undefended_value * 価値合計差 + weights.supported_threat * V`。旧Uを加えない。係数は駒得1以上、他0以上の厳密な整数（bool/floatを拒否）。不正時は順に `ValueError("駒得重みは1以上の整数にしてください")`、`ValueError("対象価値差重みは0以上の整数にしてください")`、`ValueError("支えあり脅威重みは0以上の整数にしてください")`。

## 共通の固定局面と独立期待値

盤上は表の駒だけ、持ち駒なし、先手視点。A〜Cは承認済み設計の配置をそのまま使う。テスト用 `design_case(name: str) -> Position` と `design_case_pieces(name: str) -> tuple[PieceSpec, ...]` を新supportに置き、既存supportの `position`、`rotate_and_swap`、`snapshot` を再利用する。未知名は `ValueError`。玉なし部分局面を対局用の合法局面と呼ばない。

| 局面 | 先手 | 後手 | M（駒得） | U（枚数差） | V（支えあり脅威） | 先手価値合計／後手価値合計 | 価値合計差 | 従来点／今回点 |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| A | 飛4五、歩1八 | 桂5三 | 10 | −1 | 0 | 15／0 | −15 | 99／85 |
| B | 歩4五、飛1八 | 桂5三 | 10 | −1 | 0 | 1／0 | −1 | 99／99 |
| C | 飛4五、歩1八、銀3六 | 桂5三 | 18 | 0 | −1 | 0／0 | 0 | 179／179 |
| D | 飛4五、歩1八、角8五、金7六 | 桂5三、歩8四 | 31 | −1 | −1 | 15／0 | −15 | 308／294 |
| E | 飛4五、歩8五 | 桂5三、銀8四 | 2 | 0 | 0 | 15／8 | −7 | 20／13 |

D：金7六と飛4五が角8五を支え、歩8四が角を攻撃。飛4五自身は支えがなく桂5三に攻撃される。E：飛4五が歩8五を支える。歩8五は銀8四に利き、銀8四は支えがない。後手桂は飛車を攻撃する。歩は支えがあるが攻撃元銀より安いためV対象外。逆視点は差と通常点の符号反転、180度回転所属交換は対応側の値を保持する。

## 実行開始時の点検（承認後）

- [x] Git状態・branch・HEADと保護対象を再確認し、計画対象以外の製品コード変更が紛れ込んでいないことを確認した。
- [x] `.venv/bin/python --version` はPython 3.15.2、`.venv/bin/ruff --version` はrequirements-dev.txt固定版0.16.10、`git config --local --get core.hooksPath` は`.githooks`であることを照合した。既存hookは変更していない。
- [x] 変更前baselineは `python3 scripts/run_tests_parallel.py` で1039件・84モジュール・24.601秒、成功。

## Task 1：価値合計と視点差

**ファイル:** 新規集計モジュール、新support、`tests/test_undefended_piece_value.py`。

**消費:** `piece_reference_value(PieceType) -> int`、`is_square_attacked(Board, Square, Side) -> bool`、既存モデル・support。

**提供:** 上記の価値合計・視点差の2操作。

- [x] 振る舞いごとに、以下の名前と固定アサーションを持つテストを作り、その振る舞いの失敗理由を確認する。新モジュール不在のimport errorでRed完了とせず、最小のimport可能な入口を用意した後、値の不一致で失敗させる。テスト全件を先に作り切らず、対応する最小実装とGreenを繰り返す。

```python
# test_design_values_and_balances（A/B/Cと反転）
self.assertEqual(value(design_case("A"), Side.SENTE), 15)
self.assertEqual(value(design_case("B"), Side.SENTE), 1)
self.assertEqual(value(design_case("C"), Side.SENTE), 0)
self.assertEqual(balance(design_case("A"), Side.SENTE), -15)
self.assertEqual(balance(design_case("A"), Side.GOTE), 15)
# test_both_sides_nonzero（Eと180度回転所属交換）
self.assertEqual(value(design_case("E"), Side.SENTE), 15)
self.assertEqual(value(design_case("E"), Side.GOTE), 8)
self.assertEqual(balance(design_case("E"), Side.SENTE), -7)
```

- [x] `test_each_current_piece_value_and_king_exclusion`：対象駒を先手4五、攻撃元を後手桂5三に固定し、13駒種を一つずつ置く。期待値は設計の明記値をテスト内の手書き表に置く（製品表から作らない）。同位置の先手玉は0、玉の価値照会がないことも確認。先手対象に加え、反転した後手対象も確認する。
- [x] `test_sums_multiple_undefended_targets_per_side`：先手銀3七と飛車5五を後手歩3六・5四がそれぞれ狙い、価値合計23／後手歩二枚の2、視点差−21。飛車が銀を支えない離れた配置と先後反転も確認する。複数対象を足さず最後の一枚で上書きする誤りを検出する。
- [x] `test_attack_support_and_multiple_attackers`：Aへ後手銀4四を追加しても先手価値15。Aの桂を5二へ移すと先手価値0。Aへ先手銀3六を追加すると0（C）。同条件で反転側も検査し、攻撃元数加算・支え条件逆転を区別する。
- [x] `test_king_attack_support_shield_and_pin`：玉の攻撃は先手飛4五／後手玉4四で先手価値15。玉の支えは先手飛4五・玉3六／後手桂5三で先手価値0。遮蔽は先手角4五／後手飛4一に後手歩4三を入れる前後で13→0。ピンは先手飛4五・飛5九／後手桂5三・玉5一で先手価値15（後手桂が玉の前にピンされても利きを含める）。後手桂が攻撃する別の先手駒や余分な支えがないことを配置から確認する。
- [x] `test_empty_turn_hands_no_mutation_and_errors`：空盤・玉だけは0。Aの手番交換・両側持ち駒追加でも先手15／後手0を保ち、`snapshot`で全入力不変。新モジュール側の利き・価値照会を一つずつ例外へ差し替え、同じ例外を伝える。
- [x] 最小実装は盤上の非玉駒を走査し、既存利き操作で対象判定後に参考価値を一度加える。視点差は両側集計へ委譲する。旧Uの既存コードは変更しない。
- [x] 実行：`python3 -m unittest discover -s tests -p 'test_undefended_piece_value.py' -v`。期待：読み込みエラーなし、各契約のFAIL確認後の成功。既存 `test_undefended_piece.py` も同形式で実行し、従来枚数契約を補完する。
- [x] Refactor要否を確認し、対象条件共通化が今回必要か理由を記録する。独立レビューの時期は本人選択の実行方式に従うが、Critical/Importantがあれば先へ進めず解消する。

## Task 2：新しい合成評価と重み

**ファイル:** 新規合成モジュール、`tests/test_material_piece_threat_value.py`。

**消費:** Task 1の視点差、既存 `material_balance(Position, Side) -> int`、`supported_lower_value_threat_balance(Position, Side) -> int`。

**提供:** `PieceThreatValueWeights`、`evaluate_material_piece_threat_value`。

- [x] `test_default_design_scores_and_old_policy_unchanged`：A〜Eの表の従来点と今回点をそれぞれ固定値でassertする。新評価の点から旧評価の期待値を生成しない。逆視点と180度回転所属交換も確認。旧モジュール・既存公開方式が新集計へ暗黙に変わっていないことを調べる。
- [x] `test_custom_and_zero_weights`：Dで全項非ゼロを使い、名前付き係数の違いを検査する。

```python
self.assertEqual(evaluate(design_case("D"), Side.SENTE), 294)
self.assertEqual(evaluate(design_case("D"), Side.GOTE), -294)
self.assertEqual(evaluate(design_case("D"), Side.SENTE,
    weights=PieceThreatValueWeights(material=3, undefended_value=2,
                                    supported_threat=4)), 59)
# 3*31 + 2*(-15) + 4*(-1) = 59
self.assertEqual(evaluate(design_case("D"), Side.SENTE,
    weights=PieceThreatValueWeights(undefended_value=0)), 309)
self.assertEqual(evaluate(design_case("D"), Side.SENTE,
    weights=PieceThreatValueWeights(supported_threat=0)), 295)
```

- [x] `test_weights_strict_ranges_and_frozen`：既定(10,1,1)、許容境界(1,0,0)。materialの0・−1・True・False・1.0、他の−1・True・False・1.0を拒否し、上記の正確なValueError文言を確認する。フィールド代入は `FrozenInstanceError`。
- [x] `test_calls_dependencies_once_even_at_zero_and_propagates`：依存操作3個をmockし、M=7・価値合計差=−3・V=−2、係数(3,2,4)で7、(1,0,0)で7。正確な引数で各一度呼ばれることを確認。全依存操作の例外を伝え、入力snapshotを保つ。価値合計差とV（支えあり低価値駒脅威）は係数0でも例外を伝える。M（駒得）は有効最小係数1で例外を確認する。Mの係数0は契約違反なので使わない。旧U操作を合成式へ呼び足さない。
- [x] 各振る舞いについてassertionのFAILを確認してから最小実装し、Greenを確認する。係数検査・日本語docstringも実装する。実行：`python3 -m unittest discover -s tests -p 'test_material_piece_threat_value.py' -v` と既存 `test_material_piece_threat.py`。
- [x] Refactor要否・レビュー対応を記録する。重みの最適化や候補方式の追加へ範囲を広げない。

## Task 3：一手選択への注入確認、回帰検証と記録

**ファイル:** 新規 `tests/test_undefended_piece_value_selection.py`、上記知識・学習・入口文書。選択器本体やCLIは変更しない。

**消費:** Task 2の新評価、既存 `choose_one_ply_move(position, moves, rng, *, evaluate) -> Move | None`、`legal_moves`、`position_after_move`、`is_checkmate`、既存supportの `mate_case`。

**提供:** 新評価を注入しても既存選択契約を保つ証拠と、実装済みの知識メモ。

- [x] `test_prefers_support_for_rook_both_sides_and_orders`：先手玉9九・飛5五・金4七、後手玉1一・歩5四、先手番から、支え手 `BoardMove(Square(4,7), Square(4,6), False)` と非支え手 `BoardMove(Square(4,7), Square(3,7), False)` を検査する。両候補が `legal_moves` に含まれ、一手詰みでないことを確認する。全合法手中の最善を主張せず、この二候補間の検査とする。

```python
# 各着手後、開始側視点で固定値をassertする。
# M=23、後手歩は飛車から利かれ支えなしで価値1。
self.assertEqual(evaluate_material_piece_threat(supported_after, side), 230)
self.assertEqual(evaluate_material_piece_threat(unsupported_after, side), 230)
self.assertEqual(evaluate_material_piece_threat_value(supported_after, side), 230)
self.assertEqual(evaluate_material_piece_threat_value(unsupported_after, side), 216)
self.assertEqual(selected_move, supported_move)
```

- [x] 先後反転と候補順交換を検査し、どちらも支え手を選ぶ。`snapshot`で元局面・候補枝の非共有を確認する。新旧通常点と新合成点を独立固定値で比較した。
- [x] `test_zero_terms_tie_and_empty_candidates`：価値合計差・V（支えあり低価値駒脅威）の両係数0なら上記二候補は230で同点。一回の `rng.choice` に二候補が元順序のまま渡されることをspyで確認した。空候補はNone、評価と抽選の呼出しは0回。価値合計差だけを0にしてVを残すケースは229対230で同点でないことも確認した。
- [x] `test_mate_priority_with_new_evaluator`：既存 `mate_case(side)` の詰み・通常候補の合法性を実検査し、新評価に10**30を加えるラッパーを注入した。先後・候補順の全4条件で詰み手を選び、詰み枝では評価せず、通常枝を開始側視点で一度評価した。
- [x] `test_evaluator_exception_leaves_source_unchanged`：Task 2の依存操作を例外にして新評価を注入し、選択器から同じ例外が伝わり、元局面が不変であることを確認した。
- [x] 接続テストは既存選択器で初回Greenになることを実測し、未実装Redとは扱わなかった。合成・集計でのRedとは区別した。実行：`python3 -m unittest discover -s tests -p 'test_undefended_piece_value_selection.py' -v`。
- [x] 当初計画の6誤りを隔離コピーでそれぞれ意図したassertion failureとして検出した。レビュー後、複数対象の加算上書きと係数0時のV依存呼出し省略の2変異も追加検出した。worktree/cloneを作らず一時コピーを用い、protected data・archive・task areasはコピーしていない。読み込みエラーを検出に含めていない。
- [x] Ruff設定と対象を調べ、未追跡仮想環境バックアップにPythonファイルがあることを確認。保護対象を巻き込まないよう今回の新規6 Pythonファイルを明示して `.venv/bin/ruff check --select I --fix`、`.venv/bin/ruff format`、`.venv/bin/ruff check` を順に実行し成功した。変更後の全体検査 `python3 scripts/run_tests_parallel.py` は1054件・87モジュール・24.620秒で成功し、`git diff --check` も成功。
- [x] Refactor不要と判断した。独立レビュー初回はCritical 0 / Important 1 / Minor 1で、複数対象の合計テストとV係数0の例外検査を追加。再レビューはCritical 0 / Important 0 / Minor 0。契約・代表ケース・検出対象・既存補完・未検証は学習記録に記録した。
- [x] 知識メモへ契約・重み・独立期待値・比較CLI未接続と棋力未検証を記載。学習・設計・計画・索引・現在地を更新し、リンクと差分を確認した。今回のファイルだけを明示ステージし、通常hookを通す。`git add .`、`--no-verify`は使わない。
- [ ] テーマの実装・検証・レビュー・記録がそろったら作業branchにコミットする。main統合・pushはせず、別途承認を待つ。現在ディレクトリが元の作業先であること、mainへの未取り込みを報告する。承認後のmain統合と取り込み先検証、最後の理解確認一問は後続で行う。

## GREEN条件と未検証範囲

Task 1は価値合計・差の契約、Task 2は独立値による新合成と従来方式の保持、Task 3は合法候補への注入・詰み優先・全体回帰検証・独立レビュー・記録がそろった状態をGREENとする。件数や成功だけで必要十分とせず、検出した誤りに対して説明する。

既存の駒種別移動・利き・価値表・一手選択器の一般契約テストは再利用する。今回固有の対象価値・条件・合成・注入の確認を追加する。固定例は全配置の証明、合法な交換損得、係数の最適性、一般棋力・一般実時間の保証ではない。通常CLI公開はないため本段階でCVC操作を追加しない。

## 計画作成時のセルフレビュー

- [x] 設計の各契約とTask 1〜3の対応、5件のレビューフォーカスの担当テストを点検する。
- [x] 公開名・型・引数・独立期待値・コマンド・文書参照先を現物と照合する。
- [x] 読み込みエラーをRed扱いしないこと、既存経路での初回Greenを区別することを確認する。
- [x] 全入力へ保証を広げる記述、比較CLI接続／実行の先取りがないか確認する。

3タスクは順序依存が強く範囲が小さいため、アシスタント自身が順に実装し最後に独立レビューするネイティブ方式を推薦した。本人は計画を確認し、ネイティブ方式で実装を進めることに「YES」と回答した。チェックボックスは実施証拠を見て更新する。


2026-11-02のセルフレビュー：設計各節をTask 1〜3へ対応付け、代表局面D/Eと接続例を座標・価値表から再計算した。既存の公開シグネチャ、support、ランナー、Ruff設定と照合済み。新規モジュール用コマンドは作成後に実行する標準unittest discover形式であり、現段階では未実行。文書以外の変更を行っていない。計画内のPython断片は設計情報であり、テストファイルとして作成・実行していない。
