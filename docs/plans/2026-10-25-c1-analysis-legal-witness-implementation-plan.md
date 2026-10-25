# C1分析CLIの合法手存在確認を短縮する実装計画

> **AIエージェントへの指示:** 承認後、このセッションの担当者が `superpowerssuperpowers:executing-plans` と `superpowerssuperpowers:test-driven-development` を使用して順に実装する。各ステップのチェックボックスで実績を追跡する。2026-10-25、本人が実装計画全体を承認し、git worktreeでの実装を希望した。元の分析器が読む作業ディレクトリを保持し、別worktreeでTDDを開始する。

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
- 本人の追加希望に従い、`codex/c1-analysis-performance-investigation` の承認記録コミットを起点に別worktree・作業ブランチを作り、担当者が順に実装する。元の `/Users/oki2a24/kaname-shogi` のPythonソースは変更しない。実際の絶対パスとコマンドを作成後に案内する。
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

## タスク 1：合法な次の手を根拠にするreaderと契約検証

**消費するインターフェース:** 現行の `_load_game(payload, expected_schedule, config, *, conditions_sha256, allow_incomplete=False) -> GameResult` と `GameRecord.from_payload(payload) -> GameRecord`。

**変更するインターフェース:** `_validate_and_replay(timings_value, schedule, config, comparison_position, record, *, allow_nonterminal=False) -> tuple[tuple[GameEndReason, Side | None] | None, tuple[MoveTiming, ...]]` のシグネチャを維持。新しい公開APIは作らない。

- [x] 元分析session74980・PID84790の稼働と出力未作成を確認した。本人希望の別worktreeを作成し、元ディレクトリのPythonソースを変更せず先行実装した。worktreeの変更前Pythonソースは旧版 `0d8be5b` と一致し、`git archive 0d8be5b kaname_shogi` を性能比較用に展開した。
- [x] 元分析は本人端末から完了。CLIは4,080局・2,040組、95%得点区間 `[0.490, 0.606]`、判断不能を表示し、JSONを保存した。analysis JSON記録と条件・全4,080局・summaryのSHAを再照合し4,082件すべて一致。zshの `status` 代入エラーはCLI終了後の表示部分。
- [x] `.venv/bin/python --version`、`.venv/bin/ruff --version` と固定版、`core.hooksPath=.githooks` を確認した。worktree `.venv` はPython 3.15.1・固定版Ruff 0.16.10、shared hook `.githooks`。調査時の全851テスト成功とは別に、実装後テストを実行した。
- [x] 新規テストモジュールに計画どおりの局helperを置いた。合法操作で棋譜を作り、時刻・条件SHA・手番方式を構成し、独立期待値をreaderのwriter/採点出力から作らない。
- [x] 維持契約テストを旧コードで実行した。違法中間手/駒打ち、上限、先後反転した末尾終局、中断・error境界は初回Greenと記録した。

| テスト名 | fixtureと主要assertion |
| --- | --- |
| `test_rejects_illegal_intermediate_recorded_move_or_drop` | 合法3手payloadの2手目を、歩の二段移動 `3c3e`、または持ち駒なしの `P*5e` に各置換。`self.assertRaises(ValueError)`。タイミング側も同じUSIへ変え、別の計時不一致だけによる拒否に依存しない |
| `test_rejects_legal_continuation_after_ply_limit` | `7g7f 3c3d 2g2f`、上限2。`self.assertRaisesRegex(ValueError, "既終局後")` |
| 既存 `test_rejects_legal_moves_continuing_after_fifth_repetition` | 初期局面から `5i5h 5a5b 5h5i 5b5a` を4周後、`5i5h` を追加した17手。上限20で反復後継続を拒否 |
| `test_preserves_final_mate_or_no_move_before_ply_limit_for_both_sides` | 下記の末尾fixtureを先後反転して使用。`self.assertEqual(result.reason, expected_reason)`、`self.assertEqual(result.winner_side, expected_winner)`。上限1でもCHECKMATE/NO_LEGAL_MOVEを優先 |
| `test_preserves_incomplete_record_boundaries` | INTERRUPTED/ERRORそれぞれで0手・1手・合法3手、上限4。`allow_incomplete=True` では理由・手数・勝者Noneを保持、Falseでは拒否。3手・上限3の終局直後中断も理由はINTERRUPTED/ERRORのまま保持。0手のPLY_LIMIT完了記録は拒否 |

末尾fixtureは二つ用いる。詰みは既存readerテストの配置（後手玉5一、先手玉9九・飛5三・金4三、後手歩4一・6一・4二・6二）から `5c5b`、期待はCHECKMATE・先手勝ち。非王手の合法手なしは先手玉1一・歩2一/1二/2二、後手玉9八、後手番から `9h9i`、期待はNO_LEGAL_MOVE・後手勝ち。反転ケースは全駒の先後を交換し、筋/段を各 `10-元の値` に写す。期待勝者も反転し、候補方式への対応もassertする。

- [x] `test_uses_validated_next_move_and_enumerates_only_final_position` を作成した。旧コードはreaderの直接 `legal_moves` 3回で期待1回との差により意図したassertion Redを確認した。
- [x] 最小実装した。`moves = record.moves` と履歴長を一度取得し、毎手の計時・合法再生・反復・上限・後続手拒否を維持。反復終局なしの中間は根拠付きTrue、末尾のみ全列挙、未完了・0手・末尾照合も維持した。
- [x] 同じテスト群でGreenを確認した。3手例は直接列挙3回から1回へ、反復末尾は0回。維持契約テストも成功した。
- [x] `test_repeated_terminal_skips_direct_legal_enumeration` を追加し、16手反復終局のreader直接列挙0回、REPETITION・勝者なしを検査した。最適化後の初回Greenとして記録した。
- [x] `test_keeps_multimove_incomplete_games_pending_on_resume` を追加した。4手完成局を保持し、3手の中断・errorと欠落局の3局だけを再投入し、完成局JSONのバイト列保持を検査した。
- [x] 比較reader、再開、分析CLI、compare CLI、pipelineの関連88テストを実行し成功した。
- [x] Refactor要否を確認した。二分岐に対する汎用キャッシュ・公開型・reader分割は不要。変更は `moves` 参照の一本化と中間/末尾分岐、根拠のdocstringに限定した。

## タスク 2：検出力・性能・全成果物の一致・独立レビュー

**消費:** タスク1の変更と同一の既存reader/analysis CLI。新しい製品インターフェースは作らない。

- [x] 隔離コピーで4代表変異を一つずつ実施した。末尾固定は終局理由/勝者assertion、上限確認省略は `ValueError not raised`、反復終局変換省略は反復結果assertion、旧全列挙復帰は `3 != 1` の呼出し回数assertionで検出。importやfixture読込失敗ではない。
- [x] import変更後 `.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`、`.venv/bin/ruff check .`、format check（106ファイル）と差分確認を実行し成功した。
- [x] `.venv/bin/python scripts/run_tests_parallel.py` で全858件・57モジュールを22.525秒で実行し成功した。除外・skipなし。
- [x] 一時計測スクリプト `/private/tmp/c1_analysis_witness_benchmark.py` を作成した。旧/新rootは別Python subprocess、読込/JSON decode外、`_load_game` 呼出し内だけを計時した。製品CLI/APIは追加していない。
- [x] 固定6局を指定順で4ラウンド計測し、各局のwall/CPUの全4測定と中央値・6局中央値合計を記録した。単体テストに時間閾値は設けていない。
- [x] 6局ごとに予定ID・開始SFEN・棋譜・終局・勝者/方式・手数・全計時・未確定計算/故障値の検証済み結果signatureが旧新版で一致し、conditionsと代表局のSHAが計測前後で同じことを確認した。
- [x] 本人が新版readerで同じ全4,080局を未使用の別出力へ端末実行した。出力は `data/comparison/runs/c1-rook-mobility-confirmation-2026-10-25-analysis-legal-witness.json`、表示終了コード0、4080局・2040組。
- [x] 旧/新版分析JSONを比較し、`analyzer` だけを除いた全項目が一致した。条件・4,080局・summaryのSHA-256も計4,082件を実ファイルから再計算して全件一致。両JSONの得点区間・判定・集計・比較経過時間記録が同一で、source SHAだけが異なるanalyzerメタデータを独立標本として数えていない。
- [x] `requesting-code-review` に従って独立レビューを実施。初回Critical 0 / Important 0 / Minor 1のdocstring不整合を修正し、再確認後Critical 0 / Important 0 / Minor 0。検証範囲と未検証事項も提示した。
- [x] Refactorの判断、Red/初回Green/Green、変異結果、性能の生値、独立レビューと対応を設計・本計画・調査/C1学習記録へ記録した。知識・resume・索引の現在地も更新し、7文書のローカルMarkdownリンク709件と差分を検証した。
- [x] 全4,080局の旧新版分析JSONの一致結果を記録し、関連文書・索引・再開案内を更新した。
- [x] 最終の文書差分検査・Markdownローカルリンク770件（欠落0）を確認した。
- [ ] 意図したコード・テスト・文書だけを通常コミットする。hookを回避しない。main統合は実装・検証・レビュー・記録を示し本人承認後に行い、統合先で検証する。

## セルフレビューと承認段階

設計の中間/末尾/反復/上限/未完了局はタスク1、統計と入力整合・性能・全成果物はタスク2に対応する。存在根拠の効率性を直接呼出し回数で検査し、速度と分析値の一致は別に測る。実装者が合理的に決めるのはfixture内の補助関数配置と、一時計測ログの形式だけで、受理条件・終局優先順位・対象範囲を変更しない。

計画提示時点では文書確認だけを行い、上のコマンドを実行済みとは扱わなかった。その後、本人が計画全体を明示承認し、worktreeでの実装を希望した。作業場所変更は本人の追加指示として記録し、振る舞い・検証範囲は承認済み計画のまま実行する。

**2026-10-25 17:09 JSTの本筋状態確認：** 元分析PID84790とsession74980が確認できず、旧分析JSONも出力されていなかった。プロセス終了の原因・終了コードは不明であった。原本4,080局は保持され、summaryは完了・投入中0。

**2026-10-25 17:12 JSTの再実行：** 本人端末に終了ログがないため、旧ソースHEAD `14e7210` の元ディレクトリからCLIを再実行した。実行session29130は10秒後のpollで継続中、出力JSON未作成。原本4,080局は保持され、summaryは完了・投入中0。旧分析の成功保存後に全体旧新版照合を行う。

**2026-10-25 17:16 JSTの中止：** 本人は長時間実行を中止し、人間自身で端末から実行したいと指示した。対象PID3283へSIGINTを送り、session29130の出力「分析を中断しました。」と終了コード130を確認した。PID停止、旧分析JSON未作成も確認済み。次は本人の端末実行を待つ。

**本人端末での旧分析完了：** 4,080局・2,040組、区間 `[0.490274264295, 0.605804167078]`、判定`inconclusive`。analysis JSONに記録された条件・4,080局・summaryの全4,082 SHA-256が実ファイルと一致した。本人が人間端末実行を基本と希望したため、新版readerの分析CLIは次のコマンドで本人が実行する。

本人は新版readerの分析CLIを2026-10-25 22:00頃に端末から開始し、後日完了を報告した。出力JSON・入力SHA・旧新版の全項目一致を検証済み。CLI表示は4080局・2040組、終了コード0だった。
