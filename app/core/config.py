from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    fleet_environment: str = "development"
    database_url: str
    fleet_max_speed_kph: float = Field(
        default=100.0,
        gt=0,
        allow_inf_nan=False,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
