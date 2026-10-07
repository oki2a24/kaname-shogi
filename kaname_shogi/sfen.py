"""将棋局面とSFEN文字列の変換を行う。"""

from dataclasses import dataclass

from .model import (BasicPieceType, Board, Hand, Piece, PieceType, Position,
                    Side, Square)


_UNPROMOTED_PIECES = {
    "K": PieceType.KING,
    "R": PieceType.ROOK,
    "B": PieceType.BISHOP,
    "G": PieceType.GOLD,
    "S": PieceType.SILVER,
    "N": PieceType.KNIGHT,
    "L": PieceType.LANCE,
    "P": PieceType.PAWN,
}
_PROMOTED_PIECES = {
    "R": PieceType.DRAGON,
    "B": PieceType.HORSE,
    "S": PieceType.PRO_SILVER,
    "N": PieceType.PRO_KNIGHT,
    "L": PieceType.PRO_LANCE,
    "P": PieceType.PRO_PAWN,
}
_PIECE_SYMBOLS = {
    PieceType.KING: "K",
    PieceType.ROOK: "R",
    PieceType.BISHOP: "B",
    PieceType.GOLD: "G",
    PieceType.SILVER: "S",
    PieceType.KNIGHT: "N",
    PieceType.LANCE: "L",
    PieceType.PAWN: "P",
    PieceType.DRAGON: "+R",
    PieceType.HORSE: "+B",
    PieceType.PRO_SILVER: "+S",
    PieceType.PRO_KNIGHT: "+N",
    PieceType.PRO_LANCE: "+L",
    PieceType.PRO_PAWN: "+P",
}
_HAND_PIECES = (
    ("R", BasicPieceType.ROOK),
    ("B", BasicPieceType.BISHOP),
    ("G", BasicPieceType.GOLD),
    ("S", BasicPieceType.SILVER),
    ("N", BasicPieceType.KNIGHT),
    ("L", BasicPieceType.LANCE),
    ("P", BasicPieceType.PAWN),
)


@dataclass(frozen=True)
class SfenPosition:
    """SFEN由来の局面と1始まりの手数を組にしたデータ。

    引数:
        position: 盤面・手番・先後の持ち駒を持つ局面。
        move_number: SFENの1始まりの手数。

    前提条件:
        move_numberは1以上の整数。positionは保持した参照を共有し、複製しない。

    生成時に局面を変更せず、手数と局面を別の値として組み合わせる。
    Positionは盤面・手番・持ち駒を表し、対局の手数や履歴を持たないため、
    SFENの手数はこの形式専用の結果に分けて保持する。
    """

    position: Position
    move_number: int

    def __post_init__(self) -> None:
        """SFEN手数が1以上の整数であることを確認する。"""
        if type(self.move_number) is not int or self.move_number < 1:
            raise ValueError("SFEN手数は1以上の整数で指定してください")


def parse_sfen(sfen: str) -> SfenPosition:
    """SFEN文字列を読み込み、盤面局面と手数を返す。

    引数:
        sfen: 盤面、手番、持ち駒、任意の手数からなるSFEN文字列。

    戻り値:
        Positionと1始まりの手数を組にしたSfenPosition。

    例外:
        ValueError: SFENの構文または現在の局面モデルで表現できない値を含む場合。

    盤面や手数を読み込む変換であり、入力文字列や既存局面を変更しない。
    Positionへ手数を混ぜず、SFENのスナップショット情報を分離する。玉の有無や
    二歩などの合法性・到達可能性は調べず、盤面と持ち駒を内部型で表現できるかを
    検証する。
    """
    if not isinstance(sfen, str):
        raise ValueError("SFENは文字列で指定してください")

    fields = sfen.split()
    if len(fields) not in (3, 4):
        raise ValueError("SFENは盤面・手番・持ち駒と任意の手数で指定してください")

    board = _parse_board(fields[0])
    side_to_move = _parse_side_to_move(fields[1])
    sente_hand, gote_hand = _parse_hands(fields[2])
    move_number = _parse_move_number(fields[3]) if len(fields) == 4 else 1
    return SfenPosition(Position(board, side_to_move, sente_hand, gote_hand),
                        move_number)


def format_sfen(sfen_position: SfenPosition) -> str:
    """局面と手数を正規化したSFEN文字列へ書き出す。

    引数:
        sfen_position: 盤面局面と1始まりの手数を持つSFEN専用データ。

    戻り値:
        盤面、手番、持ち駒、手数を含むSFEN文字列。

    例外:
        ValueError: 渡された局面をSFENとして表現できない場合。

    読み取り専用の変換であり、Positionや持ち駒を変更しない。正規化は同じ
    局面を一意で比較しやすい表記にし、解析結果の再出力を安定させる。盤面・
    手番・持ち駒・正の手数がSFENで表現できることを前提にし、問題があれば
    ValueErrorを返す。
    """
    if not isinstance(sfen_position, SfenPosition):
        raise ValueError("SFEN書出しにはSfenPositionを指定してください")
    if not isinstance(sfen_position.position, Position):
        raise ValueError("SFEN局面にはPositionを指定してください")
    if (type(sfen_position.move_number) is not int
            or sfen_position.move_number < 1):
        raise ValueError("SFEN手数は1以上の整数で指定してください")

    position = sfen_position.position
    if position.side_to_move is Side.SENTE:
        side_token = "b"
    elif position.side_to_move is Side.GOTE:
        side_token = "w"
    else:
        raise ValueError("SFEN手番を表現できません")

    board_text = _format_board(position.board)
    hand_text = _format_hands(position.sente_hand, position.gote_hand)
    return f"{board_text} {side_token} {hand_text} {sfen_position.move_number}"


def _parse_board(board_text: str) -> Board:
    """SFEN盤面を9段に分け、9筋から1筋の順に盤へ配置する。"""
    rows = board_text.split("/")
    if len(rows) != 9:
        raise ValueError("SFEN盤面は9段で指定してください")

    board = Board()
    for rank, row in enumerate(rows, start=1):
        file = 9
        index = 0
        previous_was_empty_count = False
        while index < len(row):
            token = row[index]
            if token in "0123456789":
                if token == "0":
                    raise ValueError("SFEN盤面の空きマス数に0は使えません")
                if previous_was_empty_count:
                    raise ValueError("SFEN盤面の連続する空きマス数をまとめてください")
                empty_count = int(token)
                if file - empty_count < 0:
                    raise ValueError("SFEN盤面の段幅が9マスを超えています")
                file -= empty_count
                index += 1
                previous_was_empty_count = True
                continue

            previous_was_empty_count = False
            promoted = token == "+"
            if promoted:
                index += 1
                if index >= len(row):
                    raise ValueError("SFEN盤面の成り記号の後に駒がありません")
                token = row[index]

            symbol = token.upper()
            if symbol not in _UNPROMOTED_PIECES:
                raise ValueError(f"SFEN盤面に不明な駒記号があります: {token}")
            if promoted:
                if symbol not in _PROMOTED_PIECES:
                    raise ValueError(f"SFEN盤面で成れない駒に成り記号があります: {token}")
                piece_type = _PROMOTED_PIECES[symbol]
            else:
                piece_type = _UNPROMOTED_PIECES[symbol]

            if file < 1:
                raise ValueError("SFEN盤面の段幅が9マスを超えています")
            side = Side.SENTE if token.isupper() else Side.GOTE
            board.set_piece(Square(file, rank), Piece(piece_type, side))
            file -= 1
            index += 1

        if file != 0:
            raise ValueError("SFEN盤面の各段は9マスで指定してください")
    return board


def _parse_side_to_move(token: str) -> Side:
    """SFEN手番のb/wを内部の先手・後手へ変換する。"""
    if token == "b":
        return Side.SENTE
    if token == "w":
        return Side.GOTE
    raise ValueError(f"SFEN手番はbまたはwで指定してください: {token}")


def _parse_hands(hand_text: str) -> tuple[Hand, Hand]:
    """SFENの持ち駒欄を先手・後手それぞれのHandへ変換する。"""
    sente_hand, gote_hand = Hand(), Hand()
    if hand_text == "-":
        return sente_hand, gote_hand
    if not hand_text:
        raise ValueError("SFEN持ち駒欄が空です")

    index = 0
    while index < len(hand_text):
        count_start = index
        while index < len(hand_text) and hand_text[index] in "0123456789":
            index += 1
        count_text = hand_text[count_start:index]
        if index >= len(hand_text):
            raise ValueError("SFEN持ち駒の枚数の後に駒記号がありません")

        token = hand_text[index]
        symbol = token.upper()
        hand_piece = dict(_HAND_PIECES).get(symbol)
        if hand_piece is None:
            raise ValueError(f"SFEN持ち駒に不明または表現できない駒があります: {token}")
        try:
            count = int(count_text) if count_text else 1
        except ValueError as error:
            raise ValueError("SFEN持ち駒の枚数を整数として読めません") from error
        if count < 1:
            raise ValueError("SFEN持ち駒の枚数は1以上で指定してください")

        hand = sente_hand if token.isupper() else gote_hand
        for _ in range(count):
            hand.add(hand_piece)
        index += 1
    return sente_hand, gote_hand


def _parse_move_number(token: str) -> int:
    """SFEN手数欄を正の整数へ変換する。"""
    if not token or any(character not in "0123456789" for character in token):
        raise ValueError(f"SFEN手数は正の整数で指定してください: {token}")
    try:
        move_number = int(token)
    except ValueError as error:
        raise ValueError("SFEN手数を整数として読めません") from error
    if move_number < 1:
        raise ValueError("SFEN手数は1以上で指定してください")
    return move_number


def _format_board(board: Board) -> str:
    """盤を段順に走査し、連続する空きマスを一つの数字へまとめる。"""
    rows = []
    for rank in range(1, 10):
        row = []
        empty_count = 0
        for file in range(9, 0, -1):
            piece = board.piece_at(Square(file, rank))
            if piece is None:
                empty_count += 1
                continue
            if empty_count:
                row.append(str(empty_count))
                empty_count = 0
            try:
                symbol = _PIECE_SYMBOLS[piece.piece_type]
            except (AttributeError, KeyError, TypeError) as error:
                raise ValueError("SFEN盤面に表現できない駒があります") from error
            if piece.side is Side.GOTE:
                if symbol.startswith("+"):
                    symbol = "+" + symbol[1].lower()
                else:
                    symbol = symbol.lower()
            elif piece.side is not Side.SENTE:
                raise ValueError("SFEN盤面の駒所有者を表現できません")
            row.append(symbol)
        if empty_count:
            row.append(str(empty_count))
        rows.append("".join(row))
    return "/".join(rows)


def _format_hands(sente_hand: Hand, gote_hand: Hand) -> str:
    """持ち駒を駒種順、先手・後手順で正規化する。"""
    tokens = []
    for hand, is_sente in ((sente_hand, True), (gote_hand, False)):
        for symbol, piece_type in _HAND_PIECES:
            count = hand.count(piece_type)
            if count:
                count_text = str(count) if count > 1 else ""
                piece_symbol = symbol if is_sente else symbol.lower()
                tokens.append(f"{count_text}{piece_symbol}")
    return "".join(tokens) or "-"
