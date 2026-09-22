# 学習・開発の再開案内

最終整理：2026-09-22。恒常的な運用方針はルートのAGENTS.mdを参照する。

## 現在の到達点

玉・歩・金・銀・桂・香・飛車・角について、盤上の駒の所有者に応じた移動先候補を計算できる。候補計算は盤面・手番・持ち駒を変更せず、盤外と自駒を除外し、相手駒のあるマスを候補に含める。

`Position` は盤面、手番、先手の `sente_hand`、後手の `gote_hand` を持つ。`Hand` は一方の持ち駒の枚数を扱う可変のデータで、先後・盤面・手番は知らない。`count` は枚数を読み、`add` は1枚加え、`remove` は1枚減らす。玉は持ち駒に入れない。

`move_piece(board, source, destination)` は空マスへの盤面操作だけを担う。`apply_move(position, source, destination)` は出発駒の所有者が手番と一致し、既存候補に含まれるときだけ局面を進める。到着マスが空なら移動し、相手の玉以外なら取り、手番側の持ち駒へ基本駒種を加える。玉取り、候補外、所有者不一致、空出発、自駒の到着、同一マスでは `ValueError` とし、盤面・手番・双方の持ち駒を変えない。

`apply_drop(position, piece_type, destination)` は、手番側の持ち駒を1枚減らして空マスへその側の駒を置き、手番を交代する。玉の指定、持ち駒不足、先後いずれかの駒があるマス、持ち歩を打つ筋に手番側の未成の歩がある二歩、歩・香・桂を行き所のない段へ打つ操作は `ValueError` で拒否し、局面を変えない。

行き所のない歩・香・桂の駒打ち制限は実装済みである。打ち歩詰め、成り・不成、成駒を取ったときの基本駒種への復元、王手・詰み・合法手、CLI入力、履歴、評価、探索は未実装である。

## 読む順序

1. ルートのAGENTS.md、[README](../README.md)、現在のGit状態。
2. [第28回：行き所のない駒](learning/28-no-legal-destination-drops.md)、[参照メモ](knowledge/21-no-legal-destination-drops.md)、[設計](plans/2026-09-22-no-legal-destination-drops-design.md)、[実装計画](plans/2026-09-22-no-legal-destination-drops.md)。
3. [第26回：持ち駒を打つ基本操作と打ち場所の制限](learning/26-hand-drops.md)、[参照メモ](knowledge/19-hand-drops.md)、[設計](design/14-hand-drops.md)、[実装計画](plans/2026-09-22-hand-drops.md)。
4. [移動・候補生成のコード](../kaname_shogi/movegen.py)、[状態モデル](../kaname_shogi/model.py)、[テスト](../tests/test_model.py)と[移動テスト](../tests/test_movegen.py)。

## 直近までの記録

第28回では、設計合意後にRed → Green → Refactorで行き所のない駒の駒打ち制限を追加した。先後それぞれの歩・香・桂について禁止段8ケースを拒否し、境界成功6ケースを確認した。Redは8ケースすべて `ValueError not raised` で失敗し、Green後は移動テスト95件、全116テストが成功した。Refactorは不要と判断し、独立レビューはCritical・Important・Minorなしでマージ可能との評価だった。CLIと `git diff --check` も成功し、`main`へfast-forwardで取り込んだ。

## 次に行うこと

1. 第28回の学習・知識・実装記録を確認する。
2. 次テーマ候補から本人が一つ選ぶ。
3. 選ばれたテーマの一次資料確認から始める。

## 再開用プロンプト

```text
kaname-shogiの続きをお願いします。
AGENTS.md、README.md、docs/resume.mdから最新の学習・設計・実装記録とGit状態を確認してください。
第27回「二歩」はmainへの取り込みまで完了しています。次テーマは第28回「行き所のない駒」です。新しいセッションで、docs/handover-no-legal-destination-drops.md、AGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/learning/27-nifu.md、docs/knowledge/20-nifu.md、docs/design/15-nifu.md、Git状態を確認してください。その後、日本将棋連盟などの一次資料で、歩・香・桂を行き所のない段へ打てない規則を確認し、確認問題を一問だけ出して本人の回答を待ってください。設計承認前にコードやテストを書かないでください。
```

## 実行場所とコマンド

```sh
cd /Users/oki2a24/kaname-shogi
python3 -m unittest discover -s tests -v
python3 -m kaname_shogi
```

過去の成功記録を今回実行済みとは扱わない。別の作業ツリーを選ぶ場合は、実際のパスと元のmainとの関係を確認する。
