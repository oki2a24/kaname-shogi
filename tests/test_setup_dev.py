"""ネットワークに接続せず、開発環境構築の停止条件を確認する。"""

import subprocess
import tempfile
import unittest
from pathlib import Path
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

    def git(self, *args):
        return self.run(["git", "-C", str(self.root), *args], capture_output=True)

    def create_env(self, path):
        path = Path(path)
        (path / "bin").mkdir(parents=True)
        (path / "bin/python").touch()
        (path / "pyvenv.cfg").write_text("home = test\n")

    def invoke(self, fail_install=False, bad_version=False):
        def run(args, **kwargs):
            if str(args[0]) == str(self.root / ".venv/bin/python"):
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
