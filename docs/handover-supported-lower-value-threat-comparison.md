# V比較接続・二段階比較の開始時引き継ぎ

作成日：2026-10-31

## 目的と選定の背景

主線は非駒得評価を一項目ずつ学び、実装し、比較して確かめること。本人は2026-10-31に「Vの比較を先に設計する」を選び、V典型局面での予備比較と、独立した幅広い局面での確認比較を行う二段階方式を選択した。設計案と実装計画全体は本人が明示承認済み。予備・確認の両比較を `--workers 4` で実施するよう本人から指示がある。

2026-10-31に主線候補「次の評価項目を選び、学習・設計する」を最初に選んだ理由は本人から聞いていないため推測しない。「駒の働き・活性度」は以前に提示した例で、本人が選んだ評価項目ではない。

## 承認済みの比較仕様

- 対照は `10M+U`、候補は `10M+U+V`。同じ `evaluate_material_piece_threat` と既存一手選択器を使い、差は `supported_threat=0` 対 `supported_threat=1` のみ。
- 接続対象は比較CLIだけ。通常CLI・USI、通常CLIのSFEN入出力、飛車可動性v2、玉安全度との合成、Uの二手・四手適用は追加しない。
- 予備は専用のV典型5局面、各10組、合計50組・100局を提案条件とし、上限は一局1024手。確認判定には加算しない。
- 確認は予備と異なる幅広い6局面、各340組、合計2040組・4080局を提案条件とする。予備の状況を確認後、開始前に一局1024手の上限を最終固定する。
- 予備と確認で別の合法局面セット・seed一覧・出力先を用意し、対局結果を見る前に局面内容、独立したM/U/V期待値、seed、conditions、出力先を固定する。既存の局面セットを自動流用しない。予備局面と確認局面は重複させない。
- workerは両方とも `--workers 4`。実行時のCLI `--help` で4が使えることを確認し、使えなければ小さいworker数へ縮退せず停止して報告する。長時間実行中は約一時間ごとに実測完了局数・組数・残数・故障・保存summaryを確認する。
- 確認比較の主判定は承認済み設計の95%区間、50%境界、55%効果目標、80%検出力案に従う。未決着は勝敗へ読み替えず、結果を固定局面群・選択方式・手数上限・実行条件の範囲に限定する。一般棋力向上の証明とはしない。
- 実装後のコード検証と条件固定を終えてから比較を行う。条件を実質変更する必要が出た場合は止めて本人の承認を待つ。

## 完了済みと未着手

V評価本体・固定期待値・既存一手選択での確認はmainに存在し、直前のV実装・理解確認は[学習記録](learning/supported-piece-lower-value-threat.md)と[確定知識](knowledge/supported-piece-lower-value-threat.md)を参照する。今回承認された比較設計と実装計画は次の文書にある。

- [承認済み比較設計](plans/2026-10-31-supported-lower-value-threat-comparison-design.md)
- [承認済み実装計画](plans/2026-10-31-supported-lower-value-threat-comparison-implementation-plan.md)

この引き継ぎ作成時点では、比較CLIのV0/V1接続、TDD、コード・テスト変更、局面・seed一覧の作成、比較実行、統計分析は未着手。実装計画のTask 1〜4を新セッションで進める。設計・実装計画は承認済みなので、再承認を求めず計画どおりに着手してよい。長時間比較についても、worker 4の指定は本人から受領済みであり、上記の実装・検証・条件固定を満たした後は計画どおり実施する。

## Git・物理状態

- 作業場所：`/Users/oki2a24/.codex/worktrees/undefended-piece-integration/kaname-shogi`
- 作業ブランチ：`codex/supported-lower-value-threat-comparison`
- ブランチ作成時の `main` / `HEAD`：`5a8395a270bc8c9b308e801b7bc65fa2f9dca072`
- この引き継ぎ文書、再開案内、次テーマ索引、文書索引、設計と計画の承認記録を同branchにコミットする。コミット後の実測状態は新セッションで改めて確認する。
- このhandoffコミットをmainへ統合・pushしない。将来の実装のmain統合・pushもこの引き継ぎでは承認されていない。
- 元の `/Users/oki2a24/kaname-shogi` は既存の文書変更・未追跡物があるため、切替・編集・上書き・clean/reset・削除をしない。
- `.agents/tasks/` と `data/comparison/runs/` にある未追跡物、特にC2保護対象4件を保持する。既存ファイルを読み替えたり、移動・上書き・削除したりしない。比較用の新規出力先は既存物と衝突しない一意なパスにする。
- ShogiHomeでのU候補実対局は遠隔PCへアクセスできず保留中。本人からPCアクセス可能との連絡が来た後に、別途実践を再提案する。

## 新セッションでの開始手順

1. 下記5コマンドをこの順で実行し、ブランチ・履歴・開始点を現物確認する。

   ```sh
   git status --short --branch
   git log -3 --oneline --decorate
   git branch --show-current
   git rev-parse main
   git rev-parse HEAD
   ```

2. `AGENTS.md`、`docs/resume.md`、本引き継ぎを現物と照合する。
3. 承認済み比較設計・実装計画、`docs/knowledge/search-comparison.md`、V評価コード、比較CLIとartifact readerの関係箇所を読む。実装計画には対象ファイル、TaskごとのTDD、確認契約が書かれている。
4. TDDへ入る前に `~/.codex/observations/test-driven-development.md` と `docs/knowledge/test-coverage-review.md` を読み、対象契約・検出したい誤り・代表例・単独/全体の検出範囲・未検証事項を当てはめる。開発環境もAGENTS.mdに従って確認する。
5. topic branch上で、承認済み計画のTask 1〜4をTDDで実装・検証する。各TaskのRefactor要否確認後に独立レビューを行う。Python変更時のRuff・差分検査・関連/全体テストはAGENTS.mdと実装計画に従う。
6. 実験局面、独立期待値、seed一覧、conditions、出力先を確定してから、まず予備を `--workers 4` で実施・分析する。予備条件から確認条件を変える場合は、承認済み案の範囲内で開始前に固定する。提案値から実質変更する場合は本人の承認を待つ。
7. 予備結果を確認して確認比較の条件を凍結し、別の局面・seed・出力先で確認比較を `--workers 4` で実施・分析する。結果を見て局面や組数を追加・差し替えない。
8. 実装成果・実測・統計・限界を記録し、最終独立レビューを行う。main統合・pushは別途本人の明示承認を得る。

## 新セッション用の再開プロンプト

以下を新セッションの最初のメッセージとして入力する。

> `/Users/oki2a24/.codex/worktrees/undefended-piece-integration/kaname-shogi` のtopic branch `codex/supported-lower-value-threat-comparison` で、V比較CLI接続・二段階比較を始めます。まず `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`、`git rev-parse main`、`git rev-parse HEAD` をこの順に実行してください。続けて `AGENTS.md`、`docs/resume.md`、`docs/handover-supported-lower-value-threat-comparison.md`、承認済みのV比較設計・実装計画を現物と照合してください。設計・実装計画は承認済みです。新たな設計承認を取り直さず、計画に従って `~/.codex/observations/test-driven-development.md` と `docs/knowledge/test-coverage-review.md` の点検後にTDD・実装へ進んでください。実装は比較CLIだけに限定してください。通常CLI・USI、通常CLIのSFEN入出力、飛車可動性v2、玉安全度との合成、Uの二手・四手適用は追加しないでください。実装・検証後、予備と確認の両方を `--workers 4` で比較してください。実行時の `--help` でworker 4が使えるか確認し、使えなければ縮退せず停止してください。予備は専用5局面・50組/100局、確認は別の幅広い6局面・2040組/4080局で、局面列・独立M/U/V期待値・seed一覧・conditions・出力先を結果を見る前に固定してください。予備を確認判定へ加算せず、約一時間ごとに実測進捗を確認してください。保護対象の `.agents/tasks/`、`data/comparison/runs/` とC2保護4件、元の `/Users/oki2a24/kaname-shogi` は変更しないでください。main統合・pushは別途承認なしに行わないでください。`
