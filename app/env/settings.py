from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Environnement
    environment: str = "local"

    # Ligue virtuelle ciblee (English League par defaut)
    league_id: int = 8035

    # Domaine du site : utilise pour les en-tetes Origin/Referer (anti-bot de l'API)
    site_origin: str = "https://bet261.mg"

    # Base de donnees (SQLite ; le mode WAL est active dans database.py)
    database_url: str = "sqlite:///bet261.db"
    sql_echo: bool = False               # True = logge chaque requete SQL (debug)

    # Collecte
    poll_interval_seconds: int = 60      # un cycle de collecte / 60 s
    all_markets: bool = False            # False = marches "coeur" ; True = 33 marches
    enable_scheduler: bool = True        # desactivable en test

    # Analyse
    tz_offset: int = 3                   # heure locale Madagascar (UTC+3)

    # Securite optionnelle : si defini, exige l'entete X-API-Key
    api_key: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
