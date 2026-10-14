# Python更新の影響調査・移行案

> 2026-10-14時点の調査と合意方針。移行先・最低対応版は本人が確定済み。実装の承認・実施記録ではない。

## 目的と範囲

Python 3.9のEOLを受け、現行コード・実行入口・開発環境・静的検査への影響を分けて調べ、移行の選択肢、検証計画、復帰方法を整理する。今回は現状調査と案の提示までとし、Python/Ruff/依存の導入・更新、コード・設定変更、テスト追加・実行、移行実施は行わない。

二手先読みと時計は「学習・実装テーマとしては完了。ShogiHome実機挙動と一般的な時間保証は未確認のまま」。今回のPython調査は、この未確認事項を解消したことを意味しない。

## 着手時の実測

2026-10-14に **/Users/oki2a24/kaname-shogi** で、指定順に次を確認した。

| コマンド | 結果 |
| --- | --- |
| git status --short --branch | main...origin/main [ahead 39]、開始時点でclean |
| git log -3 --oneline --decorate | HEAD 11d49ed、直近は 11d49ed, da6cb9a, d9307cf |
| .venv/bin/ruff --version | ruff 0.16.10 |
| git config --local --get core.hooksPath | .githooks |
| python3 --version / .venv/bin/python --version | どちらもPython 3.9.6 |
| command -v python3 / /usr/bin/python3 --version | /usr/bin/python3 / Python 3.9.6 |
| .venv/pyvenv.cfg | home = /Library/Developer/CommandLineTools/usr/bin、version = 3.9.6 |
| OS | macOS 27.0.1、arm64 |

現在のGit状態と履歴は引き継ぎ準備時点の値から変わっていたため、今回の実測を採用した。

## Python公式資料によるサポート状況

| 比較候補 | 2026-10-14時点の公式状態 | 選択上の特徴 |
| --- | --- | --- |
| Python 3.14.8 | 3.14系の最新保守版。3.14系はbugfix期間、EOLは2030-10予定 | **最低対応版を3.14系にする方針で合意**。実施時点の3.14系最新パッチを下限確認に使う |
| Python 3.15.0 | 2026-10-09公開の最新安定版。bugfix期間、EOLは2031-10予定 | **移行先を3.15系にする方針で合意**。公開から5日後の調査時点では新しいため、Homebrew `python@3.15` の実施時点最新パッチを通常版で使い、3.14系を最低対応にする |

Python 3.9は2025-10-31にEOL済み。3.10も2026-10-01にEOLとなった。3.11〜3.15は公式のサポート対象だが、3.11〜3.13はsecurity段階、3.14・3.15はbugfix段階である。合意した最低対応版を3.14系とするため、3.11〜3.13の公式サポート期間が残っていても、このプロジェクトの最低対応範囲には含めない。

Python公式macOSインストーラの3.15版はmacOS 10.15以降向けのuniversal2で、現ホストのmacOS 27.0.1 / arm64は要件上の対象に入る。3.15のインストーラは通常のGIL有効版に加えてfree-threaded版を別ビルドとして既定で導入する。free-threaded版の実行名は *python3.15t* であり、通常版とは環境とsite-packagesが分かれる。今回はどちらもインストールしていない。3.15ではテキストの既定エンコーディングがUTF-8になるが、対局記録と時計設定の本体読み書きはすでにUTF-8を明示している。Tk依存は見つからず、3.15公開ページにあるmacOS 27のTk注意事項はこのプログラムの直接依存ではない。

## 現行構成と影響

### 実行時Python

- kaname_shogi/、kaname-shogi-usi と実行テストはPython標準ライブラリだけを使う。実行時依存ファイルはない。
- 通常CLIは *python3 -m kaname_shogi*、USIモジュール入口は *python3 -m kaname_shogi.usi_engine*。
- ShogiHome登録用の kaname-shogi-usi はシバンが #!/usr/bin/python3。現在の python3 と同じPython 3.9.6を指す。新しいPythonを入れたり、python3 のPATH順だけを変えたりしても、この固定パスの入口は自動では切り替わらない。
- ソースは3.9で使える標準機能（dataclass、enum、typing、組み込みジェネリック型、str.removeprefix など）を使用する。game_record.py は遅延評価の型注釈を使う。調査した構文・標準APIから、3.14/3.15で明らかに廃止される依存は見つからなかった。これは静的な読取り結果であり、実行互換性の確認ではない。
- ファイル入出力の主要箇所はUTF-8を明示する。一方、開発セットアップのrequirements読込みや一部のテスト用テキストI/Oは既定エンコーディングを使う。3.15では既定値がUTF-8になるため、テスト結果と日本語出力を移行後に確認する。
- USIエンジンと対応テストは threading、queue、selectors、os.pipe、pty、POSIXの pass_fds を使う。現在の方針どおりmacOS/Linuxの範囲で確認し、Windows対応を今回の移行に含めない。

### 開発環境とRuff

- READMEのセットアップ条件はmacOS/Linux・Python 3.9以上。scripts/setup_dev.py もPOSIXと3.9以上を確認し、実行したPythonから .venv を作成する。
- セットアップスクリプトは既存 .venv のPythonを入れ替えない。Python更新後も既存環境が残る場合はそのまま再利用するため、READMEどおり旧 .venv を別名へ退避してから新Pythonでセットアップする必要がある。
- .githooks/pre-commit は .venv/bin/python からステージ済みファイル検査を起動する。.venv を退避した後に再構築が失敗するとフックは動けないため、復帰時は旧環境を .venv に戻す。
- Ruffは開発専用で、requirements-dev.txt は ruff==0.16.10。同じ版が pyproject.toml の required-version、READMEの期待値、tests/test_setup_dev.py のfixtureにも記録される。
- pyproject.toml の target-version = "py39" はRuffが保つ構文互換性の下限であり、実際の実行Pythonとは別の設定。keep-runtime-typing = true も、3.9で評価できない型注釈への自動変換を避ける意図がある。
- Ruff 0.16.10の公式変更履歴はPython 3.15をサポート対象に追加しているため、Pythonを3.15へ上げるだけでRuff更新が必須とは確認されなかった。Ruff 0.17.0も2026-10-09に公開済みだが、別の開発依存更新である。版を変える場合は、固定値の同期、診断・整形差分・3.9互換性の再評価が必要。
- プロジェクト公開用の requires-python などのパッケージメタデータ、tox/nox/uvによるPython版マトリクス、CI定義は見つからなかった。

## 合意した移行方針

2026-10-14、本人が次の方針を確定した。

- 移行先はHomebrewの通常版CPython 3.15系（`python@3.15`）。実施時点でHomebrewが提供する最新3.15.xパッチ版を使う。
- プロジェクトの最低対応版はPython 3.14系。3.11〜3.13は公式サポート中でも、このプロジェクトでは最低対応範囲から外す。
- Ruffの構文対象は`py314`にする。これは最低対応版の構文互換性を指定するもので、実行インタプリタの選択とは別。
- macOSでは通常のGIL有効ビルドを対象にする。free-threaded版（`python3.15t`）は今回の対象外。
- Python更新とRuff更新を分け、Ruff 0.16.10の固定は原則維持する。
- ShogiHome用の現行`#!/usr/bin/python3`はHomebrew導入だけでは切り替わらない。実際のHomebrew実行ファイルの場所を確認し、ランチャーを明示パスまたは検証済みラッパーへ移す方法を実施前に確定する。OS付属Pythonや全体PATHを無断で置き換えない。

実行時依存は追加しない。HomebrewでPythonを導入するタイミングは移行方針の合意と実施承認の後、移行作業に入る直前の事前確認とする。

実施承認後の手順案：

1. 作業用ブランチを作り、Homebrewの`python@3.15`を導入して実際の実行ファイルとバージョンを確認する。実施時点の最新3.15.xを記録する。
2. README・setup_dev.py・Ruff対象版を最低3.14に揃え、下限判定を3.14未満拒否へ更新する。必要ならUSIシバンまたは検証済みラッパーも更新する。
3. 既存`.venv`を削除せず退避し、HomebrewのPython 3.15実行ファイルを明示して`scripts/setup_dev.py`を実行する。Ruff固定は原則維持する。
4. Python 3.14系と3.15系の両方で下記検証を行い、差分と利用者向け手順を独立レビューする。Critical/Important指摘を解消してから記録を更新する。

## 検証計画と検出範囲

| 契約 | 代表ケース・検証 | 検出対象 | 未検証として残る範囲 |
| --- | --- | --- | --- |
| セットアップが最低対応版と一致する | Python 3.14系で`.venv`を作れるケースと、3.13系で環境・フック設定を変更せず停止するケース。既存`tests/test_setup_dev.py`に3.14受理・3.13拒否の境界確認を加える | 3.9など旧下限のまま受理する判定漏れ、下限ちょうどを誤拒否する不等号ミス、失敗前に環境やhookPathを変更する順序誤り | 今回はテスト追加・実行なし |
| テストとアプリが移行先で起動する | Python 3.14系と3.15系の両方で`.venv/bin/python --version`、`pyvenv.cfg`、`sys.executable`、CLI入口、USIモジュール入口を確認。ShogiHomeランチャーの実プロセス起動も実行 | PATHが旧Pythonを選ぶ、古い`.venv`を使う、シバンだけ旧Pythonに残る、USI初期応答/終了コードが変わる | ShogiHome画面からの実機接続・対局は別途承認なしに行わない |
| 既存の機能契約が維持される | Python 3.14系と3.15系それぞれの`.venv/bin/python -m unittest discover -s tests -v` | 将棋ルール、棋譜/設定JSON、並行入力、停止・プロセス終了、CLI/USI境界の既存回帰 | 有限の既存局面・OSでの検査であり、全入力や時間保証の証明ではない |
| 静的検査・コミット前フックが同じ固定版で動く | `.venv/bin/ruff --version`、`ruff format --check .`、`ruff check .`、`.githooks`設定確認。ステージ済み検査を通常フック経由で確認 | `py314`構文対象との不整合、新診断、整形差分、hookが旧/欠落環境を参照する誤り | Ruff更新も行う場合はその診断差分を別にレビューする |
| 日本語・設定/棋譜の入出力が保たれる | JSON設定と保存棋譜の既存テスト、UTF-8入出力、CLI/USI標準出力 | 既定エンコーディング変更による文字化け・読込失敗 | 非UTF-8ロケールや別配布元の挙動は今回の範囲外 |

観察指針に従い、単独ケースの検出対象と全体テストによる補完、未検証範囲を分けた。合意した範囲は通常版のみであり、free-threaded版の並行性特性は今回検証しない。

最低対応版を上げる実装では、現行 tests/test_setup_dev.py にない下限判定を固有契約として確認する。新しい最低版ちょうどを受理するケースと、一つ下の版を拒否し環境・hookPathへ触れないケースを分ける。後者のRed確認は隔離コピーで古い/誤った下限判定を入れ、期待する戻り値・変更なしのアサーションが失敗することを確かめる。読み込み失敗だけをRedと見なさない。復元後の単独テストと全体テストがそれぞれ検出する範囲を記録する。この調査ではテスト設計の方針までとし、テストの追加・実行はしていない。

今回テストは追加も実行もしていない。旧Python 3.9.6の既存テスト成功記録を新Pythonの検証結果として流用しない。

## 復帰方法

移行時も旧Pythonと旧 .venv を削除しない。新 .venv のセットアップまたは検証に失敗した場合は、選定版のプロセスを止め、新 .venv を別名へ退避して旧環境を .venv に戻す。.githooks設定を維持した状態でフックが旧 .venv/bin/python から動くことを確かめる。コード・設定変更は移行ブランチを戻すか、そのブランチを破棄し、現行mainへ未承認の統合をしない。OS付属の /usr/bin/python3 を書き換えない。

## 未決事項

- Homebrew導入時に提供される3.15.xの正確なパッチ版と、ShogiHomeランチャーが使う実行ファイルの明示パスまたはラッパー方式。
- Ruff 0.16.10を維持するか。現案は維持であり、Ruff更新は別の合意と影響確認が必要。
- LinuxでのセットアップはREADME上未実測のまま維持するか。今回の対象へWindows対応を追加しない。
- 変更・検証・独立レビュー後のmain統合は別途承認が必要。移行実施そのものもまだ明示承認されていない。

## Python/Ruff公式資料（2026-10-14確認）

- [Python versions status](https://devguide.python.org/versions/) — サポート状態とEOL日。
- [Python 3.14.8 release](https://www.python.org/downloads/release/python-3148/) — 3.14系最新保守版。
- [Python 3.15.0 release](https://www.python.org/downloads/release/python-3150/) — 安定版公開日、macOS installer、3.15の変更点。
- [PEP 790: Python 3.15 release schedule](https://peps.python.org/pep-0790/) — 3.15のbugfix/security期間。
- [Using Python on macOS](https://docs.python.org/3.15/using/mac.html) — universal2、対応macOS、通常版/free-threaded版の別。
- [Ruff FAQ](https://docs.astral.sh/ruff/faq/) — RuffのPython実行要件と対象版。
- [Ruff 0.16.10 changelog](https://github.com/astral-sh/ruff/blob/0.16.10/CHANGELOG.md) — Python 3.15をサポート対象へ追加。
- [Ruff versioning](https://docs.astral.sh/ruff/versioning/) — Ruffの版変更・互換性方針。
- [Ruff 0.17.0 changelog](https://github.com/astral-sh/ruff/blob/0.17.0/CHANGELOG.md) — 別途検討できる開発依存更新。
