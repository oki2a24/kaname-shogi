# ShogiHomeとUSIの接続範囲確認：開始時点の引き継ぎ

作成日：2026-10-02。この文書はテーマ1を始める前の状態と判断理由を記録する。記載したGit状態は作成時点のものであり、再開時に必ず現在値を確認する。

## 最終目標

手元のMacでShogiHomeのデスクトップ版から `kaname-shogi` をUSIエンジンとして使い、息子が盤面から指す・打つ操作をして平手から対局できるようにする。最初の到達点は、GUI上で人間と既存の弱い選択器の手が交互に進み、投了などで対局を終了できること。範囲を一回一テーマに分けた[USI接続のロードマップ](roadmap-usi-shogihome.md)を本人が承認した。

## 完了事項と意思決定の背景

- 第53回「`test_movegen.py` の `_hand_counts` 重複再評価」は完了し、[学習記録](learning/53-movegen-hand-counts-review.md)に最後の理解確認まで記録した。補助は共通化せず残し、本体コード・テストは変更していない。
- CLIで対局した本人は `move` / `drop` の文字入力を面倒と感じ、息子が気軽に指すための画面が次の課題だと判断した。自作ブラウザUIも将来の候補だが、本人はまず既存GUIで早く遊べることを優先した。
- 既存GUIとの接続にはUSIを使う。自作ブラウザUI向けのHTTP APIやREST形式は今回の前提にしない。評価関数・探索は最初のGUI対局後に必要性を見直す。
- 本人は最初の接続先を手元のMacのShogiHomeデスクトップ版と決めた。[ShogiHome公式案内](https://sunfish-shogi.github.io/shogihome/)はmacOS版とUSIエンジンを案内し、[インタプリタ型エンジンの起動条件](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%B7%E3%82%A7%E3%83%AB%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%97%E3%83%88%E3%82%84%E3%82%A4%E3%83%B3%E3%82%BF%E3%83%97%E3%83%AA%E3%82%BF%E5%9E%8B%E8%A8%80%E8%AA%9E%E3%81%A7%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E3%82%92%E5%AE%9F%E8%A1%8C%E3%81%97%E3%81%9F%E3%81%84%E6%96%B9%E3%81%B8)はシバンと実行権限を示す。
- [将棋所のUSI説明](https://shogidokoro2.stars.ne.jp/usi.html)によると、GUIとエンジンは標準入出力で通信し、平手の局面は `position startpos moves ...` で表せる。ただし、ShogiHomeが最初の対局で実際に送る `position` の形は未確認である。任意局面のSFEN相互変換を無条件に最初のテーマにせず、必要性を確かめる。
- 本人は[ロードマップ](roadmap-usi-shogihome.md)の5テーマと到達条件を承認し、テーマ1の実践は新しいセッションで始めることを選んだ。このセッションではロードマップ作成のために一次資料を読んだが、テーマ1の実機調査や実装には進んでいない。

## 現在の物理状態

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`。別のGit作業ツリーは作成していない。
- 引き継ぎ作成時の作業ブランチ：`codex/usi-shogihome-roadmap`。作成前の `main` のHEADは `a9d76d6`。本ロードマップ、現在の入口文書、引き継ぎを文書変更として記録し、`main` に取り込む予定だった。再開時には結果を決めつけずGitで確認する。
- 直近の文書検証：`git diff --check` 成功。変更対象の文書7件の相対Markdownリンク246件を確認し、欠落・行末空白・最終改行の問題は0件。`git diff --exit-code -- kaname_shogi tests` 成功。コミットと取り込み後にも現在状態を再確認する。
- テスト：ロードマップ作成は文書変更のみのため実行していない。ShogiHomeの導入、Mac上での起動、Pythonエンジン登録、実際のUSI通信は未確認。
- 主な資料：[README](../README.md)、[プロジェクトの方向性](02-project-direction.md)、[再開案内](resume.md)、[次テーマの選定](next-topics.md)、[ロードマップ](roadmap-usi-shogihome.md)。実装側の入口は `kaname_shogi/cli.py`、`kaname_shogi/game_record.py`、`kaname_shogi/move.py`、`kaname_shogi/movegen.py`。

## 次の具体的な行動

1. リポジトリ直下で `git status --short --branch` と `git log -3 --oneline` を実行し、現在のブランチ、HEAD、未コミット変更を確認する。
2. `AGENTS.md`、ルートの `README.md`、`docs/README.md`、`docs/resume.md`、この引き継ぎ、ロードマップ、`docs/next-topics.md`、`docs/02-project-direction.md` と上記のUSI・ShogiHome一次資料を読む。
3. `superpowerssuperpowers:brainstorming` でテーマ1を開始し、目的、調査範囲、ShogiHomeの導入と通信観測の方法、記録・検証方法を一問ずつ確認する。必要なら観測用の使い捨てスクリプトを計画するが、適用するパスの承認条件が整うまで作らない。
4. 手元のMacでShogiHomeの起動・登録条件と、平手対局時の実際の通信を確認する。観測できなかった点は推測で確定せず、後続テーマの結合検証へ残す。
5. テーマ1の学習記録とロードマップに観測結果・未解決事項を残す。テーマ1の完了手順は `AGENTS.md` に従う。テーマ2以降の製品コードにはまだ着手しない。

## 再開用プロンプト

> kaname-shogi の次テーマ「ShogiHomeとUSIの接続範囲を確定する」を始めてください。最初に `git status --short --branch` と `git log -3 --oneline` で現在状態を確認し、`AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/roadmap-usi-shogihome.md`、`docs/handover-usi-shogihome-connection-scope.md`、`docs/next-topics.md`、`docs/02-project-direction.md` を読んでください。将棋所のUSI説明とShogiHomeの公式案内・エンジン登録手順を一次資料として確認してください。目的は、手元のMacのShogiHomeデスクトップ版から後で `kaname-shogi` と平手対局するため、必要なUSIコマンドと起動・登録・通信観測の条件を確定することです。まず `superpowerssuperpowers:brainstorming` を使い、対象範囲、調査方法、記録・検証方法を一問ずつ確認し、設計案を提示して承認を待ってください。このセッションでUSIの指し手変換や対局ループの実装を始めないでください。
