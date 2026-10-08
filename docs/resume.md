# 学習・開発の再開案内

## 現在地

第67回「SFEN局面変換」は実装・独立レビュー・main統合・全326テスト・理解確認まで完了した。第68回ではShogiHome 1.28.1の画面へ4欄・3欄SFENを貼り付けて局面表示を確認した。第69回では同じ4欄SFENを時計あり一局でエンジンへ渡し、USI `position sfen` と `bestmove 9a9b`、棋譜への一手反映を確認し、本人の理解確認まで完了した。

本人は第70回予定テーマに **「SFEN手数欄が `4` から `1` になった理由を調べる」** を選び、新しいセッションの準備を依頼した。第69回の入力SFENの手数欄は4、ShogiHomeから送られたUSIログの手数欄は1だったが、どの段階で・なぜ変わったかは未確認である。次セッションではまず既存記録・現行コード・一次資料による読み取り専用調査から始め、ShogiHome操作・ログ追加採取・コード変更などは別途合意・承認が必要である。

## 第70回予定テーマの実施前状態

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`。
- 第70回引き継ぎ準備開始時のHEAD：`e4b9f53 docs: 第69回SFENエンジン連携を引き継ぐ`。SFEN実装をmainへ統合したHEADは `8421492`、第69回引き継ぎ準備の開始時点は `5afb40b`。実際の現在状態は再開時にGitコマンドで確認する。
- 準備開始時は `main...origin/main [ahead 2]` で、D69記録・知識・手順・再開案内などの文書変更と、観察メモ・第69回学習記録の未追跡ファイルがあった。今回のドキュメント引き継ぎコミットでこれらを記録し、pushはしない。
- D69でコード・テストは変更せず、テストも実行していない。D67の全326テスト成功は `8421492` 時点。
- ShogiHomeの直近観察では結果棋譜が未保存のまま残り、USI稼働数は0だった。USIログ設定はOFFで保存済みだが、アプリ再起動後に反映されるため、再起動まではエンジンを起動しない。これは観察時点の記録であり、次セッションの現行状態ではない。次テーマは原則として読み取り専用で進め、ShogiHomeの画面や設定を触らない。
- 持ち時間0・秒読み0は第69回にShogiHomeが開始を拒否した。10分・30秒では一回開始できたが、既定値・次回推奨値ではない。時計条件が必要な場合は画面の値を推測せず、一問ずつ確認する。
- 専用ShogiHomeスキルには `position startpos moves ...` 限定の古い記述が残る。第69回のコード・知識・実通信ではSFENを確認している。スキル更新は次テーマ候補として記録したが、第70回の選定範囲には含めない。

## 次セッションで読む資料

- `/Users/oki2a24/kaname-shogi/AGENTS.md`、ルート `README.md`。
- [文書索引](README.md)、本書、[次テーマ候補と選定履歴](next-topics.md)、[プロジェクトの方向性](02-project-direction.md)。
- [第70回予定テーマの引き継ぎ](handover-shogihome-sfen-move-number.md)。
- [第69回学習記録](learning/69-shogihome-sfen-engine.md)と[第69回開始時点の引き継ぎ・実施後記録](handover-shogihome-sfen-engine.md)。
- [SFEN局面表記](knowledge/sfen-position-notation.md)、[USIエンジンの一手応答](knowledge/usi-engine-response.md)、[ShogiHomeでの対局知識](knowledge/usi-shogihome-gameplay.md)。
- [ShogiHome接続手順書](shogihome-connection-guide.md)、[ShogiHome専用スキル](../.agents/skills/shogihome-connection/SKILL.md)、[USI接続ロードマップ](roadmap-usi-shogihome.md)。スキル本文の古いSFEN制約と現行知識の差を認識する。
- [再発しやすいShogiHomeの時計・SFEN・ログ設定の観察メモ](../.antigravity/observations/shogihome-sfen-clock.md)。

## 第70回再開用プロンプト

次の全文を新しいセッションへ入力する。本人が入力する前に第70回の調査・実機確認を開始しない。

> `/Users/oki2a24/kaname-shogi` で、第70回予定テーマ「SFEN手数欄が `4` から `1` になった理由を調べる」を始めてください。最初に `git status --short --branch` と `git log -3 --oneline` を実行し、現在のブランチ・HEAD・作業ツリーを確認してください。`AGENTS.md`、ルートREADME、文書索引、再開案内、次テーマ候補、プロジェクト方向性、本書、第69回学習記録、第69回開始時点の引き継ぎ、`docs/knowledge/sfen-position-notation.md`、`docs/knowledge/usi-engine-response.md`、`docs/knowledge/usi-shogihome-gameplay.md`、ShogiHome接続手順書・専用スキル・ロードマップを読み直してください。第69回では入力した4欄SFENの手数 `4` に対し、ShogiHomeから送信されたUSI `position sfen` は手数 `1` でした。ログの盤面・手番・持ち駒は入力局面と一致し、`bestmove 9a9b` が棋譜へ反映されましたが、手数欄が変化した段階と理由は未確認です。`superpowerssuperpowers:brainstorming` と `superpowerssuperpowers:roadmap-management` を使い、まず第69回の既存ログ・現行コード・知識メモ・ShogiHome公式資料を使った読み取り専用調査の範囲と完了条件を明確にしてください。確定事実・出典・仮説を分け、理由を先取りして断定しないでください。ShogiHome画面操作、追加USIログ採取、設定変更、棋譜の保存・削除・再起動、コード・テスト変更は今回のテーマ選定から自動的に許可されたと扱わないでください。追加確認が必要なら具体案と影響を示し、別途明示承認を待ってください。現行画面・版・登録先・棋譜・セッション状態は過去の記録から推測せず、承認された画面操作案ができた場合に操作直前に現物確認してください。ShogiHomeの時計0・秒読み0は開始を拒否した一例があり、時計あり10分・30秒が一回開始できましたが、いずれも次回設定の既定値ではありません。USIログ設定はOFFで保存済みでも再起動までは反映されず、直近では結果棋譜が未保存だったため再起動を保留しました。設定がOFFになるまでエンジンを起動せず、棋譜を無断で保存・破棄したりアプリを再起動したりしないでください。プロジェクト専用ShogiHomeスキルには古い `startpos` 限定記述が残るため、現行の知識メモ・接続手順書・D69実測と区別してください。本人がこの再開用プロンプトを新セッションへ入力するまで、第70回の調査・実機確認を開始しないでください。
