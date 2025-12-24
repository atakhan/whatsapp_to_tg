"""
Telegram client wrapper using Telethon
"""
from telethon import TelegramClient
from telethon.tl.types import User, Chat, Channel
from pathlib import Path
from typing import List, Dict, Optional, Union
import asyncio
import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global locks for session files to prevent concurrent access
_session_locks: Dict[int, asyncio.Lock] = {}
_locks_lock = asyncio.Lock()


async def get_session_lock(user_id: int) -> asyncio.Lock:
    """Get or create lock for a user session"""
    async with _locks_lock:
        if user_id not in _session_locks:
            _session_locks[user_id] = asyncio.Lock()
        return _session_locks[user_id]


class TelegramClientWrapper:
    """Wrapper for Telethon client"""
    
    def __init__(self, user_id: int, session_path: Path):
        self.user_id = user_id
        self.session_path = session_path
        self.client: Optional[TelegramClient] = None
        self._lock: Optional[asyncio.Lock] = None
    
    async def connect(self, retries: int = 3, retry_delay: float = 1.0) -> bool:
        """Connect to Telegram with retry and lock mechanism"""
        # Get lock for this user's session
        self._lock = await get_session_lock(self.user_id)
        
        for attempt in range(retries):
            try:
                async with self._lock:
                    logger.debug(
                        "Connecting to Telegram (attempt %d/%d)",
                        attempt + 1,
                        retries,
                        extra={
                            "error_code": None,
                            "extra_data": {"user_id": self.user_id, "attempt": attempt + 1},
                        },
                    )
                    
                    self.client = TelegramClient(
                        str(self.session_path),
                        settings.TELEGRAM_API_ID,
                        settings.TELEGRAM_API_HASH
                    )
                    await self.client.connect()
                    
                    if not await self.client.is_user_authorized():
                        await self.client.disconnect()
                        self.client = None
                        return False
                    
                    # Verify connection is stable
                    if not self.client.is_connected():
                        logger.error(
                            "Client connection lost immediately after connect",
                            extra={
                                "error_code": "TELEGRAM_CONNECTION_UNSTABLE",
                                "extra_data": {"user_id": self.user_id},
                            },
                        )
                        await self.client.disconnect()
                        self.client = None
                        raise Exception("Connection lost immediately after connect")
                    
                    logger.info(
                        "Successfully connected to Telegram",
                        extra={
                            "error_code": None,
                            "extra_data": {
                                "user_id": self.user_id,
                                "is_connected": self.client.is_connected(),
                            },
                        },
                    )
                    return True
                    
            except Exception as e:
                error_msg = str(e)
                is_locked = "locked" in error_msg.lower() or "database is locked" in error_msg.lower()
                
                # Always try to clean up client on error
                if self.client:
                    try:
                        await self.client.disconnect()
                    except Exception:
                        pass
                    finally:
                        self.client = None
                
                if is_locked and attempt < retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(
                        "Telegram session locked, retrying in %.1fs (attempt %d/%d)",
                        wait_time,
                        attempt + 1,
                        retries,
                        extra={
                            "error_code": "TELEGRAM_SESSION_LOCKED",
                            "extra_data": {
                                "user_id": self.user_id,
                                "attempt": attempt + 1,
                                "retries": retries,
                            },
                        },
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(
                        "Failed to connect to Telegram",
                        extra={
                            "error_code": "TELEGRAM_CONNECT_FAIL",
                            "extra_data": {
                                "user_id": self.user_id,
                                "session_path": str(self.session_path),
                                "attempt": attempt + 1,
                                "error": error_msg,
                            },
                        },
                        exc_info=True,
                    )
                    return False
        
        return False
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            try:
                # Use lock if available, otherwise create a temporary one
                lock_to_use = self._lock if self._lock else await get_session_lock(self.user_id)
                async with lock_to_use:
                    try:
                        await self.client.disconnect()
                    except Exception as disconnect_error:
                        logger.warning(
                            "Error during Telegram disconnect",
                            extra={
                                "error_code": "TELEGRAM_DISCONNECT_ERROR",
                                "extra_data": {
                                    "user_id": self.user_id,
                                    "error": str(disconnect_error),
                                },
                            },
                            exc_info=True,
                        )
            except Exception as e:
                logger.warning(
                    "Error disconnecting Telegram client",
                    extra={
                        "error_code": "TELEGRAM_DISCONNECT_FAIL",
                        "extra_data": {
                            "user_id": self.user_id,
                            "error": str(e),
                        },
                    },
                    exc_info=True,
                )
            finally:
                self.client = None
    
    async def get_dialogs(self) -> List[Dict]:
        """Get list of chats/dialogs"""
        # Ensure client is connected
        if not self.client or not self.client.is_connected():
            logger.warning(
                "Client not connected, attempting to reconnect",
                extra={
                    "error_code": "TELEGRAM_CLIENT_NOT_CONNECTED",
                    "extra_data": {"user_id": self.user_id},
                },
            )
            connected = await self.connect(retries=3, retry_delay=1.0)
            if not connected:
                logger.error(
                    "Failed to reconnect client",
                    extra={
                        "error_code": "TELEGRAM_RECONNECT_FAIL",
                        "extra_data": {"user_id": self.user_id},
                    },
                )
            return []
        
        dialogs = []
        async for dialog in self.client.iter_dialogs():
            entity = dialog.entity
            
            dialog_info = {
                "id": dialog.id,
                "name": dialog.name,
                "is_user": isinstance(entity, User),
                "is_group": isinstance(entity, Chat),
                "is_channel": isinstance(entity, Channel),
            }
            
            if isinstance(entity, User):
                dialog_info["username"] = entity.username
                dialog_info["phone"] = entity.phone
            
            dialogs.append(dialog_info)
        
        return dialogs
    
    async def send_message(self, chat_id: Union[int, str], text: str) -> bool:
        """Send text message"""
        try:
            # Ensure client is connected
            if not self.client or not self.client.is_connected():
                logger.warning(
                    "Client not connected, attempting to reconnect",
                    extra={
                        "error_code": "TELEGRAM_CLIENT_NOT_CONNECTED",
                        "extra_data": {"user_id": self.user_id},
                    },
                )
                connected = await self.connect(retries=3, retry_delay=1.0)
                if not connected:
                    logger.error(
                        "Failed to reconnect client",
                        extra={
                            "error_code": "TELEGRAM_RECONNECT_FAIL",
                            "extra_data": {"user_id": self.user_id},
                        },
                    )
                    return False
            
            # Handle "me" for Saved Messages
            target = "me" if chat_id == "me" or str(chat_id) == "me" else chat_id
            text_preview = (text[:100] + "...") if text and len(text) > 100 else text
            
            logger.info(
                "Sending text message to Telegram",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "user_id": self.user_id,
                        "chat_id": chat_id,
                        "target": target,
                        "text_length": len(text) if text else 0,
                        "text_preview": text_preview,
                    },
                },
            )
            
            result = await self.client.send_message(target, text)
            
            logger.info(
                "Text message sent successfully",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "user_id": self.user_id,
                        "chat_id": chat_id,
                        "target": target,
                        "message_id": result.id if hasattr(result, 'id') else None,
                    },
                },
            )
            
            return True
        except Exception as e:
            logger.error(
                "Failed to send message",
                extra={
                    "error_code": "TELEGRAM_SEND_MESSAGE_FAIL",
                    "extra_data": {
                        "chat_id": chat_id,
                        "user_id": self.user_id,
                        "text_length": len(text) if text else 0,
                        "error": str(e),
                    },
                },
                exc_info=True,
            )
            return False
    
    async def send_document(
        self,
        chat_id: Union[int, str],
        file_path: str,
        caption: Optional[str] = None
    ) -> bool:
        """Send document (for photos, videos, etc. in max quality)"""
        try:
            # Ensure client is connected
            if not self.client or not self.client.is_connected():
                logger.warning(
                    "Client not connected, attempting to reconnect",
                    extra={
                        "error_code": "TELEGRAM_CLIENT_NOT_CONNECTED",
                        "extra_data": {"user_id": self.user_id},
                    },
                )
                connected = await self.connect(retries=3, retry_delay=1.0)
                if not connected:
                    logger.error(
                        "Failed to reconnect client",
                        extra={
                            "error_code": "TELEGRAM_RECONNECT_FAIL",
                            "extra_data": {"user_id": self.user_id},
                        },
                    )
                    return False
            
            # Handle "me" for Saved Messages
            target = "me" if chat_id == "me" or str(chat_id) == "me" else chat_id
            
            file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
            caption_preview = (caption[:50] + "...") if caption and len(caption) > 50 else caption
            
            logger.info(
                "Sending document to Telegram",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "user_id": self.user_id,
                        "chat_id": chat_id,
                        "target": target,
                        "file_path": file_path,
                        "file_size": file_size,
                        "has_caption": bool(caption),
                        "caption_preview": caption_preview,
                    },
                },
            )
            
            result = await self.client.send_file(
                target,
                file_path,
                caption=caption,
                force_document=True  # Send as document for max quality
            )
            
            logger.info(
                "Document sent successfully",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "user_id": self.user_id,
                        "chat_id": chat_id,
                        "target": target,
                        "file_path": file_path,
                        "message_id": result.id if hasattr(result, 'id') else None,
                    },
                },
            )
            
            return True
        except Exception as e:
            logger.error(
                "Failed to send document",
                extra={
                    "error_code": "TELEGRAM_SEND_DOC_FAIL",
                    "extra_data": {
                        "chat_id": chat_id,
                        "user_id": self.user_id,
                        "file_path": file_path,
                        "file_exists": Path(file_path).exists() if file_path else False,
                        "error": str(e),
                    },
                },
                exc_info=True,
            )
            return False
    
    async def send_voice(self, chat_id: Union[int, str], file_path: str) -> bool:
        """Send voice message"""
        try:
            # Ensure client is connected
            if not self.client or not self.client.is_connected():
                logger.warning(
                    "Client not connected, attempting to reconnect",
                    extra={
                        "error_code": "TELEGRAM_CLIENT_NOT_CONNECTED",
                        "extra_data": {"user_id": self.user_id},
                    },
                )
                connected = await self.connect(retries=3, retry_delay=1.0)
                if not connected:
                    logger.error(
                        "Failed to reconnect client",
                        extra={
                            "error_code": "TELEGRAM_RECONNECT_FAIL",
                            "extra_data": {"user_id": self.user_id},
                        },
                    )
                    return False
            
            # Handle "me" for Saved Messages
            target = "me" if chat_id == "me" or str(chat_id) == "me" else chat_id

            file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0

            logger.info(
                "Sending voice message to Telegram",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "user_id": self.user_id,
                        "chat_id": chat_id,
                        "target": target,
                        "file_path": file_path,
                        "file_size": file_size,
                    },
                },
            )
            
            result = await self.client.send_file(
                target,
                file_path,
                voice_note=True
            )
            
            logger.info(
                "Voice message sent successfully",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "user_id": self.user_id,
                        "chat_id": chat_id,
                        "target": target,
                        "file_path": file_path,
                        "message_id": result.id if hasattr(result, 'id') else None,
                    },
                },
            )
            
            return True
        except Exception as e:
            logger.error(
                "Failed to send voice",
                extra={
                    "error_code": "TELEGRAM_SEND_VOICE_FAIL",
                    "extra_data": {
                        "chat_id": chat_id,
                        "user_id": self.user_id,
                        "file_path": file_path,
                        "file_exists": Path(file_path).exists() if file_path else False,
                        "error": str(e),
                    },
                },
                exc_info=True,
            )
            return False
    
    async def send_media_group(
        self,
        chat_id: Union[int, str],
        media_files: List[str],
        captions: Optional[List[str]] = None
    ) -> bool:
        """Send media group (album)"""
        try:
            # Handle "me" for Saved Messages
            target = "me" if chat_id == "me" or str(chat_id) == "me" else chat_id
            
            file_sizes = []
            for f in media_files:
                if Path(f).exists():
                    file_sizes.append(Path(f).stat().st_size)
                else:
                    file_sizes.append(0)
            
            logger.info(
                "Sending media group to Telegram",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "user_id": self.user_id,
                        "chat_id": chat_id,
                        "target": target,
                        "media_count": len(media_files),
                        "file_paths": media_files,
                        "file_sizes": file_sizes,
                        "has_captions": bool(captions),
                        "caption_count": len(captions) if captions else 0,
                    },
                },
            )
            
            # Telethon send_file accepts list of files for albums
            # Captions are passed as a list matching files
            result = await self.client.send_file(
                target,
                media_files,
                force_document=True,
                captions=captions if captions else None
            )
            
            # result can be a list of messages for albums
            message_ids = []
            if isinstance(result, list):
                message_ids = [msg.id for msg in result if hasattr(msg, 'id')]
            elif hasattr(result, 'id'):
                message_ids = [result.id]
            
            logger.info(
                "Media group sent successfully",
                extra={
                    "error_code": None,
                    "extra_data": {
                        "user_id": self.user_id,
                        "chat_id": chat_id,
                        "target": target,
                        "media_count": len(media_files),
                        "message_ids": message_ids,
                    },
                },
            )
            
            return True
        except Exception as e:
            logger.error(
                "Failed to send media group",
                extra={
                    "error_code": "TELEGRAM_SEND_MEDIA_GROUP_FAIL",
                    "extra_data": {
                        "chat_id": chat_id,
                        "user_id": self.user_id,
                        "media_files": media_files,
                        "media_count": len(media_files),
                        "error": str(e),
                    },
                },
                exc_info=True,
            )
            return False
    
    async def get_me(self) -> Optional[Dict]:
        """Get current user info"""
        if not self.client:
            return None
        
        try:
            me = await self.client.get_me()
            return {
                "id": me.id,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "username": me.username,
                "phone": me.phone
            }
        except Exception as e:
            logger.error(
                "Failed to get user info",
                extra={
                    "error_code": "TELEGRAM_GET_ME_FAIL",
                    "extra_data": {"user_id": self.user_id},
                },
                exc_info=True,
            )
            return None
