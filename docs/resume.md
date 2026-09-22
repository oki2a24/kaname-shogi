# 学習・開発の再開案内

最終整理：2026-09-22。恒常的な運用方針はルートのAGENTS.mdを参照する。

## 現在の到達点

初期配置CLIと玉・歩・金・銀・桂・香・飛車・角の移動先候補を実装。玉は第20回、飛車は第14回、角は第16回、桂馬は第19回で学習・設計合意後の実装を行った。

候補計算は盤面と出発マスを受け、盤上の駒から所有者を読む。玉は先後によらず周囲8方向へ1マス進み、各駒の基本候補を返す。盤外・自駒を除外し、相手駒を含める。空または対象外の駒種の出発点はValueError。盤面を変更せず、手番で制限しない。成り、合法手確定、持ち駒は未実装。
候補計算は盤面と出発マスを受け、盤上の駒から所有者を読む。玉は先後によらず周囲8方向へ1マス進み、各駒の基本候補を返す。盤外・自駒を除外し、相手駒を含める。空または対象外の駒種の出発点はValueError。候補計算は盤面を変更せず、手番で制限しない。

空マスへの移動適用として `move_piece(board, source, destination)` を追加した。検証成功時に出発マスを空にし、到着マスへ同じ駒を置く。空の出発マス、占有された到着マス、同一マスはValueErrorとし、失敗時は盤面を変更しない。移動方向、駒取り、手番更新、成り、王手、合法手判定は未実装。将来、評価・探索の段階で不変な盤面または局面を返す方式へ見直す課題を残している。

`apply_move(position, source, destination)` は、出発駒の `Piece.side` と `Position.side_to_move` が一致するときだけ `move_piece` に盤面移動を委譲し、成功後だけ手番を交代する。不一致なら盤面移動の前に `ValueError` を送出し、盤面と手番は変更しない。空出発・占有到着・同一マスの既存の拒否契約も維持する。移動方向、候補生成結果、駒取り、持ち駒、成り、王手、合法手判定は未実装である。

## 読む順序

1. ルートのAGENTS.mdと[README](../README.md)、現在のGit状態。
2. [第12回：香の学習](learning/12-lance-move-candidates.md)と[参照メモ](knowledge/12-lance-move-candidates.md)。
3. [香の設計](design/05-lance-move-candidates.md)と[第13回：実装・検証記録](learning/13-lance-candidates-implementation.md)。
4. [飛車の学習](learning/14-rook-move-candidates.md)、[参照メモ](knowledge/13-rook-move-candidates.md)、[設計](design/06-rook-move-candidates.md)、[実装計画](plans/2026-09-17-rook-move-candidates.md)、[第15回：実装・検証記録](learning/15-rook-candidates-implementation.md)。
5. [第18回：桂馬の学習](learning/18-knight-move-candidates.md)、[桂馬の参照メモ](knowledge/15-knight-move-candidates.md)、[桂馬の設計](design/08-knight-move-candidates.md)、[桂馬の実装計画](plans/2026-09-20-knight-move-candidates.md)、[第19回：桂馬の実装・検証記録](learning/19-knight-candidates-implementation.md)。
6. [候補生成のコード](../kaname_shogi/movegen.py)と[テスト](../tests/test_movegen.py)。
7. [第20回：玉の学習](learning/20-king-move-candidates.md)、[玉の設計](design/09-king-move-candidates.md)、[玉の実装計画](plans/2026-09-20-king-move-candidates.md)。
8. [第23回：手番と所有者の学習](learning/23-turn-ownership.md)、[参照メモ](knowledge/16-turn-ownership.md)、[設計](design/11-turn-ownership.md)、[実装計画](plans/2026-09-22-turn-ownership.md)。

## 直近までの記録

香は学習・設計合意後、Red → Green → Refactorで実装した。全54テスト、CLI、READMEの4例、差分・文書参照の検証を確認し、独立レビューの指摘はなかった。実装コミットは `2f0c44e`。実装後にコードを説明し、自駒判定を候補追加の後ろへ移すと何が起こるかを確認した。本人から「先手後手ともに駒のあるマスが候補に含まれる」と正答を得て、相手駒のマスは本来含めてよく、自駒まで含めることが誤りだと補足した。回答・補足は[第13回](learning/13-lance-candidates-implementation.md)を参照する。この正答を実装全体の把握と同一視しない。

角は学習・設計・実装・検証・レビュー・理解確認まで完了した。`bishop_move_candidates(board, source)`は右前・左前・右後ろ・左後ろの順に斜め4方向を走査し、空マスと最初の相手駒のマスを候補に含め、自駒とその先を含めない。成り、馬の動き、実際の移動、駒取り、持ち駒、王手、合法手判定、飛車との共通化は対象外である。実装・検証記録は[第17回](learning/17-bishop-candidates-implementation.md)を参照する。

[第12回](learning/12-lance-move-candidates.md)の第1問〜第3問と第5問・第6問は正答。第4問では相手駒より先も候補に含めたが、補足後の再確認で飛び越せない理由を正しく説明できた。「引っかかっている点はありません。進みましょう。」と振り返りを得た。初回正答と補足後の正答を区別する。

第10回の最初の候補列挙には横と前の取り違えがあり、補足後に筋・段の区別を確認した。以降の後手の5方向、盤外、自駒・相手駒、候補計算後の盤面は正答。「引っかかっている点はありません」と振り返りを得た。すべてを初回正解とは扱わない。

[銀への旧引き継ぎ](handover-silver.md)は学習開始前の経緯として保存している。再開位置は本書、第14回、第15回を優先する。

桂馬は学習・知識整理・設計・計画・実装・検証・レビュー対応・理解確認まで完了した。`knight_move_candidates(board, source)`は右前・左前の順に候補を返し、途中の駒を飛び越し、自駒の到着先を除外して相手駒の到着先を含める。全84テスト、CLI、`git diff --check`を確認した。詳細は[第18回](learning/18-knight-move-candidates.md)、[知識15](knowledge/15-knight-move-candidates.md)、[設計08](design/08-knight-move-candidates.md)、[実装計画](plans/2026-09-20-knight-move-candidates.md)、[第19回](learning/19-knight-candidates-implementation.md)を参照する。

玉は学習・設計・実装・検証まで完了した。`king_move_candidates(board, source)`は先後によらず8方向を固定順に返し、盤外と自駒を除外して相手駒を含める。理解確認の回答と補足は第20回に記録している。

## 次に行うこと

1. 現在のGit状態とREADME、最新の学習・設計・実装記録を確認する。
2. [第23回](learning/23-turn-ownership.md)の実装後理解確認まで完了していることを確認する。
3. [次のテーマ候補](next-topics.md)、README、プロジェクト背景・方向性を照合し、次の学習テーマを相談する。

## 次回セッションの開始点

第23回では、`apply_move` が先手番には先手の駒、後手番には後手の駒だけを動かすようにした。`Piece.side` と `Position.side_to_move` が不一致なら、盤面と手番を変更せず `ValueError` にする。実装後の理解確認まで完了している。移動方向、候補生成結果、駒取り、持ち駒、成り、王手、合法手判定、CLI入力、評価、探索は扱わない。次回は次テーマの選択から再開する。

次回も、一次情報の確認、確認問題一問、学習記録、設計相談と承認、設計書・実装計画、TDD、検証、レビュー、記録の順で進める。設計承認前にコードを書かない。

## 再開用プロンプト

```text
kaname-shogiの続きをお願いします。
AGENTS.md、README.md、docs/resume.mdから最新の学習・設計・実装記録を読み、現在のGit状態を確認してください。
第23回の実装後理解確認まで完了しています。README、docs/resume.md、docs/next-topics.md、docs/01-project-background.md、docs/02-project-direction.mdを読み、次の学習テーマ候補と推薦理由を相談してください。新しいテーマでは、確認問題を一問ずつ出し、回答と振り返りを記録してから設計・実装へ進んでください。
飛車の移動先候補は実装とレビュー対応まで完了しています。桂馬はタスク3まで実装・検証・記録済みですが、実装後の理解確認は未実施です。第19回の記録とGitの現在の状態を確認してください。
角の移動先候補は学習・設計・実装・検証・レビュー・理解確認まで完了しています。次の学習テーマを相談してください。確認問題は一問ずつ出し、回答を待ってください。設計承認前に実装へ進まないでください。
`superpowerssuperpowers` プラグインを適用し、学習と具体的な設計の合意後にRed → Green → Refactorで実装してください。
```

## 実行場所とコマンド

```sh
cd /Users/oki2a24/kaname-shogi
python3 -m unittest discover -s tests -v
python3 -m kaname_shogi
```

過去の成功記録を今回実行済みとは扱わない。別の作業ツリーを選ぶ場合は、実際のパスと元のmainとの関係を確認する。
