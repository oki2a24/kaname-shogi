# 支えがある駒への低価値駒の利き（V）

## 現在の定義

盤上の対象駒が玉以外で、味方の盤上駒に支えられ、かつ現在価値が対象より低い相手の盤上非玉駒に利かれていれば、対象を一枚と数える。対象一枚は攻撃元が複数でも一回だけ数える。価値が同じか高い攻撃元だけなら数えない。価値差は点数にしない。

玉は対象・低価値攻撃元から除外し、支え役には含める。持ち駒と手番は無視する。成駒は現在の駒種の価値と利きを使う。利きは既存の幾何学的な盤上利きと同じ意味で、ピンされた駒を含む。遮蔽は現在の盤面を保つ。合法な駒取り、取り返し、自玉安全、詰み、将来の駒打ちは判定しない。

側 `s` の枚数を `C_V(P, s)` とすると、視点 `p` の差は `V(P, p) = C_V(P, 相手(p)) - C_V(P, p)`。正なら視点側の対象が少ない。

通常評価の合成は `E(P, p) = 10M(P, p) + U(P, p) + V(P, p)`。Mは既存の駒得差、Uは支えのない狙われた駒の差であり、いずれも正を視点側有利とする。名前付きの `PieceThreatWeights` で各係数を指定できる。materialは1以上、U/Vは0以上の整数。これは一手選択器へ注入可能な通常点で、比較CLIは `material-piece-threat-v0`（10M+U+0V）と `material-piece-threat-v1`（10M+U+1V）を使う。通常CLIの候補7とUSI `MaterialSupportedPieceThreat` は既存V1方針へ対応し、M=10、U=1、V=1で一手選択する。V0は比較CLI専用のまま。比較で改善を支持した結果は事前固定6局面・一手選択・指定条件の範囲に限られ、一般局面の棋力向上は示さない。比較実装・結果と通常CLI/USI接続の実績は[学習記録](../learning/supported-piece-lower-value-threat.md)を参照する。

## 現在の公開操作

- `piece_reference_value(PieceType) -> int`：玉以外の盤上駒の既存参考価値を返す。
- `is_piece_attacking_square(Board, Square, Square) -> bool`：指定された盤上駒が対象マスへ利くかを既存候補生成へ委譲して調べる。
- `supported_lower_value_threat_count(Position, Side) -> int`：指定側のV対象枚数。
- `supported_lower_value_threat_balance(Position, Side) -> int`：指定視点のV差。
- `PieceThreatWeights` と `evaluate_material_piece_threat(Position, Side, *, weights=...) -> int`：M/U/Vを各一度計算して係数合成する。U/V係数が0でも依存操作を呼び、例外を伝える。

設計・引数・戻り値・不変性の詳細は[承認済み設計](../plans/2026-10-31-supported-piece-lower-value-threat-design.md)と[実装計画](../plans/2026-10-31-supported-piece-lower-value-threat-implementation-plan.md)を参照する。

## 検証の意味と限界

固定局面、先後反転、指定駒の利き、一手選択、比較CLIの方式名・条件・成果物reader、通常CLI/USI接続を確認した。比較CLIのV条件は、baseline/candidateごとに `material=10`、`undefended=1`、`supported_threat=0/1`、`mate_priority=true`を保存する。旧U成果物の重みとsummary順は維持する。通常CLI/USIではV1だけを一手選択へ接続し、V0は公開しない。先後を逆にした通常CLI CVC二局は、選択表示・両側の実着手・終局を確認した操作実証であり、棋力やV単独の効果を判定しない。Vの一般局面への効果、ShogiHomeでの選択・対局、二手・四手への適用、玉安全度との合成、飛車可動性v2、通常CLIのSFEN入出力は未検証または未接続。
