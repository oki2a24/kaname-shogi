# 作業場所と知識メモの整理（事後記録）

2026-11-01、本人は主線の作業場所を `/Users/oki2a24/kaname-shogi` に一本化し、知識メモの古い記述を直すよう依頼した。次の評価項目は未選定。

元ディレクトリは旧C1 branchにあり、変更文書3件と未追跡文書3件が現在の主線と衝突した。6件は内容を照合して `migration-preservation-2026-11-01/original-documents.tar` に退避し、追跡文書の差分patchも保存した。旧branchは保持した。本人は保護指定の例外として、主線が追跡するC2成果物23件の展開を許可した。既存の比較結果は削除・上書きしない。

飛車可動性、玉安全度、Uの知識メモについて、比較CLI・通常CLI・USIへの接続と、C1/C2比較の範囲を現行コードと学習記録に合わせた。製品コードとテストには変更を加えていない。

独立文書レビューはCritical 0、Important 1、Minor 1。Importantは再開案内の未完了表現がコミット後に古くなる点、Minorは旧cloneのoriginを現在の設定と誤読し得る点で、いずれも修正した。再レビューはCritical 0、Important 0、Minor 1。Minorの記録への入口不足は再開案内と文書索引にリンクを追加して対応した。コミットフック実行時に旧 `.venv` が削除済みPython 3.15.1を参照して停止したため、旧環境を `.venv.backup-2026-11-01-broken-python-3151` に保全し、READMEに従って `python3 scripts/setup_dev.py` でPython 3.15.2の環境を再構築した。Ruff整形確認142ファイル・lint・全体1039テスト/84モジュール（24.619秒）が成功した。文書差分の相対リンクは731件で欠落0、`git diff --check` は成功した。

## 再発防止

今回、旧知識メモの未更新と一時cloneの継続使用が本人の指摘で判明した。固定版Ruffだけでは古いPython参照を検出できず、コミットフックで発覚した。以後の具体的な確認手順は[文書更新ガイド](../documentation-guide.md#作業場所と知識メモの継続点検)へ追加し、このセッションでも作業先・既存差分・退避物・Python本体・各知識メモを照合した。これらの手順は将来のセッションでも再開時と関係文書更新時に適用する。

旧cloneの全Git参照は `migration-preservation-2026-11-01/clone-all-refs.bundle` に、無視対象の `.superpowers` と `.venv` は `clone-ignored-artifacts.tar` に退避した。bundleの検証と、tar内の通常ファイル1770件の内容照合を行った。旧cloneの知識メモ3件の差分は、元ディレクトリのコミットとSHA-256が一致した。旧cloneの保護指定に関係する成果物の扱いは、整理時に改めて現物と本人の指定を確認する。

再発防止策の独立レビューはCritical 0、Important 1、Minor 0。再開時の必読入口から手順に到達できない指摘に対応し、再開案内に適用指示とガイドへのリンクを追加し、再レビューはCritical 0、Important 0、Minor 0だった。
