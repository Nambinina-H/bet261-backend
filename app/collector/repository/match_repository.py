from sqlalchemy.orm import Session

from app.collector.models.match import Match


class MatchRepository:
    def ensure(self, db: Session, *, match_key, round, expected_start,
               hour_utc, weekday, home, away, first_seen) -> bool:
        """Cree la ligne (pre-match) si elle n'existe pas. Renvoie True si creee."""
        if db.get(Match, match_key) is not None:
            return False
        db.add(Match(
            match_key=match_key, round=round, expected_start=expected_start,
            hour_utc=hour_utc, weekday=weekday, home=home, away=away,
            first_seen=first_seen,
        ))
        return True

    def settle(self, db: Session, *, match_key, round, expected_start, hour_utc, weekday,
               home, away, ft_score, ht_score, ft_home, ft_away, ht_home, ht_away,
               total_goals, btts, result_1x2, ht_result, settled_at) -> None:
        """Renseigne le resultat. Cree la ligne si on n'avait pas vu les cotes."""
        m = db.get(Match, match_key)
        if m is None:
            db.add(Match(
                match_key=match_key, round=round, expected_start=expected_start,
                hour_utc=hour_utc, weekday=weekday, home=home, away=away,
                ft_score=ft_score, ht_score=ht_score, ft_home=ft_home, ft_away=ft_away,
                ht_home=ht_home, ht_away=ht_away, total_goals=total_goals, btts=btts,
                result_1x2=result_1x2, ht_result=ht_result,
                first_seen=settled_at, settled_at=settled_at,
            ))
        elif m.ft_score is None:
            m.round = round
            m.ft_score, m.ht_score = ft_score, ht_score
            m.ft_home, m.ft_away = ft_home, ft_away
            m.ht_home, m.ht_away = ht_home, ht_away
            m.total_goals, m.btts = total_goals, btts
            m.result_1x2, m.ht_result = result_1x2, ht_result
            m.settled_at = settled_at
