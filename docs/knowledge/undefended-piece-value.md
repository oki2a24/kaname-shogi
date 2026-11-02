# 支えのない被攻撃駒の価値合計

## 集計する対象

盤上の非玉駒について、相手の盤上駒から利かれ、味方の盤上駒から支えられていない駒を対象にする。対象一枚は攻撃元の数にかかわらず一度だけ数え、その駒種の現在の参考価値を合計する。玉は対象から除くが、攻撃元と支え役には含める。持ち駒と手番は対象にしない。

`attacked_undefended_piece_value(position, side) -> int` は指定側の価値合計を返す読み取り操作である。`attacked_undefended_piece_value_balance(position, perspective) -> int` は、相手側の価値合計から視点側の価値合計を引く。正なら視点側の危険が小さい。価値は既存の `piece_reference_value` へ委譲し、成駒も成った後の価値を使う。

利き・遮蔽・ピンの扱いは既存の `is_square_attacked` と同じで、合法に取れるか、取り返せるか、実際に駒を失うかは判定しない。局面の盤面・手番・持ち駒を変更せず、価値・利きの依存操作からの例外を伝える。玉なし部分局面を受け付ける。

```text
側 s の価値合計 Cᵥ(P, s)
  = 相手の利きがあり、味方の支えがない盤上非玉駒の参考価値の合計

視点 p の価値合計差 Dᵥ(P, p)
  = Cᵥ(P, 相手(p)) − Cᵥ(P, p)
```

ここで使う参考値は、北海道大学の講義資料「ゲームプレイング」7ページにある谷川浩司の参考値をコード化した既存表である。歩1・銀8・飛車15などの値であり、公式な勝敗点ではない。[一次資料PDF](https://ocw.hokudai.ac.jp/wp-content/uploads/2016/01/IntelligentInformationProcessing-2005-Note-06.pdf)

## 合成評価

記号は既存の意味を保つ。

- M（駒得）：視点側の駒価値合計から相手側を引く。
- U（支えのない被攻撃駒の枚数差）：相手側の対象枚数から視点側を引く。既存方式で使う。
- V（支えあり低価値駒脅威の枚数差）：相手側の対象枚数から視点側を引く。既存方式で使う。

今回の価値合計差に新しい略号は割り当てない。従来方式と今回の方式は次の式で区別する。

```text
従来点 = 10 × M（駒得）+ U（枚数差）+ V（支えあり低価値駒脅威の枚数差）
今回点 = 10 × M（駒得）+ 1 × 支えのない被攻撃駒の価値合計差
         + V（支えあり低価値駒脅威の枚数差）
```

`PieceThreatValueWeights` は係数を保持する変更不能な設定データで、既定値は `material=10`、`undefended_value=1`、`supported_threat=1`。駒得係数は1以上、他の係数は0以上の整数で、`bool` と `float` は受け付けない。`evaluate_material_piece_threat_value(position, perspective, *, weights=...) -> int` はM（駒得）・価値合計差・V（支えあり低価値駒脅威）を一度ずつ取得して合成する読み取り操作である。旧U（枚数差）は合成しない。追加項の係数が0でも依存操作を呼び、その例外を伝える。

## 固定例と確認範囲

設計書の手計算を独立期待値として使った。表は「従来点／今回点」である。

| 局面 | 従来点 | 今回点 | 確認する違い |
| --- | ---: | ---: | --- |
| A | 99 | 85 | 支えのない飛車と、相手の桂の危険を枚数でなく価値で比べる |
| B | 99 | 99 | 同じ枚数差でも、対象の価値に応じて評価差が変わる |
| C | 179 | 179 | 支えを加えた駒は価値合計から外れ、V（支えあり低価値駒脅威）側へ移る |
| D | 308 | 294 | 両側の対象価値、符号、V（支えあり低価値駒脅威）を合わせて確認する |
| E | 20 | 13 | 両側に対象があるときの価値差を確認する |

一手選択へ注入する確認では、飛車を金で支える手が従来点では両候補230の同点、今回点では支え手230・非支え手216となり、先後と候補順を入れ替えても支え手を選んだ。一手詰み優先、空候補、同点抽選、例外伝播も既存の一手選択器で確認した。これは固定局面と候補間の確認で、全合法手の最善、合法な交換損得、係数の最適性、一般棋力の改善を示さない。

集計の加算確認では、先手の支えのない飛車15と銀8、後手の歩1二枚を別々に狙わせ、価値合計23／2、先手視点差−21を固定値で確認する。攻撃元が複数でも一枚を二重に加算しないテストとは別に、同じ側の複数対象を加算する契約を検査する。

## 比較CLIでの方式

比較専用policy `material-piece-threat-value-v1` は、従来 `material-piece-threat-v1` と別の評価器・重みを使う。従来式は `10 × M（駒得）+ U（支えのない被攻撃駒の枚数差）+ V（支えあり低価値駒脅威の枚数差）`、候補式は `10 × M（駒得）+ 1 × 支えのない被攻撃駒の価値合計差 + V（支えあり低価値駒脅威の枚数差）` で、旧Uは候補へ重ねない。conditions JSONでは旧方式の `undefended` と候補方式の `undefended_value` を別キーとして記録する。新policyは比較CLIだけで使い、通常CLI・USIには公開しない。

新しい固定7局面の手順とM/U/価値/V期待値は[比較局面テスト](../../tests/test_undefended_piece_value_comparison_positions.py)および[比較局面JSON](../../data/comparison/undefended-piece-value-positions-v1.json)にある。テストは局面内・セット内の一意性に加え、追跡済みの旧U・V pilot/confirmation・C2開始SFENとの非重複を検査する。対局比較・分析の実測とその適用範囲は[学習記録](../learning/undefended-piece-value.md)、条件・保存形式と独立組得点の契約は[比較の知識メモ](search-comparison.md)を参照する。ShogiHomeでのU候補実践はアクセス可能との本人連絡後に再提案する保留目標である。

実装は [`undefended_piece_value.py`](../../kaname_shogi/undefended_piece_value.py) と [`material_piece_threat_value.py`](../../kaname_shogi/material_piece_threat_value.py)、契約・独立期待値は関連する `tests/test_undefended_piece_value*.py` と `tests/test_material_piece_threat_value.py` にある。判断理由・回答・検証・レビューは[学習記録](../learning/undefended-piece-value.md)、承認仕様は[設計書](../plans/2026-11-02-undefended-piece-value-design.md)、手順と実施状況は[実装計画](../plans/2026-11-02-undefended-piece-value-implementation-plan.md)を参照する。
