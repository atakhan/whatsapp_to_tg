"""
DOM chat source - extracts chats from DOM (fallback).
"""

from typing import List, Optional
import logging
import asyncio
import random

from playwright.async_api import Page

from .base import IChatSource, SourceUnavailableError
from ..models.raw_chat import RawChat

logger = logging.getLogger(__name__)


class DOMChatSource(IChatSource):
    """
    Extracts chats from DOM elements (fallback source).
    
    This is the least reliable source and should only be used
    when Store and CDP Network are unavailable.
    
    Note: ID extraction from DOM is less reliable (may use fallback IDs).
    All chats from this source will have integrity="fallback".
    """
    
    def __init__(self, page: Page):
        self.page = page
        self._initialized = False
        self._seen_ids: set = set()
        self._scroll_iterations = 0
        self._no_new_chats_count = 0
        self._reached_bottom = False
    
    @property
    def source_name(self) -> str:
        return "dom"
    
    async def init(self) -> None:
        """Initialize DOM parsing - wait for page to load."""
        try:
            # Wait for chat list container
            chatlist_selectors = [
                'div[data-testid="chatlist"]',
                'div[role="listbox"]',
                'div[aria-label*="Chat"]',
            ]
            
            found = False
            for selector in chatlist_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    logger.info("DOM source: found chat list with selector: %s", selector)
                    found = True
                    break
                except Exception:
                    continue
            
            if not found:
                logger.warning("DOM source: chat list container not found, will try to parse anyway")
            
            # Scroll to top to start from beginning
            # Also try to scroll the chat list container
            await self.page.evaluate("""
                () => {
                    window.scrollTo(0, 0);
                    // Also try to scroll chat list containers
                    const containers = [
                        document.querySelector('div[data-testid="chatlist"]'),
                        document.querySelector('div[role="listbox"]'),
                        document.querySelector('#pane-side')
                    ];
                    containers.forEach(container => {
                        if (container) {
                            container.scrollTop = 0;
                        }
                    });
                }
            """)
            await asyncio.sleep(0.5)
            
            self._initialized = True
            
        except Exception as e:
            logger.error("Failed to initialize DOM source: %s", str(e), exc_info=True)
            raise SourceUnavailableError(f"Failed to initialize DOM: {str(e)}")
    
    async def fetch_batch(self) -> List[RawChat]:
        """Fetch visible chats from DOM, scrolling to load more if needed."""
        if not self._initialized:
            await self.init()
        
        # Scroll to load more chats before parsing
        # This is important for virtual scrolling in WhatsApp Web
        # Scroll multiple times to ensure we load all chats
        if not self._reached_bottom and self._no_new_chats_count < 10:
            # Scroll multiple times to load more content
            # For virtual scrolling, we need to scroll gradually to trigger loading
            scroll_count = 0
            for scroll_attempt in range(5):  # Try up to 5 scrolls per batch
                scrolled = await self.scroll_for_more()
                if scrolled:
                    scroll_count += 1
                    # Wait for new chats to render after each scroll
                    # Increase wait time for virtual scrolling to load content
                    await asyncio.sleep(1.5)  # Increased wait time for virtual scrolling
                else:
                    # Can't scroll more, but don't break immediately - might need to wait
                    if self._reached_bottom:
                        logger.info("DOM source: reached bottom after %d scrolls", scroll_count)
                        break
                    # If not at bottom but can't scroll, wait a bit and try again
                    await asyncio.sleep(0.5)
            
            if scroll_count > 0:
                logger.info("DOM source: performed %d scrolls before parsing batch", scroll_count)
        
        try:
            chats_data = await self.page.evaluate("""
                () => {
                    const chats = [];
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
                    let bestSelector = null;
                    let maxElements = 0;
                    
                    // Try all selectors and use the one that finds the most elements
                    for (const selector of chatSelectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > maxElements) {
                            maxElements = elements.length;
                            chatElements = Array.from(elements);
                            bestSelector = selector;
                        }
                    }
                    
                    // If still no elements, try more aggressive search
                    if (chatElements.length === 0) {
                        const allDivs = document.querySelectorAll('div[role="row"], div[aria-label]');
                        chatElements = Array.from(allDivs).filter(div => {
                            const ariaLabel = div.getAttribute('aria-label') || '';
                            return ariaLabel.includes('Chat') || ariaLabel.includes('чат') || 
                                   ariaLabel.includes('group') || ariaLabel.includes('групп');
                        });
                    }
                    
                    // Additional fallback: look for any div with clickable chat-like structure
                    if (chatElements.length === 0) {
                        const chatListContainer = document.querySelector('div[data-testid="chatlist"]') || 
                                                 document.querySelector('div[role="listbox"]');
                        if (chatListContainer) {
                            chatElements = Array.from(chatListContainer.querySelectorAll('div[role="row"], div > div'));
                        }
                    }
                    
                    // Parse all elements in DOM
                    chatElements.forEach((element, index) => {
                        try {
                            let name = null;
                            const ariaLabel = element.getAttribute('aria-label');
                            if (ariaLabel) {
                                const match = ariaLabel.match(/^([^,]+)/);
                                if (match) name = match[1].trim();
                            }
                            
                            if (!name) {
                                const titleElement = element.querySelector('[title]');
                                if (titleElement) {
                                    name = titleElement.getAttribute('title') || titleElement.textContent.trim();
                                }
                            }
                            
                            if (!name) {
                                const textContent = element.textContent.trim();
                                if (textContent && textContent.length < 100) {
                                    name = textContent.split('\\n')[0].trim();
                                }
                            }
                            
                            if (!name || name.length === 0) {
                                name = `Chat ${index + 1}`;
                            }
                            
                            // Extract chat ID - DOM source uses fallback methods
                            // Note: This is less reliable than Store/Network sources
                            let chatId = null;
                            
                            // Try multiple data attributes (more reliable)
                            chatId = element.getAttribute('data-id') || 
                                    element.getAttribute('data-chat-id') ||
                                    element.getAttribute('data-testid') ||
                                    element.getAttribute('id');
                            
                            // Try to find link with chat ID
                            if (!chatId) {
                                const linkElement = element.querySelector('a[href]');
                                if (linkElement) {
                                    const href = linkElement.getAttribute('href');
                                    // Extract ID from href like /chat/1234567890@c.us
                                    const match = href.match(/[\\/](\\d+@[cg]\\.us|[^\\/]+)$/);
                                    if (match) chatId = match[1];
                                }
                            }
                            
                            // Try to find ID in child elements
                            if (!chatId) {
                                const idElement = element.querySelector('[data-id], [data-chat-id]');
                                if (idElement) {
                                    chatId = idElement.getAttribute('data-id') || 
                                            idElement.getAttribute('data-chat-id');
                                }
                            }
                            
                            // Try to extract from aria-label (less reliable but acceptable for DOM fallback)
                            if (!chatId && ariaLabel) {
                                // Try to find WhatsApp ID format in aria-label
                                const match = ariaLabel.match(/(\\+?\\d{10,15}@[cg]\\.us|\\d+@[cg]\\.us)/);
                                if (match) chatId = match[1];
                            }
                            
                            // Last resort: generate stable fallback ID based on name and position
                            if (!chatId) {
                                // Use hash of name + index for stability
                                const nameHash = name.split('').reduce((acc, char) => {
                                    return ((acc << 5) - acc) + char.charCodeAt(0);
                                }, 0);
                                chatId = `dom_chat_${Math.abs(nameHash)}_${index}`;
                            }
                            
                            const isGroup = element.querySelector('[data-testid="group"]') !== null ||
                                           element.querySelector('[data-testid="group-icon"]') !== null ||
                                           (ariaLabel && (ariaLabel.toLowerCase().includes('group') || 
                                                          ariaLabel.toLowerCase().includes('групп'))) ||
                                           false;
                            
                            const avatarElement = element.querySelector('img[src]');
                            const avatar = avatarElement ? avatarElement.getAttribute('src') : null;
                            
                            let messageCount = 0;
                            const unreadElement = element.querySelector('[data-testid="icon-unread-count"]');
                            if (unreadElement) {
                                const unreadText = unreadElement.textContent.trim();
                                messageCount = parseInt(unreadText) || 0;
                            }
                            
                            if (name && name.length > 0 && name !== `Chat ${index + 1}`) {
                                chats.push({
                                    id: chatId,
                                    name: name,
                                    isGroup: isGroup,
                                    unreadCount: messageCount,
                                    avatarUrl: avatar,
                                    rawData: {
                                        selector: bestSelector || 'fallback',
                                        index: index,
                                        hasAriaLabel: !!ariaLabel,
                                    }
                                });
                            }
                        } catch (e) {
                            console.error('Error parsing chat element:', e);
                        }
                    });
                    
                    return chats;
                }
            """)
            
            # Convert to RawChat objects
            raw_chats = []
            new_chats_count = 0
            
            for chat_data in chats_data or []:
                chat_id = chat_data.get('id')
                if not chat_id:
                    continue
                
                # Track seen IDs to avoid duplicates
                if chat_id in self._seen_ids:
                    continue
                
                self._seen_ids.add(chat_id)
                new_chats_count += 1
                
                # For DOM source, use wid for fallback IDs (non-JID format)
                # and jid for proper WhatsApp JIDs
                jid = None
                wid = None
                
                if '@' in chat_id:
                    # Looks like a proper WhatsApp JID
                    jid = chat_id
                else:
                    # Fallback ID - use wid field
                    wid = chat_id
                
                raw_chat = RawChat(
                    source="dom",
                    jid=jid,
                    wid=wid,  # Store fallback ID here for DOM source
                    name=chat_data.get('name'),
                    is_group=chat_data.get('isGroup', False),
                    unread_count=chat_data.get('unreadCount', 0),
                    avatar_url=chat_data.get('avatarUrl'),
                    raw_data=chat_data.get('rawData', {})
                )
                raw_chats.append(raw_chat)
            
            # Track if we got new chats
            if new_chats_count == 0:
                self._no_new_chats_count += 1
            else:
                self._no_new_chats_count = 0  # Reset counter if we found new chats
                # If we found new chats, we're not at bottom yet
                if self._reached_bottom:
                    logger.info("DOM source: found new chats after reaching bottom, resetting bottom flag")
                    self._reached_bottom = False
                
                # If this is the first batch with chats, try aggressive scrolling to load all
                # This helps with virtual scrolling - scroll to bottom immediately after first load
                if len(self._seen_ids) == new_chats_count and new_chats_count > 0:
                    logger.info("DOM source: first batch loaded %d chats, scrolling to bottom to load all", new_chats_count)
                    # Scroll to absolute bottom to trigger loading of all chats
                    await self._scroll_to_bottom_aggressive()
            
            logger.info(
                "DOM source: parsed %d chats (%d new, %d total seen, no_new_count=%d)",
                len(chats_data) if chats_data else 0,
                new_chats_count,
                len(self._seen_ids),
                self._no_new_chats_count
            )
            
            return raw_chats
            
        except Exception as e:
            logger.error("Failed to fetch chats from DOM: %s", str(e), exc_info=True)
            return []
    
    async def scroll_for_more(self) -> bool:
        """
        Scroll to load more chats.
        
        Returns:
            True if scrolled, False if reached bottom
        """
        try:
            scroll_info = await self.page.evaluate("""
                () => {
                    // Try to find chat list container - try multiple selectors
                    let chatList = null;
                    const selectors = [
                        'div[data-testid="chatlist"]',
                        'div[role="listbox"]',
                        'div[aria-label*="Chat"]',
                        '#pane-side',
                        'div[data-testid="chatlist"] > div',
                        'div[role="application"] > div > div'
                    ];
                    
                    for (const selector of selectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            // Check if element is scrollable
                            const style = window.getComputedStyle(element);
                            if (element.scrollHeight > element.clientHeight || 
                                style.overflowY === 'auto' || 
                                style.overflowY === 'scroll' ||
                                element.scrollHeight > 0) {
                                chatList = element;
                                break;
                            }
                        }
                    }
                    
                    if (chatList) {
                        const oldScrollTop = chatList.scrollTop;
                        const oldScrollHeight = chatList.scrollHeight;
                        const oldClientHeight = chatList.clientHeight;
                        
                        // Calculate distance to bottom
                        const distanceToBottom = chatList.scrollHeight - chatList.scrollTop - chatList.clientHeight;
                        
                        // Scroll strategy for virtual scrolling:
                        // Always scroll to near bottom (not absolute bottom) to trigger loading
                        // Virtual scrolling loads content as we approach bottom
                        // Don't scroll to absolute bottom immediately - leave space for loading
                        if (distanceToBottom > 500) {
                            // Far from bottom, scroll by large amount to get closer
                            const scrollAmount = Math.max(
                                chatList.clientHeight * 2.0,  // 200% of viewport for faster loading
                                1500  // Minimum 1500px
                            );
                            chatList.scrollTop += scrollAmount;
                        } else {
                            // Close to bottom, scroll to near bottom (not absolute) to trigger loading
                            // Leave some space (200px) to allow virtual scrolling to load more
                            chatList.scrollTop = chatList.scrollHeight - chatList.clientHeight - 200;
                        }
                        
                        // Force a small delay to let virtual scrolling work
                        // (actual delay happens in Python)
                        
                        // Wait a moment for virtual scrolling to update scrollHeight
                        // (actual wait happens in Python)
                        const newScrollHeight = chatList.scrollHeight;
                        // More lenient bottom detection - consider bottom if within 300px
                        // This prevents premature completion when virtual scrolling is still loading
                        const atBottom = chatList.scrollTop >= chatList.scrollHeight - chatList.clientHeight - 300;
                        
                        return {
                            scrolled: chatList.scrollTop !== oldScrollTop,
                            scrollTop: chatList.scrollTop,
                            scrollHeight: newScrollHeight,
                            oldScrollHeight: oldScrollHeight,
                            clientHeight: chatList.clientHeight,
                            oldClientHeight: oldClientHeight,
                            atBottom: atBottom,
                            hasMoreContent: newScrollHeight > oldScrollHeight,
                            scrollDelta: chatList.scrollTop - oldScrollTop
                        };
                    }
                    
                    // Fallback to window scroll
                    const oldScrollTop = window.scrollY;
                    const oldScrollHeight = document.body.scrollHeight;
                    const scrollAmount = window.innerHeight * 0.9;
                    window.scrollBy(0, scrollAmount);
                    
                    return {
                        scrolled: window.scrollY !== oldScrollTop,
                        scrollTop: window.scrollY,
                        scrollHeight: document.body.scrollHeight,
                        oldScrollHeight: oldScrollHeight,
                        clientHeight: window.innerHeight,
                        atBottom: window.scrollY >= document.body.scrollHeight - window.innerHeight - 200,
                        hasMoreContent: document.body.scrollHeight > oldScrollHeight,
                        scrollDelta: window.scrollY - oldScrollTop
                    };
                }
            """)
            
            self._reached_bottom = scroll_info.get('atBottom', False)
            scrolled = scroll_info.get('scrolled', False)
            
            if scrolled:
                self._scroll_iterations += 1
                logger.info(
                    "DOM scroll: iteration=%d, scrollTop=%.0f, scrollHeight=%.0f, scrollDelta=%.0f, atBottom=%s, hasMoreContent=%s",
                    self._scroll_iterations,
                    scroll_info.get('scrollTop', 0),
                    scroll_info.get('scrollHeight', 0),
                    scroll_info.get('scrollDelta', 0),
                    self._reached_bottom,
                    scroll_info.get('hasMoreContent', False)
                )
            else:
                logger.info("DOM scroll: could not scroll (atBottom=%s, scrollTop=%.0f, scrollHeight=%.0f)", 
                           self._reached_bottom,
                           scroll_info.get('scrollTop', 0),
                           scroll_info.get('scrollHeight', 0))
            
            return scrolled
            
        except Exception as e:
            logger.debug("Error scrolling: %s", str(e))
            return False
    
    async def _scroll_to_bottom_aggressive(self):
        """
        Aggressively scroll to bottom to load all chats.
        This is used after first batch to trigger virtual scrolling.
        """
        try:
            scroll_result = await self.page.evaluate("""
                () => {
                    // Try to find chat list container
                    let chatList = null;
                    const selectors = [
                        'div[data-testid="chatlist"]',
                        'div[role="listbox"]',
                        'div[aria-label*="Chat"]',
                        '#pane-side',
                        'div[data-testid="chatlist"] > div',
                        'div[role="application"] > div > div'
                    ];
                    
                    for (const selector of selectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            const style = window.getComputedStyle(element);
                            if (element.scrollHeight > element.clientHeight || 
                                style.overflowY === 'auto' || 
                                style.overflowY === 'scroll' ||
                                element.scrollHeight > 0) {
                                chatList = element;
                                break;
                            }
                        }
                    }
                    
                    if (chatList) {
                        const oldScrollTop = chatList.scrollTop;
                        const oldScrollHeight = chatList.scrollHeight;
                        
                        // Scroll to absolute bottom
                        chatList.scrollTop = chatList.scrollHeight;
                        
                        return {
                            scrolled: true,
                            oldScrollTop: oldScrollTop,
                            oldScrollHeight: oldScrollHeight,
                            newScrollTop: chatList.scrollTop,
                            newScrollHeight: chatList.scrollHeight,
                            scrollDelta: chatList.scrollTop - oldScrollTop
                        };
                    }
                    
                    // Fallback to window scroll
                    const oldScrollTop = window.scrollY;
                    const oldScrollHeight = document.body.scrollHeight;
                    window.scrollTo(0, document.body.scrollHeight);
                    
                    return {
                        scrolled: true,
                        oldScrollTop: oldScrollTop,
                        oldScrollHeight: oldScrollHeight,
                        newScrollTop: window.scrollY,
                        newScrollHeight: document.body.scrollHeight,
                        scrollDelta: window.scrollY - oldScrollTop
                    };
                }
            """)
            
            if scroll_result.get('scrolled'):
                logger.info(
                    "DOM source: aggressive scroll to bottom - scrollTop: %.0f -> %.0f, scrollHeight: %.0f -> %.0f",
                    scroll_result.get('oldScrollTop', 0),
                    scroll_result.get('newScrollTop', 0),
                    scroll_result.get('oldScrollHeight', 0),
                    scroll_result.get('newScrollHeight', 0)
                )
                
                # Wait for virtual scrolling to load content, then check if more content loaded
                await asyncio.sleep(2.0)  # Longer wait for aggressive scroll
                
                # Check if scrollHeight increased after waiting (virtual scrolling loaded more)
                check_result = await self.page.evaluate("""
                    () => {
                        let chatList = null;
                        const selectors = [
                            'div[data-testid="chatlist"]',
                            'div[role="listbox"]',
                            'div[aria-label*="Chat"]',
                            '#pane-side'
                        ];
                        
                        for (const selector of selectors) {
                            const element = document.querySelector(selector);
                            if (element && element.scrollHeight > element.clientHeight) {
                                chatList = element;
                                break;
                            }
                        }
                        
                        if (chatList) {
                            return {
                                scrollHeight: chatList.scrollHeight,
                                scrollTop: chatList.scrollTop,
                                clientHeight: chatList.clientHeight
                            };
                        }
                        return null;
                    }
                """)
                
                if check_result:
                    old_height = scroll_result.get('newScrollHeight', 0)
                    new_height = check_result.get('scrollHeight', 0)
                    if new_height > old_height:
                        logger.info(
                            "DOM source: scrollHeight increased after wait: %.0f -> %.0f (virtual scrolling loaded more)",
                            old_height, new_height
                        )
                        # Scroll again to new bottom
                        await self.page.evaluate("""
                            () => {
                                let chatList = null;
                                const selectors = [
                                    'div[data-testid="chatlist"]',
                                    'div[role="listbox"]',
                                    'div[aria-label*="Chat"]',
                                    '#pane-side'
                                ];
                                
                                for (const selector of selectors) {
                                    const element = document.querySelector(selector);
                                    if (element && element.scrollHeight > element.clientHeight) {
                                        chatList = element;
                                        break;
                                    }
                                }
                                
                                if (chatList) {
                                    chatList.scrollTop = chatList.scrollHeight;
                                }
                            }
                        """)
                        await asyncio.sleep(1.0)  # Wait again for more content
                
                # Reset bottom flag since we scrolled
                self._reached_bottom = False
                
        except Exception as e:
            logger.warning("Failed to aggressively scroll to bottom: %s", str(e))
    
    async def is_complete(self) -> bool:
        """Check if DOM parsing is complete (heuristic-based)."""
        # Complete if:
        # 1. Reached bottom AND no new chats found in last 5 iterations, OR
        # 2. No new chats found in last 10 iterations (even if not at bottom - might be stuck)
        # 3. Safety limit: too many scroll iterations
        
        if self._reached_bottom and self._no_new_chats_count >= 5:
            logger.info("DOM source: complete - reached bottom and no new chats for %d iterations", self._no_new_chats_count)
            return True
        
        if self._no_new_chats_count >= 10:
            logger.info("DOM source: complete - no new chats for %d iterations (might be stuck)", self._no_new_chats_count)
            return True
        
        # Safety limit: if we've scrolled too many times, consider it complete
        if self._scroll_iterations >= 100:
            logger.warning("DOM source: complete - reached scroll limit (%d iterations)", self._scroll_iterations)
            return True
        
        return False
    
    async def total_expected(self) -> Optional[int]:
        """DOM source doesn't know total count."""
        return None

