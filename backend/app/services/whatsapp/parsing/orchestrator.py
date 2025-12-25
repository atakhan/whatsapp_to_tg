"""
Chat parsing orchestrator - main entry point.
Coordinates all components: sources, normalizers, identity resolver, completion, and publisher.
"""

from typing import AsyncGenerator, List, Optional
import logging
from datetime import datetime

from playwright.async_api import Page

from .models.chat_dto import ChatDTO
from .models.parsing_result import ParsingResult
from .models.raw_chat import RawChat

from .sources.source_selector import SourceSelector
from .sources.base import IChatSource

from .normalizers.chat_normalizer import ChatNormalizer
from .identity.identity_resolver import IdentityResolver
from .completion.completion_controller import CompletionController
from .publishers.result_publisher import ResultPublisher

logger = logging.getLogger(__name__)


class ChatParsingOrchestrator:
    """
    Main orchestrator for chat parsing.
    
    Coordinates:
    - Source selection and data fetching
    - Data normalization
    - Identity resolution
    - Completion checking
    - Result publishing
    """
    
    def __init__(self):
        """Initialize orchestrator with all components."""
        self.source_selector = SourceSelector()
        self.normalizer = ChatNormalizer()
        self.identity_resolver = IdentityResolver()
        self.completion_controller = CompletionController()
        self.publisher = ResultPublisher()
    
    async def parse_chats_streaming(
        self,
        page: Page
    ) -> AsyncGenerator[ParsingResult, None]:
        """
        Parse chats from page, streaming results as they are collected.
        
        Args:
            page: Playwright page instance with WhatsApp Web loaded
            
        Yields:
            ParsingResult objects with incremental chat data
            
        Process:
            1. Select best available source (Store → CDP Network → DOM)
            2. Initialize source
            3. Fetch batches of raw chats
            4. Normalize and resolve IDs
            5. Stream intermediate results
            6. Check completion
            7. Detect anomalies
            8. Publish final result
        """
        source: Optional[IChatSource] = None
        source_degraded = False
        source_metadata = {}
        
        try:
            # Step 1: Select source
            logger.info("Selecting chat data source...")
            source, source_degraded, source_metadata = await self.source_selector.select_source(page)
            source_type = source.source_name
            
            logger.info(
                "Selected source: %s (degraded=%s)",
                source_type,
                source_degraded
            )
            
            # Step 2: Initialize source (if not already done)
            if not hasattr(source, '_initialized') or not source._initialized:
                await source.init()
            
            # Get expected total for progress tracking
            expected_total = await source.total_expected()
            
            # Step 3: Collect all chats
            all_raw_chats: List[RawChat] = []
            all_normalized_chats: List[ChatDTO] = []
            
            # Fetch batches and normalize
            batch_count = 0
            async for raw_batch in self._fetch_batches(source):
                batch_count += 1
                all_raw_chats.extend(raw_batch)
                
                # Normalize batch
                normalized_batch = self.normalizer.normalize_batch(
                    raw_batch,
                    identity_resolver=self.identity_resolver
                )
                all_normalized_chats.extend(normalized_batch)
                
                # Stream intermediate result
                intermediate_result = await self.publisher.publish_stream(
                    self._chats_to_generator(normalized_batch),
                    source_type=source_type,
                    source_degraded=source_degraded,
                    expected_total=expected_total
                )
                
                async for result in intermediate_result:
                    yield result
            
            logger.info(
                "Collected %d raw chats, normalized to %d chats (batches: %d)",
                len(all_raw_chats),
                len(all_normalized_chats),
                batch_count
            )
            
            # Fallback logic: If we got 0 chats from CDP Network, try DOM source
            if len(all_normalized_chats) == 0 and source_type == "network":
                logger.warning(
                    "CDP Network source returned 0 chats, falling back to DOM source"
                )
                try:
                    from .sources.dom_chat_source import DOMChatSource
                    dom_source = DOMChatSource(page)
                    await dom_source.init()
                    
                    # Fetch from DOM
                    dom_raw_chats: List[RawChat] = []
                    async for raw_batch in self._fetch_batches(dom_source):
                        dom_raw_chats.extend(raw_batch)
                    
                    if dom_raw_chats:
                        # Normalize DOM chats
                        dom_normalized = self.normalizer.normalize_batch(
                            dom_raw_chats,
                            identity_resolver=self.identity_resolver
                        )
                        all_normalized_chats.extend(dom_normalized)
                        all_raw_chats.extend(dom_raw_chats)
                        
                        source_type = "dom"
                        source_degraded = True
                        expected_total = await dom_source.total_expected()
                        
                        logger.info(
                            "DOM fallback successful: collected %d chats",
                            len(dom_normalized)
                        )
                except Exception as e:
                    logger.warning(
                        "DOM fallback failed: %s",
                        str(e)
                    )
            
            # Step 4: Check completion
            is_complete, final_expected, missing_ids = await self.completion_controller.check_completion(
                all_normalized_chats,
                source
            )
            
            # Update expected if we got it from completion controller
            if final_expected is not None:
                expected_total = final_expected
            
            # Step 5: Determine completeness status
            completeness = self.completion_controller.determine_completeness_status(
                is_complete,
                len(all_normalized_chats),
                expected_total
            )
            
            # Step 6: Detect anomalies
            anomalies = self.identity_resolver.detect_ambiguities(all_normalized_chats)
            
            # Validate uniqueness
            is_unique, duplicate_ids = self.identity_resolver.validate_uniqueness(all_normalized_chats)
            if not is_unique:
                anomalies.append({
                    'type': 'duplicate_ids',
                    'duplicate_ids': duplicate_ids,
                    'count': len(duplicate_ids)
                })
                logger.warning(
                    "Found %d duplicate chat IDs: %s",
                    len(duplicate_ids),
                    duplicate_ids[:10]  # Log first 10
                )
            
            # Step 7: Prepare metadata
            metadata = {
                'source_metadata': source_metadata,
                'batch_count': batch_count,
                'raw_chats_count': len(all_raw_chats),
                'normalized_chats_count': len(all_normalized_chats),
                'anomalies_count': len(anomalies),
                'duplicate_ids_count': len(duplicate_ids) if not is_unique else 0,
                'parsing_timestamp': datetime.utcnow().isoformat(),
            }
            
            # Step 8: Publish final result
            final_result = await self.publisher.publish_final(
                chats=all_normalized_chats,
                completeness=completeness,
                expected=expected_total,
                missing_ids=missing_ids,
                source_type=source_type,
                source_degraded=source_degraded,
                anomalies=anomalies,
                metadata=metadata
            )
            
            yield final_result
            
            # Cleanup if source has cleanup method
            if hasattr(source, 'cleanup'):
                try:
                    await source.cleanup()
                except Exception as e:
                    logger.warning("Error cleaning up source: %s", str(e))
            
        except Exception as e:
            logger.error(
                "Error in chat parsing orchestrator: %s",
                str(e),
                exc_info=True
            )
            # Yield error result
            error_result = ParsingResult(
                chats=[],
                completeness="partial",
                collected=0,
                expected=None,
                source_type=source.source_name if source else "unknown",
                source_degraded=source_degraded,
                anomalies=[{
                    'type': 'parsing_error',
                    'error': str(e)
                }],
                metadata={
                    'error': True,
                    'error_message': str(e),
                    'source_metadata': source_metadata
                }
            )
            yield error_result
    
    async def parse_chats(
        self,
        page: Page
    ) -> ParsingResult:
        """
        Parse all chats from page (non-streaming, blocking).
        
        Args:
            page: Playwright page instance with WhatsApp Web loaded
            
        Returns:
            Final ParsingResult with all chats
        """
        # Collect all results from streaming
        final_result: Optional[ParsingResult] = None
        
        async for result in self.parse_chats_streaming(page):
            final_result = result
        
        return final_result or ParsingResult(
            chats=[],
            completeness="partial",
            collected=0,
            source_type="unknown"
        )
    
    async def _fetch_batches(
        self,
        source: IChatSource
    ) -> AsyncGenerator[List[RawChat], None]:
        """
        Fetch batches of raw chats from source.
        
        Args:
            source: Data source to fetch from
            
        Yields:
            Batches of RawChat objects
        """
        # For sources like Store, fetch_batch returns all chats at once
        # For sources like DOM, we may need to fetch multiple batches
        
        max_iterations = 100  # Safety limit
        iteration = 0
        
        while iteration < max_iterations:
            batch = await source.fetch_batch()
            
            # For DOM source, empty batch doesn't mean we're done - we need to keep scrolling
            # Only break if source explicitly says it's complete
            if batch:
                yield batch
            
            # Check if source is complete (even if batch was empty)
            if await source.is_complete():
                logger.debug(
                    "Source %s marked as complete after %d iterations",
                    source.source_name,
                    iteration + 1
                )
                break
            
            # For DOM source, continue even if batch is empty (might need more scrolling)
            if not batch and source.source_name != 'dom':
                # For non-DOM sources, empty batch means done
                logger.debug(
                    "Source %s returned empty batch, stopping",
                    source.source_name
                )
                break
            
            iteration += 1
        
        if iteration >= max_iterations:
            logger.warning(
                "Reached max iterations (%d) for fetching batches from source %s",
                max_iterations,
                source.source_name
            )
    
    async def _chats_to_generator(
        self,
        chats: List[ChatDTO]
    ) -> AsyncGenerator[List[ChatDTO], None]:
        """Convert list of chats to async generator."""
        yield chats
