import httpx

from app.env.settings import get_settings


def _build_headers(origin: str) -> dict:
    """Reproduit les en-tetes du navigateur : l'API (stack SportyBet) renvoie 403
    sans Origin/Referer valides."""
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Origin": origin,
        "Referer": origin + "/",
    }


class Bet261Client:
    """Client HTTP synchrone vers l'API sporty-tech (publique) de Bet261."""

    def __init__(self, league_id: int):
        settings = get_settings()
        self.base = f"https://hg-event-api-prod.sporty-tech.net/api/instantleagues/{league_id}"
        self.headers = _build_headers(settings.site_origin)

    def get_matches(self) -> dict:
        """Rounds a venir + cotes."""
        r = httpx.get(f"{self.base}/matches", headers=self.headers, timeout=25.0)
        r.raise_for_status()
        return r.json()

    def get_results(self, take: int = 20) -> dict:
        """Derniers rounds joues (scores, mi-temps, buts)."""
        r = httpx.get(f"{self.base}/results", params={"skip": 0, "take": take},
                      headers=self.headers, timeout=25.0)
        r.raise_for_status()
        return r.json()
