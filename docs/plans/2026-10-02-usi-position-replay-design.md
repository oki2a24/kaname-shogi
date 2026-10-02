# USI平手手順からの局面再現：設計仕様

## 状態

2026-10-02、本人が設計案全体と別文書の実装計画を承認した。作業ブランチ `codex/usi-position-replay` で実装し、専用7テスト・全体264テストが成功した。Refactorは不要、独立コードレビューはCritical / Important / Minorすべてなし。学習記録・知識メモの確認とコミットは未完了。

## 目的

ShogiHomeで平手対局する大テーマの第3小テーマとして、USIの平手局面コマンド `position startpos moves ...` に含まれる指し手列を先頭から合法手として適用し、現在の `Position` を再現する。

## 根拠と観測範囲

USI原案と将棋所の説明は、`position` で開始局面を指定し、`moves` にその局面からの指し手列を続ける形式を示している。原案の文法には `startpos` と `sfen` の分岐がある。本テーマでは `startpos` だけを実装する。

- [The Universal Shogi Interface (USI), original description](https://hgm.nubati.net/usi.html)
- [将棋所：USIプロトコルとは](https://shogidokoro2.stars.ne.jp/usi.html)

第54回のShogiHome 1.28.1実機観測は `position startpos moves 7g7f` の一例だけだった。その後、本テーマの設計検討中に一時的な記録用エンジンを使って通常手の複数手を確認した。ShogiHomeから届いた `position` は次のとおり。

```text
position startpos moves 7g7f
position startpos moves 7g7f 3c3d 2g2f
```

この観測から確認できるのは、この対局で通常手を含む全手順が2回目のコマンドに含まれたことまでである。ShogiHomeが成り・駒打ち・SFEN・不正手順を送る方法や、その際の挙動は確認していない。USI資料の文法と実機観測は別の証拠として扱う。

## 合意した範囲

### 対象

- 完全な `position startpos moves <move1> ... <moveN>` コマンドを受け付ける。
- `moves` と1手以上の指し手を必須にする。
- 既存の `parse_usi_move` が扱う通常移動・成り・7種類の駒打ちを、複数手順の各トークンとして利用する。
- 平手初期局面から手順を順番に合法適用し、最後の `Position` を返す。
- 文法エラー、指し手変換失敗、不合法手は `ValueError` とし、原因が分かるメッセージを付ける。
- ShogiHome実機で確認した通常手の複数手順と、テストで確認する機能範囲を区別して記録する。

### 対象外

- `position startpos` 単独、および指し手が空の `position startpos moves`
- `position sfen ...` とSFEN解析
- USI入出力ループ、`go` / `bestmove`、手の選択、ShogiHomeとの実対局制御
- 実機で未観測の成り・駒打ち・SFEN・不正手順に対するShogiHomeの挙動確認
- 返却値 `Position` への指し手履歴の追加

## APIと依存関係

新しい `kaname_shogi.usi_position` モジュールで次の関数を公開する。

```python
parse_usi_position(command: str) -> Position
```

この関数はUSIの `position` コマンド全体を受け取り、コマンド種別、開始局面キーワード、`moves`、1手以上のトークン列を検査する。各手の文字列表記は既存の `kaname_shogi.usi_move.parse_usi_move(text)` に委譲する。`parse_usi_move` は一手トークンを `BoardMove` または `DropMove` に変換する下位の部品であり、その既存仕様は変更しない。

再生時は `create_initial_position()` で平手初期局面を作り、そのコピーを内部に保持する `GameRecord` を作る。解析された `BoardMove` は `GameRecord.apply_move`、`DropMove` は `GameRecord.apply_drop` へ渡し、既存の合法手処理へ委譲する。全手成功後に `GameRecord.current_position` が返す独立コピーを返す。失敗時は `ValueError` とし、メッセージは原因を特定できるようにする。固定文言は契約にしない。

`Position` は盤面・手番・先後の持ち駒を表す可変の現在局面であり、履歴を含まない。関数の呼び出し側は受け取ったコマンドを保持できるため、`Position` を返すことは履歴を別途保持する可能性を妨げない。将来、履歴が必要な呼び出し側は入力コマンドまたは `GameRecord` を別に保持する。このAPI自体は履歴や `GameRecord` を返さない。

Move値型、`Position`、`GameRecord`、`movegen`、`kaname_shogi.__init__` は変更しない。`parse_usi_position` はモジュールから直接importできる公開APIとし、package rootから再exportしない。

## 確認方法

新しい `tests/test_usi_position.py` に標準ライブラリ `unittest` の単体テストを追加する。

- 通常手を含む複数手 `position startpos moves 7g7f 3c3d 2g2f` から、駒配置と手番が3手後の局面に一致することを確認する。
- 成りを含む `position startpos moves 7g7f 3c3d 7f7e 3d3e 7e7d 3e3f 7d7c+` から、と金と手番を確認する。
- 捕獲で得た歩を打つ手順 `position startpos moves 1g1f 1c1d 1f1e 1d1e 1i1h 4c4d 1h1e 4d4e P*1d` から、打った歩、持ち駒、手番を確認する。
- `position startpos`、`position startpos moves`、SFEN形式、不正コマンド、不正な一手トークンを `ValueError` として拒否する。
- 平手初期局面で不合法な手 `7g7e` を含むコマンドを `ValueError` として拒否する。
- 既存の `tests/test_usi_move.py` と `tests/test_game_record.py` は変更せず、新しいコマンド境界の責務を専用テストへ置く。

検証コマンドは専用テスト、全テスト、差分検査の順とする。

```bash
python3 -m unittest tests.test_usi_position -v
python3 -m unittest discover -s tests -v
git diff --check
git diff --cached --check
```

ShogiHome実機の通常手複数手の観測記録は、単体テストの成功や未観測の指し手形式に対する互換性の根拠として流用しない。

## 記録と承認手順

- 本書は承認された設計を記録する。個別のテスト名・実装手順・Red/Green・レビュー方法は、別の実装計画で具体化する。
- 実装計画を提示し、本人の明示的な承認を得てからコード・テストを変更する。
- 実装後はRefactorの要否を確認し、独立コードレビューを行う。Critical / Important / Minorの結論と対応を学習記録へ残す。
- 学習経緯、本人の回答と補足、実機観測、実際の実装・検証・レビュー結果・未解決事項は `docs/learning/56-usi-position-replay.md` に記録する。
- 確定した `parse_usi_position` の責務、履歴との関係、エラー境界は `docs/knowledge/usi-position-replay.md` に簡潔に記録する。
- 学習記録・知識メモは本人が内容を確認してから日本語Conventional Commitで記録する。mainへの取り込みはテーマ完了後に別途確認する。

## 実装結果

2026-10-02に `kaname_shogi.usi_position.parse_usi_position(command: str) -> Position` と `tests/test_usi_position.py` を追加した。文法を検査し、各USI一手トークンを `parse_usi_move` に渡し、`GameRecord` の `apply_move` / `apply_drop` で合法適用した。失敗した手の番号とトークンを含む `ValueError` とし、成功時は履歴を含まない独立 `Position` を返す。既存値型・局面履歴・合法手処理は変更していない。

テストを先に作り、一時的な `None` 返却実装に対して7テストを実行した。結果は振る舞いアサーション9件の失敗と2件の例外未送出で、importエラーではなかった。実装後は専用7テスト、全体264テストが成功した。Refactorは責務重複や不要な分岐がないため不要と判断した。

独立コードレビューの結論は **Critical: なし、Important: なし、Minor: なし**。後続手の失敗診断を追加で守る任意テストの提案はあったが、必須変更とはせず保留した。レビュー後にも専用7テスト、全体264テスト、および `git diff --check` / `git diff --cached --check` が成功した。実装・記録の内容確認およびコミットは未完了で、詳細は[第56回学習記録](../learning/56-usi-position-replay.md)に記す。

## 参照

- [第54回：ShogiHome接続範囲](../learning/54-usi-shogihome-connection-scope.md) — 初回実機観測 `position startpos moves 7g7f`。
- [第55回：USI一手表記](../learning/55-usi-move-notation.md)
- [USI一手表記と内部の一手データ](../knowledge/usi-move-notation.md)
- [ShogiHome対局ロードマップ](../roadmap-usi-shogihome.md)
- [GameRecordと局面適用](../../kaname_shogi/game_record.py)
- [USI一手変換](../../kaname_shogi/usi_move.py)
