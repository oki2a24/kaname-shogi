"""ステージ内容の品質検査を、外部パッケージなしで確認する。"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import check_staged_python


class QualityGateTests(unittest.TestCase):
    """一時Gitリポジトリで検査対象と非変更を確認する。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        (self.root / "pyproject.toml").write_text("[tool.ruff]\n")
        self.git("add", "pyproject.toml")
        tools = self.root / ".venv/bin"
        tools.mkdir(parents=True)
        self.log = self.root / "calls.txt"
        self.ruff = tools / "ruff"
        self.ruff.write_text(
            "#!" + sys.executable + "\n"
            "import pathlib, sys\n"
            "files = [pathlib.Path(p) for p in sys.argv[1:] if p.endswith('.py')]\n"
            f"pathlib.Path({str(self.log)!r}).open('a').write(repr([(str(p), p.read_text()) for p in files]) + '\\n')\n"
            "raise SystemExit(int(any('BAD' in p.read_text() for p in files)))\n"
        )
        self.ruff.chmod(0o755)

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
        ).stdout

    def stage(self, text, name="sample.py"):
        path = self.root / name
        path.write_text(text)
        self.git("add", "--", name)
        return path

    def test_rejects_bad_index_despite_clean_worktree(self):
        """作業版が修正済みでも、不合格のステージ版は止める。

        作業ツリーだけを検査してコミット予定の誤りを見逃す実装を検出する。
        """
        path = self.stage("BAD\n")
        path.write_text("good = 1\n")
        before = self.git("diff", "--cached")
        self.assertNotEqual(check_staged_python.main(self.root), 0)
        self.assertEqual(self.git("diff", "--cached"), before)
        self.assertEqual(path.read_text(), "good = 1\n")

    def test_accepts_clean_index_despite_bad_worktree(self):
        """未ステージの誤りは、合格するステージ版の判定を変えない。

        部分ステージ時にコミット対象と検査対象が食い違う誤りを検出する。
        """
        self.stage("good = 1\n").write_text("BAD\n")
        self.assertEqual(check_staged_python.main(self.root), 0)
        self.assertTrue(self.log.is_file(), "ステージ版を実際に検査する")
        self.assertIn("good = 1", self.log.read_text())
        self.assertNotIn("BAD", self.log.read_text())

    def test_missing_tool_blocks_commit(self):
        """Ruffがない場合は検査を省略せずコミットを止める。

        未セットアップのPCで合格扱いにしてしまう誤りを検出する。
        """
        self.stage("good = 1\n")
        self.ruff.unlink()
        self.assertNotEqual(check_staged_python.main(self.root), 0)

    def test_missing_staged_config_blocks_commit(self):
        """設定が作業版にしかない場合は止める。

        ステージされていない設定を使って合格する誤りを検出する。
        """
        self.stage("good = 1\n")
        self.git("rm", "--cached", "pyproject.toml")
        self.assertNotEqual(check_staged_python.main(self.root), 0)

    def test_space_path_is_checked(self):
        """空白付きパスも一つの対象として検査する。

        シェルで文字列を分割してファイルを検査し損なう誤りを検出する。
        """
        self.stage("BAD\n", "space name.py")
        self.assertNotEqual(check_staged_python.main(self.root), 0)

    def test_deleted_python_is_not_checked(self):
        """インデックスから削除したPythonファイルは検査しない。

        作業版に残った削除対象まで検査する誤りを検出する。
        """
        self.stage("BAD\n")
        self.git("rm", "--cached", "sample.py")
        self.assertEqual(check_staged_python.main(self.root), 0)

    def test_untracked_python_is_not_checked(self):
        """未追跡Pythonファイルはコミット予定に含めない。

        一時ファイルや仮想環境を検査対象に混ぜる誤りを検出する。
        """
        (self.root / "untracked.py").write_text("BAD\n")
        self.assertEqual(check_staged_python.main(self.root), 0)

    def test_symlink_python_blocks_commit(self):
        """外部を参照し得るPythonシンボリックリンクは止める。

        スナップショット外のファイルを検査する誤りを検出する。
        """
        os.symlink("outside.py", self.root / "linked.py")
        self.git("add", "linked.py")
        self.assertNotEqual(check_staged_python.main(self.root), 0)
