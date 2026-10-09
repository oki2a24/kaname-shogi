# Ruff追加検査の選定と適用（2026-10-09）

## 目的・合意・範囲

本人は「さらに厳しくする合理性はあるか」「インターネットでベストプラクティスを調べて適用したい」と希望した。目的はルール数そのものではなく、学習時の読みやすさとPython 3.9対応を保ちつつ、見逃しやすい誤りを減らすことである。

公式資料と既存コードへの読み取り専用検査を比較後、UP・PIE・RUF024・RUF026・RUF100追加、型表記の個別修正、代表違反と実コミットの検証、全テスト・独立レビュー・説明更新の短い具体案を提示し、本人が「良い」と承認した。限定された既存設定の拡張として独立計画書は作らず実施した。本書は調査・合意・実施を整理した記録である。

開始HEAD `0262832`、作業場所 `/Users/oki2a24/kaname-shogi`、ブランチ `codex/ruff-practical-rules`。別worktreeなし。開始時にIの本人回答など3文書が未コミットだったため保持した。本人の記録確認・統合承認後、`ab62a64` をmainへfast-forwardで取り込み済み。pushなし。

## 公式資料と判断

公式は明示的な `select`、少数から段階的にルール群を追加する方法、`ALL` の慎重な使用を勧める。ルール群の追加は公式に沿うが、以下の具体的な組合せはこのプロジェクトでの判断であり、公式の万能設定ではない。

- [ルール選択の指針](https://docs.astral.sh/ruff/linter/#rule-selection)
- [自動修正の安全性](https://docs.astral.sh/ruff/linter/#fix-safety)
- [フォーマッタとの併用](https://docs.astral.sh/ruff/formatter/#conflicting-lint-rules)
- [UP007と実行時の型評価](https://docs.astral.sh/ruff/rules/non-pep604-annotation-union/)
- [RUF100：不要な検査除外](https://docs.astral.sh/ruff/rules/unused-noqa/)

safeは実行時の意味を保つ意図の修正、unsafeは意味やコメントが変わり得る修正であり、指摘の重大度ではない。違反の検出と修正の自動適用を分ける。コミット前フックは検査のみとする。固定版0.16.10、Python 3.9、行長88、Pythonのみという範囲を維持し、previewは有効化しない。

## 候補比較（設定変更前の現コード）

| 候補 | 診断数 | 採否と理由 |
|---|---:|---|
| UP | 10 | 採用。対応Pythonで使える型などの表記を統一する。実行時型評価への配慮後は6件 |
| PIE | 0 | 採用。クラスの重複定義・Enum値の重複などを検出し、不要な処理も整理する |
| RUF024・RUF026・RUF100 | 0 | 個別採用。可変値共有・defaultdictの引数ミス・不要な検査除外を防ぐ |
| SIM | 21 | 見送り。19件はテストのwith入れ子整理。主に簡潔化であり今回の優先度は低い |
| C4 | 1 | 見送り。今回の指摘はdict呼出しの表記改善 |
| RUF全体 | 222 | 見送り。RUF001〜003が218件で日本語の全角記号などを指摘。残りはRUF022が1件、RUF005が3件 |
| S | 56 | 全体は見送り。将棋用乱数33件、SFENのtokenなど9件、subprocess関係13件、一時パス1件。個別のセキュリティ監査完了を意味しない |
| A・RET・N・W | 各0 | 今回は追加しない。診断0件だけを採用理由にしない |
| ARG | 4 | 見送り。テスト用コールバックの未使用引数が中心 |
| D | 1133 | 全体は見送り。1068件はdocstring末尾の句点等。日本語の記録方針と合う個別選択は別途検討可能 |
| PT | 812 | 見送り。unittestをpytest形式へ変える診断であり現行方針と合わない |

採用ルールにより既存の不具合が判明したわけではない。今回のコード修正は型表記の統一で、追加の誤り検出は将来の予防である。

RUF024は `dict.fromkeys(["a", "b"], [])` で両キーが同じリストを共有する誤りを検出する。RUF026は `defaultdict(default_factory=list)` が既定値生成の指定ではなく辞書項目の登録になる誤りを検出する。PIE796はEnumの値重複を検出する。意図的な別名などは診断を根拠に個別判断する。

出典：[RUF024](https://docs.astral.sh/ruff/rules/mutable-fromkeys-value/)、[RUF026](https://docs.astral.sh/ruff/rules/default-factory-kwarg/)、[PIE794](https://docs.astral.sh/ruff/rules/duplicate-class-field-definition/)、[PIE796](https://docs.astral.sh/ruff/rules/non-unique-enums/)。

## 実際の変更と検証

1. `pyproject.toml` にUP・PIE・RUF024・RUF026・RUF100と `lint.pyupgrade.keep-runtime-typing=true` を追加した。遅延評価があるPython 3.9でも提案される `Union` → `X | Y` の変更を避け、現在の実行時型評価の互換性を保つ。
2. `movegen.py` の `Tuple` 4箇所をPython 3.9で使用可能な `tuple` に変更し、不要になったimportを除去した。`game_record.py` は遅延評価があるため戻り値の `"GameRecord"` を `GameRecord` にした。型名はデータの種類を表し、tupleは要素を変更できない並びを表す型であって操作ではない。`tuple[Move, ...]` は任意個のMoveを保持する。Unionは複数の候補型のいずれかを表す。将棋の処理・引数・副作用は変更しない。
3. UP006の修正はRuffでunsafe扱いのため、`--unsafe-fixes` を一括使用せず個別に変更した。
4. `/private/tmp/kaname-ruff-extra-probe.py` の代表違反（UP・PIE796・RUF024・RUF026・RUF100）は、旧設定で終了0となり「検出する」という期待を満たさなかった（Red）。新設定で6診断・終了1となり期待を満たした（Green）。読み込みエラーをRedとして扱っていない。
5. `/private/tmp/kaname-ruff-extra-hook.py` は一時Gitリポジトリで旧設定のcommit成功、新設定をステージすると上記違反でcommit停止・HEAD不変、個別修正と再ステージ後のcommit成功を確認した。検証用スクリプトは使い捨てであり配布物ではない。
6. Python 3.9.6でRuff整形検査（28ファイル）とlintが成功し、`python3 -m unittest discover -s tests -v` の全340テストが成功した。変更した5関数の型注釈は `typing.get_type_hints` によるPython 3.9.6での実行時評価も成功した。確認用コマンドの初回は存在しない関数名の指定で失敗し、実際の `choose_move` に訂正して再確認した。README・AGENTS・知識メモ・索引・再開案内を更新した。新しい依存関係やGitスクリプトの変更は不要。

## Refactor・独立レビュー

Refactor不要。型表記の限定変更であり、責務や将棋処理の変更は必要ない。

別レビュアーの独立レビューはCritical 0件・Important 0件・Minor 1件。Minorは本書の「tupleは固定長」という説明が `tuple[Move, ...]` の任意個の要素と混同し得る点であり、「要素を変更できない並び」「任意個のMove」に修正した。コードへの修正要求なし。レビュアー自身もPython 3.9.6で型注釈評価、Ruff両検査、全340テスト、一時リポジトリの実コミット検証を再実行し成功した。

## 現在地・確認問題・次回への問い

実装・検証・独立レビューとMinorの説明修正後、本人が「良い」と記録確認・コミット・main統合・再検証を承認した。コミット前フック合格後に `ab62a64` を作成し、元の作業ディレクトリのmainへfast-forward統合した。main上でRuff整形検査（28ファイル）・lint・全340テストが成功した。別worktree・pushなし。

最後の確認問題：Ruffが修正をunsafeと分類した場合、指摘内容は確認しつつ一括自動修正を避けるのはなぜか？

本人の回答：未回答。回答と補足は回答後に追記する。

今回の追加で品質検査を一区切りにできるか、理解確認後に既存の第76回強化設計などの候補を再確認する。本人が選ぶまで次テーマは開始しない。
