"""
Migration manager - handles message queue and sending
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from app.services.telegram_client import TelegramClientWrapper
from app.core.config import settings


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
        self.target_chat_id: Optional[int] = None
        self.is_running = False
    
    def load_messages(self, messages: List[Dict]):
        """Load messages to migrate"""
        self.messages = messages
        self.status["total"] = len(messages)
        self._save_status()
    
    def set_client(self, client: TelegramClientWrapper):
        """Set Telegram client"""
        self.client = client
    
    def set_target_chat(self, chat_id: int):
        """Set target chat ID"""
        self.target_chat_id = chat_id
    
    def load_status(self) -> Dict:
        """Load migration status from file"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    self.status = json.load(f)
            except Exception as e:
                print(f"Error loading status: {e}")
        return self.status
    
    def _save_status(self):
        """Save migration status to file"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.status, f, indent=2)
        except Exception as e:
            print(f"Error saving status: {e}")
    
    async def start_migration(self):
        """Start migration process"""
        if not self.client or not self.target_chat_id:
            raise ValueError("Client and target chat must be set")
        
        if self.is_running:
            return
        
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
                    self.status["percent"] = (self.status["processed"] / self.status["total"]) * 100
                    self.status["current_action"] = f"Processing message {i + 1}/{self.status['total']}"
                    self._save_status()
                    
                    # Throttle
                    await asyncio.sleep(settings.MESSAGE_DELAY)
                    
                except Exception as e:
                    error_msg = f"Error processing message {i + 1}: {str(e)}"
                    self.status["errors"].append(error_msg)
                    print(error_msg)
                    self._save_status()
            
            # Send remaining album
            if current_album:
                await self._send_album(current_album)
            
            self.status["completed_at"] = datetime.now().isoformat()
            self.status["current_action"] = "Migration completed"
            self._save_status()
            
        finally:
            self.is_running = False
    
    async def _send_message(self, msg: Dict):
        """Send a single message"""
        if not self.client:
            return
        
        msg_type = msg.get("type", "text")
        text = msg.get("text", "")
        media_path = msg.get("media_path")
        
        if msg_type == "text":
            if text:
                await self.client.send_message(self.target_chat_id, text)
        elif msg_type == "image":
            if media_path and Path(media_path).exists():
                await self.client.send_document(self.target_chat_id, media_path, caption=text if text else None)
            elif text:
                await self.client.send_message(self.target_chat_id, text)
        elif msg_type == "video":
            if media_path and Path(media_path).exists():
                await self.client.send_document(self.target_chat_id, media_path, caption=text if text else None)
            elif text:
                await self.client.send_message(self.target_chat_id, text)
        elif msg_type == "audio":
            if media_path and Path(media_path).exists():
                await self.client.send_document(self.target_chat_id, media_path, caption=text if text else None)
            elif text:
                await self.client.send_message(self.target_chat_id, text)
        elif msg_type == "voice":
            if media_path and Path(media_path).exists():
                await self.client.send_voice(self.target_chat_id, media_path)
            elif text:
                await self.client.send_message(self.target_chat_id, text)
        elif msg_type in ["document", "sticker", "gif"]:
            if media_path and Path(media_path).exists():
                await self.client.send_document(self.target_chat_id, media_path, caption=text if text else None)
            elif text:
                await self.client.send_message(self.target_chat_id, text)
    
    async def _send_album(self, album_messages: List[Dict]):
        """Send media album"""
        if not self.client or not album_messages:
            return
        
        media_files = []
        captions = []
        
        for msg in album_messages:
            media_path = msg.get("media_path")
            if media_path and Path(media_path).exists():
                media_files.append(media_path)
                captions.append(msg.get("text", ""))
        
        if media_files:
            await self.client.send_media_group(self.target_chat_id, media_files, captions)
    
    def stop_migration(self):
        """Stop migration process"""
        self.is_running = False
    
    def get_status(self) -> Dict:
        """Get current migration status"""
        return self.status
