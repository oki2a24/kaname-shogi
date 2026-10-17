"""新旧コマンドで共用する入力・整形・一致判定の契約。"""

import unittest
from dataclasses import replace

from kaname_shogi.model import Side
from kaname_shogi.search import comparison
from kaname_shogi.search.result import SearchResult
from kaname_shogi.usi_move import parse_usi_move


class ComparisonTests(unittest.TestCase):
    def test_input_and_format_contracts(self):
        """SFENの手番と評価・手なしの表示を保つ。

        入力の手番欠落・符号反転・終端評価の駒得表示を検出する。
        """
        sfen = "8k/9/9/9/9/9/9/9/K8 w - 1"
        self.assertEqual(comparison.parse_position(sfen).side_to_move, Side.GOTE)
        self.assertEqual(
            comparison.make_parser("説明").parse_args(["--sfen", sfen]).sfen, sfen
        )
        with self.assertRaises(ValueError):
            comparison.parse_position("invalid")
        for score, want in (
            ((0, -2), "−2"),
            ((0, 0), "＋0"),
            ((1, 0), "勝ち"),
            ((-1, 99), "負け"),
        ):
            self.assertEqual(comparison.format_score(score), want)
        self.assertEqual(comparison.format_move(None), "なし")
        self.assertEqual(
            comparison.format_move(parse_usi_move("P*5e")), "P*5e（5五に歩を打つ）"
        )

    def test_match_accepts_ties_rejects_wrong_score_or_move(self):
        """同点別手を許容し、低い手と評価違いを拒否する。

        手の完全一致だけ・評価だけの比較への退行を検出する。
        """
        a, b, c = map(parse_usi_move, ("9i9h", "9i8h", "9i8i"))
        full = SearchResult((0, 3), a, 7, ((a, (0, 3)), (b, (0, 3)), (c, (0, -2))))
        other = SearchResult((0, 3), b, 6, None)
        self.assertEqual(comparison.best_moves(full), (a, b))
        self.assertTrue(comparison.results_match(full, other))
        self.assertFalse(comparison.results_match(full, replace(other, move=c)))
        self.assertFalse(comparison.results_match(full, replace(other, score=(0, 2))))
