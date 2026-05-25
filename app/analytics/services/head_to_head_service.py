import math

from sqlalchemy.orm import Session

from app.analytics.handler.stats import Z, wilson
from app.analytics.repository.analytics_repository import AnalyticsRepository


class HeadToHeadService:
    """Resultats par duel (A domicile vs B exterieur) compares aux cotes."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository()

    def analyze(self, min_matches: int = 5, limit: int = 30):
        agg = self.repo.head_to_head(self.db, min_matches)
        rows = []
        for (home, away), a in agg.items():
            n = a["n"]
            p, lo, hi = wilson(a["hw"], n)   # taux de victoire domicile
            implied = (a["imp_sum"] / a["imp_n"]) if a["imp_n"] else None
            gap = (p - implied) if implied is not None else None

            roi_block = None
            if a["ret_n"]:
                m = a["ret_n"]
                roi = a["ret_sum"] / m
                var = max(0.0, a["ret_sq"] / m - roi * roi)
                ci = Z * math.sqrt(var / m) if m else 0
                roi_block = {
                    "roi": round(roi, 4),
                    "roi_ci_low": round(roi - ci, 4),
                    "roi_ci_high": round(roi + ci, 4),
                    "positive_ci": (roi - ci) > 0,
                }

            rows.append({
                "home": home, "away": away, "n": n,
                "home_win_pct": round(p, 4),
                "draw_pct": round(a["dw"] / n, 4),
                "away_win_pct": round(a["aw"] / n, 4),
                "implied_home": round(implied, 4) if implied is not None else None,
                "gap": round(gap, 4) if gap is not None else None,
                "home_win_ci_low": round(lo, 4),
                "home_win_ci_high": round(hi, 4),
                "bet_home_roi": roi_block,
            })

        # tri par ecart (gap) decroissant : les duels les plus "sous-cotes" en tete
        rows.sort(key=lambda r: r["gap"] if r["gap"] is not None else -999, reverse=True)
        positive = sum(1 for r in rows
                       if r["bet_home_roi"] and r["bet_home_roi"]["positive_ci"])
        return {
            "min_matches": min_matches,
            "pairings_tested": len(rows),
            "positive_ci_count": positive,
            "head_to_head": rows[:limit],
        }
