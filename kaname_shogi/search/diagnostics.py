"""探索診断で使う任意計数データ。"""

from dataclasses import dataclass


@dataclass
class SearchCounters:
    """通常探索の調査入口と静止探索の呼出しを分けて数える可変データ。

    normal_nodesは通常探索が将棋用inspect操作へ入った回数。初期予備手準備と
    静止探索内部の調査は含めない。quiescence_callsは中断を含む静止探索関数への
    有効な呼出し回数。両者を合算して異なる局面数とはみなさない。
    """

    normal_nodes: int = 0
    quiescence_calls: int = 0
