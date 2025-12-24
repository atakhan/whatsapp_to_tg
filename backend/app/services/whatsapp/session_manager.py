"""
Session management for WhatsApp Web
"""
import asyncio
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from playwright.async_api import BrowserContext, Page

from app.services.whatsapp.browser_manager import BrowserManager

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages WhatsApp sessions on disk and in memory"""
    
    def __init__(self, sessions_dir: Path, browser_manager: BrowserManager):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.browser_manager = browser_manager
        self.sessions: Dict[str, Dict] = {}  # session_id -> {context, page, status, ...}
    
    def get_session_path(self, session_id: str) -> Path:
        """Get path to WhatsApp session directory"""
        return self.sessions_dir / session_id
    
    def list_existing_sessions(self) -> List[str]:
        """List all existing session IDs from disk"""
        if not self.sessions_dir.exists():
            return []
        
        sessions = []
        for item in self.sessions_dir.iterdir():
            if item.is_dir():
                # Check if session has browser_data (indicates it was used)
                browser_data_path = item / "browser_data"
                if browser_data_path.exists():
                    sessions.append(item.name)
        return sessions
    
    async def check_session_exists(self, session_id: str) -> bool:
        """Check if session directory exists on disk"""
        session_path = self.get_session_path(session_id)
        return session_path.exists()
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session from memory cache"""
        return self.sessions.get(session_id)
    
    def set_session(self, session_id: str, session_data: Dict):
        """Store session in memory cache"""
        self.sessions[session_id] = session_data
    
    def is_session_ready(self, session_id: str) -> bool:
        """Check if session exists in memory and is ready"""
        session = self.sessions.get(session_id)
        return session is not None and session.get('status') == 'ready'
    
    async def try_reuse_session(self, session_id: str) -> Dict:
        """
        Try to reuse an existing WhatsApp session.
        Returns status dict with 'reused' boolean and session info.
        """
        # Check if session already exists in memory and is ready
        if self.is_session_ready(session_id):
            existing_session = self.sessions[session_id]
            logger.info("Session %s already loaded and ready", session_id)
            return {
                "reused": True,
                "status": "ready",
                "connected_at": existing_session.get('connected_at', '')
            }
        
        session_path = self.get_session_path(session_id)
        
        if not session_path.exists():
            return {
                "reused": False,
                "reason": "Session directory not found"
            }
        
        browser_data_path = session_path / "browser_data"
        if not browser_data_path.exists():
            return {
                "reused": False,
                "reason": "No browser data found"
            }
        
        # Try to load the session
        try:
            await self.browser_manager.initialize()
            
            # Check again if session was loaded by another process
            if self.is_session_ready(session_id):
                existing_session = self.sessions[session_id]
                return {
                    "reused": True,
                    "status": "ready",
                    "connected_at": existing_session.get('connected_at', '')
                }
            
            # Create browser context with existing persistent storage
            user_data_dir = str(browser_data_path)
            context = await self.browser_manager.create_persistent_context(user_data_dir)
            page = await self.browser_manager.create_page(context)
            
            # Navigate to WhatsApp Web
            await page.goto('https://web.whatsapp.com', wait_until='networkidle')
            await asyncio.sleep(3)  # Wait for page to load
            
            # Check if already connected (look for chat list or main interface)
            connected_selectors = [
                'div[data-testid="chatlist"]',
                'div[role="listbox"]',
                'div[data-testid="chat"]',
                'div[aria-label*="Chat"]',
            ]
            
            is_connected = False
            for selector in connected_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        box = await element.bounding_box()
                        if box and box['width'] > 0 and box['height'] > 0:
                            is_connected = True
                            break
                except Exception:
                    continue
            
            if is_connected:
                # Session is valid and connected
                self.sessions[session_id] = {
                    'context': context,
                    'page': page,
                    'status': 'ready',
                    'connected_at': datetime.utcnow().isoformat(),
                }
                
                logger.info(
                    "Successfully reused WhatsApp session %s",
                    session_id,
                    extra={
                        "error_code": None,
                        "extra_data": {"session_id": session_id},
                    },
                )
                
                return {
                    "reused": True,
                    "status": "ready",
                    "connected_at": self.sessions[session_id]['connected_at']
                }
            else:
                # Session exists but not connected - need QR
                await context.close()
                return {
                    "reused": False,
                    "reason": "Session exists but not connected - QR required"
                }
                
        except Exception as e:
            logger.warning(
                "Failed to reuse WhatsApp session %s: %s",
                session_id,
                str(e),
                extra={
                    "error_code": "WHATSAPP_SESSION_REUSE_FAIL",
                    "extra_data": {"session_id": session_id, "error": str(e)},
                },
            )
            return {
                "reused": False,
                "reason": f"Error reusing session: {str(e)}"
            }
    
    async def cleanup_session(self, session_id: str) -> bool:
        """Cleanup and close a session"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        context: Optional[BrowserContext] = session.get('context')
        
        if context:
            try:
                await context.close()
            except Exception as e:
                logger.warning("Error closing context for session %s: %s", session_id, str(e))
        
        del self.sessions[session_id]
        logger.info("Session %s cleaned up", session_id)
        return True
    
    def is_connected(self, session_id: str) -> bool:
        """Check if session is connected"""
        return self.is_session_ready(session_id)
    
    def cleanup_old_sessions(self, max_age_days: int = 7, max_sessions: Optional[int] = None) -> Dict[str, int]:
        """
        Cleanup old sessions from disk
        
        Args:
            max_age_days: Delete sessions older than this many days
            max_sessions: If provided, keep only the N most recent sessions
        
        Returns:
            Dict with cleanup statistics
        """
        if not self.sessions_dir.exists():
            return {"deleted": 0, "kept": 0, "total_before": 0}
        
        sessions_to_check = []
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        # Collect all sessions with their metadata
        for item in self.sessions_dir.iterdir():
            if not item.is_dir():
                continue
            
            browser_data_path = item / "browser_data"
            if not browser_data_path.exists():
                continue
            
            # Get modification time of browser_data directory
            try:
                mtime = datetime.fromtimestamp(browser_data_path.stat().st_mtime)
                sessions_to_check.append({
                    "id": item.name,
                    "path": item,
                    "mtime": mtime,
                    "age_days": (datetime.now() - mtime).days
                })
            except Exception as e:
                logger.warning("Error checking session %s: %s", item.name, str(e))
                continue
        
        deleted_count = 0
        kept_count = 0
        
        # Sort by modification time (newest first)
        sessions_to_check.sort(key=lambda x: x["mtime"], reverse=True)
        
        # If max_sessions is set, keep only the N most recent
        if max_sessions and len(sessions_to_check) > max_sessions:
            sessions_to_delete = sessions_to_check[max_sessions:]
            for session_info in sessions_to_delete:
                try:
                    shutil.rmtree(session_info["path"])
                    deleted_count += 1
                    logger.info("Deleted old session %s (age: %d days, exceeded max_sessions limit)", 
                              session_info["id"], session_info["age_days"])
                except Exception as e:
                    logger.warning("Error deleting session %s: %s", session_info["id"], str(e))
            
            # Update kept_count for remaining sessions
            sessions_to_check = sessions_to_check[:max_sessions]
        
        # Delete sessions older than max_age_days
        for session_info in sessions_to_check:
            if session_info["mtime"] < cutoff_date:
                # Skip if already deleted
                if not session_info["path"].exists():
                    continue
                
                try:
                    shutil.rmtree(session_info["path"])
                    deleted_count += 1
                    logger.info("Deleted old session %s (age: %d days)", 
                              session_info["id"], session_info["age_days"])
                except Exception as e:
                    logger.warning("Error deleting session %s: %s", session_info["id"], str(e))
            else:
                if session_info["path"].exists():
                    kept_count += 1
        
        return {
            "deleted": deleted_count,
            "kept": kept_count,
            "total_before": len(sessions_to_check) + deleted_count
        }
