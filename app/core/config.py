from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_API_KEY_LENGTH = 16


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    fleet_environment: str = "development"
    database_url: str
    fleet_api_key: SecretStr | None = None
    fleet_max_speed_kph: float = Field(
        default=100.0,
        gt=0,
        allow_inf_nan=False,
    )

    @field_validator("fleet_api_key")
    @classmethod
    def validate_api_key(cls, value: SecretStr | None) -> SecretStr | None:
        """Treat a blank key as unset and reject keys that are too short."""
        if value is None:
            return None

        key = value.get_secret_value().strip()

        if not key:
            return None

        if len(key) < MIN_API_KEY_LENGTH:
            raise ValueError(
                f"FLEET_API_KEY must be at least {MIN_API_KEY_LENGTH} characters."
            )

        return SecretStr(key)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
