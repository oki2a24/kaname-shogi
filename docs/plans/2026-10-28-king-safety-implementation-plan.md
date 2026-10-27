# 玉周辺の安全度と駒得の合成評価 実装計画

> **AIエージェントへの指示:** 本人は計画全体と、作成者自身が実装して各段階で独立レビューを受けるネイティブ方式を承認済み。B2開始時にsuperpowerssuperpowers:executing-plansを使用する。各タスクの追跡はチェックボックスで行い、AGENTS.mdが定める各タスクのRefactor要否確認後と最終の独立レビューを省略しない。

**目標:** 玉周辺の攻撃マスを重複せず数える安全度差を作り、既存駒得と10対1で合成し、既存の一手選択へ注入できる部品として検証する。

**アーキテクチャ:** movegenに対象占有を補正した公開利き照会を追加し、既存の駒種別候補へ委譲する。新しいking_safetyは近傍集計・視点の差、新しいmaterial_king_safetyは不変の重み・駒得との合成を担当する。一手選択本体は既存choose_one_ply_moveを使う。

**技術スタック:** 現行Python 3.14以上、標準unittest、固定Ruff 0.16.10。新規依存なし。計画作成時の指定作業ツリーはPython 3.15.2、Ruff 0.16.10、ローカルcore.hooksPath=.githooksを確認した。

**仕様:** [本人承認済み設計](2026-10-28-king-safety-design.md)、[学習・回答・承認記録](../learning/king-safety-design.md)。2026-10-28、本人は設計全体へ「承認する」と回答した。同日、本人は実装計画全体と推薦したネイティブ方式にも「承認する」と回答した。A2の最後の理解確認と回答記録まで完了した。全タスク未着手で、B2への移行・新セッション再開指示を待つ。

## グローバル制約

- 攻撃側の自玉を王手にさらすか、実際の着手として合法かは調べない。
- 手番には依存しない。持ち駒から将来打つ手や、その後の利きは数えない。
- 評価は盤面・手番・双方の持ち駒を変更しない。
- 安全度差S(P)=D(Q)-D(P)。
- 通常評価E(P)=material×M(P)+safety×S(P)。
- 既定値はmaterial=10、safety=1。正が指定側に有利で、同一局面の逆視点は符号を反転する。
- 重み10対1は本人了承済みの仮設定。盤端補正・割合換算をせず、玉自身と盤外を近傍へ入れない。
- 欠落だけでなく同一側の複数玉もValueErrorにする。safety=0でも両玉の前提を検査する。
- 公開利き操作は玉の存在を要求しない。新評価の玉検査を既存SFEN・王手・駒得へ追加しない。
- B2で追加する範囲は利き操作・評価部品と、その既存選択器への注入の検証まで。
- CLI/USI・比較CLIへの公開、方針列挙値・保存形式の追加、二手・四手適用、通常CLIのSFEN入出力、飛車可動性バージョン2を含めない。
- 型名は日本語の意味とデータか操作かを説明する。公開docstringは引数・戻り値・副作用・前提・設計理由を記す。テスト名は英語、日本語docstringに振る舞いと検出対象を記す。
- 各新規振る舞いはassert失敗の理由を確認して最小実装・成功確認・Refactor要否確認・独立レビューを行う。ImportErrorやAttributeErrorだけを振る舞いのRedとしない。
- Critical/Importantは修正・再検証・独立再レビューで解消してから各タスクをコミットする。フック回避やunsafe修正の一括適用をしない。
- 長時間の比較・分析CLIは本人が端末で実行し、アシスタントは起動・監視しない。

## レビューフォーカス

基本例では見逃す次の条件を、以下の所有タスクの検査へ組み込む。

1. 攻撃側の味方駒がtargetを占める場合も利くが、そこにいた駒自身からの自己攻撃はない（Task 1）。
2. targetの占有だけを補正し、別の遮蔽・現在の玉による遮蔽を除かない。通常・例外終了後も元盤は不変（Task 1・2）。
3. 両側が非零かつ不等で、手番・視点・先後反転により符号を取り違えない（Task 2・3）。
4. 玉欠落・複数玉を、safety=0でも拒否し、一度の重み変更が既定値へ漏れない（Task 2・3）。
5. 成り・捕獲・駒打ちという異種の兄弟候補を同じ元局面から評価しても、盤面・双方持ち駒が枝間で共有されない（Task 4）。

## 作業場所・開始前確認・共通サイクル

作業先は /Users/oki2a24/.codex/worktrees/c1-analysis-speedup/kaname-shogi。
現在の記録用ブランチcodex/a2-king-safety-designを使い、mainでは実装しない。
計画作成の起点はfc32080bで、作成時は計画記録のコミットが未確定だった。この値を実装開始HEADと決めつけず再確認する。
git-dirは元リポジトリの.git/worktrees/kaname-shogi4、common-dirは.gitで、サブモジュールではないリンク作業ツリーと確認した。
元の /Users/oki2a24/kaname-shogi は本人の文書・比較データを保持し、clean/reset/切替・ステージ等を行わない。
新しい作業ツリーの作成・main統合・pushは本計画の承認へ含めない。

- [x] 本人の本計画全体への承認と実行方式を記録する。2026-10-28、本人「承認する」。
- [x] A2の最後の理解確認と回答・補足を記録する。2026-10-28、本人は今回の指標と合法な逃げ先の違いを回答した。
- [ ] B2への移行を本人が選ぶまで、計画承認だけで次テーマを開始しない。原則は新セッション用の引き継ぎを作り、本人が入力した再開指示を待つ。同セッション継続を本人が明示した場合はその希望に従う。
- [ ] 指定作業先でgit status --short --branch、git log -3 --oneline --decorate、git branch --show-currentを実行し、無関係な変更があれば保持する。
- [ ] .venv/bin/python3 --version、.venv/bin/ruff --versionとrequirements-dev.txt、git config --local --get core.hooksPathを照合する。不足時はREADMEの手順に従い、グローバル設定を変えない。
- [ ] 計画承認後・製品変更前に、PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.pyでベースラインを確認する。失敗があれば新規変更と区別し、先に切り分ける。計画作成中の今回は未実行。
- [ ] 各タスクで、下記のケースを振る舞い単位に追加してRed→最小実装→Greenと進める。一括実装後にRedを捏造しない。スタブで既に満たす境界は初回Greenとして区別する。
- [ ] 各タスクのRefactor要否を確認し、独立レビューの重大度・対応・検証範囲を学習記録へ残す。
- [ ] Pythonのimport追加・変更後は .venv/bin/ruff check --select I --fix .、.venv/bin/ruff format .、.venv/bin/ruff check .、git diff --check、変更に見合うテストの順に進める。
- [ ] 当該タスクのファイルと記録のみ明示的にステージし、git diff --cached --checkと内容確認後、通常のgit commitを行う。記録に実施済みの手順だけを書く。

unittestの専用実行は下記のdiscoverコマンドを使う。終了コード0かつOKが成功条件で、指定ファイルが実際に発見され、0件でないことも確認する。
専用・関連・全体の範囲を区別し、全体をskip・filterして短縮しない。
逐次のpython3 -m unittest discover -s tests -vは共有状態・順序依存・並列差等の調査時に併用し、理由のない全体再実行を繰り返さない。

## ファイルと依存方向

| ファイル | 作成・変更と責務 |
| --- | --- |
| kaname_shogi/movegen.py | 公開is_square_attackedのみ追加。既存の駒種別候補への振り分けを再利用し、is_in_check・候補・合法手・詰み・方式の契約は変更しない |
| kaname_shogi/king_safety.py | 新規。両玉の枚数検査、DとSを返す読み取り部品 |
| kaname_shogi/material_king_safety.py | 新規。不変設定と既存M・新Sによる合成 |
| tests/test_square_attacks.py | 新規。占有補正を含む全14駒種の利き・遮蔽・不変性 |
| tests/test_king_safety.py | 新規。近傍範囲・重複排除・視点・玉前提 |
| tests/test_material_king_safety.py | 新規。固定点数・係数・成り/取り/打ち後 |
| tests/test_king_safety_selection.py | 新規。既存一手選択への新評価注入・異種の兄弟枝 |
| docs/learning/king-safety-design.md・本計画 | 実施・Red/Green・Refactor・レビュー・未検証の記録 |
| docs/knowledge/king-safety-evaluation.md | 実装した契約と限界の参照メモ。Task 4で作成 |
| docs/README.md・docs/resume.md等の現在入口 | 記録と現在地への参照。READMEの利用案内や将来テーマを実装済みにしない |

依存はmaterial_king_safety→evaluationとking_safety、king_safety→modelとmovegen。
movegenから新評価をimportしない。新規__init__公開や既存方式の全面分割を行わない。

## Task 1：占有マスを含む公開利き照会

**ファイル:** 変更kaname_shogi/movegen.py、作成tests/test_square_attacks.py。
**消費:** Board.copy/piece_at/set_piece、Square、Side、同一movegen内の_move_candidates_for_piece。
**生産:** is_square_attacked(board: Board, target: Square, attacking_side: Side) -> bool。
対象マスへ指定側の盤上駒から一つでも利きがあればTrue。玉なし盤でも使え、手番・持ち駒・合法性を調べない。
有効なBoard・Square・Sideを引数の前提とし、無関係な入力型の汎用検証を追加しない。

- [ ] **1. 独立フィクスチャと失敗するテストを作る。** 最小宣言を置く場合はFalseスタブ等にとどめ、正の到達ケースのassertTrue失敗をRedとして確認する。

| テスト名 | 固定入力・アサーション |
| --- | --- |
| test_matches_all_piece_geometries_for_both_sides | 空盤の５五に攻撃元を一枚。下記の手書き到達集合について全盤内81マスのTrue/Falseを確認。全14駒種・先後両方。製品の候補生成から期待集合を作らない |
| test_counts_friendly_occupied_target | ５五の各14駒種が到達する一マスに攻撃側の歩を配置してTrue。馬は直交隣、竜は斜め隣も使う。移動候補の味方除外を検出 |
| test_counts_opponent_occupied_target | 同じ到達先を反対側の歩が占有してもTrue |
| test_excludes_self_attack_and_empty_attackers | 攻撃元一枚の出発マス自身はFalse。攻撃側の駒がない空盤もFalse |
| test_stops_at_first_blocker_in_every_sliding_direction | source５五、飛/角/香/馬/竜の各走行方向で2マス先へ桂を置く。1マス先と桂のマスはTrue、3マス先はFalse。桂の所属は両方。桂は隣への利きがなく、遮蔽駒自身の利きが期待値を汚さない |
| test_knight_jumps_over_unrelated_blockers | 先手桂５五→４三/６三、後手桂５五→４七/６七は、中間の５四/５六に駒があってもTrue |
| test_preserves_board_on_success_and_failure | 味方占有targetを照会する前後で81マスのPiece/Noneの列が同じ。候補への委譲を例外にする検査でも例外を伝え、元盤が同じ |

手書き到達集合は５五からの筋差df・段差drで次の通り。k=1,2,3,4。先手の前はdrが負。
後手は表のdrを反転した集合を使う。KING/ROOK等の定義では日本語の駒名を併記する。

| 駒種 | 先手の到達差分 |
| --- | --- |
| 玉・王 | df,drが-1～1、(0,0)を除く8個 |
| 飛車 | (±k,0),(0,±k) |
| 角行 | (±k,±k)の四方向 |
| 金将・と金・成香・成桂・成銀 | (-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(0,1) |
| 銀将 | (-1,-1),(0,-1),(1,-1),(-1,1),(1,1) |
| 桂馬 | (-1,-2),(1,-2) |
| 香車 | (0,-k) |
| 歩兵 | (0,-1) |
| 馬 | 角の集合＋(±1,0),(0,±1) |
| 竜 | 飛車の集合＋(±1,±1) |

- [ ] **2. Red確認。** 実行: PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p test_square_attacks.py -v。意図した到達値のassert失敗を記録する。
- [ ] **3. 最小実装。** targetをattacking_sideの駒が占有するときだけBoard.copyで複製し、そのtargetだけを空にする。照会盤の指定側の各駒の既存候補にtargetがあるか調べる。targetにいた駒自身を攻撃元に含めず、別の遮蔽は残す。
- [ ] **4. Green・Refactor・独立レビュー。** 専用実行成功後、同じdiscoverで-p test_movegen.pyを関連検査として実行。候補生成の全14駒種の方向等は既存検査が補完するが、味方占有target・自己攻撃除外・複製補正は今回固有と確認。
- [ ] **5. 共通品質検査と記録後、当該ファイルをコミット。** 例: feat: 占有マスを含む利き照会を追加。

**GREEN条件:** 全14駒種の固定到達集合、占有・遮蔽、不変性、既存movegenの関連検査が成功し、独立レビューのCritical/Importantが0。

## Task 2：危険マス数と指定側の安全度差

**ファイル:** 作成kaname_shogi/king_safety.py、tests/test_king_safety.py。
**消費:** Task 1のis_square_attacked(board, target, attacking_side)、modelの盤面・所属・駒種。
**生産:** king_danger_count(position: Position, side: Side) -> int、king_safety_balance(position: Position, perspective: Side) -> int。
どちらも両側に正確に一枚ずつの玉が必要で、欠落・複数玉はValueError。メッセージは「先手・後手の玉はそれぞれ1枚必要です」。
公開二操作から同じ玉検査と近傍集計を再利用し、SをD(Q)-D(P)として計算する。

- [ ] **1. テストを振る舞い単位に追加する。** 固定配置は設計の表の通り、記載以外空・持ち駒なし。D/Sの期待値を製品照会で生成しない。

| テスト名 | 固定値・検出対象 |
| --- | --- |
| test_counts_static_cases_from_design | 先手玉５五・後手王９一。後手歩５三のAはD先手1/D後手0/S先手-1/S後手+1、後手歩５二のBは両D0・S0 |
| test_counts_distinct_attacked_squares | 先手玉５五・後手王９一、後手歩５三/４三と後手桂６二。５四・４四だけが対象なのでD先手2。延べ3にしない |
| test_subtracts_two_nonzero_unequal_dangers | 先手玉５五・先手歩８三、後手王９一・後手歩５三/４三。D先手2、D後手1、S先手-1、S後手+1 |
| test_rotates_owners_and_ignores_turn | 上例を(筋,段)→(10-筋,10-段)として先後交換するとS先手+1・S後手-1。手番だけを変えた元局面のSは不変 |
| test_uses_only_on_board_adjacent_squares | 玉を５五/１五/１一、反対玉９九。利き照会を常にTrueのダブルにし、呼んだtarget集合を手書きの8/5/3マスへ照合。D=8/5/3、玉自身・盤外・距離2を除く。実利きのA/Bがダブル依存を補う |
| test_excludes_king_square_itself | 先手玉５五・後手王９一・後手桂４三。桂の利きは３五/５五で、玉自身を除けば近傍への利きはなくD先手0 |
| test_includes_pinned_piece_attacks | 先手飛５九・先手玉４五、後手王５一・後手銀５三。銀の４四・５四が対象でD先手2、D後手0、S先手-2 |
| test_keeps_current_king_as_a_blocker | 先手玉５五・後手王９一・後手飛５一。先手玉は王手だが静的評価入力として使用可。周辺で利くのは５四だけでD先手1。玉を除いて背後の５六まで数える誤りを検出 |
| test_ignores_potential_hand_attacks | Aに任意の持ち飛・持ち桂を追加してもD/Sは不変。駒得Mの変化はTask 3で別に確認 |
| test_requires_exactly_one_king_per_side | 玉を両方除く、片側を除く、各側を一枚ずつ増やすケースを両公開操作でValueErrorへ照合。玉なしを0にしない |
| test_preserves_full_position | 盤面81マス、手番、先後の持ち駒の各枚数を保存し、D/Sを反復しても同一 |

- [ ] **2. Red確認。** PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p test_king_safety.py -v。0スタブ等ではA・非零差・前提違反のassert失敗を確認。B=0等の初回Greenは区別する。
- [ ] **3. 最小実装。** 両玉を一回の走査で検査できる内部処理を共有し、盤内の隣接マスだけへ公開利き照会を行う。合法手生成・試し指し・盤端補正を呼ばない。
- [ ] **4. Green・Refactor・独立レビュー。** 専用とtest_square_attacks.pyを実行し、依存の再利用、両側非零不等での符号検出、局面不変を確認。
- [ ] **5. 共通品質検査と学習記録更新後、当該ファイルをコミット。** 例: feat: 玉周辺の危険マス数と安全度差を追加。

**GREEN条件:** D/Sの固定値、視点・先後反転・手番非依存、玉前提と読み取り契約が成功し、独立レビューのCritical/Importantが0。

## Task 3：不変の重みと駒得との合成

**ファイル:** 作成kaname_shogi/material_king_safety.py、tests/test_material_king_safety.py。
**消費:** king_safety_balance(position, perspective)、evaluation.material_balance(position, perspective)。
**生産:** 凍結dataclassのKingSafetyWeights(material: int = 10, safety: int = 1)という設定データ、および
evaluate_material_king_safety(position: Position, perspective: Side, *, weights: KingSafetyWeights = _DEFAULT_KING_SAFETY_WEIGHTS) -> intという読み取り操作。
_DEFAULT_KING_SAFETY_WEIGHTSはモジュール定数に一度だけ生成した設定。既定引数内で生成せずRuff B008を避ける。
materialは正整数、safetyは0以上の整数で、bool・float・範囲違反はValueError。エラー文言は項目と許容範囲を日本語で示す。

- [ ] **1. 設定・合成のテストを振る舞い単位に追加する。**

| テスト名 | 独立期待値・assert |
| --- | --- |
| test_combines_material_and_safety | 設計A/Bは先手-11/-10、後手+11/+10。集中例はM=-8・S=-2から-82。元局面は不変 |
| test_accepts_named_weights_without_changing_defaults | A、material=2・safety=3で-5、material=2・safety=0で-2、その後の既定評価は-11 |
| test_validates_immutable_weights | 既定(10,1)。material=0/-1/True/1.5、safety=-1/True/1.5はValueError。生成後フィールド代入はFrozenInstanceError |
| test_validates_kings_even_with_zero_safety_weight | 欠落・複数玉の各ケースはsafety=0でもValueError。両玉を省いたMだけの評価へ暗黙切替しない |
| test_values_promotion_capture_and_drop | 下記の共通局面から、成り108、竜取り320、歩打ち-2、元局面-2。成駒と持ち駒の境界・手番更新後の視点固定を確認 |
| test_hand_changes_material_but_not_safety | 設計Aへ先手持ち歩1枚を追加するとMは-1→0、S=-1のままでE=-11→-1。先手持ち飛追加ならM=14、E=139 |

成り・捕獲・駒打ちの共通局面は先手玉９九・先手飛８八・先手歩５四・先手持ち歩1、
後手王１一・後手竜８七。M=0。竜の８八/９八への利きが先手玉周辺に入りD先手2、D後手0、S=-2、E=-2。
独立複製に既存position_after_moveを適用し、評価視点は開始側の先手に固定する。
５四歩→５三と金はM=11・S=-2・E=108、８八飛→８七飛で竜を取ると持ち飛1枚になりM=32・S=0・E=320、
７六への歩打ちは盤上・持ち駒の合計M=0、S=-2・E=-2。各枝の元局面は変更しない。
これらの合法性・非詰みは既存操作で実装時に照合し、誤りがあれば製品結果へ点数を合わせず配置から再点検する。

中心例のテストアサーション（aは設計Aの固定配置から構築）:

```python
self.assertEqual(evaluate_material_king_safety(a, Side.SENTE), -11)
self.assertEqual(evaluate_material_king_safety(a, Side.GOTE), 11)
self.assertEqual(
    evaluate_material_king_safety(
        a, Side.SENTE, weights=KingSafetyWeights(material=2, safety=3)
    ),
    -5,
)
```

- [ ] **2. Red確認。** PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p test_material_king_safety.py -v。最小宣言後の点数・範囲・不変性のassert失敗を確認する。
- [ ] **3. 最小実装。** 既存MとTask 2のSを呼び、名前付き重みで合成する。safety=0でもSを呼び前提を検査する。詰み・探索・乱数や飛車可動性を持ち込まない。
- [ ] **4. Green・Refactor・独立レビュー。** 専用に加えtest_king_safety.py・test_evaluation.py・test_material_rook_mobility.pyを実行。既存M・可動性設定と新規設定の独立を確認。
- [ ] **5. 共通品質検査と学習記録更新後、当該ファイルをコミット。** 例: feat: 駒得と玉周辺安全度の合成評価を追加。

**GREEN条件:** 固定点数、設定の境界・不変性、0倍時の玉前提、成り/取り/打ち後が成功し、独立レビューのCritical/Importantが0。

## Task 4：既存一手選択への注入・全体検証・記録

**ファイル:** 作成tests/test_king_safety_selection.py、docs/knowledge/king-safety-evaluation.md。学習・計画・現在入口を更新。
**消費:** Task 3のevaluate_material_king_safety、既存choose_one_ply_move(position, moves, rng, *, evaluate)、position_after_move、合法手・詰み操作。
**生産:** 新評価を注入した一手選択の接続検証と、確定契約・検出範囲・未検証の記録。新しい選択器や公開方針は作らない。

- [ ] **1. 新評価の接続ケースを作る。** selector本体は既存であり、この段階で最初から成功するケースは既存部品との初回Greenと記録する。Redを作る目的で既存本体を壊さない。Task 1～3で新機能のRedを担当し、下記は注入の実局面検証と代表変異で検出力を確認する。

| テスト名 | ケースとアサーション |
| --- | --- |
| test_prefers_safer_king_move_for_both_sides | 設計Aから５五玉→４五玉(-11)と５五玉→５六玉(-10)。候補順を両順にして後者を選ぶ。180度回転・所属交換した後手開始でも対応する手を選ぶ |
| test_material_only_keeps_both_moves_tied | 同じ二候補へmaterial_balanceを注入すると双方-1。乱数器ダブルのchoiceへ渡る最高候補タプルが両方で、一回だけ呼ばれる。新評価なら安全側一候補のみ |
| test_mate_priority_survives_safety_evaluator | 先手玉９九・飛５三・金４三、後手王５一・後手歩４一/６一/４二/６二。５三飛→５二飛が詰み、５三飛→６三飛が通常。通常枝の新評価へ10**30を加えるラッパーでも詰み手を選び、詰み枝で評価が呼ばれない。先後鏡像と候補両順も確認 |
| test_preserves_mixed_move_branches | Task 3共通局面で成り・捕獲・打ちの三候補を注入評価で採点し、108/320/-2、捕獲手の選択を確認。評価器ラッパーに三枝を保持し、捕獲枝の盤と双方持ち駒を後から変更しても、他枝と元局面の81マス・両持ち駒・手番が不変。候補順を逆にしても一致 |

枝の変更は分岐局面の共有漏れを検出するための検査操作であり、通常評価が局面を変更してよいという契約ではない。
空候補・最高同点一回抽選・負数・非詰み手なし・評価例外・不正手の伝達は既存test_one_ply_selection.pyの対応テストで補完する。
全共通テストを新ファイルへ複写せず、新評価の実局面接続と異種枝を固有に確かめる。

- [ ] **2. 接続GreenとRefactor・独立レビュー。** PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest discover -s tests -p test_king_safety_selection.py -v と、-p test_one_ply_selection.pyを実行。新評価の注入だけで必要な選択が得られるか点検する。
- [ ] **3. 代表誤りを隔離コピーで確認。** 下表の一つずつを新鮮な一時コピーへ入れ、対応するテストの意図したassertion failureを確認する。コピーしたソースを本当にimportしているか__file__で確かめ、元の作業ツリーを変異させない。変異ごとに復元・成功を確認し、隔離コピーを片付ける。

| 代表誤り | 必ず失敗を確認する対象 |
| --- | --- |
| targetが攻撃側の味方である場合の占有補正を省く | test_counts_friendly_occupied_target |
| 照会用盤からtarget以外の遮蔽も取り除く | test_stops_at_first_blocker_in_every_sliding_direction |
| 占有補正を複製でなく元の盤へ行う | test_preserves_board_on_success_and_failure |
| 危険マスを重複して加算する | test_counts_distinct_attacked_squares |
| Sの引き算の向きを逆にする／相手Dを無視する（別々） | test_subtracts_two_nonzero_unequal_dangers |
| 既定material係数10を1へ変える | test_combines_material_and_safety |

実装の形によって注入箇所が変わる場合は、同じ現実的な誤り・同じ検出契約となることを記録する。
ImportError・構文エラーや別の原因だけの失敗は検出成功へ数えない。
既存検査だけが検出する誤りと、新規専用検査が単独で検出する誤りを区別する。

- [ ] **4. 品質・全体回帰・最終ブランチレビュー。** import整理→全体format→全体Ruff→git diff --checkの後、PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.pyを実行し、発見された全モジュールの件数・成功・実時間を記録。過去の898件成功を今回の実測としない。fc32080bからの製品差分・設計・計画・文書を独立レビューし、各Taskの指摘と最終Critical/Importantを解消する。修正後は影響に見合う再検証・再レビューを行う。
- [ ] **5. 確定知識・学習記録・現在地を更新してコミット。** D/S/E、利きと移動先の違い、両玉・設定前提、詰み優先、一手選択の注入例、対象外を知識メモへ記録。各検証のコマンド・結果・初回Green/Red・Refactor要否・代表誤り検出・レビュー対応・未検証を学習記録へ残す。文書リンクと差分を確認し、Task 4のファイルと記録だけを通常コミットする。

**GREEN条件:** 新評価の選択接続、代表誤りの意図した失敗と復元後成功、品質検査、全体回帰、独立最終レビューと記録がそろい、未解決Critical/Importantが0。

## 実装後の提示と主線への帰還

上記はB2の実装・検証・記録の計画であり、main統合の承認を含まない。
作業場所・ブランチ・コミット・検証と限界、元ディレクトリへ未統合である状態を本人へ示す。
mainへの取り込みは本人の別途承認後に、取り込み先の現在状態を確認して行い、取り込み先で検証する。
元の作業ディレクトリの未コミットデータを保護し、統合のためにそのcheckoutをclean/reset/切替しない。
統合後、最後の理解確認を一問だけ出して回答を待ち、回答と補足を記録してから次テーマ候補を示す。
主線の次の帰還目標はC2の接続・比較であり、道具の補助作業を自動追加しない。
C2の実験・統計条件や長時間CLIは別途設計・本人実行とする。

## 計画作成時の点検

この節は作成時の確認であり、Taskの実施結果ではない。
設計の各契約はTask 1の利き、Task 2の近傍・前提・符号、Task 3の合成・設定、
Task 4の選択接続・回帰・記録へ対応付けた。公開操作の名称・引数・返値をTask間で照合した。
レビューフォーカス5件を所有Taskのケースへ対応付けた。
全14駒種の期待集合、遮蔽駒自身の利きによる検査汚染、両側非零不等の符号、
成り/取り/打ちの固定値を手計算で点検した。設計の数倍の長さとなる実装本体の写経は避けた。
専用・関連コマンドは既存unittestのdiscover形式と実在する.venvに合わせた。計画作成時は未承認だったため、新規テスト実行はしていない。その後の計画承認時点でも、全タスクの開始・テスト実行はまだ行っていない。
製品コード・テスト・依存関係を作成・変更していない。計画自体の検証結果は学習記録へ別途保存する。

作成時は依存が順につながる4Taskなので、作成者自身の実装＋各Task後と最終の独立レビューを推薦し、タスク別の別実装者方式も提示した。
2026-10-28、本人は計画と推薦方式を承認した。B2開始は次テーマへの移行・再開指示に従い、独立レビューは各Taskと最終の両方で行う。
