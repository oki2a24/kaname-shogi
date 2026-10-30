# 駒の連携評価を通常CLI・USIへ接続する実装計画

> 実行時は、承認された方法に応じて superpowers:executing-plans または superpowers:subagent-driven-development を使用する。計画中の各手順は実績に応じてチェックする。

**目標:** 既存の一手選択方針を保ちながら、10M+Uを通常CLIとUSIで選択可能にする。通常CLIのコンピュータ対コンピュータでは先手・後手へ別の方針を割り当て、比較したい二方式を見分けやすくする。

**アーキテクチャ:** 既存の MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE と game_search.search_move の経路を再利用する。CLIの方針メニューに第6候補を加え、対局形式に応じて選択した方針をrun_gameへ渡す。run_gameは既存の単一方針引数を互換用に残し、新しい先後別方針が渡された場合だけ手番Sideで選択する。USIはDifficulty comboの通知値と既知値表を拡張し、現在の「最初のgoで局の方針を固定し、usinewgameで次局へ移る」責務を維持する。

**技術スタック:** READMEが指定するPython 3.14以上、標準ライブラリ unittest、既存のCLI・game_search・USI実装、requirements-dev.txtで固定されたRuff。

**仕様:** [本人承認済み設計案](../plans/2026-10-31-undefended-piece-normal-cli-usi-design.md)。本人は2026-10-31に設計全体を明示承認し、続けてこの実装計画全体とネイティブ実行を承認した。

**状態:** 本人が2026-10-31に計画全体とネイティブ実行を承認。Task 1 CLI選択、Task 2 USI option、実使用で発見した制御付き探索のU接続修正、先後を入れ替えたCVC 2局、利用文書更新、検出力確認、最終検証・独立レビューまで完了。関連155件/13.869秒、全体987件/75モジュール/22.468秒、Ruff、リンク818件確認が成功。現在は学習記録と知識メモを本人へ提示して内容確認を待ち、確認後の通常ブランチコミットへ進む段階。ShogiHome実対局はPCロック解除可能後の保留事項として残す。

## この計画で固定するインターフェースと表示

- CLIの候補番号は1 RANDOM、2 MATERIAL、3 TWO_PLY_MATERIAL、4 FOUR_PLY_FULL_WIDTH、5 FOUR_PLY_ALPHA_BETA、6 MATERIAL_UNDEFENDED_PIECE。第6候補の表示名は「一手駒得＋支えのない狙われた駒」。不正番号は7など候補外の値とし、エラー表示は1〜6に更新する。
- choose_move_selection_policy は既存の入力関数・表示関数引数を保ち、任意のSideをキーワードで受け取れるようにする。先後別メニューではプロンプトへ先手・後手を明示し、Side省略時は既存の一般表示を保つ。空入力は呼び出しごとに独立してRANDOM。
- __main__.main は人間対人間では方針を尋ねない。人間対コンピュータでは自動担当の後手だけを尋ね、CVCでは先手を選んでから後手を尋ねる。全選択後、run_gameを開始する前に各側の方式名を表示する。人間対コンピュータの先手表示は人間担当と示す。
- run_gameには Mapping[Side, MoveSelectionPolicy] | None の先後別引数 move_selection_policies を加える。既存の move_selection_policy 引数とそのRANDOM既定を保ち、先後別引数を省略した既存呼び出しは従来どおり単一方針を全コンピュータ側へ適用する。先後別引数を渡す呼び出しではその値を優先し、対局形式に必要な自動担当側を過不足なく含むか、時計作成・設定読込・初期盤面表示などの副作用より前に検証して、一局用に複製する。探索のたびに現在のposition.side_to_moveに対応する方針を _run_computer_turn へ渡す。
- USIの Difficulty combo に MaterialUndefendedPiece を追加し、大小文字を区別せず MATERIAL_UNDEFENDED_PIECE へ変換する。未知のoption名・値は現在どおり無視し、未設定時のRANDOM、プロセス中の設定保持、最初のgoからusinewgameまでの局内固定を変えない。
- 探索評価・重み・比較CLI・既定方式・USIの先後別設定は変更しない。ShogiHome実対局はPCをロック解除できる状態になるまで保留する。

## グローバル制約 (Global Constraints)

- 実作業先は /Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi、ブランチ codex/undefended-piece-evaluation。元の /Users/oki2a24/kaname-shogi を上書き・削除・clean/reset・切替しない。
- .agents/tasks/ と data/comparison/runs/ の現在の未追跡成果物、およびC2保護対象4件を変更・削除・ステージしない。
- この計画全体への明示承認前は、TDD、コード・テスト変更、テスト実行、通常CLIの受け入れ対局を始めない。承認後もShogiHome実対局は行わない。
- 実装は対象を通常CLI/USIの選択接続に限る。通常CLIのSFEN入出力、飛車可動性v2、玉安全度との合成、二手・四手への連携評価適用、比較専用モードの公開を加えない。
- README・確定知識・学習記録は日本語で更新する。公開関数のdocstringに引数・戻り値・副作用・前提と設計理由を反映し、テスト名は英語・説明は日本語とする。
- 変更前に .venv/bin/ruff --version と requirements-dev.txt の固定版を照合し、git config --local --get core.hooksPath が .githooks であることを確認する。不足時はREADME記載のローカルセットアップ手順を使い、グローバル設定や既存フックを変更しない。
- Python変更では import 整理、.venv/bin/ruff format .、.venv/bin/ruff check .、差分確認、関連テスト、全体テストを行う。テストのskip/filterで範囲を縮めない。
- 各振る舞いのRed理由をアサーションの失敗として確認する。読み込みエラーをRedと扱わない。Green後にRefactor要否を確認し、誤り注入を隔離コピーで実行する。
- Refactor要否確認後、コードとテストを独立レビューする。Critical・Important・Minorの結果と対応を学習記録へ残し、CriticalまたはImportantは再検証・再レビューして解消する。
- 実績と文書の内容を本人に提示して確認を得た後、通常のブランチコミットを行う。コミット前の学習記録確認を省略しない。main統合・pushはそれぞれ別途本人承認を得る。

## レビューフォーカス (Review Focus)

- 先後を入れ替えたとき方針も正しく入れ替わり、CVCで同じ方針を両側へ誤適用しないか。CLI側の単独テストで検出できること。
- 人間対人間は選択せず、人間対コンピュータは後手だけ、CVCは先手の次に後手を選ぶか。空入力の一方のRANDOMが他方へ漏れないか。
- 第6候補の番号・日本語名・内部enum・開始前の表示が一致し、無効入力7を再質問するか。
- USIが新しいDifficulty値をusiokより前に通知し、大小混在を含めて新enumへ対応づけるか。未設定Randomや未知値の保持を壊さないか。
- USIの局中変更は現在局へ早期適用されず、usinewgame後には反映されるか。先行するUSI lifetimeテストが検出する誤りと新値固有テストの役割を区別する。

## 実装前の準備

- [x] 作業ディレクトリ・ブランチ・差分を再確認し、保護対象の未追跡データが存在することを確認した。元の作業ディレクトリには触れていない。
- [x] Ruff 0.16.10がrequirements-dev.txtのruff==0.16.10と一致し、git config --local --get core.hooksPathが.githooksであることを確認した。
- [x] 変更前baselineを実行した。関連テスト105件・7.574秒、全体973件・75モジュール・21.894秒が成功した。出力は/private/tmp/kaname-undefended-cli-usi-focused-baseline.log と /private/tmp/kaname-undefended-cli-usi-full-baseline.log に保存した。

## Task 1: 通常CLIで方針を先後別に選び実際の手番へ渡す

**変更対象:** kaname_shogi/cli.py、kaname_shogi/__main__.py、tests/test_cli.py、tests/test_cli_entrypoint.py。

**テスト先行:**

1. MoveSelectionPolicyMenuTests.test_choose_move_selection_policy_maps_choices を拡張し、1〜5の既存対応を維持しながら6が MATERIAL_UNDEFENDED_PIECE になることと、新候補名を含む表示を確認する。
2. 空入力テストで、同じ選択関数を先手・後手として別々に呼び、両方が独立にRANDOMとなることを確認する。無効入力テストは現在新候補番号になった6から7へ変更し、エラー範囲1〜6と再質問を確認する。
3. test_main_prompts_sente_then_gote_for_computer_vs_computer を追加し、選択関数へのSide.SENTE、次にSide.GOTEの呼出し、両方の方式マップ、開始前の表示順を確認する。
4. test_main_selects_only_gote_for_human_vs_computer を追加し、後手だけ選択し、先手は人間と表示することを確認する。既存の人間対人間入口テストは方針選択を呼ばない契約を保つ。
5. GameplayTests.test_run_game_routes_distinct_policies_by_side を追加する。初期局面で先手の7七歩から7六、後手の3三歩から3四を返すmock探索を使い、探索引数が順に（先手、U）・（後手、Material）となることと、割当を逆にしたcaseも確認する。3回目の探索でKeyboardInterruptを発生させ、実対局を長時間化せずrun_gameの既存終了境界を通す。
6. test_run_game_rejects_incomplete_or_wrong_side_policy_mapping を追加し、CVCの後手欠落、人間対コンピュータへ人間側の先手を誤って割り当てるケースなどで、時計作成・設定読込・盤面表示・探索の前に明確なValueErrorとなることを確認する。新引数が未実装のbaselineでは、inspect.signatureの包含assertionを使って意図した振る舞いの失敗を出し、TypeErrorをRed理由にしない。
7. 既存の直接run_game呼出しに対する test_run_game_defaults_to_random_policy と test_run_game_passes_selected_policy_to_computer_turn を維持し、先後別引数を省いた互換動作を保つ。
8. tests/test_cli_entrypoint.pyの既存入口テストを更新し、選択回数・順序・run_game引数と開始前表示を検査する。実プロセスのHVC入口テストは後手メニュー・開始前表示・時計・盤面の順序を確認する。CVCの二回選択と表示は依存をmockした入口テストで確認し、テスト実行時に長時間のCVC対局を起動しない。

**Red:** 次を実行し、未実装機能に対する候補対応・Side付き選択・独立ルーティングのassertion failureを確認する。テスト読み込み失敗は不可。
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli.MoveSelectionPolicyMenuTests tests.test_cli.GameplayTests tests.test_cli_entrypoint -v

**実装:** cli.pyの選択関数に側別プロンプトと第6候補を追加する。run_gameの後方互換な単一方針引数を残し、先後別Mappingをコピー・検証して手番Sideで解決する。__main__.pyは対局形式に応じた順序で必要な方式だけを選択し、確定名を表示してから方針マップを渡す。公開一覧・docstring・表示文言を更新する。

**Green:** 上記の同じunittestコマンドを再実行し、候補6の対応、空入力、無効入力7、対局形式別質問、先後反転ルーティング、開始前表示、旧scalar呼出しの全assertionが成功する。

## Task 2: USI Difficultyから新候補を選べるようにする

**変更対象:** kaname_shogi/usi_engine.py、tests/test_usi_engine.py。

**テスト先行:**

1. test_answers_usi_with_difficulty_combo_before_usiok を更新し、MaterialUndefendedPiece がoption行にあり、引き続きusiokより前に出ることを確認する。
2. test_applies_material_undefended_piece_at_first_go を追加し、setoption name Difficulty value MaterialUndefendedPiece の後、最初のgoがMATERIAL_UNDEFENDED_PIECEを探索へ渡すことを確認する。
3. 新値を大小混在させた設定でも同じenumになることを確認する。既存case-insensitiveテストに新値を含めるか、新値固有のassertionを追加する。
4. test_material_undefended_piece_is_fixed_until_next_game を追加し、最初のgoでUを固定した後の局中Material変更が現在局の次goを変えず、usinewgame後の次局goではMaterialに変わることを確認する。
5. 有効なU設定後の未知Difficulty値・未知option名が設定Uを消さないことを、既存のinvalid/unknownテストにUを使ったケースで確認する。未設定ならRandomの既存既定を維持する。
6. 新しい値についての期待値は内部対応表をそのまま読み返して作らず、設計が指定したMaterialUndefendedPieceとMATERIAL_UNDEFENDED_PIECEの対応から独立に固定する。

**Red:** 次を実行し、option出力または新値の探索方針assertionが失敗することを確認する。
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine.UsiEngineFunctionTests.test_answers_usi_with_difficulty_combo_before_usiok -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine.UsiEngineFunctionTests.test_applies_material_undefended_piece_at_first_go -v

**実装:** usi_engine.pyのcombo応答に正確な表示値 MaterialUndefendedPiece を加え、casefold後の対応表を既存enumへ結ぶ。状態寿命・未知値処理・探索処理は既存の局内固定フローを再利用し、変更しない。

**Green:** 次を実行し、新値の通知、設定、大小混在、局内固定、次局適用、既定Random、未知値維持、および既存USI契約の全assertionが成功する。
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_usi_engine -v

## Task 1・2の実使用統合補足：制御付き探索へUを接続する

**発見経緯:** Task 3の通常CLIを起動し、先手MATERIAL・後手MATERIAL_UNDEFENDED_PIECEを選ぶと、表示と先手の着手は正常だったが、後手初回探索で `game_search._pruning_for` が新候補を未知方針として拒否した。既存の入口テストは探索関数をspyへ差し替えており、この経路漏れを検出しなかった。USIも同じ探索入口を共有するため、同様に実使用できない。

**追加対象:** `kaname_shogi/game_search.py`、`kaname_shogi/movegen.py`、`tests/test_game_search.py`、`tests/test_search_movegen.py`。

- [x] Red: adapter委譲・制御付き詰み採点・停止後破棄・先後合法手の各テストが、未実装箇所でAssertionErrorとなることを確認した。
- [x] 実装: game_searchからUだけを既存制御付き候補探索へ渡した。movegenの停止確認・予備手・完了候補抽選を保ち、10M+U評価と一手詰み優先を追加した。四手探索・時計・USI応答方式や他方針は変更していない。
- [x] Green: 追加4件、`tests.test_game_search` / `tests.test_search_movegen` 48件、未守備駒選択3件、全体986件/75モジュールが成功した。

**実行上の記録:** 1局目は先手MATERIAL・後手10M+Uで開始し、先手の初手 `3七歩→3六`、後手候補の選択表示まで確認した。後手の最初の探索は上記ValueErrorで異常終了したため終局していない。2局目は未実施。検出ログと正確な履歴は学習記録へ事後記録する。

## Task 3: 通常CLIの2局操作確認と利用文書を整える

**対象:** README.md、docs/knowledge/31-weak-move-selection.md、docs/knowledge/usi-engine-response.md、docs/learning/undefended-piece-coordination-evaluation.md、docs/plans/2026-10-31-undefended-piece-normal-cli-usi-design.md、docs/README.md、docs/resume.md、docs/next-topics.md。

- [x] READMEと知識メモに、CLIの6候補・先後別CVC選択・開始前の方式表示・空入力Random、USIのDifficulty値と設定寿命を反映した。10M+Uの一般的な棋力向上や既定採用を示していない。
- [x] 通常CLIでMaterial対10M+Uを2局行った。1局目は先手Material・後手10M+U、2局目は先手10M+U・後手Material。両局で開始前表示、両方の選択方式の実着手、終局を確認した。空入力の既定時計を使用し、各探索で表示された消費時間を合計して学習記録へ記した。全体の壁時計経過時間は計測していない。初回の経路エラーは事実と修正を記録し、修正後に2局を完了した。
- [x] これは操作・側別割当確認として記録し、2局の勝敗を棋力証明としていない。Materialと新候補は一手詰み優先経路も異なるためUの単独効果を分離しないこと、比較CLIの10M対10M+Uの結果とは証拠を分けた。
- [x] ShogiHome実対局はPCロック解除可能後の保留事項として記録した。今回接続・設定・対局・ログ採取はしていない。
- [x] 学習記録に本人の承認・希望、変更した契約、TDDのRed/Green、実測と未検証事項を記録し、docs/resume.md・docs/next-topics.md・docs/README.mdの現在地を更新した。代表変異、最終検証、独立レビュー結果も追記した。

## Task 4: 検出力点検、全体検証、独立レビュー、記録確認

- [x] 隔離コピーにCLI先後方針の同側固定変異を注入し、先後の両方を入れ替えたケースで方針引数assertion failureを確認した。正しい実装へ復元後にGreenを再実行し、コピーを破棄した。
- [x] 隔離コピーでUSI新値を既存MATERIALへ誤対応させ、新値選択のassertion failureを確認した。設定更新を毎go反映する変異も局内固定テストのassertion failureになった。誤りを戻した各コピーでGreenを確認して破棄した。設定ファイル不足などの試行エラーは成功証拠に数えていない。
- [x] 独立レビューの重要指摘を受けて、制御付きU評価の符号、先後視点、着手後局面を直接検査するテストを追加した。符号反転・視点反転・着手前局面を渡す3変異を隔離コピーへ注入して各assertion failureを確認し、復元後にGreenを再確認してコピーを破棄した。
- [x] 単独テストが検出した誤り、既存テストと実際のCLI 2局による補完、USI実機・GUI互換性や全局面が未検証であることを[学習記録](../learning/undefended-piece-coordination-evaluation.md)へ記録した。
- [x] Python変更に対して以下を実行し、関係する差分以外に整形変更がないことを確認した。Ruff cacheは選択worktreeの書込制限を避けるため `/private/tmp/kaname-undefended-ruff-cache-20261031` を使った。
  - .venv/bin/ruff check --select I --fix .
  - .venv/bin/ruff format .
  - .venv/bin/ruff check .
  - git diff --check
- [x] 関連回帰と全体テストを実行した。
  - `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m unittest tests.test_cli.MoveSelectionPolicyMenuTests tests.test_cli.GameplayTests tests.test_cli_entrypoint tests.test_game_search tests.test_search_movegen tests.test_usi_engine -v`: 155件・13.869秒
  - `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py`: 987件/75モジュール・22.468秒
  - 並列ランナーまたは共有状態の疑いがあれば、併せて python3 -m unittest discover -s tests -v を実行する。原因を確認せずテストを除外しない。
- [x] コード・テストを独立レビューした。初回Critical 0 / Important 1 / Minor 2、追補後にImportant 1、修正・再検証後の最終レビューはCritical 0 / Important 0 / Minor 0。指摘・対応とRefactorを行わなかった理由は学習記録にある。
- [x] 設計・実装計画・README・知識・学習・入口文書の相対リンク・見出し参照818件を確認し、欠落0件。現状の重複・矛盾も修正し、`git diff --check` を確認した。
- [ ] 本人へ学習記録と知識メモの内容を提示して確認を待つ。確認後、対象差分だけを通常コミットする。コミット準備で未追跡の比較成果物や `.agents/tasks/` を追加しない。

## このテーマの完了条件と別承認

通常CLI/USIの選択接続、契約ごとのテスト、指定された2局の操作観察またはその実際の中断理由、検出力点検、Ruff・全体テスト・独立レビュー、学習と現在地の記録が揃った時点でテーマ作業を完了扱いにする。元ディレクトリへの取り込み状態は確認するが、main統合は別途本人承認まで行わない。pushも別途本人承認まで行わない。ShogiHome実対局はPCを利用できる状態になった後、別途範囲と方法を相談する。
