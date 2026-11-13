from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    JWT_SECRET: str = "dev-secret-key-32-chars-long-hackathon-2026"

    # Databases
    DATABASE_URL: str = "postgresql+psycopg://user:password@localhost:5432/opssaathi"
    VERIFIER_DATABASE_URL: str = (
        "postgresql+psycopg://verifier_ro:password@localhost:5432/opssaathi"
    )

    # Providers
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str | None = None
    SARVAM_API_KEY: str | None = None

    # Paytm Staging
    PAYTM_ENVIRONMENT: str = "staging"
    PAYTM_MID: str | None = None
    PAYTM_MERCHANT_KEY: str | None = None
    PAYTM_WEBSITE_NAME: str = "WEBSTAGING"

    # Voice & Language
    VOICE_PROVIDER: str = "sarvam"
    DEFAULT_LANGUAGE: str = "en"

    # Operational Controls
    DEMO_DATA_MODE: bool = True
    DEMO_DETERMINISTIC: bool = False
    RESYNC_APPROVAL_THRESHOLD_INR: Decimal = Decimal("5000.00")
    SETTLEMENT_OPS_ADAPTER: str = "mock"


settings = Settings()
