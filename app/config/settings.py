import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ticket CRM"
    DATABASE_URL: str = "sqlite+aiosqlite:///./tickets.db"
    
    # Bloom Filter settings
    BLOOM_CAPACITY: int = 10000
    BLOOM_ERROR_RATE: float = 0.001

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
