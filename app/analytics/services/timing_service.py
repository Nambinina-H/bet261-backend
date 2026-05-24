from sqlalchemy.orm import Session

from app.analytics.repository.analytics_repository import AnalyticsRepository


class TimingService:
    """Distribution des buts par tranche de 15 minutes."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository()

    def timing(self):
        counts, tot, summ = self.repo.aggregate_goal_minutes(self.db)
        if tot == 0:
            return {"total_goals_logged": 0, "avg_minute": None, "buckets": {}}
        return {"total_goals_logged": tot, "avg_minute": round(summ / tot, 2),
                "buckets": {f"{a}-{b}": {"goals": c, "share": round(c / tot, 4)}
                            for (a, b), c in counts.items()}}
