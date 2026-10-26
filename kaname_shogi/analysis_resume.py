"""分析CLIの再開チェックポイント用保存先・排他lockを扱う。"""

from __future__ import annotations

import copy
import errno
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

from . import comparison_io
from .comparison_artifact_io import decode_object

_CHECKPOINT_FORMAT = "kaname-shogi-analysis-checkpoint-v1"
_GAME_CHECKPOINT_FORMAT = "kaname-shogi-analysis-game-checkpoint-v1"
_GAME_ID_PATTERN = re.compile(r"game-[0-9]{6,}")
_MANIFEST_KEYS = {"format", "manifest", "sha256"}
_GAME_KEYS = {"format", "game_id", "record", "sha256"}
_RECORD_KEYS = {"input_sha256", "summary"}


class AnalysisCheckpointWriteError(Exception):
    """分析checkpointまたはlockの保存に失敗したことを表す。"""


def checkpoint_path_for_output(output: Path) -> Path:
    """分析JSONの隣に置くチェックポイントdirectoryのPathを返す。

    引数:
        output: 完成分析JSONの保存先。

    戻り値:
        保存先のbasenameへ `.checkpoint` を足した隣接directoryのPath。

    副作用:
        なし。ファイルやdirectoryは作成しない。

    前提条件:
        outputはファイル名を持つ分析JSONの保存先である。
    """
    output = Path(output)
    return output.with_name(f"{output.name}.checkpoint")


def analysis_lock_path_for_output(output: Path) -> Path:
    """分析JSONの隣に置く排他lock fileのPathを返す。

    引数:
        output: 完成分析JSONの保存先。

    戻り値:
        保存先basenameへ `.lock` を足した隣接fileのPath。

    副作用:
        なし。fileは作成しない。

    前提条件:
        outputはファイル名を持つ分析JSONの保存先である。
    """
    output = Path(output)
    return output.with_name(f"{output.name}.lock")


@contextmanager
def analysis_run_lock(output: Path) -> Iterator[None]:
    """同じ分析出力先を使う並行実行を排他する。

    引数:
        output: 分析結果JSONの保存先。lockはそのbasenameに`.lock`を足した隣接file。

    戻り値:
        lockを保持するcontext manager。

    例外:
        ValueError: lockが既にあり、別処理中または前回強制終了後の確認が必要な場合。
        AnalysisCheckpointWriteError: lock fileの作成・初期書込に失敗した場合。

    副作用:
        排他的作成でPIDとnonceを書いたlockを作り、正常なcontext終了時に自分が作った
        同一lockだけを削除する。解除中にKeyboardInterruptが起きた場合は診断を出して
        その割込みを抑止し、lockが残れば人にPID確認を求める。残存lockを自動で解除しない。

    前提条件:
        呼出側は、処理を始める前に同じoutputを新規保存可能か検証する。
    """
    lock_path = analysis_lock_path_for_output(output)
    token = f"{os.getpid()}:{secrets.token_hex(16)}\n"
    try:
        descriptor = os.open(
            lock_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
    except FileExistsError as error:
        raise ValueError(
            f"分析出力先のロックが既にあります。処理中か残存lockかPIDを確認してください: "
            f"{lock_path}"
        ) from error
    except OSError as error:
        raise AnalysisCheckpointWriteError(
            f"分析ロックを作成できません: {lock_path}: {error}"
        ) from error

    created_stat: os.stat_result | None = None
    try:
        created_stat = os.fstat(descriptor)
        with os.fdopen(descriptor, "w", encoding="ascii") as lock_file:
            if lock_file.write(token) != len(token):
                raise OSError("分析ロックを最後まで書き込めませんでした")
            lock_file.flush()
            os.fsync(lock_file.fileno())
    except OSError as error:
        try:
            _cleanup_failed_lock_initialization(
                lock_path, descriptor, token, created_stat
            )
        except OSError as cleanup_error:
            raise AnalysisCheckpointWriteError(
                f"分析ロックを書き込めません ({error}); 後始末に失敗しました "
                f"({cleanup_error}): {lock_path}"
            ) from error
        raise AnalysisCheckpointWriteError(
            f"分析ロックを書き込めません: {lock_path}: {error}"
        ) from error
    except BaseException:
        try:
            _cleanup_failed_lock_initialization(
                lock_path, descriptor, token, created_stat
            )
        except OSError as cleanup_error:
            print(
                f"分析ロック初期化中の後始末に失敗しました。lockとPIDを確認してください: "
                f"{lock_path}: {cleanup_error}",
                file=sys.stderr,
            )
        raise

    try:
        yield
    finally:
        try:
            _remove_owned_lock(lock_path, token, created_stat, require_token=True)
        except KeyboardInterrupt:
            print(
                "分析lock解除が中断されました。lockが残っている場合は、"
                f"PIDを確認してから手動で解除してください: {lock_path}",
                file=sys.stderr,
            )
        except OSError as error:
            print(
                f"分析ロックを解除できません。PIDを確認してから手動で削除してください: "
                f"{lock_path}: {error}",
                file=sys.stderr,
            )


def _remove_owned_lock(
    lock_path: Path,
    token: str,
    created_stat: os.stat_result,
    *,
    require_token: bool,
) -> None:
    """作成時inodeが一致する通常fileだけを、自分のlockとして削除する。"""
    try:
        current_stat = lock_path.lstat()
        if (
            not stat.S_ISREG(current_stat.st_mode)
            or current_stat.st_dev != created_stat.st_dev
            or current_stat.st_ino != created_stat.st_ino
        ):
            return
        if not require_token or lock_path.read_text(encoding="ascii") == token:
            lock_path.unlink()
    except FileNotFoundError:
        pass


def _close_descriptor(descriptor: int) -> None:
    """fdopen前後を問わず、lock descriptorが開いていれば閉じる。"""
    try:
        os.close(descriptor)
    except OSError as error:
        if error.errno != errno.EBADF:
            raise


def _cleanup_failed_lock_initialization(
    lock_path: Path,
    descriptor: int,
    token: str,
    created_stat: os.stat_result | None,
) -> None:
    """FDと自分が作ったlockの後始末を両方試し、失敗を呼出側へ伝える。"""
    errors = []
    try:
        _close_descriptor(descriptor)
    except OSError as error:
        errors.append(error)
    try:
        if created_stat is None:
            _remove_uninitialized_lock(lock_path)
        else:
            _remove_owned_lock(lock_path, token, created_stat, require_token=False)
    except OSError as error:
        errors.append(error)
    if errors:
        raise OSError("; ".join(str(error) for error in errors)) from errors[0]


def _remove_uninitialized_lock(lock_path: Path) -> None:
    """fstat前の失敗時に空のlockを除去する。

    fstat前はfdのinodeを取得できないため、exclusive open後に別プロセスが同じpathへ
    空の通常fileを差し替えないことを前提にする。lock初期化中の外部path操作は非対応。
    """
    try:
        current_stat = lock_path.lstat()
        if stat.S_ISREG(current_stat.st_mode) and current_stat.st_size == 0:
            lock_path.unlink()
    except FileNotFoundError:
        pass


class AnalysisCheckpointStore:
    """一つの分析実行に属するmanifestと局単位checkpointを管理する。

    引数:
        root: manifestとgames directoryを含むcheckpoint directory。

    副作用:
        インスタンス生成自体はファイルを読み書きしない。各操作の副作用は各methodに記す。

    前提条件:
        CLIではanalysis output隣接の固定pathを使い、同じoutputの排他lockを保持する。
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._manifest_cache: Mapping[str, object] | None = None

    def read_manifest(self) -> Mapping[str, object]:
        """保存済みmanifestを形式・checksum検証後に返す。

        戻り値:
            作成時に保存した入力条件・予定・分析器指紋の独立mapping。

        例外:
            ValueError: root、manifest形式、またはchecksumが不正な場合。
            OSError: manifestを読み込めない場合。

        副作用:
            manifest fileを読み取る。checkpointを変更しない。

        前提条件:
            呼出側が、返されたmanifestと現在の分析入力を照合する。
        """
        manifest = self._read_manifest()
        self._manifest_cache = copy.deepcopy(manifest)
        return copy.deepcopy(manifest)

    @classmethod
    def create(
        cls, root: Path, manifest: Mapping[str, object]
    ) -> AnalysisCheckpointStore:
        """新しいcheckpoint directoryを作り、manifestをchecksummedで保存する。

        引数:
            root: 分析outputに隣接する新しいcheckpoint directory。
            manifest: 入力条件・summary・schedule・分析器指紋を識別するmapping。

        戻り値:
            保存済みmanifestを持つcheckpoint store。

        例外:
            ValueError: manifestがJSON互換でない、またはrootが既存の場合。
            AnalysisCheckpointWriteError: directoryまたはmanifestの保存に失敗した場合。

        副作用:
            root、`games/`、`manifest.json`を新規作成する。既存checkpointは変更しない。

        前提条件:
            同じoutputに対する`analysis_run_lock`を保持し、rootがCLI規定の隣接pathである。
        """
        destination = Path(root)
        if not isinstance(manifest, Mapping):
            raise ValueError("分析checkpoint manifestはMappingで指定してください")
        manifest_value = copy.deepcopy(dict(manifest))
        envelope = {
            "format": _CHECKPOINT_FORMAT,
            "manifest": manifest_value,
        }
        envelope["sha256"] = _checksum(envelope)
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"分析checkpointは新規pathが必要です: {destination}")

        created = False
        try:
            destination.mkdir(mode=0o700)
            created = True
            (destination / "games").mkdir(mode=0o700)
            comparison_io.atomic_write_json(destination / "manifest.json", envelope)
        except TypeError, ValueError:
            if created:
                shutil.rmtree(destination, ignore_errors=True)
            raise
        except OSError as error:
            if created:
                shutil.rmtree(destination, ignore_errors=True)
            raise AnalysisCheckpointWriteError(
                f"分析checkpointを作成できません: {destination}: {error}"
            ) from error
        except BaseException:
            if created or (destination.is_dir() and not destination.is_symlink()):
                shutil.rmtree(destination, ignore_errors=True)
            raise
        store = cls(destination)
        store._manifest_cache = copy.deepcopy(manifest_value)
        return store

    @classmethod
    def resume(
        cls, root: Path, expected_manifest: Mapping[str, object]
    ) -> AnalysisCheckpointStore:
        """既存checkpointを開き、現在の入力識別manifestと一致するか確認する。

        引数:
            root: 既存の分析checkpoint directory。
            expected_manifest: 現在のconditions・summary・schedule・sourceから作ったmanifest。

        戻り値:
            保存manifestと現在の期待値が一致したcheckpoint store。

        例外:
            ValueError: manifestが壊れている、入力識別が異なる、またはpathが通常directoryでない場合。
            OSError: manifestを読み込めない場合。

        副作用:
            manifest fileだけを読み、checkpointを変更しない。

        前提条件:
            呼出側は同じ分析outputを指す排他lockを保持し、既存完成outputを検査している。
        """
        if not isinstance(expected_manifest, Mapping):
            raise ValueError(
                "再開時の分析checkpoint manifestはMappingで指定してください"
            )
        store = cls(Path(root))
        actual = store.read_manifest()
        if _checksum(actual) != _checksum(expected_manifest):
            raise ValueError(
                "分析checkpoint manifestが現在の入力・sourceと一致しません"
            )
        store._validate_store()
        return store

    def save_game(self, game_id: str, payload: Mapping[str, object]) -> None:
        """完全検証済み一局の小さな集計を原子的JSONへ保存する。

        引数:
            game_id: 比較予定にある一意な局ID。
            payload: 元JSON SHA-256と再集計に必要な局summary。

        戻り値:
            なし。局ファイルが新規作成される。

        例外:
            ValueError: ID・record形式が不正、または同じ局IDが既に保存済みの場合。
            AnalysisCheckpointWriteError: 局checkpointの原子的保存に失敗した場合。

        副作用:
            `games/<game_id>.json`を同一directoryのtemporary file経由で原子的に作る。

        前提条件:
            呼出側が元棋譜を完全合法再生し、予定・終局・計時・条件hashを照合済みである。
        """
        _validate_game_id(game_id)
        if not isinstance(payload, Mapping) or set(payload) != _RECORD_KEYS:
            raise ValueError("分析局checkpointのrecord形式が不正です")
        record = dict(payload)
        _validate_sha256(record["input_sha256"], "局入力SHA-256")
        if type(record["summary"]) is not dict:
            raise ValueError("分析局checkpoint summaryはobjectで指定してください")
        self._validate_store()
        path = self.root / "games" / f"{game_id}.json"
        if path.exists() or path.is_symlink():
            raise ValueError(f"分析局checkpointは既に存在します: {game_id}")
        envelope = {
            "format": _GAME_CHECKPOINT_FORMAT,
            "game_id": game_id,
            "record": record,
        }
        envelope["sha256"] = _checksum(envelope)
        try:
            comparison_io.atomic_write_json(path, envelope)
        except TypeError, ValueError:
            raise
        except OSError as error:
            raise AnalysisCheckpointWriteError(
                f"分析局checkpointを書き込めません: {game_id}: {error}"
            ) from error

    def load_game(self, game_id: str) -> Mapping[str, object] | None:
        """保存済み局recordを形式・checksum検証後に返す。

        引数:
            game_id: 読み戻す比較予定の局ID。

        戻り値:
            有効なrecord mapping。未保存ならNone。

        例外:
            ValueError: JSON、形式、checksum、ID、通常file条件に違反する場合。
            OSError: checkpoint fileが読めない場合。

        副作用:
            root・games構造と一局JSONを読み取る。manifestはcreate/resumeで検証・保持し、
            各局の読込ごとには再解析しない。checkpointを変更しない。

        前提条件:
            入力比較側のJSON hashとの照合は呼出側で行う。
        """
        _validate_game_id(game_id)
        self._validate_store()
        path = self.root / "games" / f"{game_id}.json"
        if path.is_symlink():
            raise ValueError(f"分析局checkpointは通常fileではありません: {game_id}")
        if not path.exists():
            return None
        if (
            not path.is_file()
            or path.resolve().parent != (self.root / "games").resolve()
        ):
            raise ValueError(f"分析局checkpointは通常fileではありません: {game_id}")
        value = decode_object(path.read_bytes(), context=f"分析checkpoint {game_id}")
        if set(value) != _GAME_KEYS or value.get("format") != _GAME_CHECKPOINT_FORMAT:
            raise ValueError(f"分析局checkpoint形式が対応していません: {game_id}")
        if value.get("game_id") != game_id:
            raise ValueError(f"分析局checkpoint IDが一致しません: {game_id}")
        record = value.get("record")
        if type(record) is not dict or set(record) != _RECORD_KEYS:
            raise ValueError(f"分析局checkpoint record形式が不正です: {game_id}")
        _validate_sha256(record["input_sha256"], "局入力SHA-256")
        if type(record["summary"]) is not dict:
            raise ValueError(f"分析局checkpoint summary形式が不正です: {game_id}")
        self._validate_checksum(value)
        return record

    def completed_game_ids(self) -> frozenset[str]:
        """検証用形式を満たす予定内の保存済み局IDを返す。

        戻り値:
            manifest.scheduleに含まれ、局JSONとして保存済みの一意なgame ID集合。

        例外:
            ValueError: schedule欠落・重複、予定外ファイル・ID、symlink、directoryなどがある場合。
            OSError: games directoryを列挙できない場合。

        副作用:
            検証済みmanifest内のscheduleとgames directoryのentryを参照する。局JSON本文は読み込まない。

        前提条件:
            個々の局JSON形式・checksum・現在の入力hashは、各IDを`load_game`した後に照合する。
            scheduleにないIDは使わず、予定上の欠落局は未完了として許可する。
        """
        manifest = self._cached_manifest()
        schedule = manifest.get("schedule")
        if type(schedule) is not list:
            raise ValueError("分析checkpoint manifestに局scheduleがありません")
        expected_ids: set[str] = set()
        for item in schedule:
            if type(item) is not dict or "game_id" not in item:
                raise ValueError("分析checkpoint manifestの局scheduleが不正です")
            game_id = item["game_id"]
            _validate_game_id(game_id)
            if game_id in expected_ids:
                raise ValueError(
                    f"分析checkpoint scheduleの局IDが重複しています: {game_id}"
                )
            expected_ids.add(game_id)

        self._validate_store()
        games_directory = self.root / "games"
        completed: set[str] = set()
        for path in games_directory.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ValueError(
                    f"分析局checkpointは通常fileではありません: {path.name}"
                )
            match = re.fullmatch(r"(game-[0-9]{6,})\.json", path.name)
            if match is None:
                raise ValueError(f"分析局checkpointのファイル名が不正です: {path.name}")
            game_id = match.group(1)
            if game_id not in expected_ids:
                raise ValueError(f"分析checkpointに予定外の局があります: {game_id}")
            if game_id in completed:
                raise ValueError(f"分析checkpointの局IDが重複しています: {game_id}")
            completed.add(game_id)
        return frozenset(completed)

    def remove(self) -> None:
        """manifestを検証してcheckpoint directoryを削除する。

        戻り値:
            なし。checkpointが存在しない場合も成功する。

        例外:
            ValueError: symlinkまたは壊れたmanifestを指す場合。
            OSError: 削除に失敗した場合。

        副作用:
            完成結果保存後にcheckpoint一式を再帰削除する。

        前提条件:
            呼出側が最終analysis JSONの新規保存に成功している。
        """
        if self.root.is_symlink():
            raise ValueError("分析checkpoint rootはsymlinkにできません")
        if not self.root.exists():
            return
        self._read_manifest()
        shutil.rmtree(self.root)

    def _read_manifest(self) -> Mapping[str, object]:
        """manifest fileの固定path・形式・checksumを検証してmappingを返す。"""
        if self.root.is_symlink() or not self.root.is_dir():
            raise ValueError("分析checkpoint rootが通常directoryではありません")
        path = self.root / "manifest.json"
        if path.is_symlink() or not path.is_file():
            raise ValueError("分析checkpoint manifestが通常fileではありません")
        value = decode_object(path.read_bytes(), context="分析checkpoint manifest")
        if set(value) != _MANIFEST_KEYS or value.get("format") != _CHECKPOINT_FORMAT:
            raise ValueError("分析checkpoint形式が対応していません")
        if type(value.get("manifest")) is not dict:
            raise ValueError("分析checkpoint manifest形式が不正です")
        self._validate_checksum(value)
        return value["manifest"]

    def _validate_store(self) -> None:
        """初回のmanifest検証後はrootとgames directoryの固定構造を検証する。"""
        if self._manifest_cache is None:
            self._manifest_cache = self._read_manifest()
        elif self.root.is_symlink() or not self.root.is_dir():
            raise ValueError("分析checkpoint rootが通常directoryではありません")
        games = self.root / "games"
        if games.is_symlink() or not games.is_dir():
            raise ValueError("分析checkpoint games directoryが不正です")

    def _cached_manifest(self) -> Mapping[str, object]:
        """create/resume時に検証したmanifestを局ごとの操作で再利用する。"""
        if self._manifest_cache is None:
            self._manifest_cache = self._read_manifest()
        return self._manifest_cache

    @staticmethod
    def _validate_checksum(value: Mapping[str, object]) -> None:
        """envelopeのsha256を他keyから独立して照合する。"""
        digest = value.get("sha256")
        _validate_sha256(digest, "分析checkpoint checksum")
        unsigned = {key: item for key, item in value.items() if key != "sha256"}
        if digest != _checksum(unsigned):
            raise ValueError("分析checkpoint checksumが一致しません")


def _validate_game_id(game_id: object) -> None:
    """局IDを安全な固定ファイル名形式に限定する。"""
    if not isinstance(game_id, str) or _GAME_ID_PATTERN.fullmatch(game_id) is None:
        raise ValueError("分析局checkpoint IDが不正です")


def _validate_sha256(value: object, context: str) -> str:
    """lowercase SHA-256表記を検証して返す。"""
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{context}が不正です")
    return value


def _checksum(value: Mapping[str, object]) -> str:
    """JSON objectをcanonical bytesにしSHA-256を計算する。"""
    try:
        serialized = json.dumps(
            dict(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ValueError("分析checkpointにJSON互換でない値があります") from error
    return hashlib.sha256(serialized).hexdigest()
