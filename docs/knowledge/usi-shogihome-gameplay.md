# ShogiHomeでの平手対局確認

## 確認できた範囲

2026-10-04、Mac版ShogiHome 1.28.1で平手対局を行った。第59回は人間先手・後手 `kaname-shogi` で、人の７六歩・２六歩にエンジンが４四歩・９二飛と応じ、人間の投了で終局した。第60回は人間（息子）先手・エンジン後手で、息子の19手とエンジンの18応手を棋譜上で確認した。息子が投了操作をしていない状態で、最後の人の手 `☗４一金` の後にエンジン側の番で自動的に「投了」終局したが、その時点ではUSI通信ログを取っていなかった。

第61回では第60回の37手までのKIFを開き、37手目を画面で選択したことを確認して「現在の局面」から対局した。USIログのsid=2で、ShogiHomeからの37手の `position` と時間付き `go` に対し、エンジンが `< bestmove resign` を返し、その後ShogiHomeが `> gameover lose` と `> quit` を送り、プロセス終了まで記録された。ログ原本は `/Users/oki2a24/Library/Logs/electron-shogi/usi-20261004_201234.log`、全通信の転記と画面・棋譜の記録は[第61回学習記録](../learning/61-shogihome-auto-resign-logs.md)にある。

このログは、第61回の再現局面・ShogiHome 1.28.1・設定で一度観測した実通信である。第60回の実通信を遡って示すものではなく、他局面、他の終局理由、他バージョンにも同じ送受信列が必須だとは結論しない。

## 設定上の注意

第59回の設定画面では `USI_Ponder` が既定ONと表示された。ローカル `usi_engine.py` は `go ponder` に未対応として拒否するため、第59・60回はPonderをOFFにした。第61回のログにも `> setoption name USI_Ponder value false` が記録された。Ponder ON時の通信・挙動は未確認である。

ShogiHome登録エンジンは、過去にアーカイブ済みworktree内のランチャーを指して `ENOENT` となったため、第60回に `/Users/oki2a24/kaname-shogi/kaname-shogi-usi` へ登録し直した。第61回でもこの登録先を画面で再確認した。worktreeや作業ディレクトリが変わった後も同じパスが有効だとは決めつけず、ShogiHome上で確認する。

第61回ではUSI通信ログだけを観察中ONにし、ShogiHomeを再起動してから記録した。観察後はOFFへ戻し、再起動後の設定も確認した。ShogiHomeの通常の監視画面は稼働中セッションの補助確認に使えるが、終了済みセッションの履歴は残らない場合があるため、USI通信の主証拠はログ原本とする。プロンプトへ手動コマンドは送っていない。

## 確認していないこと

- ShogiHome 1.28.1以外の版、macOS以外のOS、他の局面・終局理由での通信。
- Ponder ON、時間管理の精度、SFEN局面、全USIコマンドとの互換性。
- 第59・60回のUSI通信ログ。両回の対局内容は画面と棋譜で確認したが、コマンド列を記録していない。
- 第59・60回の棋譜ファイル出力。これらはShogiHome内の画面・棋譜で確認し、ファイルには保存・エクスポートしていない。第61回の一時KIF再現とは別の記録である。
- 第61回の結果から導く、すべての対局での後続コマンドの必須順序。

## 一次資料

- [USI原案](https://hgm.nubati.net/usi.html)
- [ShogiHome公式: エンジン登録手順](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E7%99%BB%E9%8C%B2%E6%89%8B%E9%A0%86)
- [ShogiHome公式: スクリプト・インタプリタ型エンジンの注意](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%B7%E3%82%A7%E3%83%AB%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%97%E3%83%88%E3%82%84%E3%82%A4%E3%83%B3%E3%82%BF%E3%83%97%E3%83%AA%E3%82%BF%E5%9E%8B%E8%A8%80%E8%AA%9E%E3%81%A7%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E3%82%92%E5%AE%9F%E8%A1%8C%E3%81%97%E3%81%9F%E3%81%84%E6%96%B9%E3%81%B8)
- [ShogiHome公式: ログ・監視・プロンプト](https://github.com/sunfish-shogi/shogihome/wiki/%E9%96%8B%E7%99%BA%E8%80%85%E5%90%91%E3%81%91%E6%A9%9F%E8%83%BD%E3%81%AE%E4%BD%BF%E3%81%84%E6%96%B9)
- [ShogiHome公式: 基本操作](https://github.com/sunfish-shogi/shogihome/wiki/%E5%9F%BA%E6%9C%AC%E7%9A%84%E3%81%AA%E6%93%8D%E4%BD%9C%E6%96%B9%E6%B3%95)
