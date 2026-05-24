import os

from sqlalchemy.orm import Session

from app.analytics.handler.stats import to_local_iso
from app.analytics.repository.analytics_repository import AnalyticsRepository
from app.env.settings import get_settings


class HealthService:
    """Etat de la collecte (pour /health)."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository()

    def health(self):
        settings = get_settings()
        data = self.repo.health(self.db)
        data["last_expected_start_local"] = to_local_iso(
            data.get("last_expected_start_utc"), settings.tz_offset)
        # taille de la base si SQLite fichier
        url = settings.database_url
        if url.startswith("sqlite:///"):
            path = url.replace("sqlite:///", "")
            try:
                data["db_size_mb"] = round(os.path.getsize(path) / 1e6, 2)
            except OSError:
                data["db_size_mb"] = None
        data["league_id"] = settings.league_id
        return data
