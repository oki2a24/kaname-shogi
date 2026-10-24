# 飛車可動性を加えた一手評価

## 評価の契約

`rook_mobility_balance(position, perspective)` は、盤上の未成飛車ごとの移動候補マス数を合計し、指定側から相手側を引く。候補は既存の `rook_move_candidates` に委ねる。各飛車の寄与を合算するため、複数の飛車に共通する到達マスも飛車ごとに数える。手番・持ち駒・自玉の安全・相手の利きは評価しない。竜と持ち駒の飛車は可動性対象外である。定義上、同じ到着マスへの成り・不成を二重計上しない。

`RookMobilityWeights` は変更できない名前付き設定データで、既定値は駒得係数10、飛車可動性係数1。駒得係数は正整数、可動性係数は0以上の整数である。`evaluate_material_rook_mobility(position, perspective, *, weights)` は次の通常点を返す。

```text
weights.material × material_balance(position, perspective)
+ weights.mobility × rook_mobility_balance(position, perspective)
```

重みは式へ散らさず設定データに置き、環境変数や外部設定ファイルからは読み込まない。係数10は既存の駒得尺度に対する今回の仮重みであり、棋力向上を実証した値ではない。

## 一手選択との接続境界

`choose_one_ply_move(position, moves, rng, *, evaluate)` は評価操作を引数で受ける。各手を独立した複製局面へ適用し、開始局面の手番を評価視点として通常点を比べる。一手で相手を詰ませる手は通常点と別の優先区分で扱い、通常点の大きさで詰みが逆転しない。同点最高の候補だけから乱数器で一手を選ぶ。候補が空なら `None`。二手以降の探索はしない。

この選択部品は特定の評価関数へ依存せず、既存の選択方針、CLI、USIにも接続していない。既存の一手駒得の挙動と評価表は[合法手列挙と方針別の一手選択](31-weak-move-selection.md)を参照する。

## 確認範囲と限界

固定局面で遮蔽・盤端・複数飛車・先後視点・竜と持ち駒の除外を確認した。合成評価は独立に計算した値173/176、逆視点−173/−176、別重み71などで検査した。一手選択は評価差替え、詰み優先、同点抽選、空候補、局面枝の分離、例外伝播を固定局面で確認した。具体的な期待値、テスト検出対象、全体検証は[学習・実施記録](../learning/rook-mobility-design.md)と[承認済み実装計画](../plans/2026-10-24-rook-mobility-implementation-plan.md)を参照する。

全配置、全重み、棋力・勝率、評価要素の相互作用は検証していない。合法な移動先の安全確認、竜・持ち駒を含む発展版は別候補として扱う。通常CLIのSFEN入出力は別テーマである。

定義：[飛車可動性](../../kaname_shogi/rook_mobility.py)、[駒得・可動性の合成評価](../../kaname_shogi/material_rook_mobility.py)、[評価差替式一手選択](../../kaname_shogi/one_ply_selection.py)
