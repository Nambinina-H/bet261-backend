from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analytics.repository.analytics_repository import AnalyticsRepository
from app.analytics.schemas.analytics_schema import (
    BacktestResponseSchema, HealthSchema, MatchListSchema,
)
from app.analytics.services.health_service import HealthService
from app.analytics.services.match_stats_service import MatchStatsService
from app.analytics.services.odds_stats_service import OddsStatsService
from app.analytics.services.timing_service import TimingService
from app.common.decorator.api_endpoint import api_endpoint
from app.common.dependencies import require_api_key
from app.database.database_session import get_db
from app.env.settings import get_settings

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _guard(db: Session):
    if AnalyticsRepository().count_settled(db) == 0:
        raise HTTPException(status_code=503,
                            detail="Aucun match joue en base. Laisse tourner le collecteur.")


@router.get("/health", response_model=HealthSchema, summary="Etat de la collecte")
@api_endpoint
def health(db: Session = Depends(get_db)):
    return HealthService(db).health()


@router.get("/overview", summary="Echantillon & periode")
@api_endpoint
def overview(db: Session = Depends(get_db), _=Depends(require_api_key)):
    _guard(db)
    return MatchStatsService(db).overview()


@router.get("/results", summary="1X2, mi-temps, HT/FT (+ IC 95%)")
@api_endpoint
def results(db: Session = Depends(get_db), _=Depends(require_api_key)):
    _guard(db)
    return MatchStatsService(db).results()


@router.get("/goals", summary="Buts : moyenne, distribution, O/U, BTTS")
@api_endpoint
def goals(db: Session = Depends(get_db), _=Depends(require_api_key)):
    _guard(db)
    return MatchStatsService(db).goals()


@router.get("/timing", summary="Minutage des buts (tranches 15 min)")
@api_endpoint
def timing(db: Session = Depends(get_db), _=Depends(require_api_key)):
    return TimingService(db).timing()


@router.get("/by-hour", summary="Distribution par heure (locale, defaut UTC+3)")
@api_endpoint
def by_hour(
    tz_offset: int = Query(get_settings().tz_offset, ge=-12, le=14),
    db: Session = Depends(get_db),
    _=Depends(require_api_key),
):
    _guard(db)
    return MatchStatsService(db).by_hour(tz_offset=tz_offset)


@router.get("/by-team", summary="Stats par equipe + proba implicite")
@api_endpoint
def by_team(db: Session = Depends(get_db), _=Depends(require_api_key)):
    _guard(db)
    return MatchStatsService(db).by_team()


@router.get("/calibration", summary="Cotes : proba implicite vs reel")
@api_endpoint
def calibration(db: Session = Depends(get_db), _=Depends(require_api_key)):
    _guard(db)
    return OddsStatsService(db).calibration()


@router.get("/backtest", response_model=BacktestResponseSchema,
            summary="Backtest value-bet (EV/ROI + IC)")
@api_endpoint
def backtest(
    min_samples: int = Query(200, ge=1),
    limit: int = Query(30, ge=1, le=500),
    db: Session = Depends(get_db),
    _=Depends(require_api_key),
):
    _guard(db)
    return OddsStatsService(db).backtest(min_samples=min_samples, limit=limit)


@router.get("/randomness", summary="Tests d'aleatoire (chi2 vs Poisson)")
@api_endpoint
def randomness(db: Session = Depends(get_db), _=Depends(require_api_key)):
    _guard(db)
    return MatchStatsService(db).randomness()


@router.get("/matches", response_model=MatchListSchema,
            summary="Liste des matchs joues (paginee, filtrable)")
@api_endpoint
def matches(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    team: Optional[str] = Query(None),
    round_no: Optional[int] = Query(None, alias="round"),
    db: Session = Depends(get_db),
    _=Depends(require_api_key),
):
    rows = AnalyticsRepository().list_matches(db, limit=limit, offset=offset,
                                              team=team, round_no=round_no)
    return {"count": len(rows), "limit": limit, "offset": offset, "matches": rows}
