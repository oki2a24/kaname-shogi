# Pythonコードの整形・静的検査

## 現行設定

Ruff 0.16.10をプロジェクト内の `.venv` に導入し、Python 3.9を対象に、Pythonファイルだけを整形・検査する。行長は88を目安とし、行長違反E501は有効にしない。

`pyproject.toml` の `lint.select` は `E4,E7,E9,F,B,I,UP,PIE,RUF024,RUF026,RUF100`。基本ルールに加え、Bはflake8-bugbear由来の気付きにくい誤りを検査する。Iはimportのグループ分け・並び順・重複整理を確認する。I002（必須importの検査）も選択されるが、必須importの指定は追加していない。

- B006：既定引数の変更可能なデータ（リストなど）の共有を検査する。
- B008：既定引数の関数呼び出しが定義時に一度だけ実行されることによる誤りを検査する。例外もあり、関数呼び出しすべてを禁止する意味ではない。
- 既定引数は関数定義時に評価される。毎回新しいリストを使う場合は、既定値をNoneにし、関数内で生成する。

UPは対応Pythonで使える表記への統一、PIEは重複定義や不要な処理を検査する。RUF024は `dict.fromkeys` の可変値共有、RUF026は `defaultdict` の引数誤り、RUF100は不要な `noqa` を検出する。`lint.pyupgrade.keep-runtime-typing=true` により、Python 3.9で実行時に評価できないunion表記への変更を避ける。safeとunsafeは修正の分類であり、違反の重大度ではない。unsafe修正は一括適用しない。

リンターは型検査・単体テスト・コードレビューの代替ではない。Ruffの更新や追加ルールの有効化は、影響確認と検証を行う。

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
