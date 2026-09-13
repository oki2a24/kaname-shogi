"""局面を先手視点の文字列へ変換する。端末への出力は行わない。"""

from .model import PieceType, Position, Side, Square


def render_position(position: Position) -> str:
    side_name = "先手" if position.side_to_move == Side.SENTE else "後手"
    names = {
        PieceType.ROOK: "飛", PieceType.BISHOP: "角", PieceType.GOLD: "金",
        PieceType.SILVER: "銀", PieceType.KNIGHT: "桂", PieceType.LANCE: "香",
        PieceType.PAWN: "歩",
    }
    lines = [f"手番：{side_name}", "+：先手、-：後手", ""]
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
    return "\n".join(lines)
