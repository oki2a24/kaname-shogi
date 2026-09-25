# 弱い自動指し手のための合法手列挙と一手選択：参照メモ

更新日：2026-09-25

## 中立な一手データ

- `BoardMove` は出発 `Square`、到着 `Square`、`promote` を持つ変更不可の盤上移動データ。
- `DropMove` は `BasicPieceType` と打ち先 `Square` を持つ変更不可の駒打ちデータ。
- `Move` は上のどちらかを表す型注釈。いずれも局面を変更する操作ではない。
- 実際の適用は `apply_move` / `apply_drop` が担う。棋譜の `RecordedMove` / `RecordedDrop` とは責務を分ける。

定義：[kaname_shogi/move.py](../../kaname_shogi/move.py)

## 合法手一覧

`legal_moves(position)` は、現在実装済みの規則で適用できる `Move` の `tuple` を返す。局面は変更しない。成り、二歩、行き所のない駒、自玉の安全、打ち歩詰めは既存の局面適用を複製局面へ試して判定する。

列挙順は固定で、強さの優先順位ではない。

1. 盤上移動
2. 出発マスは1一から9九
3. 各駒の既存候補順
4. 不成、成り
5. 駒打ち
6. 駒種は飛・角・金・銀・桂・香・歩
7. 各打ち先は1一から9九

`has_legal_move(position)` は `bool(legal_moves(position))` で判定する。打ち歩詰め確認中の内部再帰回避は非公開列挙器の設定で維持する。

## 弱い一手選択

`choose_weak_move(moves, rng)` は、`legal_moves` が返した一覧を再検証せず、注入された `random.Random` で一様に一手を選ぶ。空タプルなら `None` を返す。`None` は「選べる一手がない」という選択器の結果であり、詰み・投了・勝敗・USIの `bestmove resign` を表さない。

## 対象外と申し送り

- CLIの人間対コンピュータ進行
- USI・SFEN・標準入出力通信と外部文字列変換
- 評価、探索、定跡、強さ調整
- `GameRecord` の棋譜型との変換
- 千日手、持将棋、入玉、時間切れ、反則勝敗

一次資料：[日本将棋連盟「対局規則」](https://www.shogi.or.jp/match/taikyoku_rules/)、[日本将棋連盟「反則について」](https://www.shogi.or.jp/knowledge/shogi/05.php)
