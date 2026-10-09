"""cloneごとにプロジェクト内の開発環境とGitフックを用意する。"""

import os
import subprocess
import sys
import venv
from pathlib import Path


def main(root=None):
    """開発環境を構築し、成功時0、停止時1を返す。

    rootは通常のcloneのルートPath（省略時はスクリプトの親の親）。macOS/Linux、
    Python 3.9以上、Gitとパッケージ取得の通信環境を前提とする。リポジトリ内の
    .venvとローカルGit設定だけを変更する。再実行は既存環境を再利用するが、
    壊れた環境を削除しない。既存フックを無効にせず、依存導入成功後だけ新しい
    フックを有効化する順序により、不完全な構築を成功扱いにしない。
    """
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    root = root.resolve()
    try:
        if os.name != "posix" or sys.version_info < (3, 9):
            raise ValueError("macOS/LinuxとPython 3.9以上が必要です。")
        if not (root / ".git").is_dir():
            raise ValueError(
                "通常のclone内で実行してください。別worktreeは今回の対象外です。"
            )
        hook = root / ".githooks/pre-commit"
        if not hook.is_file() or not os.access(hook, os.X_OK):
            raise ValueError(
                "実行可能な.githooks/pre-commitがありません。Gitの取得状態を確認してください。"
            )
        configured = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if configured.returncode not in (0, 1):
            raise ValueError("Gitフック設定を読み取れません。")
        current = configured.stdout.strip()
        if current and current != ".githooks":
            raise ValueError(
                f"既存のcore.hooksPath={current}があります。統合方法を相談してください。"
            )
        if not current:
            active = [
                p.name
                for p in (root / ".git/hooks").iterdir()
                if p.is_file() and not p.name.endswith(".sample")
            ]
            if active:
                raise ValueError(
                    f"既存フックがあります: {', '.join(active)}。統合方法を相談してください。"
                )
        env = root / ".venv"
        python = env / "bin/python"
        if env.exists():
            if not (env / "pyvenv.cfg").is_file() or not python.is_file():
                raise ValueError(
                    ".venvが不完全です。READMEの環境再作成手順を確認してください。"
                )
        else:
            venv.EnvBuilder(with_pip=True).create(env)
        subprocess.run(
            [
                str(python),
                "-c",
                "import sys; assert sys.version_info >= (3, 9); "
                "assert sys.prefix != sys.base_prefix",
            ],
            cwd=root,
            check=True,
        )
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-cache-dir",
                "-r",
                str(root / "requirements-dev.txt"),
            ],
            cwd=root,
            check=True,
        )
        version = subprocess.run(
            [str(python), "-m", "ruff", "--version"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        # バージョンの唯一の定義はrequirements-dev.txtとし、更新漏れを減らす。
        requirement = (root / "requirements-dev.txt").read_text().strip()
        expected = "ruff " + requirement.removeprefix("ruff==")
        if not requirement.startswith("ruff==") or version.stdout.strip() != expected:
            raise ValueError("Ruffのバージョンが固定版と一致しません。")
        if not (env / "bin/ruff").is_file():
            raise ValueError(
                ".venv/bin/ruffがありません。環境再作成手順を確認してください。"
            )
        subprocess.run(
            ["git", "config", "--local", "core.hooksPath", ".githooks"],
            cwd=root,
            check=True,
        )
        print(
            f"開発環境を構築しました: {version.stdout.strip()} / core.hooksPath=.githooks"
        )
        print("次にRuff両検査と全体テストを実行してください（README参照）。")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"セットアップを停止しました: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
