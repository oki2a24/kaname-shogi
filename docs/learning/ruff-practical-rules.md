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

本人の回答：「壊れる可能性があるから」

アシスタントの補足：正解。unsafe修正は実行時の振る舞いやコメントを変える可能性がある。検出した違反の重大度とは別の分類なので、指摘を無視するのではなく、意図と影響を個別に確認して必要な修正・テストを行う。

回答追記は本人の内容確認・コミット前。README・次テーマ候補・プロジェクトの方向性を再確認し、既存の第76回「一手駒得評価の次段階を設計する」を引き続き推薦する。小さい順の候補は、一局面で評価の限界を学ぶ、次段階を設計する、自作ブラウザUIを設計する。追加ルールを次テーマの必須条件にはしない。

今回の追加で品質検査を一区切りにできるか、理解確認後に既存の第76回強化設計などの候補を再確認する。本人が選ぶまで次テーマは開始しない。

## 厳格化の区切りと運用方針

追加検査の理解確認後、本人はさらに厳しくする合理性、打ち止めの判断、インターネット調査と適用を希望した。公式資料を再確認し、固定版0.16.10で未採用ルールを読み取り専用で再検査した。現在の設定のlintは成功した。

- SIMは21件（SIM117が19件、SIM114・SIM105が各1件）、C4はC408が1件。
- PLは49件（PLR2004が39件、PLR0912が5件、PLW1510・PLR1714が各2件、PLC0415が1件）。PLW1510の2箇所は終了コードを既に個別確認しており、失敗確認漏れではなかった。
- RUF全体は222件で日本語記号関係が218件。RET・A・N・Wは各0件。

公式は明示的なルール選択、少数から段階的な追加、ALLの慎重な使用を勧める。無制限に増やすことを完成条件にはしない。現コードでは追加候補の多くが簡潔化や表記・設計上の判断を求め、追加の利益より変更・判断の負担が目立つと評価した。この比較は全未採用ルールの網羅的監査ではなく、候補群を使った判断である。

本人に「現設定を維持し、実際の不具合・繰り返すレビュー指摘・用途変更を再検討の条件とする。Ruff更新時は診断と整形差分を確認する。README・AGENTS・知識メモに記録する」という具体案を提示し、「良い」と承認を得た。

作業開始HEAD `1f0e001`、元の作業場所 `/Users/oki2a24/kaname-shogi`、ブランチ `codex/ruff-maintenance-policy`。前回の回答追記3文書を保持した。設定・Pythonコード・テストは変更せず、実装計画書は作らない限定的な文書更新として実施した。Refactor不要。文書6件のみの差分と相対リンクの参照先存在、`git diff --check`、Ruff両検査の成功を確認した。文書のみの変更なので全体テストは再実行していない。独立レビューはCritical 0件・Important 0件・Minor 1件。MinorはRuff更新後の仮想環境への再導入手順の明記であり、`python3 scripts/setup_dev.py` 再実行と版・フック確認を追記して対応した。レビュアーもリンク・見出し参照、候補診断数、現設定lint、差分検査を確認した。本人の「良い」による記録確認・コミット・統合承認後、`02d1e3e` をコミット前フック合格後に作成し、元の作業ディレクトリのmainへfast-forward統合した。main上で文書6件の参照先存在、差分検査、Ruff整形検査（28ファイル）・lintの成功を確認した。文書のみの変更であり全体テストの再実行は省略した。pushなし。

運用方針の最後の確認問題：今後Ruffルールの追加を再検討するのは、どのようなときか？

本人の回答：未回答。回答と補足は回答後に追記する。

出典：[公式設定指針](https://docs.astral.sh/ruff/linter/#rule-selection)、[SIM117](https://docs.astral.sh/ruff/rules/multiple-with-statements/)、[PLR2004](https://docs.astral.sh/ruff/rules/magic-value-comparison/)、[PLR0912](https://docs.astral.sh/ruff/rules/too-many-branches/)、[PLW1510](https://docs.astral.sh/ruff/rules/subprocess-run-without-check/)、[公式FAQ](https://docs.astral.sh/ruff/faq/#how-does-ruffs-linter-compare-to-pylint)、[バージョニング](https://docs.astral.sh/ruff/versioning/)。
