# 学習・開発の再開案内

## 現在地

第67回「SFEN局面変換」は実装・独立レビュー・main統合・全326テスト・最終理解確認まで完了した。第68回「ShogiHome画面へのSFEN貼り付け確認」では、ShogiHome 1.28.1の画面へ同じ3手後局面の4欄SFENと3欄SFENを貼り付け、どちらも盤面・後手番・持ち駒なしが期待どおり表示された。本人の理解確認回答も記録した。ShogiHomeから `kaname-shogi` へのUSI `position sfen` 送信・エンジン応答は未確認である。

本人は次テーマに「ShogiHomeからkaname-shogiへSFEN局面を渡す」（第69回予定）を選び、新セッションの準備を依頼した。準備だけを記録し、第69回の学習・設計・実機確認はまだ開始していない。本人がこのページの再開用プロンプトを新セッションへ入力してから設計対話を始める。ShogiHome画面の操作は具体案への明示承認後に限る。

第69回の引き継ぎ準備開始時は `/Users/oki2a24/kaname-shogi` の `main`、HEAD `5afb40b`、作業ツリーはクリーンで `origin/main` より1コミット先行だった。今回の準備で引き継ぎ文書を追加し、`main` に文書コミットを作成した（pushなし）。新セッションではGit状態を再確認する。コード・テストは変更しておらず、この準備中にテストを実行していない。第67回の全326テストは `8421492` 時点の結果である。

第68回の最終画面は、ShogiHome 1.28.1で3欄局面を未保存新規棋譜として表示し、USIエンジン0・CSAサーバー0だった。これは過去の観察であり、現在の状態ではない。現行画面・版・登録先・棋譜・稼働セッションは、実機操作を承認された後に現物確認する。接続手順書と専用スキルにはエンジンが `position startpos moves ...` のみ対応するという古い記述が残る一方、現行コード・知識メモは `position sfen` を扱う。この差分は第69回で照合する。

## 確認記録

- [第67回学習記録](learning/67-sfen-position-conversion.md)：設計選択、実装、レビュー、テスト、本人回答と補足、未確認事項。
- [SFEN局面表記の確定知識](knowledge/sfen-position-notation.md)：現在のAPI、変換規則、検証範囲。
- [第68回学習記録](learning/68-shogihome-sfen-paste.md)：4欄・3欄SFENの画面貼り付け結果、未確認事項、本人回答と補足。
- [第68回予定テーマの引き継ぎ](handover-shogihome-sfen-paste.md)：開始時のGit状態と、開始前計画・実施結果。
- [第69回予定テーマの引き継ぎ](handover-shogihome-sfen-engine.md)：次テーマの背景、合意と未決事項、開始手順、再開用プロンプト。
- [次テーマ候補と選定履歴](next-topics.md)：第68回完了後に選定された第69回予定テーマ。
- [ShogiHome接続手順書](shogihome-connection-guide.md)と[接続スキル](../.agents/skills/shogihome-connection/SKILL.md)：実機確認を検討するときの運用条件。古いSFEN制約を現行コードと照合する。

## 再開時に行うこと

まず次を実行して、現在の状態を過去の引き継ぎから推測せず確認する。

```sh
git status --short --branch
git log -3 --oneline
```

その後、[第69回予定テーマの引き継ぎ](handover-shogihome-sfen-engine.md)と第67回学習記録も読み、コード・知識メモと接続手順書・専用スキルの古い記述を照合する。`superpowerssuperpowers:brainstorming` と `superpowerssuperpowers:roadmap-management` を使い、一問ずつ確認範囲を決める。

次テーマの選定はShogiHome操作やログ採取、設定変更の承認ではない。具体的な操作案への明示承認を得るまではShogiHome画面を操作しない。承認後に初めて現行画面・版・棋譜・セッションを確認する。コード・テスト変更、棋譜の保存・削除、設定変更、ログ採取へは範囲を広げず、必要性が見つかった場合は別途合意と承認を得る。新セッションで本人が下記プロンプトを入力するまで第69回を開始しない。

## 第69回再開用プロンプト

以下を新しいセッションへ入力する。

> `/Users/oki2a24/kaname-shogi` で、選定済みの次テーマ「ShogiHomeからkaname-shogiへSFEN局面を渡す」（第69回予定）を始める準備をしてください。最初に `git status --short --branch` と `git log -3 --oneline` を実行し、引き継ぎ準備開始時のHEAD `5afb40b`、SFEN実装統合時のHEAD `8421492`、今回の引き継ぎコミットを含む現在状態を照合してください。`AGENTS.md`、ルートREADME、文書索引、再開案内、次テーマ候補、プロジェクト方向性、本書、第68回学習記録、第67回学習記録、`docs/knowledge/sfen-position-notation.md`、ShogiHome接続手順書・専用スキル・ロードマップを読み直してください。`superpowerssuperpowers:brainstorming` と `superpowerssuperpowers:roadmap-management` を使い、画面へのSFEN貼り付けとShogiHomeからkaname-shogiへのUSI `position sfen` 送信を区別して、一問ずつ第69回の範囲を具体化してください。候補の最小案は任意局面でSFENを送りエンジンが合法手を返すところまでですが、入力局面、開始方法、期待応答、USIログの要否・範囲、棋譜保全、後片付け、停止条件はまだ実施計画として合意されていません。第67回ではコードのSFEN読込・書出しとUSI `position sfen` を実装し、統合時の全326テストが成功しました。第68回ではShogiHome画面への4欄・3欄SFEN貼り付けと局面表示を確認しましたが、ShogiHomeからkaname-shogiへのUSI送信・エンジン応答は未確認です。接続手順書と専用スキルにはエンジンが `position startpos moves ...` のみ対応するという古い記述が残るため、現行コード・知識と照合してください。実機操作案を提示し、明示承認を待つまではShogiHome画面を操作しないでください。現行の画面・版・登録先・棋譜・セッション状態を過去の記録から推測せず、承認後に現物確認してください。ログ採取、設定変更、棋譜の保存・削除、コード・テスト変更は自動的に実施範囲へ含めず、必要性があれば具体案を提示して別途合意・承認を得てください。本人がこの再開用プロンプトを新セッションへ入力するまで、第69回の学習・実機確認を開始しないでください。
