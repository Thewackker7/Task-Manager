import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import __version__
from app.api.deps import DbSession
from app.core.config import get_settings
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(response: Response, db: DbSession) -> HealthResponse:
    """Report whether the API is up and can reach the database.

    Returns 503 if the database is unreachable, so load balancers and
    orchestrators know not to send traffic here.
    """
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:
        # Log details server-side; never expose internals to the client.
        logger.exception("Database health check failed")
        database = "unavailable"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        database=database,
        environment=settings.environment,
        version=__version__,
    )
