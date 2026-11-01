# セッション引き継ぎ：主線の次の非駒得評価項目を選ぶ

作成日：2026-11-01。本人はVの通常CLI・USI接続完了後、提示した候補のうち「主線の継続」を採用した。ここで選ばれたのは、非駒得評価項目を一つ選び、学習・設計する主線テーマである。候補プール内の具体的な評価項目はまだ選んでいない。この引き継ぎは新しいセッションで項目選定を続けるための記録であり、項目の設計、実装計画、TDD、コード・テスト変更、実装を承認したものではない。

## 最終目標

主線「駒得以外の局面評価を一項目ずつ育てる」に戻り、現行の駒得・飛車可動性・玉周辺安全度・U・Vと重複しない可能性のある候補を比較して、本人が次に学ぶ項目を一つ選ぶ。選んだ後に一次資料と現行コードを照合し、改善仮説・独立期待値・代表局面・対象範囲・確認方法を学び設計する。実装計画を提示して明示承認を得るまではTDD、テスト変更、コード変更、実装を開始しない。

ロードマップ上のA/B/C番号は先回りして予約しない。主線を採用したことは具体的な評価項目の選定ではない。

## 完了した事項と意思決定の背景

### 主線と直近の派生テーマ

- 主線A1/B1（飛車可動性）、C1（比較は判断不能で一旦区切り）、A2/B2（玉周辺安全度）、C2（登録4局面の比較）は完了している。C2は指定条件下で悪化を支持し、全局面の棋力を示さない。
- U（支えのない狙われた駒）は実装・比較・通常CLI/USI接続まで完了した。
- V（支えがある駒への低価値駒の利き）は比較CLIへ接続し、確認比較を完了した。事前固定6局面・一手選択・指定条件における候補平均得点の95% Hoeffding区間は `[0.505225, 0.567569]` で、当該範囲の改善を支持した。これは一般局面での棋力向上を示さない。
- その後の派生テーマでV1を通常CLI候補7とUSI `MaterialSupportedPieceThreat` に接続し、実装・検証・独立レビュー・main統合・push・理解確認を完了した。詳細は[Vの学習記録](learning/supported-piece-lower-value-threat.md)、[通常CLI・USI接続設計](plans/2026-11-01-v-normal-cli-usi-design.md)、[実装計画と実績](plans/2026-11-01-v-normal-cli-usi-implementation-plan.md)を参照する。

### 通常CLI CVCの実証と証拠の範囲

先後を入れ替えたCVCを2局行った。両局とも開始前の方式表示、両側の実着手、終局（後手投了・先手勝ち）を確認した。本人は「その前のエンジンと同等の棋力がありそうに見えることが言える、実際に棋力が向上したとは言えない」と回答した。「同等に見える」は2局を見た印象として保持する。2局から方式間の棋力同等性や向上は判定できない。CVCは操作実証であり、固定局面比較の統計結果とも別の証拠である。

本人は、通常CLIから選択できる一手選択方式を追加・変更する今後のテーマでも、通常CLI CVCを複数局実施することを希望した。`AGENTS.md` の現行方針では、別指定がなければ2局以上を行い、可能な場合は対象方式の先後を入れ替え、開始前表示・両側の実着手・終局までを確認する。少数局の勝敗を棋力向上の根拠にしない。

### 今回の本人選択と未選定項目

2026-11-01、本人は提示候補の「主線の継続（新しい評価項目を一つ選び、学習・設計する）」を採用した。選定理由は尋ねていないため推測しない。次セッションでは、現行の候補プールと評価コードを確認し、独立期待値・既存評価との重複・検証可能性を比較してから、具体的な項目を本人と選ぶ。

現在の候補プールは [次テーマ候補](next-topics.md) にあり、主な案は次の3つである。これは候補であり、選定済みの方式や改善が確認された方式ではない。

1. 角の可動性：飛車可動性と測り方が重なる可能性がある。斜線遮蔽・盤端・先後反転を含む独立局面で定義を確認する。
2. 成りに近づく進行度：対象駒、陣までの距離、陣内の扱いが未決定である。駒得やU/Vと独立な期待値を作れるか検討する。
3. 選んだ重要マスへの利き：対象マスの根拠が未決定で、一般の利き数へ広げると可動性やU/Vと重なりやすい。対象マスの選定根拠を確認する。

「駒の働き・活性度」は広い表現にすぎず、本人が具体的項目として選んだものではない。通常CLIのSFEN入出力、飛車可動性v2、玉安全度との合成、Uの二手・四手適用も未選定の任意候補であり、今回の主線へ自動追加しない。

ShogiHomeでのU候補実践は補助的な未完了帰還目標である。遠隔PCへアクセス可能との本人連絡後、条件を再提案する。今回の主線選択に含めたり、実施許可と解釈したりしない。

## 現在の物理状態

- **作業ディレクトリ:** `/private/tmp/kaname-shogi-main-integration-clone`
- **今回の作業branch:** `codex/next-non-material-evaluation-item`
- **branchの基点:** 引き継ぎ準備開始時、cleanな `main` と `HEAD` は `9cad36da20c8fed785bcda8bf4501f96d3aecc95`。この時点で `refs/remotes/github/main` も同じSHAだった。handoff用branchはこのコミットから作成した。
- **remote注意:** `git remote -v` では `origin` が元checkout `/Users/oki2a24/kaname-shogi` を指す。`origin/main` は `7a389a52f0b68a57a68c3bee97b750ae5475858a` と古く、GitHubの先端として扱わない。過去にGitHub `main` の先端を直接照合した時点では `9cad36da` だった。次セッションではすべてのGit状態を再計測し、リモートを推測で更新しない。
- **handoffのGit状態:** このbranchは引き継ぎと現在地・索引を記録する文書専用branchで、GitHubへpushしていない。コミットとclean状態は再開時のGitコマンドで確認する。コード・テスト・比較成果物を変更していない。
- **直近の製品検証:** V通常CLI/USI統合先で全1039テスト・84モジュール、Ruff、`git diff --check` が成功した。以後の変更は文書のみで、全体テストを再実行していない。これらの結果を次テーマの検証実績として流用しない。
- **保護対象:** 元の `/Users/oki2a24/kaname-shogi` は既存作業を保持しており、変更・切替・clean・reset・stashをしない。`.agents/tasks/`、`data/comparison/runs/`、C2保護4件を追加・移動・削除・上書き・一括ステージしない。

## 次の具体的な行動

1. 再開時に指定cloneで `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`、`git rev-parse main`、`git rev-parse HEAD` をこの順に実行する。handoff文書と現状が違えば実測を優先して確認する。
2. `AGENTS.md`、`docs/resume.md`、本引き継ぎを照合し、`docs/next-topics.md`、`docs/roadmap-non-material-position-evaluation.md`、`docs/02-project-direction.md`、README、`docs/README.md`を読む。過去の [2026-10-29の引き継ぎ](handover-next-evaluation-item-selection.md) は当時の履歴として参照し、そのGit状態・次の行動は現行指示として流用しない。
3. 主線の候補プール、現行評価の実装・テスト、関係する知識メモを確認する。候補ごとに、既存M・飛車可動性・S・U・Vと観測対象がどこで重なるか、独立期待値をどの小局面で検査できるか、改善仮説が測定可能かを比べる。
4. `superpowerssuperpowers:brainstorming` を適用し、必要な確認は一問ずつ行い、回答を待ってから選択肢を絞る。本人は主線テーマを選択済みなので、テーマを再選択させない。具体的な評価項目を本人が選ぶまでは候補を確定しない。
5. 選ばれた一項目について一次資料と現行コードを照合して学び、対象範囲・定義・独立期待値・既存評価との関係・改善仮説・確認方法・未検証事項を設計案と実装計画にまとめる。計画を提示して明示承認を待つ。承認前にTDD、テスト変更、製品コード変更、実装を始めない。
6. 将来実装が承認された時点で、`~/.codex/observations/test-driven-development.md` と `docs/knowledge/test-coverage-review.md` を読み、作業環境・固定Ruff・`.githooks`・baselineをその時点で確認する。対象振る舞いごとの assertion Red、最小実装、Green、Refactor要否、独立レビュー、実績記録を行う。通常CLI方式を新設・変更したときは、別指定がなければCVCを2局以上、可能なら先後反転で実施する。
7. 次テーマの設計・実装完了後のmain統合とpushは、それぞれ別途本人承認を待つ。元checkoutと比較成果物を保護する。

## 再開用プロンプト

> `/private/tmp/kaname-shogi-main-integration-clone` のbranch `codex/next-non-material-evaluation-item` で、主線「次の非駒得評価項目を一つ選び、学び、設計する」を始めます。まず `git status --short --branch`、`git log -3 --oneline --decorate`、`git branch --show-current`、`git rev-parse main`、`git rev-parse HEAD` をこの順で実行し、`AGENTS.md`、`docs/resume.md`、`docs/handover-mainline-next-evaluation-item.md` と現物を照合してください。本人は2026-11-01に主線へ戻るテーマを採用しましたが、具体的な評価項目はまだ選んでいません。過去の候補表をそのまま決定とみなさず、`docs/next-topics.md`、`docs/roadmap-non-material-position-evaluation.md`、`docs/02-project-direction.md`、README、`docs/README.md`、現行の評価コードとテスト、関係する知識メモを確認してください。`superpowerssuperpowers:brainstorming` を使い、候補ごとの既存評価との重複、独立期待値、代表局面、測定可能な改善仮説を照合し、確認は一問ずつ行って本人の選択を待ってください。「駒の働き・活性度」、角の可動性、成りに近づく進行度、選んだ重要マスへの利きのどれも選定済みとは扱わず、A番号も予約しないでください。項目選定後は一次資料に基づき学習・設計し、実装計画を提示して明示承認を待ってください。承認前は `~/.codex/observations/test-driven-development.md` や `docs/knowledge/test-coverage-review.md` の確認が必要な開発段階に入らず、TDD・テスト変更・コード変更・実装を開始しないでください。通常CLIの方式を将来追加・変更する場合は、別指定がない限りCVCを2局以上、可能な限り先後を入れ替えて操作確認し、少数局の勝敗から棋力を主張しないでください。ShogiHomeでのU候補実践はアクセス可能との連絡後に再提案する保留帰還目標です。`/Users/oki2a24/kaname-shogi` の作業状態、`.agents/tasks/`、`data/comparison/runs/`とC2保護4件は変更しないでください。次テーマのmain統合とpushは別途承認を待ってください。すべて日本語で進めてください。
