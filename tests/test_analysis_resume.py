"""分析CLIのチェックポイント保存境界を確認する。"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from kaname_shogi import analysis_resume


class AnalysisCheckpointStoreTests(unittest.TestCase):
    """一局checkpointの形式・完全性・排他境界を検証する。"""

    def _store_type(self):
        store_type = getattr(analysis_resume, "AnalysisCheckpointStore", None)
        self.assertIsNotNone(store_type, "分析checkpoint storeが未実装です")
        return store_type

    def _lock(self):
        lock = getattr(analysis_resume, "analysis_run_lock", None)
        self.assertIsNotNone(lock, "分析排他lockが未実装です")
        return lock

    @staticmethod
    def _manifest():
        return {
            "input_dir": "/fixture/input",
            "conditions_sha256": "a" * 64,
            "schedule": [{"game_id": "game-000001"}],
        }

    @staticmethod
    def _game_payload():
        return {
            "input_sha256": "b" * 64,
            "summary": {"reason": "ply_limit", "plies": 2},
        }

    def test_checkpoint_round_trip_and_duplicate_id_preserves_original(self):
        """一局記録を再読込し、重複IDで確定記録を上書きしない。

        不完全な上書きで以前に検証した勝敗や入力hashを失う誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            manifest = self._manifest()
            store = self._store_type().create(root, manifest)
            payload = self._game_payload()

            self.assertEqual(store.read_manifest(), manifest)
            store.save_game("game-000001", payload)
            saved_path = root / "games" / "game-000001.json"
            original = saved_path.read_bytes()
            self.assertEqual(store.load_game("game-000001"), payload)

            with self.assertRaises(ValueError):
                store.save_game("game-000001", {**payload, "input_sha256": "c" * 64})

            self.assertEqual(saved_path.read_bytes(), original)

    def test_manifest_checksum_mismatch_is_rejected(self):
        """manifestの条件値だけが変わったcheckpointを破損として拒否する。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            store = self._store_type().create(root, self._manifest())
            manifest_path = root / "manifest.json"
            stored = json.loads(manifest_path.read_bytes())
            stored["manifest"]["conditions_sha256"] = "c" * 64
            manifest_path.write_text(json.dumps(stored), encoding="utf-8")

            with self.assertRaises(ValueError):
                store.read_manifest()

    def test_manifest_cache_isolated_from_input_and_returned_mapping(self):
        """入力mappingや公開読込値の変更が内部schedule cacheへ漏れない。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            manifest = self._manifest()
            store = self._store_type().create(root, manifest)
            store.save_game("game-000001", self._game_payload())

            manifest["schedule"][0]["game_id"] = "game-000002"
            self.assertEqual(store.completed_game_ids(), frozenset({"game-000001"}))

            returned_manifest = store.read_manifest()
            returned_manifest["schedule"][0]["game_id"] = "game-000003"
            self.assertEqual(store.completed_game_ids(), frozenset({"game-000001"}))

    def test_resume_rejects_manifest_mismatch(self):
        """入力識別値が変わった状態を別の比較条件として再開しない。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            store = self._store_type().create(root, self._manifest())

            with self.assertRaises(ValueError):
                self._store_type().resume(
                    root,
                    {**self._manifest(), "conditions_sha256": "c" * 64},
                )

            self.assertEqual(store.read_manifest(), self._manifest())

    def test_completed_game_ids_rejects_unexpected_entries(self):
        """局checkpoint directoryの予定外ファイルを見逃さない。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            store = self._store_type().create(root, self._manifest())
            store.save_game("game-000001", self._game_payload())
            self.assertEqual(store.completed_game_ids(), frozenset({"game-000001"}))

            (root / "games" / "game-not-a-number.json").write_text(
                "{}", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                store.completed_game_ids()

    def test_completed_game_ids_rejects_unplanned_game_id(self):
        """manifest予定にない局IDのcheckpointを再利用しない。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            store = self._store_type().create(root, self._manifest())
            extra = root / "games" / "game-000002.json"
            extra.write_text("{}", encoding="utf-8")

            with self.assertRaises(ValueError):
                store.completed_game_ids()

    def test_completed_game_ids_rejects_symlinks(self):
        """外部ファイルを指す局checkpoint symlinkを完了局として数えない。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            store = self._store_type().create(root, self._manifest())
            target = Path(directory) / "outside.json"
            target.write_text("{}", encoding="utf-8")
            (root / "games" / "game-000001.json").symlink_to(target)

            with self.assertRaises(ValueError):
                store.completed_game_ids()

    def test_unknown_game_checkpoint_format_is_rejected(self):
        """未知checkpoint形式を既知形式として読み込まない。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            store = self._store_type().create(root, self._manifest())
            store.save_game("game-000001", self._game_payload())
            saved_path = root / "games" / "game-000001.json"
            stored = json.loads(saved_path.read_bytes())
            stored["format"] = "unknown-format"
            saved_path.write_text(json.dumps(stored), encoding="utf-8")

            with self.assertRaises(ValueError):
                store.load_game("game-000001")

    def test_corrupted_game_checkpoint_json_is_rejected(self):
        """壊れたJSON局記録を空や未完了局として扱わない。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            store = self._store_type().create(root, self._manifest())
            saved_path = root / "games" / "game-000001.json"
            saved_path.write_text("{broken", encoding="utf-8")

            with self.assertRaises(ValueError):
                store.load_game("game-000001")

    def test_checkpoint_checksum_mismatch_is_rejected(self):
        """局summaryだけが変わったcheckpointを破損として拒否する。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            store = self._store_type().create(root, self._manifest())
            store.save_game("game-000001", self._game_payload())
            saved_path = root / "games" / "game-000001.json"
            stored = json.loads(saved_path.read_bytes())
            stored["record"]["summary"]["reason"] = "checkmate"
            saved_path.write_text(json.dumps(stored), encoding="utf-8")

            with self.assertRaises(ValueError):
                store.load_game("game-000001")

    def test_symlink_game_checkpoint_is_rejected(self):
        """checkpoint内の局JSON symlinkを外部成果物として拒否する。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            store = self._store_type().create(root, self._manifest())
            store.save_game("game-000001", self._game_payload())
            saved_path = root / "games" / "game-000001.json"
            target = Path(directory) / "outside.json"
            target.write_text("{}", encoding="utf-8")
            saved_path.unlink()
            saved_path.symlink_to(target)

            with self.assertRaises(ValueError):
                store.load_game("game-000001")

    def test_run_lock_rejects_competitor_and_releases_owned_file(self):
        """同じ出力先の二重実行を拒否し、自分のlockだけを解放する。"""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "analysis.json"
            lock_path = output.with_name(output.name + ".lock")
            run_lock = self._lock()

            with run_lock(output):
                self.assertTrue(lock_path.is_file())
                with self.assertRaises(ValueError):
                    with run_lock(output):
                        self.fail("競合した二つ目の分析へ入ってはいけません")

            self.assertFalse(lock_path.exists())

    def test_run_lock_removes_partial_file_when_initial_write_fails(self):
        """lock初期書込が途中失敗した場合は自分の部分fileを除去する。"""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "analysis.json"
            lock_path = output.with_name(output.name + ".lock")
            run_lock = self._lock()
            real_fdopen = analysis_resume.os.fdopen

            class PartialLockFile:
                def __init__(self, descriptor):
                    self.file = real_fdopen(descriptor, "w", encoding="ascii")

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, traceback):
                    self.file.close()
                    return False

                def write(self, value):
                    self.file.write(value[:3])
                    self.file.flush()
                    raise OSError("injected lock write failure")

                def flush(self):
                    self.file.flush()

                def fileno(self):
                    return self.file.fileno()

            with (
                patch.object(
                    analysis_resume.os,
                    "fdopen",
                    side_effect=lambda descriptor, *args, **kwargs: PartialLockFile(
                        descriptor
                    ),
                ),
                self.assertRaises(analysis_resume.AnalysisCheckpointWriteError),
            ):
                with run_lock(output):
                    self.fail("lock初期書込失敗後に分析へ入ってはいけません")

            self.assertFalse(lock_path.exists())

    def test_run_lock_closes_descriptor_and_removes_file_when_fstat_fails(self):
        """lock作成直後のfstat失敗でもFDと部分lockを残さない。"""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "analysis.json"
            lock_path = output.with_name(output.name + ".lock")
            run_lock = self._lock()
            real_open = analysis_resume.os.open
            opened_descriptors = []

            def track_open(*args, **kwargs):
                descriptor = real_open(*args, **kwargs)
                opened_descriptors.append(descriptor)
                return descriptor

            with (
                patch.object(analysis_resume.os, "open", side_effect=track_open),
                patch.object(
                    analysis_resume.os,
                    "fstat",
                    side_effect=OSError("injected fstat failure"),
                ),
                self.assertRaises(analysis_resume.AnalysisCheckpointWriteError),
            ):
                with run_lock(output):
                    self.fail("fstat失敗後に分析へ入ってはいけません")

            self.assertFalse(lock_path.exists())
            self.assertEqual(len(opened_descriptors), 1)
            with self.assertRaises(OSError):
                analysis_resume.os.fstat(opened_descriptors[0])

    def test_run_lock_cleans_up_when_fstat_is_interrupted(self):
        """lock作成直後のKeyboardInterruptでも部分lockとFDを残さない。"""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "analysis.json"
            lock_path = output.with_name(output.name + ".lock")
            run_lock = self._lock()
            real_open = analysis_resume.os.open
            opened_descriptors = []

            def track_open(*args, **kwargs):
                descriptor = real_open(*args, **kwargs)
                opened_descriptors.append(descriptor)
                return descriptor

            with (
                patch.object(analysis_resume.os, "open", side_effect=track_open),
                patch.object(
                    analysis_resume.os, "fstat", side_effect=KeyboardInterrupt
                ),
                self.assertRaises(KeyboardInterrupt),
            ):
                with run_lock(output):
                    self.fail("fstat割込み後に分析へ入ってはいけません")

            self.assertFalse(lock_path.exists())
            self.assertEqual(len(opened_descriptors), 1)
            with self.assertRaises(OSError):
                analysis_resume.os.fstat(opened_descriptors[0])

    def test_run_lock_reports_descriptor_cleanup_error_after_interruption(self):
        """割込み時にFD後始末も失敗した可能性を利用者へ知らせる。"""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "analysis.json"
            lock_path = output.with_name(output.name + ".lock")
            run_lock = self._lock()
            real_close = analysis_resume.os.close
            stderr = io.StringIO()

            def close_then_fail(descriptor):
                real_close(descriptor)
                raise OSError("injected close failure")

            with (
                patch.object(
                    analysis_resume.os, "fstat", side_effect=KeyboardInterrupt
                ),
                patch.object(analysis_resume.os, "close", side_effect=close_then_fail),
                redirect_stderr(stderr),
                self.assertRaises(KeyboardInterrupt),
            ):
                with run_lock(output):
                    self.fail("fstat割込み後に分析へ入ってはいけません")

            self.assertFalse(lock_path.exists())
            self.assertIn("後始末", stderr.getvalue())

    def test_per_game_operations_do_not_reparse_manifest(self):
        """store生成後の局保存・読込でschedule全体を含むmanifestを再解析しない。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            store = self._store_type().create(root, self._manifest())
            with patch.object(
                store, "_read_manifest", wraps=store._read_manifest
            ) as read_manifest:
                store.save_game("game-000001", self._game_payload())
                self.assertEqual(store.load_game("game-000001"), self._game_payload())
                self.assertEqual(store.completed_game_ids(), frozenset({"game-000001"}))

            self.assertEqual(read_manifest.call_count, 0)

    def test_create_cleans_partial_checkpoint_when_manifest_save_is_interrupted(self):
        """manifest作成中の割込み後に再開不能なroot directoryを残さない。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            store_type = self._store_type()

            with (
                patch.object(
                    analysis_resume.comparison_io,
                    "atomic_write_json",
                    side_effect=KeyboardInterrupt,
                ),
                self.assertRaises(KeyboardInterrupt),
            ):
                store_type.create(root, self._manifest())

            self.assertFalse(root.exists())

    def test_create_cleans_root_when_interrupted_immediately_after_mkdir(self):
        """root作成直後、作成済み記録前の割込みでも空rootを残さない。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "analysis.json.checkpoint"
            real_mkdir = Path.mkdir

            def create_then_interrupt(path, *args, **kwargs):
                result = real_mkdir(path, *args, **kwargs)
                if path == root:
                    raise KeyboardInterrupt
                return result

            with (
                patch.object(Path, "mkdir", new=create_then_interrupt),
                self.assertRaises(KeyboardInterrupt),
            ):
                self._store_type().create(root, self._manifest())

            self.assertFalse(root.exists())

    def test_run_lock_preserves_stale_lock_for_human_inspection(self):
        """残存lockを自動削除せず、人のPID確認を要求する。"""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "analysis.json"
            lock_path = output.with_name(output.name + ".lock")
            lock_path.write_text("pid=not-running-yet\n", encoding="ascii")
            run_lock = self._lock()

            with self.assertRaises(ValueError):
                with run_lock(output):
                    self.fail("残存lockがある状態で分析へ入ってはいけません")

            self.assertEqual(
                lock_path.read_text(encoding="ascii"), "pid=not-running-yet\n"
            )
