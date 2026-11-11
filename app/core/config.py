from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_API_KEY_LENGTH = 16
MIN_WEBHOOK_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    fleet_environment: str = "development"
    database_url: str
    fleet_api_key: SecretStr | None = None
    fleet_webhook_secret: SecretStr | None = None
    fleet_webhook_tolerance_seconds: int = Field(
        default=300,
        gt=0,
        le=3600,
    )
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

    @field_validator("fleet_webhook_secret")
    @classmethod
    def validate_webhook_secret(
        cls,
        value: SecretStr | None,
    ) -> SecretStr | None:
        """Treat a blank secret as unset and reject weak secrets."""
        if value is None:
            return None

        secret = value.get_secret_value().strip()

        if not secret:
            return None

        if len(secret) < MIN_WEBHOOK_SECRET_LENGTH:
            raise ValueError(
                "FLEET_WEBHOOK_SECRET must be at least "
                f"{MIN_WEBHOOK_SECRET_LENGTH} characters."
            )

        return SecretStr(secret)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
