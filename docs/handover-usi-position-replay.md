# 第56回「USIの平手手順から局面を再現する」開始時点の引き継ぎ

## 最終目標

手元のMacのShogiHomeデスクトップ版から `kaname-shogi` を使い、平手で人間と対局できるようにする。本人が選んだロードマップ第3小テーマは「USIの平手手順から局面を再現する」。この引き継ぎは新しいセッションで調査と設計を始めるための背景であり、テーマのAPI・変換境界・エラー方針・実装方式を決定するものではない。

## 選定理由とテーマの位置づけ

本人は、第55回「USIの指し手表記と内部の一手の対応」を終えた後、ロードマップ第3項を次テーマに選んだ。USIの一手トークンと内部 `Move` 値の対応を使い、平手の初期局面から指し手列を順に適用して局面を再現することがロードマップ上の到達点である。USI標準入出力の対局ループやShogiHomeとの実対局は後続テーマにある。

第55回では `kaname_shogi.usi_move.parse_usi_move` / `format_usi_move` による一手単位の相互変換が実装済みである。変換は局面を参照せず、合法性を判定しない。第56回では局面手順を読む際に既存の合法手適用とどうつなぐかを調べるが、具体的な設計や扱う入力範囲はまだ合意していない。

## 第54回の実機観測と証拠の限界

第54回にShogiHome 1.28.1で、平手・人間先手・使い捨てプローブ後手の対局を観測した。人間の初手後に届いた局面通知は次の一例である。

```text
position startpos moves 7g7f
```

その後の時間付き `go`、プローブからの `bestmove resign`、ShogiHomeからの `gameover lose` / `quit` も記録されている。これは一回の実機観測例である。複数手の履歴、成り、駒打ち、`position sfen`、違法手に対するShogiHomeの動作は観測していない。USIの一般文法や未観測の挙動をこの例から推測しない。詳細は[第54回学習記録](learning/54-usi-shogihome-connection-scope.md)を参照する。

## 第55回で確定した既存境界

- `kaname_shogi.usi_move.parse_usi_move(text)` はUSI一手トークンから `BoardMove` / `DropMove` を作る。
- `kaname_shogi.usi_move.format_usi_move(move)` はこれらの内部値をUSI一手トークンにする。
- `7g7f` は `BoardMove(Square(7, 7), Square(7, 6), False)` に対応する。
- 変換処理は駒の動き、局面上の駒、手番、成りの可否、持ち駒、合法性を判定しない。
- 一手表記の文法・座標と確定仕様は[知識メモ](knowledge/usi-move-notation.md)、判断と実装の経緯は[第55回学習記録](learning/55-usi-move-notation.md)、レビュー済み設計は[第55回設計仕様](plans/2026-10-02-usi-move-notation-design.md)を参照する。

## 既存コードを調べる入口

再開時に現在の実装を直接読み、次の境界を確認する。以下は調査入口であり、第56回の実装方式を先取りしない。

- `kaname_shogi/usi_move.py` — USI一手トークンの解析・形式化関数。
- `kaname_shogi/move.py` — `BoardMove` / `DropMove` / `Move` の値型。
- `kaname_shogi/model.py` — `Square`、`Position`、`BasicPieceType` などのモデル。
- `kaname_shogi/game_record.py` — `GameRecord.apply_move` / `apply_drop` と `position_at(move_count)`。開始局面と成功手履歴を保持し、履歴を再適用して局面を取得する既存機能。
- `kaname_shogi/movegen.py` — `apply_move` / `apply_drop` と合法性検査を行う局面操作。
- `tests/test_usi_move.py`、`tests/test_game_record.py`、`tests/test_movegen.py` — 一手変換、棋譜再現、局面適用の既存確認。

現状では専用JSONの `GameRecord` 読込や `position_at` に既存の履歴再適用がある。USIの `position` 手順を新たにどう表現するか、既存APIをどう使うか、別の境界を設けるかは未決定であり、設計対話で確認する。

## 未決定事項と後続テーマとの境界

次の項目は新しいセッションで一次資料と既存コードを確認し、必要な範囲だけ一問ずつ決める。

- 読み取るUSI入力の範囲。平手 `position startpos moves ...` だけにするか、`position` 文法のどこまでを対象にするか。
- 空の手順、複数手、不正なトークン、局面上で不合法な手がある場合の振る舞い・エラー表現。
- 局面再現を公開する場所、引数と戻り値、既存の `GameRecord` や局面適用APIとの接続。
- 単体テストの対象ケース、確認コマンド、学習記録・知識メモの要否と置き場所。
- 必要と判断された場合に限り、ShogiHome実機での追加確認をどこで行うか。

ロードマップでは、最初のShogiHome平手対局で `position sfen` を受け取る必要が分かった場合、SFEN入力を別テーマとして追加してから進める。第54回では `position sfen` を観測していないので、現時点で対象に含めると決めない。標準入出力コマンドループ、`go` / `bestmove`、手の選択、ShogiHome上の実対局も後続テーマであり、今回の設計時に必要性を確認せず先取りしない。

## USI資料を確認する入口

- [The Universal Shogi Interface (USI), original description](https://hgm.nubati.net/usi.html) — USI原案。次セッションで `position` と `startpos` / `moves` の文法を直接確認する。
- [将棋所：USIプロトコルとは](https://shogidokoro2.stars.ne.jp/usi.html) — 日本語でのプロトコル・局面通知の説明。必要なコマンド範囲と用語を照合する。

資料に書かれたプロトコル文法と、ShogiHomeで実際に観測した挙動は証拠を分けて記録する。資料を確認する前にこの引き継ぎから細かな構文規則を補わない。

## 再開時に読む資料

1. `git status --short --branch` と `git log -3 --oneline` の現在結果を確認する。
2. `AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、本書、`docs/roadmap-usi-shogihome.md`、`docs/learning/54-usi-shogihome-connection-scope.md`、`docs/learning/55-usi-move-notation.md`、`docs/knowledge/usi-move-notation.md`、`docs/02-project-direction.md` を読む。
3. 上記の `usi_move.py`、`move.py`、`model.py`、`game_record.py`、`movegen.py` と対応テストを調べる。
4. `superpowerssuperpowers:brainstorming` を使い、USIの一次資料で `position startpos moves ...` の文法を確認する。第54回の `7g7f` は実機の一例として扱い、未観測の規則・ShogiHomeの挙動を推測しない。
5. 対象範囲・表現・検証・記録方法を一問ずつ確認し、設計案を提示する。明示的な設計承認を待つ。実装計画を別文書にする場合は、計画への明示的な承認も待つ。承認前にコード・テストを変更しない。

## 開始時の物理状態

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`
- この引き継ぎの作成開始時：ブランチ `codex/usi-shogihome-connection-scope`、HEAD `424d743 docs: 第55回の記録状態を確定する`、作業ツリー clean。
- 同時点の `main`：`41b69a4 docs: ShogiHome対局ロードマップと引き継ぎを記録する`。第55回の実装は現在の作業ブランチに取り込み済みで、`main` にはまだ取り込まれていない。
- 作成開始時点で最後に確認された全テスト結果：257件成功。新セッションでは実装作業を始める前に必要な状態確認を行い、古い結果を現在の証拠とみなさない。
- Git状態、テスト件数、ShogiHome環境はこの引き継ぎ作成時点の記録である。次セッションで必ず再確認する。

## 再開用プロンプト

> kaname-shogi の第56回テーマ「USIの平手手順から局面を再現する」を始めてください。最初に `git status --short --branch` と `git log -3 --oneline` で現在状態を確認し、`AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/handover-usi-position-replay.md`、`docs/roadmap-usi-shogihome.md`、`docs/learning/54-usi-shogihome-connection-scope.md`、`docs/learning/55-usi-move-notation.md`、`docs/knowledge/usi-move-notation.md`、`docs/02-project-direction.md` を読んでください。`kaname_shogi/usi_move.py` の一手変換、`kaname_shogi/move.py` と `model.py` の値型、`kaname_shogi/game_record.py` の `GameRecord` / `position_at`、`kaname_shogi/movegen.py` の局面適用と対応する既存テストを確認してください。ShogiHomeで `kaname-shogi` と平手対局する大テーマの第3小テーマとして、ロードマップ第3項の「USIの平手手順から局面を再現する」に取り組みます。第54回の実機例は `position startpos moves 7g7f` の一つだけです。未観測の複数手、成り、駒打ち、`position sfen` や不正手順時のShogiHomeの挙動をその例から推測しないでください。まず `superpowerssuperpowers:brainstorming` を使い、[USI原案](https://hgm.nubati.net/usi.html) と[将棋所の説明](https://shogidokoro2.stars.ne.jp/usi.html)で `position` 文法を確認してから、このプロジェクトの局面履歴・合法手適用と照合してください。対象範囲、APIやデータ表現、エラー表現、確認方法、記録方法は未決定なので、一問ずつ確認して設計案を提示し、明示的な承認を待ってください。設計承認前はコード・テストを変更しないでください。独立した実装計画を作る場合も、計画を提示して明示的な承認を待ってください。実装が承認された場合は `AGENTS.md` に従い、目的が分かる作業ブランチ、TDD、Refactor判断、独立コードレビュー、検証、学習記録、必要な日本語Conventional Commitを進めてください。
