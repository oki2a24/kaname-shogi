# 支えのない狙われた駒の評価

## 枚数と差

盤上の非玉駒を、相手の利きが1つ以上あり、味方の支えが0なら一枚として数える。対象が占有するマスへの利きも含める。複数の攻撃元でも対象一枚は1であり、支えが一つでもあれば対象にしない。

`attacked_undefended_piece_count(position, side)` は指定側の対象枚数を返す読み取り操作である。玉は枚数の対象外だが、攻撃元と支え役に含める。成駒は成った後の動きで判定し、遮蔽も現在の盤面のとおりに扱う。ピンされた駒も既存利き操作の定義により利きへ含める。

`attacked_undefended_piece_balance(position, perspective)` は指定視点の相手側枚数から自分側枚数を引いた符号付き整数 `U` を返す。

```text
C(P) = P側の対象枚数
U(P) = C(相手側) - C(P)
```

手番と持ち駒は枚数に加えず、盤面・手番・持ち駒を変更しない。玉なしの部分局面も受け付ける。利きの有無を数えるのであり、合法な駒取り、取り返し、交換損得は判定しない。

## 駒得との合成

`UndefendedPieceWeights` は合成係数を名前で指定する凍結設定データである。既定値は `material=10`、`undefended=1`。materialはbool・floatを含まない1以上の整数、undefendedはbool・floatを含まない0以上の整数である。設定フィールドは生成後に代入できない。

`evaluate_material_undefended_piece(position, perspective, *, weights)` は既存の駒得差 `M` と上の差 `U` を各一度取得し、次の通常評価値 `E` を返す読み取り操作である。

```text
E(P) = weights.material × M(P) + weights.undefended × U(P)
```

undefendedを0にしてもUを計算する。依存先の例外を伝播し、入力局面を変更しない。これは通常の整数評価であり、詰みを表す特殊値は作らない。既存 `choose_one_ply_move` へ `evaluate=evaluate_material_undefended_piece` として渡すと、同操作が別に扱う一手詰み優先を保ったまま一手後の通常評価として使える。

設計局面A/B/Cでは、いずれも `M=14` で、先手視点の `U=-1/0/0`、既定Eは `139/140/140` となる。これらは固定局面の式と実装を確かめる値で、棋力や仮重みの妥当性を示す実戦結果ではない。

## 比較CLIへの接続

承認済みの比較CLIでは、同じ一手選択器と一手詰み優先を使い、次の2方式を選べる。違いはUの重みだけである。

| 比較方式 | 実効重み | 意味 |
| --- | --- | --- |
| `material-undefended-piece-material-only` | `material=10`, `undefended=0` | `10M` の対照。Uも計算するが評価値へ加えない |
| `material-undefended-piece` | `material=10`, `undefended=1` | `10M+U` の候補 |

両方式の接続先は比較CLIに限る。通常CLI・USIの方式選択肢や、保存棋譜の公開形式は変更しない。

## 境界と未検証事項

- 通常CLI・USI、二手・四手探索、通常利用向け方式には接続しない。通常CLIのSFEN入出力、飛車可動性バージョン2、玉周辺安全度との合成、ShogiHome対局も含めない。
- 固定局面で対象枚数・符号・成駒・玉・ピン・遮蔽・手番/持ち駒の無視、重み境界、例外伝播、選択器への注入と一手詰み優先を確認した。比較CLIの接続・保存・分析は小規模pipelineで確認した。
- 長時間比較は未実施であり、所要時間、手数上限率、未裁定率、得点区間は未測定。全局面、合法な駒取りや交換連鎖、最適重み、棋力・勝率、実時間性能も未検証。

実装は [`undefended_piece.py`](../../kaname_shogi/undefended_piece.py) と [`material_undefended_piece.py`](../../kaname_shogi/material_undefended_piece.py)、比較方式の接続は [`comparison_io.py`](../../kaname_shogi/comparison_io.py)・[`comparison.py`](../../kaname_shogi/comparison.py)・[`game_search.py`](../../kaname_shogi/game_search.py)、独立期待値とpipelineは関連する `test_undefended_piece*` にある。理由・検出範囲・検証結果は[学習記録](../learning/undefended-piece-coordination-evaluation.md)、承認仕様は[接続比較設計](../plans/2026-10-30-undefended-piece-comparison-design.md)、実施手順は[実装計画](../plans/2026-10-30-undefended-piece-comparison-implementation-plan.md)を参照する。
