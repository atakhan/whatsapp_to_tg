"""
Connection management for WhatsApp Web (QR codes, connection monitoring)
"""
import asyncio
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from playwright.async_api import Page, TimeoutError, ElementHandle

from app.core.config import settings
from app.core.logging_setup import (
    set_correlation_ids,
    set_request_context,
    trace_id_ctx,
    request_id_ctx,
)
from app.services.whatsapp.session_manager import SessionManager
from app.services.whatsapp.browser_manager import BrowserManager

logger = logging.getLogger(__name__)

QR_WAIT_TIMEOUT_MS = 30000  # Allow slower networks to fetch QR


class ConnectionManager:
    """Manages WhatsApp Web connections, QR codes, and connection monitoring"""
    
    def __init__(self, session_manager: SessionManager, browser_manager: BrowserManager):
        self.session_manager = session_manager
        self.browser_manager = browser_manager
    
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
        await self.browser_manager.initialize()
        logger.info("Start connection for session %s", session_id)
        
        # Check if session already exists and is ready
        if self.session_manager.is_session_ready(session_id):
            logger.info("Session %s already connected, returning status", session_id)
            status = await self.get_status(session_id)
            return {
                "session_id": session_id,
                "qr_code": "",
                "status": "ready",
                "expires_at": ""
            }
        
        # Create session directory
        session_path = self.session_manager.get_session_path(session_id)
        session_path.mkdir(parents=True, exist_ok=True)
        
        # Create browser context with persistent storage
        user_data_dir = str(session_path / "browser_data")
        context = None
        qr_selector = 'div[data-ref] canvas, div[data-ref] img'
        
        try:
            context = await self.browser_manager.create_persistent_context(user_data_dir)
            page = await self.browser_manager.create_page(context)
            
            # Navigate to WhatsApp Web
            target_url = 'https://web.whatsapp.com'
            logger.info("Session %s navigating to %s ...", session_id, target_url)
            await page.goto(target_url, wait_until='networkidle')
            logger.info("Session %s page loaded, current url=%s", session_id, page.url)
            
            # Wait for page to fully render
            await asyncio.sleep(10)
            
            # Wait for canvas elements to appear
            try:
                await page.wait_for_selector('canvas', timeout=15000)
                logger.info("Session %s canvas elements appeared on page", session_id)
            except Exception:
                logger.warning("Session %s no canvas elements found after wait", session_id)
            
            # Check page title and basic structure
            title = await page.title()
            logger.info("Session %s page title: %s", session_id, title)
            
            # Check if page has loaded properly
            try:
                await page.wait_for_selector('div#app', timeout=10000)
                logger.info("Session %s WhatsApp app container found", session_id)
                
                # Diagnostic: check what elements are present
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
            
            # Find QR code
            qr_element, used_selector = await self._find_qr_code(page, session_id, qr_selector)
            
            if not qr_element:
                raise Exception("QR code element not found")
            
            # Get QR code as base64
            qr_screenshot = await qr_element.screenshot(type='png')
            qr_base64 = base64.b64encode(qr_screenshot).decode('utf-8')
            logger.info(
                "Session %s QR captured (%d bytes base64) using selector: %s",
                session_id,
                len(qr_base64),
                used_selector or qr_selector,
            )
            
            # Calculate expiry
            expires_at = datetime.utcnow() + timedelta(seconds=settings.WHATSAPP_QR_REFRESH_SEC)
            
            # Store session info
            self.session_manager.set_session(session_id, {
                'context': context,
                'page': page,
                'status': 'waiting_qr',
                'expires_at': expires_at.isoformat(),
                'created_at': datetime.utcnow().isoformat()
            })
            
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
    
    async def _find_qr_code(self, page: Page, session_id: str, qr_selector: str) -> Tuple[Optional[ElementHandle], Optional[str]]:
        """Find QR code element on page using multiple strategies"""
        qr_element = None
        used_selector = None
        
        # Strategy 1: Find QR by canvas size (QR codes are usually square, 200-400px)
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
                        ratio = width / height if height > 0 else 0
                        is_square = 0.8 <= ratio <= 1.2
                        is_qr_size = 150 <= width <= 500 and 150 <= height <= 500
                        
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
        
        # Strategy 2: Try multiple QR selectors
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
                        box = await qr_element.bounding_box()
                        if box and box['width'] > 0 and box['height'] > 0:
                            logger.info("Session %s found QR with selector: %s (size: %dx%d)", 
                                      session_id, selector, int(box['width']), int(box['height']))
                            used_selector = selector
                            break
                except Exception as e:
                    logger.debug("Session %s selector %s failed: %s", session_id, selector, str(e))
                    continue
        
        # Strategy 3: Fallback to original combined selector
        if not qr_element:
            logger.info("Session %s trying original combined selector as fallback (timeout=%dms)", 
                      session_id, QR_WAIT_TIMEOUT_MS)
            try:
                await page.wait_for_selector(qr_selector, timeout=QR_WAIT_TIMEOUT_MS)
                qr_element = await page.query_selector(qr_selector)
                used_selector = qr_selector
                logger.info("Session %s found QR with fallback selector", session_id)
            except TimeoutError:
                # Take screenshot and log for debugging
                try:
                    screenshot = await page.screenshot(type='png', full_page=True)
                    screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
                    
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
        
        return qr_element, used_selector
    
    async def _monitor_connection(self, session_id: str):
        """Monitor WhatsApp Web connection status in background"""
        # Ensure correlation ids exist in background task
        set_correlation_ids(trace_id_ctx.get(), request_id_ctx.get())
        set_request_context()

        session = self.session_manager.get_session(session_id)
        if not session:
            logger.warning("Session %s not found for monitoring", session_id)
            return
        
        page = session['page']
        
        logger.info(
            "Session %s starting connection monitoring (timeout=%ds)",
            session_id,
            settings.WHATSAPP_CONNECT_TIMEOUT_SEC,
        )
        
        try:
            connected_selectors = [
                'div[data-testid="chatlist"]',
                'div[data-testid="conversation-header"]',
                'div#app > div > div > div[role="application"]',
                'div[data-testid="intro-md-beta-logo"]',
                'div[aria-label*="Chat"]',
                'div[data-testid="chat"]',
                'nav[aria-label*="Chat"]',
            ]
            
            timeout_seconds = settings.WHATSAPP_CONNECT_TIMEOUT_SEC
            start_time = datetime.utcnow()
            
            while True:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= timeout_seconds:
                    expires_at = datetime.fromisoformat(session['expires_at'])
                    if datetime.utcnow() > expires_at:
                        session['status'] = 'expired'
                        self.session_manager.set_session(session_id, session)  # Update session
                        logger.warning(
                            "Session %s QR expired during monitor",
                            session_id,
                            extra={
                                "error_code": "WHATSAPP_QR_EXPIRED",
                                "extra_data": {"elapsed_sec": elapsed, "timeout_sec": timeout_seconds},
                            },
                        )
                    break
                
                # Check if QR disappeared
                try:
                    qr_selector = 'div[data-ref] canvas, div[data-ref] img'
                    qr_element = await page.query_selector(qr_selector)
                    if not qr_element:
                        logger.info("Session %s QR code disappeared, checking for connection...", session_id)
                except:
                    pass
                
                # Check each selector for connection indicators
                for selector in connected_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            box = await element.bounding_box()
                            if box and box['width'] > 0 and box['height'] > 0:
                                logger.info(
                                    "Session %s connection successful! Found selector: %s",
                                    session_id,
                                    selector,
                                )
                                session['status'] = 'ready'
                                session['connected_at'] = datetime.utcnow().isoformat()
                                self.session_manager.set_session(session_id, session)  # Update session
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
                
                await asyncio.sleep(2)
            
        except Exception as e:
            session['status'] = 'failed'
            session['error'] = str(e)
            self.session_manager.set_session(session_id, session)  # Update session
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
        session = self.session_manager.get_session(session_id)
        if not session:
            return {
                "session_id": session_id,
                "status": "not_found"
            }
        
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
                        self.session_manager.set_session(session_id, session)  # Update session
                        result['qr_code'] = qr_base64
                        result['expires_at'] = new_expires.isoformat()
                    else:
                        session['status'] = 'expired'
                        self.session_manager.set_session(session_id, session)  # Update session
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
                    self.session_manager.set_session(session_id, session)  # Update session
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
    
    async def _check_connection_status(self, page: Page) -> bool:
        """Check if WhatsApp is connected by looking for chat list elements"""
        connected_selectors = [
            'div[data-testid="chatlist"]',
            'div[role="listbox"]',
            'div[data-testid="chat"]',
            'div[aria-label*="Chat"]',
        ]
        
        for selector in connected_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    box = await element.bounding_box()
                    if box and box['width'] > 0 and box['height'] > 0:
                        return True
            except Exception:
                continue
        
        return False
