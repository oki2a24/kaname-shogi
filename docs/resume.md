# 学習・開発の再開案内

最終整理：2026-09-23。恒常的な運用方針はルートのAGENTS.mdを参照する。

## 現在の到達点

玉・歩・金・銀・桂・香・飛車・角について、盤上の駒の所有者に応じた移動先候補を計算できる。候補計算は盤面・手番・持ち駒を変更せず、盤外と自駒を除外し、相手駒のあるマスを候補に含める。

`PieceType` は盤上14種、`BasicPieceType` は持ち駒8種を表す。`Piece` は不変値で、成駒の`base_piece_type`と`is_promoted`を提供する。`Position` は盤面、手番、先手の `sente_hand`、後手の `gote_hand` を持つ。`Hand` は`BasicPieceType`だけを受け付ける可変データで、玉は持ち駒に入れない。

`move_piece(board, source, destination)` は空マスへの盤面操作だけを担う。`apply_move(position, source, destination, *, promote=False)` は出発駒の所有者が手番と一致し、既存候補に含まれるときだけ局面を進める。敵陣での任意成り、歩・香・桂の強制成りを検証し、成駒は次回まで移動を拒否する。到着マスが空なら移動し、相手の玉以外なら取り、成駒も基本駒種へ戻して手番側の持ち駒へ加える。失敗時は盤面・手番・双方の持ち駒を変えない。

`apply_drop(position, piece_type, destination)` は、手番側の持ち駒を1枚減らして空マスへその側の駒を置き、手番を交代する。玉の指定、持ち駒不足、先後いずれかの駒があるマス、持ち歩を打つ筋に手番側の未成の歩がある二歩、歩・香・桂を行き所のない段へ打つ操作は `ValueError` で拒否し、局面を変えない。

行き所のない歩・香・桂の駒打ち制限、成り・不成、強制成り、成駒を取ったときの基本駒種への復元は実装済みである。成駒の移動、打ち歩詰め、王手・詰み・合法手、CLI入力、履歴、評価、探索は未実装である。

## 読む順序

1. ルートのAGENTS.md、[README](../README.md)、現在のGit状態。
2. [成り・不成テーマの引き継ぎ](handover-promotion-and-non-promotion.md)、[第28回：行き所のない駒](learning/28-no-legal-destination-drops.md)、[第29回：成り・不成の基礎](learning/29-promotion-and-non-promotion.md)、[参照メモ](knowledge/22-promotion-and-non-promotion.md)。
3. [状態モデル](../kaname_shogi/model.py)、[移動・候補生成](../kaname_shogi/movegen.py)、[モデルテスト](../tests/test_model.py)、[移動テスト](../tests/test_movegen.py)。

## 直近までの記録

第28回では、設計合意後にRed → Green → Refactorで行き所のない駒の駒打ち制限を追加した。先後それぞれの歩・香・桂について禁止段8ケースを拒否し、境界成功6ケースを確認した。Redは8ケースすべて `ValueError not raised` で失敗し、Green後は移動テスト95件、全116テストが成功した。Refactorは不要と判断し、独立レビューはCritical・Important・Minorなしでマージ可能との評価だった。CLIと `git diff --check` も成功し、`main`へfast-forwardで取り込んだ。

## 次に行うこと

1. 第29回の実装・検証・独立レビュー・最後の理解確認・記録は完了し、`main`へ取り込んだ。
2. 次テーマは第30回「成駒の移動」に決定した。新しい学習・実装へ進む前に、一次資料と現在の状態を確認する。

## 再開用プロンプト

```text
kaname-shogiの続きをお願いします。
AGENTS.md、README.md、docs/resume.md、docs/next-topics.mdと現在のGit状態を確認してください。
第29回「成り・不成の基礎」は実装・検証・独立レビュー・記録まで完了しています。作業ブランチ codex/promotion-and-non-promotion の取り込みは本人の承認を待ち、次テーマの候補を小さい順に示してください。成駒の移動はまだ未実装です。
```

## 実行場所とコマンド

```sh
cd /Users/oki2a24/kaname-shogi
python3 -m unittest discover -s tests -v
python3 -m kaname_shogi
```

過去の成功記録を今回実行済みとは扱わない。別の作業ツリーを選ぶ場合は、実際のパスと元のmainとの関係を確認する。
