"""比較用の乱数種一覧の生成・検証契約を確認する。"""

import importlib
import json
import unittest

try:
    comparison_seeds_module = importlib.import_module("kaname_shogi.comparison_seeds")
except ModuleNotFoundError as error:
    if error.name != "kaname_shogi.comparison_seeds":
        raise
    comparison_seeds_module = None

SeedPlan = getattr(comparison_seeds_module, "SeedPlan", None)
generate_seed_plan = getattr(comparison_seeds_module, "generate_seed_plan", None)
parse_seed_plan = getattr(comparison_seeds_module, "parse_seed_plan", None)
seed_plan_payload = getattr(comparison_seeds_module, "seed_plan_payload", None)
validate_seed_plan = getattr(comparison_seeds_module, "validate_seed_plan", None)


class ComparisonSeedPlanTests(unittest.TestCase):
    def _require_implementation(self):
        """API不足をimport失敗でなく機能不足として示す。"""
        self.assertIsNotNone(SeedPlan, "乱数種一覧データが未実装です")
        self.assertIsNotNone(generate_seed_plan, "乱数種一覧生成が未実装です")

    def test_generates_four_pairs_from_eight_fixed_draws(self):
        """2局面各2組を8回の固定128ビット抽選から順序どおり生成する。

        抽選回数・ビット幅、局面順、反復番号、基準/候補種の割当てを、製品関数と
        独立した固定期待値で比較し、抽選の再利用や方式別種の取り違えを検出する。
        """
        self._require_implementation()
        draws = iter(range(11, 19))
        bit_requests = []

        def fixed_randbits(bits):
            bit_requests.append(bits)
            return next(draws)

        plan = generate_seed_plan(
            ("a", "b"),
            "a" * 64,
            2,
            "pilot",
            randbits=fixed_randbits,
        )

        rows = [
            (
                pair.position_id,
                pair.repetition_index,
                pair.baseline_seed,
                pair.candidate_seed,
            )
            for pair in plan.pairs
        ]
        self.assertEqual(
            rows,
            [
                ("a", 0, 11, 12),
                ("a", 1, 13, 14),
                ("b", 0, 15, 16),
                ("b", 1, 17, 18),
            ],
        )
        self.assertEqual(bit_requests, [128] * 8)
        self.assertEqual(plan.position_ids, ("a", "b"))
        self.assertEqual(plan.pairs_per_position, 2)
        self.assertEqual(plan.purpose, "pilot")
        self.assertEqual(plan.positions_sha256, "a" * 64)

    def test_generated_plan_keeps_repeated_seed_values_and_both_boundaries(self):
        """偶然の重複種を残し、0と128ビット最大値を有効値として扱う。

        独立抽選値を一意化する、または整数境界を1つずらして受理・拒否する誤りを
        固定乱数列で検出する。
        """
        self._require_implementation()
        draws = iter((0, 0, 0, (1 << 128) - 1))

        plan = generate_seed_plan(
            ("a",),
            "b" * 64,
            2,
            "confirmation",
            randbits=lambda bits: next(draws),
        )

        self.assertEqual(
            [
                (
                    pair.position_id,
                    pair.repetition_index,
                    pair.baseline_seed,
                    pair.candidate_seed,
                )
                for pair in plan.pairs
            ],
            [("a", 0, 0, 0), ("a", 1, 0, (1 << 128) - 1)],
        )

    def test_generated_plan_rejects_invalid_draws_before_returning(self):
        """bool・負数・2**128を種として返す乱数源を拒否する。

        Pythonでboolがintの派生型であることや、上限を含めてしまう誤りを検出する。
        """
        self._require_implementation()
        for invalid_seed in (True, -1, 1 << 128):
            with self.subTest(seed=invalid_seed):
                with self.assertRaises(ValueError):
                    generate_seed_plan(
                        ("a",),
                        "c" * 64,
                        1,
                        "pilot",
                        randbits=lambda bits, seed=invalid_seed: seed,
                    )

    def test_seed_plan_payload_has_exact_keys_and_round_trips(self):
        """一覧を規定キー・順序のJSON値へ変換し、読込後も同値にする。

        source/bitsや方式名を誤記する、局面順・組順を失う、読み書きで値を変える誤りを
        独立した固定辞書との照合で検出する。
        """
        self.assertIsNotNone(seed_plan_payload, "乱数種一覧のJSON変換が未実装です")
        self.assertIsNotNone(parse_seed_plan, "乱数種一覧のJSON読込が未実装です")
        self._require_implementation()
        draws = iter((11, 12, 13, 14))
        plan = generate_seed_plan(
            ("a", "b"),
            "d" * 64,
            1,
            "pilot",
            randbits=lambda bits: next(draws),
        )

        payload = seed_plan_payload(plan)

        self.assertEqual(
            payload,
            {
                "format": "kaname-shogi-comparison-seeds-v1",
                "purpose": "pilot",
                "positions_sha256": "d" * 64,
                "position_ids": ["a", "b"],
                "pairs_per_position": 1,
                "source": "os",
                "bits": 128,
                "pairs": [
                    {
                        "position_id": "a",
                        "repetition_index": 0,
                        "baseline_seed": 11,
                        "candidate_seed": 12,
                    },
                    {
                        "position_id": "b",
                        "repetition_index": 0,
                        "baseline_seed": 13,
                        "candidate_seed": 14,
                    },
                ],
            },
        )
        self.assertEqual(parse_seed_plan(json.dumps(payload).encode("utf-8")), plan)

    def test_seed_plan_validation_matches_position_snapshot_and_pair_count(self):
        """予定照合で局面内容・ID順・局面ごとの組数の違いを拒否する。

        IDだけの一致や組数の部分一致で別実験の一覧を使う誤りを検出する。
        """
        self.assertIsNotNone(validate_seed_plan, "乱数種一覧の照合が未実装です")
        self._require_implementation()
        plan = generate_seed_plan(
            ("a", "b"), "e" * 64, 1, "confirmation", randbits=lambda bits: 1
        )
        validate_seed_plan(
            plan,
            position_ids=("a", "b"),
            positions_sha256="e" * 64,
            pairs_per_position=1,
        )
        invalid_expectations = (
            (("a", "b"), "f" * 64, 1),
            (("b", "a"), "e" * 64, 1),
            (("a", "b"), "e" * 64, 2),
        )
        for position_ids, digest, pair_count in invalid_expectations:
            with self.subTest(position_ids=position_ids, pairs=pair_count):
                with self.assertRaises(ValueError):
                    validate_seed_plan(
                        plan,
                        position_ids=position_ids,
                        positions_sha256=digest,
                        pairs_per_position=pair_count,
                    )

    def test_seed_parser_rejects_incorrect_shape_order_and_seed_values(self):
        """欠落・未知キー、重複組、順序違い、非整数種を一覧として拒否する。

        JSON標準読込後の曖昧値や順序を黙って正規化し、予定と異なる乱数列を使う誤りを
        独立した不正一覧の変異で検出する。
        """
        self.assertIsNotNone(parse_seed_plan, "乱数種一覧のJSON読込が未実装です")
        self._require_implementation()
        valid = {
            "format": "kaname-shogi-comparison-seeds-v1",
            "purpose": "pilot",
            "positions_sha256": "f" * 64,
            "position_ids": ["a", "b"],
            "pairs_per_position": 1,
            "source": "os",
            "bits": 128,
            "pairs": [
                {
                    "position_id": "a",
                    "repetition_index": 0,
                    "baseline_seed": 0,
                    "candidate_seed": (1 << 128) - 1,
                },
                {
                    "position_id": "b",
                    "repetition_index": 0,
                    "baseline_seed": 8,
                    "candidate_seed": 9,
                },
            ],
        }
        invalid_values = []
        for field, value in (("source", "python"), ("bits", 64)):
            changed = {**valid, field: value}
            invalid_values.append(changed)
        invalid_values.extend(
            (
                {key: value for key, value in valid.items() if key != "purpose"},
                {**valid, "unknown": True},
                {**valid, "pairs": list(reversed(valid["pairs"]))},
                {**valid, "pairs": [valid["pairs"][0], valid["pairs"][0]]},
                {
                    **valid,
                    "pairs": [
                        {**valid["pairs"][0], "baseline_seed": True},
                        valid["pairs"][1],
                    ],
                },
                {
                    **valid,
                    "pairs": [
                        {**valid["pairs"][0], "candidate_seed": 1 << 128},
                        valid["pairs"][1],
                    ],
                },
            )
        )
        for index, payload in enumerate(invalid_values):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    parse_seed_plan(json.dumps(payload).encode("utf-8"))
