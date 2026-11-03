# 残存未追跡データと退避物の期限付き整理

## 目的と開始条件

この文書は、作業checkoutに残る未追跡の比較出力・作業メモ・保全アーカイブを、内容を失わずに整理するための再開手順である。日付は整理の自動許可ではない。各セッションの開始時にAsia/Tokyoの現在日付を確認し、以下の次回判定日と比較する。期限前は対象を変更せず、空の進捗報告を繰り返さない。期限後は現行のGit状態、本人の保護指定、保存先をその都度確認する。

**削除・移動・上書き・ステージは禁止:** `.agents/tasks/`、`.antigravity/tasks/`、`data/comparison/runs/` の未追跡成果物、C2保護4件、`migration-preservation-2026-11-01/`、`worktree-preservation-2026-11-01/`。本人が保護解除を明示するまで維持する。

## 2026-11-03時点の記録

- 文書整理開始時の基点は `/Users/oki2a24/kaname-shogi` の `main` と `origin/main` が一致する `d9a9d8e38b9276492833cf03a01abfeef2dfff2b`。追跡ファイルはcleanで、比較成果物と保全アーカイブは未追跡のまま保持されていた。
- 作業ブランチは `codex/session-start-cleanup-gate`。別worktree・別cloneは使わない。
- 未追跡比較データはC1確認比較・追試・pilotとU価値確認比較で、概算合計約794MB。対応する記録は `docs/learning/c1-rook-mobility-evaluation.md` と `docs/learning/undefended-piece-value.md` にある。C1確認比較は4,080局、追試も4,080局、追試pilotは120局、U価値確認比較は4,074局の完了summaryを持つ。seed・条件・summary・analysisと保存棋譜の対応を削除前に照合する。
- 退避物は `migration-preservation-2026-11-01/` が約175MB、`worktree-preservation-2026-11-01/` が約480MB。B2統合worktreeのtarにはC2保護4件と `.agents/tasks/` が含まれる。退避作成時の照合範囲と限界は `worktree-preservation-2026-11-01/README.md` と `docs/learning/workspace-knowledge-consolidation.md` に記録されている。
- 2026-11-03に3つの `.venv.backup-*` を誤って削除した。対象名は `.venv.backup-2026-10-22/`、`.venv.backup-2026-10-25-broken-python-3150/`、`.venv.backup-2026-11-01-broken-python-3151/`。ホーム内、Trash、`.codex`、確認できた保全tar、Time Machineの保存先とローカルsnapshotからは原本を見つけられなかった。別内容を原本として作り直さない。現行 `.venv` とこの探索結果は次回も実物に照合する。
- 比較データのcheckout外保管先は本人が2027-02-01頃に決めると回答した。2026-11-03時点では `/Volumes` に外付け媒体はなく、Time Machineの保存先もなかった。保管先を推測して作成・複製しない。
- 次の主線である非駒得評価項目の選定は未完了のまま維持する。この整理を理由に完了扱いしない。

## 第1段階：2026-12-03以降に退避物を検証

開始前に `git status --short --branch`、`git rev-parse main`、`git rev-parse HEAD`、`git rev-parse origin/main`、`git worktree list` を現在のcheckoutで確認し、保護対象の現状を確認する。過去のbranch・hash・件数を現在値とみなさない。

次のアーカイブを読み取り専用で再確認する。

1. `migration-preservation-2026-11-01/` と `worktree-preservation-2026-11-01/` の各ファイルのSHA-256を取り、以下の2026-11-03基準値と比較する。
2. 各tarを `tar -tf` で走査し、可能なら内容をファイルへ展開せず `tar -xOf <archive> >/dev/null` で読み通せることを確認する。bundleは `git bundle verify migration-preservation-2026-11-01/clone-all-refs.bundle` で検証する。
3. `worktree-preservation-2026-11-01/b2-main-integration.tar` 内にC2保護4件と `.agents/tasks/` が存在することを確認する。tarの読込可能性やhash一致を、展開後の実用性確認と混同しない。
4. 新しい同等の保管コピーがあるか、元ファイルと照合して確認する。新規コピー作成・配置には本人が選んだ保存先を使い、既存の保護対象を動かさない。
5. 検証日・コマンド・件数・hash・確認できた範囲・未検証事項をこの文書へ追記する。検証が全て成功した日から30日間は削除しない。12月3日に検証完了した場合の最短再検討日は2027-01-02。1項目でも不一致・未検証があれば猶予期間を開始せず、原因を調べる。

### SHA-256基準値（2026-11-03取得）

| ファイル | SHA-256 |
| --- | --- |
| `migration-preservation-2026-11-01/clone-ignored-artifacts.tar` | `80658831f8b057b13a8eee5314bd941c50e5070256a5488810f82c4da7438447` |
| `migration-preservation-2026-11-01/clone-all-refs.bundle` | `7cb37684338353177635b063a3d7c65eb81a02ad0f6c1c84ef007e9aa3464ba6` |
| `migration-preservation-2026-11-01/original-documents.tar` | `2826220bfc5d7acd82fe76a328ba43e6e606a821023515b161f1ac3956cc4a8c` |
| `migration-preservation-2026-11-01/original-tracked-changes.patch` | `7f206f0b4b785f590c0703b04e574317b4f11fef28585b58c8f2660aedd2a83f` |
| `migration-preservation-2026-11-01/clone-complete-2026-11-01.tar` | `13d52a03c41104ec9a05de157ece8ebcb15e828b487955c5743c2d9aa209fc82` |
| `worktree-preservation-2026-11-01/55-usi-move-notation.md` | `53ac4c383e7154f92837d57bdf454f202872e86199e167edcb0caad4d94c864e` |
| `worktree-preservation-2026-11-01/README.md` | `2d4718d2eda7b26e105a3f08ee9c5b4fa5a538dbe0a91a4e2d6c558f82bf0ccb` |
| `worktree-preservation-2026-11-01/b2-main-integration.tar` | `60c4ec54270b3e7e9fe3951200234c3a4bdbb2dc3d405a4feb89ef4e96577bd1` |
| `worktree-preservation-2026-11-01/c1-analysis-resume.tar` | `b60c60b3f12c22e9715fd897ab7ca586e297f1650d0546835816a9afde1886f3` |
| `worktree-preservation-2026-11-01/c1-analysis-speedup.tar` | `3ffd579e5952948584c9d2a0fa4f4a47f169b04035abaad96861b65951d36c4e` |
| `worktree-preservation-2026-11-01/undefended-piece-integration.tar` | `9fc9b98082e20a9b41b091b94231812a833fcbe94ca82c1525b83e4bb9604b51` |
| `worktree-preservation-2026-11-01/usi-move-notation-record.tar` | `9dd122279f6cd34dc11ef28949ac15891ca79c8499ebe0c122d145cac0ac22d7` |
| `worktree-preservation-2026-11-01/usi-move-notation-uncommitted.patch` | `19e208e618a167b7052a0c551e348287470d5aed8a360b29679fdfc58419922e` |

## 第2段階：2027-02-01以降に比較データを判断

セッション開始時に本人へcheckout外の保管先を確認する。選択後、その場所の現在状態と空き容量を確認し、合意した対象だけを新規の一意な保存先に複製する。複製後、全ファイルの件数とSHA-256を原本と照合し、seed・条件・summary・analysis・学習記録が相互参照できることを確認する。外付け媒体が接続されていない場合や、保存先・検証に不一致がある場合は原本を残す。

比較結果の生棋譜は現在の保護指示が有効な間、削除・移動・上書き・一括ステージしない。本人が保護解除を明示し、確認済みコピーと文書参照を再確認した場合に限り、対象を個別に選んでcheckout内の重複を整理する。C2保護4件と `.agents/tasks/` を含むB2アーカイブは、他のC1/U比較データと一緒に扱わず、本人が別途解除するまで保全する。

## セッション再開時の判定

- 2026-12-02以前：Git状態のみ通常の再開手順で確認し、保全物には触れない。期限前の同じ待機報告は繰り返さない。
- 2026-12-03以降：第1段階を実施し、成功した場合だけ実際の検証日から30日後を次回判定日にする。
- 2027-02-01以降：第2段階に進み、保管先と保護解除が未確定なら整理を保留する。日付到来だけで削除しない。
- 実行前後に現在のGit状態を取り直し、既存の未追跡物を誤ってステージしない。
