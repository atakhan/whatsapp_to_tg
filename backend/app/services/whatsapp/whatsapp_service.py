"""
Main WhatsApp service - facade that composes all components
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator

from app.core.config import settings
from app.services.whatsapp.browser_manager import BrowserManager
from app.services.whatsapp.session_manager import SessionManager
from app.services.whatsapp.connection_manager import ConnectionManager
from app.services.whatsapp.chat_parser import ChatParser
from app.services.whatsapp.message_parser import MessageParser

logger = logging.getLogger(__name__)


class WhatsAppConnectService:
    """Main WhatsApp service - facade that composes all components"""
    
    def __init__(self):
        # Initialize components
        self.browser_manager = BrowserManager()
        self.session_manager = SessionManager(
            Path(settings.WHATSAPP_SESSIONS_DIR),
            self.browser_manager
        )
        self.connection_manager = ConnectionManager(
            self.session_manager,
            self.browser_manager
        )
        self.chat_parser = ChatParser()
        self.message_parser = MessageParser()
    
    # Browser management methods
    async def initialize(self):
        """Initialize Playwright browser"""
        await self.browser_manager.initialize()
    
    async def shutdown(self):
        """Shutdown all browsers and cleanup"""
        # Cleanup all sessions
        for session_id in list(self.session_manager.sessions.keys()):
            await self.session_manager.cleanup_session(session_id)
        
        await self.browser_manager.shutdown()
    
    # Session management methods
    def get_session_path(self, session_id: str) -> Path:
        """Get path to WhatsApp session directory"""
        return self.session_manager.get_session_path(session_id)
    
    def list_existing_sessions(self) -> List[str]:
        """List all existing session IDs from disk"""
        return self.session_manager.list_existing_sessions()
    
    def cleanup_old_sessions(self, max_age_days: int = 7, max_sessions: Optional[int] = None) -> Dict[str, int]:
        """Cleanup old sessions from disk"""
        return self.session_manager.cleanup_old_sessions(max_age_days, max_sessions)
    
    async def check_session_exists(self, session_id: str) -> bool:
        """Check if session directory exists on disk"""
        return await self.session_manager.check_session_exists(session_id)
    
    async def try_reuse_session(self, session_id: str) -> Dict:
        """Try to reuse an existing WhatsApp session"""
        return await self.session_manager.try_reuse_session(session_id)
    
    async def cleanup_session(self, session_id: str) -> bool:
        """Cleanup session and close browser context"""
        return await self.session_manager.cleanup_session(session_id)
    
    def is_connected(self, session_id: str) -> bool:
        """Check if session is connected"""
        return self.session_manager.is_connected(session_id)
    
    # Connection methods
    async def start_connection(self, session_id: str) -> Dict:
        """Start WhatsApp Web connection process"""
        return await self.connection_manager.start_connection(session_id)
    
    async def get_status(self, session_id: str) -> Dict:
        """Get current connection status"""
        return await self.connection_manager.get_status(session_id)
    
    # Chat methods
    async def get_chats_streaming(self, session_id: str) -> AsyncGenerator[List[Dict], None]:
        """Get list of WhatsApp chats, streaming them as they are parsed"""
        session = self.session_manager.get_session(session_id)
        if not session or session.get('status') != 'ready':
            logger.warning("Session %s not ready for get_chats_streaming", session_id)
            return
        
        page = session['page']
        async for batch in self.chat_parser.parse_chats_streaming(page):
            yield batch
    
    async def get_chats(self, session_id: str) -> List[Dict]:
        """Get list of WhatsApp chats from the connected session"""
        session = self.session_manager.get_session(session_id)
        if not session or session.get('status') != 'ready':
            logger.warning("Session %s not ready for get_chats", session_id)
            return []
        
        page = session['page']
        return await self.chat_parser.parse_chats(page)
    
    # Message methods
    async def get_chat_messages_streaming(
        self, 
        session_id: str, 
        chat_id: str, 
        limit: Optional[int] = None,
        chat_name: Optional[str] = None
    ) -> AsyncGenerator[Dict, None]:
        """Stream messages from a specific WhatsApp chat as they are loaded"""
        session = self.session_manager.get_session(session_id)
        if not session or session.get('status') != 'ready':
            logger.warning("Session %s not ready for get_chat_messages_streaming", session_id)
            return
        
        page = session['page']
        async for item in self.message_parser.parse_messages_streaming(page, chat_id, limit, chat_name):
            yield item
    
    async def get_chat_messages(self, session_id: str, chat_id: str) -> List[Dict]:
        """Get messages from a specific WhatsApp chat"""
        session = self.session_manager.get_session(session_id)
        if not session or session.get('status') != 'ready':
            logger.warning("Session %s not ready for get_chat_messages", session_id)
            return []
        
        page = session['page']
        return await self.message_parser.parse_messages(page, chat_id)
    
    # Backward compatibility: expose sessions dict for any code that might access it directly
    @property
    def sessions(self) -> Dict:
        """Access to sessions dict for backward compatibility"""
        return self.session_manager.sessions
