"""
Telegram client wrapper using Telethon
"""
from telethon import TelegramClient
from telethon.tl.types import User, Chat, Channel
from pathlib import Path
from typing import List, Dict, Optional
import asyncio
from app.core.config import settings


class TelegramClientWrapper:
    """Wrapper for Telethon client"""
    
    def __init__(self, user_id: int, session_path: Path):
        self.user_id = user_id
        self.session_path = session_path
        self.client: Optional[TelegramClient] = None
    
    async def connect(self) -> bool:
        """Connect to Telegram"""
        try:
            self.client = TelegramClient(
                str(self.session_path),
                settings.TELEGRAM_API_ID,
                settings.TELEGRAM_API_HASH
            )
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                return False
            
            return True
        except Exception as e:
            print(f"Error connecting to Telegram: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()
    
    async def get_dialogs(self) -> List[Dict]:
        """Get list of chats/dialogs"""
        if not self.client:
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
    
    async def send_message(self, chat_id: int, text: str) -> bool:
        """Send text message"""
        try:
            await self.client.send_message(chat_id, text)
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    async def send_document(
        self,
        chat_id: int,
        file_path: str,
        caption: Optional[str] = None
    ) -> bool:
        """Send document (for photos, videos, etc. in max quality)"""
        try:
            await self.client.send_file(
                chat_id,
                file_path,
                caption=caption,
                force_document=True  # Send as document for max quality
            )
            return True
        except Exception as e:
            print(f"Error sending document: {e}")
            return False
    
    async def send_voice(self, chat_id: int, file_path: str) -> bool:
        """Send voice message"""
        try:
            await self.client.send_file(
                chat_id,
                file_path,
                voice_note=True
            )
            return True
        except Exception as e:
            print(f"Error sending voice: {e}")
            return False
    
    async def send_media_group(
        self,
        chat_id: int,
        media_files: List[str],
        captions: Optional[List[str]] = None
    ) -> bool:
        """Send media group (album)"""
        try:
            # Telethon send_file accepts list of files for albums
            # Captions are passed as a list matching files
            await self.client.send_file(
                chat_id,
                media_files,
                force_document=True,
                captions=captions if captions else None
            )
            return True
        except Exception as e:
            print(f"Error sending media group: {e}")
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
            print(f"Error getting user info: {e}")
            return None
