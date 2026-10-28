# C2：玉周辺安全度の確認比較設計案

## 文書状態

2026-10-28、二つの予備比較の結果を受けた確認比較の提案。本人は「C1の統計目標を再採用」する案を良いと思うと述べ、推薦を尋ねた。アシスタントも、候補の小さな効果を判断する目標が明確になるため同案を推薦した。以下は設計案であり、本人の明示承認前のため、種一覧の生成・比較実行・分析実行は行わない。

## 目的と判定対象

B2の玉周辺安全度を含む一手選択が、対照と比べてC2で定めた四局面群上の得点率に変化をもたらすかを、事前固定した一回の比較で評価する。C1から再採用する値は統計上の仮目標（真の候補得点率55%、互角境界50%、信頼水準95%、目標検出力80%）だけとする。C1の局面、seed、結果、手数上限、組数をそのまま流用しない。

主要評価量は、四つの登録局面に等しい重みを与えた候補方式の組平均得点率である。一組は同じ局面から始める先後交換二局で構成し、組得点は二局の候補側得点の平均とする。比較CLIの既存分析方式は組単位を独立単位として95% Hoeffding区間を計算する。確認目的の判定は、区間下端が0.5を厳密に超えれば改善、上端が0.5を厳密に下回れば悪化、それ以外は判断不能とする。55%は標本数計算のための効果目標であり、採用条件でも観測結果の予言でもない。

## 比較条件

| 項目 | 提案条件 |
| --- | --- |
| 局面 | C2専用 data/comparison/c2-king-safety-positions-v1.json の4局面。各位置を等重みにする |
| 対照 | material-king-safety-material-only。駒得10、安全度0 |
| 候補 | material-king-safety。駒得10、安全度1 |
| 一組 | 各局面からbaseline先手/candidate後手と、baseline後手/candidate先手の二局 |
| 標本単位 | 先後交換二局からなる組。組内二局の独立性は仮定しない |
| 組数 | 2,036組、各局面509組。計4,072局 |
| 乱数 | 実行直前にOS乱数源から新規に事前抽出する purpose=confirmation の種一覧。二つのpilotのseed一覧は使わず、結果も加算しない |
| 手数上限 | 各局256手。上限変更・未決着後の自動再戦はしない |
| worker | 1。pilotの実測を時間見積もりへ使うため条件を合わせる |
| 主比較 | 確認比較一回、主要評価量一つ。位置別得点は記述値に限定し、別々の効果判定をしない |

## 組数の根拠と時間見積もり

組ごとの得点は0〜1に有界で、組間は新規seed一覧で独立抽出する。未決着がない場合のHoeffding十分条件として、既存の比較分析が使う式をC2の仮目標へ当てはめる。

n > (sqrt(ln(40)) + sqrt(ln(5)))² / (2 × 0.05²) = 2034.3037103489096

したがって最低基準は2,035組。四局面へ等数配分するため4の倍数に切り上げ、2,036組（各509組）とする。理論上の95% Hoeffding半径は、全組が決着した場合に約0.0301である。これは十分条件であり、必要最小組数ではない。組間独立性が崩れる場合や、未決着による得点上下限の幅が残る場合には、55%での検出力80%を保証しない。未決着局は分析CLI既定の候補視点 [0, 1] の範囲に残し、削除・再戦・都合のよい一方への確定を行わない。

256手pilotは4組・8局で79.203秒だった。単純比例では2,036組のworker 1実行に約40,314秒、約11時間12分かかる見積もりとなる。4組のpilotだけから計算した参考値で、実時間の保証ではない。CPU負荷・棋譜の長さ・局面ごとの探索時間で大きく変わり得る。長時間実行を受け入れられるかを、実行前に確認する。

## 実行手順案

実行者は本人とし、対象は /Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi。保護対象の /Users/oki2a24/kaname-shogi は使用しない。下記は本人が設計を承認した後に端末で実行する案である。実行前に既存の出力先がないことを確認する。

~~~sh
cd /Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi || exit

PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi.prepare_comparison_seeds   --positions data/comparison/c2-king-safety-positions-v1.json   --pairs-per-position 509   --purpose confirmation   --output data/comparison/runs/c2-king-safety-confirmation-2026-10-28-seeds.json
~~~

種一覧生成の終了コードが0であり、記録された目的・局面ハッシュ・四局面・509組/局面が合っていることを確認してから比較する。種一覧が未追跡のまま比較を始めた場合はconditionsのdirty記録がtrueになるため、原因を実行記録に明記する。これは比較ソース指紋の一致とは区別する。

~~~sh
PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi.compare_games   --baseline material-king-safety-material-only   --candidate material-king-safety   --positions data/comparison/c2-king-safety-positions-v1.json   --pairs-per-position 509   --seed-list data/comparison/runs/c2-king-safety-confirmation-2026-10-28-seeds.json   --max-plies 256   --workers 1   --output-dir data/comparison/runs/c2-king-safety-confirmation-2026-10-28
~~~

比較完了後、保存済みの結果だけを分析する。

~~~sh
PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi.analyze_comparison   --input-dir data/comparison/runs/c2-king-safety-confirmation-2026-10-28   --output data/comparison/runs/c2-king-safety-confirmation-2026-10-28-analysis.json
~~~

## 確認と結果の扱い

- 条件JSONでbaseline/candidate名・重み、局面とハッシュ、seed一覧とハッシュ、組数、先後割当、256手上限、worker数、ソース指紋を照合する。
- summaryで予定4,072局、完了局・完了組・未決着・中断・故障の件数を確認する。
- 分析JSONの purpose=confirmation、組数、得点上下限、95%区間、判定を確認し、分析が参照したconditions・棋譜・summary全ファイルのSHA-256を保存ファイルと照合する。
- 標本数を見た目の途中結果に応じて増減せず、早期停止やpilotとの合算を行わない。中断時は同じ条件・seed・出力先で既存の局単位再開を使う。
- 結論が判断不能の場合、「効果なし」とは言い換えない。改善・悪化もこの四局面・今回の一手選択・比較条件に限定して報告し、通常対局全般の強さや既定方式の採用を自動決定しない。

## 対象外と承認境界

通常CLI・USIへの接続、通常CLIのSFEN入出力、飛車可動性バージョン2、二手・四手への適用、追加局面や追加主要仮説、main統合、pushは対象外である。比較の実行・分析は本人が行う。本文の実行案は条件設計への承認後に本人が端末で使うためのものであり、今回の設計案作成は実行承認を意味しない。main統合・pushは別途承認を要する。

## 承認欄

- 統計方針（55%・95%・検出力80%）：本人はこの案がよいと思うと述べ、推薦を質問。アシスタントは同案を推薦。設計全体は未承認。
- 4局面均等2,036組、256手上限、worker 1、実行担当・手順：本人の明示承認待ち。
- 実行・分析、main統合、push：未承認。
