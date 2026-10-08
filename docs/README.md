# kaname-shogi 文書案内

## この索引の使い方

この索引は、すべての文書を最初から順番に読むための一覧ではありません。
知りたいことに合う文書だけを選び、現在の情報と過去の経緯を混同せずに読むための入口です。

## 目的別の読み方

- 現在できることと使い方を知る：ルートの [README](../README.md)
- ShogiHomeへの接続・対局手順を知る：[ShogiHome接続手順書](shogihome-connection-guide.md)
- 作業を再開する：[AGENTS.md](../AGENTS.md)、ルートの [README](../README.md)、[再開案内](resume.md)、現在の実装計画、現在のGit状態。引き継ぎはテーマ開始時点の背景として読む
- 現在の確定仕様を調べる：下のテーマ別索引から対応する知識メモ
- 判断理由や学習の経緯を調べる：対応する学習記録
- 実装する：承認済みの設計仕様、実装計画、関連コード、関連テスト

AIは最初からすべての学習記録、設計書、実装計画、引き継ぎを読みません。テーマ別索引から現在の確定知識と設計を選び、判断理由が必要になったときだけ学習記録や過去の引き継ぎへ進みます。過去の文書にあるGit状態、テスト件数、次の行動は、その時点の記録であって現在値ではありません。

## 文書種別の役割

| 文書 | 主な役割 | 主な読み手 | 読むタイミング | 更新契機 | 情報の性質 |
| --- | --- | --- | --- | --- | --- |
| ルートの `README.md` | 現在の概要と利用方法 | 初めて訪れた人、利用者 | 最初 | 利用方法または主要機能が変わったとき | 現在情報 |
| `docs/README.md` | 文書の地図と選択的な読み方 | 人間、AI | 詳細文書を探すとき | 各テーマの完了時 | 現在の入口と履歴への索引 |
| `docs/resume.md` | 現在の作業を再開する短い入口 | 人間、AI | セッション再開時 | テーマ完了時、次テーマを選び引き継ぐとき | 現在情報 |
| `docs/handover-*.md` | 対応テーマ開始時点の物理状態と再開手順 | 作業を引き継ぐ人、AI | 対応テーマの再開時、経緯確認時 | 次テーマを新しいセッションへ引き継ぐとき | 作成時点の情報 |
| `docs/knowledge/` | 現在の確定知識と実装上の参照事項 | 実装・保守を行う人、AI | 現在仕様を確認するとき | 確定知識が追加・変更されたとき | 現在の確定知識 |
| `docs/learning/` | 回答、合意、実施、レビュー、振り返り | 学習者、判断経緯を調べる人、AI | なぜその判断になったか調べるとき | 各学習回の進行時と完了時 | 学習と判断の履歴 |
| `docs/plans/*-design.md` | 承認対象となる現在方式の設計仕様 | 本人、実装担当 | 設計レビュー時、実装前 | 設計合意後と設計修正時 | 承認済み仕様と判断履歴 |
| `docs/plans/` の実装計画 | 承認済み設計を実行する手順と検証方法 | 実装担当 | 実装開始前と実装中 | 計画作成時、実際との差異が生じたとき | 実行手順と実施記録 |
| `docs/design/` | 初期段階の設計 | 経緯を調べる人、AI | 初期実装の判断を調べるとき | 原則として更新しない | 初期設計の履歴 |
| `docs/02-project-direction.md` | 長期的な方向と節目の判断 | 本人、AI | 次テーマの選定時 | 大きな到達点や方向変更時 | 長期方針と判断履歴 |
| `docs/next-topics.md` | 完了テーマ後の候補と選定結果 | 本人、AI | 次テーマの選定時 | テーマ完了後の理解確認後 | 候補と選定履歴 |
| ロードマップ | 複数テーマの順序とGREEN条件 | 本人、AI | 長期作業の開始・切替時 | テーマ開始時と完了時 | 現在の進行と完了履歴 |

## 現在の作業入口

- [第71回学習記録：ShogiHome専用スキルの現行化（main統合・文書検証済み、最終理解確認待ち）](learning/71-shogihome-connection-skill-update.md)

- [第67回の実装計画（実装・レビュー・全326テスト・main統合・理解確認完了）](plans/2026-10-07-sfen-position-conversion-implementation-plan.md)
- [第67回の設計仕様](plans/2026-10-07-sfen-position-conversion-design.md)
- [第67回の学習記録（実装・main統合・全326テスト・理解確認完了）](learning/67-sfen-position-conversion.md)
- [SFEN局面表記の確定知識](knowledge/sfen-position-notation.md)
- [第66回学習記録：ShogiHomeでMaterialの着手への影響を確認する（実機観察・理解確認完了）](learning/66-shogihome-material-move-effect.md)
- [第67回開始時点の引き継ぎ（履歴）：SFEN局面変換](handover-sfen-position-conversion.md)
- [第68回開始時点の引き継ぎと実施結果：ShogiHome画面へのSFEN貼り付け確認](handover-shogihome-sfen-paste.md)
- [第69回開始時点の引き継ぎと実施後記録：ShogiHomeからkaname-shogiへSFEN局面を渡す](handover-shogihome-sfen-engine.md)
- [第69回の学習記録：ShogiHomeからのSFEN送信・時計あり一手応答](learning/69-shogihome-sfen-engine.md)
- [第70回学習記録：SFEN手数欄が `4` から `1` になった理由（調査・理解確認・記録内容確認済み）](learning/70-shogihome-sfen-move-number.md)
- [第71回予定テーマの引き継ぎ：ShogiHome専用スキルを現行化する](handover-shogihome-connection-skill-update.md)
- [第70回開始時点の引き継ぎ（履歴）：SFEN手数欄が `4` から `1` になった理由を調べる](handover-shogihome-sfen-move-number.md)
- [再発しやすいShogiHomeの時計・SFEN・ログ設定の注意](../.antigravity/observations/shogihome-sfen-clock.md)
- [第65回学習記録：ShogiHomeでDifficulty設定を確認する（実機観察・理解確認完了）](learning/65-shogihome-difficulty-verification.md)
- [学習・開発の再開案内](resume.md)
- [次テーマ候補と選定履歴：第70回完了、第71回予定テーマ選定済み](next-topics.md)
- [第66回開始時点の引き継ぎ（開始時の履歴）：ShogiHomeでMaterialの着手への影響を確認する](handover-shogihome-material-move-effect.md)
- [第65回開始時点の引き継ぎ（開始時の履歴）：ShogiHomeでDifficulty設定を確認する](handover-shogihome-difficulty-verification.md)
- [第64回実装計画（本人承認済み）](plans/2026-10-05-weakest-mode-difficulty-selection-implementation-plan.md)
- [第64回学習記録：承認済み難易度選択設計の実装](learning/64-weakest-mode-difficulty-selection-implementation.md)
- [最弱手選択と駒得評価の確定知識](knowledge/31-weak-move-selection.md)
- [USI Difficulty optionの確定知識](knowledge/usi-engine-response.md)
- [第64回学習記録：難易度選択の実装・main取り込み・理解確認まで完了](learning/64-weakest-mode-difficulty-selection-implementation.md)
- [第63回学習記録：最弱モードを残す難易度選択の最小設計（設計・理解確認完了）](learning/63-weakest-mode-difficulty-selection.md)
- [第64回開始時点の引き継ぎ（開始時の履歴）](handover-weakest-mode-difficulty-selection-implementation.md)
- [第63回の設計仕様（本人承認済み）](plans/2026-10-05-weakest-mode-difficulty-selection-design.md)
- [次テーマ開始時点の引き継ぎ：最弱モードを残す難易度選択の最小設計](handover-weakest-mode-difficulty-selection.md)
- [第61回学習記録：ShogiHome自動投了時のUSI通信確認](learning/61-shogihome-auto-resign-logs.md)
- [第61回開始時点の引き継ぎ（開始時の履歴）：ShogiHome自動投了時のUSI通信確認](handover-shogihome-auto-resign-logs.md)
- [第60回予定テーマ開始時点の引き継ぎ：息子によるShogiHome試用](handover-son-shogihome-trial.md)
- [第60回学習記録：息子によるShogiHome試用（実対局・理解確認まで完了）](learning/60-shogihome-son-trial.md)
- [ShogiHomeで対局するためのロードマップ](roadmap-usi-shogihome.md)
- [第59回開始時点の引き継ぎ：ShogiHomeで平手対局する](handover-usi-shogihome-gameplay.md)
- [第59回学習記録：ShogiHomeで平手対局する（main取り込み・全283テスト・理解確認まで完了）](learning/59-shogihome-even-game.md)
- [ShogiHome平手対局の確定知識](knowledge/usi-shogihome-gameplay.md)
- [第59回の実装計画](plans/2026-10-04-shogihome-gameplay-implementation-plan.md)
- [第58回学習記録：USIコマンド型・独立状態APIの導入要否](learning/58-usi-command-state-api-review.md)
- [第58回の設計仕様](plans/2026-10-04-usi-command-state-api-review-design.md)
- [第58回の実装計画](plans/2026-10-04-usi-command-state-api-review-implementation-plan.md)
- [第57回学習記録：USIエンジンとして一手を返す](learning/57-usi-engine-response.md)
- [USIエンジン応答の確定知識](knowledge/usi-engine-response.md)
- [第57回の設計仕様](plans/2026-10-03-usi-engine-response-design.md)
- [第57回の実装計画](plans/2026-10-03-usi-engine-response-implementation-plan.md)
- [第57回開始時点の引き継ぎ](handover-usi-engine-response.md)
- [第58回開始時点の引き継ぎ：USIコマンド型・独立状態APIの導入要否](handover-usi-command-state-api-review.md)
- [第56回開始時点の引き継ぎ（開始時の履歴）](handover-usi-position-replay.md)
- [第51回学習記録](learning/51-cli-help-display.md)
- [第52回学習記録：対局中の持ち駒表示](learning/52-cli-hand-display.md)
- [第53回学習記録：`_hand_counts` 重複の再評価](learning/53-movegen-hand-counts-review.md)
- [第54回学習記録：ShogiHomeとUSIの接続範囲](learning/54-usi-shogihome-connection-scope.md)
- [第55回学習記録：USI指し手表記と内部の一手の対応](learning/55-usi-move-notation.md)
- [USI一手表記の確定知識](knowledge/usi-move-notation.md)
- [第56回学習記録：USIの平手手順から局面を再現する](learning/56-usi-position-replay.md)
- [USI平手局面再現の確定知識](knowledge/usi-position-replay.md)
- [第56回の設計仕様](plans/2026-10-02-usi-position-replay-design.md)
- [第56回の実装計画](plans/2026-10-02-usi-position-replay-implementation-plan.md)
- [持ち駒表示の確定知識](knowledge/34-cli-hand-display.md)
- [持ち駒表示の設計仕様](plans/2026-10-01-cli-hand-display-design.md)
- [持ち駒表示の実装計画](plans/2026-10-01-cli-hand-display.md)

第51〜66回の学習記録は最後の理解確認まで完了しています。第60〜62回ではShogiHomeでの試用、通信観察、接続手順の整備を行いました。第63〜64回では難易度選択を設計・実装し、全305テストとmain取り込み後の検証を完了しました。第65〜66回ではShogiHomeのDifficulty設定と、Random / Materialの一局面での着手を観察しました。第67回「SFEN局面変換」では、SFEN読込・書出しとUSI `position sfen` を実装し、独立レビュー、全326テスト、main統合後の検証、最終理解確認まで完了しました。
第68回ではShogiHome 1.28.1の画面に4欄SFENと手数欄を省いた3欄SFENを貼り付け、どちらも期待した局面を表示することを確認しました。第69回では同じ4欄SFENを時計あり（持ち時間10分・秒読み30秒）の一局でエンジンへ渡し、USIログの `position sfen` と `bestmove 9a9b`、棋譜上の後手の一手を確認しました。持ち時間・秒読みが両方0の設定はShogiHomeに拒否されたため、時計ありへ変更しています。本人の理解確認回答も記録済みです。次テーマに「SFEN手数欄が `4` から `1` になった理由を調べる」（第70回予定）を選びました。詳細は[第69回学習記録](learning/69-shogihome-sfen-engine.md)、[第70回引き継ぎ](handover-shogihome-sfen-move-number.md)、再発時に使う注意は[ShogiHome観察メモ](../.antigravity/observations/shogihome-sfen-clock.md)を参照してください。`handover-*.md` はテーマ開始時点の履歴であり、現在の状態は `resume.md` と再開時のGit確認で確かめます。

## テーマ・学習回別索引

第71回は本人が新セッションへプロンプトを入力して開始し、具体案への明示承認後に専用スキルを更新した。判断課題の評価と独立レビュー（Critical・Important・Minor各0件）は済み、本人の内容確認・承認後、`491596b` をmainへ取り込み、取り込み先の文書検証まで済んだ。最終理解確認を待っている。以下の第70回末尾の選定説明は開始前の履歴である。現在の再開手順は[再開案内](resume.md)、今回の承認・変更・検証・限界は[第71回学習記録](learning/71-shogihome-connection-skill-update.md)を参照する。

第70回は既存ログ・現行コード・ShogiHome 1.28.1と固定依存の公式ソースを読み取り専用で調査した。入力の手数4は局面読込時に保持されず、USI生成時に開始局面のSFENへ1を付ける経路が第69回の実測と一致した。盤面が平手初期配置へ戻る意味ではない。理解確認の最初の回答・補足・再回答は[第70回学習記録](learning/70-shogihome-sfen-move-number.md)に記録した。本人による内容確認後、`9110acb` にコミットした。次テーマは「ShogiHome専用スキルを現行化する」（第71回予定）に決まり、[引き継ぎ](handover-shogihome-connection-skill-update.md)を用意した。本人が新セッションへプロンプトを入力するまで着手しない。

リンクがない文書種別は `—` と表示します。複数の学習回で一つの実装テーマを扱った場合は、同じ行にまとめています。

| テーマ | 学習記録 | 確定知識 | 設計仕様 | 実装計画 | 引き継ぎ |
| --- | --- | --- | --- | --- | --- |
| 将棋の全体像（第1回） | [第1回](learning/01-shogi-overview.md) | [将棋の全体像](knowledge/01-shogi-overview.md) | — | — | — |
| 駒の動きと成り（第2回） | [第2回](learning/02-piece-movement-and-promotion.md) | [駒の動きと成り](knowledge/02-piece-movement-and-promotion.md) | — | — | — |
| 初期配置と盤上の座標（第3回） | [第3回](learning/03-initial-setup-and-coordinates.md) | [初期配置と盤上の座標](knowledge/03-initial-setup-and-coordinates.md) | — | — | — |
| 初期実装の設計と初期配置CLI（第4〜5回） | [第4回](learning/04-first-implementation-design.md)、[第5回](learning/05-initial-position-implementation.md) | [第1回実装の設計](knowledge/04-first-implementation-design.md) | [初期設計](design/01-board-and-initial-position.md) | [初期配置](superpowers/plans/2026-09-13-initial-position.md) | — |
| 歩の移動先候補（第6〜7回） | [第6回](learning/06-pawn-move-candidates.md)、[第7回](learning/07-pawn-candidates-implementation.md) | [歩](knowledge/06-pawn-move-candidates.md) | [初期設計](design/02-pawn-move-candidates.md) | — | — |
| 金の移動先候補（第8〜9回） | [第8回](learning/08-gold-move-candidates.md)、[第9回](learning/09-gold-candidates-implementation.md) | [金](knowledge/08-gold-move-candidates.md) | [初期設計](design/03-gold-move-candidates.md) | — | — |
| 銀の移動先候補（第10〜11回） | [第10回](learning/10-silver-move-candidates.md)、[第11回](learning/11-silver-candidates-implementation.md) | [銀](knowledge/10-silver-move-candidates.md) | [初期設計](design/04-silver-move-candidates.md) | — | [銀](handover-silver.md) |
| 香の移動先候補（第12〜13回） | [第12回](learning/12-lance-move-candidates.md)、[第13回](learning/13-lance-candidates-implementation.md) | [香](knowledge/12-lance-move-candidates.md) | [初期設計](design/05-lance-move-candidates.md) | — | — |
| 飛車の移動先候補（第14〜15回） | [第14回](learning/14-rook-move-candidates.md)、[第15回](learning/15-rook-candidates-implementation.md) | [飛車](knowledge/13-rook-move-candidates.md) | [初期設計](design/06-rook-move-candidates.md) | [実装計画](plans/2026-09-17-rook-move-candidates.md) | — |
| 角の移動先候補（第16〜17回） | [第16回](learning/16-bishop-move-candidates.md)、[第17回](learning/17-bishop-candidates-implementation.md) | [角](knowledge/14-bishop-move-candidates.md) | [初期設計](design/07-bishop-move-candidates.md) | [実装計画](plans/2026-09-19-bishop-move-candidates.md) | — |
| 桂馬の移動先候補（第18〜19回） | [第18回](learning/18-knight-move-candidates.md)、[第19回](learning/19-knight-candidates-implementation.md) | [桂馬](knowledge/15-knight-move-candidates.md) | [初期設計](design/08-knight-move-candidates.md) | [実装計画](plans/2026-09-20-knight-move-candidates.md) | — |
| 玉の移動先候補（第20回） | [第20回](learning/20-king-move-candidates.md) | — | [初期設計](design/09-king-move-candidates.md) | [実装計画](plans/2026-09-20-king-move-candidates.md) | — |
| 空マスへの移動適用（第21回） | [第21回](learning/21-empty-square-move-application.md) | — | [初期設計](design/10-empty-square-move-application.md) | [実装計画](plans/2026-09-21-empty-square-move-application.md) | — |
| 手番更新（第22回） | [第22回](learning/22-turn-update.md) | — | [設計仕様](plans/2026-09-22-turn-update-design.md) | [実装計画](plans/2026-09-22-turn-update.md) | — |
| 手番と駒の所有者（第23回） | [第23回](learning/23-turn-ownership.md) | [手番と所有者](knowledge/16-turn-ownership.md) | [初期設計](design/11-turn-ownership.md) | [実装計画](plans/2026-09-22-turn-ownership.md) | [引き継ぎ](handover-turn-ownership.md) |
| 候補内の空マスへの移動（第24回） | [第24回](learning/24-candidate-only-empty-square-move.md) | [候補内の空マス](knowledge/17-candidate-only-empty-square-move.md) | [初期設計](design/12-candidate-only-empty-square-move.md) | [実装計画](plans/2026-09-22-candidate-only-empty-square-move.md) | — |
| 駒取りと持ち駒（第25回） | [第25回](learning/25-capture-and-hands.md) | [駒取りと持ち駒](knowledge/18-capture-and-hands.md) | [初期設計](design/13-capture-and-hands.md) | [実装計画](plans/2026-09-22-capture-and-hands.md) | — |
| 持ち駒を打つ（第26回） | [第26回](learning/26-hand-drops.md) | [持ち駒を打つ](knowledge/19-hand-drops.md) | [初期設計](design/14-hand-drops.md)、[設計仕様](plans/2026-09-22-hand-drops-design.md) | [実装計画](plans/2026-09-22-hand-drops.md) | — |
| 二歩（第27回） | [第27回](learning/27-nifu.md) | [二歩](knowledge/20-nifu.md) | [初期設計](design/15-nifu.md)、[設計仕様](plans/2026-09-22-nifu-design.md) | [実装計画](plans/2026-09-22-nifu.md) | [引き継ぎ](handover-nifu.md) |
| 行き所のない駒（第28回） | [第28回](learning/28-no-legal-destination-drops.md) | [行き所のない駒](knowledge/21-no-legal-destination-drops.md) | [設計仕様](plans/2026-09-22-no-legal-destination-drops-design.md) | [実装計画](plans/2026-09-22-no-legal-destination-drops.md) | [引き継ぎ](handover-no-legal-destination-drops.md) |
| 成り・不成（第29回） | [第29回](learning/29-promotion-and-non-promotion.md) | [成り・不成](knowledge/22-promotion-and-non-promotion.md) | [設計仕様](plans/2026-09-23-promotion-and-non-promotion-design.md) | [実装計画](plans/2026-09-23-promotion-and-non-promotion.md) | [引き継ぎ](handover-promotion-and-non-promotion.md) |
| 成駒の移動（第30回） | [第30回](learning/30-promoted-piece-movement.md) | [成駒の移動](knowledge/23-promoted-piece-movement.md) | [設計仕様](plans/2026-09-23-promoted-piece-movement-design.md) | [実装計画](plans/2026-09-23-promoted-piece-movement.md) | — |
| 王手と合法手判定（第31回） | [第31回](learning/31-check-and-legal-moves.md) | [王手と合法手](knowledge/24-check-and-legal-moves.md) | [設計仕様](plans/2026-09-23-check-and-legal-moves-design.md) | [実装計画](plans/2026-09-23-check-and-legal-moves.md) | [引き継ぎ](handover-check-and-legal-moves.md) |
| 詰み・終局判定（第32回） | [第32回](learning/32-checkmate-and-game-end.md) | [詰み・終局](knowledge/25-checkmate-and-game-end.md) | [設計仕様](plans/2026-09-23-checkmate-and-game-end-design.md) | [実装計画](plans/2026-09-23-checkmate-and-game-end.md) | [引き継ぎ](handover-checkmate-and-game-end.md) |
| 打ち歩詰め（第33回） | [第33回](learning/33-uchi-fuzume.md) | [打ち歩詰め](knowledge/26-uchi-fuzume.md) | [設計仕様](plans/2026-09-23-uchi-fuzume-design.md) | [実装計画](plans/2026-09-23-uchi-fuzume.md) | [引き継ぎ](handover-uchi-fuzume.md) |
| CLIでの指し手入力と対局進行（第34回） | [第34回](learning/34-cli-gameplay.md) | [CLI対局](knowledge/27-cli-gameplay.md) | [設計仕様](plans/2026-09-23-cli-gameplay-design.md) | [実装計画](plans/2026-09-23-cli-gameplay.md) | [引き継ぎ](handover-cli-gameplay.md) |
| 終局理由の拡張（第35回） | [第35回](learning/35-game-end-reasons.md) | [終局理由](knowledge/28-game-end-reasons.md) | [設計仕様](plans/2026-09-23-game-end-reasons-design.md) | [実装計画](plans/2026-09-23-game-end-reasons.md) | [引き継ぎ](handover-game-end-reasons.md) |
| 棋譜・局面のメモリ内保存（第36回） | [第36回](learning/36-game-record-and-position-save.md) | [棋譜と局面](knowledge/29-game-record-and-position-save.md) | [設計仕様](plans/2026-09-23-game-record-and-position-save-design.md) | [実装計画](plans/2026-09-23-game-record-and-position-save.md) | [引き継ぎ](handover-game-record-and-position-save.md) |
| 棋譜・局面のJSONファイル保存（第37回） | [第37回](learning/37-game-record-file-save.md) | [JSONファイル保存](knowledge/30-game-record-file-save.md) | [設計仕様](plans/2026-09-24-game-record-file-save-design.md) | [実装計画](plans/2026-09-24-game-record-file-save.md) | [引き継ぎ](handover-game-record-file-save.md) |
| 弱い自動指し手（第38回） | [第38回](learning/38-weak-move-selection.md) | [合法手列挙と一手選択](knowledge/31-weak-move-selection.md) | [設計仕様](plans/2026-09-25-weak-move-selection-design.md) | [実装計画](plans/2026-09-25-weak-move-selection.md) | [引き継ぎ](handover-weak-move-selection.md) |
| 人間対コンピュータのCLI進行（第39回） | [第39回](learning/39-human-vs-computer-cli.md) | [人間対コンピュータ](knowledge/32-human-vs-computer-cli.md) | [設計仕様](plans/2026-09-26-human-vs-computer-cli-design.md) | [実装計画](plans/2026-09-26-human-vs-computer-cli.md) | [引き継ぎ](handover-human-vs-computer-cli.md) |
| 駒打ち順の保守（第40回） | [第40回](learning/40-drop-order-maintenance.md) | [駒打ち順](knowledge/32-drop-order-maintenance.md) | [設計仕様](plans/2026-09-26-drop-order-maintenance-design.md) | [実装計画](plans/2026-09-26-drop-order-maintenance.md) | [引き継ぎ](handover-drop-order-maintenance.md) |
| 対局モードの選択（第41回） | [第41回](learning/41-game-mode-selection.md) | [対局形式](knowledge/33-game-mode-selection.md) | [設計仕様](plans/2026-09-27-game-mode-selection-design.md) | [実装計画](plans/2026-09-27-game-mode-selection.md) | [引き継ぎ](handover-game-mode-selection.md) |
| CLIでの明示的な保存・読込（第42回） | [第42回](learning/42-cli-save-load.md) | [JSONファイル保存](knowledge/30-game-record-file-save.md) | [設計仕様](plans/2026-09-27-cli-save-load-design.md) | [実装計画](plans/2026-09-27-cli-save-load.md) | [引き継ぎ](handover-cli-save-load.md) |
| 文書構成の棚卸しと入口設計（第43回） | [第43回](learning/43-document-structure-audit.md) | — | [設計仕様](plans/2026-09-27-repository-document-navigation-design.md) | — | [引き継ぎ](handover-repository-foundation-docs-audit.md) |
| 文書ナビゲーションの最小改善（第44回） | [第44回](learning/44-document-navigation.md) | — | [設計仕様](plans/2026-09-27-repository-document-navigation-design.md) | [実装計画](plans/2026-09-27-repository-document-navigation.md) | [開始時点の引き継ぎ](handover-repository-foundation-document-navigation.md) |
| 古い文書記述の是正（第45回） | [第45回](learning/45-stale-document-correction.md) | — | [設計仕様](plans/2026-09-27-stale-document-correction-design.md) | [実装計画](plans/2026-09-27-stale-document-correction.md) | [開始時点の引き継ぎ](handover-repository-foundation-stale-document-correction.md) |
| コードとユニットテストの構造レビュー（第46回） | [第46回](learning/46-code-and-unit-test-structure-review.md) | — | [設計仕様](plans/2026-09-28-code-and-unit-test-structure-review-design.md) | [実装計画](plans/2026-09-28-code-and-unit-test-structure-review.md) | [開始時点の引き継ぎ](handover-code-and-unit-test-structure-review.md) |
| CLI実行入口のスモークテスト配置を明確にする（第47回） | [第47回](learning/47-cli-entrypoint-smoke-test-placement.md) | — | [設計仕様](plans/2026-09-29-cli-entrypoint-smoke-test-placement-design.md) | [実装計画](plans/2026-09-29-cli-entrypoint-smoke-test-placement.md) | [開始時点の引き継ぎ](handover-cli-entrypoint-smoke-test-placement.md) |
| `test_movegen.py` の局面スナップショット補助を一つにする（第48回） | [第48回](learning/48-movegen-position-snapshot-helper.md) | — | [設計仕様](plans/2026-09-29-movegen-position-snapshot-helper-design.md) | [実装計画](plans/2026-09-29-movegen-position-snapshot-helper.md) | [開始時点の引き継ぎ](handover-movegen-position-snapshot-helper.md) |
| CLIの駒名入出力対応を一つの定義から導く（第49回） | [第49回](learning/49-cli-piece-name-single-definition.md) | — | [設計仕様](plans/2026-09-30-cli-piece-name-single-definition-design.md) | [実装計画](plans/2026-09-30-cli-piece-name-single-definition.md) | [開始時点の引き継ぎ](handover-cli-piece-name-single-definition.md) |
| CLIコマンド解析の公開境界を設計し直す（第50回） | [第50回](learning/50-cli-command-parsing-public-boundary.md) | — | [設計仕様](plans/2026-09-30-cli-command-parsing-public-boundary-design.md) | [実装計画](plans/2026-09-30-cli-command-parsing-public-boundary.md) | [開始時点の引き継ぎ](handover-cli-command-parsing-public-boundary.md) |
| CLIの `help` 表示（第51回） | [第51回](learning/51-cli-help-display.md) | — | [設計仕様](plans/2026-10-01-cli-help-display-design.md) | [実装計画](plans/2026-10-01-cli-help-display.md) | [開始時点の引き継ぎ](handover-cli-help-display.md) |
| 対局中の持ち駒表示（第52回） | [第52回](learning/52-cli-hand-display.md) | [持ち駒表示](knowledge/34-cli-hand-display.md) | [設計仕様](plans/2026-10-01-cli-hand-display-design.md) | [実装計画](plans/2026-10-01-cli-hand-display.md) | [開始時点の引き継ぎ](handover-cli-hand-display.md) |
| `test_movegen.py` の `_hand_counts` 重複再評価（第53回） | [第53回](learning/53-movegen-hand-counts-review.md) | — | — | — | [開始時点の引き継ぎ](handover-movegen-hand-counts-review.md) |
| ShogiHomeとUSIの接続範囲（第54回） | [第54回](learning/54-usi-shogihome-connection-scope.md) | — | — | — | [開始時点の引き継ぎ](handover-usi-shogihome-connection-scope.md) |
| USI指し手表記と内部の一手の対応（第55回） | [第55回](learning/55-usi-move-notation.md) | [USI一手表記](knowledge/usi-move-notation.md) | [設計仕様](plans/2026-10-02-usi-move-notation-design.md) | [実装計画](plans/2026-10-02-usi-move-notation-implementation-plan.md) | [開始時点の引き継ぎ](handover-usi-move-notation.md) |
| USIの平手手順から局面を再現（第56回） | [第56回](learning/56-usi-position-replay.md) | [局面再現](knowledge/usi-position-replay.md) | [設計仕様](plans/2026-10-02-usi-position-replay-design.md) | [実装計画](plans/2026-10-02-usi-position-replay-implementation-plan.md) | [開始時点の引き継ぎ](handover-usi-position-replay.md) |
| USIエンジンとして一手を返す（第57回・実装、レビュー、記録承認、main取り込み済み） | [第57回](learning/57-usi-engine-response.md) | [USIエンジン応答](knowledge/usi-engine-response.md) | [設計仕様](plans/2026-10-03-usi-engine-response-design.md) | [実装計画](plans/2026-10-03-usi-engine-response-implementation-plan.md) | [開始時点の引き継ぎ](handover-usi-engine-response.md) |
| USIコマンド型・独立状態APIの導入要否を再検討（第58回・main取り込み、理解確認、全281テスト完了） | [第58回](learning/58-usi-command-state-api-review.md) | [USIエンジン応答](knowledge/usi-engine-response.md) | [設計仕様](plans/2026-10-04-usi-command-state-api-review-design.md) | [実装計画](plans/2026-10-04-usi-command-state-api-review-implementation-plan.md) | [開始時点の引き継ぎ](handover-usi-command-state-api-review.md) |
| ShogiHomeで平手対局する（第59回・main取り込み、全283テスト、理解確認まで完了） | [第59回](learning/59-shogihome-even-game.md) | [ShogiHome平手対局](knowledge/usi-shogihome-gameplay.md) | — | [実装計画](plans/2026-10-04-shogihome-gameplay-implementation-plan.md) | [開始時点の引き継ぎ](handover-usi-shogihome-gameplay.md) |
| 息子によるShogiHome試用（第60回・実対局、理解確認まで完了） | [第60回](learning/60-shogihome-son-trial.md) | [ShogiHome平手対局](knowledge/usi-shogihome-gameplay.md) | — | — | [開始時点の引き継ぎ](handover-son-shogihome-trial.md) |
| ShogiHome自動投了時のUSI通信確認（第61回・実機観察と理解確認まで完了） | [第61回](learning/61-shogihome-auto-resign-logs.md) | [ShogiHome平手対局](knowledge/usi-shogihome-gameplay.md) | — | — | [開始時点の引き継ぎ](handover-shogihome-auto-resign-logs.md) |
| ShogiHome接続手順書の作成（第62回・実証、理解確認まで完了） | [第62回](learning/62-shogihome-connection-guide.md) | [ShogiHome接続手順書](shogihome-connection-guide.md)、[専用Codexスキル](../.agents/skills/shogihome-connection/SKILL.md) | — | — | [開始時点の引き継ぎ](handover-shogihome-connection-guide.md) |
| 最弱モードを残す難易度選択の最小設計（第63回・設計と理解確認完了） | [第63回](learning/63-weakest-mode-difficulty-selection.md) | [USIエンジン応答](knowledge/usi-engine-response.md) | [本人承認済み設計仕様](plans/2026-10-05-weakest-mode-difficulty-selection-design.md) | — | [開始時点の引き継ぎ](handover-weakest-mode-difficulty-selection.md) |
| 最弱モードを残す難易度選択の実装（第64回・レビュー、main取り込み、全305テスト、理解確認まで完了） | [第64回](learning/64-weakest-mode-difficulty-selection-implementation.md) | [一手選択](knowledge/31-weak-move-selection.md)、[USI応答](knowledge/usi-engine-response.md) | [承認済み設計仕様](plans/2026-10-05-weakest-mode-difficulty-selection-design.md) | [実装計画](plans/2026-10-05-weakest-mode-difficulty-selection-implementation-plan.md) | [開始時点の引き継ぎ](handover-weakest-mode-difficulty-selection-implementation.md) |
| ShogiHomeでDifficulty設定を確認（第65回・実機観察、理解確認完了） | [第65回](learning/65-shogihome-difficulty-verification.md) | — | — | — | [開始時点の引き継ぎ](handover-shogihome-difficulty-verification.md) |
| ShogiHomeでMaterialの着手への影響を確認（第66回・実機観察、理解確認完了） | [第66回](learning/66-shogihome-material-move-effect.md) | — | — | — | [開始時点の引き継ぎ](handover-shogihome-material-move-effect.md) |
| SFEN局面変換（第67回・main統合、全326テスト、理解確認まで完了。ShogiHome実機確認は未実施） | [第67回](learning/67-sfen-position-conversion.md) | [SFEN局面表記](knowledge/sfen-position-notation.md) | [設計仕様](plans/2026-10-07-sfen-position-conversion-design.md) | [実装計画](plans/2026-10-07-sfen-position-conversion-implementation-plan.md) | [開始時点の引き継ぎ](handover-sfen-position-conversion.md) |
| ShogiHome画面へのSFEN貼り付け確認（第68回・実機確認、理解確認完了） | [第68回](learning/68-shogihome-sfen-paste.md) | [SFEN局面表記](knowledge/sfen-position-notation.md) | — | — | [開始時点の引き継ぎと実施結果](handover-shogihome-sfen-paste.md) |
| ShogiHomeからkaname-shogiへSFEN局面を渡す（第69回・実機で一例確認、理解確認完了） | [第69回](learning/69-shogihome-sfen-engine.md) | [SFEN局面表記](knowledge/sfen-position-notation.md)、[ShogiHome対局](knowledge/usi-shogihome-gameplay.md) | — | — | [開始時点の引き継ぎ・実施後追記](handover-shogihome-sfen-engine.md) |
| SFEN手数欄が4から1になった理由（第70回・調査・理解確認・記録内容確認済み） | [第70回](learning/70-shogihome-sfen-move-number.md) | [SFEN局面表記](knowledge/sfen-position-notation.md) | — | — | [開始時点の引き継ぎ](handover-shogihome-sfen-move-number.md) |
| ShogiHome専用スキルの現行化（第71回・main統合・文書検証済み、最終理解確認待ち） | [第71回](learning/71-shogihome-connection-skill-update.md) | [専用スキル](../.agents/skills/shogihome-connection/SKILL.md)、[接続手順書](shogihome-connection-guide.md) | — | — | [開始時点の引き継ぎ](handover-shogihome-connection-skill-update.md) |

## 例外と履歴の読み方

- 初期段階の設計は `docs/design/` にあります。後期の設計仕様は `docs/plans/*-design.md` にあり、今後の設計仕様もこちらへ置きます。既存ファイルは移動しません。
- `docs/knowledge/32-drop-order-maintenance.md` と `docs/knowledge/32-human-vs-computer-cli.md` は番号が重複しています。番号ではなく「駒打ち順」「人間対コンピュータ」という題名とテーマで識別します。
- `docs/superpowers/plans/2026-09-13-initial-position.md` は初期配置実装時の計画履歴です。
- 引き継ぎに記録されたブランチ、HEAD、テスト件数、次の行動は作成時点の情報です。現在値は `git status --short --branch` と現役の再開案内で確認します。

## 更新規則

- 各テーマの完了時に、該当するテーマ行とリンクを更新します。
- 進行中の細かな状態と次の一手は `resume.md` と現在の実装計画に置き、この索引へ重複させません。次テーマを新しいセッションへ引き継ぐときだけ、再開用プロンプトを `resume.md` と新しい引き継ぎの両方へ記録します。
- 新しい文書種別を作る前に、既存の単一索引から到達できない理由があるかを確認します。
