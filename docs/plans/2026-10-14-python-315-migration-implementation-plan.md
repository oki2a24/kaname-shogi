# Python 3.15移行 実装計画

> 2026-10-14作成。以下の計画は、本人がHomebrew CPython 3.15系とPython 3.14系の最低対応を決めた後、実施承認前に記録した。作成時点ではコード・設定・テスト・環境は変更していなかった。実施結果は末尾に事後記録する。

## 目的

Homebrewの通常版CPython 3.15系へこのcloneの実行・開発環境を移し、プロジェクトの最低対応版を3.14系に揃える。Ruffは0.16.10を保ち、構文対象を`py314`へ変更する。ShogiHomeに登録済みの起動ファイル名は維持し、その起動ファイルが選定Pythonを確実に使うようにする。

移行後も実行時依存はPython標準ライブラリだけとし、対応OSはmacOS/Linuxとする。Linuxは今回のホストでは実機検証できないため、実測対象外と明記する。ShogiHomeの画面設定変更、接続、対局はこの計画に含めない。

## 合意済みの決定

- 移行先：Homebrew `python@3.15` の通常版。現行formulaは3.15.0。実施時にformulaが更新されていれば、その時点の最新3.15.xを使い、実バージョンを記録する。
- 最低対応版：Python 3.14系。下限確認にはHomebrew `python@3.14` の実施時点の最新パッチ版を使う。現行formulaは3.14.8。
- Ruff構文対象：`py314`。Ruffと開発依存の固定版は更新しない。
- Python 3.15 free-threaded版は今回使わない。
- Homebrew導入は移行作業の事前確認として行う。OS付属の`/usr/bin/python3`や全体PATHを置き換えない。

Homebrewはversioned formulaとして3.15系と3.14系を提供し、3.15系を通常版として選べる。Homebrew formulaは更新されるため、インストール直前に状態を再確認する。[python@3.15](https://formulae.brew.sh/formula/python@3.15)、[python@3.14](https://formulae.brew.sh/formula/python@3.14)、[HomebrewのPython案内](https://docs.brew.sh/Language-Runtimes-and-Packages)

## 変更対象

1. `scripts/setup_dev.py`
   - 最低版チェック、`.venv`内Pythonの検査、メッセージ、docstringをPython 3.14以上に揃える。
   - 3.13以下では`.venv`作成・パッケージ導入・フック設定より前に停止する。
2. `tests/test_setup_dev.py`
   - 3.14を受理し、3.13を副作用なく拒否する下限境界テストを追加する。
3. `pyproject.toml`
   - `target-version`を`py314`に変更する。`required-version`、Ruffルール、`keep-runtime-typing`は維持する。
4. `kaname-shogi-usi`と`tests/test_usi_engine_launcher.py`
   - 既存のPython直シバンをPOSIX shellランチャーにし、スクリプト位置からclone rootを求めて`.venv/bin/python -m kaname_shogi.usi_engine`を起動する。
   - `PYTHONPATH`へclone rootを追加して元の作業ディレクトリを保つ。`.venv/bin/python`がない場合は、セットアップ手順を示してUSI起動前に失敗させる。
   - この方式ならShogiHomeのGUIプロセスがHomebrewの`PATH`を継承するかに依存せず、移行済みの`.venv`と同じPythonを使える。ShogiHomeに登録する実行ファイルのパスは変わらない。
   - テスト用一時cloneに`.venv/bin/python`を用意し、別cwd起動・USI応答・異常終了コード・設定読込と、環境欠落時の案内を検査する。
5. `README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/shogihome-connection-guide.md`、`docs/knowledge/python-quality-checks.md`、今回の学習・計画記録と既存影響調査
   - Python 3.14以上、実測したPython版、`py314`、ShogiHome launcherが`.venv`を使うこと、セットアップ・復帰手順を現行情報として更新する。
   - 履歴に残る過去のPython 3.9記録は書き換えない。

`requirements-dev.txt`、`.githooks/pre-commit`、Ruff固定版は変更しない。アプリ本体の将棋・時計・USIロジックも変更しない。

## 実施手順

1. この計画の承認後、作成済みの`codex/python-315-migration`上で実装を開始する。着手直前に作業ツリー・HEAD・Homebrew formulaの版を記録する。
2. Homebrewの導入内容を確認し、`python@3.15`と下限検証用`python@3.14`を導入する。各versioned executableの実パスとバージョンを記録する。Homebrewの基底環境へ`pip install`しない。
3. 既存`.venv`を削除せず、重複しない退避名へ移動する。`$(brew --prefix python@3.15)/bin/python3.15 scripts/setup_dev.py`で環境を作り直し、`.venv`が3.15を指すことと`core.hooksPath=.githooks`を確認する。
4. TDDで3.14境界・3.13拒否を追加し、失敗理由を確認してからsetup条件とlauncherを実装する。Python変更時のRuff手順はAGENTS.mdに従う。
5. Ruffのimport整理、format、check、差分確認を行う。`py314`変更によるソース修正が必要な場合は、Python 3.14と3.15の双方で意味を確認し、必要箇所だけ変更する。
6. 3.14系と3.15系で対象テストを実行する。3.15の`.venv`から通常コミット前hookも確認する。ShogiHome GUIは起動・設定変更せず、登録予定のlauncherをプロセス境界から検証する。
7. Refactor要否を確認後、独立レビューを行う。Critical/Important指摘を解消して再検証・再レビューし、学習記録と索引を更新する。mainへは取り込まない。

## テスト計画

| 対象 | 検出したい誤り | 検証 |
| --- | --- | --- |
| setup下限の受理 | 3.14を誤拒否、条件の不等号誤り | ホストと仮想環境の3.14でsetup成功経路へ進み、Ruff固定導入とhook設定が行われることを確認 |
| setup下限の拒否 | 3.13以下で環境やhookを先に変更 | ホスト3.13と、ホスト3.14上の既存仮想環境3.13で停止し、pip・`core.hooksPath`変更がないことを確認 |
| launcher実行環境 | 旧`/usr/bin/python3`またはGUIのPATHへ依存 | `.venv/bin/python`経由でUSI応答を返し、3.14受理・3.13拒否、別cwdからの設定読込とcwd保持を検査 |
| launcher障害処理 | `.venv`欠落で曖昧なシェルエラー、USI応答を誤出力 | 設定された案内をstderrへ出し、非0終了・stdout空を確認 |
| Python下限と移行先 | 3.14または3.15での構文/API/挙動差 | 3.14系と3.15系で`python -m unittest discover -s tests -v`を個別実行し、Ruff 0.16.10で`format --check`と`check`を行う |
| commit前hook | 新`.venv`・Ruff・staged checkerの参照誤り | `core.hooksPath`確認後、通常のcommit前検査を実行。`--no-verify`は使わない |

ShogiHome実アプリからの起動・対局はこの検証に含めない。直接起動テストはlauncherのプロセス境界を確認するが、ShogiHomeアプリ環境での接続互換性を証明しない。

## 復帰方法

- 旧`.venv`を退避保存し、削除しない。新環境の失敗時は新`.venv`を別名に退避して旧`.venv`を戻し、`core.hooksPath=.githooks`とフック起動を確認する。
- コード・テスト・設定の変更は作業ブランチ上に留める。問題があれば修正を戻すかブランチを破棄し、mainへ統合しない。
- Homebrewで追加されたPythonと依存formulaは、他の用途があり得るため自動アンインストールしない。
- `/usr/bin/python3`、全体PATH、ShogiHomeの保存済みエンジン登録設定を変更しない。

## 計画時点の未決事項と対象外

- 作成時点で未決だったHomebrewのpatch版と実行ファイルの絶対パスは、実施結果に記録した。
- ShogiHome GUIからの接続・対局は別途依頼がない限り行わない。
- Linuxは既存方針どおり未実測。Windows、free-threaded Python、Ruff更新、main統合も対象外。
- 二手先読みと時計は「学習・実装テーマとしては完了。ShogiHome実機挙動と一般的な時間保証は未確認のまま」。

## 参照資料

- [Python移行の影響調査](2026-10-14-python-upgrade-impact.md)
- [AGENTS.mdの開発・テスト・レビュー手順](../../AGENTS.md)
- [ShogiHome接続手順書](../shogihome-connection-guide.md)
- [ShogiHomeのスクリプト・インタプリタ型エンジン実行要件](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%B7%E3%82%A7%E3%83%AB%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%97%E3%83%88%E3%82%84%E3%82%A4%E3%83%B3%E3%82%BF%E3%83%97%E3%83%AA%E3%82%BF%E5%9E%8B%E8%A8%80%E8%AA%9E%E3%81%A7%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E3%82%92%E5%AE%9F%E8%A1%8C%E3%81%97%E3%81%9F%E3%81%84%E6%96%B9%E3%81%B8)
- [Homebrew python@3.15](https://formulae.brew.sh/formula/python@3.15) and [python@3.14](https://formulae.brew.sh/formula/python@3.14)

## 移行実施結果（2026-10-14事後記録）

本人の「移行実施」という明示指示と、事前提示した本計画への承認に基づき、作業ブランチ `codex/python-315-migration` で実施した。実施時はmain統合を計画の対象外とし、後日、別の明示承認を得て統合した。取り込み結果は末尾に事後記録する。

### 環境

- Homebrewの通常版CPython 3.15.0を `/opt/homebrew/bin/python3.15`、下限検証用CPython 3.14.8を `/opt/homebrew/bin/python3.14` から使用した。Homebrew依存としてmpdecimal 4.0.1も導入された。
- 旧 `.venv` のPython 3.9.6環境は削除せず、`/private/tmp/kaname-shogi-venv-python39-20261014` に退避した。新しいclone内 `.venv` はCPython 3.15.0で作成し、Ruff 0.16.10と `core.hooksPath=.githooks` を確認した。
- CPython 3.14.8の全体テスト用仮想環境は `/private/tmp/kaname-shogi-venv-python314-test-20261014` に作成し、全件検証後に削除した。`/usr/bin/python3`、全体PATH、ShogiHomeの保存済み登録設定は変更していない。

### 実際の変更

- `scripts/setup_dev.py` のホスト・既存 `.venv` の最低版を3.14へ上げた。3.13以下では依存導入やGitフック設定へ進まない。
- Ruffの `target-version` を `py314` に変更した。Ruffの固定版、`requirements-dev.txt`、既存ルール、`keep-runtime-typing` の設定値は維持した。
- `py314`で出た注釈の更新（`Optional`/`Union`のPEP 604形式、不要な文字列前方参照、collections.abcからのCallable import）とPython 3.14のPEP 758複数例外構文を適用した。B905の4か所は、長さ一致が契約の3か所に `strict=True`、長さが異なる列を意図していた1か所に `strict=False` を指定した。
- `kaname-shogi-usi` をPOSIX shellランチャーにし、clone内 `.venv/bin/python` からモジュール起動するようにした。clone外からの起動でも設定を読み、呼び出し元のcwdを保つ。Python 3.14未満や `.venv` 不在ではUSI出力前に停止し、READMEの手順へ案内する。
- 受理・拒否境界、既存の古い仮想環境、launcherの3.14受理・3.13拒否、clone内Python選択、cwd保持のテストを追加した。

### 検証と限界

2026-10-14に次を実施した。

- `.venv/bin/ruff check --select I --fix .`、`.venv/bin/ruff format .`、`.venv/bin/ruff format --check .`、`.venv/bin/ruff check .` は成功し、最終状態は「38 files already formatted」「All checks passed!」。
- `.venv/bin/python -m unittest discover -s tests -v` はCPython 3.15.0で463件成功した。
- `/private/tmp/kaname-shogi-venv-python314-test-20261014/bin/python -m unittest discover -s tests -v` はCPython 3.14.8で463件成功した。
- cwd検査の初回はmacOSの `/var` と `/private/var` の別名を文字列比較して失敗した。同じパスを `Path.resolve()` で比較するテストに直し、該当単体テストと両版の全463件を再実行して成功した。ランチャーがcwdを変更した不具合ではない。
- 2026-10-14の独立レビュー最終結果はCritical 0・Important 0・Minor 0。初回レビューのREADME案内先とcwd検査に関する指摘を修正し、再レビューで解消を確認した。最終レビューは検査を再実行していない。テスト・Ruff・リンク確認の実行結果は上記のとおり。通常の `git commit` でcommit前hookを実行し、「38 files already formatted」「All checks passed!」を確認した。

Linux、Windows、free-threaded Python、ShogiHome GUIからの実起動・接続・対局は未検証。ローカルプロセス起動とUSI入出力のテストはShogiHome実アプリとの互換性保証ではない。

### 復帰と次の承認段階

新 `.venv` に問題があれば、まず新環境を別名へ退避し、`/private/tmp/kaname-shogi-venv-python39-20261014` をclone内の `.venv` へ戻す。HomebrewのPythonは他用途の可能性があるため自動削除しない。実施時はコード・設定の変更を作業ブランチに留め、統合前に復帰する計画だった。

その後、本人の明示承認を受けて2026-10-14にコミット `358f4ac` をmainへfast-forward統合し、取り込み先で全463テスト、Ruff lint、整形確認を再実行して成功した。統合後HEADは `358f4ac`。pushはしていない。最後の理解確認を一問提示し、回答と補足を学習記録へ追記するまで次テーマを開始しない。
