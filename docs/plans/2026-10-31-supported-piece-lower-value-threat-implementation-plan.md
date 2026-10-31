# 支えがある駒への低価値駒の利き：実装計画

> **実施状況:** 設計案・本計画の全体承認とネイティブ実行の本人選択を受けて実施。Task 1〜4の実装・専用検証・Task別レビュー、全体検証・独立レビューを完了し、作業ブランチへコミット `7f810ac` として記録した。main統合・pushはしていない。

**目標:** V枚数・差と10M+U+Vの合成を実装し、既存の評価差替式一手選択器へ注入できることを確認する。

**アーキテクチャ:** 参考価値と移動規則の定義元を共用する小さな公開操作を追加し、新指標と合成を別ファイルに置く。既存方式や選択器の本体・CLI/USI公開は変更しない。

**技術スタック:** Python標準ライブラリ、unittest、固定版Ruff 0.16.10。新規依存なし。READMEの実行要件Python 3.14以上と現行Ruff設定を維持し、既存方針に従いunsafe修正やPython 3.9への影響も個別に確認する。

**仕様:** [2026-10-31承認済み設計](2026-10-31-supported-piece-lower-value-threat-design.md)。設計案・本計画・ネイティブ実行は本人が明示承認済み。

## グローバル制約

- 攻撃元が複数でも対象一枚は1。価値差を点数にしない。同価値・高価値の攻撃元しかなければ対象外。
- 玉は対象・低価値攻撃元から除外し、支え役には含める。
- 利きは既存の盤上利きと同じ意味で、ピンされた駒も含む。遮蔽は現在盤面のまま。
- 持ち駒は対象・攻撃元・支え役にせず、手番は参照しない。成駒は現在の動きと価値を使う。
- 合法な駒取り、取り返し、自玉安全、詰み、将来の駒打ちは判定しない。
- 玉なし部分局面も受け付け、盤面・持ち駒・手番を変更しない。依存する操作の例外を隠さない。
- 今回のB範囲はV枚数・差、M/U/V合成、既存一手選択器への注入確認まで。
- 比較CLI・通常CLI・USIへの方式公開、長時間比較、二手・四手、玉安全度との合成、飛車可動性v2、通常CLIのSFEN入出力は対象外。既存方式の挙動を維持する。
- 公開操作には日本語で引数・戻り値・副作用・前提・設計理由を記す。
- 作業場所は /Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi。既存worktree・作業ブランチを再利用し、mainでは実装しない。元checkout、未追跡C2保護4件、U比較データ、.agents/tasks/を保持する。main統合・pushは別途承認。

## レビューフォーカス

1. 攻撃元の走査順で、先に見つかった高価値駒のために後続の低価値駒を見落とさない（Task 3の混合攻撃元）。
2. 味方占有マスへの支えと対象自身の除外を両立し、射線途中の遮蔽を消さない（Task 2の占有・同一マス・遮蔽）。
3. 馬と飛車の同価値や成駒の逆転を、基本駒の値で誤判定しない（Task 1の全13値、Task 3の成駒境界）。
4. 係数0でも各依存操作の失敗を隠さず、入力を変更しない（Task 4の呼出・例外・snapshot）。
5. 一手選択で開始側視点を守り、一手詰みを通常点より優先する（Task 4の先後・順序・詰み接続）。

## ファイルと公開インターフェース

| Task | 変更・作成先 | 責務 |
| --- | --- | --- |
| 1 | kaname_shogi/evaluation.py、tests/test_evaluation.py | 既存価値表を読む操作 |
| 2 | kaname_shogi/movegen.py、tests/test_piece_attack.py（新規） | 指定攻撃元からの利き |
| 3 | kaname_shogi/supported_piece_threat.py、tests/test_supported_piece_threat.py、tests/supported_piece_threat_support.py（新規） | V枚数・差と固定局面 |
| 4 | kaname_shogi/material_piece_threat.py、tests/test_material_piece_threat.py、tests/test_piece_threat_selection.py（新規） | M/U/V合成と選択接続 |

英語名の意味：piece_reference_valueは「駒の参考価値を読む操作」、is_piece_attacking_squareは「指定駒の利きを調べる操作」、supported_lower_value_threat_count/balanceは「支えがある駒への低価値駒の脅威の枚数/差を数える操作」。PieceThreatWeightsは合成係数を保持する設定データ。evaluate_material_piece_threatは合成点を返す操作。

## 実行前準備（計画承認後）

- [x] 実行方式の選択を記録し、using-git-worktreesで既存のリンクworktreeを再確認する。新しいworktreeを作らない。必要なTDD・実行・レビュー用スキルを読む。
- [x] Git状態、requirements-dev.txt、.venv/bin/ruff --version、git config --local --get core.hooksPathを確認する。不一致はREADME手順で修復し、既存hookを上書きしない。今回の計画作成時点ではRuff 0.16.10・hook .githooksを読み取り確認済み。
- [x] 個人テスト点検とdocs/knowledge/test-coverage-review.mdを再確認する。
- [x] 製品変更前に python3 scripts/run_tests_parallel.py を実行し、件数・モジュール数・時間・失敗を記録する。失敗は解決前に既存成功と扱わない。承認前には実行しない。

## 全Task共通の進め方

各Taskのテスト一覧を一度に実装しない。振る舞いごとに以下を繰り返す。

- [ ] 下記の契約・独立期待値に対応するテストを一つ追加する。
- [ ] 指定コマンドで実行し、意図したassertion failureを確認する。公開名がない段階はgetattrとcallableのassertで境界不在を示し、最小の宣言後にも振る舞いの失敗を確認する。ImportErrorだけではRed完了にしない。既存実装による初回Greenは区別して記録する。
- [ ] 対象の契約だけを満たす最小実装を行う。
- [ ] 同コマンドで成功を確認する。
- [ ] 全契約を終えたらRefactorの要否を確認し、変更した場合は再検証する。
- [ ] imports変更時は .venv/bin/ruff check --select I --fix .、続いて .venv/bin/ruff format .、.venv/bin/ruff check .、git diff --check と差分確認、該当テストを行う。他のPython差分が出たら原因を確認し、無断で含めない。
- [ ] Refactor有無を問わず独立コードレビューへ契約・代表例・検出対象・補完・未検証を渡す。Critical/Importantを解消し、再検証・再レビューする。各重大度と対応を学習記録へ残す。
- [ ] 当該コード・テストと記録だけを明示してステージし、通常hookを通してコミットする。一括add・検査回避禁止。実行方式がネイティブでもTask別独立レビューは省略しない。

## Task 1：参考価値を共用する

**変更:** evaluation.py、test_evaluation.py。

**生産:** piece_reference_value(piece_type: PieceType) -> int。非玉の全13駒種を受け、既存_TANIGAWA_PIECE_VALUESから返す。玉は ValueError("玉の参考価値は定義しません")。有効なPieceTypeが前提で、任意型の検証は追加しない。既存material_balanceと持ち駒表の挙動は変えず、価値表を複製しない。

- [x] test_piece_reference_values_match_current_table：独立な期待表をテストへ列挙する。歩1/と金12/香5/成香10/桂6/成桂10/銀8/成銀9/金9/角13/馬15/飛15/竜17について assertEqual(piece_reference_value(kind), expected)。馬15と飛15が等しいことも確認する。
- [x] test_king_has_no_reference_value：assertRaisesRegex(ValueError, "玉の参考価値は定義しません")。
- [x] 共通サイクルを実施。実行：python3 -m unittest discover -s tests -p 'test_evaluation.py' -v。既存駒得の先後±13や複製適用も成功すること。

## Task 2：攻撃元を指定した利き

**変更/作成:** movegen.py、test_piece_attack.py。

**生産:** is_piece_attacking_square(board: Board, source: Square, target: Square) -> bool。sourceが空、source==targetならFalse。駒の所属はsourceから取得する。味方占有targetだけをコピー盤上で空け、既存_move_candidates_for_pieceへ委譲する。元盤を変更せず、他の遮蔽を残す。ピン・手番・合法性は問わず、候補生成の例外は伝播する。既存is_square_attackedは変更不要とし、移動形状を再実装しない。

- [x] test_source_target_occupancy_and_blockers：先手飛5九、先手金5五で5五への利きTrue。後手金へ交換してもTrue、空にしてもTrue。途中5七へ先手歩または後手歩を置けばFalse。5九自身および空の出発点からはFalse。各照会前後の81マスが同じ。
- [x] test_king_and_promoted_piece_geometry：先手玉5五→4四 True/3三 False、先手馬5五→5四 True/5三 False、先手竜5五→4四 True/3三 False。後手と180度反転でも同じ結果。成駒追加の動きがVへ届く境界を検査する。
- [x] test_pinned_source_keeps_geometric_attack：先手玉5九・先手銀5八・後手飛5一で銀5八→4七はTrue。銀が動くと飛の射線を開くが利きには含める。
- [x] test_candidate_error_propagates：委譲先候補操作をRuntimeErrorで差し替え、同じ例外が伝播すること。
- [x] 共通サイクルを実施。実行：python3 -m unittest discover -s tests -p 'test_piece_attack.py' -v。補完として python3 -m unittest discover -s tests -p 'test_movegen.py' -v と test_king_safety.py を同方式で実行し、既存利きと矛盾しないことを確認。

## Task 3：V枚数・差

**消費:** Task 1/2の公開操作、is_square_attacked(board, target, side)、既存Position/Side。

**生産:** supported_piece_threat.pyの supported_lower_value_threat_count(position: Position, side: Side) -> int と supported_lower_value_threat_balance(position: Position, perspective: Side) -> int。後者は相手枚数−視点側枚数。非玉・味方支えありの各対象について相手非玉の現在価値を比較し、安い攻撃元から利けば一回加算する。玉の価値照会をしない。各候補を全て評価する必要はなく、一つ見つけたら対象の調査を終えてよい。

テスト用新ファイルには design_case(name: str) -> Position（A/B/C）と both_sides_case() -> Position（以下D）を置く。未知のnameはValueError。構築・回転・snapshot・詰み局面は既存undefended_piece_supportのposition・rotate_and_swap・snapshot・mate_caseを再利用し、評価結果から期待値を生成しない。回転はPieceSpecの列から独立に構築し、元側と比較する視点も先後交換する。

- [x] test_design_case_counts / test_design_case_balances：承認済みA/B/Cについて、先手枚数1/0/0、後手全0、先手差−1/0/0、逆視点+1/0/0を確認。PieceSpecから独立に先後反転した配置でも値を保つ。
- [x] test_both_sides_count_and_nonzero_balance：Dは先手角5五・角3五・金4六・歩8四、後手歩5四・歩3四・飛8三・金7二。先手対象は角二枚、後手は飛一枚。count(SENTE)=2、count(GOTE)=1、balance(SENTE)=−1、balance(GOTE)=1。先後反転も確認。
- [x] test_strict_value_boundary：角13に対し、同価値角は0、低価値銀は1、高価値飛は0を別配置で確認。
- [x] test_promoted_values_and_motion：成駒の現在価値と馬・竜の追加利きの境界を確認。
- [x] test_all_nonking_targets：対象を全13非玉駒種へ差し替え、歩だけ0、残り全て1を確認。
- [x] test_all_nonking_attackers：攻撃元を全13非玉駒種で確認。竜だけ同価値で0、他12種は1。全種の形状の正しさは既存移動テストも補完する。
- [x] test_multiple_and_mixed_attackers：高価値の飛を安い攻撃元より前に置き、後続の安い銀・歩を見落とさず対象一枚だけ数える。先後反転でも確認。
- [x] test_king_roles：玉を支え役に含め、低価値攻撃元・対象から除外する。
- [x] test_shield_and_pin：遮蔽の有無、ピンされた攻撃元、ピンされた支えを確認。
- [x] test_empty_hands_turn_and_no_mutation：空盤、手番、両側の持ち駒、snapshot不変、価値・利き依存操作の例外伝播を確認。
- [x] 共通サイクルを実施。専用13件と既存Uテスト10件が成功し、U自体は変更していない。

## Task 4：合成と一手選択

**消費:** material_balance、attacked_undefended_piece_balance、Task 3の差、既存choose_one_ply_move。

**生産:** material_piece_threat.pyの凍結dataclass PieceThreatWeights(material: int = 10, undefended: int = 1, supported_threat: int = 1) と evaluate_material_piece_threat(position: Position, perspective: Side, *, weights: PieceThreatWeights = _DEFAULT_PIECE_THREAT_WEIGHTS) -> int。非公開定数_DEFAULT_PIECE_THREAT_WEIGHTSはPieceThreatWeights()で生成する。

materialは正整数、他は非負整数、bool/floatを拒否する。エラー文言は既存の「駒得重みは1以上の整数にしてください」「対象差重みは0以上の整数にしてください」と、新規「支えあり脅威重みは0以上の整数にしてください」。M/U/Vを各一度読み、係数0でも呼び出し、例外を伝播する。

- [x] test_design_scores_and_zero_v：A/B/Cは既定209/209/210、V係数0なら210/209/210、逆視点は各負値。Uを二重加算しない。
- [x] test_all_terms_nonzero_and_custom_weights：DはM=10、U=−1、V=−1。既定98、(3,2,4)なら24、逆視点−98/−24。Dの歩8四は後手飛に狙われ無支えなのでUで一枚、V対象の角二枚・後手飛一枚とは別。
- [x] test_weights_and_dependency_contract：既定と凍結、(1,0,0)の受理、各フィールドへの−1/bool/float、material=0拒否。各依存操作のMockで一回・同じ引数、0でも呼出し、例外伝播、snapshot不変。ゼロ係数で評価項を省略する実装を検出する。
- [x] test_selects_escape_with_v_for_both_sides_and_orders：局面は先手玉9九・角5五・金4六、後手玉4三・歩5四、先手番。候補は角5五→6六（逃げる）と金4六→4五（支えを維持）。両方legal_movesに含まれ、適用後非詰みとassert。両枝M=21/U=0、Vは逃げ0/維持−1、既定210/209。先後反転・候補順反転でも逃げる手を選ぶ。
- [x] test_zero_v_keeps_both_candidates_tied：同じ二枝はV係数0で共に210。rng.choiceが元順の候補二つで一度呼ばれ、元局面snapshot不変。
- [x] test_mate_priority_with_new_evaluator：既存mate_caseを先後双方・両候補順で使用し合法性と詰み/非詰みを直接assert。新合成評価に10**30を加えたラッパーでも詰み手を選び、通常枝だけ評価される。空候補・枝独立性等の一般契約は既存test_one_ply_selectionが補完する。
- 計画時の選択局面は後手歩5四を後手玉が支えておらず、支えを保つ枝でUが+1になることがTask 4の接続確認で分かった。そのままではVだけを変える比較にならないため、歩5四を守る後手玉を4三へ置いた。両候補の合法性、非詰み、M=21/U=0、V差と得点差を再計算してからテストを確定した。評価仕様・対象範囲の変更ではない。
- [x] 共通サイクルを実施。専用合成5件・一手接続3件、既存一手選択10件・U選択3件の合計21件が成功。全体 `python3 scripts/run_tests_parallel.py` は1014件・79モジュール・22.462秒で成功。Ruff format 137ファイル確認・check・差分検査も成功。

Task 4では公開操作未定義とV重み0を無視する振る舞いのRedを確認し、M/U/V合成と一手選択接続後に専用8件を成功させた。各契約テストを個別に失敗させてから実装したとは記録しない。接続試験で計画局面の後手玉1二が後手歩5四を支えておらず、支え維持枝のUが+1となることを発見した。歩を守る後手玉4三へ修正し、合法手・非詰み・M=21/U=0・V差と合成点を再確認した。局面フィクスチャの修正であり評価仕様は変えていない。Refactor要否：不要。Task 4の独立レビューはCritical 0 / Important 0 / Minor 0。

## 検出力・全体検証・記録

- [x] 隔離コピーで代表変異を一つずつ入れ、狙ったassertion failureと変異なしの作業ツリーでの成功を記録する。Task 1の成駒を基本価値へ戻す変異は `/private/tmp/kaname-shogi-task1-2-mutants-langsvd9/` のコピーで検出。Task 2の味方占有先を空けない変異も同コピー、途中駒を盤面から除去する変異は `/private/tmp/kaname-shogi-task2-blocker-mutant-1whyzcba/` で検出。Task 3は<=/支え条件反転/攻撃元重複/玉を安い攻撃元/片側固定、Task 4はV省略/U二重加算を完了。Task 4は `/private/tmp/kaname-shogi-task4-mutants-hngetkyw/` の隔離コピーで意図したassertion failureを確認し、変異なしの作業ツリーでは関連テストと全体テストが成功した。比較データは変更していない。
- [x] テストの単独検出と既存全体の補完を区別し、検出しない誤りと未検証を記録する。固定例を全配置の証明と呼ばない。
- [x] imports整理、format、check、差分確認後、python3 scripts/run_tests_parallel.pyで全発見モジュールを実行する。今回はランナーを変えないため逐次全体実行は通常不要。共有状態・順序依存を疑った場合は python3 -m unittest discover -s tests -v を併用する。
- [x] Task別レビュー後、ブランチ全体を新しい独立レビュアーが確認する。初回はCritical 0 / Important 0 / Minor 0。追補文書の再確認でMinor 1（学習記録とREADME索引の進捗表示が古い）を受け、2箇所を更新。最終再確認はCritical 0 / Important 0 / Minor 0、追加指摘なし。レビュアーはテスト・Ruffを再実行していない。
- [x] docs/knowledge/supported-piece-lower-value-threat.mdを作成し、学習・設計・実装計画へ実績を追記。docs/README.mdの索引、resumeの承認段階を更新した。変更した文書9件について相対Markdownリンク877件・見出し参照6件を確認し欠落0。差分確認後、対象12ファイルだけを明示ステージし、通常hook付きの `7f810ac` としてコミットした。
- [x] 元の作業ディレクトリを読み取り照合し、別ブランチの既存文書変更・未追跡データを保持するため切替・編集しない。本人の通常手順指示を受け、別のclean integration worktreeでmainへfast-forwardした。引き継ぎ文書コミット 37719073 は除外し、評価機能・記録の5コミットだけをローカルmainへ統合した。origin/mainへのpushは自動レビューに明示承認不足として拒否され、未実施。main上で全体1014件・79モジュール、Ruff、差分検査を再確認。最後の理解確認を一問だけ行い、回答後に次テーマ候補を示す。ShogiHome実践や未承認の評価接続へ自動移行しない。

## 実行方式とセルフレビュー

推薦はネイティブ（このセッションの担当が実装）。4Taskは共通操作→指標→合成の順序依存が強い。本人がサブエージェント駆動を選ぶこともできる。どちらでもリポジトリ規則のTask別独立レビューと最終レビューを行う。

計画作成時に仕様網羅性・ステップ粒度・型/名前の整合・レビューフォーカスとテストの対応・分量・コマンドをセルフレビューした。実施結果は[学習記録](../learning/supported-piece-lower-value-threat.md)へ追記する。Task 3では公開操作の未定義・枚数差操作の未定義をassertion failureで確認したが、後続の全契約テストは共有実装後に追加してGreenとなり、計画した個々のケースでのRed確認を省略した。この逸脱は記録済み。期待値は製品採点から取得していない。棋力・重み最適化・全配置・実時間性能・合法な交換損得は未検証として残す。

## ローカルmain統合の実績（2026-10-31）

作業ブランチの5コミットを、引き継ぎ文書コミット 37719073 を除いてクリーンなmainベースへcherry-pickした。文書案内5件は引き継ぎコミットと同じ行を変更していたため、mainの履歴を保って競合を解消し、今回の評価項目と完了状況だけを記録した。元のチェックアウトと保護対象の未追跡データは変更していない。

統合コミットは 8c4d5366、a405bc62、ec7a6cfc、07e38d9e、b25b7d7d。main上で1014テスト・79モジュールが22.464秒で成功し、Ruff format確認137ファイル、Ruff check、git diff --check も成功した。origin/mainへのpushを試みたが、自動レビューに明示承認不足として拒否された。回避して再試行せず、本人の明示承認待ち。最終理解確認は未実施で、統合後に一問だけ確認する。
