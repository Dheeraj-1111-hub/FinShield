from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict

import os
env_path = os.path.join(os.path.dirname(__file__), "../../.env")

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "local"  # local, test, staging, production
    
    # Core Infrastructure
    DATABASE_URL: str
    REDIS_URL: Optional[str] = None
    
    # Security Secrets
    SESSION_SECRET: str
    JWT_SECRET: str
    ENCRYPTION_KEY: str
    WEBHOOK_SIGNING_SECRET: str
    
    # Cookies / CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    COOKIE_DOMAIN: Optional[str] = None
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    
    # External APIs
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o"
    LLM_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: Optional[str] = "openai/gpt-oss-20b"
    CEREBRAS_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    PAYMENT_PROCESSOR_URL: Optional[str] = None
    
    # Observability
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=env_path,
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
settings = Settings()
