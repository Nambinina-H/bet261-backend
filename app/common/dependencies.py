from typing import Optional

from fastapi import Header, HTTPException

from app.env.settings import get_settings


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Si une cle API est configuree (settings.api_key), l'exige via X-API-Key.
    Sinon (usage local), laisse passer."""
    settings = get_settings()
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Cle API invalide ou manquante (X-API-Key).")
