# 玉周辺安全度の合成評価

## 指標と評価

`is_square_attacked(board, target, attacking_side)` は、指定側の盤上駒が対象マスへ現在利いているかを返す読み取り操作である。合法な移動先とは異なり、ピンされた駒の利きと、味方・相手の駒が占有するマスへの利きを含む。対象マスが攻撃側の駒で占有される場合は複製盤上でそのマスだけを空け、他の遮蔽を残す。手番・持ち駒・合法性は参照しない。

指定側の玉について、盤内の隣接マスのうち相手の利きがある異なるマスの数を危険マス数 `D` とする。玉自身のマス、盤外、距離2以上、持ち駒から将来打てるマスは含めない。危険マス数は0～8で、合法な逃げ先の数や詰みの判定ではない。

指定側を `P`、相手を `Q` とすると、安全度差は `S(P) = D(Q) - D(P)`。指定側の玉周辺が相手より安全なほど正になる。両側に玉がちょうど一枚ずつ必要であり、欠落・重複時は `king_danger_count` と `king_safety_balance` が `ValueError("先手・後手の玉はそれぞれ1枚必要です")` を送出する。

既存の駒得差を `M(P)` とし、通常評価は `E(P) = 10 × M(P) + S(P)`。係数は教材用の仮設定で、`KingSafetyWeights(material=10, safety=1)` が既定値である。設定は凍結dataclassで、駒得係数は1以上、安全度係数は0以上の整数に限る。bool・floatは拒否する。安全度係数を0にしても両玉の前提は検査する。

## 一手選択との接続

新評価は通常の整数評価であり、詰みを表す値を作らない。既存 `choose_one_ply_move` に評価操作として注入する。

```python
selected = choose_one_ply_move(
    position,
    moves,
    rng,
    evaluate=evaluate_material_king_safety,
)
```

選択器は各手を複製局面へ適用し、開始側の視点で評価する。通常評価の値にかかわらず一手詰みを優先し、詰み枝では通常評価を呼ばない。この接続で選択器本体や既存の方針を変更しない。

## 比較CLIへの接続

比較CLIには `material-king-safety-material-only`（対照）と `material-king-safety`（候補）を用意する。両方式は同じ一手選択と一手詰み優先を使い、駒得重み10・安全度重み0または1で合成する。安全度重み0でも危険度計算と両玉の前提検査を行う。既存の `material` は詰み優先の選択経路が異なり、変更していない。

比較条件には方式名と重みを記録する。分析CLIが読むのは従来どおり種一覧を使うconditions v2/v3で、主乱数種の結果は分析対象外である。対象局面と重み、接続テストの範囲は[C2学習記録](../learning/c2-king-safety-evaluation.md)と[C2設計](../plans/2026-10-28-c2-king-safety-evaluation-design.md)を参照する。

## 範囲と限界

- この指標は盤上の現在の利きを使う小さな静的指標で、勝敗・王手回避・合法な玉の逃げ先を保証しない。
- 重みの棋力上の妥当性や一般的な実時間性能は未検証。予備比較の実測と限界は[C2学習記録](../learning/c2-king-safety-evaluation.md)にある。
- 通常対局CLI・USIへの公開、通常CLIのSFEN入出力、飛車可動性バージョン2、二手・四手への適用は含めない。
- 確認比較条件は[承認済み設計案](../plans/2026-10-28-c2-king-safety-confirmation-comparison-design.md)で固定済み。比較結果と実際の棋力差は未検証。

設計は[承認済み仕様](../plans/2026-10-28-king-safety-design.md)、実装手順と検証は[承認済み計画](../plans/2026-10-28-king-safety-implementation-plan.md)と[学習記録](../learning/king-safety-design.md)を参照する。
