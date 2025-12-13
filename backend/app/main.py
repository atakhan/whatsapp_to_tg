"""
FastAPI main application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api import upload, parse, auth, telegram, migrate
from app.core.config import settings

app = FastAPI(
    title="WhatsApp to Telegram Migrator",
    description="Migrate WhatsApp chats to Telegram with all media",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(parse.router, prefix="/api", tags=["parse"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["telegram"])
app.include_router(migrate.router, prefix="/api/migrate", tags=["migrate"])

# Create necessary directories
os.makedirs(settings.SESSIONS_DIR, exist_ok=True)
os.makedirs(settings.TMP_DIR, exist_ok=True)


@app.get("/")
async def root():
    return {"message": "WhatsApp to Telegram Migrator API"}


@app.get("/health")
async def health():
    return {"status": "ok"}
