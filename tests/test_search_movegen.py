"""探索中断の確定・未確定を、固定局面と操作境界で確認する。"""

import unittest
from unittest.mock import patch

from kaname_shogi import movegen as mg
from kaname_shogi.model import (
    BasicPieceType,
    Board,
    Piece,
    PieceType,
    Position,
    Side,
    Square,
)
from kaname_shogi.move import BoardMove, DropMove
from kaname_shogi.search_control import SearchControl
from kaname_shogi.time_management import SearchBudget

LEGACY_POLICIES = (
    mg.MoveSelectionPolicy.RANDOM,
    mg.MoveSelectionPolicy.MATERIAL,
    mg.MoveSelectionPolicy.TWO_PLY_MATERIAL,
)
CONTROLLED_ONE_PLY_POLICIES = (
    *LEGACY_POLICIES,
    mg.MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE,
)


def snapshot(p):
    return (
        tuple(
            p.board.piece_at(Square(f, r)) for f in range(1, 10) for r in range(1, 10)
        ),
        tuple(
            h.count(t)
            for h in (p.sente_hand, p.gote_hand)
            for t in BasicPieceType
            if t != BasicPieceType.KING
        ),
        p.side_to_move,
    )


def pawns():
    p = Position(Board(), Side.SENTE)
    for f in (2, 7):
        p.board.set_piece(Square(f, 7), Piece(PieceType.PAWN, Side.SENTE))
    return p


def kings_and_pawns(side):
    """先後の玉と二歩だけを置いたU制御探索用局面を返す。"""
    p = Position(Board(), side)
    p.board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
    p.board.set_piece(Square(5, 1), Piece(PieceType.KING, Side.GOTE))
    rank = 7 if side is Side.SENTE else 3
    for file in (2, 7):
        p.board.set_piece(Square(file, rank), Piece(PieceType.PAWN, side))
    return p


def uchi(side):
    p = Position(Board(), side)
    other = Side.GOTE if side == Side.SENTE else Side.SENTE

    def sq(f, r):
        return Square(f, r) if side == Side.SENTE else Square(10 - f, 10 - r)

    for f, r, t, s in (
        (5, 1, PieceType.KING, other),
        (9, 9, PieceType.KING, side),
        (4, 3, PieceType.GOLD, side),
        (4, 1, PieceType.PAWN, other),
        (6, 1, PieceType.PAWN, other),
        (4, 2, PieceType.PAWN, other),
        (6, 2, PieceType.PAWN, other),
    ):
        p.board.set_piece(sq(f, r), Piece(t, s))
    (p.sente_hand if side == Side.SENTE else p.gote_hand).add(BasicPieceType.PAWN)
    return p, sq(5, 2)


class ControlledGenerationTests(unittest.TestCase):
    def test_root_generation_stops_after_first_legal_move(self):
        """0予算でも最初の合法手を確保し、空盤は全調査の手なしとなる。

        予備手未確保の即打切りと全一覧の継続を検出する。
        """
        c = SearchControl(SearchBudget(0, 0), 0, now_ns=lambda: 0)
        result = mg._legal_moves_controlled(
            pawns(), check_uchi_fuzume=True, control=c, root=True
        )
        self.assertFalse(result.completed)
        self.assertEqual(result.moves, (BoardMove(Square(2, 7), Square(2, 6), False),))
        empty = mg._legal_moves_controlled(
            Position(Board(), Side.SENTE), check_uchi_fuzume=True, control=c, root=True
        )
        self.assertTrue(empty.completed)
        self.assertEqual(empty.moves, ())

    def test_keeps_only_confirmed_moves(self):
        """盤上手・成り・駒打ちの確認途中で止まると未確定手を追加しない。

        下位適用復帰後や反復ごとの停止確認漏れを検出する。
        """
        for mode in ("board", "promotion", "drop"):
            with self.subTest(mode=mode):
                p = pawns() if mode == "board" else Position(Board(), Side.SENTE)
                if mode == "promotion":
                    p.board.set_piece(Square(3, 4), Piece(PieceType.PAWN, Side.SENTE))
                if mode == "drop":
                    p.sente_hand.add(BasicPieceType.ROOK)
                c = SearchControl(None, 0)
                original = mg._apply_drop_unchecked if mode == "drop" else mg.apply_move

                def trigger(*args, mode=mode, c=c, original=original, **kwargs):
                    if (
                        (mode == "board" and args[1] == Square(7, 7))
                        or (mode == "promotion" and kwargs.get("promote"))
                        or (mode == "drop" and args[2] == Square(1, 2))
                    ):
                        c.request_stop()
                    return original(*args, **kwargs)

                expected = {
                    "board": BoardMove(Square(2, 7), Square(2, 6), False),
                    "promotion": BoardMove(Square(3, 4), Square(3, 3), False),
                    "drop": DropMove(BasicPieceType.ROOK, Square(1, 1)),
                }[mode]
                before = snapshot(p)
                with patch.object(
                    mg,
                    "_apply_drop_unchecked" if mode == "drop" else "apply_move",
                    side_effect=trigger,
                ):
                    result = mg._legal_moves_controlled(
                        p, check_uchi_fuzume=True, control=c, root=True
                    )
                self.assertFalse(result.completed)
                self.assertEqual(result.moves, (expected,))
                self.assertEqual(snapshot(p), before)

    def test_suppression_breaks_first_move_protection(self):
        """最初の合法判定中の抑制は保護を破り、未確定手を渡さない。

        抑制にも通常停止の保護を適用する誤りを検出する。
        """
        c = SearchControl(None, 0)
        original = mg.apply_move

        def suppress(*args, **kwargs):
            c.request_stop(suppress_response=True)
            return original(*args, **kwargs)

        with patch.object(mg, "apply_move", side_effect=suppress):
            result = mg._legal_moves_controlled(
                pawns(), check_uchi_fuzume=True, control=c, root=True
            )
        self.assertFalse(result.completed)
        self.assertEqual(result.moves, ())

    def test_uchi_fuzume_interrupt_is_not_legality(self):
        """先後の打ち歩詰めの防御確認中断を合法・非詰みへ変換しない。

        根保護は通常停止を下位へ伝え、抑制は保留しない対照も調べる。
        """
        for side in Side:
            for protected, suppress in (
                (False, False),
                (False, True),
                (True, False),
                (True, True),
            ):
                with self.subTest(side=side, protected=protected, suppress=suppress):
                    p, dest = uchi(side)
                    before = snapshot(p)
                    c = SearchControl(None, 0)
                    original = mg._has_legal_move_controlled

                    def stop_inside(
                        *args, c=c, suppress=suppress, original=original, **kwargs
                    ):
                        c.request_stop(suppress_response=suppress)
                        return original(*args, **kwargs)

                    with patch.object(
                        mg, "_has_legal_move_controlled", side_effect=stop_inside
                    ):
                        if protected and not suppress:
                            with self.assertRaises(ValueError):
                                mg._apply_drop_controlled(
                                    p,
                                    BasicPieceType.PAWN,
                                    dest,
                                    check_uchi_fuzume=True,
                                    control=c,
                                    protect_first_legal=True,
                                )
                        else:
                            try:
                                result = mg._apply_drop_controlled(
                                    p,
                                    BasicPieceType.PAWN,
                                    dest,
                                    check_uchi_fuzume=True,
                                    control=c,
                                    protect_first_legal=protected,
                                )
                            except ValueError:
                                self.fail("中断を打ち歩詰め確定に変換した")
                            self.assertFalse(result.completed)
                    self.assertEqual(snapshot(p), before)

    def test_checkmate_and_move_existence_keep_unknown(self):
        """中断は不明を保持し、玉なし・非王手は完了した非詰みになる。

        空の途中一覧を手なし確定にする誤りを検出する。
        """
        c = SearchControl(None, 0)
        c.request_stop()
        result = mg._has_legal_move_controlled(
            pawns(), check_uchi_fuzume=True, control=c
        )
        self.assertFalse(result.completed)
        self.assertIsNone(result.value)
        p, dest = uchi(Side.SENTE)
        mg._apply_drop_unchecked(p, BasicPieceType.PAWN, dest)
        result = mg._is_checkmate_controlled(p, check_uchi_fuzume=False, control=c)
        self.assertFalse(result.completed)
        self.assertIsNone(result.value)
        for p in (pawns(), Position(Board(), Side.SENTE)):
            result = mg._is_checkmate_controlled(p, check_uchi_fuzume=True, control=c)
            self.assertTrue(result.completed)
            self.assertFalse(result.value)
        self.assertEqual(
            mg._has_legal_move_controlled(
                pawns(), check_uchi_fuzume=True, control=None
            ).value,
            True,
        )
        self.assertEqual(
            mg._has_legal_move_controlled(
                Position(Board(), Side.SENTE), check_uchi_fuzume=True, control=None
            ).value,
            False,
        )

    def test_interrupted_application_preserves_position(self):
        """一手適用中断は元局面を保存し、未知手と違法手は例外のまま渡す。

        中断の部分局面返却と故障の正常停止化を検出する。
        """
        p = pawns()
        before = snapshot(p)
        c = SearchControl(None, 0)
        original = mg.apply_move

        def stop(*args, **kwargs):
            original(*args, **kwargs)
            c.request_stop()

        with patch.object(mg, "apply_move", side_effect=stop):
            result, after = mg._position_after_move_controlled(
                p, BoardMove(Square(2, 7), Square(2, 6), False), control=c
            )
        self.assertFalse(result.completed)
        self.assertIsNone(after)
        self.assertEqual(snapshot(p), before)
        with self.assertRaises(TypeError):
            mg._position_after_move_controlled(p, object(), control=None)
        with self.assertRaises(ValueError):
            mg._position_after_move_controlled(
                p, BoardMove(Square(2, 7), Square(2, 5), False), control=None
            )

    def test_does_not_start_next_trial_after_stop(self):
        """予備手が確定した後の停止では次の不成・成り・駒打ちを開始しない。

        復帰後の確認だけを残して反復開始の確認を消す誤りを検出する。
        """
        for drop in (False, True):
            with self.subTest(drop=drop):
                p = Position(Board(), Side.SENTE) if drop else pawns()
                if drop:
                    p.sente_hand.add(BasicPieceType.ROOK)
                c = SearchControl(None, 0)
                name = "_apply_drop_unchecked" if drop else "apply_move"
                original = getattr(mg, name)
                seen = []

                def stop_after(*args, c=c, original=original, seen=seen, **kwargs):
                    original(*args, **kwargs)
                    seen.append(args[2])
                    c.request_stop()

                with patch.object(mg, name, side_effect=stop_after):
                    result = mg._legal_moves_controlled(
                        p, check_uchi_fuzume=True, control=c, root=True
                    )
                self.assertFalse(result.completed)
                self.assertEqual(
                    result.moves,
                    (DropMove(BasicPieceType.ROOK, Square(1, 1)),)
                    if drop
                    else (BoardMove(Square(2, 7), Square(2, 6), False),),
                )
                self.assertTrue(seen)
                self.assertEqual(set(seen), {Square(1, 1) if drop else Square(2, 6)})

    def test_protected_non_mating_pawn_drop_completes(self):
        """保護中の通常停止でも合法な歩打ちを確定できる。

        打ち歩詰めの内部だけ保護を失う誤りを合法側の対照で検出する。
        """
        for side in Side:
            p, dest = uchi(side)
            # 金を除くと玉が打った歩を取れるので、歩打ちは合法。
            p.board.set_piece(
                Square(4, 3) if side == Side.SENTE else Square(6, 7), None
            )
            c = SearchControl(None, 0)
            original = mg._has_legal_move_controlled

            def stop_inside(*args, c=c, original=original, **kwargs):
                c.request_stop()
                return original(*args, **kwargs)

            with patch.object(
                mg, "_has_legal_move_controlled", side_effect=stop_inside
            ):
                result = mg._apply_drop_controlled(
                    p,
                    BasicPieceType.PAWN,
                    dest,
                    check_uchi_fuzume=True,
                    control=c,
                    protect_first_legal=True,
                )
            self.assertTrue(result.completed)
            self.assertEqual(p.board.piece_at(dest), Piece(PieceType.PAWN, side))

    def test_move_existence_finishes_at_first_confirmed_move(self):
        """手ありは最初の合法手で確定し、後続候補を調べない。

        既知Trueを後続中断で不明へ戻す誤りを検出する。
        """
        c = SearchControl(None, 0)
        original = mg.apply_move
        seen = []

        def stop_later(*args, **kwargs):
            seen.append(args[1])
            if args[1] == Square(7, 7):
                c.request_stop()
            return original(*args, **kwargs)

        with patch.object(mg, "apply_move", side_effect=stop_later):
            result = mg._has_legal_move_controlled(
                pawns(), check_uchi_fuzume=True, control=c
            )
        self.assertTrue(result.completed)
        self.assertTrue(result.value)
        self.assertEqual(seen, [Square(2, 7)])

    def test_root_protection_reaches_pawn_defense(self):
        """根の最初の歩打ちの防御確認まで保護を伝え、抑制だけは中断する。

        候補を一手に絞る境界と実際の防御調査をつなぎ、根からのフラグ喪失を検出する。
        """
        for suppress in (False, True):
            with self.subTest(suppress=suppress):
                p, dest = uchi(Side.SENTE)
                p.board.set_piece(Square(4, 3), None)
                c = SearchControl(SearchBudget(0, 0), 0, now_ns=lambda: 0)
                drop = mg._apply_drop_controlled
                defense = mg._has_legal_move_controlled
                apply = mg.apply_move

                def root_move(*args, apply=apply, **kwargs):
                    if args[0].side_to_move == Side.SENTE:
                        raise ValueError("この教材では根の盤上候補を除く")
                    return apply(*args, **kwargs)

                def root_drop(*args, dest=dest, drop=drop, **kwargs):
                    if args[0].side_to_move == Side.SENTE and (
                        args[1] != BasicPieceType.PAWN or args[2] != dest
                    ):
                        raise ValueError("この教材では指定した根の歩打ちだけ調べる")
                    return drop(*args, **kwargs)

                def stop_inside(
                    *args, c=c, suppress=suppress, defense=defense, **kwargs
                ):
                    c.request_stop(suppress_response=suppress)
                    return defense(*args, **kwargs)

                with (
                    patch.object(mg, "apply_move", side_effect=root_move),
                    patch.object(mg, "_apply_drop_controlled", side_effect=root_drop),
                    patch.object(
                        mg, "_has_legal_move_controlled", side_effect=stop_inside
                    ),
                ):
                    result = mg._legal_moves_controlled(
                        p, check_uchi_fuzume=True, control=c, root=True
                    )
                self.assertFalse(result.completed)
                self.assertEqual(
                    result.moves,
                    () if suppress else (DropMove(BasicPieceType.PAWN, dest),),
                )


def recapture(side):
    """歩取り7点、取り返し後-23点、安全手5点の先後教材。"""
    p = Position(Board(), side)
    other = Side.GOTE if side == Side.SENTE else Side.SENTE

    def sq(f, r):
        return Square(f, r) if side == Side.SENTE else Square(10 - f, 10 - r)

    for f, r, t, s in (
        (9, 9, PieceType.KING, side),
        (5, 5, PieceType.ROOK, side),
        (1, 1, PieceType.KING, other),
        (5, 3, PieceType.GOLD, other),
        (5, 4, PieceType.PAWN, other),
    ):
        p.board.set_piece(sq(f, r), Piece(t, s))
    return p, BoardMove(sq(5, 5), sq(5, 4), False), BoardMove(sq(5, 5), sq(4, 5), False)


def mating(side):
    p = Position(Board(), side)
    other = Side.GOTE if side == Side.SENTE else Side.SENTE

    def sq(f, r):
        return Square(f, r) if side == Side.SENTE else Square(10 - f, 10 - r)

    for f, r, t, s in (
        (9, 9, PieceType.KING, side),
        (5, 3, PieceType.ROOK, side),
        (4, 3, PieceType.GOLD, side),
        (5, 1, PieceType.KING, other),
        (4, 1, PieceType.PAWN, other),
        (6, 1, PieceType.PAWN, other),
        (4, 2, PieceType.PAWN, other),
        (6, 2, PieceType.PAWN, other),
    ):
        p.board.set_piece(sq(f, r), Piece(t, s))
    return p, BoardMove(sq(5, 3), sq(5, 2), False)


class ControlledEvaluationTests(unittest.TestCase):
    def test_undefended_piece_controlled_score_uses_turn_perspective(self):
        """通常局面のU評価値・着手後局面・視点を先後とも正しく渡す。

        評価関数へ着手前局面を渡す誤り、値の反転、手番視点の誤りを検出する。
        """
        policy = mg.MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE
        for side in Side:
            with self.subTest(side=side):
                position = kings_and_pawns(side)
                move = mg.legal_moves(position)[0]
                before = snapshot(position)
                expected_after = position.copy()
                mg.apply_move(
                    expected_after, move.source, move.destination, promote=move.promote
                )

                with patch(
                    "kaname_shogi.material_undefended_piece.evaluate_material_undefended_piece",
                    return_value=7,
                ) as evaluate:
                    result = mg._evaluate_candidate(
                        position,
                        move,
                        policy,
                        control=SearchControl(None, 0),
                    )

                    self.assertEqual(result, mg.CandidateEvaluation(True, (0, 7)))
                    evaluate.assert_called_once()
                    self.assertEqual(
                        snapshot(evaluate.call_args.args[0]), snapshot(expected_after)
                    )
                    self.assertIs(evaluate.call_args.args[1], side)
                self.assertEqual(snapshot(position), before)

    def test_undefended_piece_scores_mate_before_normal_evaluation(self):
        """制御付きU評価も先後とも一手詰みを `(1, 0)` として優先する。

        時計付き経路だけ詰みを通常評価へ混ぜる誤りと、候補適用で元局面を変える誤りを検出する。
        """
        policy = mg.MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE
        for side in Side:
            with self.subTest(side=side):
                position, move = mating(side)
                self.assertIn(move, mg.legal_moves(position))
                before = snapshot(position)

                try:
                    result = mg._evaluate_candidate(
                        position,
                        move,
                        policy,
                        control=SearchControl(None, 0),
                    )
                except ValueError as error:
                    self.fail(f"制御付き候補評価がU方針を拒否しました: {error}")

                self.assertEqual(result, mg.CandidateEvaluation(True, (1, 0)))
                self.assertEqual(snapshot(position), before)

    def test_undefended_piece_discards_evaluation_stopped_at_boundary(self):
        """U採点中の停止は候補未完了として返す。

        採点復帰後の停止確認を省いて部分・期限超過の点を完了扱いにする誤りを検出する。
        """
        position = kings_and_pawns(Side.SENTE)
        move = mg.legal_moves(position)[0]
        control = SearchControl(None, 0)

        def stop_after_evaluation(*args, **kwargs):
            control.request_stop()
            return 7

        with patch(
            "kaname_shogi.material_undefended_piece.evaluate_material_undefended_piece",
            side_effect=stop_after_evaluation,
        ):
            try:
                result = mg._evaluate_candidate(
                    position,
                    move,
                    mg.MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE,
                    control=control,
                )
            except ValueError as error:
                self.fail(f"制御付き候補評価がU方針を拒否しました: {error}")

        self.assertEqual(result, mg.CandidateEvaluation(False, None))

    def test_completed_scores_preserve_policy_and_perspective(self):
        """先後反転でも一手7/5点、二手-23/5点と詰みの勝敗を維持する。

        駒得は15+1-9=7、取り返し後1-15-9=-23、通常15-9-1=5。
        詰み勝ち(1,0)・負け(-1,0)を通常駒得へ混ぜる誤りも検出する。
        """
        for side in Side:
            p, capture, safe = recapture(side)
            for policy, move, score in (
                (mg.MoveSelectionPolicy.MATERIAL, capture, (0, 7)),
                (mg.MoveSelectionPolicy.MATERIAL, safe, (0, 5)),
                (mg.MoveSelectionPolicy.TWO_PLY_MATERIAL, capture, (0, -23)),
                (mg.MoveSelectionPolicy.TWO_PLY_MATERIAL, safe, (0, 5)),
            ):
                with self.subTest(side=side, policy=policy, move=move):
                    before = snapshot(p)
                    r = mg._evaluate_candidate(
                        p, move, policy, control=SearchControl(None, 0)
                    )
                    self.assertTrue(r.completed)
                    self.assertEqual(r.score, score)
                    self.assertEqual(snapshot(p), before)
            p, move = mating(side)
            r = mg._evaluate_candidate(
                p,
                move,
                mg.MoveSelectionPolicy.TWO_PLY_MATERIAL,
                control=SearchControl(None, 0),
            )
            self.assertEqual(r.score, (1, 0))
            # 相手側の開始視点では、全応手の一つで詰まされるため最悪(-1,0)。
            other = Side.GOTE if side == Side.SENTE else Side.SENTE
            r = mg._two_ply_score_controlled(p, other, control=SearchControl(None, 0))
            self.assertEqual(r.score, (-1, 0))
            empty = Position(Board(), other)
            for _ in range(7):
                (empty.sente_hand if side == Side.SENTE else empty.gote_hand).add(
                    BasicPieceType.PAWN
                )
            r = mg._two_ply_score_controlled(
                empty, side, control=SearchControl(None, 0)
            )
            self.assertEqual(r.score, (0, 7))

    def test_target_allows_current_candidate_to_finish(self):
        """目標到達だけなら現在候補と応手調査を完了させる。

        評価中に根と同じ目標判定を流用する誤りを検出する。
        """
        for policy in (
            mg.MoveSelectionPolicy.MATERIAL,
            mg.MoveSelectionPolicy.TWO_PLY_MATERIAL,
        ):
            with self.subTest(policy=policy):
                p, move, _ = recapture(Side.SENTE)
                now = [0]
                c = SearchControl(
                    SearchBudget(10, 20), 0, now_ns=lambda now=now: now[0]
                )
                apply = mg.apply_move

                def reach_target(*args, apply=apply, now=now, **kwargs):
                    apply(*args, **kwargs)
                    now[0] = 10_000_000

                with patch.object(mg, "apply_move", side_effect=reach_target):
                    r = mg._evaluate_candidate(p, move, policy, control=c)
                self.assertTrue(r.completed)
                self.assertEqual(
                    r.score,
                    (0, 7) if policy == mg.MoveSelectionPolicy.MATERIAL else (0, -23),
                )
                zero = SearchControl(SearchBudget(0, 1), 0, now_ns=lambda: 0)
                self.assertTrue(
                    mg._evaluate_candidate(p, move, policy, control=zero).completed
                )

    def test_maximum_or_stop_discards_candidate(self):
        """静的採点の復帰時に上限かstopなら候補を未完了にする。

        計算済みの点でも最終確認前なら完了へ昇格させない境界を検出する。
        """
        for stop in (False, True):
            p, move, _ = recapture(Side.SENTE)
            now = [0]
            c = SearchControl(SearchBudget(10, 20), 0, now_ns=lambda now=now: now[0])
            balance = mg.material_balance

            def expire(*args, balance=balance, stop=stop, c=c, now=now, **kwargs):
                score = balance(*args, **kwargs)
                if stop:
                    c.request_stop()
                else:
                    now[0] = 20_000_000
                return score

            with patch.object(mg, "material_balance", side_effect=expire):
                r = mg._evaluate_candidate(
                    p, move, mg.MoveSelectionPolicy.MATERIAL, control=c
                )
            self.assertFalse(r.completed)
            self.assertIsNone(r.score)

    def test_reply_and_mate_interrupt_propagate(self):
        """応手の先頭・中間・末尾と詰みの防御調査中断を不明のまま伝える。

        部分minや未確定詰みの通常点化を検出し、先後と元局面保存も確認する。
        """
        for side in Side:
            for slot in ("first", "middle", "last"):
                with self.subTest(side=side, slot=slot):
                    p, move, _ = recapture(side)
                    after = mg._position_after_move(p, move)
                    replies = mg.legal_moves(after)
                    chosen = replies[
                        {"first": 0, "middle": len(replies) // 2, "last": -1}[slot]
                    ]
                    c = SearchControl(None, 0)
                    application = mg._position_after_move_controlled

                    def stop_reply(
                        current,
                        reply,
                        *,
                        control,
                        chosen=chosen,
                        c=c,
                        application=application,
                    ):
                        result = application(current, reply, control=control)
                        if reply == chosen:
                            c.request_stop()
                        return result

                    before = snapshot(after)
                    with patch.object(
                        mg, "_position_after_move_controlled", side_effect=stop_reply
                    ):
                        r = mg._two_ply_score_controlled(after, side, control=c)
                    self.assertFalse(r.completed)
                    self.assertIsNone(r.score)
                    self.assertEqual(snapshot(after), before)
            p, move = mating(side)
            c = SearchControl(None, 0)
            defense = mg._has_legal_move_controlled

            def stop_defense(*args, c=c, defense=defense, **kwargs):
                c.request_stop()
                return defense(*args, **kwargs)

            with patch.object(
                mg, "_has_legal_move_controlled", side_effect=stop_defense
            ):
                r = mg._evaluate_candidate(
                    p, move, mg.MoveSelectionPolicy.TWO_PLY_MATERIAL, control=c
                )
            self.assertFalse(r.completed)
            self.assertIsNone(r.score)

    def test_last_reply_score_must_pass_return_check(self):
        """最後の応手採点復帰後に停止した候補も捨てる。

        下位呼出しの後の停止確認を省く誤りを、末尾だけの停止で検出する。
        """
        p, move, _ = recapture(Side.SENTE)
        after = mg._position_after_move(p, move)
        last = mg._position_after_move(after, mg.legal_moves(after)[-1])
        c = SearchControl(None, 0)
        balance = mg.material_balance

        def stop_last(current, perspective):
            score = balance(current, perspective)
            if snapshot(current) == snapshot(last):
                c.request_stop()
            return score

        with patch.object(mg, "material_balance", side_effect=stop_last):
            r = mg._two_ply_score_controlled(after, Side.SENTE, control=c)
        self.assertFalse(r.completed)
        self.assertIsNone(r.score)

    def test_two_ply_keeps_mate_interruption_unknown(self):
        """二手評価単独でも詰み防御調査の中断を点へ変換しない。

        外側候補評価の停止確認が下位の誤りを隠す不足を補う。
        """
        for side in Side:
            for suppress in (False, True):
                with self.subTest(side=side, suppress=suppress):
                    p, move = mating(side)
                    after = mg._position_after_move(p, move)
                    c = SearchControl(None, 0)
                    defense = mg._has_legal_move_controlled

                    def stop_inside(
                        *args, c=c, suppress=suppress, defense=defense, **kwargs
                    ):
                        c.request_stop(suppress_response=suppress)
                        return defense(*args, **kwargs)

                    with patch.object(
                        mg, "_has_legal_move_controlled", side_effect=stop_inside
                    ):
                        r = mg._two_ply_score_controlled(after, side, control=c)
                    self.assertFalse(r.completed)
                    self.assertIsNone(r.score)


class RootSearchTests(unittest.TestCase):
    def test_undefended_piece_policy_returns_legal_move_for_both_sides(self):
        """U方針は先後とも制御付き探索で合法手を完了する。

        対局専用入口で新候補を未知扱いにしたり、手番側・乱数・元局面を壊す誤りを検出する。
        """
        policy = mg.MoveSelectionPolicy.MATERIAL_UNDEFENDED_PIECE
        for side in Side:
            with self.subTest(side=side):
                position = kings_and_pawns(side)
                before = snapshot(position)
                legal = mg.legal_moves(position)
                rng = RecordingChoice()

                try:
                    result = mg.search_move(
                        position,
                        policy,
                        rng,
                        SearchControl(None, 0),
                    )
                except ValueError as error:
                    self.fail(f"制御付き探索がU方針を拒否しました: {error}")

                self.assertEqual(result.completion, mg.SearchCompletion.COMPLETE)
                self.assertIn(result.move, legal)
                self.assertEqual(len(rng.calls), 1)
                self.assertEqual(snapshot(position), before)

    def test_zero_budget_returns_fallback_or_confirmed_no_moves(self):
        """旧三方式とUの0予算・開始前stopは予備手、空盤は手なし確定を返す。

        0を時計なし扱い、未確保を投了、部分一覧の抽選にする誤りを検出する。
        """
        for policy in CONTROLLED_ONE_PLY_POLICIES:
            for side in Side:
                for zero in (False, True):
                    with self.subTest(policy=policy, side=side, zero=zero):
                        p = Position(Board(), side)
                        rank = 7 if side == Side.SENTE else 3
                        dest = 6 if side == Side.SENTE else 4
                        for f in (2, 7):
                            p.board.set_piece(
                                Square(f, rank), Piece(PieceType.PAWN, side)
                            )
                        c = SearchControl(
                            SearchBudget(0, 0) if zero else None, 0, now_ns=lambda: 0
                        )
                        if not zero:
                            c.request_stop()
                        rng = RecordingChoice()
                        before = snapshot(p)
                        r = mg.search_move(p, policy, rng, c)
                        self.assertEqual(r.completion, mg.SearchCompletion.INTERRUPTED)
                        self.assertEqual(
                            r.move, BoardMove(Square(2, rank), Square(2, dest), False)
                        )
                        self.assertEqual(rng.calls, [])
                        self.assertEqual(snapshot(p), before)
                        empty = mg.search_move(Position(Board(), side), policy, rng, c)
                        self.assertEqual(
                            empty, mg.SearchResult(mg.SearchCompletion.COMPLETE, None)
                        )

    def test_suppressed_search_has_no_response_move(self):
        """保護中の抑制も応答手なしの専用結果とし、抽選しない。

        SUPPRESSEDを手なし確定や予備手へ変換する誤りを検出する。
        """
        for policy in CONTROLLED_ONE_PLY_POLICIES:
            p = pawns()
            c = SearchControl(SearchBudget(0, 0), 0, now_ns=lambda: 0)
            c.request_stop(suppress_response=True)
            rng = RecordingChoice()
            r = mg.search_move(p, policy, rng, c)
            self.assertEqual(r, mg.SearchResult(mg.SearchCompletion.SUPPRESSED, None))
            self.assertEqual(rng.calls, [])

    def test_root_target_stops_generation_but_reply_target_does_not(self):
        """根生成は目標到達で予備手へ戻り、応手生成は目標だけでは止まらない。

        根と下位の目標判定の混同を実適用操作で検出する。
        """
        now = [0]
        c = SearchControl(SearchBudget(10, 20), 0, now_ns=lambda: now[0])
        apply = mg.apply_move

        def target(*args, **kwargs):
            apply(*args, **kwargs)
            now[0] = 10_000_000

        rng = RecordingChoice()
        with patch.object(mg, "apply_move", side_effect=target):
            r = mg.search_move(pawns(), mg.MoveSelectionPolicy.MATERIAL, rng, c)
        self.assertEqual(r.move, BoardMove(Square(2, 7), Square(2, 6), False))
        self.assertEqual(r.completion, mg.SearchCompletion.INTERRUPTED)
        self.assertEqual(rng.calls, [])
        p, move, _ = recapture(Side.SENTE)
        after = mg._position_after_move(p, move)
        r = mg._two_ply_score_controlled(after, Side.SENTE, control=c)
        self.assertTrue(r.completed)
        self.assertEqual(r.score, (0, -23))

    def test_target_prevents_next_candidate(self):
        """B評価中の目標到達ならBを保持しCを開始しない。

        目標で現在候補を捨てる誤りと新候補開始の確認漏れを検出する。
        """
        moves = three_moves()
        now = [0]
        c = SearchControl(SearchBudget(10, 20), 0, now_ns=lambda: now[0])
        seen = []

        def evaluate(p, move, policy, *, control):
            seen.append(move)
            if move == moves[1]:
                now[0] = 10_000_000
            return mg.CandidateEvaluation(True, (0, 3 if move == moves[0] else 7))

        rng = RecordingChoice()
        with (
            patch.object(
                mg,
                "_legal_moves_controlled",
                return_value=mg.LegalMovesResult(True, moves),
            ),
            patch.object(mg, "_evaluate_candidate", side_effect=evaluate),
        ):
            r = mg.search_move(pawns(), mg.MoveSelectionPolicy.MATERIAL, rng, c)
        self.assertEqual(seen, list(moves[:2]))
        self.assertEqual(r, mg.SearchResult(mg.SearchCompletion.INTERRUPTED, moves[1]))
        self.assertEqual(rng.calls, [(moves[1],)])

    def test_selects_only_completed_best_candidates(self):
        """完了した最高同点だけ一回抽選し、途中99点を使わない。

        候補順反転、同点、完了0件の対照で先頭固定・部分点採用を検出する。
        """
        original = three_moves()
        for reverse in (False, True):
            for tie in (False, True):
                with self.subTest(reverse=reverse, tie=tie):
                    moves = original[::-1] if reverse else original
                    c = SearchControl(None, 0)

                    def evaluate(
                        p, move, policy, *, control, moves=moves, c=c, tie=tie
                    ):
                        if move == moves[2]:
                            c.request_stop()
                            return mg.CandidateEvaluation(False, (0, 99))
                        return mg.CandidateEvaluation(
                            True, (0, 7 if tie or move == moves[1] else 3)
                        )

                    rng = RecordingChoice()
                    with (
                        patch.object(
                            mg,
                            "_legal_moves_controlled",
                            return_value=mg.LegalMovesResult(True, moves),
                        ),
                        patch.object(mg, "_evaluate_candidate", side_effect=evaluate),
                    ):
                        r = mg.search_move(
                            pawns(), mg.MoveSelectionPolicy.MATERIAL, rng, c
                        )
                    best = moves[:2] if tie else (moves[1],)
                    self.assertEqual(rng.calls, [best])
                    self.assertEqual(
                        r, mg.SearchResult(mg.SearchCompletion.INTERRUPTED, best[-1])
                    )
        c = SearchControl(None, 0)
        rng = RecordingChoice()
        with patch.object(
            mg, "_evaluate_candidate", return_value=mg.CandidateEvaluation(False, None)
        ):
            try:
                r = mg.search_move(pawns(), mg.MoveSelectionPolicy.MATERIAL, rng, c)
            except TypeError:
                self.fail("未完了のNone点を比較した")
        self.assertEqual(r.move, BoardMove(Square(2, 7), Square(2, 6), False))
        self.assertEqual(r.completion, mg.SearchCompletion.INTERRUPTED)
        self.assertEqual(rng.calls, [])

    def test_maximum_discards_active_candidate(self):
        """Bの実採点復帰前の上限・stopならBを捨て完了Aを返す。

        完了境界から根選択までの接続を実候補評価で検出する。
        """
        for stop in (False, True):
            with self.subTest(stop=stop):
                p = pawns()
                a = BoardMove(Square(2, 7), Square(2, 6), False)
                now = [0]
                c = SearchControl(
                    SearchBudget(10, 20), 0, now_ns=lambda now=now: now[0]
                )
                balance = mg.material_balance

                def expire_b(
                    current, perspective, stop=stop, c=c, now=now, balance=balance
                ):
                    score = balance(current, perspective)
                    if current.board.piece_at(Square(7, 6)) is not None:
                        if stop:
                            c.request_stop()
                        else:
                            now[0] = 20_000_000
                    return score

                rng = RecordingChoice()
                with patch.object(mg, "material_balance", side_effect=expire_b):
                    r = mg.search_move(p, mg.MoveSelectionPolicy.MATERIAL, rng, c)
                self.assertEqual(r, mg.SearchResult(mg.SearchCompletion.INTERRUPTED, a))
                self.assertEqual(rng.calls, [(a,)])

    def test_random_complete_and_interrupted_selection(self):
        """ランダムの全完了は全合法手を一回抽選、中断は予備手で抽選なし。

        部分一覧の抽選と二重抽選を検出する。
        """
        a = BoardMove(Square(2, 7), Square(2, 6), False)
        b = BoardMove(Square(7, 7), Square(7, 6), False)
        for budget, completion, move, calls in (
            (None, mg.SearchCompletion.COMPLETE, b, [(a, b)]),
            (SearchBudget(0, 0), mg.SearchCompletion.INTERRUPTED, a, []),
        ):
            rng = RecordingChoice()
            r = mg.search_move(
                pawns(),
                mg.MoveSelectionPolicy.RANDOM,
                rng,
                SearchControl(budget, 0, now_ns=lambda: 0),
            )
            self.assertEqual(r, mg.SearchResult(completion, move))
            self.assertEqual(rng.calls, calls)

    def test_finishes_without_waiting_for_target(self):
        """期限前に全候補完了したら待機せず完了する。

        目標まで探索を引き延ばす誤りを偽時計のまま検出する。
        """
        for policy in CONTROLLED_ONE_PLY_POLICIES:
            with self.subTest(policy=policy):
                rng = RecordingChoice()
                r = mg.search_move(
                    pawns(),
                    policy,
                    rng,
                    SearchControl(SearchBudget(10, 20), 0, now_ns=lambda: 0),
                )
                self.assertEqual(r.completion, mg.SearchCompletion.COMPLETE)
                self.assertEqual(r.move, BoardMove(Square(7, 7), Square(7, 6), False))
                self.assertEqual(len(rng.calls), 1)

    def test_new_search_preserves_position_and_does_not_reuse_result(self):
        """旧三方式とUは元局面を保存し前回の停止と予備手を引き継がない。

        共有結果・制御フラグ・元局面の部分変更を検出する。
        """
        for policy in CONTROLLED_ONE_PLY_POLICIES:
            with self.subTest(policy=policy):
                p = pawns()
                before = snapshot(p)
                c = SearchControl(None, 0)
                c.request_stop()
                first = mg.search_move(p, policy, RecordingChoice(), c)
                self.assertEqual(first.completion, mg.SearchCompletion.INTERRUPTED)
                self.assertEqual(snapshot(p), before)
                p.board.set_piece(Square(2, 7), None)
                before = snapshot(p)
                second = mg.search_move(
                    p, policy, RecordingChoice(), SearchControl(None, 0)
                )
                self.assertEqual(
                    second,
                    mg.SearchResult(
                        mg.SearchCompletion.COMPLETE,
                        BoardMove(Square(7, 7), Square(7, 6), False),
                    ),
                )
                self.assertEqual(snapshot(p), before)

    def test_search_propagates_unexpected_errors(self):
        """採点故障・未知手・不合法手は投了や予備手へ変換しない。

        故障を正常停止へ隠す広い例外捕捉を検出する。
        """
        c = SearchControl(None, 0)
        with patch.object(mg, "material_balance", side_effect=RuntimeError("採点故障")):
            with self.assertRaises(RuntimeError):
                mg.search_move(
                    pawns(), mg.MoveSelectionPolicy.MATERIAL, RecordingChoice(), c
                )
        for move, error in (
            (object(), TypeError),
            (BoardMove(Square(2, 7), Square(2, 5), False), ValueError),
        ):
            with patch.object(
                mg,
                "_legal_moves_controlled",
                return_value=mg.LegalMovesResult(True, (move,)),
            ):
                with self.assertRaises(error):
                    mg.search_move(
                        pawns(), mg.MoveSelectionPolicy.MATERIAL, RecordingChoice(), c
                    )

    def test_suppression_after_evaluation_prevents_final_choice(self):
        """最後の評価から復帰した時の抑制でも抽選せず手を渡さない。

        最終結果生成直前の抑制確認漏れを検出する。
        """
        c = SearchControl(None, 0)
        rng = RecordingChoice()

        def suppress(*args, **kwargs):
            c.request_stop(suppress_response=True)
            return mg.CandidateEvaluation(True, (0, 7))

        with patch.object(mg, "_evaluate_candidate", side_effect=suppress):
            r = mg.search_move(pawns(), mg.MoveSelectionPolicy.MATERIAL, rng, c)
        self.assertEqual(r, mg.SearchResult(mg.SearchCompletion.SUPPRESSED, None))
        self.assertEqual(rng.calls, [])


def three_moves():
    return tuple(BoardMove(Square(f, 7), Square(f, 6), False) for f in (2, 5, 7))


class RecordingChoice:
    """抽選対象を記録し最後の候補を返すテスト用操作。"""

    def __init__(self):
        self.calls = []

    def choice(self, moves):
        self.calls.append(moves)
        return moves[-1]


class ReplyProtectionTests(unittest.TestCase):
    def test_reply_generation_never_borrows_root_protection(self):
        """候補評価の応手生成は一手未確保でも通常停止を保護しない。

        外側の停止確認で隠れる、応手生成への根保護の誤適用を直接観測する。
        """
        p, move, _ = recapture(Side.SENTE)
        after = mg._position_after_move(p, move)
        c = SearchControl(None, 0)
        apply = mg.apply_move
        legal = mg._legal_moves_controlled
        observed = []

        def stop_in_reply(*args, **kwargs):
            apply(*args, **kwargs)
            c.request_stop()

        def record(*args, **kwargs):
            result = legal(*args, **kwargs)
            observed.append(result)
            return result

        with (
            patch.object(mg, "apply_move", side_effect=stop_in_reply),
            patch.object(mg, "_legal_moves_controlled", side_effect=record),
        ):
            result = mg._two_ply_score_controlled(after, Side.SENTE, control=c)
        self.assertFalse(result.completed)
        self.assertIsNone(result.score)
        self.assertEqual(observed, [mg.LegalMovesResult(False, ())])


class PublicControlledGenerationTests(unittest.TestCase):
    def test_public_generation_separates_target_and_protection(self):
        """目標の適用と最初の合法手までの保護を独立に指定する。

        rootへの一括変換や、全生成中ずっと保護する誤りを検出する。
        """
        first = BoardMove(Square(2, 7), Square(2, 6), False)
        for target in (False, True):
            c = SearchControl(SearchBudget(10, 20), 0, now_ns=lambda: 10_000_000)
            r = mg.legal_moves_controlled(pawns(), control=c, include_target=target)
            self.assertEqual(r.completed, not target)
            self.assertEqual(
                r.moves,
                () if target else (first, BoardMove(Square(7, 7), Square(7, 6), False)),
            )
        for protected in (False, True):
            c = SearchControl(None, 0)
            c.request_stop()
            r = mg.legal_moves_controlled(
                pawns(), control=c, protect_first_legal=protected
            )
            self.assertFalse(r.completed)
            self.assertEqual(r.moves, (first,) if protected else ())

    def test_first_legal_finishes_without_later_trials(self):
        """最初の合法手取得は後続候補を調べず、手なしも確定できる。

        全生成への誤委譲や、0予算・通常停止で未確保を投了にする誤りを検出する。
        """
        for zero in (False, True):
            c = SearchControl(SearchBudget(0, 0) if zero else None, 0, now_ns=lambda: 0)
            if not zero:
                c.request_stop()
            original = mg.apply_move
            seen = []

            def observe(*args, seen=seen, original=original, **kwargs):
                seen.append(args[1])
                return original(*args, **kwargs)

            with patch.object(mg, "apply_move", side_effect=observe):
                r = mg.first_legal_move_controlled(
                    pawns(), control=c, protect_first_legal=True
                )
            self.assertTrue(r.completed)
            self.assertEqual(r.moves, (BoardMove(Square(2, 7), Square(2, 6), False),))
            self.assertEqual(seen, [Square(2, 7)])
            empty = mg.first_legal_move_controlled(
                Position(Board(), Side.SENTE), control=c, protect_first_legal=True
            )
            self.assertEqual(empty, mg.LegalMovesResult(True, ()))

    def test_application_result_rejects_inconsistent_state(self):
        """未完了の部分局面と完了なのに局面なしのデータを拒否する。

        bool以外やPosition以外の値の混入も検出する。
        """
        from dataclasses import FrozenInstanceError

        for completed, position in (
            (True, None),
            (False, pawns()),
            (1, pawns()),
            (True, object()),
        ):
            with self.subTest(completed=completed), self.assertRaises(ValueError):
                mg.MoveApplicationResult(completed, position)
        value = mg.MoveApplicationResult(False, None)
        with self.assertRaises(FrozenInstanceError):
            value.position = pawns()

    def test_public_first_protection_reaches_pawn_defense(self):
        """最初の歩打ちの防御調査へ保護を伝え、抑制は中断する。

        合法側と打ち歩詰め側、先後の対照で保護喪失と不明の合法扱いを検出する。
        """
        for side in Side:
            for mating in (False, True):
                for suppress in (False, True):
                    with self.subTest(side=side, mating=mating, suppress=suppress):
                        p, dest = uchi(side)
                        if not mating:
                            p.board.set_piece(
                                Square(4, 3) if side == Side.SENTE else Square(6, 7),
                                None,
                            )
                        before = snapshot(p)
                        c = SearchControl(None, 0)
                        apply, drop, defense = (
                            mg.apply_move,
                            mg._apply_drop_controlled,
                            mg._has_legal_move_controlled,
                        )

                        def root_move(*args, side=side, apply=apply, **kwargs):
                            if args[0].side_to_move == side:
                                raise ValueError("教材では根の盤上候補を除く")
                            return apply(*args, **kwargs)

                        def root_drop(*args, side=side, dest=dest, drop=drop, **kwargs):
                            if args[0].side_to_move == side and (
                                args[1] != BasicPieceType.PAWN or args[2] != dest
                            ):
                                raise ValueError("教材では対象の歩打ちだけを調べる")
                            return drop(*args, **kwargs)

                        def stop_inside(
                            *args, c=c, suppress=suppress, defense=defense, **kwargs
                        ):
                            c.request_stop(suppress_response=suppress)
                            return defense(*args, **kwargs)

                        with (
                            patch.object(mg, "apply_move", side_effect=root_move),
                            patch.object(
                                mg, "_apply_drop_controlled", side_effect=root_drop
                            ),
                            patch.object(
                                mg,
                                "_has_legal_move_controlled",
                                side_effect=stop_inside,
                            ),
                        ):
                            r = mg.first_legal_move_controlled(
                                p, control=c, protect_first_legal=True
                            )
                        self.assertEqual(r.completed, not suppress)
                        self.assertEqual(
                            r.moves,
                            ()
                            if suppress or mating
                            else (DropMove(BasicPieceType.PAWN, dest),),
                        )
                        self.assertEqual(snapshot(p), before)

    def test_public_application_returns_only_complete_position(self):
        """盤上手・成り・打ちは独立局面、途中停止は局面なしで返す。

        元局面の変更と部分局面の漏出、故障の中断化を検出する。
        """
        from kaname_shogi.sfen import parse_sfen

        for sfen, move in (
            (None, BoardMove(Square(2, 7), Square(2, 6), False)),
            (
                "8k/9/9/7P1/9/9/9/9/K8 b - 1",
                BoardMove(Square(2, 4), Square(2, 3), True),
            ),
            ("8k/9/9/9/9/9/9/9/K8 b P 1", DropMove(BasicPieceType.PAWN, Square(5, 5))),
        ):
            p = pawns() if sfen is None else parse_sfen(sfen).position
            before = snapshot(p)
            r = mg.position_after_move_controlled(
                p, move, control=SearchControl(None, 0)
            )
            self.assertTrue(r.completed)
            self.assertIsNot(r.position, p)
            self.assertNotEqual(snapshot(r.position), before)
            for suppress in (False, True):
                c = SearchControl(None, 0)
                name = (
                    "_apply_drop_unchecked"
                    if isinstance(move, DropMove)
                    else "apply_move"
                )
                original = getattr(mg, name)

                def stop(*args, c=c, suppress=suppress, original=original, **kwargs):
                    result = original(*args, **kwargs)
                    c.request_stop(suppress_response=suppress)
                    return result

                with patch.object(mg, name, side_effect=stop):
                    r = mg.position_after_move_controlled(p, move, control=c)
                self.assertEqual(r, mg.MoveApplicationResult(False, None))
            self.assertEqual(snapshot(p), before)
        for move, error in (
            (object(), TypeError),
            (BoardMove(Square(2, 7), Square(2, 5), False), ValueError),
        ):
            with self.assertRaises(error):
                mg.position_after_move_controlled(
                    pawns(), move, control=SearchControl(None, 0)
                )
        fault = RuntimeError("適用故障")
        with (
            patch.object(mg, "apply_move", side_effect=fault),
            self.assertRaises(RuntimeError) as caught,
        ):
            mg.position_after_move_controlled(
                pawns(),
                BoardMove(Square(2, 7), Square(2, 6), False),
                control=SearchControl(None, 0),
            )
        self.assertIs(caught.exception, fault)
