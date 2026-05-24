import logging
from datetime import datetime

from app.collector.services.collect_odds_service import CollectOddsService
from app.collector.services.collect_results_service import CollectResultsService
from app.database.database_session import SessionLocal
from app.env.settings import get_settings
from app.scheduler import scheduler

logger = logging.getLogger("bet261.collector")


def run_collection_cycle():
    """Un cycle : cotes (rounds a venir) puis resultats (rounds joues)."""
    settings = get_settings()
    db = SessionLocal()
    try:
        n_matches, n_odds = CollectOddsService(db).execute(all_markets=settings.all_markets)
        n_settled, n_goals = CollectResultsService(db).execute()
        logger.info("collecte: +%s matchs / +%s cotes | %s resultats vus / +%s buts",
                    n_matches, n_odds, n_settled, n_goals)
    except Exception as exc:
        logger.error("Echec du cycle de collecte: %s", exc, exc_info=True)
    finally:
        db.close()


def register_collector():
    """Enregistre le job de collecte sur le scheduler global (1 passe immediate, puis intervalle)."""
    settings = get_settings()
    scheduler.add_job(
        run_collection_cycle,
        trigger="interval",
        seconds=settings.poll_interval_seconds,
        id="bet261_collect",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(),
    )
    logger.info("Job de collecte enregistre (toutes les %ss).", settings.poll_interval_seconds)
