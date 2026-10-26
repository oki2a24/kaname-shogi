# C1比較対局CLIの局内高速化調査

2026-10-26開始。比較対局CLI `compare_games` の並列実行は既にあるため、並列化を増やさず一局内部の速度改善を検討する。本人は、同じ局面・乱数種・条件で各指し手と対局結果を変えない最適化に限定することを選んだ。確認比較や分析CLIの本番実行は人間が端末から行う。今回のC1局内計測は小さなpilotなので、アシスタントが承認済み設計に沿って実行した。

## 目的と対象

- ゴール: `compare_games` の一局内で大きい時間要因を特定し、意味を変えない具体的な最適化候補を選ぶ。
- 非対象: 分析CLI、B1評価式・係数、統計条件、worker数、通常対局CLI、USI。
- 実装段階: 本人が選んだ候補について、対象範囲・テスト検出力・性能確認方法を含む計画を作成し、明示承認後にTDD・実装・検証・独立レビューを完了した。専用ブランチへ記録とともにコミットする。main統合はしていない。
- この調査が終わったら、本人が終了を確認した旧版分析CLIの結果を確認し、C1の本筋へ戻る。

## 本人の選択と合意

- 2026-10-26、本人は局内計測を先に行う手法を選んだ。
- profile対象は既存512手pilotの6開始局面各1局。対象は`game-000001`、`game-000003`、`game-000005`、`game-000007`、`game-000009`、`game-000011`。
- 6局すべてで、同一seedなら指し手列・成功手数・終局理由・勝者が既存の局JSONと一致することを必須にした。各種時間値は一致条件から除外する。
- profile実行は、以前の2,040組比較より短い見込みならアシスタントが進めてよいと本人が回答したため実行した。
- 2026-10-26、本人は共有 `movegen` の最初の最適化案、非制御 `_has_legal_move` を既存first-only合法手探索へ接続する案を選び、[実装計画](../plans/2026-10-26-movegen-has-legal-move-short-circuit.md)全体を明示承認した。既存の真偽値・打ち歩詰め方針・局面不変を守り、TDD、誤り注入、固定6局の同値性と変更前後の短い再生計測を行った。専用ブランチで実装・検証・独立レビュー・記録を完了し、main統合はしていない。

## 実行方法

`/Users/oki2a24/.codex/worktrees/c1-analysis-resume/kaname-shogi` のPython 3.15.1で、`/private/tmp/c1_comparison_game_profile.py` に置いた一時スクリプトから `comparison.run_game` を直接呼び、標準 `cProfile` で6局を逐次計測した。比較CLI main、出力ディレクトリ、worker pool、保存ファイルへの書込みは使っていない。入力conditionsに保存された予定・方式別seedを再利用した。

profileは607秒（約10分7秒）かかり、当初の無計測比例目安約160秒より長かった。計測器が多数の関数呼出しを記録し、特に443手局が299秒を占めた。以前の12局pilot全体319.985秒よりは長く、C1確認比較の約6時間14分より大幅に短かった。profile時間は計測器負荷を含み、通常実行時間や高速化率ではない。

| game ID | 手数 | 終局 | 勝者 | profile wall |
| --- | ---: | --- | --- | ---: |
| game-000001 | 287 | 合法手なし | material | 89.516秒 |
| game-000003 | 186 | 合法手なし | material | 39.169秒 |
| game-000005 | 262 | 合法手なし | material | 87.848秒 |
| game-000007 | 45 | 詰み | material-rook-mobility | 22.302秒 |
| game-000009 | 215 | 合法手なし | material | 69.238秒 |
| game-000011 | 443 | 詰み | material-rook-mobility | 298.907秒 |

6局の全指し手列、勝者、終局理由、成功手数が既存結果と一致した。conditions、6局JSON、summary、局面セットJSONのSHA-256は計測前後で一致した。profile中の時間は既存結果との比較から除外した。計測局はC1強さ比較の追加標本ではない。

## プロファイル結果

累積時間には親子関数の重なりがあるため単純加算しない。

| 関数 | 呼出数 | 累積時間 |
| --- | ---: | ---: |
| `game_search.choose_move` | 1,438 | 400.584秒 |
| `one_ply_selection.choose_one_ply_move` | 719 | 302.477秒 |
| `movegen._has_legal_move` | 6,017 | 252.971秒 |
| `movegen.is_checkmate` | 89,066 | 234.770秒 |
| `GameRecord.from_payload` | 1,438 | 77.132秒 |
| `evaluation.material_balance` | 271,370 | 38.445秒 |

`choose_one_ply_move` は各候補手で `is_checkmate` を呼ぶ。詰み判定時の `_has_legal_move` はbooleanだけが要るが、非制御経路では全合法手を列挙する。一方、制御付きの `_has_legal_move_controlled` は既存 `_legal_moves_controlled(..., _first_only=True)` を通り、最初の合法手で終了する。したがって、非制御経路へ同じ早期終了を適用する案を最初の最適化候補として推薦する。真偽値の契約を維持し、指し手選択・乱数消費・棋譜・対局結果を変えない見込みだった。**この段落はprofile後・実装前の状態を記録しており、未実装・未検証だった。**

`GameRecord.from_payload` の累積77.132秒も削減可能性のある候補である。棋譜履歴の複製・再生を置き換えるため、最初の候補より変更範囲と正確さの確認が大きい。`rook_mobility_balance` は上位30関数に入らず、飛車可動性評価式の最適化を先行させる根拠は得られなかった。

## 実装開始後の変更前基準計測

2026-10-26、TDDでテストを追加する前に、同じ6予定・seedを一時スクリプト `/private/tmp/c1_comparison_game_timing.py` から無計測で再生した。6局の通常wall合計は164.437秒、各手の `elapsed_ns` 合計は143.252秒だった。各局の手数は287、186、262、45、215、443手で、保存済み結果と全指し手列・終局理由・勝者・予定が一致した。conditions、summary、6局JSON、局面セットのSHA-256も計測前後で一致し、実験結果ディレクトリへの書き込みはなかった。これは変更前の一回分で、変更後との差も6局に限る参考値として扱う。

## 検出範囲・未検証

- 直接照合は固定seed・6開始局面・各1局の棋譜と終局結果を検出する。既存結果に対応する各局JSON全体と入力SHAで再実行条件を確かめた。
- cProfileの呼出し時間は計測器の負荷を含み、通常実行の速度推定には使えない。
- 調査時点で未検証: 未選択の全局面・他seed・全OS/ Python版での時間分布、4,080局全体の速度改善率、最適化後の全局面同値性、旧版分析CLIの終了出力と結果。最後の項目は後日完了し、その後の記録を末尾に追記した。

## 実装・検証・独立レビュー（2026-10-26）

本人が[実装計画](../plans/2026-10-26-movegen-has-legal-move-short-circuit.md)全体を承認後、専用ブランチ `codex/movegen-has-legal-move-short-circuit` で作業した。`_has_legal_move` は `_legal_moves_controlled(..., control=None, _first_only=True)` を呼び、返った `moves` の有無を返す実装に変更した。合法手一覧の列挙順・規則・公開API・比較条件は変更していない。

### TDDとテスト検出力

- RED: `test_uses_first_only_search_when_a_board_move_exists` を追加し、実装前に実行。テスト本体が走り、旧経路で `_first_only` が `None` となる assertion failure を確認した。
- GREEN: 同テストを含む `LegalMoveEnumerationTests` 4/4、`CheckmateAndGameEndTests` 8/8、打ち歩詰め設定伝播1/1が成功した。
- 検出力の見直し: 当初、常にFalseを返す変異に公開 `has_legal_move` のテストを選んだが、その公開APIは `legal_moves` を全列挙し、今回変更した非公開 `_has_legal_move` を通らないと分かった。変異確認対象を新テストと `CheckmateAndGameEndTests` に直した。これはテスト経路の修正で、製品コードの仕様変更ではない。
- 一時コピーで `_first_only=False` と常にFalseの二変異を個別に注入し、それぞれ新テストの指定assertionで1件ずつ失敗することを確認した。実作業ツリーの製品コードには変異を入れていない。
- Refactor確認: 既存 `LegalMovesResult` とfirst-only生成器で足りるため追加抽象化なし。

### 固定6局の同値性と所要時間

既存pilotの同じseedを、変更前後に一時スクリプト `/private/tmp/c1_comparison_game_timing.py` から無計測で一度ずつ再生した。全6局のschedule・方式別seed・先後・開始SFEN・指し手列・手数・終局理由・勝者・error値が保存済み結果と一致した。conditions、summary、6局JSON、局面セットのSHA-256も両計測の前後で一致し、比較結果ディレクトリへの書き込みはない。

| game ID | 手数 | 通常wall 変更前→後 | 各手elapsed_ns合計 変更前→後 |
| --- | ---: | ---: | ---: |
| game-000001 | 287 | 24.323→16.759秒 | 20.224→12.580秒 |
| game-000003 | 186 | 10.479→8.884秒 | 8.694→7.070秒 |
| game-000005 | 262 | 23.795→15.312秒 | 20.312→11.785秒 |
| game-000007 | 45 | 6.013→3.376秒 | 5.896→3.258秒 |
| game-000009 | 215 | 19.011→12.686秒 | 16.678→10.322秒 |
| game-000011 | 443 | 80.806→43.882秒 | 71.448→34.304秒 |
| **合計** | **1,438** | **164.437→100.908秒** | **143.252→79.319秒** |

この一回の固定6局計測では、通常wallが約38.6%、`elapsed_ns`合計が約44.6%減った。ただし同一条件の一回ずつの観測であり、全局面・他seed・比較CLI本番の速度改善率へ一般化しない。変更後のcProfile再実行と4,080局比較は行っていない。

### 全体検証・レビュー

- 開始時点の全体テスト: 894件・58モジュール、22.290秒で成功。
- 変更後: `.venv/bin/ruff format .` は1ファイルを再整形、107ファイルは変更なし。`.venv/bin/ruff check .` 成功。`python3 scripts/run_tests_parallel.py` は895件・58モジュール、21.427秒で成功。`git diff --check` 成功。
- 独立コードレビュー: Critical 0、Important 0、Minor 1。Minorは実装前の現在状態文言が古いという指摘で、この記録で実装前の履歴と現在の実績を分けて修正した。コード上の修正指摘はなかった。

### 後日記録：旧版分析CLI完了とC1の一旦区切り（2026-10-26）

上記「未検証」「結果確認は未実施」は、この記録を作成した時点の状態である。その後、本人が初回比較と独立追試の旧版分析CLI完了を確認した。追試の4,080局分析では旧版・短縮版JSONの `analyzer` 以外の全項目が一致し、各出力でconditions・4,080局・summaryのSHA-256計4,082件も実ファイルと一致した。初回比較でも旧版・短縮版の全項目と入力SHAが一致している。両比較の統計判定は判断不能で、本人はC1を一旦区切ると決めた。結果の詳細は[C1学習記録](c1-rook-mobility-evaluation.md)と[分析CLI短時間化記録](c1-analysis-performance-investigation.md)を参照する。

この変更は、比較CLIの共有movegenを使う局内最適化であり、分析CLIの再開機能とは別である。

### ローカルmainへの統合・取り込み先検証（2026-10-27）

本人の明示承認を受け、分析reader短縮化と本変更をmain起点の統合候補 `codex/c1-cli-speedups-integration` に集め、独立レビューと候補検証後にローカルmainへfast-forwardした。元mainは `0d8be5b`、コード統合コミットは `ca94847`。分析CLI局単位再開は取り込まず、既存の比較CLI局単位 `--resume` は維持した。pushはしていない。

候補ブランチ全体で859件・57モジュールのテストが21.302秒で成功した。mainへ統合した後も `python3 scripts/run_tests_parallel.py` が859件・57モジュール、20.918秒で成功した。`.venv/bin/ruff check .`、`.venv/bin/ruff format --check .`（106ファイル）、`git diff --check`も成功した。候補全体の文書12件・788リンクと、統合後に変更した文書5件・754リンクのファイル・見出し参照は未解決0件。

独立コードレビューはコード統合前の `35dab5d` を対象に実施し、Critical 0 / Important 0 / Minor 1だった。Minorはこの記録が後続の旧版分析CLI完了を反映していない点で、後日結果と参照先を追記して`ca94847`で解消した。コードの変更はレビュー後に加えていない。

取り込み作業は `/Users/oki2a24/.codex/worktrees/c1-analysis-speedup/kaname-shogi` で行った。元の `/Users/oki2a24/kaname-shogi` はbranch `codex/c1-analysis-performance-investigation` の未コミット文書と比較データを保持し、変更・clean・resetしていない。詳細な現在状態は[再開案内](../resume.md)を参照する。
