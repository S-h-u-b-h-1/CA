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
    OCR_PROVIDER: str = "mock"

    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Storage settings
    STORAGE_PROVIDER: str = "local"
    LOCAL_STORAGE_DIR: str = "./uploads"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
