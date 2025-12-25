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
            batch_size = 20
            total_parsed = 0
            seen_chat_ids = set()  # Track unique chat IDs to avoid duplicates
            
            # Scroll to top first
            await page.evaluate("""
                () => {
                    const chatList = document.querySelector('div[data-testid="chatlist"]') || 
                                   document.querySelector('div[role="listbox"]');
                    if (chatList) {
                        chatList.scrollTop = 0;
                    } else {
                        window.scrollTo(0, 0);
                    }
                }
            """)
            await asyncio.sleep(1.0)
            
            # First, get initial batch of visible chats
            chats_batch = await self._parse_all_visible_chats(page)
            if chats_batch:
                # Filter out duplicates
                new_chats = [chat for chat in chats_batch if chat.get('id') not in seen_chat_ids]
                for chat in new_chats:
                    seen_chat_ids.add(chat.get('id'))
                if new_chats:
                    total_parsed += len(new_chats)
                    yield new_chats
                    logger.info("Initial batch: found %d chats (total: %d)", len(new_chats), total_parsed)
            
            # Scroll down gradually to load more chats and parse them
            # Continue scrolling until we reach the bottom AND no new chats are found
            max_scroll_iterations = 200  # Safety limit to prevent infinite loops
            no_new_chats_count = 0  # Count consecutive iterations with no new chats
            max_no_new_chats = 10  # Stop after 10 consecutive iterations with no new chats (increased)
            previous_chat_count = 0  # Track total chat count to detect if we're still loading
            reached_bottom = False  # Track if we've reached the bottom
            last_scroll_position = 0  # Track last scroll position to detect if we're stuck
            
            for scroll_iteration in range(max_scroll_iterations):
                # Get chat list container and scroll info
                chat_list_info = await page.evaluate("""
                    () => {
                        const chatList = document.querySelector('div[data-testid="chatlist"]') || 
                                       document.querySelector('div[role="listbox"]') ||
                                       document.querySelector('div[aria-label*="Chat list"]') ||
                                       document.querySelector('[role="application"] > div > div');
                        if (chatList) {
                            return {
                                found: true,
                                scrollTop: chatList.scrollTop,
                                scrollHeight: chatList.scrollHeight,
                                clientHeight: chatList.clientHeight,
                                maxScroll: chatList.scrollHeight - chatList.clientHeight
                            };
                        }
                        return { found: false };
                    }
                """)
                
                # Check if we've reached the bottom
                if chat_list_info.get('found'):
                    scroll_progress = chat_list_info.get('scrollTop', 0)
                    scroll_max = chat_list_info.get('maxScroll', 0)
                    
                    # Check if we're at or near the bottom
                    if scroll_max > 0:
                        scroll_percentage = (scroll_progress / scroll_max) * 100 if scroll_max > 0 else 0
                        if scroll_progress >= scroll_max - 10:  # Within 10px of bottom
                            if not reached_bottom:
                                reached_bottom = True
                                logger.info("Reached bottom of chat list (scroll: %d/%d, %.1f%%)", 
                                          scroll_progress, scroll_max, scroll_percentage)
                            # Continue for a few more iterations to catch any late-loading chats
                        else:
                            logger.debug("Scroll progress: %d/%d (%.1f%%)", scroll_progress, scroll_max, scroll_percentage)
                    
                    # Check if scroll position hasn't changed (stuck)
                    if scroll_progress == last_scroll_position and scroll_iteration > 0:
                        logger.warning("Scroll position stuck at %d, trying alternative scroll method", scroll_progress)
                        # Try scrolling window instead
                        await page.evaluate("window.scrollBy(0, 500)")
                        await asyncio.sleep(0.5)
                    
                    last_scroll_position = scroll_progress
                
                # Scroll using keyboard (more reliable with virtual scrolling)
                # Use smaller scroll increments to ensure we don't skip chats
                try:
                    # Focus on chat list first
                    await page.evaluate("""
                        () => {
                            const chatList = document.querySelector('div[data-testid="chatlist"]') || 
                                           document.querySelector('div[role="listbox"]');
                            if (chatList) {
                                chatList.focus();
                            }
                        }
                    """)
                    # Press ArrowDown multiple times for smaller increments
                    for _ in range(5):
                        await page.keyboard.press('ArrowDown')
                        await asyncio.sleep(0.1)
                    # Also try PageDown for larger jumps
                    await page.keyboard.press('PageDown')
                    await asyncio.sleep(0.2)
                except Exception:
                    # Fallback to scrollTop - use smaller increments
                    scroll_amount = random.randint(300, 500)
                    await page.evaluate(f"""
                        () => {{
                            const chatList = document.querySelector('div[data-testid="chatlist"]') || 
                                           document.querySelector('div[role="listbox"]');
                            if (chatList) {{
                                const oldScroll = chatList.scrollTop;
                                chatList.scrollTop += {scroll_amount};
                                // If scroll didn't change, try scrolling to a specific position
                                if (chatList.scrollTop === oldScroll && chatList.scrollHeight > chatList.clientHeight) {{
                                    chatList.scrollTop = Math.min(chatList.scrollTop + 100, chatList.scrollHeight - chatList.clientHeight);
                                }}
                            }} else {{
                                window.scrollBy(0, {scroll_amount});
                            }}
                        }}
                    """)
                
                await asyncio.sleep(1.5)  # Give more time for lazy loading
                
                # Parse all visible chats
                chats_batch = await self._parse_all_visible_chats(page)
                current_chat_count = len(chats_batch) if chats_batch else 0
                
                if chats_batch:
                    # Filter out duplicates
                    new_chats = [chat for chat in chats_batch if chat.get('id') not in seen_chat_ids]
                    if new_chats:
                        for chat in new_chats:
                            seen_chat_ids.add(chat.get('id'))
                        total_parsed += len(new_chats)
                        yield new_chats
                        no_new_chats_count = 0  # Reset counter
                        previous_chat_count = current_chat_count
                        logger.info("Iteration %d: Found %d new chats (total unique: %d, total in DOM: %d)", 
                                  scroll_iteration + 1, len(new_chats), total_parsed, current_chat_count)
                    else:
                        # Check if total visible chats increased (even if they're duplicates)
                        if current_chat_count > previous_chat_count:
                            logger.info("Iteration %d: DOM chat count increased (%d -> %d), but no new unique chats. Continuing...", 
                                       scroll_iteration + 1, previous_chat_count, current_chat_count)
                            previous_chat_count = current_chat_count
                            no_new_chats_count = 0  # Reset - page is still loading
                        else:
                            no_new_chats_count += 1
                            logger.info("Iteration %d: No new chats (consecutive: %d/%d, unique: %d, DOM: %d)", 
                                       scroll_iteration + 1, no_new_chats_count, max_no_new_chats, total_parsed, current_chat_count)
                else:
                    no_new_chats_count += 1
                    logger.info("Iteration %d: No chats parsed (consecutive: %d/%d, unique: %d)", 
                               scroll_iteration + 1, no_new_chats_count, max_no_new_chats, total_parsed)
                
                # Stop if we've reached bottom AND no new chats found for several consecutive iterations
                if reached_bottom and no_new_chats_count >= max_no_new_chats:
                    logger.info("Stopping scroll: reached bottom and no new chats found for %d consecutive iterations (total parsed: %d)", 
                              no_new_chats_count, total_parsed)
                    break
                elif not reached_bottom and no_new_chats_count >= max_no_new_chats * 2:
                    # If we haven't reached bottom but no new chats for a while, continue scrolling
                    logger.info("No new chats for %d iterations but haven't reached bottom yet, continuing...", no_new_chats_count)
                    no_new_chats_count = max_no_new_chats  # Reset to allow more iterations
                
                # Additional check: try scrolling to the very bottom to ensure we've loaded everything
                if scroll_iteration % 10 == 9:  # Every 10 iterations
                    try:
                        reached_bottom = await page.evaluate("""
                            () => {
                                const chatList = document.querySelector('div[data-testid="chatlist"]') || 
                                               document.querySelector('div[role="listbox"]');
                                if (chatList) {
                                    const oldScrollTop = chatList.scrollTop;
                                    chatList.scrollTop = chatList.scrollHeight;
                                    return chatList.scrollTop >= chatList.scrollHeight - 10;
                                }
                                // Fallback
                                window.scrollTo(0, document.body.scrollHeight);
                                return true;
                            }
                        """)
                        await asyncio.sleep(2.0)  # Give more time for content to load
                        # Re-parse after scrolling to bottom
                        chats_batch = await self._parse_all_visible_chats(page)
                        if chats_batch:
                            new_chats = [chat for chat in chats_batch if chat.get('id') not in seen_chat_ids]
                            if new_chats:
                                for chat in new_chats:
                                    seen_chat_ids.add(chat.get('id'))
                                total_parsed += len(new_chats)
                                yield new_chats
                                no_new_chats_count = 0
                                logger.info("Found %d additional chats after scrolling to bottom (total: %d, reached_bottom: %s)", 
                                          len(new_chats), total_parsed, reached_bottom)
                    except Exception as e:
                        logger.debug("Error scrolling to bottom: %s", str(e))
            
            # Check if we stopped due to max iterations limit
            if scroll_iteration == max_scroll_iterations - 1:
                logger.warning(
                    "Stopped scrolling: reached maximum iterations limit (%d) (total parsed: %d, reached_bottom: %s, no_new_chats_count: %d)",
                    max_scroll_iterations, total_parsed, reached_bottom, no_new_chats_count
                )
            
            # Final check: scroll to absolute bottom and parse one more time
            logger.info("Performing final check: scrolling to absolute bottom...")
            try:
                await page.evaluate("""
                    () => {
                        const chatList = document.querySelector('div[data-testid="chatlist"]') || 
                                       document.querySelector('div[role="listbox"]');
                        if (chatList) {
                            chatList.scrollTop = chatList.scrollHeight;
                        } else {
                            window.scrollTo(0, document.body.scrollHeight);
                        }
                    }
                """)
                await asyncio.sleep(2.0)
                
                # Parse one final time
                chats_batch = await self._parse_all_visible_chats(page)
                if chats_batch:
                    new_chats = [chat for chat in chats_batch if chat.get('id') not in seen_chat_ids]
                    if new_chats:
                        for chat in new_chats:
                            seen_chat_ids.add(chat.get('id'))
                        total_parsed += len(new_chats)
                        yield new_chats
                        logger.info("Final check: Found %d additional chats (total: %d)", len(new_chats), total_parsed)
            except Exception as e:
                logger.debug("Error in final check: %s", str(e))
            
            logger.info("Finished streaming %d unique chats", total_parsed)
            
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
    
    async def _parse_all_visible_chats(self, page: Page) -> List[Dict]:
        """Parse all currently visible chats from the page"""
        try:
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
                            // Get all direct children that might be chats
                            chatElements = Array.from(chatListContainer.querySelectorAll('div[role="row"], div > div'));
                        }
                    }
                    
                    console.log('Found ' + chatElements.length + ' chat elements using selector: ' + (bestSelector || 'fallback'));
                    
                    // Important: Parse ALL elements in DOM, not just visible ones
                    // Virtual scrolling may keep elements in DOM even when not visible
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
            
            logger.info("Parsed %d chats from page (all in DOM, not just visible)", len(result))
            return result
            
        except Exception as e:
            logger.debug("Error parsing all visible chats: %s", str(e))
            return []
