# USI時計受付・設定接続の実装計画だけ：新セッションへの引き継ぎ

2026-10-12作成。準備時点の情報であり、次セッションで現物と照合する。

## 最終目標と選定範囲

本人：「USI時計受付・設定接続の実装計画だけ。新セッションの準備して」。次回は承認済み全体設計に沿って、USI時計引数の検証、自分側時計の選択、起動時設定読込・保持、既存予算計算との接続を具体的な実装手順・API・検証範囲へ落とす。小さく入力側を理解し、並行入力・探索中断と分けるため推薦した候補を本人が選定した。

今回は引き継ぎ準備のみ。次テーマの調査・学習・計画作成は未開始。人間が末尾の再開プロンプトを新セッションへ入力してから開始する。選定は将来の計画案承認・実装開始承認ではない。計画作成・レビュー・提示までとし、提示後に本人の明示承認を待つ。main取り込みも別承認。

入力並行処理、停止要求の伝達、探索中断、候補評価/手選択変更、故障時回収、実時間計測、ShogiHome操作・対局、最適化・棋力比較、Python更新を開始しない。コード・テスト・設定ファイルを変更せず、TDDを始めない。時計受付だけで探索が止まると説明しない。章番号・学習回番号は付けない。

## 完了事項と判断背景

前テーマの設定読込・予算計算は、計画明示承認、本人の実装開始指示、TDD、検出力確認、独立レビュー、main統合、取り込み先検証、最後の理解確認まで完了。

- [承認済み前半計画](plans/2026-10-12-time-budget-implementation-plan.md)、[全体設計](plans/2026-10-11-clock-input-time-management-design.md)、[確認範囲](plans/2026-10-12-clock-input-verification-review.md)。前半は後半の型/スレッド/USI解析へ依存せず単独実装可能と確認した。後半から前半を利用する一方向の依存。
- [実装・意思決定記録](learning/time-budget-implementation-plan.md)：設定読込f54e3eb、計算・記録3d01687、統合記録5569239、最後の回答・次候補ee3cac0。mainへ統合済み、pushなし。
- 最後の本人回答：「ならない。後半の実装でそこら辺の繋ぎこみが実装されるはず」。正しい。今回の部品ができてもUSI対局で探索停止は働かない。時計解析・選択・期限/停止伝達の一覧はアシスタント補足として分離記録した。
- 数値の精度はDecimalでJSON十進表記を保持してFractionへ変換、整数乗除算でfloorを表現。floatの丸め・巨大有限値の無限大化を避ける。数値の最適性を検証したわけではない。
- 以前の約28.4秒は本人が一例を許容しただけ。他局面・秒読み後の安全性は未保証。40手上限が長考原因という仮説も未検証。
- 前半実装では現在checkoutの作業ブランチを再利用。executing-plans補助task-startは日本語見出しを解析せずexit 3のため、briefと台帳を手動作成して補完。仕様変更はなし。補助ワークスペースは記録保存後に削除済み。次回もスキル指示と現行文書の適用範囲を確認する。

## 既存の部品と後続へ引き継ぐ契約

[時間予算参照メモ](knowledge/time-budget.md)、[実装](../kaname_shogi/time_management.py)、[テスト](../tests/test_time_management.py)、[設定](../config/time-management.json)。

- TimeManagementConfig＝時間設定データ。四欄はallocation_turns:int、maximum_multiplier:Fraction、byoyomi_target_ratio:Fraction、response_margin_ms:int。不変、直接構築も型/範囲検査、代替既定値なし。
- SearchBudget＝時間予算データ。target_ms:int、maximum_ms:int、不変、0≤目標≤上限。
- load_time_management_config(path: Optional[Path]=None)＝読込操作。省略はモジュール位置からリポジトリ直下config/time-management.json。明示相対Pathはcwd基準。キャッシュなし。ValueError（構文/型/範囲/文字コード）、OSError（読込不能）に対象パスと理由を含める。出力はしない。
- calculate_search_budget(remaining_ms:int, byoyomi_ms:int, config:TimeManagementConfig)＝計算操作。自分側の非負整数ms、bool拒否。時刻取得・先後選択・状態変更なし。予算は期間であり絶対期限ではない。
- 設定はJSON/Git管理。四項目必須、欠落/重複/未知/boolを拒否。N整数1以上=20、M有限1超=2、q有限0超1未満=0.75、S整数0以上=2000。採用済み未検証暫定値。JSONCは保留。許容範囲と式を無断変更しない。
- R>0: 基本目標=R//N、境界=max(0,R+B−S)、上限=min(floor(基本目標×M),境界)、目標=min(基本目標,上限)。R=0: 上限=max(0,B−S)、目標=floor(上限×q)。分母固定。全時間ms。

全体設計のUSI入力条件を変更しない：時計ありではbtime/wtime両方必須、byoyomi省略0。時計は非負整数ms、項目重複/非整数/欠落/負は拒否。binc/wincは0だけ受付、正は未対応、負・非数値は不正。加算0だけは時計なし、byoyomiだけは残り時間不足。時計なし通常goは時間停止なし。未知goトークンは無視し既知項目を検査。movetimeとinfinite/ponder/mate/depth/nodes/searchmovesは未対応エラー。理由はstderr、非0終了、不明時計を無制限に読み替えない。

起動時一回設定を読み、実行中固定、欠落/不正/読込不能ならstderr診断と非0終了。この接続は前半では未実装。run_usi_engineは現在同期で時計未利用、mainは入出力接続とValueError診断を担当。次回は「設定の所有者と注入境界」「時計なしと予算0の区別」「先後と局面の関係」「既存通常応答を壊さずどこまで接続するか」を計画内で具体化する。これらは今回新たに方式採用した内容ではない。探索制御未実装で予算を使わない段階の扱いを明示し、停止したと誤認させない。

全体ではgo読取時刻を単調時計の原点にし、主担当への受渡し・回収待ち等も計時。主担当は現在スレッド、入力/探索は別スレッド。予備手、完了評価、抑制付き停止、故障通知、入力待機解除・回収は承認済み設計を参照するが、今回の計画へ実装範囲を拡張しない。

## 物理状態と検証の限界

- 場所 /Users/oki2a24/kaname-shogi。準備開始main、HEAD ee3cac0、差分なし、origin/mainより53コミット先。pushなし。
- 準備ブランチcodex/usi-clock-plan-handoffをee3cac0から作成。元の場所で切替、別worktreeなし。準備文書はmain未統合。保存コミットは次回Gitログで確認。
- Ruff 0.16.10固定版一致、core.hooksPath=.githooks。Python 3.9.6。
- main取り込み先で /usr/bin/python3 -m unittest discover -s tests -v は374件成功。新規12件、既存362件。Ruff整形30ファイル・lint成功、git diff --check 1235931..HEAD成功。取り込み文書リンク484件欠落0、最後の回答更新5文書441件欠落0（アンカー除外）。
- 隔離誤り注入：設定重複検査除去4 failures、bool許容2、R=0分岐無視3、時計境界除去4、目標min除去2、切捨順1、割合float化1。いずれも最終実験errorsなし。読込エラーを検出力成功とは扱わない。全入力の証明ではない。
- 最終コード・記録・統合状態・理解確認の独立レビューはすべてCritical/Important/Minor 0。通常コミットフック成功は単体テストや独立レビューの代替ではない。
- Git更新は通常権限でindex.lockの制約が出たため、許可された保存/統合範囲として権限昇格で実施。自動承認レビューの拒否なし、未解決ブロックなし。
- Snapshot：前半完了、次テーマ選定済み、引き継ぎ準備。新テーマ計画作成/学習は人間の新セッション入力待ち。製品/テスト/設定変更は今回なし。

## 次の具体的アクション

1. 指定場所でgit status --short --branch、git log -3 --oneline、.venv/bin/ruff --version、git config --local --get core.hooksPathを実行。準備記録と現在状態を区別する。
2. AGENTS.md、README.md、docs/documentation-guide.md、docs/resume.md、本書、docs/next-topics.md、docs/02-project-direction.md、全体設計、前半計画/学習/知識、確認範囲を読む。
3. ~/.codex/observations/test-driven-development.md、docs/knowledge/test-coverage-review.mdを読み、契約/独立期待値/検出したい誤り/既存補完/未検証を点検する。
4. kaname_shogi/usi_engine.py、time_management.py、tests/test_usi_engine.py、test_usi_engine_launcher.py、test_time_management.py、kaname-shogi-usiを読み取り照合。必要な一次資料は公式資料を優先。writing-plans等の適用スキルを確認する。
5. 必要な学習は一問ずつ回答を待つ。時計受付・設定接続の範囲/API/所有者/例外/検証/後続境界を具体化し、計画文書と独立レビューを提示。明示承認前にコード・テスト・設定変更/TDDへ進まない。

## 再開用プロンプト

```text
/Users/oki2a24/kaname-shogi で、選定済みテーマ「USI時計受付・設定接続の実装計画だけ」を開始してください。
最初に git status --short --branch、git log -3 --oneline、.venv/bin/ruff --version、git config --local --get core.hooksPath を実行してください。
AGENTS.md、README.md、docs/documentation-guide.md、docs/resume.md、docs/handover-usi-clock-settings-implementation-plan.md を読み、引き継ぎに指定した資料と現在の物理状態を確認してください。
前半の設定読込・時間予算計算はmain統合・取り込み先検証・理解確認まで完了しています。今回は承認済み全体設計のUSI時計引数検証、自分側時計の選択、起動時設定読込・保持、既存予算計算への接続だけを実装計画へ具体化してください。式・許容範囲・JSON方針・暫定値を維持し、時計なしと予算0、既存応答との互換性、後続探索制御との境界を明記してください。
~/.codex/observations/test-driven-development.md と docs/knowledge/test-coverage-review.md を参照し、独立期待値・検出対象・既存補完・未検証を記載してください。学習は一問ずつ回答を待ってください。
今回は計画作成・レビュー・提示までです。コード・テスト・設定変更、TDD、入力並行処理・探索中断の実装、計測・対局・ShogiHome操作は始めず、計画提示後に本人の明示承認を待ってください。main取り込みも別承認です。
```

## 準備文書の確認

差分検査成功、対象5文書の相対リンク450件欠落0（アンカー除外）、再開用プロンプト見出し存在を確認。独立レビューCritical 0・Important 0・Minor 0。文書のみのため単体テストは再実行せず、前回結果を今回の新規実行結果へ置き換えない。準備ブランチへ保存し、新セッションの人間入力を待つ。保存コミットはGitログで確認する。
