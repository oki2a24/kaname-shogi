"""反復深化比較の順序・表示・中断・終了状態を確認する。"""

import contextlib
import io
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from kaname_shogi.search import compare_iterative
from kaname_shogi.search.result import IterationResult, SearchResult
from kaname_shogi.usi_move import parse_usi_move

KINGS = "8k/9/9/9/9/9/9/9/K8 b - 1"


class CompareIterativeTests(unittest.TestCase):
    def invoke(self, args):
        """実mainの戻り値と二つの出力先を捕捉する。"""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = compare_iterative.main(args)
        return code, out.getvalue(), err.getvalue()

    def test_real_results_and_three_counts(self):
        """実局面を深さ1から4まで比較し、今回分と累計を区別する。

        深さ省略・全幅訪問の混入・累計置換を検出する。
        """
        code, out, err = self.invoke(["--sfen", KINGS])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("完了した深さまで", out)
        self.assertIn("9i9h（9九→9八）", out)
        rows = [
            line.split("\t")
            for line in out.splitlines()
            if line[:1] in "1234" and "\t" in line
        ]
        self.assertEqual([int(row[0]) for row in rows], [1, 2, 3, 4])
        self.assertEqual(
            [list(map(int, row[-3:])) for row in rows],
            [[4, 4, 4], [9, 9, 13], [29, 29, 42], [64, 64, 106]],
        )
        self.assertTrue(all("比較成功" in row[3] for row in rows))
        self.assertIn("全深さで比較成功", out)

    def test_order_and_three_counts(self):
        """取得後に全幅・単独を実行し、反復以外の訪問を累計に入れない。

        確認用探索の先行・次深さの先行・計数混在を検出する。
        """
        move = parse_usi_move("9i9h")
        result = SearchResult((0, 0), move, 3, None)
        events = []

        def stream(node, max_depth, operations):
            self.assertEqual(max_depth, 4)
            for depth, visits, total in ((1, 3, 3), (2, 7, 10)):
                events.append(("反復", depth))
                yield IterationResult(
                    depth, replace(result, visited_nodes=visits), total
                )

        def full(node, depth, operations):
            events.append(("全幅", depth))
            return replace(result, root_scores=((move, (0, 0)),), visited_nodes=99)

        def standalone(node, depth, operations):
            events.append(("単独", depth))
            return replace(result, visited_nodes=11)

        with (
            patch.object(
                compare_iterative.iterative_deepening, "search", side_effect=stream
            ),
            patch.object(compare_iterative.minimax, "search", side_effect=full),
            patch.object(
                compare_iterative.alpha_beta, "search", side_effect=standalone
            ),
        ):
            code, out, err = self.invoke(["--sfen", KINGS])
        self.assertEqual(
            events,
            [
                ("反復", 1),
                ("全幅", 1),
                ("単独", 1),
                ("反復", 2),
                ("全幅", 2),
                ("単独", 2),
            ],
        )
        self.assertEqual((code, err), (0, ""))
        self.assertIn("\t11\t3\t3", out)
        self.assertIn("\t11\t7\t10", out)

    def test_mismatch_continues(self):
        """深さ2の不一致後も深さ4まで実行して終了1を返す。

        早期打切り・不一致の成功扱いを検出する。
        """
        real = compare_iterative.minimax.search

        def altered(node, depth, operations):
            r = real(node, depth, operations)
            return replace(r, score=(0, 99)) if depth == 2 else r

        with patch.object(compare_iterative.minimax, "search", side_effect=altered):
            code, out, err = self.invoke(["--sfen", KINGS])
        self.assertEqual(code, 1)
        self.assertIn("深さ2", err)
        self.assertIn("4\t", out)
        self.assertIn("比較不一致", out)
        self.assertNotIn("全深さで比較成功", out)

    def test_interrupt_during_iteration(self):
        """反復途中の中断は最新完了だけを残し、未完了を公開しない。

        深さ1以前の偽完了・最後の完了結果の消失を検出する。
        """
        real = compare_iterative.iterative_deepening.search
        for stop in (1, 3):

            def interrupted(node, max_depth, operations, stop=stop):
                iterator = real(node, max_depth, operations)
                for depth in range(1, max_depth + 1):
                    if depth == stop:
                        raise KeyboardInterrupt
                    yield next(iterator)

            with patch.object(
                compare_iterative.iterative_deepening, "search", side_effect=interrupted
            ):
                code, out, err = self.invoke(["--sfen", KINGS])
            self.assertEqual(code, 130)
            self.assertIn(f"深さ{stop}・反復深化", err)
            self.assertIn("未完了", err)
            self.assertNotIn("全深さで比較成功", out)
            if stop == 1:
                self.assertIn("完了結果なし", err)
            else:
                self.assertIn("反復深化：深さ2まで完了", err)
                self.assertIn("反復累計（完了した深さまで）=13", err)
                self.assertIn("9i9h", err)
                self.assertNotIn("反復深化：深さ3まで完了", err)

    def test_interrupt_during_reference_search(self):
        """反復完了後の確認用探索中断は比較だけを未完了にする。

        完了深さの巻戻し・未比較の成功表示を検出する。
        """
        for module in (compare_iterative.minimax, compare_iterative.alpha_beta):
            real = module.search

            def interrupted(node, depth, operations, real=real, **kwargs):
                # αβは反復内部からも呼ばれる。優先指定のない単独だけを中断。
                if depth == 3 and not kwargs:
                    raise KeyboardInterrupt
                return real(node, depth, operations, **kwargs)

            with patch.object(module, "search", side_effect=interrupted):
                code, out, err = self.invoke(["--sfen", KINGS])
            self.assertEqual(code, 130)
            self.assertIn("反復深化：深さ3まで完了", err)
            self.assertIn("深さ3の比較：未完了", err)
            self.assertIn("比較完了深さ：2", err)
            self.assertNotIn("全深さで比較成功", out)

    def test_mismatch_then_interrupt(self):
        """不一致の後で中断したら証拠を残して130を返す。

        不一致による終了1の誤優先と診断消去を検出する。
        """
        real = compare_iterative.minimax.search

        def altered(node, depth, operations):
            if depth == 3:
                raise KeyboardInterrupt
            r = real(node, depth, operations)
            return replace(r, score=(0, 99)) if depth == 2 else r

        with patch.object(compare_iterative.minimax, "search", side_effect=altered):
            code, out, err = self.invoke(["--sfen", KINGS])
        self.assertEqual(code, 130)
        self.assertIn("比較不一致", out)
        self.assertIn("深さ2", err)
        self.assertFalse(any(line.startswith("4\t") for line in out.splitlines()))

    def test_terminal_compares_only_depth_one(self):
        """手なしは深さ1だけ比較し、全4深さの実行と混同しない。

        不要な反復・手なし時の比較省略を検出する。
        """
        events = []
        real = compare_iterative.minimax.search

        def observed(node, depth, operations):
            events.append(depth)
            return real(node, depth, operations)

        with patch.object(compare_iterative.minimax, "search", side_effect=observed):
            code, out, err = self.invoke(["--sfen", "9/9/9/9/9/9/9/9/9 b - 1"])
        self.assertEqual((code, err, events), (0, "", [1]))
        self.assertIn("手なしで終了", out)
        self.assertIn("比較成功", out)
        self.assertNotIn("全深さで比較成功", out)

    def test_input_and_internal_errors(self):
        """入力誤りだけを終了2とし、探索内の故障を伝える。

        SFEN不正での探索開始・単独αβの例外隠蔽・広すぎる例外捕捉を検出する。
        """
        for args in ([], ["--sfen", "invalid"], ["--sfen", KINGS, "--depth", "3"]):
            with patch.object(
                compare_iterative.iterative_deepening, "search"
            ) as search:
                code, out, err = self.invoke(args)
            self.assertEqual(code, 2)
            self.assertEqual(out, "")
            self.assertTrue(err)
            search.assert_not_called()
        code, out, err = self.invoke(["--help"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("--sfen", out)
        for module in (
            compare_iterative.iterative_deepening,
            compare_iterative.minimax,
        ):
            with patch.object(module, "search", side_effect=ValueError("内部故障")):
                with self.assertRaisesRegex(ValueError, "内部故障"):
                    self.invoke(["--sfen", KINGS])

        real_alpha_beta = compare_iterative.alpha_beta.search
        calls = []

        def fail_standalone(node, depth, operations, **kwargs):
            if "preferred_move" in kwargs:
                calls.append(("反復", depth))
                return real_alpha_beta(node, depth, operations, **kwargs)
            calls.append(("単独", depth))
            raise ValueError("単独探索の内部故障")

        with patch.object(
            compare_iterative.alpha_beta, "search", side_effect=fail_standalone
        ):
            with self.assertRaisesRegex(ValueError, "単独探索の内部故障"):
                self.invoke(["--sfen", KINGS])
        self.assertEqual(calls, [("反復", 1), ("単独", 1)])

    def test_real_process_entrypoint(self):
        """実プロセスが成功・入力エラー・ヘルプの終了値を伝える。

        mainの値を終了状態へ接続し忘れる誤りを検出する。
        """
        for args, code in (
            (["--sfen", KINGS], 0),
            (["--sfen", KINGS.replace(" b ", " w ")], 0),
            (["--sfen", "invalid"], 2),
            (["--help"], 0),
        ):
            p = subprocess.run(
                [sys.executable, "-m", "kaname_shogi.search.compare_iterative", *args],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(p.returncode, code, p.stderr)
            if code == 0 and "--sfen" in args:
                self.assertIn("全深さで比較成功", p.stdout)
                if " w " in args[1]:
                    self.assertIn("後手", p.stdout)
