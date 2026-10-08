# 第70回：SFEN手数欄が `4` から `1` になった理由を調べる

調査日：2026-10-08。これは調査・理解確認後に整理した記録であり、実装計画ではない。

## 目的と合意した範囲

第69回の入力SFENの手数 `4` と、ShogiHomeが送ったUSI `position sfen` の手数 `1` の差について、変化する段階と理由を根拠に沿って説明する。画面への入力、内部の局面・棋譜、USI文字列生成、エンジン受信を区別する。

本人が再開用プロンプトを入力した後、`brainstorming` のSpikeとして読み取り専用調査案を提示し、本人の「良い」を受けて調査した。`roadmap-management` を使い、文脈確認、調査案の承認、調査・報告をチャットで追跡した。リポジトリへの進捗管理ファイル作成は調査範囲に含めなかった。

- 第69回の既存ログ原本の当該セッション・関連行、現行コード・既存テストの記述、知識メモを読む。
- ShogiHome公式資料・公式ソースは1.28.1に対応する版を優先し、依存ライブラリの版を照合する。
- GREEN条件は、変化する段階と理由を出典付きで説明すること。確定できなければ不足する証拠と追加確認案を示す。
- ShogiHome画面操作、エンジン起動、追加USIログ採取、設定変更、棋譜の保存・破棄・再起動、コード・テスト変更は行わない。
- 調査結果と理解確認の報告後、学習記録・SFEN知識メモ・文書索引・再開案内の更新案を提示し、本人の「良い」を受けて文書更新を開始した。更新内容と文書検証結果を提示した後、本人の「良い」を受けて4文書のコミット承認を得た。

## 開始時の物理状態

作業ディレクトリは `/Users/oki2a24/kaname-shogi`。最初に `git status --short --branch` と `git log -3 --oneline` を実行した。

```text
## main...origin/main [ahead 3]
d6dcfc2 docs: 第70回SFEN手数差を引き継ぐ
e4b9f53 docs: 第69回SFENエンジン連携を引き継ぐ
5afb40b docs: 第68回SFEN貼り付け確認を記録
```

作業ツリーはクリーンだった。過去の全326テスト成功は第67回の実装統合時点の記録であり、今回の実行結果とは扱わない。

## 確定した観測事実

第69回の入力は次の4欄SFENだった。入力内容は第69回学習記録に基づき、今回あらためて貼り付けてはいない。

```text
lnsgkgsnl/1r5b1/pppppp1pp/6p2/9/2P4P1/PP1PPPP1P/1B5R1/LNSGKGSNL w - 4
```

ログ原本 `/Users/oki2a24/Library/Logs/electron-shogi/usi-20261008_192440.log` の当該セッション `sid=1` では、13〜15行に次の順序が記録されていた。今回も当該通信周辺だけを読み、ログ原本を変更・共有・削除していない。

```text
> position sfen lnsgkgsnl/1r5b1/pppppp1pp/6p2/9/2P4P1/PP1PPPP1P/1B5R1/LNSGKGSNL w - 1
> go btime 600000 wtime 600000 byoyomi 30000
< bestmove 9a9b
```

エンジン応答前の送信文字列がすでに `1` である。第69回の画面・棋譜では後手の９二香が一手目として反映された。今回、現行画面・版・登録先・棋譜・セッション状態は確認していない。

## 公式ソースで確認した経路

ShogiHomeの[v1.28.1リリース](https://github.com/sunfish-shogi/shogihome/releases/tag/v1.28.1)と公式GitHub APIから、対応コミット `24960d39d0557e0109cb48e608d5e62a6cd48dd7` を確認した。その版の[package-lock.json](https://github.com/sunfish-shogi/shogihome/blob/24960d39d0557e0109cb48e608d5e62a6cd48dd7/package-lock.json#L16416)は `tsshogi` を2.3.4に固定している。公式タグv2.3.4の対応コミットは `bec83166c011eb662ee963f04ddb3fe2eb584c99` だった。ソース取得・展開は `/private/tmp` で行い、インストールや実行はしていない。

| 段階 | 確認した処理と手数の扱い | 出典 |
| --- | --- | --- |
| 貼り付けの取込 | `pasteRecord`（貼り付け棋譜を取り込む操作）は入力を `importRecord`（棋譜を読み込む操作）へ渡す。裸のSFENは形式判定でSFENとして扱う。 | [ShogiHome store](https://github.com/sunfish-shogi/shogihome/blob/24960d39d0557e0109cb48e608d5e62a6cd48dd7/src/renderer/store/index.ts#L1332)、[tsshogi形式判定](https://github.com/sunfish-shogi/tsshogi/blob/bec83166c011eb662ee963f04ddb3fe2eb584c99/src/detect.ts#L19) |
| 局面の生成 | `Position` は局面を表すデータ。`newBySFEN`（SFENから局面データを生成する操作）は `resetBySFEN`（SFENから局面を設定する操作）を呼ぶ。4欄目を検証するが、保存するのは盤面・手番・持ち駒であり、手数 `4` は保存しない。 | [Positionの読込・検証・生成](https://github.com/sunfish-shogi/tsshogi/blob/bec83166c011eb662ee963f04ddb3fe2eb584c99/src/position.ts#L605) |
| 新しい棋譜の生成 | ShogiHomeは局面を `new Record(position)` へ渡す。`Record` は棋譜を表すデータで、その局面を開始局面として複製し、開始ノードの `ply`（棋譜内の手数データ）を0にする。過去3手の履歴を生成する処理ではない。 | [ShogiHome読込分岐](https://github.com/sunfish-shogi/shogihome/blob/24960d39d0557e0109cb48e608d5e62a6cd48dd7/src/renderer/record/manager.ts#L229)、[Record生成](https://github.com/sunfish-shogi/tsshogi/blob/bec83166c011eb662ee963f04ddb3fe2eb584c99/src/record.ts#L436)、[開始ノード](https://github.com/sunfish-shogi/tsshogi/blob/bec83166c011eb662ee963f04ddb3fe2eb584c99/src/record.ts#L347) |
| SFEN・USIの生成 | `Position.sfen` はSFEN文字列を返す参照口であり、`getSFEN(1)`（手数を指定してSFENを生成する操作）を呼ぶ。`Record.getUSI`（棋譜からUSI文字列を生成する操作）は `initialPosition.sfen` を使うため、開始局面の手数欄は `1` になる。履歴がなければ `moves` は付けない。 | [SFEN生成](https://github.com/sunfish-shogi/tsshogi/blob/bec83166c011eb662ee963f04ddb3fe2eb584c99/src/position.ts#L586)、[USI生成](https://github.com/sunfish-shogi/tsshogi/blob/bec83166c011eb662ee963f04ddb3fe2eb584c99/src/record.ts#L1099) |
| USIの送信 | 対局処理は `record.usi` をプレイヤーへ渡す。プレイヤーはAPIへ送り、バックグラウンドのエンジン処理は渡された `position` 文字列を送信する。 | [対局処理](https://github.com/sunfish-shogi/shogihome/blob/24960d39d0557e0109cb48e608d5e62a6cd48dd7/src/renderer/game/game.ts#L334)、[プレイヤー](https://github.com/sunfish-shogi/shogihome/blob/24960d39d0557e0109cb48e608d5e62a6cd48dd7/src/renderer/players/usi.ts#L99)、[送信](https://github.com/sunfish-shogi/shogihome/blob/24960d39d0557e0109cb48e608d5e62a6cd48dd7/src/background/usi/engine.ts#L604) |

`Record.sfen`（現在局面のSFENを返す参照口）は `current.ply + 1` を指定するが、USI生成が使うのは `initialPosition.sfen` である。この二つを混同しない。

## 現行kaname-shogiとの境界

`parse_sfen`（SFENを解析する操作）は、入力の4欄目を `SfenPosition.move_number`（SFEN手数データ）に保持する。`parse_usi_position`（USI局面コマンドを解析する操作）もその値を保持し、`moves` があれば指し手数を加える。既存テストにも手数17の維持・手数19への加算を確認する記述があるが、今回はテストを実行していない。

`run_usi_engine`（USIコマンドを処理する操作）は解析結果の `.position` だけを探索状態へ渡す。これは受信後の責務分離であり、ShogiHomeの送信文字列上ですでに `1` だった理由ではない。

参照：[SFEN実装](../../kaname_shogi/sfen.py)、[USI局面実装](../../kaname_shogi/usi_position.py)、[エンジン実装](../../kaname_shogi/usi_engine.py)、[既存局面テスト](../../tests/test_usi_position.py)。

## 結論・仮説・限界

公式1.28.1の処理経路では、入力手数 `4` は局面読込時に保持されず、USI出力時に開始局面のSFENへ `1` が付けられる。この経路は第69回の送信ログと、貼り付け後の後手の着手が棋譜の一手目になった観察に一致する。「3手後の盤面を新しい棋譜の開始局面として扱う」ことが実装上の理由であり、平手の初期配置へ盤面を戻す処理ではない。

調査前は、貼り付け時・棋譜取込時・USI生成時のいずれかで値を置き換える可能性を仮説として扱った。ソース確認後は「読込で手数を保存しないこと」と「出力で1を付けること」を分けて説明できるようになった。

作者がこの方式を選んだ設計意図や、当時のインストール済みアプリが公式ソースと完全に同一だったこと、当時の実行中の内部状態は確認していない。他版・他形式の一般的な手数保持の保証や、不具合だという判断へは広げない。今回の完了条件には追加実機操作を必要としない。

## 理解確認

質問1：「SFENの手数 `4` が保持されなかったことと、盤面が初期配置へ戻ることは、なぜ別の話なのでしょうか。」

本人の最初の回答：「盤面が初期配置へ戻ることにより手数が１に戻るためSFENの手数は関係なくなる」

アシスタントの補足：今回は盤面が平手初期配置へ戻ったわけではない。７六・２六の先手歩、３四の後手歩がある3手後の盤面のまま、その盤面を新しい棋譜の開始局面として扱った。盤面・手番・持ち駒は読み込むが、入力手数 `4` は保持せず、USI出力では `1` を付ける。「開始局面」は、その棋譜の出発点を意味する。最初の回答は正解として扱わない。

質問2：「今回、入力から保たれた情報と、保持されなかった情報は、それぞれ何でしょうか。」

本人の再回答：「局面が保たれた。手数は保持されなかった」

アシスタントの補足：盤面・手番・持ち駒は保たれ、入力の手数 `4` は保持されなかった。その区別を再回答で確認できた。

## 振り返りと次回への問い

局面の内容と棋譜内の手数は別の情報であり、「平手初期配置」と「任意の棋譜の開始局面」を区別して理解できた。GUIが表示できたこと、入力の全欄を保持したこと、エンジンへ送ったことは、それぞれ別の確認になる。

本人による記録内容の確認とコミット承認を終えた。次テーマは未選定。記録のコミット後に、README・方向性・次テーマ候補を見直し、小さい順の候補と推薦理由を示す。専用スキルの現行化やSFEN付き指し手履歴の実機確認を今回の承認へ含めない。

## 検証と未実施事項

文書更新後に `git diff --check` を実行し、問題がないことを確認した。更新4文書の相対リンク351件を検査し、存在しない参照先は0件だった。文書の自己確認で索引の表行の区切りを修正した。本人は4文書のコミットを承認済み。コミットの作成結果はGit履歴で確認する。pushは今回の範囲に含めない。

ShogiHome画面操作、アプリやエンジンの起動、追加ログ採取、設定変更、棋譜の保存・破棄、アプリ再起動、コード・テスト変更、テスト実行はしていない。第69回のUSIログOFF保存・再起動保留・未保存結果棋譜は過去の観察であり、現在状態として推定しない。設定がOFFへ反映される前にエンジンを起動せず、棋譜の扱いと再起動は別途具体案と承認が必要である。

## 関連資料

- [第70回開始時点の引き継ぎ](../handover-shogihome-sfen-move-number.md)
- [第69回学習記録](69-shogihome-sfen-engine.md)
- [SFEN局面表記の確定知識](../knowledge/sfen-position-notation.md)
- [再開案内](../resume.md)
