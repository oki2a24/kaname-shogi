# 引き継ぎ：駒の連携評価を通常CLI・USIへ接続する

## 最終目標

主線「駒得以外の局面評価を一項目ずつ育てる」の駒の連携評価について、本人が次テーマとして選んだ「通常対局CLIとUSIから `10M+U` を選択できるように接続する」方向を、brainstormingで具体化する。選択可能な候補として試す方向は選定済みだが、利用者向けの表現、選択方法、既定値、設定寿命、確認方法、実装計画は未決定・未承認である。ShogiHome実践は前回の候補説明で「必要なら設計」としただけで、今回の選択に必須と確定した範囲ではない。必要性と対象範囲を次セッションで本人と決める。

次セッションの完了条件は、現物のGit状態と文書・CLI/USIの現在契約を再確認し、対象範囲・利用者向け表現・確認方法を明示した設計と実装計画を提示すること。本人が明示承認するまではコード・テストを変更しない。テーマ選定は実装、既定方式の変更、main統合、pushの承認ではない。

## 選択と背景

2026-10-31、前回の確認比較後の次テーマ候補1「このU評価を通常CLI/USIへ接続し、必要ならShogiHome実践を設計する」を本人が選んだ。選択直前に本人は、今回初めて比較で改善が支持されたため通常CLIとUSIへ接続する理解でよいか確認した。説明では、支持は指定5局面・比較条件に限られ、一般的な棋力向上を示さないこと、通常CLI/USIでは既定化ではなく選択可能な候補として試す設計を考える段階であることを明確にした。その理解の後に本人が「1を選択する」と回答した。この選択理由はここに記した理解の範囲であり、それ以上の動機は推測しない。

元の駒の連携評価テーマを選んだ理由は別の判断で、本人から聞いていない。混同しない。

## 完了した前段と判断材料

### 駒の連携評価の定義・実装

相手の利きがあり、味方の支えがない盤上の非玉駒を一枚単位で数える。既定の合成評価は `E = 10 × M + U`。本人はB段階最後の理解確認に「E=10M+U」と正答し、記録済み。評価部品と一手選択器への注入は実装・検証・レビュー・ローカルmain統合まで完了した。

### 前回の比較CLI評価

本人は比較先として通常CLI/USIではなく比較CLIを選び、基準 `material-undefended-piece-material-only`（M=10, U=0）と候補 `material-undefended-piece`（M=10, U=1）を比較する設計・計画を明示承認した。両方で同じ一手選択器と一手詰み優先を使い、差をUの重みに限った。通常CLI/USI接続、ShogiHome実践、SFEN入出力、飛車可動性v2、玉周辺安全度との合成、二手・四手適用は前回の比較範囲に含めていない。

- 5登録局面を均等に扱い、各局面で先後を交換した一組を単位にした。
- 各局1024手上限。対局比較CLIは `--workers 4`。
- pilotは別seed50組・100局、候補92勝8敗、平均0.920、95%区間 `[0.727935, 1.000000]`。探索的でありconfirmationへ合算していない。
- 独立confirmationは別seed2035組・4070局、候補3699勝371敗。4050局は詰み、20局は合法手なしで終了。エラー・千日手等は0。
- confirmation平均得点 `0.9088452088452088`、paired Hoeffdingの95%区間 `[0.8787394188998447, 0.9389509987905729]`。分析CLIは指定条件下で「改善を支持」と判定した。
- この結果は指定5局面・指定条件に対する10M対10M+Uの証拠で、一般的な棋力向上、全局面での優位、採用の妥当性を確定しない。

| 実験 | 組数・局数 | 保存先 | seed一覧SHA-256 | summary SHA-256 | analysis SHA-256 |
| --- | ---: | --- | --- | --- | --- |
| pilot | 50組・100局 | `data/comparison/runs/undefended-piece-evaluation-pilot-2026-10-30/` | `7d933f2b800f8ae3275419bba49d706cf65a77e7c0b866b8d6355a36d5d785ac` | `d018ff00f73bab4e988839c38c7ccaa479f9a95d9eb80fb6308dddc3f472e1e7` | `49a1b6cef29cdb5a2f1c3b8d0507ebf07c65e34cf2874a5672c3ec98a02f8939` |
| confirmation | 2035組・4070局 | `data/comparison/runs/undefended-piece-evaluation-confirmation-2026-10-30/` | `5ff463f7dd82fc23246f2b5f4a6722d9398495e5a4bed5f18e178b2662c123d8` | `19f81014219bb21594e63f654d03ea1723a59dd05719138a8bc2545f54481ef0` | `448d442bcc4d17a383737227a32be594a7fdfa5b0180de989d70d1ddfae590bc` |

pilotのsummary `elapsed_ns=877773198625`（約14分38秒）は探索的な実測である。confirmationは停止前の時間を復元できず、summaryの `elapsed_lower_bound=true`、`elapsed_ns=39072091809958`（少なくとも約10時間51分12秒）を総時間ではなく下限として記録した。confirmationの局面別平均得点は初期局面0.945946、歩2枚とも非支持0.933661、歩2枚とも支持0.862408、先手が狙われる0.902948、後手が狙われる0.899263。
- confirmationは一度停止し、同じseed・条件・出力先で `--resume` した。summaryのelapsedは下限値である。
- 分析CLIのhelpにworker指定はないため分析に `--workers` は付けていない。以後、並列指定が存在するCLIで長時間比較を承認された場合は `--workers 4` を基本とし、アシスタントが実行する。進捗はおおむね一時間ごとに確認し、質問を受けた際は実状態を調べる。

最終理解確認で本人は「b」と回答し、指定範囲での支持と一般的な棋力向上を区別する補足を学習記録に保存した。

## 現在の物理的状態

- 作業worktree：`/Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi`
- 作業ブランチ：`codex/undefended-piece-evaluation`
- 引き継ぎ作業開始時HEAD：`24f060123038a011676056e4cb5f9f278fc93535`（`docs: 駒の連携比較の理解確認を記録`）
- 同時点のローカル `main`：`087069c7e53fdf9d52b4ebeac809cc73ffedaa2b`。比較機能とその記録はmainへ統合していない。main統合・pushは別々に本人承認を得る。
- 引き継ぎ作業開始時の追跡ファイルはclean。`.agents/tasks/` と `data/comparison/runs/` に既存の未追跡ファイル・ディレクトリがある。ここに列挙したC2保護対象および比較結果はステージ・変更・削除しない。
- C2保護対象4件：`data/comparison/runs/c2-king-safety-confirmation-2026-10-28-seeds.json`、`data/comparison/runs/c2-king-safety-confirmation-2026-10-28-workers-4-analysis.json`、`data/comparison/runs/c2-king-safety-confirmation-2026-10-28-workers-4/`、`data/comparison/runs/c2-king-safety-confirmation-2026-10-28/`。
  - 保持確認済みのSHA-256：seed一覧 `52d6557657893202bac46be125b28e9044fbe32917e5afb9137bbcebcde35284`、worker-4 analysis `608e6e735d410ff7124639a506f20ded95e734adbbda2794caa7edaf4b230910`。二つの比較ディレクトリは元記録のファイル数4074件・20件と一致していた。次セッションでもこれらを比較出力先やcleanup対象に使わない。
- 前回のpilot/confirmation出力も未追跡の結果物として保持する。対象は `data/comparison/runs/undefended-piece-evaluation-pilot-2026-10-30-*` と `data/comparison/runs/undefended-piece-evaluation-confirmation-2026-10-30-*`。
- 既存の `.agents/tasks/TODO-codex-undefended-piece-evaluation.md` は前テーマ時の未追跡メモで、今回中身を確認しただけ。上書き・削除・ステージしない。今回のロードマップ管理メモは `/private/tmp/kaname-shogi-handoff-24f06012/` に分離した。
- 元の `/Users/oki2a24/kaname-shogi` は今回の作業で触れていない。既存の作業状態を保持し、clean/reset/切替・上書き・削除をしない。次セッションで必要な場合も、まず状態を読み取り照合する。

### 現行接続の調査起点（コードは未変更）

- 通常CLI方針選択：`kaname_shogi/cli.py` の `choose_move_selection_policy`（今回確認時の123行付近）
- CLI入口・対局開始：`kaname_shogi/__main__.py`、`kaname_shogi/cli.py`
- 共通方針定義・一手選択：`kaname_shogi/movegen.py` の `MoveSelectionPolicy`、`kaname_shogi/game_search.py`、`kaname_shogi/one_ply_selection.py`
- USI `Difficulty` 通知・値受け付け・局内方針：`kaname_shogi/usi_engine.py`（今回確認時398行付近）
- 既存評価と接続部品：`kaname_shogi/material_undefended_piece.py`、`kaname_shogi/undefended_piece.py`
- 近い接続テスト：`tests/test_usi_engine.py`、`tests/test_usi_engine_launcher.py`、`tests/test_undefended_piece_selection.py`。通常CLI選択テストは `tests/test_cli.py` を再確認する。
- 現在の公開選択肢はルート`README.md`のCLI/USI節に記載されたRandom・Material・TwoPlyMaterial・FullWidth4・AlphaBeta4。README上、`material-undefended-piece` は比較CLI専用であり、通常CLI/USI選択肢ではない。

## 次の具体的な手順

1. 次セッション冒頭で下記Gitコマンドを順に再実行し、引き継ぎ作成後の現物と照合する。ここに記録したハッシュを現在状態と決めつけない。
2. `AGENTS.md`、`docs/resume.md`、本書、`docs/next-topics.md`、`docs/README.md`、ルート`README.md`、`docs/02-project-direction.md`、`docs/documentation-guide.md`、[評価ロードマップ](roadmap-non-material-position-evaluation.md)、[比較の学習記録](learning/undefended-piece-coordination-evaluation.md)、[比較の承認設計](plans/2026-10-30-undefended-piece-comparison-design.md)、[評価仕様](knowledge/undefended-piece-evaluation.md)を照合する。
3. brainstormingスキルを使い、選択可能な新方針としてのCLI/USI接続について、変更する利用経路、名称・表示、既定値・設定寿命、確認方法を本人と決める。ShogiHome実践を含めるかも、含めるならいつ何を確認するかも明示的に決める。過去の比較承認を流用しない。
4. 現物コードを読んでから設計・実装計画を作成し、内容と未決事項を提示して明示承認を待つ。承認前にTDD、コード・テスト変更、実装開始、対局実践へ進まない。
5. 実装・検証・独立レビュー・記録後のmain統合とpushは、それぞれ別途本人承認が必要。今回のテーマ選択だけで実施しない。

## 再開用プロンプト

次の文章を新しいセッションへ入力する。

> `/Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi` で、本人が選んだ「駒の連携評価を通常CLI・USIへ接続する」主線テーマを開始します。最初に `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`、`git rev-parse main`、`git rev-parse HEAD` を順に実行し、AGENTS.md、docs/resume.md、docs/handover-undefended-piece-normal-cli-usi-connection.md と現物を照合してください。本人は、今回初めて比較で改善が支持された評価を通常CLIとUSIから選択できる候補として試す、という理解を確認した後、候補1を選びました。選択理由はこの明示された背景を超えて推測しません。次セッションはbrainstormingから始め、通常CLI/USIでの選択方法、名前・表示、既定値、設定寿命、確認方法を決め、ShogiHome実践を含めるかも本人と確認してください。接続先・表現・実装計画は未承認です。テーマ選択を設計・計画・コード変更の承認と扱わず、設計と実装計画を提示して明示承認を待ち、承認前にコード・テスト変更や対局実践を始めないでください。前回の比較は基準 `10M` 対候補 `10M+U`、5登録局面の2035組・4070局、比較CLI `--workers 4` で完了し、候補平均得点0.908845、95%区間 `[0.878739, 0.938951]` でした。これは指定条件の改善支持であり、一般的な棋力向上の証明や既定採用の根拠ではありません。長時間比較を別途承認された場合は利用可能な並列オプションを確認し、`--workers 4` がある比較CLIでは使ってアシスタントが実行し、約一時間ごとに進捗を確認してください。本人から進捗を尋ねられたら実際の状態を確認します。`.agents/tasks/` と `data/comparison/runs/` の未追跡データを保持してください。C2保護対象4件と元の `/Users/oki2a24/kaname-shogi` を上書き・削除・clean/reset/切替しないでください。通常CLI/USI接続以外のSFEN入出力、飛車可動性v2、玉安全度との合成、二手・四手適用は今回のテーマへ自動追加しません。main統合・pushは各々別途本人承認を得てください。すべて日本語で進めてください。`
