# 二手先読み（駒得）実装計画

> **AIエージェントへの指示:** 実装時は `subagent-driven-development` または `executing-plans` スキルを使用する。本書は計画案であり、本人の明示承認と別途の実装開始指示までTDD・コード・テスト変更を開始しない。今回の計画テーマでは承認後も実装へ進まない。

**状態:** 2026-10-10作成。名称・互換性は合意済み。本人は本書全体へ「よい」と回答し、具体的な型・操作・手順を承認した。実装は未開始。

**目標:** 自分一手と相手一手を読み、相手の最も不利な応手を考慮する選択肢を追加する。

**アーキテクチャ:** `movegen.py` の既存選択入口を保ち、非公開操作を追加する。合法手生成・移動・駒打ち・詰み判定・駒価値は既存処理を再利用し、CLIとUSIから同じ方針を渡す。

**技術スタック:** Python 3.9以上、標準ライブラリ、unittest、Ruff 0.16.10。

**仕様:** [承認済み設計](2026-10-10-evaluation-next-stage-design.md)、[今回の合意・検証記録](../learning/two-ply-implementation-plan.md)。本書の具体案は設計承認とは別に、2026-10-10に本人承認を得た。

**全体の制約:**

- 「既定の動作は一様ランダム。」
- 「盤上・持ち駒・成駒・玉の扱いを変更しない。」
- 「評価視点は開始局面の手番側に固定する。」
- 「自分の一手と相手の一手、合計二手で読むのを止める。」
- 「勝ち同士・負け同士は同点とし、詰みまでの距離では差を付けない。」
- 「開始局面、候補の手データ、双方の持ち駒を変更しない。」
- 枝刈り・可変深さ・静止探索・新評価項目・未対応の勝敗規則を追加しない。ShogiHome操作、追加接続調査、Ruff追加ルール、自作UIを前提にしない。
- 公開docstringに引数・戻り値・副作用・前提条件・設計理由を日本語で記す。テスト名は英語、日本語docstringの先頭行に振る舞い、本文に検出したい誤りを記す。

## 合意済み名称と互換性

| 動作 | CLI表示 | USI値 | 内部の方針データ |
| --- | --- | --- | --- |
| 一様ランダム | ランダム | `Random` | `MoveSelectionPolicy.RANDOM` |
| 一手後の駒得比較 | 一手駒得 | `Material` | `MoveSelectionPolicy.MATERIAL` |
| 自分一手＋相手一手 | 二手先読み（駒得） | `TwoPlyMaterial` | `MoveSelectionPolicy.TWO_PLY_MATERIAL` |

USI値・内部識別名は各推薦案に本人が `1` と回答した。既存型名・関数名・引数を保ち、`choose_move` に分岐を追加する公開API互換性方針へ `ok` と回答した。旧 `Material` の意味と `MATERIAL` の一手限定動作を変えない。既存の列挙値を並べ替えず新値を末尾へ追加する。

## 表現と操作の具体案

`MoveSelectionPolicy` は方針を表すデータ型。新しい `TWO_PLY_MATERIAL` も値であり、指す操作ではない。

非公開の評価データは `tuple[int, int]` とする。勝ち `(1, 0)`、通常 `(0, material_balance(...))`、負け `(-1, 0)`。Pythonの組の比較は先頭を優先するため、通常の点数の大きさで勝敗が逆転しない。勝敗では第二要素を必ず0にする。

追加する非公開操作は以下の三つ。公開APIやpackage rootの再公開は増やさない。

- `_position_after_move(position: Position, move: Move) -> Position`：元局面を複製し、盤上移動なら `apply_move`、駒打ちなら `apply_drop` を適用する。未知の手型は既存と同じ `TypeError`。不合法手の `ValueError` を隠さない。
- `_two_ply_score(after_move: Position, perspective: Side) -> tuple[int, int]`：自分の一手後の局面を受け取り、相手が詰みなら勝ち。相手の全合法手を複製へ適用し、自分が詰みなら負け、それ以外は開始側視点の通常評価。その最小値を返す。相手の手なしで詰みでなければ一手後の通常評価。
- `_choose_two_ply_material_move(position: Position, moves: tuple[Move, ...], rng: random.Random) -> Optional[Move]`：空ならNone。各候補の評価を求め、最大値の候補だけを元の候補順で集め、一回の `rng.choice` で選ぶ。

既存の `choose_move(position, moves, policy, rng) -> Optional[Move]` に新分岐を追加する。RANDOMの委譲とMATERIALの実装はまず維持する。通常評価は一手後と二手後の点数の合計ではなく、比較対象局面そのものの点数である。二手後の `is_checkmate` が防御手の有無を調べても、それは三手目の駒得探索ではない。

## ファイルと責務

| ファイル | 将来の変更 |
| --- | --- |
| `kaname_shogi/movegen.py` | 方針値と上記三操作、新分岐、docstring |
| `tests/test_movegen.py` | `TwoPlyMaterialSelectionTests` を追加、既存の二方式の回帰確認 |
| `kaname_shogi/cli.py` | 三択の表示・入力対応・docstring |
| `tests/test_cli.py` | 三択と方針の受け渡し、無効入力を4へ変更 |
| `tests/test_cli_entrypoint.py` | 新方針が実入口から対局へ渡る確認。入口本体は必要な変更がなければ維持 |
| `kaname_shogi/usi_engine.py` | option通知と小文字キー `twoplymaterial` の受理 |
| `tests/test_usi_engine.py` | 新値・大文字小文字・局内固定・次局継承・実応答 |
| README、知識メモ二件、文書索引、再開案内、学習記録 | 実装・検証した範囲だけ更新 |

## レビューフォーカス

1. 後手開始で評価視点が途中反転しないこと（タスク1）。
2. 異常に大きい持ち駒数でも通常評価が詰みを上回らないこと（タスク2）。
3. 成り・駒打ち・成駒取りを含む複数枝で元局面と兄弟枝を汚さないこと（タスク2）。
4. 玉なしの部分局面や王手でない手なしを負け・勝ちへ変えないこと（タスク2）。
5. USIの局中設定変更・未知値で現在局の方針や保存設定を壊さないこと（タスク4）。

## 実装時の共通サイクル

以下のタスクはすべて未実施。各表の行を一つの振る舞い単位として、次のサイクルを繰り返す。一度に全テストを書いてから実装しない。

- [ ] 行の英語名のテストと日本語docstringを作る。局面・候補が合法なこと、期待値の手計算を先に照合する。
- [ ] 未実装の振る舞いは対象テストを実行し、表に示した振る舞いの不足で失敗することを確認する。属性・importエラーだけをRed完了とせず、必要な名前を用意した後でアサーションの失敗を確認する。
- [ ] 先行タスクや既存処理ですでに成立する契約の追加テストが初回Greenなら、その理由と検出対象を記録し、未実装時のRedとは呼ばない。表の誤りだけを一時的に注入した隔離コピーまたはテスト内の置換で、対象アサーションが失敗することを確認して戻す。例えば空候補ならNoneの代わりに抽選させる、途中手なしなら通常評価を勝敗へ変える。意図した失敗理由を記録し、正しい作業ツリーへ誤りを残さない。
- [ ] 未実装の振る舞いだけ最小実装を行う。初回Greenの契約は不要な製品変更を加えない。
- [ ] 同じテストのGreenと該当テストファイルの回帰成功を確認する。
- [ ] Refactorの要否と理由を記録する。変更したら再検証する。
- [ ] 独立レビューでCritical・Important・Minorを記録する。重大指摘は解消して再検証・再レビューする。
- [ ] 実施内容と検証を学習記録へ記し、差分・整形・lintを確認して対象だけステージし、通常フック付きでコミットする。

実行場所は `/Users/oki2a24/kaname-shogi`。単一テストは `python3 -m unittest discover -s tests -p test_movegen.py -k test_avoids_rook_recapture -v` のように実行し、対象が1件以上で意図した日本語説明が出ることを確認する。成功は `OK`、Redは対象アサーションの `FAIL` で確認する。ファイル・`-k` は各行へ置き換える。

### タスク1：通常の二手比較

対象：`movegen.py` と `test_movegen.py`。消費するのは既存の `Position.copy`、`apply_move`、`apply_drop`、`legal_moves`、`is_checkmate`、`material_balance`。生産するのは上記三操作と新方針分岐。

| テスト名 | 入力・期待するアサーション | Redで検出する不足／最小実装 |
| --- | --- | --- |
| `test_avoids_rook_recapture` | 設計の９九玉・５五飛対１一玉・５三金・５四歩。候補５四飛と４五飛。`assertEqual(selected, safe)`。開始差5、歩取り直後7、金の取り返し後-23、安全手の最悪応手後5を照合 | 一手後だけなら歩取りを選ぶ。候補ごとに全応手後の最小値を比較 |
| `test_uses_worst_reply_independent_of_order` | 同じ教材の応手一覧を実生成してから逆順でも渡すラッパーを使用。`assertEqual(score, (0, -23))` を両順で確認 | 最初または最後の応手だけを使う誤り。minを全応手に適用 |
| `test_keeps_root_side_for_gote` | 教材を筋・段とも `10-n` に反転し双方の所属と手番を交換。後手の安全手を選ぶ | 先手固定・途中反転。開始側を引数で保つ |
| `test_keeps_profitable_capture` | 同じ教材から後手５三金を除く。候補は同じ二手。`assertEqual(selected, capture)`、通常値16を確認 | 駒取りの一律禁止。実際の二手後評価で選ぶ |

- [ ] 上の各行について共通サイクルを実施する。
- [ ] `python3 -m unittest discover -s tests -p test_movegen.py -v` が成功する。

### タスク2：詰み・境界・枝の独立性

対象とインターフェースはタスク1と同じ。評価の区分を通常値へ統合せず、既存詰み操作を使用する。

| テスト名 | 入力・期待するアサーション | Redで検出する不足／最小実装 |
| --- | --- | --- |
| `test_prioritizes_mate_over_large_material` | 既存 `test_cli.py` の `_mate_after_sente_rook_move` の実局面をテスト内へ用意し、詰ませる合法候補を検証。相手持ち駒に歩を1000000枚加えても飛車移動後の詰み成立を確認し、`assertEqual(score, (1, 0))`。別の玉なし通常局面の通常値1000000より勝ちが大きいことも比較 | 固定整数による逆転。勝ち区分を優先 |
| `test_rates_reply_mate_as_loss` | 既存の詰み直前局面で手番・所属を反転し、相手の一手で開始側が詰む一手後局面を作る。応手の合法性・詰みを実操作で確認。`assertEqual(score, (-1, 0))`、通常値-1000000より小さいことを比較 | 駒得だけで負けを選ぶ。二手後の詰みを負け区分へ |
| `test_draws_only_equal_best_candidates` | ９九玉・５五金対１一玉・５四銀・４五銀。金の銀取り二候補と５六金。応手後も銀取り二つが同点最高であることを照合し、記録する乱数器へ渡す候補がこの二つだけと `assert_called_once_with(best_moves)` | 全候補や先頭固定の選択。最高候補のみ一回抽選 |
| `test_ties_all_wins_and_all_losses` | 選択操作の境界テストで `_two_ply_score` を勝ち二つ、次に負け二つへ置換し、双方で元の二候補が一回抽選されることを確認。実詰みの成立は上二行で別途検証 | 勝敗同点への駒得・距離混入。勝敗の第二要素0を維持 |
| `test_selects_win_then_normal_then_loss` | 選択境界で三つの合法候補の評価をそれぞれ `(1, 0)`、`(0, 1000000)`、`(-1, 0)` に置換し、勝ち候補だけが抽選されることをassert。次に勝ち候補を除き通常値を-1000000へ変更して、通常候補だけが抽選されることをassert | 最大値選択の符号や区分優先の誤り。組の最大値を選ぶ |
| `test_empty_candidates_do_not_draw` | 新方針で空候補。`assertIsNone(selected)` と `choice.assert_not_called()` | 候補なしの抽選。入口でNone |
| `test_non_check_no_reply_uses_static_balance` | 先手５五飛のみの玉なし部分局面で５四飛後は後手手なし・詰みなし。`assertEqual(score, (0, 15))` | 手なしを勝敗へ変える誤り。静的評価へ |
| `test_non_check_no_move_at_leaf_uses_static_balance` | 先手駒なし、後手５五飛のみ、後手番の一手後相当局面。各応手後は先手手なし・詰みなし。`assertEqual(score, (0, -15))` | 二手後の手なしを負け扱い。既存詰み契約を維持 |
| `test_preserves_branches_for_promotion_drop_and_capture` | ９九玉・５四飛対１一玉・５三竜、先手持ち駒歩。５三飛成・５三飛不成・７七歩打の三候補を合法手と照合。選択前後の81マス・手番・双方の全持ち駒・候補を等値比較。単独候補時と複数候補時の各評価も一致。さらに、各候補の各応手をテスト側で毎回新しい一手後局面のcopyへ直接適用して参照評価を作り、製品の採点局面と参照局面の全状態・評価を応手ごとに照合する。正順・逆順の双方で同じ参照最小値となることをassert | 候補内で応手が同じ誤評価となり比較をすり抜ける誤りも検出。各候補と各応手へ独立したcopy |
| `test_stops_material_scoring_at_two_plies` | 教材局面で `material_balance` と公開 `legal_moves` を実処理ラップ。テスト側で各候補→各応手を一回ずつ直接適用して二手後局面の全状態と出現回数の参照集合を作る。採点局面の集合と回数が参照と一致し、各一手後局面からのみ公開応手生成されることを確認。詰み判定の内部防御確認は除外。手番一致だけを深さの証拠にしない | 三手以上の採点・不要な再帰の誤り。二段階の固定処理 |
| `test_does_not_hide_invalid_move_errors` | 非空候補に未知型、次に不合法な移動を渡し、`assertRaises(TypeError)` / `assertRaises(ValueError)` | Randomへのフォールバック。既存適用例外を伝える |

- [ ] 各行の局面を独立に検算してから共通サイクルを実施する。詰み教材に持ち駒を加えて防御が増えた場合、詰み成立しない局面を期待値に合わせて強行せず修正する。
- [ ] 既存 `MaterialEvaluationTests` と `WeakMoveSelectionTests` を含むファイル全体が成功する。一手限定・乱数委譲・既存駒価値を維持する。

### タスク3：CLIから三方式を選ぶ

対象：`cli.py`、`test_cli.py`、`test_cli_entrypoint.py`。消費は新方針値。生産する公開シグネチャは既存の `choose_move_selection_policy(input_fn=input, output_fn=print) -> MoveSelectionPolicy` のまま。

- [ ] `test_choose_move_selection_policy_maps_choices` に3を追加し、表示三名称と対応する方針値をassertする。旧表示・3未対応をRedとして確認する。
- [ ] メニューを `一手選択方針を選んでください（1: ランダム、2: 一手駒得、3: 二手先読み（駒得）、空入力: ランダム）:` に更新し、3を新方針へ対応させる。
- [ ] 無効入力テストの3を4へ置換し、`エラー：一手選択方針を1〜3で選んでください。` と再入力をassertする。空入力はRANDOMを維持する。
- [ ] `test_run_game_passes_selected_policy_to_computer_turn` と入口の方針受け渡しテストを三方式で確認する。新方式が一度だけ渡ること、人間対人間で問わないことをassertする。
- [ ] 各振る舞いで共通サイクルを実施し、`python3 -m unittest discover -s tests -p 'test_cli*.py' -v` が成功する。

### タスク4：USI設定と実応答

対象：`usi_engine.py`、`test_usi_engine.py`。消費は `choose_move` の既存シグネチャと新方針。生産する `run_usi_engine(input_fn, output_fn, rng=None) -> None` のシグネチャは変えない。

- [ ] option行の期待値を `option name Difficulty type combo default Random var Random var Material var TwoPlyMaterial` とし、通知欠落をRedで確認して通知へ追加する。
- [ ] `test_accepts_two_ply_material_case_insensitively`：新値と大小混在の値を設定してgo。既存spy境界で渡る方針を新値とassertし、辞書キーを追加する。
- [ ] `test_keeps_two_ply_policy_for_current_game`：新値設定→position→go→Material設定→go。二回とも新値とassert。続くusinewgame→position→goはMATERIALとassert。既存の局内固定・次局継承を維持する。
- [ ] `test_invalid_value_preserves_two_ply_setting`：新値→未知値→goは新値。無設定はRANDOM、旧Random/Materialも従来値をassertする。
- [ ] `test_two_ply_bestmove_is_legal_and_preserves_position`：教材のSFENを既存書出し操作で作り、新値設定とposition、go二回を送る。実選択を使い両bestmoveをparseし元局面のlegal_movesに含まれること、同じ局面が渡ることをassertする。全合法手では４五飛だけに限定しない。手なし局面のbestmove resignも新方式で確認する。
- [ ] 実プロセスの新値通知と合法bestmove、stdoutへ診断を混ぜないことを既存pipeテストの有限待ちで確認する。深さ2の実測時間が既存待ちを超えたら、失敗の理由と測定を記録して妥当な有限待ちを決める。
- [ ] 各振る舞いで共通サイクルを実施し、`python3 -m unittest discover -s tests -p 'test_usi_engine*.py' -v` が成功する。

### タスク5：全体検証・記録・統合

- [ ] `python3 -m unittest discover -s tests -v` を実行して成功を確認する。
- [ ] 教材局面と平手初期局面で三方式の選択時間を `time.perf_counter` で各3回計測し、機器・Python・乱数種・局面・最大時間を記録する。性能の合否閾値や棋力向上を事後に捏造しない。実用性を本人と確認し、遅さが問題なら未解決として報告する。対局棋力比較は別テーマとする。
- [ ] 必要なRefactorの要否を確認し、変更後は該当回帰と全体検証をやり直す。
- [ ] ブランチ全体の独立コードレビューを行い、Critical・Importantは解消後に再検証・再レビューする。Minorの対応も記録する。
- [ ] READMEの三択・USI値・二手探索の制約、知識メモ `31-weak-move-selection.md` と `usi-engine-response.md`、今回の学習記録・索引・再開案内を実績に合わせて更新する。ShogiHomeの実機確認を実施済みと書かない。
- [ ] import変更時は `.venv/bin/ruff check --select I --fix .`、続けて `.venv/bin/ruff format .`、`.venv/bin/ruff check .`、`git diff --check`、差分と文書リンクを確認する。検査回避はしない。
- [ ] 内容を確認して通常コミットする。main統合は本人承認を別途得る。元のディレクトリへの取り込み状況を明示し、取り込み先でも全体テスト・Ruff・リンクを検証する。
- [ ] 取り込み後、最後の理解確認を一問だけ出し、回答と補足を学習記録へ保存する。回答前に次テーマへ進まない。

## 今回の計画テーマの進捗

- [x] 開始Git状態、開発環境、設計、現行処理・対応テストを読み取り専用で照合。
- [x] USI値・内部識別名・公開API互換性を一つずつ合意。
- [x] 計画案を作成。
- [x] 自己確認・独立文書レビュー・リンクと差分検証。独立再レビュー残件はCritical 0・Important 0・Minor 0。
- [x] 本人へ計画全体を提示し、2026-10-10に「よい」と明示承認を得た。

計画案の承認は今回の実装開始を意味しない。未承認のmain統合・pushも行わない。今回の検証実績は学習記録へ記載する。
