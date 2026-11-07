"""将棋局面に対する静止探索の契約を確認する。"""

import unittest
from dataclasses import replace
from importlib import import_module
from inspect import signature

from kaname_shogi.model import Board, Piece, Position, Side, Square
from kaname_shogi.move import BoardMove
from kaname_shogi.movegen import is_in_check
from kaname_shogi.search import alpha_beta, minimax, quiescence, shogi
from kaname_shogi.search.result import QuiescenceLimit, SearchInterrupted
from kaname_shogi.search_control import SearchControl, SearchSignal
from kaname_shogi.sfen import format_sfen, parse_sfen
from kaname_shogi.time_management import SearchBudget
from kaname_shogi.usi_move import parse_usi_move

KINGS = "8k/9/9/9/9/9/9/9/K8 b - 1"
RECAPTURE = "8k/9/4g4/4p4/4RS3/9/9/9/K8 b - 1"
LOSING_RECAPTURE = "8k/9/9/9/4g4/4P4/9/9/4R3K w - 1"
OTHER_SQUARE_CAPTURES = "k8/9/9/9/2g1p4/9/9/9/2R1R3K b - 1"
CAPTURING_PROMOTION = "8k/9/4s4/4P4/9/9/9/9/8K b - 1"
QUIET_PROMOTION = "8k/9/9/4P4/9/9/9/9/8K b - 1"
KING_ESCAPE_CHECK = "4k4/9/9/9/4R4/9/9/9/K8 w - 1"
DROP_INTERPOSITION_CHECK = "4k4/9/2NP1PN2/9/4R4/9/9/9/K8 w g 1"
CAPTURE_CHECKER_ONLY = "9/9/9/3g5/4R4/3Sk4/3P1P3/3G1G3/8K w - 1"
MIXED_CHECK_EVASIONS = "9/9/9/3g5/4R4/4k4/9/9/8K w - 1"
MATE = "3pkp3/3p1p3/4RG3/9/9/9/9/9/K8 b - 1"


class QuiescenceSearchTests(unittest.TestCase):
    def quiescence_operations(self, perspective, additional_depth):
        """承認済みの将棋用末端操作を返し、未実装時は契約失敗として知らせる。"""
        factory = getattr(shogi, "make_quiescence_operations", None)
        self.assertTrue(callable(factory), "将棋用静止探索の操作セットが必要です")
        if factory is None:
            return None
        return factory(perspective, additional_depth)

    @staticmethod
    def control():
        """時間停止を発生させない決定的な探索制御を作る。"""
        return SearchControl(None, 0, now_ns=lambda: 0)

    @staticmethod
    def rotate_and_swap_sides(position):
        """盤面を180度回して駒・手番・双方の持ち駒を入れ替える。"""
        board = Board()
        for file in range(1, 10):
            for rank in range(1, 10):
                piece = position.board.piece_at(Square(file, rank))
                if piece is None:
                    continue
                side = Side.GOTE if piece.side is Side.SENTE else Side.SENTE
                board.set_piece(
                    Square(10 - file, 10 - rank), Piece(piece.piece_type, side)
                )
        side_to_move = Side.GOTE if position.side_to_move is Side.SENTE else Side.SENTE
        return Position(
            board,
            side_to_move,
            position.gote_hand.copy(),
            position.sente_hand.copy(),
        )

    def test_factory_connects_a_leaf_search_and_zero_limit_evaluates_quiet_position(
        self,
    ):
        """王手なしの上限0は終端確認後に通常評価を返す。

        上限を即未完了にする誤りと、静止探索を末端へ接続しない誤りを検出する。
        """
        position = parse_sfen(KINGS).position
        operations = self.quiescence_operations(Side.SENTE, 0)
        if operations is None:
            return
        result = alpha_beta.search_controlled(position, 0, operations, self.control())

        self.assertIsNotNone(operations.search_leaf)
        self.assertEqual((result.score, result.move), ((0, 0), None))

    def test_factory_rejects_negative_or_boolean_additional_depth(self):
        """追加深さはboolでない0以上の整数に限る。

        負数の無制限再帰やboolを手数として受け入れる誤りを検出する。
        """
        for depth in (-1, True, 1.5):
            with self.subTest(depth=depth), self.assertRaises(ValueError):
                self.quiescence_operations(Side.SENTE, depth)

    def test_stand_pat_rejects_a_recapture_that_worsens_the_capturing_side(self):
        """再捕獲で相手に大駒を取られる局面では静的評価を選ぶ。

        stand patを選択肢から外し、合法な捕獲を常に強制する誤りを検出する。
        """
        sf = parse_sfen(LOSING_RECAPTURE)
        position = sf.position
        base = shogi.make_operations(Side.SENTE)
        recapture = parse_usi_move("5e5f")
        self.assertEqual(base.evaluate(position), (0, 7))
        self.assertIn(recapture, base.inspect(position).moves)
        after_recapture = base.advance(position, recapture)
        self.assertEqual(base.evaluate(after_recapture), (0, 5))
        self.assertIn(parse_usi_move("5i5f"), base.inspect(after_recapture).moves)
        after_exchange = base.advance(after_recapture, parse_usi_move("5i5f"))
        self.assertEqual(base.evaluate(after_exchange), (0, 23))

        operations = self.quiescence_operations(Side.SENTE, 2)
        if operations is None:
            return
        result = alpha_beta.search_controlled(position, 0, operations, self.control())

        self.assertEqual(result.score, (0, 7))
        self.assertEqual(format_sfen(sf), LOSING_RECAPTURE)

    def test_capture_search_finds_a_better_capture_on_a_different_square(self):
        """異なる到着マスの捕獲を比べ、金を取る枝の手計算値を返す。

        直前の捕獲マスだけを調べ、別マスの合法捕獲を落とす誤りを検出する。
        """
        position = parse_sfen(OTHER_SQUARE_CAPTURES).position
        base = shogi.make_operations(Side.SENTE)
        captures = tuple(
            move
            for move in base.inspect(position).moves
            if isinstance(move, BoardMove)
            and position.board.piece_at(move.destination) is not None
        )
        self.assertCountEqual(
            captures,
            (parse_usi_move("5i5e"), parse_usi_move("7i7e")),
        )
        self.assertEqual(base.evaluate(position), (0, 20))
        for token, expected in (("5i5e", (0, 22)), ("7i7e", (0, 38))):
            after = base.advance(position, parse_usi_move(token))
            self.assertEqual(base.evaluate(after), expected)
            self.assertFalse(is_in_check(after.board, after.side_to_move))

        operations = self.quiescence_operations(Side.SENTE, 1)
        if operations is None:
            return
        result = alpha_beta.search_controlled(position, 0, operations, self.control())
        full_width = minimax.search_controlled(
            position,
            0,
            self.quiescence_operations(Side.SENTE, 1),
            self.control(),
        )

        self.assertEqual((result.score, full_width.score), ((0, 38), (0, 38)))

    def test_two_ply_exchange_reduces_temporary_material_gain_for_both_views(self):
        """取り返しを二手読むと教材の一時的な15点が3点まで減る。

        追加深さを無視する誤りと、最大側・最小側の反転を誤る実装を検出する。
        """
        sf = parse_sfen(RECAPTURE)
        base = shogi.make_operations(Side.SENTE)
        first_capture = base.advance(sf.position, parse_usi_move("5e5d"))
        self.assertEqual(base.evaluate(first_capture), (0, 15))
        recapture = parse_usi_move("5c5d")
        self.assertIn(recapture, base.inspect(first_capture).moves)
        after_recapture = base.advance(first_capture, recapture)
        self.assertEqual(base.evaluate(after_recapture), (0, -15))
        final_capture = parse_usi_move("4e5d")
        self.assertIn(final_capture, base.inspect(after_recapture).moves)
        self.assertEqual(
            base.evaluate(base.advance(after_recapture, final_capture)), (0, 3)
        )

        sente_ops = self.quiescence_operations(Side.SENTE, 2)
        gote_ops = self.quiescence_operations(Side.GOTE, 2)
        if sente_ops is None or gote_ops is None:
            return
        sente = alpha_beta.search_controlled(
            first_capture, 0, sente_ops, self.control()
        )
        gote = alpha_beta.search_controlled(first_capture, 0, gote_ops, self.control())

        self.assertEqual((sente.score, gote.score), ((0, 3), (0, -3)))
        self.assertEqual(format_sfen(sf), RECAPTURE)

    def test_check_evasion_values_reverse_when_turn_and_sides_are_swapped(self):
        """王手中の最小化・最大化が先後反転後に評価符号も反転する。

        王手回避だけ最大・最小を固定する誤りと、後手の応手に偏る誤りを検出する。
        """
        for sfen, expected in (
            (KING_ESCAPE_CHECK, 15),
            (DROP_INTERPOSITION_CHECK, 20),
            (CAPTURE_CHECKER_ONLY, 4),
            (MIXED_CHECK_EVASIONS, -24),
        ):
            with self.subTest(sfen=sfen):
                original = parse_sfen(sfen).position
                rotated = self.rotate_and_swap_sides(original)
                original_result = alpha_beta.search_controlled(
                    original,
                    0,
                    self.quiescence_operations(Side.SENTE, 1),
                    self.control(),
                )
                rotated_result = alpha_beta.search_controlled(
                    rotated,
                    0,
                    self.quiescence_operations(Side.SENTE, 1),
                    self.control(),
                )

                self.assertEqual(original.side_to_move, Side.GOTE)
                self.assertEqual(rotated.side_to_move, Side.SENTE)
                self.assertEqual(
                    (original_result.score, rotated_result.score),
                    ((0, expected), (0, -expected)),
                )

    def test_capturing_promotion_is_searched_but_quiet_promotion_is_not(self):
        """捕獲成りを残し、駒取りのない成りを静止探索候補から除く。

        成りフラグを落として評価する誤りと、静かな成りでstand patを上書きする誤りを検出する。
        """
        capture_position = parse_sfen(CAPTURING_PROMOTION).position
        base = shogi.make_operations(Side.SENTE)
        capture = parse_usi_move("5d5c")
        capture_promote = parse_usi_move("5d5c+")
        self.assertIn(capture, base.inspect(capture_position).moves)
        self.assertIn(capture_promote, base.inspect(capture_position).moves)
        self.assertEqual(base.evaluate(capture_position), (0, -7))
        self.assertEqual(base.evaluate(base.advance(capture_position, capture)), (0, 9))
        self.assertEqual(
            base.evaluate(base.advance(capture_position, capture_promote)), (0, 20)
        )

        quiet_position = parse_sfen(QUIET_PROMOTION).position
        quiet_promote = parse_usi_move("5d5c+")
        self.assertIn(quiet_promote, base.inspect(quiet_position).moves)
        self.assertEqual(base.evaluate(quiet_position), (0, 1))

        operations = self.quiescence_operations(Side.SENTE, 1)
        if operations is None:
            return
        captured = alpha_beta.search_controlled(
            capture_position, 0, operations, self.control()
        )
        quiet = alpha_beta.search_controlled(
            quiet_position, 0, operations, self.control()
        )

        self.assertEqual((captured.score, quiet.score), ((0, 20), (0, 1)))

    def test_check_evasions_include_king_moves_drops_and_captures(self):
        """王手中は玉移動・合駒・王手駒の捕獲を全て候補にする。

        王手回避を玉移動だけ、合駒だけ、または捕獲だけへ狭める誤りを検出する。
        """
        cases = (
            (
                KING_ESCAPE_CHECK,
                ("5a4a", "5a4b", "5a6b", "5a6a"),
            ),
            (DROP_INTERPOSITION_CHECK, ("G*5b", "G*5c", "G*5d")),
            (CAPTURE_CHECKER_ONLY, ("6d5e",)),
        )
        for sfen, expected_tokens in cases:
            with self.subTest(sfen=sfen):
                position = parse_sfen(sfen).position
                base = shogi.make_controlled_operations(Side.SENTE)
                control = self.control()
                inspected = base.inspect(position, control)
                expected = tuple(map(parse_usi_move, expected_tokens))
                self.assertTrue(is_in_check(position.board, position.side_to_move))
                self.assertIsNone(inspected.terminal_score)
                self.assertEqual(inspected.moves, expected)
                calls = []

                def advance(node, move, active_control, calls=calls, base=base):
                    calls.append(move)
                    return base.advance(node, move, active_control)

                operations = replace(base, advance=advance)
                result = quiescence.search(
                    position,
                    inspected,
                    1,
                    None,
                    None,
                    control,
                    operations,
                )

                self.assertNotIsInstance(result, (SearchInterrupted, QuiescenceLimit))
                self.assertEqual(tuple(calls), expected)

    def test_check_at_zero_limit_is_incomplete_but_checkmate_is_a_score(self):
        """回避のある王手で上限0は未完了、詰みは上限前に勝敗値を返す。

        王手中の静的採点と、詰みを上限未完了として失う誤りを検出する。
        """
        checked = parse_sfen(KING_ESCAPE_CHECK).position
        checked_ops = self.quiescence_operations(Side.GOTE, 0)
        if checked_ops is None:
            return
        limited = alpha_beta.search_controlled(checked, 0, checked_ops, self.control())
        self.assertIsInstance(limited, QuiescenceLimit)

        mate_base = shogi.make_operations(Side.SENTE)
        mate_position = mate_base.advance(
            parse_sfen(MATE).position, parse_usi_move("5c5b")
        )
        mate_ops = self.quiescence_operations(Side.GOTE, 0)
        if mate_ops is None:
            return
        mate = alpha_beta.search_controlled(mate_position, 0, mate_ops, self.control())

        self.assertEqual((mate.score, mate.move), ((-1, 0), None))

    def test_search_returns_stop_or_suppression_from_shared_control(self):
        """静止探索の入口・子遷移・子調査から停止理由をそのまま伝える。

        時間停止を通常評価にする、抑制を停止へ弱める、部分調査を採点する誤りを検出する。
        """
        position = parse_sfen(OTHER_SQUARE_CAPTURES).position
        base = shogi.make_controlled_operations(Side.SENTE)
        active = self.control()
        inspected = base.inspect(position, active)

        timed = SearchControl(SearchBudget(1, 1), 0, now_ns=lambda: 1_000_000)
        stopped = quiescence.search(position, inspected, 1, None, None, timed, base)
        self.assertEqual(stopped, SearchInterrupted(SearchSignal.STOP))

        suppressed = self.control()
        suppressed.request_stop()
        suppressed.request_stop(suppress_response=True)
        hidden = quiescence.search(position, inspected, 1, None, None, suppressed, base)
        self.assertEqual(hidden, SearchInterrupted(SearchSignal.SUPPRESS))

        def interrupted_inspection(node, control):
            return SearchInterrupted(SearchSignal.SUPPRESS)

        def real_advance(node, move, control):
            return base.advance(node, move, control)

        operations = replace(base, inspect=interrupted_inspection, advance=real_advance)
        partial = quiescence.search(
            position, inspected, 1, None, None, active, operations
        )
        self.assertEqual(partial, SearchInterrupted(SearchSignal.SUPPRESS))

    def test_search_checks_control_after_advance_and_preserves_operation_failures(self):
        """遷移後の停止を先に反映し、局面操作の例外をそのまま伝える。

        遷移中に届いた抑制を見落とす誤りと、故障を通常中断へ変換する誤りを検出する。
        """
        position = parse_sfen(OTHER_SQUARE_CAPTURES).position
        base = shogi.make_controlled_operations(Side.SENTE)
        active = self.control()
        inspected = base.inspect(position, active)

        def stop_during_advance(node, move, control):
            control.request_stop(suppress_response=True)
            return base.advance(node, move, control)

        interrupted = quiescence.search(
            position,
            inspected,
            1,
            None,
            None,
            active,
            replace(base, advance=stop_during_advance),
        )
        self.assertEqual(interrupted, SearchInterrupted(SearchSignal.SUPPRESS))

        failure = RuntimeError("局面遷移に失敗")

        def broken_advance(node, move, control):
            raise failure

        with self.assertRaises(RuntimeError) as caught:
            quiescence.search(
                position,
                inspected,
                1,
                None,
                None,
                self.control(),
                replace(base, advance=broken_advance),
            )
        self.assertIs(caught.exception, failure)

    def test_search_stops_during_real_controlled_legal_move_generation(self):
        """子局面の合法手一覧が途中中断なら不完全な一覧を評価に使わない。

        合法手生成中断を手なしや静的評価へ読み替える誤りを検出する。
        """
        position = parse_sfen(OTHER_SQUARE_CAPTURES).position
        base = shogi.make_controlled_operations(Side.SENTE)
        stable = self.control()
        inspected = base.inspect(position, stable)
        clock_state = {"in_child_inspect": False, "checks": 0}

        def now_ns():
            if not clock_state["in_child_inspect"]:
                return 0
            clock_state["checks"] += 1
            return 1_000_000 if clock_state["checks"] >= 6 else 0

        control = SearchControl(SearchBudget(1, 1), 0, now_ns=now_ns)

        def inspect_child(node, active_control):
            if node is not position:
                clock_state["in_child_inspect"] = True
            return base.inspect(node, active_control)

        operations = replace(base, inspect=inspect_child)
        result = quiescence.search(
            position, inspected, 1, None, None, control, operations
        )

        self.assertEqual(result, SearchInterrupted(SearchSignal.STOP))
        self.assertGreaterEqual(clock_state["checks"], 6)

    def test_stand_pat_respects_both_alpha_beta_bounds_before_captures(self):
        """stand patが境界を越えた側では捕獲枝を追加調査しない。

        呼出し元α・βの破棄と、最大側・最小側での枝刈り条件反転を検出する。
        """
        position = parse_sfen(OTHER_SQUARE_CAPTURES).position
        for perspective, lower, upper, expected in (
            (Side.SENTE, None, (0, 15), (0, 20)),
            (Side.GOTE, (0, -15), None, (0, -20)),
        ):
            with self.subTest(perspective=perspective):
                operations = shogi.make_controlled_operations(perspective)
                control = self.control()
                inspected = operations.inspect(position, control)
                advances = []

                def track_advance(
                    node,
                    move,
                    active_control,
                    advances=advances,
                    operations=operations,
                ):
                    advances.append(move)
                    return operations.advance(node, move, active_control)

                wrapped = replace(operations, advance=track_advance)
                result = quiescence.search(
                    position,
                    inspected,
                    2,
                    lower,
                    upper,
                    control,
                    wrapped,
                )

                self.assertEqual(result, expected)
                self.assertEqual(advances, [])

    def test_quiescence_limit_does_not_overwrite_later_suppression(self):
        """王手上限に達しても抑制要求を優先して返す。

        専用未完了マーカーが応答抑制を覆い隠す誤りを検出する。
        """
        position = parse_sfen(KING_ESCAPE_CHECK).position
        base = shogi.make_controlled_operations(Side.GOTE)
        control = self.control()
        inspected = base.inspect(position, control)
        control.request_stop(suppress_response=True)

        result = quiescence.search(position, inspected, 0, None, None, control, base)

        self.assertEqual(result, SearchInterrupted(SearchSignal.SUPPRESS))

    def test_position_snapshot_and_capture_order_do_not_change_quiescence_value(self):
        """捕獲枝の順序を逆転しても評価を保ち、入力局面を変更しない。

        共有可変盤面による兄弟干渉と、手順同点時の順序依存を検出する。
        """
        sf = parse_sfen(OTHER_SQUARE_CAPTURES)
        position = sf.position
        base = shogi.make_controlled_operations(Side.SENTE)
        control = self.control()
        inspected = base.inspect(position, control)

        def reverse_inspection(node, active_control):
            result = base.inspect(node, active_control)
            if isinstance(result, SearchInterrupted):
                return result
            return replace(result, moves=tuple(reversed(result.moves)))

        reversed_ops = replace(base, inspect=reverse_inspection)
        reversed_inspection = reverse_inspection(position, control)
        normal = quiescence.search(position, inspected, 2, None, None, control, base)
        reversed_result = quiescence.search(
            position, reversed_inspection, 2, None, None, control, reversed_ops
        )

        self.assertEqual((normal, reversed_result), ((0, 38), (0, 38)))
        self.assertEqual(format_sfen(sf), OTHER_SQUARE_CAPTURES)

    def test_search_counters_are_optional_and_count_independent_entries(self):
        """通常調査と静止探索入口を別計数し、計数なしの評価を変えない。

        予備手準備や局面種類の合計を探索ノードに混ぜる誤りを検出する。
        """
        try:
            diagnostics = import_module("kaname_shogi.search.diagnostics")
        except ModuleNotFoundError:
            diagnostics = None
        self.assertIsNotNone(diagnostics, "任意計数データが必要です")
        if diagnostics is None:
            return
        counters_type = getattr(diagnostics, "SearchCounters", None)
        self.assertTrue(callable(counters_type), "SearchCountersが必要です")
        if counters_type is None:
            return
        factory = getattr(shogi, "make_quiescence_operations", None)
        self.assertTrue(callable(factory), "静止探索操作セットが必要です")
        if factory is None:
            return
        self.assertIn("counters", signature(factory).parameters)
        if "counters" not in signature(factory).parameters:
            return

        position = parse_sfen(KINGS).position
        counters = counters_type()
        operations = factory(Side.SENTE, 0, counters=counters)
        inspect_calls = []
        leaf_calls = []
        inspect_operation = operations.inspect
        leaf_operation = operations.search_leaf
        self.assertIsNotNone(leaf_operation)
        if leaf_operation is None:
            return

        def count_inspect(node, control):
            inspect_calls.append(node)
            return inspect_operation(node, control)

        def count_leaf(node, inspected, lower, upper, control):
            leaf_calls.append(node)
            return leaf_operation(node, inspected, lower, upper, control)

        operations = replace(operations, inspect=count_inspect, search_leaf=count_leaf)
        measured = alpha_beta.search_controlled(position, 1, operations, self.control())
        unmeasured = alpha_beta.search_controlled(
            position, 1, factory(Side.SENTE, 0), self.control()
        )

        self.assertEqual(
            (measured.score, measured.move), (unmeasured.score, unmeasured.move)
        )
        expected_calls = (4, 3)
        self.assertEqual((len(inspect_calls), len(leaf_calls)), expected_calls)
        self.assertEqual(
            (counters.normal_nodes, counters.quiescence_calls), expected_calls
        )


if __name__ == "__main__":
    unittest.main()
