from sqlalchemy.orm import Session

from app.collector.client.bet261_client import Bet261Client
from app.collector.handler.market_filter import is_core_market
from app.collector.handler.parsing import (
    derive_hour_weekday, is_valid_start, make_key, now_iso,
)
from app.collector.repository.match_repository import MatchRepository
from app.collector.repository.odds_repository import OddRepository
from app.env.settings import get_settings


class CollectOddsService:
    """Collecte les cotes (endpoint /matches : rounds a venir)."""

    def __init__(self, db: Session, client: Bet261Client | None = None):
        self.db = db
        self.client = client or Bet261Client(get_settings().league_id)
        self.match_repo = MatchRepository()
        self.odds_repo = OddRepository()

    def execute(self, all_markets: bool = False):
        data = self.client.get_matches()
        ts = now_iso()
        n_matches, n_odds = 0, 0

        for rd in data.get("rounds", []):
            start = rd.get("expectedStart")
            if not is_valid_start(start):
                continue
            hour, weekday = derive_hour_weekday(start)
            rno = rd.get("roundNumber")

            for m in rd.get("matches", []):
                home = (m.get("homeTeam") or {}).get("name", "")
                away = (m.get("awayTeam") or {}).get("name", "")
                key = make_key(start, home, away)

                if self.match_repo.ensure(
                    self.db, match_key=key, round=rno, expected_start=start,
                    hour_utc=hour, weekday=weekday, home=home, away=away, first_seen=ts,
                ):
                    n_matches += 1

                for bt in m.get("eventBetTypes", []):
                    btid = bt.get("betTypeId")
                    name = bt.get("name", "")
                    if not all_markets and not is_core_market(btid, name):
                        continue
                    for it in bt.get("eventBetTypeItems", []):
                        sel = it.get("shortName", "")
                        od = it.get("odds")
                        if od is None:
                            continue
                        self.odds_repo.save(self.db, key, name, btid, sel, float(od), ts)
                        n_odds += 1

        self.db.commit()
        return n_matches, n_odds
