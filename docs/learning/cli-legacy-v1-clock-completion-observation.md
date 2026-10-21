# 時計のない旧v1棋譜を通常CLIで読み、起動時計の補完を一回観察する

## 目的・範囲

2026-10-21、通常CLIを人間対コンピュータ・ランダム方式・10分・30秒で起動し、時計のない旧`kaname-shogi-game-record-v1`を一度読み込んだ。読込時の実端末表示、二手後の盤面と先手人間への復帰、直後の保存JSONにある棋譜と時計を観察した。

対象は一回の手動CLI観察と学習記録まで。製品コード・テスト・設定・承認済み設計・実装計画は変更していない。自動テストは実行していない。最後の理解確認は未回答のため、このテーマはまだ完了扱いにしない。

## 開始時の現物確認

最初に指定された三つのGitコマンドを実行した。

```text
$ git status --short --branch
## main...origin/main [ahead 2]
?? .antigravity/tasks/

$ git log -3 --oneline --decorate
f850f01 (HEAD -> main) docs: select legacy v1 clock observation
0eadcac docs: record CLI load failure observation answer
0500be8 (origin/main, origin/HEAD) docs: prepare CLI load failure observation handoff

$ git branch --show-current
main
```

作業開始時に提示された`AGENTS.md`は現物と一致した。`docs/resume.md`では旧v1観察が未開始、`docs/handover-cli-legacy-v1-clock-completion-observation.md`では今回の範囲と手順が選定済みとして記録されていた。引き継ぎのGit状態は作成時点の記録であり、開始時の実測は上記のとおりだった。既存の未追跡`.antigravity/tasks/`には触れていない。

`.venv/bin/ruff --version`は`ruff 0.16.10`で、`requirements-dev.txt`の`ruff==0.16.10`と一致した。`git config --local --get core.hooksPath`は`.githooks`だった。

READMEのCLI起動・対局・時計・`save` / `load`、[通常対局CLIの知識](../knowledge/32-human-vs-computer-cli.md)、[棋譜保存の知識](../knowledge/30-game-record-file-save.md)、[承認済みCLI時計設計](../plans/2026-10-20-cli-search-time-control-design.md)の旧v1互換と時計補完、[時計つき成功観察](cli-clocked-record-roundtrip.md)、[読込失敗観察](cli-record-load-failure-observation.md)、[学習ロードマップ](../next-topics.md)、[文書更新ガイド](../documentation-guide.md)を読み直した。設計と知識資料では、コンピュータ対局で時計のない旧v1を読む場合は、そのCLIの起動時に選んだ初期時計条件から先後の時計を作り、人間同士では作らないことを確認した。保存後は内側に旧v1棋譜を含むCLIセッションJSONになる。

## 旧v1入力と実行条件

リポジトリ外の一時ディレクトリに、`GameRecord`の標準初期局面へ先手`7七→7六`、後手`3三→3四`を適用して旧v1ファイルを作った。CLI実行前にJSONを読み取り、形式識別子、二手、トップレベルに`clock`キーがないことを確認した。

```text
入力JSON: /var/folders/n4/7_s3s4k55151g86czn9bt7b80000gn/T/kaname-shogi-legacy-v1-clock-observation-lf64tr8r/legacy-no-clock-v1.json
形式: kaname-shogi-game-record-v1
clockキー: なし
履歴: 先手7七→7六、後手3三→3四（いずれも不成）
```

リポジトリ直下から`python3 -m kaname_shogi`を起動した。選択・入力した値は、対局形式`2`（人間対コンピュータ、先手人間）、方針`1`（ランダム）、持ち時間`10`分、秒読み`30`秒。その先手人間の初期手番で、上記ファイルを`load`したのは一回だけである。

## `load`時の実端末出力

以下はPTYから採取した`load`入力から、読込後の入力プロンプトまでの全出力である。この範囲内に省略はない。起動時メニューと読込前の初期盤面は含めていない。

```text
load /var/folders/n4/7_s3s4k55151g86czn9bt7b80000gn/T/kaname-shogi-legacy-v1-clock-observation-lf64tr8r/legacy-no-clock-v1.json
時計情報がないため、対局開始時に選んだ初期値を使用しました。
棋譜を読み込みました。
手番：先手
+：先手、-：後手

後手の持ち駒：なし

    9   8   7   6   5   4   3   2   1
一 -香 -桂 -銀 -金 -玉 -金 -銀 -桂 -香
二  ・ -飛  ・  ・  ・  ・  ・ -角  ・
三 -歩 -歩 -歩 -歩 -歩 -歩  ・ -歩 -歩
四  ・  ・  ・  ・  ・  ・ -歩  ・  ・
五  ・  ・  ・  ・  ・  ・  ・  ・  ・
六  ・  ・ +歩  ・  ・  ・  ・  ・  ・
七 +歩 +歩  ・ +歩 +歩 +歩 +歩 +歩 +歩
八  ・ +角  ・  ・  ・  ・  ・ +飛  ・
九 +香 +桂 +銀 +金 +王 +金 +銀 +桂 +香

先手の持ち駒：なし
指し手を入力してください（例: move 7 7 7 6）:
```

表示文言は実測どおり記録した。盤面では先手歩が7六、後手歩が3四にあり、「手番：先手」と先手向けの指し手入力プロンプトが表示された。CLI画面上には二手の履歴一覧は表示されなかった。履歴の確認には、直後に保存したJSONを使った。

## 直後の保存とJSON照合

読込後にほかの対局操作を挟まず、同じ先手入力中に次を実行した。

```text
save /var/folders/n4/7_s3s4k55151g86czn9bt7b80000gn/T/kaname-shogi-legacy-v1-clock-observation-lf64tr8r/after-load-session.json
棋譜を保存しました。
指し手を入力してください（例: move 7 7 7 6）:
```

保存ファイルの外側形式は`kaname-shogi-cli-session-v1`、外側キーは`format`・`game_record`・`clock`だった。内側の`game_record`全体は、読込前の時計なし旧v1 JSONと一致した（読み取り専用JSON比較`True`）。その内側の形式と履歴、保存された時計の実値は以下のとおり。これは保存JSONからの関係部分の抜粋であり、`initial_position`の40枚の駒配列は省略している。

```json
{
  "format": "kaname-shogi-cli-session-v1",
  "game_record": {
    "format": "kaname-shogi-game-record-v1",
    "moves": [
      {
        "kind": "move",
        "source": {"file": 7, "rank": 7},
        "destination": {"file": 7, "rank": 6},
        "promote": false
      },
      {
        "kind": "move",
        "source": {"file": 3, "rank": 3},
        "destination": {"file": 3, "rank": 4},
        "promote": false
      }
    ]
  },
  "clock": {
    "initial_time_ms": 600000,
    "byoyomi_ms": 30000,
    "sente_remaining_ns": 600000000000,
    "gote_remaining_ns": 600000000000
  }
}
```

`initial_position.side_to_move`は`SENTE`。保存JSONの手順は先手`7七→7六`、後手`3三→3四`で、二手後の先手番と表示された盤面に対応する。時計の初期条件は`600000ms`・`30000ms`、先後の残り時間は両方`600000000000ns`だった。CLI表示の時計補完メッセージと、保存された起動条件・先後の時計値の両方を観察した。

## 確認できたことと限界

- この一回のコンピュータ対局では、時計のない旧v1棋譜の`load`が成功し、端末に時計補完メッセージと棋譜読込成功が表示された。
- 読込後の端末表示は二手後の盤面、先手番、先手人間用の入力プロンプトを示した。画面に履歴一覧は出ず、二手の履歴が保持された根拠は、保存JSONの`game_record`全体が読込前の旧v1と一致したこと。
- 直後の保存では時計なしの旧v1外側形式からCLIセッション形式へ変わり、内側の旧v1棋譜は一致した。時計には起動時の10分・30秒と、先後各`600000000000ns`が保存された。
- 観察は通常CLI一回、旧v1読込一回、直後の保存一回に限る。他の初期条件・対局形式・棋譜、別OS、時計消費を伴うコンピュータ手、全般的な互換性・実時間性能は確認していない。ここでの表示・保存値はこの一回の実測であり、全入力に対する一般保証とはしない。

## 最後の理解確認（2026-10-21）

**確認したいこと:** 旧v1読込後の時計補完を、端末表示と保存値を根拠に説明できるか。

**質問:** 今回、時計のない旧v1棋譜を読み込んだあと、時計がどの値で補われたと判断できる根拠を、端末表示と保存JSONの両方から説明してください。

**本人の回答:**

> 端末には「時計情報がないため、対局開始時に選んだ初期値を使用しました。」と表示
> 保存JSONでは、先後の残り時間はともに `600000000000ns`

**アシスタントの補足:** 回答は端末の実表示と保存JSONの先後別残り値を、それぞれ根拠として挙げている。JSONではこれに加えて初期持ち時間`600000ms`（10分）と秒読み`30000ms`（30秒）が保存されていた。両側の残り時間`600000000000ns`は10分の初期持ち時間に対応する。この一回では時計補完メッセージと保存値が一致した。

本人回答と補足を記録し、この観察テーマを完了した。次テーマは本人指定済みの「ShogiHomeで全幅最大4手・αβ最大4手を実践検証する」。開始背景と再開用プロンプトは[次セッション用の引き継ぎ](../handover-shogihome-four-ply-practice-verification.md)に記録した。ShogiHomeでの操作は次のセッションで開始する。

## 振り返り・次回への問い

旧v1の時計なし棋譜を読み込むとき、端末の補完メッセージだけでなく、読み込んだ二手の履歴と起動条件から作られた時計を、直後に保存したJSONで照合できた。端末表示・履歴JSON・時計JSONはそれぞれ異なる確認材料なので、表示されていない履歴一覧を画面に出たものとして記録しなかった。

## 変更・検証の範囲

通常CLIの実行は一回。旧v1入力と読込後のCLIセッションJSONは、前掲のリポジトリ外一時ディレクトリに保存した。読み取り専用のJSON確認で、旧v1に時計キーがないこと、保存後の内側棋譜全体が旧v1入力と一致すること、二手と時計値を照合した。製品コード・テスト・設定・承認済み設計・実装計画は変更しておらず、自動テストは実行していない。

## 観察開始時のGit状態（2026-10-21）

観察開始時のHEADは`f850f01`で、`main`は`origin/main`より2コミット先行していた。未追跡`.antigravity/tasks/`も観察開始前からあり、この作業では変更していない。
