from typing import Optional

from sqlalchemy import Float, Integer, String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class Odd(Base):
    """Une cote (marche/selection) capturee avant un match."""
    __tablename__ = "odds"
    __table_args__ = (
        UniqueConstraint("match_key", "bet_type_id", "selection", "market", name="uq_odd"),
        Index("ix_odds_market", "market", "selection"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_key: Mapped[str] = mapped_column(String(120), index=True)
    market: Mapped[Optional[str]] = mapped_column(String(60))
    bet_type_id: Mapped[Optional[int]] = mapped_column(Integer)
    selection: Mapped[Optional[str]] = mapped_column(String(20))
    odds: Mapped[Optional[float]] = mapped_column(Float)
    captured_at: Mapped[Optional[str]] = mapped_column(String(40))
