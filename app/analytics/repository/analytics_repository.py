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

    # ----- Backtest par serie (streak) ------------------------------------- #
    def streak_backtest(self, db: Session, streak_len: int = 3, streak_type: str = "loss"):
        """Pour chaque equipe, parcourt ses matchs dans l'ordre chronologique.
        Quand elle entre dans un match avec `streak_len` resultats `streak_type`
        d'affilee (loss/win), on enregistre le pari 'cette equipe gagne ce match'
        (avec la cote 1X2 correspondante) et l'issue reelle.
        Renvoie (book, wld) : book=[(gagne 0/1, cote|None)], wld=compteur W/D/L."""
        target = "L" if streak_type == "loss" else "W"
        # cotes 1X2 par match (3 lignes/match, leger)
        odds = {}
        for k, sel, od in db.execute(text(
                "SELECT match_key, selection, odds FROM odds WHERE market='1X2'")).yield_per(BATCH):
            odds.setdefault(k, {})[sel] = od

        hist = defaultdict(list)   # equipe -> ['W','D','L', ...] chronologique
        book = []
        wld = {"W": 0, "D": 0, "L": 0}
        cur = db.execute(text(
            "SELECT match_key, home, away, result_1x2 FROM matches "
            "WHERE ft_score IS NOT NULL ORDER BY expected_start"))
        for (mk, home, away, res) in cur.yield_per(BATCH):
            home_res = "W" if res == "1" else ("D" if res == "X" else "L")
            away_res = "W" if res == "2" else ("D" if res == "X" else "L")
            for team, is_home, tres in ((home, True, home_res), (away, False, away_res)):
                h = hist[team]
                if len(h) >= streak_len and all(r == target for r in h[-streak_len:]):
                    wld[tres] += 1
                    od = odds.get(mk, {}).get("1" if is_home else "2")
                    book.append((1 if tres == "W" else 0, od))
            hist[home].append(home_res)
            hist[away].append(away_res)
        return book, wld

    # ----- Tete-a-tete (head-to-head) -------------------------------------- #
    def head_to_head(self, db: Session, min_matches: int = 5):
        """Regroupe les matchs par duel (home, away). Pour chaque duel revenu
        au moins `min_matches` fois, agrege : victoires dom/nul/ext, proba
        implicite domicile (1/cote '1'), et returns du pari 'domicile gagne'."""
        od1 = {}
        for k, od in db.execute(text(
                "SELECT match_key, odds FROM odds WHERE market='1X2' AND selection='1'")).yield_per(BATCH):
            od1[k] = od

        agg = defaultdict(lambda: {"n": 0, "hw": 0, "dw": 0, "aw": 0,
                                   "imp_sum": 0.0, "imp_n": 0,
                                   "ret_sum": 0.0, "ret_sq": 0.0, "ret_n": 0})
        cur = db.execute(text(
            "SELECT match_key, home, away, result_1x2 FROM matches WHERE ft_score IS NOT NULL"))
        for (mk, home, away, res) in cur.yield_per(BATCH):
            a = agg[(home, away)]
            a["n"] += 1
            if res == "1":
                a["hw"] += 1
            elif res == "X":
                a["dw"] += 1
            else:
                a["aw"] += 1
            od = od1.get(mk)
            if od and od > 0:
                a["imp_sum"] += 1.0 / od
                a["imp_n"] += 1
                ret = (od - 1) if res == "1" else -1
                a["ret_sum"] += ret
                a["ret_sq"] += ret * ret
                a["ret_n"] += 1
        return {pair: a for pair, a in agg.items() if a["n"] >= min_matches}

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
