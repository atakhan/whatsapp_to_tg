"""
Migration manager - handles message queue and sending
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime
import logging

from app.services.telegram_client import TelegramClientWrapper
from app.core.config import settings

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages migration process with queue and throttling"""
    
    def __init__(self, session_id: str, session_path: Path):
        self.session_id = session_id
        self.session_path = session_path
        self.status_file = session_path / "migration_status.json"
        self.messages: List[Dict] = []
        self.status: Dict = {
            "total": 0,
            "processed": 0,
            "percent": 0.0,
            "current_action": "",
            "errors": [],
            "started_at": None,
            "completed_at": None
        }
        self.client: Optional[TelegramClientWrapper] = None
        self.target_chat_id: Optional[Union[int, str]] = None
        self.is_running = False
    
    def load_messages(self, messages: List[Dict]):
        """Load messages to migrate"""
        self.messages = messages
        self.status["total"] = len(messages)
        self._save_status()
        
        # Log message statistics
        message_types = {}
        messages_with_media = 0
        messages_with_text = 0
        
        for msg in messages:
            msg_type = msg.get("type", "text")
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
            if msg.get("media_path"):
                messages_with_media += 1
            if msg.get("text"):
                messages_with_text += 1
        
        logger.info(
            "Messages loaded for migration",
            extra={
                "error_code": None,
                "extra_data": {
                    "session_id": self.session_id,
                    "total_messages": len(messages),
                    "message_types": message_types,
                    "messages_with_media": messages_with_media,
                    "messages_with_text": messages_with_text,
                },
            },
        )
    
    def set_client(self, client: TelegramClientWrapper):
        """Set Telegram client"""
        self.client = client
    
    def set_target_chat(self, chat_id: Union[int, str]):
        """Set target chat ID (can be int or "me" for Saved Messages)"""
        self.target_chat_id = chat_id
    
    def load_status(self) -> Dict:
        """Load migration status from file"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    self.status = json.load(f)
            except Exception as e:
                logger.error(
                    "Failed to load migration status",
                    extra={
                        "error_code": "MIGRATION_STATUS_LOAD_FAIL",
                        "extra_data": {"session_id": self.session_id, "status_file": str(self.status_file)},
                    },
                    exc_info=True,
                )
        return self.status
    
    def _save_status(self):
        """Save migration status to file"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.status, f, indent=2)
        except Exception as e:
            logger.error(
                "Failed to save migration status",
                extra={
                    "error_code": "MIGRATION_STATUS_SAVE_FAIL",
                    "extra_data": {"session_id": self.session_id, "status_file": str(self.status_file)},
                },
                exc_info=True,
            )
    
    async def start_migration(self):
        """Start migration process"""
        if not self.client or not self.target_chat_id:
            raise ValueError("Client and target chat must be set")
        
        if self.is_running:
            logger.warning(
                "Migration already running",
                extra={
                    "error_code": "MIGRATION_ALREADY_RUNNING",
                    "extra_data": {"session_id": self.session_id},
                },
            )
            return
        
        logger.info(
            "Starting migration process",
            extra={
                "error_code": None,
                "extra_data": {
                    "session_id": self.session_id,
                    "target_chat_id": self.target_chat_id,
                    "total_messages": self.status["total"],
                },
            },
        )
        
        self.is_running = True
        self.status["started_at"] = datetime.now().isoformat()
        self.status["processed"] = 0
        
        try:
            # Process messages
            current_album = []
            album_group_id = None
            
            for i, msg in enumerate(self.messages):
                if not self.is_running:
                    break
                
                try:
                    msg_type = msg.get("type", "text")
                    msg_text = msg.get("text", "")
                    msg_sender = msg.get("sender", "unknown")
                    msg_timestamp = msg.get("timestamp", "")
                    msg_media = msg.get("media_path", "")
                    
                    logger.info(
                        "Processing message %d/%d",
                        i + 1,
                        self.status["total"],
                        extra={
                            "error_code": None,
                            "extra_data": {
                                "session_id": self.session_id,
                                "message_index": i + 1,
                                "message_type": msg_type,
                                "has_text": bool(msg_text),
                                "text_length": len(msg_text) if msg_text else 0,
                                "has_media": bool(msg_media),
                                "media_path": msg_media if msg_media else None,
                                "sender": msg_sender,
                                "timestamp": msg_timestamp,
                                "target_chat_id": self.target_chat_id,
                            },
                        },
                    )
                    
                    # Handle albums
                    if msg.get("is_album") and msg.get("album_group_id"):
                        if album_group_id != msg["album_group_id"]:
                            # Send previous album if exists
                            if current_album:
                                await self._send_album(current_album)
                            current_album = []
                            album_group_id = msg["album_group_id"]
                        
                        current_album.append(msg)
                        
                        # Check if this is the last message in album
                        if (i == len(self.messages) - 1 or 
                            self.messages[i + 1].get("album_group_id") != album_group_id):
                            await self._send_album(current_album)
                            current_album = []
                            album_group_id = None
                    else:
                        # Send previous album if exists
                        if current_album:
                            await self._send_album(current_album)
                            current_album = []
                            album_group_id = None
                        
                        # Send single message
                        await self._send_message(msg)
                    
                    # Update status
                    self.status["processed"] = i + 1
                    if self.status["total"] > 0:
                        self.status["percent"] = (self.status["processed"] / self.status["total"]) * 100
                    else:
                        self.status["percent"] = 0.0
                    self.status["current_action"] = f"Processing message {i + 1}/{self.status['total']}"
                    self._save_status()
                    
                    logger.info(
                        "Message %d/%d processed successfully",
                        i + 1,
                        self.status["total"],
                        extra={
                            "error_code": None,
                            "extra_data": {
                                "session_id": self.session_id,
                                "message_index": i + 1,
                                "message_type": msg_type,
                            },
                        },
                    )
                    
                    # Throttle
                    await asyncio.sleep(settings.MESSAGE_DELAY)
                    
                except Exception as e:
                    error_msg = f"Error processing message {i + 1}: {str(e)}"
                    self.status["errors"].append(error_msg)
                    logger.error(
                        "Failed to process message",
                        extra={
                            "error_code": "MIGRATION_MESSAGE_PROCESS_FAIL",
                            "extra_data": {
                                "session_id": self.session_id,
                                "index": i + 1,
                                "total": self.status["total"],
                                "message_type": msg.get("type", "unknown"),
                                "error": str(e),
                            },
                        },
                        exc_info=True,
                    )
                    self._save_status()
            
            # Send remaining album
            if current_album:
                await self._send_album(current_album)
            
            # Finalize status
            self.status["completed_at"] = datetime.now().isoformat()
            self.status["current_action"] = "Migration completed"
            self.status["percent"] = 100.0 if self.status["total"] > 0 else 0.0
            self._save_status()
            
            logger.info(
                "Migration completed successfully",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "session_id": self.session_id,
                        "total": self.status["total"],
                        "processed": self.status["processed"],
                        "errors_count": len(self.status["errors"]),
                    },
                },
            )
            
        finally:
            self.is_running = False
    
    async def _send_message(self, msg: Dict):
        """Send a single message"""
        if not self.client:
            logger.warning(
                "Cannot send message: Telegram client not initialized",
                extra={
                    "error_code": "MIGRATION_CLIENT_NOT_INIT",
                    "extra_data": {"session_id": self.session_id},
                },
            )
            return
        
        msg_type = msg.get("type", "text")
        text = msg.get("text", "")
        media_path = msg.get("media_path")
        text_preview = (text[:100] + "...") if text and len(text) > 100 else text
        
        logger.info(
            "Sending message to Telegram",
            extra={
                "error_code": None,
                "extra_data": {
                    "session_id": self.session_id,
                    "message_type": msg_type,
                    "target_chat_id": self.target_chat_id,
                    "has_text": bool(text),
                    "text_preview": text_preview,
                    "has_media": bool(media_path),
                    "media_exists": Path(media_path).exists() if media_path else False,
                },
            },
        )
        
        success = False
        try:
            if msg_type == "text":
                if text:
                    success = await self.client.send_message(self.target_chat_id, text)
                    logger.info(
                        "Text message sent",
                        extra={
                            "error_code": None,
                            "extra_data": {
                                "session_id": self.session_id,
                                "target_chat_id": self.target_chat_id,
                                "text_length": len(text),
                                "success": success,
                            },
                        },
                    )
                else:
                    logger.warning(
                        "Skipping empty text message",
                        extra={
                            "error_code": "MIGRATION_EMPTY_MESSAGE",
                            "extra_data": {"session_id": self.session_id, "message_type": msg_type},
                        },
                    )
            elif msg_type == "image":
                if media_path and Path(media_path).exists():
                    success = await self.client.send_document(self.target_chat_id, media_path, caption=text if text else None)
                    logger.info(
                        "Image sent",
                        extra={
                            "error_code": None,
                            "extra_data": {
                                "session_id": self.session_id,
                                "target_chat_id": self.target_chat_id,
                                "media_path": media_path,
                                "has_caption": bool(text),
                                "success": success,
                            },
                        },
                    )
                else:
                    # Media file not available - send text if available
                    if text:
                        success = await self.client.send_message(self.target_chat_id, f"[Изображение недоступно]\n{text}")
                        logger.warning(
                            "Image message media not found, sent text only",
                            extra={
                                "error_code": "MIGRATION_MEDIA_NOT_FOUND",
                                "extra_data": {
                                    "session_id": self.session_id,
                                    "target_chat_id": self.target_chat_id,
                                    "media_path": media_path,
                                    "success": success,
                                },
                            },
                        )
                    else:
                        logger.warning(
                            "Skipping image message - no media and no text",
                            extra={
                                "error_code": "MIGRATION_IMAGE_SKIP",
                                "extra_data": {
                                    "session_id": self.session_id,
                                    "target_chat_id": self.target_chat_id,
                                    "media_path": media_path,
                                },
                            },
                        )
            elif msg_type == "video":
                if media_path and Path(media_path).exists():
                    success = await self.client.send_document(self.target_chat_id, media_path, caption=text if text else None)
                    logger.info(
                        "Video sent",
                        extra={
                            "error_code": None,
                            "extra_data": {
                                "session_id": self.session_id,
                                "target_chat_id": self.target_chat_id,
                                "media_path": media_path,
                                "has_caption": bool(text),
                                "success": success,
                            },
                        },
                    )
                else:
                    if text:
                        success = await self.client.send_message(self.target_chat_id, f"[Видео недоступно]\n{text}")
                        logger.warning(
                            "Video message media not found, sent text only",
                            extra={
                                "error_code": "MIGRATION_MEDIA_NOT_FOUND",
                                "extra_data": {
                                    "session_id": self.session_id,
                                    "target_chat_id": self.target_chat_id,
                                    "media_path": media_path,
                                    "success": success,
                                },
                            },
                        )
                    else:
                        logger.warning(
                            "Skipping video message - no media and no text",
                            extra={
                                "error_code": "MIGRATION_VIDEO_SKIP",
                                "extra_data": {
                                    "session_id": self.session_id,
                                    "target_chat_id": self.target_chat_id,
                                    "media_path": media_path,
                                },
                            },
                        )
            elif msg_type == "audio":
                if media_path and Path(media_path).exists():
                    success = await self.client.send_document(self.target_chat_id, media_path, caption=text if text else None)
                    logger.info(
                        "Audio sent",
                        extra={
                            "error_code": None,
                            "extra_data": {
                                "session_id": self.session_id,
                                "target_chat_id": self.target_chat_id,
                                "media_path": media_path,
                                "has_caption": bool(text),
                                "success": success,
                            },
                        },
                    )
                elif text:
                    success = await self.client.send_message(self.target_chat_id, text)
                    logger.info(
                        "Audio message fallback to text sent",
                        extra={
                            "error_code": None,
                            "extra_data": {
                                "session_id": self.session_id,
                                "target_chat_id": self.target_chat_id,
                                "success": success,
                            },
                        },
                    )
            elif msg_type == "voice":
                if media_path and Path(media_path).exists():
                    success = await self.client.send_voice(self.target_chat_id, media_path)
                    logger.info(
                        "Voice message sent",
                        extra={
                            "error_code": None,
                            "extra_data": {
                                "session_id": self.session_id,
                                "target_chat_id": self.target_chat_id,
                                "media_path": media_path,
                                "success": success,
                            },
                        },
                    )
                elif text:
                    success = await self.client.send_message(self.target_chat_id, text)
                    logger.info(
                        "Voice message fallback to text sent",
                        extra={
                            "error_code": None,
                            "extra_data": {
                                "session_id": self.session_id,
                                "target_chat_id": self.target_chat_id,
                                "success": success,
                            },
                        },
                    )
            elif msg_type in ["document", "sticker", "gif"]:
                if media_path and Path(media_path).exists():
                    success = await self.client.send_document(self.target_chat_id, media_path, caption=text if text else None)
                    logger.info(
                        "Document/sticker/gif sent",
                        extra={
                            "error_code": None,
                            "extra_data": {
                                "session_id": self.session_id,
                                "target_chat_id": self.target_chat_id,
                                "message_type": msg_type,
                                "media_path": media_path,
                                "has_caption": bool(text),
                                "success": success,
                            },
                        },
                    )
                else:
                    if text:
                        media_type_name = {"document": "Документ", "sticker": "Стикер", "gif": "GIF"}.get(msg_type, "Файл")
                        success = await self.client.send_message(self.target_chat_id, f"[{media_type_name} недоступен]\n{text}")
                        logger.warning(
                            "Document/sticker/gif message media not found, sent text only",
                            extra={
                                "error_code": "MIGRATION_MEDIA_NOT_FOUND",
                                "extra_data": {
                                    "session_id": self.session_id,
                                    "target_chat_id": self.target_chat_id,
                                    "message_type": msg_type,
                                    "media_path": media_path,
                                    "success": success,
                                },
                            },
                        )
                    else:
                        logger.warning(
                            "Skipping %s message - no media and no text",
                            msg_type,
                            extra={
                                "error_code": "MIGRATION_DOCUMENT_SKIP",
                                "extra_data": {
                                    "session_id": self.session_id,
                                    "target_chat_id": self.target_chat_id,
                                    "message_type": msg_type,
                                    "media_path": media_path,
                                },
                            },
                        )
            
            if not success:
                logger.error(
                    "Message sending returned False",
                    extra={
                        "error_code": "MIGRATION_SEND_FAILED",
                        "extra_data": {
                            "session_id": self.session_id,
                            "message_type": msg_type,
                            "target_chat_id": self.target_chat_id,
                        },
                    },
                )
        except Exception as e:
            logger.error(
                "Exception while sending message",
                extra={
                    "error_code": "MIGRATION_SEND_EXCEPTION",
                    "extra_data": {
                        "session_id": self.session_id,
                        "message_type": msg_type,
                        "target_chat_id": self.target_chat_id,
                        "error": str(e),
                    },
                },
                exc_info=True,
            )
            raise
    
    async def _send_album(self, album_messages: List[Dict]):
        """Send media album"""
        if not self.client:
            logger.warning(
                "Cannot send album: Telegram client not initialized",
                extra={
                    "error_code": "MIGRATION_CLIENT_NOT_INIT",
                    "extra_data": {"session_id": self.session_id},
                },
            )
            return
        
        if not album_messages:
            logger.warning(
                "Cannot send album: empty album messages",
                extra={
                    "error_code": "MIGRATION_EMPTY_ALBUM",
                    "extra_data": {"session_id": self.session_id},
                },
            )
            return
        
        media_files = []
        captions = []
        
        logger.info(
            "Preparing album for sending",
            extra={
                "error_code": None,
                "extra_data": {
                    "session_id": self.session_id,
                    "target_chat_id": self.target_chat_id,
                    "album_size": len(album_messages),
                },
            },
        )
        
        for idx, msg in enumerate(album_messages):
            media_path = msg.get("media_path")
            if media_path and Path(media_path).exists():
                media_files.append(media_path)
                captions.append(msg.get("text", ""))
                logger.debug(
                    "Added media to album",
                    extra={
                        "error_code": None,
                        "extra_data": {
                            "session_id": self.session_id,
                            "album_index": idx,
                            "media_path": media_path,
                            "has_caption": bool(msg.get("text")),
                        },
                    },
                )
            else:
                logger.warning(
                    "Skipping album item: media file not found",
                    extra={
                        "error_code": "MIGRATION_ALBUM_MEDIA_NOT_FOUND",
                        "extra_data": {
                            "session_id": self.session_id,
                            "album_index": idx,
                            "media_path": media_path,
                        },
                    },
                )
        
        if media_files:
            logger.info(
                "Sending media album to Telegram",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "session_id": self.session_id,
                        "target_chat_id": self.target_chat_id,
                        "media_count": len(media_files),
                    },
                },
            )
            success = await self.client.send_media_group(self.target_chat_id, media_files, captions)
            logger.info(
                "Media album sent",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "session_id": self.session_id,
                        "target_chat_id": self.target_chat_id,
                        "media_count": len(media_files),
                        "success": success,
                    },
                },
            )
            if not success:
                logger.error(
                    "Album sending returned False",
                    extra={
                        "error_code": "MIGRATION_ALBUM_SEND_FAILED",
                        "extra_data": {
                            "session_id": self.session_id,
                            "target_chat_id": self.target_chat_id,
                            "media_count": len(media_files),
                        },
                    },
                )
        else:
            logger.warning(
                "No valid media files in album",
                extra={
                    "error_code": "MIGRATION_ALBUM_NO_MEDIA",
                    "extra_data": {
                        "session_id": self.session_id,
                        "album_size": len(album_messages),
                    },
                },
            )
    
    def stop_migration(self):
        """Stop migration process"""
        self.is_running = False
    
    def get_status(self) -> Dict:
        """Get current migration status"""
        return self.status
