# 引き継ぎ：支えのない狙われた駒のB段階実装

作成日：2026-10-30。本人はA段階の最終理解確認に回答し、承認済み実装計画に沿うB段階へ進むことを「YES」と選択した。次セッションでは本書・現在地・現物を照合してから、承認済み計画のTask 1を開始する。

## 最終目標

主線「駒得以外の局面評価を一項目ずつ育てる」の次項目「相手の利きがあり、味方の支えがない駒を評価する」を、承認済み設計と実装計画に沿って学習・実装・検証・レビュー・記録する。既存の評価方式・一手選択器の既定経路を上書きせず、新しい評価部品を既存の一手選択器へ引数で注入できることまで確認する。

この承認は実装計画の実行とB段階への移行を認めるもの。ローカルmainへの統合とorigin/mainへのpushは別の判断であり、実装完了後に本人の承認を得る。

## 完了した事項と意思決定の背景

### 主線の経緯とテーマ選定

- 主線のA1/B1（未成飛車の可動性）は実装・検証・統合・理解確認まで完了。C1比較は改善・悪化の判定不能で一旦区切った。
- A2/B2（玉周辺安全度）は完了。C2では比較CLI限定の安全度重み1候補が登録4局面・各509組で95%区間[0.227, 0.305]となり、悪化を支持した。この結果を全局面や通常対局の棋力へ一般化しない。今回の新しい評価へ玉周辺安全度を合成せず、採用済み評価として扱わない。
- 本人は2026-10-29に「駒の連携」の入口として本項目を選定した。選定理由は尋ねていないため、本人の理由として推測しない。
- C2の結果を受けて玉を対象へ含めるか質問があり、対話を通じて対象と攻撃・支え役を分けた。対象は盤上の玉以外、玉は攻撃元・支え役に含める、と本人が個別に選択した。

### 本人が確認した仕様と設計

- 対象は盤上の玉以外の全13駒種。成駒も対象にし、成った後の動きを使う。
- 対象駒のマスに相手の利きが一つ以上あり、味方の支えが0なら一枚につき1。複数の攻撃元でも1、支えが一つ以上なら0。駒の価値による重みづけはしない。
- 利きは現局面の駒の動き方と遮蔽による判定。手番・持ち駒・合法性を参照せず、攻撃側と支え側のピン駒も数える。対象自身は自分への支えにしない。
- C(P)をP側の対象枚数、Qを相手とし、U(P)=C(Q)-C(P)。自分に有利な値ほど正。駒得Mとの合成はE(P)=10*M(P)+1*U(P)で、重み10/1は初期の仮値。
- 改善仮説は、一手後評価に加えると不用意に支えのない場所へ駒を差し出す手を減らせるかもしれない、というもの。棋力改善は実証していない。
- 玉周辺安全度・飛車可動性・駒得との重複を分ける独立期待値、限界、検証対象は承認済み設計に整理した。C2安全度の合成、通常CLI/USI、比較CLI公開、SFEN入出力、飛車可動性v2、二手・四手への適用はこのBに含めない。

### 現行コードと一手選択器について確認したこと

- 公開操作is_square_attacked(board, target, attacking_side)は、盤面・対象マス・攻撃側を受けて利きの有無を返す読み取り操作。既存コードは友軍占有マスへの支え、ピンされた攻撃側・支え側を今回の条件で判定できるため、そのまま再利用する設計にした。既存利き関数を改修する必要はない。
- Positionは局面データ、Boardは盤面データ、Sideは先後を表す値、Squareはマスを表す値、PieceTypeは駒種を表す値。`is_square_attacked`は盤上の利きを照会する操作。
- `choose_one_ply_move`は候補ごとに一手後の局面を作り、呼び出し元が渡した評価操作で採点し、一手詰みを優先して最大値を選び、同点を抽選する既存操作。旧一手駒得は別の評価経路で、呼び出しごとに別評価を渡せる。
- 本人は既存一手選択器が方式を上書きしないかを確認した。評価引数の注入は既存選択器の実装・既定方式を変更せず確認できると説明し、本人は了解した。Bでは新評価を渡すテストを追加し、既存選択器・方式の製品コードは変更しない。

### 独立期待値とレビュー

- 共通局面：先手玉９九・桂５五、後手王１一。Aは先手金４七・後手歩５四、Bは先手金４六・後手歩５四、Cは先手金４七・後手歩５三、Dは先手金４六・後手歩５三。先手C=1/0/0/0、後手C=0、先手U=-1/0/0/0、M=14、既定E=139/140/140/140。
- 双方非零の局面は先手玉９九・桂５五・桂３五・金４七・歩７五、後手王１一・歩５四・歩３四・桂７四。先手C=2・後手C=1、先手U=-1・後手U=+1、先手M=14、E=139、後手E=-139。
- 金４七→４六の候補と金４七→３七の候補は、設計上いずれも一手後のM=14。前者U=0・E=140、後者U=-1・E=139。これらは手書き期待値であり、実装出力から逆算していない。ユーザー最終理解確認の回答`a`は正解Aで、「式の局面別反映を確認する値で、棋力改善を示さない」と説明済み。
- 設計全体は本人承認済み。実装計画全体と推薦したネイティブ方式も2026-10-30に本人承認済み。独立設計レビューはCritical 0 / Important 0 / Minor 0。独立計画レビュー初回のMinor 1（既存テストの非公開補助に依存）は、新規テスト支援へ詰み局面を明記して解消し、再レビューはCritical 0 / Important 0 / Minor 0。これらは製品コードの実行確認ではない。

## 承認済み実装計画

計画の正本は[実装計画](plans/2026-10-30-undefended-piece-implementation-plan.md)、設計は[設計書](plans/2026-10-30-undefended-piece-evaluation-design.md)、回答と経緯は[学習記録](learning/undefended-piece-coordination-evaluation.md)。実装計画とネイティブ方式の再承認を求めない。TaskごとのRedでは、読み込みエラーだけを振る舞いの失敗と見なさず、固定期待値に対する狙ったassertion failureを確かめる。最小実装後Greenを確認し、Refactor要否を判断し、各Taskの独立レビューと最終レビューを行う。

1. **C/U集計:** 新規kaname_shogi/undefended_piece.py、tests/undefended_piece_support.py、tests/test_undefended_piece.py。`attacked_undefended_piece_count(position, side) -> int`と`attacked_undefended_piece_balance(position, perspective) -> int`を作る。四組合せ、双方非零と視点反転、13駒種、成駒の支え、玉の対象除外と攻撃・支え利用、ピン、遮蔽、複数攻撃・支え、手番・持ち駒非依存、副作用なしを固定期待値で確認する。既存の利き専用テストも補完として実行する。
2. **重み付き合成:** 新規kaname_shogi/material_undefended_piece.pyとtests/test_material_undefended_piece.py。凍結設定データ`UndefendedPieceWeights(material=10, undefended=1)`と`evaluate_material_undefended_piece(position, perspective, *, weights)`を作る。materialは1以上、undefendedは0以上の整数。boolとfloatを拒否し、undefended=0でもUの操作を呼ぶ。A-Dと双方非零の独立期待値、逆視点、異なる重み、持ち駒、玉なし局面、例外・状態不変を確認する。
3. **既存一手選択器への注入:** 新規tests/test_undefended_piece_selection.pyのみ。新評価と旧material_balanceの関数を同じ`choose_one_ply_move(..., evaluate=...)`へ渡し、先後・候補順・同点抽選・重み0・一手詰み優先を確認する。金４七→４六と金４七→３七を候補にし、候補の合法性・非詰み、E=140/139を確認。既存の詰み・同点・空候補・例外・成り/捕獲/打ち枝の契約を既存テストから点検し、今回の検査で直接確かめた範囲と分けて記録する。既存の選択器や評価方式の製品コードは変更しない。

各Task完了後にRefactor要否確認・独立レビュー・関係するテスト・Ruff・差分検査を行い、Critical/Importantを解消して再検証・再レビューする。全体レビュー、計画済みの代表変異7件の隔離コピー検査、文書・リンク点検を終え、対象ファイルを限定して通常コミットする。細かなコマンドと全受け入れ条件は承認済み計画を正本として使う。

## 現在の物理状態

- 作業worktree：/Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogi
- B用ブランチcodex/undefended-piece-evaluationをこのworktreeだけに作成した。ブランチ作成前の基点はローカルmainのbf826066、作成時のmainはorigin/mainより20コミット先行。ハンドオフ文書のコミット後HEADは、本書に記録された確認コマンドで取得し直す。
- 環境確認：python3と.venv/bin/python3はPython 3.15.2、requirements-dev.txtと.venv/bin/ruffはいずれもRuff 0.16.10、git config --local --get core.hooksPathは.githooks。READMEに記載のPython 3.14以上を満たし、セットアップ再実行は不要だった。
- 製品変更前baselineを2026-10-30に`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 scripts/run_tests_parallel.py`で実施。943 tests across 67 modules、21.826 seconds、OK。baseline後、製品コード・テストは変更していない。文書コミットのみでコードが変わらない場合に全体テストを再実行しない。
- 実装計画・学習記録・設計・現在地などの文書を対象ファイル指定でコミットする。C2比較成果物4件は未追跡のまま保持し、stage・移動・削除・上書きしない。

  data/comparison/runs/c2-king-safety-confirmation-2026-10-28-seeds.json
  data/comparison/runs/c2-king-safety-confirmation-2026-10-28-workers-4-analysis.json
  data/comparison/runs/c2-king-safety-confirmation-2026-10-28/
  data/comparison/runs/c2-king-safety-confirmation-2026-10-28-workers-4/

- 元の/Users/oki2a24/kaname-shogiには未コミット文書・比較データがある。clean/reset/ブランチ切替・削除・上書きを行わない。元checkoutは本セッションで変更していない。
- C2のローカルmain統合はpushしていない。新しいB実装のmain統合・pushも別途本人承認が必要。
- 長時間比較・分析CLIは実行していない。実行する場合は本人が端末で行う。
- コード、テスト、製品設定は未変更。手書き設計値とbaseline以外に今回の製品動作を実測していない。

## 次の具体的な行動

1. 新セッション開始時に次をこのworktreeで実行し、現物・本書・再開案内を照合する。

    git status --short --branch
    git log -3 --oneline --decorate
    git branch --show-current

2. AGENTS.md、docs/resume.md、本書を読む。4件のC2成果物と対象worktree・元checkoutの現物を確認する。元checkoutを操作しない。
3. 作業ブランチがcodex/undefended-piece-evaluationであること、Python・固定Ruff・hook状態を再確認する。個人の/Users/oki2a24/.codex/observations/test-driven-development.mdとdocs/knowledge/test-coverage-review.mdを改めて読み、承認済み計画のTask 1から始める。
4. baseline 943/67/21.826秒の記録を現在の製品ソースと比較する。コード・依存・テスト対象に変化がなければ、理由なくbaseline全体を再実行しない。差があれば原因を切り分けてから製品変更へ進む。
5. superpowerssuperpowers:executing-plansとsuperpowerssuperpowers:test-driven-developmentを適用し、Task 1を振る舞いごとのRed→最小実装→Green→Refactor要否確認→独立レビューで進める。Task 2、Task 3も同様。新規コードを書く前にテストを追加し、意図したassertion failureを確かめる。
6. Python変更時はAGENTS.mdのRuff順序、専用・関連・全体テスト、変異検査、独立最終レビュー、記録・限定コミットを計画どおり行う。既存テストの成功を今回の実測へ置き換えない。

## 再開用プロンプト

> /Users/oki2a24/.codex/worktrees/b2-main-integration/kaname-shogiで、本人が承認した「相手の利きがあり、味方の支えがない駒を評価する」B段階の実装を始めます。最初にgit status --short --branch、git log -3 --oneline --decorate、git branch --show-currentを実行し、AGENTS.md、docs/resume.md、本引き継ぎと現物を照合してください。本人は2026-10-29にテーマを選定し、選定理由は未聴取です。設計全体と実装計画全体、推薦したネイティブ実行方式は本人が2026-10-30に明示承認し、A最後の理解確認にはa（正解A）と回答しました。本人は同日にB段階へ進むことを選びました。コード・テスト変更は未着手です。専用ブランチcodex/undefended-piece-evaluationを確認してください。個人の/Users/oki2a24/.codex/observations/test-driven-development.mdとdocs/knowledge/test-coverage-review.mdを読み、環境・Ruff固定版・ローカルフックを再確認してください。製品変更前baselineは2026-10-30に943件・67モジュール・21.826秒で成功し、以後製品コードとテストに変更はありません。承認済み計画のTask 1から、assertion失敗を確認するTDDで進めてください。各Task後にRefactor要否確認と独立レビューを行い、最終独立レビュー・検証・記録を完了してください。C2比較成果物4件を保持し、元の/Users/oki2a24/kaname-shogiはclean/reset/切替・削除・上書きしないでください。通常CLI/USIへの公開、SFEN入出力、飛車可動性v2、玉周辺安全度との合成、二手・四手適用は追加しないでください。長時間比較・分析CLIは本人が端末で実行します。main統合とpushは別途本人承認を得てください。すべて日本語で進めてください。
