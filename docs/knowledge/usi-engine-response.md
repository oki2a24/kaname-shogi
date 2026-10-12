# USIエンジンの一手応答

更新日：2026-10-12

## 境界

`kaname_shogi.usi_engine.run_usi_engine(input_fn, output_fn, rng=None, *, time_config=None)` は注入された一行入出力関数でUSIコマンドを処理する。入力関数はEOF時に `EOFError` を送出し、出力関数には改行なしの応答一行を渡す。標準入出力の入口は `python3 -m kaname_shogi.usi_engine`。日本語CLIとは分離している。

## 局面と一手

- `position` は `position startpos moves <1手以上>`、`position sfen <SFEN>`、`position sfen <SFEN> moves <指し手...>` に対応する。`parse_usi_position` が再現した最新 `Position` を非公開 `_UsiEngineState` が保持する。状態オブジェクトは `Position` または未設定の `None` だけを持つ。
- `replace_position` は局面を置き換え、`clear_position` は未設定へ戻し、`require_position` は局面を返すか未設定時に `ValueError` を送出する。設定値、棋譜、合法手選択、乱数器はこの状態オブジェクトへ入れない。
- `legal_moves(position)` が合法手を列挙し、共通の `choose_move(position, moves, policy, rng)` が方針別に一手を選び、`format_usi_move` が表記する。選択した手はUSIエンジン内のPositionへ適用しない。
- 合法手がない場合は `bestmove resign` を返す。

## Difficulty option と局ごとの方針

`usi` には次のcombo行を `usiok` より前に出す。

```text
option name Difficulty type combo default Random var Random var Material var TwoPlyMaterial
```

`setoption name Difficulty value Random` は一様ランダム、`value Material` は一手後の駒得比較を選ぶ。`value TwoPlyMaterial` は二手先読み（駒得）の方針を選択境界へ渡す。設定がない場合は `Random`。USI仕様に従い、受信時のoption名と値は大文字小文字を区別せずに比較する。[USI仕様 §5.3 `setoption`](https://hgm.nubati.net/usi.html)はnameとvalueをcase-insensitiveとしている。未知の設定名は読み飛ばし、既知の `Difficulty` に不正値が届いた場合は最後の有効値を保つ。

設定値は `run_usi_engine` 内で `_UsiEngineState` と別に保持する。局の最初の `go` で有効値を局内方針として固定するため、後から届いた `setoption` は現在局の後続 `go` には影響しない。`usinewgame` は局面を消し、局内固定だけを解除して、設定値を次局へ残す。乱数器も設定・局面状態と別にし、一回のエンジン実行中で共有する。

今回の三択通知・受付はmainへ取り込み、検証済み。新値固有の局中固定・次局継承は[今回の実施記録](../learning/usi-policy-lifetime.md)の1系列で検証済み（main取り込み・検証済み）。新値後の未知値保持は[実施記録](../learning/usi-invalid-value.md)の1系列と無設定・旧値対照で検証済み（main取り込み・検証済み、理解確認完了）。新方式の関数境界の実選択・二回の合法応答・局面保存・手なしresignは[実施記録](../learning/usi-function-response.md)の教材と空盤で検証済み（main取り込み・取り込み先検証・理解確認済み）。新方式設定後の実プロセスbestmove・stdout診断分離は[実施記録](../learning/usi-process-response.md)の既存pipeケースで検証した（main取り込み・取り込み先検証済み）。新方式はShogiHome 1.28.2の平手対局一例でTwoPlyMaterial送信と20回のbestmoveを確認した（[実施記録](../learning/two-ply-final-check.md#承認後のshogihome確認実績2026-10-11事後記録)）。他局面・秒読み後の互換性や応答時間上限は未保証。[実施記録](../learning/usi-three-policies.md)を参照する。

## コマンドとエラー

- `usi` はid行、Difficulty option行、`usiok`を順に返し、`isready` は `readyok` を返す。
- `gameover`、未知コマンド、未知の `go` トークンは応答せず読み飛ばす。
- `go` は時計引数を検証し、現在Position.side_to_moveの自分側時計から予算を計算する。期間計算までの接続で、期限判定・探索停止は未実装。0予算でも通常比較を完了して応答する。
- `searchmoves`、`depth`、`nodes`、`mate`、`infinite`、`ponder`、`movetime` は未対応として `ValueError`。有効なpositionがない `go` と、対応外・不正なpositionも `ValueError`。
- 実行入口は入力受付前に同梱JSON設定を一回読む。設定のValueError/OSErrorはstderr診断・終了1、USI入力のValueErrorもstderr診断・終了1。設定読込失敗を代替値で隠さない。USI応答だけをstdoutに書き、各行をflushする。
- `quit` と入力EOFは正常終了する。

## コマンド行の表現

コマンド行は `split()` と既存の文字列分岐で扱う。USIコマンド型や公開状態APIは設けない。非公開状態クラスを独立モジュールやpackage rootから再exportしない。

第59〜62回にShogiHome 1.28.1で平手対局・観察を行った記録は[ShogiHome対局の知識メモ](usi-shogihome-gameplay.md)を参照する。第65回はDifficulty選択画面とMaterial設定のUSI送信を確認し、第66回は同じ7手局面でRandomの☖９四歩、Materialの☖８八角成を実機観察し、両方の設定と着手をUSIログで確認した。これは一局面・各設定一局の実例であり、他局面に対する一般性は示さない。詳細は[第66回学習記録](../learning/66-shogihome-material-move-effect.md)を参照する。

第67回で追加した `position sfen` のコード対応は、第69回にShogiHome 1.28.1からの実通信でも確認した。4欄SFENを画面へ貼り付けた後、時計あり（持ち時間10分・秒読み30秒）の一局で `position sfen ...`、時間付き `go`、`bestmove 9a9b` がログに記録され、盤面にも後手の合法手が反映された。画面貼り付けだけでは通信確認にならない。ShogiHomeは持ち時間と秒読みが両方0の設定を「持ち時間と秒読みが両方とも0です」と拒否したため、時計なし対局はこの版・画面では開始できなかった。実測の範囲と後片付けの制約は[第69回学習記録](../learning/69-shogihome-sfen-engine.md)を参照する。

## 時計受付と設定の寿命

時計ありではbtime/wtimeを両方必須とし、byoyomi省略は0。非負整数ms、重複・値欠落・非整数・負を拒否する。半角十進数字と任意の先頭符号、先頭0を許し、-0は0。binc/wincは0のみ受付、正は未対応。時計項目なし・加算0だけは時計なしNone、byoyomiだけは必須時計不足。未知goトークンを読み飛ばしても後続の既知項目を検査する。

TimeManagementConfigは不変な設定データで、mainが一回読んでrunへ注入する。runの省略時だけ同じloaderで一回読み、全go/usinewgameで保持する。局面やDifficultyの寿命とは分離し、別runでは読み直す。SearchBudgetは期間データで停止操作ではない。時計なしNoneと明示時計の0予算を区別し、後続の探索制御へ渡す境界を準備した。[計画・検証範囲](../plans/2026-10-12-usi-clock-settings-implementation-plan.md)、[実施記録](../learning/usi-clock-settings-implementation-plan.md)。時間内応答・探索中入力受付・stop対応はまだ保証しない。
