from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.collector.models.odd import Odd


class OddRepository:
    def save(self, db: Session, match_key, market, bet_type_id, selection, odds, captured_at) -> None:
        """Insert idempotent : on garde la 1ere cote vue pour (match, marche, selection)."""
        stmt = insert(Odd).values(
            match_key=match_key, market=market, bet_type_id=bet_type_id,
            selection=selection, odds=odds, captured_at=captured_at,
        ).on_conflict_do_nothing()
        db.execute(stmt)
