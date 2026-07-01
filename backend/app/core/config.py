from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./caintelligence.db"
    JWT_SECRET: str = "supersecretjwtkeyforlocaldevelopmentonly123!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    # AI Providers
    LLM_PROVIDER: str = "mock"
    EMBEDDING_PROVIDER: str = "mock"
    OCR_PROVIDER: str = "tesseract"

    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Storage settings
    STORAGE_PROVIDER: str = "local"
    LOCAL_STORAGE_DIR: str = "./uploads"
    CORS_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        extra = "ignore"


def _validate_production_settings(s: "Settings") -> None:
    """Refuse to boot with insecure defaults if ENV=production - fail loud at startup
    rather than silently serving traffic with a public, source-committed JWT secret
    or a wildcard CORS policy."""
    if s.ENV != "production":
        return
    errors = []
    if s.JWT_SECRET == "supersecretjwtkeyforlocaldevelopmentonly123!":
        errors.append("JWT_SECRET must be overridden in production (found the committed dev default).")
    if s.CORS_ORIGINS.strip() in ("", "*"):
        errors.append("CORS_ORIGINS must be a specific comma-separated origin list in production (found '*').")
    if errors:
        raise RuntimeError(
            "Refusing to start with insecure production configuration:\n- " + "\n- ".join(errors)
        )


settings = Settings()
_validate_production_settings(settings)
