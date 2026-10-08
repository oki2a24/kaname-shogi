# 第72回：ルートREADMEの古いSFEN説明を直す

実施日：2026-10-08。この記録はチャットの具体案承認と文書更新後に整理した実施記録であり、独立した実装計画ではない。検証・レビュー・統合・理解確認の状態は実施に応じて追記する。

## 目的・合意した範囲

入口となるルートREADMEのSFEN連携未確認・第69回予定という古い説明を、現行の対応範囲と実測の限界にそろえる。今回のテーマは文書保守であり、機能追加ではない。

`brainstorming` のBoundedとして、4段落の限定更新、表現、確認方法、独立レビュー方法をチャットに提示した。本人の「良い」を受けて開始した。`roadmap-management` で根拠確認、具体案承認、更新・検証・独立レビューの現在地とGREEN条件をチャットで追跡した。独立した仕様書・実装計画・進捗ファイルは作成していない。GREEN条件はREADMEと現行資料の一致、実測を一般化しない表現、文書検証と独立レビューの完了である。

- 対象は[ルートREADME](../../README.md)、本書、[文書索引](../README.md)、[再開案内](../resume.md)の4文書。学習記録・索引・再開案内の更新も具体案に含めて承認された。
- 同じディレクトリの作業ブランチで更新し、内容提示後にコミットする。mainへの取り込みは別途明示承認を待つ。pushは含めない。
- ShogiHome操作、エンジン起動、対局、追加ログ、設定変更、棋譜保存・破棄、再起動、コード・テスト変更は行わない。製品テストも実行しない。

## 開始時と作業場所

最初に `git status --short --branch` と `git log -3 --oneline` を実行した。

```text
## main...origin/main [ahead 8]
ff7e9ac docs: 第72回READMEのSFEN説明更新を引き継ぐ
1a430cd docs: 第71回のmain統合と文書検証を記録
491596b docs: ShogiHome専用スキルを現行化する
```

作業ツリーはクリーン。作業場所は `/Users/oki2a24/kaname-shogi`。承認後に `git switch -c codex/readme-sfen-update` を実行した。sandbox内では参照作成が失敗したため、同コマンドの許可された実行でブランチを作成した。別worktreeは使わず、この開始時点では元のmainへの取り込みは未実施だった。過去の全326テスト成功は今回の検証結果と扱わない。

## 根拠と履歴の区別

[専用スキル](../../.agents/skills/shogihome-connection/SKILL.md)、[接続手順書](../shogihome-connection-guide.md)、[SFEN知識](../knowledge/sfen-position-notation.md)、[USI応答知識](../knowledge/usi-engine-response.md)、[ShogiHome対局知識](../knowledge/usi-shogihome-gameplay.md)を現行参照資料として確認した。現行 `usi_position.py` は読み取りだけで、startposの1手以上必須、SFEN単独・SFEN＋1手以上、手数保持を照合した。

[第69回](69-shogihome-sfen-engine.md)・[第70回](70-shogihome-sfen-move-number.md)・[第71回](71-shogihome-connection-skill-update.md)と[引き継ぎ](../handover-readme-sfen-update.md)は実測・判断の履歴として読んだ。ルートREADME、索引、再開案内、候補、方向性、USIロードマップも確認した。

現行ShogiHome対局知識・USIロードマップには第70回以前の「手数差の理由は未確認」という記述が残る。その箇所を現在の結論の根拠にはせず、更新済みSFEN知識と公式固定版のソースを照合した。これらの併修は承認範囲へ自動追加しない。

今回[USI原案](https://hgm.nubati.net/usi.html)はWebで取得できた。tsshogiの固定ソースのWeb再取得はCache missで失敗したため、第70回取得物 `/private/tmp/d70-position.ts`、`/private/tmp/d70-record.ts`、`/private/tmp/d70-shogihome-source` を読み直した。残る公式tree JSONのコミット識別子とlockfileの依存版を照合した。今回の新規取得や現在の実機確認とは記録しない。

- [ShogiHomeのSFEN取込](https://github.com/sunfish-shogi/shogihome/blob/24960d39d0557e0109cb48e608d5e62a6cd48dd7/src/renderer/record/manager.ts#L229)は読み込んだ局面から新しい棋譜を生成する。
- [固定依存](https://github.com/sunfish-shogi/shogihome/blob/24960d39d0557e0109cb48e608d5e62a6cd48dd7/package-lock.json#L16416)はtsshogi 2.3.4。
- [局面読込とSFEN生成](https://github.com/sunfish-shogi/tsshogi/blob/bec83166c011eb662ee963f04ddb3fe2eb584c99/src/position.ts#L586)は盤面・手番・持ち駒を保存し、入力手数は保持せず、SFEN参照口で手数1を付ける。
- [USI生成](https://github.com/sunfish-shogi/tsshogi/blob/bec83166c011eb662ee963f04ddb3fe2eb584c99/src/record.ts#L1099)は開始局面のSFENを使う。

## 実際の変更と判断理由

1. 概要の第69回予定・未確認を、第69回の一局面の実測、第70回調査、第71回スキル保守の実施済み履歴へ更新した。
2. 現在できることでは貼り付けとUSI送信・応答を区別した。入力手数4から送信手数1への経路を固定版に限って説明し、盤面・手番・持ち駒が保たれ、平手初期配置への復帰ではないことを明記した。
3. startposは指し手1手以上が必要、SFENは単独または指し手1手以上付きに対応と明記した。SFENの構文・表現可能性検証を任意局面の合法性保証へ広げない。
4. 未対応事項では他版・全局面・SFEN付き履歴の実機互換性を未確認とした。仕様・操作条件は現行知識・手順書・専用スキルへ、実測・調査の経緯は学習記録へ誘導する。
5. 索引に本書の入口を追加し、再開案内の現在地を承認後の作業状態へ更新した。開始前プロンプトは履歴として区別する。

READMEの章構成で説明できるため、追加分割・構成変更は不要と判断した。製品コードのRefactorは今回の範囲外である。

## 検証と独立レビュー

更新後に `git diff --check` を実行し、成功した。対象4文書の相対リンク396件の参照先不存在は0件だった。READMEの古いSFEN未確認・第69回予定の記述がなく、startpos単独未対応・実機互換性の限界・平手初期配置への復帰ではない説明があることも静的に確認した。Gitの差分・未追跡ファイルを確認し、承認対象4文書だけが変更されていることを確かめた。

構成整理の要否確認後、`requesting-code-review` に従い、別サブエージェントが独立レビューした。会話履歴を渡さず、基準HEAD `ff7e9ac`、変更文書、要件、直接の現行根拠を与えた。

- Critical：0件。対応不要。
- Important：0件。対応不要。
- Minor：0件。対応不要。

レビューは対応形式と現行コード、実測の限界、固定版公式ソースによる手数境界、現在作業と履歴の区別、時計・ログ・承認範囲の整合を確認した。レビュアーも読み取りだけを行い、実機操作・エンジン起動・製品テストは行っていない。構成変更や修正の推奨はなかった。

追記後の差分検査と相対リンク396件の確認（参照先不存在0件）も成功し、内容を本人へ提示した。本人は4文書のコミット・main取り込みを「良い」と承認した。

2026-10-09、`960079f docs: READMEのSFEN対応説明を現行化する` を作成し、同じディレクトリで `git switch main`、`git merge --ff-only codex/readme-sfen-update` を実行した。main取り込み後も `git diff --check` と相対リンク396件の確認が成功し、参照先不存在は0件だった。作業ツリーはクリーン、origin/mainより9コミット先行だった。pushはしていない。本追記は統合後の実施記録であり、製品テストや実機操作は行っていない。最終理解確認への本人回答を次に待つ。

## 理解確認・振り返り・次回への問い

最終理解確認はmainへの取り込みと取り込み先文書検証後に一問だけ出す。現時点では未出題・未回答であり、理解確認済みとは扱わない。次テーマは本人回答と補足を記録してから候補を見直し、本人が選ぶまで開始しない。

## 未実施事項と運用境界

現在のShogiHome画面・版・登録先・棋譜・セッションは確認していない。第69回のログOFF保存・再起動保留は過去の観察であり、現在状態とは推定しない。OFF保存と反映を区別し、OFF反映前に起動しない。棋譜保全・再起動の操作は別途具体案への承認が必要である。

0＋0を時計なし・無制限と扱わず、操作が別途承認された場合も、正の持ち時間または秒読みと本人が合意した具体値を開始前に確認する。10分＋30秒は過去の一回の値であり既定値ではない。今回これらの実機操作はしていない。
