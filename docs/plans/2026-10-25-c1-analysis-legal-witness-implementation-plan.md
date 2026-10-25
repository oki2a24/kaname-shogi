# C1分析CLIの合法手存在確認を短縮する実装計画

> **AIエージェントへの指示:** 承認後、このセッションの担当者が `superpowerssuperpowers:executing-plans` と `superpowerssuperpowers:test-driven-development` を使用して順に実装する。各ステップのチェックボックスで実績を追跡する。現時点では実装計画の承認待ちであり、TDD・製品コード・テスト変更は始めない。

**目標:** 保存棋譜の検証契約を維持し、中間局面の合法手全列挙を検証済みの次の記録手による存在確認へ置き換える。

**アーキテクチャ:** `GameRecord.from_payload` による全手の合法再生を保持し、`_validate_and_replay` 内で一度取得した履歴タプルから後続手の有無を判別する。反復判定後、中間局面は合法手ありを根拠付きで渡し、末尾局面だけ現行の全列挙を行う。分析と局単位再開が共用するreaderを同じ規則で検証する。

**技術スタック:** 現行Python、標準ライブラリ、`unittest`、`unittest.mock`、既存JSON形式。依存追加なし。

**仕様:** [本人承認済み設計](2026-10-25-c1-analysis-legal-witness-design.md)。設計全体へのyesに続く「正確さが落ちるか」という質問に、検証の同等性と実装後の確認を説明し、本人が「ok. 続けて」と回答した。設計承認と、この実装計画の承認は区別する。

## グローバル制約

- 本筋は現在稼働中の分析CLIの完了確認とB1の効果判断。この補助作業をC1完了と扱わない。
- 個々の棋譜手の合法性・計時・方式・USI整合性、毎手の千日手と上限、末尾局面・勝者・summary・組得点・95%区間の検証を保持する。
- 並列化・進捗表示・キャッシュ・二重再生の統合、CLI引数・保存形式・依存関係、通常CLI/USI、評価方式は変更しない。
- 日本語docstring、英語テスト名と日本語の振る舞い・検出対象の説明を付ける。
- 読込エラーだけを振る舞いのRedとしない。既存挙動で成功する契約検査は初回Greenと記録する。
- 稼働中の元分析器は最終出力時にもディスク上のソース指紋を読む。その分析が完了するまで現在の作業ディレクトリのPythonソースを変更しない。
- 実装は元分析の完了を確認した後、現在の `/Users/oki2a24/kaname-shogi`、ブランチ `codex/c1-analysis-performance-investigation` で担当者が順に行う。先行実装のためのworktree追加はこの計画に含めない。
- 確認比較の原本・seedを変更せず、新たな対局は行わない。大きな未追跡成果物と仮想環境バックアップを誤ってステージしない。

## レビューフォーカス

1. 合法な次の記録手があっても、千日手・上限による終局後は継続を拒否する（タスク1の反復・上限ケース）。
2. 最終手が上限到達と同時に詰み/合法手なしになる場合、その終局・勝者を上限より優先する（タスク1の末尾・先後反転ケース）。
3. 中間手が違法な移動・持ち駒なしの駒打ちの場合、履歴が存在するだけで受理しない（タスク1の不正棋譜ケース）。
4. 再開用の0手/複数手の中断・故障、終局直後中断を誤って完成局扱いしない（タスク1の共用reader・再開ケース）。
5. 分析の値が同じでも別の局や計時を混ぜていないか、入力SHAと分析器識別を区別して確かめる（タスク2の代表局と全成果物比較）。

## 対象ファイルと責務

| ファイル | 変更 |
| --- | --- |
| `kaname_shogi/comparison_result_io.py` | `_validate_and_replay` の中間/末尾分岐と前提の説明 |
| `kaname_shogi/comparison.py` | `board_terminal` の真偽の根拠を説明するdocstring。関数本体は維持 |
| 新規 `tests/test_comparison_result_replay.py` | 合法手存在根拠・末尾・拒否契約・共用readerの集中テスト |
| `tests/test_comparison_resume.py` | 複数手の未完了局を保存局読込から再投入分類まで通す補完ケース |
| 既存 `tests/test_comparison_result_io.py` 等 | 原則再利用。既存の反復・終局優先・条件/計時/集計の契約を回帰確認 |
| 知識メモ、設計・本計画・調査/C1学習記録、resume、索引 | 実装・検証・レビュー実績と承認段階を記録 |

共通movegen、GameRecord、比較実行器のコードを変更する必要が生じたら、この計画の範囲へ黙って加えず理由と変更案を提示する。

## タスク1：合法な次の手を根拠にするreaderと契約検証

**消費するインターフェース:** 現行の `_load_game(payload, expected_schedule, config, *, conditions_sha256, allow_incomplete=False) -> GameResult` と `GameRecord.from_payload(payload) -> GameRecord`。

**変更するインターフェース:** `_validate_and_replay(timings_value, schedule, config, comparison_position, record, *, allow_nonterminal=False) -> tuple[tuple[GameEndReason, Side | None] | None, tuple[MoveTiming, ...]]` のシグネチャを維持。新しい公開APIは作らない。

- [ ] 元分析セッション・プロセス・出力JSONを確認する。完了したらその終了状態と旧分析JSONを本筋として先に報告・保存確認する。元分析がエラーで終わった場合は本筋の原因確認を先に行い、原本を書き換えたり検証を迂回して最適化を進めたりしない。実装開始前のPythonソースを旧版 `0d8be5b` と照合し、性能比較用に `git archive 0d8be5b kaname_shogi` から一時ディレクトリへ旧ソースだけを展開する。
- [ ] `.venv/bin/python --version`、`.venv/bin/ruff --version` と固定版、`core.hooksPath=.githooks` を確認する。修復済み環境の既存851テスト成功は調査時の実績であり、実装後の検証に代用しない。
- [ ] 新規テストモジュールに局ケース用の非公開helperを置く。`_replay_case(moves: tuple[str, ...], *, max_plies: int, reason: GameEndReason, position: Position | None = None, winner_side: Side | None = None, candidate_side: Side = Side.GOTE) -> tuple[dict[str, object], ScheduledGame, ComparisonConfig]`。既存合法操作で棋譜を作り、計時は第k手に `11*k` ns、条件SHAは `"a" * 64`、初期手数1、baseline=material/candidate=material-rook-mobility。生の局payloadを組み立て、比較writerや採点関数から期待値を作らない。
- [ ] 下記の維持契約テストを旧コードで実行する。初回Greenはその事実を記録する。失敗したらfixtureの合法性と独立期待値を先に調べ、最適化コードをまだ書かない。

| テスト名 | fixtureと主要assertion |
| --- | --- |
| `test_rejects_illegal_intermediate_recorded_move_or_drop` | 合法3手payloadの2手目を、歩の二段移動 `3c3e`、または持ち駒なしの `P*5e` に各置換。`self.assertRaises(ValueError)`。タイミング側も同じUSIへ変え、別の計時不一致だけによる拒否に依存しない |
| `test_rejects_legal_continuation_after_ply_limit` | `7g7f 3c3d 2g2f`、上限2。`self.assertRaisesRegex(ValueError, "既終局後")` |
| 既存 `test_rejects_legal_moves_continuing_after_fifth_repetition` | 初期局面から `5i5h 5a5b 5h5i 5b5a` を4周後、`5i5h` を追加した17手。上限20で反復後継続を拒否 |
| `test_preserves_final_mate_or_no_move_before_ply_limit_for_both_sides` | 下記の末尾fixtureを先後反転して使用。`self.assertEqual(result.reason, expected_reason)`、`self.assertEqual(result.winner_side, expected_winner)`。上限1でもCHECKMATE/NO_LEGAL_MOVEを優先 |
| `test_preserves_incomplete_record_boundaries` | INTERRUPTED/ERRORそれぞれで0手・1手・合法3手、上限4。`allow_incomplete=True` では理由・手数・勝者Noneを保持、Falseでは拒否。3手・上限3の終局直後中断も理由はINTERRUPTED/ERRORのまま保持。0手のPLY_LIMIT完了記録は拒否 |

末尾fixtureは二つ用いる。詰みは既存readerテストの配置（後手玉5一、先手玉9九・飛5三・金4三、後手歩4一・6一・4二・6二）から `5c5b`、期待はCHECKMATE・先手勝ち。非王手の合法手なしは先手玉1一・歩2一/1二/2二、後手玉9八、後手番から `9h9i`、期待はNO_LEGAL_MOVE・後手勝ち。反転ケースは全駒の先後を交換し、筋/段を各 `10-元の値` に写す。期待勝者も反転し、候補方式への対応もassertする。

- [ ] `test_uses_validated_next_move_and_enumerates_only_final_position` を作成する。合法3手 `7g7f 3c3d 2g2f`・上限3を `_load_game` へ通し、reader内の `legal_moves` を実関数でwrapして呼出しと局面を記録する。主要期待値は `self.assertEqual(spy.call_count, 1)`、`self.assertEqual(result.reason, GameEndReason.PLY_LIMIT)`、`self.assertEqual(result.plies, 3)`、保存計時 `(11,22,33)`。調べた局面の手番はGOTE、先手歩は7六・2六、後手歩は3四にあることを直接assertする。
- [ ] `.venv/bin/python -m unittest discover -s tests -p 'test_comparison_result_replay.py' -v` を実行し、旧コードの直接列挙3回と期待1回のassertion差でRedになることを確認する。importやfixture作成失敗をRedと呼ばない。
- [ ] 最小実装する。`moves = record.moves` を一度取得し、その履歴長を使用する。毎手の計時確認・合法再生・反復判定を維持し、反復終局がなければ中間局面は根拠付きのTrue、末尾は現行全列挙の真偽を `board_terminal` へ渡す。未完了・0手・最終局面照合の分岐を維持する。関連docstringを設計に合わせる。
- [ ] 同じテスト群でGreenを確認する。中間列挙が減り、維持契約テストも成功したことを別々に記録する。
- [ ] `test_repeated_terminal_skips_direct_legal_enumeration` を追加する。上記の4周16手で末尾が反復終局なら、readerの直接列挙呼出し0回、理由REPETITION・勝者Noneをassertする。最適化後に追加する場合は初回Greenと記録する。
- [ ] `test_keeps_multimove_incomplete_games_pending_on_resume` を既存再開テストへ追加する。4局予定・共通上限4に、`7g7f 3c3d 2g2f 8c8d` の完成4手上限局、最初の3手のINTERRUPTED局、同じ3手のERROR局、欠落局を各一つ保存する。期待する完成ID集合は1件、再投入ID列は後者3件。保存済み完成局のバイト列保持もassertする。旧挙動維持なら初回Greenと記録する。
- [ ] 関連テストを実行する：`.venv/bin/python -m unittest discover -s tests -p 'test_comparison_result*.py' -v`、同様に `test_comparison_resume.py`、`test_analyze_comparison.py`、`test_compare_games.py`、`test_comparison_pipeline.py`。
- [ ] Refactor要否を確認する。今回の二分岐のために汎用キャッシュ・新しい公開型・全reader分割を追加しない。必要な最小整理と理由を記録する。

## タスク2：検出力・性能・全成果物の一致・独立レビュー

**消費:** タスク1の変更と同一の既存reader/analysis CLI。新しい製品インターフェースは作らない。

- [ ] 隔離コピーで代表変異を一つずつ入れる：(1)末尾も合法手あり固定、(2)中間の手数上限確認を省略、(3)反復終局確認を省略、(4)旧全列挙を毎手実行へ戻す。順に末尾fixture・上限後継続・反復後継続・直接列挙1回のテストが意図したassertionに失敗することを確認し、各復元後は成功を確認する。読込失敗は検出成功に含めない。
- [ ] import変更時は `.venv/bin/ruff check --select I --fix .`、続けて `.venv/bin/ruff format .`、`.venv/bin/ruff check .` と差分確認を行う。
- [ ] `.venv/bin/python scripts/run_tests_parallel.py` で全テストを実行する。テストを除外・skipせず、失敗や共有状態の疑いがある場合だけ標準逐次を併用する。
- [ ] 一時計測スクリプトを `/private/tmp/c1_analysis_witness_benchmark.py` に置く。旧ソースroot・新ソースroot・入力ディレクトリを引数で受け、各版を別Python subprocessの作業ディレクトリからimportする。入力JSONと条件を読み、計測区間は `_load_game` 呼出しだけとする。テスト用製品コードは追加しない。
- [ ] 固定6局（000129/001007/001501/002125/002745/003923）を4ラウンド測る。各ラウンドで両版を一回ずつ実行し、版の順序を旧→新、新→旧、旧→新、新→旧と交互にする。同じPython、同じ入力、同じ呼出し条件を使い、各局のwall/CPU時間・4回の中央値・6局合計を記録する。秒数を単体テストの合否条件にせず、短縮の再現性を確認する。
- [ ] 各代表局について、予定ID・開始SFEN・棋譜payload・理由・勝者先後/方式・手数・全計時・未確定計算/故障値が旧版と完全一致すること、入力SHAが計測前後で同じことを確認する。短縮しても不一致があれば受け入れない。
- [ ] 元分析の旧JSONが正常保存されていることを確認し、新版で同じ全4,080局を別の新規出力 `data/comparison/runs/c1-rook-mobility-confirmation-2026-10-25-analysis-legal-witness.json` へ分析する。既存出力は上書きしない。
- [ ] 旧/新の分析JSONから `analyzer` メタデータだけを除いた辞書が完全一致することをassertする。入力SHA一覧・件数・得点区間・判定・記述集計・比較時の計時がすべて比較対象になる。新版source/Git識別は変更されることを記録し、分析を独立した追加標本に数えない。
- [ ] `requesting-code-review` に従い独立レビューを行う。契約・代表ケース・検出する誤り・既存テストの補完・未検証を渡す。Critical/Importantを解消し、変更に見合う再検証・再レビュー後に記録を確定する。
- [ ] Refactorの判断、Red/初回Green/Green、変異結果、性能の生値、全成果物の一致、レビュー各重大度と対応を設計・本計画・調査/C1学習記録へ残す。知識・resume・索引の現在地を更新し、リンク・差分を検証する。
- [ ] 意図したコード・テスト・文書だけを通常コミットする。hookを回避しない。main統合は実装・検証・レビュー・記録を示し本人承認後に行い、統合先で検証する。

## セルフレビューと承認段階

設計の中間/末尾/反復/上限/未完了局はタスク1、統計と入力整合・性能・全成果物はタスク2に対応する。存在根拠の効率性を直接呼出し回数で検査し、速度と分析値の一致は別に測る。実装者が合理的に決めるのはfixture内の補助関数配置と、一時計測ログの形式だけで、受理条件・終局優先順位・対象範囲を変更しない。

現時点では計画作成・文書確認だけを行った。上のコマンドは承認後の実行手順であり、未作成テストや一時計測スクリプトを実行済みと扱わない。実装計画全体の本人承認を待つ。
