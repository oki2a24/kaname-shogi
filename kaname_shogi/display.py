"""局面を、人が読むための先手視点の文字列へ変換する。

モデルの保存順や列挙値を表示形式に結び付けない。文字列の生成と出力を
分けることで、端末を介さず全文を検証できる。将来のUSI通信は別の責務。
"""

from .model import (BasicPieceType, Hand, PieceType, Position, Side,
                    Square)


_HAND_PIECE_SPECS = (
    (BasicPieceType.PAWN, "歩"),
    (BasicPieceType.LANCE, "香"),
    (BasicPieceType.KNIGHT, "桂"),
    (BasicPieceType.SILVER, "銀"),
    (BasicPieceType.GOLD, "金"),
    (BasicPieceType.BISHOP, "角"),
    (BasicPieceType.ROOK, "飛"),
)


def _render_hand(hand: Hand, side_label: str) -> str:
    """一方の持ち駒を固定順・枚数付きの一行へ変換する。

    引数:
        hand: 表示する側の枚数を保持するHand。
        side_label: 行頭に示す先手または後手。

    戻り値:
        「先手の持ち駒：歩1」の形式の文字列。持ち駒が0枚なら「なし」とする。

    副作用:
        なし。Hand.countで読み取るだけで、局面や持ち駒を変更しない。
    """
    pieces = []
    for piece_type, name in _HAND_PIECE_SPECS:
        count = hand.count(piece_type)
        if count > 0:
            pieces.append(f"{name}{count}")
    contents = "、".join(pieces) if pieces else "なし"
    return f"{side_label}の持ち駒：{contents}"


def render_position(position: Position) -> str:
    """局面を変更せず、手番・凡例・双方の持ち駒・全盤面を文字列で返す。

    引数はPosition。現在定義された14種類のPieceTypeとSideを想定する。
    盤の上に後手、下に先手の持ち駒を表示し、所持駒は歩・香・桂・銀・金・角・飛の
    順で枚数付き、0枚は「なし」とする。段は一→九、各段の筋は9→1。
    +が先手、-が後手、・が空マス。
    玉と王は同一の駒種だが、この表示では先手を王、後手を玉とする。

    日本語が2桁幅の等幅端末を想定し、各セルを4桁相当に揃える。
    各行末の空白と文字列末尾の改行は付けず、CLIのprintが最後に改行する。
    標準出力、色付け、入力操作は行わない。
    """
    side_name = "先手" if position.side_to_move == Side.SENTE else "後手"
    names = {
        PieceType.ROOK: "飛", PieceType.BISHOP: "角", PieceType.GOLD: "金",
        PieceType.SILVER: "銀", PieceType.KNIGHT: "桂", PieceType.LANCE: "香",
        PieceType.PAWN: "歩", PieceType.PRO_PAWN: "と",
        PieceType.PRO_LANCE: "成香", PieceType.PRO_KNIGHT: "成桂",
        PieceType.PRO_SILVER: "成銀", PieceType.HORSE: "馬",
        PieceType.DRAGON: "竜",
    }
    lines = [f"手番：{side_name}", "+：先手、-：後手", "",
             _render_hand(position.gote_hand, "後手"), ""]
    lines.append("   " + "".join(f" {file}  " for file in range(9, 0, -1)).rstrip())
    # 保存順によらず、表示は一段目から、各段は９筋からたどる。
    for rank, label in enumerate("一二三四五六七八九", start=1):
        cells = []
        for file in range(9, 0, -1):
            piece = position.board.piece_at(Square(file, rank))
            if piece is None:
                cells.append(" ・ ")
                continue
            mark = "+" if piece.side == Side.SENTE else "-"
            if piece.piece_type == PieceType.KING:
                name = "王" if piece.side == Side.SENTE else "玉"
            else:
                name = names[piece.piece_type]
            cells.append(f"{mark}{name} ")
        lines.append((label + " " + "".join(cells)).rstrip())
    lines.extend(("", _render_hand(position.sente_hand, "先手")))
    return "\n".join(lines)
