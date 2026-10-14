# Python更新の影響調査・移行案だけ

## 学習目的と範囲

2026-10-14、以前からのPython更新希望を現行構成に照らして調べる。Python公式のEOL・候補版、実行時Python、Ruffを含む開発環境、実行入口、テストの影響を分け、移行案・検証計画・復帰方法・未決事項を提示する。

移行先の系列と最低対応系列は確定したが、Homebrew導入時の具体的なパッチ版は未確定。Python/Ruff/依存の導入・更新、コード・設定変更、テスト追加・実行、移行実施は今回の範囲外。調査と案は[調査・移行案](../plans/2026-10-14-python-upgrade-impact.md)。その背景は[開始時の引き継ぎ](../handover-python-upgrade-impact.md)。

二手先読みと時計は「学習・実装テーマとしては完了。ShogiHome実機挙動と一般的な時間保証は未確認のまま」。

## 着手時の状態

2026-10-14、/Users/oki2a24/kaname-shogi、branch main、HEAD 11d49ed、origin/mainより39コミット先行、開始時の作業ツリーclean。Ruff 0.16.10、core.hooksPath=.githooks、python3と.venv/bin/pythonはともにPython 3.9.6だった。OSはmacOS 27.0.1 arm64。指定された入口文書とコード、テスト、セットアップ、コミット前フックを照合した。

## 要点

- Python 3.9は2025-10-31にEOL済み。着手時点でPython 3.14.8はbugfix期間、EOL予定2030-10。Python 3.15.0は2026-10-09公開の安定版でbugfix期間、EOL予定2031-10。本人は移行先を3.15系、最低対応版を3.14系に確定した。
- 実行時依存はPython標準ライブラリだけ。Pythonの最低対応版・開発時に作る.venv・Ruffの構文対象は別の判断である。
- 現行の /usr/bin/python3 はPython 3.9.6。ShogiHome用ランチャーも同じ絶対パスをシバンに持つため、新しいPythonをPATHへ追加するだけではランチャーが切り替わらない。
- Ruff 0.16.10はPython 3.15をサポート対象としている。Python更新からRuffの更新を分ける案とした。3.15のmacOSインストーラは通常版とfree-threaded版を別に導入し、free-threaded版は python3.15t として動く。
- .venvは作成時のインタプリタを保持する。READMEの手順どおり、移行時に削除せず退避してから選定Pythonで作り直す。失敗時は旧.venvを復元すれば、既存のコミット前フックが使うPythonも戻せる。
- テストは実行していない。検証計画には、セットアップ下限の境界、実際の実行インタプリタ、ゲーム/USI回帰、日本語入出力、Ruffとhookを分けて記載した。

## 本人が確定した移行方針

2026-10-14、本人は次の組み合わせを確定した。

- 移行先：Homebrewの通常版CPython 3.15系。導入時点で利用できる最新3.15.xを使う。
- 最低対応版：Python 3.14系。3.11〜3.13は公式サポート期間中でも、このプロジェクトの最低対応範囲から外す。
- Ruffの構文対象：`py314`。
- free-threaded版：今回の対象外。

この確定は移行実施の承認ではない。Pythonのインストール、コード・設定変更、テスト、移行は明示承認まで開始しない。

## 公式資料

[Python versions status](https://devguide.python.org/versions/)、[Python 3.14.8](https://www.python.org/downloads/release/python-3148/)、[Python 3.15.0](https://www.python.org/downloads/release/python-3150/)、[PEP 790](https://peps.python.org/pep-0790/)、[Python on macOS](https://docs.python.org/3.15/using/mac.html)、[Ruff FAQ](https://docs.astral.sh/ruff/faq/)、[Ruff 0.16.10変更履歴](https://github.com/astral-sh/ruff/blob/0.16.10/CHANGELOG.md)を2026-10-14に確認した。詳細は調査・移行案にある。

## 確認問題

**問1：** pyproject.tomlのRuff設定にある target-version = "py39" は、何を指定する値でしょうか。

**本人の回答：** Ruffが保つ構文互換性の下限を指定。

**アシスタントの補足：** その理解で正しい。target-versionは、Ruffが構文の検査やバージョン別の提案・整形を行う際に対象とするPythonの下限を表す。実行時のpython3や.venv/bin/pythonを選択する設定ではない。そのため、実行環境を新しいPythonへ変えても3.9互換を続けるならpy39を保てる。最低対応版を上げる場合に初めて、その決定に合わせて変更を検討する。

## 振り返りと次回への問い

実行時Python、仮想環境、Ruffの構文対象を別々に考える必要があることを確認し、移行先と最低対応版を確定した。実施時にはHomebrewが提供する正確なパッチ版とShogiHomeランチャーの実行パスを確認し、別途、移行実施の明示承認を得る。

## 移行実施記録（2026-10-14事後記録）

本人は調査・計画の後に「移行実施」と指示し、事前承認済み計画に沿う変更を `codex/python-315-migration` で開始した。候補版・下限は選定済み方針を維持し、Ruffと開発依存の更新、ShogiHome GUI操作、main統合は行わない範囲とした。

### 実環境

- Homebrew CPython 3.15.0 (`/opt/homebrew/bin/python3.15`) を開発用 `.venv` に使用し、CPython 3.14.8 (`/opt/homebrew/bin/python3.14`) を最低版検証に使った。OSはmacOS 27.0.1 arm64。
- `.venv` はCPython 3.15.0、Ruffは固定版0.16.10、`core.hooksPath` は `.githooks`。元のPython 3.9.6環境は削除せず `/private/tmp/kaname-shogi-venv-python39-20261014` に退避した。
- 3.14.8のテスト環境は `/private/tmp/kaname-shogi-venv-python314-test-20261014` に作成し、全件検証後に削除した。Homebrew側の依存としてmpdecimal 4.0.1が入った。OS付属Python、全体PATH、ShogiHomeの保存済み登録は変えていない。

### 変更と理由

- `scripts/setup_dev.py` はホストPythonと既存 `.venv` の両方で3.14以上を要求するようにした。ホストが3.14でも、古い3.13 `.venv` を誤再利用しないことをテストで確認する。
- `pyproject.toml` のRuff `target-version` を `py314` に変更した。Ruff 0.16.10、`requirements-dev.txt`、`required-version`、選択ルール、`keep-runtime-typing=true` は維持した。
- `py314`の診断で、`Optional`/`Union`をPEP 604形式へ更新し、古い文字列前方参照を除き、`Callable`を `collections.abc` から読み込む箇所を整理した。Python 3.14で遅延評価注釈の仕様が導入されていることを踏まえ、3.14と3.15双方で実行した。`except EOFError, KeyboardInterrupt` はPython 3.14のPEP 758構文である。
- `target-version`切替直後の診断は合計51件（UP045が32、UP007が7、UP035が4、UP037が4、B905が4）。診断の意味と移行先を照合し、既存のルールや除外を増やさず対応した。
- B905の `zip` 4か所に意図を明示した。対応する長さが一致する3か所は `strict=True`、13種類の駒を79マスへ対応させる意図的な不一致1か所は `strict=False` とコメントを付けた。
- `kaname-shogi-usi` はPOSIX shellランチャーへ変更し、clone内 `.venv/bin/python` でモジュールを起動する。これによりShogiHomeのプロセスがHomebrewのPATHを引き継ぐかに依存せず、別cwdからもclone設定を読み込める。3.13は起動拒否、3.14は受理、cwd維持もテストした。ShogiHome GUIでの接続は今回確認していない。
- README、ShogiHome接続手順、Python品質検査の現行案内と、再開案内・索引・計画を更新した。過去の調査時点や当時の確認問題の回答は履歴として保持した。

### TDDとRefactorの確認

境界テストを先に作成し、旧実装ではsetupが3.13を通すこと、ShogiHomeランチャーがclone内 `.venv` を使わないことをRedとして確認してから、下限チェックとランチャーを変更した。後から追加した既存3.13仮想環境テストは依存導入前の停止を、launcherの偽Pythonテストは3.13拒否・3.14受理を確認する。Refactor要否を見直し、追加の整理は行わなかった。レビュー後にcwd検査のパス正規化差を修正した際も、失敗と修正後の該当テスト通過を確認している。

根拠となる一次資料は、[Python 3.14の遅延評価注釈（PEP 649/749）](https://docs.python.org/3.14/whatsnew/3.14.html#pep-649--pep-749-deferred-evaluation-of-annotations)、[複数例外の括弧省略（PEP 758）](https://peps.python.org/pep-0758/)、[Ruffの`keep-runtime-typing`](https://docs.astral.sh/ruff/settings/#lintpyupgradekeep-runtime-typing)、[UP045](https://docs.astral.sh/ruff/rules/non-pep604-annotation-optional/)、[UP007](https://docs.astral.sh/ruff/rules/non-pep604-annotation-union/)、[B905](https://docs.astral.sh/ruff/rules/zip-without-explicit-strict/)。

### 検証結果

- `.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`、`.venv/bin/ruff format --check .`、`.venv/bin/ruff check .` は成功した（最終時点で38ファイル整形済み、診断なし）。
- CPython 3.15.0の `.venv/bin/python -m unittest discover -s tests -v` と、CPython 3.14.8の一時環境で同じ全体テストを個別に実行し、各463テストが成功した。
- cwd保持テストの初回はmacOS一時パス `/var/...` と `/private/var/...` の別名を比較して失敗した。`Path.resolve()` 後の比較へ修正し、該当テストと両Pythonの全体テストが成功することを確認した。これはテストのパス正規化差で、起動cwdが変わった動作不良ではなかった。
- 独立レビューはコード・テスト・移行案内を確認し、最終結果はCritical 0・Important 0・Minor 0。初回レビューで挙がったREADME案内先とcwdテスト期待値は、README更新と実パスの正規化比較で解消し、再レビューで確認した。最終レビュー担当はテストやRuffを再実行していない。通常のコミット前hookは通常の `git commit` で実行され、「38 files already formatted」「All checks passed!」を確認した。

### main統合と取り込み先検証（2026-10-14事後記録）

実装コミット `358f4ac` の後、本人の明示承認を受けて `/Users/oki2a24/kaname-shogi` の `main` を `1c148bd` から `358f4ac` へfast-forwardした。pushはしていない。取り込み先の `main` で `.venv/bin/python -m unittest discover -s tests -q` を実行し、463件成功した。`.venv/bin/ruff check .` と `.venv/bin/ruff format --check .` も成功し、38ファイルが整形済みだった。検査fixture由来の標準エラー出力はあったが、テスト全体の終了コードは0である。

### 未確認範囲と復帰

Linux、Windows、free-threaded版、ShogiHome実機の起動・対局は対象外で未確認。Homebrew Pythonは他用途の可能性があるため削除しない。復帰時は新 `.venv` を別名へ退避し、退避したPython 3.9 `.venv` を元の位置へ戻せる。Git上の変更はコミット `358f4ac` としてmainに統合済みであるため、問題があれば原因を調査し、修正コミットまたは明示的なrevertで復帰する。

main統合と取り込み先での検証は完了した。最後の理解確認として、次の一問だけを提示し、本人の回答を待つ。回答と補足は受領後にこの記録へ追記する。二手先読みと時計は「学習・実装テーマとしては完了。ShogiHome実機挙動と一般的な時間保証は未確認のまま」。本人の回答を記録するまで次テーマを選定・開始しない。

**最後の理解確認：** この移行で、実行時Pythonの最低対応版を3.14にし、開発用の実行環境を3.15にし、Ruffの`target-version`を`py314`にした理由を、それぞれ何に影響する設定・選択かに触れて説明してください。

**本人の回答：** 「動作保証を3.14と3.15、ryffには3.14以降を対応」

**アシスタントの補足：** 概ね捉えられている。プロジェクトの実行時最低対応版はPython 3.14で、実際にCPython 3.14.8と3.15.0で全463テストを実行した。したがって「3.14と3.15」は実測した版を指し、3.14以上を対応下限とする宣言はすべての将来版を個別に検証済みという意味ではない。開発用 `.venv` を3.15にしたのは、このcloneで使う具体的な開発インタプリタの選択で、セットアップの下限は3.14以上である。Ruffの`target-version = "py314"`は、Ruffが診断・整形時に前提とするPython構文の対象を3.14にする設定であり、Ruff自体の対応版一覧や実行Pythonを指定するものではない。

この理解確認を記録し、Python移行テーマを完了とする。二手先読みと時計は「学習・実装テーマとしては完了。ShogiHome実機挙動と一般的な時間保証は未確認のまま」。次テーマは未選定であり、候補と推薦理由は[次テーマ候補](../next-topics.md)に記録する。
