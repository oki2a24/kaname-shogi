"""C2の方式名と重みを比較CLI条件へ接続する契約を確認する。"""

import tempfile
import unittest
from pathlib import Path

from kaname_shogi.comparison import make_schedule
from kaname_shogi.comparison_io import conditions_payload, load_config
from kaname_shogi.movegen import MoveSelectionPolicy
from tests import test_comparison_io as fixtures


class KingSafetyComparisonInputTests(unittest.TestCase):
    def test_comparison_cli_accepts_both_king_safety_policies(self):
        """比較CLIは対照と候補の両方式名を受け付ける。

        条件解析に一方を登録し忘れたり二方式を取り違える誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            positions = fixtures.ComparisonInputTests._write_positions(
                directory, [fixtures.ComparisonInputTests._position_entry()]
            )
            args = fixtures.ComparisonInputTests._config_args(
                positions,
                Path(directory) / "results",
                **{
                    "--baseline": "material-king-safety-material-only",
                    "--candidate": "material-king-safety",
                },
            )
            try:
                config = load_config(args)
            except ValueError as error:
                self.fail(f"C2方式を比較条件として受け付けません: {error}")
        self.assertIs(
            config.baseline, MoveSelectionPolicy.MATERIAL_KING_SAFETY_MATERIAL_ONLY
        )
        self.assertIs(config.candidate, MoveSelectionPolicy.MATERIAL_KING_SAFETY)

    def test_conditions_save_both_weights_for_each_seed_mode(self):
        """主乱数種と種一覧の両条件で二方式の重みが保存される。

        条件保存時の方式名欠落や安全度0・1の取り違えを検出する。
        """
        for use_seed_list in (False, True):
            with (
                self.subTest(seed_list=use_seed_list),
                tempfile.TemporaryDirectory() as directory,
            ):
                positions = fixtures.ComparisonInputTests._write_positions(
                    directory, [fixtures.ComparisonInputTests._position_entry()]
                )
                args = fixtures.ComparisonInputTests._config_args(
                    positions,
                    Path(directory) / "results",
                    **{
                        "--baseline": "material-king-safety-material-only",
                        "--candidate": "material-king-safety",
                        "--pairs-per-position": "1",
                    },
                )
                if use_seed_list:
                    seed_list = fixtures.ComparisonInputTests._write_seed_list(
                        directory, positions, pairs_per_position=1
                    )
                    args.remove("--seed")
                    args.remove("17")
                    args.extend(("--seed-list", str(seed_list)))
                config = load_config(args)
                try:
                    payload = conditions_payload(
                        config, make_schedule(config), source_root=Path.cwd()
                    )
                except KeyError as error:
                    self.fail(f"C2方式を条件へ保存できません: {error}")
                self.assertEqual(
                    payload["baseline"], "material-king-safety-material-only"
                )
                self.assertEqual(payload["candidate"], "material-king-safety")
                self.assertEqual(
                    payload.get("policy_parameters"),
                    {
                        "baseline": {
                            "material": 10,
                            "safety": 0,
                            "mate_priority": True,
                        },
                        "candidate": {
                            "material": 10,
                            "safety": 1,
                            "mate_priority": True,
                        },
                    },
                )

    def test_main_seed_records_weights_when_only_one_policy_is_new(self):
        """主乱数種で片側だけC2方式でもその重みを保存する。

        両側がC2の場合だけ保存する分岐や、先後の役割の取り違えを検出する。
        """
        for baseline, candidate, expected in (
            (
                "material",
                "material-king-safety",
                {
                    "baseline": {},
                    "candidate": {"material": 10, "safety": 1, "mate_priority": True},
                },
            ),
            (
                "material-king-safety-material-only",
                "material",
                {
                    "baseline": {"material": 10, "safety": 0, "mate_priority": True},
                    "candidate": {},
                },
            ),
        ):
            with (
                self.subTest(baseline=baseline),
                tempfile.TemporaryDirectory() as directory,
            ):
                positions = fixtures.ComparisonInputTests._write_positions(
                    directory, [fixtures.ComparisonInputTests._position_entry()]
                )
                args = fixtures.ComparisonInputTests._config_args(
                    positions,
                    Path(directory) / "results",
                    **{"--baseline": baseline, "--candidate": candidate},
                )
                config = load_config(args)
                payload = conditions_payload(
                    config, make_schedule(config), source_root=Path.cwd()
                )
                self.assertEqual(payload.get("policy_parameters"), expected)

    def test_parallel_seed_list_preserves_king_safety_weights(self):
        """並列・種一覧の条件にもC2重みとworker数を保存する。

        v3への変換時に重みを落とす、または実行条件を間違う誤りを検出する。
        """
        with tempfile.TemporaryDirectory() as directory:
            positions = fixtures.ComparisonInputTests._write_positions(
                directory, [fixtures.ComparisonInputTests._position_entry()]
            )
            seeds = fixtures.ComparisonInputTests._write_seed_list(
                directory, positions, pairs_per_position=1
            )
            args = fixtures.ComparisonInputTests._config_args(
                positions,
                Path(directory) / "results",
                **{
                    "--baseline": "material-king-safety-material-only",
                    "--candidate": "material-king-safety",
                    "--pairs-per-position": "1",
                },
            )
            args.remove("--seed")
            args.remove("17")
            args.extend(("--seed-list", str(seeds), "--workers", "2"))
            config = load_config(args)
            payload = conditions_payload(
                config, make_schedule(config), source_root=Path.cwd()
            )
            self.assertEqual(payload["format"], "kaname-shogi-comparison-conditions-v3")
            self.assertEqual(
                payload["execution"], {"executor": "process-pool", "workers": 2}
            )
            self.assertEqual(
                payload["policy_parameters"],
                {
                    "baseline": {"material": 10, "safety": 0, "mate_priority": True},
                    "candidate": {"material": 10, "safety": 1, "mate_priority": True},
                },
            )
