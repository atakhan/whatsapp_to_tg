"""
FastAPI main application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api import upload, parse, auth, telegram, migrate, whatsapp
from app.core.config import settings
from app.core.logging_setup import configure_logging, request_logging_middleware
from app.services.whatsapp_connect import whatsapp_service

configure_logging(
    service_name=settings.SERVICE_NAME,
    env=settings.ENV,
    level=os.getenv("LOG_LEVEL", "INFO"),
)

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
app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["whatsapp"])

# Attach request logging middleware
app.middleware("http")(request_logging_middleware)

# Create necessary directories
os.makedirs(settings.SESSIONS_DIR, exist_ok=True)
os.makedirs(settings.TMP_DIR, exist_ok=True)
os.makedirs(settings.WHATSAPP_SESSIONS_DIR, exist_ok=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    await whatsapp_service.shutdown()


@app.get("/")
async def root():
    return {"message": "WhatsApp to Telegram Migrator API"}


@app.get("/health")
async def health():
    return {"status": "ok"}
