"""停止不能な担当を親プロセスから回収するUSIテスト用補助。"""

import subprocess
import sys
import textwrap


def run_isolated(case, body, *, timeout=5):
    """子で実コンポーネントを動かし、失敗・相互待ちでも親が回収する。"""
    process = subprocess.Popen(
        [sys.executable, "-c", textwrap.dedent(body)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            case.fail("子プロセスが有限時間内に担当を回収できませんでした")
        case.assertEqual(process.returncode, 0, (stdout + stderr).decode())
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
        process.stdout.close()
        process.stderr.close()
