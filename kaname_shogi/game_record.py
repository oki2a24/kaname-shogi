"""対局中の成功した指し手と現在局面を保持する。"""

from __future__ import annotations

from dataclasses import dataclass

from .model import BasicPieceType, Position, Square
from .movegen import apply_drop, apply_move


@dataclass(frozen=True)
class RecordedMove:
    """盤上移動（出発・到着・成り指定）を表す変更不可の履歴データ。"""

    source: Square
    destination: Square
    promote: bool


@dataclass(frozen=True)
class RecordedDrop:
    """駒打ち（基本駒種・到着）を表す変更不可の履歴データ。"""

    piece_type: BasicPieceType
    destination: Square


class GameRecord:
    """開始局面から成功した指し手の経過を保持する可変の対局記録。

    引数:
        initial_position: 対局開始時の局面。内部で複製するため、渡した局面は
            記録と共有されない。

    戻り値:
        `GameRecord` は開始局面、現在局面、成功した指し手列を保持するデータであり、
        `apply_move` / `apply_drop` は戻り値を持たない操作である。

    副作用:
        適用操作が成功した場合だけ内部の現在局面と履歴を変更する。公開プロパティ
        から返す局面は複製なので、呼び出し側の変更で記録内部は変化しない。

    前提条件:
        指し手の合法性、手番、成り、駒取り、駒打ちの規則は既存の
        `movegen.apply_move` / `movegen.apply_drop` に委譲する。失敗時に既存操作が
        `ValueError` を送出した場合は履歴へ追加しない。局面責務に履歴を混在させず、
        将来の再現処理が開始局面と指し手列を明示的に扱えるようにするための型である。
    """

    def __init__(self, initial_position: Position) -> None:
        """開始局面を複製し、空の履歴を持つ対局記録を作る。"""
        self._initial_position = initial_position.copy()
        self._current_position = initial_position.copy()
        self._moves: list[RecordedMove | RecordedDrop] = []

    @property
    def moves(self) -> tuple[RecordedMove | RecordedDrop, ...]:
        """成功した盤上移動・駒打ちを順番どおりに返す読み取り値。"""
        return tuple(self._moves)

    @property
    def current_position(self) -> Position:
        """現在局面の独立複製を返す読み取り操作。"""
        return self._current_position.copy()

    @property
    def initial_position(self) -> Position:
        """開始局面の独立複製を返す読み取り操作。"""
        return self._initial_position.copy()

    def position_at(self, move_count: int) -> Position:
        """開始局面から指定手数を再適用した、独立した局面を作る。

        引数:
            move_count: 開始局面から適用する履歴の手数。0は開始局面、履歴長は
                現在局面を表す。

        戻り値:
            指定手数までの指し手を開始局面へ適用した新しい `Position`。

        例外:
            ValueError: 手数が整数でない、負数、または現在の履歴長を超える場合。

        副作用:
            記録内部の開始局面・現在局面・履歴を変更しない。履歴を再適用して
            過去局面を作ることで、各手後の局面を全件保持せずに再現範囲を提供する。
        """
        if type(move_count) is not int or not 0 <= move_count <= len(self._moves):
            raise ValueError("手数は履歴の範囲で指定してください")

        position = self._initial_position.copy()
        for move in self._moves[:move_count]:
            if isinstance(move, RecordedMove):
                apply_move(position, move.source, move.destination,
                           promote=move.promote)
            else:
                apply_drop(position, move.piece_type, move.destination)
        return position

    def apply_move(self, source: Square, destination: Square,
                   *, promote: bool = False) -> None:
        """合法な盤上移動を現在局面へ適用し、成功後だけ履歴へ追加する。

        引数:
            source: 出発マスの筋・段を表す値。
            destination: 到着マスの筋・段を表す値。
            promote: 成りを選択するならTrue。

        戻り値:
            なし（None）。

        副作用:
            成功時だけ現在局面と履歴を変更する。失敗時は既存の
            `movegen.apply_move` が局面を変更せず `ValueError` を送出する。

        盤上移動の値を先に履歴へ追加せず、合法性判定と局面更新に成功した後で
        追加することで、失敗した入力を棋譜へ混ぜない。
        """
        apply_move(self._current_position, source, destination, promote=promote)
        self._moves.append(RecordedMove(source, destination, promote))

    def apply_drop(self, piece_type: BasicPieceType,
                   destination: Square) -> None:
        """合法な駒打ちを現在局面へ適用し、成功後だけ履歴へ追加する。

        引数:
            piece_type: 打つ持ち駒の基本駒種を表す値。
            destination: 打ち先の筋・段を表す値。

        戻り値:
            なし（None）。

        副作用:
            成功時だけ現在局面と履歴を変更する。失敗時は既存の
            `movegen.apply_drop` が局面を変更せず `ValueError` を送出する。

        駒打ちは盤上移動と異なる履歴データで保持し、既存の二歩・行き所のない駒・
        王手放置・打ち歩詰めの検証を重複実装しない。
        """
        apply_drop(self._current_position, piece_type, destination)
        self._moves.append(RecordedDrop(piece_type, destination))
