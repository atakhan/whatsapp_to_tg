"""
WhatsApp Web connection service using Playwright
"""
import asyncio
import base64
import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from app.core.config import settings


class WhatsAppConnectService:
    """Manages WhatsApp Web connections via Playwright"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}  # session_id -> {browser, context, page, status}
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.sessions_dir = Path(settings.WHATSAPP_SESSIONS_DIR)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize Playwright browser"""
        if self.playwright is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
    
    async def shutdown(self):
        """Shutdown all browsers and cleanup"""
        for session_id in list(self.sessions.keys()):
            await self.cleanup_session(session_id)
        
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def get_session_path(self, session_id: str) -> Path:
        """Get path to WhatsApp session directory"""
        return self.sessions_dir / session_id
    
    async def start_connection(self, session_id: str) -> Dict:
        """
        Start WhatsApp Web connection process
        
        Returns:
            {
                "session_id": str,
                "qr_code": str (base64 PNG),
                "status": "waiting_qr",
                "expires_at": str (ISO datetime)
            }
        """
        await self.initialize()
        
        # Create session directory
        session_path = self.get_session_path(session_id)
        session_path.mkdir(parents=True, exist_ok=True)
        
        # Create browser context with persistent storage
        user_data_dir = str(session_path / "browser_data")
        context = await self.browser.new_context(
            user_data_dir=user_data_dir,
            viewport={'width': 1280, 'height': 720}
        )
        
        page = await context.new_page()
        
        # Navigate to WhatsApp Web
        await page.goto('https://web.whatsapp.com', wait_until='networkidle')
        
        # Wait for QR code to appear
        try:
            # Wait for QR code container
            qr_selector = 'div[data-ref] canvas, div[data-ref] img'
            await page.wait_for_selector(qr_selector, timeout=10000)
            
            # Get QR code as base64
            qr_element = await page.query_selector(qr_selector)
            if qr_element:
                # Take screenshot of QR code
                qr_screenshot = await qr_element.screenshot(type='png')
                qr_base64 = base64.b64encode(qr_screenshot).decode('utf-8')
            else:
                raise Exception("QR code element not found")
            
            # Calculate expiry (QR codes typically expire in ~20 seconds)
            expires_at = datetime.utcnow() + timedelta(seconds=settings.WHATSAPP_QR_REFRESH_SEC)
            
            # Store session info
            self.sessions[session_id] = {
                'browser': self.browser,
                'context': context,
                'page': page,
                'status': 'waiting_qr',
                'expires_at': expires_at.isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Start monitoring connection status in background
            asyncio.create_task(self._monitor_connection(session_id))
            
            return {
                "session_id": session_id,
                "qr_code": qr_base64,
                "status": "waiting_qr",
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            await context.close()
            raise Exception(f"Failed to get QR code: {str(e)}")
    
    async def _monitor_connection(self, session_id: str):
        """Monitor WhatsApp Web connection status in background"""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        page = session['page']
        
        try:
            # Wait for connection (check for main app container)
            # WhatsApp Web shows different selectors when connected
            connected_selectors = [
                'div[data-testid="chatlist"]',  # Chat list appears
                'div[data-testid="conversation-header"]',  # Conversation header
                'div#app > div > div > div[role="application"]'  # Main app container
            ]
            
            timeout_seconds = settings.WHATSAPP_CONNECT_TIMEOUT_SEC
            start_time = datetime.utcnow()
            
            # Poll for connection with shorter intervals
            while True:
                # Check if timeout reached
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= timeout_seconds:
                    # Check if QR expired
                    expires_at = datetime.fromisoformat(session['expires_at'])
                    if datetime.utcnow() > expires_at:
                        session['status'] = 'expired'
                    break
                
                # Check each selector
                for selector in connected_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            # Connection successful
                            session['status'] = 'ready'
                            session['connected_at'] = datetime.utcnow().isoformat()
                            return
                    except:
                        continue
                
                # Wait a bit before checking again
                await asyncio.sleep(2)
            
        except Exception as e:
            session['status'] = 'failed'
            session['error'] = str(e)
    
    async def get_status(self, session_id: str) -> Dict:
        """
        Get current connection status
        
        Returns:
            {
                "session_id": str,
                "status": "waiting_qr" | "ready" | "expired" | "failed",
                "qr_code": str (base64, if status is waiting_qr),
                "expires_at": str (if waiting_qr),
                "connected_at": str (if ready),
                "error": str (if failed)
            }
        """
        if session_id not in self.sessions:
            return {
                "session_id": session_id,
                "status": "not_found"
            }
        
        session = self.sessions[session_id]
        status = session['status']
        
        result = {
            "session_id": session_id,
            "status": status
        }
        
        # If waiting for QR, check if it expired and refresh if needed
        if status == 'waiting_qr':
            expires_at = datetime.fromisoformat(session['expires_at'])
            now = datetime.utcnow()
            
            if now > expires_at:
                # QR expired, try to get new one
                try:
                    page = session['page']
                    qr_selector = 'div[data-ref] canvas, div[data-ref] img'
                    qr_element = await page.query_selector(qr_selector)
                    
                    if qr_element:
                        qr_screenshot = await qr_element.screenshot(type='png')
                        qr_base64 = base64.b64encode(qr_screenshot).decode('utf-8')
                        new_expires = now + timedelta(seconds=settings.WHATSAPP_QR_REFRESH_SEC)
                        
                        session['expires_at'] = new_expires.isoformat()
                        result['qr_code'] = qr_base64
                        result['expires_at'] = new_expires.isoformat()
                    else:
                        session['status'] = 'expired'
                        result['status'] = 'expired'
                except:
                    session['status'] = 'expired'
                    result['status'] = 'expired'
            else:
                # QR still valid, return it
                try:
                    page = session['page']
                    qr_selector = 'div[data-ref] canvas, div[data-ref] img'
                    qr_element = await page.query_selector(qr_selector)
                    if qr_element:
                        qr_screenshot = await qr_element.screenshot(type='png')
                        qr_base64 = base64.b64encode(qr_screenshot).decode('utf-8')
                        result['qr_code'] = qr_base64
                        result['expires_at'] = session['expires_at']
                except:
                    pass
        
        if status == 'ready' and 'connected_at' in session:
            result['connected_at'] = session['connected_at']
        
        if status == 'failed' and 'error' in session:
            result['error'] = session['error']
        
        return result
    
    async def cleanup_session(self, session_id: str) -> bool:
        """Cleanup session and close browser context"""
        if session_id not in self.sessions:
            return False
        
        try:
            session = self.sessions[session_id]
            context = session.get('context')
            
            if context:
                await context.close()
            
            # Remove from active sessions
            del self.sessions[session_id]
            
            # Optionally remove session directory (keep for now to preserve login)
            # session_path = self.get_session_path(session_id)
            # if session_path.exists():
            #     import shutil
            #     shutil.rmtree(session_path)
            
            return True
        except Exception as e:
            print(f"Error cleaning up session {session_id}: {e}")
            return False
    
    def is_connected(self, session_id: str) -> bool:
        """Check if session is connected"""
        if session_id not in self.sessions:
            return False
        return self.sessions[session_id]['status'] == 'ready'


# Global service instance
whatsapp_service = WhatsAppConnectService()
