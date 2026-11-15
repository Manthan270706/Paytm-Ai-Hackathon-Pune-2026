from decimal import Decimal
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT_ENV = Path(__file__).resolve().parents[4] / ".env"
_API_DIR_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT_ENV, _API_DIR_ENV, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    JWT_SECRET: str = "dev-secret-key-32-chars-long-hackathon-2026"

    # Databases
    DATABASE_URL: str = "postgresql+psycopg://user:password@localhost:5432/opssaathi"
    VERIFIER_DATABASE_URL: str = (
        "postgresql+psycopg://verifier_ro:password@localhost:5432/opssaathi"
    )

    # Providers & Cascade
    LLM_PROVIDER: str = "groq"
    LLM_CASCADE: str = "groq,ollama,cache,mock"
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # Local LLM (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    LOCAL_LLM_ENABLED: bool = True
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434/v1"
    LOCAL_LLM_MODEL: str = "qwen2.5:3b"

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
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
