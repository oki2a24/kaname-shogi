"""千日手履歴の位置同一性と終局判定を検証する。"""

import unittest

from kaname_shogi.game_record import GameRecord
from kaname_shogi.model import (
    BasicPieceType,
    Board,
    Piece,
    PieceType,
    Position,
    Side,
    Square,
)

try:
    from kaname_shogi.repetition import RepetitionOutcomeKind, RepetitionTracker
except ModuleNotFoundError as error:
    if error.name != "kaname_shogi.repetition":
        raise
    RepetitionOutcomeKind = RepetitionTracker = None


class RepetitionTrackerTests(unittest.TestCase):
    def _require_implementation(self):
        """未実装部品を読み込みエラーではなく機能不足として失敗させる。"""
        self.assertIsNotNone(RepetitionTracker, "千日手判定部品が未実装です")
        self.assertIsNotNone(RepetitionOutcomeKind, "千日手結果の種類が未実装です")

    @staticmethod
    def _initial_position():
        """合法循環を作れる玉二枚・先手飛車の開始局面を作る。"""
        board = Board()
        board.set_piece(Square(9, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(5, 1), Piece(PieceType.KING, Side.GOTE))
        board.set_piece(Square(4, 9), Piece(PieceType.ROOK, Side.SENTE))
        return Position(board, Side.SENTE)

    @staticmethod
    def _ordinary_cycle():
        """双方の玉が安全な通常循環を筋・段の着手列で返す。"""
        return (
            (Square(4, 9), Square(4, 8)),
            (Square(5, 1), Square(6, 1)),
            (Square(4, 8), Square(4, 9)),
            (Square(6, 1), Square(5, 1)),
        )

    @staticmethod
    def _checking_cycle():
        """先手飛車が毎回後手玉へ王手をかける合法循環を返す。"""
        return (
            (Square(4, 9), Square(5, 9)),
            (Square(5, 1), Square(4, 1)),
            (Square(5, 9), Square(4, 9)),
            (Square(4, 1), Square(5, 1)),
        )

    def _record_after_cycles(self, cycle, count):
        """開始局面へ指定循環を実着手し、棋譜として返す。"""
        record = GameRecord(self._initial_position())
        for _ in range(count):
            for source, destination in cycle:
                record.apply_move(source, destination)
        return record

    def test_repetition_key_includes_board_hands_and_turn(self):
        """盤上の駒・双方の持ち駒・手番を局面同一性へ含める。

        いずれかの項目を位置キーから外して複数の異なる局面を同一視する誤りを、
        駒の種類・所有者・配置位置、双方の持ち駒、手番を単独で変えた局面列で検出する。
        """
        self._require_implementation()
        initial = self._initial_position()
        variants = []

        changed_type = initial.copy()
        changed_type.board.set_piece(Square(4, 9), Piece(PieceType.BISHOP, Side.SENTE))
        variants.append(changed_type)

        changed_owner = initial.copy()
        changed_owner.board.set_piece(Square(4, 9), Piece(PieceType.ROOK, Side.GOTE))
        variants.append(changed_owner)

        changed_square = initial.copy()
        changed_square.board.set_piece(Square(4, 9), None)
        changed_square.board.set_piece(Square(4, 8), Piece(PieceType.ROOK, Side.SENTE))
        variants.append(changed_square)

        changed_sente_hand = initial.copy()
        changed_sente_hand.sente_hand.add(BasicPieceType.PAWN)
        variants.append(changed_sente_hand)

        changed_gote_hand = initial.copy()
        changed_gote_hand.gote_hand.add(BasicPieceType.PAWN)
        variants.append(changed_gote_hand)

        changed_turn = initial.copy()
        changed_turn.side_to_move = Side.GOTE
        variants.append(changed_turn)

        for variant in variants:
            with self.subTest(variant=variant):
                tracker = RepetitionTracker(initial)
                outcome = tracker.current_outcome
                for position in (
                    variant,
                    variant.copy(),
                    variant.copy(),
                    initial.copy(),
                ):
                    outcome = tracker.add_position(position)
                self.assertEqual(outcome.kind, RepetitionOutcomeKind.CONTINUE)

    def test_fourth_ordinary_occurrence_continues(self):
        """4回目の通常出現では終了せず、指し継ぎを案内できる状態にする。

        開始局面を一回目として3循環後に到達する4回目を、即時の千日手終局へ
        誤分類する実装を検出する。
        """
        self._require_implementation()
        record = self._record_after_cycles(self._ordinary_cycle(), 3)

        tracker = RepetitionTracker.from_positions(record.iter_positions())

        self.assertEqual(
            tracker.current_outcome.kind, RepetitionOutcomeKind.FOURFOLD_CONTINUE
        )

    def test_fifth_occurrence_ends_as_repetition(self):
        """打開後に同一局面が再出現した5回目を通常千日手にする。

        初回の4出現だけで恒久的に継続扱いにしたり、別の循環で履歴を消去したり
        する誤りを検出する。
        """
        self._require_implementation()
        record = self._record_after_cycles(self._ordinary_cycle(), 4)

        tracker = RepetitionTracker.from_positions(record.iter_positions())

        self.assertEqual(tracker.current_outcome.kind, RepetitionOutcomeKind.REPETITION)
        self.assertIsNone(tracker.current_outcome.losing_side)

    def test_fourth_occurrence_of_continuous_check_loses(self):
        """4回目の局面まで王手を続けた先手を連続王手負けにする。

        通常千日手へ誤分類したり、王手を受けた側を敗者にしたりする誤りを検出する。
        """
        self._require_implementation()
        record = self._record_after_cycles(self._checking_cycle(), 3)

        tracker = RepetitionTracker.from_positions(record.iter_positions())

        self.assertEqual(
            tracker.current_outcome.kind, RepetitionOutcomeKind.PERPETUAL_CHECK_LOSS
        )
        self.assertEqual(tracker.current_outcome.losing_side, Side.SENTE)

    def test_fourth_occurrence_of_gote_continuous_check_loses(self):
        """後手が連続王手を続けた場合は後手を敗者にする。

        先手の循環だけを正しく処理し、後手の王手を取り違える左右・手番固定の誤りを
        検出する。
        """
        self._require_implementation()
        board = Board()
        board.set_piece(Square(5, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(1, 1), Piece(PieceType.KING, Side.GOTE))
        board.set_piece(Square(6, 1), Piece(PieceType.ROOK, Side.GOTE))
        record = GameRecord(Position(board, Side.GOTE))
        cycle = (
            (Square(6, 1), Square(5, 1)),
            (Square(5, 9), Square(6, 9)),
            (Square(5, 1), Square(6, 1)),
            (Square(6, 9), Square(5, 9)),
        )
        for _ in range(3):
            for source, destination in cycle:
                record.apply_move(source, destination)

        tracker = RepetitionTracker.from_positions(record.iter_positions())

        self.assertEqual(
            tracker.current_outcome.kind, RepetitionOutcomeKind.PERPETUAL_CHECK_LOSS
        )
        self.assertEqual(tracker.current_outcome.losing_side, Side.GOTE)

    def test_fifth_occurrence_checks_latest_four_occurrences(self):
        """5回目では出現2〜5回目の区間を使って連続王手を判定する。

        最初の区間には非王手の先手着手がある一方、直近4出現の区間はすべて先手の
        王手である。古い窓を再利用して通常千日手へ誤分類する実装を検出する。
        """
        self._require_implementation()
        record = self._record_after_cycles(self._ordinary_cycle(), 1)
        for source, destination in self._checking_cycle() * 2:
            record.apply_move(source, destination)
        tracker = RepetitionTracker.from_positions(record.iter_positions())
        self.assertEqual(
            tracker.current_outcome.kind, RepetitionOutcomeKind.FOURFOLD_CONTINUE
        )

        previous_move_count = len(record.moves)
        for source, destination in self._checking_cycle():
            record.apply_move(source, destination)
        new_positions = list(record.iter_positions())[previous_move_count + 1 :]
        for position in new_positions:
            tracker.add_position(position)

        self.assertEqual(
            tracker.current_outcome.kind, RepetitionOutcomeKind.PERPETUAL_CHECK_LOSS
        )
        self.assertEqual(tracker.current_outcome.losing_side, Side.SENTE)

    def test_both_sides_continuous_check_returns_unresolved(self):
        """双方の全着手が王手のとき、勝者を推測しない結果を返す。

        合法棋譜ではない両玉同時王手の制御局面を使い、双方該当を片側負けや通常
        千日手へ変換する誤分類を検出する。
        """
        self._require_implementation()
        board = Board()
        board.set_piece(Square(9, 9), Piece(PieceType.KING, Side.SENTE))
        board.set_piece(Square(1, 1), Piece(PieceType.KING, Side.GOTE))
        board.set_piece(Square(1, 9), Piece(PieceType.ROOK, Side.SENTE))
        board.set_piece(Square(9, 1), Piece(PieceType.ROOK, Side.GOTE))
        initial = Position(board, Side.SENTE)
        tracker = RepetitionTracker(initial)
        outcome = tracker.current_outcome

        for side_to_move in (Side.GOTE, Side.SENTE) * 3:
            position = initial.copy()
            position.side_to_move = side_to_move
            outcome = tracker.add_position(position)

        self.assertEqual(
            outcome.kind,
            RepetitionOutcomeKind.UNRESOLVED_DOUBLE_PERPETUAL_CHECK,
        )
        self.assertIsNone(outcome.losing_side)

    def test_add_position_after_terminal_raises(self):
        """終局判定済みの履歴には局面を追加できない。

        連続王手負け後に同じトラッカーを再利用して判定状態を書き換える誤りを検出する。
        """
        self._require_implementation()
        record = self._record_after_cycles(self._checking_cycle(), 3)
        tracker = RepetitionTracker.from_positions(record.iter_positions())

        with self.assertRaisesRegex(ValueError, "終局"):
            tracker.add_position(record.current_position)

    def test_from_positions_rejects_moves_after_terminal(self):
        """千日手成立後にも位置が続く履歴の再構成を拒否する。

        過去棋譜の終局後の手を黙認し、読込時に不正な対局を再開する誤りを検出する。
        """
        self._require_implementation()
        record = self._record_after_cycles(self._checking_cycle(), 4)

        with self.assertRaisesRegex(ValueError, "終局"):
            RepetitionTracker.from_positions(record.iter_positions())

    def test_from_positions_rejects_empty_history(self):
        """開始局面がない空履歴を再構成できない。

        初期局面の欠落を空の継続状態として扱う誤りを検出する。
        """
        self._require_implementation()
        with self.assertRaisesRegex(ValueError, "開始局面"):
            RepetitionTracker.from_positions(iter(()))

    def test_from_positions_reconstructs_outcome(self):
        """棋譜の開始局面と全成功手から終局結果を再構成する。

        同じ局面を再現できても反復判定が読込履歴へ引き継がれない誤りを検出する。
        """
        self._require_implementation()
        record = self._record_after_cycles(self._ordinary_cycle(), 4)

        tracker = RepetitionTracker.from_positions(record.iter_positions())

        self.assertEqual(tracker.current_outcome.kind, RepetitionOutcomeKind.REPETITION)


if __name__ == "__main__":
    unittest.main()
