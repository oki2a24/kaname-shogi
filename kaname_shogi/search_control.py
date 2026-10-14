"""探索の期限と停止要求を扱う。"""

import time
from collections.abc import Callable
from enum import Enum, auto
from threading import Lock

from .time_management import SearchBudget


class SearchSignal(Enum):
    """継続・通常停止・抑制付き停止の状態データ。"""

    CONTINUE = auto()
    STOP = auto()
    SUPPRESS = auto()


class SearchControl:
    """一探索の期限と停止要求を所有する制御データ。

    引数:
        budget: 整数msの目標/上限期間。Noneなら時間停止を設けない。
        started_ns: go行の読取り時点の整数ns。boolを拒否し、負は許す。
        now_ns: started_nsと同じ単調時計の整数nsを返す操作。
    戻り値:
        新しい制御。要求を別探索へ引き継がない。
    副作用:
        check時だけ時計を読み、停止要求を専用Lockで同期する。
    前提条件・設計理由:
        呼出し元が読取り原点を渡すことで受渡し/起動待ちも計時する。
        探索・出力・担当回収は行わず、確認点で協調停止する。
        型の違う原点はValueError。期限の整数演算にfloatを挟まない。
    """

    def __init__(
        self,
        budget: SearchBudget | None,
        started_ns: int,
        *,
        now_ns: Callable[[], int] = time.monotonic_ns,
    ):
        if type(started_ns) is not int:
            raise ValueError("started_nsは整数nsが必要です")
        self._target_ns = (
            None if budget is None else started_ns + budget.target_ms * 1_000_000
        )
        self._maximum_ns = (
            None if budget is None else started_ns + budget.maximum_ms * 1_000_000
        )
        self._now_ns = now_ns
        self._lock = Lock()
        self._stop_requested = False
        self._suppress_response = False

    def request_stop(self, *, suppress_response: bool = False) -> None:
        """停止を記録する。抑制指定は通常停止で解除せず、返り値はない。

        呼出し元が入力/故障を確定した後に使う。結果や出力には触れない。
        """
        with self._lock:
            self._stop_requested = True
            self._suppress_response = self._suppress_response or suppress_response

    def check(
        self, *, include_target: bool = False, protect_first_legal: bool = False
    ) -> SearchSignal:
        """確認点の状態を返す。目標の適用と根の保護を呼出し側が指定する。

        SUPPRESSを最優先し、保護中は通常停止のみ保留する。時計関数の呼出し中は
        Lockを保持しない。送信直前の競合を解決する共通出力Lockの代替ではない。
        """
        now = self._now_ns()
        with self._lock:
            if self._suppress_response:
                return SearchSignal.SUPPRESS
            if protect_first_legal:
                return SearchSignal.CONTINUE
            if self._stop_requested:
                return SearchSignal.STOP
        if self._maximum_ns is not None and now >= self._maximum_ns:
            return SearchSignal.STOP
        if include_target and self._target_ns is not None and now >= self._target_ns:
            return SearchSignal.STOP
        return SearchSignal.CONTINUE
