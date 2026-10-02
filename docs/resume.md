# 学習・開発の再開案内

現在の選定テーマは、第56回「USIの平手手順から局面を再現する」です。ShogiHomeで `kaname-shogi` と平手対局する大テーマの第3小テーマとして、本人がロードマップ第3項を選び、新しいセッション用の引き継ぎ作成を依頼しました。テーマの対象範囲、API、エラー表現、検証方法はまだ決めていません。新しいセッションでは一次資料の確認と設計対話から始めます。

## 現在の物理状態

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`
- 引き継ぎ文書の作成開始時のブランチ：`codex/usi-shogihome-connection-scope`
- 作成開始時のHEAD：`424d743 docs: 第55回の記録状態を確定する`
- 作成開始時に `git status --short --branch` で作業ツリーがcleanであることを確認。`main` は `41b69a4 docs: ShogiHome対局ロードマップと引き継ぎを記録する`。新セッションでは値を必ず取り直す。
- 第55回のUSI一手変換、専用テスト、学習・知識・設計記録はローカルブランチに取り込み済み。最新確認では全257テストが成功している。引き継ぎ文書のコミット後も、新セッションで現在値を確認する。
- ShogiHome 1.28.1での実機観測は第54回に実施済み。`position startpos moves 7g7f`、時間付き `go`、`bestmove resign` 後の `gameover lose` / `quit` を記録した。実機例は `7g7f` の一つであり、他の手順や一般仕様を推測する根拠にはしない。
- ShogiHomeの一時エンジン登録とUSIログ設定は解除済み。一時プローブとそのログは削除済み。実機の詳細と後片付けは[第54回学習記録](learning/54-usi-shogihome-connection-scope.md)を参照する。
- `kaname-shogi` 自体をShogiHomeへ登録して応手を返す実対局は未実施。

この一覧は引き継ぎ文書の作成時点の情報です。再開時は必ず `git status --short --branch` と `git log -3 --oneline` を実行してください。

## 第55回から引き継ぐ確定事項

- `kaname_shogi.usi_move.parse_usi_move` と `format_usi_move` が、USI一手トークンと既存の `BoardMove` / `DropMove` を相互変換する。
- 盤上移動、成り指定、7種の駒打ち、USI座標の筋・段対応を扱う。玉打ちや不正な一手表記などは `ValueError` にする。
- 変換は一手表記と値の対応に限り、局面、手番、持ち駒、駒の動き、合法性を判定しない。
- `position` コマンド解析、複数手の局面再現、USI対局ループは第55回に含めていない。
- 最終理解確認の本人回答と補足は[第55回学習記録](learning/55-usi-move-notation.md)に記録済み。確定仕様は[USI一手表記の知識メモ](knowledge/usi-move-notation.md)を参照する。

## 次に行うこと

1. 新しいセッションで[第56回の引き継ぎ](handover-usi-position-replay.md)にある再開用プロンプトを使う。
2. 現在のGit状態を取り直し、指定資料と既存のUSI一手変換・局面履歴APIを確認する。
3. `superpowerssuperpowers:brainstorming` を使い、USI一次資料の確認後に対象範囲・表現・検証・記録方法を一問ずつ相談する。設計案への明示的な承認を待つ。
4. 実装計画を文書化する場合は計画を提示し、別途明示的な承認を得てから実装へ進む。

## 再開時に読む資料

1. `git status --short --branch` と `git log -3 --oneline` の現在結果
2. `AGENTS.md`、ルートの `README.md`、[文書索引](README.md)
3. この `docs/resume.md`、[第56回の引き継ぎ](handover-usi-position-replay.md)、[次テーマの選定履歴](next-topics.md)
4. [USI接続ロードマップ](roadmap-usi-shogihome.md)、[第55回学習記録](learning/55-usi-move-notation.md)、[USI一手表記の知識メモ](knowledge/usi-move-notation.md)、[プロジェクトの方向性](02-project-direction.md)
