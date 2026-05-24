import asyncio
import logging
from functools import wraps

from fastapi import HTTPException
from pydantic import ValidationError

logger = logging.getLogger("bet261.api")


def api_endpoint(func):
    """Enveloppe un endpoint : log + conversion propre des erreurs en HTTP."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        except ValidationError as ve:
            raise HTTPException(status_code=422, detail=ve.errors()) from ve
        except HTTPException as http_exc:
            logger.warning("HTTPException in %s: %s - %s",
                           func.__name__, http_exc.status_code, http_exc.detail)
            raise
        except Exception as exc:
            logger.error("Error in %s: %s", func.__name__, str(exc), exc_info=True)
            raise HTTPException(status_code=500, detail="An internal error occurred.") from exc
    return wrapper
