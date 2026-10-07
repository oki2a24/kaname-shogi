# 第67回：SFEN局面変換

## 状態

実装・関連テスト・全326テスト・独立コードレビューまで作業ブランチで完了。実装とレビュー対応は3コミットで、本人が内容確認した記録文書は `52deb02` で `feature/sfen-position-conversion` に記録した。`main` への統合、統合先検証、最終理解確認は未実施。ShogiHome実機操作はしていない。

## 目的

将棋局面をSFENから読み込み、正規化して書き出し、USI `position sfen` から受け取った局面へ既存の手適用を接続する。SFENの局面・手数とJSON棋譜の履歴を混同しない。

## 本人が選んだ仕様

- SFENは読込と書出しの両方を実装する。ShogiHomeとの最低限の互換性を目標にする。
- USI `position sfen <SFEN>` 単独と、`position sfen <SFEN> moves <指し手...>` の両方を受け付ける。
- 読み込んだ手数を保持して書き出す。`moves` の各手を適用したらその数を加算する。
- 手数は `Position` ではなくSFEN専用の `SfenPosition` に置く。
- 手数欄の省略を受け付け、値を1とする。書き出しには常に手数を書く。
- 検証は構文と内部モデルでの表現可能性までとし、合法性・実戦到達可能性は検査しない。
- 読込エラーは理由付き `ValueError` とする。
- SFENはJSON棋譜と別形式に保ち、既存JSON構造を変えない。
- 関連unittest、USIエンジン入出力テスト、全テストを実行する。ShogiHome操作は行わない。

## 設計と実装

`kaname_shogi.sfen` に `SfenPosition(position, move_number)`、`parse_sfen`、`format_sfen` を追加した。盤面、手番、持ち駒を内部型へ対応づけ、書き出しでは空きマス、成駒、持ち駒順を正規化する。省略手数は1。玉の有無・二歩・駒総数などの局面合法性は判定しない。

`parse_usi_position` は `startpos` と `sfen` を起点にする結果を `SfenPosition` で返す。SFEN単独はその手数を保ち、指し手列がある場合は既存の `parse_usi_move` と `GameRecord` に再生を委譲して、成功した手数を数える。USIエンジン状態に渡すのは従来どおり `.position` のみ。

入力を大文字化してから確認すると、Unicodeの `ſ` が `S` になって銀として扱われるため、盤面・持ち駒ともASCIIの許可集合を先に照合する。

## レビューを受けた設計修正

初回の独立レビューはCriticalなし、Important 1件、Minor 2件だった。

- Important：持ち駒を枚数分 `Hand.add` すると、SFENで非常に大きな枚数を指定したとき処理が枚数に比例して止まり得る。ユーザーは任意の正の枚数を保つ案として、`Hand.add_many` を追加し計画を更新することを承認した。
- Minor：ASCII以外の駒記号を正規化後に受け入れる問題を、元記号のASCII許可集合チェックで修正した。
- Minor：SFEN起点の不正な手表記・不合法手を、手数・トークン・原因まで直接確かめるテストを追加した。

`Hand.add_many(piece_type, count)` は駒種と1以上の整数枚数を検証し、持ち駒の内部カウントを一度だけ更新する。無効入力時は変更しない。SFEN変換から `Hand._counts` を直接操作せず、通常の将棋枚数へ制限もしない。

修正前のTDD Redでは、`Hand.add_many` が存在せず、巨大枚数の読込テストも `Hand.add` 呼び出しガードにより即時失敗した。実装後、これらを含む3テストがGreenになった。Unicode記号の盤面・持ち駒ケースも修正前はそれぞれ失敗し、修正後に通った。SFEN起点のエラー診断テストは、既存のエラー経路が要件を満たすことを確認した。

同じレビュアーに修正後の差分を再レビューしてもらい、Critical・Important・Minorはいずれもなし。レビュー自体は静的確認で、テスト実行は担当者が行った。

## 一次資料と比較資料

- [USI原案](https://hgm.nubati.net/usi.html)：SFEN欄、USI `position` コマンドの構造。
- [ShogiHome公式Issue #1115](https://github.com/sunfish-shogi/shogihome/issues/1115)：ShogiHomeのGUIへ貼り付けるSFENで手数欄を省略できる件。USI通信上の形式根拠とは区別した。
- [YaneuraOu `position.cpp`](https://github.com/yaneurao/YaneuraOu/blob/master/source/position.cpp)、[cshogi `Engine.py`](https://github.com/TadaoYamaoka/cshogi/blob/master/cshogi/usi/Engine.py)：別の将棋ソフトでの実装比較。
- 現在の仕様とAPIの詳細は[SFEN局面表記の知識メモ](../knowledge/sfen-position-notation.md)を参照する。

## 確認結果

- `test_sfen.py`：10テスト成功。
- `test_model.py`：27テスト成功。
- `test_usi_position.py`：14テスト成功。
- `test_usi_engine.py`：25テスト成功。
- 全体：`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`、326テスト成功。
- `git diff --check`：成功。
- ShogiHomeの画面、SFEN貼り付け、エンジン接続は未確認。最低限の互換性目標を実機検証済みとは扱わない。

## Refactorと振り返り

Refactorの要否を見直した。SFEN文字列変換は `sfen.py`、USI一手表記は `usi_move.py`、合法手適用は `GameRecord`、エンジン状態は `Position` のままで責務が分かれている。一括加算は既存の `Hand` 検証境界を守るために必要な小さな追加で、別のSFEN用駒台表現や内部辞書への直書きは導入しなかった。

レビューを早めに行ったことで、表記の厳密さだけでなく、大きな入力でUSIの処理が止まる経路も検討できた。設計で「モデルで表現可能な値は受け付ける」と決める際は、値域だけでなく、その値を処理する計算量も確認する必要がある。

## 最終理解確認

`main` への統合承認と統合先検証の後に一問だけ出す。本人の回答とアシスタント補足は、回答後に追記する。現時点では未実施。

## 次回への問い

本人は2026-10-07にこの記録と知識メモの内容を確認し、文書コミットを承認した。文書は `52deb02` で記録済み。次は別途 `main` へ取り込むか確認し、承認された場合だけ統合・検証する。
