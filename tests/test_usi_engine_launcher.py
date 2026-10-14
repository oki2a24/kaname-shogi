"""ShogiHome用USIエンジン起動ファイルの実プロセス境界を確認する。"""

import os
import shlex
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = PROJECT_ROOT / "kaname-shogi-usi"


class UsiEngineLauncherTests(unittest.TestCase):
    def fake_python(self, version):
        return (
            f"#!{sys.executable}\n"
            "import os\n"
            "import sys\n"
            f"version = {version!r}\n"
            "if sys.argv[1] == '-c':\n"
            "    sys.version_info = version\n"
            "    exec(sys.argv[2], {'__name__': '__main__'})\n"
            "else:\n"
            "    os.execv(sys.executable, [sys.executable, *sys.argv[1:]])\n"
        )

    def create_clone(self, root, with_python=True, python_script=None):
        import shutil

        shutil.copytree(
            PROJECT_ROOT / "kaname_shogi",
            root / "kaname_shogi",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        shutil.copytree(PROJECT_ROOT / "config", root / "config")
        launcher = root / "kaname-shogi-usi"
        shutil.copy2(LAUNCHER, launcher)
        if with_python:
            python = root / ".venv/bin/python"
            python.parent.mkdir(parents=True)
            if python_script is None:
                python.symlink_to(sys.executable)
            else:
                python.write_text(python_script, encoding="utf-8")
                python.chmod(0o755)
        return launcher

    def test_launcher_advertises_difficulty_combo(self):
        """実行ファイルのusi応答でDifficulty comboをusiok前に通知する。

        ShogiHomeに登録する起動境界でoption応答が欠落したり、順序がずれる誤りを
        検出する。
        """
        self.assertTrue(LAUNCHER.is_file(), "USIエンジンの実行ファイルがありません")
        self.assertTrue(
            os.access(LAUNCHER, os.X_OK), "USIエンジンの実行権限がありません"
        )

        result = subprocess.run(
            [str(LAUNCHER)],
            cwd=PROJECT_ROOT,
            input="usi\nquit\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "id name kaname-shogi\n"
            "id author kaname-shogi project\n"
            "option name Difficulty type combo default Random var Random var Material var TwoPlyMaterial\n"
            "usiok\n",
        )
        self.assertEqual(result.stderr, "")

    def test_launcher_propagates_usi_engine_error_status(self):
        """不正なUSI入力時の異常終了コードを呼び出し側へ伝える。

        mainの戻り値を破棄し、エラーを成功終了として報告する誤りを検出する。
        """
        self.assertTrue(LAUNCHER.is_file(), "USIエンジンの実行ファイルがありません")
        self.assertTrue(
            os.access(LAUNCHER, os.X_OK), "USIエンジンの実行権限がありません"
        )

        result = subprocess.run(
            [str(LAUNCHER)],
            cwd=PROJECT_ROOT,
            input="position sfen invalid\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("USIエンジンエラー:", result.stderr)

    def test_launcher_loads_config_from_other_cwd(self):
        """別cwdからの起動でも同梱設定を読んでUSI応答する。

        設定をcwd相対で探す誤りを実入口で検出する。
        """
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            result = subprocess.run(
                [str(LAUNCHER)],
                cwd=directory,
                input="usi\nquit\n",
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "id name kaname-shogi",
                "id author kaname-shogi project",
                "option name Difficulty type combo default Random var Random var Material var TwoPlyMaterial",
                "usiok",
            ],
        )

    def test_launcher_uses_python_from_clone_venv(self):
        """隔離cloneの仮想環境PythonでUSIエンジンを起動する。

        システムPythonや呼び出し元のPATHへ暗黙に依存する誤りを検出する。
        """
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            launcher = self.create_clone(root)
            marker = root / "python-arguments"
            cwd_marker = root / "python-cwd"
            python = root / ".venv/bin/python"
            python.unlink()
            python.write_text(
                "#!/bin/sh\n"
                'printf \'%s\\n\' "$*" > "$KANAME_LAUNCHER_PYTHON_ARGS"\n'
                'printf \'%s\\n\' "$PWD" > "$KANAME_LAUNCHER_CWD"\n'
                f'exec {shlex.quote(sys.executable)} "$@"\n',
                encoding="utf-8",
            )
            python.chmod(0o755)
            env = os.environ.copy()
            env["KANAME_LAUNCHER_PYTHON_ARGS"] = str(marker)
            env["KANAME_LAUNCHER_CWD"] = str(cwd_marker)
            caller = root / "caller"
            caller.mkdir()

            result = subprocess.run(
                [str(launcher)],
                cwd=caller,
                env=env,
                input="usi\nquit\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=5,
                check=False,
            )
            marker_was_written = marker.is_file()
            marker_arguments = (
                marker.read_text(encoding="utf-8") if marker_was_written else ""
            )
            actual_cwd = cwd_marker.read_text(encoding="utf-8").strip()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            marker_was_written, "clone内の.venv/bin/pythonが呼び出されていません"
        )
        self.assertEqual(marker_arguments, "-m kaname_shogi.usi_engine\n")
        self.assertEqual(actual_cwd, str(caller.resolve()))
        self.assertIn("usiok\n", result.stdout)

    def test_launcher_reports_missing_clone_venv_before_usi(self):
        """仮想環境がないcloneでは手順を案内してUSI応答前に停止する。

        不明瞭な実行エラーや環境外Pythonへの暗黙フォールバックを検出する。
        """
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            launcher = self.create_clone(root, with_python=False)
            result = subprocess.run(
                [str(launcher)],
                cwd=root,
                input="usi\nquit\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=5,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn(".venv/bin/python", result.stderr)
        self.assertIn("README", result.stderr)

    def test_launcher_rejects_python_below_supported_minimum(self):
        """古い仮想環境ではPython下限を案内し、エンジンを起動しない。

        Python 3.14未満の既存環境から未対応構文へ進む誤りを検出する。
        """
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "engine-arguments"
            launcher = self.create_clone(
                root,
                python_script=self.fake_python((3, 13, 9)),
            )
            env = os.environ.copy()
            env["KANAME_LAUNCHER_PYTHON_ARGS"] = str(marker)
            result = subprocess.run(
                [str(launcher)],
                cwd=root,
                env=env,
                input="usi\nquit\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=5,
                check=False,
            )
            engine_was_started = marker.is_file()

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Python 3.14以上", result.stderr)
        self.assertIn("README", result.stderr)
        self.assertFalse(engine_was_started)

    def test_launcher_accepts_supported_python_minimum(self):
        """最低対応版のPython 3.14でエンジンを起動する。

        起動側だけ下限を3.15以上へ誤って引き上げる不整合を検出する。
        """
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            launcher = self.create_clone(
                root,
                python_script=self.fake_python((3, 14, 8)),
            )
            result = subprocess.run(
                [str(launcher)],
                cwd=root,
                input="usi\nquit\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=5,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usiok\n", result.stdout)

    def test_launcher_rejects_bad_config_before_usi(self):
        """隔離した実入口で設定故障をUSI応答前に診断する。

        読込不能や不正JSONの無断代替、起動時応答の先行を検出する。
        """
        from tempfile import TemporaryDirectory

        for fault in ("missing", "syntax", "key", "encoding", "directory"):
            with self.subTest(fault=fault), TemporaryDirectory() as directory:
                root = Path(directory)
                launcher = self.create_clone(root)
                config = root / "config/time-management.json"
                if fault == "missing":
                    config.unlink()
                elif fault == "syntax":
                    config.write_text("{", encoding="utf-8")
                elif fault == "key":
                    config.write_text("{}", encoding="utf-8")
                elif fault == "encoding":
                    config.write_bytes(b"\xff")
                elif fault == "directory":
                    config.unlink()
                    config.mkdir()
                result = subprocess.run(
                    [str(launcher)],
                    cwd=root,
                    input="usi\nquit\n",
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=5,
                    check=False,
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn("USIエンジンエラー:", result.stderr)
                self.assertIn(str(config), result.stderr)
                self.assertTrue(result.stderr.partition(str(config))[2].strip())
