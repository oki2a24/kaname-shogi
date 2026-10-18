# 引き継ぎ：全幅4手とαβ枝刈り4手を対局で使える方式にする接続設計

## 最終目標と選定範囲

- 将棋の処理を理解しながら強化し、既存の選択肢を保って新しい探索方式を対局で使えるようにする。
- 2026-10-18、本人は次テーマとして「全幅4手とαβ枝刈り4手を、対局で使える方式にする接続設計」を選定した。今回のテーマは学習と接続設計である。
- 全幅読みとαβ枝刈りは、すでに開発用比較として実装済みである。今回の選定目的は、この二方式とも対局で使える選択肢にするための接続設計である。接続先を通常対局CLI・USIのどこにするか、二方式の選択方法・設定寿命、反復深化・時間制御との関係は未決定。全幅読みを比較専用にとどめる案は本人の選定要件を弱めるため、既定の前提にしない。実現上の制約が見つかった場合は根拠と選択肢を示し、本人に確認する。
- 既存のRandom（最弱・既定）、Material（一手後の駒得）、TwoPlyMaterial（二手先読み）を選べる状態で残す方針を前提にする。
- このテーマの選定はコード・テスト変更、実装計画、実装、mainへの統合の承認ではない。今回の設計案を提示し、本人の明示承認を待つ。設計の明示承認後も、実装計画と実装は別段階として扱う。時間保証を設計上の前提や成功条件にしない。
- 本人がこの引き継ぎ末尾のプロンプトを新しいセッションへ入力するまでは、選定テーマの学習・設計を開始しない。

## 完了事項と意思決定の背景

### 全幅読みとαβ枝刈り

- [済] `kaname_shogi.search.minimax` の全幅ミニマックス探索と `kaname_shogi.search.alpha_beta` のαβ枝刈り付き探索を、共通の探索本体で実装した。開始側視点の駒得評価と詰み優先を使い、二・三・四手の独立探索を比較する開発用入口 `kaname_shogi.search.compare` を用意した。
- [済] 全幅側は各根候補の確定値を保持して最善候補集合を作る。αβ側は枝を省き、根の評価と選択手を比較する。根評価が一致し、αβの選択手が全幅の最善候補に含まれるかを確認する。訪問回数は探索本体へ入った局面数である。
- [済] READMEの玉だけのSFENに対する二手比較例では、両方式の評価は0、訪問数は全幅13・αβ9と記載されている。これは当該例の比較値であり、一般的な速度や棋力を保証しない。
- **背景:** 目的は駒得評価を固定して、探索の深さと計算量の関係を学ぶことだった。最初の合意範囲は開発用比較であり、通常対局・USIへ新方式を追加すること、時間制御、置換表、駒取り継続、評価項目追加などは含めなかった。詳しい合意・実装・検証・未検証事項は[承認済み設計](plans/2026-10-17-engine-search-comparison-design.md)と[学習・実装記録](learning/engine-improvement-stage-design.md)にある。

### 反復深化と時間制御

- [済] 反復深化の開発用比較は、同じ開始局面で深さ1〜4を順に調べ、完了結果・前回最善手による根の探索順・訪問累計を表示する。全幅との比較も行う。
- [済] 時間制御付き反復探索部品は既存の予算・停止制御を使う。別テーマで専用開発用コマンドを設計・実装し、通常対局やUSIへは接続していない。
- [済] 直前テーマではREADME記載の小さいSFENを一回実行した。指定は`--max-depth 4 --target-ms 50 --maximum-ms 100`、終了コード0、終了状態`STOPPED（通常停止）`、選択手`9i9h`は完了結果由来、完了記録は深さ2・評価＋0・訪問9・完了深さまでの累計13だった。出力から目標50msと上限100msのどちらが停止判断に関係したかは分からず、経過時間も表示されない。これは一回の実測で、時間保証ではない。
- **背景:** この一回は開発用入口の出力の読み方を確認する観察テーマであり、対局接続の承認ではない。本人の回答と補足、正確な出力は[出力観察の学習記録](learning/controlled-iterative-search-command-output-reading.md)にある。

### 現在の対局選択肢

- READMEでは、通常対局CLIおよびUSIの選択肢としてRandom、Material、TwoPlyMaterialを案内している。
- 全幅読みとαβ枝刈り、反復深化、時間制御付き反復探索、今回の専用コマンドは開発用探索・比較の範囲にある。対局で選べる新方式としては未接続である。
- [プロジェクトの方向性](02-project-direction.md)では、既存方式を新方式で置き換えず、現行二手先読みも選択肢に残す方針が記録されている。

## 現在の物理的状態

- **リポジトリ:** `/Users/oki2a24/kaname-shogi`。
- **引き継ぎ準備開始時のGit状態（2026-10-18）:** `main`、HEAD `fafca62 docs: record controlled search output reading`、`origin/main`より1コミット先行。`git status --short --branch`には未追跡`.antigravity/tasks/`があった。これは既存記録として保持し、削除・ステージ・コミットしない。この引き継ぎ準備のコミットでHEADは進むため、新セッションでは必ず状態を再取得する。
- **変更対象:** この引き継ぎと、`docs/resume.md`、`docs/next-topics.md`、`docs/README.md`。製品コード・テスト・設定は変更しない。
- **今回の準備での検証:** 変更文書4件に含まれるローカルMarkdownリンク584件のファイル先が存在し、5件の見出しアンカーが見出しから計算した参照先と一致した。`git diff --check`も成功した。文書のみの準備なので製品テストや探索コマンドは再実行していない。
- **未実施:** 選定テーマの調査・学習、接続先・二方式の選択方法・時間制御の範囲に関する設計決定、設計案作成、設計承認、コード・テスト変更、実装。
- **Snapshot:** 前テーマの出力観察は完了。次テーマは選定済みだが、この準備時点では未開始。新セッションで本人が再開用プロンプトを入力してから開始する。

## 次に読む資料

1. `AGENTS.md`、`docs/resume.md`、`docs/next-topics.md`、本書を現物で確認する。READMEは現在の機能・使い方・接続状態の照合に使う。
2. [全幅読みとαβ枝刈りの承認済み設計](plans/2026-10-17-engine-search-comparison-design.md)、[学習・実装記録](learning/engine-improvement-stage-design.md)、[探索比較メモ](knowledge/search-comparison.md)を読み、現在の開発用比較契約と今回の当初範囲を確認する。
3. [プロジェクトの方向性](02-project-direction.md)、[現行三方式の構成調査](learning/three-policy-architecture.md)、READMEのCLI/USI選択肢を確認し、既存方式を維持する方針を把握する。
4. [時間制御付き反復深化の承認済み設計](plans/2026-10-18-iterative-deepening-stop-time-control-design.md)、[実装計画・結果](plans/2026-10-18-iterative-deepening-stop-time-control-implementation-plan.md)、[学習・実施記録](learning/iterative-deepening-stop-time-control-implementation.md)、[探索停止メモ](knowledge/search-stop.md)を必要な範囲で読み、既存の時間制御・停止状態を対局接続の未決事項と混同しない。
5. 前テーマの[開発用コマンド設計](plans/2026-10-18-controlled-iterative-search-command-design.md)、[実装計画](plans/2026-10-18-controlled-iterative-search-command-implementation-plan.md)、[出力観察記録](learning/controlled-iterative-search-command-output-reading.md)を参照する。
6. ソース上の接続点を確認するときは、探索の`kaname_shogi/search/minimax.py`、`alpha_beta.py`、`core.py`、`shogi.py`、`iterative_deepening.py`、`run_controlled_iterative.py`と、既存利用側の`kaname_shogi/cli.py`、`kaname_shogi/usi_engine.py`を読む。設計上必要な範囲を現物確認し、過去文書だけから現行実装を推測しない。
7. テスト設計・補強を具体的に扱う場合は、`docs/knowledge/test-coverage-review.md`と`~/.codex/observations/test-driven-development.md`を読む。ただし、この選定テーマ内ではコード・テストを変更・実行しない。

## 次の具体的な行動

1. 再開時に`git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`を実行し、本書・`docs/resume.md`・`docs/next-topics.md`と現状を照合する。過去のHEADや検証結果を現在の状態と決めつけない。
2. 全幅4手とαβ枝刈り4手が開発用比較であること、時間制御付き反復探索も現時点では開発用コマンドであること、通常対局の現行方式が三つあることを資料とコードで再確認する。
3. 本人の理解・目的を一問ずつ確認し、次の設計判断を急いで決めない。全幅読みとαβ枝刈りの両方式を対局で使える選択肢にする目標を保った上で、接続先（通常対局CLI/USI）、選択方法、設定寿命、反復深化・時間制御を含める境界、既存三方式の維持、停止時の選択手と応答責務を整理する。全幅読みを比較専用にする方向へ変更する必要がある場合は、技術的根拠を示して本人の判断を待つ。
4. 合意後、対象範囲・方式の役割・接続箇所・設定の寿命・停止/抑制/結果返却・エラー境界・確認方法・時間保証を扱わないこと・未解決事項を含む設計案を作成する。テストを確認方法として設計する場合は、規定資料を読んで検出対象と未検証範囲を明示する。
5. 設計案を本人へ提示し、明示承認を待つ。このテーマの選定を設計承認や実装承認に読み替えない。承認前に実装計画・TDD・コード/テスト変更へ進まない。

## 再開用プロンプト

> `/Users/oki2a24/kaname-shogi` で、選定済みテーマ「全幅4手とαβ枝刈り4手を、対局で使える方式にする接続設計」を新しいセッションで始めます。
>
> 最初に `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current` を実行し、`AGENTS.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/handover-four-ply-search-game-integration-design.md` を現在の状態と照合してください。次にREADMEの現行CLI/USI方式と開発用探索コマンド、`docs/02-project-direction.md`、`docs/plans/2026-10-17-engine-search-comparison-design.md`、`docs/learning/engine-improvement-stage-design.md`、`docs/knowledge/search-comparison.md`を読み、全幅4手とαβ枝刈り4手の実装済み範囲および開発用比較としての当初合意を確認してください。時間制御付き反復探索の接続状況と停止責務は、必要な範囲で承認済み設計・学習記録・`docs/knowledge/search-stop.md`・関連コードを確認してください。
>
> テーマは学習と接続設計です。選定した目標は全幅4手とαβ枝刈り4手の両方式を対局で使える選択肢にすることです。既存のRandom・Material・TwoPlyMaterialも選択肢に残す方針を前提に、接続先を通常対局CLIとUSIのどこにするか、選択方法・設定寿命、反復深化・時間制御を設計範囲に含めるか、停止/抑制時の結果返却・応答責務を一問ずつ確認してください。全幅読みを比較専用にとどめる前提へ変更せず、実現上の制約が見つかった場合は根拠と選択肢を本人に示してください。
>
> 合意した範囲・理由・確認方法・未決事項を含む具体的な設計案を作り、本人へ提示して明示承認を待ってください。今回はコード・テスト・設定変更、実装計画、実装、通常対局/USIへの接続、時間保証を行いません。テスト設計まで扱う場合は `docs/knowledge/test-coverage-review.md` と `~/.codex/observations/test-driven-development.md` を先に読み、検出したい誤りと未検証範囲を整理してください。
