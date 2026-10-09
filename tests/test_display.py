"""表示の筋段・所有者・手番・成駒名の誤りを検出する。"""

import unittest

from kaname_shogi.display import render_position
from kaname_shogi.model import (
    BasicPieceType,
    Board,
    Piece,
    PieceType,
    Position,
    Side,
    Square,
    create_initial_position,
)

EXPECTED = """手番：先手
+：先手、-：後手

後手の持ち駒：なし

    9   8   7   6   5   4   3   2   1
一 -香 -桂 -銀 -金 -玉 -金 -銀 -桂 -香
二  ・ -飛  ・  ・  ・  ・  ・ -角  ・
三 -歩 -歩 -歩 -歩 -歩 -歩 -歩 -歩 -歩
四  ・  ・  ・  ・  ・  ・  ・  ・  ・
五  ・  ・  ・  ・  ・  ・  ・  ・  ・
六  ・  ・  ・  ・  ・  ・  ・  ・  ・
七 +歩 +歩 +歩 +歩 +歩 +歩 +歩 +歩 +歩
八  ・ +角  ・  ・  ・  ・  ・ +飛  ・
九 +香 +桂 +銀 +金 +王 +金 +銀 +桂 +香

先手の持ち駒：なし"""


class DisplayTests(unittest.TestCase):
    def test_renders_all_promoted_piece_names(self):
        """成駒6種を含む局面を、KeyErrorにせず名称付きで表示する。"""
        position = Position(Board(), Side.SENTE)
        promoted_pieces = (
            (Square(1, 1), PieceType.PRO_PAWN),
            (Square(2, 1), PieceType.PRO_LANCE),
            (Square(3, 1), PieceType.PRO_KNIGHT),
            (Square(4, 1), PieceType.PRO_SILVER),
            (Square(5, 1), PieceType.HORSE),
            (Square(6, 1), PieceType.DRAGON),
        )
        for square, piece_type in promoted_pieces:
            position.board.set_piece(square, Piece(piece_type, Side.SENTE))

        rendered = render_position(position)

        for name in ("と", "成香", "成桂", "成銀", "馬", "竜"):
            self.assertIn("+" + name, rendered)

    def test_initial_position_matches_full_display(self):
        """初期配置を先手視点で筋段・所有者付きで表示する。

        固定した全文を使い、保存順の流用や飛角・王玉の表示違いを検出する。
        """
        self.assertEqual(render_position(create_initial_position()), EXPECTED)

    def test_turn_label_follows_position(self):
        """後手番の局面には「手番：後手」と表示する。

        先手の表示への固定化を検出し、手番以外の表示が変わらないことも確認する。
        """
        position = create_initial_position()
        position.side_to_move = Side.GOTE
        self.assertEqual(
            render_position(position), EXPECTED.replace("手番：先手", "手番：後手", 1)
        )

    def test_renders_sente_and_gote_hands_in_fixed_piece_order(self):
        """先手・後手の持ち駒を固定順と枚数付きで表示する。

        Sideとの対応違い、枚数1の省略、駒種の挿入順への依存を検出する。
        """
        position = Position(Board(), Side.SENTE)
        position.sente_hand.add(BasicPieceType.GOLD)
        position.sente_hand.add(BasicPieceType.LANCE)
        position.sente_hand.add(BasicPieceType.ROOK)
        position.sente_hand.add(BasicPieceType.LANCE)
        position.sente_hand.add(BasicPieceType.GOLD)
        position.sente_hand.add(BasicPieceType.PAWN)
        position.sente_hand.add(BasicPieceType.GOLD)
        position.gote_hand.add(BasicPieceType.BISHOP)
        position.gote_hand.add(BasicPieceType.KNIGHT)
        position.gote_hand.add(BasicPieceType.SILVER)
        position.gote_hand.add(BasicPieceType.BISHOP)
        position.gote_hand.add(BasicPieceType.KNIGHT)
        position.gote_hand.add(BasicPieceType.BISHOP)

        rendered = render_position(position)

        self.assertIn("後手の持ち駒：桂2、銀1、角3", rendered)
        self.assertIn("先手の持ち駒：歩1、香2、金3、飛1", rendered)

    def test_renders_empty_hands_as_none(self):
        """双方の持ち駒がない局面には「なし」と表示する。

        0枚を空欄や存在しない駒種として出力する誤りを検出する。
        """
        position = Position(Board(), Side.SENTE)

        rendered = render_position(position)

        self.assertIn("後手の持ち駒：なし", rendered)
        self.assertIn("先手の持ち駒：なし", rendered)

    def test_rendering_hands_does_not_change_position(self):
        """持ち駒を表示しても局面の持ち駒枚数を変更しない。

        表示処理が枚数の増減や、局面内の可変データへの書き込みを行う誤りを検出する。
        """
        position = Position(Board(), Side.SENTE)
        position.sente_hand.add(BasicPieceType.PAWN)
        position.gote_hand.add(BasicPieceType.ROOK)
        piece_types = (
            BasicPieceType.PAWN,
            BasicPieceType.LANCE,
            BasicPieceType.KNIGHT,
            BasicPieceType.SILVER,
            BasicPieceType.GOLD,
            BasicPieceType.BISHOP,
            BasicPieceType.ROOK,
        )
        before = tuple(
            (
                position.sente_hand.count(piece_type),
                position.gote_hand.count(piece_type),
            )
            for piece_type in piece_types
        )

        render_position(position)

        after = tuple(
            (
                position.sente_hand.count(piece_type),
                position.gote_hand.count(piece_type),
            )
            for piece_type in piece_types
        )
        self.assertEqual(after, before)
