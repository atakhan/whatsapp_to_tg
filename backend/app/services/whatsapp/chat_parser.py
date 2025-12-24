"""
Chat parsing for WhatsApp Web
"""
import asyncio
import logging
import random
from typing import Dict, List, AsyncGenerator
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class ChatParser:
    """Parses WhatsApp chats from the page"""
    
    async def parse_chats_streaming(self, page: Page) -> AsyncGenerator[List[Dict], None]:
        """
        Parse chats from page, streaming them as they are found
        
        Yields batches of chats as they are parsed
        """
        try:
            logger.info("Starting to fetch chats list (streaming)")
            
            # Wait a bit for page to fully load
            await asyncio.sleep(1)
            
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
                    logger.info("Chat list container found with selector: %s", selector)
                    chatlist_found = True
                    break
                except Exception:
                    continue
            
            if not chatlist_found:
                logger.warning(
                    "Chat list container not found with any selector, trying to parse anyway",
                    extra={
                        "error_code": "WHATSAPP_CHATLIST_NOT_FOUND",
                        "extra_data": {"selectors_tried": chatlist_selectors},
                    },
                )
            
            # Scroll to top to ensure we start from the beginning
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.5)
            
            # Parse chats in batches as we scroll
            batch_size = 10
            total_parsed = 0
            
            # First, get initial batch of visible chats
            chats_batch = await self._parse_chats_batch(page, 0, batch_size)
            if chats_batch:
                total_parsed += len(chats_batch)
                yield chats_batch
            
            # Scroll down gradually to load more chats and parse them
            for scroll_iteration in range(5):  # Limit scroll iterations
                scroll_amount = random.randint(300, 500)
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await asyncio.sleep(0.5)
                
                # Parse new batch
                chats_batch = await self._parse_chats_batch(page, total_parsed, batch_size)
                if chats_batch:
                    total_parsed += len(chats_batch)
                    yield chats_batch
                else:
                    # No new chats found, might have reached the end
                    break
            
            logger.info("Finished streaming %d chats", total_parsed)
            
        except Exception as e:
            logger.error(
                "Failed to get chats (streaming)",
                extra={
                    "error_code": "WHATSAPP_GET_CHATS_STREAMING_FAIL",
                },
                exc_info=True,
            )
    
    async def parse_chats(self, page: Page) -> List[Dict]:
        """
        Parse all chats from page (non-streaming, blocking)
        
        Returns list of chats with:
        - id: chat ID
        - name: chat name
        - type: "personal" or "group"
        - avatar: avatar URL (if available)
        - message_count: approximate message count
        - is_group: boolean indicating if it's a group chat
        """
        try:
            logger.info("Starting to fetch chats list")
            
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
                    logger.info("Chat list container found with selector: %s", selector)
                    chatlist_found = True
                    break
                except Exception:
                    continue
            
            if not chatlist_found:
                logger.warning(
                    "Chat list container not found with any selector, trying to parse anyway",
                    extra={
                        "error_code": "WHATSAPP_CHATLIST_NOT_FOUND",
                        "extra_data": {"selectors_tried": chatlist_selectors},
                    },
                )
            
            # Scroll to top
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # Scroll down to load more chats (lazy loading)
            try:
                for i in range(3):
                    scroll_amount = random.randint(400, 600)
                    await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    await asyncio.sleep(random.uniform(0.8, 1.5))
                # Scroll back to top
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                logger.debug("Scroll failed: %s", str(e))
            
            # Wait for chats to render
            await asyncio.sleep(random.uniform(2.0, 3.0))
            
            # Parse all chats
            chats_data = await page.evaluate("""
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
                    for (const selector of chatSelectors) {
                        chatElements = document.querySelectorAll(selector);
                        if (chatElements.length > 0) {
                            console.log('Found ' + chatElements.length + ' elements with selector: ' + selector);
                            break;
                        }
                    }
                    
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
                            
                            let chatId = null;
                            if (ariaLabel) {
                                const match = ariaLabel.match(/(\\+?\\d{10,15}|\\d+@[cg]\\.us)/);
                                if (match) chatId = match[1];
                            }
                            
                            if (!chatId) {
                                chatId = element.getAttribute('data-id') || 
                                        element.getAttribute('data-chat-id') ||
                                        element.getAttribute('id');
                            }
                            
                            if (!chatId) {
                                chatId = `chat_${index}_${name.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 50)}`;
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
                                const chatData = {
                                    id: chatId,
                                    name: name,
                                    type: isGroup ? 'group' : 'personal',
                                    avatar: avatar,
                                    message_count: messageCount,
                                    is_group: isGroup
                                };
                                chats.push(chatData);
                                console.log(`Parsed chat [${index}]: id="${chatId}", name="${name}"`);
                            }
                        } catch (e) {
                            console.error('Error parsing chat element:', e);
                        }
                    });
                    
                    return chats;
                }
            """)
            
            logger.info("Found %d chats", len(chats_data) if chats_data else 0)
            
            # Convert to proper format
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
                "Failed to get chats",
                extra={
                    "error_code": "WHATSAPP_GET_CHATS_FAIL",
                },
                exc_info=True,
            )
            return []
    
    async def _parse_chats_batch(self, page: Page, start_index: int, batch_size: int) -> List[Dict]:
        """Parse a batch of chats from the page"""
        try:
            chats_data = await page.evaluate(f"""
                () => {{
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
                    for (const selector of chatSelectors) {{
                        chatElements = document.querySelectorAll(selector);
                        if (chatElements.length > 0) break;
                    }}
                    
                    if (chatElements.length === 0) {{
                        const allDivs = document.querySelectorAll('div[role="row"], div[aria-label]');
                        chatElements = Array.from(allDivs).filter(div => {{
                            const ariaLabel = div.getAttribute('aria-label') || '';
                            return ariaLabel.includes('Chat') || ariaLabel.includes('чат') || 
                                   ariaLabel.includes('group') || ariaLabel.includes('групп');
                        }});
                    }}
                    
                    // Get batch starting from start_index
                    const batchStart = {start_index};
                    const batchEnd = Math.min(batchStart + {batch_size}, chatElements.length);
                    
                    for (let i = batchStart; i < batchEnd; i++) {{
                        const element = chatElements[i];
                        try {{
                            let name = null;
                            const ariaLabel = element.getAttribute('aria-label');
                            if (ariaLabel) {{
                                const match = ariaLabel.match(/^([^,]+)/);
                                if (match) name = match[1].trim();
                            }}
                            
                            if (!name) {{
                                const titleElement = element.querySelector('[title]');
                                if (titleElement) {{
                                    name = titleElement.getAttribute('title') || titleElement.textContent.trim();
                                }}
                            }}
                            
                            if (!name) {{
                                const textContent = element.textContent.trim();
                                if (textContent && textContent.length < 100) {{
                                    name = textContent.split('\\n')[0].trim();
                                }}
                            }}
                            
                            if (!name || name.length === 0) {{
                                name = `Chat ${{i + 1}}`;
                            }}
                            
                            let chatId = null;
                            if (ariaLabel) {{
                                const match = ariaLabel.match(/(\\+?\\d{{10,15}}|\\d+@[cg]\\.us)/);
                                if (match) chatId = match[1];
                            }}
                            
                            if (!chatId) {{
                                chatId = element.getAttribute('data-id') || 
                                        element.getAttribute('data-chat-id') ||
                                        element.getAttribute('id');
                            }}
                            
                            if (!chatId) {{
                                chatId = `chat_${{i}}_${{name.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 50)}}`;
                            }}
                            
                            const isGroup = element.querySelector('[data-testid="group"]') !== null ||
                                           element.querySelector('[data-testid="group-icon"]') !== null ||
                                           (ariaLabel && (ariaLabel.toLowerCase().includes('group') || 
                                                          ariaLabel.toLowerCase().includes('групп'))) ||
                                           false;
                            
                            const avatarElement = element.querySelector('img[src]');
                            const avatar = avatarElement ? avatarElement.getAttribute('src') : null;
                            
                            let messageCount = 0;
                            const unreadElement = element.querySelector('[data-testid="icon-unread-count"]');
                            if (unreadElement) {{
                                const unreadText = unreadElement.textContent.trim();
                                messageCount = parseInt(unreadText) || 0;
                            }}
                            
                            if (name && name.length > 0 && name !== `Chat ${{i + 1}}`) {{
                                chats.push({{
                                    id: chatId,
                                    name: name,
                                    type: isGroup ? 'group' : 'personal',
                                    avatar: avatar,
                                    message_count: messageCount,
                                    is_group: isGroup
                                }});
                            }}
                        }} catch (e) {{
                            console.error('Error parsing chat element:', e);
                        }}
                    }}
                    
                    return chats;
                }}
            """)
            
            # Convert to proper format
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
            logger.debug("Error parsing chat batch: %s", str(e))
            return []
