# 三方式の選択時間計測だけ

## 目的・範囲・承認

2026-10-11、本人の再開指示により、[承認済み計画タスク5](../plans/2026-10-10-two-ply-implementation-plan.md#タスク5全体検証記録統合)の時間計測1項目だけを実施した。[開始時の引き継ぎ](../handover-selection-timing.md)と現物を照合した。計画訂正なし。製品・テスト・独立した計測スクリプトの追加変更なし。以下は実施記録であり、新規実装計画ではない。

開始HEAD `0db3e1b`、作業場所 `/Users/oki2a24/kaname-shogi`、ブランチ `codex/selection-timing-handoff`、開始差分なし。mainは `f4083dd`。Ruff 0.16.10は固定版に一致、ローカルフックは `.githooks`。新規worktree・pushなし。

## 実行前に明確にした条件

- 対象操作は `choose_move(position, moves, policy, rng)` 一回。`MoveSelectionPolicy` は選択方針のデータ、`choose_move` は一手を選ぶ操作。
- 計測は `time.perf_counter()` の呼出し直前・直後の差（秒）。最初の合法手列挙、局面・乱数器作成、import、検証・出力は区間外。二手方式内部の応手列挙・詰み判定・評価・抽選は区間内。画面・通信・プロセス起動の時間は含めない。
- 各回に局面と合法手タプルを新規作成し、`random.Random(0)` を新規作成。連続した乱数列の3抽選ではなく、同じ乱数種0からの独立した3呼出し。選択手を次の回へ適用しない。
- 同一Pythonプロセスで、教材→平手、各局面でRandom→Material→TwoPlyMaterial、方式ごとに1〜3回の固定順。ウォームアップなし、並列計測なし。GC・OSスケジューリングは既定、他プロセス・電源・温度は制御していない。
- 呼出しごとにSIGALRMの実時間タイマー60秒を設定し、終了後解除。これは安全上の打切りであり性能合否閾値ではない。例外・打切りもそのまま出力し、成功値への置換や再測定をしない。
- 実行前に以上をチャットで提示。承認済み項目の条件具体化であり計画本文は変更していない。測定中の条件変更なし。

## 機器・Python・局面

実行開始は2026-10-11 14:27:33 JST。MacBook Pro（Mac17,2）、Apple M5、10コア、メモリ32 GB。`system_profiler SPHardwareDataType` で確認（識別用番号は記録しない）。`sysctl` のCPU名照会はサンドボックスで拒否されたため、測定前にsystem_profilerで確認した。

macOS 27.0.1 / arm64、CPython 3.9.6（Clang 21.0.0）。実行ファイル `/Library/Developer/CommandLineTools/usr/bin/python3`。時計は `mach_absolute_time()`、monotonic=True、adjustable=False、表示分解能約4.17×10^-8秒。表示桁数が測定精度を保証するわけではない。

教材は承認済み設計・既存USIテストと同じ、先手９九玉・５五飛、後手１一玉・５三金・５四歩、先手番、双方持ち駒なし、他は空。SFENは `8k/9/4g4/4p4/4R4/9/9/9/K8 b - 1`、合法手16件。平手は `create_initial_position()`（平手初期局面を作る操作）から作成し、SFENは `lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1`、先手番・双方持ち駒なし・合法手30件。

## 結果

単位は秒。各組3回の最大値は観測最大であり、全局面・将来実行の上限ではない。

| 局面 | 方式 | 1回目 | 2回目 | 3回目 | 最大 |
| --- | --- | ---: | ---: | ---: | ---: |
| 教材 | RANDOM | 0.000003541 | 0.000001250 | 0.000001083 | 0.000003541 |
| 教材 | MATERIAL | 0.003226167 | 0.003232916 | 0.003329417 | 0.003329417 |
| 教材 | TWO_PLY_MATERIAL | 0.107445334 | 0.106088541 | 0.104725458 | 0.107445334 |
| 平手 | RANDOM | 0.000001583 | 0.000001000 | 0.000000959 | 0.000001583 |
| 平手 | MATERIAL | 0.006880125 | 0.006882500 | 0.006975417 | 0.006975417 |
| 平手 | TWO_PLY_MATERIAL | 0.607585833 | 0.607304375 | 0.604583250 | 0.607585833 |

18回すべて正常終了、例外・打切り0。各回で返却手が元の合法手一覧に含まれ、呼出し前後のSFENが一致。今回の環境・2局面では二手方式の選択時間が他方式より長かった。棋力向上・全局面での応答時間・統計的な速度比は主張しない。Randomの極短時間は時計呼出し等の影響もあるため、精密な性能比較としない。

実用性について、本人へ教材最大約0.107秒・平手最大約0.608秒と測定区間の制約を提示した。本人回答は「実際の使用感を判断するには情報が足りない」。アシスタント補足：今回の選択操作の計測だけでは使用感を判断できないため、実用性は未判断として残す。許容・不許容のどちらにも読み替えず、実際の使用感確認へ範囲を広げない。事後の合否基準は設けていない。

## 実行方法と生の出力

リポジトリ直下で `python3 - <<'PY' > /tmp/selection-timing-run.txt` により標準入力のPythonコードを一度実行し、終了後 `cat /tmp/selection-timing-run.txt` で確認した。独立した計測用Pythonファイルは保存していない。以下は実行ツール呼出しに渡した標準入力コード全文の転記（事後保存）。再実行はしていない。Pythonスクリプト製品として追加したものではなく、測定の監査・再現用記録である。

```python
import platform
import random
import signal
import sys
import time
from datetime import datetime
from kaname_shogi.model import Board, Piece, PieceType, Position, Side, Square, create_initial_position
from kaname_shogi.movegen import MoveSelectionPolicy, choose_move, legal_moves
from kaname_shogi.sfen import SfenPosition, format_sfen

print(datetime.now().astimezone().isoformat(), sys.version, platform.platform(), flush=True)
print('clock', time.get_clock_info('perf_counter'), flush=True)
def timeout_handler(signum, frame):
    raise TimeoutError('60秒で打切り')
signal.signal(signal.SIGALRM, timeout_handler)
for label in ('教材', '平手'):
    for policy in (MoveSelectionPolicy.RANDOM, MoveSelectionPolicy.MATERIAL, MoveSelectionPolicy.TWO_PLY_MATERIAL):
        for repeat in range(1, 4):
            if label == '平手':
                position = create_initial_position()
            else:
                board = Board()
                for file, rank, kind, side in (
                    (9, 9, PieceType.KING, Side.SENTE),
                    (5, 5, PieceType.ROOK, Side.SENTE),
                    (1, 1, PieceType.KING, Side.GOTE),
                    (5, 3, PieceType.GOLD, Side.GOTE),
                    (5, 4, PieceType.PAWN, Side.GOTE),
                ):
                    board.set_piece(Square(file, rank), Piece(kind, side))
                position = Position(board, Side.SENTE)
            before = format_sfen(SfenPosition(position, 1))
            moves = legal_moves(position)
            rng = random.Random(0)
            signal.setitimer(signal.ITIMER_REAL, 60)
            start = time.perf_counter()
            try:
                selected = choose_move(position, moves, policy, rng)
                elapsed = time.perf_counter() - start
                status = '成功'
            except Exception as error:
                elapsed = time.perf_counter() - start
                status = repr(error)
                selected = None
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
            after = format_sfen(SfenPosition(position, 1))
            print(label, policy.name, repeat, format(elapsed, '.9f'), status, '候補数', len(moves), '合法', selected in moves, '局面保存', before == after, 'SFEN', before, flush=True)
```

SIGALRMハンドラは `TimeoutError('60秒で打切り')` を送出する。終了後の合法性・SFEN比較・出力は時間に含めない。以下に一時ファイル消失後も追跡できる出力全文を保存する。

```text
2026-10-11T14:27:33.355305+09:00 3.9.6 (default, Aug 25 2026, 21:26:21)
[Clang 21.0.0 (clang-2100.3.34.2)] macOS-27.0.1-arm64-arm-64bit
clock namespace(implementation='mach_absolute_time()', monotonic=True, adjustable=False, resolution=4.166666666666667e-08)
教材 RANDOM 1 0.000003541 成功 候補数 16 合法 True 局面保存 True SFEN 8k/9/4g4/4p4/4R4/9/9/9/K8 b - 1
教材 RANDOM 2 0.000001250 成功 候補数 16 合法 True 局面保存 True SFEN 8k/9/4g4/4p4/4R4/9/9/9/K8 b - 1
教材 RANDOM 3 0.000001083 成功 候補数 16 合法 True 局面保存 True SFEN 8k/9/4g4/4p4/4R4/9/9/9/K8 b - 1
教材 MATERIAL 1 0.003226167 成功 候補数 16 合法 True 局面保存 True SFEN 8k/9/4g4/4p4/4R4/9/9/9/K8 b - 1
教材 MATERIAL 2 0.003232916 成功 候補数 16 合法 True 局面保存 True SFEN 8k/9/4g4/4p4/4R4/9/9/9/K8 b - 1
教材 MATERIAL 3 0.003329417 成功 候補数 16 合法 True 局面保存 True SFEN 8k/9/4g4/4p4/4R4/9/9/9/K8 b - 1
教材 TWO_PLY_MATERIAL 1 0.107445334 成功 候補数 16 合法 True 局面保存 True SFEN 8k/9/4g4/4p4/4R4/9/9/9/K8 b - 1
教材 TWO_PLY_MATERIAL 2 0.106088541 成功 候補数 16 合法 True 局面保存 True SFEN 8k/9/4g4/4p4/4R4/9/9/9/K8 b - 1
教材 TWO_PLY_MATERIAL 3 0.104725458 成功 候補数 16 合法 True 局面保存 True SFEN 8k/9/4g4/4p4/4R4/9/9/9/K8 b - 1
平手 RANDOM 1 0.000001583 成功 候補数 30 合法 True 局面保存 True SFEN lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1
平手 RANDOM 2 0.000001000 成功 候補数 30 合法 True 局面保存 True SFEN lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1
平手 RANDOM 3 0.000000959 成功 候補数 30 合法 True 局面保存 True SFEN lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1
平手 MATERIAL 1 0.006880125 成功 候補数 30 合法 True 局面保存 True SFEN lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1
平手 MATERIAL 2 0.006882500 成功 候補数 30 合法 True 局面保存 True SFEN lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1
平手 MATERIAL 3 0.006975417 成功 候補数 30 合法 True 局面保存 True SFEN lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1
平手 TWO_PLY_MATERIAL 1 0.607585833 成功 候補数 30 合法 True 局面保存 True SFEN lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1
平手 TWO_PLY_MATERIAL 2 0.607304375 成功 候補数 30 合法 True 局面保存 True SFEN lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1
平手 TWO_PLY_MATERIAL 3 0.604583250 成功 候補数 30 合法 True 局面保存 True SFEN lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1
```

## 検証・検出範囲・Refactor・レビュー

対象契約は2局面×3方式×3回を同じ初期化・測定区間で観察し、各回と最大を正しく記録すること。対象ケースは先手番の教材部分局面と平手初期局面。18行の組合せ・回数・非負の秒数・成功状態・合法性・局面保存を点検し、表と出力を照合する。合法性確認だけでは方式取り違え・最良性を検出できないため、呼出しに渡す列挙値も独立レビューで確認する。探索の正しさは既存テストが補完するが、今回の時間測定を全入力の性能証明にはしない。

製品・テストの振る舞い変更がないため、新機能のRed→Greenや製品への変異注入は実施していない。TDDスキルと個人知見の適用範囲を確認し、計測の観察を未実装Redと扱わない。Refactorは不要。最適化・棋力比較・ShogiHomeは未実施。タスク5全体の完了ではない。

- 生出力との完全一致、18組合せ、各回の成功・合法性・局面保存、6表行の各値と最大を検証コードで照合した。すべて一致。
- `.venv/bin/ruff format --check .` は28ファイル整形済み、`.venv/bin/ruff check .` は成功、`git diff --check` 成功。製品・テスト変更なしの文書記録のため全体単体テストは再実行していない。過去の362件成功を今回の実行結果とは扱わない。
- 実行者は対象4文書の相対リンク先412件欠落0（見出しアンカー対象外）を確認。独立レビュアーは相対リンク・見出し416件問題0と差分を実測。
- 独立レビューはCritical 0・Important 0・Minor 0、残件なし。実行コード全文の方式・初期化・区間、教材、表と生出力一致、範囲と入口を確認。初回レビュー中の実行コード全文の提示依頼に応じ、ツール入力を事後転記して監査情報を補完した。レビュアーは計測再実行・製品テスト・Ruff再実行なし。事前提示と元ツール入力の独立確認はせず、保存した全文を確認した。
- 今回の計測・検証・独立レビュー・記録を通常フック付きコミットへ保存する。main取り込みは別途本人承認待ち、取り込み先検証・最後の理解確認は未実施。実用性は本人回答どおり未判断であり、タスク5の全体完了とはしない。

## 要点・確認問題・振り返り・次への問い

選択操作だけの所要時間と、合法手列挙・通信・画面を含む実際の待ち時間を区別する。同一乱数種と新規局面で条件をそろえたが、固定順・3回・2局面という観察の制約が残る。他乱数種・後手番・持ち駒の多い局面・他機器・実際の対局使用感は未検証。

確認問題はmain取り込み承認と取り込み先検証後に一問だけ出す。現在は未出題・未回答。本人回答とアシスタント補足は回答後に記録する。振り返りは、時間計測をテスト全体の所要時間から切り分け、条件と生値を残せたこと。次への問いは「計測区間に何を含めたか」。新テーマは開始しない。

## main取り込みと取り込み先検証

2026-10-11、本人はmain取り込みの確認へ「ok」と回答した。元ディレクトリで `git switch main`、`git merge --ff-only codex/selection-timing-handoff` を実行し、mainを `f4083dd` → `d74fe55` へ進めた。準備 `0db3e1b` を含む。push・新規worktreeなし。

取り込み先で `python3 -m unittest discover -s tests -v` を実行し362件成功（ログ `/tmp/selection-timing-main-tests.log`）。Ruff固定版0.16.10・フック `.githooks` 一致、整形確認28ファイル・lint・差分成功。対象4文書の相対リンク先412件欠落0（見出しアンカー対象外）。時間計測は再実行していない。実用性は本人回答どおり未判断のまま。統合記録を通常コミットへ保存する。最後の理解確認はこれから一問出し、回答を待つ。タスク5全体・後続テーマへは進まない。

統合記録の独立文書レビューは初回Critical 0・Important 0・Minor 1。候補の現在欄にコミット前の表現が残っていたため保存済みの表現へ訂正した。レビュアーはmainのHEAD・全体ログ362件/5.322秒/OK・差分を確認し、全体テスト・時間計測は再実行していない。

訂正後の独立再確認はCritical 0・Important 0・Minor 0、残件なし。最終リンク先412件欠落0・差分・Ruff成功後、通常コミットへ保存する。

## 最後の理解確認と次候補（2026-10-11）

main取り込み先検証と統合記録 `ac7b22b` 保存後、アシスタントは「今回の最大約0.608秒には、choose_moveを呼ぶ前の最初の合法手列挙の時間も含まれていますか？」と一問出題した。

- 本人回答：「いいえ」
- アシスタント補足：そのとおり。最初の合法手列挙は計測区間外。一方、choose_move内部で二手先読みのために行う応手の列挙は区間内。

最初の合法手列挙が対象外という具体的な理解を確認した。内部処理や性能測定全般の習得までは判定しない。三方式の選択時間計測という今回のテーマを一区切りとする。実用性は本人の「実際の使用感を判断するには情報が足りない」という回答どおり未判断であり、タスク5全体の完了ではない。

回答記録後、README・方向性・候補を見直した。次の候補は小さい順に、(1) タスク5の残項目の棚卸しだけ、(2) 実際の使用感を確認する条件の設計だけ、(3) タスク5全体の最終確認。まず実施済み・未完了・未判断を整理すれば、重複検証や自動的な範囲拡大を避けて次の一項目を選べるため(1)を推薦する。(2)では最初の合法手列挙や入出力を含む範囲と本人が判断する方法を決めるが、測定・対局を先に始めない。本人の選定まで新テーマへ着手しない。候補の詳細は[次テーマ候補](../next-topics.md)に記録する。

回答・候補・入口の独立文書レビューはCritical 0・Important 0・Minor 0。方向性の古い計測未実施表記も結果への参照へ訂正し、追加レビューC0/I0/M0。実行者は対象4文書の相対リンク先45件欠落0（アンカー対象外）、Ruff整形28ファイル・lint・差分成功を確認。文書のみのため全体テスト・時間計測は再実行していない。

本人は次候補から「タスク5全体の最終確認。新セッションの準備して」と選定した。今回の後続作業は[引き継ぎ](../handover-two-ply-final-check.md)の文書準備だけとし、本人が再開プロンプトを新セッションへ入力するまで最終確認は開始しない。
