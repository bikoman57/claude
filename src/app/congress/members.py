"""Member performance rating system for Congressional traders."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from app.congress.fetcher import CongressTrade, TransactionType


class MemberTier(StrEnum):
    """Performance tier for a Congress member."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


@dataclass(frozen=True, slots=True)
class RoundTrip:
    """A matched buy-sell round trip for performance calculation."""

    ticker: str
    buy_date: str
    sell_date: str
    buy_amount_mid: float
    sell_amount_mid: float
    return_pct: float
    holding_days: int


@dataclass(frozen=True, slots=True)
class MemberRating:
    """Performance rating for a Congressional member."""

    name: str
    chamber: str
    party: str
    state: str
    total_trades: int
    round_trips: int
    wins: int
    losses: int
    win_rate: float
    weighted_win_rate: float
    avg_return_pct: float
    tier: str  # MemberTier value
    trade_volume_usd: float
    last_trade_date: str
    best_sectors: tuple[str, ...]


def _amount_midpoint(trade: CongressTrade) -> float:
    """Estimate dollar amount as midpoint of reported range."""
    return (trade.amount_low + trade.amount_high) / 2


def _days_between(date1: str, date2: str) -> int:
    """Calculate days between two YYYY-MM-DD date strings."""
    try:
        d1 = datetime.strptime(date1, "%Y-%m-%d").replace(tzinfo=UTC)
        d2 = datetime.strptime(date2, "%Y-%m-%d").replace(tzinfo=UTC)
        return abs((d2 - d1).days)
    except ValueError:
        return 0


def _recency_weight(trade_date: str) -> float:
    """Weight by recency: recent trades matter more."""
    try:
        td = datetime.strptime(trade_date, "%Y-%m-%d").replace(tzinfo=UTC)
        days_ago = (datetime.now(tz=UTC) - td).days
    except ValueError:
        return 0.5

    if days_ago <= 90:
        return 2.0
    if days_ago <= 180:
        return 1.5
    if days_ago <= 365:
        return 1.0
    return 0.5


def match_round_trips(
    trades: list[CongressTrade],
) -> list[RoundTrip]:
    """Match buy-sell pairs per ticker using FIFO ordering.

    Returns completed round trips with return estimates.
    Note: Since STOCK Act only reports amount ranges (not exact prices),
    returns are approximate based on midpoint of reported ranges.
    """
    # Group by ticker
    by_ticker: dict[str, list[CongressTrade]] = defaultdict(list)
    for t in trades:
        by_ticker[t.ticker].append(t)

    round_trips: list[RoundTrip] = []

    for ticker, ticker_trades in by_ticker.items():
        # Sort by date for FIFO matching
        sorted_trades = sorted(ticker_trades, key=lambda t: t.trade_date)

        buys: list[CongressTrade] = []
        for trade in sorted_trades:
            if trade.transaction_type == TransactionType.PURCHASE:
                buys.append(trade)
            elif (
                trade.transaction_type
                in (
                    TransactionType.SALE_FULL,
                    TransactionType.SALE_PARTIAL,
                )
                and buys
            ):
                buy = buys.pop(0)  # FIFO
                buy_mid = _amount_midpoint(buy)
                sell_mid = _amount_midpoint(trade)
                ret_pct = ((sell_mid - buy_mid) / buy_mid * 100) if buy_mid > 0 else 0.0
                days = _days_between(buy.trade_date, trade.trade_date)
                round_trips.append(
                    RoundTrip(
                        ticker=ticker,
                        buy_date=buy.trade_date,
                        sell_date=trade.trade_date,
                        buy_amount_mid=buy_mid,
                        sell_amount_mid=sell_mid,
                        return_pct=ret_pct,
                        holding_days=days,
                    ),
                )

    return round_trips


def _assign_tier(
    weighted_win_rate: float,
    avg_return_pct: float,
    total_completed: int,
) -> str:
    """Assign member tier based on performance metrics."""
    min_trades_for_above_c = 5

    if total_completed < min_trades_for_above_c:
        return MemberTier.C

    if weighted_win_rate >= 0.65 and avg_return_pct >= 5.0:
        return MemberTier.A
    if weighted_win_rate >= 0.55 and avg_return_pct >= 2.0:
        return MemberTier.B
    if weighted_win_rate >= 0.45:
        return MemberTier.C
    if weighted_win_rate >= 0.35:
        return MemberTier.D
    return MemberTier.F


def rate_member(
    name: str,
    trades: list[CongressTrade],
) -> MemberRating:
    """Compute full performance rating for one member."""
    member_trades = [t for t in trades if t.member_name == name]
    if not member_trades:
        return MemberRating(
            name=name,
            chamber="",
            party="",
            state="",
            total_trades=0,
            round_trips=0,
            wins=0,
            losses=0,
            win_rate=0.0,
            weighted_win_rate=0.0,
            avg_return_pct=0.0,
            tier=MemberTier.C,
            trade_volume_usd=0.0,
            last_trade_date="",
            best_sectors=(),
        )

    first = member_trades[0]
    trips = match_round_trips(member_trades)

    # Compute basic stats
    wins = sum(1 for rt in trips if rt.return_pct > 0)
    losses = len(trips) - wins
    win_rate = wins / len(trips) if trips else 0.0
    avg_ret = sum(rt.return_pct for rt in trips) / len(trips) if trips else 0.0

    # Compute recency-weighted win rate
    weighted_wins = 0.0
    weighted_total = 0.0
    for rt in trips:
        w = _recency_weight(rt.sell_date)
        weighted_total += w
        if rt.return_pct > 0:
            weighted_wins += w
    weighted_win_rate = weighted_wins / weighted_total if weighted_total > 0 else 0.0

    # Total volume
    volume = sum(_amount_midpoint(t) for t in member_trades)

    # Last trade date
    last_date = max(t.trade_date for t in member_trades)

    # Best sectors (by win count per ticker)
    ticker_wins: dict[str, int] = defaultdict(int)
    for rt in trips:
        if rt.return_pct > 0:
            ticker_wins[rt.ticker] += 1
    best = sorted(ticker_wins, key=ticker_wins.get, reverse=True)[:3]  # type: ignore[arg-type]

    tier = _assign_tier(weighted_win_rate, avg_ret, len(trips))

    return MemberRating(
        name=name,
        chamber=first.chamber,
        party=first.party,
        state=first.state,
        total_trades=len(member_trades),
        round_trips=len(trips),
        wins=wins,
        losses=losses,
        win_rate=round(win_rate, 4),
        weighted_win_rate=round(weighted_win_rate, 4),
        avg_return_pct=round(avg_ret, 2),
        tier=tier,
        trade_volume_usd=round(volume, 2),
        last_trade_date=last_date,
        best_sectors=tuple(best),
    )


def rate_all_members(
    trades: list[CongressTrade],
) -> list[MemberRating]:
    """Rate all members, sorted by tier then weighted win rate."""
    names = sorted({t.member_name for t in trades})
    ratings = [rate_member(name, trades) for name in names]

    tier_order: dict[str, int] = {
        MemberTier.A: 0,
        MemberTier.B: 1,
        MemberTier.C: 2,
        MemberTier.D: 3,
        MemberTier.F: 4,
    }
    return sorted(
        ratings,
        key=lambda r: (tier_order.get(r.tier, 5), -r.weighted_win_rate),
    )


def get_member_weight(tier: str) -> float:
    """Get aggregation weight for a member tier.

    A-tier members' trades are weighted most heavily.
    """
    weights: dict[str, float] = {
        MemberTier.A: 1.0,
        MemberTier.B: 0.75,
        MemberTier.C: 0.5,
        MemberTier.D: 0.25,
        MemberTier.F: 0.0,
    }
    return weights.get(tier, 0.5)
