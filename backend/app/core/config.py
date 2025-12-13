"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Telegram API credentials
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_BOT_TOKEN: str = ""  # Optional, for bot features
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # Directories
    SESSIONS_DIR: str = "sessions"
    TMP_DIR: str = "tmp"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Limits
    MAX_ZIP_SIZE: int = 20 * 1024 * 1024 * 1024  # 20GB
    MAX_FILE_SIZE: int = 2 * 1024 * 1024 * 1024  # 2GB
    
    # Migration settings
    MESSAGE_DELAY: float = 0.5  # seconds between messages
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
