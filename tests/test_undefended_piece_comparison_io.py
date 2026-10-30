"""連携評価policyの比較CLI入力とconditions契約を確認する。"""

import hashlib
import json
import unittest
from pathlib import Path

from kaname_shogi import comparison_io
from kaname_shogi.comparison import make_schedule
from kaname_shogi.movegen import MoveSelectionPolicy


class UndefendedPieceComparisonIOTests(unittest.TestCase):
    """連携評価policyを比較入力と保存条件へ接続する。"""

    @staticmethod
    def _config(root, *, baseline, candidate, pairs=1, seed_list=True, workers=4):
        """小さな局面・seed一覧で比較CLIの条件を作る。"""
        positions_path = root / "positions.json"
        positions_raw = json.dumps(
            {
                "format": "kaname-shogi-comparison-positions-v1",
                "id": "undefended-policy-test",
                "positions": [
                    {"id": "initial", "setup_moves": [], "rationale": "テスト局面"}
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        positions_path.write_bytes(positions_raw)

        position_ids = ["initial"]
        seed_pairs = [
            {
                "position_id": "initial",
                "repetition_index": index,
                "baseline_seed": 11 + 2 * index,
                "candidate_seed": 12 + 2 * index,
            }
            for index in range(pairs)
        ]
        seed_path = root / "seeds.json"
        seed_path.write_text(
            json.dumps(
                {
                    "format": "kaname-shogi-comparison-seeds-v1",
                    "purpose": "pilot",
                    "positions_sha256": hashlib.sha256(positions_raw).hexdigest(),
                    "position_ids": position_ids,
                    "pairs_per_position": pairs,
                    "source": "os",
                    "bits": 128,
                    "pairs": seed_pairs,
                }
            ),
            encoding="utf-8",
        )
        output_path = root / "results"
        args = [
            "--baseline",
            baseline,
            "--candidate",
            candidate,
            "--positions",
            str(positions_path),
            "--pairs-per-position",
            str(pairs),
        ]
        if seed_list:
            args.extend(("--seed-list", str(seed_path)))
        else:
            args.extend(("--seed", "17"))
        args.extend(
            (
                "--max-plies",
                "1",
                "--workers",
                str(workers),
                "--output-dir",
                str(output_path),
            )
        )
        try:
            config = comparison_io.load_config(args)
        except ValueError as error:
            raise AssertionError(f"比較CLIが方式を受理できません: {error}") from error
        return config, seed_path

    def test_comparison_cli_accepts_both_undefended_piece_policies(self):
        """比較CLIがU重み0と1の方式名を対応するpolicyへ変換する。

        parserの選択肢や方式表から新方式が漏れ、比較条件として指定できない誤りを
        検出する。
        """
        with self.subTest(policy="material-only"):
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as directory:
                config, _ = self._config(
                    Path(directory),
                    baseline="material-undefended-piece-material-only",
                    candidate="material-undefended-piece",
                )
                self.assertIs(
                    config.baseline,
                    MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE_MATERIAL_ONLY,
                )
                self.assertIs(
                    config.candidate,
                    MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE,
                )

    def test_conditions_save_weights_with_seed_list_and_four_workers(self):
        """conditions v3が方式・実効重み・seed一覧・worker数を一体保存する。

        CLI表示名、Uの0/1割当、乱数条件、実行workerのいずれかが取り違えられ、
        保存後に比較条件を再現できなくなる誤りを検出する。
        """
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            config, seed_path = self._config(
                root,
                baseline="material-undefended-piece-material-only",
                candidate="material-undefended-piece",
            )
            payload = comparison_io.conditions_payload(
                config, make_schedule(config), source_root=Path(__file__).parents[1]
            )

            self.assertEqual(payload["format"], "kaname-shogi-comparison-conditions-v3")
            self.assertEqual(
                (payload["baseline"], payload["candidate"]),
                (
                    "material-undefended-piece-material-only",
                    "material-undefended-piece",
                ),
            )
            self.assertEqual(
                payload["policy_parameters"],
                {
                    "baseline": {
                        "material": 10,
                        "undefended": 0,
                        "mate_priority": True,
                    },
                    "candidate": {
                        "material": 10,
                        "undefended": 1,
                        "mate_priority": True,
                    },
                },
            )
            self.assertEqual(
                payload["execution"], {"executor": "process-pool", "workers": 4}
            )
            self.assertEqual(payload["randomization"]["purpose"], "pilot")
            self.assertEqual(
                payload["randomization"]["seed_list_sha256"],
                hashlib.sha256(seed_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                payload["randomization"]["seed_list_json"],
                seed_path.read_text(encoding="utf-8"),
            )

    def test_sequential_conditions_save_weights_for_undefended_policy(self):
        """逐次seed条件もU方式の実効重みを保存する。

        主乱数seedを使う条件だけUの重みを欠落させ、実験方式を後から識別できなくなる
        誤りを検出する。
        """
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            config, _ = self._config(
                root,
                baseline="material",
                candidate="material-undefended-piece",
                seed_list=False,
                workers=1,
            )
            payload = comparison_io.conditions_payload(
                config, make_schedule(config), source_root=Path(__file__).parents[1]
            )

            self.assertEqual(payload["format"], "kaname-shogi-comparison-conditions-v1")
            self.assertEqual(
                payload.get("policy_parameters"),
                {
                    "baseline": {},
                    "candidate": {
                        "material": 10,
                        "undefended": 1,
                        "mate_priority": True,
                    },
                },
            )

    def test_conditions_save_parameters_when_only_one_side_uses_undefended_policy(self):
        """片側だけがU方式でも、その側の実効重みをconditionsに残す。

        一方の方式だけに連携評価を適用した比較で、通常方式の空条件を新方式の重みと
        混同する、またはU重みを記録しない誤りを検出する。
        """
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            config, _ = self._config(
                root,
                baseline="material",
                candidate="material-undefended-piece",
            )
            payload = comparison_io.conditions_payload(
                config, make_schedule(config), source_root=Path(__file__).parents[1]
            )

            self.assertEqual(
                payload["policy_parameters"],
                {
                    "baseline": {},
                    "candidate": {
                        "material": 10,
                        "undefended": 1,
                        "mate_priority": True,
                    },
                },
            )


if __name__ == "__main__":
    unittest.main()
