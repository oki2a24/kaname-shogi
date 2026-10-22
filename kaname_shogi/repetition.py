"""実着手で生じた局面履歴から千日手を判定する。"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto

from .model import BasicPieceType, Position, Side, Square
from .movegen import is_in_check

_HAND_PIECE_TYPES = (
    BasicPieceType.PAWN,
    BasicPieceType.LANCE,
    BasicPieceType.KNIGHT,
    BasicPieceType.SILVER,
    BasicPieceType.GOLD,
    BasicPieceType.BISHOP,
    BasicPieceType.ROOK,
)


class RepetitionOutcomeKind(Enum):
    """反復履歴の継続・終局・未裁定を表す種類。"""

    CONTINUE = auto()
    FOURFOLD_CONTINUE = auto()
    REPETITION = auto()
    PERPETUAL_CHECK_LOSS = auto()
    UNRESOLVED_DOUBLE_PERPETUAL_CHECK = auto()


@dataclass(frozen=True)
class RepetitionOutcome:
    """反復判定の種類と、連続王手負けがある場合の敗者側を表す値。

    引数:
        kind: 継続・通常千日手・連続王手負け・未裁定のいずれか。
        losing_side: 連続王手負けが一方に決まる場合の敗者。その他はNone。

    戻り値:
        判定内容を保持する変更不可の値。

    副作用:
        なし。盤面や履歴の状態は変更しない。

    前提条件:
        `losing_side` は `PERPETUAL_CHECK_LOSS` でのみ値を持ち、双方連続王手や
        通常千日手から勝者を推測しない。結果の種類と敗者を分けて扱うための値である。
    """

    kind: RepetitionOutcomeKind
    losing_side: Side | None = None


class RepetitionTracker:
    """成功した一手後の局面列を記録し、千日手を判定する。

    引数:
        initial_position: 対局開始局面。位置キーと出現1回目の履歴に使う。

    戻り値:
        対局の実着手後だけを受け取る反復判定器。

    副作用:
        局面キーごとの最新出現位置と、各実着手の移動側・王手有無を内部に記録する。
        渡された局面そのものは変更しない。

    前提条件:
        追加する `Position` は、直前に成功した一手の後の局面である。探索中の仮想局面
        や失敗した指し手を渡さず、棋譜の開始局面から同じ一局の順に追加する。81マス・
        双方の持ち駒・手番を完全比較し、ハッシュ衝突で同一局面を誤認しない。
    """

    def __init__(self, initial_position: Position) -> None:
        """開始局面を1回目として履歴判定を初期化する。"""
        self._occurrences: dict[tuple, deque[int]] = {}
        self._occurrence_counts: dict[tuple, int] = {}
        self._move_checks: list[tuple[Side, bool]] = []
        self._position_count = 1
        self._outcome = RepetitionOutcome(RepetitionOutcomeKind.CONTINUE)
        key = self._position_key(initial_position)
        self._occurrences[key] = deque((0,), maxlen=4)
        self._occurrence_counts[key] = 1

    @property
    def current_outcome(self) -> RepetitionOutcome:
        """最後に追加した局面への判定結果を返す読み取り値。"""
        return self._outcome

    def add_position(self, position: Position) -> RepetitionOutcome:
        """成功した一手後の局面を追加し、その時点の反復判定を返す。

        引数:
            position: 成功手直後の局面。次の手番側が王手中なら直前の手を王手として記録。

        戻り値:
            継続、4回出現後の指し継ぎ、通常千日手、連続王手負け、双方連続王手の
            未裁定のいずれかを表す `RepetitionOutcome`。

        例外:
            ValueError: 千日手終局後にさらに局面を追加した場合。

        副作用:
            局面キーの出現数と最新4出現位置、実着手の王手履歴、現在の判定結果を更新する。
            位置キーには棋譜上の手数を含めず、同一局面の出現区間だけで連続王手を調べる。
        """
        if self._is_terminal(self._outcome.kind):
            raise ValueError("終局後に局面を追加できません")

        mover = Side.GOTE if position.side_to_move is Side.SENTE else Side.SENTE
        gave_check = is_in_check(position.board, position.side_to_move)
        self._move_checks.append((mover, gave_check))
        position_index = self._position_count
        self._position_count += 1

        key = self._position_key(position)
        occurrences = self._occurrences.setdefault(key, deque(maxlen=4))
        occurrences.append(position_index)
        occurrence_count = self._occurrence_counts.get(key, 0) + 1
        self._occurrence_counts[key] = occurrence_count

        if occurrence_count < 4:
            self._outcome = RepetitionOutcome(RepetitionOutcomeKind.CONTINUE)
        else:
            self._outcome = self._classify_occurrence_window(
                occurrences, occurrence_count
            )
        return self._outcome

    @classmethod
    def from_positions(cls, positions: Iterable[Position]) -> RepetitionTracker:
        """開始局面と成功手後の局面列から反復履歴を再構成する。

        引数:
            positions: 開始局面を先頭にし、以降は一手ごとの直後局面を順に返す反復可能値。

        戻り値:
            全履歴を再判定した新しい `RepetitionTracker`。

        例外:
            ValueError: 局面列が空、または千日手終局後にも局面が続く場合。

        副作用:
            入力反復子から局面を一方向に読む。入力局面と既存棋譜を変更しない。
            保存形式へ結果欄を追加せず、開始局面と成功手から復元するための操作である。
        """
        iterator = iter(positions)
        try:
            initial_position = next(iterator)
        except StopIteration as error:
            raise ValueError("履歴には開始局面が必要です") from error

        tracker = cls(initial_position)
        for position in iterator:
            tracker.add_position(position)
        return tracker

    def _classify_occurrence_window(
        self, occurrences: deque[int], occurrence_count: int
    ) -> RepetitionOutcome:
        """出現4回目の初区間または最新4出現間の王手列を分類する。"""
        start_index = occurrences[0]
        end_index = occurrences[-1]
        checking_sides = []
        for side in Side:
            checks = [
                gave_check
                for mover, gave_check in self._move_checks[start_index:end_index]
                if mover is side
            ]
            if checks and all(checks):
                checking_sides.append(side)

        if len(checking_sides) == 2:
            return RepetitionOutcome(
                RepetitionOutcomeKind.UNRESOLVED_DOUBLE_PERPETUAL_CHECK
            )
        if len(checking_sides) == 1:
            return RepetitionOutcome(
                RepetitionOutcomeKind.PERPETUAL_CHECK_LOSS, checking_sides[0]
            )
        if occurrence_count == 4:
            return RepetitionOutcome(RepetitionOutcomeKind.FOURFOLD_CONTINUE)
        return RepetitionOutcome(RepetitionOutcomeKind.REPETITION)

    @staticmethod
    def _position_key(position: Position) -> tuple:
        """棋譜手数を含めず、盤・双方の持ち駒・手番を全値比較できるキーへ写す。"""
        board = tuple(
            (
                piece.piece_type,
                piece.side,
            )
            if (piece := position.board.piece_at(Square(file, rank))) is not None
            else None
            for file in range(1, 10)
            for rank in range(1, 10)
        )
        hands = tuple(
            position.sente_hand.count(piece_type) for piece_type in _HAND_PIECE_TYPES
        ) + tuple(
            position.gote_hand.count(piece_type) for piece_type in _HAND_PIECE_TYPES
        )
        return board, hands, position.side_to_move

    @staticmethod
    def _is_terminal(kind: RepetitionOutcomeKind) -> bool:
        """継続不能となる判定種類か返す。"""
        return kind in {
            RepetitionOutcomeKind.REPETITION,
            RepetitionOutcomeKind.PERPETUAL_CHECK_LOSS,
            RepetitionOutcomeKind.UNRESOLVED_DOUBLE_PERPETUAL_CHECK,
        }
