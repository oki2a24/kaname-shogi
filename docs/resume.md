# 学習・開発の再開案内

第41回「対局モードの選択」は、設計合意、TDD、独立レビュー、全検証、main取り込み、最後の理解確認まで完了した。

`python3 -m kaname_shogi`は起動時に人間対人間・人間対コンピュータ・コンピュータ対コンピュータを選べる。先後交代は局面規則、担当は`GameMode`というCLI設定である。全230テストが成功している。

本人は第42回として「CLIでの明示的な保存・読込」を選んだ。詳細な現在地と再開手順は[第42回の引き継ぎ](handover-cli-save-load.md)を参照する。本人が新しいセッションで下の再開用プロンプトを入力するまで、第42回の学習・設計・実装を開始しない。

```text
kaname-shogiの第42回「CLIでの明示的な保存・読込」を始めてください。最初にAGENTS.md、README.md、docs/resume.md、docs/next-topics.md、docs/02-project-direction.md、docs/learning/37-game-record-file-save.md、docs/knowledge/30-game-record-file-save.md、docs/handover-cli-save-load.md、kaname_shogi/cli.py、kaname_shogi/game_record.py、tests/test_cli.py、tests/test_game_record.pyを読み、git status --short --branchで現在の状態を確認してください。必要最小限の一次資料を確認し、保存形式を担うGameRecordと、save/load入力・表示・再入力を担うCLI進行を切り分けてください。対象範囲を確認問題として一度に一問ずつ出し、私の回答を待ちながら合意してください。少なくとも、save/loadの入力形式と保存先、読込後の局面・手番・表示、失敗時の再入力、終局状態、GameRecordの置換と記録範囲を確認してください。設計合意と設計書承認までコードやテストを書かないでください。承認後にmainではない作業ブランチでTDD、独立レビュー、全検証、学習記録、mainへの取り込みを行い、最後に理解確認を一問だけ出してください。コミットメッセージは日本語のConventional Commitにしてください。
```
