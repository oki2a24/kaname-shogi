# 第56回：USIの平手手順から局面を再現する

## 目的

ShogiHomeで `kaname-shogi` と平手対局する大テーマの第3小テーマとして、USIの `position startpos moves ...` を読み、複数の指し手を平手初期局面から合法適用した現在局面を再現する。USI資料の文法、ShogiHome実機で観測した範囲、プロジェクト内の手変換・履歴・合法手適用の責務を区別する。

## 開始時の状態

- 2026-10-02の開始時、作業ブランチは `codex/usi-shogihome-connection-scope`、作業ツリーはclean、HEADは `2257e5e` だった。開始前に `git status --short --branch` と `git log -3 --oneline` を確認した。
- 第55回で `kaname_shogi.usi_move.parse_usi_move` はUSI一手表記を `BoardMove` / `DropMove` に変換するが、盤面依存の合法性は判定しないと整理済み。
- `GameRecord` は現在局面と履歴を管理し、`apply_move` / `apply_drop` は合法手適用を担う。`Position` は盤面・手番・持ち駒を表し、履歴を持たない。
- 本テーマは設計承認後、別に承認された実装計画に従い、作業ブランチ `codex/usi-position-replay` で進めた。

## 資料と実機観測

[USI原案](https://hgm.nubati.net/usi.html) と[将棋所のUSI説明](https://shogidokoro2.stars.ne.jp/usi.html)で、開始局面を `startpos` または `sfen` で指定し、`moves` にその局面以後の手順を続ける `position` の文法を確認した。本テーマでは承認された範囲に従い `startpos` のみを実装し、SFEN解析は対象外とした。

第54回に記録したShogiHome 1.28.1の実機例は `position startpos moves 7g7f` の1件だった。今回の設計確認でShogiHomeを起動し、一時的な記録用エンジンを使って通常手の複数手を追加観測した。先手 `7g7f`、記録用エンジンの後手 `3c3d`、先手 `2g2f` のあとに観測したコマンドは次のとおり。

```text
position startpos moves 7g7f
position startpos moves 7g7f 3c3d 2g2f
```

この対局では、2回目の `position` にそれまでの通常手全体が含まれていた。これは実機観測であり、USI一般の仕様や、成り・駒打ち・SFEN・不正手順時のShogiHomeの挙動を実証したものではない。後者は実機で確認していない。記録用エンジンと一時ファイルは確認後に削除し、ShogiHomeのUSI通信ログ機能は有効にしていない。

## 本人との設計確認

### 対象範囲と手順

**確認：** 今回は `startpos` のみを対象にし、SFENを除外するか。

**本人の回答：** はい。

**補足：** `position sfen ...` の解析は将来の別テーマへ残した。

**確認：** `position startpos` 単独も受け付けて初期局面を返すか、それとも `moves` を必須にするか。

**本人の回答：** 必須にする。

**補足：** 空手順は今回のAPIの成功入力に含めず、`moves` と1手以上を要求する。

### 戻り値と履歴

**本人の質問：** `Position` を返すことで履歴が保持できなくなるのか。

**補足：** `Position` 自体には履歴がないが、受け取ったコマンド全文を呼び出し側で保持できるため、履歴保持の可能性は失われない。この関数自体は `GameRecord` や履歴を返さず、最後の局面だけを返す。

### ShogiHomeから届く手順

**本人の質問・許可：** 呼び出し側はShogiHomeと考えているが、履歴を送るのはオプション等で受け入れるのか。必要なら起動中のShogiHomeを確認してよい。

**補足と確認：** 一時的な記録用エンジンで実機を確認し、通常手の3手目時点のコマンドにも初手からの手順が含まれることを観測した。確認した入力方法は `position startpos moves ...`。他形式や未観測の手に関する結論は出していない。

### エラー・確認方法・API関係

**確認：** 文法・手変換・不合法手を、原因が分かるメッセージ付き `ValueError` にするか。

**本人の回答：** 良い。

**確認：** 複数の合法手を再現する単体テストと、文法・変換・合法性エラーの単体テストを行い、実機確認は観測済みの通常手に限定するか。

**本人の回答：** 良い。

**本人の確認：** `parse_usi_position(command: str) -> Position` と `parse_usi_move` の関係を質問し、説明を受けて「理解した。良い」と回答した。

**補足：** `parse_usi_position` はコマンド文法と複数手の順序を扱い、各手トークンを既存の `parse_usi_move` に委譲する。一手変換後の盤面上の合法性は `GameRecord.apply_move` / `apply_drop` が検査する。既存の一手変換関数の契約は変更しない。

### 記録方法と承認

**確認：** 設計仕様、別途承認する実装計画、第56回学習記録と知識メモという記録方法にするか。

**本人の回答：** よい。

本人は設計案全体を承認し、続いて実装計画を承認した。計画承認後に限ってコードとテストを変更した。学習記録・知識メモの内容は本記録の提示後に確認を受け、承認後にコミットする。

## 実装とテスト

- `kaname_shogi.usi_position.parse_usi_position(command: str) -> Position` を追加した。文法を検査し、平手初期局面を持つ `GameRecord` でトークンを一つずつ合法適用し、独立した現在 `Position` を返す。
- 各トークンは既存の `parse_usi_move` で `BoardMove` / `DropMove` に変換する。`GameRecord.apply_move` / `apply_drop` へ渡し、失敗時は問題の手数とトークンを含む `ValueError` にする。
- `tests/test_usi_position.py` に7件を追加した。通常手の複数手、成り、捕獲駒の打ち、`moves` 必須、SFENや不正コマンド、一手変換失敗、不合法手を確認する。
- TDD Redでは一時的な `None` 返却実装に対して7件を実行し、期待Positionとの不一致9件と、ValueErrorが送出されない例外アサーション失敗2件を確認した。importエラーではなかった。
- Greenでは専用7テストと全体264テストが成功した。Refactorを確認し、責務の重複や不要な分岐はないためコード変更不要と判断した。
- 独立コードレビューの結果は **Critical: なし、Important: なし、Minor: なし**。任意提案として、合法な先行手のあとに不正トークンを置くテストで後続手の診断情報を守る案が出た。必須修正ではないので追加せず保留した。
- レビュー後に専用7テスト、全体264テスト、`git diff --check`、`git diff --cached --check` を再実行し、すべて成功した。

## 判断と未解決事項

- 戻り値の `Position` に履歴を追加しない。履歴が必要な呼び出し側は入力コマンドまたは別の `GameRecord` を保持する。
- `position sfen ...`、`position startpos` 単独、空の `moves`、USI入出力ループ、ShogiHome未観測挙動は今回の対象外。
- 実機で複数手を観測したのは通常手のみ。成り・駒打ち・不正手順のUSI互換性は単体テストによるプロジェクト内検証であり、ShogiHome実機の確認とは区別する。
- 作業ブランチは `codex/usi-position-replay`。実装・テスト・記録のコミットとmainへの取り込みは未実施で、記録の本人確認後に進める。

## 最後の理解確認

実装・記録のコミット後に、最後の理解確認を一問出す。本人の回答と補足は別記し、本人確認を受けてから記録する。この記録はその回答前の草稿である。
\n