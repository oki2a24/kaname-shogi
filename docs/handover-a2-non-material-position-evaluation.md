# 引き継ぎ：主線A2「次の駒得以外の評価項目を一つ選ぶ」

作成日：2026-10-27

## 🎯 最終目標

主線「駒得以外の局面評価を一項目ずつ育てる」に戻り、A2として次に学ぶ評価項目を一つ選ぶ。項目はまだ決めていない。まず一次資料と現在の実装を照合し、本人が候補を比較して選んだ後、その項目の改善仮説・独立期待値を持つ小局面・評価の視点と尺度・既存評価との関係・範囲・確認方法・検出力・未検証事項を具体化する。

今回の選定は学習テーマA2を選んだという意味であり、評価項目・仕様・実装計画・TDD・コード変更・テスト変更を承認した意味ではない。

## ✅ 完了事項と選定の背景

- A1/B1では飛車可動性を学び、最小実装をローカルmainに統合した。C1では `material` と `material-rook-mobility` を比較し、初回確認比較・独立追試を別々に2,040組ずつ分析した。両95%得点区間が50%を含み、本人は改善・悪化を確認できない「判断不能」の結論でC1を一旦区切ると決めた。比較は合算せず、現時点で追加比較は予定していない。詳細は[飛車可動性評価の学習記録](learning/c1-rook-mobility-evaluation.md)を参照する。
- C1の補助として着手した比較CLI局単位再開、分析CLI短時間化、比較CLI局内高速化、分析CLI局単位再開はローカルmainへ統合済み（`9e959b2`、`ca94847`、`441345e`）。統合先検証は[再開案内](resume.md)と[各学習記録](README.md)にある。これらは実行・分析を支える補助機能であり、C1の棋力判定を変えない。
- C1再開機能のmain統合が棋力判定を変えるかという理解確認で、本人は「言えない」と回答した。分析再開は完了済み棋譜の検証再利用と中断耐性を扱うため、候補方式の指し手や対局成績は変えない。この回答と補足は[分析CLI再開の学習記録](learning/c1-analysis-resume.md)にある。
- 本人は着手済みの脇道が完了していることを確認し、「本筋に戻りましょう」と選んだ。ロードマップの次の主線はA2である。通常CLIのSFEN入出力と飛車可動性バージョン2は将来候補として保留されており、今回の完了を妨げる作業ではない。
- A2の候補プールにある玉の安全度・駒の働き・可動性・利き・連携・配置などは例であり、採用順や実装予定ではない。前に玉の安全度を先に示した順序はアシスタントの案で、本人はまだどの項目も選んでいない。

評価項目を選ぶ理由は、駒得と重複しない独立した改善仮説を確かめ、根拠を得た変更だけを採用するためである。一局面で期待値を手計算できるテストは定義や符号の誤りを検出するが、棋力向上の証明にはならない。実装後の対局比較はC段階で改めて設計し、C1の統計設計や結果を新しい項目へ自動転用しない。

## 🚧 物理的状態と検証の起点

- A2引き継ぎ準備開始時の統合作業場所は `/Users/oki2a24/.codex/worktrees/c1-analysis-speedup/kaname-shogi`、ブランチは `main`、HEADは `ecb18b7`、worktreeはcleanで `origin/main` より17コミット先行していた。A2開始時に古いスナップショットを現在状態と決めつけず、Git状態を再確認する。
- 統合されたC1機能・補助機能はローカルmainにあるが、pushしていない。C1実装コミット `42fc9e9` はmainの祖先である。
- 元の `/Users/oki2a24/kaname-shogi` は確認時点で `codex/c1-analysis-performance-investigation`、HEAD `14e7210`。未コミットの文書変更と比較データ、未追跡の仮想環境バックアップ等を保持している。このcheckoutをclean/reset/branch切替せず、A2のmain作業場所と混同しない。
- mainでの分析CLI再開統合後の最後の全体検証は898テスト・58モジュール成功（22.530秒）。関連65テスト、Ruff、`git diff --check` も成功した。詳細は[分析CLI再開記録](learning/c1-analysis-resume.md)にある。この引き継ぎは文書だけの変更であり、A2開始時に再検証が必要かは変更範囲とGit状態を見て判断する。
- 現行の駒得評価と方針は `kaname_shogi/evaluation.py`、`kaname_shogi/one_ply_selection.py`、`kaname_shogi/material_rook_mobility.py`、`kaname_shogi/rook_mobility.py` および対応テスト・知識メモを入口に確認する。ファイル・契約は現行コードで照合する。

## 📝 次の具体的な行動

1. 新セッションで作業場所 `/Users/oki2a24/.codex/worktrees/c1-analysis-speedup/kaname-shogi` を明示し、`git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current` を実行する。
2. `AGENTS.md`、`docs/resume.md`、本書を現物と照合し、`docs/README.md` の索引からA2に必要な資料を選ぶ。
3. `docs/next-topics.md`、`README.md`、`docs/02-project-direction.md`、`docs/roadmap-non-material-position-evaluation.md` を読み、主線の位置とA2の範囲を確認する。
4. `docs/knowledge/31-weak-move-selection.md`、`docs/knowledge/rook-mobility-evaluation.md`、`docs/plans/2026-10-10-evaluation-next-stage-design.md`、`docs/learning/evaluation-next-stage.md`、`docs/learning/rook-mobility-design.md`、`docs/learning/c1-rook-mobility-evaluation.md` を必要箇所から読む。`README.md` と現行コード、対応テストも確認し、一次資料を候補の問いに合わせて調査する。
5. 候補と根拠を一項目ずつ示し、質問は一問ずつ出して回答を待つ。候補を決め打ちせず、既存評価との重複や尺度の違いも説明する。
6. 本人が選んだ項目について、独立期待値を持つ小局面、改善仮説、視点・符号・尺度・重み、対象範囲、既存評価との関係、局面テストの検出対象と検出力、C段階の比較方法、未検証事項を明確にする。手計算による期待値と実装の出力を独立させる。
7. 実装計画を作る場合は内容を提示して明示承認を待つ。承認前にTDD、コード・テスト変更、実装を開始しない。A2の項目選定を実装や棋力向上の承認へ読み替えない。

通常CLIのSFEN入出力と飛車可動性バージョン2をA2へ自動追加しない。長時間の比較・分析CLIは本人が端末から実行する。

## 💬 再開用プロンプト

> `/Users/oki2a24/.codex/worktrees/c1-analysis-speedup/kaname-shogi` で主線A2「次の駒得以外の評価項目を一つ選ぶ」を始めます。最初に `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current` を実行し、`AGENTS.md`、`docs/resume.md`、この引き継ぎと現在状態を照合してください。A1/B1とC1の記録を起点にしつつ、過去の状態を現在と同一視しないでください。主線の次はA2です。C1の比較は「判断不能」で一旦区切られ、着手済みの補助作業はローカルmainへ統合済みですが、`origin/main`へpushされていません。元の `/Users/oki2a24/kaname-shogi` は未コミット文書・比較データを保持しているため、clean/reset/切替をしないでください。次に `docs/README.md` から資料を選び、`docs/next-topics.md`、`README.md`、`docs/02-project-direction.md`、`docs/roadmap-non-material-position-evaluation.md`、既存の評価知識・学習記録、現行コード・対応テストを確認してください。一次資料に基づいて評価項目の候補と違いを一つずつ説明し、質問は一問ずつ出して回答を待ってください。評価項目はまだ選ばれていません。本人が選んだ要素について独立期待値を持つ小局面を設計し、改善仮説、視点・符号・尺度・重み、既存評価との関係、対象範囲、確認方法、検出力、未検証事項を明確にしてください。実装計画を作った場合は提示して明示承認を待ち、承認前にTDD・コード・テスト変更・実装を始めないでください。通常CLIのSFEN入出力と飛車可動性バージョン2は自動追加しないでください。長時間の比較・分析CLIは私が端末で実行する前提です。すべて日本語で進めてください。
