# 学習・開発の再開案内

最終整理：2026-09-17。恒常的な運用方針はルートのAGENTS.mdを参照する。

## 現在の到達点

初期配置CLIと歩・金・銀・香・飛車の移動先候補を実装。飛車は第14回で学習・設計合意を行い、元の `/Users/oki2a24/kaname-shogi` のmainで実装した。別作業ツリーからの取り込みは不要。飛車の実装とレビュー対応後、全64テスト、CLI、`git diff --check`、文書参照の確認が成功している。現在の変更は未コミットであるため、コミット番号はまだない。

候補計算は盤面と出発マスを受け、盤上の駒から所有者を読む。盤外・自駒を除外し、香は前方、飛車は右・左・前・後ろの各方向を走査して、自駒の手前または最初の相手駒のマスで停止する。空または対象外の駒種の出発点はValueError。盤面を変更せず、手番で制限しない。成り、合法手確定、実際の移動、持ち駒は未実装。

## 読む順序

1. ルートのAGENTS.mdと[README](../README.md)、現在のGit状態。
2. [第12回：香の学習](learning/12-lance-move-candidates.md)と[参照メモ](knowledge/12-lance-move-candidates.md)。
3. [香の設計](design/05-lance-move-candidates.md)と[第13回：実装・検証記録](learning/13-lance-candidates-implementation.md)。
4. [飛車の学習](learning/14-rook-move-candidates.md)、[参照メモ](knowledge/13-rook-move-candidates.md)、[設計](design/06-rook-move-candidates.md)、[実装計画](plans/2026-09-17-rook-move-candidates.md)、[第15回：実装・検証記録](learning/15-rook-candidates-implementation.md)。
5. [候補生成のコード](../kaname_shogi/movegen.py)と[テスト](../tests/test_movegen.py)。

## 直近までの記録

香は学習・設計合意後、Red → Green → Refactorで実装した。全54テスト、CLI、READMEの4例、差分・文書参照の検証を確認し、独立レビューの指摘はなかった。実装コミットは `2f0c44e`。実装後にコードを説明し、自駒判定を候補追加の後ろへ移すと何が起こるかを確認した。本人から「先手後手ともに駒のあるマスが候補に含まれる」と正答を得て、相手駒のマスは本来含めてよく、自駒まで含めることが誤りだと補足した。回答・補足は[第13回](learning/13-lance-candidates-implementation.md)を参照する。この正答を実装全体の把握と同一視しない。

飛車は学習・設計合意後、元のmainへ実装した。`rook_move_candidates(board, source)`は右・左・前・後ろの順に候補を返す。Redでは未定義によるImportErrorと、ValueError契約の失敗を区別した。Greenでは最小実装で4方向を走査し、追加テストを含む全64テストが成功した。Refactorでは方向データと走査処理、変数名、公開docstringを点検し、香との共通化は先取りしなかった。レビュー指摘により盤端の四隅の正確な候補座標・順序を検証するテストと、モジュールdocstring・設計文書参照を追加した。実装・検証記録は[第15回](learning/15-rook-candidates-implementation.md)を参照する。現在はREADME、計画、実装、テスト、学習記録が未コミット変更として残っている。

[第12回](learning/12-lance-move-candidates.md)の第1問〜第3問と第5問・第6問は正答。第4問では相手駒より先も候補に含めたが、補足後の再確認で飛び越せない理由を正しく説明できた。「引っかかっている点はありません。進みましょう。」と振り返りを得た。初回正答と補足後の正答を区別する。

第10回の最初の候補列挙には横と前の取り違えがあり、補足後に筋・段の区別を確認した。以降の後手の5方向、盤外、自駒・相手駒、候補計算後の盤面は正答。「引っかかっている点はありません」と振り返りを得た。すべてを初回正解とは扱わない。

[銀への旧引き継ぎ](handover-silver.md)は学習開始前の経緯として保存している。再開位置は本書、第14回、第15回を優先する。

## 次に行うこと

1. 未コミット変更を確認し、必要なら権限を整えてコミットする。
2. コミット後のGit状態とテスト結果を確認する。
3. 飛車の実装後の理解確認を、実際のコードを説明してから一問ずつ行う。
4. 理解確認が一区切りになった後、次の学習テーマを相談する。成り、実際の移動、駒取り、持ち駒、王手、合法手判定は先取りしない。

## 再開用プロンプト

```text
kaname-shogiの続きをお願いします。
AGENTS.md、README.md、docs/resume.mdから最新の学習・設計・実装記録を読み、現在のGit状態を確認してください。
飛車の移動先候補は実装とレビュー対応まで完了しています。第14回・第15回の記録とGitの現在の状態を確認してください。
飛車の実装後の理解確認を、コードの説明から始めてください。確認問題は一問ずつ出し、回答を待ってください。
`superpowerssuperpowers` プラグインを適用し、学習と具体的な設計の合意後にRed → Green → Refactorで実装してください。
```

## 実行場所とコマンド

```sh
cd /Users/oki2a24/kaname-shogi
python3 -m unittest discover -s tests -v
python3 -m kaname_shogi
```

過去の成功記録を今回実行済みとは扱わない。別の作業ツリーを選ぶ場合は、実際のパスと元のmainとの関係を確認する。
