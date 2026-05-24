"""Acces aux donnees pour l'analyse, en mode STREAMING (yield_per) : la memoire
reste ~constante quelle que soit la taille de la base (adapte a un VPS 1 Go)."""
from collections import Counter, defaultdict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.analytics.handler.stats import selection_won

BATCH = 5000


class AnalyticsRepository:

    # ----- Passe 1 : table matches (sans cotes) ---------------------------- #
    def aggregate_matches(self, db: Session) -> dict:
        sql = text("""SELECT round, expected_start, hour_utc, home, away,
                             ft_home, ft_away, ht_home, ht_away, total_goals,
                             btts, result_1x2, ht_result
                      FROM matches WHERE ft_score IS NOT NULL ORDER BY expected_start""")
        A = {"n": 0, "res": Counter(), "ht": Counter(), "htft": Counter(), "tg": Counter(),
             "btts": 0, "rounds": set(), "start_min": None, "start_max": None,
             "hour": defaultdict(lambda: {"n": 0, "1": 0, "X": 0, "2": 0, "g": 0, "o25": 0}),
             "team": defaultdict(lambda: {"n": 0, "hw": 0, "aw": 0, "gf": 0, "ga": 0,
                                          "imp_sum": 0.0, "imp_n": 0}),
             "runs": 0, "_prev": None}
        for row in db.execute(sql).yield_per(BATCH):
            (rnd, start, hour, home, away, fh, fa, hh, ha, tg, btts, res, htr) = row
            A["n"] += 1
            A["res"][res] += 1; A["ht"][htr] += 1; A["htft"][f"{htr}/{res}"] += 1
            A["tg"][tg] += 1
            if btts == 1:
                A["btts"] += 1
            if rnd is not None:
                A["rounds"].add(rnd)
            if start:
                if A["start_min"] is None or start < A["start_min"]:
                    A["start_min"] = start
                if A["start_max"] is None or start > A["start_max"]:
                    A["start_max"] = start
            if hour is not None:
                h = A["hour"][hour]; h["n"] += 1; h[res] += 1; h["g"] += tg
                if tg > 2.5:
                    h["o25"] += 1
            th, ta = A["team"][home], A["team"][away]
            th["n"] += 1; ta["n"] += 1
            th["gf"] += fh; th["ga"] += fa; ta["gf"] += fa; ta["ga"] += fh
            if res == "1":
                th["hw"] += 1
            elif res == "2":
                ta["aw"] += 1
            if A["_prev"] is not None and res != A["_prev"]:
                A["runs"] += 1
            A["_prev"] = res
        if A["n"]:
            A["runs"] += 1
        return A

    # ----- Passe 2 : table goals ------------------------------------------- #
    def aggregate_goal_minutes(self, db: Session):
        buckets = [(0, 15), (16, 30), (31, 45), (46, 60), (61, 75), (76, 90)]
        counts = {b: 0 for b in buckets}
        tot, summ = 0, 0
        for (mn,) in db.execute(text("SELECT minute FROM goals WHERE minute IS NOT NULL")).yield_per(BATCH):
            tot += 1; summ += mn
            for a, b in buckets:
                if a <= mn <= b:
                    counts[(a, b)] += 1
                    break
        return counts, tot, summ

    # ----- Passe 3 : jointure odds x matches (sur disque) ------------------ #
    def aggregate_odds(self, db: Session, team_stats=None):
        sql = text("""SELECT o.market, o.selection, o.odds, m.result_1x2, m.ht_result,
                             m.total_goals, m.ft_home, m.ft_away, m.ht_home, m.ht_away,
                             m.btts, m.home, m.away
                      FROM odds o JOIN matches m ON o.match_key = m.match_key
                      WHERE m.ft_score IS NOT NULL""")
        cb = [(0, .1), (.1, .2), (.2, .3), (.3, .4), (.4, .5), (.5, .7), (.7, 1.01)]
        calib = {b: {"n": 0, "imp": 0.0, "won": 0} for b in cb}
        book = defaultdict(lambda: [0, 0, 0.0, 0.0, 0.0])  # n, wins, sodds, sret, sret2
        any_odds = False
        for row in db.execute(sql).yield_per(BATCH):
            (market, sel, od, res, htr, tg, fh, fa, hh, ha, btts, home, away) = row
            any_odds = True
            if not od or od <= 0:
                continue
            if market == "1X2":
                imp = 1.0 / od
                won_1x2 = 1 if res == sel else 0
                for lo, hi in cb:
                    if lo <= imp < hi:
                        c = calib[(lo, hi)]; c["n"] += 1; c["imp"] += imp; c["won"] += won_1x2
                        break
                if team_stats is not None:
                    if sel == "1" and home in team_stats:
                        team_stats[home]["imp_sum"] += imp; team_stats[home]["imp_n"] += 1
                    elif sel == "2" and away in team_stats:
                        team_stats[away]["imp_sum"] += imp; team_stats[away]["imp_n"] += 1
            won = selection_won(market, sel, res, htr, tg, fh, fa, hh, ha, btts)
            if won is None:
                continue
            agg = book[(market, sel)]
            ret = (od - 1) if won else -1
            agg[0] += 1; agg[1] += 1 if won else 0; agg[2] += od; agg[3] += ret; agg[4] += ret * ret
        return calib, book, any_odds

    # ----- Sante & liste --------------------------------------------------- #
    def health(self, db: Session) -> dict:
        row = db.execute(text(
            "SELECT COUNT(*), SUM(CASE WHEN ft_score IS NOT NULL THEN 1 ELSE 0 END), "
            "MAX(expected_start) FROM matches")).first()
        total, settled, last_start = (row[0] or 0), (row[1] or 0), row[2]
        last_round = db.execute(text(
            "SELECT round FROM matches WHERE ft_score IS NOT NULL "
            "ORDER BY expected_start DESC LIMIT 1")).first()
        n_odds = db.execute(text("SELECT COUNT(*) FROM odds")).scalar() or 0
        return {"matches_total": total, "matches_settled": settled, "odds_rows": n_odds,
                "last_round": last_round[0] if last_round else None,
                "last_expected_start_utc": last_start}

    def count_settled(self, db: Session) -> int:
        return db.execute(text("SELECT COUNT(*) FROM matches WHERE ft_score IS NOT NULL")).scalar() or 0

    def list_matches(self, db: Session, limit=50, offset=0, team=None, round_no=None):
        sql = ("SELECT round, expected_start, home, away, ft_score, ht_score, "
               "total_goals, btts, result_1x2, ht_result FROM matches WHERE ft_score IS NOT NULL")
        params = {}
        if team:
            sql += " AND (home = :team OR away = :team)"; params["team"] = team
        if round_no is not None:
            sql += " AND round = :round_no"; params["round_no"] = round_no
        sql += " ORDER BY expected_start DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit; params["offset"] = offset
        cols = ["round", "expected_start", "home", "away", "ft_score", "ht_score",
                "total_goals", "btts", "result_1x2", "ht_result"]
        return [dict(zip(cols, r)) for r in db.execute(text(sql), params).all()]
