"""既存三方式と新しい四手探索を対局用入口へ接続する契約を確認する。"""

import random
import unittest
from unittest.mock import patch

from kaname_shogi import game_search
from kaname_shogi import movegen as mg
from kaname_shogi.material_rook_mobility import evaluate_material_rook_mobility
from kaname_shogi.model import (
    BasicPieceType,
    Board,
    Piece,
    PieceType,
    Position,
    Side,
    Square,
)
from kaname_shogi.move import BoardMove
from kaname_shogi.search.result import (
    ControlledCompletion,
    ControlledSearchResult,
    IterationResult,
    SearchResult,
)
from kaname_shogi.search_control import SearchControl
from kaname_shogi.sfen import parse_sfen


def kings_only(side: Side) -> Position:
    """両玉だけの局面で、指定側を手番として返す。"""
    turn = "b" if side is Side.SENTE else "w"
    return parse_sfen(f"8k/9/9/9/9/9/9/9/K8 {turn} - 1").position


def snapshot(position: Position):
    """盤面・手番・持ち駒を読み取り専用の組にする。"""
    return (
        tuple(
            position.board.piece_at(Square(file, rank))
            for file in range(1, 10)
            for rank in range(1, 10)
        ),
        tuple(
            hand.count(piece_type)
            for hand in (position.sente_hand, position.gote_hand)
            for piece_type in BasicPieceType
            if piece_type is not BasicPieceType.KING
        ),
        position.side_to_move,
    )


class RecordingChoice:
    """抽選候補と呼出回数を記録し、候補先頭を返すテスト用操作。"""

    def __init__(self):
        self.calls = 0
        self.seen = ()

    def choice(self, candidates):
        self.calls += 1
        self.seen = tuple(candidates)
        return candidates[0]


class GameSearchTests(unittest.TestCase):
    def new_policy(self, name):
        """新方針が存在することを確認してから、その値を返す。"""
        policy = getattr(mg.MoveSelectionPolicy, name, None)
        self.assertIsNotNone(policy, f"{name}方針を追加してください")
        return policy

    def _choose_b1(self, position, moves, rng):
        """未接続方針のValueErrorを期待する失敗テストへ変換して呼ぶ。"""
        policy = self.new_policy("MATERIAL_ROOK_MOBILITY")
        try:
            return game_search.choose_move(position, moves, policy, rng)
        except ValueError as error:
            self.fail(f"有効なB1選択を拒否しました: {error}")

    @staticmethod
    def _mate_capture_case(side):
        """即詰み手と、より大きな駒得を得る非詰み手を返す。"""
        board = Board()
        for square, piece_type, owner in (
            (Square(9, 9), PieceType.KING, Side.SENTE),
            (Square(5, 3), PieceType.ROOK, Side.SENTE),
            (Square(4, 3), PieceType.GOLD, Side.SENTE),
            (Square(5, 1), PieceType.KING, Side.GOTE),
            (Square(4, 1), PieceType.PAWN, Side.GOTE),
            (Square(6, 1), PieceType.PAWN, Side.GOTE),
            (Square(4, 2), PieceType.PAWN, Side.GOTE),
            (Square(6, 2), PieceType.PAWN, Side.GOTE),
            (Square(6, 3), PieceType.ROOK, Side.GOTE),
        ):
            board.set_piece(square, Piece(piece_type, owner))
        position = Position(board, Side.SENTE)
        if side is Side.SENTE:
            return (
                position,
                BoardMove(Square(5, 3), Square(5, 2), False),
                BoardMove(Square(5, 3), Square(6, 3), False),
            )

        rotated = Board()
        for file in range(1, 10):
            for rank in range(1, 10):
                piece = board.piece_at(Square(file, rank))
                if piece is not None:
                    owner = Side.GOTE if piece.side is Side.SENTE else Side.SENTE
                    rotated.set_piece(
                        Square(10 - file, 10 - rank), Piece(piece.piece_type, owner)
                    )
        return (
            Position(rotated, Side.GOTE),
            BoardMove(Square(5, 7), Square(5, 8), False),
            BoardMove(Square(5, 7), Square(4, 7), False),
        )

    def test_b1_dispatch_preserves_full_best_set(self):
        """B1は手計算した最大7手だけを一度抽選し、元局面を保つ。

        駒得だけへの誤配線、最高候補の欠落・余計な混入、抽選の複数回実行、
        候補評価による元局面の変更を検出する。最大176点は駒得16×10と
        可動性16×1、期待する7手は飛車が玉に遮られず横8方向を確保する配置から
        独立に定めている。
        """
        position = parse_sfen("8k/9/9/9/9/9/4P4/4R4/K8 b - 1").position
        before = snapshot(position)
        moves = mg.legal_moves(position)

        class RecordingChoice:
            """抽選候補と呼出回数を記録し、候補内の一手を返す。"""

            def __init__(self):
                self.calls = 0
                self.seen = ()

            def choice(self, candidates):
                self.calls += 1
                self.seen = tuple(candidates)
                return candidates[0]

        expected_moves = {
            BoardMove(Square(5, 8), Square(1, 8), False),
            BoardMove(Square(5, 8), Square(2, 8), False),
            BoardMove(Square(5, 8), Square(3, 8), False),
            BoardMove(Square(5, 8), Square(4, 8), False),
            BoardMove(Square(5, 8), Square(6, 8), False),
            BoardMove(Square(5, 8), Square(7, 8), False),
            BoardMove(Square(5, 8), Square(8, 8), False),
        }
        rng = RecordingChoice()

        selected = self._choose_b1(position, moves, rng)

        self.assertEqual(set(rng.seen), expected_moves)
        self.assertEqual(rng.calls, 1)
        self.assertIn(selected, expected_moves)
        self.assertEqual(snapshot(position), before)

    def test_b1_empty_candidates_return_none_without_randomness(self):
        """B1の候補なしを通常手なしとして返し、乱数を使わない。

        B1を四手探索側へ誤分類して例外にすることや、空候補で抽選する誤りを検出する。
        """
        policy = self.new_policy("MATERIAL_ROOK_MOBILITY")
        position = kings_only(Side.SENTE)

        class RecordingChoice:
            """抽選が発生したかだけを記録する。"""

            def __init__(self):
                self.calls = 0

            def choice(self, candidates):
                self.calls += 1
                return candidates[0]

        rng = RecordingChoice()

        try:
            selected = game_search.choose_move(position, (), policy, rng)
        except ValueError as error:
            self.fail(f"空候補を返さずB1を拒否しました: {error}")

        self.assertIsNone(selected)
        self.assertEqual(rng.calls, 0)

    def test_b1_dispatch_preserves_full_best_set_for_gote(self):
        """後手でも独立に手計算した最高7手だけを一度抽選する。

        先手視点固定を検出する。後手飛車５二から横へ動き、自玉１一に遮られず
        16マスを保つ7手を期待値として固定する。
        """
        position = parse_sfen("8k/4r4/4p4/9/9/9/9/9/K8 w - 1").position
        moves = mg.legal_moves(position)
        expected_moves = {
            BoardMove(Square(5, 2), Square(2, 2), False),
            BoardMove(Square(5, 2), Square(3, 2), False),
            BoardMove(Square(5, 2), Square(4, 2), False),
            BoardMove(Square(5, 2), Square(6, 2), False),
            BoardMove(Square(5, 2), Square(7, 2), False),
            BoardMove(Square(5, 2), Square(8, 2), False),
            BoardMove(Square(5, 2), Square(9, 2), False),
        }
        rng = RecordingChoice()

        selected = self._choose_b1(position, moves, rng)

        self.assertEqual(set(rng.seen), expected_moves)
        self.assertEqual(rng.calls, 1)
        self.assertIn(selected, expected_moves)

    def test_b1_prefers_one_point_pawn_advance_for_both_sides(self):
        """駒得同値なら飛車の移動先が1増える歩の前進を先後とも選ぶ。

        一手駒得だけへの誤配線、先手視点の固定、候補順による選択を検出する。
        固定SFENで、先手の歩５七→５六は170対169、後手の歩５三→５四も
        170対169と手計算した期待値に照合する。
        """
        cases = (
            (
                Side.SENTE,
                "8k/9/9/9/9/9/4P4/4R4/K8 b - 1",
                BoardMove(Square(5, 7), Square(5, 6), False),
                BoardMove(Square(9, 9), Square(8, 9), False),
            ),
            (
                Side.GOTE,
                "8k/4r4/4p4/9/9/9/9/9/K8 w - 1",
                BoardMove(Square(5, 3), Square(5, 4), False),
                BoardMove(Square(1, 1), Square(2, 1), False),
            ),
        )
        for side, sfen, pawn_move, king_move in cases:
            with self.subTest(side=side):
                position = parse_sfen(sfen).position
                self.assertIn(pawn_move, mg.legal_moves(position))
                self.assertIn(king_move, mg.legal_moves(position))
                self.assertEqual(
                    evaluate_material_rook_mobility(
                        mg.position_after_move(position, pawn_move), side
                    ),
                    170,
                )
                self.assertEqual(
                    evaluate_material_rook_mobility(
                        mg.position_after_move(position, king_move), side
                    ),
                    169,
                )
                rng = RecordingChoice()

                selected = self._choose_b1(position, (king_move, pawn_move), rng)

                self.assertEqual(rng.seen, (pawn_move,))
                self.assertEqual(rng.calls, 1)
                self.assertEqual(selected, pawn_move)

    def test_b1_retains_weak_rook_safety_example(self):
        """26手局面では危険な２三不成を安全候補より2点高く採点する。

        B1接続で駒得・可動性の符号が変わる誤りを検出する。比較は二候補だけで、
        全合法手からこの手を必ず選ぶことや安全性評価の実装を主張しない。
        """
        position = parse_sfen(
            "ln1g2snl/5kgb1/p2p1p2p/2psp1pR1/9/1rP1PSP2/"
            "P2P1P2P/1BGK5/LNS2G1NL b 2P2p 27"
        ).position
        risky = BoardMove(Square(2, 4), Square(2, 3), False)
        safer = BoardMove(Square(2, 4), Square(2, 6), False)
        self.assertIn(risky, mg.legal_moves(position))
        self.assertIn(safer, mg.legal_moves(position))
        self.assertEqual(
            evaluate_material_rook_mobility(
                mg.position_after_move(position, risky), Side.SENTE
            ),
            1,
        )
        self.assertEqual(
            evaluate_material_rook_mobility(
                mg.position_after_move(position, safer), Side.SENTE
            ),
            -1,
        )
        rng = RecordingChoice()

        selected = self._choose_b1(position, (safer, risky), rng)

        self.assertEqual(rng.seen, (risky,))
        self.assertEqual(rng.calls, 1)
        self.assertEqual(selected, risky)

    def test_b1_prioritizes_mate_over_higher_material_capture_for_both_sides(self):
        """B1は駒得361点の非詰み手より49点の即詰み手を先後とも優先する。

        通常点だけで詰み手を落とす誤り、先手固定、巨大な通常点が勝敗優先を
        上回る誤りを検出する。詰み判定と通常評価は実処理を使う。
        """
        for side in Side:
            with self.subTest(side=side):
                position, mate, capture = self._mate_capture_case(side)
                self.assertIn(mate, mg.legal_moves(position))
                self.assertIn(capture, mg.legal_moves(position))
                self.assertTrue(mg.is_checkmate(mg.position_after_move(position, mate)))
                self.assertFalse(
                    mg.is_checkmate(mg.position_after_move(position, capture))
                )
                mate_score = evaluate_material_rook_mobility(
                    mg.position_after_move(position, mate), side
                )
                capture_score = evaluate_material_rook_mobility(
                    mg.position_after_move(position, capture), side
                )
                self.assertEqual((mate_score, capture_score), (49, 361))
                rng = RecordingChoice()

                selected = self._choose_b1(position, (capture, mate), rng)

                self.assertEqual(rng.seen, (mate,))
                self.assertEqual(rng.calls, 1)
                self.assertEqual(selected, mate)

    def test_legacy_policies_delegate_unchanged(self):
        """旧三方式は同じ引数を一度だけ旧入口へ渡し結果をそのまま返す。

        ラッパー内の再選択、引数の複製、旧探索挙動の書換えを検出する。
        """
        adapter = game_search
        position = Position(Board(), Side.SENTE)
        move = BoardMove(Square(2, 7), Square(2, 6), False)
        moves = (move,)
        rng = object()
        control = object()
        for policy in (
            mg.MoveSelectionPolicy.RANDOM,
            mg.MoveSelectionPolicy.MATERIAL,
            mg.MoveSelectionPolicy.TWO_PLY_MATERIAL,
        ):
            with self.subTest(policy=policy):
                chosen = object()
                with patch.object(mg, "choose_move", return_value=chosen) as legacy:
                    result = adapter.choose_move(position, moves, policy, rng)
                self.assertIs(result, chosen)
                legacy.assert_called_once_with(position, moves, policy, rng)

                searched = object()
                with patch.object(mg, "search_move", return_value=searched) as legacy:
                    result = adapter.search_move(position, policy, rng, control)
                self.assertIs(result, searched)
                legacy.assert_called_once_with(position, policy, rng, control)

        for name in ("FOUR_PLY_FULL_WIDTH", "FOUR_PLY_ALPHA_BETA"):
            policy = self.new_policy(name)
            with self.subTest(rejected_policy=name):
                with patch.object(mg, "_legal_moves_controlled") as generate:
                    with self.assertRaises(ValueError):
                        mg.search_move(
                            position,
                            policy,
                            rng,
                            SearchControl(None, 0, now_ns=lambda: 0),
                        )
                generate.assert_not_called()

    def test_undefended_piece_uses_controlled_selection_path(self):
        """Uは時計付き探索の既存候補選択へ同じ引数で委譲する。

        未知の四手方式へ誤分類したり、停止制御を捨てて別入口へ送る誤りを検出する。
        """
        policy = mg.MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE
        position = kings_only(Side.SENTE)
        rng = object()
        control = object()
        move = mg.legal_moves(position)[0]
        expected = mg.SearchResult(
            mg.SearchCompletion.COMPLETE,
            move,
        )

        with patch.object(mg, "search_move", return_value=expected) as controlled:
            try:
                result = game_search.search_move(position, policy, rng, control)
            except ValueError as error:
                self.fail(f"U方針が制御付き候補選択へ接続されていません: {error}")

        self.assertIs(result, expected)
        controlled.assert_called_once_with(position, policy, rng, control)

    def test_new_modes_use_depth_four_and_starting_side(self):
        """新二方式は開始側視点で深さ4へ接続し、同じ制御と乱数なしを守る。

        先後視点の固定誤り、方式の取り違え、深さ違い、制御の再生成、乱数使用を検出する。
        """
        adapter = game_search
        expected = {
            "FOUR_PLY_FULL_WIDTH": False,
            "FOUR_PLY_ALPHA_BETA": True,
        }
        move = BoardMove(Square(2, 7), Square(2, 6), False)
        for side in Side:
            position = kings_only(side)
            for name, pruning in expected.items():
                policy = self.new_policy(name)
                with self.subTest(side=side, policy=name):
                    operations = object()
                    record = IterationResult(4, SearchResult((0, 0), move, 1, None), 10)
                    rng = object()
                    with (
                        patch.object(
                            adapter.shogi,
                            "make_operations",
                            return_value=operations,
                        ) as make_operations,
                        patch.object(
                            adapter.iterative_deepening,
                            "search",
                            return_value=iter((record,)),
                        ) as iterative_search,
                    ):
                        selected = adapter.choose_move(position, (move,), policy, rng)
                    self.assertIs(selected, move)
                    make_operations.assert_called_once_with(side)
                    iterative_search.assert_called_once_with(
                        position, 4, operations, pruning=pruning
                    )

                    control = object()
                    controlled_operations = object()
                    controlled_result = ControlledSearchResult(
                        ControlledCompletion.COMPLETE, move, record
                    )
                    with (
                        patch.object(
                            adapter.shogi,
                            "make_controlled_operations",
                            return_value=controlled_operations,
                        ) as make_controlled_operations,
                        patch.object(
                            adapter.iterative_deepening,
                            "search_controlled",
                            return_value=controlled_result,
                        ) as controlled_search,
                    ):
                        response = adapter.search_move(position, policy, rng, control)
                    self.assertEqual(
                        response, mg.SearchResult(mg.SearchCompletion.COMPLETE, move)
                    )
                    make_controlled_operations.assert_called_once_with(side)
                    controlled_search.assert_called_once_with(
                        position, 4, controlled_operations, control, pruning=pruning
                    )

    def test_controlled_outcomes_preserve_selected_move(self):
        """制御結果を既存応答型へ写し、抑制記録から手を復活させない。

        停止予備手・停止済み最善手・手なし・抑制を投了や再選択に変える誤りを検出する。
        """
        adapter = game_search
        selected = BoardMove(Square(2, 7), Square(2, 6), False)
        record = IterationResult(2, SearchResult((0, 3), selected, 7, None), 10)
        scenarios = (
            (
                ControlledSearchResult(ControlledCompletion.COMPLETE, selected, record),
                mg.SearchResult(mg.SearchCompletion.COMPLETE, selected),
            ),
            (
                ControlledSearchResult(ControlledCompletion.NO_LEGAL_MOVE, None, None),
                mg.SearchResult(mg.SearchCompletion.COMPLETE, None),
            ),
            (
                ControlledSearchResult(ControlledCompletion.STOPPED, selected, None),
                mg.SearchResult(mg.SearchCompletion.INTERRUPTED, selected),
            ),
            (
                ControlledSearchResult(ControlledCompletion.STOPPED, selected, record),
                mg.SearchResult(mg.SearchCompletion.INTERRUPTED, selected),
            ),
            (
                ControlledSearchResult(ControlledCompletion.SUPPRESSED, None, record),
                mg.SearchResult(mg.SearchCompletion.SUPPRESSED, None),
            ),
        )
        for name in ("FOUR_PLY_FULL_WIDTH", "FOUR_PLY_ALPHA_BETA"):
            policy = self.new_policy(name)
            pruning = name == "FOUR_PLY_ALPHA_BETA"
            for controlled_result, expected in scenarios:
                with self.subTest(policy=name, completion=controlled_result.completion):
                    position = kings_only(Side.SENTE)
                    rng = object()
                    control = object()
                    operations = object()
                    with (
                        patch.object(
                            adapter.shogi,
                            "make_controlled_operations",
                            return_value=operations,
                        ),
                        patch.object(
                            adapter.iterative_deepening,
                            "search_controlled",
                            return_value=controlled_result,
                        ) as search,
                    ):
                        response = adapter.search_move(position, policy, rng, control)
                    self.assertEqual(response, expected)
                    search.assert_called_once_with(
                        position, 4, operations, control, pruning=pruning
                    )

        policy = self.new_policy("FOUR_PLY_FULL_WIDTH")
        failure = RuntimeError("search operation failed")
        with patch.object(
            adapter.iterative_deepening,
            "search_controlled",
            side_effect=failure,
        ):
            with self.assertRaises(RuntimeError) as caught:
                adapter.search_move(
                    kings_only(Side.SENTE),
                    policy,
                    object(),
                    SearchControl(None, 0, now_ns=lambda: 0),
                )
        self.assertIs(caught.exception, failure)

    def test_unknown_policy_fails_before_search(self):
        """未知値やNoneは探索操作を作る前に両対局入口で拒否する。

        不明値の旧方式誤受入れ、探索・合法手生成の開始、例外の後送りを検出する。
        """
        adapter = game_search
        position = kings_only(Side.SENTE)
        moves = (BoardMove(Square(2, 7), Square(2, 6), False),)
        for invalid in (object(), None):
            with self.subTest(policy=invalid):
                with (
                    patch.object(mg, "choose_move") as legacy_choose,
                    patch.object(mg, "search_move") as legacy_search,
                    patch.object(adapter.shogi, "make_operations") as make_operations,
                    patch.object(
                        adapter.shogi, "make_controlled_operations"
                    ) as make_controlled_operations,
                    patch.object(adapter.iterative_deepening, "search") as search,
                    patch.object(
                        adapter.iterative_deepening, "search_controlled"
                    ) as search_controlled,
                ):
                    with self.assertRaises(ValueError):
                        adapter.choose_move(position, moves, invalid, object())
                    with self.assertRaises(ValueError):
                        adapter.search_move(
                            position,
                            invalid,
                            object(),
                            SearchControl(None, 0, now_ns=lambda: 0),
                        )
                legacy_choose.assert_not_called()
                legacy_search.assert_not_called()
                make_operations.assert_not_called()
                make_controlled_operations.assert_not_called()
                search.assert_not_called()
                search_controlled.assert_not_called()

    def test_new_modes_connect_to_real_sente_and_gote_search(self):
        """玉だけの先後局面を両方式で通常・制御探索し、元局面を保つ。

        視点固定、手の不在や不合法、制御経路の切断、試し指しの元局面漏れを検出する。
        """
        adapter = game_search
        for side in Side:
            for name in ("FOUR_PLY_FULL_WIDTH", "FOUR_PLY_ALPHA_BETA"):
                policy = self.new_policy(name)
                with self.subTest(side=side, policy=name):
                    position = kings_only(side)
                    before = snapshot(position)
                    legal = mg.legal_moves(position)
                    self.assertTrue(legal)
                    selected = adapter.choose_move(
                        position, legal, policy, random.Random(0)
                    )
                    self.assertIn(selected, legal)
                    self.assertEqual(snapshot(position), before)

                    response = adapter.search_move(
                        position,
                        policy,
                        random.Random(0),
                        SearchControl(None, 0, now_ns=lambda: 0),
                    )
                    self.assertEqual(response.completion, mg.SearchCompletion.COMPLETE)
                    self.assertEqual(response.move, selected)
                    self.assertEqual(snapshot(position), before)
