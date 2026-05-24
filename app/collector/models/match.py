from typing import Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class Match(Base):
    """Un match (rencontre d'un round). Cle = expected_start|home|away (globale unique)."""
    __tablename__ = "matches"

    match_key: Mapped[str] = mapped_column(String(120), primary_key=True)
    round: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    expected_start: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    hour_utc: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    weekday: Mapped[Optional[int]] = mapped_column(Integer)
    home: Mapped[Optional[str]] = mapped_column(String(60))
    away: Mapped[Optional[str]] = mapped_column(String(60))

    ft_score: Mapped[Optional[str]] = mapped_column(String(10))
    ht_score: Mapped[Optional[str]] = mapped_column(String(10))
    ft_home: Mapped[Optional[int]] = mapped_column(Integer)
    ft_away: Mapped[Optional[int]] = mapped_column(Integer)
    ht_home: Mapped[Optional[int]] = mapped_column(Integer)
    ht_away: Mapped[Optional[int]] = mapped_column(Integer)
    total_goals: Mapped[Optional[int]] = mapped_column(Integer)
    btts: Mapped[Optional[int]] = mapped_column(Integer)        # 0/1
    result_1x2: Mapped[Optional[str]] = mapped_column(String(1))
    ht_result: Mapped[Optional[str]] = mapped_column(String(1))

    first_seen: Mapped[Optional[str]] = mapped_column(String(40))   # 1ere capture (pre-match)
    settled_at: Mapped[Optional[str]] = mapped_column(String(40))   # capture du resultat
