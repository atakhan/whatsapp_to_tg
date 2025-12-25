"""
Store chat source - extracts chats from WhatsApp Web internal store.
"""

from typing import List, Optional
import logging

from playwright.async_api import Page

from .base import IChatSource, SourceUnavailableError
from ..models.raw_chat import RawChat

logger = logging.getLogger(__name__)


class StoreChatSource(IChatSource):
    """
    Extracts chats from window.Store in WhatsApp Web.
    
    This is the preferred source as it provides:
    - All chats at once (no scrolling needed)
    - Reliable IDs (jid, wid)
    - Total count information
    - Complete chat metadata
    """
    
    def __init__(self, page: Page):
        self.page = page
        self._initialized = False
        self._total_count: Optional[int] = None
        self._store_available = False
    
    @property
    def source_name(self) -> str:
        return "store"
    
    async def init(self) -> None:
        """Check if Store is available and get total count."""
        import asyncio
        
        # Try multiple times with delays - Store might not be initialized immediately
        max_attempts = 5
        delay = 1.0
        
        for attempt in range(max_attempts):
            try:
                # Check if window.Store exists
                store_info = await self.page.evaluate("""
                    () => {
                        // Try multiple possible Store locations
                        const store = window.Store || window.WWebJS || window.webpackChunkwhatsapp_web_client;
                        if (!store) {
                            return { available: false, reason: 'Store not found' };
                        }
                        
                        // Try to access Chat models
                        let chatModels = null;
                        if (store.Chat && store.Chat.models) {
                            chatModels = store.Chat.models;
                        } else if (store.chats) {
                            chatModels = store.chats;
                        } else if (store.Chat) {
                            chatModels = store.Chat;
                        }
                        
                        if (!chatModels) {
                            return { 
                                available: false, 
                                reason: 'Chat models not found',
                                storeKeys: Object.keys(store).slice(0, 20) // For debugging
                            };
                        }
                        
                        // Get count
                        let totalCount = 0;
                        if (Array.isArray(chatModels)) {
                            totalCount = chatModels.length;
                        } else if (chatModels instanceof Map || chatModels instanceof Set) {
                            totalCount = chatModels.size;
                        } else if (typeof chatModels === 'object') {
                            totalCount = Object.keys(chatModels).length;
                        }
                        
                        return {
                            available: true,
                            totalCount: totalCount,
                            storeKeys: Object.keys(store).slice(0, 10) // First 10 keys for debugging
                        };
                    }
                """)
                
                if store_info.get('available'):
                    self._total_count = store_info.get('totalCount', 0)
                    self._store_available = True
                    self._initialized = True
                    
                    logger.info(
                        "Store source initialized: total_count=%d (attempt %d/%d)",
                        self._total_count,
                        attempt + 1,
                        max_attempts
                    )
                    return
                
                # If not available and not last attempt, wait and retry
                if attempt < max_attempts - 1:
                    reason = store_info.get('reason', 'Unknown')
                    logger.debug(
                        "Store not available yet: %s (attempt %d/%d, retrying in %.1fs)",
                        reason,
                        attempt + 1,
                        max_attempts,
                        delay
                    )
                    await asyncio.sleep(delay)
                    delay *= 1.5  # Exponential backoff
                else:
                    # Last attempt failed
                    reason = store_info.get('reason', 'Unknown')
                    store_keys = store_info.get('storeKeys', [])
                    logger.warning(
                        "Store source unavailable after %d attempts: %s (store keys: %s)",
                        max_attempts,
                        reason,
                        store_keys
                    )
                    raise SourceUnavailableError(f"Store not available: {reason}")
                    
            except SourceUnavailableError:
                raise
            except Exception as e:
                if attempt < max_attempts - 1:
                    logger.debug(
                        "Store init attempt %d/%d failed: %s (retrying)",
                        attempt + 1,
                        max_attempts,
                        str(e)
                    )
                    await asyncio.sleep(delay)
                    delay *= 1.5
                else:
                    logger.error("Failed to initialize Store source after %d attempts: %s", max_attempts, str(e), exc_info=True)
                    raise SourceUnavailableError(f"Failed to initialize Store: {str(e)}")
    
    async def fetch_batch(self) -> List[RawChat]:
        """Fetch all chats from Store."""
        if not self._initialized:
            await self.init()
        
        if not self._store_available:
            return []
        
        try:
            raw_chats_data = await self.page.evaluate("""
                () => {
                    const store = window.Store || window.WWebJS;
                    if (!store) {
                        console.warn('[StoreChatSource] Store not found');
                        return [];
                    }
                    
                    // Try multiple ways to access Chat models
                    let chatModels = null;
                    
                    // Method 1: store.Chat.models (most common)
                    if (store.Chat && store.Chat.models) {
                        chatModels = store.Chat.models;
                    }
                    // Method 2: store.chats
                    else if (store.chats) {
                        chatModels = store.chats;
                    }
                    // Method 3: store.Chat (direct)
                    else if (store.Chat) {
                        chatModels = store.Chat;
                    }
                    
                    if (!chatModels) {
                        console.warn('[StoreChatSource] Chat models not found. Store keys:', Object.keys(store).slice(0, 20));
                        return [];
                    }
                    
                    // Convert to array if it's a Map, Set, or object
                    let chats = [];
                    if (Array.isArray(chatModels)) {
                        chats = chatModels;
                    } else if (chatModels instanceof Map) {
                        chats = Array.from(chatModels.values());
                    } else if (chatModels instanceof Set) {
                        chats = Array.from(chatModels);
                    } else if (typeof chatModels === 'object') {
                        // Try to get values if it's an object with values() method
                        if (typeof chatModels.values === 'function') {
                            chats = Array.from(chatModels.values());
                        } else {
                            // Fallback: iterate over object keys
                            chats = Object.values(chatModels);
                        }
                    }
                    
                    return chats.map((chat, index) => {
                        try {
                            // Extract JID - try different possible structures
                            let jid = null;
                            if (chat.id) {
                                // Most common: chat.id._serialized
                                if (chat.id._serialized) {
                                    jid = chat.id._serialized;
                                }
                                // Alternative: chat.id.user (for personal chats)
                                else if (chat.id.user) {
                                    jid = chat.id.user;
                                }
                                // Alternative: chat.id (if it's already a string)
                                else if (typeof chat.id === 'string') {
                                    jid = chat.id;
                                }
                                // Last resort: try to stringify
                                else {
                                    jid = String(chat.id);
                                }
                            }
                            
                            // Extract wid (alternative ID format)
                            let wid = null;
                            if (chat.wid) {
                                wid = typeof chat.wid === 'string' ? chat.wid : chat.wid._serialized || String(chat.wid);
                            }
                            
                            // Extract name - try multiple sources
                            let name = null;
                            if (chat.name) {
                                name = chat.name;
                            } else if (chat.contact && chat.contact.name) {
                                name = chat.contact.name;
                            } else if (chat.pushName) {
                                name = chat.pushName;
                            } else if (chat.formattedTitle) {
                                name = chat.formattedTitle;
                            }
                            
                            // Determine if group
                            const isGroup = chat.isGroup === true || 
                                          chat.isGroupChat === true ||
                                          (jid && jid.endsWith('@g.us')) ||
                                          false;
                            
                            // Extract unread count
                            const unreadCount = chat.unreadCount || 
                                             chat.unread || 
                                             (chat.msgs && chat.msgs.unreadCount) ||
                                             0;
                            
                            // Extract avatar URL
                            let avatarUrl = null;
                            if (chat.avatar) {
                                avatarUrl = typeof chat.avatar === 'string' ? chat.avatar : chat.avatar.url;
                            } else if (chat.profilePicUrl) {
                                avatarUrl = chat.profilePicUrl;
                            } else if (chat.pic) {
                                avatarUrl = typeof chat.pic === 'string' ? chat.pic : chat.pic.url;
                            }
                            
                            return {
                                jid: jid,
                                wid: wid,
                                name: name,
                                isGroup: isGroup,
                                unreadCount: unreadCount,
                                avatarUrl: avatarUrl,
                                rawData: {
                                    // Store diagnostic info
                                    hasId: !!chat.id,
                                    hasContact: !!chat.contact,
                                    hasName: !!chat.name,
                                    idType: chat.id ? typeof chat.id : null,
                                    chatIndex: index,
                                }
                            };
                        } catch (e) {
                            console.error('[StoreChatSource] Error parsing chat at index', index, ':', e);
                            return null;
                        }
                    }).filter(chat => chat !== null); // Remove failed parses
                }
            """)
            
            raw_chats = []
            for chat_data in raw_chats_data:
                if not chat_data:  # Skip null entries
                    continue
                    
                raw_chat = RawChat(
                    source="store",
                    jid=chat_data.get('jid'),
                    wid=chat_data.get('wid'),
                    name=chat_data.get('name'),
                    is_group=chat_data.get('isGroup', False),
                    unread_count=chat_data.get('unreadCount', 0),
                    avatar_url=chat_data.get('avatarUrl'),
                    raw_data=chat_data.get('rawData', {})
                )
                raw_chats.append(raw_chat)
            
            logger.info("Fetched %d chats from Store", len(raw_chats))
            
            # Log diagnostic info if we got fewer chats than expected
            if self._total_count and len(raw_chats) < self._total_count:
                logger.warning(
                    "Fetched %d chats but expected %d from Store",
                    len(raw_chats), self._total_count
                )
            
            return raw_chats
            
        except Exception as e:
            logger.error("Failed to fetch chats from Store: %s", str(e), exc_info=True)
            return []
    
    async def is_complete(self) -> bool:
        """Store provides all chats at once, so always complete after first fetch."""
        return True
    
    async def total_expected(self) -> Optional[int]:
        """Return total count from Store."""
        return self._total_count

