"""ネットワークに接続せず、開発環境構築の停止条件を確認する。"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import setup_dev


class SetupDevTests(unittest.TestCase):
    """Gitは実物、仮想環境とパッケージ取得は代替して確認する。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run = subprocess.run
        self.git("init", "-q")
        (self.root / ".githooks").mkdir()
        hook = self.root / ".githooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 0\n")
        hook.chmod(0o755)
        (self.root / "requirements-dev.txt").write_text("ruff==0.16.10\n")
        self.installs = 0
        self.env_creations = 0
        self.env_python_version = (3, 14, 0)

    def git(self, *args):
        return self.run(["git", "-C", str(self.root), *args], capture_output=True)

    def create_env(self, path):
        self.env_creations += 1
        path = Path(path)
        (path / "bin").mkdir(parents=True)
        python = path / "bin/python"
        python.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            f"sys.version_info = {self.env_python_version!r}\n"
            "sys.prefix = '/fake/venv'\n"
            "sys.base_prefix = '/fake/base'\n"
            "exec(sys.argv[2], {'__name__': '__main__'})\n",
            encoding="utf-8",
        )
        python.chmod(0o755)
        (path / "pyvenv.cfg").write_text("home = test\n")

    def invoke(
        self,
        fail_install=False,
        bad_version=False,
        python_version=None,
        env_python_version=(3, 14, 0),
    ):
        self.env_python_version = env_python_version

        def run(args, **kwargs):
            if str(args[0]) == str(self.root / ".venv/bin/python"):
                if args[1:2] == ["-c"]:
                    return self.run(args, **kwargs)
                if "pip" in args:
                    self.installs += 1
                    if fail_install:
                        raise subprocess.CalledProcessError(1, args)
                    (self.root / ".venv/bin/ruff").touch()
                elif "ruff" in args:
                    return subprocess.CompletedProcess(
                        args, 0, "ruff 0.0.0\n" if bad_version else "ruff 0.16.10\n", ""
                    )
                return subprocess.CompletedProcess(args, 0, "", "")
            return self.run(args, **kwargs)

        with (
            patch(
                "scripts.setup_dev.venv.EnvBuilder.create", side_effect=self.create_env
            ),
            patch("scripts.setup_dev.subprocess.run", side_effect=run),
            patch(
                "scripts.setup_dev.sys",
                SimpleNamespace(
                    version_info=python_version or sys.version_info, stderr=sys.stderr
                ),
            ),
        ):
            return setup_dev.main(self.root)

    def test_setup_enables_local_hook_and_can_repeat(self):
        """初回と再実行で固定版導入とローカルフック設定を行う。

        clone後に環境とフックの片方だけを用意して成功とする誤りを検出する。
        """
        self.assertEqual(self.invoke(), 0)
        self.assertEqual(
            self.git("config", "--local", "--get", "core.hooksPath").stdout.strip(),
            b".githooks",
        )
        self.assertEqual(self.invoke(), 0)
        self.assertEqual(self.installs, 2)

    def test_python_314_is_accepted(self):
        """最低対応版のPython 3.14で開発環境を構築できる。

        下限を誤って3.15以上にする境界条件の誤りを検出する。
        """
        self.assertEqual(self.invoke(python_version=(3, 14, 0)), 0)
        self.assertEqual(self.env_creations, 1)
        self.assertEqual(self.installs, 1)
        self.assertEqual(
            self.git("config", "--local", "--get", "core.hooksPath").stdout.strip(),
            b".githooks",
        )

    def test_python_313_is_rejected_before_side_effects(self):
        """Python 3.13では環境・依存・Gitフックを変更する前に停止する。

        旧下限を残したり、拒否前にセットアップを始めたりする誤りを検出する。
        """
        self.assertNotEqual(self.invoke(python_version=(3, 13, 9)), 0)
        self.assertFalse((self.root / ".venv").exists())
        self.assertEqual(self.env_creations, 0)
        self.assertEqual(self.installs, 0)
        self.assertEqual(
            self.git("config", "--local", "--get", "core.hooksPath").returncode, 1
        )

    def test_existing_python_313_env_is_rejected_before_side_effects(self):
        """Python 3.14のホストでも既存の3.13仮想環境を再利用しない。

        ホストだけを検査して古い.venvのPython下限を見逃す誤りを検出する。
        """
        env = self.root / ".venv"
        self.env_python_version = (3, 13, 9)
        self.create_env(env)
        marker = env / "keep"
        marker.write_text("keep")

        self.assertNotEqual(
            self.invoke(python_version=(3, 14, 0), env_python_version=(3, 13, 9)),
            0,
        )
        self.assertTrue(marker.exists())
        self.assertEqual(self.installs, 0)
        self.assertEqual(
            self.git("config", "--local", "--get", "core.hooksPath").returncode, 1
        )

    def test_install_failure_does_not_enable_hook(self):
        """依存導入に失敗したらフックを新規有効化しない。

        未完成の環境を成功扱いにする誤りを検出する。
        """
        self.assertNotEqual(self.invoke(fail_install=True), 0)
        self.assertEqual(self.installs, 1)
        self.assertEqual(
            self.git("config", "--local", "--get", "core.hooksPath").returncode, 1
        )

    def test_existing_hook_path_is_preserved(self):
        """別のフック設定があるときは導入前に止める。

        他の開発ツールのフックを無断で無効にする誤りを検出する。
        """
        self.git("config", "--local", "core.hooksPath", "other-hooks")
        self.assertNotEqual(self.invoke(), 0)
        self.assertEqual(self.installs, 0)
        self.assertEqual(
            self.git("config", "--local", "--get", "core.hooksPath").stdout.strip(),
            b"other-hooks",
        )

    def test_existing_default_hook_is_preserved(self):
        """標準のhooks配下の既存フックも上書きしない。

        core.hooksPathの変更で従来の検査が働かなくなる誤りを検出する。
        """
        hook = self.root / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 0\n")
        hook.chmod(0o755)
        self.assertNotEqual(self.invoke(), 0)
        self.assertEqual(self.installs, 0)

    def test_broken_env_is_not_deleted(self):
        """壊れた仮想環境は自動削除せず止める。

        利用者の既存ファイルを勝手に削除する誤りを検出する。
        """
        env = self.root / ".venv"
        env.mkdir()
        marker = env / "keep"
        marker.write_text("keep")
        self.assertNotEqual(self.invoke(), 0)
        self.assertTrue(marker.exists())

    def test_wrong_ruff_version_does_not_enable_hook(self):
        """固定版と異なるRuffではセットアップ完了としない。

        別PCで異なる検査結果を許す誤りを検出する。
        """
        self.assertNotEqual(self.invoke(bad_version=True), 0)
        self.assertEqual(self.installs, 1)
        self.assertEqual(
            self.git("config", "--local", "--get", "core.hooksPath").returncode, 1
        )
