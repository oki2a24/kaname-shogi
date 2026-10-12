"""期限・停止要求・予備手保護の契約を固定時刻で確認する。"""

import unittest

from kaname_shogi.search_control import SearchControl, SearchSignal
from kaname_shogi.time_management import SearchBudget


class SearchControlTests(unittest.TestCase):
    def test_deadline_boundaries(self):
        """目標は候補開始時だけ、上限は常に一致から停止する。

        単位誤換算、境界の不包含、目標と上限の混同を検出する。
        """
        for now, target, expected in (
            (1009999999, True, SearchSignal.CONTINUE),
            (1010000000, True, SearchSignal.STOP),
            (1010000001, True, SearchSignal.STOP),
            (1010000001, False, SearchSignal.CONTINUE),
            (1019999999, False, SearchSignal.CONTINUE),
            (1020000000, False, SearchSignal.STOP),
            (1020000001, False, SearchSignal.STOP),
        ):
            with self.subTest(now=now, target=target):
                c = SearchControl(
                    SearchBudget(10, 20), 1000000000, now_ns=lambda now=now: now
                )
                self.assertEqual(c.check(include_target=target), expected)

    def test_uses_received_origin(self):
        """構築前の受渡し遅延も予算へ含める。

        構築時へ原点を置き換える誤りを検出する。
        """
        c = SearchControl(SearchBudget(10, 20), 1000000000, now_ns=lambda: 1021000000)
        self.assertEqual(c.check(), SearchSignal.STOP)

    def test_preserves_large_integer_budget(self):
        """巨大予算でも整数の期限直前と一致を区別する。

        float化や独自の時間上限を検出する。
        """
        now = 10**406
        c = SearchControl(SearchBudget(10**400, 10**400), 1, now_ns=lambda: now)
        self.assertEqual(c.check(), SearchSignal.CONTINUE)
        now += 1
        self.assertEqual(c.check(), SearchSignal.STOP)

    def test_validates_origin_type_without_restricting_sign(self):
        """原点の型を検査し、負の単調時計原点も許す。

        boolの整数扱いと絶対時刻への不要な非負制限を検出する。
        """
        for value in (True, False, 1.0, "1", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                SearchControl(None, value)
        now = -990000001
        c = SearchControl(SearchBudget(10, 20), -1000000000, now_ns=lambda: now)
        self.assertEqual(c.check(include_target=True), SearchSignal.CONTINUE)
        now += 1
        self.assertEqual(c.check(include_target=True), SearchSignal.STOP)

    def test_distinguishes_no_budget_and_zero(self):
        """時計なしは期限を設けず、明示0は停止要求となる。

        0予算を時計なしへ読み替える誤りを検出する。
        """
        for budget, expected in (
            (None, SearchSignal.CONTINUE),
            (SearchBudget(0, 0), SearchSignal.STOP),
        ):
            with self.subTest(budget=budget):
                c = SearchControl(budget, 0, now_ns=lambda: 10**20)
                self.assertEqual(c.check(), expected)
        c = SearchControl(SearchBudget(0, 1), 0, now_ns=lambda: 0)
        self.assertEqual(c.check(), SearchSignal.CONTINUE)
        self.assertEqual(c.check(include_target=True), SearchSignal.STOP)

    def test_protects_only_ordinary_stop(self):
        """予備手保護は期限と通常stopを保留し、抑制を保留しない。

        抑制まで保護して終了不能になる誤りを検出する。
        """
        c = SearchControl(SearchBudget(0, 0), 0, now_ns=lambda: 0)
        self.assertEqual(
            c.check(protect_first_legal=True, include_target=True),
            SearchSignal.CONTINUE,
        )
        c.request_stop()
        self.assertEqual(
            c.check(protect_first_legal=True, include_target=True),
            SearchSignal.CONTINUE,
        )
        self.assertEqual(c.check(), SearchSignal.STOP)
        c.request_stop(suppress_response=True)
        self.assertEqual(c.check(protect_first_legal=True), SearchSignal.SUPPRESS)

    def test_suppression_is_monotonic(self):
        """反復stopで一度立った抑制を解除しない。

        通常stopによる上書きと要求の使い捨てを検出する。
        """
        c = SearchControl(None, 0)
        c.request_stop()
        self.assertEqual(c.check(), SearchSignal.STOP)
        c.request_stop(suppress_response=True)
        c.request_stop()
        for protected in (False, True):
            self.assertEqual(
                c.check(protect_first_legal=protected), SearchSignal.SUPPRESS
            )

    def test_new_control_does_not_inherit_stop(self):
        """別探索の制御へ停止を継承しない。

        クラス共有フラグによる停止残留を検出する。
        """
        first = SearchControl(None, 0)
        first.request_stop()
        second = SearchControl(None, 0)
        self.assertEqual(first.check(), SearchSignal.STOP)
        self.assertEqual(second.check(), SearchSignal.CONTINUE)
