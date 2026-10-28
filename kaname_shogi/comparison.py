"""比較対局の条件と予定を表すデータを定義する。"""

import random
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from . import game_search
from .comparison_seeds import SeedPlan
from .game_record import GameRecord
from .model import Position, Side
from .move import BoardMove, DropMove, Move
from .movegen import MoveSelectionPolicy, is_in_check, legal_moves
from .repetition import RepetitionOutcome, RepetitionOutcomeKind, RepetitionTracker


@dataclass(frozen=True)
class ComparisonPosition:
    """合法手順から作った比較開始局面と、その由来を保持するデータ。

    引数:
        position_id: セット内で一意なASCII識別子。
        setup_moves: 平手初期局面から比較開始位置までのUSI一手列。
        rationale: この動作確認用局面の作成理由。
        start_position: 準備手順の最終局面。
        start_sfen: 初期配置からの準備手数を含む正規化SFEN。
        initial_move_number: SFEN表示用の1始まり手数。比較対局の手数には加えない。

    戻り値:
        比較局面の情報を結び付けた変更不可データ。

    副作用:
        なし。Position参照そのものは可変だが、生成後にこの型から盤面を変更しない。

    前提条件:
        `start_position` は `setup_moves` の合法再生結果であり、開始時に合法手がある。
        比較履歴はこの位置から新しく数え、準備手順を履歴へ含めない。
    """

    position_id: str
    setup_moves: tuple[str, ...]
    rationale: str
    start_position: Position
    start_sfen: str
    initial_move_number: int


@dataclass(frozen=True)
class ComparisonConfig:
    """一回の比較実験に使う検証済み条件と入力元を表すデータ。

    引数:
        baseline/candidate: 比較対象となる別々の既存一手選択方式。
        positions: 実験に使う順序固定の局面集合。
        pairs_per_position: 各局面で先後を交換する対局組数。
        seed: 0以上の主乱数種。乱数種一覧方式ではNone。
        max_plies: 比較開始後の成功手数の上限。
        output_dir: 通常実行では未使用パス、再開では既存実験ディレクトリ。
        positions_path: 読み込んだ局面セットの入力パス。
        positions_json: 検証した局面セットの読込時バイト列。
        seed_plan: 方式別乱数種一覧。旧主乱数種方式ではNone。
        seed_list_json: 検証した乱数種一覧JSONの読込時バイト列。
        seed_list_path: 乱数種一覧の入力パス。
        workers: 一局ずつ比較を実行するプロセス数。省略時は従来どおり逐次実行。
        resume: 既存条件・保存局を照合して未完了局だけを再実行する指定。

    戻り値:
        比較条件を一つの変更不可データへまとめた値。

    副作用:
        なし。出力先は作成せず、入力元バイト列も変更しない。

    前提条件:
        CLI検証済みであり、両方式は異なり、組数・手数上限は正。
        `seed`と`seed_plan`のちょうど一方を使う。
        入力ファイルの読込後に外部で同ファイルが変わっても、positions_jsonが
        検証済み局面を復元できる実験条件の正本となる。
    """

    baseline: MoveSelectionPolicy
    candidate: MoveSelectionPolicy
    positions: tuple[ComparisonPosition, ...]
    pairs_per_position: int
    seed: int | None
    max_plies: int
    output_dir: Path
    positions_path: Path
    positions_json: bytes
    seed_plan: SeedPlan | None = None
    seed_list_json: bytes | None = None
    seed_list_path: Path | None = None
    workers: int = 1
    resume: bool = False


@dataclass(frozen=True)
class ScheduledGame:
    """一局の識別・組・方式の先後・方式別乱数種を表す予定データ。

    引数:
        game_id: バッチ内で一意な連番ID。
        position_id: 使用する比較開始局面のID。
        pair_number: 設計式で採番した組番号q。
        game_number_in_pair: 組の一局目または二局目。
        baseline_side/candidate_side: 方式ごとの先後担当。
        baseline_seed/candidate_seed: 方式ごとの乱数種。

    戻り値:
        バッチ予定の一局分を表す変更不可データ。

    副作用:
        なし。

    前提条件:
        二局一組で同じ盤面・駒所有を用い、二局目は方式の先後だけが逆になる。
        各組で方式別の乱数種は両局間で変えない。
    """

    game_id: str
    position_id: str
    pair_number: int
    game_number_in_pair: int
    baseline_side: Side
    candidate_side: Side
    baseline_seed: int
    candidate_seed: int


def make_schedule(config: ComparisonConfig) -> tuple[ScheduledGame, ...]:
    """検証済み条件から先後を交換する一局単位の予定を順番に作る。

    引数:
        config: 局面順、組数、主乱数種または検証済み種一覧を持つ比較条件。

    戻り値:
        各局面を配列順、反復を0から昇順、組の一局目・二局目の順に並べた予定。

    副作用:
        なし。条件・局面・乱数生成器を変更しない。

    前提条件:
        `config` は入力検証済みであり、組数は1以上である。旧方式では組番号qを
        局面番号pと反復番号rからp*K+rで定め、方式別乱数種をbaselineがS+2*q、
        candidateがS+2*q+1とする。一覧方式では一致済み一覧の順序付き種を使う。
        どちらも一組の二局で方式別種を維持し、二局目は先後だけを反転する。
        開始盤面・駒所有は反転しない。
    """
    scheduled: list[ScheduledGame] = []
    for position_index, position in enumerate(config.positions):
        for repetition_index in range(config.pairs_per_position):
            pair_number = position_index * config.pairs_per_position + repetition_index
            first_baseline_side = Side.SENTE if pair_number % 2 == 0 else Side.GOTE
            if config.seed_plan is None:
                if config.seed is None:
                    raise ValueError("比較予定には主乱数種または乱数種一覧が必要です")
                baseline_seed = config.seed + 2 * pair_number
                candidate_seed = config.seed + 2 * pair_number + 1
            else:
                pair_seeds = config.seed_plan.pairs[pair_number]
                if (
                    pair_seeds.position_id != position.position_id
                    or pair_seeds.repetition_index != repetition_index
                ):
                    raise ValueError("乱数種一覧の予定順が比較条件と一致しません")
                baseline_seed = pair_seeds.baseline_seed
                candidate_seed = pair_seeds.candidate_seed
            for game_number, baseline_side in enumerate(
                (first_baseline_side, _opposite(first_baseline_side)), start=1
            ):
                scheduled.append(
                    ScheduledGame(
                        game_id=f"game-{len(scheduled) + 1:06d}",
                        position_id=position.position_id,
                        pair_number=pair_number,
                        game_number_in_pair=game_number,
                        baseline_side=baseline_side,
                        candidate_side=_opposite(baseline_side),
                        baseline_seed=baseline_seed,
                        candidate_seed=candidate_seed,
                    )
                )
    return tuple(scheduled)


def _opposite(side: Side) -> Side:
    """指定された先後と反対側を返す。"""
    return Side.GOTE if side is Side.SENTE else Side.SENTE


class GameEndReason(Enum):
    """比較対局の排他的な終局理由を表す値。"""

    CHECKMATE = "checkmate"
    NO_LEGAL_MOVE = "no_legal_move"
    PERPETUAL_CHECK_LOSS = "perpetual_check_loss"
    REPETITION = "repetition"
    PLY_LIMIT = "ply_limit"
    INTERRUPTED = "interrupted"
    ERROR = "error"
    UNRESOLVED_DOUBLE_PERPETUAL_CHECK = "unresolved_double_perpetual_check"


def repetition_terminal(
    outcome: RepetitionOutcome,
) -> tuple[GameEndReason, Side | None] | None:
    """反復判定の終局理由と勝者先後を比較対局の値へ変換する。

    引数:
        outcome: 千日手判定器が返した現在局面の判定。

    戻り値:
        継続中はNone。通常千日手・双方連続王手の未裁定では勝者なし、片側連続王手
        負けでは敗者の反対側を勝者として返す。

    例外:
        ValueError: 判定データの型、種類、連続王手敗者が契約外の場合。

    副作用:
        なし。反復履歴や局面を変更しない。

    前提条件:
        反復終局を盤面の合法手有無や手数上限より先に評価し、通常千日手・双方未裁定へ
        勝者を補わない。
    """
    if not isinstance(outcome, RepetitionOutcome) or not isinstance(
        outcome.kind, RepetitionOutcomeKind
    ):
        raise ValueError("反復判定データが不正です")
    if outcome.kind is RepetitionOutcomeKind.REPETITION:
        if outcome.losing_side is not None:
            raise ValueError("通常千日手に敗者側を指定できません")
        return GameEndReason.REPETITION, None
    if outcome.kind is RepetitionOutcomeKind.PERPETUAL_CHECK_LOSS:
        if not isinstance(outcome.losing_side, Side):
            raise ValueError("連続王手負けの敗者側がありません")
        return GameEndReason.PERPETUAL_CHECK_LOSS, _opposite(outcome.losing_side)
    if outcome.kind is RepetitionOutcomeKind.UNRESOLVED_DOUBLE_PERPETUAL_CHECK:
        if outcome.losing_side is not None:
            raise ValueError("双方連続王手の未裁定に敗者側を指定できません")
        return GameEndReason.UNRESOLVED_DOUBLE_PERPETUAL_CHECK, None
    if outcome.losing_side is not None:
        raise ValueError("継続・非敗北の反復判定に敗者を指定できません")
    if outcome.kind in {
        RepetitionOutcomeKind.CONTINUE,
        RepetitionOutcomeKind.FOURFOLD_CONTINUE,
    }:
        return None
    raise ValueError("反復判定の種類が未対応です")


def board_terminal(
    position: Position,
    *,
    has_legal_moves: bool,
    plies: int,
    max_plies: int,
) -> tuple[GameEndReason, Side | None] | None:
    """合法手の有無を示す根拠値と上限から盤面終局を変換する。

    引数:
        position: 判定対象となる現在局面。
        has_legal_moves: 現在局面に合法手があるか。根拠は前提条件を参照。
        plies: 比較開始後に確定した成功手数。
        max_plies: 成功手数の上限。

    戻り値:
        合法手なしなら詰みまたは合法手なしと反対側勝ち、上限到達なら未決着上限、
        それ以外はNone。

    例外:
        ValueError: 局面、合法手有無、手数または上限が契約外の場合。

    副作用:
        なし。合法手を列挙せず、受け取った局面も変更しない。

    前提条件:
        千日手判定後に呼ばれ、合法手なしを手数上限より優先する。呼び出し側は合法手を
        生成して真偽を渡すか、全記録手を合法再生済みの棋譜readerなら中間局面の次の記録手を
        合法手存在の根拠として渡す。後者は探索の計時境界に使う対局実行経路へ適用しない。
    """
    if (
        not isinstance(position, Position)
        or not isinstance(position.side_to_move, Side)
        or type(has_legal_moves) is not bool
        or type(plies) is not int
        or plies < 0
        or type(max_plies) is not int
        or max_plies < 1
    ):
        raise ValueError("盤面終局判定の入力が不正です")
    if not has_legal_moves:
        side = position.side_to_move
        reason = (
            GameEndReason.CHECKMATE
            if is_in_check(position.board, side)
            else GameEndReason.NO_LEGAL_MOVE
        )
        return reason, _opposite(side)
    if plies >= max_plies:
        return GameEndReason.PLY_LIMIT, None
    return None


class BatchStatus(Enum):
    """比較バッチ全体の完了・割込み・故障状態を表す値。"""

    RUNNING = "running"
    COMPLETE = "complete"
    INTERRUPTED = "interrupted"
    ERROR = "error"


@dataclass(frozen=True)
class MoveTiming:
    """一手の探索にかかった時間と、選ばれた手を表す記録。"""

    ply: int
    side: Side
    policy: MoveSelectionPolicy
    move: Move
    elapsed_ns: int


@dataclass(frozen=True)
class GameResult:
    """比較対局一局の確定手・終局・計時を保持する結果データ。

    引数:
        schedule: 一局の識別子、方式の先後、方式別乱数種。
        start_sfen: 比較開始局面と表示手数を含むSFEN。
        initial_move_number: 開始局面SFENの1始まり手数。
        record: 開始局面から成功手だけを保持する棋譜。
        reason: 勝敗や未決着を区別する排他的な終局理由。
        winner_side/winner_policy: 勝者が定まるときの先後と方式。それ以外はNone。
        plies: 確定した成功手数。
        move_times_ns: 成功手の選択時間を順番に並べた値。
        unfinished_calculation_ns: 成功手へ確定できなかった計算の経過時間。
        error: ERROR時の診断文字列。通常の終局ではNone。

    戻り値:
        一局を後から直列化・集計できる結果値。

    副作用:
        なし。`record` はこの結果が保持する一局の棋譜である。

    前提条件:
        `plies == len(record.moves)` であり、手数と計時は成功した手だけを数える。
        通常千日手、双方連続王手の未裁定、手数上限、割込み、エラーは勝者を持たない。
    """

    schedule: ScheduledGame
    start_sfen: str
    initial_move_number: int
    record: GameRecord
    reason: GameEndReason
    winner_side: Side | None
    winner_policy: MoveSelectionPolicy | None
    plies: int
    move_times_ns: tuple[MoveTiming, ...]
    unfinished_calculation_ns: int | None
    error: str | None


def run_game(
    schedule: ScheduledGame,
    position: ComparisonPosition,
    config: ComparisonConfig,
    *,
    clock_ns: Callable[[], int] = time.monotonic_ns,
) -> GameResult:
    """条件と予定に従って一局を進行し、確定した棋譜と終局結果を返す。

    引数:
        schedule: 先後・方式別乱数種を固定した一局予定。
        position: 初期局面、SFEN、表示手数を持つ比較開始局面。
        config: 比較条件と最大成功手数。
        clock_ns: 合法手生成直前と探索返却直後を読む単調ナノ秒時計。

    戻り値:
        成功した手だけを記録し、終局理由・勝者・成功手計時を対応づけた結果。

    副作用:
        一局専用の棋譜、反復判定器、方式別乱数生成器を生成する。渡された開始局面、
        条件、予定は変更しない。時計と既存探索器の乱数以外の状態も共有しない。

    例外:
        想定された探索・適用・時計の例外は `ERROR` として結果に保持する。
        探索中のKeyboardInterruptは `INTERRUPTED` として返す。

    前提条件:
        `position` は合法な比較開始局面、`schedule` は異なる二方式の予定に属し、
        `config.max_plies` は1以上。成功手後は千日手、合法手なし、手数上限の順で
        判定する。4回目の通常出現は継続し、5回目の通常出現は千日手終局とする。
        連続王手負けは敗者の反対側の方式勝ち、双方連続王手は勝者なしの未裁定とする。
    """
    record = GameRecord(position.start_position)
    tracker = RepetitionTracker(record.current_position)
    move_times: list[MoveTiming] = []
    unfinished_calculation_ns: int | None = None
    error: str | None = None

    rng_by_side = {
        schedule.baseline_side: random.Random(schedule.baseline_seed),
        schedule.candidate_side: random.Random(schedule.candidate_seed),
    }

    def policy_for(side: Side) -> MoveSelectionPolicy:
        """その先後を担当する方式を返す。"""
        return config.baseline if side is schedule.baseline_side else config.candidate

    def result(
        reason: GameEndReason,
        *,
        winner_side: Side | None = None,
    ) -> GameResult:
        """現在まで確定済みの局面・手計時から一局結果を作る。"""
        return GameResult(
            schedule=schedule,
            start_sfen=position.start_sfen,
            initial_move_number=position.initial_move_number,
            record=record,
            reason=reason,
            winner_side=winner_side,
            winner_policy=policy_for(winner_side) if winner_side is not None else None,
            plies=len(record.moves),
            move_times_ns=tuple(move_times),
            unfinished_calculation_ns=unfinished_calculation_ns,
            error=error,
        )

    def failure_duration(start_ns: int | None) -> int | None:
        """未確定の探索に対する経過時間を可能な範囲で読む。"""
        if start_ns is None:
            return None
        try:
            return clock_ns() - start_ns
        except Exception:
            return None

    while True:
        terminal = repetition_terminal(tracker.current_outcome)
        if terminal is not None:
            reason, winner_side = terminal
            return result(reason, winner_side=winner_side)

        current_position = record.current_position
        side = current_position.side_to_move
        start_ns: int | None = None
        try:
            start_ns = clock_ns()
            candidates = legal_moves(current_position)
            terminal = board_terminal(
                current_position,
                has_legal_moves=bool(candidates),
                plies=len(record.moves),
                max_plies=config.max_plies,
            )
            if terminal is not None:
                reason, winner_side = terminal
                return result(reason, winner_side=winner_side)

            policy = policy_for(side)
            selected = game_search.choose_move(
                current_position.copy(), candidates, policy, rng_by_side[side]
            )
            end_ns = clock_ns()
        except KeyboardInterrupt:
            unfinished_calculation_ns = failure_duration(start_ns)
            return result(GameEndReason.INTERRUPTED)
        except Exception as caught_error:
            unfinished_calculation_ns = failure_duration(start_ns)
            error = f"{type(caught_error).__name__}: {caught_error}"
            return result(GameEndReason.ERROR)

        elapsed_ns = end_ns - start_ns
        if elapsed_ns < 0:
            unfinished_calculation_ns = elapsed_ns
            error = "単調時計が逆行しました"
            return result(GameEndReason.ERROR)
        if selected is None or selected not in candidates:
            unfinished_calculation_ns = elapsed_ns
            error = "探索結果が合法手一覧にありません"
            return result(GameEndReason.ERROR)

        try:
            candidate_record = GameRecord.from_payload(record.to_payload())
            if isinstance(selected, BoardMove):
                candidate_record.apply_move(
                    selected.source,
                    selected.destination,
                    promote=selected.promote,
                )
            elif isinstance(selected, DropMove):
                candidate_record.apply_drop(selected.piece_type, selected.destination)
            else:
                raise ValueError("探索結果の指し手型が不正です")
            candidate_position = candidate_record.current_position
            tracker.add_position(candidate_position)
        except KeyboardInterrupt:
            unfinished_calculation_ns = elapsed_ns
            return result(GameEndReason.INTERRUPTED)
        except Exception as caught_error:
            unfinished_calculation_ns = elapsed_ns
            error = f"{type(caught_error).__name__}: {caught_error}"
            return result(GameEndReason.ERROR)

        record = candidate_record
        move_times.append(
            MoveTiming(
                ply=len(record.moves),
                side=side,
                policy=policy,
                move=selected,
                elapsed_ns=elapsed_ns,
            )
        )


def summarize(
    config: ComparisonConfig,
    results: Sequence[GameResult],
    *,
    batch_status: BatchStatus,
    unstarted_games: int,
    in_flight_games: int = 0,
    elapsed_ns: int,
) -> dict[str, object]:
    """確定済み局結果を排他的な件数と方式別計時へ集計する。

    引数:
        config: 実験予定の局面・組数・方式を保持する比較条件。
        results: 予定順に開始済みの各局から得た確定結果。
        batch_status: 全局完了・中断・故障のいずれか。
        unstarted_games: 予定のうち開始しなかった局数。
        in_flight_games: 並列実行で投入済み・未回収の局数。逐次実行では0。
        elapsed_ns: バッチ開始から集計時点までの経過ナノ秒。

    戻り値:
        排他的な終了理由、局面・先後・方式別の記述集計を持つJSON用辞書。開始局数は
        保存済み結果と投入中局の合計、終了局数は保存済み結果数。複数ワーカーでは
        投入中局数も含める。

    例外:
        ValueError: 件数恒等式、予定ID、重複局、勝者契約または手数記録が不整合の場合。

    副作用:
        なし。結果・棋譜・条件を変更しない。

    前提条件:
        `results` は保存済み局だけを一局ずつ含み、各 `GameResult` は成功手と計時が
        そろっている。保存済み・投入中・未開始の合計は予定局数に一致する。終了理由は
        相互排他的に一度数え、連続王手の敗者内訳は別枠で報告しても終了理由合計へ
        重ねて加えない。勝率や統計的判定は計算しない。
    """
    scheduled = make_schedule(config)
    if type(unstarted_games) is not int or unstarted_games < 0:
        raise ValueError("未開始局数は0以上の整数で指定してください")
    if type(in_flight_games) is not int or in_flight_games < 0:
        raise ValueError("投入中局数は0以上の整数で指定してください")
    if type(elapsed_ns) is not int or elapsed_ns < 0:
        raise ValueError("経過時間は0以上の整数で指定してください")
    if not isinstance(batch_status, BatchStatus):
        raise ValueError("バッチ状態が不正です")
    if config.workers == 1 and in_flight_games != 0:
        raise ValueError("逐次比較に投入中局を指定できません")
    if len(results) + in_flight_games + unstarted_games != len(scheduled):
        raise ValueError("保存済み・投入中・未開始局数の合計が予定局数と一致しません")

    schedule_by_id = {game.game_id: game for game in scheduled}
    seen_game_ids: set[str] = set()
    reason_counts = {reason.value: 0 for reason in GameEndReason}
    side_counts = {
        Side.SENTE: {"games": 0, "wins": 0, "losses": 0, "no_winner": 0},
        Side.GOTE: {"games": 0, "wins": 0, "losses": 0, "no_winner": 0},
    }
    position_counts = {
        position.position_id: {
            "started_games": 0,
            "results": {reason.value: 0 for reason in GameEndReason},
        }
        for position in config.positions
    }
    perpetual_check_losses = {Side.SENTE: 0, Side.GOTE: 0}
    pair_game_numbers: dict[int, set[int]] = {}
    incomplete_pairs: set[int] = set()
    policies = tuple(
        policy
        for policy in MoveSelectionPolicy
        if policy
        not in (
            MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY,
            MoveSelectionPolicy.MATERIAL_KING_SAFETY_MATERIAL_ONLY,
            MoveSelectionPolicy.MATERIAL_KING_SAFETY,
        )
    )
    if MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY in {
        config.baseline,
        config.candidate,
    }:
        policies += (MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY,)
    policy_times: dict[MoveSelectionPolicy, list[int]] = {
        policy: [] for policy in policies
    }

    winning_reasons = {
        GameEndReason.CHECKMATE,
        GameEndReason.NO_LEGAL_MOVE,
        GameEndReason.PERPETUAL_CHECK_LOSS,
    }
    for game_result in results:
        game = game_result.schedule
        expected_game = schedule_by_id.get(game.game_id)
        if expected_game is None or expected_game != game:
            raise ValueError(f"予定にない局結果です: {game.game_id}")
        if game.game_id in seen_game_ids:
            raise ValueError(f"局結果IDが重複しています: {game.game_id}")
        seen_game_ids.add(game.game_id)
        if game_result.reason in winning_reasons:
            if game_result.winner_side is None or game_result.winner_policy is None:
                raise ValueError("勝敗がつく終局理由に勝者情報が必要です")
        elif (
            game_result.winner_side is not None or game_result.winner_policy is not None
        ):
            raise ValueError("未決着の終局理由に勝者情報を指定できません")
        if game_result.plies != len(game_result.record.moves):
            raise ValueError("成功手数と棋譜手数が一致しません")
        if game_result.plies != len(game_result.move_times_ns):
            raise ValueError("成功手数と一手計時件数が一致しません")

        reason_counts[game_result.reason.value] += 1
        position_counts[game.position_id]["started_games"] += 1
        position_counts[game.position_id]["results"][game_result.reason.value] += 1
        pair_game_numbers.setdefault(game.pair_number, set()).add(
            game.game_number_in_pair
        )
        if game_result.reason in {GameEndReason.INTERRUPTED, GameEndReason.ERROR}:
            incomplete_pairs.add(game.pair_number)

        for side in Side:
            side_counts[side]["games"] += 1
            if game_result.winner_side is None:
                side_counts[side]["no_winner"] += 1
            elif game_result.winner_side is side:
                side_counts[side]["wins"] += 1
            else:
                side_counts[side]["losses"] += 1
        if game_result.reason is GameEndReason.PERPETUAL_CHECK_LOSS:
            assert game_result.winner_side is not None
            losing_side = _opposite(game_result.winner_side)
            perpetual_check_losses[losing_side] += 1

        for move_timing in game_result.move_times_ns:
            if move_timing.policy not in policy_times:
                raise ValueError("計時方式が比較条件の方式と一致しません")
            policy_times[move_timing.policy].append(move_timing.elapsed_ns)

    completed_pairs = sum(
        game_numbers == {1, 2} and pair_number not in incomplete_pairs
        for pair_number, game_numbers in pair_game_numbers.items()
    )
    partial_pairs = sum(
        game_numbers != {1, 2} or pair_number in incomplete_pairs
        for pair_number, game_numbers in pair_game_numbers.items()
    )
    move_time_by_policy = {}
    for policy, times in policy_times.items():
        total_ns = sum(times)
        move_time_by_policy[_policy_name(policy)] = {
            "successful_moves": len(times),
            "total_ns": total_ns,
            "average_ns": total_ns / len(times) if times else None,
            "max_ns": max(times) if times else None,
        }

    summary = {
        "status": batch_status.value,
        "planned_games": len(scheduled),
        "started_games": len(results) + in_flight_games,
        "ended_games": len(results),
        "unstarted_games": unstarted_games,
        "completed_pairs": completed_pairs,
        "partial_pairs": partial_pairs,
        "results": reason_counts,
        "perpetual_check_losses": {
            _side_name(side): count for side, count in perpetual_check_losses.items()
        },
        "by_position": position_counts,
        "by_side": {_side_name(side): counts for side, counts in side_counts.items()},
        "move_time_by_policy": move_time_by_policy,
        "elapsed_ns": elapsed_ns,
        "statistical_decision": None,
    }
    if config.workers > 1:
        summary["in_flight_games"] = in_flight_games
    return summary


_POLICY_NAMES = {
    MoveSelectionPolicy.RANDOM: "random",
    MoveSelectionPolicy.MATERIAL: "material",
    MoveSelectionPolicy.MATERIAL_ROOK_MOBILITY: "material-rook-mobility",
    MoveSelectionPolicy.TWO_PLY_MATERIAL: "two-ply-material",
    MoveSelectionPolicy.FOUR_PLY_FULL_WIDTH: "full-width-4",
    MoveSelectionPolicy.FOUR_PLY_ALPHA_BETA: "alpha-beta-4",
}


def _policy_name(policy: MoveSelectionPolicy) -> str:
    """一手選択方式を既存CLIで使う安定した識別子へ変換する。"""
    return _POLICY_NAMES[policy]


def _side_name(side: Side) -> str:
    """先後の列挙値をJSONで使う小文字識別子へ変換する。"""
    return "sente" if side is Side.SENTE else "gote"
