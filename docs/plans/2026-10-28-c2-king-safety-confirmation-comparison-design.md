# C2：玉周辺安全度の確認比較設計案

## 文書状態

2026-10-28、二つの予備比較の結果を受けた確認比較の設計。本人は「C1の統計目標を再採用」する案を良いと思うと述べ、推薦を尋ねた。アシスタントも同案を推薦し、本人は設計案全体に「yes」と回答して承認した。その後、本人の希望で実行条件をworker 1からworker 4へ変更した。本人はconfirmation種一覧を生成済み。worker 1比較は16:19に開始し、本人がCtrl-Cで中断した。worker 1の部分出力は保持する。worker 4比較は同じ種一覧と新しい出力先で16:31に開始し、本人報告と保存summaryで21:40に完了を確認した。4,072局・2,036組の統計分析は未実施で、本人端末で実行待ち。

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
| 乱数 | 本人が生成済みの purpose=confirmation 種一覧（SHA-256 52d6557657893202bac46be125b28e9044fbe32917e5afb9137bbcebcde35284）。二つのpilotとは別の種。worker 1中断後のworker 4実行で同じ一覧を使い、独立標本として二重計上しない |
| 手数上限 | 各局256手。上限変更・未決着後の自動再戦はしない |
| worker | 4。本人の希望により変更。確認比較の実測所要時間は約5時間09分。この一回の実績であり一般的な所要時間を保証しない |
| 主比較 | 確認比較一回、主要評価量一つ。位置別得点は記述値に限定し、別々の効果判定をしない |

## 組数の根拠と時間見積もり

組ごとの得点は0〜1に有界で、組間は新規seed一覧で独立抽出する。未決着がない場合のHoeffding十分条件として、既存の比較分析が使う式をC2の仮目標へ当てはめる。

n > (sqrt(ln(40)) + sqrt(ln(5)))² / (2 × 0.05²) = 2034.3037103489096

したがって最低基準は2,035組。四局面へ等数配分するため4の倍数に切り上げ、2,036組（各509組）とする。理論上の95% Hoeffding半径は、全組が決着した場合に約0.0301である。これは十分条件であり、必要最小組数ではない。組間独立性が崩れる場合や、未決着による得点上下限の幅が残る場合には、55%での検出力80%を保証しない。未決着局は分析CLI既定の候補視点 [0, 1] の範囲に残し、削除・再戦・都合のよい一方への確定を行わない。

256手pilotはworker 1で4組・8局を79.203秒で完了した。そこから算出した約11時間12分はworker 1向けの事前参考値であり、worker 4の実績とは異なる。今回の確認比較はworker 4で約5時間09分だった。実行時間はCPU負荷・棋譜の長さ・局面ごとの探索時間で変わるため、この一回の実績から他の比較の所要時間を保証しない。

## 実行手順（worker 4版、本人の端末で実行）

対象は /Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi。保護対象の /Users/oki2a24/kaname-shogi は使用しない。

本人はすでに次のconfirmation種一覧を生成した。purpose=confirmation、4局面×509組、計2,036組。SHA-256は52d6557657893202bac46be125b28e9044fbe32917e5afb9137bbcebcde35284。再生成せず、worker 4版でもこの同じ一覧を使う。

worker 1版の出力先 data/comparison/runs/c2-king-safety-confirmation-2026-10-28/ は本人がCtrl-Cで中断した部分結果を含み、保持している。worker 4版は別の新規出力先 data/comparison/runs/c2-king-safety-confirmation-2026-10-28-workers-4/ へ実行済みである。分析ファイル data/comparison/runs/c2-king-safety-confirmation-2026-10-28-workers-4-analysis.json は確認時点で未作成。

worker 4版conditions.jsonにはGit HEAD=db921cbc83f79b46dc27345664b47c9720c03542、dirty=trueが記録された。実行時に種一覧とworker 1部分出力が未追跡だったためで、製品コードの変更を示さない。比較ソース指紋f840a3a7bd2b04e9fbf3829cb4cc4447578da085730c6ec32f7ebc21a080204fは保存値である。

本人がworker 1をCtrl-Cで中断し、新出力先が未使用であることを確認した後、本人は16:31にworker 4比較を開始した。

~~~sh
cd /Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi || exit

PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi.compare_games   --baseline material-king-safety-material-only   --candidate material-king-safety   --positions data/comparison/c2-king-safety-positions-v1.json   --pairs-per-position 509   --seed-list data/comparison/runs/c2-king-safety-confirmation-2026-10-28-seeds.json   --max-plies 256   --workers 4   --output-dir data/comparison/runs/c2-king-safety-confirmation-2026-10-28-workers-4
~~~

本人は21:40に比較完了を報告した。保存conditionsはworker 4・509組/局面を記録し、summaryはstatus=complete、4,072/4,072局、2,036完了組、手数上限71局、詰み3,966局、合法手なし35局、エラー・中断0局を示す。4,072局の結果ファイルは連番で揃っている。比較CLIの経過時間は約5時間09分。候補方式の統計的な強さ判定はまだ行っていない。

完了後、worker 4版の保存結果を分析する。

~~~sh
PYTHONDONTWRITEBYTECODE=1 python3 -m kaname_shogi.analyze_comparison   --input-dir data/comparison/runs/c2-king-safety-confirmation-2026-10-28-workers-4   --output data/comparison/runs/c2-king-safety-confirmation-2026-10-28-workers-4-analysis.json
~~~

worker 4版を中断した場合の再開は、同じseed、worker数、条件、出力先の --resume を使う。worker 1版へresumeしたり、worker 1/4の結果を結合したりしない。

## 確認と結果の扱い

- 条件JSONでbaseline/candidate名・重み、局面とハッシュ、seed一覧とハッシュ、組数、先後割当、256手上限、worker数、ソース指紋を照合する。
- summaryで予定4,072局、完了局・完了組・未決着・中断・故障の件数を確認する。
- 分析JSONの purpose=confirmation、組数、得点上下限、95%区間、判定を確認し、分析が参照したconditions・棋譜・summary全ファイルのSHA-256を保存ファイルと照合する。
- 標本数を見た目の途中結果に応じて増減せず、早期停止やpilotとの合算を行わない。中断時は同じ条件・seed・出力先で既存の局単位再開を使う。
- 結論が判断不能の場合、「効果なし」とは言い換えない。改善・悪化もこの四局面・今回の一手選択・比較条件に限定して報告し、通常対局全般の強さや既定方式の採用を自動決定しない。

## 対象外と承認境界

通常CLI・USIへの接続、通常CLIのSFEN入出力、飛車可動性バージョン2、二手・四手への適用、追加局面や追加主要仮説、main統合、pushは対象外である。本人は本設計案を承認済みで、比較・分析は本人の端末で実行する。これはアシスタントが長時間CLIを起動する承認ではない。main統合・pushは別途承認を要する。

## 承認欄

- 統計方針（55%・95%・検出力80%）、4局面均等2,036組、256手上限、本人端末での実行：本人の「yes」により2026-10-28承認済み。
- worker数：当初worker 1で設計承認済み。その後本人がworker 4を優先すると指示し、同じconfirmation種で新しい出力先を使う変更を了承。worker 1は本人がCtrl-Cで中断済み。
- worker 4版の比較：本人端末で16:31に開始、21:40に完了。保存summary・4,072局ファイルの存在を確認済み。所要時間は約5時間09分。
- worker 4版の統計分析：本人端末での実行待ち。強さ判定は未実施。
- main統合・push：別途承認。
