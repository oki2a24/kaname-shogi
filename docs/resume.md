# 学習・開発の再開案内

## 現在地（2026-11-03、作業中）

### 期限付きの比較CLI性能目標（承認済み・実行中）

本人の明示承認を2026-11-03 12:16:27 JSTに受領し、同時刻に8時間の作業期限を開始した。終了予定は20:16:27 JST。承認待ち12:08:38〜12:16:27（7分49秒）は除外する。作業ブランチは `codex/comparison-cli-performance`、開始HEADは `aa70d1d`。開始環境はPython 3.15.2、Ruff 0.16.10、hooksPath `.githooks`。既存全量summaryは `elapsed_lower_bound=true` のため正確なwall基準にはしない。B0 fresh42局baselineは外部wall730.49秒・元棋譜完全一致。B1の14局cProfileは1,549手・14/14一致で、`is_square_attacked`の反復scanと候補生成が大きい処理と確認。初回B2の458.47秒はSquare cacheに玉`Piece`生成ホイストが混在したため合わせ技候補値。独立レビューでCriticalなし、Important 1件（計測交絡）、Minor 1件（`is_in_check` testが早期returnでscan再生成を見逃す可能性）。是正としてPiece生成頻度を従来へ戻し、末尾攻撃元の王手scan testを補強。関連216 test・Ruff成功、旧scan変異は意図どおり失敗。Square-only fresh42局はwall500.30秒、summary499.759秒、42/42棋譜・合法再生一致。B2a Piece生成ホイスト単独版は492.66秒、Square-only比1.53%短縮で事前基準未達により棄却し、コードはSquare-only版に戻した。B2の独立再レビューはCritical/Important/Minorなしで完了し、Square-only変更・test・記録をcommit `8b510a99`として作業ブランチへ保存済み。次はprofileで156,972,383回/1,106秒だった候補一覧生成を避けるB3直接target判定仮説をテスト先行で検証する。Square-only 42局の9.205 moves/secに対し、全量平均の手数で30分達成には約32.03倍の追加速度が必要という粗い試算はGOALに記録した。製品コード/testはSquare cacheと補強testのみ。[GOAL](../GOAL.md)、[承認済み設計](plans/2026-11-03-comparison-cli-performance-design.md)、[承認済み実装計画](plans/2026-11-03-comparison-cli-performance-implementation-plan.md)、[実験記録](learning/comparison-cli-performance.md)を参照する。

主線「次の非駒得評価項目を一つ選び、学ぶ」は未完了で、具体項目も未選定。支えのない被攻撃駒の価値合計比較は指定7局面・2037組/4074局で改善を支持し、main統合・push・統合後検証・最後の理解確認まで完了したが、一般棋力向上は示さない。

本人承認を受け、比較済みの `10M+U価値合計+V` を通常CLI候補8・USI `MaterialUndefendedPieceValuePlusV` に接続する実装を完了した。U枚数とU価値合計の名前を区別し、比較CLI ID `material-piece-threat-value-v1` は比較専用のままにした。1,073テスト・92モジュール、Ruff、代表変異、独立レビュー、通常CLIの先後を入れ替えたCVC 2局を確認し、2026-11-03に `d9a9d8e` としてmainへ統合・pushした。統合後も1,073テスト・92モジュールが成功した。詳細は[学習記録](learning/undefended-piece-coordination-evaluation.md)、[設計](plans/2026-11-03-undefended-piece-value-normal-cli-usi-design.md)、[実装計画](plans/2026-11-03-undefended-piece-value-normal-cli-usi-implementation-plan.md)。

ShogiHome 1.28.2で `MaterialUndefendedPieceValuePlusV` を一局選択・保存し、盤面上で42手分の応答を観察した。盤上入力が反映されなくなったため先手投了で終了し、棋譜は `/Users/oki2a24/Documents/20261103_101001_人_kaname-shogi.kif` に自動保存された。指定されたSID 8のUSI行を照合したが、最初の検索では許可外行も表示されたため、その行を使用しない逸脱を記録した。次候補 `MaterialUndefendedPieceCountPlusV` については一度停止判断があった後、本人の「変更して続行」の指示と設定変更承認を受けて一局実施した。Difficultyを同名に変更・保存し再表示で確認。人間先手・エンジン後手、平手、双方10分＋30秒・加算なしの局で、画面上15回のエンジン応答後に盤上入力が反映されなくなり、先手投了で終了した。棋譜は `/Users/oki2a24/Documents/20261103_104906_人_kaname-shogi.kif` に自動保存され、投了後にSID 12が監視一覧から消え、USI/CSA稼働数0を確認した。この二局目のUSIログは閲覧していない。いずれも完局・方式比較ではなく、棋力や息子が感じる差は不明。`MaterialUndefendedPieceCount` の新しい明示名は未選択だが、同じU枚数動作は旧名で実機確認済み。

2026-11-03の文書整理開始時、基点は `/Users/oki2a24/kaname-shogi` の `main` と `origin/main` が一致する `d9a9d8e38b9276492833cf03a01abfeef2dfff2b` で、追跡ファイルに差分はなかった。文書更新は同じcheckout内の `codex/session-start-cleanup-gate` で行っている。保全整理の期限と手順は[期限付き整理の引き継ぎ](handover-residual-artifact-cleanup.md)を参照し、セッション開始時にAsia/Tokyoの日付で次の判定日を確認する。比較データの保管先は本人が2027-02-01頃に決める。`.antigravity/tasks/`、未追跡比較データ、C2保護4件、`migration-preservation-2026-11-01/`、`worktree-preservation-2026-11-01/` は保持する。主線「次の非駒得評価項目を一つ選び、学ぶ」は未完了で、具体項目も未選定のまま維持する。

### 次の具体的な行動

1. 期限付き整理の引き継ぎに従い、2026-12-03以降に現行Git状態と二つの保全アーカイブを読み取り専用で再確認する。検証後30日間は削除せず、保護解除と重複確認後に限って整理する。
2. 2027-02-01以降、本人と比較データの保管先を決め、seed・conditions・summary・analysis・学習記録の参照とコピーを照合する。条件を満たすまで未追跡データを移動・削除しない。
3. `MaterialUndefendedPieceCountPlusV` のShogiHome実践は15回の後手応答後、盤上操作不調により投了で終了した。USIログ照合は未実施。完局・方式比較・棋力判断とは扱わない。詳細は前段と学習記録を参照する。
4. 次の非駒得評価項目を選ぶ主線は未完了として保持する。

### 作業場所の整理と前テーマの履歴

2026-11-01、本人は今後ワークツリーを使用しない方針を再確認した。既存9件の調査後、本人承認を得て、変更のない `main` 使用中の一時ワークツリーを削除した。その後、不要と確認した3件、および必要な記録を取り込み全体を退避・照合した4件を削除した。第55回の未コミット学習記録は履歴として取り込んだ。最後の1件はC2保護4件と `.agents/tasks/` を含んでいたため全体を未追跡 `worktree-preservation-2026-11-01/` に退避・照合し、本人が元worktreeの削除を明示承認した後に削除した。Git一覧上、追加worktreeは残っていない。

作業は `/Users/oki2a24/kaname-shogi` だけで行い、開発は同じディレクトリ内の作業ブランチで行う。別worktreeや別cloneは使用しない。再開時は[作業場所と知識メモの継続点検](documentation-guide.md#作業場所と知識メモの継続点検)を適用し、Git状態と仮想環境のPython本体を確認する。

2026-11-01、本人の希望により主線の作業先を `/Users/oki2a24/kaname-shogi` へ戻した。移行直後の作業branchは `codex/next-non-material-evaluation-item`。元のC1作業の変更文書3件と、同名衝突する未追跡文書3件は内容照合後、元ディレクトリ内の未追跡 `migration-preservation-2026-11-01/original-documents.tar` と差分patchに退避した。元branch `codex/c1-analysis-performance-investigation` も保持する。既存の比較データとC2保護4件は保持し、本人の許可を得て追跡済みC2比較成果物23件を展開した。飛車可動性・玉安全度・Uの知識メモは現行の接続と比較結果に合わせて修正した。具体的な次の評価項目は未選定のままである。移行経緯と文書レビューは[整理記録](learning/workspace-knowledge-consolidation.md)にある。過去の引き継ぎにある作業先は作成時点の情報である。

V比較CLI接続・予備比較・確認比較・分析を完了し、本人承認後にmainへ統合した。確認比較は事前固定6局面・一手選択・指定条件の範囲で改善を支持したが、一般局面の棋力向上を示さない。通常CLI・USI接続の設計案・実装計画は本人が全体承認し、実装も承認した。V1は通常CLI候補7とUSI `MaterialSupportedPieceThreat` に接続済み。通常CLI CVCは先後を入れ替えた2局を既定の10分・30秒で完局し、開始表示・両側の実着手・終局を確認した。詳細は[設計](plans/2026-11-01-v-normal-cli-usi-design.md)、[実装計画](plans/2026-11-01-v-normal-cli-usi-implementation-plan.md)、[学習記録](learning/supported-piece-lower-value-threat.md)にある。

前テーマの作業・統合先は標準clone `/private/tmp/kaname-shogi-main-integration-clone` だった。本人確認後にtopic branchへ実装コミット `2f49b186ba9b775bebaa4da79381feb721b28b50`を作成し、明示承認後にclone内の`main`をfast-forwardしてGitHubへpushした。統合記録コミット `86e98980`もpush済みで、この最終理解確認の記録更新開始時点ではローカル`main`とGitHub `main`が一致していた。全体1039件/84モジュール、Ruff、差分検査、レビューが成功。cloneの`origin`は元checkoutを指し`origin/main`が古いため、GitHubの実先端とは区別する。開始時の物理状態は[引き継ぎ](handover-v-normal-cli-usi-connection.md)を参照。

前テーマの確認比較は別の6局面・2040組/4080局・`--workers 4` で完了し、候補平均得点の95% Hoeffding区間[0.505225, 0.567569]から、固定した条件下で改善を支持した。一般局面の棋力向上は示さない。結果と本人回答は[学習記録](learning/supported-piece-lower-value-threat.md)に記録した。統合先テストは1031件・84モジュール・25.565秒で成功し、後続の文書コミットはhookと差分・リンク検査を通過した。

前テーマ実施時は、元の `/Users/oki2a24/kaname-shogi` と保護指定 `.agents/tasks/`、`data/comparison/runs/`、C2保護4件を変更しなかった。現在の移行状態は冒頭に記す。

Vの通常CLI・USI接続は実装・検証・独立レビュー・main統合・pushと最後の理解確認まで完了した。本人はCVCの印象として「前のエンジンと同等に見える」と答えたが、2局から棋力の同等性は判定できない。固定6局面比較は指定条件下で改善を支持する一方、一般局面での棋力向上は示さない。

本人は2026-11-01、次の非駒得評価項目を一つ選び学ぶ主線を採用した。これは主線テーマの選択であり、具体的な評価項目は未選定。候補の現行評価との重複・独立期待値・確認可能性を照合し、本人が一項目を選ぶところから新セッションで再開する。設計・実装計画・TDD・コード・テスト変更は未着手・未承認である。詳細と再開プロンプトは[新しい引き継ぎ](handover-mainline-next-evaluation-item.md)に記録した。ShogiHomeでのU実践も、遠隔PCへアクセス可能との本人連絡後に再提案する保留目標として残る。

引き継ぎ作成時のbranchは `codex/next-non-material-evaluation-item`、当時の作業先は標準clone `/private/tmp/kaname-shogi-main-integration-clone`。基点は `9cad36da20c8fed785bcda8bf4501f96d3aecc95`。文書のみのbranchで、GitHubへpushしていない。当時のcloneの `origin` は元checkoutを指し、その `origin/main` は古かった。引き継ぎ作成時は元の `/Users/oki2a24/kaname-shogi` と保護対象を変更していなかった。

### B2統合時点の実績（履歴・2026-10-28）

B2は承認済み4Taskの実装、検証、Task別・最終独立レビューを終え、2026-10-28にmainへ統合してorigin/mainへpush済み。統合先では全928テスト・62モジュールが25.003秒で成功し、Ruff整形確認・lint・差分検査も成功した。統合前の初回実行は統合用worktreeに `.venv` がなくUSI起動テスト3件が失敗したが、既存環境への一時リンクで8件を再確認してから全体テストを通した。詳細は[B2学習記録](learning/king-safety-design.md)、[確定知識](knowledge/king-safety-evaluation.md)、[承認済み設計](plans/2026-10-28-king-safety-design.md)、[実装計画と実績](plans/2026-10-28-king-safety-implementation-plan.md)を参照する。

### C2作業時点の環境・Git状態（履歴・2026-10-28）

C2作業対象は `/Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi`。開始時は `main` と `origin/main` が同期した `cdd46519` でcleanだった。実装・検証・レビューは作業ブランチ `codex/c2-king-safety-evaluation` で行い、最終全体テストは943件・67モジュールが25.382秒で成功した。別worktreeではREADMEのセットアップスクリプトが対象外として停止したため、専用仮想環境を作り固定版Ruff 0.16.10とhook `.githooks` を確認した。製品変更前baselineは928件・62モジュールが23.349秒で成功した。これらは当時の記録であり、現在のブランチ・状態・検証は冒頭の現在地と[C2後の統合記録](learning/c2-king-safety-evaluation.md)を参照する。当時は元の `/Users/oki2a24/kaname-shogi` の未コミット文書・比較データを保持するため、clean/reset/切替を行わず保護していた。B2後の本人回答「少なくとも先手玉の周囲に後手の利きが２つ以上ある状態」と、S=-2が表す差ちょうど2の補足は[学習記録](learning/king-safety-design.md)に記録済み。通常CLIのSFEN入出力と飛車可動性バージョン2は保留し、C2へ自動追加しない。

## C1開始前の状態（履歴）

2026-10-24、主線A1「駒得以外の局面評価を一項目から学び設計する」の飛車可動性について、本人承認済み計画に従うB1実装・検証・記録を作業ブランチで完了し、本人承認後にローカルmainへ統合した。未成飛車の可動性差、名前付き重みによる駒得との合成評価、評価関数を差し替えられる一手選択を個別ファイルへ追加した。詳細は[学習・本人回答・実装・検証記録](learning/rook-mobility-design.md)、[確定知識](knowledge/rook-mobility-evaluation.md)、[承認済み設計](plans/2026-10-24-rook-mobility-design.md)、[実装計画と実績](plans/2026-10-24-rook-mobility-implementation-plan.md)を参照する。

当時の作業場所は `/Users/oki2a24/kaname-shogi`、当時の作業ブランチは `main`。C1引き継ぎ開始時のGit状態と未追跡の保持物は[C1引き継ぎ](handover-c1-rook-mobility-evaluation.md)を参照する。実装コミットは `8f39c9b`、`e9a3d45`、`bc6651b`、統合時点は `06453c9`。統合先で全体テスト729件・48モジュールが14.634秒で成功し、Ruff（90ファイル変更なし）・差分検査・文書リンク790件/アンカー5件（欠落0）も成功した。代表変異7件は意図したassertion failureですべて検出済み。独立コードレビューはCritical 0 / Important 0 / Minor 1、最終文書レビューはCritical 0 / Important 0で追加指摘なし。Minorは異なる手種の兄弟枝を混在させた相互干渉の直接検査がない範囲上の残件として学習記録に残した。pushはしていない。未追跡 `.antigravity/tasks/` と `.venv.backup-2026-10-22/` は保持している。

A1の学習・設計、B1の実装・main統合・統合先検証、最後の理解確認と回答記録まで完了した。本人は次の主線目標C1「飛車可動性を接続して比較評価する」を選定済み。C1の学習・調査・設計はまだ始めておらず、新セッション開始待ちである。接続先、比較条件、判定方法は未決定で、選定は実装承認ではない。再開時は[C1引き継ぎ](handover-c1-rook-mobility-evaluation.md)のプロンプトから始める。 引き継ぎ準備では更新した6文書の相対Markdownリンク792件が欠落0件、`git diff --check`が成功した。文書のみの変更のため製品テストは再実行していない。通常CLIのSFEN入出力と「可動性バージョン2」は別候補として[next-topics](next-topics.md)へ保持する。P2以前の記述は履歴であり、現在の段階は本節と学習記録を正本とする。

## A1開始時の背景（2026-10-23、履歴）

2026-10-22、P1「比較方法と比較用CLIを学び設計する」は設計承認・最後の理解確認・回答記録まで完了済み。[P1学習記録](learning/engine-comparison-design.md)と[承認済み比較設計](plans/2026-10-21-engine-comparison-design.md)を参照する。補助テーマ「千日手ルールを学び設計する」は一次資料・現行コード・将棋ソフト実装を確認し、本人回答と判断理由を[学習記録](learning/repetition-rule-design.md)へ保存した。設計案・実装計画の明示承認を受け、Task 1〜5を作業ブランチ `codex/repetition-rule` で実装・検証・レビュー・記録し、`4080c4a` としてコミットした。本人承認後、`1b69147` からローカルmainへfast-forwardし、統合先 `7985cb9` で全体661件・42モジュール（15.034秒）、Ruff整形確認78ファイル・check、差分検査が成功した。最終独立レビューはCritical 0 / Important 0 / Minor 2（Deferred）。

最後の理解確認と回答記録まで完了した。[千日手テーマの学習記録](learning/repetition-rule-design.md)を参照。本人は2026-10-23にP2比較CLI実装計画全体と、双方連続王手の未裁定を独立結果・集計件数にする仕様調整を「承認する」と明示した。承認済み計画に従って実装し、独立レビュー・修正・全体検証後、別途本人承認を受けてローカルmainへ統合し、統合先検証と最後の理解確認まで完了した。最終独立レビューはCritical 0 / Important 0 / Minor 0。本人はP2完了後に主線の最初の評価項目A1へ戻ると指定した。通常CLIのSFEN入出力は将来の別候補として保持し、P2へ含めない。P2の詳細は[計画・実績](plans/2026-10-22-comparison-cli-implementation-plan.md)と[学習記録](learning/engine-comparison-design.md)、A1の再開背景は[引き継ぎ](handover-a1-non-material-position-evaluation.md)を参照する。

## 今回開始前の背景（2026-10-21時点）

テーマ「ShogiHomeで全幅最大4手とαβ最大4手を実践検証する」は、合意した二局の観察と最後の理解確認まで完了した。実測・証拠・限界と本人の振り返りは[学習記録](learning/shogihome-four-ply-practice-verification.md)にある。元の主線に未完了の帰還目標はない。CLI時計の設計・実装と予定していた観察も派生した補助テーマとして完了した。

本人は次の大テーマ「駒得以外の局面評価を一項目から学び設計する」を選定した。テーマ内で非駒得評価の一項目を選び、学習・設計するところから始める。評価要素、具体設計、実装範囲は未決であり、テーマ選定を設計承認・実装承認と扱わない。今回開始時の背景・再開プロンプトは[引き継ぎ](handover-non-material-position-evaluation.md)、主線と任意候補は[学習ロードマップ](next-topics.md)を参照する。本人の序盤テンポに関する改善仮説は別の任意候補であり、今回の範囲に含めない。

本人の承認を受け、Pythonユニットテストの並列実行を実装・記録したブランチ `codex/parallel-unittest-runner` を2026-10-21にmainへfast-forward統合した（統合先コミット `c89128a`）。統合後に `PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_tests_parallel.py` を実行し、637件・41モジュールが19.843秒で成功した。並列実行は未統合ブランチで別途3回、標準逐次は1回検証済み。READMEに人間向け手順、AGENTS.mdにAI作業者向け通常コマンド・逐次診断条件を記載済み。最後の理解確認では、逐次実行を残す理由として本人が「問題発生時の切り分けのため」と回答し、補足とともに[学習記録](learning/python-unittest-parallel-runner.md)へ記録した。実装・レビュー・各コミットの経緯は同学習記録と[実装計画](plans/2026-10-21-parallel-unittest-runner-implementation-plan.md)にある。main側の未追跡 `.antigravity/tasks/TODO-codex-controlled-iterative-search-command.md` は保持した。

## 以前に完了した観察テーマ（時間制御付き探索コマンド）

前テーマではREADME記載の小さいSFENで開発用コマンドを一回実行し、理解確認まで完了した。[学習記録](learning/controlled-iterative-search-command-output-reading.md)に実出力・終了コード・本人の回答と補足を保存した。

実行条件は`--max-depth 4 --target-ms 50 --maximum-ms 100`。終了コード0、状態`STOPPED（通常停止）`、選択手`9i9h`は完了結果由来、完了記録は深さ2・評価＋0・訪問9・完了深さまでの累計13だった。出力から目標50msと上限100msのどちらが停止判断の原因かは特定できず、経過時間も表示されなかった。上限msは実応答時間の保証ではない。製品コード・テストの変更はなく、テストも実行していない。

## 完了した開発用コマンド設計

学習・設計・独立レビュー・本人による[設計全体](plans/2026-10-18-controlled-iterative-search-command-design.md)の明示承認と、最後の理解確認まで完了。[学習記録](learning/controlled-iterative-search-command-design.md)に個別選択・承認・レビュー・初回誤答と再確認正解を区別して保存した。設計承認0e5ea66、理解確認/候補8d29088。独立レビューの初回Minor 1は記録更新で解消、最終Critical/Important/Minorすべて0。

専用コマンドで一回探索。SFEN・上限深さ・目標/上限msは必須。操作セット生成後の探索直前から計時し、探索内部の合法予備手準備を含む。Task 1〜5として入力検査、一回探索接続、四状態表示、`main`・例外境界・実プロセス入口、全体検証を完了。最終専用テスト14/14、関連68/68、全体560/560、Ruff成功。代表変異8件と最終独立ブランチレビューCritical 0 / Important 0 / Minor 0。既存三方式と比較入口を維持し、通常対局・USIへの新方式接続、予算式変更、時間保証は対象外。

計画作成時点では製品テスト未実行だった。その後の実装テスト結果は上記Task 1〜5の今回実測に限る。過去の探索部品546件成功などを今回の実測とは扱わない。実時間性能・期限内応答、SIGINT実プロセス配送、USI競合、全局面/OS、棋力などは未検証。

## 完了した前テーマ

時間制御付き反復深化の計画承認、5段階の実装・検証・各段階と全体の独立レビュー、本人の別承認によるmain統合、取り込み先検証、最後の理解確認まで完了した。[実装計画と結果](plans/2026-10-18-iterative-deepening-stop-time-control-implementation-plan.md)、[学習・実施・本人回答](learning/iterative-deepening-stop-time-control-implementation.md)を参照する。

実装5コミットはca59b63・8d4ced6・73a0264・db31d03・30fe837、最終記録80e3db0まで統合、統合記録04de2ae、回答補足0be1c7a、理解確認と次候補605b0a3。最後の理解確認は初回の抑制時の手の扱いを補足し、再確認回答を記録して完了した。

直近の製品検証は取り込み先80e3db0で全体546件30.083秒OK、Ruff63ファイル整形確認・check、差分検査成功。代表変異11件と独立全体レビューは取り込み前の実績（最終Critical/Important/Minor 0/0/0）。これらを新セッションの実測として流用しない。以降は文書変更だけで、製品テストは再実行していない。過去の設計と反復深化補強の履歴は学習記録と各開始時引き継ぎからたどる。

## A1開始前に指定した再開手順（履歴）

P2実装コミット `3adbd23` は、本人の別途承認を受け2026-10-23に `e595f8e` からローカルmainへfast-forward統合した。統合先で `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py` が705件・45モジュール（14.548秒）成功し、Ruff整形確認84ファイル・check、`git diff --check` も成功した。pushはしていない。最後の理解確認では、本人が「4回目で千日手ではあるが、続行も可能なため、5回目で終了とするため」と回答し、補足とともに[学習記録](learning/engine-comparison-design.md)へ保存した。本人はP2の後に戻る主線目標をA1と指定済みである。次の新セッションは[A1引き継ぎ](handover-a1-non-material-position-evaluation.md)のプロンプトから始める。引き継ぎ準備開始時の状態は `main`、HEAD `c4cd68b`、`origin/main` より7コミット先行で、既存未追跡 `.antigravity/tasks/` と `.venv.backup-2026-10-22/` を保持していた。再開時にGit状態を再確認する。
