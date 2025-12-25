"""
Result publisher - publishes parsing results.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional
import logging

from ..models.chat_dto import ChatDTO
from ..models.parsing_result import ParsingResult

logger = logging.getLogger(__name__)


class ResultPublisher:
    """
    Publishes parsing results in streaming or final format.
    """
    
    async def publish_stream(
        self,
        chats: AsyncGenerator[List[ChatDTO], None],
        source_type: str,
        source_degraded: bool,
        expected_total: Optional[int] = None
    ) -> AsyncGenerator[ParsingResult, None]:
        """
        Stream parsing results as they are collected.
        
        Args:
            chats: Async generator of chat batches
            source_type: Type of source used
            source_degraded: Whether fallback source was used
            expected_total: Optional expected total count (for progress tracking)
            
        Yields:
            ParsingResult objects with incremental chat data
        """
        all_chats: List[ChatDTO] = []
        
        async for batch in chats:
            all_chats.extend(batch)
            
            # Determine completeness for this batch
            # If we have expected_total and reached it, mark as complete
            completeness = "partial"
            if expected_total is not None and len(all_chats) >= expected_total:
                completeness = "complete"
            
            # Publish intermediate result
            result = ParsingResult(
                chats=all_chats.copy(),  # Copy to avoid mutation
                completeness=completeness,
                collected=len(all_chats),
                expected=expected_total,
                source_type=source_type,
                source_degraded=source_degraded,
                anomalies=[],  # Anomalies will be detected at the end
                metadata={
                    'streaming': True,
                    'batch_count': len(batch)
                }
            )
            
            yield result
        
        # Final result will be published separately by orchestrator
        # after completion check and anomaly detection
    
    async def publish_final(
        self,
        chats: List[ChatDTO],
        completeness: str,
        expected: Optional[int],
        missing_ids: List[str],
        source_type: str,
        source_degraded: bool,
        anomalies: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> ParsingResult:
        """
        Publish final parsing result.
        
        Args:
            chats: Complete list of parsed chats
            completeness: "complete" or "partial"
            expected: Expected total count
            missing_ids: List of missing chat IDs
            source_type: Type of source used
            source_degraded: Whether fallback source was used
            anomalies: List of detected anomalies
            metadata: Additional metadata
            
        Returns:
            Final ParsingResult
        """
        result = ParsingResult(
            chats=chats,
            completeness=completeness,
            collected=len(chats),
            expected=expected,
            missing_ids=missing_ids,
            source_type=source_type,
            source_degraded=source_degraded,
            anomalies=anomalies,
            metadata=metadata
        )
        
        logger.info(
            "Published final result: %d chats, completeness=%s, source=%s",
            len(chats), completeness, source_type
        )
        
        return result

