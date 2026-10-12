# 時計設定と時間予算の参照メモ

[承認済み計画](../plans/2026-10-12-time-budget-implementation-plan.md)、[全体設計](../plans/2026-10-11-clock-input-time-management-design.md)、[実装記録](../learning/time-budget-implementation-plan.md)。

`kaname_shogi.time_management` はJSON設定読込と整数msの予算計算を提供する。USI起動入口からの時計検証・自分側選択・設定保持・予算計算は接続済み。探索の時間停止はまだ働かない。

- `TimeManagementConfig` は時間設定データ、`SearchBudget` は目標/上限期間のデータ。不変で、構築時に型と範囲を検証する。
- `load_time_management_config` は設定を読む操作。引数省略時はモジュール位置からリポジトリ直下の `config/time-management.json` を読む。明示相対Pathはcwd基準。キャッシュなし。
- `calculate_search_budget` は自分側の残り持ち時間・秒読み（非負整数ms）と設定から予算を計算する操作。先後の選択・時刻取得・期限判定はしない。

四設定はallocation_turns=20（整数1以上）、maximum_multiplier=2（有限数1超）、byoyomi_target_ratio=0.75（有限数0超1未満）、response_margin_ms=2000（整数0以上）。値は採用済みの未検証暫定値。JSONの整数欄は整数表記、係数欄は整数/十進数を許す。必須・重複・未知・bool等を検査し、代替既定値は使わない。十進表記をDecimalで保持しFractionへ変換、整数演算で切り捨てる。

R>0では基本目標=R//N、境界=max(0,R+B−S)、上限=min(floor(基本目標×M),境界)、目標=min(基本目標,上限)。R=0では上限=max(0,B−S)、目標=floor(上限×q)。分母Nは固定。時間はms。

不正JSON・値・文字コードはValueError、読込失敗はOSError。パスと理由を例外へ含める。mainは入力受付前に一回読み、runへ注入して実行中固定する。設定故障はstderr診断・終了1。run直接呼出しはtime_config省略時だけ一回読み、例外を伝達する。巨大値はfloatへ変換しないが資源制限は残る。期限内応答・最適性・任意サイズの入力処理成功は保証しない。

技術根拠: [Python JSON](https://docs.python.org/3.9/library/json.html)、[Decimal](https://docs.python.org/3.9/library/decimal.html)、[Fraction](https://docs.python.org/3.9/library/fractions.html)。

USI時計のNoneは時計なし、SearchBudget(0,0)は明示時計から計算した0期間。現在はどちらも通常の有限比較を完了して返す。期限判定・探索停止への接続は後続。[時計受付・接続計画](../plans/2026-10-12-usi-clock-settings-implementation-plan.md)、[実施記録](../learning/usi-clock-settings-implementation-plan.md)。
