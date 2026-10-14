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
