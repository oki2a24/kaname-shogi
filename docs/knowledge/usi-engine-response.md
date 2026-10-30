# USIエンジンの一手応答

更新日：2026-10-31

## 境界

`kaname_shogi.usi_engine.run_usi_engine(input_fn, output_fn, rng=None, *, time_config=None, cancel_input_fn=None)` は注入された一行入出力関数でUSIコマンドを処理する。入力関数はEOF時に `EOFError` を送出し、出力関数には改行なしの応答一行を渡す。標準入出力の入口は `python3 -m kaname_shogi.usi_engine`。日本語CLIとは分離している。待機する注入入力には、別threadから呼ぶcancel_input_fnで必ず返却またはEOFErrorにできることが必要。有限入力は取消省略可。出力は探索担当からも呼ばれるため再入させない。

## 局面と一手

- `position` は `position startpos moves <1手以上>`、`position sfen <SFEN>`、`position sfen <SFEN> moves <指し手...>` に対応する。`parse_usi_position` が再現した最新 `Position` を非公開 `_UsiEngineState` が保持する。状態オブジェクトは `Position` または未設定の `None` だけを持つ。
- `replace_position` は局面を置き換え、`clear_position` は未設定へ戻し、`require_position` は局面を返すか未設定時に `ValueError` を送出する。設定値、棋譜、合法手選択、乱数器はこの状態オブジェクトへ入れない。
- 各goで独立Position.copyと新SearchControlを作り、`search_move(position, policy, rng, control)` が停止可能な生成・選択を一回行い、`format_usi_move` が表記する。選択した手はUSIエンジン内のPositionへ適用しない。
- 合法手がない場合は `bestmove resign` を返す。

## Difficulty option と局ごとの方針

`usi` には次のcombo行を `usiok` より前に出す。

```text
option name Difficulty type combo default Random var Random var Material var TwoPlyMaterial var FullWidth4 var AlphaBeta4 var MaterialUndefendedPiece
```

`setoption name Difficulty value Random` は一様ランダム、`value Material` は一手後の駒得比較、`value TwoPlyMaterial` は二手先読み（駒得）の方針を選択境界へ渡す。`value FullWidth4` は枝を省略しない最大4手の反復深化、`value AlphaBeta4` はαβ枝刈り付き最大4手の反復深化を選ぶ。`value MaterialUndefendedPiece` は既存の `10M+U` 評価を使う制御付き一手選択を選ぶ。一手詰み優先と既存の停止制御を使い、二手・四手探索には切り替えない。新二方式は各 `go` で深さ1から4へ進む。設定がない場合は `Random`。USI仕様に従い、受信時のoption名と値は大文字小文字を区別せずに比較する。[USI仕様 §5.3 `setoption`](https://hgm.nubati.net/usi.html)はnameとvalueをcase-insensitiveとしている。未知の設定名は読み飛ばし、既知の `Difficulty` に不正値が届いた場合は最後の有効値を保つ。

設定値は `run_usi_engine` 内で `_UsiEngineState` と別に保持する。局の最初の `go` で有効値を局内方針として固定するため、後から届いた `setoption` は現在局の後続 `go` には影響しない。`usinewgame` は局面を消し、局内固定だけを解除して、設定値を次局へ残す。乱数器も設定・局面状態と別にし、一回のエンジン実行中で共有する。

以前の三択通知・受付とそのShogiHome確認は、各リンク先に記録した当時の実績として保持する。2026-10-19に `FullWidth4`・`AlphaBeta4` を追加し、`game_search.search_move` をUSI入口へ接続した。先行する新二方式の局中固定・次局継承、未知値保持、時計予算・同一制御、応答状態・送信競合・実入口確認は[今回の実装・学習記録](../learning/four-ply-search-game-integration-plan.md)を参照する。この作業ではShogiHome実機を確認していないため、二新方式のGUI表示・対局互換性・応答時間は未検証である。

## コマンドとエラー

- `usi` はid行、Difficulty option行、`usiok`を順に返し、`isready` は `readyok` を返す。
- 未知コマンド、未知の `go` トークンは応答せず読み飛ばす。`gameover` は未送信応答を抑制して探索を回収し、入力受付を継続する。局面・設定寿命はusinewgameに代えない。
- `go` は時計引数を検証し、現在Position.side_to_moveの自分側時計から予算を計算する。go完成行の読取り時刻を整数nsで制御へ渡し、期限判定・探索停止へ接続する。0予算でも最初の合法手確保または手なし確定まで通常停止を保留する。
- `searchmoves`、`depth`、`nodes`、`mate`、`infinite`、`ponder`、`movetime` は未対応として `ValueError`。有効なpositionがない `go` と、対応外・不正なpositionも `ValueError`。
- 実行入口は入力受付前に同梱JSON設定を一回読む。設定のValueError/OSErrorはstderr診断・終了1、USI入力のValueErrorもstderr診断・終了1。設定読込失敗を代替値で隠さない。USI応答だけをstdoutに書き、各行をflushする。
- `quit` と入力EOFは未送信応答を抑制し、入力待機を解除して両担当を回収後、正常終了する。探索・応答未完了中のposition/go/usinewgameは抑制してValueError。送信後の命令は前担当回収後に処理する。

## コマンド行の表現

コマンド行は `split()` と既存の文字列分岐で扱う。USIコマンド型や公開状態APIは設けない。非公開状態クラスを独立モジュールやpackage rootから再exportしない。

第59〜62回にShogiHome 1.28.1で平手対局・観察を行った記録は[ShogiHome対局の知識メモ](usi-shogihome-gameplay.md)を参照する。第65回はDifficulty選択画面とMaterial設定のUSI送信を確認し、第66回は同じ7手局面でRandomの☖９四歩、Materialの☖８八角成を実機観察し、両方の設定と着手をUSIログで確認した。これは一局面・各設定一局の実例であり、他局面に対する一般性は示さない。詳細は[第66回学習記録](../learning/66-shogihome-material-move-effect.md)を参照する。

第67回で追加した `position sfen` のコード対応は、第69回にShogiHome 1.28.1からの実通信でも確認した。4欄SFENを画面へ貼り付けた後、時計あり（持ち時間10分・秒読み30秒）の一局で `position sfen ...`、時間付き `go`、`bestmove 9a9b` がログに記録され、盤面にも後手の合法手が反映された。画面貼り付けだけでは通信確認にならない。ShogiHomeは持ち時間と秒読みが両方0の設定を「持ち時間と秒読みが両方とも0です」と拒否したため、時計なし対局はこの版・画面では開始できなかった。実測の範囲と後片付けの制約は[第69回学習記録](../learning/69-shogihome-sfen-engine.md)を参照する。

## 時計受付と設定の寿命

時計ありではbtime/wtimeを両方必須とし、byoyomi省略は0。非負整数ms、重複・値欠落・非整数・負を拒否する。半角十進数字と任意の先頭符号、先頭0を許し、-0は0。binc/wincは0のみ受付、正は未対応。時計項目なし・加算0だけは時計なしNone、byoyomiだけは必須時計不足。未知goトークンを読み飛ばしても後続の既知項目を検査する。

TimeManagementConfigは不変な設定データで、mainが一回読んで非公開sessionへ注入する。runの省略時だけ同じloaderで一回読み、全go/usinewgameで保持する。局面やDifficultyの寿命とは分離し、別runでは読み直す。SearchBudgetは期間データで停止操作ではない。時計なしNoneと明示時計の0予算を区別し、各goの探索制御へ渡す。[計画・検証範囲](../plans/2026-10-12-usi-clock-settings-implementation-plan.md)、[実施記録](../learning/usi-clock-settings-implementation-plan.md)。時間内応答は保証しない。

## 入力・送信・故障回収（2026-10-12接続）

[承認済み接続計画](../plans/2026-10-12-input-concurrency-usi-implementation-plan.md)、[実装・検証記録](../learning/input-concurrency-usi-plan.md)。本人承認によりmain取り込み・取り込み先検証済み。

現在threadが命令を管理し、一入力threadとgoごとの一探索threadをQueueで接続する。読取りと入力確定は別。入力確定と最終送信を同じLockで順序付け、先に終了・禁止命令を確定すれば送信しない。先に送信を完了すればその一回は残る。通常stopは抑制にせず、idle stopは持ち越さない。isready/usiは探索中も行単位で送信できる。

既存三方式の `SearchResult` は結果データ。COMPLETE/Noneだけresign、INTERRUPTEDは合法手、SUPPRESSEDは無応答。新二方式の制御付き反復結果は対局アダプターで既存の状態・手へ変換され、USI送信側は同じ契約を使う。NO_LEGAL_MOVEは手なしとして `bestmove resign`、STOPPEDは最新完了手または合法予備手、SUPPRESSEDは手なしとなる。送信直前にも共通Lock下で抑制を再確認し、writeとflushが戻ってからsentを確定するため、一つの探索応答は最大一回である。送信完了と担当終了は別なので、次探索前に共通Lock外でjoinする。乱数器は実行内共有だが並行探索へ渡さない。

mainの入力源はmacOSのfdと内部終了pipeをselectorで待ち、非blocking readと逐次復号を使う。LF/CRLF/CR、分割文字、EOF末尾行に対応する。CRのみは次バイトまたはEOFで完成する。完成時刻から受渡し・前担当回収・解析・複製・起動を予算へ含める。借用stdinは閉じず属性を復元し、自前pipe/selectorだけ解放する。標準入力は先読みされていないことが前提。

担当故障はQueueで主担当を起こし、次のGUI入力を待たず取消・抑制・両担当回収へ進む。送信故障は再送しない。構築・後片付け故障でも残る解放を試み、主原因と追加故障をstderrへ診断し終了1。KeyboardInterruptは回収後に再送出する。

実入口・実pipe・制御付き探索と実探索ラッパーを分けて確認した。全競合・全局面・全OSは未証明。OS遅延、単一処理、出力先の詰まり、合法手未確保時の通常停止保留による超過は残る。他OSではfd同時待機・nonblocking・復号改行・取消回収を再点検する。計測・対局・ShogiHomeの再確認は行っていない。
