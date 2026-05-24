from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base

from app.env.settings import get_settings

settings = get_settings()

# check_same_thread=False : l'API (threadpool FastAPI) et le job scheduler
# partagent la meme base SQLite.
engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)


# Active le mode WAL : plusieurs lecteurs (API) en parallele d'un ecrivain (collecteur).
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()


Base = declarative_base()
