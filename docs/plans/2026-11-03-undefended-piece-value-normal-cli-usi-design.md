# U二種類を区別する一手評価候補の通常CLI・USI接続：設計案

作成日：2026-11-03。本人は、比較済みの「U価値合計+V」を通常CLIへ候補として追加し、USIにも同時に接続する案を選んだ。本人は同日、本設計案を承認した。実装計画承認・コード変更承認はまだない。

## 目的

息子が対局時に方式の違いを見分けやすいよう、ランダム・評価項目・探索する手数を区別して表示する。特にUを「支えのない被攻撃駒の枚数差」と「同じ駒の価値合計差」に分け、通常CLIとShogiHomeの両方から選べる固定方式にする。

一局の着手差は操作観察であり、棋力や強さの証明ではない。比較CLIの確認結果も登録7局面の条件に限られる。

## 現行方式とUの二種類

Mは駒得差、Uの対象は相手に狙われて味方の支えがない盤上の非玉駒である。Uの数え方は二種類ある。

- **U枚数**：対象駒一枚を一枚として数え、相手側枚数から自分側枚数を引く。
- **U価値合計**：対象駒の参考価値を一枚ずつ合計し、相手側の合計から自分側の合計を引く。U枚数は重ねて加えない。
- **V**：味方に支えられた対象駒が、対象より価値の低い相手駒に狙われているとき一枚として数える差。

| 評価式 | 比較CLI | 現行の通常CLI / USI |
| --- | --- | --- |
| `10M` | U比較の対照方式として存在 | `Material` |
| `10M+U枚数` | `material-undefended-piece` | `MaterialUndefendedPiece` |
| `10M+U枚数+V` | `material-piece-threat-v1` | `MaterialSupportedPieceThreat` |
| `10M+U価値合計+V` | `material-piece-threat-value-v1` | 未公開。本案で通常CLI・USIへ追加する候補 |

比較専用の `material-piece-threat-value-v1` は、事前固定7局面の確認比較で `10M+U枚数+V` と比べられ、指定条件内で改善を支持した。これは一般棋力向上を示さない。比較専用方式名そのものはShogiHomeのDifficulty値として公開しない。

実装上は `MATERIAL_PIECE_THREAT_VALUE_V1` と評価器 `evaluate_material_piece_threat_value` が既にある。通常の一手選択から直接選ぶ分岐もある一方、対局で使う時計・停止制御付き経路の許可方針と評価候補判定には含まれず、通常CLIの候補表とUSI `Difficulty` にもない。表示だけ足すのでは足りず、制御付き経路まで通す必要がある。

## 分類と表示案

選択肢は、強さの段階ではなく、何を評価するか・何手先まで読むかで分類する。既存番号1〜7と動作は保ち、選択番号8だけを追加する。本人は、ShogiHomeのDifficulty欄でもU枚数とU価値合計を選択肢名から見分けられるようにすることを選んだ。

| 番号 | 分類 | 通常CLI表示案 | 評価・探索 |
| --- | --- | --- | --- |
| 1 | ランダム | ランダム | 合法手から一様ランダム |
| 2 | 一手評価 | 駒得のみ（10M） | 一手後の駒得差 |
| 3 | 探索手数 | 二手先読み（駒得） | 自分一手と相手の応手 |
| 4 | 探索手数 | 全幅読み（最大4手） | 深さ1〜4、枝を省略しない |
| 5 | 探索手数 | αβ枝刈り（最大4手） | 深さ1〜4、αβ枝刈り |
| 6 | 一手評価 | 駒得＋狙われ駒の枚数（10M+U枚数） | U枚数を加える |
| 7 | 一手評価 | 駒得＋U枚数＋支えあり駒への低価値駒の利き（10M+U枚数+V） | U枚数とVを加える |
| 8 | 一手評価 | 駒得＋狙われ駒の価値合計＋支えあり駒への低価値駒の利き（10M+U価値合計+V） | U価値合計とVを加える |

CLI表示では各行に「ランダム」「一手評価」「探索手数」の分類を付け、Uを含む行には「枚数」または「価値合計」と式を併記する。ShogiHomeに広告するUSI Difficulty値もUの集計方法を表す名前にそろえる。既存の `MaterialUndefendedPiece` は `MaterialUndefendedPieceCount`、既存の `MaterialSupportedPieceThreat` は `MaterialUndefendedPieceCountPlusV`、新方式は `MaterialUndefendedPieceValuePlusV` とする。保存済み設定との互換のため、旧二値は受信値として引き続き受理するが、選択欄へは重複して広告しない。値からU枚数かU価値合計かが直接分かるようにする。

この分類は評価内容と探索深さの違いを見せるためのもので、各方式の強さの順位を示さない。一局で人間が違いを感じられる保証も置かない。

## 手法の比較と選択

| 手法 | 利点 | 留意点 |
| --- | --- | --- |
| 表示だけを整理する | 変更が小さい | U価値合計方式をShogiHomeから選べず、二種類のUを対局で比べられない |
| 比較済みの `10M+U価値合計+V` を固定候補として通常CLI・USIへ追加する | Vを同じ1に保ち、U枚数版とU価値合計版を並べられる。新しい重み探索を増やさない | 通常CLI/USIの制御付き探索経路、表示、テストを更新する必要がある |
| U/Vの有無と係数を個別選択にする | 多数の組合せを試せる | 選択が増え、何の差を対局で比べたか息子にも説明しにくくなる |

本人は二つ目を選んだ。通常CLIとUSIで同じ固定方式を使い、U二種類を識別しやすくする。別の係数、`10M+U価値合計`単独、`10M+V`、全係数の組合せは今回追加しない。

## 提案する振る舞い

- 通常CLIの候補8に `MATERIAL_PIECE_THREAT_VALUE_V1` を追加し、既存の一手評価器と一手詰み優先を使う。重みは `material=10`、`undefended_value=1`、`supported_threat=1` に固定する。
- USI `Difficulty` が広告するU関連値を `MaterialUndefendedPieceCount`、`MaterialUndefendedPieceCountPlusV`、`MaterialUndefendedPieceValuePlusV` にそろえる。旧値 `MaterialUndefendedPiece` と `MaterialSupportedPieceThreat` は受信時の互換別名として同じ既存方式値へ対応させる。未設定時Random、未知値処理、局内固定、`usinewgame` 後の反映は維持する。
- 既存の候補1〜7、空入力Random、先後別選択、開始前表示、Ponder、時計・停止制御、V0の比較専用扱いは変えない。Vの二手・四手探索への拡張もしない。
- 比較CLIの方式・保存形式・結果・seed・未追跡データは変更せず、長時間比較も再実行しない。

## 確認方法と範囲

実装計画では、少なくとも以下を別々に確認する。

1. U価値合計をU枚数として誤用せず、着手後局面・手番視点で `10M+U価値合計+V` を評価する。
2. 先後双方で新候補の一手詰み優先、停止時の未完了評価破棄、合法手応答を保つ。
3. CLIの番号8と分類表示、USI Difficultyの広告名がU枚数とU価値合計を区別すること、旧USI値の互換受信、大文字小文字を区別しない設定、プロセス内保持と次局反映を確認する。新旧値それぞれが意図した方式へ対応し、実プロセスで合法な `bestmove` まで照合する。
4. AGENTS.mdに従い通常CLIのCVCを2局以上、可能なら先後を入れ替えて完局し、開始表示・両側の実着手・終局を操作確認する。勝敗から棋力を推定しない。
5. 本人が希望した「他の対応方式もこのセッションでShogiHome動作確認する」候補は、広告名を変更しない `Random`、`Material`、`TwoPlyMaterial`、`FullWidth4`、`AlphaBeta4` と、U方式の広告名 `MaterialUndefendedPieceCount`、`MaterialUndefendedPieceCountPlusV`、`MaterialUndefendedPieceValuePlusV` である。前回の一局は旧名 `MaterialUndefendedPiece` のU枚数単独で実施済みだが、改名後の表示値は現画面で改めて照合する。過去の実機記録を今回の確認に流用しない。実装後に現在の画面、版、登録先、Ponder、棋譜、稼働セッションを改めて確認し、対象方式・先後・局面・時計・一方式あたりの局数は一問ずつ合意する。設定変更やログ閲覧は具体案と別の明示承認を得てから行う。ここでは対局数やログ要否を決めない。

一局の操作確認は選択・接続・応答の実証に限り、強さや棋力向上は示さない。比較CLIの固定局面結果とShogiHome実践の観察も分けて記録する。

## 対象外と承認段階

- 係数最適化、任意の組合せ、U価値合計単独、V単独の新方式、二手・四手探索への接続。
- 比較CLIの変更・再実行、棋力の結論、既定方式の変更、mainへの統合・push。
- 現在のShogiHomeでの設定・対局・ログ状態の推定。実践条件は操作時に現画面から確認する。

本人は2026-11-03に本設計案と[実装計画](2026-11-03-undefended-piece-value-normal-cli-usi-implementation-plan.md)を承認し、ネイティブ実行を選んだ。通常CLI候補8・USI `MaterialUndefendedPieceValuePlusV` への接続、TDD、検証、独立レビュー、通常CLI CVC2局は完了した。ShogiHomeでは同方式と `MaterialUndefendedPieceCountPlusV` を各一局開始し、設定の選択・保存後に複数回の応答を観察したが、どちらも盤上入力を継続できず先手投了で終了した。CountPlusV局はUSIログを閲覧しておらず、通信行との照合はしていない。価値合計+V局のログ検索で許可範囲外行を表示した逸脱は、許可行だけを根拠に使う形で学習記録へ残した。二局はいずれも完局ではなく、過去に実機確認した他候補は重ねて実施していない。新名のU枚数単独は未選択だが、同一方式は旧名で実施済み。topic commitを作成済み。main統合・pushは未実施。主線の次の非駒得評価項目は未完了・未選定のまま保持する。

## 参照資料

- [比較専用U価値合計の設計](2026-11-02-undefended-piece-value-comparison-design.md)
- [U評価の知識メモ](../knowledge/undefended-piece-evaluation.md)
- [V評価の知識メモ](../knowledge/supported-piece-lower-value-threat.md)
- [USI応答の知識メモ](../knowledge/usi-engine-response.md)
- [通常CLI・USIへV1を接続した設計](2026-11-01-v-normal-cli-usi-design.md)
