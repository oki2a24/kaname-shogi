# 学習・開発の再開案内

最終整理：2026-09-22。恒常的な運用方針はルートのAGENTS.mdを参照する。

## 現在の到達点

初期配置CLIと玉・歩・金・銀・桂・香・飛車・角の移動先候補を実装。玉は第20回、飛車は第14回、角は第16回、桂馬は第19回で学習・設計合意後の実装を行った。

候補計算は盤面と出発マスを受け、盤上の駒から所有者を読む。玉は先後によらず周囲8方向へ1マス進み、各駒の基本候補を返す。盤外・自駒を除外し、相手駒を含める。空または対象外の駒種の出発点はValueError。盤面を変更せず、手番で制限しない。成り、合法手確定、持ち駒は未実装。
候補計算は盤面と出発マスを受け、盤上の駒から所有者を読む。玉は先後によらず周囲8方向へ1マス進み、各駒の基本候補を返す。盤外・自駒を除外し、相手駒を含める。空または対象外の駒種の出発点はValueError。候補計算は盤面を変更せず、手番で制限しない。

空マスへの移動適用として `move_piece(board, source, destination)` を追加した。検証成功時に出発マスを空にし、到着マスへ同じ駒を置く。空の出発マス、占有された到着マス、同一マスはValueErrorとし、失敗時は盤面を変更しない。移動方向、駒取り、手番更新、成り、王手、合法手判定は未実装。将来、評価・探索の段階で不変な盤面または局面を返す方式へ見直す課題を残している。

`apply_move(position, source, destination)` は、出発駒の `Piece.side` と `Position.side_to_move` が一致し、出発駒の既存候補に `destination` が含まれるときだけ `move_piece` に盤面移動を委譲し、成功後だけ手番を交代する。不一致・候補外では盤面移動の前に `ValueError` を送出し、盤面と手番は変更しない。空出発・占有到着・同一マスの既存の拒否契約も維持する。候補に含まれる相手駒のマスも、今回は駒取り未実装のため占有到着として拒否する。持ち駒、成り、王手、合法手判定は未実装である。

## 読む順序

1. ルートのAGENTS.mdと[README](../README.md)、現在のGit状態。
2. [第12回：香の学習](learning/12-lance-move-candidates.md)と[参照メモ](knowledge/12-lance-move-candidates.md)。
3. [香の設計](design/05-lance-move-candidates.md)と[第13回：実装・検証記録](learning/13-lance-candidates-implementation.md)。
4. [飛車の学習](learning/14-rook-move-candidates.md)、[参照メモ](knowledge/13-rook-move-candidates.md)、[設計](design/06-rook-move-candidates.md)、[実装計画](plans/2026-09-17-rook-move-candidates.md)、[第15回：実装・検証記録](learning/15-rook-candidates-implementation.md)。
5. [第18回：桂馬の学習](learning/18-knight-move-candidates.md)、[桂馬の参照メモ](knowledge/15-knight-move-candidates.md)、[桂馬の設計](design/08-knight-move-candidates.md)、[桂馬の実装計画](plans/2026-09-20-knight-move-candidates.md)、[第19回：桂馬の実装・検証記録](learning/19-knight-candidates-implementation.md)。
6. [候補生成のコード](../kaname_shogi/movegen.py)と[テスト](../tests/test_movegen.py)。
7. [第20回：玉の学習](learning/20-king-move-candidates.md)、[玉の設計](design/09-king-move-candidates.md)、[玉の実装計画](plans/2026-09-20-king-move-candidates.md)。
8. [第23回：手番と所有者の学習](learning/23-turn-ownership.md)、[参照メモ](knowledge/16-turn-ownership.md)、[設計](design/11-turn-ownership.md)、[実装計画](plans/2026-09-22-turn-ownership.md)。
9. [第24回：候補内の空マスへの移動](learning/24-candidate-only-empty-square-move.md)、[参照メモ](knowledge/17-candidate-only-empty-square-move.md)、[設計](design/12-candidate-only-empty-square-move.md)、[実装計画](plans/2026-09-22-candidate-only-empty-square-move.md)。

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
2. [第24回](learning/24-candidate-only-empty-square-move.md)の実装後理解確認まで完了していることを確認する。
3. 「駒取りと持ち駒の基礎」の最小実装範囲を相談し、設計の合意を得る。

## 次回セッションの開始点

第24回では、`apply_move` が手番に合う出発駒について、その既存候補に含まれる空マスだけを移動できるようにした。候補外、所有者不一致、空出発、占有到着、同一マスでは盤面と手番を変更せず `ValueError` にする。候補に含まれる相手駒のマスへの駒取り、持ち駒、成り、王手、合法手判定、CLI入力、評価、探索は扱わない。実装後の理解確認では、候補外を指定すると例外を出し、盤面・手番とも変わらないと本人が正答した。補足と振り返りは[第24回](learning/24-candidate-only-empty-square-move.md)を参照する。

次の学習テーマは「駒取りと持ち駒の基礎」とした。日本将棋連盟の一次資料で、相手駒のある所へ進むとその駒を取れ、取った駒を持ち駒ということ、持ち駒は原則として空いている所へ打てることを確認した。第1問では、５五が空き５四に先手の歩が移る点は正答だった。一方で、持ち駒の歩を５四にあるとしたため、５四の盤上の先手歩と、盤上のマスを持たない先手の持ち駒を区別する補足を行った。再確認では、５四の先手歩は盤上の５四、持ち駒の歩は盤上にないと正答した。振り返りは「ありません」。設計の合意やコード変更はまだ行っていない。

次回も、一次情報の確認、確認問題一問、学習記録、設計相談と承認、設計書・実装計画、TDD、検証、レビュー、記録の順で進める。設計承認前にコードを書かない。

## 再開用プロンプト

```text
kaname-shogiの続きをお願いします。
AGENTS.md、README.md、docs/resume.mdから最新の学習・設計・実装記録を読み、現在のGit状態を確認してください。
第24回の実装後理解確認まで完了しています。次のテーマ「駒取りと持ち駒の基礎」は、一次資料の確認、第1問、持ち駒が盤上のマスを持たない点の再確認、振り返りまで済んでいます。次は最小実装範囲の設計相談を行い、承認を得るまでコードを書かないでください。
`superpowerssuperpowers` プラグインを適用し、学習と具体的な設計の合意後にRed → Green → Refactorで実装してください。
```

## 実行場所とコマンド

```sh
cd /Users/oki2a24/kaname-shogi
python3 -m unittest discover -s tests -v
python3 -m kaname_shogi
```

過去の成功記録を今回実行済みとは扱わない。別の作業ツリーを選ぶ場合は、実際のパスと元のmainとの関係を確認する。
