# 引き継ぎ：小さいSFENで開発用コマンドの出力を読む

## 最終目標と選定範囲

2026-10-18、時間制御付き反復探索の開発用コマンド実装が完了した後、本人が次候補1「開発用コマンドを小さいSFENで試し、出力を読む」を選んだ。実装した入口を一度使い、実行条件・終了状態・選択手と由来・完了記録が出力でどう対応するかを学ぶ。

次テーマは小さいSFENによる一回の手動実行と出力の観察・理解確認・記録まで。製品コードやテストの変更、TDD、通常対局やUSIへの新方式接続、予算式変更は含めない。`--maximum-ms` は探索へ渡す予算であり、実応答時間や期限内の完了を保証しない。過去に成功したテスト件数・探索結果をこのテーマの実測へ転用しない。

本人はmain統合を明示許可し、実装ブランチをローカルmainへfast-forward統合した。最後の理解確認は先に記録済みの`STOPPED`／`SUPPRESSED`に関する回答を本人が完了済みと確認したため、その回答と補足を正本として扱う。追加で再提示した問いへの回答は受けておらず、新たな回答を作らない。

このテーマは新しいセッションで始める。本人が末尾の再開用プロンプトを入力するまで、実行・観察・学習を開始しない。

## 完了事項と意思決定の背景

- 承認済み設計に基づく専用開発用コマンドを実装し、作業ブランチで段階的TDD・検出力補強・独立レビューまで完了した。詳細な作業順と制約は[実装計画・結果](plans/2026-10-18-controlled-iterative-search-command-implementation-plan.md)と[学習・実施記録](learning/controlled-iterative-search-command-implementation-plan.md)を参照する。
- 本人の許可後、`codex/controlled-iterative-search-command`の7コミットをローカル`main`へfast-forwardした。統合時のHEADは`f0f4027`。pushはしていない。
- 統合後のmainで全体テスト560件（35.310秒）、Ruff format --check（65ファイル）、Ruff checkが成功した。これは前テーマの統合検証であり、次テーマのコマンド実行結果ではない。
- SFEN・最大深さ・目標期間・上限期間をすべて明示する入口を採用したのは、設定からの予算計算や比較探索と混同せず、時間制御付き反復の出力に集中するため。小さいキングのみのSFENは、表示各行を追いやすいREADME記載の例である。
- 候補1を選んだ理由は、完了した実装を使って表示を具体的に読む、小さな観察テーマだから。結果の深さを固定期待にせず、実行した一回の出力と実行条件から事実を読む。

## 現在の物理的状態

- 作業場所：`/Users/oki2a24/kaname-shogi`。
- 引き継ぎ作成開始時の状態：`main`、HEAD `f0f4027`、`origin/main`より27コミット先。作業ブランチ`codex/controlled-iterative-search-command`も`f0f4027`を指す。これは文書更新前の観測値で、正確な再開時HEADは新セッションで取得する。
- 未追跡の`.antigravity/tasks/`は既存のタスク記録であり、削除・ステージ・コミットしない。
- 直近の統合検証コマンドは次のとおり。いずれも次テーマの実行結果ではない。

```sh
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests
.venv/bin/ruff format --check .
.venv/bin/ruff check .
```

- 次テーマで実際に実行するコマンドは、READMEの既存例を基準にする。以下は引き継ぎ用の実行候補であり、まだ今回の実測ではない。

```sh
.venv/bin/python -m kaname_shogi.search.run_controlled_iterative \
  --sfen "8k/9/9/9/9/9/9/9/K8 b - 1" \
  --max-depth 4 --target-ms 50 --maximum-ms 100
```

- このテーマの出力観察・実時間性能・期限内応答・全SFEN/OS・SIGINT配送・棋力は未検証。既存三方式と比較コマンドは維持し、通常対局/USIへの新方式接続、予算式変更、時間保証を追加しない。

## 次に読む資料

1. 最初に`git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`を実行し、`AGENTS.md`、`docs/resume.md`、本書を現在の現物と照合する。
2. ルート`README.md`の「時間制御付き反復探索を一回試す」、`docs/knowledge/search-stop.md`、承認済みの[コマンド設計](plans/2026-10-18-controlled-iterative-search-command-design.md)を読む。
3. [実装記録](learning/controlled-iterative-search-command-implementation-plan.md)の最終確認回答と、必要なら[実装計画](plans/2026-10-18-controlled-iterative-search-command-implementation-plan.md)を参照する。
4. 実装を確認するときは`kaname_shogi/search/run_controlled_iterative.py`を読み、引数検査、計時原点、結果表示、中断境界を対応付ける。結果型の契約は`kaname_shogi/search/result.py`と`docs/knowledge/search-stop.md`から確認する。

## 次の具体的な行動

1. 再開時のGit状態と文書を現物確認する。引き継ぎのコミットや検証値を現在値と決めつけない。
2. `README.md`の既存例を実行し、実際の標準出力を保存・読み取る。まず入力SFEN、評価視点、指定深さ・各期間、終了状態、選択手、その由来、完了記録の有無を対応付ける。
3. `COMPLETE`は指定深さ完了、`STOPPED`は通常停止、`NO_LEGAL_MOVE`は合法手なし、`SUPPRESSED`は応答抑制と読む。`STOPPED`から目標/上限のどちらが原因かは推測しない。選択手と完了記録は別項目である。記録がない場合、深さ・評価・訪問数・累計を補って作らない。抑制では選択手なしだが、以前の完了記録は保持され得る。
4. 一回の観察を実時間保証と解釈せず、出力をもとに一問だけ理解確認する。回答後、本人回答と補足を分けて学習記録へ残し、次テーマ候補と再開案内を更新する。
5. 実行した探索コマンドの出力・終了コード・実行条件だけを今回の実測として記録する。過去のテスト成功や他のセッションの測定値と混ぜない。

## 再開用プロンプト

> `/Users/oki2a24/kaname-shogi` で、選定済みテーマ「小さいSFENで時間制御付き反復探索の開発用コマンドを試し、出力を読む」を始めます。
>
> 最初に `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current` を実行し、`AGENTS.md`、`docs/resume.md`、`docs/handover-controlled-iterative-search-command-output-reading.md` を現物と照合してください。案内に沿ってREADMEのコマンド例、承認済み設計、学習記録、探索停止メモ、関連コードを確認してください。
>
> README記載の小さいSFENを使い、`--max-depth 4 --target-ms 50 --maximum-ms 100` で開発用コマンドを一回実行して実際の出力を読みます。出力から実測できたことだけを説明し、深さや終了状態を固定期待せず、上限msを実応答時間の保証と扱わないでください。通常対局・USIへの接続、予算式変更、時間保証、コード/テスト変更、実装は対象外です。確認問題が必要なら一問ずつ出して回答を待ってください。
