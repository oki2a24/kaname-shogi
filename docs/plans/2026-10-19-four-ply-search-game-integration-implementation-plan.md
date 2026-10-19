# 四手探索二方式の対局接続 実装計画

> **AIエージェントへの指示:** 本人が2026-10-19に計画とネイティブ実行を明示承認済み。`executing-plans` と `test-driven-development` に従って実行し、チェックボックスを実績に合わせて更新する。mainへの取り込みは別途本人承認が必要。

**目標:** 全幅読み・αβ枝刈りの最大四手反復探索を、既存三方式と共存するCLI・USIの選択肢にする。

**アーキテクチャ:** 共通探索本体と共通反復ループを使い、全幅とαβを選択可能にする。新設する `game_search.py` が既存三方式と新二方式を振り分け、USI向けには既存の最終結果型へ変換する。CLI・USIは現在の選択寿命と送信管理を維持する。

**技術スタック:** 現行Python 3.15環境、標準ライブラリ、unittest、固定版Ruff 0.16.10。依存・Python・時計設定の変更なし。

**仕様:** [本人承認済み設計](2026-10-19-four-ply-search-game-integration-design.md)。識別子、`pruning` 引数、対局用アダプター、結果型変換、以下の確認方法は本計画で具体化した提案であり、計画承認対象。

**グローバル制約（設計から）:**

- 「既存のRandom・Material・TwoPlyMaterialも引き続き選択可能にする。」
- 「選択は既存のCLI対局前メニューとUSI `Difficulty` 設定に二方式を加えて行い、別の設定群は作らない。」
- 「CLIでは、選んだ方式を一局の全コンピュータ手で使う。」
- 「USIでは現在の実装と同じく、設定値を最初の `go` で局用に固定し、対局中に届いた設定変更は `usinewgame` で始まる次局から使う。」
- 「USIの既存時計予算を使い、予算式を変更しない。」
- 「探索本体・評価・停止確認・反復ループを方式ごとに複製しない。」
- 各コンピュータ手で深さ1→4、CLIは時間制御なし。通常停止は最新完了手または合法予備手、抑制は応答手なし。USI側が送信前に再確認し最大一回送信する。
- 日本語で説明・docstring・学習記録を書く。テストメソッドは英語名と日本語docstringを付け、検出対象も説明する。

## 状態と開始条件

2026-10-19、本人「続けて」を受け、同セッションで実装計画案を作成。本人はその後「yes」と回答し、計画と推薦したネイティブ実行方法を明示承認した。承認時の開始HEADは `867b64c`、`main` は `origin/main` より3コミット先行。現在の作業ブランチは `codex/four-ply-game-integration`。既存未追跡 `.antigravity/tasks/` は保持し、ステージしない。計画承認前には製品テストを実行していない。

計画とネイティブ実行の承認後に上記作業ブランチを作成した。通常コミットのフックを通し、main取り込みは実装・検証・独立レビュー・記録がそろってから本人の別承認を待つ。

## レビューフォーカス

仕様から見落としやすい以下の五条件を各タスクへ割り当てる。

1. 全幅の名前でαβを呼ぶと評価だけの比較では発見できない。省略可能な数値木で全幅の全訪問・全根候補値を確認する（タスク1・2）。
2. 後手開始で先手視点を使うと合法でも悪い手を選び得る。開始側の操作セット、元局面不変、二方式の実探索を確認する（タスク3）。
3. 深さ1完了前の時計0／stopでも合法予備手が必要。抑制は予備手を復活させない（タスク2・3・5）。
4. 探索返却後・送信直前に抑制が確定した場合も送信0回。送信が先に確定した場合は再送しない（タスク5）。
5. 新方式選択後に局中変更・未知値・次局開始が重なる場合も現在局と設定値を取り違えない（タスク5）。

## ファイルと公開インターフェース

| ファイル | 責務・変更 |
| --- | --- |
| `kaname_shogi/search/minimax.py` | 優先手と制御付き一深さ探索の薄い入口 |
| `kaname_shogi/search/iterative_deepening.py` | 共通反復で全幅／αβを選択。既定は従来のαβ |
| `kaname_shogi/movegen.py` | 選択方針の値を二つ追加。既存三方式の探索本体は維持 |
| `kaname_shogi/game_search.py`（新規） | 対局方式の振分け、将棋操作セット生成、USI向けの結果変換 |
| `kaname_shogi/cli.py` | メニューを五方式へ拡張し対局用選択へ接続 |
| `kaname_shogi/usi_engine.py` | Difficulty通知・受付を拡張し対局用探索へ接続 |

新しい方針データは `MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH` と `FOUR_PLY_ALPHA_BETA`。CLI番号4・5、USI値 `FullWidth4`・`AlphaBeta4` をそれぞれ対応付ける。既存番号1〜3と既定Randomは維持する。

`minimax.search(node, depth, operations, *, preferred_move=None) -> SearchResult` と、新規 `minimax.search_controlled(node, depth, operations, control, *, preferred_move=None) -> SearchResult | SearchInterrupted` は共通本体に `pruning=False` を渡す。優先手は根だけに適用し、既定Noneでは従来順序・比較結果を保つ。

`iterative_deepening.search(node, max_depth, operations, *, pruning: bool = True) -> Iterator[IterationResult]`、`search_controlled(node, max_depth, operations, control, *, pruning: bool = True) -> ControlledSearchResult` とする。Trueは既存αβ、Falseは全幅。bool以外は、通常入口でも反復取得前、制御付き入口でも準備前にValueError。既存の引数呼出しと既定動作を保つ。

対局用の新しい二操作は旧入口と同じ引数形を持つ。

- `game_search.choose_move(position: Position, moves: tuple[Move, ...], policy: MoveSelectionPolicy, rng: random.Random) -> Move | None`。旧三方式は元の `movegen.choose_move` へそのまま委譲。新二方式は開始側視点の通常操作セット、上限4、指定pruningで反復を最後まで取得する。合法手なしはNone。入力movesは現局面の全合法手という従来の前提を保つ。CLIの事前合法手生成は維持し、新探索の根調査は独自の操作セットで行う。根のキャッシュ機構は追加しない。
- `game_search.search_move(position: Position, policy: MoveSelectionPolicy, rng: random.Random, control: SearchControl) -> movegen.SearchResult`。旧三方式は元の `movegen.search_move` へ委譲。新二方式は開始側視点の制御付き操作セットを作り、同じcontrol、上限4、指定pruningで反復する。新方式ではrngを使わない。

制御付き結果の変換は COMPLETE→COMPLETE、NO_LEGAL_MOVE→COMPLETE（手なし）、STOPPED→INTERRUPTED、SUPPRESSED→SUPPRESSED（手なし）。探索中断時の手を選び直さず、返されたmoveをそのまま渡す。元の反復結果は完了記録を保持するが、既存送信境界が使うデータは状態と手だけ。USI層へ評価表示や新しい通知を追加しない。

`game_search` が `movegen` と `search.shogi` に依存する方向とし、ルール側から対局用モジュールをimportしない。既存 `movegen` の選択APIは三方式用として残す。制御付き旧APIの方針検査は三方式を明示列挙し、新しいenum値を誤受理しない。

## 共通の実行規律

以下は承認済み計画の実行規律。各タスク内で振る舞いを一つずつRed→最小実装→Greenへ進め、実績を学習記録と作業台帳に残す。

- [x] [検出力点検](../knowledge/test-coverage-review.md)と `~/.codex/observations/test-driven-development.md` を読み、契約・独立期待値・検出する誤りをテスト前に記す。
- [ ] 英語名・日本語docstringのテストを一つ追加し、指定ファイルをunittestで実行する。import失敗だけでRed完了にせず、必要なら最小の呼出可能な仮実装でassertionの失敗を得る。
- [ ] 最小実装後に同じテストとタスクの関連範囲を実行する。既存テストの初回Greenは未実装Redと区別する。
- [ ] Refactorの要否を記録し、変更の有無にかかわらず独立レビューでCritical・Important・Minorと対応を残す。Critical・Importantは解消し再検証・再レビューする。
- [ ] 各タスクの代表的な誤りを隔離コピーへ注入し、意図したassertionのFAILと復元後成功を確認する。単独が見逃し全体が検出する誤りも区別する。
- [ ] import変更時は `.venv/bin/ruff check --select I --fix .`、続いて `.venv/bin/ruff format .`、`.venv/bin/ruff check .`、差分確認、関連テストを行う。
- [ ] 実績は [計画学習記録](../learning/four-ply-search-game-integration-plan.md) に追記。対象ファイルだけステージし、`git diff --cached --check` と内容を確認して通常コミットする。`.antigravity/tasks/` と無関係の変更を含めない。

## タスク 1：全幅の優先手・制御付き入口

**ファイル:** 変更 `kaname_shogi/search/minimax.py`、`tests/test_search_minimax.py`。新規 `tests/test_search_minimax_controlled.py`。
**消費:** 既存core.search/search_controlled、SearchControl、操作セット、数値木補助。
**生産:** 上記のminimax二入口。再帰・停止・採点はcoreを共有。

- [x] `test_preferred_move_only_reorders_root` と `test_full_width_keeps_all_candidates` を追加する。数値木A=[3,5]、B=[−2,10]、深さ2では評価3・A・訪問7、root_scores=((A,3),(B,−2))。優先Bでも両枝を最後まで訪問し、根の候補順だけB→A。同点木A=[3,5]、B=[3,4]で優先BならBを選ぶ。不在優先手はadvance前にValueError。

```python
self.assertEqual((result.score, result.move, result.visited_nodes), ((0, 3), 'A', 7))
self.assertEqual(result.root_scores, (('A', (0, 3)), ('B', (0, -2))))
```

- [x] 制御付き `test_completed_result_is_full_width` で同じ独立値を確認し、prepareを呼ばないことも確認する。`test_stop_and_suppression_do_not_publish_partial_scores` は操作途中で要求し、SearchInterrupted(STOP/SUPPRESS)を返し未完了SearchResultを作らないことを確認する。
- [x] 実行: `.venv/bin/python -m unittest discover -s tests -p 'test_search_minimax*.py' -v`。未実装の振る舞いでFAILする理由を確認する。
- [x] 最小実装: preferred_moveをcoreへ渡す。新制御付き入口もcoreへ委譲し、bool以外の深さなど既存検査・例外をそのまま使う。
- [x] 同じコマンドと `test_search_alpha_beta*.py` を実行してOK。代表変異 `pruning=True` を全幅入口へ入れ、訪問数／候補一覧assertionのFAILを確認する。
- [x] 共通規律のレビュー・記録・コミット。例: `feat: add controlled full-width search entry`。

## タスク 2：二方式で共通の反復深化

**ファイル:** 変更 `kaname_shogi/search/iterative_deepening.py`、`tests/test_search_iterative_deepening.py`、`tests/test_search_iterative_deepening_controlled.py`。
**消費:** タスク1のminimax入口と既存αβ入口。
**生産:** pruningを選べる二つの反復入口。既存呼出しはTrueで互換。

- [x] `test_both_methods_complete_depths_one_to_four` を追加し、既存 `depth_tree()` の手計算値を各方式へ個別に照合する。

```python
self.assertEqual([(r.depth, r.result.move, r.result.score,
                   r.result.visited_nodes, r.total_visited_nodes) for r in records],
                 [(1, 'A', (0, 0), 3, 3), (2, 'A', (0, 1), 5, 8),
                  (3, 'B', (0, 2), 7, 15), (4, 'A', (0, 3), 9, 24)])
```

- [x] `test_full_width_is_not_pruned` で省略可能な木の全訪問を確認。優先手・例外・不正上限・不正pruningの即時検査も両経路へ適用する。
- [x] 制御付きの既存STOPPED/SUPPRESSED/NO_LEGAL_MOVE、深い未完了結果を採用しない例、同じcontrol、返却直前抑制、操作故障の代表をFalse/Trueで確認する。stop先行は合法予備手、深さ2完了後の深さ3停止は深さ2の手、抑制はmove=Noneとする。
- [x] 実行: `.venv/bin/python -m unittest discover -s tests -p 'test_search_iterative_deepening*.py' -v`。新しい選択と全幅経路の振る舞いFAILを確認する。
- [x] 最小実装: 選択した一深さ入口を既存 `_iterations` へ渡す。準備・最終状態選択・制御保持を一か所に保ち、既定入口の実行時patchも有効にする。
- [x] 同コマンドと `test_search_compare*.py` を実行してOK。代表変異はFalse無視と最新記録の未完了上書き。既存比較コマンドがαβ既定のままであることを確認する。
- [x] 共通規律のレビュー・記録・コミット。例: `feat: select full-width or alpha-beta iterative search`。

## タスク 3：五方式の対局用選択アダプター

**ファイル:** 新規 `kaname_shogi/game_search.py`、`tests/test_game_search.py`。変更 `kaname_shogi/movegen.py`、`tests/test_search_movegen.py`。
**消費:** タスク2の反復入口、既存三方式、将棋操作セットと結果型。
**生産:** 上記の新enum値、game_search.choose_move/search_move。

- [x] `test_legacy_policies_delegate_unchanged` で旧三方式の各入口へ局面・moves・policy・rng・controlの同じ参照を一回だけ渡し、結果を選び直さず返すことを確認する。旧search_moveは新enum値を合法生成前に拒否する。
- [x] 既存 `test_search_movegen.py` のenum全列挙4か所は、対象APIが扱う旧三方式の明示列挙へ変更する。既存三方式の条件・期待値は削らず、新二方式の同じ停止・抑制・連続探索の契約はtest_game_searchで補完する。enumのdocstringは五方式の方針値として説明し、探索深さを表さないという旧説明を修正する。
- [x] `test_new_modes_use_depth_four_and_starting_side` で両先後・二方式を確認し、呼出しは上限4、正しいpruning、開始側視点、同じcontrolとする。新方式のrng.choiceは0回。
- [x] `test_controlled_outcomes_preserve_selected_move` で四状態を上記の対応表に照合する。STOPPEDで予備手のみ／完了記録ありを区別し、SUPPRESSEDの診断記録から手を復活させない。故障RuntimeErrorは伝播する。

```python
self.assertEqual(adapted_stopped, movegen.SearchResult(movegen.SearchCompletion.INTERRUPTED, selected))
self.assertEqual(adapted_suppressed, movegen.SearchResult(movegen.SearchCompletion.SUPPRESSED, None))
```

- [x] `test_unknown_policy_fails_before_search` は未知のobjectやNoneを両アダプターへ渡しValueError、探索開始0回を確認する。
- [x] 実行: `.venv/bin/python -m unittest discover -s tests -p 'test_game_search.py' -v`。入口を仮実装した場合も状態・深さ・方式のassertionによるFAILを得る。
- [x] 最小実装し、元局面不変と実探索接続は玉だけの先手・後手開始SFENで確認する。各方式の時計なし制御付き結果と通常反復の最終手を照合し、既存の将棋接続テストを独立期待値の補完として使う。
- [x] 同コマンド、`test_search_shogi*.py`、`test_search_movegen.py` を実行してOK。代表変異は先手固定、STOPPED→手なし、SUPPRESSEDの記録手復活から選ぶ。
- [x] 共通規律のレビュー・記録・コミット。例: `feat: route five game move selection policies`。

## タスク 4：CLIの五方式メニューと対局接続

**ファイル:** 変更 `kaname_shogi/cli.py`、`tests/test_cli.py`、`tests/test_cli_entrypoint.py`。
**消費:** タスク3のchoose_moveと五方式。
**生産:** 番号4=全幅、5=αβを選べるCLI。対局呼出しの引数形は従来どおり。

- [x] メニューの対応テストを五方式へ拡張する。表示には `4: 全幅読み（最大4手）、5: αβ枝刈り（最大4手）`、エラーは `エラー：一手選択方針を1〜5で選んでください。`。無効例を従来の4から6へ変更し、空入力Random・再入力を維持する。

```python
self.assertEqual(cli.choose_move_selection_policy(input_fn=lambda: '4', output_fn=lambda _: None),
                 MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH)
self.assertEqual(cli.choose_move_selection_policy(input_fn=lambda: '5', output_fn=lambda _: None),
                 MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA)
```

- [x] `test_new_modes_remain_fixed_for_game` は一局の複数コンピュータ手で同じpolicyが届くことを確認。`test_each_computer_turn_restarts_at_depth_one` は小局面から二回の新方式呼出しで一深さ入口の深さ列がそれぞれ[1,2,3,4]となることを確認する。実際の対局入口がアダプターを通ることも確認する。
- [x] 実行: `.venv/bin/python -m unittest discover -s tests -p 'test_cli*.py' -v`。メニューと呼出し先の振る舞いFAILを確認する。
- [x] 最小実装: cliのchoose_moveのimportをgame_searchへ接続し、メニューに二項目追加。従来の合法手生成、対局形式、Ctrl+C終了、手の表示・適用を維持する。
- [x] 同コマンドを実行してOK。代表変異は番号4/5逆転、各手を深さ4単発に置換。時計・設定読込をCLIへ追加していないことを差分と呼出し検査で確認する。
- [x] 共通規律のレビュー・記録・コミット。例: `feat: offer four-ply search modes in CLI games`。

## タスク 5：USIの五方式・既存時計・停止応答接続

**ファイル:** 変更 `kaname_shogi/usi_engine.py`、`tests/test_usi_engine.py`。新規 `tests/test_usi_four_ply.py`。必要な既存同期試験は `tests/test_usi_concurrency.py` と `tests/usi_test_support.py` を参照する。
**消費:** タスク3のsearch_move、既存SearchContext・SearchControl・共通送信Lock・時計予算。
**生産:** 新二方式のDifficulty通知・受付・対局応答。送信アルゴリズムは既存のまま。

- [ ] USI宣言の期待値を `option name Difficulty type combo default Random var Random var Material var TwoPlyMaterial var FullWidth4 var AlphaBeta4` に更新。大文字小文字を無視した受付、最初のgoで固定、局中変更を次局へ延期、未知値後の保持を両新値で確認する。
- [ ] `test_new_modes_reuse_go_control_and_budget` は実アダプターを通し、時計付きgoで作った同一制御が反復へ届くことを確認する。設定はTimeManagementConfig(20, Fraction(2), Fraction(3,4), 2000)、入力は `go btime 600000 wtime 120000 byoyomi 30000`。予算の独立期待値は先手SearchBudget(30000,60000)、後手SearchBudget(6000,12000)。固定read_ns原点と同じ制御を観測し、深さごとの再構築を検出する。時計なしはNone、両時計0はSearchBudget(0,0)と区別する。
- [ ] `test_new_mode_results_send_once_or_suppress` は制御付き反復の四状態を実アダプター経由で返し、COMPLETE/STOPPEDは選択手を一回、NO_LEGAL_MOVEは `bestmove resign` 一回、SUPPRESSEDは0回とする。完了前stopの合法予備手も含める。

固定応答例は先手玉だけSFEN `8k/9/9/9/9/9/9/9/K8 b - 1` の合法手 `9i9h` を使う。

```python
self.assertEqual(completed_lines, ['bestmove 9i9h'])
self.assertEqual(stopped_lines, ['bestmove 9i9h'])
self.assertEqual(no_legal_move_lines, ['bestmove resign'])
self.assertEqual(suppressed_lines, [])
```

- [ ] `test_suppression_between_search_return_and_send` は新方式アダプターを通した探索担当を明示Eventで止め、共通Lock下で抑制確定→返却解除なら送信0回、送信確定→抑制なら一回のままとする。子プロセスの `run_isolated` でハングを回収し、固定sleepや期限内応答を合格条件にしない。探索例外も既存故障回収へ届き、予備手で隠さない。
- [ ] 実行: `.venv/bin/python -m unittest discover -s tests -p 'test_usi_four_ply.py' -v` と `test_usi_engine.py`。宣言だけでなく実アダプター経路のassertionでFAILを確認する。
- [ ] 最小実装: USI側search_moveのimportをgame_searchへ変更し、値表と宣言へ二方式追加。設定寿命・時計作成・送信Lock・担当回収を作り直さない。
- [ ] 上記と `test_usi_clock.py`、`test_usi_concurrency.py`、`test_usi_process_concurrency.py` を実行してOK。既存実プロセス試験の入力先行による抑制と区別し、必要な応答を待ってから次命令を送る。
- [ ] 代表変異は送信前抑制確認の欠落、新方式だけ局中再設定、control作り直し。新テスト単独／既存全体の検出を区別し、共通規律のレビュー・記録・コミット。例: `feat: connect four-ply modes to USI clock and stop handling`。

## タスク 6：全体回帰・利用案内・最終レビュー

**ファイル:** README.md、docs/knowledge/search-comparison.md、docs/knowledge/search-stop.md、docs/knowledge/usi-engine-response.md、docs/02-project-direction.md、docs/README.md、docs/resume.md、docs/next-topics.md、本計画・学習記録。機能変更のある説明だけ更新する。
**消費:** タスク1〜5の実装と検証証拠。
**生産:** 五方式の現行利用案内と、今回実測・未検証範囲を区別した実績。

- [ ] 最終Ruff整形・検査、`git diff --check`、`.venv/bin/python -m unittest discover -s tests -v` を実行する。全体回帰後に変更・失敗・未解決懸念がなければ不要に繰り返さない。
- [ ] READMEのCLI/USI五方式、各手1→4、USIのみ時計、全幅の待ち時間と時間保証なしを更新する。開発用比較と対局入口の違いを知識メモに反映し、当初合意の履歴は残す。
- [ ] 独立した最終ブランチレビューへ、契約／独立期待値／代表変異／既存補完／未検証を渡す。Critical・Importantを解消して再検証・再レビューし、各重大度の結果を記録する。
- [ ] 文書リンク・見出し、ステージ対象、差分を確認してコミットする。例: `docs: document five game search modes and validation`。
- [ ] mainへの取り込み内容を提示し本人の別承認を待つ。承認後に取り込み先で変更に見合う検証を行い、最後の理解確認を一問だけ出す。本人回答・補足を保存後に次候補を見直す。

## 検出範囲・留保・自己点検

数値木は独立した評価・最善手・訪問数で全幅／αβと深さを検出する。アダプターテストは方式、開始側、最大深さ、同じ制御、結果変換を検出し、将棋ルールの網羅は既存movegen/shogiテストが補完する。USI送信は新方式の実アダプター経路と既存の同期・プロセス試験を組み合わせる。方式を差し替えるmockだけの成功を接続実装の証拠にしない。

実時間内応答、全幅四手の実戦待ち時間、全局面・全OS・全競合、ShogiHome実機、棋力向上は未検証として残す。実機操作・性能計測を自動的に開始せず、必要なら別の条件設計を行う。新評価・置換表・並列化・CLI時計は含めない。

作成時の自己点検: 全幅制御入口=1、二方式反復と停止=2、選択・結果境界=3、CLI=4、USI寿命・時計・送信=5、利用案内・全体回帰・レビュー=6に対応。後続が使う名前・型・既定値は上記に統一した。既存低水準テストのenum全列挙4か所が新方式まで対象に含めてしまう点を検出し、旧三方式の明示列挙と新アダプター側の補完をタスク3へ追記した。コマンドは既存unittest discover形式に合わせており、未作成テストのコマンドを計画段階で実行したとは扱わない。

本人はネイティブ実装を選択した。共有する探索・結果境界に依存があるため、依存順で一段ずつ進める。各タスクの独立レビューと最後の独立ブランチレビューを、実装担当と別の視点で行う。
