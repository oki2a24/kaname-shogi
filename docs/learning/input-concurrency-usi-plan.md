# 入力並行処理・USI接続の計画作成

2026-10-12開始。本人が選定した計画作成・レビュー・提示だけのテーマ。コード・テスト・設定変更、TDD、実装、計測・対局は対象外。[計画案](../plans/2026-10-12-input-concurrency-usi-implementation-plan.md)、[開始時引き継ぎ](../handover-input-concurrency-usi-plan.md)。

## 目的・要点

完成した探索部品と承認済み全体設計を照合し、入力と探索の接続・停止と抑制・送信順序・故障回収を実装単位と検証へ具体化する。新しい全体設計を作り直さない。時間原点、送信完了、担当終了の三つを分ける。

開始時に指定4コマンドを実行。ブランチcodex/input-concurrency-plan-handoff、HEAD06e288a、差分なし。Ruff0.16.10は固定版一致、hooksPath=.githooks。元ディレクトリで作業、別worktreeなし、main未取り込み。前テーマ425件成功を今回の結果として流用しない。

using-superpowers / writing-plansを確認・使用。brainstormingは適用範囲を確認し、承認済み全体設計からの計画具体化なので設計の再選択へ戻らない。個人観察とtest-coverage-reviewの契約・代表誤り・独立期待値・補完・未検証の点検を計画へ適用。TDDは計画内の将来手順だけ。

## 確認問題1：次goの原点

質問：次のgo行を読み取った後、前の探索担当の回収に時間がかかった場合、その待ち時間を次の探索予算に含めるには、時間原点をどこに置く必要がありますか？

本人回答：「次のgo」

アシスタント補足：次のgo行を入力担当が読み取った時点。その時刻を主担当へ渡せば、受渡し・前担当回収・解析・複製・探索起動も次の予算へ含まれる。本人の短い回答と、この具体化を区別する。

## 判断理由と振り返り

入力待機解除はmacOS対象のselector＋非blocking os.read＋内部通知pipeへ具体化。通常のreadlineを別スレッドへ移すだけでは、部分行や無言GUIで故障後の回収ができない。入力源の所有資源と標準入力の借用を分ける。

完成行の読取り時刻と、主担当が共通Lock内で行う入力確定を分ける。送信完了後でも探索担当の後片付けが残り得るため、次命令の正常受付と前担当joinを分ける。公開runの注入入力に待機解除の新前提が必要なことは、互換性の限界として計画承認対象へ明記。

次への問い：送信前の抑制と送信後の回収待ちを、どの同期点で検査すると競合順序を再現できるか。追加の確認問題はまだ出しておらず、回答済みとは扱わない。

## 検証・レビュー・承認段階

requesting-code-reviewに従い、セッション履歴なしの読み取り専用レビュアーへ成果物・基準・現在コード・禁止範囲を渡した。初回Critical 0・Important 1・Minor 0。Importantは相互待ち/内部通知無視の変異が非daemon担当を残し、有限join FAIL後も検査プロセスの終了を妨げる点。receiving-code-reviewでthreadingの終了契約と照合し、停止不能になり得る関数・実pipeケースを含め、親監視付き子プロセスとterminate→kill→waitで検査自体を回収する方針を計画へ追記。ファイル隔離だけではプロセス隔離にならない。反復cancelのpipe待ち回避と回収時の追加例外処理も明示した。再レビュー結果と文書点検は実施後に追記する。

今回は文書のみなので全体テストは実行せず、計画中のコマンドは未実施。コード・テスト・設定変更、TDD、実装、計測・対局・コミット・main統合・pushなし。具体計画承認と実装開始指示を待つ。

再レビューはCritical 0・Important 0・Minor 0、本人への提示可能。初回Importantの解消と、反復cancel・資源解放・回収例外処理の整合を確認した。独立レビュアーは読み取りのみでテストは実行していない。主担当は仕様要件と4タスク・API整合・未実施の区別を自己点検し、verification-before-completionに従い文書検証を実行。対象5文書の相対リンク466件・見出し11件欠落0、末尾空白/改行不備0、git diff --check成功。Git状態は入口3文書変更と新規計画・学習2文書だけ、HEAD06e288aを維持。最終の実績追記後も同じ確認を行う。

計画を本人へ提示し明示承認待ち。計画承認と実装開始指示、main取り込み承認を区別する。公開runへのcancel_input_fn追加と取消可能入力の前提、macOS向け入力方式、テストのプロセス隔離を含めて確認対象とする。

## 一次資料の再確認

[USI仕様](https://hgm.nubati.net/usi.html)の探索中入力・idle stop無視・改行応答を再確認。[Python 3.9 os](https://docs.python.org/3.9/library/os.html)のread/pipe/set_blocking、[codecs](https://docs.python.org/3.9/library/codecs.html)のincremental decoder、[io](https://docs.python.org/3.9/library/io.html#io.IncrementalNewlineDecoder)の改行復号、[threading](https://docs.python.org/3.9/library/threading.html#threading.Thread.join)の回収契約を参照。selectorsの英語公式ページ取得が失敗したため、[公式日本語ページ](https://docs.python.org/ja/3.9/library/selectors.html)で同時待機・OSによる対応対象差・closeを確認。API選択は本プロジェクトの計画案で、OS動作実証ではない。

## 計画承認の受領

2026-10-12、本人回答「承認する」。提示済み計画全体への明示承認として記録する。実装開始指示・main取り込み承認には広げない。現在は実装開始指示待ち。上記の承認待ちは提示時点の履歴。計画本文のAPI・タスク・検証範囲は変更せず、承認段階だけを文書5件へ反映した。コード・テスト・設定変更、TDD、実装、計測・対局・コミット・main統合・pushは行っていない。承認記録のみのため単体テストと独立レビューは再実行せず、差分・リンク先の存在・空白を確認する。

## 実装開始（2026-10-12）

本人「実装開始して下さい。適切なスキルを使用して下さい」により承認済み4タスクを開始。executing-plans / test-driven-development / using-git-worktreesを確認し、承認済み計画の現在ブランチ・元ディレクトリを再利用。main統合は別承認。開始HEAD06e288a、承認済み計画等の文書5件の未コミット差分を保持し、コード着手前に保存する。Ruff0.16.10・hooksPath=.githooks一致。開始全体テスト425件成功。個人観察と検出力点検を継続適用する。
