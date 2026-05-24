from typing import List, Optional

from pydantic import BaseModel


class HealthSchema(BaseModel):
    matches_total: int
    matches_settled: int
    odds_rows: int
    last_round: Optional[int] = None
    last_expected_start_utc: Optional[str] = None
    last_expected_start_local: Optional[str] = None
    db_size_mb: Optional[float] = None
    league_id: int


class BacktestSelectionSchema(BaseModel):
    market: str
    selection: str
    n: int
    win_pct: float
    avg_odds: float
    roi: float
    roi_ci_low: float
    roi_ci_high: float
    positive_ci: bool


class BacktestResponseSchema(BaseModel):
    has_odds: bool
    tested: int
    positive_ci_count: int
    selections: List[BacktestSelectionSchema]


class MatchRowSchema(BaseModel):
    round: Optional[int] = None
    expected_start: Optional[str] = None
    home: Optional[str] = None
    away: Optional[str] = None
    ft_score: Optional[str] = None
    ht_score: Optional[str] = None
    total_goals: Optional[int] = None
    btts: Optional[int] = None
    result_1x2: Optional[str] = None
    ht_result: Optional[str] = None


class MatchListSchema(BaseModel):
    count: int
    limit: int
    offset: int
    matches: List[MatchRowSchema]
