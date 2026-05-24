from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.analytics.controllers.analytics_router import router as analytics_router
from app.collector.cron.collect_scheduler import register_collector
# Import des modeles pour que create_all les enregistre
from app.collector.models.goal import Goal  # noqa: F401
from app.collector.models.match import Match  # noqa: F401
from app.collector.models.odd import Odd  # noqa: F401
from app.database.database import Base, engine
from app.env.settings import get_settings
from app.logging_config import setup_logging
from app.scheduler import scheduler

settings = get_settings()
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.enable_scheduler:
        register_collector()
        scheduler.start()
        logger.info("Scheduler demarre (collecte active).")
    yield
    if settings.enable_scheduler and scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Bet261 Analytics API", version="1.0.0", lifespan=lifespan)

# CORS : origines ouvertes SANS credentials (combinaison valide et sure).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    payload = {"message": str(exc.detail), "path": request.url.path, "method": request.method}
    if settings.environment == "local":
        logger.warning("%s %s -> %s %s", request.method, request.url.path,
                       exc.status_code, exc.detail)
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.get("/", tags=["meta"], summary="Infos service")
def root():
    return {"service": "Bet261 Analytics API", "docs": "/docs",
            "health": "/api/analytics/health", "environment": settings.environment}


app.include_router(analytics_router, prefix="/api")
