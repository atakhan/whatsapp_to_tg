"""
Migration API endpoints
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List, Dict
import json
import logging
import base64
import mimetypes
import hashlib
import asyncio

import httpx

from app.services.migration_manager import MigrationManager
from app.services.telegram_client import TelegramClientWrapper
from app.services.file_manager import FileManager
from app.core.config import settings
from app.core.logging_setup import set_correlation_ids, set_request_context

router = APIRouter()
file_manager = FileManager(settings.TMP_DIR, settings.SESSIONS_DIR)
logger = logging.getLogger(__name__)

# Store active migrations
active_migrations: Dict[str, MigrationManager] = {}


async def download_media_file(media_path: str, output_dir: Path, index: int) -> Optional[str]:
    """
    Download media file from URL or data URI to local file
    
    Returns local file path if successful, None otherwise
    """
    try:
        # Create media directory
        media_dir = output_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        
        # Handle data URIs
        if media_path.startswith("data:"):
            # Extract data URI parts: data:[<mediatype>][;base64],<data>
            header, data = media_path.split(",", 1)
            is_base64 = "base64" in header
            
            # Determine file extension from mime type
            mime_type = header.split(":")[1].split(";")[0] if ":" in header else "application/octet-stream"
            ext = mimetypes.guess_extension(mime_type) or ".bin"
            
            # Decode data
            if is_base64:
                file_data = base64.b64decode(data)
            else:
                file_data = data.encode('utf-8')
            
            # Generate filename
            file_hash = hashlib.md5(file_data).hexdigest()[:8]
            filename = f"media_{index}_{file_hash}{ext}"
            file_path = media_dir / filename
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            logger.info(
                "Downloaded media from data URI",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "index": index,
                        "mime_type": mime_type,
                        "file_size": len(file_data),
                        "file_path": str(file_path),
                    },
                },
            )
            
            return str(file_path)
        
        # Handle HTTP/HTTPS URLs
        elif media_path.startswith(("http://", "https://")):
            # Generate filename from URL
            url_hash = hashlib.md5(media_path.encode()).hexdigest()[:8]
            # Try to get extension from URL
            ext = Path(media_path).suffix or ".bin"
            filename = f"media_{index}_{url_hash}{ext}"
            file_path = media_dir / filename
            
            # Download file
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(media_path)
                response.raise_for_status()
                
                # Save file
                with open(file_path, 'wb') as f:
                    f.write(response.content)
            
            logger.info(
                "Downloaded media from URL",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "index": index,
                        "url": media_path,
                        "file_size": len(response.content),
                        "file_path": str(file_path),
                    },
                },
            )
            
            return str(file_path)
        
        # If it's already a local path, check if it exists
        elif Path(media_path).exists():
            logger.info(
                "Media file already exists locally",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "index": index,
                        "file_path": media_path,
                    },
                },
            )
            return media_path
        
        else:
            logger.warning(
                "Unknown media path format or file not found",
                extra={
                    "error_code": "MEDIA_DOWNLOAD_UNKNOWN_FORMAT",
                    "extra_data": {
                        "index": index,
                        "media_path": media_path,
                    },
                },
            )
            return None
            
    except Exception as e:
        logger.error(
            "Failed to download media file",
            extra={
                "error_code": "MEDIA_DOWNLOAD_FAIL",
                "extra_data": {
                    "index": index,
                    "media_path": media_path,
                    "error": str(e),
                },
            },
            exc_info=True,
        )
        return None


async def download_media_files(messages: List[Dict], session_path: Path) -> List[Dict]:
    """
    Download all media files from messages and update media_path
    
    Returns updated messages list
    """
    # Create list of messages that need media download
    download_tasks = []
    
    for i, msg in enumerate(messages):
        media_path = msg.get("media_path")
        if media_path and msg.get("type") != "text":
            # Check if it's already a local file that exists
            if Path(media_path).exists():
                continue  # Already downloaded, skip
            
            # Add download task
            download_tasks.append((i, msg.copy()))
    
    # Download all media files concurrently
    if download_tasks:
        logger.info(
            "Downloading %d media files",
            len(download_tasks),
            extra={
                "error_code": None,
                "extra_data": {"total_media": len(download_tasks)},
            },
        )
        
        # Execute downloads with some concurrency limit (max 5 at a time)
        semaphore = asyncio.Semaphore(5)
        
        async def download_with_semaphore(index, msg):
            async with semaphore:
                local_path = await download_media_file(msg.get("media_path"), session_path, index)
                return index, local_path
        
        download_results = await asyncio.gather(
            *[download_with_semaphore(i, msg) for i, msg in download_tasks]
        )
        
        # Update messages with downloaded paths
        result_dict = {i: path for i, path in download_results}
        for i, msg in enumerate(messages):
            if i in result_dict:
                local_path = result_dict[i]
                if local_path:
                    messages[i]["media_path"] = local_path
                else:
                    # Remove media_path if download failed
                    messages[i]["media_path"] = None
                    logger.warning(
                        "Media download failed, message will be skipped",
                        extra={
                            "error_code": "MEDIA_DOWNLOAD_SKIP",
                            "extra_data": {
                                "index": i,
                                "message_type": messages[i].get("type"),
                            },
                        },
                    )
    
    logger.info(
        "Media download completed",
        extra={
            "error_code": None,
            "extra_data": {
                "total_messages": len(messages),
                "downloaded_media": len(download_tasks),
            },
        },
    )
    
    return messages


class StartMigrationRequest(BaseModel):
    session_id: str
    user_id: int
    target_chat_id: int
    whatsapp_chat_id: Optional[str] = None  # Optional: WhatsApp chat ID if using WhatsApp Web


async def run_migration(session_id: str, user_id: int, target_chat_id: int, whatsapp_chat_id: str = None):
    """Background task to run migration"""
    # Inherit or generate correlation ids for background task
    trace_id, request_id = set_correlation_ids()
    set_request_context(user_id=str(user_id))

    try:
        session_path = file_manager.get_session_path(session_id)
        session_path.mkdir(parents=True, exist_ok=True)
        
        # Load messages - try from file first, then from WhatsApp Web if available
        messages_file = session_path / "messages.json"
        messages = []
        
        if messages_file.exists():
            logger.info("Loading messages from file for session %s", session_id)
            with open(messages_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            # Download media files if needed (in case they contain URLs)
            messages = await download_media_files(messages, session_path)
        elif whatsapp_chat_id:
            # Get messages from WhatsApp Web
            logger.info("Fetching messages from WhatsApp Web for chat %s", whatsapp_chat_id)
            
            # Initialize migration manager early to show status
            manager = MigrationManager(session_id, session_path)
            manager.status["current_action"] = "Получение сообщений из WhatsApp Web..."
            manager.status["total"] = 0  # Will be updated after loading
            manager._save_status()
            active_migrations[session_id] = manager
            
            from app.services.whatsapp import whatsapp_service
            messages = await whatsapp_service.get_chat_messages(session_id, whatsapp_chat_id)
            
            logger.info(
                "Fetched %d messages from WhatsApp Web",
                len(messages),
                extra={
                    "error_code": None,
                    "extra_data": {"session_id": session_id, "messages_count": len(messages)},
                },
            )
            
            # Download media files before migration
            manager.status["current_action"] = "Скачивание медиафайлов..."
            manager._save_status()
            
            messages = await download_media_files(messages, session_path)
            
            # Save messages to file for future use
            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
            
            # Update manager with messages
            manager.load_messages(messages)
            manager.status["current_action"] = f"Получено {len(messages)} сообщений. Подготовка к переносу..."
            manager._save_status()
        else:
            raise ValueError("Messages file not found and no WhatsApp chat ID provided")
        
        # Initialize migration manager (if not already created during WhatsApp Web fetch)
        if session_id not in active_migrations:
            manager = MigrationManager(session_id, session_path)
            manager.load_messages(messages)
            manager.set_target_chat(target_chat_id)
            active_migrations[session_id] = manager
        else:
            # Manager already exists from WhatsApp Web fetch
            manager = active_migrations[session_id]
            manager.set_target_chat(target_chat_id)
        
        # Update status to show we're connecting to Telegram
        manager.status["current_action"] = "Подключение к Telegram..."
        manager._save_status()
        
        # Initialize Telegram client with retry
        telegram_session_path = file_manager.get_telegram_session_path(user_id)
        client_wrapper = None
        client_connected = False
        
        try:
            client_wrapper = TelegramClientWrapper(user_id, telegram_session_path)
            logger.info(
                "Connecting to Telegram for migration",
                extra={
                    "error_code": None,
                    "extra_data": {"user_id": user_id, "session_id": session_id},
                },
            )
            
            connected = await client_wrapper.connect(retries=10, retry_delay=3.0)
            
            if not connected:
                manager.status["current_action"] = "Ошибка подключения к Telegram"
                manager.status["errors"].append("Не удалось подключиться к Telegram. Возможно, сессия используется другим процессом.")
                manager._save_status()
                raise ValueError("Could not connect to Telegram")
            
            # Verify client is still connected after connect() returns
            if not client_wrapper.client or not client_wrapper.client.is_connected():
                logger.error(
                    "Client disconnected immediately after connect",
                    extra={
                        "error_code": "TELEGRAM_CLIENT_DISCONNECTED_IMMEDIATELY",
                        "extra_data": {
                            "session_id": session_id,
                            "user_id": user_id,
                        },
                    },
                )
                manager.status["current_action"] = "Ошибка подключения к Telegram"
                manager.status["errors"].append("Подключение к Telegram было разорвано сразу после установки.")
                manager._save_status()
                raise ValueError("Telegram client disconnected immediately after connect")
            
            client_connected = True
            manager.status["current_action"] = "Подключено к Telegram, начало переноса..."
            manager._save_status()
            
            logger.info(
                "Telegram client connected and verified",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "is_connected": client_wrapper.client.is_connected() if client_wrapper.client else False,
                    },
                },
            )
            
            # Handle special target_chat_id values
            original_target_chat_id = target_chat_id
            if target_chat_id == 777000:  # Placeholder for 'saved' or 'new'
                logger.info(
                    "Processing special target_chat_id 777000 (Saved Messages)",
                    extra={
                        "error_code": None,
                        "extra_data": {
                            "session_id": session_id,
                            "user_id": user_id,
                            "original_target_chat_id": target_chat_id,
                        },
                    },
                )
                # Try to find Saved Messages or use "me"
                try:
                    # Get Saved Messages dialog
                    dialogs = await client_wrapper.get_dialogs()
                    saved_messages = None
                    for dialog in dialogs:
                        if dialog.get("name") == "Saved Messages" or dialog.get("name") == "Избранное":
                            saved_messages = dialog.get("id")
                            break
                    
                    if saved_messages:
                        target_chat_id = saved_messages
                        logger.info(
                            "Found Saved Messages dialog",
                            extra={
                                "error_code": None,
                                "extra_data": {
                                    "session_id": session_id,
                                    "saved_messages_id": saved_messages,
                                },
                            },
                        )
                    else:
                        # Use "me" for Saved Messages (Telethon accepts this)
                        target_chat_id = "me"
                        logger.info(
                            "Using 'me' alias for Saved Messages",
                            extra={
                                "error_code": None,
                                "extra_data": {"session_id": session_id},
                            },
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to find Saved Messages, using 'me'",
                        extra={
                            "error_code": "MIGRATION_SAVED_MESSAGES_NOT_FOUND",
                            "extra_data": {
                                "session_id": session_id,
                                "error": str(e),
                            },
                        },
                        exc_info=True,
                    )
                    target_chat_id = "me"
            
            logger.info(
                "Setting target chat for migration",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "original_target_chat_id": original_target_chat_id,
                        "final_target_chat_id": target_chat_id,
                    },
                },
            )
            
            manager.set_target_chat(target_chat_id)
            manager.set_client(client_wrapper)
            
            logger.info(
                "Starting migration execution",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "target_chat_id": target_chat_id,
                        "total_messages": manager.status["total"],
                    },
                },
            )
        
            # Run migration
            await manager.start_migration()
            
        except Exception as e:
            logger.error(
                "Migration task failed",
                extra={
                    "error_code": "MIGRATION_RUN_FAIL",
                    "extra_data": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "target_chat_id": target_chat_id,
                    },
                },
                exc_info=True,
            )
            if session_id in active_migrations:
                active_migrations[session_id].status["errors"].append(str(e))
                active_migrations[session_id]._save_status()
        finally:
            # Always disconnect client, even on error
            if client_wrapper:
                try:
                    await client_wrapper.disconnect()
                except Exception as disconnect_error:
                    logger.warning(
                        "Error disconnecting Telegram client after migration",
                        extra={
                            "error_code": "MIGRATION_DISCONNECT_FAIL",
                            "extra_data": {
                                "session_id": session_id,
                                "user_id": user_id,
                                "error": str(disconnect_error),
                            },
                        },
                        exc_info=True,
                    )
        
    except Exception as e:
        logger.error(
            "Migration task failed (outer exception)",
            extra={
                "error_code": "MIGRATION_OUTER_FAIL",
                "extra_data": {
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(e),
                },
            },
            exc_info=True,
        )
        if session_id in active_migrations:
            active_migrations[session_id].status["errors"].append(str(e))
            active_migrations[session_id]._save_status()


@router.post("/start")
async def start_migration(request: StartMigrationRequest, background_tasks: BackgroundTasks):
    """
    Start migration process
    """
    try:
        session_path = file_manager.get_session_path(request.session_id)
        session_path.mkdir(parents=True, exist_ok=True)
        
        # Check if messages are parsed OR if we can get them from WhatsApp Web
        messages_file = session_path / "messages.json"
        if not messages_file.exists() and not request.whatsapp_chat_id:
            raise HTTPException(
                status_code=400, 
                detail="Messages not parsed yet. Either parse messages first or provide whatsapp_chat_id"
            )
        
        # If using WhatsApp Web, check if session is connected
        if request.whatsapp_chat_id:
            from app.services.whatsapp import whatsapp_service
            if not whatsapp_service.is_connected(request.session_id):
                raise HTTPException(
                    status_code=400,
                    detail="WhatsApp Web is not connected. Please connect first."
                )
        
        # Check if Telegram session exists
        telegram_session_path = file_manager.get_telegram_session_path(request.user_id)
        if not telegram_session_path.exists():
            raise HTTPException(status_code=404, detail="Telegram session not found")
        
        # Start migration in background
        background_tasks.add_task(
            run_migration,
            request.session_id,
            request.user_id,
            request.target_chat_id,
            request.whatsapp_chat_id
        )
        
        return {
            "session_id": request.session_id,
            "status": "started",
            "message": "Migration started"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error starting migration",
            extra={
                "error_code": "MIGRATION_START_FAIL",
                "extra_data": {
                    "session_id": request.session_id,
                    "user_id": request.user_id,
                },
            },
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Error starting migration: {str(e)}")


@router.get("/status/{session_id}")
async def get_migration_status(session_id: str):
    """
    Get migration status
    """
    try:
        session_path = file_manager.get_session_path(session_id)
        status_file = session_path / "migration_status.json"
        
        if session_id in active_migrations:
            # Get live status
            status = active_migrations[session_id].get_status()
        elif status_file.exists():
            # Load from file
            with open(status_file, 'r') as f:
                status = json.load(f)
        else:
            raise HTTPException(status_code=404, detail="Migration not found")
        
        return status
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.post("/stop/{session_id}")
async def stop_migration(session_id: str):
    """
    Stop migration process
    """
    try:
        if session_id in active_migrations:
            active_migrations[session_id].stop_migration()
            return {"status": "stopped", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="Migration not found")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping migration: {str(e)}")


@router.post("/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """
    Cleanup session files after migration
    """
    try:
        success = file_manager.cleanup_session(session_id)
        
        if session_id in active_migrations:
            del active_migrations[session_id]
        
        return {
            "session_id": session_id,
            "cleaned": success
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up: {str(e)}")
