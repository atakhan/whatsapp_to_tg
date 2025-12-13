"""
File management utilities
"""
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional
import uuid


class FileManager:
    """Manages temporary files and sessions"""
    
    def __init__(self, tmp_dir: str, sessions_dir: str):
        self.tmp_dir = Path(tmp_dir)
        self.sessions_dir = Path(sessions_dir)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def create_session_dir(self, session_id: str) -> Path:
        """Create temporary directory for a session"""
        session_path = self.tmp_dir / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        return session_path
    
    def extract_zip(self, zip_path: Path, session_id: str) -> Path:
        """
        Extract WhatsApp ZIP export to session directory
        
        Returns:
            Path to extracted directory
        """
        session_dir = self.create_session_dir(session_id)
        extract_path = session_dir / "extracted"
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        return extract_path
    
    def get_session_path(self, session_id: str) -> Path:
        """Get path to session directory"""
        return self.tmp_dir / session_id
    
    def cleanup_session(self, session_id: str) -> bool:
        """Remove all files for a session"""
        try:
            session_path = self.get_session_path(session_id)
            if session_path.exists():
                shutil.rmtree(session_path)
            return True
        except Exception as e:
            print(f"Error cleaning up session {session_id}: {e}")
            return False
    
    def get_telegram_session_path(self, user_id: int) -> Path:
        """Get path to Telegram session file"""
        return self.sessions_dir / f"{user_id}.session"
    
    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        return str(uuid.uuid4())
