from fastapi import FastAPI
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    fleet_environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

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
