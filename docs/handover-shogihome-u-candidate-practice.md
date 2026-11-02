# ShogiHomeでU候補を実践する

## 🎯 最終目標

ShogiHomeで、このリポジトリのエンジンに接続済みのU評価候補を使い、本人が指定・承認した範囲の実践を行う。観察した画面・棋譜・条件を記録し、少数局の結果から棋力向上を結論しない。完了後も主線の「次の非駒得評価項目を一つ選び、学び・設計する」は未完了として残す。

## ✅ 完了した事項と選定の背景

- 非駒得評価として、支えのない被攻撃駒の枚数差Uを含む `10 × M（駒得）+ U（支えのない被攻撃駒の枚数差）` を、通常CLIの候補とUSI `MaterialUndefendedPiece` に接続した。候補は既定方式へ置き換えず、選択可能な方式として残している。
- 5局面の比較では、指定した条件下で10M+U候補の改善が支持された。この結果は登録局面・比較条件に限られ、一般棋力向上を示さない。根拠と条件は [`docs/learning/undefended-piece-coordination-evaluation.md`](learning/undefended-piece-coordination-evaluation.md) と [`docs/knowledge/undefended-piece-evaluation.md`](knowledge/undefended-piece-evaluation.md) にある。
- 通常CLIではMaterialとU候補を先後入れ替えで2局操作確認済み。これは操作観察であり、勝敗を強さの証拠にしない。
- ShogiHomeでの実践は、以前は遠隔PCのロックを解除できないため保留されていた。本人は2026-11-03に「ShogiHomeでU候補を実践する」を次テーマとして選んだ。選定理由の追加説明はなく、動機は推測しない。
- ここでいうU候補は枚数差方式 `MaterialUndefendedPiece`（10M+U）。2026-11-02に比較した価値合計方式 `material-piece-threat-value-v1` は比較CLI専用で、通常CLI・USIの選択肢ではないため、ShogiHomeでの対象にしない。

## 🚧 現在の物理的状態

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`
- 作業ブランチ：`codex/shogihome-u-candidate-practice`
- 引き継ぎ準備の基点：`23cf552f4146fa580a0add638e1e9bb979355cc7`（`main` と `origin/main` が一致していた状態）
- このテーマの引き継ぎ文書・現在地・学習記録を同ブランチに作成し、コミットする。main統合とpushは別途承認を待つ。
- このセッションではShogiHomeの画面、PCアクセス、アプリ版、登録エンジンパス、設定、棋譜、稼働セッションを確認していない。過去の画面・版・絶対パスを現在値として扱わない。
- 既存の未追跡比較データ、`.agents/tasks/`、C2保護4件、`.antigravity/tasks/`、`.venv.backup-*`、`migration-preservation-2026-11-01/`、`worktree-preservation-2026-11-01/` は変更しない。別worktree・別cloneは作らない。
- main統合後の直近全体検証は2026-11-03の `python3 scripts/run_tests_parallel.py` で1066テスト・92モジュール・28.028秒成功。この引き継ぎは文書のみの変更で、製品テストを再実行する対象ではない。

## 📝 次の具体的な行動

1. 新セッションでGit状態と [`docs/resume.md`](resume.md) を確認し、この引き継ぎのブランチ・基点・現在地を現物に照合する。
2. 操作の前に [ShogiHome接続スキル](../.agents/skills/shogihome-connection/SKILL.md) と [ShogiHome接続手順書](shogihome-connection-guide.md) を読み、そこに従う。履歴文書は操作条件の根拠として流用しない。
3. CUAで現在のShogiHome画面と版を確認する。監視タブの最新一覧でUSI/CSAセッションを確認し、棋譜の未保存状態・現在の局面・手番・登録エンジンパス・Ponder・時計設定を画面で調べる。現在画面と手順書が異なる、稼働状態が読めない、未保存棋譜がある場合は推測操作せず停止して本人へ伝える。
4. 本人のテーマ選択はU候補の実践を始める意図として扱う。先後・局面・持ち時間/秒読み・対局数・ログ採取が特定できない項目は一問ずつ確認する。新規平手対局の既定手順は人間先手・エンジン後手だが、依頼内容と合わなければ開始前に確認する。時計は0+0を使わず、合意した正の時間を画面で確かめる。
5. 登録先、Ponder、ログなど永続設定の変更が必要なら、現在値と具体的な変更を示し、変更ごとに明示承認を得る。USIログは本人が依頼した場合のみ扱い、ShogiHomeのプロンプト欄へUSIコマンドを手入力しない。
6. 合意された一局だけを実施し、終局後は表示・棋譜・結果を確認する。追加局や設定復帰用対局を自動で始めない。観察結果と未確認範囲を学習記録に追記し、次の非駒得評価項目を選ぶ主線へ戻る。

## 💬 再開用プロンプト

> `/Users/oki2a24/kaname-shogi` の `codex/shogihome-u-candidate-practice` で、本人が選んだ「ShogiHomeでU候補を実践する」を再開してください。最初に `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`、`git rev-parse main`、`git rev-parse HEAD`、`git worktree list` を順に確認し、`AGENTS.md`、`docs/resume.md`、本引き継ぎ、`docs/learning/undefended-piece-coordination-evaluation.md`、現行のU評価知識とREADMEを現物に照合してください。操作前に `.agents/skills/shogihome-connection/SKILL.md` と `docs/shogihome-connection-guide.md` を読み、その現在画面・停止条件に従ってください。対象は通常CLI/USIに接続済みの枚数差方式 `MaterialUndefendedPiece`（10M+U）です。比較専用の `material-piece-threat-value-v1` はShogiHomeで選べる方式として扱わないでください。PCアクセス・ShogiHomeの版・現在の登録先・Ponder・棋譜・稼働セッション・時計を過去記録から推定せず、現在の画面で確認してください。先後・開始局面・時計・対局数・ログ要否で未確定のものは一問ずつ確認し、設定変更やログ採取には具体案と別途明示承認を得てください。合意した一局だけを実施し、少数局から棋力を判定しないでください。`.agents/tasks/`、未追跡比較データ、C2保護4件、退避アーカイブを変更せず、別worktree・別cloneは使わないでください。実施後は観察と限界を学習記録へ残し、主線の次評価項目を未完了として保持してください。
