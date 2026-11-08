from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

app = FastAPI(
    title="Fleet Operations Intelligence Platform",
    description=(
        "An enterprise-style platform for fleet operations "
        "intelligence, data integration, and AI governance."
    ),
    version="0.1.0",
)


@app.get("/")
def root():
    """Return basic information about the application."""
    return {
        "service": "Fleet Operations Intelligence Platform",
        "environment": settings.fleet_environment,
        "status": "running",
    }


@app.get("/health/live")
def health_check():
    """Check whether the application process is running."""
    return {"status": "healthy"}


@app.get("/health/ready")
def readiness_check(db: Annotated[Session, Depends(get_db)]):
    """Check whether the application can communicate with PostgreSQL."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from exc

    return {
        "status": "ready",
        "database": "connected",
    }
