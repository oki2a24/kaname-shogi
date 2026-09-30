# 🔄 Session Handoff: CLIの `help` 表示

作成日：2026-09-30

## 🎯 最終目標 (Ultimate Goal)

`kaname-shogi` のCLIで人間が入力できるコマンドと書式を、対局中に確認できる `help` 表示として小さく追加する。

既存の `move`、`drop`、`resign`、`save <path>`、`load <path>` の入力文法、対局規則、保存形式、公開APIを先に広げない。何を表示し、いつ入力を受け直すか、解析結果を表す型へ `help` を含めるかは、既存のCLI実装とテストを調査してから本人と設計する。

## ✅ 完了した事項と意思決定の背景 (Done & Why)

- [済] 最初の実装上の到達点を第42回までに完了した。
  - **Why:** 将棋のルール、局面表示、合法手、弱い自動指し手、三つの対局形式、投了、JSON形式の明示的な保存・読込を、小さく理解可能な段階で積み上げた。CLIで弱くても対局を完結できる状態を先に作るためである。
- [済] 第43〜50回のリポジトリ基盤整理を完了した。
  - **Why:** 次の機能追加で既存の振る舞い・文書・公開境界を取り違えないよう、文書入口、古い現在記述、コードとテストの構造、CLIの駒名定義、`parse_command` の公開境界を順に整理した。第50回では `MoveCommand` などの名前付き公開型と `Command` を明記し、`GameMode`、`choose_game_mode`、`run_game` を含めてCLIの公開APIを `__all__` で固定した。
  - **検証:** 第50回はmain取り込み後に全240件のテストを成功させ、独立レビューはCritical・Important・Minorすべて0件だった。続く方向性文書の現在地是正もmainへ取り込み、全240件を再確認した。
- [済] 次テーマを「CLIの `help` 表示」に選定した。
  - **Why:** 構造整理を完了した直後は、SFENや評価関数のように範囲を広げる前に、利用者が既に使えるCLIコマンドを自力で発見できるようにする価値が高い。入力・表示・再入力という既存境界を一テーマで学べ、将棋規則・保存形式・公開APIを変えずに改善できるためである。
  - **Crucial:** `_hand_counts` の共通化再評価は以前に利益が小さいと見送った候補であり、今回開始しない。SFEN、USI、評価関数、探索も将来の別テーマである。

## 🚧 現在の物理的状態 (Physical Anchor)

- **作業ディレクトリ:** `/Users/oki2a24/kaname-shogi`
- **ブランチ:** `main`
- **引き継ぎ開始時点のHEAD:** `4f17bd3 docs: 基盤整理完了の現在地を是正する`
- **作業ツリー:** この引き継ぎ文書、`docs/resume.md`、`docs/next-topics.md`、`docs/README.md` の変更は未コミット。次テーマのコード・テスト変更はない。
- **リモートとの差:** `main...origin/main [ahead 15]`（引き継ぎ作成時点）
- **直近の成功コマンド:** `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q`（240件成功）、`git diff --check`
- **直近の完了コミット:** `4f17bd3 docs: 基盤整理完了の現在地を是正する`
- **未実施:** `help` の表示内容・入力時の制御・公開境界・エラー時の扱いの調査、brainstorming、設計仕様、設計承認、作業ブランチ、実装計画、実装、レビュー。
- **変更対象候補:** `kaname_shogi/cli.py`、`tests/test_cli.py`、必要に応じてCLI利用方法を示すREADMEと、設計・計画・学習記録・案内文書。ただし、設計・計画の承認前に既存文書、コード、テストを変更しない。

## 📝 次に読むファイルと具体的なアクション (Next Steps)

1. `/Users/oki2a24/kaname-shogi` で `git status --short --branch` と `git log -3 --oneline` を実行し、現在値を確認する。過去のHEAD・テスト結果を現在値と決めつけない。
2. `AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、この引き継ぎ、`docs/02-project-direction.md`、`docs/learning/50-cli-command-parsing-public-boundary.md`、`kaname_shogi/cli.py`、`tests/test_cli.py` を読む。
3. `superpowerssuperpowers:brainstorming` を使い、`help` の対象範囲、表示するコマンドと書式、入力後の制御、現在の `parse_command` と公開型への影響、既存テストの意図、互換性、確認方法、記録形式、検証方法を一度に一問ずつ確認する。
4. 設計を提示して本人の明示承認を待つ。承認前にコード、テスト、既存文書を変更しない。
5. 設計仕様を記録・自己レビュー・コミットし、本人のレビュー承認を待つ。
6. `writing-plans` を使って実装計画を文書化し、計画内容を提示して本人の明示承認を待つ。
7. 承認後に目的が分かる `codex/` 作業ブランチで、テストの失敗理由を確認してから最小実装、Green確認、Refactor要否確認、独立レビュー、記録、main取り込み、取り込み先検証を行う。

## 💬 再開用プロンプト (Resumption Prompt)

> kaname-shogiの次テーマ「CLIの `help` 表示」を始めてください。最初に `git status --short --branch` と `git log -3 --oneline` で現在の状態を確認し、AGENTS.md、README.md、docs/README.md、docs/resume.md、docs/next-topics.md、docs/handover-cli-help-display.md、docs/02-project-direction.md、docs/learning/50-cli-command-parsing-public-boundary.md、kaname_shogi/cli.py、tests/test_cli.py を読んでください。対象は、対局中に人間が入力できる `move`、`drop`、`resign`、`save <path>`、`load <path>` の書式を確認できるCLIの `help` 表示です。入力文法、将棋規則、保存形式、既存の公開APIを設計前に変更しません。`_hand_counts` の重複、SFEN、USI、評価関数、探索は扱いません。superpowerssuperpowers:brainstormingを使い、対象範囲、表示内容、入力後の制御、`parse_command` と公開型への影響、既存テストの意図、互換性、確認方法、記録形式、検証方法を設計し、一度に一問ずつ確認してください。設計を提示して私の明示的な承認を待ち、承認前にコード・テスト・既存文書を変更しないでください。実装計画を文書化した後も、計画を提示して私の明示的な承認を待ってください。必要な変更は目的が分かる作業ブランチで行い、日本語のConventional Commitにしてください。

このプロンプトを人間が新しいセッションへ入力するまで、次テーマの調査・設計・実装を開始しない。
