"""開発用比較の合否・表示・終了・例外境界を確認する。"""

import contextlib
import io
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from kaname_shogi.search import compare
from kaname_shogi.search.result import SearchResult
from kaname_shogi.usi_move import parse_usi_move

KINGS = "8k/9/9/9/9/9/9/9/K8 b - 1"


class CompareTests(unittest.TestCase):
    def invoke(self, args):
        """実コマンド操作の出力先を捕捉する。"""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = compare.main(args)
        return code, out.getvalue(), err.getvalue()

    def test_matches_exact_values_and_best_membership(self):
        """同点の別手を許容し、低い手・異なる評価・片側手なしを拒否する。

        選択手完全一致だけや評価一致だけの判定を検出する。
        """
        a, b, c = map(parse_usi_move, ("9i9h", "9i8h", "9i8i"))
        full = SearchResult((0, 3), a, 7, ((a, (0, 3)), (b, (0, 3)), (c, (0, -2))))
        pruned = SearchResult((0, 3), b, 6, None)
        self.assertTrue(compare.results_match(full, pruned))
        for bad in (
            replace(pruned, move=c),
            replace(pruned, score=(0, 2)),
            replace(pruned, move=None),
        ):
            self.assertFalse(compare.results_match(full, bad))
        self.assertFalse(compare.results_match(replace(full, move=c), pruned))
        empty = SearchResult((-1, 0), None, 1, ())
        self.assertTrue(compare.results_match(empty, replace(empty, root_scores=None)))
        self.assertFalse(compare.results_match(empty, pruned))

    def test_formats_board_promotion_drop_and_no_move(self):
        """移動・成り・打ちと手なしを二つの表記で説明する。

        成りや駒種・筋段の取り違えを検出する。
        """
        for token, expected in (
            ("5e5d", "5e5d（5五→5四）"),
            ("2d2c+", "2d2c+（2四→2三・成り）"),
            ("P*5e", "P*5e（5五に歩を打つ）"),
            ("R*2b", "R*2b（2二に飛を打つ）"),
        ):
            self.assertEqual(compare.format_move(parse_usi_move(token)), expected)
        self.assertEqual(compare.format_move(None), "なし")

    def test_success_runs_fixed_depths_and_reports_results(self):
        """実局面を固定深さで独立探索し、各方式の結果を標準出力へ出す。

        深さの省略・一方式だけの成功・診断の出力先混在を検出する。
        """
        full_search, alpha_search = compare.minimax.search, compare.alpha_beta.search
        with (
            patch.object(compare.minimax, "search", wraps=full_search) as full,
            patch.object(compare.alpha_beta, "search", wraps=alpha_search) as alpha,
        ):
            code, out, err = self.invoke(["--sfen", KINGS])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn(KINGS, out)
        self.assertIn("先手", out)
        for name in ("全幅", "αβ"):
            for depth in (2, 3, 4):
                self.assertIn(f"{depth}\t{name}\t", out)
        self.assertIn("9i9h（9九→9八）", out)
        self.assertIn("2\t全幅\t＋0\t9i9h（9九→9八）\t13", out)
        self.assertIn("2\tαβ\t＋0\t9i9h（9九→9八）\t9", out)
        self.assertIn("全深さで比較成功", out)
        self.assertEqual([c.args[1] for c in full.call_args_list], [2, 3, 4])
        self.assertEqual([c.args[1] for c in alpha.call_args_list], [2, 3, 4])

    def test_mismatch_continues_and_returns_one(self):
        """一深さの不一致でも後続を比較し、合否と診断を出し分ける。

        早期終了や不一致を成功と報告する誤りを検出する。
        """
        real = compare.alpha_beta.search

        def altered(*args):
            result = real(*args)
            return replace(result, score=(0, 1)) if args[1] == 2 else result

        with patch.object(compare.alpha_beta, "search", side_effect=altered) as search:
            code, out, err = self.invoke(["--sfen", KINGS])
        self.assertEqual(code, 1)
        self.assertEqual(search.call_count, 3)
        self.assertIn("深さ2: 比較不一致", out)
        self.assertIn("深さ4: 比較成功", out)
        self.assertIn("深さ2", err)
        self.assertNotIn("全深さで比較成功", out)

    def test_invalid_input_does_not_search(self):
        """不正入力は探索せず終了2、ヘルプは終了0にする。

        不正SFENの探索開始とargparseの例外漏れを検出する。
        """
        for args in ([], ["--sfen", "invalid"], ["--sfen", KINGS, "--depth", "3"]):
            with (
                self.subTest(args=args),
                patch.object(compare.minimax, "search") as search,
            ):
                code, out, err = self.invoke(args)
                self.assertEqual(code, 2)
                self.assertTrue(err)
                self.assertEqual(out, "")
                search.assert_not_called()
        code, out, err = self.invoke(["--help"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("--sfen", out)

    def test_search_value_error_is_not_input_error(self):
        """入力解析後の内部故障は不正SFENへ変換しない。

        広すぎるValueError捕捉による原因隠蔽を検出する。
        """
        with patch.object(
            compare.minimax, "search", side_effect=ValueError("内部故障")
        ):
            with (
                contextlib.redirect_stdout(io.StringIO()),
                self.assertRaisesRegex(ValueError, "内部故障"),
            ):
                compare.main(["--sfen", KINGS])

    def test_interrupt_retains_completed_rows(self):
        """片方式完了後の中断は結果を残し、実行中を未完了にする。

        後続実行、成功の誤表示、出力破棄を検出する。
        """
        with patch.object(
            compare.alpha_beta, "search", side_effect=KeyboardInterrupt
        ) as search:
            code, out, err = self.invoke(["--sfen", KINGS])
        self.assertEqual(code, 130)
        self.assertIn("2\t全幅\t", out)
        self.assertNotIn("2\tαβ\t", out)
        self.assertNotIn("全深さで比較成功", out)
        self.assertIn("深さ2", err)
        self.assertIn("αβ", err)
        self.assertIn("未完了", err)
        self.assertEqual(search.call_count, 1)

    def test_terminal_and_gote_output(self):
        """手なしと後手開始も実比較と表示の契約を守る。

        手なしを通常勝敗へ混同する表示や先手固定を検出する。
        """
        for sfen, expected in (
            ("9/9/9/9/9/9/9/9/9 b - 1", "なし"),
            (KINGS.replace(" b ", " w "), "後手"),
        ):
            code, out, err = self.invoke(["--sfen", sfen])
            self.assertEqual((code, err), (0, ""))
            self.assertIn(expected, out)

    def test_real_process_entrypoint(self):
        """実プロセスで成功・入力エラー・ヘルプの終了値を伝える。

        mainの戻り値を終了状態へ反映しない入口を検出する。
        """
        for args, code in (
            (["--sfen", KINGS], 0),
            (["--sfen", "invalid"], 2),
            (["--help"], 0),
        ):
            p = subprocess.run(
                [sys.executable, "-m", "kaname_shogi.search.compare", *args],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(p.returncode, code, p.stderr)
            if code == 2:
                self.assertTrue(p.stderr)
            elif "--sfen" in args:
                self.assertIn("全深さで比較成功", p.stdout)
