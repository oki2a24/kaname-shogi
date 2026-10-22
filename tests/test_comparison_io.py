"""比較実験の入力セット・CLI条件検証を確認する。"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kaname_shogi import comparison_io as comparison_io_module
from kaname_shogi.comparison import (
    ComparisonConfig,
    ComparisonPosition,
    GameEndReason,
    GameResult,
    MoveTiming,
    make_schedule,
)
from kaname_shogi.game_record import GameRecord
from kaname_shogi.model import Side, Square, create_initial_position
from kaname_shogi.movegen import MoveSelectionPolicy
from kaname_shogi.usi_move import parse_usi_move

try:
    from kaname_shogi.comparison_io import load_config, load_positions
except ModuleNotFoundError as error:
    if error.name != "kaname_shogi.comparison_io":
        raise
    load_config = load_positions = None

conditions_payload = getattr(comparison_io_module, "conditions_payload", None)
game_payload = getattr(comparison_io_module, "game_payload", None)
summary_payload = getattr(comparison_io_module, "summary_payload", None)
atomic_write_json = getattr(comparison_io_module, "atomic_write_json", None)


class ComparisonInputTests(unittest.TestCase):
    def _require_implementation(self):
        """未実装APIをimport失敗ではなく機能不足として示す。"""
        self.assertIsNotNone(load_positions, "比較局面セット読込が未実装です")
        self.assertIsNotNone(load_config, "比較条件の検証が未実装です")

    @staticmethod
    def _position_entry(position_id="one", setup_moves=None):
        """比較設計の局面セットに使う最小項目を返す。"""
        return {
            "id": position_id,
            "setup_moves": [] if setup_moves is None else setup_moves,
            "rationale": "テスト用の局面",
        }

    @classmethod
    def _write_positions(cls, directory, positions, *, format_name=None):
        """局面セットJSONを一時ディレクトリに保存しパスを返す。"""
        payload = {
            "format": format_name or "kaname-shogi-comparison-positions-v1",
            "id": "test-set",
            "positions": positions,
        }
        path = Path(directory) / "positions.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    @staticmethod
    def _config_args(positions_path, output_path, **overrides):
        """必須CLI引数を具体値で作り、指定されたものだけを置き換える。"""
        values = {
            "--baseline": "material",
            "--candidate": "random",
            "--positions": str(positions_path),
            "--pairs-per-position": "2",
            "--seed": "17",
            "--max-plies": "40",
            "--output-dir": str(output_path),
        }
        values.update(overrides)
        args = []
        for key, value in values.items():
            args.extend((key, value))
        return args

    def test_loads_approved_start_positions_and_expected_sfen(self):
        """承認済み4局面を合法手順から設計値どおりに作る。

        局面ID・準備手順・理由または手数欄を取り違え、別の開始局面を生成する誤りを
        独立した設計値との比較で検出する。
        """
        self._require_implementation()
        path = Path(__file__).parents[1] / "data/comparison/start-positions-v1.json"

        positions = load_positions(path)

        self.assertEqual(
            [
                (
                    item.position_id,
                    item.setup_moves,
                    item.rationale,
                    item.start_sfen,
                    item.initial_move_number,
                )
                for item in positions
            ],
            [
                (
                    "initial",
                    (),
                    "平手初期局面",
                    "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
                    1,
                ),
                (
                    "open-bishops",
                    ("7g7f", "3c3d", "2g2f", "8c8d"),
                    "双方の角道と飛車先の歩を動かした序盤",
                    "lnsgkgsnl/1r5b1/p1pppp1pp/1p4p2/9/2P4P1/PP1PPPP1P/1B5R1/LNSGKGSNL b - 5",
                    5,
                ),
                (
                    "closed-bishop",
                    ("7g7f", "8c8d", "6g6f"),
                    "先手が角道を閉じた、後手番の序盤",
                    "lnsgkgsnl/1r5b1/p1ppppppp/1p7/9/2PP5/PP2PPPPP/1B5R1/LNSGKGSNL w - 4",
                    4,
                ),
                (
                    "pawn-exchanges",
                    (
                        "7g7f",
                        "3c3d",
                        "2g2f",
                        "8c8d",
                        "2f2e",
                        "8d8e",
                        "2e2d",
                        "2c2d",
                        "2h2d",
                        "8e8f",
                        "8g8f",
                        "8b8f",
                    ),
                    "双方の飛車先で歩を交換し、双方に持ち歩がある局面",
                    "lnsgkgsnl/7b1/p1pppp2p/6pR1/9/1rP6/P2PPPP1P/1B7/LNSGKGSNL b 2P2p 13",
                    13,
                ),
            ],
        )

    def test_rejects_duplicate_json_keys(self):
        """同名JSONキーを持つ局面セットを拒否する。

        JSON標準読込が後勝ちで重複キーを隠し、利用者の意図と違う条件で実験する誤りを
        検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "positions.json"
            path.write_text(
                '{"format":"kaname-shogi-comparison-positions-v1",'
                '"id":"first","id":"second","positions":[]}',
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_positions(path)

    def test_rejects_unknown_and_missing_position_set_keys(self):
        """局面セットと項目の未知キー・必須キー欠落を拒否する。

        未知欄を黙って無視したり、欠落欄を暗黙の既定値で補う誤りを検出する。
        """
        self._require_implementation()
        invalid_payloads = (
            {
                "format": "kaname-shogi-comparison-positions-v1",
                "id": "set",
                "positions": [self._position_entry()],
                "unexpected": True,
            },
            {
                "format": "kaname-shogi-comparison-positions-v1",
                "positions": [self._position_entry()],
            },
            {
                "format": "kaname-shogi-comparison-positions-v1",
                "id": "set",
                "positions": [{"id": "one", "setup_moves": []}],
            },
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, payload in enumerate(invalid_payloads):
                with self.subTest(index=index):
                    path = Path(directory) / f"positions-{index}.json"
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_positions(path)

    def test_rejects_empty_set_unknown_format_duplicate_ids_and_duplicate_positions(
        self,
    ):
        """空局面列、未知形式、重複IDと局面同一性の重複を拒否する。

        表記IDだけを見て盤面・持ち駒・手番が同じ項目を別局面として数える誤りを
        検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            cases = (
                ([], "kaname-shogi-comparison-positions-v1"),
                ([self._position_entry()], "unknown-format"),
                (
                    [self._position_entry("same"), self._position_entry("same")],
                    "kaname-shogi-comparison-positions-v1",
                ),
                (
                    [self._position_entry("first"), self._position_entry("second")],
                    "kaname-shogi-comparison-positions-v1",
                ),
            )
            for index, (positions, format_name) in enumerate(cases):
                with self.subTest(index=index):
                    path = self._write_positions(
                        directory, positions, format_name=format_name
                    )
                    with self.assertRaises(ValueError):
                        load_positions(path)

    def test_rejects_illegal_last_setup_move(self):
        """最後の準備手が不合法な局面セットを拒否する。

        先頭の局面だけを検証し、後半の不正手を含むセットを受理する誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_positions(
                directory,
                [self._position_entry(setup_moves=["7g7f", "7g7f"])],
            )

            with self.assertRaises(ValueError):
                load_positions(path)

    def test_rejects_setup_sequence_that_reaches_repetition(self):
        """準備中に千日手が成立する局面を比較開始位置として拒否する。

        終局済みの準備履歴を開始位置の新しい反復履歴へ持ち込んで実験を始める誤りを
        検出する。
        """
        self._require_implementation()
        cycle = ("5i5h", "5a5b", "5h5i", "5b5a")
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_positions(
                directory, [self._position_entry(setup_moves=list(cycle * 4))]
            )

            with self.assertRaises(ValueError):
                load_positions(path)

    def test_rejects_bad_cli_values_without_creating_output_directory(self):
        """不正なCLI条件を出力先作成前に拒否する。

        boolを整数として受け入れる、必須条件を補う、または失敗後に出力ディレクトリを
        残す誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._write_positions(directory, [self._position_entry()])
            bad_values = (
                {"--pairs-per-position": "0"},
                {"--seed": "-1"},
                {"--max-plies": "0"},
                {"--baseline": "material", "--candidate": "material"},
            )
            for index, overrides in enumerate(bad_values):
                with self.subTest(overrides=overrides):
                    output_path = Path(directory) / f"output-{index}"
                    args = self._config_args(positions_path, output_path, **overrides)
                    with self.assertRaises(ValueError):
                        load_config(args)
                    self.assertFalse(output_path.exists())

    def test_rejects_late_invalid_position_before_creating_output_directory(self):
        """後半局面の不正手も対局開始前に検出する。

        一局目の実行・条件保存後に不正な局面を発見する部分検証を検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._write_positions(
                directory,
                [
                    self._position_entry("valid"),
                    self._position_entry("invalid", ["7g7f", "7g7f"]),
                ],
            )
            output_path = Path(directory) / "results"

            with self.assertRaises(ValueError):
                load_config(self._config_args(positions_path, output_path))

            self.assertFalse(output_path.exists())

    def test_config_parses_the_same_position_file_snapshot_it_records(self):
        """条件記録と開始局面を一度読んだ同じファイル内容から作る。

        読込中に局面セットが差し替わると、保存されるSHA対象内容と実験した局面が
        食い違う二重読込を検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_positions(
                directory, [self._position_entry("first", ["7g7f"])]
            )
            first_snapshot = path.read_bytes()
            changed_path = self._write_positions(
                directory, [self._position_entry("second", ["7g7f", "3c3d"])]
            )
            second_snapshot = changed_path.read_bytes()
            output_path = Path(directory) / "results"
            real_read_bytes = Path.read_bytes
            read_count = 0

            def changing_read_bytes(file_path):
                nonlocal read_count
                if file_path == path:
                    read_count += 1
                    return first_snapshot if read_count == 1 else second_snapshot
                return real_read_bytes(file_path)

            with patch.object(Path, "read_bytes", changing_read_bytes):
                config = load_config(self._config_args(path, output_path))

            self.assertEqual(config.positions_json, first_snapshot)
            self.assertEqual(tuple(p.position_id for p in config.positions), ("first",))

    def test_rejects_unknown_argument_and_existing_or_invalid_output_directory(self):
        """未知引数・既存出力先・存在しない親を拒否する。

        条件入力の誤りや上書き先を受理し、確定済みファイルを壊す誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            positions_path = self._write_positions(directory, [self._position_entry()])
            existing = Path(directory) / "existing"
            existing.mkdir()
            missing_parent_output = Path(directory) / "missing-parent" / "results"
            for output_path, extra, already_exists in (
                (Path(directory) / "fresh", ("--unexpected", "1"), False),
                (existing, (), True),
                (missing_parent_output, (), False),
            ):
                with self.subTest(output_path=output_path):
                    args = self._config_args(positions_path, output_path) + list(extra)
                    with self.assertRaises(ValueError):
                        load_config(args)
                    self.assertEqual(output_path.exists(), already_exists)


class ComparisonSerializationTests(unittest.TestCase):
    def _require_implementation(self):
        """保存値APIの不足をimport失敗ではなく振る舞いの失敗にする。"""
        self.assertIsNotNone(conditions_payload, "条件JSON変換が未実装です")
        self.assertIsNotNone(game_payload, "局JSON変換が未実装です")
        self.assertIsNotNone(summary_payload, "summary JSON変換が未実装です")
        self.assertIsNotNone(atomic_write_json, "原子的JSON保存が未実装です")

    @staticmethod
    def _config():
        """期待値を固定しやすい一局面の比較条件を作る。"""
        position = ComparisonPosition(
            "initial",
            (),
            "平手初期局面",
            create_initial_position(),
            "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
            1,
        )
        return ComparisonConfig(
            baseline=MoveSelectionPolicy.MATERIAL,
            candidate=MoveSelectionPolicy.RANDOM,
            positions=(position,),
            pairs_per_position=1,
            seed=17,
            max_plies=40,
            output_dir=Path("results"),
            positions_path=Path("fixtures/positions.json"),
            positions_json=b'{"positions": "captured"}\n',
        )

    @staticmethod
    def _expected_source_sha256(source_root):
        """本番の実装関数を使わず計画記載の長さ前置形式を計算する。"""
        package_root = Path(source_root) / "kaname_shogi"
        digest = hashlib.sha256()
        files = sorted(
            package_root.rglob("*.py"),
            key=lambda path: path.relative_to(package_root).as_posix(),
        )
        for path in files:
            relative_path = path.relative_to(package_root).as_posix().encode("utf-8")
            content = path.read_bytes()
            digest.update(len(relative_path).to_bytes(4, "big", signed=False))
            digest.update(relative_path)
            digest.update(len(content).to_bytes(8, "big", signed=False))
            digest.update(content)
        return digest.hexdigest()

    def test_conditions_payload_has_exact_contract_and_deterministic_fingerprints(self):
        """条件JSONのキー・入力ハッシュ・予定・コード指紋を独立値と照合する。

        元局面JSONの読込内容、予定の先後/種、相対パス長前置を落とす・誤る場合を
        検出し、環境依存値だけをGitメタデータmockで固定する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory)
            package_root = source_root / "kaname_shogi"
            (package_root / "nested").mkdir(parents=True)
            (package_root / "z.py").write_bytes(b"Z = 1\n")
            (package_root / "nested/a.py").write_bytes(b"A = 'ja'\n")
            (package_root / "ignored.pyc").write_bytes(b"not source")
            config = self._config()
            schedule = make_schedule(config)
            git_metadata = {
                "head": "0123456789abcdef",
                "dirty": True,
                "diagnostic": None,
            }
            expected_source_sha256 = self._expected_source_sha256(source_root)

            with patch.object(
                comparison_io_module,
                "_git_metadata",
                return_value=git_metadata,
            ):
                payload = conditions_payload(config, schedule, source_root=source_root)

        self.assertEqual(
            set(payload),
            {
                "format",
                "baseline",
                "candidate",
                "positions_file",
                "positions_sha256",
                "positions",
                "pairs_per_position",
                "seed",
                "max_plies",
                "schedule",
                "timing",
                "clock",
                "repetition",
                "git",
                "runtime",
                "source_sha256",
            },
        )
        self.assertEqual(payload["format"], "kaname-shogi-comparison-conditions-v1")
        self.assertEqual(payload["baseline"], "material")
        self.assertEqual(payload["candidate"], "random")
        self.assertEqual(payload["positions_file"], "fixtures/positions.json")
        self.assertEqual(
            payload["positions_sha256"],
            hashlib.sha256(config.positions_json).hexdigest(),
        )
        self.assertEqual(
            payload["positions"],
            [
                {
                    "id": "initial",
                    "setup_moves": [],
                    "rationale": "平手初期局面",
                    "start_sfen": config.positions[0].start_sfen,
                    "initial_move_number": 1,
                }
            ],
        )
        self.assertEqual(
            payload["schedule"],
            [
                {
                    "game_id": "game-000001",
                    "position_id": "initial",
                    "pair_number": 0,
                    "game_number_in_pair": 1,
                    "baseline_side": "sente",
                    "candidate_side": "gote",
                    "baseline_seed": 17,
                    "candidate_seed": 18,
                },
                {
                    "game_id": "game-000002",
                    "position_id": "initial",
                    "pair_number": 0,
                    "game_number_in_pair": 2,
                    "baseline_side": "gote",
                    "candidate_side": "sente",
                    "baseline_seed": 17,
                    "candidate_seed": 18,
                },
            ],
        )
        self.assertEqual(
            payload["timing"],
            {
                "source": "time.monotonic_ns",
                "start": "immediately_before_legal_moves",
                "end": "immediately_after_choose_move_returns",
                "unit": "nanoseconds",
            },
        )
        self.assertIsNone(payload["clock"])
        self.assertEqual(
            payload["repetition"],
            {
                "ordinary_fourth_occurrence": "continue",
                "ordinary_fifth_occurrence": "terminal",
                "ordinary_rematch": False,
                "perpetual_check_loss": "opposite_side_wins",
                "double_perpetual_check": "unresolved_no_winner",
            },
        )
        self.assertEqual(payload["git"], git_metadata)
        self.assertEqual(payload["source_sha256"], expected_source_sha256)
        self.assertEqual(payload["pairs_per_position"], 1)
        self.assertEqual(payload["seed"], 17)
        self.assertEqual(payload["max_plies"], 40)
        self.assertEqual(
            set(payload["runtime"]),
            {
                "python_version",
                "python_implementation",
                "platform",
                "machine",
                "processor",
            },
        )

    def test_conditions_payload_keeps_git_unknown_with_diagnostic(self):
        """Git判定が使えない環境を架空のHEADやclean状態にしない。

        Git情報の取得失敗時に条件JSONから診断を失う、または不明値を正常値として
        記録する誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory)
            (source_root / "kaname_shogi").mkdir()
            config = self._config()
            with patch.object(
                comparison_io_module,
                "_git_metadata",
                return_value={
                    "head": None,
                    "dirty": None,
                    "diagnostic": "git is unavailable",
                },
            ):
                payload = conditions_payload(
                    config, make_schedule(config), source_root=source_root
                )

        self.assertEqual(
            payload["git"],
            {"head": None, "dirty": None, "diagnostic": "git is unavailable"},
        )

    def test_git_metadata_failure_returns_null_values_and_diagnostic(self):
        """Gitコマンドが起動しない場合にnullと診断を返す。

        コマンド失敗を例外で比較全体へ漏らしたり、cleanなGit状態を捏造する誤りを
        検出する。
        """
        self._require_implementation()
        with patch.object(
            comparison_io_module.subprocess,
            "run",
            side_effect=FileNotFoundError("git missing"),
        ):
            metadata = comparison_io_module._git_metadata(Path("/source"))

        self.assertIsNone(metadata["head"])
        self.assertIsNone(metadata["dirty"])
        self.assertIsInstance(metadata["diagnostic"], str)
        self.assertTrue(metadata["diagnostic"])

    def test_game_payload_preserves_record_v1_and_serializes_winner_and_timing(self):
        """局JSONへ勝者・予定・成功手計時を記録し既存棋譜v1をそのまま埋める。

        棋譜v1へ比較専用キーを混入する、先後と勝者方式を誤る、USI手や時間を落とす
        誤りを手書き期待値で検出する。
        """
        self._require_implementation()
        config = self._config()
        schedule = make_schedule(config)[0]
        record = GameRecord(config.positions[0].start_position)
        record.apply_move(Square(7, 7), Square(7, 6))
        move = parse_usi_move("7g7f")
        result = GameResult(
            schedule=schedule,
            start_sfen=config.positions[0].start_sfen,
            initial_move_number=1,
            record=record,
            reason=GameEndReason.CHECKMATE,
            winner_side=Side.GOTE,
            winner_policy=MoveSelectionPolicy.RANDOM,
            plies=1,
            move_times_ns=(
                MoveTiming(1, Side.SENTE, MoveSelectionPolicy.MATERIAL, move, 123),
            ),
            unfinished_calculation_ns=None,
            error=None,
        )

        payload = game_payload(result, config, conditions_sha256="a" * 64)

        self.assertEqual(
            set(payload),
            {
                "format",
                "conditions_sha256",
                "game_id",
                "position_id",
                "pair_number",
                "game_number_in_pair",
                "baseline",
                "candidate",
                "baseline_seed",
                "candidate_seed",
                "baseline_side",
                "candidate_side",
                "start_sfen",
                "initial_move_number",
                "plies",
                "reason",
                "winner_side",
                "winner_policy",
                "record",
                "move_times",
                "unfinished_calculation",
                "error",
            },
        )
        self.assertEqual(payload["format"], "kaname-shogi-comparison-game-v1")
        self.assertEqual(payload["conditions_sha256"], "a" * 64)
        self.assertEqual(payload["game_id"], "game-000001")
        self.assertEqual(payload["baseline"], "material")
        self.assertEqual(payload["candidate"], "random")
        self.assertEqual(payload["baseline_seed"], 17)
        self.assertEqual(payload["candidate_seed"], 18)
        self.assertEqual(payload["baseline_side"], "sente")
        self.assertEqual(payload["candidate_side"], "gote")
        self.assertEqual(payload["reason"], "checkmate")
        self.assertEqual(payload["winner_side"], "gote")
        self.assertEqual(payload["winner_policy"], "random")
        self.assertEqual(payload["record"], record.to_payload())
        self.assertEqual(
            set(payload["record"]),
            {"format", "initial_position", "moves"},
        )
        self.assertEqual(
            payload["move_times"],
            [
                {
                    "ply": 1,
                    "side": "sente",
                    "policy": "material",
                    "move": "7g7f",
                    "elapsed_ns": 123,
                }
            ],
        )
        self.assertIsNone(payload["unfinished_calculation"])
        self.assertIsNone(payload["error"])

    def test_nonwinning_end_reasons_serialize_null_winner(self):
        """未決着理由を勝者なしとして保存し通常千日手と未裁定を分ける。

        千日手・手数上限・割込み・故障・双方連続王手へ勝者または勝者方式を付ける
        誤りを検出する。
        """
        self._require_implementation()
        config = self._config()
        schedule = make_schedule(config)[0]
        for reason in (
            GameEndReason.REPETITION,
            GameEndReason.PLY_LIMIT,
            GameEndReason.INTERRUPTED,
            GameEndReason.ERROR,
            GameEndReason.UNRESOLVED_DOUBLE_PERPETUAL_CHECK,
        ):
            with self.subTest(reason=reason):
                result = GameResult(
                    schedule=schedule,
                    start_sfen=config.positions[0].start_sfen,
                    initial_move_number=1,
                    record=GameRecord(config.positions[0].start_position),
                    reason=reason,
                    winner_side=None,
                    winner_policy=None,
                    plies=0,
                    move_times_ns=(),
                    unfinished_calculation_ns=None,
                    error="fixture" if reason is GameEndReason.ERROR else None,
                )

                payload = game_payload(result, config, conditions_sha256="b" * 64)

                self.assertIsNone(payload["winner_side"])
                self.assertIsNone(payload["winner_policy"])
                self.assertEqual(payload["reason"], reason.value)

    def test_summary_payload_adds_format_version_without_strength_decision(self):
        """summary JSONの版を固定し、記述集計をそのまま保持する。

        勝率や統計判定をsummaryへ混ぜる、または出力形式版を欠落させる誤りを検出する。
        """
        self._require_implementation()
        summary = {
            "status": "complete",
            "started_games": 2,
            "results": {"repetition": 1, "unresolved_double_perpetual_check": 1},
            "statistical_decision": None,
        }

        payload = summary_payload(summary)

        self.assertEqual(
            payload,
            {"format": "kaname-shogi-comparison-summary-v1", **summary},
        )
        self.assertNotIn("win_rate", payload)
        self.assertNotIn("statistically_significant", payload)

    def test_atomic_json_write_replaces_and_cleans_up_after_write_or_replace_failure(
        self,
    ):
        """JSONを書込失敗時も旧ファイルを保ち、一時ファイルを残さない。

        直接上書きして既存の確定JSONを壊す、一時ファイルを別ディレクトリへ置く、
        失敗後に一時ファイルを残す誤りを検出する。
        """
        self._require_implementation()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "result.json"
            target.write_text("old\n", encoding="utf-8")

            atomic_write_json(target, {"name": "比較", "count": 2})

            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8")),
                {"name": "比較", "count": 2},
            )
            self.assertEqual(list(Path(directory).glob(".result.json.*.tmp")), [])

            target.write_text("stable\n", encoding="utf-8")
            with patch.object(
                comparison_io_module,
                "_json_bytes",
                side_effect=OSError("write failed"),
            ):
                with self.assertRaisesRegex(OSError, "write failed"):
                    atomic_write_json(target, {"new": True})
            self.assertEqual(target.read_text(encoding="utf-8"), "stable\n")
            self.assertEqual(list(Path(directory).glob(".result.json.*.tmp")), [])

            with patch.object(
                comparison_io_module.os,
                "replace",
                side_effect=OSError("replace failed"),
            ):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    atomic_write_json(target, {"new": True})
            self.assertEqual(target.read_text(encoding="utf-8"), "stable\n")
            self.assertEqual(list(Path(directory).glob(".result.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
