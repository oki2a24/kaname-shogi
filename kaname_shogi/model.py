"""筋・段で扱う駒・盤面・持ち駒・局面と、平手の初期配置を定義する。

呼び出し側は９九などの筋・段で操作し、保存用の添字を意識しない。
数学のxyは学習時の補助だったため、公開インターフェースには導入しない。
不変の値（Square・Piece）と可変の状態（Board・Position）を分ける。
表示・入力・合法手判定はこのモジュールの現在の責務に含めない。

設計と背景：docs/design/01-board-and-initial-position.md、
docs/learning/04-first-implementation-design.md。
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class Side(Enum):
    """駒の所有者または手番を表す先手・後手の区別。

    SENTEは先手、GOTEは後手。駒の色ではなく学習済みの用語で命名する。
    列挙値の数値は内部用で、USI・SFENの値として出力しない。
    """

    SENTE = auto()
    GOTE = auto()


class PieceType(Enum):
    """成る前の基本8種類。所有者と表示名はこの型に含めない。

    玉と王は同じKINGとして扱う。成り状態は必要な実装段階で追加する。
    auto()の数値を外部形式や永続化の識別子として使用しない。
    """

    KING = auto()    # 玉将・王将（玉・王）
    ROOK = auto()    # 飛車（飛）
    BISHOP = auto()  # 角行（角）
    GOLD = auto()    # 金将（金）
    SILVER = auto()  # 銀将（銀）
    KNIGHT = auto()  # 桂馬（桂）
    LANCE = auto()   # 香車（香）
    PAWN = auto()    # 歩兵（歩）


@dataclass(frozen=True)
class Square:
    """盤上の一マスを、変更不可の筋・段の組として表す。

    引数:
        file: 筋（1〜9）。先手視点で右端が1、左端が9。
        rank: 段（1〜9）。先手視点で上端が1、下端が9。

    例: Square(file=9, rank=9) は９九、Square(7, 6) は７六。
    不正な値は生成時にValueErrorにする。整数と等値でも1.0やTrueは拒否する。
    作成後に位置を変えないことで、参照先が途中で変わることを防ぐ。
    別のマスは新しいSquareで表す。
    """

    file: int
    rank: int

    def __post_init__(self) -> None:
        """dataclassの生成直後に、筋・段の型と盤内の範囲を検証する。"""
        # boolはintの一種だが、将棋の座標としては受け付けない。
        if any(type(value) is not int or not 1 <= value <= 9
               for value in (self.file, self.rank)):
            raise ValueError("筋・段は1〜9の整数で指定してください")

    def to_index(self) -> int:
        """保存用の0〜80の添字を返す。元の座標は変更しない。

        １一、１二、…、１九、２一、…、９九の順。１一は0、７六は59、
        ９九は80になる。確認したやねうら王・cshogiの実例と同じ番号順だが、
        外部通信の規格ではない。変換をここに集約し、呼び出し側の初期配置・
        表示・ルール処理には添字計算を分散させない。
        """
        return (self.file - 1) * 9 + (self.rank - 1)


@dataclass(frozen=True)
class Piece:
    """駒種piece_typeと所有者sideを組にした、変更不可の値。

    位置はBoardが保持するため、Piece自身には座標や個体番号を持たせない。
    将来、成りや所有者変更を扱う場合は新しいPieceで置き換える方針。
    現在は成り状態を持たない。型注釈は実行時の型検証ではないので、
    呼び出し側はPieceTypeとSideの列挙値を渡す。
    """

    piece_type: PieceType
    side: Side


@dataclass
class Hand:
    """一方が保持する持ち駒の枚数を表す可変のデータ。

    持ち駒は、相手から取って盤上にない駒である。Handは駒台という物理的な
    場所ではなく、歩・香・桂・銀・金・角・飛の各駒種が何枚あるかを表す。
    先手・後手、盤上の位置、手番は保持しない。どちらの持ち駒かはPositionが
    対応付けることで、枚数のデータと局面規則を分ける。
    """

    _counts: dict[PieceType, int] = field(default_factory=dict)

    def _validate_piece_type(self, piece_type: PieceType) -> None:
        """持ち駒にできる基本駒種かを確認し、玉ならValueErrorにする。"""
        if piece_type == PieceType.KING:
            raise ValueError("玉は持ち駒にできません")

    def count(self, piece_type: PieceType) -> int:
        """piece_typeの持ち駒枚数を返し、状態を変更しない。

        引数:
            piece_type: 枚数を調べる玉以外の基本駒種。

        戻り値:
            その駒種の枚数。まだ一枚もなければ0。

        例外:
            ValueError: 玉を指定した場合。玉は取って持ち駒にする駒ではない。

        countは枚数を読む操作であり、持ち駒や局面を変更しない。駒打ちの可否は
        将来の別の操作で扱うため、ここでは判定しない。
        """
        self._validate_piece_type(piece_type)
        return self._counts.get(piece_type, 0)

    def add(self, piece_type: PieceType) -> None:
        """piece_typeを1枚加え、持ち駒を変更する。

        引数:
            piece_type: 加える玉以外の基本駒種。

        戻り値:
            なし（None）。成功時は指定した駒種の枚数だけを1増やす。

        例外:
            ValueError: 玉を指定した場合。失敗時は枚数を変更しない。

        addは枚数を増やす操作であり、駒がどちらの側のものかは判断しない。
        Positionが駒取りを適用するときに、指した側のHandを選ぶ。
        """
        self._validate_piece_type(piece_type)
        self._counts[piece_type] = self.count(piece_type) + 1


class Board:
    """81マスの配置だけを保持する可変の盤。手番はPositionの責務。

    駒はPiece、空マスはNone。呼び出し側はpiece_at/set_pieceとSquareで
    操作し、内部の_cellsには直接触れない。保存順は筋ごと、表示順は段ごと
    なので、リストをそのまま画面の行として解釈しない。
    """

    def __init__(self) -> None:
        """全マスが空の盤を作る。リストは盤ごとに新しく確保する。

        [None] * 81は不変のNoneを並べるだけで、可変な行の共有は起こらない。
        平手の40枚が必要ならcreate_initial_positionを使う。
        """
        self._cells: list[Optional[Piece]] = [None] * 81

    def piece_at(self, square: Square) -> Optional[Piece]:
        """squareの駒を返し、空ならNoneを返す。盤面は変更しない。

        引数は検証済みのSquare。例: board.piece_at(Square(9, 9))。
        Pieceは不変なので、その値を複製せず返す。
        """
        return self._cells[square.to_index()]

    def set_piece(self, square: Square, piece: Optional[Piece]) -> None:
        """squareの内容をpieceで上書きする。Noneなら空にし、戻り値はない。

        引数はSquareとPieceまたはNone。既存の駒もそのまま置き換える。
        初期配置を組み立てるための操作であり、駒の移動・駒取り・手番変更・
        合法性の検証は行わない。これらを暗黙に追加すると配置と対局進行が
        混ざるため、将来の指し手適用は別の責務として設計する。
        """
        self._cells[square.to_index()] = piece


@dataclass
class Position:
    """盤面board、手番、先後それぞれの持ち駒を保持する可変の局面。

    渡されたBoardをそのまま保持し、コピーはしない。同じBoardを二つの
    Positionに渡すと盤面も共有する。独立した開始局面は生成関数で作る。
    sente_handは先手、gote_handは後手が保持する持ち駒のデータであり、各既定値は
    新しいHandを作るため別の局面や側と共有しない。手番の設定だけでは盤面・
    持ち駒は変わらない。持ち駒を盤へ打つ操作、手数・履歴は未実装で、現在の
    情報だけでSFENや対局全体を表せるとはしない。
    """

    board: Board
    side_to_move: Side
    sente_hand: Hand = field(default_factory=Hand)
    gote_hand: Hand = field(default_factory=Hand)


def create_initial_position() -> Position:
    """平手の40枚と先手の手番を持つ、新しいPositionを返す。

    引数は不要。呼び出すたびに新しいBoardを作り、既存局面を変更しない。
    各側20枚。先手は九段の最奥列・七段の歩、後手は一段・三段に配置する。
    飛角は先手８八の角・２八の飛、後手８二の飛・２二の角。
    対称な最奥列と歩は繰り返し、取り違えやすい飛角は筋・段を明記する。

    配置の根拠: docs/knowledge/03-initial-setup-and-coordinates.md、
    https://www.shogi.or.jp/knowledge/shogi/01.php
    """
    board = Board()
    back_rank = (
        PieceType.LANCE, PieceType.KNIGHT, PieceType.SILVER,
        PieceType.GOLD, PieceType.KING, PieceType.GOLD,
        PieceType.SILVER, PieceType.KNIGHT, PieceType.LANCE,
    )
    for side, home_rank, pawn_rank in [(Side.SENTE, 9, 7), (Side.GOTE, 1, 3)]:
        for file, piece_type in enumerate(back_rank, start=1):
            board.set_piece(Square(file, home_rank), Piece(piece_type, side))
            board.set_piece(Square(file, pawn_rank), Piece(PieceType.PAWN, side))

    # 飛角は先後で筋が異なるため、学習済みの筋・段を明記する。
    board.set_piece(Square(8, 8), Piece(PieceType.BISHOP, Side.SENTE))
    board.set_piece(Square(2, 8), Piece(PieceType.ROOK, Side.SENTE))
    board.set_piece(Square(8, 2), Piece(PieceType.ROOK, Side.GOTE))
    board.set_piece(Square(2, 2), Piece(PieceType.BISHOP, Side.GOTE))
    return Position(board, Side.SENTE)
