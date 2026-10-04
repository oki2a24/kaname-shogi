# ShogiHomeでの平手対局確認

## 確認できた範囲

2026-10-04、Mac版ShogiHome 1.28.1の「ローカル対局」で、作業ブランチの `kaname-shogi-usi` を登録した。開始局面は平手、先手は人、後手は `kaname-shogi` とした。棋譜・盤面に人の７六歩、エンジンの４四歩、人の２六歩、エンジンの９二飛が順に表示された。人が投了すると、ShogiHomeは「対局終了（投了）」を表示し、棋譜にも投了を記録した。これによりこの版・環境・局面で、エンジンの通常応答をGUIが受け入れ、対局を終了できることを確認した。

## 設定上の注意

エンジン設定画面では `USI_Ponder` が既定ONと表示された。ローカル `usi_engine.py` は `go ponder` に未対応であるため、今回の対局ではエンジン設定をOFFにした。対局中のUSI通信ログは有効にしていないので、ShogiHomeが実際に送ったコマンドや、Ponder設定による通信差は未確認である。

## 確認していないこと

この一局は時計の精度・強さ・別局面・全USIコマンド・他バージョンや他OSでの互換性を示さない。棋譜ファイルの保存・エクスポートも行っていない。詳細な経緯と証拠範囲は[第59回学習記録](../learning/59-shogihome-even-game.md)を参照する。

## 一次資料

- [USI原案](https://hgm.nubati.net/usi.html)
- [ShogiHome公式: エンジン登録手順](https://github.com/sunfish-shogi/shogihome/wiki/%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E7%99%BB%E9%8C%B2%E6%89%8B%E9%A0%86)
- [ShogiHome公式: 基本操作](https://github.com/sunfish-shogi/shogihome/wiki/%E5%9F%BA%E6%9C%AC%E7%9A%84%E3%81%AA%E6%93%8D%E4%BD%9C%E6%96%B9%E6%B3%95)
