"""
CDP Network chat source - extracts chats from network payloads via CDP.
"""

from typing import Any, Dict, List, Optional
import logging
import json
import asyncio

from playwright.async_api import Page, CDPSession

from .base import IChatSource, SourceUnavailableError
from ..models.raw_chat import RawChat

logger = logging.getLogger(__name__)


class CDPNetworkChatSource(IChatSource):
    """
    Extracts chats by intercepting network requests via Chrome DevTools Protocol.
    
    This source:
    - Intercepts WhatsApp Web API calls
    - Parses protobuf/JSON payloads
    - Provides reliable IDs from network data
    
    Note: WhatsApp Web uses protobuf for most API calls, but some endpoints
    may return JSON. We'll try to parse both formats.
    """
    
    def __init__(self, page: Page):
        self.page = page
        self.cdp_session: Optional[CDPSession] = None
        self._initialized = False
        self._collected_payloads: List[Dict[str, Any]] = []
        self._collected_chats: Dict[str, RawChat] = {}  # Keyed by chat ID
        self._total_count: Optional[int] = None
        self._response_listener_task: Optional[asyncio.Task] = None
        self._collection_timeout = 30.0  # Wait up to 30 seconds for responses
    
    @property
    def source_name(self) -> str:
        return "network"
    
    async def init(self) -> None:
        """Initialize CDP session and enable network interception."""
        try:
            # Create CDP session
            self.cdp_session = await self.page.context.new_cdp_session(self.page)
            
            # Enable Network domain
            await self.cdp_session.send('Network.enable')
            
            # Set up response listener
            self._setup_response_listener()
            
            # Try to trigger chat loading by clicking on chat list or scrolling
            # This helps ensure WhatsApp Web loads chats via network
            try:
                # Wait a bit for page to be ready
                await asyncio.sleep(0.5)
                
                # Try to find and click on chat list to trigger loading
                chat_list_selectors = [
                    'div[data-testid="chat-list"]',
                    'div[role="application"] > div > div',
                    'div[aria-label*="Chat"]',
                    '#pane-side'  # WhatsApp Web chat list container
                ]
                
                for selector in chat_list_selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            # Scroll to trigger loading
                            await element.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            logger.debug("Triggered chat loading via selector: %s", selector)
                            break
                    except Exception:
                        continue
                        
            except Exception as e:
                logger.debug("Could not trigger chat loading: %s", str(e))
                # Not critical, continue anyway
            
            self._initialized = True
            logger.info("CDP Network source initialized, listening for network responses")
            
        except Exception as e:
            logger.error("Failed to initialize CDP Network source: %s", str(e), exc_info=True)
            raise SourceUnavailableError(f"Failed to initialize CDP Network: {str(e)}")
    
    def _setup_response_listener(self):
        """Set up listener for network responses."""
        async def handle_response(event: Dict[str, Any]):
            """Handle network response events."""
            try:
                response = event.get('response', {})
                request = event.get('request', {})
                url = response.get('url', '')
                request_id = event.get('requestId')
                
                # Filter for WhatsApp Web API endpoints
                # WhatsApp Web uses various endpoints, we'll look for chat-related ones
                if not any(keyword in url.lower() for keyword in ['chat', 'conversation', 'whatsapp', 'web.whatsapp.com']):
                    return
                
                # Skip non-API requests
                if not url.startswith('https://') or 'web.whatsapp.com' not in url:
                    return
                
                logger.debug("Intercepted network response: %s", url[:100])
                
                # Try to get response body
                try:
                    body = await self.cdp_session.send('Network.getResponseBody', {
                        'requestId': request_id
                    })
                    
                    body_text = body.get('body', '')
                    if body.get('base64Encoded'):
                        import base64
                        body_text = base64.b64decode(body_text).decode('utf-8', errors='ignore')
                    
                    # Try to parse as JSON first
                    try:
                        data = json.loads(body_text)
                        self._parse_json_payload(data, url)
                    except json.JSONDecodeError:
                        # Might be protobuf or other format
                        logger.debug("Response is not JSON, might be protobuf: %s", url[:100])
                        # TODO: Add protobuf parsing if needed
                        
                except Exception as e:
                    logger.debug("Failed to get response body for %s: %s", url[:100], str(e))
                    
            except Exception as e:
                logger.warning("Error handling network response: %s", str(e))
        
        # Subscribe to Network.responseReceived events
        self.cdp_session.on('Network.responseReceived', handle_response)
    
    def _parse_json_payload(self, data: Dict[str, Any], url: str):
        """Parse JSON payload and extract chat information."""
        try:
            # WhatsApp Web API structure varies, try common patterns
            chats = []
            
            # Pattern 1: Direct array of chats
            if isinstance(data, list):
                chats = data
            # Pattern 2: Nested structure with chats array
            elif isinstance(data, dict):
                # Try common keys
                if 'chats' in data:
                    chats = data['chats'] if isinstance(data['chats'], list) else []
                elif 'conversations' in data:
                    chats = data['conversations'] if isinstance(data['conversations'], list) else []
                elif 'data' in data and isinstance(data['data'], list):
                    chats = data['data']
                # Check for total count
                if 'total' in data:
                    self._total_count = data['total']
                elif 'count' in data:
                    self._total_count = data['count']
            
            # Parse each chat
            for chat_data in chats:
                if not isinstance(chat_data, dict):
                    continue
                
                # Extract chat ID - try multiple fields
                chat_id = None
                if 'id' in chat_data:
                    id_val = chat_data['id']
                    if isinstance(id_val, dict):
                        chat_id = id_val.get('_serialized') or id_val.get('user') or str(id_val)
                    else:
                        chat_id = str(id_val)
                elif 'jid' in chat_data:
                    chat_id = str(chat_data['jid'])
                elif 'wid' in chat_data:
                    chat_id = str(chat_data['wid'])
                
                if not chat_id:
                    continue
                
                # Extract other fields
                name = chat_data.get('name') or chat_data.get('contact', {}).get('name')
                is_group = chat_data.get('isGroup') or chat_data.get('isGroupChat') or False
                unread_count = chat_data.get('unreadCount') or chat_data.get('unread') or 0
                avatar_url = chat_data.get('avatar') or chat_data.get('profilePicUrl')
                
                # Create or update RawChat
                raw_chat = RawChat(
                    source="network",
                    jid=chat_id if '@' in chat_id else None,
                    wid=chat_data.get('wid'),
                    server_id=chat_data.get('id', {}).get('server_id') if isinstance(chat_data.get('id'), dict) else None,
                    user_id=chat_data.get('id', {}).get('user') if isinstance(chat_data.get('id'), dict) else None,
                    name=name,
                    is_group=is_group,
                    unread_count=unread_count,
                    avatar_url=avatar_url,
                    raw_data={'url': url, 'source': 'network_response'}
                )
                
                # Store by ID (will deduplicate)
                self._collected_chats[chat_id] = raw_chat
                
        except Exception as e:
            logger.debug("Error parsing JSON payload from %s: %s", url[:100], str(e))
    
    async def fetch_batch(self) -> List[RawChat]:
        """Fetch chats from collected network payloads."""
        if not self._initialized:
            await self.init()
        
        # Wait longer for network responses to arrive
        # WhatsApp Web might need time to load chats
        if not self._collected_chats:
            logger.info("No chats collected yet, waiting for network responses...")
            # Wait up to 5 seconds with periodic checks
            for i in range(5):
                await asyncio.sleep(1.0)
                if self._collected_chats:
                    logger.info("Chats collected after %.1fs", i + 1.0)
                    break
        
        # Return collected chats
        chats = list(self._collected_chats.values())
        logger.info("Fetched %d chats from CDP Network", len(chats))
        return chats
    
    async def is_complete(self) -> bool:
        """Check if all chats have been collected from network."""
        # If we have a total count and collected that many, we're complete
        if self._total_count and len(self._collected_chats) >= self._total_count:
            return True
        
        # Otherwise, we can't be sure - network responses are asynchronous
        # In practice, we might need to wait for a specific signal or timeout
        return False
    
    async def total_expected(self) -> Optional[int]:
        """Return total count from network payloads if available."""
        return self._total_count
    
    async def cleanup(self):
        """Clean up CDP session."""
        if self.cdp_session:
            try:
                # Remove listeners
                # Note: Playwright CDP doesn't have explicit unsubscribe,
                # but detaching the session should clean up
                await self.cdp_session.detach()
            except Exception as e:
                logger.warning("Failed to detach CDP session: %s", str(e))
            self.cdp_session = None

