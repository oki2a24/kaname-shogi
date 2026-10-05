# 学習・開発の再開案内

## 現在地

第64回「承認済み難易度選択設計を実装する」を進行中。作業ブランチは `codex/weakest-mode-difficulty-selection-implementation`、作業開始時の基点と現在のHEADは `859742d`。コード・テスト・記録文書は作業ツリーにあり、まだコミットしていない。

共通方針選択、CLI選択、USI Difficulty comboを実装し、Refactor確認と独立コードレビューを終えた。レビューのImportant指摘を修正して再レビューを受け、Critical・Important・Minorはいずれも0件。関連focused testsは段階ごとに成功し、選択関連75件の回帰確認も成功した。レビュー修正後は駒得評価9件、USI設定・ケース・局固定4件を再実行して成功した。全体の `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` は305件すべて成功し、`git diff --check` と変更した9件のMarkdownローカルリンク確認も成功した。

### 現在の合意済み動作

- CLIとUSIの両方で利用でき、現行の一様ランダムを最弱として残す。未指定時の既定値も一様ランダム。
- CLIはコンピュータ参加形式の開始前に「最弱（一様ランダム）」または「駒得を考える」を選び、同じ局では固定する。
- USIは `Difficulty` comboの `Random` / `Material` を扱い、局の最初の `go` で方針を固定する。
- 駒得評価は谷川浩司さんの参考値を使い、合法手一手後の「指し手側の盤上・持ち駒合計 − 相手側の盤上・持ち駒合計」を比較する。玉将を除外し、取った成駒は基本駒の持ち駒値に戻す。探索はせず、同点はランダム。

第64回の[実装計画](plans/2026-10-05-weakest-mode-difficulty-selection-implementation-plan.md)、[学習記録](learning/64-weakest-mode-difficulty-selection-implementation.md)、[承認済み設計](plans/2026-10-05-weakest-mode-difficulty-selection-design.md)、[一手選択の知識](knowledge/31-weak-move-selection.md)、[USI応答の知識](knowledge/usi-engine-response.md)を参照する。

ShogiHomeの実機設定・対局・USIログ採取は行っていない。このテーマでの対象外として本人と合意済みであり、別途必要になった場合は対象と方法を合意して、別の承認を得る。

## 再開時に行うこと

まず実際の状態を確認し、この文書の記載と照合する。

```sh
git status --short --branch
git log -3 --oneline
```

その後、実装計画のチェックリストと実行記録、学習記録の最終検証結果、README・索引・方向性の状態を確認する。学習記録・知識メモを本人が確認するまで作業ブランチへコミットしない。`main` への取り込みには別途本人の明示承認が必要。取り込み先検証の後に最後の理解確認を一問だけ行い、回答を学習記録へ記録してから次テーマ候補を見直す。

## 次に読むファイル

1. [AGENTS.md](../AGENTS.md)、[README](../README.md)、[文書索引](README.md)、この案内、[次テーマ候補](next-topics.md)、[プロジェクト方向性](02-project-direction.md)
2. [第64回実装計画](plans/2026-10-05-weakest-mode-difficulty-selection-implementation-plan.md)、[第64回学習記録](learning/64-weakest-mode-difficulty-selection-implementation.md)、[承認済み設計](plans/2026-10-05-weakest-mode-difficulty-selection-design.md)
3. [一手選択の確定知識](knowledge/31-weak-move-selection.md)、[USI応答の確定知識](knowledge/usi-engine-response.md)、変更したコードとテスト

テーマ開始時点の背景・照合基点・再開用プロンプトは[第64回引き継ぎ](handover-weakest-mode-difficulty-selection-implementation.md)に残してある。これは現在のGit状態を示すものではない。
