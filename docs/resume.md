# 学習・開発の再開案内

最終整理：2026-09-14。ここは再開位置の案内であり、恒常的な運用方針はルートのAGENTS.mdを参照する。テーマが進んだら本書も更新する。

## 現在の到達点

初期配置CLIと歩・金の移動先候補を実装済み。金は利用者の選択により元の `/Users/oki2a24/kaname-shogi` のmainで実装し、別作業ツリーは使っていない。コミットと検証の経過は第9回の記録およびGit履歴を参照し、再開時に現在の状態を確認する。

候補は盤面と出発マスを受け、所有者を盤上のPieceから読む。盤外・自駒を除外し、空または対象外の駒種の出発点はValueError。盤面を変更せず、手番で制限しない。成り、合法手確定、実際の移動、持ち駒は未実装。

## 読む順序

1. ルートのAGENTS.mdと[README](../README.md)。
2. [第8回：金の移動先候補](learning/08-gold-move-candidates.md)と[参照メモ](knowledge/08-gold-move-candidates.md)。
3. [金の候補生成の設計](design/03-gold-move-candidates.md)。
4. [第9回の実装・検証記録](learning/09-gold-candidates-implementation.md)。
5. [候補生成のコード](../kaname_shogi/movegen.py)と[テスト](../tests/test_movegen.py)。

## 次に行うこと

金の実装後の理解確認から再開する。最初の問題は「ある方向が盤外や自駒だったとき、金の候補生成では関数を終えるreturnではなく、次の方向へ進むcontinueを使うのはなぜか」。回答は未取得。一問だけ出して待ち、新機能へ進まない。

第8回は筋と段、候補計算と実際の移動、状態の復元について補足した経緯があるため、すべて初回正解とは扱わない。

## 再開用プロンプト

```text
kaname-shogiの続きをお願いします。
AGENTS.mdとdocs/resume.mdを読み、現在のGit状態を確認してください。
再開案内に挙げた設計・学習記録・コード・テストを読んだうえで、
記載された最初の確認問題を一問だけ出し、私の回答を待ってください。
今回はまだ新機能の実装を始めないでください。
```

## 実行場所とコマンド

```sh
cd /Users/oki2a24/kaname-shogi
python3 -m unittest discover -s tests -v
python3 -m kaname_shogi
```

別の作業ツリーを選ぶ場合は、実際のパスと元のmainとの関係を確認する。
