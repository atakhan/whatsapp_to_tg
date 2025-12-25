"""
Base interface for chat data sources.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..models.raw_chat import RawChat


class IChatSource(ABC):
    """
    Interface for chat data sources.
    
    All sources (Store, CDP Network, DOM) must implement this interface.
    This allows the orchestrator to work with any source transparently.
    """
    
    @abstractmethod
    async def init(self) -> None:
        """
        Initialize the data source.
        
        This should:
        - Check if the source is available
        - Prepare any necessary connections/sessions
        - Validate that the source can provide data
        
        Raises:
            SourceUnavailableError: If source cannot be initialized
        """
        pass
    
    @abstractmethod
    async def fetch_batch(self) -> List[RawChat]:
        """
        Fetch a batch of raw chats from the source.
        
        Returns:
            List of RawChat objects. Empty list if no more chats available.
            
        Note:
            For sources like Store, this may return all chats at once.
            For sources like DOM, this may return only visible chats.
        """
        pass
    
    @abstractmethod
    async def is_complete(self) -> bool:
        """
        Check if all available chats have been fetched.
        
        Returns:
            True if all chats have been fetched, False otherwise.
            
        Note:
            For sources with known total count, this should check
            if collected count == total count.
            For sources without known total, this may use heuristics.
        """
        pass
    
    @abstractmethod
    async def total_expected(self) -> Optional[int]:
        """
        Get the expected total number of chats.
        
        Returns:
            Total number of chats if known, None otherwise.
            
        Note:
            Store source should provide this from internal state.
            CDP Network source may provide this from API responses.
            DOM source typically returns None (unknown).
        """
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        Get the name of this source for logging and diagnostics.
        
        Returns:
            Source name: 'store', 'network', or 'dom'
        """
        pass
    
    @property
    def is_available(self) -> bool:
        """
        Check if source is currently available.
        
        Default implementation returns True. Override if source
        needs to check availability dynamically.
        """
        return True


class SourceUnavailableError(Exception):
    """Raised when a source cannot be initialized or is unavailable."""
    pass


