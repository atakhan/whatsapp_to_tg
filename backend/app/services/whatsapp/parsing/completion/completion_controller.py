"""
Completion controller - determines when parsing is complete.
"""

from typing import List, Optional, Tuple
import logging

from ..models.chat_dto import ChatDTO
from ..sources.base import IChatSource

logger = logging.getLogger(__name__)


class CompletionController:
    """
    Implements deterministic completion criteria.
    
    Completion is determined by:
    1. Source explicitly signals completion (is_complete() == True)
    2. Collected count == expected total (if known)
    """
    
    async def check_completion(
        self,
        collected_chats: List[ChatDTO],
        source: IChatSource
    ) -> Tuple[bool, Optional[int], List[str]]:
        """
        Check if parsing is complete.
        
        Args:
            collected_chats: List of collected chats so far
            source: The data source being used
            
        Returns:
            Tuple of (is_complete, expected_total, missing_ids)
        """
        collected_count = len(collected_chats)
        
        # Check if source signals completion
        try:
            source_complete = await source.is_complete()
        except Exception as e:
            logger.warning("Error checking source completion: %s", str(e))
            source_complete = False
        
        # Get expected total
        try:
            expected_total = await source.total_expected()
        except Exception as e:
            logger.warning("Error getting expected total: %s", str(e))
            expected_total = None
        
        # Determine completion
        if source_complete:
            # Source says it's complete
            if expected_total is not None:
                # Check if we have all expected chats
                if collected_count >= expected_total:
                    missing_ids = self._calculate_missing_ids(
                        collected_chats, expected_total
                    )
                    return True, expected_total, missing_ids
                else:
                    # Source says complete but we're missing chats
                    logger.warning(
                        "Source reports complete but collected (%d) < expected (%d)",
                        collected_count, expected_total
                    )
                    missing_ids = self._calculate_missing_ids(
                        collected_chats, expected_total
                    )
                    return False, expected_total, missing_ids
            else:
                # Source complete but no expected total
                return True, None, []
        else:
            # Source not complete yet
            if expected_total is not None:
                missing_ids = self._calculate_missing_ids(
                    collected_chats, expected_total
                )
                return False, expected_total, missing_ids
            else:
                # No expected total, can't determine completion
                return False, None, []
    
    def _calculate_missing_ids(
        self,
        collected_chats: List[ChatDTO],
        expected_total: int
    ) -> List[str]:
        """
        Calculate missing chat IDs.
        
        Note: Without knowing the full list of expected IDs from the source,
        we can only report the count of missing chats, not specific IDs.
        This is acceptable for the current implementation as sources like
        Store provide total count but not the full list of IDs.
        
        Returns:
            Empty list (specific IDs unknown) if missing chats detected,
            otherwise empty list
        """
        collected_count = len(collected_chats)
        if collected_count < expected_total:
            missing_count = expected_total - collected_count
            logger.warning(
                "Missing %d chats (collected: %d, expected: %d). "
                "Specific IDs unknown without full expected list from source.",
                missing_count, collected_count, expected_total
            )
            # Return empty list - we don't know which specific IDs are missing
            # This is acceptable as we report the count in ParsingResult
            return []
        return []
    
    def determine_completeness_status(
        self,
        is_complete: bool,
        collected: int,
        expected: Optional[int]
    ) -> str:
        """
        Determine completeness status string.
        
        Args:
            is_complete: Whether parsing is complete
            collected: Number of collected chats
            expected: Expected total (if known)
            
        Returns:
            "complete" or "partial"
        """
        if is_complete:
            if expected is not None:
                if collected >= expected:
                    return "complete"
                else:
                    # Complete according to source, but missing some
                    return "partial"
            else:
                # Complete according to source, no expected total
                return "complete"
        else:
            return "partial"

