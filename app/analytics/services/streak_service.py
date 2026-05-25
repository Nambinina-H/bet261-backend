import math

from sqlalchemy.orm import Session

from app.analytics.handler.stats import Z, wilson
from app.analytics.repository.analytics_repository import AnalyticsRepository


class StreakService:
    """Teste la strategie 'parier sur une equipe apres une serie de defaites/victoires'."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository()

    def backtest(self, streak_len: int = 3, streak_type: str = "loss"):
        book, wld = self.repo.streak_backtest(self.db, streak_len, streak_type)
        n = len(book)
        label = ("defaites" if streak_type == "loss" else "victoires")
        result = {
            "bet": f"parier la victoire d'une equipe apres {streak_len} {label} d'affilee",
            "streak": streak_len,
            "streak_type": streak_type,
            "situations": n,
        }
        if n == 0:
            result["note"] = "Aucune situation de ce type en base (pas assez de donnees ou serie trop longue)."
            return result

        # Issue reelle du match suivant (teste l'idee 'l'equipe est due pour gagner')
        tot = sum(wld.values())
        result["next_match_outcome"] = {
            "win": {"n": wld["W"], "pct": round(wld["W"] / tot, 4)},
            "draw": {"n": wld["D"], "pct": round(wld["D"] / tot, 4)},
            "loss": {"n": wld["L"], "pct": round(wld["L"] / tot, 4)},
        }
        p, lo, hi = wilson(wld["W"], tot)
        result["win_pct"] = round(p, 4)
        result["win_ci_low"] = round(lo, 4)
        result["win_ci_high"] = round(hi, 4)

        # ROI du pari (sur les situations ou la cote 1X2 est connue)
        with_odds = [(w, o) for w, o in book if o and o > 0]
        if with_odds:
            m = len(with_odds)
            returns = [(o - 1) if w else -1 for w, o in with_odds]
            roi = sum(returns) / m
            var = max(0.0, sum(r * r for r in returns) / m - roi * roi)
            ci = Z * math.sqrt(var / m) if m else 0
            result["roi"] = {
                "n_with_odds": m,
                "avg_odds": round(sum(o for _, o in with_odds) / m, 3),
                "roi": round(roi, 4),
                "roi_ci_low": round(roi - ci, 4),
                "roi_ci_high": round(roi + ci, 4),
                "positive_ci": (roi - ci) > 0,
            }
        else:
            result["roi"] = {"note": "Pas encore de cotes capturees pour ces situations."}
        return result
