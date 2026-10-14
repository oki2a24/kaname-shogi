# 引き継ぎ：Python更新の影響調査・移行案だけ

2026-10-14、本人が次テーマに選定し、新しいセッションの準備を依頼した。これは開始時点の背景と再開方法であり、Pythonのサポート状況や移行先はまだ調査していない。現行状態と公式情報を新しいセッションで改めて確認する。

## 最終目標

Pythonを更新した場合にこのリポジトリと開発環境へ及ぶ影響を調べ、移行の選択肢・手順・必要な検証・未決事項を示す。成果は影響調査と移行案までとし、具体的な移行先バージョンの最終決定、PythonやRuffその他依存の導入・更新、コード・設定の変更、テスト実行、移行実施は行わない。候補版は公式資料で確認し比較材料として示せるが、決定済みと扱わない。実施へ進むには、提示した案に対する本人の明示承認と実施開始指示を別に得る。

## 選定経緯と判断の背景

- 本人は2026-10-11、後日のテーマとしてPython更新と三方式のコード構成調査を記録するよう依頼した。更新希望の背景は、利用中のPython 3.9がEOLらしいと知ったこと。
- 当時のアシスタント推薦は、二手先読み計画のタスク2〜5、CLI/USIの三方式、時間計測、全体検証、記録、統合、理解確認を終えた後、まずPython更新の影響を調べ、その後に三方式の構成を別テーマで調べる順だった。これは推薦案で、当時は確定選定や移行許可ではなかった。根拠は[時期を検討した引き継ぎ](handover-two-ply-outcome-order.md#python更新とコード構成再検討の時期)と[保留候補](next-topics.md#保留候補)。
- 2026-10-14、本人は二手先読みと時計を「学習・実装テーマとしては完了。ShogiHome実機挙動と一般的な時間保証は未確認のまま」と整理した上で、候補「Python更新の影響調査・移行案だけ」を選び、新セッション準備を依頼した。
- 選定は調査と案の作成を指示する。Pythonの更新版を決めたり、環境を変えたりする許可ではない。調査中にRuffや依存ツールの更新を先取りしない。Python更新とコード構成の変更も同時にしない。
- Python 3.9のEOL日は過去に公式PEP 596で2025-10-31と確認した履歴がある。現行サポート状況、最新安定版、今後のサポート日程は変わり得るので、次のセッションでPython公式資料を再確認する。

## 今回までに確認した現行プロジェクト情報

以下は引き継ぎ準備中のローカル読取り結果であり、新セッションでは現物とGit履歴を再確認する。

- READMEの実測開発環境はmacOS・Python 3.9.6。READMEの別PCセットアップ条件はmacOS/Linux・Python 3.9以上で、Windowsネイティブは未実測としている。
- 準備時の `python3 --version` と `.venv/bin/python --version` はともに `Python 3.9.6`。
- 実行時依存はPython標準ライブラリのみとREADMEに記載されている。`requirements-dev.txt` は `ruff==0.16.10` のみ。
- `pyproject.toml` はRuff設定で、`required-version = "==0.16.10"`、`target-version = "py39"`、`lint.pyupgrade.keep-runtime-typing = true`。更新案では実行時PythonとRuffの対応範囲、設定変更要否を分けて検討する。
- `scripts/setup_dev.py` はmacOS/Linux（POSIX）とPython 3.9以上を要求し、通常cloneの `.git` ディレクトリ、リポジトリ内 `.venv`、固定Ruff導入、成功後のローカル `.githooks` 設定を前提とする。別Git worktreeとWindowsネイティブは今回の対象外と記載されている。
- コミット前フック `.githooks/pre-commit` は `.venv/bin/python` でステージ済みPythonファイル・設定の検査を呼び出す。テストの代替ではない。
- 開発・検査運用は[Python品質検査の知識メモ](knowledge/python-quality-checks.md)とREADMEを参照する。

## 引き継ぎ準備時点の物理状態

- 作業場所：`/Users/oki2a24/kaname-shogi`
- 準備開始時ブランチ：`main`
- 準備開始時HEAD：`da6cb9a`（`docs: 最後の理解確認と次テーマ候補を記録`）
- 準備開始時の `git status --short --branch`：`## main...origin/main [ahead 38]`。作業ツリーclean。引き継ぎ文書を追加・記録するため、この後コミットでHEADとahead数は変わる。次のセッションで必ず再照合し、この開始時記録を現状として流用しない。
- `.venv/bin/ruff --version`：`ruff 0.16.10`。`git config --local --get core.hooksPath`：`.githooks`。
- 直近の状態確認・準備コマンドはGit status/log、Ruff version、hook path、Python interpreter versions。すべて成功した。今回の準備ではテストを実行していない。
- 選定テーマの調査・公式情報の確認、Pythonインストール、Ruff更新、コード・テスト・設定の変更はまだ始めていない。実施タスクリストは作っていない。

## 新しいセッションで最初に読む資料

再開時はまず現物の状態を確認し、次に次の資料を読む。

1. `/Users/oki2a24/kaname-shogi/AGENTS.md`
2. `/Users/oki2a24/kaname-shogi/README.md`
3. `/Users/oki2a24/kaname-shogi/docs/resume.md`
4. `/Users/oki2a24/kaname-shogi/docs/next-topics.md`
5. `/Users/oki2a24/kaname-shogi/docs/02-project-direction.md`
6. `/Users/oki2a24/kaname-shogi/docs/documentation-guide.md`
7. `/Users/oki2a24/kaname-shogi/docs/knowledge/python-quality-checks.md`
8. `/Users/oki2a24/kaname-shogi/docs/handover-two-ply-outcome-order.md` の「Python更新とコード構成再検討の時期」と物理状態
9. `/Users/oki2a24/kaname-shogi/pyproject.toml`、`requirements-dev.txt`、`scripts/setup_dev.py`、`.githooks/pre-commit`、テスト配置とPythonソースの互換性調査に必要な箇所

## 次の具体的な行動

1. 次のセッションで `git status --short --branch`、`git log -3 --oneline --decorate`、`.venv/bin/ruff --version`、`git config --local --get core.hooksPath` を実行し、上記の準備開始時状態ではなく現在の状態を基準にする。
2. 上記の入口資料と対象ファイルを読み、Python実行環境、開発ツール、テスト、OS/セットアップの現行前提を一覧化する。
3. WebでPython公式のサポート期間・リリース状況・ダウンロード/移行関連資料を一次資料として確認し、着手日時点で再検証する。バージョン情報は古いPEP 596の記録から転記せず、必要ならRuff等の公式リリース・互換性資料も確認する。
4. 現在の前提、影響対象、候補間の違い、移行案、リスク、必要な検証と復帰手順、未決事項を分けて提示する。移行先の確定はしない。
5. 文書更新ガイドに従って学習記録・影響調査/移行案の置き場所を決め、内容をレビュー・リンク検証する。案を提示して本人の明示承認を待つ。承認前にPython環境・依存・コード・設定を変更せず、テストや移行を実行しない。
6. 本人が案を選ぶまで、コード構成調査など別テーマへ進まない。mainへの取り込みは必要な実施段階で別途承認を得る。

## 再開用プロンプト

> `/Users/oki2a24/kaname-shogi` の現行作業ツリーで、選定済みテーマ「Python更新の影響調査・移行案だけ」を始めてください。最初に `git status --short --branch`、`git log -3 --oneline --decorate`、`.venv/bin/ruff --version`、`git config --local --get core.hooksPath` を順に確認し、この引き継ぎとAGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/02-project-direction.md、docs/documentation-guide.md、docs/knowledge/python-quality-checks.mdを読んで範囲を照合してください。以前からのPython更新希望を扱いますが、Python 3.9のEOL日や候補版の現行状況はPython公式一次資料で着手時に再確認してください。pyproject.toml、requirements-dev.txt、scripts/setup_dev.py、.githooks/pre-commit、実行入口、Pythonソース・テストを読み、実行時Pythonと開発ツールを分けて影響を整理してください。成果は影響調査と移行案だけです。候補版を比較材料として示しても最終版を決定せず、Python/Ruff/依存の導入・更新、コード・設定変更、テスト実行、移行実施をしないでください。移行案、検証計画、復帰方法、未決事項を提示し、実施の明示承認を待ってください。二手先読みと時計は「学習・実装テーマとしては完了。ShogiHome実機挙動と一般的な時間保証は未確認のまま」です。確認問題は一問ずつ進めてください。本人がこのプロンプトを入力するまでは調査を始めないでください。
