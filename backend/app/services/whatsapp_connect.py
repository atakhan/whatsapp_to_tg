"""
WhatsApp Web connection service using Playwright
"""
import asyncio
import base64
import json
import random
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import logging

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError

from app.core.config import settings
from app.core.logging_setup import (
    set_correlation_ids,
    set_request_context,
    trace_id_ctx,
    request_id_ctx,
)

logger = logging.getLogger(__name__)

QR_WAIT_TIMEOUT_MS = 30000  # Allow slower networks to fetch QR


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
            logger.info("Starting Playwright...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            logger.info("Playwright started, browser launched (headless)")
    
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
    
    async def try_reuse_session(self, session_id: str) -> Dict:
        """
        Try to reuse an existing WhatsApp session.
        Returns status dict with 'reused' boolean and session info.
        """
        # Check if session already exists in memory and is ready
        if session_id in self.sessions:
            existing_session = self.sessions[session_id]
            if existing_session.get('status') == 'ready':
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
            await self.initialize()
            
            # Check again if session was loaded by another process
            if session_id in self.sessions:
                existing_session = self.sessions[session_id]
                if existing_session.get('status') == 'ready':
                    return {
                        "reused": True,
                        "status": "ready",
                        "connected_at": existing_session.get('connected_at', '')
                    }
            
            # Create browser context with existing persistent storage
            user_data_dir = str(browser_data_path)
            user_agent = (
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=True,
                viewport={'width': 1280, 'height': 720},
                user_agent=user_agent,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                ],
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            )
            
            # Get the first page
            pages = context.pages
            if pages:
                page = pages[0]
            else:
                page = await context.new_page()
            
            # Override webdriver property
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
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
        logger.info("Start connection for session %s", session_id)
        
        # Check if session already exists and is ready
        if session_id in self.sessions:
            existing_session = self.sessions[session_id]
            if existing_session.get('status') == 'ready':
                logger.info("Session %s already connected, returning status", session_id)
                status = await self.get_status(session_id)
                return {
                    "session_id": session_id,
                    "qr_code": "",
                    "status": "ready",
                    "expires_at": ""
                }
        
        # Create session directory
        session_path = self.get_session_path(session_id)
        session_path.mkdir(parents=True, exist_ok=True)
        
        # Create browser context with persistent storage using launch_persistent_context
        user_data_dir = str(session_path / "browser_data")
        context = None
        qr_selector = 'div[data-ref] canvas, div[data-ref] img'
        try:
            # Use realistic user agent to avoid detection as headless browser
            user_agent = (
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=True,
                viewport={'width': 1280, 'height': 720},
                user_agent=user_agent,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                ],
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            )
            
            # Get the first page from persistent context
            pages = context.pages
            if pages:
                page = pages[0]
            else:
                page = await context.new_page()
            
            # Override webdriver property to avoid detection
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            # Navigate to WhatsApp Web
            target_url = 'https://web.whatsapp.com'
            logger.info("Session %s navigating to %s ...", session_id, target_url)
            await page.goto(target_url, wait_until='networkidle')
            logger.info("Session %s page loaded, current url=%s", session_id, page.url)
            
            # Wait for page to fully render and JavaScript to execute
            # WhatsApp Web may need more time to render QR code
            await asyncio.sleep(10)
            
            # Wait for any canvas elements to appear (QR is usually rendered as canvas)
            try:
                await page.wait_for_selector('canvas', timeout=15000)
                logger.info("Session %s canvas elements appeared on page", session_id)
            except Exception:
                logger.warning("Session %s no canvas elements found after wait", session_id)
            
            # Check page title and basic structure
            title = await page.title()
            logger.info("Session %s page title: %s", session_id, title)
            
            # Check if page has loaded properly (look for common WhatsApp Web elements)
            try:
                # Wait for app container to appear
                await page.wait_for_selector('div#app', timeout=10000)
                logger.info("Session %s WhatsApp app container found", session_id)
                
                # Diagnostic: check what elements are actually present
                try:
                    canvas_count = await page.evaluate("document.querySelectorAll('canvas').length")
                    div_ref_count = await page.evaluate("document.querySelectorAll('div[data-ref]').length")
                    logger.info(
                        "Session %s page diagnostics: canvas elements=%d, div[data-ref] elements=%d",
                        session_id,
                        canvas_count,
                        div_ref_count,
                    )
                    
                    # Check if there's any QR-related text on page
                    page_text = await page.evaluate("document.body.innerText.substring(0, 500)")
                    if 'QR' in page_text.upper() or 'сканир' in page_text.lower():
                        logger.info("Session %s found QR-related text on page", session_id)
                    else:
                        logger.warning(
                            "Session %s no QR-related text found on page",
                            session_id,
                            extra={
                                "error_code": "WHATSAPP_QR_TEXT_MISSING",
                                "extra_data": {"text_preview": page_text[:200]},
                            },
                        )
                except Exception as diag_error:
                    logger.warning("Session %s diagnostic check failed: %s", session_id, str(diag_error))
                    
            except Exception as e:
                logger.warning(
                    "Session %s WhatsApp app container not found",
                    session_id,
                    extra={
                        "error_code": "WHATSAPP_APP_CONTAINER_MISSING",
                        "extra_data": {"error": str(e)},
                    },
                )
            
            # First, try to find QR by canvas size (QR codes are usually square, 200-400px)
            qr_element = None
            used_selector = None
            
            try:
                logger.info("Session %s searching for QR by canvas size (square, 200-400px)", session_id)
                all_canvases = await page.query_selector_all('canvas')
                logger.info("Session %s found %d canvas elements", session_id, len(all_canvases))
                
                for idx, canvas in enumerate(all_canvases):
                    try:
                        box = await canvas.bounding_box()
                        if box:
                            width = box['width']
                            height = box['height']
                            # QR codes are usually square-ish (ratio close to 1:1)
                            ratio = width / height if height > 0 else 0
                            is_square = 0.8 <= ratio <= 1.2
                            is_qr_size = 150 <= width <= 500 and 150 <= height <= 500
                            
                            logger.debug(
                                "Session %s canvas[%d]: %dx%d (ratio=%.2f, square=%s, qr_size=%s)",
                                session_id, idx, int(width), int(height), ratio, is_square, is_qr_size
                            )
                            
                            if is_square and is_qr_size:
                                logger.info(
                                    "Session %s found potential QR canvas[%d]: %dx%d",
                                    session_id, idx, int(width), int(height)
                                )
                                qr_element = canvas
                                used_selector = f'canvas[{idx}]'
                                break
                    except Exception as e:
                        logger.debug("Session %s error checking canvas[%d]: %s", session_id, idx, str(e))
                        continue
            except Exception as e:
                logger.warning("Session %s error searching by canvas size: %s", session_id, str(e))
            
            # If not found by size, try multiple QR selectors (WhatsApp may use different structures)
            if not qr_element:
                qr_selectors = [
                    'div[data-ref] canvas',
                    'div[data-ref] img',
                    'canvas[aria-label*="QR"]',
                    'div[data-ref]',
                    'div._2EZ_m canvas',
                    'div#app canvas',
                    'canvas',
                ]
                
                for selector in qr_selectors:
                    try:
                        logger.info("Session %s trying QR selector: %s", session_id, selector)
                        await page.wait_for_selector(selector, timeout=5000)
                        qr_element = await page.query_selector(selector)
                        if qr_element:
                            # Check if element is visible and has content
                            box = await qr_element.bounding_box()
                            if box and box['width'] > 0 and box['height'] > 0:
                                logger.info("Session %s found QR with selector: %s (size: %dx%d)", 
                                          session_id, selector, int(box['width']), int(box['height']))
                                used_selector = selector
                                break
                    except Exception as e:
                        logger.debug("Session %s selector %s failed: %s", session_id, selector, str(e))
                        continue
            
            if not qr_element:
                # Fallback: try original combined selector
                logger.info("Session %s trying original combined selector as fallback (timeout=%dms)", 
                          session_id, QR_WAIT_TIMEOUT_MS)
                try:
                    await page.wait_for_selector(qr_selector, timeout=QR_WAIT_TIMEOUT_MS)
                    qr_element = await page.query_selector(qr_selector)
                    used_selector = qr_selector
                    logger.info("Session %s found QR with fallback selector", session_id)
                except TimeoutError:
                    # Take screenshot and log page structure for debugging
                    try:
                        screenshot = await page.screenshot(type='png', full_page=True)
                        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
                        
                        # Get page HTML snippet for diagnostics
                        html_snippet = await page.evaluate("""
                            () => {
                                const app = document.querySelector('div#app');
                                return app ? app.innerHTML.substring(0, 500) : 'No app container';
                            }
                        """)
                        
                        logger.error(
                            "Session %s QR not found after all selectors, timeout reached",
                            session_id,
                            extra={
                                "error_code": "WHATSAPP_QR_TIMEOUT",
                                "extra_data": {
                                    "selectors_tried": qr_selectors + [qr_selector],
                                    "page_url": page.url,
                                    "page_title": await page.title(),
                                    "screenshot_size": len(screenshot_b64),
                                    "html_snippet": html_snippet[:200] if html_snippet else None,
                                },
                            },
                        )
                    except Exception as screenshot_error:
                        logger.error(
                            "Session %s QR timeout and failed to capture screenshot",
                            session_id,
                            extra={
                                "error_code": "WHATSAPP_QR_TIMEOUT",
                                "extra_data": {"screenshot_error": str(screenshot_error)},
                            },
                        )
                    raise TimeoutError(f"QR selector not found after {QR_WAIT_TIMEOUT_MS}ms")
                except Exception as e:
                    logger.error(
                        "Session %s error in fallback selector",
                        session_id,
                        extra={
                            "error_code": "WHATSAPP_QR_FETCH_FAIL",
                            "extra_data": {"error": str(e), "selector": qr_selector},
                        },
                        exc_info=True,
                    )
                    raise
            
            # Get QR code as base64 (qr_element should be found by now)
            if qr_element:
                # Take screenshot of QR code
                qr_screenshot = await qr_element.screenshot(type='png')
                qr_base64 = base64.b64encode(qr_screenshot).decode('utf-8')
                logger.info(
                    "Session %s QR captured (%d bytes base64) using selector: %s",
                    session_id,
                    len(qr_base64),
                    used_selector or qr_selector,
                )
            else:
                logger.error(
                    "Session %s QR element not found after all selectors",
                    session_id,
                    extra={
                        "error_code": "WHATSAPP_QR_NOT_FOUND",
                        "extra_data": {"selectors_tried": qr_selectors + [qr_selector]},
                    },
                )
                raise Exception("QR code element not found")
            
            # Calculate expiry (QR codes typically expire in ~20 seconds)
            expires_at = datetime.utcnow() + timedelta(seconds=settings.WHATSAPP_QR_REFRESH_SEC)
            
            # Store session info
            self.sessions[session_id] = {
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
            
        except TimeoutError as e:
            logger.error(
                "Session %s timed out waiting for QR selector",
                session_id,
                extra={
                    "error_code": "WHATSAPP_QR_TIMEOUT",
                    "extra_data": {"selector": qr_selector, "timeout_ms": QR_WAIT_TIMEOUT_MS},
                },
                exc_info=True,
            )
            if context:
                await context.close()
            raise Exception(f"Failed to get QR code (timeout {QR_WAIT_TIMEOUT_MS} ms)") from e
        except Exception as e:
            logger.error(
                "Session %s failed to obtain QR",
                session_id,
                extra={
                    "error_code": "WHATSAPP_QR_FETCH_FAIL",
                    "extra_data": {"selector": qr_selector},
                },
                exc_info=True,
            )
            if context:
                await context.close()
            raise Exception(f"Failed to get QR code: {str(e)}")
    
    async def _monitor_connection(self, session_id: str):
        """Monitor WhatsApp Web connection status in background"""
        # Ensure correlation ids exist in background task
        set_correlation_ids(trace_id_ctx.get(), request_id_ctx.get())
        set_request_context()

        if session_id not in self.sessions:
            logger.warning("Session %s not found for monitoring", session_id)
            return
        
        session = self.sessions[session_id]
        page = session['page']
        
        logger.info(
            "Session %s starting connection monitoring (timeout=%ds)",
            session_id,
            settings.WHATSAPP_CONNECT_TIMEOUT_SEC,
        )
        
        try:
            # Wait for connection (check for main app container)
            # WhatsApp Web shows different selectors when connected
            connected_selectors = [
                'div[data-testid="chatlist"]',  # Chat list appears
                'div[data-testid="conversation-header"]',  # Conversation header
                'div#app > div > div > div[role="application"]',  # Main app container
                'div[data-testid="intro-md-beta-logo"]',  # Intro screen (also indicates connection)
                'div[aria-label*="Chat"]',  # Chat area
                'div[data-testid="chat"]',  # Chat container
                'nav[aria-label*="Chat"]',  # Navigation with chats
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
                        logger.warning(
                            "Session %s QR expired during monitor",
                            session_id,
                            extra={
                                "error_code": "WHATSAPP_QR_EXPIRED",
                                "extra_data": {"elapsed_sec": elapsed, "timeout_sec": timeout_seconds},
                            },
                        )
                    break
                
                # First check: QR code disappeared (good sign)
                try:
                    qr_selector = 'div[data-ref] canvas, div[data-ref] img'
                    qr_element = await page.query_selector(qr_selector)
                    if not qr_element:
                        # QR disappeared, check for connection indicators
                        logger.info("Session %s QR code disappeared, checking for connection...", session_id)
                except:
                    pass
                
                # Check each selector for connection indicators
                for selector in connected_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            # Check if element is visible
                            box = await element.bounding_box()
                            if box and box['width'] > 0 and box['height'] > 0:
                                # Connection successful
                                logger.info(
                                    "Session %s connection successful! Found selector: %s",
                                    session_id,
                                    selector,
                                )
                                session['status'] = 'ready'
                                session['connected_at'] = datetime.utcnow().isoformat()
                                return
                    except Exception as e:
                        logger.debug("Session %s selector %s check failed: %s", session_id, selector, str(e))
                        continue
                
                # Log progress every 10 seconds
                if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                    logger.info(
                        "Session %s still waiting for connection (elapsed: %ds, timeout: %ds)",
                        session_id,
                        int(elapsed),
                        timeout_seconds,
                    )
                
                # Wait a bit before checking again
                await asyncio.sleep(2)
            
        except Exception as e:
            session['status'] = 'failed'
            session['error'] = str(e)
            logger.error(
                "Session %s monitor failed",
                session_id,
                extra={
                    "error_code": "WHATSAPP_MONITOR_FAIL",
                    "extra_data": {"session_id": session_id},
                },
                exc_info=True,
            )
    
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
                        logger.warning(
                            "Session %s QR element missing on refresh",
                            session_id,
                            extra={
                                "error_code": "WHATSAPP_QR_REFRESH_MISSING",
                                "extra_data": {"selector": qr_selector},
                            },
                        )
                except Exception:
                    session['status'] = 'expired'
                    result['status'] = 'expired'
                    logger.warning(
                        "Session %s QR refresh failed",
                        session_id,
                        extra={
                            "error_code": "WHATSAPP_QR_REFRESH_FAIL",
                            "extra_data": {"selector": qr_selector},
                        },
                        exc_info=True,
                    )
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
                except Exception:
                    pass
        
        if status == 'ready':
            result['connected'] = True
            if 'connected_at' in session:
                result['connected_at'] = session['connected_at']
        else:
            result['connected'] = False
        
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
            logger.error(
                "Failed to cleanup WhatsApp session",
                extra={
                    "error_code": "WHATSAPP_SESSION_CLEANUP_FAIL",
                    "extra_data": {"session_id": session_id},
                },
                exc_info=True,
            )
            return False
    
    def is_connected(self, session_id: str) -> bool:
        """Check if session is connected"""
        if session_id not in self.sessions:
            return False
        return self.sessions[session_id]['status'] == 'ready'
    
    async def get_chats(self, session_id: str) -> List[Dict]:
        """
        Get list of WhatsApp chats from the connected session
        
        Returns list of chats with:
        - id: chat ID (phone number or group ID)
        - name: chat name
        - type: "personal" or "group"
        - avatar: avatar URL (if available)
        - message_count: approximate message count (0 if not available)
        - is_group: boolean indicating if it's a group chat
        """
        if session_id not in self.sessions:
            logger.warning("Session %s not found for get_chats", session_id)
            return []
        
        session = self.sessions[session_id]
        
        if session['status'] != 'ready':
            logger.warning(
                "Session %s not ready for get_chats (status: %s)",
                session_id,
                session['status'],
            )
            return []
        
        page = session['page']
        
        try:
            logger.info("Session %s starting to fetch chats list", session_id)
            
            # Wait a bit for page to fully load
            await asyncio.sleep(2)
            
            # Try multiple selectors for chat list container
            chatlist_selectors = [
                'div[data-testid="chatlist"]',
                'div[role="listbox"]',
                'div[aria-label*="Chat"]',
                'div#app > div > div > div[role="application"] > div > div',
                'div[data-testid="chat"]',
            ]
            
            chatlist_found = False
            for selector in chatlist_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    logger.info("Session %s chat list container found with selector: %s", session_id, selector)
                    chatlist_found = True
                    break
                except Exception:
                    continue
            
            if not chatlist_found:
                logger.warning(
                    "Session %s chat list container not found with any selector, trying to parse anyway",
                    session_id,
                    extra={
                        "error_code": "WHATSAPP_CHATLIST_NOT_FOUND",
                        "extra_data": {"selectors_tried": chatlist_selectors},
                    },
                )
            
            # Scroll to top to ensure we start from the beginning
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # Try to scroll down to load more chats (lazy loading) - with human-like delays
            try:
                # Scroll down gradually to trigger lazy loading
                for i in range(3):
                    scroll_amount = random.randint(400, 600)  # Random scroll amount
                    await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    await asyncio.sleep(random.uniform(0.8, 1.5))  # Human-like delay
                # Scroll back to top
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                logger.debug("Session %s scroll failed: %s", session_id, str(e))
            
            # Wait a bit more for chats to render (human-like delay)
            await asyncio.sleep(random.uniform(2.0, 3.0))
            
            # Parse chats using JavaScript evaluation
            chats_data = await page.evaluate("""
                () => {
                    const chats = [];
                    // Try multiple selectors for chat items
                    const chatSelectors = [
                        'div[data-testid="cell-frame-container"]',
                        'div[role="row"]',
                        'div[data-testid="chat"]',
                        'div[aria-label*="Chat"]',
                        'div[aria-label*="чат"]',
                        'div[aria-label*="групп"]',
                        'div[aria-label*="group"]',
                        'div[role="listbox"] > div',
                        'div[data-testid="list"] > div',
                    ];
                    
                    let chatElements = [];
                    for (const selector of chatSelectors) {
                        chatElements = document.querySelectorAll(selector);
                        if (chatElements.length > 0) {
                            console.log('Found ' + chatElements.length + ' elements with selector: ' + selector);
                            break;
                        }
                    }
                    
                    // If no elements found, try to find any clickable divs that might be chats
                    if (chatElements.length === 0) {
                        const allDivs = document.querySelectorAll('div[role="row"], div[aria-label]');
                        chatElements = Array.from(allDivs).filter(div => {
                            const ariaLabel = div.getAttribute('aria-label') || '';
                            return ariaLabel.includes('Chat') || ariaLabel.includes('чат') || 
                                   ariaLabel.includes('group') || ariaLabel.includes('групп');
                        });
                        console.log('Found ' + chatElements.length + ' potential chat elements by aria-label');
                    }
                    
                    chatElements.forEach((element, index) => {
                        try {
                            // Get chat name from multiple sources
                            let name = null;
                            
                            // Try aria-label first
                            const ariaLabel = element.getAttribute('aria-label');
                            if (ariaLabel) {
                                // Extract name from aria-label (usually format: "Name, unread messages" or "Name")
                                const match = ariaLabel.match(/^([^,]+)/);
                                if (match) name = match[1].trim();
                            }
                            
                            // Try title attribute
                            if (!name) {
                                const titleElement = element.querySelector('[title]');
                                if (titleElement) {
                                    name = titleElement.getAttribute('title') || titleElement.textContent.trim();
                                }
                            }
                            
                            // Try text content
                            if (!name) {
                                const textContent = element.textContent.trim();
                                if (textContent && textContent.length < 100) {
                                    name = textContent.split('\\n')[0].trim();
                                }
                            }
                            
                            // Fallback
                            if (!name || name.length === 0) {
                                name = `Chat ${index + 1}`;
                            }
                            
                            // Try to get chat ID from data attributes or aria-label
                            let chatId = null;
                            if (ariaLabel) {
                                // Extract phone number or group ID from aria-label
                                const match = ariaLabel.match(/(\\+?\\d{10,15}|\\d+@[cg]\\.us)/);
                                if (match) chatId = match[1];
                            }
                            
                            // Try data attributes
                            if (!chatId) {
                                chatId = element.getAttribute('data-id') || 
                                        element.getAttribute('data-chat-id') ||
                                        element.getAttribute('id');
                            }
                            
                            // If no ID found, generate one from name
                            if (!chatId) {
                                chatId = `chat_${index}_${name.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 50)}`;
                            }
                            
                            // Check if it's a group (look for group indicators)
                            const isGroup = element.querySelector('[data-testid="group"]') !== null ||
                                           element.querySelector('[data-testid="group-icon"]') !== null ||
                                           (ariaLabel && (ariaLabel.toLowerCase().includes('group') || 
                                                          ariaLabel.toLowerCase().includes('групп'))) ||
                                           false;
                            
                            // Get avatar if available
                            const avatarElement = element.querySelector('img[src]');
                            const avatar = avatarElement ? avatarElement.getAttribute('src') : null;
                            
                            // Try to get unread count or message info
                            let messageCount = 0;
                            const unreadElement = element.querySelector('[data-testid="icon-unread-count"]');
                            if (unreadElement) {
                                const unreadText = unreadElement.textContent.trim();
                                messageCount = parseInt(unreadText) || 0;
                            }
                            
                            // Skip if name is too generic or empty
                            if (name && name.length > 0 && name !== `Chat ${index + 1}`) {
                                chats.push({
                                    id: chatId,
                                    name: name,
                                    type: isGroup ? 'group' : 'personal',
                                    avatar: avatar,
                                    message_count: messageCount,
                                    is_group: isGroup
                                });
                            }
                        } catch (e) {
                            console.error('Error parsing chat element:', e);
                        }
                    });
                    
                    return chats;
                }
            """)
            
            logger.info(
                "Session %s found %d chats",
                session_id,
                len(chats_data) if chats_data else 0,
            )
            
            # Convert None to None (Python None) and ensure proper types
            result = []
            for chat in chats_data or []:
                result.append({
                    'id': chat.get('id', ''),
                    'name': chat.get('name', 'Unknown'),
                    'type': chat.get('type', 'personal'),
                    'avatar': chat.get('avatar') if chat.get('avatar') else None,
                    'message_count': chat.get('message_count', 0),
                    'is_group': chat.get('is_group', False),
                })
            
            return result
            
        except Exception as e:
            logger.error(
                "Session %s failed to get chats",
                session_id,
                extra={
                    "error_code": "WHATSAPP_GET_CHATS_FAIL",
                    "extra_data": {"session_id": session_id},
                },
                exc_info=True,
            )
            return []


    async def get_chat_messages(self, session_id: str, chat_id: str) -> List[Dict]:
        """
        Get messages from a specific WhatsApp chat
        
        Returns list of messages with:
        - timestamp: message timestamp (ISO format)
        - sender: sender name
        - type: message type (text, image, video, audio, voice, document, etc.)
        - text: message text
        - media_path: path to downloaded media file (if applicable)
        """
        if session_id not in self.sessions:
            logger.warning("Session %s not found for get_chat_messages", session_id)
            return []
        
        session = self.sessions[session_id]
        
        if session['status'] != 'ready':
            logger.warning(
                "Session %s not ready for get_chat_messages (status: %s)",
                session_id,
                session['status'],
            )
            return []
        
        page = session['page']
        
        try:
            logger.info(
                "Session %s starting to fetch messages for chat %s",
                session_id,
                chat_id,
            )
            
            # Find and click on the chat
            # Try to find chat by name or ID
            chat_found = False
            try:
                # Try to find chat element by clicking on it
                # First, try to find chat in the list
                chat_selectors = [
                    f'div[aria-label*="{chat_id}"]',
                    f'div[title*="{chat_id}"]',
                    f'span[title*="{chat_id}"]',
                ]
                
                for selector in chat_selectors:
                    try:
                        chat_element = await page.query_selector(selector)
                        if chat_element:
                            await chat_element.click()
                            await asyncio.sleep(2)  # Wait for chat to open
                            chat_found = True
                            logger.info("Session %s clicked on chat %s", session_id, chat_id)
                            break
                    except Exception:
                        continue
                
                if not chat_found:
                    # Try to find by index if chat_id is numeric
                    try:
                        chat_index = int(chat_id.split('_')[1]) if '_' in chat_id else None
                        if chat_index is not None:
                            all_chats = await page.query_selector_all('div[role="row"], div[aria-label*="Chat"]')
                            if chat_index < len(all_chats):
                                await all_chats[chat_index].click()
                                # Human-like delay
                                await asyncio.sleep(random.uniform(2.0, 3.0))
                                chat_found = True
                    except Exception:
                        pass
            except Exception as e:
                logger.warning("Session %s failed to open chat: %s", session_id, str(e))
            
            if not chat_found:
                logger.warning("Session %s chat %s not found", session_id, chat_id)
                return []
            
            # Wait for messages to load (human-like delay)
            await asyncio.sleep(random.uniform(3.0, 5.0))
            
            # Scroll to top to load all messages - keep scrolling until no new messages load
            # Use human-like scrolling with random delays to avoid detection
            try:
                # Find message container
                message_container = await page.query_selector('div[role="log"], div[data-testid="conversation-panel-messages"]')
                if message_container:
                    last_message_count = 0
                    scroll_attempts = 0
                    max_scroll_attempts = 100  # Increased for large chats
                    no_change_count = 0  # Track consecutive attempts with no new messages
                    
                    while scroll_attempts < max_scroll_attempts:
                        # Scroll to top with slight randomization to mimic human behavior
                        scroll_position = random.randint(-10, 10)  # Small random offset
                        await message_container.evaluate(f"element => element.scrollTop = {scroll_position}")
                        
                        # Human-like delay: 2-4 seconds between scrolls (longer than before)
                        scroll_delay = random.uniform(2.0, 4.0)
                        await asyncio.sleep(scroll_delay)
                        
                        # Count current messages (only every 3rd attempt to reduce evaluate() calls)
                        if scroll_attempts % 3 == 0:
                            current_count = await message_container.evaluate("""
                                () => {
                                    const selectors = [
                                        'div[data-testid="msg-container"]',
                                        'div[data-id]',
                                        'div[role="row"]'
                                    ];
                                    for (const sel of selectors) {
                                        const els = document.querySelectorAll(sel);
                                        if (els.length > 0) return els.length;
                                    }
                                    return 0;
                                }
                            """)
                            
                            # If no new messages loaded, increment counter
                            if current_count == last_message_count:
                                no_change_count += 1
                                # If no change for 3 consecutive checks (9 scroll attempts), we're done
                                if no_change_count >= 3 and scroll_attempts >= 9:
                                    logger.info("Session %s loaded all messages: %d total (after %d scrolls)", session_id, current_count, scroll_attempts)
                                    break
                            else:
                                no_change_count = 0  # Reset counter if we found new messages
                            
                            last_message_count = current_count
                            
                            if scroll_attempts % 15 == 0:  # Log less frequently
                                logger.info("Session %s scrolling... loaded %d messages so far (%d attempts)", session_id, current_count, scroll_attempts)
                        else:
                            # On non-counting attempts, still check if we've scrolled enough
                            if no_change_count >= 3 and scroll_attempts >= 9:
                                # Final count to confirm
                                current_count = await message_container.evaluate("""
                                    () => {
                                        const selectors = [
                                            'div[data-testid="msg-container"]',
                                            'div[data-id]',
                                            'div[role="row"]'
                                        ];
                                        for (const sel of selectors) {
                                            const els = document.querySelectorAll(sel);
                                            if (els.length > 0) return els.length;
                                        }
                                        return 0;
                                    }
                                """)
                                if current_count == last_message_count:
                                    logger.info("Session %s loaded all messages: %d total (after %d scrolls)", session_id, current_count, scroll_attempts)
                                    break
                        
                        scroll_attempts += 1
                else:
                    # Fallback: scroll page
                    await page.evaluate("window.scrollTo(0, 0)")
                    await asyncio.sleep(2)
            except Exception as e:
                logger.warning("Session %s scroll failed: %s", session_id, str(e))
            
            # Parse messages using JavaScript - improved version with full media support
            messages_data = await page.evaluate("""
                () => {
                    const messages = [];
                    const processedIds = new Set(); // Track processed messages to avoid duplicates
                    
                    // Try multiple selectors for message elements
                    const messageSelectors = [
                        'div[data-testid="msg-container"]',
                        'div[data-id]',
                        'div[role="row"]',
                        'div[data-testid="conversation-panel-messages"] > div',
                    ];
                    
                    let messageElements = [];
                    for (const selector of messageSelectors) {
                        messageElements = document.querySelectorAll(selector);
                        if (messageElements.length > 0) break;
                    }
                    
                    messageElements.forEach((element, index) => {
                        try {
                            // Skip system messages (status indicators, read receipts, etc.)
                            const isSystemMessage = element.querySelector('[data-testid="status"], [data-testid="msg-status"], [data-icon="check-dbl"], [data-icon="check"]');
                            if (isSystemMessage && !element.querySelector('[data-testid="msg-text"], span.selectable-text, img, video, audio, a[href]')) {
                                return; // Skip pure status messages
                            }
                            
                            // Get message ID to avoid duplicates
                            const msgId = element.getAttribute('data-id') || element.getAttribute('data-testid') || index.toString();
                            if (processedIds.has(msgId)) return;
                            processedIds.add(msgId);
                            
                            // Get message text - try multiple selectors
                            let text = '';
                            const textSelectors = [
                                '[data-testid="msg-text"]',
                                'span.selectable-text',
                                'span[dir="ltr"]',
                                'div[dir="ltr"]',
                                'span.copyable-text'
                            ];
                            
                            for (const selector of textSelectors) {
                                const textElement = element.querySelector(selector);
                                if (textElement) {
                                    text = textElement.textContent.trim();
                                    if (text) break;
                                }
                            }
                            
                            // Get sender name - try multiple approaches
                            let sender = 'Unknown';
                            const senderSelectors = [
                                '[data-testid="conversation-info-header"]',
                                'span[title]',
                                'div[title]',
                                '[data-testid="msg-meta"] span',
                                '.message-author'
                            ];
                            
                            for (const selector of senderSelectors) {
                                const senderElement = element.querySelector(selector);
                                if (senderElement) {
                                    sender = senderElement.getAttribute('title') || senderElement.textContent.trim();
                                    if (sender && sender !== 'Unknown') break;
                                }
                            }
                            
                            // Detect message type and media
                            let msgType = 'text';
                            let mediaPath = null;
                            
                            // Check for images (including stickers and GIFs)
                            const imgElement = element.querySelector('img[src]');
                            if (imgElement) {
                                const imgSrc = imgElement.getAttribute('src');
                                if (imgSrc && !imgSrc.includes('data:image/svg+xml')) { // Skip SVG icons
                                    msgType = 'image';
                                    mediaPath = imgSrc;
                                    
                                    // Check if it's a sticker or GIF
                                    const parentClasses = element.className || '';
                                    if (parentClasses.includes('sticker') || imgSrc.includes('sticker')) {
                                        msgType = 'sticker';
                                    } else if (imgSrc.includes('gif') || parentClasses.includes('gif')) {
                                        msgType = 'gif';
                                    }
                                }
                            }
                            
                            // Check for videos
                            if (msgType === 'text') {
                                const videoElement = element.querySelector('video[src], video source[src]');
                                if (videoElement) {
                                    msgType = 'video';
                                    mediaPath = videoElement.getAttribute('src') || videoElement.querySelector('source')?.getAttribute('src');
                                }
                            }
                            
                            // Check for audio/voice messages
                            if (msgType === 'text') {
                                const audioElement = element.querySelector('audio[src], audio source[src]');
                                if (audioElement) {
                                    const audioSrc = audioElement.getAttribute('src') || audioElement.querySelector('source')?.getAttribute('src');
                                    // Check if it's a voice note (PTT)
                                    const isVoiceNote = element.querySelector('[data-testid="ptt"], [data-icon="mic"]');
                                    msgType = isVoiceNote ? 'voice' : 'audio';
                                    mediaPath = audioSrc;
                                }
                            }
                            
                            // Check for documents/files
                            if (msgType === 'text') {
                                const docElement = element.querySelector('[data-testid="media-document"], a[href*="blob"], a[download]');
                                if (docElement) {
                                    msgType = 'document';
                                    mediaPath = docElement.getAttribute('href') || docElement.getAttribute('src');
                                }
                            }
                            
                            // Check for links (if no other media found)
                            if (msgType === 'text') {
                                const linkElement = element.querySelector('a[href^="http"], a[href^="https"]');
                                if (linkElement && !text.includes(linkElement.href)) {
                                    const linkUrl = linkElement.getAttribute('href');
                                    if (linkUrl && (linkUrl.startsWith('http://') || linkUrl.startsWith('https://'))) {
                                        text = text ? text + ' ' + linkUrl : linkUrl;
                                    }
                                }
                            }
                            
                            // Get timestamp
                            let timestamp = new Date().toISOString();
                            const timeSelectors = [
                                'span[title]',
                                'div[title]',
                                '[data-testid="msg-meta"] span',
                                '.message-time'
                            ];
                            
                            for (const selector of timeSelectors) {
                                const timeElement = element.querySelector(selector);
                                if (timeElement) {
                                    const timeTitle = timeElement.getAttribute('title');
                                    if (timeTitle) {
                                        try {
                                            const date = new Date(timeTitle);
                                            if (!isNaN(date.getTime())) {
                                                timestamp = date.toISOString();
                                                break;
                                            }
                                        } catch (e) {
                                            // Try parsing text content
                                            const timeText = timeElement.textContent.trim();
                                            if (timeText) {
                                                try {
                                                    const date = new Date(timeText);
                                                    if (!isNaN(date.getTime())) {
                                                        timestamp = date.toISOString();
                                                        break;
                                                    }
                                                } catch (e2) {}
                                            }
                                        }
                                    }
                                }
                            }
                            
                            // Only add message if it has meaningful content
                            // Skip empty messages, pure status indicators, and system messages
                            const hasContent = text || (msgType !== 'text' && mediaPath);
                            const isStatusOnly = element.querySelector('[data-icon="check"], [data-icon="check-dbl"]') && !hasContent;
                            
                            if (hasContent && !isStatusOnly) {
                                messages.push({
                                    timestamp: timestamp,
                                    sender: sender,
                                    type: msgType,
                                    text: text,
                                    media_path: mediaPath,
                                    is_album: false,
                                    album_group_id: null
                                });
                            }
                        } catch (e) {
                            console.error('Error parsing message:', e);
                        }
                    });
                    
                    return messages;
                }
            """)
            
            # Count message types for logging
            message_types = {}
            for msg in messages_data or []:
                msg_type = msg.get('type', 'text')
                message_types[msg_type] = message_types.get(msg_type, 0) + 1
            
            logger.info(
                "Session %s found %d messages for chat %s",
                session_id,
                len(messages_data) if messages_data else 0,
                chat_id,
                extra={
                    "error_code": None,
                    "extra_data": {
                        "session_id": session_id,
                        "chat_id": chat_id,
                        "total_messages": len(messages_data) if messages_data else 0,
                        "message_types": message_types,
                    },
                },
            )
            
            # Convert to proper format and filter out invalid messages
            result = []
            for msg in messages_data or []:
                msg_type = msg.get('type', 'text')
                text = msg.get('text', '')
                media_path = msg.get('media_path')
                
                # Skip messages without content
                if not text and (msg_type == 'text' or not media_path):
                    continue
                
                result.append({
                    'timestamp': msg.get('timestamp', datetime.utcnow().isoformat()),
                    'sender': msg.get('sender', 'Unknown'),
                    'type': msg_type,
                    'text': text,
                    'media_path': media_path,
                    'is_album': msg.get('is_album', False),
                    'album_group_id': msg.get('album_group_id'),
                })
            
            logger.info(
                "Session %s processed %d valid messages (filtered from %d)",
                session_id,
                len(result),
                len(messages_data) if messages_data else 0,
                extra={
                    "error_code": None,
                    "extra_data": {
                        "session_id": session_id,
                        "chat_id": chat_id,
                        "valid_messages": len(result),
                        "raw_messages": len(messages_data) if messages_data else 0,
                    },
                },
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Session %s failed to get messages",
                session_id,
                extra={
                    "error_code": "WHATSAPP_GET_MESSAGES_FAIL",
                    "extra_data": {"session_id": session_id, "chat_id": chat_id},
                },
                exc_info=True,
            )
            return []


# Global service instance
whatsapp_service = WhatsAppConnectService()
