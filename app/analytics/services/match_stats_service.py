import math

from sqlalchemy.orm import Session

from app.analytics.handler.stats import chi2_sf, ci_dict
from app.analytics.repository.analytics_repository import AnalyticsRepository


class MatchStatsService:
    """Statistiques issues de la table matches (un seul scan, mis en cache)."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository()
        self._A = None

    def _agg(self):
        if self._A is None:
            self._A = self.repo.aggregate_matches(self.db)
        return self._A

    def overview(self):
        A = self._agg()
        return {"matches_analyzed": A["n"], "period_utc": [A["start_min"], A["start_max"]],
                "distinct_rounds": len(A["rounds"])}

    def results(self):
        A = self._agg(); n = A["n"]
        return {"n": n,
                "result_1x2": {k: ci_dict(v, n) for k, v in A["res"].items()},
                "halftime": {k: ci_dict(v, n) for k, v in A["ht"].items()},
                "htft": {k: ci_dict(v, n)
                         for k, v in sorted(A["htft"].items(), key=lambda x: -x[1])}}

    def goals(self):
        A = self._agg(); n = A["n"]; tgc = A["tg"]
        avg = sum(g * c for g, c in tgc.items()) / n if n else 0
        maxg = max(tgc) if tgc else 0
        over = {f"over_{line}": ci_dict(sum(c for g, c in tgc.items() if g > line), n)
                for line in (0.5, 1.5, 2.5, 3.5, 4.5)}
        return {"n": n, "avg_goals": round(avg, 3), "max_goals": maxg,
                "distribution": {g: ci_dict(tgc.get(g, 0), n) for g in range(0, maxg + 1)},
                "over_under": over, "btts": ci_dict(A["btts"], n)}

    def by_hour(self, tz_offset: int = 3):
        A = self._agg()
        out = []
        for h in sorted(A["hour"]):
            g = A["hour"][h]; nn = g["n"]
            if not nn:
                continue
            out.append({"hour_local": (h + tz_offset) % 24, "hour_utc": h, "n": nn,
                        "pct_1": round(g["1"] / nn, 4), "pct_X": round(g["X"] / nn, 4),
                        "pct_2": round(g["2"] / nn, 4), "avg_goals": round(g["g"] / nn, 3),
                        "over_2_5": round(g["o25"] / nn, 4)})
        out.sort(key=lambda x: x["hour_local"])
        return {"tz_offset": tz_offset, "timezone": f"UTC{tz_offset:+d}", "by_hour": out}

    def by_team(self):
        A = self._agg()
        self.repo.aggregate_odds(self.db, A["team"])  # remplit la proba implicite
        out = []
        for team, s in A["team"].items():
            nn = s["n"]
            if not nn:
                continue
            wins = s["hw"] + s["aw"]
            imp = (s["imp_sum"] / s["imp_n"]) if s["imp_n"] else None
            out.append({"team": team, "n": nn, "wins": wins, "win_pct": round(wins / nn, 4),
                        "goals_for_avg": round(s["gf"] / nn, 3),
                        "goals_against_avg": round(s["ga"] / nn, 3),
                        "implied_prob_avg": round(imp, 4) if imp is not None else None})
        out.sort(key=lambda x: -x["wins"])
        return {"by_team": out}

    def randomness(self):
        A = self._agg(); n = A["n"]; tgc = A["tg"]
        if n < 30:
            return {"enough_data": False, "n": n}
        lam = sum(g * c for g, c in tgc.items()) / n
        maxg = max(tgc) if tgc else 0
        cells, exp_cells = [], []
        for g in range(0, maxg + 1):
            exp_cells.append(n * math.exp(-lam) * lam ** g / math.factorial(g))
            cells.append(tgc.get(g, 0))
        if exp_cells:
            exp_cells[-1] = max(1e-9, n - sum(exp_cells[:-1]))
        stat = sum((o - e) ** 2 / e for o, e in zip(cells, exp_cells) if e > 0)
        df = max(1, len(cells) - 2)
        pv = chi2_sf(stat, df)
        return {"enough_data": True, "n": n, "lambda": round(lam, 3),
                "poisson_chi2": round(stat, 3), "df": df, "p_value": round(pv, 4),
                "poisson_compatible": pv > 0.05, "result_runs": A["runs"]}
