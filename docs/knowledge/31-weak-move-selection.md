# 合法手列挙と方針別の一手選択：参照メモ

更新日：2026-10-31

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

## 支えのない狙われた駒を加える一手方針

`MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE` は既存の `10M+U` 評価を一手選択へ使う方針データ。各候補手を独立した複製局面へ適用し、`evaluate_material_undefended_piece` が返す開始手番側の評価値を比べ、最大候補から注入乱数器で選ぶ。`M` は既存の駒得差、`U` は相手の利きがあり味方の支えがない非玉の駒数の差で、重みは `10 × M + 1 × U`。定義と比較条件は[駒の連携評価メモ](undefended-piece-evaluation.md)にある。

制御付き一手探索では、候補を評価する前に一手詰みを調べ、勝ちを通常評価より優先する。停止時の合法な予備手・完了候補・探索制御は既存の制御付き探索と共有する。二手・四手先の評価はこの方針に加えない。実際のCLI/USI接続では `game_search.search_move` から制御付き一手経路へ渡す。

## 二手先読み（駒得）の内部方針

`MoveSelectionPolicy.TWO_PLY_MATERIAL` は二手比較を指定する方針データ。`choose_move` は各候補を独立した複製へ適用し、相手の全合法応手もそれぞれ別の複製へ適用する操作である。開始手番側の視点を固定し、応手後の最小評価が最大となる候補を選ぶ。最高同点候補だけを元の候補順で集め、注入乱数器で一回抽選する。元局面・双方の持ち駒・候補データを変更しない。

評価は勝ち `(1, 0)`、通常 `(0, 駒得差)`、負け `(-1, 0)`。一手後に相手が詰みなら勝ち、応手後に開始側が詰みなら負けとし、通常点の大きさで勝敗が逆転しない。勝ち同士・負け同士は同点。開始時の候補なしはNone、途中の詰みでない手なしは静的な駒得差とする。自分一手＋相手一手で駒得探索を止める。既存の詰み判定の防御確認は、その先の駒得探索には含めない。

タスク1では通常比較とその補強を検証した。タスク2の最初の2項目では、実局面の詰み勝ち・応手後の詰み負けと、通常値±1000000との順序を先後両方で確認した。負け側は詰ませる応手群の先頭・中間・末尾でも同じ評価になることを確認した（[詰み優先の記録](../learning/two-ply-mate-priority.md)）。タスク2の勝敗混在・同点・境界・枝独立性の検証も完了した（[枝独立性とタスク2完了の記録](../learning/two-ply-branch-independence.md)）。設計理由と実績は[承認済み設計](../plans/2026-10-10-evaluation-next-stage-design.md)と[実装の学習記録](../learning/two-ply-basic-comparison.md)を参照する。CLIの三択追加は[CLIの実施記録](../learning/cli-three-policies.md)を参照する。USIへの三択通知・受付は[実施記録](../learning/usi-three-policies.md)を参照する（main取り込み・検証済み）。

## 利用面

- CLIは対局形式に応じてコンピュータ側の方針を尋ねる。CVCは先手、後手の順に別々に選択する。空入力はそれぞれランダム。候補はランダム、一手駒得、二手先読み（駒得）、全幅読み（最大4手）、αβ枝刈り（最大4手）、一手駒得＋支えのない狙われた駒。選択は一局中固定する。
- USIは `Difficulty` comboを通知し、`Random` / `Material` / `TwoPlyMaterial` / `FullWidth4` / `AlphaBeta4` / `MaterialUndefendedPiece` を受け付ける。未設定時はRandom。設定はプロセス中に保持し、局の最初のgoから `usinewgame` まで局内固定する。新値固有の局中固定・次局継承、未知値保持、応答範囲は[USIエンジン応答](usi-engine-response.md)と[今回の学習記録](../learning/undefended-piece-coordination-evaluation.md)を参照する。先行する三択やUSI各境界の実施記録はそれぞれのリンク先の歴史的検証範囲を示す。
- ShogiHome画面でのこの設定や実対局は、この実装テーマでは確認していない。

## 対象外

- 二手を超える探索、定跡、棋力保証、段級位の指定
- 千日手、持将棋、入玉、時間切れ、反則勝敗
- `GameRecord` の棋譜型と選択処理の変換

定義：[kaname_shogi/move.py](../../kaname_shogi/move.py)、[kaname_shogi/movegen.py](../../kaname_shogi/movegen.py)

一次資料：[日本将棋連盟「対局規則」](https://www.shogi.or.jp/match/taikyoku_rules/)、[日本将棋連盟「FAQ（持将棋・入玉の点数計算）」](https://www.shogi.or.jp/faq/rules/)
