import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}/fund_assistant.db"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production-abc123"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS — 开发模式允许局域网访问
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://192.168.1.7:5173"

    # Scraping
    FUND_UPDATE_INTERVAL_MINUTES: int = 30
    MARKET_UPDATE_INTERVAL_MINUTES: int = 5

    # Notification defaults
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        env_file_encoding = "utf-8"


settings = Settings()
