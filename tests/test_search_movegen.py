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
