"""標準unittestのテストモジュールを別プロセスで並列実行する。"""

import argparse
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_TEST_SUMMARY = re.compile(r"^Ran (\d+) tests? in [0-9.]+s$", re.MULTILINE)
_SKIP_SUMMARY = re.compile(r"^OK \(.*\bskipped=(\d+)\b.*\)$", re.MULTILINE)
_VALID_MODULE_NAME = re.compile(r"[_a-z]\w*\.py$", re.IGNORECASE)
_WORKER_BOOTSTRAP = (
    "import sys, unittest; "
    "tests_dir, module = sys.argv[1:3]; "
    "sys.path.insert(0, tests_dir); "
    "program = unittest.main(module=module, argv=['unittest', '-v'], exit=False); "
    "sys.exit(0 if program.result.wasSuccessful() else 1)"
)


@dataclass(frozen=True)
class ModuleResult:
    """一つのunittestモジュール実行の結果を表す。"""

    module: str
    returncode: int
    stdout: str
    stderr: str
    test_count: int
    skipped_count: int
    elapsed_seconds: float


def discover_test_modules(tests_dir):
    """標準discoverのパターンとpackage再帰条件でテスト名を返す。

    Args:
        tests_dir: `unittest discover -s` に渡す探索開始ディレクトリ。

    Returns:
        標準discoveryと同じ有効な `test*.py` とpackageを辞書順で返す。
        package自身も含み、initializerのテストとimport失敗を実行対象にする。

    Raises:
        FileNotFoundError: 探索開始ディレクトリが存在しない場合。
        NotADirectoryError: 探索開始パスがディレクトリでない場合。
    """
    tests_dir = Path(tests_dir).resolve()
    if not tests_dir.exists():
        raise FileNotFoundError(tests_dir)
    if not tests_dir.is_dir():
        raise NotADirectoryError(tests_dir)

    modules = []

    def visit(directory, package_parts):
        for path in sorted(directory.iterdir()):
            if (
                path.is_file()
                and _VALID_MODULE_NAME.fullmatch(path.name)
                and fnmatchcase(path.name, "test*.py")
            ):
                module_parts = package_parts + [path.stem]
                modules.append(".".join(module_parts))
            elif path.is_dir() and (path / "__init__.py").is_file():
                nested_parts = package_parts + [path.name]
                modules.append(".".join(nested_parts))
                visit(path, nested_parts)

    visit(tests_dir, [])
    return sorted(modules)


def _run_test_module(module, tests_dir, repo_root):
    """標準unittestを一つのモジュールに対して実行する。"""
    env = os.environ.copy()
    env["PYTHON_COLORS"] = "0"
    python_paths = [str(Path(tests_dir).resolve())]
    if env.get("PYTHONPATH"):
        python_paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    command = [
        sys.executable,
        "-c",
        _WORKER_BOOTSTRAP,
        str(Path(tests_dir).resolve()),
        module,
    ]
    started = time.monotonic()

    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            env=env,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as error:
        return ModuleResult(
            module=module,
            returncode=1,
            stdout="",
            stderr=f"Could not start {command!r}: {error}\n",
            test_count=0,
            skipped_count=0,
            elapsed_seconds=time.monotonic() - started,
        )

    output = completed.stdout + completed.stderr
    summaries = _TEST_SUMMARY.findall(output)
    skipped_summaries = _SKIP_SUMMARY.findall(output)
    return ModuleResult(
        module=module,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        test_count=int(summaries[-1]) if summaries else 0,
        skipped_count=int(skipped_summaries[-1]) if skipped_summaries else 0,
        elapsed_seconds=time.monotonic() - started,
    )


def run_test_modules(modules, *, tests_dir, repo_root, workers):
    """各モジュールをworker上限内で実行し、入力順の結果を返す。

    Args:
        modules: 実行するunittestモジュール名の列。
        tests_dir: テストモジュールをimportするためのディレクトリ。
        repo_root: 各プロセスの作業ディレクトリ。
        workers: 同時に実行する最大プロセス数。

    Returns:
        完了順にかかわらず、入力順に整列した各モジュールの結果。

    Raises:
        ValueError: workersが1未満の場合。
    """
    if workers < 1:
        raise ValueError("workers must be at least 1")
    if not modules:
        return []

    results = {}
    max_workers = min(workers, len(modules))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_test_module, module, tests_dir, repo_root): module
            for module in modules
        }
        for future in as_completed(futures):
            module = futures[future]
            try:
                results[module] = future.result()
            except Exception as error:
                results[module] = ModuleResult(
                    module=module,
                    returncode=1,
                    stdout="",
                    stderr=f"Worker raised {type(error).__name__}: {error}\n",
                    test_count=0,
                    skipped_count=0,
                    elapsed_seconds=0.0,
                )
    return [results[module] for module in modules]


def _default_worker_count():
    """利用可能CPU数を最大4に抑え、1以上の既定値を返す。"""
    return min(4, max(1, os.cpu_count() or 1))


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Run unittest test modules in separate parallel processes."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=_default_worker_count(),
        help="maximum concurrent test processes (default: up to 4 CPUs)",
    )
    return parser


def main(argv=None):
    """CLIから全テストを並列実行し、いずれかの失敗を非0で返す。

    Args:
        argv: 引数列。Noneの場合は標準入力引数を使う。

    Returns:
        成功または正当なskipの場合は0、失敗・起動失敗・実行0件の場合は1。

    Raises:
        SystemExit: 引数不正、テストモジュール0件、探索失敗の場合。
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("workers must be at least 1")

    tests_dir = PROJECT_ROOT / "tests"
    try:
        modules = discover_test_modules(tests_dir)
    except OSError as error:
        parser.error(f"could not discover tests: {error}")
    if not modules:
        parser.error(f"No test modules found in {tests_dir}")

    started = time.monotonic()
    results = run_test_modules(
        modules,
        tests_dir=tests_dir,
        repo_root=PROJECT_ROOT,
        workers=args.workers,
    )
    for result in results:
        sys.stdout.write(f"\n=== {result.module} ===\n")
        sys.stdout.write(result.stdout)
        sys.stdout.write(result.stderr)
        if result.stdout and not result.stdout.endswith("\n"):
            sys.stdout.write("\n")
        if result.stderr and not result.stderr.endswith("\n"):
            sys.stdout.write("\n")

    elapsed = time.monotonic() - started
    total_tests = sum(result.test_count for result in results)
    total_skipped = sum(result.skipped_count for result in results)
    failures = [result.module for result in results if result.returncode != 0]
    sys.stdout.write(
        f"\nRan {total_tests} tests across {len(results)} modules in {elapsed:.3f}s\n"
    )
    if failures:
        sys.stdout.write(f"FAILED modules: {', '.join(failures)}\n")
        return 1
    if total_tests == 0 and total_skipped == 0:
        sys.stdout.write("NO TESTS RAN\n")
        return 1
    sys.stdout.write("OK\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
