import math

from sqlalchemy.orm import Session

from app.analytics.handler.stats import Z, wilson
from app.analytics.repository.analytics_repository import AnalyticsRepository


class OddsStatsService:
    """Statistiques issues de la jointure cotes x resultats."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository()
        self._cache = None

    def _agg(self):
        if self._cache is None:
            self._cache = self.repo.aggregate_odds(self.db, None)
        return self._cache

    def calibration(self):
        calib, _, any_odds = self._agg()
        if not any_odds:
            return {"has_odds": False, "buckets": []}
        out = []
        for (lo, hi), c in calib.items():
            if not c["n"]:
                continue
            imp = c["imp"] / c["n"]; real = c["won"] / c["n"]
            out.append({"implied_range": [lo, round(hi, 2)], "n_bets": c["n"],
                        "implied_avg": round(imp, 4), "real_win": round(real, 4),
                        "gap": round(real - imp, 4)})
        return {"has_odds": True, "buckets": out}

    def backtest(self, min_samples: int = 200, limit: int = 30):
        _, book, any_odds = self._agg()
        if not any_odds or not book:
            return {"has_odds": any_odds, "tested": 0, "positive_ci_count": 0, "selections": []}
        rows = []
        for (market, sel), (cnt, wins, sodds, sret, sret2) in book.items():
            if cnt < min_samples:
                continue
            p, _, _ = wilson(wins, cnt)
            roi = sret / cnt
            var = max(0.0, sret2 / cnt - roi * roi)
            ci = Z * math.sqrt(var / cnt) if cnt else 0
            rows.append({"market": market, "selection": sel, "n": cnt,
                         "win_pct": round(p, 4), "avg_odds": round(sodds / cnt, 3),
                         "roi": round(roi, 4), "roi_ci_low": round(roi - ci, 4),
                         "roi_ci_high": round(roi + ci, 4), "positive_ci": (roi - ci) > 0})
        rows.sort(key=lambda r: -r["roi"])
        pos = sum(1 for r in rows if r["positive_ci"])
        return {"has_odds": True, "tested": len(rows), "positive_ci_count": pos,
                "selections": rows[:limit]}
