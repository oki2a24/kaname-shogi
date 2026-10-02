# 第57回「USIエンジンとして一手を返す」開始時点の引き継ぎ

作成日：2026-10-02。第56回完了後に選ばれた次テーマを、新しいセッションで設計から始めるための記録である。これは実装仕様・実装計画ではない。

## 大テーマと選定理由

大テーマは、手元のMacでShogiHomeを使い、息子が盤面から着手して `kaname-shogi` と平手対局できるようにすること。ロードマップ第1〜3項で、接続範囲の実機確認、USI一手表記の変換、平手手順からの局面再現を完了した。本人は次にロードマップ第4項 **「USIエンジンとして一手を返す」** を選び、新しいセッションの準備を依頼した。

本テーマは、既存のUSI変換・局面再現・合法手選択を、USIエンジンとして一手を返す処理へどうつなぐかを学ぶ段階である。ShogiHomeから `kaname-shogi` 自身へ合法な応手を返す実対局はまだ行っていない。第5項「ShogiHomeから実際に対局する」は後続テーマである。

## 完了済みの前提

- 第54回：Mac版ShogiHome 1.28.1と使い捨てプローブの接続範囲を確認した。実機では `usi`、`setoption name USI_Hash value 32`、`setoption name USI_Ponder value true`、`isready` / `readyok`、`usinewgame` を観測した。人間が７六歩を指した後に `position startpos moves 7g7f` と時間付き `go` が届き、プローブの `bestmove resign` に対して `gameover lose`、`quit` が届いた。
- 第56回の設計時には通常手の複数手履歴も観測した。例は `position startpos moves 7g7f 3c3d 2g2f`。これはその実機対局の観測であり、成り・駒打ち・SFEN・不正入力・先読み停止系などの挙動は確認していない。
- 第55回：`kaname_shogi.usi_move.parse_usi_move` はUSIの一手トークン一つを `BoardMove` / `DropMove` へ変換し、`format_usi_move` は逆変換する。どちらも局面や合法性を判定しない。
- 第56回：`kaname_shogi.usi_position.parse_usi_position` は `position startpos moves ...` コマンド全体を解析し、各手を `parse_usi_move` へ渡す。`GameRecord.apply_move` / `apply_drop` が手順の再生中に合法性を検証する。平手初期局面から最後の `Position` を返す。`position sfen ...` は未対応。
- `kaname_shogi.movegen.legal_moves(position)` は合法手一覧を返し、`choose_weak_move(moves, rng)` は一覧から一手を選ぶ。CLIには弱い選択器の利用例がある。次テーマでは現行実装を読み直し、どの境界を再利用するかを設計対話で決める。

資料の詳しい記録は[第54回](learning/54-usi-shogihome-connection-scope.md)、[第55回](learning/55-usi-move-notation.md)、[第56回](learning/56-usi-position-replay.md)、[USI一手表記の知識メモ](knowledge/usi-move-notation.md)、[平手局面再現の知識メモ](knowledge/usi-position-replay.md)、[ロードマップ](roadmap-usi-shogihome.md)を参照する。

## 未決定事項

次の項目は選択肢を列挙しただけで、合意・設計済みではない。一次資料と現行コードを確認した上で、一問ずつ確認する。

- ロードマップ第4項には大まかな到達条件が記載されているが、ロードマップ自体は設計仕様ではない。今回の実装範囲としては未承認なので、着手時に照合して確認する。
- どのUSIコマンドを本テーマで扱い、どこまでの対局ループを到達点にするか。既知の実機観測は上記のとおりで、未観測のコマンド挙動を推測しない。
- プロトコル処理・エンジン処理・実行入口をどのモジュールや関数で公開するか。既存CLIを変更・共用するかも未決定。
- `go` に対して一手を選び、USI文字列で返すまでのデータの流れ、合法手がない場合の扱い、終了通知など。
- 標準入力の読み取り、標準出力のプロトコル専用化、改行・flush、診断出力の扱いと、それをどう確認するか。
- 既存の乱数選択器を使う場合の乱数生成器の寿命・注入境界・テスト可能性。
- `position sfen`、`stop` / ponder、時間制御、探索・評価、対局終了後の振る舞いを本テーマに含めるか。必要性の根拠を確かめるまで先取りしない。
- エラー表現、確認コマンド・テスト範囲、手動での標準入出力確認、記録の構成と承認手順。

## 再開時の物理状態

- 作業ディレクトリ：`/Users/oki2a24/kaname-shogi`
- 引き継ぎ文書作成開始時に確認した状態：ブランチ `main`、HEAD `d2453ba docs: 第56回完了後の現在地と次候補を記録する`、作業ツリー clean、`origin/main` より11コミット先行。リモートへpushしていない。
- 第56回の実装 `a273aac` と理解確認記録 `17957af` はローカル `main` に含まれる。
- 第56回のmain取り込み後に全264テストが成功した。引き継ぎ文書作成では文書だけを編集し、今回テストは実行していない。新セッションでコードへ変更を加える場合は、古い成功結果を現在の検証として扱わない。
- 第57回の学習記録、設計仕様、実装計画、コード、テストはまだ作成・変更していない。
- 新セッションでは必ず `git status --short --branch` と `git log -3 --oneline` を再実行する。

## 新セッションの最初の作業

1. Git状態と直近コミットを再確認する。
2. `AGENTS.md`、README、文書索引、再開案内、本書、次テーマ選定履歴、USI接続ロードマップ、第54〜56回学習記録、関連知識メモ、プロジェクト方向性を読む。
3. `usi_move.py`、`usi_position.py`、`movegen.py`、`game_record.py`、`cli.py` と起動入口、および対応する既存テストを読む。
4. `superpowerssuperpowers:brainstorming` を使う。[USI原案](https://hgm.nubati.net/usi.html)などの一次資料を確認し、標準仕様、ShogiHome実機で確認した内容、未確認の挙動を分ける。
5. 対象範囲・表現・検証・記録方法を一問ずつ相談し、設計案を提示して本人の明示的な承認を待つ。独立した実装計画を作る場合は、その計画も提示して明示的な承認を待つ。
6. 必要な承認前はコード、テスト、局面再生、指し手変換、USI対局ループを変更しない。承認後は `AGENTS.md` のブランチ、TDD、Refactor判断、独立レビュー、検証、記録、コミット方針に従う。

## 再開用プロンプト

次の文を新しいセッションへ入力する。入力されるまで第57回の調査・設計・実装を開始しない。

> kaname-shogi の第57回テーマ「USIエンジンとして一手を返す」を始めてください。最初に `git status --short --branch` と `git log -3 --oneline` で現在状態を確認し、`AGENTS.md`、`README.md`、`docs/README.md`、`docs/resume.md`、`docs/next-topics.md`、`docs/handover-usi-engine-response.md`、`docs/roadmap-usi-shogihome.md`、`docs/learning/54-usi-shogihome-connection-scope.md`、`docs/learning/55-usi-move-notation.md`、`docs/learning/56-usi-position-replay.md`、`docs/knowledge/usi-move-notation.md`、`docs/knowledge/usi-position-replay.md`、`docs/02-project-direction.md` を読んでください。`kaname_shogi/usi_move.py`、`kaname_shogi/usi_position.py`、`kaname_shogi/movegen.py` の `legal_moves` / `choose_weak_move`、`kaname_shogi/game_record.py`、`kaname_shogi/cli.py` と起動入口、これらに対応する既存テストを調べてください。ShogiHomeで `kaname-shogi` と平手対局する大テーマの途中として、USIエンジンが一手を返す境界を扱います。第54回に使い捨てプローブで観測したコマンド・応答と、USI一次資料の仕様と、まだ未確認のShogiHome挙動を区別してください。仕様や実機一例から未確認の実装要件を推測しないでください。`superpowerssuperpowers:brainstorming` を使い、USI一次資料と既存コードを確認した後、対象範囲・表現・検証方法・記録方法を一問ずつ確認し、設計案を提示してください。コマンド範囲、公開境界、標準入出力、合法手がない場合、乱数選択の扱いなどは未決定です。設計案への明示的承認を待ってください。実装計画を作る場合も提示後に明示的な承認を待ち、承認前に指し手変換、局面再現、対局ループの実装やテスト変更を始めないでください。承認後は `AGENTS.md` に従い、目的が分かる作業ブランチ、TDD、Refactor判断、独立レビュー、日本語の学習・確定知識の記録、検証を進めてください。ShogiHomeでの実対局はロードマップ第5項の後続テーマとして扱い、本テーマの設計で確認範囲を決めてください。
