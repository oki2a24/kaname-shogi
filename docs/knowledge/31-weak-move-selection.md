# 合法手列挙と方針別の一手選択：参照メモ

更新日：2026-10-10

## 中立な一手データと合法手一覧

- `BoardMove` は出発 `Square`、到着 `Square`、`promote` を持つ変更不可の盤上移動データ。
- `DropMove` は `BasicPieceType` と打ち先 `Square` を持つ変更不可の駒打ちデータ。
- `Move` は上のどちらかを表す型注釈。いずれも局面を変更する操作ではない。
- 実際の適用は `apply_move` / `apply_drop` が担う。棋譜の `RecordedMove` / `RecordedDrop` とは責務を分ける。
- `legal_moves(position)` は現在実装済みの規則で適用できる `Move` の固定順タプルを返し、元の局面を変更しない。

列挙順は強さの優先順位ではなく、再現できる一覧を作るために固定している。`has_legal_move(position)` は一覧が空かどうかを使って判定する。

## 最弱の一様ランダム

`choose_weak_move(moves, rng)` は渡された合法手を再検証せず、注入された `random.Random` から一手を一様に選ぶ。空タプルなら `None` を返す。これは終局・投了・勝敗を表さない。

`MoveSelectionPolicy.RANDOM` と `choose_move(position, moves, policy, rng)` は、最弱方針を既存の `choose_weak_move` へ委譲する。未指定時の既定値もRANDOMであり、従来の選択動作を保つ。

## 駒得を考える方針

`material_balance(position, perspective)` は指定側の盤上と持ち駒を合算し、相手側の合計を引いた値を返す。盤上は成駒を含む現在の駒種、持ち駒は基本駒種で数える。玉将は盤上の点数に含めない。

| 駒 | 盤上の値 | 成駒 | 成駒の値 | 持ち駒の値 |
| --- | ---: | --- | ---: | ---: |
| 歩 | 1 | と金 | 12 | 1 |
| 香 | 5 | 成香 | 10 | 5 |
| 桂 | 6 | 成桂 | 10 | 6 |
| 銀 | 8 | 成銀 | 9 | 8 |
| 金 | 9 | — | — | 9 |
| 角 | 13 | 馬 | 15 | 13 |
| 飛 | 15 | 竜 | 17 | 15 |
| 玉・王 | 点数に含めない | — | — | 持ち駒にできない |

数値は[北海道大学講義資料 p.6「参考：将棋の駒の価値（谷川浩司）」](https://ocw.hokudai.ac.jp/wp-content/uploads/2016/01/IntelligentInformationProcessing-2005-Note-06.pdf)の参考値を教材用に採用した。通常の将棋の勝敗は詰みを中心とした規則で決まり、この値の合計を競うものではない。[日本将棋連盟の対局規則](https://www.shogi.or.jp/match/taikyoku_rules/)と、入玉・持将棋の成立後に使う規則上の点数計算を説明する[日本将棋連盟FAQ](https://www.shogi.or.jp/faq/rules/)とは区別する。

`choose_move(..., MoveSelectionPolicy.MATERIAL, ...)` は渡された各合法手を独立した複製局面へ一手だけ適用し、元の `side_to_move` から見た適用直後の `material_balance` を比べる。最高値の手だけを候補にし、同点は注入乱数器で選ぶ。相手の応手やその先の読みは含まず、局面と合法手一覧を変更しない。成駒を取った場合、既存の適用処理が基本駒種の持ち駒へ戻す。

これは探索付きの評価関数や棋力保証ではなく、駒得の変化を比較する一手の教材用ヒューリスティックである。

## 二手先読み（駒得）の内部方針

`MoveSelectionPolicy.TWO_PLY_MATERIAL` は二手比較を指定する方針データ。`choose_move` は各候補を独立した複製へ適用し、相手の全合法応手もそれぞれ別の複製へ適用する操作である。開始手番側の視点を固定し、応手後の最小評価が最大となる候補を選ぶ。最高同点候補だけを元の候補順で集め、注入乱数器で一回抽選する。元局面・双方の持ち駒・候補データを変更しない。

評価は勝ち `(1, 0)`、通常 `(0, 駒得差)`、負け `(-1, 0)`。一手後に相手が詰みなら勝ち、応手後に開始側が詰みなら負けとし、通常点の大きさで勝敗が逆転しない。勝ち同士・負け同士は同点。開始時の候補なしはNone、途中の詰みでない手なしは静的な駒得差とする。自分一手＋相手一手で駒得探索を止める。既存の詰み判定の防御確認は、その先の駒得探索には含めない。

タスク1では通常比較4件を検証した。詰み・境界・枝独立性の網羅検証は後続タスク2に残る。設計理由と実績は[承認済み設計](../plans/2026-10-10-evaluation-next-stage-design.md)と[実装の学習記録](../learning/two-ply-basic-comparison.md)を参照する。CLI・USIの選択肢にはまだ追加していない。

## 利用面

- CLIは対局形式を選んだ後、コンピュータが参加する場合に方針を尋ねる。空入力は「最弱（一様ランダム）」、もう一方は「駒得を考える」。選択は一局中固定する。
- USIは `Difficulty` comboを通知し、`Random` / `Material` を受け付ける。詳細とUSI状態の寿命は[USIエンジン応答](usi-engine-response.md)を参照する。
- ShogiHome画面でのこの設定や実対局は、この実装テーマでは確認していない。

## 対象外

- 二手を超える探索、定跡、棋力保証、段級位の指定
- 千日手、持将棋、入玉、時間切れ、反則勝敗
- `GameRecord` の棋譜型と選択処理の変換

定義：[kaname_shogi/move.py](../../kaname_shogi/move.py)、[kaname_shogi/movegen.py](../../kaname_shogi/movegen.py)

一次資料：[日本将棋連盟「対局規則」](https://www.shogi.or.jp/match/taikyoku_rules/)、[日本将棋連盟「FAQ（持将棋・入玉の点数計算）」](https://www.shogi.or.jp/faq/rules/)
