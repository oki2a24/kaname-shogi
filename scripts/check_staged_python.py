"""Gitインデックス内のPythonコードを、作業版を変えずに検査する。"""

from pathlib import Path
import subprocess
import sys
import tempfile


def main(root=None):
    """コミット予定内容を検査し、成功時0、失敗時1を返す。

    rootはGitリポジトリのルートを表すPath（省略時は本スクリプトの親の親）。
    固定版Ruffが.venv/bin/ruffにあることを前提とする。Gitのblobを一時領域に
    複写して検査するため、作業版・インデックスは変更しない。checkout時の
    改行変換やフィルタを避け、実際にステージされた内容を検査する設計である。
    Pythonファイルと設定のシンボリックリンクは検査対象外への参照を防ぐため拒否する。
    """
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    root = root.resolve()
    ruff = root / ".venv/bin/ruff"
    try:
        if not ruff.is_file():
            raise ValueError(
                "Ruffがありません。python3 scripts/setup_dev.py を実行してください。"
            )
        result = subprocess.run(
            ["git", "ls-files", "--stage", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
        )
        entries = []
        for record in result.stdout.split(b"\0"):
            if not record:
                continue
            metadata, raw_path = record.split(b"\t", 1)
            mode, oid, stage = metadata.split()
            path = raw_path.decode(sys.getfilesystemencoding(), "surrogateescape")
            if stage != b"0":
                raise ValueError("未解決の競合があります。先に解消してください。")
            if path.endswith(".py") or path == "pyproject.toml":
                if mode not in (b"100644", b"100755"):
                    raise ValueError(f"通常ファイルでない検査対象です: {path}")
                entries.append((path, oid.decode("ascii")))
        if not any(path == "pyproject.toml" for path, _ in entries):
            raise ValueError("pyproject.tomlをステージしてください。")
        with tempfile.TemporaryDirectory(prefix="kaname-staged-") as directory:
            snapshot = Path(directory)
            for path, oid in entries:
                target = snapshot / path
                target.parent.mkdir(parents=True, exist_ok=True)
                blob = subprocess.run(
                    ["git", "cat-file", "blob", oid],
                    cwd=root,
                    check=True,
                    capture_output=True,
                )
                target.write_bytes(blob.stdout)
            paths = [
                str(snapshot / path) for path, _ in entries if path.endswith(".py")
            ]
            for start in range(0, len(paths), 100):
                batch = paths[start : start + 100]
                for command in (["format", "--check"], ["check"]):
                    result = subprocess.run(
                        [
                            str(ruff),
                            *command,
                            "--no-cache",
                            "--config",
                            str(snapshot / "pyproject.toml"),
                            *batch,
                        ],
                        cwd=snapshot,
                    )
                    if result.returncode:
                        return 1
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"コミット前検査を停止しました: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
