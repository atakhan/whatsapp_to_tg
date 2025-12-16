"""
Application configuration
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os
import sys


class Settings(BaseSettings):
    # Telegram API credentials
    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_BOT_TOKEN: str = ""  # Optional, for bot features
    
    @field_validator('TELEGRAM_API_ID', mode='before')
    @classmethod
    def validate_api_id_before(cls, v):
        # Check for placeholder before conversion
        if isinstance(v, str) and (not v.strip() or v.strip() == "your_api_id"):
            print("\n❌ Configuration Error: TELEGRAM_API_ID is not set", file=sys.stderr)
            print("\nTo fix this:", file=sys.stderr)
            print("1. Edit backend/.env file", file=sys.stderr)
            print("2. Replace 'your_api_id' with your actual TELEGRAM_API_ID (integer)", file=sys.stderr)
            print("3. Replace 'your_api_hash' with your actual TELEGRAM_API_HASH (string)", file=sys.stderr)
            print("4. Get your credentials from https://my.telegram.org/apps\n", file=sys.stderr)
            sys.exit(1)
        return v
    
    @field_validator('TELEGRAM_API_ID', mode='after')
    @classmethod
    def validate_api_id_after(cls, v):
        # Check that value is not 0 after conversion
        if v == 0:
            print("\n❌ Configuration Error: TELEGRAM_API_ID cannot be 0", file=sys.stderr)
            print("\nTo fix this:", file=sys.stderr)
            print("1. Edit backend/.env file", file=sys.stderr)
            print("2. Set TELEGRAM_API_ID to your actual API ID (integer)", file=sys.stderr)
            print("3. Get your credentials from https://my.telegram.org/apps\n", file=sys.stderr)
            sys.exit(1)
        return v
    
    @field_validator('TELEGRAM_API_HASH')
    @classmethod
    def validate_api_hash(cls, v):
        if not v or v == "your_api_hash":
            print("\n❌ Configuration Error: TELEGRAM_API_HASH is not set", file=sys.stderr)
            print("\nTo fix this:", file=sys.stderr)
            print("1. Edit backend/.env file", file=sys.stderr)
            print("2. Replace 'your_api_id' with your actual TELEGRAM_API_ID (integer)", file=sys.stderr)
            print("3. Replace 'your_api_hash' with your actual TELEGRAM_API_HASH (string)", file=sys.stderr)
            print("4. Get your credentials from https://my.telegram.org/apps\n", file=sys.stderr)
            sys.exit(1)
        return v
    
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
    
    # WhatsApp Web settings
    WHATSAPP_SESSIONS_DIR: str = "sessions/whatsapp"
    WHATSAPP_QR_REFRESH_SEC: int = 20  # QR code refresh interval
    WHATSAPP_CONNECT_TIMEOUT_SEC: int = 300  # Max time to wait for connection
    
    class Config:
        env_file = ".env"
        env_file_path = ".env"  # Will be resolved relative to where the app is run from
        case_sensitive = True


# Initialize settings (validation happens in validators)
settings = Settings()
