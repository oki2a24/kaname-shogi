# 支えのない被攻撃駒の価値の比較CLI接続・比較 実施計画案

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: この計画の実装には executing-plans を使用する。各タスクでTDDを行い、本人承認前は着手しない。

**目標:** 比較CLIに旧U方式と価値合計方式を同じ一手選択経路で接続し、新規に設計した局面群と独立seed一覧で比較する。

**アーキテクチャ:** 既存の比較専用policy識別・評価委譲・conditions保存・result reader・summary計時へ新policyを加える。旧V1 policyを対照として保持し、新policyは既存の価値合計評価器を重み10/1/1で呼ぶ。新しい合法局面セットを使い、既存のseed-list・先後交換・分析CLI契約を再利用する。

**技術スタック:** Python 3.15.2、標準ライブラリ、unittest、既存比較準備・対局比較・分析CLI、Ruff 0.16.10。

**仕様 (Spec):** [設計案](2026-11-02-undefended-piece-value-comparison-design.md)（2026-11-02、本人の実施指示を受領）

## グローバル制約

- **本人の実施指示を受領済み。** 2026-11-02、提示した設計・計画に沿いworker 4で進めるよう依頼された。TDD、Python・テスト変更、局面データ作成、seed準備、対局比較をこの計画の順に進める。main統合とpushはそれぞれ別途承認を待つ。
- 比較対象は旧方式10M+U+Vと候補方式10M+支えのない被攻撃駒の価値合計差+V。Mは駒得、Uは旧方式の支えのない被攻撃駒枚数差、Vは支えあり低価値駒脅威の枚数差を指す。
- 確認比較の各組は同じ局面の先後を交換した二局。確認比較は独立confirmation seed一覧を使い、pilotと合算しない。
- 通常CLI・USI、ShogiHome、二手・四手探索、係数探索を変更しない。ShogiHomeでのU候補実践はPCへアクセス可能との本人連絡後に再提案する。
- /Users/oki2a24/kaname-shogi と現在のbranch内だけで作業し、別worktree・別cloneを使わない。
- 既存の未追跡比較データ、.agents/tasks/、C2保護4件、migration-preservation-2026-11-01/ と worktree-preservation-2026-11-01/ の退避物を変更しない。全比較出力は本計画専用の新規パスを使う。
- テスト名は英語、日本語docstringの先頭行に確認する動作、その後に検出対象を記す。独立期待値は製品評価やCLI出力から作らない。
- mainへの統合とpushはそれぞれ別途本人承認を待つ。
- A番号を付けない。

## レビューフォーカス

| 優先 | 誤り・条件 | 期待する検出 |
| --- | --- | --- |
| 1 | 新policyが旧U evaluatorや重み10/1/1以外へ誤接続 | evaluatorの関数・重みデータを直接確認し、独立したスコアと選択期待値を照合する。 |
| 2 | 条件JSONで旧Uと価値合計差の係数・キーを混同 | 旧policyのundefendedと新policyのundefended_valueを別々に固定し、改変した重みをreaderが拒否する。 |
| 3 | 新policyがVまたは一手詰み優先を落とす | V込みの固定点、V-only対照、先後両方の一手詰みを確認する。 |
| 4 | 新規局面の先後・手番・対象数・期待値が誤る | 合法USI列、開始SFEN、M/U/価値合計差/Vを手書き期待値へ照合し、先後反転で符号を確認する。 |
| 5 | 旧条件・旧成果物・summary順・resumeの互換を壊す | 既存U/V比較テストと過去artifact readerを実行し、未選択policyが旧summaryへ混入しないことを確認する。 |

## 計画対象ファイル

| ファイル | 変更内容 |
| --- | --- |
| `kaname_shogi/movegen.py` | 比較専用の新しい選択policy値と評価器への委譲。 |
| `kaname_shogi/game_search.py` | 一手選択一覧と日本語docstringを更新。制御付き通常CLI/USI一覧へは追加しない。 |
| `kaname_shogi/comparison.py` | 方式名と選択時だけのsummary計時順を追加。 |
| `kaname_shogi/comparison_io.py` | CLI識別子、実効重みの保存、条件検証を追加。 |
| `kaname_shogi/comparison_result_io.py` | 新policyの条件・局結果reader検証と選択時の計時順を追加。旧形式の検証は保つ。 |
| `data/comparison/undefended-piece-value-positions-v1.json` | 新規7局面の合法開始列を保存。既存局面ファイルは編集しない。 |
| `tests/test_piece_threat_value_comparison_policy.py` | 旧・新policyの評価接続、独立選択例、詰み優先を検査。 |
| `tests/test_piece_threat_value_comparison_io.py` | policy名・条件重み・条件readerを検査。 |
| `tests/test_piece_threat_value_comparison_results.py` | 保存結果・旧artifact互換・summary順を検査。 |
| `tests/test_undefended_piece_value_comparison_positions.py` | 新7局面の合法性・一意性・手計算値と、過去U/V/C2開始SFENとの非重複を検査。 |
| `tests/test_undefended_piece_value_comparison_pipeline.py` | 小規模seed-list比較と分析の接続を検査。 |
| `tests/undefended_piece_value_comparison_support.py` | テスト専用の局面生成・独立期待値・回転反転補助。 |
| README、docsの比較知識・価値合計知識・学習記録・索引・現在地・ロードマップ | 実際の変更と検証だけを記録し、一般化の限界を明記する。 |

## タスク 1：比較専用の新policyを接続する

**消費:** `PieceThreatValueWeights(material=10, undefended_value=1, supported_threat=1)`、`evaluate_material_piece_threat_value(position, perspective, *, weights=...)`、既存 `choose_one_ply_move`。

**生産:** CLI識別子 `material-piece-threat-value-v1` に対応する `MoveSelectionPolicy.MATERIAL_PIECE_THREAT_VALUE_V1`。通常CLI・USIの方式選択には追加しない。

- [x] **テストを先に作る:** `test_value_policy_uses_exact_evaluator_and_weights` で旧V1が `PieceThreatWeights(10, 1, 1)`、新policyが `PieceThreatValueWeights(10, 1, 1)` を対応する別関数へ渡すことを検査する。
- [x] **接続の失敗を確認する:** 新policy不在を示すassertion failureを確認した。import errorではない。
- [x] **選択差のテストを作る:** 前テーマで手計算した合法二候補例を両側・両候補順で使った。旧方式は230/230、新方式は支える手230・支えない手216で、新方式だけが支える手を選ぶ。snapshotで入力不変も確認した。
- [x] **一手詰み優先のテストを作る:** 既存 `mate_case` の先手・後手、候補順両方で、通常評価を非詰み手へ極端に有利にしても新policyが詰み手を選ぶことを確認した。
- [x] **最小実装を行う:** `movegen.py` にenum値と値評価器の委譲を追加した。`game_search.py` の通常一手選択一覧と説明へ追加し、制御付き探索一覧には加えていない。`comparison.py` で新識別子と選択時だけのsummary計時を登録した。
- [x] **対象テストを実行する:** `PYTHONPATH=tests .venv/bin/python -m unittest test_piece_threat_value_comparison_policy tests.test_piece_threat_comparison_policy tests.test_material_piece_threat_value -v` は12件成功。
- [x] **Refactor要否を記録する:** 旧・新評価は別の型と関数を持つため、それぞれの名前付き重みを `partial` へ直接渡した。評価器を共通化するとUの枚数差と価値合計差の型の違いを隠すため共通化しない。

実行時の裁定: 新enumは既存summaryの既定方式走査にも入るため、policy接続だけでは旧比較summaryへ新計時欄が混入した。未選択時の除外、選択時の新方式登録、安定識別子をTask 1で追加し、既存summary順を維持した。残るCLI条件・成果物reader接続はTask 2で行う。

## タスク 2：比較条件・成果物readerへ接続する

**ファイル:** `comparison.py`、`comparison_io.py`、`comparison_result_io.py` と新規のpolicy / IO / resultsテスト。

**契約:** 旧・新の方式名と係数をconditions JSON、局JSON、summary、analysisへ保持する。新policyの実効重みは `material=10, undefended_value=1, supported_threat=1, mate_priority=true`。旧V1は従来どおり `material=10, undefended=1, supported_threat=1, mate_priority=true`。

- [x] **失敗テストを作る:** 新policy名のconfig受理、旧・新の実効重み、tamperした重みの拒否、選択中policyのsummary計時を固定値で検査した。新key欠落・`undefended` への取り違えを検査した。
- [x] **Redを確認する:** 未登録方式と未登録重みの独立assertion failuresを確認した。reader例外だけをRed完了とはしていない。
- [x] **最小実装を行う:** CLI登録、実効重み保存、result readerの許可値と重み検証、選択中policyだけのsummary計時へ新policyを追加した。
- [x] **既存互換を確認する:** 旧U/V条件、保存結果、旧summary順、resume readerテストを同時に実行した。未選択の新policyは古いsummaryへ追加されない。
- [x] **対象テストを実行する:** `PYTHONPATH=tests .venv/bin/python -m unittest test_piece_threat_value_comparison_io test_piece_threat_value_comparison_results tests.test_comparison_io tests.test_comparison_result_io tests.test_comparison_resume tests.test_piece_threat_comparison_io tests.test_piece_threat_comparison_results -v` は73件成功。

## タスク 3：独立した7局面と短いpipelineを作る

**ファイル:** 新規の局面JSON、support、position / pipelineテスト。

- [x] **7局面のmove列を新規作成する:** 無対象、低価値、高価値、同数異価値、枚数と価値の順位逆転、両側複数対象、U/V混在の7役割を満たす。V-onlyは既存の固定評価テストで確認し、比較開始局面へ追加しない。既存U・V・C2・合成A〜Eの比較用局面列をコピーしない。全局面を初期局面からの合法USI列にした。
- [x] **独立期待値表を作る:** 各局面のM・U・価値合計差・V・旧点・新点を現在の参考価値から手計算し、両視点で点の符号が反転することを確認した。
- [x] **positionテストを先に作る:** `test_positions_match_hand_calculated_components` で合法再生済みSFENの一意性、手計算値、U対象、V対象、支え、攻撃元を照合する。別テストで旧U・V pilot/confirmation・C2開始局面とのSFEN非重複も検査する。
- [x] **Redと最小修正を確認する:** 局面JSON未作成を示すassertion failureを確認してから7局面を追加し、全期待値テストを成功させた。
- [x] **小規模pipelineテストを作る:** `test_seed_compare_and_analyze_preserve_old_and_value_policies` で7局面各1組のseed一覧を作り、baseline `material-piece-threat-v1` / candidate `material-piece-threat-value-v1`、`max-plies=1`、`workers=4` の比較・分析を実行した。条件重み、先後交換14局、方式別計時、analysis件数を固定値で検査した。強さ判定はしない。
- [x] **Red・Greenを確認する:** Task 1・2で方式名・重み未登録をassertion failureから接続した。今回の統合テストは同じseed一覧を2回実行し、両回の14局の予定と棋譜結果が一致することを確認した。

## タスク 4：検出力・回帰・文書を仕上げる

- [x] **誤り注入を行う:** 保護対象をコピーしないリポジトリ外の一時コピーで、候補の評価器を旧Uへ差し替える、価値重みを0/2へ変える、Vを落とす、価値差符号を反転する、条件keyを混同する6変異を注入した。全て対応テストが意図したassertion failureで検出し、実作業ツリーに変異は残さなかった。
- [x] **単独と全体の検出範囲を整理する:** policy/比較IO/result reader/7局面pipelineの今回テスト、既存 `test_material_piece_threat_value.py`、旧U/V policy・artifact・resumeテストが補完する範囲と、一般棋力・実戦局面代表性で未検証の事項を学習記録へ区別して記した。
- [x] **品質検査を行う:** Python変更へimport整理・format・Ruff lint、`git diff --check`、`python3 scripts/run_tests_parallel.py` を実行した。修正後は1066テスト・92モジュール・26.996秒で成功。
- [x] **Refactor要否を確認する:** policy列挙、候補選択、conditions重み、result reader、summary計時は別々の保存・実行境界であり、今回一方式だけのために共通抽象を作らない。重複登録の不一致はpolicy・reader・pipelineの固定期待値テストで検出する。
- [x] **独立コードレビューを行う:** Task 1〜3の初回レビューはCritical 0 / Important 0 / Minor 0。無対象対照の重複修正後の再レビューはCritical 0 / Important 0 / Minor 1で、旧V/U例と現テーマの組数を明記して解消した。Task 5後の最終branchレビューはCritical 0 / Important 0 / Minor 1。READMEの「今回の6局面」という曖昧さを修正し、confirmation間で共通する分析契約の説明へ改めた。各レビューは読み取り専用。初回レビューの後で見つけた無対象対照の重複は、テスト追加と局面差替えで解消した。
- [x] **文書を更新する:** README、比較/価値の知識メモ、学習記録、docs README、resume、next topics、ロードマップを実施結果に合わせた。pilot/confirmationの分析・終局内訳・適用範囲・最終レビューも追記し、ローカルリンクと差分を確認した。

## タスク 5：pilotと独立confirmationを実行・分析する

**新規保存先案:**

- 局面: `data/comparison/undefended-piece-value-positions-v1.json`
- pilot seeds / 結果 / 分析: `data/comparison/runs/undefended-piece-value-comparison-pilot-2026-11-02-seeds.json`、`data/comparison/runs/undefended-piece-value-comparison-pilot-2026-11-02/`、`data/comparison/runs/undefended-piece-value-comparison-pilot-2026-11-02-analysis.json`
- confirmation seeds / 結果 / 分析: `data/comparison/runs/undefended-piece-value-comparison-confirmation-2026-11-02-seeds.json`、`data/comparison/runs/undefended-piece-value-comparison-confirmation-2026-11-02/`、`data/comparison/runs/undefended-piece-value-comparison-confirmation-2026-11-02-analysis.json`

- [x] seed生成・比較実行の前に、全ての出力パス6件が未使用であること、保護対象と衝突しないこと、実験条件の局面順・各局面組数・policy・上限・workerが承認済み計画と一致することを確認した。
- [x] pilot用に各7局面2組、purpose `pilot` の新しいseed一覧を作った。旧・新policyを比較CLIで14組・28局、各局512手上限、worker 4で実行・分析した。実測426.373417秒、詰み26局、手数上限2局、その他の終局・故障・中断0。分析CLIは候補得点区間 `[0.244, 1.000]` を予備比較として出し、強さの判定をしなかった。pilotは接続・時間・未決着の確認にのみ使った。
- [x] pilotと異なるpurpose `confirmation` のseed一覧を新規生成し、各局面291組、合計2037組・4074局で同条件の独立確認比較を行った。局面・反復番号・baseline/candidate両seedを使ってpilotとの共有seedが0件であることを照合した。各局512手上限、worker 4。再開後を含む経過時間69,063.743秒は下限値。
- [x] summary・conditions・4074局の全保存hashを分析CLI出力と照合した。終局は詰み3976、合法手なし1、連続王手負け1、通常千日手9、手数上限87。未開始・部分組・進行中・故障・中断・双方連続王手未裁定は0。7局面各291組である。
- [x] pilotとconfirmationは合算せず分析した。候補の組得点平均区間は `[0.6823, 0.7036]`、95% paired Hoeffding区間は `[0.6522, 0.7337]`、CLI判定は `improved`。適用範囲を固定7局面・一手選択・512手上限・実行環境に限定し、一般棋力やShogiHome実践結果と混同しない記録を学習記録へ残した。
- [x] 初回終局集計、同じseed一覧の全局hash再照合、保存分析とsummaryの照合を完了した。最終独立レビューはCritical 0 / Important 0 / Minor 1。READMEの比較方法説明に「今回の6局面」とある曖昧さを指摘され、各実験で事前固定した局面群を等重みに扱う表現へ修正した。独立レビューは保護対象の既存比較データとC2保護物・アーカイブを読まず、task専用成果物・コード・テスト・文書を対象にした。

## 完了・承認境界

GREENは比較policy接続、手計算局面、短いpipeline、既存artifact互換、全体テスト、Ruff、独立レビュー、文書更新、pilotと独立confirmation・分析がこの計画の範囲で完了した状態とする。数値が候補有利であることはGREENの条件ではない。

作業branch上の確認済み変更を記録・コミットした後も、mainへの統合とpushは各々別途本人承認を得る。ShogiHome実践、通常CLI/USI接続、他の探索方式への適用を本計画の完了条件へ含めない。

## 計画セルフレビュー

- 設計の各要件をタスク1〜5へ対応付けた。policyの直接評価、conditionsとreader、独立局面、pipeline、統計・記録のいずれも担当箇所を明示した。
- 期待値は固定設計A〜Eと先行する一手選択例を製品出力から再生成せず、局面セットは新規に作ると定めた。
- Red確認ではimport errorのみを数えず、条件違い・値違いの意図したassertionを確認する。
- 旧policy・旧artifact・summary順・未選択policy・詰み優先をレビュー対象に含めた。
- 55%の仮目標、95%区間、80%検出力の式から、7局面各291組を計画した。結果は登録局面群だけへ限定する。
- 計画と結果を将来文書へ記録するが、未実施のRuff・テスト・比較実行は本案作成時点の実績としていない。
