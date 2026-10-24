"""比較実験を既存の条件・局結果に照合して再開する。"""

from __future__ import annotations

import hashlib
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .comparison import (
    ComparisonConfig,
    GameEndReason,
    GameResult,
    ScheduledGame,
    make_schedule,
)
from .comparison_artifact_io import decode_object
from .comparison_io import conditions_payload
from .comparison_result_io import _json_values_equal, _load_game


@dataclass(frozen=True)
class ResumeState:
    """再開の入力照合結果を保持する読み取り専用値。"""

    conditions_sha256: str
    completed_results: tuple[GameResult, ...]
    pending_schedule: tuple[ScheduledGame, ...]
    elapsed_ns: int


@contextmanager
def run_lock(output_dir: Path) -> Iterator[None]:
    """同じ実験出力先を別プロセスが同時使用しないよう排他する。

    引数:
        output_dir: 実験成果物を置く既存ディレクトリ。

    戻り値:
        with文の本体へNoneを渡す。

    例外:
        ValueError: ロックが既にあり、使用中または確認が必要な場合。
        OSError: ロックを作成・削除できない場合。

    副作用:
        ディレクトリ内にPIDと一意トークンを記したロックファイルを排他的に作成し、
        自分が作成した同一ファイルだけを終了時に削除する。

    前提条件:
        強制終了後の残存ロックは自動削除しない。PIDの実行状態を人が確かめてから
        手動で除去し、誤った二重実行を防ぐ。
    """
    lock_path = Path(output_dir) / ".comparison.lock"
    token = f"{os.getpid()} {uuid.uuid4().hex}\n"
    try:
        descriptor = os.open(
            lock_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError as error:
        raise ValueError(
            f"比較出力先は使用中か残存ロックがあります: {lock_path}。"
            "PIDが動作中でないことを確認してから残存ロックを除去してください"
        ) from error
    created_file = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as lock_file:
            lock_file.write(token)
            lock_file.flush()
            os.fsync(lock_file.fileno())
        yield
    finally:
        try:
            current_file = os.stat(lock_path, follow_symlinks=False)
            if (current_file.st_dev, current_file.st_ino) == (
                created_file.st_dev,
                created_file.st_ino,
            ):
                lock_path.unlink()
        except FileNotFoundError:
            pass


def load_resume_state(config: ComparisonConfig, *, source_root: Path) -> ResumeState:
    """保存条件を再生成条件へ照合し、再開状態を返す。

    引数:
        config: `--resume` で検証済みの比較条件。
        source_root: `kaname_shogi` パッケージを含むGit作業ルート。

    戻り値:
        保存条件のハッシュ、完了局、未完了予定、保存済み経過時間。

    例外:
        ValueError: 条件・ソース・成果物が不正または異なる場合。
        OSError: 条件ファイルを読めない場合。

    副作用:
        条件ファイルと現在のソースを読み取る。既存成果物を変更しない。

    前提条件:
        出力先は既存ディレクトリで、configは通常の入力検証を通過している。
        Git HEADやdirty状態は再開条件でなく、Pythonソース指紋と実行環境が一致する。
    """
    if not config.resume:
        raise ValueError("再開状態は--resume指定の条件でのみ読み込めます")
    root = Path(config.output_dir)
    conditions_path = root / "conditions.json"
    if conditions_path.is_symlink() or not conditions_path.is_file():
        raise ValueError("再開条件conditions.jsonがありません")

    raw = conditions_path.read_bytes()
    saved = decode_object(raw, context="比較条件")
    schedule = make_schedule(config)
    current = conditions_payload(config, schedule, source_root=Path(source_root))
    if saved.get("source_sha256") != current["source_sha256"]:
        raise ValueError("再開時のソースが保存時と一致しません")

    saved_without_git = dict(saved)
    current_without_git = dict(current)
    saved_without_git.pop("git", None)
    current_without_git.pop("git", None)
    if not _json_values_equal(saved_without_git, current_without_git):
        raise ValueError("再開条件が保存済み比較条件と一致しません")

    scheduled_by_name = {f"{game.game_id}.json": game for game in schedule}
    actual_names = {path.name for path in root.glob("game-*.json")}
    unexpected_names = actual_names - scheduled_by_name.keys()
    if unexpected_names:
        raise ValueError(f"再開局の予定IDが一致しません: {sorted(unexpected_names)}")

    conditions_sha256 = hashlib.sha256(raw).hexdigest()
    completed_results: list[GameResult] = []
    pending_schedule: list[ScheduledGame] = []
    for game in schedule:
        game_path = root / f"{game.game_id}.json"
        if not game_path.exists() and not game_path.is_symlink():
            pending_schedule.append(game)
            continue
        if game_path.is_symlink() or not game_path.is_file():
            raise ValueError(f"{game.game_id}局JSONは通常ファイルではありません")
        payload = decode_object(game_path.read_bytes(), context=f"{game.game_id}局")
        result = _load_game(
            payload,
            game,
            config,
            conditions_sha256=conditions_sha256,
            allow_incomplete=True,
        )
        if result.reason in {GameEndReason.ERROR, GameEndReason.INTERRUPTED}:
            pending_schedule.append(game)
        else:
            completed_results.append(result)

    summary_path = root / "summary.json"
    elapsed_ns = 0
    if summary_path.is_symlink():
        raise ValueError("再開summaryは通常ファイルで指定してください")
    if summary_path.is_file():
        summary = decode_object(summary_path.read_bytes(), context="比較summary")
        value = summary.get("elapsed_ns", 0)
        if type(value) is not int or value < 0:
            raise ValueError("再開summaryの経過時間が不正です")
        elapsed_ns = value

    return ResumeState(
        conditions_sha256=conditions_sha256,
        completed_results=tuple(completed_results),
        pending_schedule=tuple(pending_schedule),
        elapsed_ns=elapsed_ns,
    )
