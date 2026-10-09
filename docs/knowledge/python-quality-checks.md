# Pythonコードの整形・静的検査

## 現行設定

Ruff 0.16.10をプロジェクト内の `.venv` に導入し、Python 3.9を対象に、Pythonファイルだけを整形・検査する。行長は88を目安とし、行長違反E501は有効にしない。

`pyproject.toml` の `lint.select` は `E4,E7,E9,F,B,I,UP,PIE,RUF024,RUF026,RUF100`。基本ルールに加え、Bはflake8-bugbear由来の気付きにくい誤りを検査する。Iはimportのグループ分け・並び順・重複整理を確認する。I002（必須importの検査）も選択されるが、必須importの指定は追加していない。

- B006：既定引数の変更可能なデータ（リストなど）の共有を検査する。
- B008：既定引数の関数呼び出しが定義時に一度だけ実行されることによる誤りを検査する。例外もあり、関数呼び出しすべてを禁止する意味ではない。
- 既定引数は関数定義時に評価される。毎回新しいリストを使う場合は、既定値をNoneにし、関数内で生成する。

UPは対応Pythonで使える表記への統一、PIEは重複定義や不要な処理を検査する。RUF024は `dict.fromkeys` の可変値共有、RUF026は `defaultdict` の引数誤り、RUF100は不要な `noqa` を検出する。`lint.pyupgrade.keep-runtime-typing=true` により、Python 3.9で実行時に評価できないunion表記への変更を避ける。safeとunsafeは修正の分類であり、違反の重大度ではない。unsafe修正は一括適用しない。

リンターは型検査・単体テスト・コードレビューの代替ではない。Ruffの更新や追加ルールの有効化は、影響確認と検証を行う。

## ルール追加と更新の方針

現在の設定を基準とし、厳格化はいったんここで区切る。すべての誤りを防げるという意味ではなく、学習目的に対する追加の効果と保守負担を比較した判断である。

- 実際の不具合、繰り返すレビュー指摘、用途変更があったときに、対応する個別ルールを再検討する。ルール数や診断0件だけを採用理由にしない。
- 採用前に、検出したい誤り、現コードの診断、誤検出や例外、Python 3.9と日本語への影響を確認する。代表例で検出を確認し、変更に見合うテストとレビューを行う。
- `ALL` やpreview、ルール群全体を目的なく有効化しない。将棋の正しさはテストとレビューで確認する。
- Ruff更新は専用の変更として、リリース情報を確認し、`requirements-dev.txt` と `required-version` を同じ版へ更新する。READMEに従い `python3 scripts/setup_dev.py` を再実行し、作業ブランチの仮想環境への新版導入とフック設定を確認する。その後、整形検査・lintを実行し、新しい診断と整形差分を評価する。Python 3.9での動作、全体テスト、コミット前検査、別PCセットアップも確認してから取り込む。新しい診断を単に消すために一括修正や除外を追加しない。

根拠：[公式のルール選択指針](https://docs.astral.sh/ruff/linter/#rule-selection)、[フォーマッタとの競合](https://docs.astral.sh/ruff/formatter/#conflicting-lint-rules)、[バージョニング](https://docs.astral.sh/ruff/versioning/)。プロジェクト固有の比較と停止判断は[追加検査の記録](../learning/ruff-practical-rules.md#厳格化の区切りと運用方針)を参照する。

## 操作

```sh
.venv/bin/ruff check --select I --fix .
.venv/bin/ruff format .
.venv/bin/ruff check .
```

import整理は整形前に実行する。import順序はモジュール初期化の順序にも関わるため、整理後も差分を確認する。整形・検査・差分確認・テスト後にステージしてコミットする。フックはステージした設定とPythonコードを検査し、違反時にコミットを止める。ファイル保存だけではステージ内容は更新されない。修正後は `git add` が必要である。

別PCではREADMEのセットアップを行う。ルール追加による新しいパッケージ導入は不要で、設定が入ったコミットを取得すると既存の固定版Ruffが追加ルールを適用する。

## 参照

- [人間向けのセットアップ・日常操作](../../README.md)
- [初回導入の記録](../learning/ruff-local-quality-gate.md)
- [B追加の記録と学習例](../learning/ruff-bugbear-rules.md)
- [I追加の記録とimport整理](../learning/ruff-import-order.md)
- [Ruff I001公式資料](https://docs.astral.sh/ruff/rules/unsorted-imports/)
- [Ruff B006公式資料](https://docs.astral.sh/ruff/rules/mutable-argument-default/)
- [Ruff B008公式資料](https://docs.astral.sh/ruff/rules/function-call-in-default-argument/)

追加検査の比較・採否・検証は[学習記録](../learning/ruff-practical-rules.md)を参照する。
