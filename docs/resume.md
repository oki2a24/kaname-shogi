# 学習・開発の再開案内

## 現在地

2026-10-17更新。本人が新セッションに再開指示を入力し、「次のエンジン強化段階を設計する」の学習・設計を開始済み。現在は、全幅読みとαβ枝刈りの開発用比較を設計している。

- [学習記録](learning/engine-improvement-stage-design.md)：本人回答、合意、訂正、一次資料、局面の検算。2026-10-17に対話から事後整理。
- [設計書](plans/2026-10-17-engine-search-comparison-design.md)：合意条件、公開契約、確認局面。2026-10-17に全体承認済み。
- [開始時の引き継ぎ](handover-engine-improvement-stage-design.md)：開始前の背景として保存。未開始という記述は準備当時の状態。

合意範囲は二・三・四手の全幅／αβ比較、駒得と詰み優先、評価値と最善候補への所属の一致、訪問回数、同じ探索順、最初の同点最善手。SFEN入力、USI表記と日本語の併記、開発用比較まで。Random（最弱・既定）・一手駒得・現行二手先読みを維持し、新探索と必要な共通処理だけを分割する。

実装計画は本人承認済み。GPT-6.1 Solでネイティブ実行中。タスク1〜3（共有化・全幅探索・αβ枝刈り）は検証・独立レビュー完了。次はタスク4の将棋接続。詳細とRed/Greenは学習記録、ライブ台帳は `.superpowers/sdd/2026-10-17-engine-search-comparison-implementation-plan/progress.md`。main統合は未承認。

## Gitと検証の状態

作業場所は `/Users/oki2a24/kaname-shogi`、ブランチは `codex/engine-search-comparison-design`。文書作業開始HEADは `1af87d8`（開始時mainとorigin/main）。現在は文書の未コミット変更を作成中。mainへの統合は未実施。再開時に `git status --short --branch` と直近ログで照合する。

既存操作による局面の局所検算は学習記録を参照。新探索は未実装で、製品テスト成功の主張はない。文書検証とレビューの最新状態も同記録へ記す。

入口更新前の固有情報は[再開案内の履歴](resume-history.md)に保全した。文書の置き場所は[文書更新ガイド](documentation-guide.md)、索引は[文書案内](README.md)。
