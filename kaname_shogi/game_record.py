"""対局中の成功した指し手と現在局面を保持する。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from .model import (BasicPieceType, Board, Hand, Piece, PieceType, Position,
                    Side, Square)
from .movegen import apply_drop, apply_move


_HAND_PIECE_TYPES = (
    BasicPieceType.PAWN,
    BasicPieceType.LANCE,
    BasicPieceType.KNIGHT,
    BasicPieceType.SILVER,
    BasicPieceType.GOLD,
    BasicPieceType.BISHOP,
    BasicPieceType.ROOK,
)


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

    def save(self, path: Union[str, Path]) -> None:
        """開始局面と成功手を専用JSONファイルへ保存する。

        引数:
            path: 保存先を表す文字列またはPath。

        戻り値:
            なし（None）。

        例外:
            OSError: 保存先を開けない、または書き込めない場合。

        副作用:
            保存先のファイルを作成または上書きする。JSONへ変換できない状態が
            ある場合は、ファイルを開く前に失敗する。現在局面は保存せず、開始局面
            と履歴から再現できる形にすることで二重管理を避ける。
        """
        payload = _record_to_payload(self)
        with Path(path).open("w", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=False, indent=2)
            output.write("\n")

    @classmethod
    def load(cls, path: Union[str, Path]) -> "GameRecord":
        """専用JSONを検証して、新しい対局記録として読み込む。

        引数:
            path: 読み込むJSONファイルを表す文字列またはPath。

        戻り値:
            開始局面へ履歴を再適用した、新しいGameRecord。

        例外:
            ValueError: JSONの構造・値、または履歴が保存形式や合法手に合わない場合。
            OSError: ファイルを開けない、または読み込めない場合。

        副作用:
            読み込み中に既存のGameRecordを変更しない。新しい記録へ既存の局面操作を
            再適用することで、保存した現在局面との二重管理を避ける。
        """
        with Path(path).open(encoding="utf-8") as source:
            payload = json.load(source)
        initial_position, moves = _payload_to_position_and_moves(payload)
        record = cls(initial_position)
        for move in moves:
            if isinstance(move, RecordedMove):
                record.apply_move(move.source, move.destination,
                                  promote=move.promote)
            else:
                record.apply_drop(move.piece_type, move.destination)
        return record

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


def _record_to_payload(record: GameRecord) -> dict:
    """GameRecordを保存形式のJSON値へ変換する。"""
    return {
        "format": "kaname-shogi-game-record-v1",
        "initial_position": _position_to_payload(record.initial_position),
        "moves": [_move_to_payload(move) for move in record.moves],
    }


def _position_to_payload(position: Position) -> dict:
    """局面をJSON保存用の辞書へ変換する。"""
    pieces = []
    for file in range(1, 10):
        for rank in range(1, 10):
            square = Square(file, rank)
            piece = position.board.piece_at(square)
            if piece is None:
                continue
            pieces.append({
                "file": file,
                "rank": rank,
                "piece_type": piece.piece_type.name,
                "side": piece.side.name,
            })

    hands = {}
    for side_name, hand in (("SENTE", position.sente_hand),
                            ("GOTE", position.gote_hand)):
        hand_payload = {}
        for piece_type in _HAND_PIECE_TYPES:
            count = hand.count(piece_type)
            if count:
                hand_payload[piece_type.name] = count
        hands[side_name] = hand_payload

    return {
        "side_to_move": position.side_to_move.name,
        "pieces": pieces,
        "hands": hands,
    }


def _move_to_payload(move: Union[RecordedMove, RecordedDrop]) -> dict:
    """履歴の一手をJSON保存用の辞書へ変換する。"""
    if isinstance(move, RecordedMove):
        return {
            "kind": "move",
            "source": {"file": move.source.file, "rank": move.source.rank},
            "destination": {
                "file": move.destination.file,
                "rank": move.destination.rank,
            },
            "promote": move.promote,
        }
    if isinstance(move, RecordedDrop):
        return {
            "kind": "drop",
            "piece_type": move.piece_type.name,
            "destination": {
                "file": move.destination.file,
                "rank": move.destination.rank,
            },
        }
    raise ValueError("未知の指し手履歴です")


def _payload_to_position_and_moves(payload: object) -> tuple:
    """JSON値を検証し、開始局面と履歴へ変換する。"""
    _require_dict(payload, "トップレベル")
    _require_keys(payload, {"format", "initial_position", "moves"},
                  "トップレベル")
    if payload["format"] != "kaname-shogi-game-record-v1":
        raise ValueError("JSON形式識別子が正しくありません")
    position = _payload_to_position(payload["initial_position"])
    moves_payload = payload["moves"]
    if not isinstance(moves_payload, list):
        raise ValueError("movesは配列で指定してください")
    moves = [_payload_to_move(move) for move in moves_payload]
    return position, moves


def _payload_to_position(payload: object) -> Position:
    """JSONの開始局面を検証してPositionへ変換する。"""
    _require_dict(payload, "initial_position")
    _require_keys(payload, {"side_to_move", "pieces", "hands"},
                  "initial_position")
    side = _enum_from_name(Side, payload["side_to_move"], "手番")

    pieces_payload = payload["pieces"]
    if not isinstance(pieces_payload, list):
        raise ValueError("piecesは配列で指定してください")
    board = Board()
    seen_squares = set()
    for piece_payload in pieces_payload:
        _require_dict(piece_payload, "盤上の駒")
        _require_keys(piece_payload,
                      {"file", "rank", "piece_type", "side"}, "盤上の駒")
        square = _payload_to_square(piece_payload, "盤上の駒",
                                    allow_extra=True)
        if square in seen_squares:
            raise ValueError("同じマスに複数の駒を指定できません")
        seen_squares.add(square)
        piece_type = _enum_from_name(PieceType, piece_payload["piece_type"],
                                     "盤上の駒種")
        piece_side = _enum_from_name(Side, piece_payload["side"],
                                     "盤上の所有者")
        board.set_piece(square, Piece(piece_type, piece_side))

    hands_payload = payload["hands"]
    _require_dict(hands_payload, "hands")
    _require_keys(hands_payload, {"SENTE", "GOTE"}, "hands")
    hands = {}
    for side_name, hand_payload in hands_payload.items():
        _require_dict(hand_payload, f"{side_name}の持ち駒")
        hand = Hand()
        for name, count in hand_payload.items():
            piece_type = _enum_from_name(BasicPieceType, name,
                                         f"{side_name}の持ち駒")
            if piece_type == BasicPieceType.KING:
                raise ValueError("玉は持ち駒に指定できません")
            if type(count) is not int or count <= 0:
                raise ValueError("持ち駒の枚数は1以上の整数で指定してください")
            hand.add(piece_type)
            for _ in range(count - 1):
                hand.add(piece_type)
        hands[side_name] = hand

    return Position(board, side, hands["SENTE"], hands["GOTE"])


def _payload_to_move(payload: object) -> Union[RecordedMove, RecordedDrop]:
    """JSONの履歴一件を検証してRecordedMoveまたはRecordedDropへ変換する。"""
    _require_dict(payload, "履歴")
    kind = payload.get("kind")
    if kind == "move":
        _require_keys(payload,
                      {"kind", "source", "destination", "promote"}, "盤上移動")
        promote = payload["promote"]
        if type(promote) is not bool:
            raise ValueError("promoteは真偽値で指定してください")
        return RecordedMove(
            _payload_to_square(payload["source"], "出発マス"),
            _payload_to_square(payload["destination"], "到着マス"),
            promote,
        )
    if kind == "drop":
        _require_keys(payload, {"kind", "piece_type", "destination"}, "駒打ち")
        piece_type = _enum_from_name(BasicPieceType, payload["piece_type"],
                                     "駒打ちの駒種")
        if piece_type == BasicPieceType.KING:
            raise ValueError("玉は駒打ちに指定できません")
        return RecordedDrop(piece_type,
                            _payload_to_square(payload["destination"], "打ち先"))
    raise ValueError("履歴の操作種別が正しくありません")


def _payload_to_square(payload: object, label: str,
                       *, allow_extra: bool = False) -> Square:
    """JSONの筋・段を厳密に検証してSquareへ変換する。"""
    _require_dict(payload, label)
    if allow_extra:
        if not {"file", "rank"}.issubset(payload):
            raise ValueError(f"{label}の項目が正しくありません")
    else:
        _require_keys(payload, {"file", "rank"}, label)
    file = payload["file"]
    rank = payload["rank"]
    if type(file) is not int or type(rank) is not int:
        raise ValueError(f"{label}の筋・段は整数で指定してください")
    try:
        return Square(file, rank)
    except ValueError as error:
        raise ValueError(f"{label}の筋・段が盤外です") from error


def _require_dict(value: object, label: str) -> None:
    """値がJSONオブジェクトであることを検証する。"""
    if not isinstance(value, dict):
        raise ValueError(f"{label}はオブジェクトで指定してください")


def _require_keys(value: dict, expected: set, label: str) -> None:
    """JSONオブジェクトのキー集合が期待どおりであることを検証する。"""
    if set(value) != expected:
        raise ValueError(f"{label}の項目が正しくありません")


def _enum_from_name(enum_type: object, value: object, label: str):
    """列挙型の固定名を検証して値へ変換する。"""
    if not isinstance(value, str):
        raise ValueError(f"{label}の名前が正しくありません")
    try:
        return enum_type[value]
    except KeyError as error:
        raise ValueError(f"{label}の名前が正しくありません") from error
