# 全幅読みとαβ枝刈りの開発用比較 実装計画

> **AIエージェントへの指示:** REQUIRED SUB-SKILL: 承認後の実行では `subagent-driven-development` または `executing-plans` を使用する。実行方法は本人の選択待ち。各段階の独立レビューはプロジェクト方針を優先する。

**目標:** SFENで指定した局面を二・三・四手の全幅／αβ探索で比較し、正しい評価・最善候補・訪問回数を説明できる開発用コマンドを作る。

**アーキテクチャ:** 二方式の入口と一つの共通探索本体を設ける。操作データを介して将棋局面と数値木を接続し、評価の正本だけを既存処理から抽出する。既存三方式の選択・時間制御は維持する。

**技術スタック:** プロジェクトのPython 3.14以上、標準ライブラリ、unittest、Ruff固定版0.16.10。既存 `.venv` を使う。追加ライブラリなし。

**仕様:** [承認済み設計](2026-10-17-engine-search-comparison-design.md)。本人の設計承認は2026-10-17。これは実装計画案であり、2026-10-17に本人から実装開始の指示を受け承認済み。

**グローバル制約:**

- 評価視点は開始側に固定。開始側の手番では最大、相手手番では最小の値を採用する。
- 詰みの勝ち > 通常の駒得 > 詰みの負け。末端でも詰みを確認する。勝ち同士・負け同士は同点で、詰み距離は比較しない。
- 両方式の合法手を調べる順序をそろえる。同点の最善手は最初のものを選ぶ。
- 指定深さまで完了した結果だけを比較する。手動中断は未完了であり、比較成功と表示しない。
- Random（最弱・既定）、一手駒得、現行二手先読みの選択と振る舞いを維持する。
- 通常対局のCLI/USIへの新方式追加、反復深化、時間制御の組み込み、置換表、駒取り継続、評価項目の追加、定跡は対象外。
- 今回追加する探索と必要な共通処理を分け、既存三方式の全面分割は行わない。

## 承認・実行状態

2026-10-17、本人がGPT-6.1 Solを設定し、このセッションで実装開始を指示した。実行は私自身が順に行い、各段階を独立レビューする。本文中のコードは確認内容の記述であり、製品・テストファイルへ転記していない。下記コマンドは承認後の実行用で、今回実行した検証結果ではない。

作業場所 `/Users/oki2a24/kaname-shogi`、作業ブランチ `codex/engine-search-comparison-design`、文書作業開始HEAD `1af87d8`。実行開始時に現在状態を再確認する。新しいworktreeは前提にしない。main統合は別途本人承認が必要。

## レビューフォーカス

1. 二手以降の探索で発生したValueErrorを、不正SFENとして2へ変換しない（タスク5）。
2. 根が手なし、またはdepth=0でも訪問1・正しい値・選択なしが成立する（タスク2・4）。
3. 同点に見えるαβ境界値で、本当は劣る候補へ選択を上書きしない（タスク3）。
4. 後手開始や終端が深さ境界に一致する場合に、視点と勝敗優先が崩れない（タスク2・4）。
5. 一方式だけ完了した後の中断で、完了行は残し全体成功を表示しない（タスク5）。

## ファイルと公開契約の一覧

全体の依存方向は設計書に従う。以下の名前は本計画で実装者間の契約として固定する。

| ファイル | 新規／変更と担当 |
| --- | --- |
| `kaname_shogi/evaluation.py` | 新規：駒価値表と `material_balance(position: Position, perspective: Side) -> int` |
| `kaname_shogi/movegen.py` | 変更：駒得の互換入口、`position_after_move(position: Position, move: Move) -> Position` を既存経路へ委譲 |
| `kaname_shogi/search/__init__.py` | 新規：副作用のないパッケージ |
| `kaname_shogi/search/result.py` | 新規：Score、SearchResult |
| `kaname_shogi/search/contracts.py` | 新規：NodeInspection、SearchOperations |
| `kaname_shogi/search/core.py` | 新規：共通再帰探索 |
| `kaname_shogi/search/minimax.py` | 新規：全幅入口 |
| `kaname_shogi/search/alpha_beta.py` | 新規：αβ入口 |
| `kaname_shogi/search/shogi.py` | 新規：将棋用操作セット |
| `kaname_shogi/search/compare.py` | 新規：コマンド・比較・表示 |
| `tests/search_tree_support.py` | 新規：数値木データと操作セット。探索アルゴリズムは書かない |
| `tests/test_evaluation.py` | 新規：評価の独立期待値と互換入口 |
| `tests/test_movegen.py` | 変更：新しい複製適用入口と既存経路の補完 |
| `tests/test_search_minimax.py` | 新規：汎用全幅探索 |
| `tests/test_search_alpha_beta.py` | 新規：枝刈り・境界・訪問数 |
| `tests/test_search_shogi.py` | 新規：将棋との接続・SFEN教材 |
| `tests/test_search_compare.py` | 新規：比較・表示・例外・コマンド |

データは変更不可のdataclassを基本とし、結果・手の並びはtuple。探索対象のPositionは可変なので操作の非破壊契約で保護する。英語の型名には日本語名とデータ／操作の区別をdocstringへ書く。

- `Score = tuple[int, int]`：勝ち `(1,0)`、通常 `(0,n)`、負け `(-1,0)`。
- `NodeInspection[M](moves: tuple[M, ...], maximizing: bool, terminal_score: Score | None)`：局面調査結果データ。終端時はmoves空かつ値あり、継続時は手ありかつ値None。
- `SearchOperations[N,M](inspect: Callable[[N], NodeInspection[M]], advance: Callable[[N,M], N], evaluate: Callable[[N], Score])`：操作を束ねるデータ。
- `SearchResult[M](score: Score, move: M | None, visited_nodes: int, root_scores: tuple[tuple[M, Score], ...] | None)`：完了結果データ。全幅だけroot_scoresを保持、根手なしは空tuple、αβはNone。
- `core.search(node: N, depth: int, operations: SearchOperations[N,M], *, pruning: bool) -> SearchResult[M]`：内部共有操作。
- `minimax.search(node: N, depth: int, operations: SearchOperations[N,M]) -> SearchResult[M]`：pruning=Falseで委譲。
- `alpha_beta.search(node: N, depth: int, operations: SearchOperations[N,M]) -> SearchResult[M]`：pruning=Trueで委譲。
- `shogi.make_operations(perspective: Side) -> SearchOperations[Position, Move]`：開始側を固定した接続操作。
- `compare.main(argv: list[str] | None = None) -> int`：標準出力／標準エラーへ表示するコマンド操作。モジュール入口がSystemExitへ反映。
- `compare.format_move(move: Move | None) -> str`：表示操作。手なしは「なし」、通常・成り・打ちをUSIと日本語で併記。
- `compare.results_match(full: SearchResult[Move], pruned: SearchResult[Move]) -> bool`：全幅の確定候補集合と両選択手、根評価を照合。両方手なしのときだけ手なし分岐。

## 共通の実行規律

各タスクの振る舞い単位で、以下を繰り返す。全部のテストを先に書いて一括実装しない。

- [ ] 対象契約・独立期待値・検出したい誤りを記してテストを一つ追加する。英語メソッド名、日本語docstring（振る舞いと検出対象）を付ける。
- [ ] 単独実行で意図したassertionの失敗を確認する。import失敗だけをRed完了としない。必要なら最小の呼出可能な仮実装を置いて振る舞いの失敗を確認する。
- [ ] 最小実装して同じ確認を成功させ、タスク内の関連範囲を実行する。
- [ ] Refactorの要否を判断し、変更の有無と理由を記録する。
- [ ] 独立レビューで契約／代表例／検出対象／他テストの補完／未検証を渡し、Critical・Important・Minorの結論を残す。Critical・Importantは修正・再検証・再レビューする。
- [ ] import変更時に `.venv/bin/ruff check --select I --fix .`、続いて `.venv/bin/ruff format .`、`.venv/bin/ruff check .`、差分確認、該当テストを行う。
- [ ] 学習記録と現在地へ実績を更新して、タスクの明示したファイルだけをステージ・コミットする。`--no-verify`を使わない。

既存処理の抽出は、既存テストの初回Greenを移動前基準として記録し、未実装Redとは呼ばない。必要な新入口だけ新しい振る舞いとしてRedを確認する。

## タスク 1：評価の正本と複製適用の公開入口

**ファイル:** evaluation.py新規、movegen.py変更、test_evaluation.py新規、test_movegen.py変更。

**消費:** 既存Position/Move、`movegen._position_after_move`、既存駒価値表。
**生産:** 上記 `evaluation.material_balance`、`movegen.material_balance` の互換入口、`movegen.position_after_move`。

- [ ] 既存movegen／探索停止テストを実行し、移動前の振る舞いを確認する。
- [ ] `test_material_balance_keeps_perspective_and_compatibility`：取り返しSFENに対する独立値を両入口で確認する。

```python
self.assertEqual(material_balance(position, Side.SENTE), 13)
self.assertEqual(material_balance(position, Side.GOTE), -13)
self.assertEqual(movegen.material_balance(position, Side.SENTE), 13)
```

- [ ] `test_position_after_move_preserves_source_and_hands`：歩取り5e5d後の点15、先手持ち歩1、元局面13・盤面・持駒・手番不変、別枝非共有を確認。未知型TypeErrorと不合法ValueErrorを隠さない。既存適用の打ち・成りは既存テストで補完する。
- [ ] 共通規律のRed→最小実装→Greenを行う。駒価値表は一か所に保持し互換入口を残す。時間制御経路を変更しない。
- [ ] 実行：`.venv/bin/python -m unittest discover -s tests -p 'test_evaluation.py' -v`、同様に `test_movegen.py` と `test_search_movegen.py`。期待：全てOK。
- [ ] 独立レビュー・記録後、対象4ファイルと実績文書をコミット。例：`refactor: 駒得評価を共有し複製適用の入口を公開`。

## タスク 2：数値木で全幅探索を成立させる

**ファイル:** searchのinit/result/contracts/core/minimax、search_tree_support.py、test_search_minimax.py。
**消費:** 将棋型に依存しない。
**生産:** 上記データ4種、core.search、minimax.search（pruning=Trueの機能はタスク3）。

数値木用 `TreeNode` は `label: str`、`score: Score`、`maximizing: bool`、順序付き `(手ラベル, 子節点)`、任意のterminal_scoreを持つ変更不可データ。空の子ならterminal_scoreまたはscoreで終了し、子があるときは深さ打切りまでscoreを使わない。操作セットは節点の情報を返すだけで、minimaxを複製実装しない。

- [ ] `test_depth_changes_best_move`：設計の一本道二枝を作り、次の独立期待値を確認する。

```python
for depth, score, move, visits in ((2, 1, 'A', 5), (3, 2, 'B', 7), (4, 3, 'A', 9)):
    result = minimax.search(root, depth, operations)
    self.assertEqual((result.score, result.move, result.visited_nodes), ((0, score), move, visits))
```

- [ ] `test_minimizes_opponent_replies_and_retains_root_scores`：最大根・最小子A=[3,5]、B=[4,6]。score=(0,4)、move=B、visits=7、root_scores=((A,(0,3)),(B,(0,4)))。
- [ ] `test_zero_depth_and_terminal_precedence`：depth0の非終端は静的値・手なし・visits1・root_scores空。終端の負けと静的＋1000000を併置した節点は負け、evaluate/advance呼出なし。深さ境界とそれより前の終端も確認。
- [ ] `test_first_equal_best_and_invalid_depth`：A/B同点なら最初。順序を逆にすればB。depthに−1、True、1.5を渡すとValueError。inspectが各訪問一回であることを確認。
- [ ] 共通規律で本体を最小実装する。深さ確認、訪問、inspect、終端、depth0、順序付き再帰、厳密改善時更新の順。
- [ ] 実行：`.venv/bin/python -m unittest discover -s tests -p 'test_search_minimax.py' -v`。期待：OK。
- [ ] max/min反転または深さを減らさない誤りの代表を隔離コピーへ入れ、該当の意図したFAILと復元後OKを記録する。無限再帰を要する注入は避け、depthの比較を一つずらす等の有限の誤りを使う。
- [ ] 独立レビュー・記録・対象ファイルのコミット。例：`feat: 操作を分離した全幅探索を追加`。

## タスク 3：同一本体へαβ枝刈りを追加

**ファイル:** core.py変更、alpha_beta.py新規、test_search_alpha_beta.py新規。
**消費:** タスク2のデータ、操作、数値木。
**生産:** alpha_beta.searchとpruning=Trueのcore.search。

- [ ] `test_prunes_minimizing_branch`：最大根・最小子A=[3,5]、B=[−2,10]。

```python
self.assertEqual((full.score, full.move, full.visited_nodes), ((0, 3), 'A', 7))
self.assertEqual((pruned.score, pruned.move, pruned.visited_nodes), ((0, 3), 'A', 6))
self.assertIsNone(pruned.root_scores)
```

- [ ] `test_prunes_maximizing_branch`：最小根・最大子A=[2,4]、B=[5,10]。score4・A・全幅7／αβ6。一本道の最大根を上に足す場合は8／7。省いた葉のinspectが呼ばれていないことも確認。
- [ ] `test_equal_bound_does_not_replace_exact_best`：最大根A=[3,5]、B=[3,−2]。αβはBの境界3でAを置き換えずscore3・A・visits6。全幅のB確定値は−2。
- [ ] `test_true_ties_and_no_cutoff`：真の同点A=[3,5]、B=[3,4]は最初の手。刈れないA=[3,5]、B=[4,6]は4・B・両方7。
- [ ] 上下限None、最大側で下限更新、最小側で上限更新、両方ありかつ下限>=上限で省略する最小実装。根では無境界で開始。子からの値はfail-softの境界を許容するが公開する根は確定値。
- [ ] 実行：`.venv/bin/python -m unittest discover -s tests -p 'test_search_minimax.py' -v` と `test_search_alpha_beta.py`。期待：全てOK。
- [ ] 等号を省かない誤り、境界を後続へ渡さない誤り、同点で上書きする誤りを隔離コピーで個別注入。値だけでなく訪問・手のassertionがFAILすることを記録。
- [ ] 独立レビュー・記録・コミット。例：`feat: 共通探索にαβ枝刈りを追加`。

## タスク 4：将棋接続とSFEN教材を確認

**ファイル:** shogi.py新規、test_search_shogi.py新規。
**消費:** タスク1の評価・公開適用、既存legal_moves/is_in_check、タスク2/3の入口。
**生産:** make_operations(perspective)。

- [ ] `test_kings_only_matches_and_counts_depth_two`：設計の玉だけSFEN。二・三・四手の根は通常0、最善候補は全3手、先手の選択9i9h。二手の厳密期待値：全幅13、αβ9。深い場合の訪問は正数かつαβ<=全幅を確認し、未検算の値を発明しない。
- [ ] `test_gote_perspective_and_material_sign`：取り返しSFENのevaluateは先手(0,13)、後手(0,−13)。make_operations(後手)で先手番はmaximizing=False、後手番はTrue。玉だけ後手開始では両探索0・最初の合法手を選ぶ。
- [ ] `test_material_lines_and_source_independence`：取り返し列13→15→−15→3、静かな逃げ列−2維持、交換枝−2→16→−14をadvance/evaluateで確認。各手の合法性をinspectから確認し元局面不変。これを根の探索値と呼ばない。
- [ ] `test_mate_at_root_and_horizon`：5c5bが詰ませる既存配置。直後のinspectは先手視点勝ち／後手視点負け、手空。後手を開始側として二・三・四手を読むと負け・手なし・訪問1。先手開始の元局面の二手探索は勝ち（具体的勝ち手の一意性は要求しない）。
- [ ] `test_no_moves_without_check_and_inspection_reuse`：空盤持駒なしは通常0・手なし・訪問1。inspectがlegal_movesを一度呼び、手あり時は余計な詰み判定を呼ばない。手なし時はis_in_checkで判定。
- [ ] 成りの例は `8k/9/9/7P1/9/9/9/9/K8 b - 1` の `2d2c+`。先手駒得1→12、2三がと金、後手番、元局面不変。打ちの例は `8k/9/9/9/9/9/9/9/K8 b P 1` の `P*5e`。先手駒得1維持、持ち歩1→0、5五が先手歩、後手番、元局面不変。inspectの合法手に含まれることを確認してadvanceを通す。ルール網羅は既存test_movegenで補完する。
- [ ] 共通規律で実装し、`.venv/bin/python -m unittest discover -s tests -p 'test_search_shogi.py' -v` と既存test_movegen.py／test_search_movegen.pyを実行。期待：全てOK。
- [ ] 開始側を先手固定にする誤り、詰みを通常点へ落とす誤り、訪問の根を数えない誤りから接続リスクに合う代表を注入しFAIL／復元OKを確認。
- [ ] 独立レビュー・記録・コミット。例：`feat: 将棋局面を共通探索へ接続`。

## タスク 5：比較コマンドと最終受入

**ファイル:** compare.py新規、test_search_compare.py新規。利用案内はREADME.md、仕様参照はdocs/README.md、実績は今回学習記録・resume.md・next-topics.md。
**消費:** 既存parse_sfen/format_usi_move、make_operations、両search、SearchResult。
**生産:** main、format_move、results_match。

- [ ] `test_matches_exact_values_and_best_membership`：全幅根候補A3/B3/C−2。αβ3/Bは成功、3/C・2/Aは失敗。両方手なしで同評価は成功、片方だけ手なしは失敗。αβ境界の全候補一覧を必要としない。
- [ ] `test_formats_board_promotion_drop_and_no_move`：次を厳密確認する。

```python
self.assertEqual(format_move(parse_usi_move('5e5d')), '5e5d（5五→5四）')
self.assertEqual(format_move(parse_usi_move('2d2c+')), '2d2c+（2四→2三・成り）')
self.assertEqual(format_move(parse_usi_move('P*5e')), 'P*5e（5五に歩を打つ）')
self.assertEqual(format_move(None), 'なし')
```

- [ ] `test_success_runs_fixed_depths_and_reports_results`：mainへ玉だけSFENを渡し0。標準出力に入力SFEN、開始側、深さ2/3/4、全幅／αβの6行、値・手・訪問・深さごとの一致判定。標準エラー空。各方式は開始局面から独立実行し履歴を共有しない。
- [ ] `test_mismatch_continues_and_returns_one`：一深さの結果だけ意図的に差し替え、残る深さも実行、出力に該当深さの不一致、標準エラー診断、終了1。
- [ ] `test_invalid_input_does_not_search`：引数なし／不正SFEN／未対応--depthを2にし、探索呼出0回、標準エラー診断。argparseのSystemExitはmain内の引数処理境界で整数コードへ戻す。--helpは0。
- [ ] `test_search_value_error_is_not_input_error`：入力変換は成功、探索がValueError('内部故障')を出す場合mainから伝播することをassertRaisesRegexで確認。広い入力エラー捕捉を検出。
- [ ] `test_interrupt_retains_completed_rows`：二手全幅の終了後にαβでKeyboardInterruptを発生させる。mainは130、完了全幅行あり、標準エラーに深さと方式・未完了、全体成功なし、後続深さを開始しない。
- [ ] 共通規律で実装。入力解析、表示、探索呼出の例外境界を分ける。比較不一致は結果として扱い、内部例外を成功や入力エラーへ変換しない。
- [ ] `.venv/bin/python -m unittest discover -s tests -p 'test_search_compare.py' -v`。実プロセスの小さいスモークではsys.executableで `-m kaname_shogi.search.compare` を呼び、玉だけ成功0／不正入力2／--help0を確認する。タイムアウトはテストのハング検出用で、製品の時間制御とは別。
- [ ] 固定時間のsleepに依存したSIGINT実プロセステストは追加しない。Ctrl+Cの捕捉・表示は上記境界テストで確認し、OSからの配送経路は未検証と記録する。
- [ ] 最終整形・静的検査後、`.venv/bin/python -m unittest discover -s tests -v` を一度実行。既存CLI/USI三方式・時計・停止・棋譜等を含む回帰を確認し、件数ではなく変更契約との対応を記す。新しい変更・失敗がなければ全体を不要に繰り返さない。
- [ ] 承認済みコマンドを玉だけ局面で実行し、二手の13／9と全深さの一致を確認。実行時間や棋力の一般保証にはしない。
- [ ] 独立した最終レビュー、Critical/Important解消、結果文書更新、リンク確認、対象ファイルのコミット。例：`feat: SFENから探索方式を比較する開発コマンドを追加`。

## 各タスクのステージと記録

`git add .`は使わず、各タスクのファイル一覧と、その時点で更新した学習・現在地文書を指定する。ステージ済み差分を確認し、通常コミットのフックを通す。製品コードの各タスク完了時に次の文書更新時点も本人へ伝える。

実績は[学習記録](../learning/engine-improvement-stage-design.md)に、対象契約、Redの失敗理由、実変更、Green、Refactor判断、誤り注入、独立レビューの各重大度、未検証、コミットを追記する。設計・計画から変わるときは差分の理由を記し、承認範囲を越える変更を先取りしない。

## 最終の統合と学習

main統合は実装・検証・独立レビュー・記録がそろってから本人承認を得る。元ディレクトリへの取り込み状況を明示し、取り込み先で必要な検証を行う。最後の理解確認を一問だけ出し、本人回答・補足を記録する。その後に次テーマ候補を見直す。反復深化などへ自動的に着手しない。

## 計画の自己点検と実行方法

仕様→タスク対応：共有化1、操作／深さ／終端／結果2、枝刈り／境界3、将棋との接続4、SFEN／表示／合否／終了／回帰5。共通処理の一致だけに頼らず独立期待値と誤り注入を用意した。クラス名・引数・結果フィールドは上記契約で統一した。

コマンドは既存unittest discoverの形式に合わせた。新規ファイルを指定するコマンドは実装後に利用可能になるため計画段階では未実行。計画だけのため製品テストを実行したとは報告しない。

推奨実行方法は、このセッションの本人との学習速度に合わせたネイティブ実装。タスク間の依存が強いため同じ実装担当が順に進め、各段階の独立レビューは別の担当に依頼する。サブエージェント駆動を選ぶ場合も依存順は維持し、同じファイルを並行編集しない。どちらも本人の計画承認と実行方法の選択後に開始する。
