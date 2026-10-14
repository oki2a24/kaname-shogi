# 三つの選択方式の構成調査（開始時点の引き継ぎ）

## 🎯 最終目標

現行の一様ランダム・一手後の駒得・二手先読みの一手選択について、責務、共通処理、依存関係、検査境界を理解し、現状維持と方式別ファイルへの分離を比較する。調査結果と推薦案を提示するところまでとし、コード・設定・テストを変更しない。

## ✅ 完了した事項と意思決定の背景

- [済] Python 3.15移行テーマは2026-10-14にmainへ統合され、取り込み先で検証された。
  - **Why:** 本人が承認したCPython 3.15移行を最低対応3.14で実施した。実装コミット `358f4ac` をfast-forwardで取り込み、3.14.8と3.15.0で全463テスト、Ruff lint・整形確認を行った。本人の最終理解確認への回答と補足も学習記録へ残した。
  - **Crucial:** 二手先読みと時計は「学習・実装テーマとしては完了。ShogiHome実機挙動と一般的な時間保証は未確認のまま」。この状態表現を維持する。
- [済] 本人は次テーマ候補1「三つの選択方式の構成調査だけ」を選び、新セッションの準備を依頼した。
  - **Why:** Python移行後に、以前からの保留候補である方式別構成の仮説を、現行コードに照らして小さく調べる。プロジェクトの目的は強さや速度より、各処理の理由を理解すること。
  - **Crucial:** 「エンジンごとに別ファイルにした方がよい」は本人の検討仮説で、決定済み仕様ではない。調査前に分離を正解とみなさない。
- [未着手] このテーマのコード・テスト構成の調査はまだ始めていない。新セッションへ人間が再開用プロンプトを入力してから着手する。

## 🚧 現在の物理的状態

- **作業ディレクトリ:** `/Users/oki2a24/kaname-shogi`
- **準備開始時のGit状態:** branch `main`、HEAD `1156be1f54dd35a271c361440e50cb73816bd812`、作業ツリーclean、`origin/main`より44コミット先行。引き継ぎ準備文書のコミットでHEADは進むので、再開時に実際の状態を確認すること。pushはしていない。
- **開発環境:** `.venv/bin/python` はCPython 3.15.0、Ruff 0.16.10、`core.hooksPath=.githooks`。
- **直近の検証:** Python移行の取り込み先で `.venv/bin/python -m unittest discover -s tests -q` が463件成功。`.venv/bin/ruff check .` と `.venv/bin/ruff format --check .` も成功。今回の構成調査ではテストを実行しない。
- **未確認:** 本テーマの責務・依存・共通処理・テスト境界は未調査。ShogiHome実機挙動と一般的な時間保証も未確認のまま。

## 調査範囲と対象外

1. 現行の三方式がどこで選ばれ、どこへ委譲され、どの局面・合法手・乱数・評価処理を共有しているかをコードと既存テストから追う。
2. 現在のファイル境界、責務、依存方向、共通処理、方式固有処理、テストが守る契約と未検証範囲を整理する。
3. 現状維持と方式別ファイルへの分離を、理解しやすさ、重複、依存、変更時の影響、検査のしやすさで比較し、根拠を添えて推薦案と未決事項を提示する。

コード・設定・テストの変更、テスト実行、リファクタリング、ファイル分割、選択方式の挙動変更、性能・棋力測定、実装計画の承認済み扱いは対象外。別の変更へ進まず、調査結果だけを提示する。

## 📝 次の具体的なアクション

1. 再開時に現在のGit状態、Ruff固定版、ローカルhook設定を確認する。
2. `AGENTS.md`、`README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/02-project-direction.md`、`docs/documentation-guide.md`、`docs/knowledge/test-coverage-review.md` を読み、選定範囲を照合する。
3. `docs/knowledge/31-weak-move-selection.md` と `docs/learning/evaluation-next-stage.md` を読み、現行仕様と二手先読み設計の背景を押さえる。
4. `rg -n "choose_move|choose_weak_move|material_balance|MoveSelectionPolicy|RANDOM|MATERIAL|TWO_PLY_MATERIAL" kaname_shogi tests` で関連コードとテストを特定し、必要なファイルだけ読む。テストは読むだけで実行しない。
5. 責務・依存・共通処理・検査境界を事実に基づいて整理し、現状維持案と分離案を比較して推薦理由、リスク、未決事項を提示する。
6. 調査後は学習記録と次テーマ候補・再開案内を、文書ガイドに沿って記録する。本人が調査結果を確認するまで、後続の設計承認や実装へ進まない。

## 📚 再開時に読む資料

- [作業方針](../AGENTS.md)
- [利用方法と開発環境](../README.md)
- [現在地](resume.md)
- [選定と候補](next-topics.md)
- [プロジェクトの方向性](02-project-direction.md)
- [文書更新ガイド](documentation-guide.md)
- [一手選択と駒得評価](knowledge/31-weak-move-selection.md)
- [評価・探索の次段階を設計した理由](learning/evaluation-next-stage.md)
- [テストの検出力と範囲の点検](knowledge/test-coverage-review.md)

## 💬 再開用プロンプト

```text
/Users/oki2a24/kaname-shogi の現行作業ツリーで、選定済みテーマ「三つの選択方式の構成調査だけ」を始めてください。まず git status --short --branch、git log -3 --oneline --decorate、.venv/bin/ruff --version、git config --local --get core.hooksPath を順に確認し、この引き継ぎと AGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/02-project-direction.md、docs/documentation-guide.md、docs/knowledge/test-coverage-review.md、docs/knowledge/31-weak-move-selection.md、docs/learning/evaluation-next-stage.md を読んで範囲を照合してください。

一様ランダム・一手後の駒得・二手先読みの現行コードと既存テストを読み、責務、共通処理、依存関係、検査境界を整理し、現状維持と方式別ファイルへの分離を比較してください。「エンジンごとに別ファイルにした方がよい」は未決の仮説として扱い、結論を先取りしないでください。成果は構成調査、比較、推薦案、根拠、リスク、未決事項だけです。コード・設定・テストの変更、テスト実行、リファクタリング、分割、実装計画の承認済み扱いはしないでください。結果を文書へ記録した後は本人の確認を待ってください。

二手先読みと時計の状態は「学習・実装テーマとしては完了。ShogiHome実機挙動と一般的な時間保証は未確認のまま」です。確認問題を出す場合は一問ずつ進めてください。
```
