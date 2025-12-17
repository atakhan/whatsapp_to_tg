"""
WhatsApp export parser
Supports both TXT and JSON formats
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


class WhatsAppParser:
    """Parser for WhatsApp chat exports"""
    
    def __init__(self, export_path: Path):
        self.export_path = export_path
        self.messages: List[Dict] = []
    
    def parse(self) -> List[Dict]:
        """Parse WhatsApp export and return list of messages"""
        # Try to find chat file
        chat_file = self._find_chat_file()
        if not chat_file:
            raise ValueError("Chat file not found in export")
        
        # Parse based on file extension
        if chat_file.suffix == ".json":
            return self._parse_json(chat_file)
        else:
            return self._parse_txt(chat_file)
    
    def _find_chat_file(self) -> Optional[Path]:
        """Find chat file in export directory"""
        # Look for common patterns
        patterns = [
            "*_chat.txt",
            "messages.json",
            "*.txt",
            "*.json"
        ]
        
        for pattern in patterns:
            files = list(self.export_path.rglob(pattern))
            if files:
                # Prefer chat.txt or messages.json
                for file in files:
                    if "chat" in file.name.lower() or "messages" in file.name.lower():
                        return file
                return files[0]
        
        return None
    
    def _parse_txt(self, file_path: Path) -> List[Dict]:
        """Parse TXT format WhatsApp export"""
        messages = []
        
        # Common patterns for different locales
        patterns = [
            # Format: [DD.MM.YYYY, HH:MM:SS] Sender: Message
            r'\[(\d{1,2})\.(\d{1,2})\.(\d{4}),\s*(\d{1,2}):(\d{1,2}):(\d{1,2})\]\s*(.+?):\s*(.+)',
            # Format: [MM/DD/YYYY, HH:MM:SS AM/PM] Sender: Message
            r'\[(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2}):(\d{1,2}):(\d{1,2})\s*(AM|PM)\]\s*(.+?):\s*(.+)',
            # Format: DD/MM/YYYY, HH:MM - Sender: Message
            r'(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2}):(\d{1,2})\s*-\s*(.+?):\s*(.+)',
        ]
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Try each pattern
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                try:
                    msg = self._parse_txt_match(match, pattern)
                    if msg:
                        messages.append(msg)
                except Exception as e:
                    logger.warning(
                        "Error parsing message",
                        extra={
                            "error_code": "WHATSAPP_PARSE_MESSAGE_FAIL",
                            "extra_data": {"pattern": pattern},
                        },
                        exc_info=True,
                    )
                    continue
        
        # Sort by timestamp
        messages.sort(key=lambda x: x['timestamp'])
        
        # Group albums
        messages = self._group_albums(messages)
        
        return messages
    
    def _parse_txt_match(self, match: re.Match, pattern: str) -> Optional[Dict]:
        """Parse a single TXT match"""
        groups = match.groups()
        
        # Extract timestamp
        try:
            if len(groups) >= 7:
                if 'AM' in pattern or 'PM' in pattern:
                    # US format with AM/PM
                    month, day, year, hour, minute, second, am_pm, sender, text = groups
                    hour = int(hour)
                    if am_pm == 'PM' and hour != 12:
                        hour += 12
                    elif am_pm == 'AM' and hour == 12:
                        hour = 0
                    dt = datetime(int(year), int(month), int(day), hour, int(minute), int(second))
                else:
                    # European format
                    day, month, year, hour, minute, second, sender, text = groups[:8]
                    dt = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
            else:
                # Simple format
                day, month, year, hour, minute, sender, text = groups
                dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
            
            timestamp = int(dt.timestamp())
        except (ValueError, IndexError) as e:
            logger.warning(
                "Error parsing timestamp",
                extra={
                    "error_code": "WHATSAPP_PARSE_TIMESTAMP_FAIL",
                    "extra_data": {"raw_groups": groups},
                },
                exc_info=True,
            )
            return None
        
        # Detect media
        media_path = None
        msg_type = "text"
        
        # Check for media indicators
        if "<Media omitted>" in text or "Media omitted" in text:
            media_path = self._find_media_file(timestamp, sender)
            if media_path:
                msg_type = self._detect_media_type(media_path)
            text = text.replace("<Media omitted>", "").replace("Media omitted", "").strip()
        
        return {
            "timestamp": timestamp,
            "sender": sender.strip(),
            "type": msg_type,
            "text": text.strip() if text else "",
            "media_path": str(media_path) if media_path else None,
            "is_album": False,
            "album_group_id": None
        }
    
    def _parse_json(self, file_path: Path) -> List[Dict]:
        """Parse JSON format WhatsApp export (iOS)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        messages = []
        
        # Handle different JSON structures
        if isinstance(data, list):
            chat_data = data
        elif isinstance(data, dict):
            chat_data = data.get("messages", [])
        else:
            return []
        
        for msg_data in chat_data:
            try:
                msg = self._parse_json_message(msg_data)
                if msg:
                    messages.append(msg)
            except Exception as e:
                logger.warning(
                    "Error parsing JSON message",
                    extra={
                        "error_code": "WHATSAPP_PARSE_JSON_MESSAGE_FAIL",
                        "extra_data": {"keys": list(msg_data.keys())},
                    },
                    exc_info=True,
                )
                continue
        
        # Sort by timestamp
        messages.sort(key=lambda x: x['timestamp'])
        
        # Group albums
        messages = self._group_albums(messages)
        
        return messages
    
    def _parse_json_message(self, msg_data: Dict) -> Optional[Dict]:
        """Parse a single JSON message"""
        # Extract timestamp
        timestamp_str = msg_data.get("date", msg_data.get("timestamp"))
        if isinstance(timestamp_str, str):
            # Parse ISO format or other
            try:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                timestamp = int(dt.timestamp())
            except:
                timestamp = int(msg_data.get("timestamp_ms", 0) / 1000)
        else:
            timestamp = int(msg_data.get("timestamp_ms", 0) / 1000)
        
        # Extract sender
        sender = msg_data.get("from", msg_data.get("sender_name", "Unknown"))
        
        # Extract text
        text = msg_data.get("text", "")
        if isinstance(text, list):
            text = " ".join(text)
        
        # Extract media
        media_path = None
        msg_type = "text"
        
        if msg_data.get("photo") or msg_data.get("image"):
            media_path = self._find_media_file(timestamp, sender, "image")
            msg_type = "image"
        elif msg_data.get("video"):
            media_path = self._find_media_file(timestamp, sender, "video")
            msg_type = "video"
        elif msg_data.get("audio") or msg_data.get("ptt"):
            media_path = self._find_media_file(timestamp, sender, "audio")
            msg_type = "voice" if msg_data.get("ptt") else "audio"
        elif msg_data.get("document"):
            media_path = self._find_media_file(timestamp, sender, "document")
            msg_type = "document"
        elif msg_data.get("sticker"):
            media_path = self._find_media_file(timestamp, sender, "sticker")
            msg_type = "sticker"
        elif msg_data.get("animated_gif"):
            media_path = self._find_media_file(timestamp, sender, "gif")
            msg_type = "gif"
        
        return {
            "timestamp": timestamp,
            "sender": sender,
            "type": msg_type,
            "text": text.strip() if text else "",
            "media_path": str(media_path) if media_path else None,
            "is_album": False,
            "album_group_id": None
        }
    
    def _find_media_file(
        self,
        timestamp: int,
        sender: str,
        media_type: Optional[str] = None
    ) -> Optional[Path]:
        """Find media file by timestamp and sender"""
        # Media directories
        media_dirs = {
            "image": ["Media/Images", "Media/IMG", "Images"],
            "video": ["Media/Videos", "Media/VID", "Videos"],
            "audio": ["Media/Audio", "Media/AUD", "Audio"],
            "voice": ["Media/Voice Notes", "Media/PTT", "Voice Notes"],
            "document": ["Media/Documents", "Media/DOC", "Documents"],
            "sticker": ["Media/Stickers", "Stickers"],
            "gif": ["Media/Animated GIFs", "Media/GIF", "Animated GIFs"]
        }
        
        # Convert timestamp to date for matching
        dt = datetime.fromtimestamp(timestamp)
        date_str = dt.strftime("%Y%m%d")
        
        # Search in media directories
        search_dirs = []
        if media_type and media_type in media_dirs:
            search_dirs = media_dirs[media_type]
        else:
            # Search all media directories
            for dirs in media_dirs.values():
                search_dirs.extend(dirs)
        
        for media_dir in search_dirs:
            media_path = self.export_path / media_dir
            if media_path.exists():
                # Look for files matching date pattern
                for file in media_path.iterdir():
                    if file.is_file() and date_str in file.name:
                        return file
        
        return None
    
    def _detect_media_type(self, file_path: Path) -> str:
        """Detect media type from file extension"""
        ext = file_path.suffix.lower()
        
        image_exts = ['.jpg', '.jpeg', '.png', '.webp']
        video_exts = ['.mp4', '.avi', '.mov', '.mkv']
        audio_exts = ['.mp3', '.m4a', '.ogg', '.wav']
        
        if ext in image_exts:
            return "image"
        elif ext in video_exts:
            return "video"
        elif ext in audio_exts:
            return "audio"
        elif ext == '.gif':
            return "gif"
        else:
            return "document"
    
    def _group_albums(self, messages: List[Dict]) -> List[Dict]:
        """Group consecutive images from same sender into albums"""
        albums = []
        current_album = []
        album_group_id = None
        
        for i, msg in enumerate(messages):
            # Check if this message can be part of an album
            if (msg['type'] == 'image' and 
                msg['media_path'] and
                (not current_album or 
                 (msg['sender'] == current_album[-1]['sender'] and
                  msg['timestamp'] - current_album[-1]['timestamp'] < 120))):  # Within 2 minutes
                
                if not current_album:
                    album_group_id = f"album_{msg['timestamp']}"
                
                msg['is_album'] = True
                msg['album_group_id'] = album_group_id
                current_album.append(msg)
            else:
                # End current album
                if current_album:
                    albums.append(current_album)
                    current_album = []
                    album_group_id = None
                
                albums.append([msg])
        
        # Add remaining album
        if current_album:
            albums.append(current_album)
        
        # Flatten back to list
        result = []
        for album in albums:
            result.extend(album)
        
        return result
