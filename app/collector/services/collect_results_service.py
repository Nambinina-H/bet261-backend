from sqlalchemy.orm import Session

from app.collector.client.bet261_client import Bet261Client
from app.collector.handler.parsing import (
    derive_hour_weekday, is_valid_start, make_key, now_iso, parse_score,
)
from app.collector.repository.goal_repository import GoalRepository
from app.collector.repository.match_repository import MatchRepository
from app.env.settings import get_settings


class CollectResultsService:
    """Collecte les resultats (endpoint /results : rounds joues)."""

    def __init__(self, db: Session, client: Bet261Client | None = None):
        self.db = db
        self.client = client or Bet261Client(get_settings().league_id)
        self.match_repo = MatchRepository()
        self.goal_repo = GoalRepository()

    def execute(self, take: int = 20):
        data = self.client.get_results(take=take)
        ts = now_iso()
        n_settled, n_goals = 0, 0

        for rd in data.get("rounds", []):
            rno = rd.get("roundNumber")
            rstart = rd.get("expectedStart")

            for m in rd.get("matches", []):
                home = (m.get("homeTeam") or {}).get("name", "")
                away = (m.get("awayTeam") or {}).get("name", "")
                start = rstart if is_valid_start(rstart) else m.get("expectedStart")
                if not is_valid_start(start):
                    continue

                fh, fa = parse_score(m.get("score"))
                hh, ha = parse_score(m.get("halfTimeScore"))
                if fh is None:
                    continue  # pas encore termine

                key = make_key(start, home, away)
                hour, weekday = derive_hour_weekday(start)
                res = "1" if fh > fa else ("2" if fh < fa else "X")
                htr = "1" if hh > ha else ("2" if hh < ha else "X")
                btts = 1 if (fh > 0 and fa > 0) else 0

                self.match_repo.settle(
                    self.db, match_key=key, round=rno, expected_start=start,
                    hour_utc=hour, weekday=weekday, home=home, away=away,
                    ft_score=m.get("score"), ht_score=m.get("halfTimeScore"),
                    ft_home=fh, ft_away=fa, ht_home=hh, ht_away=ha,
                    total_goals=fh + fa, btts=btts, result_1x2=res, ht_result=htr,
                    settled_at=ts,
                )
                n_settled += 1

                for g in m.get("goals", []):
                    self.goal_repo.save(self.db, key, g.get("minute"), g.get("team"),
                                        g.get("homeScore"), g.get("awayScore"))
                    n_goals += 1

        self.db.commit()
        return n_settled, n_goals
