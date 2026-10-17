# 学習・開発の再開案内

## 現在地

2026-10-17更新。「次のエンジン強化段階を設計する」は、全幅読みとαβ枝刈りの開発用比較の実装・検証・独立レビュー・main統合・取り込み先検証・最後の理解確認まで完了した。本人回答「切り捨てた可能性があるため」と補足を[学習・実装記録](learning/engine-improvement-stage-design.md)に保存した。

- 利用方法と制約：[探索比較メモ](knowledge/search-comparison.md)、[README](../README.md)。
- 仕様と実装：[承認済み設計](plans/2026-10-17-engine-search-comparison-design.md)、[承認済み計画・結果参照](plans/2026-10-17-engine-search-comparison-implementation-plan.md)。
- 開始前の背景：[引き継ぎ](handover-engine-improvement-stage-design.md)。未開始という記述は準備当時の状態。

次は[次テーマ候補](next-topics.md)から本人の選択を待つ。推薦は「反復深化を学び次段階を設計する」。選択前に新しい学習・設計・実装を始めない。選択後は別希望がなければ新セッション用引き継ぎを作る。

Random（最弱・既定）、一手駒得、現行二手先読みを維持。新探索は開発用比較であり通常対局へ未接続。OSからのSIGINT配送、棋力・全局面の速度・履歴終局は未検証。

## Gitと検証の状態

作業場所は `/Users/oki2a24/kaname-shogi`、現在ブランチは `main`。文書作業開始HEADは `1af87d8`、実装統合先HEADは `ecc1c73`。統合記録は `9c702ae`。最後の回答と完了状態を文書へ追記する。リモートへは未push。作業ブランチは統合・検証後に通常削除済み。再開時に `git status --short --branch` と直近ログで現在の状態を照合する。

既存操作による局面の局所検算は学習記録を参照。新探索は実装済みで、全体490件成功と玉だけ局面の実測を学習記録へ保存。文書検証とレビューの最新状態も同記録へ記す。

入口更新前の固有情報は[再開案内の履歴](resume-history.md)に保全した。文書の置き場所は[文書更新ガイド](documentation-guide.md)、索引は[文書案内](README.md)。
