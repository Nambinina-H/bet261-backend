from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_key(start: str, home: str, away: str) -> str:
    return f"{start}|{home}|{away}"


def parse_score(s):
    """'2:1' -> (2, 1) ; renvoie (None, None) si non parsable."""
    try:
        a, b = (s or ":").split(":")
        return int(a), int(b)
    except (ValueError, IndexError):
        return None, None


def derive_hour_weekday(start: str):
    try:
        dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        return dt.hour, dt.weekday()
    except (ValueError, AttributeError):
        return None, None


def is_valid_start(start) -> bool:
    return bool(start) and not str(start).startswith("0001")
