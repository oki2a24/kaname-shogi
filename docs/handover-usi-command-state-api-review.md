# 第58回「USIコマンド型・独立状態APIの導入要否を再検討する」開始時点の引き継ぎ

作成日：2026-10-03。第57回の最終理解確認を記録し、本人が選んだ次テーマを新しいセッションで検討するための準備記録である。これは第58回の設計仕様・実装計画ではなく、コマンド型や独立状態APIの採用もまだ決まっていない。

## 次テーマと選定理由

大テーマは、手元のMacでShogiHomeを使い、息子が盤面から着手して `kaname-shogi` と平手対局できるようにすること。ロードマップ第1〜4項の接続範囲確認、一手表記変換、平手手順からの局面再現、USIエンジンの一手応答は完了した。ShogiHomeで `kaname-shogi` 自身と実際に対局するロードマップ第5項は未実施である。

第57回では、USIコマンド型と `Position` 等を保持する独立状態APIを先取りせず、`run_usi_engine` の中で最新 `Position` を保持する方式を選んだ。本人は、ほかのUSIコマンドへの対応を進める際にはコマンド型・独立状態APIを導入する方がプログラム構造上よい可能性が高いので、その必要性を次テーマで再検討したいと選定した。本人の考えている進め方は、`position`、`go` などのコマンドを一覧し、それぞれに対応する型を作るか考えることである。この考え方は、コマンド型と独立状態APIを別々の設計判断として評価する題材にできる。ただし、全コマンドに型を設けること、どちらかを必ず導入すること、また第58回で実装することは未決定である。

## 第57回から引き継ぐ背景と確定事項

- `kaname_shogi/usi_engine.py` は、日本語CLIから分離した `run_usi_engine(input_fn, output_fn, rng=None)` を持つ。関数内に最新 `Position` と乱数生成器を保持し、USIコマンドの行を読みながら応答する。
- 第57回の学習記録に記載された現状のコマンド処理は、`usi`、`isready`、`setoption` の読み飛ばし、`usinewgame`、`position`、`go`、`gameover` の読み飛ばし、`quit`、未知コマンドの読み飛ばしである。既知の未対応 `go` 検索条件は診断して終了し、未知の `go` トークンは読み飛ばす。時計引数は使わない。実装実態は第58回開始後にコードを再確認する。
- `position` は既存の `parse_usi_position` へ委譲し、局面を置き換える。`go` は既存の `legal_moves`、`choose_weak_move`、`format_usi_move` を順に使い `bestmove` を返す。選択手は保持中の局面へ適用しない。合法手がない場合は `bestmove resign` を返す。
- 入力・出力関数は注入され、`main()` が実際の標準入出力へ接続する。USI応答はstdout、診断はstderrへ出す。
- 第57回では、コマンド型も `Position` 等を包む独立状態APIも導入しなかった。これは当時の範囲を小さくする判断であり、第58回で必要性を再評価する。

詳しい判断と実装実績は[第57回学習記録](learning/57-usi-engine-response.md)、[承認済み設計仕様](plans/2026-10-03-usi-engine-response-design.md)、[実装計画と実績](plans/2026-10-03-usi-engine-response-implementation-plan.md)、[USIエンジン応答の確定知識](knowledge/usi-engine-response.md)にある。

## 区別して扱う根拠

- **USI一次資料：** [The Universal Shogi Interface](https://hgm.nubati.net/usi.html) はUSI原案と将棋所GUIの拡張を説明する資料である。第57回ではコマンド、応答、`go` 引数の仕様確認に利用した。第58回では対象にするコマンドやその表現を決める際、必要な箇所を一次資料で読み直す。
- **ShogiHomeの実機一例：** 第54回の[学習記録](learning/54-usi-shogihome-connection-scope.md)には、Mac版ShogiHome 1.28.1と使い捨てプローブ間で観測した `usi`、`setoption`、`isready`、`usinewgame`、`position startpos moves 7g7f`、時計付き `go`、プローブの `bestmove resign` 後の `gameover lose` / `quit` が記録されている。この一例を、すべての実装要件や未観測コマンドの根拠へ広げない。
- **第57回のローカル実装：** `usi_engine.py` とそのテストは、選択済みの狭い範囲を確認したもの。プロセステストが確認した標準入出力境界をShogiHome実機互換性の証拠と混同しない。
- **未確認のShogiHome挙動：** `kaname-shogi` をShogiHomeに登録した実対局、合法な `bestmove` を受け取ったGUIの応答、複数手の通常対局、今回の状態・コマンド設計で十分かは未確認である。実対局はロードマップ第5項の後続テーマに残し、第58回では実機挙動を推測しない。

## 第58回で最初に確認する資料とコード

新セッションで現在のGit状態を確認した後、次を読み直す。

- 方針・現在地：`AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、本書、`docs/next-topics.md`、`docs/02-project-direction.md`。
- 直近のUSI判断：`docs/learning/57-usi-engine-response.md`、`docs/knowledge/usi-engine-response.md`、`docs/plans/2026-10-03-usi-engine-response-design.md`、`docs/plans/2026-10-03-usi-engine-response-implementation-plan.md`、`docs/roadmap-usi-shogihome.md`。
- 背景記録：`docs/learning/54-usi-shogihome-connection-scope.md`、`docs/learning/55-usi-move-notation.md`、`docs/learning/56-usi-position-replay.md`、`docs/knowledge/usi-move-notation.md`、`docs/knowledge/usi-position-replay.md`。
- 実装とテスト：`kaname_shogi/usi_engine.py`、`kaname_shogi/usi_move.py`、`kaname_shogi/usi_position.py`、`kaname_shogi/movegen.py` の `legal_moves` / `choose_weak_move`、`kaname_shogi/game_record.py`、`kaname_shogi/cli.py`、`kaname_shogi/__main__.py`、`tests/test_usi_engine.py`、`tests/test_usi_move.py`、`tests/test_usi_position.py`、`tests/test_movegen.py`、`tests/test_game_record.py`、`tests/test_cli.py`、`tests/test_cli_entrypoint.py`。

このリストは現行実装のコマンド一覧を確定したものではない。実際のコマンド分岐、状態の所有者、呼び出し関係、公開境界、テストの責務を読み、記録上の説明と照合する。

## 再開後の進め方

1. `git status --short --branch` と `git log -3 --oneline` で現在状態を確認する。引き継ぎにあるコミットや検証結果を現在値と決めつけない。
2. 上記資料と第57回の一次資料リンクを確認する。USI標準、ShogiHomeの一実機例、第57回実装の事実、未確認事項を分ける。
3. `superpowerssuperpowers:brainstorming` を使い、コマンドの候補・現状の分岐と応答・将来対応を考えるための範囲を一問ずつ確認する。
4. 設計判断を少なくとも二軸に分けて検討する。(a) コマンド行を文字列の分岐で扱うか、必要なコマンドのみ型で表すか、(b) 局面や乱数器などの状態を関数内に置くか、独立した状態APIへまとめるか。両方を採る・片方だけ採る・どちらも採らない選択を残し、型を作ること自体を目的にしない。
5. 設計結果がコード変更を含む場合は、変更範囲・表現・検証方法・記録方法を示して設計案の明示的承認を待つ。実装計画を文書化する場合は、計画も提示して明示的承認を待つ。承認前にコードやテストを変更しない。設計レビューだけで完了する場合も、合意された根拠と未解決事項を日本語で記録する。
6. 実装する場合は `AGENTS.md` に従い、目的の分かるブランチ、TDD、Refactor判断、独立コードレビュー、学習記録・確定知識、検証を進める。第57回で成功したテスト結果を第58回の検証として扱わない。
7. ShogiHome実対局はロードマップ第5項の後続テーマとして扱う。第58回での確認範囲を設計対話で決め、資料または一例から未確認のGUI要件を推測しない。

## 引き継ぎ準備時の物理状態

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`
- 引き継ぎ準備を始める前に確認した状態：ブランチ `main`、HEAD `15e5038 docs: 第57回の取り込み結果を記録する`、`origin/main` より5コミット先行。作業ツリーには、本人が確認した第57回最終理解回答などを確定する文書変更があった。
- 引き継ぎ準備では文書だけを更新した。第57回実装の最終全体テストは、main取り込み後の `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` で277/277件成功している。今回の文書差分は `git diff --check` が成功し、テストは再実行していない。
- 新セッションの開始時には、上記の状態に依存せずGit状態と直近コミットを再確認する。

## 再開用プロンプト

次の文を新しいセッションへ入力する。人間が入力するまで、第58回の一次資料調査・既存コード調査・設計対話を始めない。

> kaname-shogi の第58回テーマ「USIコマンド型・独立状態APIの導入要否を再検討する」を始めてください。最初に `git status --short --branch` と `git log -3 --oneline` で現在状態を確認し、`AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/handover-usi-command-state-api-review.md`、`docs/02-project-direction.md`、`docs/roadmap-usi-shogihome.md`、`docs/learning/54-usi-shogihome-connection-scope.md`、`docs/learning/55-usi-move-notation.md`、`docs/learning/56-usi-position-replay.md`、`docs/learning/57-usi-engine-response.md`、`docs/knowledge/usi-move-notation.md`、`docs/knowledge/usi-position-replay.md`、`docs/knowledge/usi-engine-response.md`、`docs/plans/2026-10-03-usi-engine-response-design.md`、`docs/plans/2026-10-03-usi-engine-response-implementation-plan.md` を読んでください。`kaname_shogi/usi_engine.py`、`kaname_shogi/usi_move.py`、`kaname_shogi/usi_position.py`、`kaname_shogi/movegen.py` の `legal_moves` / `choose_weak_move`、`kaname_shogi/game_record.py`、`kaname_shogi/cli.py` と起動入口、これらに対応する既存テストを確認してください。ShogiHomeで `kaname-shogi` と平手対局する大テーマの途中として、第57回で `run_usi_engine` 内に置いた最新 `Position` などの状態管理とUSIコマンド処理の構造を見直します。`position`、`go` などのコマンドを一覧する際は、USI一次資料にあるコマンド、ShogiHome第54回の使い捨てプローブで観測した一例、第57回のローカル実装で扱うコマンド、未確認のShogiHome挙動を区別し、仕様や実機一例から未確認の実装要件を推測しないでください。`superpowerssuperpowers:brainstorming` を使い、一次資料と既存コードを確認した後、コマンド行を型で表すかどうかと独立状態APIを設けるかどうかを別の判断として、一問ずつ相談してください。全コマンドに型を作ること、状態APIを導入すること、実装へ進むことは先に決めず、設計案を示して明示的な承認を待ってください。実装計画を作成する場合も提示後に明示的な承認を待ち、承認前にコードやテストを変更しないでください。ShogiHomeでの実対局はロードマップ第5項の後続テーマとして扱ってください。
