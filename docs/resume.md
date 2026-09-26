# 学習・開発の再開案内

第39回「人間対コンピュータのCLI進行」は、設計合意、TDD、独立レビュー、全検証、main取り込み、最後の理解確認まで完了した。

## 現在の到達点

`python3 -m kaname_shogi` は、人間先手・コンピュータ後手で進む。人間の成功手の後、コンピュータは一局に一つの `random.Random` を使い、合法手から一手を選んで表示し、`GameRecord` 経由で適用する。人間の投了、EOF/Ctrl-C、詰み、詰みではないコンピュータの合法手空一覧で終了し、成功した盤上移動・駒打ちだけを記録する。

詰みの判定は `is_game_over` が担い、`choose_weak_move` の `None` は選択不能だけを表す。人間対人間・コンピュータ対コンピュータへの切替、評価・探索、USI、SFEN、CLI保存読込、千日手、持将棋、入玉、時間切れ、反則勝敗は未実装である。

## 次に始めるとき

本人は次テーマとして第40回「駒打ち順の保守改善」を選び、新しいセッションで始めることを希望した。選定理由、現在の物理的状態、再開手順、再開用プロンプトは [第40回の引き継ぎ](handover-drop-order-maintenance.md) に記録する。引き継ぎ文書とこのファイルをコミットした後にだけ、本人が再開用プロンプトを新しいセッションへ入力する。入力前に第40回の一次資料確認、確認問題、設計、実装を開始しない。

現在の候補と推薦は [次のテーマ](next-topics.md) を参照する。

## 第40回の再開用プロンプト

```text
kaname-shogiの第40回「駒打ち順の保守改善」を新しいセッションで始めてください。最初にAGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/02-project-direction.md、docs/learning/38-weak-move-selection.md、docs/knowledge/31-weak-move-selection.md、docs/learning/39-human-vs-computer-cli.md、docs/handover-drop-order-maintenance.md、kaname_shogi/model.py、kaname_shogi/movegen.py、tests/test_movegen.pyを読み、git status --short --branchで現在の状態を確認してください。必要最小限の一次資料を確認し、駒打ち順が将棋規則ではなく公開APIの再現性のための契約であることを切り分けてください。対象範囲を確認問題として一度に一問ずつ出し、私の回答を待ちながら合意してください。少なくとも、駒打ち順だけに限定するか、順序をどこで明示するか、全駒種・全打ち先の確認方法、BasicPieceTypeとの関係、既存の局面不変性・合法性の回帰確認を確認してください。設計合意と設計書承認までコードやテストを書かないでください。承認後に作業ブランチでTDD、独立レビュー、全検証、学習記録、mainへの取り込みを行い、最後に理解確認を一問だけ出してください。コミットメッセージは日本語のConventional Commitにしてください。
```

最終整理：2026-09-26。現在のGit状態は、再開時に必ず `git status --short --branch` で確認する。
