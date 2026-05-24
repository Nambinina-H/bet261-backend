from typing import Optional

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class Goal(Base):
    """Un but marque dans un match (minute par minute)."""
    __tablename__ = "goals"
    __table_args__ = (
        UniqueConstraint("match_key", "minute", "team", "home_score", "away_score",
                         name="uq_goal"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_key: Mapped[str] = mapped_column(String(120), index=True)
    minute: Mapped[Optional[int]] = mapped_column(Integer)
    team: Mapped[Optional[str]] = mapped_column(String(10))   # Home / Away
    home_score: Mapped[Optional[int]] = mapped_column(Integer)
    away_score: Mapped[Optional[int]] = mapped_column(Integer)
