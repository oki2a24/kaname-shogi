"""対局で使う既存三方式・飛車可動性付き一手方式・四手探索二方式の選択境界。"""

from random import Random

from . import movegen
from .model import Position
from .move import Move
from .search import iterative_deepening, shogi
from .search.result import ControlledCompletion
from .search_control import SearchControl

_LEGACY_POLICIES = (
    movegen.MoveSelectionPolicy.RANDOM,
    movegen.MoveSelectionPolicy.MATERIAL,
    movegen.MoveSelectionPolicy.TWO_PLY_MATERIAL,
)
_ONE_PLY_POLICIES = (
    *_LEGACY_POLICIES,
    movegen.MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY,
)
_FULL_WIDTH_POLICY = movegen.MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH
_ALPHA_BETA_POLICY = movegen.MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA


def _pruning_for(policy: movegen.MoveSelectionPolicy) -> bool:
    """新方式をpruning値へ変換し、未知値を探索開始前に拒否する。"""
    if policy == _FULL_WIDTH_POLICY:
        return False
    if policy == _ALPHA_BETA_POLICY:
        return True
    raise ValueError("未知の一手選択方針です")


def choose_move(
    position: Position,
    moves: tuple[Move, ...],
    policy: movegen.MoveSelectionPolicy,
    rng: Random,
) -> Move | None:
    """選択方式に応じて、現在局面からコンピュータの一手を返す。

    引数: positionは開始局面、movesは同局面の全合法手、policyは既存三方式・
    駒得と飛車可動性の一手方式・四手探索方式のいずれか、rngは一手方式の抽選に
    使う生成器。
    戻り値: 選択した合法手。合法手なしならNone。
    副作用: 旧三方式と駒得・飛車可動性方式はmovegen.choose_moveと同じ副作用を持つ。新二方式は
    開始側を視点とする探索を行い、rng・position・movesを変更しない。
    前提・設計理由: movesはCLIが従来どおり生成した全合法手。新方式の探索は
    独立した将棋操作セットから深さ1→4で開始するため、根候補の再生成を許容する。
    深さごとの反復・前回最善手は共通探索へ委譲し、新二方式は抽選しない。
    時間制御や応答期限は担当しない。
    """
    if policy in _ONE_PLY_POLICIES:
        return movegen.choose_move(position, moves, policy, rng)
    pruning = _pruning_for(policy)
    if not moves:
        return None
    operations = shogi.make_operations(position.side_to_move)
    last = None
    for record in iterative_deepening.search(position, 4, operations, pruning=pruning):
        last = record
    if last is None:
        raise ValueError("反復探索から完了記録が返りませんでした")
    return last.result.move


def search_move(
    position: Position,
    policy: movegen.MoveSelectionPolicy,
    rng: Random,
    control: SearchControl,
) -> movegen.SearchResult:
    """制御付き方式から既存のUSI向け完了・中断・抑制結果を返す。

    引数: positionは開始局面、policyは既存三方式か四手探索方式、rngは既存方式用、
    controlは呼出し元が所有する一探索分の制御。
    戻り値: 既存のmovegen.SearchResult。新方式のSTOPPEDはINTERRUPTED、
    SUPPRESSEDは手なしのSUPPRESSED、手なし確定は手なしのCOMPLETEへ対応する。
    副作用: 旧三方式はmovegen.search_moveと同じ。新方式は同じcontrolで反復探索し、
    rngを使わない。送信・時計原点・予算生成を行わない。
    前提・設計理由: 対局層の送信責務を既存USI側に保つため、新しい探索結果を
    既存応答型へ変換する。抑制時に診断用の最終完了手を応答として復活させない。
    """
    if policy in _LEGACY_POLICIES:
        return movegen.search_move(position, policy, rng, control)
    pruning = _pruning_for(policy)
    operations = shogi.make_controlled_operations(position.side_to_move)
    result = iterative_deepening.search_controlled(
        position, 4, operations, control, pruning=pruning
    )
    if result.completion in (
        ControlledCompletion.COMPLETE,
        ControlledCompletion.NO_LEGAL_MOVE,
    ):
        completion = movegen.SearchCompletion.COMPLETE
    elif result.completion is ControlledCompletion.STOPPED:
        completion = movegen.SearchCompletion.INTERRUPTED
    elif result.completion is ControlledCompletion.SUPPRESSED:
        completion = movegen.SearchCompletion.SUPPRESSED
    else:
        raise ValueError("探索結果の終了状態が不正です")
    move = None if completion is movegen.SearchCompletion.SUPPRESSED else result.move
    return movegen.SearchResult(completion, move)
