# CLI持ち駒表示テーマの開始時点：引き継ぎ

## 最終目標

kaname-shogiの対局中表示に、持ち駒をどのように表示するかを学び、合意した範囲だけを小さく設計・実装する。利用者が自分と相手双方の持ち駒を把握できるようにしたい、という本人の問題意識から選ばれたテーマである。

## 選定理由と判断背景

直前のテーマ「CLIの `help` 表示」は完了している。続いて本人から、対局中に持ち駒がどう把握されるか、表示されるならどう表示されるか、表示されないなら盤上で両者の駒台が見えることを踏まえて表示すべきではないか、との質問があった。現状を調べた結果、持ち駒はモデルで保持・更新されるが、文字盤表示には含まれないことが分かった。そのため本人は「持ち駒表示」を次テーマに選定し、新しいセッションの準備を依頼した。

物理的な対局では持ち駒は各対局者から見て盤の右側の駒台に置く。日本将棋連盟の対局規則第3条第2項に記載がある。取った駒を持ち駒にし、空いているマスに打てることは同第5条第2項・第3項に記載がある。

一次資料：
- [日本将棋連盟「対局規則」](https://www.shogi.or.jp/match/taikyoku_rules/)
- [日本将棋連盟「将棋とは？」](https://www.shogi.or.jp/knowledge/about/)

## 現在確認できている実装

- `kaname_shogi/model.py` の `Hand`（136行付近）は駒種ごとの持ち駒数を保持し、`Position`（278行付近）は先手・後手それぞれの持ち駒を持つ。
- `kaname_shogi/display.py` の `render_position(position)`（10行付近）は手番、凡例、筋段、盤上の駒を先手視点の文字列へ変換する。持ち駒の表示はない。
- `tests/test_display.py` の `test_initial_position_matches_full_display`（45行付近）は盤面表示全体を固定文字列で確認している。
- `kaname_shogi/cli.py` の `run_game`（385行付近）は局面表示を対局の進行に合わせて呼ぶ。
- ルート `README.md` のCLI説明は `help` の操作書式を説明している。持ち駒表示は記述していない。

ここまでは調査結果であり、表示方式の設計合意ではない。持ち駒をどの位置・順序・表記で表示するか、枚数1や0枚をどう表すか、両者の表示をどう区別するか、`render_position` とCLI進行層の責務をどう分けるかは未決定である。人間対人間・人間対コンピュータ・コンピュータ対コンピュータで同じ表示にするかも設計時に確認する。

## 対象境界

対象テーマは対局中に先手・後手双方の持ち駒を文字で見られる表示である。入力文法、将棋規則、持ち駒の保持・更新モデル、保存形式、既存公開APIを設計承認前に変えない。SFEN、USI、評価関数、探索、`_hand_counts` のテスト補助重複は扱わない。その他の拡張は設計で必要性を確認し、先取りしない。

## 開始時のGit・検証アンカー

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`
- この引き継ぎ作成前のブランチ：`main`
- 作成前のHEAD：`5edc5c3 docs: 第51回完了後の案内と次テーマ候補を更新する`
- 作成前の状態：`main...origin/main [ahead 7]`、作業ツリー clean
- 第51回の `main` 取り込み先で全243テスト成功。これは今回の実装を検証するものではない。
- 新セッションでは過去記録を現在値とみなさず、最初に `git status --short --branch` と `git log -3 --oneline` を実行する。
- 今回の準備コミット後のブランチ・HEAD・リモート差分は、再開時に必ず現在値を確認する。

## 次の具体的な手順

1. `git status --short --branch` と `git log -3 --oneline` で現在状態を確認する。
2. `AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、この引き継ぎ、`docs/02-project-direction.md`、`docs/learning/51-cli-help-display.md`、`kaname_shogi/model.py`、`kaname_shogi/display.py`、`kaname_shogi/cli.py`、`tests/test_display.py` を読む。
3. 日本将棋連盟の一次資料で、持ち駒の扱い・駒台の配置を確認する。
4. `superpowerssuperpowers:brainstorming` を使い、対象範囲、表示内容・配置、手番や対局形式との関係、表示責務の境界、既存テストの意図、互換性、確認・検証方法、記録形式を一問ずつ本人に確認する。
5. 設計案を提示し、明示的な承認を待つ。承認前にコード、テスト、既存文書を変更しない。
6. 承認後、実装計画を文書化して提示し、別途明示的な承認を待つ。承認前にTDDや実装を始めない。
7. 承認された手順に従い、目的が分かる作業ブランチで実装・検証・独立レビュー・記録を行う。日本語のConventional Commitを使う。

## 再開用プロンプト

> kaname-shogiの次テーマ「対局中の持ち駒表示」を始めてください。最初に `git status --short --branch` と `git log -3 --oneline` で現在の状態を確認し、AGENTS.md、README.md、docs/README.md、docs/resume.md、docs/next-topics.md、docs/handover-cli-hand-display.md、docs/02-project-direction.md、docs/learning/51-cli-help-display.md、kaname_shogi/model.py、kaname_shogi/display.py、kaname_shogi/cli.py、tests/test_display.py を読んでください。対局中に先手・後手双方の持ち駒を文字で確認できる表示が対象です。モデルは持ち駒を保持していますが現在の `render_position` は持ち駒を表示しないことを前提に、一次資料も確認してください。入力文法、将棋規則、持ち駒の保持・更新モデル、保存形式、既存の公開APIを設計承認前に変更しません。SFEN、USI、評価関数、探索、`_hand_counts` の重複は扱いません。`superpowerssuperpowers:brainstorming` を使い、対象範囲、表示内容・配置、手番や対局形式との関係、責務境界、既存テストの意図、互換性、確認方法、記録形式、検証方法を一度に一問ずつ確認してください。設計を提示して私の明示的な承認を待ち、承認前にコード・テスト・既存文書を変更しないでください。実装計画を文書化した後も、計画を提示して私の明示的な承認を待ってください。必要な変更は目的が分かる作業ブランチで行い、日本語のConventional Commitにしてください。
