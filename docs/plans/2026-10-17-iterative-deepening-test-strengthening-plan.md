# 反復深化で留保したテスト2件を補強する 実装計画

> **状態：作業ブランチへの実装・記録コミット済み。main未統合。** 本人は計画提示後に「yes」と回答した。製品コードは変更していない。

**目標:** 前テーマの独立レビューで留保した2件について、独立ストリーム間の前回手混在と単独αβ段階の内部例外隠蔽を、対象テスト単独でも検出できるようにする。

**範囲:** `tests/test_search_iterative_deepening.py` と `tests/test_search_compare_iterative.py` の対象テストを補強する。現在の探索コードは契約どおり動作している。製品コードの変更は予定しない。元実装が新しいテストに失敗した場合は製品不具合として扱わず、まず期待値・テスト設計・現物を照合して本人へ報告し、範囲変更を承認なしに行わない。

**継続する制約:** Random（最弱・既定）、一手駒得、現行二手先読みを維持する。SOLID・DRYに沿った小さな範囲とし、時間制御・通常対局接続・評価方式変更・将来機能を加えない。後続テーマ「反復深化の停止と既存時間制御の接続を学び設計する」は開始しない。

**想定モデル:** 本人指定のGPT-6 Luna、推論強度Medium。実行方式はこのセッション内での実装を推薦し、最後に独立レビューを受ける。mainへの統合は別途本人の承認を得る。

## 契約・検出したい誤り・代表ケース

| 対象 | 契約 | 代表ケースと期待値 | 検出したい誤り |
| --- | --- | --- | --- |
| `test_records_are_immutable_and_streams_independent` | 反復ストリームごとに前回完了時の最善手を保持し、そのストリームの次の深さへだけ渡す。完了記録・累計も独立する | `changing_tree()` は深さ1でAを選ぶ。もう一方は `depth_tree()` の根直下A/Bの浅い評価をA=(0, 0)、B=(0, 1)として深さ1でBを選ばせる。交互に取得し、呼出し記録 `(ストリーム, 深さ, preferred_move)` が `first/1/None`, `second/1/None`, `first/2/A`, `second/2/B` となることを確認する。既存の不変性・result同一性・累計確認は残す | 前回手をモジュール共有状態などへ置き、別ストリームのBを `first` の深さ2へ渡す |
| `test_input_and_internal_errors` | 入力エラーだけを終了2に変換し、探索内部のValueErrorは発生した段階を問わず伝播する | 反復中のαβ呼び出し（`preferred_move` キーワードあり）は実αβへ委譲し、同キーワードのない単独αβ呼び出しだけValueErrorを発生させる。深さ1の反復呼出しの後、深さ1の単独比較で例外が伝播することを確認する | 単独αβ呼び出しの例外だけを握り潰す、または単独段階に到達する前に例外を起こして確認をすり替える |

期待値はテスト用数値木の明示値と呼出し段階から決める。製品の結果から期待値を逆算しない。二つの例は代表的な回帰であり、全てのストリーム順序や例外型を証明するものではない。

## タスク1：独立ストリームの前回手を観察する

**ファイル:** `tests/test_search_iterative_deepening.py`。製品コードは変更しない。

- [x] `test_records_are_immutable_and_streams_independent` の2つ目の木を、深さ1の最善手が1つ目と異なるようにした。`depth_tree()` の深い順序特性を保ちつつ、根直下A/Bの深さ1評価をA=(0, 0)、B=(0, 1)にした。docstringへ前回最善手の共有を追加した。
- [x] `alpha_beta.search` ラッパーで根オブジェクト・深さ・`preferred_move` を記録し、交互取得時の期待列を確認するようにした。
- [x] 既存の凍結記録・結果オブジェクト同一性を保ち、2つ目の浅い結果Bと累計 `(3, 8)` を確認するようにした。訪問数は変わらなかった。
- [x] 変更前の基準テストは1件成功。変更後は対象1件と反復テスト群8件が成功した（既存実装での初回Green）。

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_search_iterative_deepening.py' -k 'records_are_immutable_and_streams_independent' -v
.venv/bin/python -m unittest discover -s tests -p 'test_search_iterative_deepening.py' -v
```

## タスク2：単独αβ段階の例外伝播を区別する

**ファイル:** `tests/test_search_compare_iterative.py`。製品コードは変更しない。

- [x] `test_input_and_internal_errors` で `preferred_move` キーワードの存在を判定するようにし、存在時は実αβへ委譲、欠如時は識別可能なValueErrorを送出するようにした。docstringへ単独αβの例外隠蔽を追加した。
- [x] 呼出し記録で反復αβ深さ1、単独αβ深さ1の順を確認し、単独段階のValueError伝播を確認するようにした。
- [x] 既存の入力エラー・help・反復深化と全幅探索での内部ValueError伝播を保持した。
- [x] 変更前の基準テストは1件成功。変更後は対象1件と比較CLIテスト群9件が成功した（既存実装での初回Green）。

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_search_compare_iterative.py' -k 'input_and_internal_errors' -v
.venv/bin/python -m unittest discover -s tests -p 'test_search_compare_iterative.py' -v
```

## タスク3：誤り注入・回帰・レビュー・記録

- [x] 代表変異を一件ずつ注入し、対象テスト単独と全体513件で意図したアサーションが失敗することを確認した。全体検証では、コピー環境が既存プロセス起動テストに必要な環境と一致せず無関係な失敗を出したため、実作業環境で製品コードへ一時変異を当てて同じ検証をやり直した。各変異後に製品コードを元へ戻した。
  - 反復の前回手をストリーム間で共有する。
  - 単独 `alpha_beta.search` のValueErrorを握り潰す。
- [x] 独立ストリーム変異は対象テストで `first` の深さ2にBが渡る呼出し記録の不一致となり失敗した。実作業環境の全体テストも513件中このテストだけが失敗し、他512件は通過した。
- [x] 単独αβのValueError隠蔽変異は対象テストで `ValueError not raised` となり失敗した。実作業環境の全体テストも513件中このテストだけが失敗し、他512件は通過した。
- [x] 変異を戻した実作業環境で全体513件が成功した。コピー上の単独変異テストも狙ったAssertionErrorで失敗することを確認した。コピー上の全体テスト結果は実行環境差のため判定資料に採用していない。
- [x] `.venv/bin/python -m unittest discover -s tests -q` は513件成功。Python変更後の `.venv/bin/ruff format .` と `.venv/bin/ruff check .` は成功（import追加・変更なし）。最終の再検証はレビュー対応後に行う。
- [x] Refactor要否を確認した。二つの対象テストにだけ局所的な観察コードを置き、重複の共通化や抽象化は不要。
- [x] 独立レビューを実施。Criticalなし、Importantなし、Minorなし。テスト期待値・対象コード・文書の不整合なしとの報告を受け、修正は不要。
- [x] 学習記録へレビュー結論を追記し、`docs/README.md`、`docs/next-topics.md`、`docs/resume.md` をレビュー完了状態へ更新。更新後にローカル文書リンク525件と `git diff --check` を確認。
- [x] レビュー後に `.venv/bin/python -m unittest discover -s tests -q` を再実行し513件成功。`.venv/bin/ruff format .` は59ファイル変更なし、`.venv/bin/ruff check .` 成功。
- [x] 本人承認済み計画の範囲を作業ブランチへコミットした。テスト・文書のコミットは `7f32f3e` (`test: strengthen iterative deepening regression coverage`)。続く現在地の記録はdocsコミットに保存する。main統合は別途本人の承認を待つ。

## 承認前の自己点検

- 対象契約、二つの代表ケース、各変異、単独テストと全体テストの範囲、未検証事項を記載した。
- 前テーマのレビューで未実施だった全体513件への変異注入は、今回、実際の件数と結果を記録する計画にした。前回の件数・検証結果は今回の結果として流用しない。
- 本人の計画承認後にテスト変更へ進み、TDDの既存実装初回Green・代表変異FAIL・復元後Greenを別々に確認した。現行製品コードは変更していない。
- 独立レビュー後の全体513件・Ruff・文書リンク・差分点検が成功し、作業ブランチへコミット済み。main未統合・未push。次の文書更新はmain統合の承認後の判断・結果を記録する時点。後続テーマは開始しない。
