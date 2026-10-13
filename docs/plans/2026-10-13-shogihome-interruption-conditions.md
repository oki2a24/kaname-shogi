# ShogiHome「対局中断」経路の資料整理と条件案

2026-10-13作成。**条件案は2026-10-13に本人が承認。実施開始は2026-10-13に本人が承認。main取り込みは未承認。** 条件案作成後、本人の実施開始と変更・保全・復帰の別承認を得た一局、および未達手順への依頼を受けた一局を実施した。さらに以前調査した39手目局面を指定され一局再挑戦したが、自然応答と持将棋が先行し、探索中の対局中断経路の観測は未達。実機観測は計三局で、三回目の証拠・復帰状態は末尾を参照。[作成・学習記録](../learning/shogihome-interruption-conditions.md)。

## 対象と結論

通常ローカル対局の「対局中断」が対局・エンジンを終了する経路を整理する。通常stop後の合法応答と対局継続の代替にはしない。二手先読みと時計は「学習・実装テーマとしては完了。ShogiHome実機挙動と一般的な時間保証は未確認のまま」を維持する。

現行安定版として公式APIが示す **v1.29.1** と、過去記録の **v1.28.2** の固定タグを確認した。両版の `game/game.ts` と `background/usi/engine.ts` は取得本文の `cmp` で一致した。対局中断は `INTERRUPT` を対局結果へ変換しないため、**この経路ではgameoverを送らず、closeからquitへ進む**。資料から経路と観測手段は定義可能。ただし条件案作成時点ではインストール済み版・実画面・実通信・正常終了は未確認だった。その後の実施結果と限界は末尾を参照。

## 一次資料と版の固定

確認日はすべて2026-10-13。Wikiは版に固定されない利用者資料、以下のソースは固定タグであり、実アプリの観測ではない。

| 資料 | 今回確認した範囲 |
| --- | --- |
| [公式latest API](https://api.github.com/repos/sunfish-shogi/shogihome/releases/latest)、[v1.29.1リリース](https://github.com/sunfish-shogi/shogihome/releases/tag/v1.29.1) | APIのtag_nameはv1.29.1、published_atは2026-10-04T06:59:35Z。リリース本文は分岐一覧レイアウト修正・セキュリティ強化。中断経路の仕様説明ではない |
| [過去対象v1.28.2リリース](https://github.com/sunfish-shogi/shogihome/releases/tag/v1.28.2) | 過去対象版を識別する。現行版の証拠へ流用しない |
| [エンジン機能の操作方法](https://github.com/sunfish-shogi/shogihome/wiki/エンジンを使う機能の操作方法) | 通常はローカル対局。検討の停止ボタンはエンジンを残して思考を中断。通常対局中断のUSI列は説明していない |
| [開発者向け機能](https://github.com/sunfish-shogi/shogihome/wiki/開発者向け機能の使い方) | USIログ、設定後の再起動、監視の約1秒更新、UI終了とセッション終了の非同期性。画面だけで通信・終了を確定しない |
| [基本操作](https://github.com/sunfish-shogi/shogihome/wiki/基本的な操作方法) | 棋譜読込・保存。終了コマンド列の説明はない |

Webの `/releases/latest` 取得結果はv1.29.0を示したが、公開APIを直接取得するとv1.29.1だった。APIとv1.29.1リリースを採用した。可変mainのソースは今回の結論に使わない。公式ソース取得は `/private/tmp/shogihome-source-review/` に置いた公開資料のコピーであり、実機ログではない。

## 固定タグで追った経路

以下の行番号はv1.29.1のソース行。英語名の `stopGame` / `stop` / `end` / `close` は操作、`INTERRUPT` は中断を表すデータ、`GameResult` は勝敗結果のデータである。

1. [日本語ラベル](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/common/i18n/locales/ja.ts#L191)の `stopGame` は「対局中断」。[ControlPane.vue](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/renderer/view/main/ControlPane.vue#L32)はGAME/CSA_GAME時に表示し、onStopからstore.stopGameを呼ぶ（247行）。今回はGAMEだけを対象にする。
2. [store/index.ts](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/renderer/store/index.ts#L814)のGAME分岐はgameManager.stopへ進む。repeat >= 2では確認ダイアログを挟むため、代表条件はrepeat=1。CSA・並列・連続対局は対象外。
3. [game.ts](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/renderer/game/game.ts#L485)は100msのintervalでACTIVE/PENDINGを待ち、end(INTERRUPT)へ進む。IDLEなら終了し、他状態では待ち続けうる。100msは完了時間保証ではない。
4. [sendGameResultと変換](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/renderer/game/game.ts#L615)は変換結果がある場合だけplayer.gameoverを呼ぶ。[変換関数](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/renderer/game/game.ts#L673)にINTERRUPTはなくnullとなる。従って中断ではgameover通知なし。
5. [endの後半](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/renderer/game/game.ts#L511)は時計pause、中断の特殊手と終局情報の記録を行う。自動保存ONなら保存処理もある。INTERRUPTは次局へ進まずclosePlayersへ。[USIPlayer.close](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/renderer/players/usi.ts#L284)は応答ハンドラを消してusiQuitを呼ぶ。
6. [preload](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/renderer/ipc/preload.ts)、[IPC受信](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/background/window/ipc.ts#L992)、[USI管理quit](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/background/usi/index.ts#L474)、[Engine.quit](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/background/usi/engine.ts#L346)を経てquit行を送る。quitはstopやbestmove待ちを挟まない。
7. [終了タイマー](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/background/usi/engine.ts#L562)は5秒後にprocess.killを行う。[プロセス部品](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/background/usi/process.ts#L56)はNodeのkillを呼ぶ。kill到達を正常終了と扱わない。[onClose](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/background/usi/engine.ts#L584)は終了コード・signalを記録する。IPC完了や通常画面への遷移だけではOSプロセス終了の証拠にならない。

v1.28.2も[中断・終了](https://github.com/sunfish-shogi/shogihome/blob/v1.28.2/src/renderer/game/game.ts#L485)、[結果変換](https://github.com/sunfish-shogi/shogihome/blob/v1.28.2/src/renderer/game/game.ts#L673)、[USIPlayer.close](https://github.com/sunfish-shogi/shogihome/blob/v1.28.2/src/renderer/players/usi.ts#L245)、[Engine.quit](https://github.com/sunfish-shogi/shogihome/blob/v1.28.2/src/background/usi/engine.ts#L346)を再読した。過去の[通常停止記録](../learning/shogihome-normal-stop-conditions.md)の「終局通知はgameoverを呼ぶ」は、変換結果がある場合の説明に限定する。中断でgameoverが送られるという事実はない。過去本文は履歴として残し、訂正へのリンクを添える。

## 五つの経路の区別

| 経路 | 資料で言えること | 未確定・区別すること |
| --- | --- | --- |
| 対局中断 | GAME・ACTIVE/PENDINGからINTERRUPT、gameoverなし、quit。時計pauseと中断棋譜を記録 | 実通信順序、自然応答との競合、実終了時間、インストール済み版 |
| 通常stop | [USIPlayer.stop](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/renderer/players/usi.ts#L276)→usiStop→[Engine.stop](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/background/usi/engine.ts#L497)。対象状態でstop送信 | 通常対局画面の任意操作がこれを呼ぶとは確認していない。中断で代用しない |
| 時計期限 | [GameManager.timeout](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/renderer/game/game.ts#L470)はエンジン時間切れ無効ならplayer.stopで継続、有効または人間側ならTIMEOUT終局 | エンジン内部の期限とは別。内部期限で先にbestmoveが返る可能性あり |
| 検討・解析中断 | [ResearchManager.pause](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/renderer/store/research.ts#L150)はstopで一時停止、closeはquit。[単一棋譜解析close](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/renderer/store/analysis.ts#L104)はエンジンcloseへ進む | 検討の一時停止・検討終了・棋譜解析中断は別。連続解析も別管理であり今回対象外。kaname-shogiはgo infinite等未対応 |
| 終局後gameover / quit | 勝敗へ変換できる終局ではplayer.gameover。[Engine.gameover](https://github.com/sunfish-shogi/shogihome/blob/v1.29.1/src/background/usi/engine.ts#L516)は探索状態次第でstopを先送りしbestmoveを無効化。その後、連続対局終了時はclose/quit | 常にstop→gameover→quitという固定列ではない。中断は変換なし。gameoverはプロセス終了命令ではない |

## kaname-shogi側の契約と既存検査

[USI応答](../knowledge/usi-engine-response.md)、[探索停止](../knowledge/search-stop.md)、[時計予算](../knowledge/time-budget.md)と現行コード・検査本文を読み取りで照合した。

- 通常stopは合法予備手確保まで保留しうるが、一応答を返す。quit/EOF/gameoverは未送信応答を抑制して探索を回収する。gameoverは入力受付を続け、quit/EOFは終了する。
- quitの入力確定と送信は共通Lockで順序付く。送信完了が先なら一応答が残る。ログ上quitの後にbestmoveが見えても、受渡し・記録遅れがあり、内部確定順や不具合をその列だけで断定しない。
- `tests/test_usi_concurrency.py` の `test_input_confirmation_orders_suppression_and_send` と送信先行の対ケースは、関数境界の抑制と順序を検出する。`tests/test_usi_process_concurrency.py::test_controlled_search_accepts_and_shuts_down` は実pipeと固定探索でstop・quit・EOF・gameoverを区別する。ShogiHome操作や実探索の時間保証は確認しない。
- 契約は「中断後に合法bestmoveが必須」ではなく「未送信抑制・回収」。代表ケースは探索中の中断、区別すべき誤りは中断を通常stop扱い・gameover必須・UI終了をプロセス終了とすること。既存検査はエンジン側の契約だけを補完し、ホスト経路は補完しない。今回はテスト実行・誤り注入を行わない。

## 将来の代表条件案と開始前ゲート

以下は資料から導き、本人が承認した条件案。実施開始も別途承認されたが、設定変更・棋譜保全等の具体範囲は開始前ゲートで確定する。過去の局面・時計・試行値を自動継承しない。

- 対象版候補はv1.29.1。ただし更新・インストールは提案範囲外。後日に実際の版を確認し、違えば該当タグで再照合するまで開始しない。v1.28.2も調査済みだが現在の実機版と断定しない。
- 通常ローカル対局一局・repeat=1・人間先手・エンジン後手・Ponder OFF・TwoPlyMaterial・外部定跡なし・自動保存OFFを代表条件とする。平手から本人の先手７六歩一手（`7g7f`）後の後手goを対象にする。これなら未対応のposition startpos単独をエンジンに要求しない。合法手の事前照合は将来の別承認に含め、今回は列挙・実行しない。
- 時計候補は双方10分＋秒読み60秒・加算0。時計切れを誘発せず中断操作を調べるための新しい提案値であり、性能保証ではない。開始前の設定値と実際のgo引数を照合する。時計・設定変更の具体範囲は別途承認する。
- 版、登録先、局面、手番、上記設定、未保存棋譜の保全方法、採取対象ログと保存先、復帰元の値を実施前に本人と確定する。ログ設定変更・再起動・棋譜保存も別承認の具体範囲に含める。未確定ならgoを開始しない。
- 中断操作は当該通常対局画面の「対局中断」一回だけ。資料と画面が違う、別機能の停止、確認ダイアログの意味が違う場合は止める。USIプロンプト、直接入力、時計切れ、解析中断に切り替えない。

## 将来の証拠と判定案

同一セッションIDで、版・登録先・設定・開始局面と手番・position/go・操作前後の画面・棋譜・送受信の全行・プロセス終了を結び付ける。USIログを通信の主証拠、監視を生存状態の補助証拠にする。操作時点は別の時系列に記録し、ログ時刻との精度差を残す。

| 判定材料 | 扱い |
| --- | --- |
| go後、応答前の通常対局で中断操作、その後同セッションにquit、棋譜中断・時計停止・通常画面、終了コード0・signalなし・対象セッション消滅 | 「この一回で資料の中断終了経路と整合」。内部探索位置や全版互換性の証明にはしない |
| bestmoveなしでquit後に終了 | 正常な抑制と整合。合法応答を必須にしない |
| 操作前にbestmove・盤面反映 | 自然応答先行。探索中中断の観測は未達。追加手を指さず、同じ中断操作で一局を終了し、探索後の終了として別分類 |
| 中断付近にbestmoveが一件ある | 送信先行との競合を記録し、対象positionの合法手と照合する。中断確定前の反映と中断後の反映を区別できなければ判定保留。内部確定順を推定しない |
| stop / gameoverが現れる、切れ負けや別終局、二重応答、不正応答、別セッション、証拠不足 | 代表経路との差分として保留。通常stop成功やエンジン故障へ読み替えない |
| quit後signal付き終了・5秒タイマーによるkillの形跡 | ホストによる終了。正常回収成立とはしない。終了コードやsignalが得られなければ正常終了は未確認 |

合法手照合は返答があった場合だけ必要。特殊手の中断は着手ではなく、元の盤面を進める合法手と同一視しない。棋譜の中断理由と実指し手の増分を別々に比較する。ShogiHomeは終局時に自動保存しうるため、保存OFFを確認できなければ開始しない。

## 有限の停止・終了・復帰案

- 一局・対象go一回・中断一回、再試行0。起動/readyの観測待ちは各最大10秒を提案する。対象goを確認したら待ち時間を意図的に延ばさず中断へ進み、go確認から操作着手までの上限を5秒とする。5秒は探索継続の予測ではなく作業を切り上げる管理値。自然応答が先なら上の別分類にする。
- 対象goを確認できない、状態不一致、操作できない場合は追加着手・開始操作を止める。既に対局を開始していた場合は、版・通常対局状態・ボタン対応が確認できる場合だけ同じ中断を一度行い、条件不足として終了観測へ進む。対応が不明なら操作せず復帰未完了として本人へ引き継ぐ。
- 中断操作後は最大10秒で画面・ログ・監視・終了の観測を切り上げる。ホストの5秒killを含みうる窓であり、10秒以内の正常終了保証ではない。残存時は追加stop/quit、プロンプト、強制終了を行わず証拠と残存状態を提示する。アプリ自身のkillがありうる点を実施承認時にも明示する。
- 設定・棋譜の復帰は事前に承認した保存先・開始前値へ戻し、必要な再起動後にログ設定・登録・棋譜・対象セッション消滅を確認する。復帰のための追加対局は行わない。未保存棋譜・保存失敗・再起動不能なら復帰保留とし、未承認の破棄や再起動をしない。
- 復帰操作は一巡のみ、復帰後のセッション確認待ちは最大10秒。操作不一致・エラーなら即時停止する。時間枠は観測待ちの上限であり、保存・人間判断・復帰操作を含む全経過時間の保証ではない。復帰できない状態を成功として隠さない。

## 本人の判断・未検証・承認境界

条件案の承認対象は「資料上の経路整理、代表条件、証拠、分類、有限の終了・復帰という考え方」。後日の実施開始では、実機版・棋譜保全・ログ/設定変更と再起動・具体的保存先・終了タイマーの扱いを含む条件を提示し、別の明示承認を待つ。main取り込みも別承認。

将来結果を提示するなら、本人には「どの分類まで証拠がそろい、この一回を中断終了経路と整合する観測として受け入れるか」を判断してもらう。受け入れと理解確認・統合承認を分ける。

条件案作成時点で未検証だったのは実機の版・画面・通信列・ログ粒度・終了時間・正常回収・棋譜反映・設定復帰。その後確認できた事実と復帰保留は末尾に分けて記録する。全局面・全競合・他OS・CSA/並列/連続対局・検討/解析・一般的な時間保証は対象外。自然応答との競合を必ず避けられるとは言えない。これらを二手先読み・時計テーマの完了条件へ積み戻さない。

## 条件案の承認（2026-10-13）

本人は提示した条件案に「承認する」と回答した。資料整理・代表条件・証拠・判定分類・有限の終了と復帰の考え方への承認として記録する。実施開始、実機操作・設定変更・ログ採取・計測、main取り込みの承認とは扱わない。

## 実施開始承認と事前確認（2026-10-13）

本人は具体的な実施内容の説明後に「実機作業を開始して下さい」と指示した。実施開始を承認として受け付け、接続スキル・手順書・本条件を再読して画面を確認した。main取り込みは未承認。

画面はShogiHome 1.28.2、`/private/tmp/kaname-shogihome-clock-deadline-20261013-before.kif`、開始局面表示、USI/CSAセッション0。登録先は現行チェックアウトの `kaname-shogi-usi`、Ponder OFF、Difficulty Random、Hash 32、外部定跡OFF。ログはアプリ/USI/CSAすべてOFF、レベルINFO。対局設定は人先手・kaname後手、10分+30秒・加算0、エンジン時間切れありON、後手別時計OFF、現在の局面、最大40手、連続1局・並列1、自動保存OFF。設定画面と対局画面はキャンセルで閉じ、値を変更していない。対局・エンジン起動・ログ採取はまだ行っていない。

具体的な設定変更と棋譜保全・復帰の承認待ち。提案はDifficulty Random→TwoPlyMaterial、秒読み30→60秒、開始局面を平手として一局を開始し、実施後に元の設定へ戻す。アプリログとUSIログをOFF→ON、CSAはOFF維持、INFO維持。開始前棋譜と結果棋譜を新規の一時保存先へ保全し、ログ有効化/復帰時に再起動する。現行版は両経路を照合済みの1.28.2を使い、更新しない。quit後5秒のホスト側killが起こりうる点も判断材料に含める。

## 一回の実機観測と復帰（2026-10-13）

本人は「変更・保全・復帰をまとめて承認」と回答。アプリ/USIログON、CSA OFF維持、INFO維持、Difficulty TwoPlyMaterial、共通時計10分+60秒、開始局面平手への変更、棋譜保全・再起動・復帰を承認した。

### 観測事実

- 実機はShogiHome 1.28.2。開始前棋譜を `/private/tmp/kaname-shogihome-interruption-20261013/before.kif` へ別名保存した。元ファイルとバイト一致を確認した。
- ログ設定とDifficultyを保存し、ShogiHomeを終了・再起動した。再起動後、アプリ/USIログON・CSA OFF・INFO、TwoPlyMaterial・Ponder OFF・外部定跡OFFを確認した。登録先は現行作業ツリーのランチャー。
- 人先手・kaname後手、平手、10分+60秒・加算0、エンジン時間切れありON、後手別時計OFF、最大40手、連続1局・並列1、自動保存OFFで一局だけ開始した。７六歩一手後に中断ボタンを一度押し、追加着手・再試行はない。
- 対局セッションはSID 2、PID 93151。ログは `position startpos moves 7g7f`、`go btime 569898 wtime 600000 byoyomi 60000` を21:29:22.387に送信。quitは21:29:22.953、終了は21:29:22.968、`close=0 signal=null`。go→quitは0.566秒、quit→closeは0.015秒。これらはホストログ時刻差で内部受付・探索位置の計測ではない。
- SID 2のstop/gameover/bestmoveは0件。画面に「対局終了（中断）」、通常画面で時計表示の消失、７六歩後の盤面と棋譜「７六歩→中断」を確認した。監視はquitCompletedとなり、その後セッション0を確認した。結果KIFは `result.kif` に保存。持ち時間10:00+60、実指し手1手と中断特殊手を確認した。
- 対局前、後手の設定確認ボタンを開いた際にエンジン情報取得用SID 1が別途起動していたことがログで判明した。usi/usiok/quitのみ、goなし、正常終了。この補助起動を隠さず、対局SID 2と区別する。対局は一局・goは一回。

### 条件との差と判定の限界

中断直前の監視表示は更新前のready/usinewgameで、操作前にgoを画面・ログで確認できていなかった。７六歩の操作開始から中断操作開始までの外部時刻差は731ms。実際のgo→quitは事後ログで確認できたが、事前確認済みと扱わない。また中断終了ダイアログを閉じて監視を再確認した表示時刻は21:29:33.833（quitから10.880秒後）で、最大10秒の観測窓を超えた。終了自体はquitの15ms後とログで確認できるが、10秒以内に全画面確認を終えたとは言わない。

判定は「この一回の通信・棋譜・正常終了は資料の中断終了経路と整合」。操作前go確認の欠落、確認窓超過、下記の復帰保留があり、承認済み条件を全項目満たしたという判定は保留。内部探索の開始位置・quit受付時刻・未送信抑制の内部因果、一般的時間保証は未確認。bestmoveがなかったので合法応答の照合は対象なし。

### 復帰できた事項と保留

結果保存後、DifficultyをRandomへ保存復帰。アプリ/USIログをOFFへ戻し、CSA OFF・INFOを維持して保存・終了・再起動した。再起動後ログ3種OFF、Random、Ponder OFF、外部定跡OFF、元の `/private/tmp/kaname-shogihome-clock-deadline-20261013-before.kif` と開始局面表示、セッション0を画面で確認した。未保存結果は残していない。

秒読みを30秒、開始局面を「現在の局面」へ戻してキャンセルしたが、再表示は60秒・平手となり保存されなかった。対局設定に保存専用ボタンが見えず、「対局開始」を使う追加対局は本条件が禁止しているため実行していない。**この2項目の復帰は保留**。値入力の途中で6300という表示になったが、30へ訂正した後キャンセルしており、6300で対局はしていない。復帰完了とは報告しない。再試行・直接設定ファイル変更・プロンプト・強制終了は行っていない。

### 証拠と承認段階

保存先は `/private/tmp/kaname-shogihome-interruption-20261013/`。before.kif、result.kif、当該起動のusi-20261013_212714.logとapp-20261013_212714.logのコピーを保持する。原ログは `~/Library/Logs/electron-shogi/` に保持、共有・削除・外部送信なし。画面証拠は本会話のUIツール出力にあり、別画像ファイルとしては保存していない。今回の作業でコード・テスト・製品設定JSON変更・テスト実行はない。アプリ設定変更は上記承認範囲で行った。観測結果の本人受け入れ、復帰保留の次の判断、main取り込み、最後の理解確認は未取得。

### 独立照合で確認した補助起動の追加

USI生ログにはSID 1に加えて、復帰時の設定確認に伴うSID 3もあった。SID 3は21:30:21.869起動、usi/usiok後21:30:21.916にquit、21:30:21.921にclose=0/signal=null、goなし。したがってこのログのエンジン起動は計3回（情報取得SID 1・3、対局SID 2）で、対局一局・対象go一回とは区別する。先のSID 1だけの説明を補足する。

## 追加の実機再挑戦と復帰（2026-10-13）

本人は未達項目のうち手順の完全成立だけを、本セッションで再挑戦するよう依頼した。前回と同じ一局条件・保存先・復帰範囲を適用し、追加一局だけを実施した。再挑戦前にDifficulty Random、アプリ/USIログOFF、CSA OFF、INFOへ復帰し再起動済み。保存済み `before.kif` を開き、平手初期局面とセッション0を確認した。秒読み60秒・開始局面平手は前回以降残っていた設定値であり、再挑戦前の対局画面で再確認した。

### 通信と手順の結果

- アプリ/USIログをON、CSAログをOFF、INFOを維持し、DifficultyをTwoPlyMaterialにして保存・再起動した。再起動後のログ値は画面で確認した。人先手・エンジン後手、平手、10分+60秒・加算0、Ponder OFF、外部定跡OFF、1局・並列1・自動保存OFFで開始した。
- SID 1で `position startpos moves 7g7f` と `go btime 588497 wtime 600000 byoyomi 60000` が21:47:23.459に送信された。21:47:23.644更新の画面監視で `waitingForBestMove` とgoを確認した。
- 「対局中断」クリックの開始時刻は21:47:29.200ごろ。go送信からは約5.741秒、画面確認からは約5.556秒で、画面確認後5秒以内に操作する条件を超過した。USIログ上の `bestmove 4c4d` は21:47:24.349に到着しており、クリックより約4.851秒先行していた。ログにstop行はない。自然応答先行のため、探索中の対局中断に伴う未送信抑制・回収の観測は未達。
- 中断後の画面は「対局終了（中断）」、棋譜は「７六歩→４四歩→中断」。21:47:29.389にquit、21:47:29.398に `close=0 signal=null`。gameoverは記録されていない。画面から中断で終わりquitへ進む点は資料の終端経路と整合するが、自然応答が先行しているため、探索中の中断時の抑制・終了挙動を確認した証拠ではない。
- quit後2.256秒の監視で状態 `quitCompleted`・最終送信quit・最終受信bestmoveを確認したが、USIエンジン数は1だった。quit後9.255秒でも1。エンジン数0は結果を保存した21:48:55.646の監視で確認したため、10秒内に監視一覧から消えたとは言えない。USI生ログのprocess closeはquit後9msである。

### 記録と復帰の結果

- 棋譜を `/private/tmp/kaname-shogihome-interruption-20261013/result-retry-20261013.kif` に保存し、アプリログとUSIログを同じフォルダに `app-retry-20261013_214635.log` と `usi-retry-20261013_214635.log` で保全した。USIログにはSID 1のみで、設定確認の補助起動は含まれない。アプリログは結果 `invalid: 1` を記録する。
- Difficulty Random、アプリ/USIログOFF、CSA OFF、INFOへ戻し、保存・再起動後にログ3種OFFを確認。保存済み `before.kif` を開き、開始局面表示とセッション0を確認した。
- 秒読み60→30秒と開始局面平手→「現在の局面」は未復帰。前回の画面試行ではキャンセル後に値が戻り、対局開始による保存以外のUI手段が見えなかった。追加対局と設定ファイル直接編集は行わず保留。よってログ・Difficulty・棋譜・セッションは確認済みだが、設定全体の復帰は未完了。

本再挑戦は一局・go一回・中断操作一回。自然応答先行と画面確認後5秒窓の超過により、本人が求めた手順の完全成立は達成できなかった。ここからの再試行は未承認。結果受け入れ、秒読みと開始局面を復帰する方法、mainへの取り込み、最後の理解確認は未完了。作業ブランチ・未コミット文書差分は継続し、製品コード・テスト・設定ファイル変更とテスト実行はない。

## 研究済み39手目局面での追加再挑戦と復帰（2026-10-14）

本人の「探索時間を確保できる局面は、以前のセッションで調査しています。それを使って再挑戦してください」という依頼を受け、追加一局だけを実施した。対象は[二手先読みの再調査KIF](../records/two-ply-usability-check-2026-10-11-retry.kif)の39手目「１五歩」後で、棋譜上は40手目に「９四角打」（28秒）、41手目に持将棋が記録されている。コピーしたKIFを開き39手目を選択し、対局開始ダイアログで「現在の局面」を選んだ。開始画面で人先手・エンジン後手、10分+60秒・加算0、Difficulty TwoPlyMaterial、Ponder OFF、最大40手・一局・並列1、自動保存OFFを確認した。過去の探索時間を再現・保証できるという前提は置かない。

### 通信と手順の結果

- 対局エンジンはSID 2、PID 44592。`position startpos moves` は39手を含む対象局面を記録し、`go btime 600000 wtime 600000 byoyomi 60000` は `2026-10-14T06:35:30.914` に送信された。探索中の監視画面は `2026/10/14 06:35:36.680` 更新で `waitingForBestMove` を表示しており、go送信から約5.766秒後に探索中を画面確認した。条件案の5秒管理値はこの画面確認から操作着手までを対象とするが、実際のクリック試行時刻は記録されておらず、窓を超過したとは判定できない。
- 画面操作には以前取得したアクセシビリティ要素IDを使ったが「element ID no longer valid」となり、クリックは成立しなかった。新しい画面状態を取得した時点で「対局終了（持将棋）」のモーダルが表示されていた。従って、この回では「対局中断」ボタンを実際に押しておらず、中断経路は未観測。画面確認後5秒以内に有効な操作ができたかは、クリック試行時刻がないため不明。
- `2026-10-14T06:35:42.645` に `bestmove P*2e` が到着し、goから11.731秒後だった。KIFの変化40手目には「２五歩打」（11秒）、41手目には持将棋が記録された。3ms後に `gameover draw`、6ms後に `quit`、さらに3ms後に `close=0 signal=null` が記録された。`stop` は0件。元KIFにも41手目の持将棋があるが、この結果と通信列だけから、ShogiHomeが終局へ進んだ内部理由や元KIFの終局情報が直接の原因だったかは断定しない。
- これは自然な一手の応答後に持将棋として終了した観測であり、探索中の対局中断、未送信応答の抑制、通常 `stop`、時計期限のいずれの成立証拠にもならない。39手目の同じ開始局面でも実応答時間は元棋譜の28秒と異なるため、過去の消費時間は再現時間の保証ではない。

### 証拠保全と復帰

- この回のログと棋譜は `/private/tmp/kaname-shogihome-interruption-20261014-retry/` にコピー保存した。内容は `position-researched-20261011.kif`（対象KIF）、`before-current.kif`（復帰前の平手初期局面KIF）、`result-20261014.kif`（実機結果）、`usi-20261014_063349.log`、`app-20261014_063349.log`。対象KIF SHA-256は `0111c5ba2c606e162fd23400d4df823684f8b57cc6d4dc163734573449617694`、結果KIFは `0cb1bf82061f991350f3c7f5eca623cf6dfc7a17f475e9e4a55055e8fe03124b`、USIログは `5d3891a072deea3799167290c5f78628a42b39be2e23399d016bdb28da74ccd5`、アプリログは `03ca9430bc31fdf20899073d9415cfa1baf7ac9dc163a964dc681ed3385fa0fd`。
- USIログのSID 1は開始前のエンジン情報取得（usi/usiok/quitのみ、goなし）、SID 2だけがこの一局の対局セッション、SID 3は対局後のエンジン設定確認（usi/usiok/quitのみ、goなし）だった。全セッションを含むUSIログを保全しており、補助起動を対局と混同しない。
- DifficultyをRandomへ戻して保存し、アプリ/USI/CSAログをすべてOFF（INFO維持）へ戻して保存・再起動した。再起動後にログ3種OFF、Difficulty Random、Ponder OFFをUIで確認した。結果棋譜を保存した後、`before-current.kif` をShogiHomeで開き、平手初期局面表示とUSI/CSAセッション0を確認した。
- 対局設定ダイアログを読み取りで再確認したところ、開始局面は元の「現在の局面」に戻っていた。一方、秒読みは60秒のままで、開始前の30秒へ復帰していない。過去の画面確認では開始ダイアログの変更をキャンセルすると保存されず、値の保存には対局開始が必要に見える。今回承認されたのは研究済み局面での一局再挑戦であり、復帰目的の追加対局は行わない。設定ファイルを直接編集することもしていないため、秒読み60秒→30秒のみ復帰保留。

この依頼による追加再挑戦は一局・対象go一回まで。自然応答と終局が画面操作より先行し、対局中断操作そのものが未成立だった。本人による今回結果の受け入れ、秒読み設定の復帰方法の次判断、追加実機操作、main取り込み、理解確認は未取得・未承認。今回もコード・テスト・設定ファイル変更とテスト実行は行っていない。

## 追加再挑戦結果の受け入れと復帰判断（復帰専用対局前、2026-10-14）

本人は今回の結果に「受け入れる」と回答した。これは自然応答後の持将棋終局という観測結果を受け入れた記録であり、探索中の対局中断が成立したという意味ではない。この時点では秒読み60秒から開始前の30秒への復帰だけが未完了だった。

ShogiHome 1.28.2のローカル対局設定ダイアログには「対局開始」と「キャンセル」があり、保存専用ボタンは確認できなかった。設定値変更後のキャンセルで保存されず60秒へ戻ることも画面で確認済み。取得済みの公式v1.28.2 [`store.startGame`](https://github.com/sunfish-shogi/shogihome/blob/v1.28.2/src/renderer/store/index.ts#L656)は `api.saveGameSettings(settings)` の後に対局マネージャを開始する。このUIと取得ソースの範囲では30秒を保存するには新しい対局開始が必要に見える。当初承認された再挑戦には復帰専用対局を含めなかったため、別途本人判断を求めた。ShogiHome設定ファイルの直接編集はしていない。

今回結果の受け入れは済み。この記録時点では秒読み復帰とそのための追加操作について本人判断待ちだった。main取り込みは別承認、理解確認は未実施。

## 本人承認後の秒読み復帰専用対局（2026-10-14）

本人は「秒読みを30秒へ戻すためだけに対局を1回開始し、すぐ終了する操作」を承認した。保存済み `/private/tmp/kaname-shogihome-interruption-20261014-retry/before-current.kif` を開いた状態でローカル対局設定を開き、10分・加算0秒・先手人・後手kaname-shogi・先後同一時計・開始局面「現在の局面」を維持して、秒読み60秒を30秒に変更した。開始前の設定画面は先後双方を30秒と表示した。

一局を開始した直後の画面では平手初期局面・人の手番・USI SID 2 / PID 51932 / State `ready`・最終送受信 `usinewgame` / `readyok` を確認した。直ちに「対局中断」を選び、画面に「対局終了（中断）」、棋譜欄に「中断」と経過0:03が表示された。エンジン監視欄はその後 `quitCompleted` と最終送信 `quit` を表示し、元棋譜を開き直した後は「未保存」表示が消え、初期局面とUSI/CSAセッション0に戻った。復帰専用対局のUSIログは採取していないため、これは探索中の停止経路を検証する通信証拠ではない。

保存済み元棋譜を開き直した後、対局を開始せず設定画面だけを再確認した。10分・秒読み30秒・加算0秒、先後双方30秒、「現在の局面」が維持されていることを確認してキャンセルした。設定ファイル編集や製品コード・テスト変更、テスト実行は行っていない。設定復帰は完了。探索中の対局中断経路は未達のまま、追加実機操作とmain取り込みは未承認、理解確認は未実施。
