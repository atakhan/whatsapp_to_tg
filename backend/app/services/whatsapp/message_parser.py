"""
Message parsing for WhatsApp Web
"""
import asyncio
import logging
import random
import time
from typing import Dict, List, AsyncGenerator, Optional, Tuple
from playwright.async_api import Page, ElementHandle

logger = logging.getLogger(__name__)


class MessageParser:
    """Parses WhatsApp messages from chat pages"""
    
    async def parse_messages_streaming(
        self, 
        page: Page, 
        chat_id: str, 
        limit: Optional[int] = None,
        chat_name: Optional[str] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream messages from a specific WhatsApp chat as they are loaded
        
        Yields messages with progress updates:
        - type: 'progress' - progress update with loaded/total count
        - type: 'message' - actual message data
        - type: 'complete' - all messages loaded
        """
        try:
            log_message = f"Начинаем загрузку сообщений для чата {chat_id}"
            if chat_name:
                log_message += f" (имя: '{chat_name}')"
            log_message += f" (лимит: {limit or 'без ограничений'})"
            logger.info("Starting to stream messages for chat %s (name: %s, limit: %s)", chat_id, chat_name, limit)
            yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
            
            # Open the chat
            try:
                chat_opened = await self._open_chat(page, chat_id, chat_name)
                if not chat_opened:
                    log_message = f"Чат {chat_id} не найден"
                    logger.warning("Chat %s not found", chat_id)
                    yield {'type': 'log', 'level': 'warning', 'message': log_message, 'timestamp': time.time()}
                    yield {'type': 'error', 'error': 'Chat not found'}
                    return
            except Exception as e:
                error_message = f"Ошибка при открытии чата: {str(e)}"
                logger.error("Error opening chat %s: %s", chat_id, str(e), exc_info=True)
                yield {'type': 'log', 'level': 'error', 'message': error_message, 'timestamp': time.time()}
                # Extract meaningful error message
                if "Timeout" in str(e) or "timeout" in str(e).lower():
                    error_msg = "Не удалось открыть чат: превышено время ожидания. Возможно, чат перекрыт диалогом или другим элементом."
                elif "intercepts pointer events" in str(e):
                    error_msg = "Не удалось открыть чат: элемент перекрыт диалогом или другим элементом интерфейса."
                else:
                    error_msg = f"Не удалось открыть чат: {str(e)}"
                yield {'type': 'error', 'error': error_msg}
                return
            
            # Get opened chat name for logging
            opened_chat_name = await page.evaluate("""
                () => {
                    const header = document.querySelector('[data-testid="conversation-header"]') ||
                                  document.querySelector('header[role="banner"]');
                    if (!header) return '';
                    const titleElement = header.querySelector('span[title]') ||
                                        header.querySelector('div[title]') ||
                                        header.querySelector('span[dir="auto"]');
                    return titleElement ? (titleElement.getAttribute('title') || titleElement.textContent || '').trim() : '';
                }
            """)
            
            log_message = f"Чат {chat_id} успешно открыт"
            if opened_chat_name:
                log_message += f" (открыт чат: '{opened_chat_name}')"
            logger.info("Chat %s opened successfully (opened: '%s')", chat_id, opened_chat_name)
            yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
            
            # Wait for messages to load
            await asyncio.sleep(3.0)
            
            # Wait for message elements to appear
            log_message = "Ожидание появления элементов сообщений..."
            logger.info("Waiting for message elements to appear...")
            yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
            
            message_appeared = False
            for wait_attempt in range(10):
                try:
                    has_messages = await page.evaluate("""
                        () => {
                            return !!(
                                document.querySelector('[data-testid*="msg-container"]') ||
                                document.querySelector('[data-testid*="msg-text"]') ||
                                document.querySelector('span.selectable-text') ||
                                document.querySelector('div[data-id]')
                            );
                        }
                    """)
                    if has_messages:
                        message_appeared = True
                        log_message = f"Элементы сообщений появились (попытка {wait_attempt + 1})"
                        logger.info("Message elements appeared (attempt %d)", wait_attempt + 1)
                        yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
                        break
                    await asyncio.sleep(1.0)
                except Exception as e:
                    log_message = f"Ошибка проверки сообщений (попытка {wait_attempt + 1}): {str(e)}"
                    logger.debug("Error checking for messages (attempt %d): %s", wait_attempt + 1, str(e))
                    yield {'type': 'log', 'level': 'debug', 'message': log_message, 'timestamp': time.time()}
                    await asyncio.sleep(1.0)
            
            if not message_appeared:
                log_message = "Элементы сообщений не найдены после ожидания, но продолжаем..."
                logger.warning("No message elements found after waiting, but continuing...")
                yield {'type': 'log', 'level': 'warning', 'message': log_message, 'timestamp': time.time()}
            
            # Find message container
            log_message = "Поиск контейнера сообщений с помощью JavaScript..."
            logger.info("Searching for message container using JavaScript...")
            yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
            
            message_container = await self._find_message_container(page)
            
            if not message_container:
                log_message = "Контейнер сообщений не найден ни одним методом"
                logger.error("Message container not found with any method")
                yield {'type': 'log', 'level': 'error', 'message': log_message, 'timestamp': time.time()}
                yield {'type': 'error', 'error': 'Message container not found'}
                return
            
            log_message = "Контейнер сообщений успешно найден"
            logger.info("Message container found successfully")
            yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
            
            # Log container details
            try:
                if message_container:
                    container_info = await message_container.evaluate("element => ({ scrollHeight: element.scrollHeight, clientHeight: element.clientHeight, childCount: element.children.length })")
                    log_message = f"Контейнер: scrollHeight={container_info.get('scrollHeight')}, clientHeight={container_info.get('clientHeight')}, childCount={container_info.get('childCount')}"
                    yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
            except Exception as e:
                log_message = f"Не удалось получить информацию о контейнере: {str(e)}"
                yield {'type': 'log', 'level': 'warning', 'message': log_message, 'timestamp': time.time()}
            
            # Stream messages as we scroll
            processed_message_ids = set()
            scroll_attempts = 0
            max_scroll_attempts = 200
            no_change_count = 0
            last_processed_count = 0
            
            # Send initial progress
            yield {'type': 'progress', 'loaded': 0, 'total': None, 'message': 'Начинаем загрузку сообщений...'}
            
            # Parse initial messages before scrolling
            log_message = "Парсинг начальных сообщений..."
            logger.info("Parsing initial messages...")
            yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
            
            initial_messages = await self._parse_all_messages(page, message_container)
            initial_count = len(initial_messages) if initial_messages else 0
            
            if initial_count > 0:
                log_message = f"Найдено {initial_count} начальных сообщений"
                logger.info("Found %d initial messages", initial_count)
                yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
            else:
                log_message = "Начальные сообщения не найдены (0 сообщений)"
                logger.warning("No initial messages found")
                yield {'type': 'log', 'level': 'warning', 'message': log_message, 'timestamp': time.time()}
                
                # Additional diagnostic - detailed analysis
                try:
                    # Check if container has any child elements
                    child_count = await message_container.evaluate("element => element.children.length")
                    log_message = f"Контейнер содержит {child_count} дочерних элементов"
                    yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
                    
                    # Check for message-like elements
                    msg_elements_count = await message_container.evaluate("""
                        element => {
                            const allDivs = element.querySelectorAll('div');
                            return {
                                dataId: element.querySelectorAll('div[data-id]').length,
                                msgContainer: element.querySelectorAll('[data-testid*="msg"]').length,
                                selectableText: element.querySelectorAll('span.selectable-text').length,
                                totalDivs: allDivs.length,
                                hasText: Array.from(allDivs).some(div => div.textContent && div.textContent.trim().length > 0),
                                scrollHeight: element.scrollHeight,
                                clientHeight: element.clientHeight
                            };
                        }
                    """)
                    log_message = f"Диагностика контейнера: div[data-id]={msg_elements_count.get('dataId')}, msg-container={msg_elements_count.get('msgContainer')}, selectable-text={msg_elements_count.get('selectableText')}, всего div={msg_elements_count.get('totalDivs')}, есть текст={msg_elements_count.get('hasText')}, scrollHeight={msg_elements_count.get('scrollHeight')}, clientHeight={msg_elements_count.get('clientHeight')}"
                    yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
                    
                    # Check page structure
                    page_structure = await page.evaluate("""
                        () => {
                            return {
                                title: document.title,
                                url: window.location.href,
                                hasApp: !!document.querySelector('#app'),
                                hasMain: !!document.querySelector('#main'),
                                roleLog: document.querySelectorAll('div[role="log"]').length,
                                conversationPanel: document.querySelectorAll('[data-testid*="conversation"]').length
                            };
                        }
                    """)
                    log_message = f"Структура страницы: title={page_structure.get('title')}, hasApp={page_structure.get('hasApp')}, hasMain={page_structure.get('hasMain')}, roleLog={page_structure.get('roleLog')}, conversationPanel={page_structure.get('conversationPanel')}"
                    yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
                except Exception as e:
                    log_message = f"Ошибка диагностики контейнера: {str(e)}"
                    yield {'type': 'log', 'level': 'error', 'message': log_message, 'timestamp': time.time()}
            
            if initial_messages:
                for msg in initial_messages:
                    if msg.get('id') and msg['id'] not in processed_message_ids:
                        processed_message_ids.add(msg['id'])
                        yield {'type': 'message', 'message': msg}
                
                last_processed_count = len(processed_message_ids)
                log_message = f"Отправлено {last_processed_count} начальных сообщений"
                logger.info("Sending %d initial messages", last_processed_count)
                yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
                yield {
                    'type': 'progress',
                    'loaded': last_processed_count,
                    'total': None,
                    'message': f'Загружено {last_processed_count} сообщений...'
                }
            else:
                log_message = "Начальные сообщения не найдены"
                logger.warning("No initial messages found")
                yield {'type': 'log', 'level': 'warning', 'message': log_message, 'timestamp': time.time()}
            
            # Scroll and load more messages
            while scroll_attempts < max_scroll_attempts:
                # Scroll to top to load older messages
                await message_container.evaluate("element => element.scrollTop = 0")
                
                # Wait for messages to load
                scroll_delay = random.uniform(1.5, 2.5)
                await asyncio.sleep(scroll_delay)
                
                # Parse messages
                all_messages = await self._parse_all_messages(page, message_container)
                parsed_count = len(all_messages) if all_messages else 0
                
                if scroll_attempts % 5 == 0 or parsed_count > 0:
                    log_message = f"Парсинг: найдено {parsed_count} сообщений (попытка {scroll_attempts}, обработано: {len(processed_message_ids)})"
                    logger.info(
                        "Parsed %d messages (attempt %d, processed: %d)",
                        parsed_count,
                        scroll_attempts,
                        len(processed_message_ids)
                    )
                    yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
                
                # Log if no messages found after several attempts
                if parsed_count == 0 and scroll_attempts >= 3:
                    log_message = f"Попытка {scroll_attempts}: сообщения не найдены (0 сообщений в контейнере)"
                    yield {'type': 'log', 'level': 'warning', 'message': log_message, 'timestamp': time.time()}
                
                # Filter out already processed messages
                new_messages = [
                    msg for msg in all_messages 
                    if msg.get('id') and msg['id'] not in processed_message_ids
                ]
                
                # Add new message IDs to processed set
                for msg in new_messages:
                    if msg.get('id'):
                        processed_message_ids.add(msg['id'])
                
                # Send new messages
                if new_messages:
                    log_message = f"Отправка {len(new_messages)} новых сообщений (всего обработано: {len(processed_message_ids)})"
                    logger.info(
                        "Sending %d new messages (total processed: %d)",
                        len(new_messages),
                        len(processed_message_ids)
                    )
                    yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
                    for msg in new_messages:
                        yield {'type': 'message', 'message': msg}
                
                current_processed_count = len(processed_message_ids)
                
                # Send progress update
                yield {
                    'type': 'progress',
                    'loaded': current_processed_count,
                    'total': None,
                    'message': f'Загружено {current_processed_count} сообщений...'
                }
                
                # Update tracking
                if current_processed_count > last_processed_count:
                    last_processed_count = current_processed_count
                    no_change_count = 0
                    
                    # Check if we've reached the limit
                    if limit and current_processed_count >= limit:
                        logger.info("Reached message limit: %d", limit)
                        yield {
                            'type': 'progress',
                            'loaded': limit,
                            'total': limit,
                            'message': f'Загружено {limit} сообщений (лимит)'
                        }
                        break
                else:
                    no_change_count += 1
                    # If no change for 3 consecutive attempts, we're done
                    if no_change_count >= 3 and scroll_attempts >= 6:
                        log_message = f"Загружены все сообщения: {current_processed_count} всего (после {scroll_attempts} скроллов)"
                        logger.info("Loaded all messages: %d total (after %d scrolls)", current_processed_count, scroll_attempts)
                        yield {'type': 'log', 'level': 'info', 'message': log_message, 'timestamp': time.time()}
                        yield {
                            'type': 'progress',
                            'loaded': current_processed_count,
                            'total': current_processed_count,
                            'message': f'Загружено {current_processed_count} сообщений'
                        }
                        break
                
                scroll_attempts += 1
            
            # Send completion
            yield {'type': 'complete', 'total': len(processed_message_ids), 'message': 'Все сообщения загружены'}
            
        except Exception as e:
            log_message = f"Ошибка при загрузке сообщений: {str(e)}"
            logger.error(
                "Failed to stream messages",
                extra={
                    "error_code": "WHATSAPP_STREAM_MESSAGES_FAIL",
                    "extra_data": {"chat_id": chat_id},
                },
                exc_info=True,
            )
            yield {'type': 'log', 'level': 'error', 'message': log_message, 'timestamp': time.time()}
            yield {'type': 'error', 'error': str(e)}
    
    async def parse_messages(self, page: Page, chat_id: str) -> List[Dict]:
        """
        Parse all messages from a specific WhatsApp chat (non-streaming, blocking)
        
        Returns list of messages with:
        - timestamp: message timestamp (ISO format)
        - sender: sender name
        - type: message type (text, image, video, audio, voice, document, etc.)
        - text: message text
        - media_path: path to downloaded media file (if applicable)
        """
        try:
            logger.info("Starting to fetch messages for chat %s", chat_id)
            
            # Open the chat
            chat_opened = await self._open_chat(page, chat_id)
            if not chat_opened:
                logger.warning("Chat %s not found", chat_id)
                return []
            
            # Wait for messages to load
            await asyncio.sleep(3.0)
            
            # Find message container
            message_container = await self._find_message_container(page)
            if not message_container:
                logger.warning("Message container not found")
                return []
            
            # Parse all messages
            messages = await self._parse_all_messages(page, message_container)
            
            logger.info("Found %d messages", len(messages))
            return messages
            
        except Exception as e:
            logger.error(
                "Failed to get messages",
                extra={
                    "error_code": "WHATSAPP_GET_MESSAGES_FAIL",
                    "extra_data": {"chat_id": chat_id},
                },
                exc_info=True,
            )
            return []
    
    async def _open_chat(self, page: Page, chat_id: str, chat_name: Optional[str] = None) -> bool:
        """Open a chat by clicking on it"""
        try:
            logger.info("Opening chat with ID: %s (provided name: %s)", chat_id, chat_name)
            
            # Check if a chat is already open and get its name
            current_chat_name = await page.evaluate("""
                () => {
                    const header = document.querySelector('[data-testid="conversation-header"]') ||
                                  document.querySelector('header[role="banner"]');
                    if (!header) return '';
                    const titleElement = header.querySelector('span[title]') ||
                                        header.querySelector('div[title]') ||
                                        header.querySelector('span[dir="auto"]');
                    return titleElement ? (titleElement.getAttribute('title') || titleElement.textContent || '').trim() : '';
                }
            """)
            if current_chat_name:
                logger.info("Currently opened chat: '%s'", current_chat_name)
            
            # Use provided chat_name if available, otherwise try to extract from chat_id
            if not chat_name and '_' in chat_id:
                parts = chat_id.split('_')
                if len(parts) > 2:
                    # Format: chat_2_ИмяЧата - but name is already converted to underscores
                    # So we can't reliably extract it. Skip this.
                    pass
                elif len(parts) == 2 and not parts[1].isdigit():
                    # Format: chat_ИмяЧата - same issue
                    pass
            
            # Strategy 0: Check if the correct chat is already open (fastest path)
            if current_chat_name and chat_name:
                normalized_current = current_chat_name.lower().strip()
                normalized_expected = chat_name.lower().strip()
                # Exact match
                if normalized_current == normalized_expected:
                    logger.info("Correct chat '%s' is already open (exact match), skipping", current_chat_name)
                    return True
                # Substring match
                if normalized_expected in normalized_current or normalized_current in normalized_expected:
                    logger.info("Correct chat '%s' is already open (substring match), skipping", current_chat_name)
                    return True
                logger.info("Different chat is open ('%s' vs expected '%s'), need to switch", current_chat_name, chat_name)
            
            # Extract index from chat_id (format: chat_2__________)
            chat_index = None
            if chat_id.startswith('chat_') and '_' in chat_id:
                try:
                    index_part = chat_id.split('_')[1]
                    numeric_part = ''.join(filter(str.isdigit, index_part))
                    if numeric_part:
                        chat_index = int(numeric_part)
                        logger.info("Extracted chat index %d from chat_id %s", chat_index, chat_id)
                except (ValueError, IndexError) as e:
                    logger.warning("Failed to extract index from chat_id %s: %s", chat_id, str(e))
            
            # Helper function to verify opened chat
            async def verify_opened_chat(expected_name: str = None) -> Tuple[bool, str]:
                """
                Verify that the correct chat is opened by checking header.
                Returns (is_correct, opened_name)
                
                If expected_name is provided, verification is STRICT - must match.
                If expected_name is None, just returns the opened name.
                """
                try:
                    await asyncio.sleep(1.5)  # Wait for header to load
                    header_info = await page.evaluate("""
                        () => {
                            const header = document.querySelector('[data-testid="conversation-header"]') ||
                                          document.querySelector('header[role="banner"]') ||
                                          document.querySelector('div[data-testid="chatlist"] + div header');
                            if (!header) return null;
                            
                            const titleElement = header.querySelector('span[title]') ||
                                                header.querySelector('div[title]') ||
                                                header.querySelector('span[dir="auto"]') ||
                                                header;
                            const title = titleElement ? (titleElement.getAttribute('title') || titleElement.textContent || '').trim() : '';
                            
                            return { title: title, found: true };
                        }
                    """)
                    
                    opened_name = ""
                    if header_info and header_info.get('title'):
                        opened_name = header_info['title']
                        logger.info("Opened chat header shows: '%s'", opened_name)
                    
                    # If no expected name, just return what we found
                    if not expected_name:
                        return (True, opened_name)
                    
                    # If we have expected name but couldn't get opened name, it's an error
                    if not opened_name:
                        logger.warning("Chat verification failed: couldn't get opened chat name, but expected '%s'", expected_name)
                        return (False, "")
                    
                    # Normalize names for comparison (remove extra spaces, case insensitive)
                    normalized_opened = opened_name.lower().strip()
                    normalized_expected = expected_name.lower().strip()
                    
                    # Try exact match first
                    if normalized_opened == normalized_expected:
                        logger.info("Chat verification successful (exact match): '%s' == '%s'", opened_name, expected_name)
                        return (True, opened_name)
                    
                    # Try substring match (more lenient)
                    if normalized_expected in normalized_opened or normalized_opened in normalized_expected:
                        logger.info("Chat verification successful (substring match): '%s' contains '%s'", opened_name, expected_name)
                        return (True, opened_name)
                    
                    # No match - verification failed
                    logger.warning("Chat verification FAILED: opened '%s' but expected '%s'", opened_name, expected_name)
                    return (False, opened_name)
                    
                except Exception as e:
                    logger.error("Error verifying opened chat: %s", str(e), exc_info=True)
                    # If we have expected name, we must verify - so this is a failure
                    if expected_name:
                        return (False, "")
                    # If no expected name, we can't verify but it's not critical
                    return (True, "")
            
            # Strategy 1: Try to find by name first (most reliable if name is provided)
            if chat_name:
                logger.info("Trying to find chat by provided name: '%s'", chat_name)
                try:
                    # Get all chat elements and find by name
                    all_chats = await page.query_selector_all('div[role="row"], div[aria-label*="Chat"], div[data-testid="cell-frame-container"]')
                    logger.info("Found %d chat elements for name search", len(all_chats))
                    
                    normalized_search = chat_name.lower().strip()
                    matching_chats = []
                    
                    # First pass: collect all chats with their names
                    all_chat_names = []
                    for idx, chat_element in enumerate(all_chats):
                        try:
                            chat_info = await chat_element.evaluate("""
                                element => {
                                    const titleElement = element.querySelector('span[title]') ||
                                                       element.querySelector('div[title]') ||
                                                       element.querySelector('span[dir="auto"]');
                                    const title = titleElement ? (titleElement.getAttribute('title') || titleElement.textContent || '').trim() : '';
                                    const ariaLabel = element.getAttribute('aria-label') || '';
                                    return { title: title, ariaLabel: ariaLabel };
                                }
                            """)
                            
                            chat_title = chat_info.get('title', '') or chat_info.get('ariaLabel', '')
                            if chat_title:
                                all_chat_names.append(f"[{idx}] '{chat_title}'")
                                normalized_title = chat_title.lower().strip()
                                # Check for exact match first, then substring
                                is_exact = normalized_title == normalized_search
                                is_substring = normalized_search in normalized_title or normalized_title in normalized_search
                                
                                if is_exact or is_substring:
                                    matching_chats.append({
                                        'index': idx,
                                        'name': chat_title,
                                        'is_exact': is_exact,
                                        'element': chat_element
                                    })
                                    logger.info("Found potential match [%d]: '%s' (exact: %s, search: '%s')", idx, chat_title, is_exact, chat_name)
                        except Exception as e:
                            logger.debug("Error checking chat element %d: %s", idx, str(e))
                            continue
                    
                    # Log first 10 chat names for debugging
                    if all_chat_names:
                        logger.info("Sample chat names found (first 10): %s", ', '.join(all_chat_names[:10]))
                    
                    if not matching_chats:
                        logger.warning("No chats found matching name '%s' (searched in %d chats)", chat_name, len(all_chats))
                    else:
                        logger.info("Found %d potential matches for name '%s'", len(matching_chats), chat_name)
                    
                    # Sort: exact matches first
                    matching_chats.sort(key=lambda x: (not x['is_exact'], x['index']))
                    
                    # Try each matching chat until we find the correct one
                    for match in matching_chats:
                        logger.info("Trying chat at index %d: '%s'", match['index'], match['name'])
                        await match['element'].click()
                        
                        # Verify it's the correct chat
                        is_correct, opened_name = await verify_opened_chat(chat_name)
                        if is_correct:
                            logger.info("Successfully opened chat by name: '%s' (opened: '%s')", match['name'], opened_name)
                            return True
                        else:
                            logger.warning("Opened chat '%s' doesn't match expected '%s', trying next match...", opened_name, chat_name)
                    
                    if matching_chats:
                        logger.warning("Tried %d matching chats but none matched expected name '%s'", len(matching_chats), chat_name)
                except Exception as e:
                    logger.warning("Failed to find chat by name: %s", str(e))
            
            # Strategy 2: Try to find by index (fallback - WARNING: index may be unstable)
            # Only use this if name search failed and we have no other option
            if chat_index is not None and not chat_name:
                logger.warning("Using index-based search (unreliable) - chat_name not provided")
            if chat_index is not None:
                try:
                    logger.info("Trying to find chat by index %d", chat_index)
                    all_chats = await page.query_selector_all('div[role="row"], div[aria-label*="Chat"], div[data-testid="cell-frame-container"]')
                    logger.info("Found %d chat elements", len(all_chats))
                    
                    if chat_index < len(all_chats):
                        # Before clicking, check the name of the chat at this index (if we have expected name)
                        if chat_name:
                            try:
                                chat_info = await all_chats[chat_index].evaluate("""
                                    element => {
                                        const titleElement = element.querySelector('span[title]') ||
                                                           element.querySelector('div[title]') ||
                                                           element.querySelector('span[dir="auto"]');
                                        const title = titleElement ? (titleElement.getAttribute('title') || titleElement.textContent || '').trim() : '';
                                        const ariaLabel = element.getAttribute('aria-label') || '';
                                        return { title: title, ariaLabel: ariaLabel };
                                    }
                                """)
                                chat_title = chat_info.get('title', '') or chat_info.get('ariaLabel', '')
                                if chat_title:
                                    normalized_title = chat_title.lower().strip()
                                    normalized_expected = chat_name.lower().strip()
                                    if normalized_title != normalized_expected and normalized_expected not in normalized_title and normalized_title not in normalized_expected:
                                        logger.warning("Chat at index %d has name '%s' but expected '%s' - index may be wrong, trying anyway...", 
                                                     chat_index, chat_title, chat_name)
                                    else:
                                        logger.info("Chat at index %d has matching name '%s'", chat_index, chat_title)
                            except Exception as e:
                                logger.debug("Couldn't check chat name at index %d: %s", chat_index, str(e))
                        
                        logger.info("Clicking on chat element at index %d", chat_index)
                        await all_chats[chat_index].click()
                        
                        # Wait for chat panel to appear
                        chat_opened = False
                        for wait_attempt in range(5):
                            await asyncio.sleep(1.0)
                            has_conversation = await page.evaluate("""
                                () => {
                                    return !!(
                                        document.querySelector('[data-testid="conversation-header"]') ||
                                        document.querySelector('div[role="log"]') ||
                                        document.querySelector('[data-testid="conversation-panel-messages"]') ||
                                        document.querySelector('[data-testid="msg-container"]')
                                    );
                                }
                            """)
                            if has_conversation:
                                chat_opened = True
                                logger.info("Chat panel opened (attempt %d)", wait_attempt + 1)
                                break
                        
                        if chat_opened:
                            # Verify it's the correct chat (STRICT - must match if name provided)
                            is_correct, opened_name = await verify_opened_chat(chat_name)
                            if is_correct:
                                logger.info("Successfully clicked on chat at index %d (opened: '%s')", chat_index, opened_name)
                                return True
                            else:
                                logger.warning("Chat at index %d doesn't match expected name (opened: '%s', expected: '%s'), trying other methods...", 
                                             chat_index, opened_name, chat_name)
                        else:
                            logger.warning("Chat panel may not have opened after clicking index %d", chat_index)
                            # Still try to verify - maybe it opened but we didn't detect it
                            is_correct, opened_name = await verify_opened_chat(chat_name)
                            if is_correct:
                                logger.info("Chat panel opened (verified: '%s')", opened_name)
                                return True
                    else:
                        logger.warning("Chat index %d is out of range (total chats: %d)", chat_index, len(all_chats))
                except Exception as e:
                    logger.warning("Failed to click chat by index: %s", str(e))
            
            # Strategy 3: Fallback - try to find by name/ID selectors
            logger.info("Trying to find chat by name/ID selectors")
            search_terms = [chat_name] if chat_name else []
            search_terms.append(chat_id)
            
            for search_term in search_terms:
                if not search_term:
                    continue
                chat_selectors = [
                    f'div[aria-label*="{search_term}"]',
                    f'div[title*="{search_term}"]',
                    f'span[title*="{search_term}"]',
                ]
                
                for selector in chat_selectors:
                    try:
                        chat_element = await page.query_selector(selector)
                        if chat_element:
                            logger.info("Found chat element with selector: %s", selector)
                            await chat_element.click()
                            await asyncio.sleep(2.0)
                            
                            # Verify it's the correct chat
                            is_correct, opened_name = await verify_opened_chat(chat_name)
                            if is_correct:
                                logger.info("Clicked on chat %s using selector (opened: '%s')", search_term, opened_name)
                                return True
                            else:
                                logger.warning("Chat opened by selector doesn't match (opened: '%s', expected: '%s')", opened_name, chat_name)
                    except Exception as e:
                        logger.debug("Selector %s failed: %s", selector, str(e))
                        continue
            
            logger.error("Failed to open chat %s with any method", chat_id)
            return False
            
        except Exception as e:
            logger.error("Failed to open chat: %s", str(e), exc_info=True)
            return False
    
    async def _find_message_container(self, page: Page) -> Optional[ElementHandle]:
        """Find the message container using multiple strategies"""
        # Strategy 1: JavaScript-based search
        container_info = await page.evaluate("""
            () => {
                const selectors = [
                    'div[role="log"]',
                    'div[data-testid="conversation-panel-messages"]',
                    'div[data-testid="msg-container"]',
                    'div#main > div > div > div[role="application"] > div > div > div > div',
                ];
                
                for (const selector of selectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        return { found: true, selector: selector };
                    }
                }
                
                // Broad search: find scrollable containers with messages
                const allDivs = Array.from(document.querySelectorAll('div'));
                const candidates = allDivs
                    .filter(div => {
                        const hasScroll = div.scrollHeight > div.clientHeight && div.scrollHeight > 200;
                        const hasMessageElements = div.querySelector('[data-testid*="msg"], span.selectable-text, div[data-id]');
                        return hasScroll && hasMessageElements;
                    })
                    .sort((a, b) => b.scrollHeight - a.scrollHeight);
                
                if (candidates.length > 0) {
                    const candidate = candidates[0];
                    const index = Array.from(document.querySelectorAll('div')).indexOf(candidate);
                    return {
                        found: true,
                        selector: 'broad-search',
                        index: index,
                        scrollHeight: candidate.scrollHeight,
                    };
                }
                
                return { found: false };
            }
        """)
        
        message_container = None
        if container_info.get('found'):
            if container_info.get('selector') != 'broad-search':
                try:
                    message_container = await page.query_selector(container_info.get('selector'))
                except Exception:
                    pass
            else:
                # Broad search: get element by index
                try:
                    container_selector_info = await page.evaluate("""
                        () => {
                            const allDivs = Array.from(document.querySelectorAll('div'));
                            const candidates = allDivs
                                .filter(div => {
                                    const hasScroll = div.scrollHeight > div.clientHeight && div.scrollHeight > 200;
                                    const hasMessageElements = div.querySelector('[data-testid*="msg"], span.selectable-text, div[data-id]');
                                    return hasScroll && hasMessageElements;
                                })
                                .sort((a, b) => b.scrollHeight - a.scrollHeight);
                            
                            if (candidates.length > 0) {
                                const candidate = candidates[0];
                                const index = Array.from(document.querySelectorAll('div')).indexOf(candidate);
                                return {
                                    found: true,
                                    index: index,
                                    scrollHeight: candidate.scrollHeight,
                                };
                            }
                            return { found: false };
                        }
                    """)
                    
                    if container_selector_info.get('found'):
                        all_divs = await page.query_selector_all('div')
                        target_index = container_selector_info.get('index')
                        if target_index is not None and target_index < len(all_divs):
                            message_container = all_divs[target_index]
                            logger.info("Successfully got message container from broad search (index %d, scrollHeight: %d)", 
                                      target_index, container_selector_info.get('scrollHeight', 0))
                except Exception as e:
                    logger.warning("Failed to get element by index: %s", str(e))
        
        # Fallback: try standard selectors
        if not message_container:
            container_selectors = [
                'div[role="log"]',
                'div[data-testid="conversation-panel-messages"]',
                'div[data-testid="msg-container"]',
                'div#main > div > div > div[role="application"] > div > div > div > div',
            ]
            
            for selector in container_selectors:
                try:
                    message_container = await page.wait_for_selector(selector, timeout=3000)
                    if message_container:
                        logger.info("Found message container with wait: %s", selector)
                        break
                except Exception:
                    continue
            
            if not message_container:
                for selector in container_selectors:
                    try:
                        message_container = await page.query_selector(selector)
                        if message_container:
                            logger.info("Found message container with direct query: %s", selector)
                            break
                    except Exception:
                        continue
        
        if not message_container:
            # Take screenshot for debugging
            try:
                screenshot_path = f"/tmp/whatsapp_error_{int(time.time())}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.error("Screenshot saved to: %s", screenshot_path)
            except Exception as e:
                logger.warning("Failed to take screenshot: %s", str(e))
        
        return message_container
    
    async def _parse_all_messages(self, page: Page, container: Optional[ElementHandle] = None) -> List[Dict]:
        """Parse all visible messages from the page or within a specific container"""
        try:
            # Use provided container or try to find one
            if container:
                logger.info("_parse_all_messages: using provided container")
                # Verify container is still valid
                try:
                    container_info = await container.evaluate("element => ({ scrollHeight: element.scrollHeight, clientHeight: element.clientHeight, childCount: element.children.length, tagName: element.tagName })")
                    logger.info("_parse_all_messages: container info - scrollHeight=%s, clientHeight=%s, childCount=%s, tagName=%s", 
                               container_info.get('scrollHeight'), 
                               container_info.get('clientHeight'),
                               container_info.get('childCount'),
                               container_info.get('tagName'))
                    
                    if container_info.get('scrollHeight', 0) < 50:
                        logger.warning("_parse_all_messages: container seems too small (scrollHeight=%s), but continuing anyway", 
                                     container_info.get('scrollHeight'))
                except Exception as e:
                    logger.warning("_parse_all_messages: container validation check failed: %s, but continuing with container anyway", str(e))
            
            if not container:
                logger.debug("_parse_all_messages: container not provided or invalid, searching...")
                container_selectors = [
                    'div[role="log"]',
                    'div[data-testid="conversation-panel-messages"]',
                    'div[data-testid="msg-container"]',
                    'div#main > div > div > div[role="application"] > div > div > div > div',
                ]
                
                for selector in container_selectors:
                    try:
                        container = await page.query_selector(selector)
                        if container:
                            logger.debug("_parse_all_messages: found container with selector: %s", selector)
                            break
                    except Exception:
                        continue
            
            if not container:
                logger.warning("Message container not found in _parse_all_messages with any selector")
                return []
            
            # Parse messages WITHIN the container (not the whole page!)
            messages_data = await container.evaluate("""
                (element) => {
                    const messages = [];
                    const processedIds = new Set();
                    
                    const messageSelectors = [
                        'div[data-testid="msg-container"]',
                        'div[data-id]',
                        'div[role="row"]',
                    ];
                    
                    let messageElements = [];
                    
                    // Search WITHIN container (element), not document
                    for (const selector of messageSelectors) {
                        messageElements = Array.from(element.querySelectorAll(selector));
                        if (messageElements.length > 0) {
                            console.log('Found', messageElements.length, 'elements with selector:', selector, 'inside container');
                            break;
                        }
                    }
                    
                    // If still no elements, try broader search within container
                    if (messageElements.length === 0) {
                        const allDivs = element.querySelectorAll('div');
                        messageElements = Array.from(allDivs).filter(div => {
                            return div.querySelector('[data-testid="msg-text"], span.selectable-text, img[src], video, audio') ||
                                   div.getAttribute('data-id') ||
                                   div.getAttribute('data-testid');
                        });
                        console.log('Found', messageElements.length, 'potential message elements with broader search inside container');
                    }
                    
                    for (let i = 0; i < messageElements.length; i++) {
                        const msgElement = messageElements[i];
                        try {
                            const isSystemMessage = msgElement.querySelector('[data-testid="status"], [data-testid="msg-status"], [data-icon="check-dbl"], [data-icon="check"]');
                            if (isSystemMessage && !msgElement.querySelector('[data-testid="msg-text"], span.selectable-text, img, video, audio, a[href]')) {
                                continue;
                            }
                            
                            const msgId = msgElement.getAttribute('data-id') || msgElement.getAttribute('data-testid') || i.toString();
                            if (processedIds.has(msgId)) continue;
                            processedIds.add(msgId);
                            
                            let text = '';
                            const textSelectors = [
                                '[data-testid="msg-text"]',
                                'span.selectable-text',
                                'span[dir="ltr"]',
                                'div[dir="ltr"]',
                                'span.copyable-text'
                            ];
                            
                            for (const selector of textSelectors) {
                                const textElement = msgElement.querySelector(selector);
                                if (textElement) {
                                    text = textElement.textContent.trim();
                                    if (text) break;
                                }
                            }
                            
                            let sender = 'Unknown';
                            const senderSelectors = [
                                '[data-testid="conversation-info-header"]',
                                'span[title]',
                                'div[title]',
                                '[data-testid="msg-meta"] span',
                                '.message-author'
                            ];
                            
                            for (const selector of senderSelectors) {
                                const senderElement = msgElement.querySelector(selector);
                                if (senderElement) {
                                    sender = senderElement.getAttribute('title') || senderElement.textContent.trim();
                                    if (sender && sender !== 'Unknown') break;
                                }
                            }
                            
                            let msgType = 'text';
                            let mediaPath = null;
                            
                            const imgElement = msgElement.querySelector('img[src]');
                            if (imgElement) {
                                const imgSrc = imgElement.getAttribute('src');
                                if (imgSrc && !imgSrc.includes('data:image/svg+xml')) {
                                    msgType = 'image';
                                    mediaPath = imgSrc;
                                    const parentClasses = msgElement.className || '';
                                    if (parentClasses.includes('sticker') || imgSrc.includes('sticker')) {
                                        msgType = 'sticker';
                                    } else if (imgSrc.includes('gif') || parentClasses.includes('gif')) {
                                        msgType = 'gif';
                                    }
                                }
                            }
                            
                            if (msgType === 'text') {
                                const videoElement = msgElement.querySelector('video[src], video source[src]');
                                if (videoElement) {
                                    msgType = 'video';
                                    mediaPath = videoElement.getAttribute('src') || videoElement.querySelector('source')?.getAttribute('src');
                                }
                            }
                            
                            if (msgType === 'text') {
                                const audioElement = msgElement.querySelector('audio[src], audio source[src]');
                                if (audioElement) {
                                    const isVoiceNote = msgElement.querySelector('[data-testid="ptt"], [data-icon="mic"]');
                                    msgType = isVoiceNote ? 'voice' : 'audio';
                                    mediaPath = audioElement.getAttribute('src') || audioElement.querySelector('source')?.getAttribute('src');
                                }
                            }
                            
                            if (msgType === 'text') {
                                const docElement = msgElement.querySelector('[data-testid="media-document"], a[href*="blob"], a[download]');
                                if (docElement) {
                                    msgType = 'document';
                                    mediaPath = docElement.getAttribute('href') || docElement.getAttribute('src');
                                }
                            }
                            
                            let timestamp = new Date().toISOString();
                            const timeSelectors = [
                                'span[title]',
                                'div[title]',
                                '[data-testid="msg-meta"] span',
                                '.message-time'
                            ];
                            
                            for (const selector of timeSelectors) {
                                const timeElement = msgElement.querySelector(selector);
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
                            
                            const hasContent = text || (msgType !== 'text' && mediaPath);
                            const isStatusOnly = msgElement.querySelector('[data-icon="check"], [data-icon="check-dbl"]') && !hasContent;
                            
                            if (hasContent && !isStatusOnly) {
                                messages.push({
                                    id: msgId,
                                    timestamp: timestamp,
                                    sender: sender,
                                    type: msgType,
                                    text: text || '',
                                    media_path: mediaPath
                                });
                            }
                        } catch (e) {
                            console.error('Error parsing message element:', e);
                        }
                    }
                    
                    return messages;
                }
            """)
            
            # Convert to proper format
            result = []
            for msg in messages_data or []:
                result.append({
                    'id': msg.get('id', ''),
                    'timestamp': msg.get('timestamp', ''),
                    'sender': msg.get('sender', 'Unknown'),
                    'type': msg.get('type', 'text'),
                    'text': msg.get('text', ''),
                    'media_path': msg.get('media_path') if msg.get('media_path') else None,
                })
            
            if len(result) > 0:
                logger.info("_parse_all_messages: successfully parsed %d messages", len(result))
            else:
                logger.warning("_parse_all_messages: parsed 0 messages")
                # Additional diagnostic when no messages found
                try:
                    if container:
                        diagnostic = await container.evaluate("""
                            element => {
                                const allDivs = element.querySelectorAll('div');
                                const msgElements = {
                                    dataId: element.querySelectorAll('div[data-id]').length,
                                    msgContainer: element.querySelectorAll('[data-testid*="msg"]').length,
                                    selectableText: element.querySelectorAll('span.selectable-text').length,
                                    totalDivs: allDivs.length,
                                    hasText: Array.from(allDivs).some(div => div.textContent && div.textContent.trim().length > 0)
                                };
                                return msgElements;
                            }
                        """)
                        logger.warning("_parse_all_messages: diagnostic - dataId=%s, msgContainer=%s, selectableText=%s, totalDivs=%s, hasText=%s",
                                     diagnostic.get('dataId', 0),
                                     diagnostic.get('msgContainer', 0),
                                     diagnostic.get('selectableText', 0),
                                     diagnostic.get('totalDivs', 0),
                                     diagnostic.get('hasText', False))
                except Exception as diag_err:
                    logger.warning("_parse_all_messages: failed to get diagnostic: %s", str(diag_err))
            
            return result
            
        except Exception as e:
            logger.error("Error parsing all messages: %s", str(e), exc_info=True)
            return []
