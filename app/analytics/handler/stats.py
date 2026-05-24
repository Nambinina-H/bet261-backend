"""Outils statistiques (bibliotheque standard uniquement)."""
import math
from datetime import datetime, timedelta, timezone

Z = 1.96  # 95 %


def wilson(k, n, z=Z):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    demi = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (p, max(0.0, centre - demi), min(1.0, centre + demi))


def ci_dict(k, n):
    p, lo, hi = wilson(k, n)
    return {"n": k, "total": n, "freq": round(p, 4),
            "ci_low": round(lo, 4), "ci_high": round(hi, 4)}


def _gammainc_lower_reg(s, x, itmax=300, eps=1e-12):
    if x <= 0:
        return 0.0
    if x < s + 1:
        term = 1.0 / s
        total = term
        n = s
        for _ in range(itmax):
            n += 1
            term *= x / n
            total += term
            if abs(term) < abs(total) * eps:
                break
        return total * math.exp(-x + s * math.log(x) - math.lgamma(s))
    b = x + 1 - s
    c = 1e30
    d = 1.0 / b
    h = d
    for i in range(1, itmax):
        an = -i * (i - s)
        b += 2
        d = an * d + b
        if abs(d) < 1e-30:
            d = 1e-30
        c = b + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    q = math.exp(-x + s * math.log(x) - math.lgamma(s)) * h
    return 1.0 - q


def chi2_sf(stat, df):
    if stat <= 0:
        return 1.0
    return max(0.0, 1.0 - _gammainc_lower_reg(df / 2.0, stat / 2.0))


def to_local_iso(utc_iso, offset_hours=3):
    if not utc_iso:
        return None
    try:
        dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
        loc = dt.astimezone(timezone(timedelta(hours=offset_hours)))
        return loc.strftime("%Y-%m-%d %H:%M") + f" (UTC{offset_hours:+d})"
    except ValueError:
        return utc_iso


def selection_won(market, sel, res, htr, tg, fh, fa, hh, ha, btts):
    """True/False si la selection est gagnante, None si non resolvable."""
    sel = (sel or "").strip()
    name = (market or "").lower()
    if "ht/ft" in name or ("/" in sel and len(sel) == 3 and sel[1] == "/"):
        try:
            a, b = sel.split("/"); return (htr == a) and (res == b)
        except ValueError:
            return None
    if "mi-tps 1x2" in name or "mi-temps 1x2" in name:
        return htr == sel
    if name == "1x2":
        return res == sel
    if "double chance" in name and "mi" not in name:
        return {"1X": res in ("1", "X"), "X2": res in ("X", "2"), "12": res in ("1", "2")}.get(sel)
    if "mi-tps dc" in name:
        return {"1X": htr in ("1", "X"), "X2": htr in ("X", "2"), "12": htr in ("1", "2")}.get(sel)
    if sel.startswith(">") or sel.startswith("<"):
        try:
            line = float(sel.replace(">", "").replace("<", "").strip())
            return tg > line if sel.startswith(">") else tg < line
        except ValueError:
            return None
    if "total de buts" in name:
        try:
            v = int(sel); return tg >= 6 if v == 6 else tg == v
        except ValueError:
            return None
    if "score exact" in name and "mi" not in name:
        try:
            a, b = sel.replace(":", "-").split("-"); return fh == int(a) and fa == int(b)
        except ValueError:
            return None
    if "mi-tps cs" in name:
        try:
            a, b = sel.replace(":", "-").split("-"); return hh == int(a) and ha == int(b)
        except ValueError:
            return None
    if "g/ng" in name:
        s = sel.lower()
        if s in ("g", "gg", "oui", "yes"):
            return btts == 1
        if s in ("ng", "non", "no"):
            return btts == 0
        return None
    return None
