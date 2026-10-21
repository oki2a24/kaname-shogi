"""並列unittestランナーがテストを漏れなく実行し、失敗を伝えることを確認する。"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_tests_parallel as parallel


class ParallelTestRunnerTests(unittest.TestCase):
    """一時プロジェクトを使い、ランナーの入出力契約を確認する。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tests_dir = self.root / "tests"
        self.tests_dir.mkdir()
        (self.root / "project-marker").touch()

    def write_test(self, relative_path, source):
        path = self.tests_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return path

    def test_discovery_matches_unittest_pattern_and_package_recursion(self):
        """test*.pyとpackage配下だけを標準の並びで発見する。

        補助モジュールやpackageでないサブディレクトリを誤って実行する漏れを検出する。
        """
        self.write_test("test_zeta.py", "")
        self.write_test("test_alpha.py", "")
        self.write_test("helper.py", "")
        self.write_test("not_a_package/test_hidden.py", "")
        self.write_test("package/__init__.py", "")
        self.write_test("package/test_gamma.py", "")
        self.write_test("package/nested/__init__.py", "")
        self.write_test("package/nested/test_delta.py", "")

        self.assertEqual(
            parallel.discover_test_modules(self.tests_dir),
            [
                "package.nested.test_delta",
                "package.test_gamma",
                "test_alpha",
                "test_zeta",
            ],
        )

    def test_empty_discovery_returns_no_modules_for_cli_to_reject(self):
        """テストモジュールがない状態を空として検出する。

        テスト0件のまま成功終了する誤りを検出する。
        """
        self.assertEqual(parallel.discover_test_modules(self.tests_dir), [])

        stderr = io.StringIO()
        with (
            patch.object(parallel, "PROJECT_ROOT", self.root),
            contextlib.redirect_stderr(stderr),
        ):
            with self.assertRaises(SystemExit) as raised:
                parallel.main([])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("No test modules found", stderr.getvalue())

    def test_successful_modules_run_once_and_aggregate_test_counts(self):
        """各モジュールを一回ずつ標準unittestで実行し件数を集約する。

        import path・作業ディレクトリの欠落やモジュールの二重実行を検出する。
        """
        self.write_test(
            "test_alpha.py",
            """import sys
import unittest
from pathlib import Path

class AlphaTests(unittest.TestCase):
    def test_environment_is_explicit(self):
        self.assertTrue((Path.cwd() / "project-marker").exists())
        self.assertIn(str(Path(__file__).parent), sys.path)
""",
        )
        self.write_test(
            "package/__init__.py",
            "",
        )
        self.write_test(
            "package/test_beta.py",
            """import unittest

class BetaTests(unittest.TestCase):
    def test_package_module_runs(self):
        self.assertTrue(True)
""",
        )

        modules = parallel.discover_test_modules(self.tests_dir)
        results = parallel.run_test_modules(
            modules,
            tests_dir=self.tests_dir,
            repo_root=self.root,
            workers=2,
        )

        self.assertEqual([result.module for result in results], modules)
        self.assertEqual([result.test_count for result in results], [1, 1])
        self.assertTrue(all(result.returncode == 0 for result in results))
        self.assertEqual(sum(result.test_count for result in results), 2)
        self.assertIn("Ran 1 test", results[0].stdout + results[0].stderr)

    def test_requested_workers_are_applied_as_executor_limit(self):
        """指定したworkers数を同時実行の上限として渡す。

        指定値を無視してワーカーを増やし、CPUや共有資源を過剰に使う誤りを検出する。
        """
        self.write_test("test_alpha.py", "")
        self.write_test("test_beta.py", "")
        modules = parallel.discover_test_modules(self.tests_dir)

        with patch.object(
            parallel, "ThreadPoolExecutor", wraps=parallel.ThreadPoolExecutor
        ) as executor:
            parallel.run_test_modules(
                modules,
                tests_dir=self.tests_dir,
                repo_root=self.root,
                workers=2,
            )

        executor.assert_called_once_with(max_workers=2)

    def test_default_workers_are_capped_at_four_and_available_cpus(self):
        """既定workers数はCPU数を超えず最大4になる。

        小さいマシンで過剰に並列化したり、大きいマシンで無制限に増やしたりする誤りを検出する。
        """
        for cpu_count, expected in ((1, 1), (2, 2), (8, 4), (None, 1)):
            with self.subTest(cpu_count=cpu_count):
                with patch.object(parallel.os, "cpu_count", return_value=cpu_count):
                    self.assertEqual(parallel._default_worker_count(), expected)

    def test_nonpositive_workers_are_rejected(self):
        """workersに0以下を指定すると引数エラーで終了する。

        無効な値で逐次化したり、executor例外を利用者へ漏らしたりする誤りを検出する。
        """
        stderr = io.StringIO()
        with (
            patch.object(parallel, "PROJECT_ROOT", self.root),
            contextlib.redirect_stderr(stderr),
        ):
            for value in ("0", "-1"):
                with self.subTest(value=value):
                    with self.assertRaises(SystemExit) as raised:
                        parallel.main(["--workers", value])
                    self.assertEqual(raised.exception.code, 2)

        self.assertIn("workers must be at least 1", stderr.getvalue())

    def test_any_failed_module_returns_failure_and_keeps_diagnostics(self):
        """一つの失敗を非0終了と診断出力として呼出し元へ返す。

        失敗workerを成功扱いしたり、assertionの詳細を捨てたりする誤りを検出する。
        """
        self.write_test(
            "test_failure.py",
            """import unittest

class FailureTests(unittest.TestCase):
    def test_expected_failure(self):
        self.fail("intentional worker failure")
""",
        )

        result = parallel.run_test_modules(
            ["test_failure"],
            tests_dir=self.tests_dir,
            repo_root=self.root,
            workers=1,
        )[0]

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.test_count, 1)
        self.assertIn("intentional worker failure", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
