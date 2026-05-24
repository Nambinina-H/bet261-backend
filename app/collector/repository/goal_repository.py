from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.collector.models.goal import Goal


class GoalRepository:
    def save(self, db: Session, match_key, minute, team, home_score, away_score) -> None:
        """Insert idempotent (ignore les doublons grace a la contrainte unique)."""
        stmt = insert(Goal).values(
            match_key=match_key, minute=minute, team=team,
            home_score=home_score, away_score=away_score,
        ).on_conflict_do_nothing()
        db.execute(stmt)
