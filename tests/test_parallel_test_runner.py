"""並列unittestランナーがテストを漏れなく実行し、失敗を伝えることを確認する。"""

import contextlib
import io
import os
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
        self.write_test("test_alpha.copy.py", "")
        self.write_test("helper.py", "")
        self.write_test("not_a_package/test_hidden.py", "")
        self.write_test(
            "package/__init__.py",
            """import unittest

class PackageInitTests(unittest.TestCase):
    def test_package_initializer_is_discovered(self):
        pass
""",
        )
        self.write_test("package/test_gamma.py", "")
        self.write_test(
            "package/nested/__init__.py",
            """import unittest

class NestedPackageInitTests(unittest.TestCase):
    def test_nested_initializer_is_discovered(self):
        pass
""",
        )
        self.write_test("package/nested/test_delta.py", "")

        self.assertEqual(
            parallel.discover_test_modules(self.tests_dir),
            [
                "package",
                "package.nested",
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

    def test_cli_fails_when_discovered_modules_contain_no_tests(self):
        """実行対象モジュールがあっても全体0件ならCLIを失敗させる。

        empty packageやempty test moduleだけのsuiteを成功扱いする誤りを検出する。
        """
        for relative_path in ("package/__init__.py", "test_empty.py"):
            with self.subTest(relative_path=relative_path):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    tests_dir = root / "tests"
                    tests_dir.mkdir()
                    empty_module = tests_dir / relative_path
                    empty_module.parent.mkdir(parents=True, exist_ok=True)
                    empty_module.write_text("", encoding="utf-8")
                    stdout = io.StringIO()

                    with (
                        patch.object(parallel, "PROJECT_ROOT", root),
                        contextlib.redirect_stdout(stdout),
                    ):
                        exit_code = parallel.main(["--workers", "1"])

                    self.assertEqual(exit_code, 1)
                    self.assertIn("NO TESTS RAN", stdout.getvalue())

    def test_cli_accepts_a_module_skipped_during_setup(self):
        """setUpModuleでskipされたsuiteを0件失敗と区別する。

        正常なmodule skipまでテスト未発見として失敗にする誤りを検出する。
        """
        self.write_test(
            "test_skipped.py",
            """import unittest

def setUpModule():
    raise unittest.SkipTest("skip whole module")

class SkippedTests(unittest.TestCase):
    def test_is_skipped(self):
        self.fail("a skipped test must not run")
""",
        )
        stdout = io.StringIO()

        with (
            patch.object(parallel, "PROJECT_ROOT", self.root),
            patch.dict(os.environ, {"PYTHON_COLORS": "1"}),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = parallel.main(["--workers", "1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("skipped=1", stdout.getvalue())

    def test_package_initializer_import_failure_is_reported(self):
        """テストpackageの初期化失敗を実行失敗として報告する。

        package initializerのimport errorを再帰探索中に見落とす誤りを検出する。
        """
        self.write_test(
            "package/__init__.py", 'raise RuntimeError("package import failed")\n'
        )
        self.write_test("package/test_child.py", "")

        modules = parallel.discover_test_modules(self.tests_dir)
        results = parallel.run_test_modules(
            modules,
            tests_dir=self.tests_dir,
            repo_root=self.root,
            workers=2,
        )
        package_result = next(
            result for result in results if result.module == "package"
        )

        self.assertNotEqual(package_result.returncode, 0)
        self.assertIn("package import failed", package_result.stderr)

    def test_empty_package_initializer_does_not_fail_when_child_tests_pass(self):
        """空のpackage initializerは子テスト成功時にCLIを失敗させない。

        unittestが0件のinitializerへ返す専用終了コードを通常のpackageとして扱う誤りを検出する。
        """
        self.write_test("package/__init__.py", "")
        self.write_test(
            "package/test_child.py",
            """import unittest

class ChildTests(unittest.TestCase):
    def test_passes(self):
        pass
""",
        )
        stdout = io.StringIO()

        with (
            patch.object(parallel, "PROJECT_ROOT", self.root),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = parallel.main(["--workers", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Ran 1 tests across 2 modules", stdout.getvalue())
        self.assertNotIn("FAILED modules", stdout.getvalue())

    def test_successful_modules_run_once_and_aggregate_test_counts(self):
        """各モジュールを一回ずつ標準unittestで実行し件数を集約する。

        import path・作業ディレクトリの欠落やモジュールの二重実行を検出する。
        """
        self.write_test(
            "test_alpha.py",
            """import sys
import unittest
from pathlib import Path

def record_run():
    with Path(__file__).with_name("alpha-runs.txt").open("a") as stream:
        stream.write("run\\n")

class AlphaTests(unittest.TestCase):
    def test_environment_is_explicit(self):
        self.assertTrue((Path.cwd() / "project-marker").exists())
        self.assertIn(str(Path(__file__).parent), sys.path)
        record_run()

    def test_count_and_module_run_count(self):
        record_run()
""",
        )
        self.write_test(
            "package/__init__.py",
            """import unittest

class PackageTests(unittest.TestCase):
    def test_package_initializer_is_executed(self):
        pass
""",
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
        self.assertEqual([result.test_count for result in results], [1, 1, 2])
        self.assertTrue(all(result.returncode == 0 for result in results))
        self.assertEqual(sum(result.test_count for result in results), 4)
        self.assertIn("Ran 2 tests", results[-1].stdout + results[-1].stderr)
        alpha_runs = (self.tests_dir / "alpha-runs.txt").read_text(encoding="utf-8")
        self.assertEqual(alpha_runs.splitlines(), ["run", "run"])

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

    def test_modules_are_imported_from_tests_directory_before_project_root(self):
        """同名モジュールがあってもtests内で発見したファイルを実行する。

        cwdがPYTHONPATHより優先され、プロジェクト直下の同名ファイルを誤実行する問題を検出する。
        """
        (self.root / "test_collision.py").write_text(
            """import unittest

class WrongModuleTests(unittest.TestCase):
    def test_wrong_module_was_imported(self):
        self.fail("project-root module was imported")
""",
            encoding="utf-8",
        )
        self.write_test(
            "test_collision.py",
            """import unittest

class CorrectModuleTests(unittest.TestCase):
    def test_tests_directory_module_was_imported(self):
        self.assertTrue(True)
""",
        )

        result = parallel.run_test_modules(
            ["test_collision"],
            tests_dir=self.tests_dir,
            repo_root=self.root,
            workers=1,
        )[0]

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.test_count, 1)
        self.assertNotIn("project-root module was imported", result.stderr)

    def test_cli_returns_nonzero_when_a_module_fails(self):
        """CLI全体も一つの失敗を非0終了として報告する。

        worker結果をmainが集約し損ね、失敗を成功終了にする誤りを検出する。
        """
        self.write_test(
            "test_failure.py",
            """import unittest

class FailureTests(unittest.TestCase):
    def test_expected_failure(self):
        self.fail("intentional CLI failure")
""",
        )
        stdout = io.StringIO()

        with (
            patch.object(parallel, "PROJECT_ROOT", self.root),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = parallel.main(["--workers", "1"])

        self.assertEqual(exit_code, 1)
        self.assertIn("intentional CLI failure", stdout.getvalue())
        self.assertIn("FAILED modules: test_failure", stdout.getvalue())
        self.assertIn("Ran 1 tests across 1 modules", stdout.getvalue())

    def test_cli_returns_nonzero_when_worker_start_or_execution_raises(self):
        """起動例外とworker例外もCLIの失敗として伝える。

        process起動やfuture完了時の例外をmainが成功扱いする誤りを検出する。
        """
        self.write_test("test_failure.py", "")

        for error, expected_diagnostic in (
            (OSError("cannot start worker"), "Could not start"),
            (RuntimeError("worker crashed"), "Worker raised RuntimeError"),
        ):
            with self.subTest(error=type(error).__name__):
                stdout = io.StringIO()
                with (
                    patch.object(parallel, "PROJECT_ROOT", self.root),
                    patch.object(parallel.subprocess, "run", side_effect=error),
                    contextlib.redirect_stdout(stdout),
                ):
                    exit_code = parallel.main(["--workers", "1"])

                self.assertEqual(exit_code, 1)
                self.assertIn(expected_diagnostic, stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
